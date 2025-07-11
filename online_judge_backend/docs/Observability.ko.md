# 모니터링 및 메트릭 수집 가이드

이 문서는 FastAPI 백엔드와 워커 프로세스에서 Prometheus 기반 모니터링을 설정하는 방법을 설명합니다.

## 1. FastAPI 백엔드
- `logging_middleware.py` 미들웨어가 모든 HTTP 요청을 로깅하고 Prometheus 메트릭을 기록합니다.
- `main.py`에서 해당 미들웨어를 등록하고 `/metrics` 엔드포인트를 마운트하여 메트릭을 노출합니다.
- 수집되는 주요 메트릭
  - `http_requests_total`: 요청 수를 메서드와 경로, 상태 코드 기준으로 카운트합니다.
  - `http_request_latency_seconds`: 요청 지연 시간을 히스토그램으로 기록합니다.

## 2. 워커 프로세스
- `worker.py`는 작업 처리 결과와 시간을 Prometheus 메트릭으로 노출합니다.
- 워커 시작 시 `start_http_server(8001)`가 호출되어 포트 `8001`에서 메트릭을 제공합니다.
- 수집되는 주요 메트릭
  - `worker_jobs_total`: 작업 결과(성공/실패)별 카운트
  - `worker_job_duration_seconds`: 작업 처리 시간을 히스토그램으로 기록

## 3. Prometheus 설정 예시
다음과 같이 `prometheus.yml`에 스크레이프 대상을 추가할 수 있습니다.

```yaml
scrape_configs:
  - job_name: 'online-judge-backend'
    static_configs:
      - targets: ['localhost:18651']
  - job_name: 'online-judge-worker'
    static_configs:
      - targets: ['localhost:8001']
```

Prometheus 서버를 실행하면 `/metrics`와 워커 포트에서 메트릭을 수집하여 Grafana 등에서 시각화할 수 있습니다.
