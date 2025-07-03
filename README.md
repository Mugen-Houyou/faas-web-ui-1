# Codeground Online Judge

[한국어 README](README.ko.md)

- An interface that allows you to execute code via several HTTP endpoints.

- Executes Python, Java, C, and C++ code
- Returns **501 Not Implemented** for unsupported languages
- The backend (in the `online_judge_backend` folder) exposes `/execute` for synchronous
  runs and `/execute_v2`/`/execute_v3`/`/execute_v4` for asynchronous processing. Jobs are delivered
  to workers via RabbitMQ.
- Workers can be started with the command `python -m online_judge_backend.app.worker`.
- The frontend (in the `frontend` folder) is a demo web UI that utilizes the backend.

## Requirements
- A web browser is all you need to use the frontend.
- The backend requires Python 3.11 and additional tools such as C/C++ compilers and a JDK as described below.

## Backend Setup
1. Create and activate a virtual environment:
   ```bash
   cd online_judge_backend
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Install C/C++ compilers (for Ubuntu 22.04 LTS):
   ```bash
   sudo apt update
   sudo apt install build-essential
   ```
4. Install OpenJDK (for Ubuntu 22.04 LTS):
   ```bash
   sudo apt install openjdk-17-jdk
   ```
5. Run the RabbitMQ server. The default address is `amqp://guest:guest@localhost/` and can be changed using the `RABBITMQ_URL` on the `.env` file.

- For detailed installation instructions refer to the [official documentation](https://www.rabbitmq.com/docs/install-debian). Or you might want to consider using the [official Docker image](https://hub.docker.com/_/rabbitmq).

6. Start the worker process:
   ```bash
   python -m online_judge_backend.app.worker
   ```
7. Start the FastAPI backend:
   ```bash
   uvicorn online_judge_backend.app.main:app --host 0.0.0.0 --port 18651
   ```

## Running the Frontend
You can either directly open `frontend/index.html` in a browser or serve it using a simple HTTP server.

```bash
cd frontend
python -m http.server 8080
```
Then visit `http://localhost:8080`.

The original `frontend/index.html` still uses the synchronous `/execute`
endpoint. The `frontend/index_v2.html` page demonstrates the asynchronous API
that streams progress over WebSockets. Problem-based judging can also be
tested with `frontend/index_v3.html`, which calls the `/execute_v3` API. A variant
`/execute_v4` works the same but omits `stdout` and `stderr` from the results. The
`/execute_v3` endpoint streams judging progress in the same way as
`/execute_v2`. Because the client does not know the number of test cases in
advance, each progress message now includes a `total` field so the progress bar
can be updated correctly. If any test case fails, the remaining cases are skipped
and the final graded result is returned immediately. The HTTP response only
contains a `requestId` and the final graded result is delivered via the
WebSocket.

Problem definitions are normally loaded from an AWS S3 bucket. If the AWS
environment variables are not set or the bucket is unreachable, the backend
falls back to the JSON files in `online_judge_backend/static`. See
`online_judge_backend/.env.example` for the variables that configure the S3
bucket and prefix used by `/execute_v3` and `/execute_v4`.

The frontend includes a field to specify the API URL. The default is `http://localhost:18651`, which points to the FastAPI backend. If specifying a different server, make sure CORS settings are configured properly. Additional origins can be added via the `CORS_ALLOW_ORIGINS` variable in the `.env` file (comma-separated).

## Usage
After entering a JWT token, select a language and write your code. If there is STDIN input, enter it as blocks separated by blank lines. Each block can contain multiple lines, and a new execution is triggered when a blank line is encountered. Press the **Execute!** button to receive an array of results, one per input block.

## REST API Specification
Refer to [online_judge_backend/docs/API.md](online_judge_backend/docs/API.md) for an overview of the REST API. A more detailed Korean version is available at `API.ko.md`.

## Asynchronous Processing with RabbitMQ Server
This codebase is designed with **asynchronous processing based on a RabbitMQ server** in mind. See [online_judge_backend/docs/RabbitMQ.ko.md](online_judge_backend/docs/RabbitMQ.ko.md) for more information.

## Building Docker Images for AWS ECR
Two Dockerfiles are provided for running the backend and worker on ECS/Fargate.

Build the backend image:

```bash
docker build -f Dockerfile.online-judge.backend -t <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/online-judge-backend:latest .
```

Build the worker image:

```bash
docker build -f Dockerfile.online-judge.worker -t <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/online-judge-worker:latest .
```

Push images to ECR (after logging in):

```bash
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/online-judge-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/online-judge-worker:latest
```

## Configuring Environment Variables on AWS
You can define environment variables such as `CORS_ALLOW_ORIGINS`, `FAAS_BASE_URL`, `FAAS_TOKEN`, and `RABBITMQ_URL` in your ECS task definition. In the AWS console, open the task definition and add them under **Environment variables**. These can also be specified when registering the task definition using the AWS CLI.

## License
This repository does not include a separate license file.
