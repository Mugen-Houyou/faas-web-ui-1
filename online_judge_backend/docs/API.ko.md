# Online Judge Backend REST API 명세서

이 문서는 온라인 저지 백엔드에서 제공하는 HTTP API를 설명합니다.

## POST `/execute`

주어진 코드를 여러 입력으로 실행하여 결과 배열을 반환합니다. 백엔드는
RabbitMQ를 통해 작업을 큐에 넣고 별도의 워커 프로세스가 이를 처리한 뒤
결과를 응답으로 전달합니다. 워커는 `python -m online_judge_backend.app.worker`
명령으로 실행할 수 있습니다.

### 요청
- **Method**: `POST`
- **URL**: `/execute`
- **Body** (`application/json`)

```json
{
  "language": "python",
  "code": "print(input())",
  "stdins": ["a", "b"],
  "timeLimit": 30000,
  "memoryLimit": 256,
  "token": null
}
```
- `language`: `c`, `cpp`, `java`, `python` 중 하나
- `code`: 실행할 소스 코드 문자열
- `stdins`: 표준 입력 문자열 배열 (기본값 `[]`). 각 요소는 한 번의 실행에서 사용할 전체 입력이며 여러 줄을 포함할 수 있습니다. 프론트엔드에서는 빈 줄을 기준으로 새 실행을 구분합니다.
- `timeLimit`: 실행 시간 제한(ms)
- `memoryLimit`: 메모리 제한(MB)
- `token`: 인증 토큰(선택)
- 입력이 부족한 경우 백엔드는 STDIN 스트림을 닫아 프로그램이 즉시 EOF를 받도록 합니다. 이때 프로그램이 종료되지 않으면 `timeLimit`이 적용되어 강제 종료될 수 있습니다.

### 응답
성공 시 `200 OK`와 함께 다음 형식의 JSON 배열을 반환합니다.

```json
[
  {
    "requestId": "UUID",
    "stdout": "output",
    "stderr": "",
    "exitCode": 0,
    "duration": 120,
    "memoryUsed": 12288,
    "timedOut": false
  }
]
```
- `duration`: 실행 시간(ms)
- `memoryUsed`: 사용한 메모리(KB)
- 지원하지 않는 언어일 경우 `501 Not Implemented`
- 잘못된 요청 등 기타 오류 시 `400 Bad Request`

### 예시
```bash
curl -X POST http://localhost:8000/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "language": "python",
    "code": "print(input())",
    "stdins": ["first\nline", "second"]
  }'
```
