# FaaS Web UI

FastAPI 백엔드와 간단한 HTML/JavaScript 프론트엔드로 구성된 코드 실행 웹 인터페이스입니다.

- Python, C, C++, Java 코드 실행 지원
- FastAPI 기반 REST API 제공
- 정적 파일은 `frontend` 디렉터리에 위치

## 요구 사항
- Python 3.11
- C/C++/Java 컴파일러(`gcc`, `g++`, `javac` 등)

## 백엔드 실행 방법
1. `backend` 디렉터리에서 가상 환경을 생성하고 활성화합니다.
   ```bash
   cd backend
   python3.11 -m venv venv
   source venv/bin/activate
   ```
2. 의존성을 설치합니다.
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. 서버를 실행합니다.
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 프론트엔드 실행
`frontend/index.html`을 브라우저로 직접 열거나 간단한 HTTP 서버를 이용해 제공할 수 있습니다.

```bash
cd frontend
python -m http.server 8080
```
이후 `http://localhost:8080`에 접속하여 사용합니다.

## 사용법
백엔드와 프론트엔드가 모두 실행 중이면 원하는 언어를 선택하고 코드를 입력한 뒤 **실행** 버튼을 누르면 결과와 실행 시간을 확인할 수 있습니다.

## 라이선스
이 저장소에는 별도의 라이선스 파일이 포함되어 있지 않습니다.
