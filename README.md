# FaaS Web UI

This repository contains a simple code runner with a FastAPI backend and a minimal HTML/JavaScript frontend.

- Execute Python, C, C++, and Java code
- REST API powered by FastAPI
- Static frontend located in the `frontend` directory

## Requirements
- Python 3.11
- Compilers for C, C++, and Java (`gcc`, `g++`, `javac`)

## Backend Setup
1. Install Python 3.11 and create a virtual environment inside `backend`:
   ```bash
   cd backend
   python3.11 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Launch the server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Frontend Setup
The frontend consists of static files. Open `frontend/index.html` directly in a browser or serve it with a simple HTTP server:

```bash
cd frontend
python -m http.server 8080
```
Then navigate to `http://localhost:8080`.

## Usage
With both backend and frontend running, select a language, enter code, and click **Run** to see output and execution time.

## Korean Version
For a Korean version of this document, see [README.ko.md](README.ko.md).

## License
No license file is provided.
