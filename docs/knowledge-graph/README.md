# Project Knowledge Graph

## Purpose

The knowledge graph is the maintenance map for Industry Pain Radar. It connects the authoritative specification to engineering decisions, runtime components, persisted entities, security controls, delivery phases, acceptance criteria, installed skills, known risks, and the sequence of actions used to build the baseline.

It is not a generated architecture diagram that becomes stale silently. `project-graph.json` is a reviewed source artifact. Every material change must update it and append an event.

## Files

| Path | Role |
|---|---|
| `project-graph.json` | Canonical graph: metadata, sources, nodes, edges, events, open questions, and next actions |
| `project-graph.mmd` | Full deterministic Mermaid projection for tooling and graph exploration |
| `views/overview.mmd` | Goals, principles, decisions, and components |
| `views/requirements.mmd` | Specification requirements, principles, decisions, and controls |
| `views/data.mmd` | Data entities, components, and technology |
| `views/delivery.mmd` | Phases, acceptance criteria, skills, risks, and controls |

The `views/` directory is generated. Edit the JSON, then regenerate.

## Schema

### Node

```json
{
  "id": "R-005",
  "type": "requirement",
  "title": "Evidence model hard constraints",
  "summary": "Persist source IDs, URLs, quotes, dates, and completeness.",
  "status": "active",
  "source_refs": ["spec:§5"]
}
```

Rules:

- IDs match `^[A-Z][A-Z0-9]*-[0-9]{3}$`.
- IDs are globally unique and stable. Do not reuse a deleted ID.
- `type` comes from `conventions.node_types`.
- `title`, `summary`, and `status` are required non-empty strings.
- Artifact nodes with a repository `path` must point to an existing file.
- External artifacts use `status: "external"` and an HTTPS `url` instead of `path`.
- Skill nodes record `url` and `install_path`; the installed directory must exist.

### Edge

```json
{
  "from": "COMP-013",
  "to": "SEC-002",
  "type": "implements",
  "note": "Evidence validator verifies quotes."
}
```

Allowed relationship types:

`implements`, `depends_on`, `constrains`, `mitigates`, `validated_by`, `owned_by`, `precedes`, `uses`, `documents`, `produces`, `supersedes`, `supports`, `contains`, `evaluates`, `installed_from`, `applies_to`.

Do not create self-edges, duplicate `(from, to, type)` triples, or dangling references. `precedes` edges must remain acyclic.

### Event

```json
{
  "sequence": 11,
  "at": "2026-10-21T23:50:00+08:00",
  "action": "implement_phase_0_health_endpoint",
  "status": "completed",
  "summary": "Added the health endpoint and smoke test; list commands and results.",
  "artifacts": ["backend/app/main.py", "backend/tests/test_health.py"],
  "related_node_ids": ["COMP-002", "PHASE-000", "ACC-001"]
}
```

Event rules:

- Sequence is unique, positive, and strictly increasing.
- Timestamps are ISO-8601 with a timezone offset and must not go backwards.
- Status is `completed`, `pending`, or `blocked`.
- Artifact paths must exist when validated. Do not record planned files as artifacts unless they exist.
- Events are append-only. Never delete or rewrite historical events to hide a change.
- Record actual commands/results in future implementation events; do not claim an unexecuted check.

## Current coverage

The canonical Phase 1 graph includes 243 nodes, 371 edges, and 24 events:

- Requirements `R-000` through `R-026`, covering all 26 numbered specification sections plus section 0.
- Goals and product principles.
- Architecture decisions and selected technologies.
- Runtime components, data entities, security controls, phases, acceptance criteria, and risks.
- Installed skills with provenance and local paths.
- Work events for repository inspection, specification movement/analysis, skill installation, technology selection, standards, Phase 0/1 implementation, security remediation, offline smoke/browser verification, Docker runtime verification, and validation.
- Open questions and next actions for real-provider policy onboarding, authentication, retention enforcement, recurring dependency audit, clustering, and Phase 2.

The runtime status is `phase1_docker_loopback_verified`. This means the Docker Compose stack, migrations, Celery worker, Nginx proxy, offline evidence loop, exports, security headers, and React workbench were executed on the loopback interface and exercised in a real browser. It does not claim that real providers or production hardening are runtime-verified.

## Update workflow

1. Read the affected requirement and decision nodes.
2. Make the implementation or documentation change.
3. Add or update nodes for any new component, entity, control, decision, risk, or acceptance criterion.
4. Add typed edges that explain why the new item exists and what constrains it.
5. Append an event with actual artifact paths and related node IDs.
6. Run validation:

```powershell
python scripts/validate_knowledge_graph.py
```

7. Regenerate Mermaid views:

```powershell
python scripts/render_knowledge_graph.py
```

8. Verify the generated files are current:

```powershell
python scripts/render_knowledge_graph.py --check
```

9. Commit the JSON and generated views together with the code/documentation change.

## Change examples

### Adding a module

1. Add a `component` node with a stable ID.
2. Link it with `implements` to the requirement it serves.
3. Link it with `uses` to technologies.
4. Link security controls with `implements` where applicable.
5. Add its source path as an event artifact after the file exists.

### Superseding a decision

1. Keep the old decision node and its history.
2. Add a new decision node with a new ID.
3. Add `new -> old` with type `supersedes` and explain the trigger in the event summary.
4. Update implementation edges to point at the new decision where appropriate.

### Recording a failed or blocked step

Use `status: "blocked"` or `completed` with an honest summary if the command ran but failed. Include the discovered blocker and the next action. Never invent test success.

## Visual views

The full graph is intentionally dense. Use the focused views for review:

- Overview: why the product exists and which structural decisions define it.
- Requirements: traceability from the specification to controls and decisions.
- Data: persistence and component relationships.
- Delivery: what is planned, what must be accepted, and which risks or skills matter.

GitHub renders `.mmd` files only in some contexts. If a viewer does not render Mermaid, open the files in a Mermaid-capable editor or use Mermaid CLI.

## Validation guarantees

`scripts/validate_knowledge_graph.py` checks:

- JSON parsing and schema version.
- Unique, pattern-valid node IDs and allowed node/edge types.
- All edge endpoints and event node references.
- No self-edges, duplicate edges, or `precedes` cycles.
- Artifact paths and skill install paths.
- Source-document size/hash integrity for the specification.
- Required node types and every requirement section `R-000` to `R-026`.
- Risk mitigation coverage.
- Monotonic event sequence/timestamps and existing event artifacts.
- Referential integrity for open-question and next-action dependencies.

`scripts/render_knowledge_graph.py --check` adds a deterministic generated-view check suitable for CI.
