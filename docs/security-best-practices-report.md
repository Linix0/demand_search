# Security Best Practices Report

## Executive summary

The current delivery is a loopback-only, single-user research workbench with a Mock evidence loop. Its strongest controls are the SSRF-gated manual fetcher, deterministic quote verification, program-owned evidence metadata, React output escaping, external-link validation, and CSV formula neutralization. The principal remaining risks are the absence of authentication and workspace authorization and the lack of a robots/terms preflight for real source collection. The current lockfile has no registry-reported npm advisories, but the audit must remain a CI gate. The system is not safe to expose to a LAN or the public internet in its current form.

Review date: 2026-10-22. Reviewed application scope: FastAPI API, Celery worker, React SPA, Nginx configuration, Docker Compose, source import/fetch path, scoring/evidence boundary, and exports. The Compose stack was subsequently started and verified on the same date; see `docs/runtime-verification.md`.

## Findings

### SEC-001: API has no authentication or workspace authorization

**Severity:** Medium in the documented local-only deployment; High if the port is exposed.

**Location:** `backend/app/api/deps.py:16`, `backend/app/api/v1/jobs.py:38`, `backend/app/api/v1/pain_points.py:37`, `backend/app/services/workspace.py:12`

**Evidence:** API dependencies provide only a database session and settings. No route verifies a user, API key, session, or resource ownership. `ensure_default_workspace()` selects the first workspace and all persisted records are reachable without a workspace predicate. A local process that can reach `127.0.0.1:8000` can create jobs, import URLs, verify pain points, merge records, and export data.

**Impact:** Any local process or user in the same OS trust boundary can read or mutate research data. Accidental LAN/public exposure would enable unauthenticated data tampering and export. Browser cross-origin reads are constrained by CORS, but CORS is not authorization.

**Fix:** Keep the service bound to loopback and document it as single-user. Before any network or multi-user release, add an identity provider, require authentication at the API boundary, and add `workspace_id` ownership checks in every repository query and mutation.

**Mitigation:** Compose ports now bind to `127.0.0.1`; production docs are disabled; CORS has no wildcard and no credentials. These reduce exposure but do not replace authentication.

**False-positive notes:** The absence is intentional for the local MVP according to `docs/architecture.md` and `AGENTS.md`. It becomes a real vulnerability only when the API is reachable by another trust domain.

### SEC-002: Online dependency audit completed and advisories remediated

**Severity:** Closed for the current lockfile; reopen on any new advisory or dependency change.

**Location:** `frontend/package.json:1`, `frontend/package-lock.json:1`

**Evidence:** Registry-backed `npm audit --json` found one moderate and two critical advisories in the `vitest` 3.2.7 chain (`@vitest/mocker` and `tinypool`). `vitest` was upgraded to 4.1.12, which supports Node 20 and the existing Vite 6 peer range, and `@testing-library/dom` 10.4.2 was declared explicitly because it is a required peer of `@testing-library/react`. The resulting audit reported 0 vulnerabilities across 528 dependencies. The rebuilt Docker web image ran `npm ci` and also reported 0 vulnerabilities.

**Impact:** The affected Vitest chain is development-only, but its file-read, mock-registration, and prototype-pollution advisories could compromise a maintainer machine or test process. The production bundle does not load Vitest.

**Fix:** Executed online, then reran frontend lint, typecheck, Vitest 4.1.12 (5 tests), production build, and the Docker web build. Keep `npm audit --json` as a CI gate because the zero result is point-in-time.

**Mitigation:** The production frontend is a static build, runtime code does not execute untrusted npm packages, and unused dependencies have been removed.

**False-positive notes:** Zero current advisories does not prove future safety. New advisories can affect an unchanged lockfile and require a fresh audit.

### SEC-003: Manual import has transport safety but no robots or terms preflight

**Severity:** Medium (compliance and source-policy risk).

**Location:** `backend/app/services/sources.py:72`, `backend/app/services/fetcher.py:97`, `frontend/src/features/sources/sources-page.tsx:1`

**Evidence:** `import_manual_url()` validates scheme, host, DNS, ports, redirects, content type, size, and timeout, then fetches immediately. It does not fetch or evaluate `robots.txt`, confirm provider terms, check authentication boundaries, or persist a per-source policy decision before retrieval. The UI correctly warns that a browser-openable page is not automatically approved for collection, but that warning is not an enforced control.

**Impact:** An operator could collect content that the site prohibits, creating legal/compliance exposure and violating the project source policy.

**Fix:** Add a source-policy preflight service that records terms URL, robots decision, access method, retention, and operator confirmation before real collection. Keep Mock and explicitly approved manual imports as the only default paths.

**Mitigation:** Compose and settings disable all real providers. Manual import is bounded to public text pages and does not bypass authentication, paywalls, or anti-bot controls.

**False-positive notes:** Manual import can be an allowed access method when the operator has confirmed the site policy. The gap is the absence of a durable preflight decision, not the existence of manual import itself.

### SEC-004: Retention timestamps exist but no deletion job enforces them

**Severity:** Medium.

**Location:** `backend/app/models/source.py:123`, `backend/app/services/sources.py:173`, `backend/app/services/pipeline.py:183`

**Evidence:** Sources receive `retention_until`, but no worker task or service deletes or anonymizes expired content. The default full-page retention is now disabled, which reduces exposure, but expired excerpts and metadata remain indefinitely.

**Impact:** Research data and personal identifiers can outlive the stated retention period and the operator's expectations.

**Fix:** Add a bounded retention job that finds expired sources, removes content fields, preserves required audit/evidence tombstones, and records the action. Test that evidence provenance remains understandable after content deletion.

**Mitigation:** Default excerpt-only storage limits the amount of retained untrusted content. Operators can delete the local database and exports manually.

**False-positive notes:** Retention deletion is a later-phase requirement and not yet claimed as implemented. It remains a privacy risk for a local workbench that runs for months.

### SEC-005: Expensive endpoints have no application-level rate limit or concurrency quota

**Severity:** Low for the loopback single-user deployment; Medium if exposed.

**Location:** `backend/app/api/v1/jobs.py:47`, `backend/app/api/v1/exports.py:20`, `backend/app/main.py:38`

**Evidence:** Demo job creation and exports are available without a rate limiter. `max_items` is bounded at 5,000, and job limits bound provider work, but repeated requests can still consume CPU, database I/O, and disk for downloads. Celery concurrency is bounded only by worker configuration.

**Impact:** A local malicious process or future multi-user caller can cause degraded availability or excessive resource consumption.

**Fix:** Add per-client rate limits and a global in-flight job quota at the API or reverse proxy. Keep export row and time limits explicit and audited.

**Mitigation:** The API is loopback-only, the frontend is a single operator, and export rows are capped.

**False-positive notes:** A local trust boundary makes noisy local DoS lower priority; the ranking changes immediately if the API is exposed.

### SEC-006: CSP permits inline styles

**Severity:** Low.

**Location:** `frontend/nginx.conf:10`

**Evidence:** The policy contains `style-src 'self' 'unsafe-inline'`. Scripts are still restricted to `'self'`, there is no `unsafe-eval`, and the application has no raw HTML sink.

**Impact:** An HTML injection that reaches a style attribute could alter presentation or facilitate limited UI redress. It cannot directly execute script under the current script policy.

**Fix:** Verify the production build has no required inline style, then remove `'unsafe-inline'` from `style-src`. If a component library requires it, document the exact exception and keep it narrowly scoped.

**Mitigation:** React escapes all rendered strings; `EvidenceLink` rejects non-HTTP(S) URLs; there is no `dangerouslySetInnerHTML`.

**False-positive notes:** Tailwind emits a stylesheet, so inline styles may not be necessary. Confirm against the built Nginx deployment before changing the policy.

### SEC-007: Docker stack runtime verified on 2026-10-22

**Severity:** Closed for the Phase 1 loopback-only stack; production hardening remains separate.

**Location:** `docker-compose.yml:1`, `backend/Dockerfile:1`, `frontend/Dockerfile:1`

**Evidence:** `docker compose up --build -d` completed, and `docker compose ps` reported PostgreSQL, Redis, API, and web `healthy` with the worker `running`. API logs showed the initial Alembic migration to `ae1ad88ecfe8`. The worker connected to Redis and received `research_jobs.execute`. The API and worker ran as `uid=100(app)`, and Nginx served `/`, `/health`, and `/openapi.json` over loopback with the configured security headers.

**Impact:** No runtime verification failure was observed. The offline demo completed with 30 persisted sources, 30 pain points, 30 evidence records, and 90 separate score records; all three export formats and the SSRF rejection path worked through Nginx.

**Fix:** Executed. Health, migrations, worker connectivity, Nginx proxy behavior, headers, non-root backend execution, exports, browser flow, and SSRF rejection are recorded in `docs/runtime-verification.md`.

**Mitigation:** Published ports remain bound to `127.0.0.1`; authentication and TLS are still required before any larger network exposure.

**False-positive notes:** This closes the unstarted-container verification gap, not the remaining authentication, retention, provider-policy, or production-hardening gaps.

## Controls that passed review

- SSRF validation rejects non-HTTP(S) schemes, credentials, disallowed ports, local hostnames, non-public DNS answers, redirect escape, and IP literals even when DNS pre-resolution is skipped (`backend/app/services/url_safety.py`, `backend/tests/unit/test_url_safety.py`).
- The fetcher disables redirects by default, revalidates every hop, fails closed when the connected peer IP is unavailable, caps content type, bytes, redirects, and timeouts, and never executes page content (`backend/app/services/fetcher.py`).
- Source text is treated as data. Model candidates use `extra="forbid"`, program code owns source IDs and URLs, and quotes are verified deterministically against persisted text (`backend/app/services/pipeline.py`, `backend/app/services/evidence.py`).
- Human verification requires persisted evidence, a legal HTTP(S) source URL, and at least one exact or normalized quote match (`backend/app/services/pain_points.py`).
- The SPA has no raw HTML sink, rejects non-HTTP(S) evidence links, and opens external links with `noopener noreferrer` and a no-referrer policy (`frontend/src/components/evidence-link.tsx`).
- CSV cells beginning with formula prefixes are neutralized, and exports use parameterized ORM queries and fixed field names (`backend/app/services/exporting.py`, `backend/app/services/exports.py`).
- Production rejects placeholder or short `APP_SECRET_KEY` values (`backend/app/core/config.py`), and Compose ports bind to loopback.
- The Docker stack builds and runs with healthy dependencies, successful migrations, a consuming Celery worker, a non-root API/worker user, a working Nginx proxy, and restrictive security headers.
- Unused table, chart, and date dependencies were removed, reducing the frontend dependency surface from the initial install.
- Request IDs, safe error envelopes, redaction of sensitive log keys, no debug docs in production, Trusted Host validation, and restrictive CORS are present.

## Verification executed

```text
backend full suite: 65 passed
backend ruff check / ruff format --check / mypy: passed
frontend lint / typecheck / Vitest 4.1.12 / production build: passed after dependency remediation (5 tests)
online npm audit: 0 vulnerabilities across 528 dependencies; Docker npm ci also reported 0
offline smoke: 30 sources, 30 pain points, 30 persisted evidence records, separate scores, CSV/JSON/Markdown exports passed
OpenAPI snapshot check: passed
Compose configuration parse: passed
browser flow: demo job, 30-row workbench, evidence detail, three score panels, SSRF error, CSV download: passed
Compose runtime: five services up; migrations, worker consumption, Nginx proxy, headers, 30-source demo, exports, and SSRF rejection passed
```

The registry-backed audit is current for this lockfile, but it remains a recurring CI gate rather than a permanent guarantee.
