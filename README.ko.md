# FaaS Web UI

FaaS 기반 REST API와 통신하는 간단한 HTML/JavaScript 프론트엔드입니다.

- Python, C, C++, Java 코드 실행 지원
- 원격 API의 `POST /execute` 엔드포인트 호출
- 정적 파일은 `frontend` 디렉터리에 위치

## 요구 사항
프론트엔드를 사용하기 위해서는 웹 브라우저만 있으면 됩니다. 실행 서버는 외부에서 제공됩니다.


## 프론트엔드 실행
`frontend/index.html`을 브라우저로 직접 열거나 간단한 HTTP 서버를 이용해 제공할 수 있습니다.

```bash
cd frontend
python -m http.server 8080
```
이후 `http://localhost:8080`에 접속하여 사용합니다.

## 사용법
JWT 토큰을 입력하고 언어와 코드를 작성한 후 필요하면 STDIN도 입력합니다. **실행** 버튼을 누르면 원격 FaaS API가 호출되며, 실행이 끝나면 결과가 표시됩니다.

## 라이선스
이 저장소에는 별도의 라이선스 파일이 포함되어 있지 않습니다.
