# Database Schema

## Current SQLite/libSQL database

The supported application still uses the SQLite-compatible schema at [`apps/api/app/core/schema.sql`](../../apps/api/app/core/schema.sql), plus additive migration definitions in [`apps/api/app/infra/database.py`](../../apps/api/app/infra/database.py). It remains a single-user database with optional Turso synchronization. The current API continues to read and write this database; the PostgreSQL target does not alter it.

## PostgreSQL target foundation

The opt-in PostgreSQL schema is defined by the SQLAlchemy models in [`apps/api/app/infra/postgres/models.py`](../../apps/api/app/infra/postgres/models.py) and the immutable initial revision in [`apps/api/alembic/versions/0001_postgres_foundation.py`](../../apps/api/alembic/versions/0001_postgres_foundation.py). It is not created at API startup. Run Alembic explicitly against a PostgreSQL database using `POSTGRES_DATABASE_URL`.

| Table | Ownership and purpose |
| --- | --- |
| `accounts` | Opaque UUID ownership namespace; contains no authentication credentials |
| `jobs` | Account-owned job records, state, visibility flags, JSON metadata, and timestamps |
| `listings` | Account-owned postings, with a composite foreign key to the same account's job |
| `events` | Account-owned job history, optionally linked to a same-account listing |
| `documents` | Account-owned job documents and metadata |
| `blocked_companies` | Account-owned company/platform exclusions |

Every private resource carries an `account_id`. Composite foreign keys include that key when referencing a job or listing, preventing cross-account relationships even if application code supplies another account's identifier. The unique `(account_id, platform, platform_id)` listing key preserves the natural listing identity within one account. No account registration, authentication, user endpoints, or SQLite/Turso importer is implemented by this schema foundation.

Jobs use a UUID primary key and also expose `(account_id, id)` as a unique target for owner-scoped foreign keys. Listing IDs remain strings to accommodate legacy opaque identifiers during a later explicit import. Event and document IDs are PostgreSQL identity values. Timestamps use `timestamptz`; flexible record metadata uses `jsonb`.

### Indexes

- `jobs(account_id, updated_at DESC)` supports account-scoped recent-job views.
- `jobs(account_id, status, updated_at DESC)` supports status-filtered job lists.
- `listings(account_id, job_id)` supports per-job listing reads; the account/platform/platform-ID unique constraint supports natural-key lookup.
- `events(account_id, job_id, event)` supports event-kind checks, `(account_id, job_id, ts DESC)` supports history reads, and `(account_id, listing_id)` supports listing references.
- `documents(account_id, job_id, created_at DESC)` supports recent document reads.
- `blocked_companies(account_id, platform)` supports account-scoped platform filtering; the primary key enforces one entry per account/company/platform.

Add indexes only for a measured query pattern or an enforced relationship lookup. PostgreSQL migrations are forward-only; never edit a released revision or use a downgrade to remove data.
