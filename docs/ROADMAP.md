# Roadmap

## Phase 0 — Foundation

- [x] React, TypeScript, Vite, design tokens, theme, and responsive shell.
- [x] FastAPI configuration, API versioning, logging, error handling, and
  liveness/readiness endpoints.
- [x] PostgreSQL engine configuration, UUID/UTC model conventions, and
  initial Alembic baseline.
- [x] Redis-backed Celery worker and Beat foundations.
- [x] Docker Compose services, health checks, and setup documentation.
- [x] Frontend and backend foundation tests.

## Phase 1 — Product foundation

Begin only after Phase 0 has been reviewed and approved. Scope domain models,
authentication, onboarding, profile ownership, authorization boundaries, and
their migrations before implementing user-facing workflows.

## Later phases

Define feature boundaries and acceptance criteria for career intelligence,
knowledge graphs, job discovery and matching, application workflows, interview
preparation, calendar and task planning, notifications, billing, and
integrations before implementation. Protect user data and make external
connections explicit and opt-in.
