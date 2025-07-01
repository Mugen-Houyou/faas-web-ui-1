# Online Judge Backend REST API

This document describes the HTTP API provided by the backend. There are three main endpoints:

- `POST /execute` &ndash; run code synchronously.
- `POST /execute_v2` &ndash; run code asynchronously and stream progress through WebSockets.
- `POST /execute_v3` &ndash; grade code against predefined problems. Progress is streamed as with `/execute_v2`.

For websocket updates, connect to `/ws/progress/{requestId}` using the `requestId` returned by the `v2` or `v3` endpoints.

## POST `/execute`
Please refer to the `API.ko.md` for the specific JSON format.

Responds with an array of execution results, one per item in `stdins`.

## POST `/execute_v2`

Uses the same request body as `/execute` but returns immediately with a `requestId`. Connect to `/ws/progress/{requestId}` to receive progress and the final results.

Please refer to the `API.ko.md` for the specific JSON format.

## POST `/execute_v3`

Grades the given code against the problem specified by `problemId`. Test case data
is loaded from an S3 bucket as configured in `.env`.

Please refer to the `API.ko.md` for the specific JSON format.

The HTTP response contains only a `requestId`. WebSocket messages include `progress` events for each test case and a final message:

Please refer to the `API.ko.md` for the specific JSON format.

Each `progress` message contains `index`, `result` and `total` fields so the client can update progress bars.
