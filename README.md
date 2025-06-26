# FaaS Web UI

-This project provides a small interface for running code through a simple `/execute` API.

- Execute Python, C, C++, and Java code
- Unsupported languages return **501 Not Implemented**
- The backend compiles the source and then runs the result locally
- Static frontend located in the `frontend` directory

## Requirements
- Web browser for the frontend
- Python 3.11 for the optional backend

## Backend Setup (optional)
1. Create and activate a virtual environment:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Install C/C++ compilers (Ubuntu 22.04 LTS):
   ```bash
   sudo apt update
   sudo apt install build-essential
   ```
4. Install OpenJDK (Ubuntu 22.04 LTS):
   ```bash
   sudo apt install openjdk-17-jdk
   ```
5. Launch the server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Frontend Setup
Open `frontend/index.html` directly in a browser or serve the directory with a simple HTTP server:

```bash
cd frontend
python -m http.server 8080
```
Then navigate to `http://localhost:8080`.

The frontend includes a field to set the API URL. It defaults to
`http://localhost:8000`, which targets the provided FastAPI backend.
If you point it directly to a different server, ensure that CORS is enabled
or your browser may block the requests.

## Usage
Enter your JWT token (if required), choose a language, provide code and optional STDIN, and click **Run**. Multiple executions can be provided by separating each STDIN set with a blank line. Each set may contain multiple lines. The request is sent to the backend which compiles the code and runs it locally. The result shows the program output, exit code, and execution time.

## Korean Version
See [README.ko.md](README.ko.md).

## License
No license file is provided.
