# ADR 0001: Multi-user PostgreSQL target and explicit legacy-data import

- Status: Accepted
- Date: 2026-11-13

## Context

The current application is a local-first, single-user job tracker backed by SQLite/libSQL, with optional Turso synchronization. The API has an optional shared API key, not per-user authentication. Private records have no owner field, and the current data layer is SQLite-oriented.

The target repository structure introduces users, profiles, authentication, PostgreSQL, and a server-oriented migration system. Moving files without first defining these boundaries would risk exposing one user's job-search data to another.

## Decisions

1. The target service is multi-user and uses PostgreSQL as its system of record.
2. Self-service account registration is the selected account-access model.
3. Existing SQLite/libSQL/Turso data is transferred only by an explicit import into a selected account. Import requires a verified backup and must never run automatically at application startup.
4. The importer preserves source data, scopes all imported private records to the selected account, validates relationships, and supports safe retry.
5. The current local-first application remains the supported runtime until the target is implemented and passes its migration, isolation, client, and release gates.
6. `/api/v1/...` is the documented API contract. Existing `/api/...` routes remain compatibility aliases until clients migrate and a breaking release removes them.
7. New product features are not created as empty packages. Each module is introduced with behavior, contracts, tests, and documentation.

## Required follow-up design

The first authentication slice has documented and tested the following choices:

- Argon2id password hashes; verified email; one-time expiring email-verification and password-reset tokens stored as hashes; minimum 12-character passwords up to 128 characters; and HMAC-keyed persistent rate limits.
- Opaque, hashed, revocable PostgreSQL sessions; Secure/HttpOnly/SameSite cookies for the dashboard and bearer tokens for the configured extension.
- SMTP with TLS for verification and password-reset messages.

Before any existing private endpoint or worker serves authenticated accounts, document and test:

- account ownership and cross-account constraints for every private resource;
- authorization and cross-account access denial for every private endpoint and background task;
- PostgreSQL connection-pool, backup, restore, and deployment settings;
- complete legacy import mapping and the cutover/rollback procedure.

Authentication endpoints alone do not enable multi-user access to the existing SQLite/libSQL/Turso API. PostgreSQL migrations remain explicit operator actions; startup never runs Alembic or imports legacy data.

## Consequences

- The PostgreSQL transition is a breaking, major-version migration.
- Existing local databases are not silently uploaded or modified.
- All private API and worker operations require an explicit authenticated owner context before multi-user exposure.
- SQLite/libSQL and Turso remain current-runtime concerns until a tested cutover is approved; no dual-write path is introduced.
- Tests must run against disposable PostgreSQL databases for migration and isolation guarantees, in addition to fast unit tests.
