# Backend (API, Scrapers, Scoring)

## Setup

- Python 3.11
- FastAPI, SQLAlchemy 2, Alembic
- Postgres 15 (via Docker)

## Structure

- `src/app/` — FastAPI app, routers, core
- `src/db/` — models, alembic
- `src/scrapers/` — leaderboard scrapers
- `src/scoring/` — normalisation, composite
- `src/jobs/` — nightly job

## Run (dev)

```sh
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn src.app.main:app --reload
```

Or use Docker Compose (see root README). 