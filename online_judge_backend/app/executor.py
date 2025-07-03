import asyncio
import os
import time
import uuid
from enum import Enum
from typing import Optional, Callable, Awaitable

from pathlib import Path
from tempfile import NamedTemporaryFile
import tempfile
import shutil
import re
from dotenv import load_dotenv
import psutil

# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=False)

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
    duration: float  # milliseconds
    memoryUsed: int  # kilobytes
    timedOut: bool


async def compile_code(
    lang: SupportedLanguage, code: str, token: Optional[str] = None
) -> Path:
    """Compile code and return a path to the executable or script."""

    if lang is SupportedLanguage.python:
        tmp = NamedTemporaryFile("w", suffix=".py", delete=False)
        tmp.write(code)
        tmp.close()
        return Path(tmp.name)

    if lang in (SupportedLanguage.c, SupportedLanguage.cpp):
        suffix = ".c" if lang is SupportedLanguage.c else ".cpp"
        src = NamedTemporaryFile("w", suffix=suffix, delete=False)
        src.write(code)
        src.close()
        exe_path = Path(src.name).with_suffix("")
        compiler = "gcc" if lang is SupportedLanguage.c else "g++"
        process = await asyncio.create_subprocess_exec(
            compiler,
            src.name,
            "-O2",
            "-o",
            str(exe_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            os.remove(src.name)
            raise RuntimeError(stderr.decode() or "Compilation failed")
        os.remove(src.name)
        return exe_path

    if lang is SupportedLanguage.java:
        match = re.search(r"public\s+class\s+(\w+)", code)
        class_name = match.group(1) if match else "Main"
        tmpdir = Path(tempfile.mkdtemp())
        src_path = tmpdir / f"{class_name}.java"
        with open(src_path, "w") as f:
            f.write(code)
        process = await asyncio.create_subprocess_exec(
            "javac",
            str(src_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise RuntimeError(stderr.decode() or "Compilation failed")
        return tmpdir / f"{class_name}.class"

    raise NotImplementedError(f"Compilation for '{lang}' is not supported yet")


async def run_code(
    lang: SupportedLanguage,
    file_path: Path,
    stdin: str,
    time_limit: int,
    memory_limit: int,
) -> ExecutionResult:
    """Run previously compiled code and return the execution result."""

    if lang is SupportedLanguage.python:
        cmd = ["python3", str(file_path)]
    elif lang in (SupportedLanguage.c, SupportedLanguage.cpp):
        cmd = [str(file_path)]
    elif lang is SupportedLanguage.java:
        cmd = [
            "java",
            "-cp",
            str(file_path.parent),
            file_path.stem,
        ]
    else:
        raise NotImplementedError(f"Execution for '{lang}' is not supported yet")

    start = time.perf_counter()
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def _track_memory_usage(pid: int) -> int:
        """Return peak RSS in bytes for the given process."""
        peak = 0
        try:
            proc = psutil.Process(pid)
        except psutil.Error:
            return peak
        while True:
            try:
                mem = proc.memory_info().rss
                peak = max(peak, mem)
                if not proc.is_running():
                    break
            except psutil.NoSuchProcess:
                break
            await asyncio.sleep(0.05)
        return peak

    mem_task = asyncio.create_task(_track_memory_usage(process.pid))

    # ``process.communicate`` sends the entire input and closes stdin. If the
    # executed program requests more data than provided, it receives EOF instead
    # of blocking indefinitely.

    timed_out = False
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(stdin.encode()), timeout=time_limit / 1000
        )
    except asyncio.TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
        timed_out = True

    duration = (time.perf_counter() - start) * 1000  # ms
    exit_code = process.returncode if process.returncode is not None else -1
    peak_rss = await mem_task

    return ExecutionResult(
        requestId=str(uuid.uuid4()),
        stdout=stdout.decode(),
        stderr=stderr.decode(),
        exitCode=exit_code,
        duration=duration,
        memoryUsed=int(peak_rss / 1024),
        timedOut=timed_out,
    )


async def execute_code(
    lang: SupportedLanguage,
    code: str,
    stdin: str = "",
    time_limit: int = 30000,
    memory_limit: int = 256,
    token: Optional[str] = None,
) -> ExecutionResult:
    """High-level helper that compiles then executes code."""
    try:
        file_path = await compile_code(lang, code, token)
    except NotImplementedError:
        raise
    except Exception as e:
        return ExecutionResult(
            requestId=str(uuid.uuid4()),
            stdout="",
            stderr=str(e),
            exitCode=-1,
            duration=0.0,
            memoryUsed=0,
            timedOut=False,
        )

    try:
        result = await run_code(lang, file_path, stdin, time_limit, memory_limit)
    finally:
        try:
            if lang is SupportedLanguage.java:
                shutil.rmtree(file_path.parent, ignore_errors=True)
            else:
                os.remove(file_path)
        except OSError:
            pass

    return result


async def execute_code_multiple(
    lang: SupportedLanguage,
    code: str,
    stdins: list[str],
    time_limit: int = 30000,
    memory_limit: int = 256,
    token: Optional[str] = None,
    *,
    expected: Optional[list[str]] = None,
    early_stop: bool = False,
    progress_cb: Optional[Callable[[ExecutionResult, int], Awaitable[None]]] = None,
    wall_time_limit: int | None = None,
) -> list[ExecutionResult]:
    """Compile once and run the code for each stdin in ``stdins``.

    If ``early_stop`` is True and ``expected`` is provided, execution stops
    upon the first failed test case.
    """
    try:
        file_path = await compile_code(lang, code, token)
    except NotImplementedError:
        raise
    except Exception as e:
        err = ExecutionResult(
            requestId=str(uuid.uuid4()),
            stdout="",
            stderr=str(e),
            exitCode=-1,
            duration=0.0,
            memoryUsed=0,
            timedOut=False,
        )
        return [err for _ in (stdins or [None])]

    results: list[ExecutionResult] = []
    start = time.perf_counter()
    try:
        for idx, data in enumerate(stdins):
            if wall_time_limit is not None:
                elapsed = (time.perf_counter() - start) * 1000
                remaining = wall_time_limit - elapsed
                if remaining <= 0:
                    res = ExecutionResult(
                        requestId=str(uuid.uuid4()),
                        stdout="",
                        stderr="",
                        exitCode=-9,
                        duration=elapsed,
                        memoryUsed=0,
                        timedOut=True,
                    )
                    results.append(res)
                    if progress_cb:
                        await progress_cb(res, idx)
                    break
                case_limit = min(time_limit, int(remaining))
            else:
                case_limit = time_limit

            res = await run_code(lang, file_path, data, case_limit, memory_limit)
            results.append(res)
            if progress_cb:
                await progress_cb(res, idx)
            if early_stop and expected and idx < len(expected):
                passed = (
                    res.exitCode == 0
                    and not res.timedOut
                    and res.stderr == ""
                    and res.stdout.strip() == str(expected[idx]).strip()
                )
                if not passed:
                    break
            if wall_time_limit is not None:
                elapsed = (time.perf_counter() - start) * 1000
                if elapsed > wall_time_limit:
                    break
    finally:
        try:
            if lang is SupportedLanguage.java:
                shutil.rmtree(file_path.parent, ignore_errors=True)
            else:
                os.remove(file_path)
        except OSError:
            pass

    return results
