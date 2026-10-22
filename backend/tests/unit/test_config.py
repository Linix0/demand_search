"""Production secret validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("secret", ["replace_me", "local-compose-change-me", "short-secret"])
def test_production_rejects_weak_or_short_secret(secret: str) -> None:
    with pytest.raises(ValidationError, match="APP_SECRET_KEY"):
        Settings(app_env="production", app_secret_key=secret)


def test_production_accepts_long_non_placeholder_secret() -> None:
    settings = Settings(
        app_env="production",
        app_secret_key="a" * 64,
    )

    assert settings.is_production is True
