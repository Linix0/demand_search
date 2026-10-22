#!/usr/bin/env python3
"""Validate the canonical project knowledge graph without third-party packages."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = REPO_ROOT / "docs" / "knowledge-graph" / "project-graph.json"
ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{3}$")
EVENT_STATUSES = {"completed", "pending", "blocked"}


class ValidationError(Exception):
    """A collection of graph integrity errors."""


def load_graph(path: Path = GRAPH_PATH) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ValidationError(f"Graph not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ValidationError("Graph root must be a JSON object.")
    return data


def _require_mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object.")
        return {}
    return value


def _require_list(value: Any, label: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array.")
        return []
    return value


def _check_unique_ids(items: list[dict[str, Any]], label: str, errors: list[str]) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        item_id = item.get("id")
        if not isinstance(item_id, str) or not ID_PATTERN.fullmatch(item_id):
            errors.append(f"{label}[{index}] has invalid id: {item_id!r}")
            continue
        if item_id in seen:
            errors.append(f"{label} contains duplicate id: {item_id}")
        seen.add(item_id)
    return seen


def _check_source_documents(data: dict[str, Any], errors: list[str]) -> None:
    documents = _require_list(data.get("source_documents"), "source_documents", errors)
    seen: set[str] = set()
    for index, document in enumerate(documents):
        document = _require_mapping(document, f"source_documents[{index}]", errors)
        document_id = document.get("id")
        if document_id in seen:
            errors.append(f"Duplicate source document id: {document_id}")
        seen.add(document_id)

        raw_path = document.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"Source document {document_id} has no path.")
            continue

        path = REPO_ROOT / raw_path
        if not path.is_file():
            errors.append(f"Source document {document_id} path does not exist: {raw_path}")
            continue

        expected_size = document.get("size_bytes")
        if expected_size is not None and path.stat().st_size != expected_size:
            errors.append(
                f"Source document {document_id} size mismatch: expected {expected_size}, "
                f"found {path.stat().st_size}"
            )

        expected_hash = document.get("sha256")
        if expected_hash:
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            if actual_hash != str(expected_hash).upper():
                errors.append(
                    f"Source document {document_id} hash mismatch: expected {expected_hash}, "
                    f"found {actual_hash}"
                )


def _check_nodes(data: dict[str, Any], errors: list[str]) -> tuple[dict[str, dict[str, Any]], set[str], set[str]]:
    conventions = _require_mapping(data.get("conventions"), "conventions", errors)
    allowed_types = set(_require_list(conventions.get("node_types"), "conventions.node_types", errors))
    required_types = set(
        _require_list(conventions.get("required_node_types"), "conventions.required_node_types", errors)
    )
    allowed_edges = set(_require_list(conventions.get("edge_types"), "conventions.edge_types", errors))

    nodes = _require_list(data.get("nodes"), "nodes", errors)
    typed_nodes: list[dict[str, Any]] = []
    for index, node in enumerate(nodes):
        node = _require_mapping(node, f"nodes[{index}]", errors)
        typed_nodes.append(node)

    ids = _check_unique_ids(typed_nodes, "nodes", errors)
    node_by_id = {node["id"]: node for node in typed_nodes if isinstance(node.get("id"), str) and node["id"] in ids}
    type_counts = Counter(node.get("type") for node in typed_nodes)

    for node_id, node in node_by_id.items():
        node_type = node.get("type")
        if node_type not in allowed_types:
            errors.append(f"Node {node_id} has invalid type: {node_type!r}")
        for field in ("title", "summary", "status"):
            if not isinstance(node.get(field), str) or not node[field].strip():
                errors.append(f"Node {node_id} is missing non-empty field {field}.")
        source_refs = node.get("source_refs", [])
        if not isinstance(source_refs, list) or not all(isinstance(ref, str) for ref in source_refs):
            errors.append(f"Node {node_id} source_refs must be an array of strings.")

        if node_type == "artifact":
            if node.get("status") == "external":
                if not isinstance(node.get("url"), str) or not node["url"].startswith("https://"):
                    errors.append(f"External artifact {node_id} must have an HTTPS url.")
            else:
                raw_path = node.get("path")
                if not isinstance(raw_path, str) or not raw_path:
                    errors.append(f"Artifact {node_id} has no path.")
                elif not (REPO_ROOT / raw_path).is_file():
                    errors.append(f"Artifact {node_id} path does not exist: {raw_path}")

        if node_type == "skill":
            install_path = node.get("install_path")
            if not isinstance(install_path, str) or not Path(install_path).is_dir():
                errors.append(f"Skill {node_id} install_path does not exist: {install_path!r}")
            url = node.get("url")
            if not isinstance(url, str) or not url.startswith("https://github.com/"):
                errors.append(f"Skill {node_id} must have a GitHub source url.")

    missing_types = sorted(required_types - set(type_counts))
    if missing_types:
        errors.append(f"Graph is missing required node types: {', '.join(missing_types)}")

    required_requirements = {f"R-{number:03d}" for number in range(27)}
    missing_requirements = sorted(required_requirements - ids)
    if missing_requirements:
        errors.append(f"Graph is missing requirement sections: {', '.join(missing_requirements)}")

    return node_by_id, ids, allowed_edges


def _check_edges(
    data: dict[str, Any], node_ids: set[str], allowed_types: set[str], errors: list[str]
) -> list[dict[str, Any]]:
    edges = _require_list(data.get("edges"), "edges", errors)
    typed_edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()

    for index, edge in enumerate(edges):
        edge = _require_mapping(edge, f"edges[{index}]", errors)
        typed_edges.append(edge)
        source = edge.get("from")
        target = edge.get("to")
        edge_type = edge.get("type")

        if source not in node_ids:
            errors.append(f"Edge[{index}] references missing source: {source!r}")
        if target not in node_ids:
            errors.append(f"Edge[{index}] references missing target: {target!r}")
        if edge_type not in allowed_types:
            errors.append(f"Edge[{index}] has invalid type: {edge_type!r}")
        if source == target and isinstance(source, str):
            errors.append(f"Edge[{index}] is a self-edge: {source}")

        key = (str(source), str(target), str(edge_type))
        if key in edge_keys:
            errors.append(f"Duplicate edge: {key}")
        edge_keys.add(key)

    inbound_mitigation = defaultdict(int)
    for edge in typed_edges:
        if edge.get("type") == "mitigates":
            inbound_mitigation[edge.get("to")] += 1

    node_by_id = {node["id"]: node for node in _require_list(data.get("nodes"), "nodes", errors)}
    for node_id, node in node_by_id.items():
        if node.get("type") == "risk" and inbound_mitigation[node_id] == 0:
            errors.append(f"Risk {node_id} has no incoming mitigates edge.")

    return typed_edges


def _check_precedes_cycles(edges: list[dict[str, Any]], errors: list[str]) -> None:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.get("type") == "precedes":
            graph[str(edge.get("from"))].append(str(edge.get("to")))

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"Cycle detected in precedes edges at {node}.")
            return
        if node in visited:
            return
        visiting.add(node)
        for target in graph.get(node, []):
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in list(graph):
        visit(node)


def _check_events(data: dict[str, Any], node_ids: set[str], errors: list[str]) -> None:
    events = _require_list(data.get("events"), "events", errors)
    sequences: set[int] = set()
    previous_sequence = 0
    previous_time: datetime | None = None

    for index, event in enumerate(events):
        event = _require_mapping(event, f"events[{index}]", errors)
        sequence = event.get("sequence")
        if not isinstance(sequence, int) or sequence <= 0:
            errors.append(f"events[{index}] has invalid sequence: {sequence!r}")
        else:
            if sequence in sequences:
                errors.append(f"Duplicate event sequence: {sequence}")
            if sequence <= previous_sequence:
                errors.append(f"Event sequence must increase: {sequence} after {previous_sequence}")
            sequences.add(sequence)
            previous_sequence = max(previous_sequence, sequence)

        timestamp = event.get("at")
        try:
            parsed = datetime.fromisoformat(str(timestamp))
        except ValueError:
            errors.append(f"Event {sequence} has invalid ISO-8601 timestamp: {timestamp!r}")
        else:
            if parsed.tzinfo is None:
                errors.append(f"Event {sequence} timestamp must include an offset: {timestamp!r}")
            if previous_time and parsed < previous_time:
                errors.append(f"Event {sequence} time goes backwards: {timestamp}")
            previous_time = parsed

        status = event.get("status")
        if status not in EVENT_STATUSES:
            errors.append(f"Event {sequence} has invalid status: {status!r}")

        for field in ("action", "summary"):
            if not isinstance(event.get(field), str) or not event[field].strip():
                errors.append(f"Event {sequence} is missing non-empty field {field}.")

        related = event.get("related_node_ids", [])
        if not isinstance(related, list):
            errors.append(f"Event {sequence} related_node_ids must be an array.")
        else:
            for node_id in related:
                if node_id not in node_ids:
                    errors.append(f"Event {sequence} references missing node: {node_id}")

        artifacts = event.get("artifacts", [])
        if not isinstance(artifacts, list):
            errors.append(f"Event {sequence} artifacts must be an array.")
        else:
            for artifact in artifacts:
                if not isinstance(artifact, str) or not artifact:
                    errors.append(f"Event {sequence} has an invalid artifact path: {artifact!r}")
                elif not (REPO_ROOT / artifact).exists():
                    errors.append(f"Event {sequence} artifact does not exist: {artifact}")

    if not events:
        errors.append("Graph must contain at least one event.")


def _check_open_items(data: dict[str, Any], node_ids: set[str], errors: list[str]) -> None:
    questions = _require_list(data.get("open_questions"), "open_questions", errors)
    question_ids = {question.get("id") for question in questions if isinstance(question, dict)}
    if len(question_ids) != len(questions):
        errors.append("open_questions contains duplicate or missing ids.")
    for question in questions:
        if not isinstance(question, dict) or not all(
            isinstance(question.get(field), str) for field in ("question", "impact", "status")
        ):
            errors.append("Every open question requires question, impact, and status strings.")

    actions = _require_list(data.get("next_actions"), "next_actions", errors)
    action_ids = {action.get("id") for action in actions if isinstance(action, dict)}
    if len(action_ids) != len(actions):
        errors.append("next_actions contains duplicate or missing ids.")
    for action in actions:
        if not isinstance(action, dict):
            errors.append("next_actions entries must be objects.")
            continue
        for field in ("action",):
            if not isinstance(action.get(field), str) or not action[field].strip():
                errors.append(f"Next action {action.get('id')} is missing {field}.")
        for dependency in action.get("depends_on", []):
            if dependency not in node_ids:
                errors.append(f"Next action {action.get('id')} references missing dependency: {dependency}")
        for acceptance in action.get("acceptance", []):
            if acceptance not in node_ids:
                errors.append(f"Next action {action.get('id')} references missing acceptance: {acceptance}")


def validate_graph(path: Path = GRAPH_PATH) -> dict[str, Any]:
    data = load_graph(path)
    errors: list[str] = []

    if data.get("schema_version") != "1.0.0":
        errors.append(f"Unsupported schema_version: {data.get('schema_version')!r}")
    _require_mapping(data.get("project"), "project", errors)
    _check_source_documents(data, errors)
    _, node_ids, allowed_edges = _check_nodes(data, errors)
    edges = _check_edges(data, node_ids, allowed_edges, errors)
    _check_precedes_cycles(edges, errors)
    _check_events(data, node_ids, errors)
    _check_open_items(data, node_ids, errors)

    if errors:
        formatted = "\n".join(f"  - {error}" for error in errors)
        raise ValidationError(f"Knowledge graph validation failed with {len(errors)} error(s):\n{formatted}")

    type_counts = Counter(node.get("type") for node in data["nodes"])
    return {
        "nodes": len(data["nodes"]),
        "edges": len(data["edges"]),
        "events": len(data["events"]),
        "types": dict(sorted(type_counts.items())),
    }


def main() -> int:
    try:
        summary = validate_graph()
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        return 1

    print("Knowledge graph is valid.")
    print(
        f"Nodes: {summary['nodes']} | Edges: {summary['edges']} | Events: {summary['events']}"
    )
    print("Node types: " + ", ".join(f"{name}={count}" for name, count in summary["types"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
