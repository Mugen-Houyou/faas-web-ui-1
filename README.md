# FaaS Web UI

This repository contains a simple web interface for an online compiler. Code is
compiled and executed by an AWS Lambda function exposed through API Gateway.

- Currently supports C and C++ (Java and Python will be added later)
- RESTful API endpoint provided by API Gateway
- Static frontend located in the `frontend` directory

## Requirements
There is no backend to run locally. Simply serve the static files in
`frontend/` or open `index.html` directly.

## Frontend Setup
Open `frontend/index.html` directly in a browser or serve it with a simple HTTP server:

```bash
cd frontend
python -m http.server 8080
```
Then navigate to `http://localhost:8080`.

## Usage
1. Enter your AWS API Gateway endpoint (e.g. `https://example.execute-api.amazonaws.com/prod/compile`).
2. Choose a language (C or C++).
3. Write your source code and optional standard input.
4. Click **Run** to see the output and execution time.

## Korean Version
For a Korean version of this document, see [README.ko.md](README.ko.md).

## License
No license file is provided.
