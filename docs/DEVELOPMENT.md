# Development

## Requirements

- Docker Engine and Docker Compose v2 for the complete stack.
- Node.js 20+ and npm for frontend development.
- Python 3.11+ for the API, tests, and workers.

## Environment

At the repository root, copy the example and keep the resulting `.env`
uncommitted:

```powershell
Copy-Item .env.example .env
```

The example contains local-only PostgreSQL credentials and a development
signing secret. Do not reuse either value in staging or production. The API
validates required settings on startup. `DATABASE_URL` must use
`postgresql+psycopg`, `REDIS_URL` must use `redis` or `rediss`, `SECRET_KEY`
must contain at least 32 characters, and `CORS_ORIGINS` is a JSON array of
specific origins.

## Full Docker stack

```powershell
docker compose up --build
docker compose ps
docker compose logs -f backend worker beat
```

The frontend is at `http://localhost:8080`; API docs are at
`http://localhost:8000/docs`. Compose waits for PostgreSQL and Redis health
before starting the API, then waits for API readiness before starting the
frontend and workers. PostgreSQL data and Redis append-only data use named
volumes.

Stop the services with `docker compose down`. To intentionally remove local
database and Redis data as well, use `docker compose down --volumes`.

## Run services on the host

Use Compose for PostgreSQL and Redis, then run each application process in a
separate terminal. The Compose ports bind to the local development host.

```powershell
docker compose up -d postgres redis
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

```powershell
Set-Location frontend
npm ci
npm run dev
```

Vite defaults to proxying API traffic to `http://127.0.0.1:8000`. Set
`VITE_API_PROXY_TARGET` in the frontend process environment to use a different
local API host.

Run background processes from `backend/` when needed:

```powershell
celery -A app.workers.celery_app:celery_app worker --loglevel=INFO
celery -A app.workers.celery_app:celery_app beat --loglevel=INFO
```

## Tests and checks

From `frontend/`:

```powershell
npm test
npm run build
```

From `backend/`:

```powershell
pytest
alembic upgrade head
```

The backend tests use SQLite in memory for deterministic connection/readiness
checks; the Compose backend readiness probe checks the actual PostgreSQL
connection. Run `alembic upgrade head` with the configured PostgreSQL service
to verify an environment's migration connectivity.

## Troubleshooting

- If Compose reports unset variables, confirm `.env` is in the repository
  root and contains every value from `.env.example`.
- If local ports are occupied, adjust `POSTGRES_PORT` in `.env`; frontend and
  API host ports can be changed in `docker-compose.yml`.
- If an API request fails in the browser, check `/health/ready`, then inspect
  `docker compose logs backend postgres`.
