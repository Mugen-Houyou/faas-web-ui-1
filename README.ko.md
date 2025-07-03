# Codeground 온라인 저지

이 프로젝트는 클라이언트로부터 HTTP 요청을 받아 코드를 실행하고 채점 결과를 제공하는 온라인 저지입니다. 데모용 프론트엔드(`frontend`), FastAPI 백엔드(`online_judge_backend/app/main.py`), 그리고 워커 프로세스(`online_judge_backend/app/worker.py`)로 구성되어 있습니다. `backend` 폴더는 추후 삭제 예정이므로 무시해주세요.

- Python, Java, C, C++ 코드를 실행
- 지원하지 않는 언어는 **501 Not Implemented** 응답
- 백엔드(`online_judge_backend` 폴더)는 FastAPI 기반 `/execute` API 외에도 `/execute_v2`, `/execute_v3`, `/execute_v4` 엔드포인트를 제공하며 RabbitMQ로 작업을 워커에 전달합니다.
- 워커는 `python -m online_judge_backend.app.worker` 명령으로 실행합니다.
- 프론트엔드(`frontend` 폴더)는 백엔드를 사용할 수 있는 데모 웹 UI입니다.

## 요구 사항
- 프론트엔드를 사용하려면 웹 브라우저만 있으면 됩니다.
- 백엔드를 사용하려면 Python 3.11이 필요하며 후술할 C, C++ 컴파일러, JDK 등이 필요합니다.
- RabbitMQ로 비동기 처리할 것을 상정하여 작성되었으므로 RabbitMQ 서버가 준비되어 있어야 합니다.

## 백엔드 설정
1. 가상 환경을 생성하고 활성화합니다.
   ```bash
   cd online_judge_backend
   python3 -m venv venv
   source venv/bin/activate
   ```
2. 의존성을 설치합니다.
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. C/C++ 컴파일러 설치(Ubuntu 22.04 LTS 기준):
   ```bash
   sudo apt update
   sudo apt install build-essential
   ```
4. OpenJDK 설치(Ubuntu 22.04 LTS 기준):
   ```bash
   sudo apt install openjdk-17-jdk
   ```
5. RabbitMQ 서버를 실행합니다. 기본 주소는 `amqp://guest:guest@localhost/`입니다.
- 자세한 설치 방법은 [공식 문서](https://www.rabbitmq.com/docs/install-debian)를 참조하세요. 또는 [Docker 이미지](https://hub.docker.com/_/rabbitmq)를 사용할 수도 있습니다.
- 인증에 쓰이는 `guest` / `guest`은 보안을 위해 바꾸는 것이 권장됩니다.

6. `.env.example`의 양식과 동일하게 `.env` 파일을 생성하여 환경 변수를 구성합니다.
- `.env.example`을 복사 후 `.env`라는 이름으로 붙여넣기하면 됩니다.

7. `online_judge_backend/app`로 이동하여 워커 프로세스를 실행합니다.
   ```bash
   python -m app.worker
   ```
8. `online_judge_backend/app`로 이동하여 FastAPI 백엔드를 실행합니다.
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 18651
   ```

## 프론트엔드 실행
`frontend/index.html`을 브라우저로 직접 열거나 간단한 HTTP 서버를 이용해 제공할 수 있습니다.

```bash
cd frontend
python -m http.server 8080
```
이후 `http://localhost:8080`에 접속합니다.

기존 `frontend/index.html`은 여전히 동기식 `/execute` 엔드포인트를 사용합
니다. `frontend/index_v2.html` 페이지에서는 WebSocket으로 진행 상황을 받
아오는 비동기 API 동작을 확인할 수 있습니다. 문제 기반 채점은
`frontend/index_v3.html` 페이지에서 `/execute_v3` API를 통해 확인할 수 있으며, `/execute_v3` 역시 `/execute_v2`와 마찬가지로 진행 상황을 WebSocket으로 전송합니다. `/execute_v4`는 동일하지만 `stdout`과 `stderr`를 클라이언트에 보내지 않습니다.

클라이언트는 테스트 케이스 수를 미리 알 수 없으므로 각 `progress` 메시지에는 전체 개수를 나타내는 `total` 값이 포함됩니다. 테스트 케이스가 하나라도 실패하면 남은 케이스는 실행하지 않고 즉시 결과가 전송됩니다. `/execute_v3`의 HTTP 응답에는 `requestId`만 포함되며 최종 채점 결과는 WebSocket 메시지로 전달됩니다.

문제 정의는 기본적으로 AWS S3 버킷에서 읽어오지만, AWS 관련 환경 변수가 비어 있거나 버킷에 연결할 수 없는 경우 `online_judge_backend/static` 폴더에 있는 JSON 파일을 사용합니다. 각 파일에는 테스트 케이스와 제한 사항이 담겨 있으며 `/execute_v3`와 `/execute_v4`에서 사용됩니다.

프론트엔드에는 API 주소를 입력할 수 있는 필드가 있습니다. 기본값은 `http://localhost:18651`으로 FastAPI 백엔드를 가리킵니다. 다른 서버를 지정하는 경우 CORS 설정이 되어 있어야 합니다. 추가 오리진은 `.env` 파일의 `CORS_ALLOW_ORIGINS` 변수(콤마 구분)를 통해 지정할 수 있습니다.

## 사용법
JWT 토큰을 입력한 뒤 언어와 코드를 작성하고 STDIN이 있다면 빈 줄로 구분된 블록 단위로 입력할 수 있습니다. 한 블록은 여러 줄을 포함할 수 있으며, 빈 줄이 나타날 때마다 다음 실행으로 인식됩니다. **실행!** 버튼을 누르면 각 블록에 대해 코드를 실행한 결과 배열을 돌려줍니다.

## REST API 명세
REST API의 세부 규격은 [online_judge_backend/docs/API.ko.md](online_judge_backend/docs/API.ko.md) 파일을 참고하세요. 간단한 영어 버전은 `API.md`에서 확인할 수 있습니다.

## RabbitMQ 관련
이 코드베이스는 **RabbitMQ 서버 기반 비동기 처리**를 상정하여 구성되었습니다. [online_judge_backend/docs/RabbitMQ.ko.md](online_judge_backend/docs/RabbitMQ.ko.md) 파일을 참고하세요.

## AWS 배포
AWS ECR/ECS Fargate에 이미지를 배포하고 환경 변수를 설정하는 방법은
[online_judge_backend/docs/AWS_Deploy.ko.md](online_judge_backend/docs/AWS_Deploy.ko.md)
문서를 참고하세요.

## 라이선스
이 저장소에는 별도의 라이선스 파일이 포함되어 있지 않습니다.
