"""FastAPI dependencies tied to application state."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import Database


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_database(request: Request) -> Database:
    return request.app.state.db


def get_db_session(request: Request) -> Iterator[Session]:
    database: Database = request.app.state.db
    yield from database.session()
