# Online Judge Backend REST API 명세서

이 문서는 온라인 저지 백엔드에서 제공하는 HTTP API를 설명합니다. 기본적인 동기식
`/execute` 엔드포인트 외에도 v2 및 v3은 RabbitMQ 기반의 비동기식 API(`/execute_v2` + WebSocket 또는 `/execute_v3` + WebSocket)를 제공합니다. `frontend/index_v2.html` 및 `frontend/index_v3.html`가 이 비동기 방식을 사용한 데모입니다.

## POST `/execute`

동기 방식. 주어진 코드를 여러 입력으로 실행하여 결과 배열을 반환합니다. 

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
curl -X POST http://localhost:18651/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "language": "python",
    "code": "print(input())",
    "stdins": ["first\nline", "second"]
  }'
```

## POST `/execute_v2`

`/execute`와 동일한 요청 본문을 사용하지만 비동기로 동작합니다. 요청을 보내면 즉시 `requestId`를 반환하며, 추후 진행 상황과 최종 결과는 WebSocket을 통해 전달됩니다. 구체적인 WebSocket 스펙에 대해서는 아래를 참조하세요.

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

응답으로 받은 `requestId`는 이후 진행 상황을 구독하기 위한 식별자입니다. 구체적인 WebSocket 스펙에 대해서는 아래를 참조하세요. 기본 흐름은 다음과 같습니다.
1. 위 API에 코드를 POST하여 `requestId`를 얻습니다.
2. `ws://<서버주소>/ws/progress/{requestId}` WebSocket에 연결합니다.
3. 실행이 끝날 때까지 서버가 보내는 `progress` / `final` 메시지를 수신합니다.
4. `final` 메시지를 받은 후 WebSocket을 닫습니다.

이 과정을 구현한 예시는 `frontend/index_v2.html`과 `frontend/app_v2.js`에서 확인할 수 있습니다.

## POST `/execute_v3`

실제 백준, 프로그래머스, LeetCode 등과 같이 지정된 문제에 대해 코드를 채점합니다. 문제 정보는 기본적으로 S3 버킷에서 읽어오며, 환경 변수가 비어 있거나 버킷에 접속할 수 없는 경우 `online_judge_backend/static` 폴더의 파일을 사용합니다. 사용되는 버킷과 경로는 `.env` 파일에서 설정합니다. 구체적인 WebSocket 스펙에 대해서는 아래를 참조하세요.

### 요청
- **Method**: `POST`
- **URL**: `/execute_v3`
- **Body** (`application/json`)

```json
{
  "language": "python",
  "code": "print(input())",
  "problemId": "prob-001",
  "token": null
}
```
- `problemId`: 채점에 사용할 문제 ID(예: `prob-001`)
- 다른 필드는 `/execute`와 동일하지만 `stdins`, `timeLimit`, `memoryLimit`는 무시되고 문제의 테스트 케이스가 사용됩니다
- 문제 파일의 `time_limit_milliseconds` 값은 모든 테스트 케이스를 실행하는 데 허용되는 총 시간입니다. 초과하면 남은 케이스는 실행하지 않고 `timeout` 상태가 반환됩니다.

### 응답
채점은 비동기적으로 진행되며 HTTP 응답에는 `requestId`만 포함됩니다. 진행 상황과 최종 결과는 WebSocket을 통해 전송됩니다. 구체적인 WebSocket 스펙에 대해서는 아래를 참조하세요. 테스트 케이스가 하나라도 실패하면 남은 케이스는 실행하지 않고 즉시 최종 결과를 반환합니다.

```json
{
  "requestId": "UUID"
}
```

`requestId`는 `/ws/progress/{requestId}` WebSocket에 연결할 때 사용합니다. 서버는 각 테스트 케이스 결과를 순차적으로 전송하며 마지막 메시지에서 `type`이 `final`이면 채점이 완료된 것입니다.

- `passed`가 `true`이면 해당 테스트 케이스를 통과한 것입니다.
- `status`는 `success`, `compile_error`, `wrong_output`, `timeout`, `failure`
  중 하나로 채점 결과를 세분화한 값입니다. `success`일 때만 `passed`가 `true`입니다.
- `allPassed`가 `true`이면 모든 테스트 케이스를 통과했음을 의미합니다.
- `/execute_v3`의 경우 각 `progress` 메시지에서도 `result.status`가 포함됩니다.

## WebSocket `/ws/progress/{request_id}`

채점 현황을 클라이언트가 실시간으로 관찰할 수 있도록 만든 WebSocket 엔드포인트입니다. `/execute_v2` 및 `/execute_v3` 요청 후 반환된 `requestId`를 사용해 연결합니다. 서버는 JSON 메시지를 스트리밍합니다.

JSON 메시지 스트림 형식은 `/execute_v2`를 보냈을 때와 `/execute_v3`을 보냈을 때가 살짝 다릅니다. 구체적으로는 아래와 같습니다.

### 진행 메시지 예시 (`/execute_v2`)
```json
{
  "type": "progress",
  "index": 0,
  "result": {
    "requestId":"c4b50694-c15c-4ce7-ab76-5e3754eebeb7",
    "stdout": "output goes here\n",
    "stderr": "error goes here\n",
    "exitCode": 0,
    "duration": 120,
    "memoryUsed": 12288,
    "timedOut": false
  }
}
```

### 진행 메시지 예시 (`/execute_v3`)
`"total": 8`은 전체 테스트 케이스의 개수입니다. 이를 통해 클라이언트에게 채점이 얼마나 진행되었는지를 알려줄 수 있습니다 (예시: 채점 중 (75%)).
```json
{
  "type": "progress",
  "index": 0,
  "result": {
    "requestId":"c4b50694-c15c-4ce7-ab76-5e3754eebeb7",
    "stdout": "output goes here\n",
    "stderr": "error goes here\n",
    "exitCode": 0,
    "duration": 120,
    "memoryUsed": 12288,
    "timedOut": false,
    "status": "success"
  },
  "total": 8
}
```

### 최종 메시지 예시 (`/execute_v2`)
```json
{
	"type": "final",
	"results": [
		{
			"requestId": "5f855593-4347-4142-8b73-01c98aa2c0c3",
			"stdout": "asdofasd\n",
			"stderr": "",
			"exitCode": 0,
			"duration": 12.89,
			"memoryUsed": 616,
			"timedOut": false
		},
		{
			"requestId": "c4b50694-c15c-4ce7-ab76-5e3754eebeb7",
			"stdout": "asdofasd\n",
			"stderr": "",
			"exitCode": 0,
			"duration": 14.02,
			"memoryUsed": 592,
			"timedOut": false
		}
	]
}
```

### 최종 메시지 예시 (`/execute_v3`)
`"total": 8`은 전체 테스트 케이스의 개수입니다. 만약 채점 도중 특정 테스트케이스가 정답과 다를 경우 바로 중단되며 최종 메시지를 출력할 수 있습니다.
```json
{
	"type": "final",
	"problemId": "prob-004",
	"allPassed": false,
	"results": [
                {
                        "id": 1,
                        "visibility": "public",
                        "passed": true,
                        "status": "success",
                        "expected": "14",
                        "stdout": "14\n",
                        "stderr": "",
                        "exitCode": 0,
                        "duration": 13.35,
                        "memoryUsed": 588,
                        "timedOut": false
                },
                {
                        "id": 2,
                        "visibility": "hidden",
                        "passed": false,
                        "status": "timeout",
                        "expected": "10",
                        "stdout": "",
                        "stderr": "",
                        "exitCode": -9,
                        "duration": 30001.0,
                        "memoryUsed": 616,
                        "timedOut": true
                }
        ],
	"total": 8
}
```

`type`이 `final`인 메시지를 받은 뒤에는 클라이언트가 WebSocket 연결을 종료하면 됩니다.

### 진행 상황 구독
기본 흐름은 다음과 같습니다.
1. 위 API에 코드를 POST하여 `requestId`를 얻습니다.
2. `ws://<서버주소>/ws/progress/{requestId}` WebSocket에 연결합니다.
3. 서버가 보내는 `progress` / `final` 메시지를 수신합니다.
4. `final` 메시지를 받은 뒤 WebSocket을 닫습니다.

각 `progress` 메시지에는 `index`와 `result`가 포함됩니다. `index`는 문제의 테스트 케이스 순서를 나타냅니다. 추가로, `POST /execute_v3`을 이용하였을 경우 `total` 값이 포함되어 전체 테스트 케이스 수를 알려줍니다. 이 `total` 값으로 유저가 채점 현황(%)을 보는 데에 사용할 수 있습니다. 이 과정을 구현한 예시는 `frontend/index_v3.html`과 `frontend/app_v3.js`에서 확인할 수 있습니다.
또한 `/execute_v3`의 진행 메시지 `result`에는 즉시 판별된 `status` 값이 포함됩니다.
