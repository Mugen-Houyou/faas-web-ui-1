# AWS ECR/ECS Fargate 배포 가이드

이 문서는 온라인 저지 백엔드와 워커 이미지를 AWS ECR과 ECS Fargate에 배포하여 필요할 때만 컨테이너를 실행하는, 이른바 "scale-to-zero"에 가까운 구조를 구성하는 방법을 안내합니다.

## 1. ECR 저장소 준비와 이미지 푸시
1. AWS 콘솔에서 **ECR** 서비스로 이동하여 백엔드(FastAPI)용과 워커(`worker.py`)용 두 개의 리포지토리를 생성합니다.
2. 로컬 PC 또는 CI 환경에서 아래 커맨드로 이미지를 빌드합니다.

```bash
docker build -f Dockerfile.online-judge.backend -t \
  <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/online-judge-backend:latest .

docker build -f Dockerfile.online-judge.worker -t \
  <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/online-judge-worker:latest .
```
3. 빌드가 끝나면 ECR에 로그인 후 이미지를 푸시합니다.

```bash
aws ecr get-login-password --region <REGION> | \
  docker login --username AWS --password-stdin \
  <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com

docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/online-judge-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/online-judge-worker:latest
```

## 2. ECS Fargate 작업 정의와 서비스 생성
1. **ECS → Task Definitions** 메뉴에서 Fargate를 선택해 작업 정의를 만듭니다.
2. 컨테이너 이미지에는 위에서 푸시한 ECR 이미지를 지정합니다.
3. 같은 화면에서 **Environment variables** 항목에 다음과 같이 `.env.example`에서 사용한 변수들을 입력할 수 있습니다.
   - `RABBITMQ_URL`
   - `CORS_ALLOW_ORIGINS`
   - `FAAS_BASE_URL`
   - `FAAS_TOKEN`
4. 필요한 CPU/메모리 값을 입력하고 작업 정의를 저장합니다.
5. 생성한 작업 정의로 **Service**를 만들면 Fargate에서 컨테이너가 실행됩니다.

## 3. Scale-to-zero 구현 꿀팁!
- ECS 서비스의 원하는 실행 개수(`Desired count`)를 0으로 변경하면 컨테이너가 모두 중지되어 비용을 최소화할 수 있습니다.
- AWS 콘솔에서 수동으로 값을 0으로 수정하거나,
  `aws ecs update-service --cluster <CLUSTER> --service <SERVICE> --desired-count 0`
  ... 커맨드로 스크립트화할 수 있습니다.
- CloudWatch Events(또는 EventBridge) 스케줄러를 이용해 야간에 자동으로 0으로   줄이고 필요 시 다시 1 이상으로 늘리는 방식으로 "사실상의" scale-to-zero 효과를 얻을 수 있습니다.
- 또는 RabbitMQ queue depth와 워커 개수를 이용한 스케일링을 고려해볼 수도 있습니다.

## 4. 추가 팁
- 로그는 CloudWatch Logs로 수집되므로, 오류 발생 시 해당 로그 그룹을 확인하세요.
- 이후 EKS로 마이그레이션을 진행하더라도 ECR 이미지는 그대로 사용할 수 있습니다.
