import os
import json
import asyncio
from typing import List, Dict, Set
from enum import Enum
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware

from .utils.logging_middleware_judge_api import LoggingMiddleware, metrics_app
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import aioboto3
from botocore.exceptions import ClientError

from .utils.logging_middleware_judge_api import (
    logger
)

from .executor import SupportedLanguage, ExecutionResult
from .utils.rabbitmq_rpc_judge_api import RpcClient, get_rpc_client


# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=False)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_PROBLEMS_BUCKET = os.getenv("AWS_PROBLEMS_BUCKET", "codeground-problems")
AWS_PROBLEMS_BUCKET_PREFIX = os.getenv("AWS_PROBLEMS_BUCKET_PREFIX", "").strip("/")
PROBLEMS_BUCKET_ENDPOINT = os.getenv("PROBLEMS_BUCKET_ENDPOINT")
SADPANDA_VALUE = os.getenv("SADPANDA", "")

class CodeRequest(BaseModel):
    language: SupportedLanguage
    code: str
    stdins: List[str] = []
    timeLimit: int = 30000
    memoryLimit: int = 256
    token: str | None = None

class CodeV3Request(BaseModel):
    language: SupportedLanguage
    code: str
    problemId: str
    token: str | None = None

class ResultStatus(str, Enum):
    SUCCESS = "success"
    COMPILE_ERROR = "compile_error"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_EXCEPTION = "runtime_exception"
    WRONG_OUTPUT = "wrong_output"
    TIMEOUT = "timeout"
    FAILURE = "failure"

app = FastAPI()
app.add_middleware(LoggingMiddleware)
app.mount("/metrics", metrics_app)
app.state.ws_connections: Dict[str, Set[WebSocket]] = {}
app.state.progress_queue = None
app.state.v3_meta: Dict[str, dict] = {}

# CORS 설정
# 기본 오리진 목록을 `.env`의 `CORS_ALLOW_ORIGINS`로 확장할 수 있다.
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://localhost:8097",
    "http://localhost:18651",
]

extra_origins = os.getenv("CORS_ALLOW_ORIGINS")
if extra_origins:
    origins.extend(o.strip() for o in extra_origins.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    logger.info("Starting up RPC client...")
    url = os.getenv("RABBITMQ_URL", "asdf")
    logger.info(f"Connecting to RabbitMQ at {url}")
    app.state.rpc: RpcClient = await get_rpc_client()
    app.state.progress_queue = await app.state.rpc.channel.declare_queue("progress", durable=True)
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_REGION:
        app.state.s3_session = aioboto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
    else:
        app.state.s3_session = None
    app.state.aws_region = AWS_REGION
    app.state.problems_bucket = AWS_PROBLEMS_BUCKET
    prefix = AWS_PROBLEMS_BUCKET_PREFIX.strip("/")
    app.state.problems_prefix = f"{prefix}/" if prefix else ""
    app.state.problems_endpoint = PROBLEMS_BUCKET_ENDPOINT
    app.state.problems_local_dir = (
        Path(__file__).resolve().parents[1]
        / "static"
        / app.state.problems_bucket
    )
    asyncio.create_task(progress_consumer())


@app.on_event("shutdown")
async def shutdown() -> None:
    await app.state.rpc.close()


async def _fetch_problem(problem_id: str) -> dict:
    """Load a problem definition from S3 if possible, otherwise from local files."""
    # key = f"{app.state.problems_prefix}{problem_id}.json"
    key = f"{app.state.problems_prefix}{problem_id}"
    if app.state.s3_session:
        logger.info(f"app.state.s3_session=True, Attempting to fetch problem {key} from AWS S3" )
        try:
            async with app.state.s3_session.client(
                "s3",
                region_name=app.state.aws_region,
                endpoint_url=app.state.problems_endpoint,
            ) as s3:
                obj = await s3.get_object(
                    Bucket=app.state.problems_bucket,
                    Key=key,
                )
                body = await obj["Body"].read()
                logger.info(f"Fetched problem {problem_id}, now parsing JSON")
                return json.loads(body)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                raise HTTPException(status_code=404, detail=f"Problem {problem_id} not found")
            # Any other error will fall back to local files
            logger.error(f"ClientError details: {e}")
        except Exception as ex:
            logger.error(f"Exception details: {ex}")

    # Fallback to local files
    logger.info(f"app.state.s3_session=False, Fetching problem {problem_id} from local files")
    path = app.state.problems_local_dir / key
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Problem {problem_id} not found")
    except Exception:
        raise HTTPException(status_code=500, detail=f"Failed to fetch the problem {problem_id}")

def _result_status(res: ExecutionResult, expected: str) -> ResultStatus:
    if res.exitCode == -1 and res.stderr:
        return ResultStatus.COMPILE_ERROR
    if res.timedOut:
        return ResultStatus.TIMEOUT
    if "SyntaxError:" in res.stderr:
        return ResultStatus.SYNTAX_ERROR
    if res.exitCode != 0:
        return ResultStatus.RUNTIME_EXCEPTION
    if res.exitCode == 0 and res.stderr == "" and res.stdout.strip() == str(expected).strip():
        return ResultStatus.SUCCESS
    if res.exitCode == 0 and res.stderr == "":
        return ResultStatus.WRONG_OUTPUT
    if "Traceback (most recent call last): " in res.stderr:
        return ResultStatus.RUNTIME_EXCEPTION
    return ResultStatus.FAILURE


def _apply_progress(data: dict, meta: dict) -> dict:
    data["total"] = meta["total"]
    hide_output = meta.get("hide_output", False)
    try:
        idx = int(data.get("index", -1))
        if 0 <= idx < len(meta["expected"]):
            exp = meta["expected"][idx]
            res = ExecutionResult(**data["result"])
            data["result"]["status"] = _result_status(res, exp).value
            if hide_output:
                data["result"].pop("stdout", None)
                data["result"].pop("stderr", None)
    except Exception:
        pass
    if hide_output:
        data["result"].pop("stdout", None)
        data["result"].pop("stderr", None)
    return data


def _prepare_final(meta: dict, results: List[ExecutionResult]) -> dict:
    hide_output = meta.get("hide_output", False)
    graded = []
    all_passed = True
    for m, exp, res in zip(meta["tc_meta"], meta["expected"], results):
        status = _result_status(res, exp)
        passed = status is ResultStatus.SUCCESS
        all_passed = all_passed and passed
        entry = {
            "id": m["id"],
            "visibility": m["visibility"],
            "passed": passed,
            "status": status.value,
            "expected": exp,
            "exitCode": res.exitCode,
            "duration": res.duration,
            "memoryUsed": res.memoryUsed,
            "timedOut": res.timedOut,
        }
        if not hide_output:
            entry["stdout"] = res.stdout
            entry["stderr"] = res.stderr
        graded.append(entry)

    final_status = graded[-1]["status"] if graded else ResultStatus.FAILURE.value
    return {
        "type": "final",
        "problemId": meta["problemId"],
        "allPassed": all_passed,
        "status": final_status,
        "results": graded,
        "total": meta["total"],
    }

def _check_sadpanda(request: Request) -> None:
    if request.cookies.get("sadpanda") != SADPANDA_VALUE:
        raise HTTPException(status_code=400, detail="Bad request")

async def progress_consumer() -> None:
    queue = app.state.progress_queue
    async with queue.iterator() as it:
        async for message in it:
            async with message.process():
                rid = message.correlation_id
                if not rid:
                    continue
                data = json.loads(message.body)
                if data.get("type") == "progress" and rid in app.state.v3_meta:
                    meta = app.state.v3_meta[rid]
                    data = _apply_progress(data, meta)
                if data.get("type") == "final" and rid in app.state.v3_meta:
                    meta = app.state.v3_meta.pop(rid)
                    results = [ExecutionResult(**r) for r in data["results"]]
                    data = _prepare_final(meta, results)

                conns = app.state.ws_connections.get(rid)
                if conns:
                    to_remove = set()
                    for ws in conns:
                        try:
                            await ws.send_json(data)
                        except Exception:
                            to_remove.add(ws)
                    conns.difference_update(to_remove)
                    if data.get("type") == "final":
                        app.state.ws_connections.pop(rid, None)


# 이 함수는 debug용으로, 프로덕션에서는 사용하지 않습니다.
# 실제로는 `/execute_v3`를 사용하여 비동기적으로 실행하고 WebSocket을 통해 결과를 받도록 하세요.
@app.post("/execute", response_model=list[ExecutionResult])
async def run_code(req: CodeRequest, request: Request):
    _check_sadpanda(request)
    try:
        payload = req.dict()
        raw_results = await app.state.rpc.call(payload)
        results = [ExecutionResult(**r) for r in raw_results]
        return results
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 이 함수는 deprecated로, 프로덕션에서는 사용하지 않습니다.
# 실제로는 `/execute_v3`를 사용 및 WebSocket을 통해 결과를 받도록 하세요.
@app.post("/execute_v2")
async def run_code_v2(req: CodeRequest, request: Request):
    _check_sadpanda(request)
    try:
        payload = req.dict()
        request_id = await app.state.rpc.send(payload)
        return {"requestId": request_id}
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.websocket("/ws/progress/{request_id}")
async def ws_progress(websocket: WebSocket, request_id: str):
    await websocket.accept()
    conns = app.state.ws_connections.setdefault(request_id, set())
    conns.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        conns.discard(websocket)
        if not conns:
            app.state.ws_connections.pop(request_id, None)


# 이 함수는 비동기적으로 문제를 실행하고 클라이언트에게 WebSocket을 통해 결과를 받도록 합니다.
@app.post("/execute_v3")
async def run_code_v3(req: CodeV3Request, request: Request):
    _check_sadpanda(request)
    try:
        problem = await _fetch_problem(req.problemId)

        if req.language.value not in problem.get("languages", []):
            raise HTTPException(status_code=400, detail="Language not allowed")

        time_limit = int(problem.get("time_limit_milliseconds", 30000))
        mem_kb = int(problem.get("memory_limit_kilobytes", 262144))
        memory_limit = mem_kb // 1024

        stdins = [tc.get("input", "") for tc in problem.get("test_cases", [])]
        expected = [tc.get("output", "") for tc in problem.get("test_cases", [])]
        tc_meta = [
            {"id": tc.get("id"), "visibility": tc.get("visibility", "public")}
            for tc in problem.get("test_cases", [])
        ]

        payload = {
            "language": req.language,
            "code": req.code,
            "stdins": stdins,
            "timeLimit": time_limit,
            "wallTimeLimit": time_limit,
            "memoryLimit": memory_limit,
            "token": req.token,
            "expected": expected,
            "earlyStop": True,
        }

        request_id = await app.state.rpc.send(payload)
        app.state.v3_meta[request_id] = {
            "expected": expected,
            "tc_meta": tc_meta,
            "problemId": req.problemId,
            "total": len(stdins),
        }

        return {"requestId": request_id}

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 새 엔드포인트: /execute_v4
# /execute_v3와 동일하나 stdout/stderr를 클라이언트에게 전달하지 않는다.
@app.post("/execute_v4")
async def run_code_v4(req: CodeV3Request):
    try:
        problem = await _fetch_problem(req.problemId)

        if req.language.value not in problem.get("languages", []):
            raise HTTPException(status_code=400, detail="Language not allowed")

        time_limit = int(problem.get("time_limit_milliseconds", 30000))
        mem_kb = int(problem.get("memory_limit_kilobytes", 262144))
        memory_limit = mem_kb // 1024

        stdins = [tc.get("input", "") for tc in problem.get("test_cases", [])]
        expected = [tc.get("output", "") for tc in problem.get("test_cases", [])]
        tc_meta = [
            {"id": tc.get("id"), "visibility": tc.get("visibility", "public")}
            for tc in problem.get("test_cases", [])
        ]

        payload = {
            "language": req.language,
            "code": req.code,
            "stdins": stdins,
            "timeLimit": time_limit,
            "wallTimeLimit": time_limit,
            "memoryLimit": memory_limit,
            "token": req.token,
            "expected": expected,
            "earlyStop": True,
        }

        request_id = await app.state.rpc.send(payload)
        app.state.v3_meta[request_id] = {
            "expected": expected,
            "tc_meta": tc_meta,
            "problemId": req.problemId,
            "total": len(stdins),
            "hide_output": True,
        }

        return {"requestId": request_id}

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

# 새 엔드포인트: /execute_v4_public
# /execute_v4와 동일하나 공개 테스트케이스만 실행한다.
@app.post("/execute_v4_public")
async def run_code_v4_public(req: CodeV3Request):
    try:
        problem = await _fetch_problem(req.problemId)

        if req.language.value not in problem.get("languages", []):
            raise HTTPException(status_code=400, detail="Language not allowed")

        time_limit = int(problem.get("time_limit_milliseconds", 30000))
        mem_kb = int(problem.get("memory_limit_kilobytes", 262144))
        memory_limit = mem_kb // 1024

        cases = [       # 필터링된 공개 테스트케이스만 가져오기
            tc for tc in problem.get("test_cases", [])
            if tc.get("visibility", "public") == "public"
        ]
        stdins = [tc.get("input", "") for tc in cases]
        expected = [tc.get("output", "") for tc in cases]
        tc_meta = [
            {"id": tc.get("id"), "visibility": tc.get("visibility", "public")}
            for tc in cases
        ]

        payload = {
            "language": req.language,
            "code": req.code,
            "stdins": stdins,
            "timeLimit": time_limit,
            "wallTimeLimit": time_limit,
            "memoryLimit": memory_limit,
            "token": req.token,
            "expected": expected,
            "earlyStop": True,
        }

        request_id = await app.state.rpc.send(payload)
        app.state.v3_meta[request_id] = {
            "expected": expected,
            "tc_meta": tc_meta,
            "problemId": req.problemId,
            "total": len(stdins),
            "hide_output": True,
        }

        return {"requestId": request_id}

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
