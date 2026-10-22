"""Shared isolated application fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    database_path = (tmp_path / "test.db").as_posix()
    return Settings(
        app_env="test",
        app_host="127.0.0.1",
        app_secret_key="test-only-secret",
        database_url=f"sqlite+pysqlite:///{database_path}",
        redis_url="",
        allowed_hosts="testserver",
    )


@pytest.fixture
def app(test_settings: Settings):  # type: ignore[no-untyped-def]
    application = create_app(test_settings)
    Base.metadata.create_all(application.state.db.engine)
    return application


@pytest.fixture
def client(app) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    with TestClient(app) as test_client:
        yield test_client
