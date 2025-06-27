# Codeground Online Judge

[한국어 README](README.ko.md)

An interface that allows you to execute code via a simple `/execute` API.

- Executes Python, Java, C, and C++ code
- Returns **501 Not Implemented** for unsupported languages
- The backend (in the `online_judge_backend` folder) provides the `/execute` API using FastAPI and
  delivers jobs to workers via RabbitMQ.
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
5. Run the RabbitMQ server. The default address is `amqp://guest:guest@localhost/`, which can be changed using the `RABBITMQ_URL` environment variable. (e.g., use [Docker](https://hub.docker.com/_/rabbitmq) locally)
6. Start the worker process:
   ```bash
   python -m online_judge_backend.app.worker
   ```
7. Start the FastAPI backend:
   ```bash
   uvicorn online_judge_backend.app.main:app --host 0.0.0.0 --port 8000
   ```

## Running the Frontend
You can either directly open `frontend/index.html` in a browser or serve it using a simple HTTP server.

```bash
cd frontend
python -m http.server 8080
```
Then visit `http://localhost:8080`.

The frontend includes a field to specify the API URL. The default is `http://localhost:8000`, which points to the FastAPI backend. If specifying a different server, make sure CORS settings are configured properly.

## Usage
After entering a JWT token, select a language and write your code. If there is STDIN input, enter it as blocks separated by blank lines. Each block can contain multiple lines, and a new execution is triggered when a blank line is encountered. Press the **Execute!** button to receive an array of results, one per input block.

## REST API Specification
Refer to the [online_judge_backend/docs/API.ko.md](online_judge_backend/docs/API.ko.md) file for detailed REST API specifications.

## Asynchronous Processing with RabbitMQ Server
This codebase is designed with **asynchronous processing based on a RabbitMQ server** in mind. See the [online_judge_backend/docs/RabbitMQ.ko.md](online_judge_backend/docs/API.ko.md) file for more information.

## License
This repository does not include a separate license file.
