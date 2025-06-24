import subprocess, tempfile, os, time
from enum import Enum
from pydantic import BaseModel

class SupportedLanguage(str, Enum):
    c = "c"
    cpp = "cpp"
    java = "java"
    python = "python"

class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    exec_time: float

def execute_code(lang: SupportedLanguage, code: str, timeout: float) -> ExecutionResult:
    with tempfile.TemporaryDirectory() as td:
        if lang == SupportedLanguage.python:
            src = os.path.join(td, "main.py")
            with open(src, "w") as f: f.write(code)
            cmd = ["python3", src]

        elif lang == SupportedLanguage.c:
            src = os.path.join(td, "main.c")
            exe = os.path.join(td, "main.out")
            with open(src, "w") as f: f.write(code)
            subprocess.run(["gcc", src, "-o", exe], check=True, capture_output=True)
            cmd = [exe]

        elif lang == SupportedLanguage.cpp:
            src = os.path.join(td, "main.cpp")
            exe = os.path.join(td, "main.out")
            with open(src, "w") as f: f.write(code)
            subprocess.run(["g++", src, "-o", exe], check=True, capture_output=True)
            cmd = [exe]

        elif lang == SupportedLanguage.java:
            src = os.path.join(td, "Main.java")
            with open(src, "w") as f: f.write(code)
            subprocess.run(["javac", src], check=True, capture_output=True)
            cmd = ["java", "-cp", td, "Main"]

        else:
            raise ValueError(f"Unsupported language: {lang}")

        start = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = time.time() - start

        return ExecutionResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exec_time=elapsed
        )
