# Development Setup

## Runtime Choices

- Backend uses Python in the repo-root `.venv`.
- Frontend uses Node.js and npm.
- The frontend package manager is npm. Commit `frontend/package-lock.json` when dependencies change.

## Backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .\backend[dev]
```

Run backend checks:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Start the API:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend

Install dependencies:

```powershell
cd frontend
npm install
```

Run frontend checks:

```powershell
npm run lint
npm run build
npm run test
```

Start the Vite dev server:

```powershell
npm run dev
```

## Full Local Workflow

Run the backend and frontend in separate terminals:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:5173
```
