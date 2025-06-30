# Online Judge Backend REST API

This document describes the HTTP API provided by the backend. There are three main endpoints:

- `POST /execute` &ndash; run code synchronously.
- `POST /execute_v2` &ndash; run code asynchronously and stream progress through WebSockets.
- `POST /execute_v3` &ndash; grade code against predefined problems. Progress is streamed as with `/execute_v2`.

For websocket updates, connect to `/ws/progress/{requestId}` using the `requestId` returned by the `v2` or `v3` endpoints.

## POST `/execute`

```json
{
  "language": "python",
  "code": "print(input())",
  "stdins": ["1"],
  "timeLimit": 30000,
  "memoryLimit": 256,
  "token": null
}
```

Responds with an array of execution results, one per item in `stdins`.

## POST `/execute_v2`

Uses the same request body as `/execute` but returns immediately with a `requestId`. Connect to `/ws/progress/{requestId}` to receive progress and the final results.

```json
{
  "requestId": "UUID"
}
```

## POST `/execute_v3`

Grades the given code against the problem specified by `problemId`. Test case data is read from `static/codeground-problems/{problemId}.json`.

```json
{
  "language": "python",
  "code": "print(input())",
  "problemId": "prob-001",
  "token": null
}
```

The HTTP response contains only a `requestId`. WebSocket messages include `progress` events for each test case and a final message:

```json
{
  "type": "final",
  "problemId": "prob-001",
  "allPassed": true,
  "results": [
    {
      "id": 1,
      "visibility": "public",
      "passed": true,
      "stdout": "2",
      "expected": "2"
    }
  ]
}
```

Each `progress` message contains `index`, `result` and `total` fields so the client can update progress bars.
