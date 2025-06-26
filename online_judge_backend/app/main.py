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
