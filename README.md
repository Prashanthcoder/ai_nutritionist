# AI Nutritionist — Project Overview

This repository implements a small AI-assisted nutrition demo. It includes a FastAPI backend with async database access, small ML helpers, and a simple static frontend.

Repository structure
- `backend/` — FastAPI app, async SQLAlchemy models, CRUD, ML helpers, websocket manager.
- `frontendfinal/` — static frontend (HTML + assets) intended to talk to the backend.
- `main.py` — small proxy-style FastAPI app that returns the hosted demo HTML from `https://ainutritionists.lovable.app`.

Running locally — quick steps

1) Start the backend service

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

2) Serve the static frontend (optional)

```bash
cd frontendfinal
python -m http.server 8080
# then open http://localhost:8080
```

Key files and purpose
- `backend/main.py`: core API endpoints for searching foods, logging meals, analytics, ML endpoints (`/predict-weight`), and `GET /ai/suggest` which uses Google Generative AI.
- `backend/database/`: DB models (`models.py`), Pydantic schemas (`schemas.py`), CRUD helpers (`crud.py`) and async DB configuration (`config.py`).
- `backend/create_tables.py`: convenience script to create DB tables.
- `main.py` (repo root): lightweight proxy that fetches and returns the hosted frontend HTML.

Environment variables
- `DATABASE_URL` — Postgres DSN (asyncpg), default present in `backend/database/config.py`.
- `REDIS_URL` — Redis connection string used by websocket manager (optional).
- `GEMINI_API_KEY` — Google Generative AI key (optional) used by the `ai/suggest` endpoint.

API overview (selected)
- `GET /` — serves an iframe or proxied frontend.
- `GET /foods?query=...` — food search.
- `POST /log-meal` and `GET /meal/today` — log and fetch user meals.
- `POST /predict-weight` — weight prediction from an uploaded image.
- `GET /ai/suggest?user_id=...` — short AI suggestion for user's daily progress.

Notes and recommendations
- The backend is asynchronous and will create tables on startup if needed; `create_tables.py` is provided for manual DDL runs.
- ML helpers under `backend/ml/` are lightweight wrappers — ensure model files or dependencies exist before calling ML endpoints.
- CORS policy in the backend is permissive for local development.

If you prefer a single canonical README, the per-folder READMEs were consolidated here. If you'd like, I can also add:
- example curl/Postman snippets for core endpoints
- `docker-compose.yml` that brings up Postgres + Redis + backend
- a small Postman collection or automated integration tests

