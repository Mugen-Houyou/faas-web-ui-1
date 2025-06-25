import os
import asyncio
from enum import Enum
from typing import Optional

from pathlib import Path
from dotenv import load_dotenv

# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

import httpx
from pydantic import BaseModel

BASE_URL = os.environ.get("FAAS_BASE_URL", "https://api.example.com/api/v1")
DEFAULT_TOKEN = os.environ.get("FAAS_TOKEN")


class SupportedLanguage(str, Enum):
    c = "c"
    cpp = "cpp"
    java = "java"
    python = "python"


class ExecutionResult(BaseModel):
    requestId: str
    stdout: str
    stderr: str
    exitCode: int
    duration: float
    memoryUsed: int
    timedOut: bool


async def execute_code(
    lang: SupportedLanguage,
    code: str,
    stdin: str = "",
    time_limit: int = 30000,
    memory_limit: int = 256,
    token: Optional[str] = None,
) -> ExecutionResult:
    headers = {"Content-Type": "application/json"}
    token = token or DEFAULT_TOKEN
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "language": lang.value,
        "code": code,
        "stdin": stdin,
        "timeLimit": time_limit,
        "memoryLimit": memory_limit,
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(f"{BASE_URL}/execute", json=payload, headers=headers)
        data = res.json()

        if res.status_code == 202:
            req_id = data["requestId"]
            while True:
                await asyncio.sleep(1)
                r = await client.get(f"{BASE_URL}/execute/{req_id}", headers=headers)
                data = r.json()
                if r.status_code == 202:
                    continue
                res = r
                break

        if res.status_code != 200:
            raise RuntimeError(data.get("error") or "Execution failed")

    return ExecutionResult(**data)
