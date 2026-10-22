# Technical Selection

## Context

The repository had no existing application stack. The requirements favor a stack that Codex can generate, test, and maintain, while keeping one local developer in control. The selection therefore optimizes for evidence integrity, deterministic processing, operational simplicity, offline demos, and testability rather than maximum scale.

The target is a modular monolith deployed with Docker Compose: FastAPI API, Celery worker, PostgreSQL, Redis, and a React single-page application. Real external providers are optional adapters; Mock providers are mandatory.

## Selected baseline

Version ranges below are initial compatibility targets. Exact versions must be locked by `pyproject`/lockfile and `package-lock.json` when the runtime scaffold is created. Do not silently float major versions.

| Area | Selection | Target | Reason |
|---|---|---|---|
| Backend language | Python | 3.12.x | Matches the recommendation, mature typing, strong web/data ecosystem |
| API | FastAPI | 0.115+ | Native OpenAPI, Pydantic integration, async HTTP boundary, easy TestClient |
| Validation | Pydantic v2 | 2.10+ | Strict structured-output validation and settings support |
| ORM | SQLAlchemy | 2.0.x | Typed mappings, transactions, predictable SQL, broad PostgreSQL support |
| Migration | Alembic | 1.14+ | Schema-first delivery and repeatable upgrade/downgrade paths |
| Database | PostgreSQL | 16 | JSONB, constraints, indexes, mature transactional behavior |
| Database driver | psycopg | 3.2+ | Current PostgreSQL driver, compatible with SQLAlchemy URL format |
| Queue | Celery | 5.4+ | Mature retries, task routing, worker control, broad operational knowledge |
| Broker/result | Redis | 7.x | Lightweight local broker; not a business-data store |
| HTTP client | httpx | 0.28+ | Timeouts, redirects, connection pooling, testable transports |
| Retry policy | tenacity | 9+ | Bounded retries with exponential backoff and jitter; respects Retry-After via wrapper |
| Rate limiting | limits | 4+ | Provider quotas using Redis-backed token buckets |
| HTML extraction | trafilatura + BeautifulSoup | Current 2.x / 4.x | Readable text extraction with a narrow fallback parser |
| Logging | structlog | 24+ | Structured, redactable server logs |
| Settings | pydantic-settings | 2.x | Typed environment configuration |
| Frontend | React + TypeScript | React 19, TS 5.8+ | Matches the specification; strong ecosystem and Codex support |
| Bundler | Vite | 6.4.x in Phase 1 | Node 20.15 is the available runtime; Vite 7 requires a newer Node patch level |
| Server state | TanStack Query | 5.x | Cache, request states, invalidation; avoids ad-hoc global stores |
| Routing | React Router | 7.x | Standard SPA routing with nested layouts |
| Forms | React Hook Form + Zod | Current | Low-rerender forms with shared validation semantics |
| UI primitives | Repository-local shadcn-style primitives | Phase 1 | One Tailwind component system; Radix is added only when a component needs its interaction primitives |
| CSS | Tailwind CSS | 4.x | Consistent tokens and compact component styling |
| Tables | Semantic HTML tables | Phase 1 | Server pagination is the source of truth; no unused headless table dependency |
| Charts | CSS score meters | Phase 1 | Avoids a chart dependency until comparison views need one |
| API typing | openapi-typescript + openapi-fetch | Current | Generate client types from OpenAPI to prevent contract drift |
| Frontend tests | Vitest + Testing Library + MSW | Current | Fast unit/component tests and deterministic network mocks |
| E2E | Playwright | Current 1.x | Real browser validation; installed Codex skill supports CLI workflows |
| Backend tests | pytest + httpx TestClient | Current | Unit, schema, and API integration tests |
| Python quality | Ruff + mypy | Current | Formatting, linting, static type checks |
| Frontend quality | ESLint + Prettier + `tsc --noEmit` | Current | Flat-config linting, formatting, strict type check |
| Deployment | Docker Compose | v2 | Single-command local stack; no Kubernetes requirement |
| LLM | OpenAI-compatible provider + Mock | Configurable | Vendor-neutral, local/cloud endpoint support, offline default |
| Embedding | Optional provider | Configurable | Feature remains functional when embeddings are absent |

## Architecture decisions

### ADR-001: Modular monolith first

Status: accepted.

Use one backend deployable with explicit `api`, `services`, `repositories`, `models`, `providers`, and `tasks` packages. Celery workers import the same domain services but have a separate process. This keeps transactions and tests simple. Microservices are rejected because provider isolation already comes from interfaces, while distributed consistency would add avoidable work.

Revisit when independent scaling, security isolation, or team ownership creates a concrete constraint.

### ADR-002: Synchronous SQLAlchemy sessions for the MVP

Status: accepted.

Use synchronous SQLAlchemy 2.x sessions and psycopg. FastAPI may run synchronous route handlers in its worker pool; Celery tasks remain synchronous. This reduces session-leak, greenlet, and async/driver complexity while leaving the HTTP boundary capable of async provider calls where beneficial.

Revisit after profiling shows database waits dominate throughput or external async integrations make the sync boundary costly. Do not mix async and sync sessions in one request path.

### ADR-003: Celery with Redis, durable state in PostgreSQL

Status: accepted.

Celery handles research jobs, fetch/extract/score stages, retries, and worker lifecycle. Redis is the broker and optional result transport. `research_jobs`, `research_job_logs`, `source_items`, `pain_points`, and `provider_usage_records` are the durable truth in PostgreSQL. A worker restart must be able to reconstruct progress from the database.

On Windows, run Celery through the Linux Docker image. Native Windows worker execution is not a supported production path.
Job lifecycle: start, resume, and retry are explicit conditional transitions. A job is claimed by the worker only when it is `queued`; the claim is one atomic `queued -> running` update. Celery renders a stable task ID for each durable job, and duplicate deliveries are harmless because they see a non-`queued` state and return. The pipeline checks that the job is still `running` before finalization and failure handling, so an operator pause or cancel is not overwritten. Orphaned-`running` recovery remains future work.

### ADR-004: Provider adapters at every external boundary

Status: accepted.

Define `SearchProvider`, `SourceProvider`, `LLMProvider`, `EmbeddingProvider`, and `Exporter` contracts. Business services accept interfaces, not SDK clients. Providers declare capabilities, limits, credentials references, and health state. Mock implementations are first-class and cover the full pipeline.

This is required for source-policy compliance and prevents vendor lock-in.

### ADR-005: Deterministic pipeline with LLM as an untrusted assistant

Status: accepted.

The LLM may suggest queries, extract candidate statements, propose categories, summarize, and explain scores. It cannot own URLs, IDs, publication times, source counts, payment evidence, final status, or score arithmetic. Structured output is parsed with strict Pydantic models and rejected on schema or business-rule violations.

No LangGraph or autonomous agent loop in the MVP. The stage pipeline is explicit, resumable, and observable.

### ADR-006: Rule-based similarity with optional embeddings

Status: accepted.

Start with URL/external-ID/content-hash deduplication and normalized text similarity. PostgreSQL text-search/trigram capabilities may support candidate pairing. Embeddings are optional and only used to propose strong duplicates or clusters; no automatic deletion occurs above the configured threshold. The system must remain functional with `EMBEDDING_PROVIDER=mock` or disabled.

### ADR-007: React SPA with server-owned state

Status: accepted.

Use React, TypeScript, Vite, TanStack Query, React Router, React Hook Form, and Zod. The API remains the source of truth for pagination, filtering, status, and score history. Local client stores are limited to UI state. Generate API types from OpenAPI instead of hand-maintaining duplicate response interfaces.

### ADR-008: One UI system and evidence-first layouts

Status: accepted.

Use Tailwind CSS with shadcn/ui/Radix primitives and Lucide icons. The pain-point workbench uses a filter rail, data table, and evidence detail panel. Source links render from persisted URLs only. Tables default to 20 rows and support 50/100; no infinite scroll that loads the full pool.

### ADR-009: Mock-first, provider-optional runtime

Status: accepted.

`mock` is the default for search, source, LLM, and embedding. The demo path must run without paid credentials and must use fixed, versioned fixtures. Real provider tests are opt-in smoke tests, not required for normal CI.

### ADR-010: Testing pyramid and security regressions

Status: accepted.

Backend:

- Unit: URL normalization, SSRF, quote matching, scoring, dedupe, state transitions, export sanitization, schema rejection.
- Integration: offline job from creation through export; provider timeout/401/429; budget pause/resume; partial completion.
- API: pagination, filters, authorization boundary assumptions, response schemas.

Frontend:

- Component: forms, loading/empty/error states, evidence rendering, review actions.
- E2E: create job, inspect evidence, verify/reject, export; use Playwright when a browser flow is part of acceptance.

### ADR-011: Codex skills are supporting capabilities

Status: accepted.

Installed from `openai/skills` into `$CODEX_HOME/skills`:

| Skill | Use in this project |
|---|---|
| `playwright` | CLI-driven real-browser checks and UI-flow debugging; not a replacement for committed E2E tests |
| `security-best-practices` | Secure-by-default Python/TypeScript implementation and focused security reviews |
| `security-threat-model` | Repository-grounded threat model for sources, fetches, prompts, workers, exports, and secrets |

Skills are invoked only when their stated trigger matches. They do not override repository rules or product requirements.

### ADR-012: Knowledge graph is a maintained artifact

Status: accepted.

`docs/knowledge-graph/project-graph.json` is the canonical maintenance graph. It stores nodes, typed edges, and append-only events. A deterministic renderer produces Mermaid, and a validator enforces referential integrity and required coverage. Every material change must update the graph and pass validation.

### ADR-013: Minimal frontend dependency surface and local UI primitives

Status: accepted for Phase 1.

The workbench uses React function components, TanStack Query, React Router, React Hook Form, Zod, Tailwind CSS, and small repository-local primitives modeled on shadcn/ui. The current components do not require Radix runtime packages, `components.json`, TanStack Table, Recharts, or `date-fns`; those unused dependencies were removed to reduce supply-chain and build surface. Add a dependency only when a concrete component needs it, and record the purpose and security implication in the graph.

The Phase 1 lockfile installs React 19.3, TypeScript 5.9, Vite 6.4.5, Vitest 4.1.12, Tailwind 4.3, TanStack Query 5.104, and React Router 7.18. Vitest 4.1.12 preserves Node 20 support while remediating the current mock/pool advisories; `@testing-library/dom` is declared explicitly as the Testing Library peer. Vite 7 is deferred until the Node runtime is upgraded and the full browser/quality suite is rerun.

## Proposed dependency sets

### Backend runtime

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy
alembic
psycopg[binary]
celery[redis]
redis
httpx
tenacity
limits
trafilatura
beautifulsoup4
lxml
structlog
python-dateutil
```

`openai` SDK is not required for the initial OpenAI-compatible adapter; plain `httpx` can target a configurable `/chat/completions` endpoint. Add a vendor SDK only if it provides a concrete capability that the HTTP adapter cannot cover safely.

### Backend development

```text
pytest
pytest-cov
respx
freezegun
ruff
mypy
types-python-dateutil
```

### Frontend runtime

```text
react
react-dom
react-router
@tanstack/react-query
react-hook-form
zod
@hookform/resolvers
tailwindcss
@tailwindcss/vite
class-variance-authority
clsx
tailwind-merge
lucide-react
openapi-fetch
```

### Frontend development

```text
typescript
vite
@vitejs/plugin-react
eslint
@eslint/js
typescript-eslint
eslint-plugin-react-hooks
eslint-plugin-jsx-a11y
prettier
vitest
jsdom
@testing-library/react
@testing-library/user-event
@testing-library/jest-dom
msw
openapi-typescript
playwright
```

Use npm for the initial frontend to match the available Node/npm environment. Revisit a workspace/package-manager migration only if the repository gains multiple packages.

## Rejected alternatives

| Alternative | Reason rejected for the MVP |
|---|---|
| Django + DRF | Strong framework, but FastAPI's schema/OpenAPI and service-oriented pipeline are a closer fit and lighter for this single-user API |
| Node/NestJS backend | Splits domain logic across two languages; Python is stronger for extraction, scoring fixtures, and data tooling |
| Microservices | Adds distributed transactions, deployment, and observability cost without a current scaling need |
| Multiple queue systems | Explicitly prohibited by the specification; one Celery path is easier to recover and test |
| LangGraph as a mandatory dependency | The first workflow is deterministic; graph orchestration would obscure state and complicate recovery |
| MongoDB as primary store | Relational evidence, score history, audit, and foreign-key integrity are central requirements |
| Vector database in Phase 1 | Optional embeddings plus PostgreSQL can cover initial clustering; a separate vector store is premature |
| Redux as default state | Server state dominates; TanStack Query removes most global state needs |
| Multiple component libraries | Creates design and accessibility inconsistency |
| Direct vendor LLM SDKs in services | Couples business logic to a vendor and bypasses the adapter boundary |
| Real crawling enabled by default | Conflicts with source policy, compliance, and offline-demo requirements |

## Re-evaluation triggers

- API p95 exceeds target after indexing and query tuning.
- A provider requires a protocol that the HTTP adapter cannot safely implement.
- Celery recovery or scheduling becomes a demonstrated reliability bottleneck.
- Embedding cost/latency is acceptable and improves measured duplicate recall without harming precision.
- Multiple frontend packages or deployment targets make the current npm/SPA structure costly.
- Team collaboration introduces authenticated multi-workspace access, at which point auth/authorization and audit scope must be redesigned first.

## Operational constraints

- Dependencies are installed and locked; add a package only when a concrete module needs it.
- Do not add a package without recording its purpose, boundary, and security implication in the graph.
- Do not enable a real source provider until its terms URL, credential path, capabilities, and rate-limit policy are persisted.
- Do not expose keys or provider response headers through API responses or logs.
- Do not treat an optional provider as required for local startup or CI.
