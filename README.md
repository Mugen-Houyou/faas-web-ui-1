# FaaS Web UI

This repository contains a simple code runner. The frontend communicates with
an external FaaS-based execution service via REST API.

- Execute Python, C, C++, and Java code
- Calls `POST /execute` on the remote API
- Static frontend located in the `frontend` directory

## Requirements
Only a web browser is required to use the frontend. The execution backend is
hosted separately.

## Frontend Setup
The frontend consists of static files. Open `frontend/index.html` directly in a browser or serve it with a simple HTTP server:

```bash
cd frontend
python -m http.server 8080
```
Then navigate to `http://localhost:8080`.

## Usage
Enter your JWT token, select a language, provide code and optional STDIN, then click **Run**. The page will call the remote FaaS API and display the result.

## Korean Version
For a Korean version of this document, see [README.ko.md](README.ko.md).

## License
No license file is provided.
