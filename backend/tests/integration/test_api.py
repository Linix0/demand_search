"""API boundary, health, and provider configuration tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_reports_version_and_docs(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Industry Pain Radar"
    assert body["version"] == "0.1.0"
    assert body["docs_enabled"] is True
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Request-ID"]


def test_health_reports_database_and_disabled_redis(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "disabled"


def test_provider_list_never_returns_secret_values(client: TestClient) -> None:
    response = client.get("/api/v1/settings/providers")

    assert response.status_code == 200
    body = response.json()
    serialized = str(body).lower()
    assert "api_key" not in serialized
    assert "client_secret" not in serialized
    assert "token" not in serialized
    providers = {item["provider_code"]: item for item in body["items"]}
    assert providers["mock"]["enabled"] is True
    assert providers["mock"]["health_status"] == "healthy"
    assert providers["reddit"]["enabled"] is False


def test_mock_provider_test_endpoint(client: TestClient) -> None:
    response = client.post("/api/v1/settings/providers/mock/test")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_disabled_provider_cannot_be_tested(client: TestClient) -> None:
    response = client.post("/api/v1/settings/providers/reddit/test")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "CONFLICT"
    assert body["request_id"]


def test_unknown_provider_uses_stable_error_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/settings/providers/not-real/test")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_invalid_host_is_rejected(client: TestClient) -> None:
    response = client.get("/", headers={"Host": "attacker.example"})

    assert response.status_code == 400
