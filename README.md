# SiraPilot AI

SiraPilot AI is a career-planning workspace. Phase 0 establishes the React
application shell, FastAPI service, PostgreSQL and Redis configuration, and
local background-worker infrastructure. Career workflows and integrations are
intentionally not implemented yet.

## Run the full stack

Requirements: Docker Engine with Docker Compose v2.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). The API documentation is
at [http://localhost:8000/docs](http://localhost:8000/docs); the readiness
endpoint is [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health).

The sample `.env` values are for local development only. Replace them with
managed secrets before deploying anywhere shared or public.

## Local development

Start the PostgreSQL and Redis services:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis
```

In a Python 3.11+ environment, install and start the API:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

In a separate terminal with Node.js 20+:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Vite serves the frontend on port 5173 and proxies API requests to port 8000.
For local background processing, run the worker and scheduler from `backend/`:

```powershell
celery -A app.workers.celery_app:celery_app worker --loglevel=INFO
celery -A app.workers.celery_app:celery_app beat --loglevel=INFO
```

See [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) for environment details,
testing, and troubleshooting.

## Validation

```powershell
# frontend/
npm test
npm run build

# backend/
pytest
alembic upgrade head
```

Database readiness uses a real `SELECT 1` against PostgreSQL. The initial
migration is deliberately an empty baseline: no career-domain tables are
introduced in Phase 0. See [docs/DATABASE.md](./docs/DATABASE.md).

## Project structure

- `frontend/` — React, TypeScript, Vite, Tailwind, and the dashboard shell.
- `backend/` — FastAPI, SQLAlchemy, Alembic, structured logs, and Celery.
- `infrastructure/` — Docker and Nginx configuration.
- `docs/` — architecture, development, database, security, and roadmap.

The dashboard emphasizes a clear career starting point, visible service
readiness, and simple next-step navigation. Those interaction priorities were
informed by the public career workflow in
[career-ops](https://github.com/career-ops-hq/career-ops), the workspace
organization in [Ekko Studio](https://github.com/EKKOLearnAI/hermes-web-ui),
and the planning patterns in
[Super Productivity](https://github.com/johannesjo/super-productivity).
No source code from those projects is included.
