# FaaS Web UI

원격 Function‑as‑a‑Service(FaaS) 실행 API와 통신하는 간단한 코드 실행 인터페이스입니다.

- Python, C, C++, Java 코드 실행 지원
- API의 `POST /execute` 엔드포인트와 통신
- 요청을 중계하는 FastAPI 백엔드(`backend`)를 선택적으로 사용 가능
- 정적 파일은 `frontend` 디렉터리에 위치

## 요구 사항
- 프론트엔드를 사용하려면 웹 브라우저만 있으면 됩니다.
- 선택적 백엔드를 사용하려면 Python 3.11이 필요합니다.

## 백엔드 설정(선택 사항)
1. 가상 환경을 생성하고 활성화합니다.
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   ```
2. 의존성을 설치합니다.
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. 환경 변수를 필요에 따라 지정합니다.
   - `FAAS_BASE_URL` (기본값 `https://api.example.com/api/v1`)
   - `FAAS_TOKEN` (인증이 필요한 경우)
4. 서버를 실행합니다.
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## 프론트엔드 실행
`frontend/index.html`을 브라우저로 직접 열거나 간단한 HTTP 서버를 이용해 제공할 수 있습니다.

```bash
cd frontend
python -m http.server 8080
```
이후 `http://localhost:8080`에 접속합니다.

## 사용법
JWT 토큰이 필요한 경우 입력한 뒤 언어와 코드를 작성하고 STDIN이 있다면 함께 입력합니다. **실행** 버튼을 누르면 FaaS API가 호출되고, 종료 시까지 자동으로 폴링하여 출력, 종료 코드, 실행 시간, 메모리 사용량을 보여줍니다.

## 라이선스
이 저장소에는 별도의 라이선스 파일이 포함되어 있지 않습니다.
