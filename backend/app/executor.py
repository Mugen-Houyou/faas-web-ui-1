import asyncio
import os
import time
import uuid
from enum import Enum
from typing import Optional

from pathlib import Path
from tempfile import TemporaryDirectory
from dotenv import load_dotenv

# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

from pydantic import BaseModel


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
    """Execute Python code locally. Other languages are not implemented."""

    if lang is not SupportedLanguage.python:
        raise NotImplementedError(f"Language '{lang}' is not supported yet")

    # Save the code to a temporary file and execute it using the system Python
    with TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "main.py"
        file_path.write_text(code)

        start = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            "python3",
            str(file_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        timed_out = False
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(stdin.encode()), timeout=time_limit / 1000
            )
        except asyncio.TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            timed_out = True

        duration = time.perf_counter() - start
        exit_code = process.returncode if process.returncode is not None else -1

        return ExecutionResult(
            requestId=str(uuid.uuid4()),
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            exitCode=exit_code,
            duration=duration,
            memoryUsed=0,
            timedOut=timed_out,
        )
