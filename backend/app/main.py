"""Simple code execution API used by the frontend.

The backend compiles supported languages (Python, C, C++, and Java) and runs
the resulting program locally. Unsupported languages raise
``NotImplementedError`` which results in a ``501 Not Implemented`` response.
Run with ``uvicorn app.main:app``.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .executor import execute_code, SupportedLanguage, ExecutionResult
import os

app = FastAPI()

# CORS 설정
# 기본 오리진 목록에 환경 변수를 통해 추가 오리진을 지정할 수 있다.
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
    stdin: str = ""
    timeLimit: int = 30000
    memoryLimit: int = 256
    token: str | None = None

@app.post("/execute", response_model=ExecutionResult)
async def run_code(req: CodeRequest):
    try:
        result = await execute_code(
            lang=req.language,
            code=req.code,
            stdin=req.stdin,
            time_limit=req.timeLimit,
            memory_limit=req.memoryLimit,
            token=req.token,
        )
        return result
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
