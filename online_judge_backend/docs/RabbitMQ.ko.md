# RabbitMQ 가이드

이 문서는 `online_judge_backend`의 온라인 저지의 비동기 동작 흐름 및 RabbitMQ 환경 설정 방법을 설명합니다. 간단한 `POST /execute` API로 코드를 실행하려면 백엔드 서버와 별도의 워커 프로세스가 필요하며, 이들은 RabbitMQ 큐를 통해 통신합니다. 이 큐잉을 위한 RabbitMQ 서버 역시 준비되어 있어야 합니다.

## 구성요소 개요
- **FastAPI 서버**: 요청을 받아 RabbitMQ 큐에 작업을 넣은 뒤, 결과를 받았을 때 응답합니다.
- **워커 프로세스(들)**: 큐에서 작업을 가져와 실제로 코드를 실행하고 결과를 돌려줍니다.
- **RabbitMQ 서버**: 이 코드베이스와는 별개로 준비되어 있어야 합니다. FastAPI 서버와 워커(들) 사이에서 메시지를 중계합니다.

## RabbitMQ 서버 준비
RabbitMQ 서버를 직접 설치할 수도 있지만, 다음과 같이 Docker 이미지를 이용하면 빠르게 실행할 수 있습니다.

```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

- `.env`에 명시하지 않았을 경우 기본 접속 URL은 `amqp://guest:guest@localhost/` 입니다.
- 관리 UI는 `http://localhost:15672` 에서 확인할 수 있으며 기본 계정은 guest/guest 입니다.

필요하다면 `.env.example`의 양식에 맞추어 `RABBITMQ_URL` 환경 변수를 명시할 수 있습니다.

## 워커 실행
백엔드 루트(`online_judge_backend` 폴더)에서 다음 명령으로 워커 프로세스를 실행합니다.

```bash
python -m app.worker
```

워커는 RabbitMQ 큐에서 작업을 읽어 들여 **실제 코드 실행**을 담당합니다. 이 프로세스는 백엔드 API 서버와 별개로 계속 실행되고 있어야 합니다.

## FastAPI 서버 실행
다른 터미널에서 가상 환경을 활성화한 뒤 아래 명령으로 FastAPI 서버를 실행합니다.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

서버가 실행되면 `/execute` 엔드포인트를 통해 코드를 실행할 수 있습니다. 워커가 실행 중이어야 결과를 받을 수 있습니다.

## `POST /execute` 요청 처리 흐름
**1. FastAPI 백엔드 초기화 및 RPC 클라이언트 연결**
- FastAPI 백엔드는 startup 시 `get_rpc_client()`로 RabbitMQ에 연결해 RPC 클라이언트를 준비합니다. 
- FastAPI 백엔드의 startup 시 초기화된 `rabbitmq_rpc.py`의 `RpcClient`는, `RabbitMQ` 연결, 임시 응답 큐 생성, 응답 메시지 처리 등을 담당합니다. 종료 시 연결을 닫습니다.

**2. 요청 처리 → RabbitMQ로 작업 전송**
- FastAPI 백엔드는 클라이언트로부터 `POST /execute` 요청을 받습니다.
- 이후 FastAPI 백엔드는 그 내용을 payload로 만든 뒤 `RpcClient.call()`을 통해 RabbitMQ의 `execute` 큐로 메시지를 발행합니다. 
- 이후 FastAPI 백엔드는 응답을 받을 때까지 대기합니다.

**3. 워커 프로세스**
- 워커 (`online_judge_backend/app/worker.py`의 `main()`)가 별도 프로세스로 실행됩니다. 
- 이 워커는 `execute` 큐에서 메시지를 받아 `execute_code_multiple()`로 코드를 실행하고, 결과를 원래 요청자가 기다리는 응답 큐(`reply_to`)로 다시 전송합니다.

**4. FastAPI 백엔드 응답**
- FastAPI 백엔드는, RabbitMQ와 연결된 상태로 응답을 기다렸다가, 요청 당시와 같은 ID로 응답이 오면 결과를 반환합니다.

## 종료 방법
실행 중인 컨테이너 및 프로세스는 다음과 같은 식으로 종료할 수 있습니다.
```bash
docker stop rabbitmq && docker rm rabbitmq
# 워커와 서버 프로세스는 각각 Ctrl+C 로 종료
```

# 예시 아키텍처
![alt text](image.png)

이 코드베이스는 FastAPI 백엔드와 워커 프로세스(들이)가 분리되어, 이들을 RabbitMQ 서버를 통해 중계할 것으로 상정하여 제작되었습니다. 즉, 각 구성요소가 RabbitMQ 서버에 연결되기만 한다면, 서로 다른 노드들에 배포 및 분산 처리가 가능해짐을 의미합니다.

예를 들어, EC2 인스턴스 5대가 있다면, 
- RabbitMQ 서버용 EC2 인스턴스 1대

- FastAPI 백엔드용 EC2 인스턴스 1대 (`online_judge_backend.app.main:app --host 0.0.0.0 --port 8000`)

- 그리고 나머지 3대가 각각 워커 프로세스를 실행 (`python -m online_judge_backend.app.worker`)

... 같은 식으로 구성할 수 있습니다. 이렇게 되면 FastAPI 백엔드는 작업을 RabbitMQ로 푸시하고, 다른 EC2 인스턴스 워커(들이)가 이를 소비/실행하며, 완료되면 FastAPI 백엔드가 결과를 반환합니다.

