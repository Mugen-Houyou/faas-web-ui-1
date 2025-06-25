"""Backend API that proxies code execution requests to a remote FaaS service.

Set ``FAAS_BASE_URL`` and ``FAAS_TOKEN`` environment variables if the defaults
do not match your environment. Run with ``uvicorn app.main:app``.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .executor import execute_code, SupportedLanguage, ExecutionResult

app = FastAPI()

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
