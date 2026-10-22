"""Manual source retention behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.base import Base
from app.db.session import Database
from app.models.source import ContentCompleteness, SourceItem
from app.services import sources as source_service
from app.services.fetcher import FetchedPage

PAGE_TEXT = (
    "Every week our team copies the same fields into a spreadsheet. "
    "The process still misses records and requires a manual reconciliation step."
)


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'sources.db').as_posix()}"
    database = Database(database_url)
    Base.metadata.create_all(database.engine)
    return database


def _settings(*, store_full_page_text: bool) -> Settings:
    return Settings(
        app_env="test",
        app_secret_key="test-only-secret",
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="",
        store_full_page_text=store_full_page_text,
    )


def _patch_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        source_service,
        "validate_outbound_url",
        lambda raw_url, **_kwargs: raw_url,
    )
    monkeypatch.setattr(
        source_service.SafeFetcher,
        "fetch",
        lambda _self, url: FetchedPage(
            requested_url=url,
            final_url=url,
            title="Imported evidence",
            text=PAGE_TEXT,
            status_code=200,
            content_type="text/html",
        ),
    )


def test_manual_import_stores_only_excerpt_by_default(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fetch(monkeypatch)
    with database.session_factory() as session:
        source, _ = source_service.import_manual_url(
            session,
            raw_url="https://evidence.example/thread/1",
            title="Imported evidence",
            settings=_settings(store_full_page_text=False),
        )

        stored = session.scalar(select(SourceItem).where(SourceItem.id == source.id))
        assert stored is not None
        assert stored.content_text is None
        assert stored.content_excerpt == PAGE_TEXT
        assert stored.content_completeness == ContentCompleteness.PARTIAL_CONTENT


def test_manual_import_can_store_full_text_when_explicitly_enabled(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fetch(monkeypatch)
    with database.session_factory() as session:
        source, _ = source_service.import_manual_url(
            session,
            raw_url="https://evidence.example/thread/2",
            title="Imported evidence",
            settings=_settings(store_full_page_text=True),
        )

        stored = session.scalar(select(SourceItem).where(SourceItem.id == source.id))
        assert stored is not None
        assert stored.content_text == PAGE_TEXT
        assert stored.content_completeness == ContentCompleteness.FULL_PUBLIC_CONTENT


def test_recheck_honors_excerpt_only_policy(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fetch(monkeypatch)
    with database.session_factory() as session:
        source, _ = source_service.import_manual_url(
            session,
            raw_url="https://evidence.example/thread/3",
            title="Imported evidence",
            settings=_settings(store_full_page_text=True),
        )
        source, _ = source_service.recheck_source(
            session, source.id, _settings(store_full_page_text=False)
        )

        assert source.content_text is None
        assert source.content_excerpt == PAGE_TEXT
        assert source.content_completeness == ContentCompleteness.PARTIAL_CONTENT
