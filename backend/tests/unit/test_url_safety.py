"""SSRF policy regression tests."""

from __future__ import annotations

import pytest

from app.core.errors import UrlSafetyError
from app.services.url_safety import validate_outbound_url, validate_redirect_target


def public_resolver(host: str, port: int) -> list[str]:
    return ["93.184.216.34"]


def test_public_url_is_canonicalized_and_tracking_removed() -> None:
    result = validate_outbound_url(
        "HTTPS://Example.COM:443/issues/42?utm_source=newsletter&state=open#comment-7",
        resolver=public_resolver,
    )

    assert result == "https://example.com/issues/42?state=open#comment-7"


@pytest.mark.parametrize(
    ("raw_url", "error_code"),
    [
        ("javascript:alert(1)", "INVALID_SCHEME"),
        ("file:///etc/passwd", "INVALID_SCHEME"),
        ("https://user:pass@example.com/", "URL_CREDENTIALS_NOT_ALLOWED"),
        ("https://localhost/", "HOST_NOT_ALLOWED"),
        ("https://metadata.google.internal/", "HOST_NOT_ALLOWED"),
        ("https://example.com:8080/", "PORT_NOT_ALLOWED"),
    ],
)
def test_obviously_unsafe_urls_are_rejected(raw_url: str, error_code: str) -> None:
    with pytest.raises(UrlSafetyError) as error:
        validate_outbound_url(raw_url, resolver=public_resolver)

    assert error.value.code == error_code


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.8", "169.254.169.254", "::1", "fd00::1", "0.0.0.0"],
)
def test_non_public_resolved_addresses_are_rejected(address: str) -> None:
    def resolver(host: str, port: int) -> list[str]:
        return [address]

    with pytest.raises(UrlSafetyError) as error:
        validate_outbound_url("https://public.example/resource", resolver=resolver)

    assert error.value.code == "NON_PUBLIC_ADDRESS"


def test_one_private_address_in_dns_answers_blocks_the_request() -> None:
    def resolver(host: str, port: int) -> list[str]:
        return ["93.184.216.34", "10.0.0.8"]

    with pytest.raises(UrlSafetyError):
        validate_outbound_url("https://public.example/resource", resolver=resolver)


@pytest.mark.parametrize(
    "raw_url",
    [
        "http://127.0.0.1/private",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/private",
    ],
)
def test_ip_literals_are_rejected_even_without_dns_lookup(raw_url: str) -> None:
    with pytest.raises(UrlSafetyError) as error:
        validate_outbound_url(raw_url, require_public_dns=False)

    assert error.value.code == "NON_PUBLIC_ADDRESS"


def test_redirect_target_is_revalidated() -> None:
    with pytest.raises(UrlSafetyError) as error:
        validate_redirect_target(
            "https://public.example/start",
            "http://169.254.169.254/latest/meta-data",
            resolver=lambda host, port: [host],
        )

    assert error.value.code == "NON_PUBLIC_ADDRESS"
