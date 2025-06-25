"""Backend API that proxies code execution requests to a remote FaaS service.

Set ``FAAS_BASE_URL`` and ``FAAS_TOKEN`` environment variables if the defaults
do not match your environment. Run with ``uvicorn app.main:app``.
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
