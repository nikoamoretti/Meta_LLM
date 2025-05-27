# Meta-LLM Leaderboard Aggregator

Nightly scrape public LLM leaderboards, normalise metrics, compute composite scores, and expose via JSON API and React dashboard.

## Local Development

1. Clone the repo
2. Build and start all services:
   ```sh
   docker compose up --build
   ```
3. Access:
   - API: http://localhost:8000
   - Frontend: http://localhost:3000

## Directory Structure

- `/backend` — FastAPI, scrapers, scoring, DB
- `/frontend` — Next.js 14, React 18, Tailwind

See `/backend/README.md` and `/frontend/README.md` for details. 