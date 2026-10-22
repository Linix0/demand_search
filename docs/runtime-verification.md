# Docker Runtime Verification

Verification date: 2026-10-22, Asia/Shanghai. Scope: the Phase 1 loopback-only Docker Compose stack with Mock providers and no external API keys.

## Environment note

The default Docker client configuration at `C:\Users\Administrator\.docker\config.json` was unreadable in this environment, so every Docker command used the repository-local `.docker` directory:

```powershell
$env:DOCKER_CONFIG=(Resolve-Path .docker).Path
```

Docker Hub was unreachable from this host. The required base images were pulled from the configured mirror and retagged to the canonical names used by Compose; no Compose or Dockerfile change was required for the product.

## Commands and results

```powershell
docker compose up --build -d
docker compose ps -a
```

Result: the API and web images built successfully. PostgreSQL, Redis, API, and web reported `healthy`; the Celery worker reported `running`. Published ports were `127.0.0.1:8000` for the API and `127.0.0.1:8080` for the web proxy.

API startup log:

```text
INFO [alembic.runtime.migration] Running upgrade -> ae1ad88ecfe8, initial schema
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

Endpoint checks from the host:

```text
GET http://127.0.0.1:8000/health       -> 200, database ok, redis ok
GET http://127.0.0.1:8080/             -> 200, 569-byte SPA shell
GET http://127.0.0.1:8080/health       -> 200, database ok, redis ok
GET http://127.0.0.1:8080/openapi.json -> 200, 44,625 bytes
```

Nginx returned `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and the configured Content-Security-Policy.

Container identity checks:

```text
api:    uid=100(app) gid=101(app)
worker: uid=100(app) gid=101(app)
web:    nginx master runs as root, as expected for the stock image
```

Celery connected to `redis://redis:6379/0`, subscribed to the `celery` queue, and received `research_jobs.execute` when the demo was submitted.

## Offline evidence loop

The demo was created through the Nginx origin:

```powershell
POST http://127.0.0.1:8080/api/v1/research-jobs/demo
```

The resulting job completed at 100% with:

```text
discovered_source_count = 30
extracted_pain_point_count = 30
verified_evidence_count = 20
```

PostgreSQL contained 30 `source_items`, 30 `pain_points`, 30 `pain_point_evidences`, 90 `pain_point_scores`, and 3 `research_job_logs`; the Alembic revision was `ae1ad88ecfe8`.

Every listed pain point had at least one persisted evidence record. Evidence retained an HTTP(S) URL such as `https://example.com/mock/.../issues/101`, the Mock Search source name, and separate evidence, commercial, and coverage scores.

Exports through Nginx:

```text
CSV      -> 200, 30 rows, 26,775 bytes
JSON     -> 200, schema_version 1.0, 30 items
Markdown -> 200, 89,345 bytes
```

SSRF guard:

```text
POST /api/v1/source-items/import-url {"url":"http://127.0.0.1/private"}
-> 400 {"code":"SSRF_BLOCKED","details":{"reason":"NON_PUBLIC_ADDRESS"}}
```

## Browser verification

The installed `playwright` skill was used against `http://127.0.0.1:8080`:

- The overview showed the health status, 30 candidates, the completed demo job, and provider states.
- The pain-point workbench displayed server-paginated candidates with evidence, commercial, and coverage scores shown separately.
- The detail page displayed the evidence chain, the original Mock Search source link, quote text, and separate scores `73.0`, `53.0`, and `21.0`.
- The export page generated and downloaded a 26,775-byte CSV through the browser.

A local screenshot of the verified export page is stored at `output/playwright/docker-verified-exports.png` and is intentionally ignored by Git.

## Residual boundaries

This verification covers the Phase 1 local, single-user, Mock-provider stack. It does not verify real provider access, robots/terms preflight, authentication, workspace authorization, retention deletion, semantic clustering, production TLS, or public deployment hardening.

## Follow-up dependency verification

The online `npm audit --json` run was repeated after the Docker checks. It initially reported one moderate and two critical advisories in the Vitest 3.2.7 dependency chain. The frontend was upgraded to Vitest 4.1.12, which supports Node 20 and the existing Vite 6 peer range, and `@testing-library/dom` 10.4.2 was declared explicitly. The final audit reported 0 vulnerabilities across 528 dependencies; the rebuilt Docker web image ran `npm ci` and also reported 0. Frontend lint, typecheck, five Vitest tests, and the production build passed after the upgrade.
