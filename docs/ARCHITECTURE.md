# Architecture

## Phase 0 boundaries

SiraPilot AI is a small monorepo with a browser client, a versioned HTTP API,
and separate background worker processes. This phase delivers the application
foundation and an honest dashboard shell; it does not include user accounts,
career-domain tables, external integrations, or generated sample data.

```text
Browser ──> Nginx (container) ──> React/Vite static build
                    ├──────────> FastAPI /api/v1
                    └──────────> FastAPI /health
                                      ├── PostgreSQL
                                      └── Redis <── Celery worker / Beat
```

In local development, Vite serves the frontend and proxies `/api` and
`/health` to FastAPI. In Compose, Nginx serves the compiled client and proxies
API and health requests over the private Compose network.

## Frontend

- React 18 and TypeScript, built by Vite.
- React Router defines the app shell and routes. Routes for future feature
  areas explicitly show that those areas are not part of this phase.
- TanStack Query fetches the real API/database readiness status and shows
  loading, failure, and retry states.
- Zustand persists only the user's light/dark theme preference.
- Tailwind CSS uses shared HSL design tokens. `components.json`, `cn`, and
  reusable button/card primitives establish the shadcn/ui conventions.
- React Hook Form, Zod, and their resolver are installed for later forms; no
  business form is introduced before its feature is scoped.

## Backend

- FastAPI exposes versioned API routes under `/api/v1`; operational liveness
  and readiness probes are available at `/health/live` and `/health/ready`.
- Pydantic Settings reads environment variables and the repository `.env`.
  Database and Redis URLs, secret length, CORS origins, and runtime mode are
  validated before the service starts.
- SQLAlchemy 2 creates a PostgreSQL engine with connection pre-ping. Shared
  model mixins define UUID primary keys and timezone-aware timestamps; metadata
  has deterministic constraint names.
- Alembic owns schema changes. The first revision establishes a migration
  baseline without creating domain tables.
- Structlog emits JSON application logs with UTC timestamps. Unhandled API
  errors are logged and return a generic response.
- Celery worker and Beat use Redis, UTC scheduling, late acknowledgement,
  bounded exponential retry, and jitter. No sample tasks or schedules are
  registered.

## Runtime and trust boundaries

Compose keeps PostgreSQL and Redis on the internal service network. The
development ports are for local use only. The frontend receives API data from
the same-origin proxy; credentials and runtime settings are supplied as
environment variables, not baked into frontend assets.

For repository-specific setup and commands, see
[DEVELOPMENT.md](./DEVELOPMENT.md). For schema and migration conventions, see
[DATABASE.md](./DATABASE.md).
