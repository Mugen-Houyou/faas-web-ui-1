"""Simple code execution API used by the frontend.

The backend compiles supported languages (Python, C, C++, and Java) and runs
the resulting program locally. Unsupported languages raise
``NotImplementedError`` which results in a ``501 Not Implemented`` response.
Run with ``uvicorn app.main:app``.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

from .executor import SupportedLanguage, ExecutionResult
from .rabbitmq_rpc import RpcClient, get_rpc_client


# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=False)

app = FastAPI()

# CORS 설정 (필요에 따라 origins 수정)
# allow requests from any origin (use env vars to restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost",
    "http://localhost:3000", # 배포 시 프론트엔드 주소 - maybe?
    "http://localhost:8080", # 배포 시 프론트엔드 주소 - maybe?
    "http://localhost:8000", ],
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
