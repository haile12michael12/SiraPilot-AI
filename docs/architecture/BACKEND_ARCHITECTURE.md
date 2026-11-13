# Backend Architecture

## Current implementation

The API is a FastAPI application. `app.main` owns application construction and lifespan setup. API authentication and route composition live in `app.api`; feature routers remain under `app.modules`. The v1 router is publicly mounted at `/api/v1`. Existing `/api/...` paths remain hidden-from-schema compatibility aliases for the dashboard and extension.

Current code is organized by responsibility:

| Area | Current owner |
| --- | --- |
| Request composition and feature routes | `app/api/`, `app/modules/` |
| Settings and process configuration | `app/config.py`, `app/core/` |
| SQLite/libSQL connections, transactions, and synchronization | `app/infra/` |
| HTTP, dependencies, logging, runtime lifecycle | `app/platform/` |
| Offline backup, restore, and checkout adoption | `app/maintenance/` |
| Pure shared values and utilities | `app/shared/` |

Routers translate requests, feature services coordinate use cases, and repositories own feature data access. Cross-feature operations are explicit application owners rather than generic service layers. See the [current architecture](../../ARCHITECTURE.md) and [API guide](../../apps/api/README.md) for behavioral invariants.

## Target boundaries

The approved redesign moves toward the following ownership:

| Target area | Responsibility |
| --- | --- |
| `app/api/` | Public transport, API versions, and request/response contracts |
| `app/core/` | Settings, authentication/authorization primitives, errors, logging, and middleware |
| `app/modules/` | Implemented product capabilities, each with explicit ownership rules |
| `app/infra/postgres/` | Implemented opt-in PostgreSQL models, sessions, transactions, and repositories |
| `apps/api/alembic/` | PostgreSQL-only, forward-only Alembic migrations |
| `app/infrastructure/` | Cache, queue, storage, and telemetry adapters as needed |
| `app/integrations/` | Browser, email, calendar, job board, and AI provider boundaries |
| `app/shared/` | Cross-module schemas, enums, constants, and pure utilities |

This is a destination for real implementations, not a checklist for generating empty modules. Existing responsibilities should move in small, tested steps; module names alone do not define new product behavior.

## Multi-user isolation

The current data access layer has no user ownership boundary. Before a multi-user API can serve requests, every private record must have a durable owner, and all repository operations must be scoped to that owner. Foreign keys and unique constraints must include ownership where needed to prevent cross-account relationships and identifier collisions.

Authentication is not authorization: a valid session must be resolved to a principal, and each use case must enforce that principal's ownership. This applies equally to background workers, exports, duplicate matching, notifications, and administrative import tools. The public health and registration endpoints are deliberately separate from private application routes.

The initial account-access choice is self-service registration. Credential format, verification, recovery, rate limiting, session transport, and secret management remain security design requirements; do not implement a partial login flow before those decisions are documented and tested.

## Persistence and migration

PostgreSQL and Alembic are the selected target for the multi-user service. An isolated SQLAlchemy foundation and initial account-scoped schema are implemented, but the existing SQLite/libSQL/Turso runtime remains the current behavior. API startup does not create a PostgreSQL connection or run Alembic. A separately tested migration is required before replacing the current runtime; the transition must not mutate a user's live database or infer consent to upload it.

Existing data enters PostgreSQL only through an explicit import from a verified backup/snapshot. The importer must map all records to one selected account, preserve relationships and timestamps, validate foreign keys and counts, and be safely retryable. Full details are in the [migration strategy](../database/MIGRATION_STRATEGY.md).

## API compatibility

`app.api.v1` is the documented public API at `/api/v1/...`. The unversioned `/api/...` aliases remain available but are omitted from OpenAPI to avoid duplicate contracts. Dashboard and extension clients may migrate separately; remove aliases only in a deliberate breaking release.
