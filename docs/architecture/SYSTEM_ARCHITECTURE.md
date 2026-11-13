# System Architecture

## Current system

SiraPilot AI is currently a local-first job tracker composed of a FastAPI API, a React dashboard, and a Chromium extension. The API owns application behavior and persists job-search data in SQLite/libSQL, with optional Turso synchronization. The dashboard and extension use the existing `/api` contract.

The current implementation is intentionally single-user. Its local database is not tenant-scoped, and the optional shared API key is not user authentication. The current runtime and data model must not be exposed as a multi-user service.

## Approved target direction

The target architecture is a multi-user application backed by PostgreSQL, with self-service account registration and an explicit, backed-up import of existing single-user data into an account. The implementation is a breaking migration and must not silently convert, upload, or discard a user's existing database.

The system will retain the existing API paths while internal boundaries are reorganized. A public URL versioning change is a separate compatibility decision. Existing browser clients must continue to work until a deliberate contract migration is designed and tested.

## Component boundaries

```text
SiraPilot-AI/
├── apps/
│   ├── api/        FastAPI routes, domain modules, AI, persistence and integrations
│   ├── web/        React dashboard
│   └── extension/  Chromium extension
├── packages/
│   └── shared/     Generated API contracts and shared TypeScript utilities
├── docs/           Architecture, product, security and operations documentation
└── scripts/        Setup, builds, checks and maintenance
```

Backend responsibilities are separated into:

- `api/`: transport and API version composition
- `core/`: application configuration, security, errors and request lifecycle
- `modules/`: implemented product capabilities and their domain operations
- `infrastructure/`: persistence, migrations, queues, storage and telemetry
- `integrations/`: external systems and provider adapters
- `shared/`: stable cross-module types and pure utilities
- `ai/`: provider, agent, orchestration, retrieval and evaluation components when implemented

The requested feature names are not a mandate to create empty packages. Add a module when it has a concrete implementation, tests, and an owning contract.

## Isolation and identity requirements

Every private record in the PostgreSQL target must be scoped to its owning user. API authentication identifies the principal; services and repositories enforce ownership on every read, write, lookup, merge, background job, and import. A client-supplied identifier is never proof of ownership.

Relationships between private records must prevent cross-user references at the database boundary as well as in application code. Background tasks must carry an explicit owner context or operate only on globally safe records. Logs and telemetry must not include passwords, tokens, private job data, or document content.

The account-authentication protocol, credential recovery, email verification, and operational deployment settings must be specified before authentication endpoints or account tables are implemented. See the [multi-user PostgreSQL ADR](ADR/0001-multi-user-postgresql.md).

## Migration boundaries

The PostgreSQL application database is the future system of record. Existing SQLite/libSQL and Turso installations are migration sources, not implicitly compatible PostgreSQL stores. A one-time importer must use an explicit operator action, validate and preserve source data, assign every imported private record to the selected account, and support safe retry without duplicates.

No schema or runtime migration may mutate the database currently used by the running local deployment. The import process must operate on a verified backup or read-only snapshot and report failures without presenting a partial import as success.

The rollout is phased: architecture and threat-boundary definition; PostgreSQL schema and migration infrastructure; authentication and user-scoped persistence; explicit legacy import; client session integration; then removal of obsolete runtime paths only after compatibility and release evidence.
