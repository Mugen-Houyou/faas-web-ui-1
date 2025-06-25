# FaaS Web UI

This project provides a small interface for running code through an external Function‑as‑a‑Service (FaaS) execution API.

- Execute Python, C, C++, and Java code
- Communicates with the API's `POST /execute` endpoint
- Optional FastAPI proxy in `backend`
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
3. Copy `.env.example` to `.env` and set variables as needed:
   - `FAAS_BASE_URL` (default `https://api.example.com/api/v1`)
   - `FAAS_TOKEN` for authenticated access
4. Launch the server:
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

## Usage
Enter your JWT token (if required), choose a language, provide code and optional STDIN, and click **Run**. The page sends the request to the FaaS API and displays the output along with exit code, execution time, and memory usage. Long-running jobs are polled until they finish.

## Korean Version
See [README.ko.md](README.ko.md).

## License
No license file is provided.
