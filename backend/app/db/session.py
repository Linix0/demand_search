"""Engine and per-request session construction."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class Database:
    """Own an engine and session factory without leaking global state."""

    def __init__(self, database_url: str) -> None:
        if database_url.startswith("sqlite+pysqlite:///"):
            raw_path = database_url.removeprefix("sqlite+pysqlite:///")
            if raw_path and raw_path != ":memory:":
                Path(raw_path).resolve().parent.mkdir(parents=True, exist_ok=True)

        engine_options: dict[str, Any] = {"pool_pre_ping": True, "future": True}
        if database_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}

        self.engine: Engine = create_engine(database_url, **engine_options)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        self.engine.dispose()
