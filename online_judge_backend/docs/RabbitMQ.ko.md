# RabbitMQ 흐름 상세

이 문서는 `online_judge_backend`의 온라인 저지의 비동기 동작 흐름을 설명합니다. 간단한 `POST /execute` API로 코드를 실행하려면 백엔드 서버와 별도의 워커 프로세스(들이)가 필요하며, 이들은 RabbitMQ 큐를 통해 통신합니다. 이 큐잉을 위한 RabbitMQ 서버 역시 준비되어 있어야 합니다.

## 구성요소 개요
- **FastAPI 서버**: 요청을 받아 RabbitMQ 큐에 작업을 넣은 뒤, 결과를 받았을 때 응답합니다.
- **워커 프로세스(들)**: 큐에서 작업을 가져와 실제로 코드를 실행하고 결과를 돌려줍니다.
- **RabbitMQ 서버**: 이 코드베이스와는 별개로 준비되어 있어야 합니다. FastAPI 서버와 워커(들) 사이에서 메시지를 중계합니다.

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

각 구성요소가 RabbitMQ 서버에 연결되어 큐잉 기반으로 비동기 처리되므로, 워커 프로세스들을 여러 노드들에 배포하여 분산 처리가 가능합니다.

예를 들어, EC2 인스턴스 5대가 있다면, 
- RabbitMQ 서버용 EC2 인스턴스 1대

- FastAPI 백엔드용 EC2 인스턴스 1대 (`online_judge_backend.app.main:app --host 0.0.0.0 --port 8000`)

- 그리고 나머지 3대가 각각 워커 프로세스를 실행 (`python -m app.worker`)

... 같은 식으로 구성할 수 있습니다. 이렇게 되면 FastAPI 백엔드는 작업을 RabbitMQ로 푸시하고, 다른 EC2 인스턴스 워커(들이)가 이를 소비/실행하며, 완료되면 FastAPI 백엔드가 결과를 반환합니다.

# 스케줄링은 누가 하나?

기본적으로 이 코드베이스의 워커는 RabbitMQ 큐를 경쟁 소비자(competing consumers) 방식으로 소비합니다. 그리고 여러 워커가 같은 큐(`execute`)를 소비하더라도, **RabbitMQ 서버는 1개의 메시지를 1개의 워커에게만 전달합니다.** 그러므로, 워커는 `message.process()` 컨텍스트에서 작업을 처리하고 자동으로 `ack`(확인)하기에 동일한 메시지가 여러 워커 프로세스들에 의해 중복 실행되거나 특정 워커 프로세스만 주구장창 동작시키는 일은 발생하지 않습니다.