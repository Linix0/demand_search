"""Boundary tests for the public-page fetch policy."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import UrlSafetyError
from app.services import fetcher as fetcher_module
from app.services.fetcher import SafeFetcher


class _ResponseContext:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response

    def __enter__(self) -> httpx.Response:
        return self.response

    def __exit__(self, *args: object) -> None:
        return None


class _ClientWithoutPeerInformation:
    def __init__(self, **_kwargs: Any) -> None:
        self.response = httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html><body>Public text</body></html>",
        )

    def __enter__(self) -> _ClientWithoutPeerInformation:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def stream(self, *_args: object, **_kwargs: object) -> _ResponseContext:
        return _ResponseContext(self.response)


def test_fetch_fails_closed_when_peer_address_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fetcher_module,
        "validate_outbound_url",
        lambda raw_url, **_kwargs: raw_url,
    )
    monkeypatch.setattr(fetcher_module.httpx, "Client", _ClientWithoutPeerInformation)
    settings = Settings(app_env="test", app_secret_key="test-only-secret", redis_url="")

    with pytest.raises(UrlSafetyError) as error:
        SafeFetcher(settings).fetch("https://public.example/page")

    assert error.value.code == "PEER_ADDRESS_UNAVAILABLE"
