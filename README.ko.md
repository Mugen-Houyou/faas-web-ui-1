# FaaS Web UI

간단한 `/execute` API를 통해 코드를 실행할 수 있는 인터페이스입니다.

- Python, Java, C, C++ 코드를 실행
- 지원하지 않는 언어는 **501 Not Implemented** 응답
- 백엔드 (`backend` 폴더)는 코드를 컴파일한 뒤 실행, 결과 반환
- 프론트엔드 (`frontend` 폴더)는 백엔드를 사용할 수 있는 데모 웹 UI

## 요구 사항
- 프론트엔드를 사용하려면 웹 브라우저만 있으면 됩니다.
- 백엔드를 사용하려면 Python 3.11이 필요하며 후술할 C, C++ 컴파일러, JDK 등이 필요합니다.

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
3. C/C++ 컴파일러 설치(Ubuntu 22.04 LTS 기준):
   ```bash
   sudo apt update
   sudo apt install build-essential
   ```
4. OpenJDK 설치(Ubuntu 22.04 LTS 기준):
   ```bash
   sudo apt install openjdk-17-jdk
   ```
5. 서버를 실행합니다.
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

프론트엔드에는 API 주소를 입력할 수 있는 필드가 있습니다. 기본값은 `http://localhost:8000`으로 FastAPI 백엔드를 가리킵니다. 다른 서버를 지정하는 경우 CORS 설정이 되어 있어야 합니다.

## 사용법
JWT 토큰을 입력한 뒤 언어와 코드를 작성하고 STDIN이 있다면 함께 입력합니다. **실행!** 버튼을 누르면 백엔드가 코드를 컴파일하고 실행해 결과를 돌려줍니다.

## 라이선스
이 저장소에는 별도의 라이선스 파일이 포함되어 있지 않습니다.
