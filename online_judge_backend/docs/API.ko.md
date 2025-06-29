# Online Judge Backend REST API 명세서

이 문서는 온라인 저지 백엔드에서 제공하는 HTTP API를 설명합니다. 기본적인 동기식
`/execute` 엔드포인트 외에도 RabbitMQ 기반의 비동기식 API(`/execute_v2` +
WebSocket)를 제공합니다. `frontend/index_v2.html` 페이지가 이 비동기 방식을 사용한
예시입니다.

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

## POST `/execute_v2`

`/execute`와 동일한 요청 본문을 사용하지만 비동기로 동작합니다. 요청을 보내면 즉시
`requestId`를 반환하며, 진행 상황과 최종 결과는 WebSocket을 통해 전달됩니다.

### 요청
- **Method**: `POST`
- **URL**: `/execute_v2`
- **Body**: `/execute`와 동일

### 응답
성공 시 다음 형식의 JSON을 반환합니다.

```json
{
  "requestId": "UUID"
}
```

응답으로 받은 `requestId`는 이후 진행 상황을 구독하기 위한 식별자입니다. 기본 흐름은 다음과 같습니다.
1. 위 API에 코드를 POST하여 `requestId`를 얻습니다.
2. `ws://<서버주소>/ws/progress/{requestId}` WebSocket에 연결합니다.
3. 실행이 끝날 때까지 서버가 보내는 `progress` / `final` 메시지를 수신합니다.
4. `final` 메시지를 받은 후 WebSocket을 닫습니다.

이 과정을 구현한 예시는 `frontend/index_v2.html`과 `frontend/app_v2.js`에서 확인할 수 있습니다.

## WebSocket `/ws/progress/{request_id}`

`/execute_v2` 요청 후 반환된 `requestId`를 사용해 연결합니다. 서버는 JSON 메시지를
스트리밍하며 형식은 다음과 같습니다.

### 진행 메시지 예시
```json
{
  "type": "progress",
  "index": 0,
  "result": {
    "stdout": "output",
    "stderr": "",
    "exitCode": 0,
    "duration": 120,
    "memoryUsed": 12288,
    "timedOut": false
  }
}
```

### 최종 메시지 예시
```json
{
  "type": "final",
  "results": [
    {
      "stdout": "output",
      "stderr": "",
      "exitCode": 0,
      "duration": 120,
      "memoryUsed": 12288,
      "timedOut": false
    }
  ]
}
```

`type`이 `final`인 메시지를 받은 뒤에는 클라이언트가 WebSocket 연결을 종료하면 됩니다.
