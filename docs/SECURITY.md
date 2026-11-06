# Security

## Phase 0 controls

- Secrets and service URLs are supplied through environment variables.
  `.env.example` contains conspicuously local-only values and must never be
  treated as deployment configuration.
- `.env` files, virtual environments, build output, and test artifacts are
  ignored by Git.
- Production settings reject the sample development secret. Use a
  high-entropy secret manager value of at least 32 characters.
- CORS allows only configured origins; wildcard origins are rejected.
- API failures return generic internal-error messages. Unexpected exceptions
  are logged with request path and method.
- PostgreSQL and Redis are not exposed through the application container
  network; Compose's PostgreSQL development port is intended for local use.
- Frontend assets do not contain database credentials, Redis URLs, or the
  backend signing secret.

## Before a shared deployment

- Replace all local credentials and restrict database/network access.
- Use TLS, a production secret manager, backups, and monitored log retention.
- Configure exact trusted CORS origins and review proxy/header settings.
- Add authentication, authorization, rate limits, and security tests before
  exposing user-specific or write-capable APIs.
- Review every integration's OAuth scopes, token storage, consent, revocation,
  and data retention before enabling it.

Phase 0 is a development foundation, not a production security certification.
