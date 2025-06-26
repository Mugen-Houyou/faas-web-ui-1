# Online Judge Backend REST API 명세서

이 문서는 온라인 저지 백엔드에서 제공하는 HTTP API를 설명합니다.

## POST `/execute`

주어진 코드를 여러 입력으로 실행하여 결과 배열을 반환합니다.

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

### 응답
성공 시 `200 OK`와 함께 다음 형식의 JSON 배열을 반환합니다.

```json
[
  {
    "requestId": "UUID",
    "stdout": "output",
    "stderr": "",
    "exitCode": 0,
    "duration": 0.12,
    "memoryUsed": 12,
    "timedOut": false
  }
]
```
- `duration`: 실행 시간(초)
- `memoryUsed`: 사용한 메모리(MB)
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
