"""Simple code execution API used by the frontend.

The backend compiles supported languages (Python, C, C++, and Java) and runs
the resulting program locally. Unsupported languages raise
``NotImplementedError`` which results in a ``501 Not Implemented`` response.
Run with ``uvicorn app.main:app``.
"""

import os
import json
import asyncio
from typing import List, Dict, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

from .executor import SupportedLanguage, ExecutionResult
from .rabbitmq_rpc import RpcClient, get_rpc_client


# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=False)

app = FastAPI()
app.state.ws_connections: Dict[str, Set[WebSocket]] = {}
app.state.progress_queue = None
app.state.v3_meta: Dict[str, dict] = {}

# CORS 설정
# 기본 오리진 목록을 환경 변수로 확장할 수 있다.
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8000",
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

class CodeRequest(BaseModel):
    language: SupportedLanguage
    code: str
    stdins: List[str] = []
    timeLimit: int = 30000
    memoryLimit: int = 256
    token: str | None = None


@app.on_event("startup")
async def startup() -> None:
    print("Starting up RPC client... ", end="")
    url = os.getenv("RABBITMQ_URL", "asdf")
    print(f"Connecting to RabbitMQ at {url}")
    app.state.rpc: RpcClient = await get_rpc_client()
    app.state.progress_queue = await app.state.rpc.channel.declare_queue("progress", durable=True)
    asyncio.create_task(progress_consumer())


@app.on_event("shutdown")
async def shutdown() -> None:
    await app.state.rpc.close()

@app.post("/execute", response_model=list[ExecutionResult])
async def run_code(req: CodeRequest):
    try:
        payload = req.dict()
        raw_results = await app.state.rpc.call(payload)
        results = [ExecutionResult(**r) for r in raw_results]
        return results
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/execute_v2")
async def run_code_v2(req: CodeRequest):
    try:
        payload = req.dict()
        request_id = await app.state.rpc.send(payload)
        return {"requestId": request_id}
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def progress_consumer() -> None:
    queue = app.state.progress_queue
    async with queue.iterator() as it:
        async for message in it:
            async with message.process():
                rid = message.correlation_id
                if not rid:
                    continue
                data = json.loads(message.body)
                if data.get("type") == "final" and rid in app.state.v3_meta:
                    meta = app.state.v3_meta.pop(rid)
                    results = [ExecutionResult(**r) for r in data["results"]]
                    graded = []
                    all_passed = True
                    for m, exp, res in zip(meta["tc_meta"], meta["expected"], results):
                        passed = (
                            res.exitCode == 0
                            and not res.timedOut
                            and res.stderr == ""
                            and res.stdout.strip() == str(exp).strip()
                        )
                        all_passed = all_passed and passed
                        graded.append({
                            "id": m["id"],
                            "visibility": m["visibility"],
                            "passed": passed,
                            "expected": exp,
                            "stdout": res.stdout,
                            "stderr": res.stderr,
                            "exitCode": res.exitCode,
                            "duration": res.duration,
                            "memoryUsed": res.memoryUsed,
                            "timedOut": res.timedOut,
                        })
                    data = {
                        "type": "final",
                        "problemId": meta["problemId"],
                        "allPassed": all_passed,
                        "results": graded,
                    }

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


class CodeV3Request(BaseModel):
    language: SupportedLanguage
    code: str
    problemId: str
    token: str | None = None


@app.post("/execute_v3")
async def run_code_v3(req: CodeV3Request):
    try:
        base = Path(__file__).resolve().parents[1] / "static" / "codeground-problems"
        path = base / f"{req.problemId}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Problem not found")
        with open(path, "r") as f:
            problem = json.load(f)

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
            "memoryLimit": memory_limit,
            "token": req.token,
        }

        request_id = await app.state.rpc.send(payload)
        app.state.v3_meta[request_id] = {
            "expected": expected,
            "tc_meta": tc_meta,
            "problemId": req.problemId,
        }

        return {"requestId": request_id}

    except HTTPException:
        raise
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
