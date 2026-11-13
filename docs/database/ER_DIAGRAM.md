# Entity Relationship Diagram

The diagram describes the initial PostgreSQL target schema. Every relationship from a private record to a job or listing includes the owner key. The current SQLite/libSQL runtime remains separate.

```text
accounts
  ├──< jobs
  │     ├──< listings
  │     │      └──< events (optional listing reference)
  │     ├──< events
  │     └──< documents
  └──< blocked_companies
```

`jobs.id` is globally unique, with an additional unique `(account_id, id)` key for composite foreign keys. `listings` is keyed by `(account_id, id)` and also has a unique `(account_id, platform, platform_id)` natural key. Events and documents retain identity IDs and reference their owning job through `(account_id, job_id)`.

`accounts.id` is only an ownership namespace. Credential storage, authentication, account lifecycle, and a production importer remain separate design and implementation work. The initial relationships do not cascade deletes, so removing an account, job, or listing cannot silently erase dependent records.
