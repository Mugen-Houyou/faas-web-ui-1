# RabbitMQ 기반 비동기 실행 튜토리얼

`online_judge_backend` 폴더를 RabbitMQ와 함께 사용하여 비동기 실행 환경을 구성하는 방법을 설명합니다.

## 요구 사항
- Python 3.11
- RabbitMQ 3.x
- 기타 파이썬 의존성은 `online_judge_backend/requirements.txt`를 참고하세요.

## 단계별 가이드
1. RabbitMQ 설치(Ubuntu 22.04 LTS 기준)
   ```bash
   sudo apt update
   sudo apt install rabbitmq-server
   ```
2. RabbitMQ 서비스 시작
   ```bash
   sudo systemctl enable rabbitmq-server
   sudo systemctl start rabbitmq-server
   ```
3. 백엔드 가상 환경 준비
   ```bash
   cd online_judge_backend
   python3 -m venv venv
   source venv/bin/activate
   ```
4. 의존성 설치
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. 환경 변수 설정
   `RABBITMQ_URL` 변수를 이용해 접속 정보를 지정할 수 있습니다. 기본값은 `amqp://guest:guest@localhost/` 입니다.
   ```bash
   export RABBITMQ_URL=amqp://user:pass@localhost/
   ```
6. 워커 실행
   ```bash
   python -m online_judge_backend.app.worker
   ```
   워커는 `execute` 큐에서 작업을 가져와 코드를 실행하고 결과를 다시 전송합니다.
7. FastAPI 서버 실행
   ```bash
   uvicorn online_judge_backend.app.main:app --host 0.0.0.0 --port 8000
   ```
   서버는 실행 시 RPC 클라이언트를 생성하여 요청을 큐에 넣고 결과를 받아 전달합니다.
8. 프론트엔드 사용
   기존 프론트엔드에서 `/execute` 엔드포인트를 호출하면 큐를 통해 실행이 이루어집니다.

## 종료
워커와 서버는 각각 실행 중인 터미널에서 `Ctrl+C`로 중지할 수 있습니다. 필요하다면 RabbitMQ 서비스는 다음 명령으로 종료합니다.
```bash
sudo systemctl stop rabbitmq-server
```

자세한 REST API 사용법은 `online_judge_backend/docs/API.ko.md`를 참고하세요.
