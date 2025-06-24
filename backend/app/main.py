"""
## 중요! 

- Python 3.11의 venv에서 실행해야 함.


## 실행 방법:

```
# 1. 시스템 패키지 최신화 및 Python 3.11 설치
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 2. 프로젝트 디렉터리로 이동
cd code-runner/backend # 즉, backend 폴더로 와서 실행해야 함.

# 3. Python 3.11 venv 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate

# 4. 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 5. 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from executor import execute_code, SupportedLanguage

app = FastAPI()

class CodeRequest(BaseModel):
    language: SupportedLanguage
    code: str
    timeout: float = 5.0

class CodeResponse(BaseModel):
    stdout: str
    stderr: str
    exec_time: float  # seconds

@app.post("/execute", response_model=CodeResponse)
async def run_code(req: CodeRequest):
    try:
        result = execute_code(req.language, req.code, req.timeout)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
