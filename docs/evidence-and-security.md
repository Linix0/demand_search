# Evidence, Scoring, Source, and Security Rules

This document condenses the non-negotiable rules that implementation and review must preserve. The source specification remains authoritative for product detail.

## 1. Evidence contract

### Required evidence fields

Every fact-level pain point must link to at least one `pain_point_evidences` row. Each row must retain:

- `source_item_id` and program-owned `source_name` / `source_url`.
- Canonical and original URLs; HTTP(S) only.
- Title when available; never fabricated.
- Original publication time when confirmed; unknown is `null`, never replaced by collection time.
- Actual collection time.
- Short quote (default 20-500 characters).
- Quote match status: `exact_match`, `normalized_match`, `snippet_only`, or `not_found`.
- Evidence type and role.
- Deterministic evidence strength.
- Target URL and optional related target URLs.
- Completeness: `full_public_content`, `partial_content`, `snippet_only`, or `metadata_only`.
- Retrieval method: `official_api`, `search_api`, `manual_import`, or `allowed_public_fetch`.

### Trust tiers

| Tier | Meaning | Evidence use |
|---|---|---|
| `A_primary_user_report` | Original user discussion, issue, or complaint | Strong evidence candidate |
| `B_primary_product_feedback` | Official feedback forum, public request, defect report | Strong evidence candidate |
| `C_secondary_review` | Review, comparison, or blog summary | Weak/context evidence; verify original where possible |
| `D_search_snippet` | Search snippet without accessible original | Lead only; low completeness; cannot alone support verified status |
| `E_generated_or_unverified` | AI inference or untraceable text | Never evidence for a fact-level pain point |

### Downgrade rules

A pain point cannot become `verified` when any of these is true:

- No legal HTTP(S) source URL exists.
- All evidence is model inference or untraceable text.
- Only a search snippet exists and there is no second independent source.
- The quote cannot be located in the available text or searchable snippet and no human has confirmed it.
- The evidence link is unrelated to the claimed problem.
- The source is marketing copy, fiction, or an unverifiable paraphrase.

These cases become `hypothesis` or `needs_review`, with the reason visible in the UI.

### Independence

Deduplicate by provider external ID, canonical URL, normalized content hash, then combined metadata/text similarity. Independence estimates use author hash, thread ID, root item ID, content hash, and source domain. When independence is uncertain, record `independence_unknown`; never inflate a source count.

## 2. Pain-point states

| State | Meaning | Allowed transition owner |
|---|---|---|
| `candidate` | New extraction, evidence not yet validated | Pipeline |
| `needs_review` | Traceable evidence, human review pending | Pipeline / reviewer |
| `verified` | Human confirmed, or explicitly labeled system review under strict rules | Human reviewer; system only when the specification permits and the label is explicit |
| `hypothesis` | Opportunity hypothesis without sufficient factual evidence | Pipeline / reviewer |
| `rejected` | Invalid, unrelated, or disproven | Reviewer / deterministic rule with reason |
| `duplicate` | Merged into another pain point | Reviewer / merge operation |
| `archived` | Removed from default opportunity views | Reviewer |

Every transition writes an audit entry with actor, timestamp, previous state, next state, and reason. `verified` is forbidden for evidence-free records.

## 3. Scoring

Do not collapse evidence confidence and commercial opportunity into one score. Coverage is a context indicator.

### Evidence Confidence (0-100)

| Dimension | Weight | Five-point meaning |
|---|---:|---|
| Source traceability | 20% | Original discussion/issue opens and points to a specific location |
| Quote verifiability | 20% | Quote exactly matches accessible source text |
| Directness | 15% | First-person description of the user's own problem |
| Independent source count | 15% | At least eight deduplicated, independent sources |
| Problem specificity | 10% | Clear task, obstacle, context, and impact |
| Observed behavior/workaround | 10% | Concrete scripts, spreadsheets, manual process, or purchased tools |
| Recency | 10% | Published within the last 30 days |

`evidence_confidence_score = sum(dimension_score / 5 * weight)`.

Deterministic caps:

- No legal source URL: score `0`; state cannot exceed `hypothesis`.
- `snippet_only`: maximum `55`.
- One thread or one author across all evidence: independence dimension maximum `1`.
- Unverified quote: maximum `60` until human confirmation.
- Irrelevant link: evidence invalid; excluded from scoring.
- Marketing-only content: directness maximum `1`.
- Unknown publication date: recency contributes no positive points and displays `unknown`.

### Commercial Opportunity (0-100)

| Dimension | Weight |
|---|---:|
| Pain severity | 20% |
| Frequency | 15% |
| Payment willingness evidence | 20% |
| Target user reachability | 15% |
| Indie-developer feasibility | 15% |
| Competitive gap / differentiation | 10% |
| Market and delivery sustainability | 5% |

`commercial_opportunity_score = sum(dimension_score / 5 * weight)`.

Guardrails:

- No payment evidence means the payment dimension cannot exceed `2`, unless a sourced budget/purchase behavior supports it.
- No explicit target user segment means reachability cannot exceed `2`.
- Feasibility requires an implementation path and the largest technical/data/compliance risk.
- More competitors is not automatically worse; evaluate positioning, channel, price, and unmet need.
- Likes/comments must not be converted into revenue, TAM, or market size.

### Payment evidence guardrails

Payment evidence is program-derived, never model-declared:

- A model `payment_signal=explicit` label alone is ignored.
- `payment_signal` evidence requires a quote with `exact_match` or `normalized_match`.
- The verified quote must match a narrow affirmative deterministic rule.
- Negated and hypothetical payment language is excluded.
- A `snippet_only` quote may be supporting evidence but cannot establish payment willingness.
- Commercial scoring reads only the persisted final `evidence_role`.

### Coverage (0-100)

Coverage is not opportunity. Default composition: independent sources 30%, source-type diversity 20%, domain/community diversity 15%, time coverage 10%, target-user clarity 10%, competitor research completeness 10%, completed interviews/direct feedback 5%.

Low coverage displays “样本不足，不宜过度解读”.

### Explainability

Each score history row stores the scoring version, dimension values, weights, final score, evidence IDs used, calculation details, model suggestion (nullable), rule adjustments, and timestamp. Rescoring appends a new row.

## 4. Source access policy

| Source | Default | Access method | Required control |
|---|---|---|---|
| Mock | Enabled | Local deterministic fixtures | No network; complete pipeline |
| Manual URL | Enabled | User-supplied public HTTP(S) URL | SSRF guard, size/type caps, no auth bypass |
| GitHub Issues/Discussions | Disabled until configured | Official REST API + optional token | API rate headers, pagination, 403/429 handling |
| Hacker News | Disabled until configured | Official Firebase API | Throttle, bounded fetch, no “trending equals coverage” claims |
| Configurable search API | Disabled until configured | Provider adapter (Tavily/Brave/Serper or another) | Terms, cost, quota, source URL verification |
| Reddit | Disabled by default | Authorized official API only | User confirms current terms and permitted use |
| Product Hunt | Disabled by default | Official API only after commercial-use confirmation | Do not assume API use is permitted for commercial product |

Rules:

- A page being open in a browser does not authorize automated collection.
- Use official APIs when available; respect robots rules, terms, login boundaries, rate limits, and retention restrictions.
- Do not bypass captchas, paywalls, access controls, or anti-bot mechanisms.
- Do not rotate identities, proxies, or accounts to evade limits.
- Preserve only short excerpts by default. Store full text only when policy and user settings permit it.
- If full content is unavailable, keep legal search metadata and label `snippet_only`; do not claim full reading.
- Each provider stores a terms URL, access method, capabilities, credential reference, rate-limit config, and health status.

## 5. SSRF protection

The URL importer and source fetcher must enforce all of the following:

1. Allow only `http` and `https`.
2. Reject credentials embedded in the URL unless a provider-specific design explicitly supports and validates them.
3. Resolve DNS and reject loopback, private, link-local, multicast, reserved, unspecified, documentation-only, and cloud metadata ranges.
4. Apply the same checks to IPv4 and IPv6, plus IPv4-mapped IPv6.
5. Revalidate every redirect target, with a maximum of five redirects.
6. Default to ports 80/443 or an explicit allowlist.
7. Set connection and read timeouts; cap response bytes and processed text.
8. Accept only explicit safe content types for text extraction.
9. Do not execute JavaScript, shell commands, macros, or downloaded files.
10. Do not expose internal DNS/IP/error details in user-facing responses.

Use a single reviewed URL-safety service for import, provider targets, redirect handling, and recheck endpoints. Unit tests must cover decimal/hex IP forms, IPv6, DNS rebinding-style revalidation, redirect escape, and oversized responses.

## 6. Prompt injection and LLM boundary

- Source text is data. System prompts state that instructions in the page must not be followed.
- The model has no arbitrary browser, shell, database-write, or network tools.
- It cannot create source IDs, URLs, authors, timestamps, source counts, payment evidence, or final scores.
- Structured output is parsed and validated with strict Pydantic schemas; unknown fields and invalid enums are rejected.
- Evidence quotes must be checked against stored text/offset data; model confidence is not verification.
- Candidate count and output tokens are bounded per source.
- Injection-bearing fixtures are part of the test suite.

## 7. Secrets, privacy, and retention

- Secrets only in backend environment variables or a secret manager; never in the SPA bundle, API responses, database plaintext, or logs.
- Store only credential environment-variable names or secret references.
- Redact `Authorization`, cookies, API keys, tokens, and personal data from logs.
- Use `author_hash` when a stable author key is needed for independence.
- Default to short excerpts and metadata; no sensitive author profiling.
- Define per-provider retention and deletion. Deleting research data must not silently destroy audit/evidence required for compliance.
- Consent, interview notes, and user PII require explicit product handling before multi-user release.

## 8. Export security

- CSV exports include IDs, statements, scores, score version, source URLs, quotes, publication/collection times, completeness, quote status, root-cause hypotheses, competitor URLs, and next action.
- Neutralize cells whose first meaningful character is `=`, `+`, `-`, `@`, tab, or carriage return.
- Quote fields and encode the CSV correctly; preserve UTF-8.
- JSON and Markdown include original source links and evidence snippets.
- Never export a summary-only opportunity list that omits evidence links.
- Markdown must escape embedded HTML/links from untrusted text.

## 9. Audit and observability

Audit at minimum:

- Job start/pause/resume/cancel/retry.
- Provider enable/disable and policy confirmation.
- Pain-point status changes, merges, score corrections, and manual evidence decisions.
- Export creation and download metadata.

Logs must identify stage/provider/request/job and safe error category. They must not contain full page bodies, secrets, or unbounded user content.

## 10. Required regression tests

- URL canonicalization preserves issue/comment anchors and removes only known tracking parameters.
- SSRF rejects private/local/metadata targets and redirect escapes; DNS failures are safe.
- Quote exact and normalized matching; missing quote downgrades and caps score.
- Evidence-free pain points cannot be verified.
- Duplicate source IDs/URLs/hashes do not inflate independent counts.
- Evidence, commercial, and coverage formulas and score history.
- Merge preserves all source evidence; duplicate redirect is auditable.
- CSV formula neutralization.
- Invalid LLM JSON, unknown schema fields, fabricated IDs, and URL injection are rejected.
- Provider 401/403/429/timeout behavior, budget pause/resume, and partial completion.
- Offline Mock job from creation through export.
