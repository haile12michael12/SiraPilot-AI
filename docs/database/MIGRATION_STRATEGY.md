# Migration Strategy

## Current persistence model

The released application uses SQLite/libSQL and may optionally synchronize through Turso. Its schema and append-only migration ledger are owned by `apps/api/app/core/schema.sql` and `apps/api/app/infra/database.py`. The existing migration compatibility rules in [Development](../DEVELOPMENT.md#database-migration-compatibility) apply to current installations.

## Target persistence model

The approved multi-user target uses PostgreSQL as its system of record and Alembic for schema migrations. The initial isolated schema, SQLAlchemy session/transaction layer, and account-scoped job repository are implemented in `apps/api/app/infra/postgres`; the initial revision is `apps/api/alembic/versions/0001_postgres_foundation.py`. This is a major-version, deployment-level change; SQLite/libSQL migration keys are not PostgreSQL migrations and must not be replayed as if they were.

The initial PostgreSQL schema contains an opaque account ownership key and account-scoped jobs, listings, events, documents, and blocked companies. It deliberately contains no credentials and is not connected to the current API. Before any endpoint serves multiple users:

1. Define the complete PostgreSQL schema, account ownership model, constraints, indexes, and transaction boundaries.
2. Extend the Alembic schema and tests against PostgreSQL as new feature data is implemented. SQLite-only tests are not sufficient evidence for PostgreSQL behavior.
3. Ensure every private row and relationship is owner-scoped in repositories and enforced by database constraints where practical.
4. Add account authentication and authorization tests, including cross-user access denial for every resource family and background task.
5. Add an explicit legacy importer and a documented cutover procedure.

## Legacy-data import

Import is an explicit operator action, not an automatic startup migration. It reads a verified SQLite snapshot or a separately created Turso export, assigns every imported record to the selected account, and writes to PostgreSQL transactionally.

The importer must:

- leave the source database unchanged;
- refuse an unverified or malformed source and preserve the original error;
- validate row counts, relationships, and private-data ownership before reporting success;
- use a stable import identity so a retry cannot duplicate records;
- produce a value-free report and never log job, email, document, or credential contents;
- require a verified source backup and a destination backup/restore procedure before cutover.

No live user database, private-overlay file, environment file, or private fixture may be used as a migration test fixture. Tests use synthetic data and disposable databases.

## Cutover and rollback

The API remains on the existing SQLite/libSQL runtime until PostgreSQL schema, authentication, import, and client changes pass the full test and release gates. Cutover requires a major version, a tested one-time import, an explicit backup, and a clear point after which writes are directed only to PostgreSQL.

The initial Alembic revision only creates tables and indexes and refuses to run in a schema with existing tables. Migrations are forward-only; do not use `alembic downgrade` as a rollback or run Alembic against the SQLite/Turso database. Take a verified PostgreSQL backup before each production upgrade. The app's SQLite backup/restore commands do not back up or restore PostgreSQL.

Do not attempt bidirectional writes or silent dual-write between SQLite/Turso and PostgreSQL. If cutover validation fails, restore service from the preserved source backup and retry the import into a clean destination; never merge partially imported state by guessing.

Removal of the SQLite/Turso runtime is a later release decision, after users have a supported import path and rollback window. Until then, current installations retain their existing behavior.
