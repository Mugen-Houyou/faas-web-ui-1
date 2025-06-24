# FaaS Web UI

AWS Lambda 기반 온라인 컴파일러를 위한 간단한 웹 인터페이스입니다.

- 현재는 C와 C++만 지원하며 추후 Java와 Python이 추가될 예정입니다.
- API Gateway를 통해 노출된 RESTful API를 사용합니다.
- 정적 파일은 `frontend` 디렉터리에 위치합니다.

## 요구 사항
추가로 실행해야 할 백엔드는 없습니다. `frontend/`의 정적 파일을 웹 브라우저로 열어 사용하면 됩니다.

## 프론트엔드 실행
`frontend/index.html`을 브라우저로 직접 열거나 간단한 HTTP 서버를 이용해 제공할 수 있습니다.

```bash
cd frontend
python -m http.server 8080
```
이후 `http://localhost:8080`에 접속합니다.

## 사용법
1. AWS API Gateway 엔드포인트(예: `https://example.execute-api.amazonaws.com/prod/compile`)를 입력합니다.
2. 언어(C 또는 C++)를 선택합니다.
3. 코드를 입력하고 필요한 경우 표준 입력을 작성합니다.
4. **실행** 버튼을 누르면 결과와 실행 시간을 확인할 수 있습니다.

## 라이선스
이 저장소에는 별도의 라이선스 파일이 포함되어 있지 않습니다.
