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
6. API file moves preserve existing `/api/...` URLs. Public API version-prefix changes are out of scope for structural refactoring.
7. New product features are not created as empty packages. Each module is introduced with behavior, contracts, tests, and documentation.

## Required follow-up design

Before implementing registration or private endpoints, document and test:

- password hashing, email verification, account recovery, registration abuse controls, and credential-reset policy;
- session/token transport and revocation, including browser-extension authentication;
- account ownership and cross-account constraints for every private resource;
- PostgreSQL transaction, connection-pool, backup, restore, and deployment settings;
- complete legacy import mapping and the cutover/rollback procedure.

## Consequences

- The PostgreSQL transition is a breaking, major-version migration.
- Existing local databases are not silently uploaded or modified.
- All private API and worker operations require an explicit authenticated owner context before multi-user exposure.
- SQLite/libSQL and Turso remain current-runtime concerns until a tested cutover is approved; no dual-write path is introduced.
- Tests must run against disposable PostgreSQL databases for migration and isolation guarantees, in addition to fast unit tests.
