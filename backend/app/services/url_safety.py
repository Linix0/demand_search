"""Outbound URL validation for SSRF-sensitive source retrieval."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from urllib.parse import SplitResult, parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from app.core.errors import UrlSafetyError

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref_src",
}

BLOCKED_HOSTS = {
    "localhost",
    "metadata",
    "metadata.google.internal",
    "metadata.azure.internal",
}

Resolver = Callable[[str, int], Iterable[str]]


def resolve_host_ips(host: str, port: int) -> list[str]:
    """Resolve all stream addresses for a host without connecting to them."""

    try:
        address_info = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UrlSafetyError(
            "DNS_RESOLUTION_FAILED", "The source host could not be resolved."
        ) from exc
    return [str(item[4][0]) for item in address_info]


def _is_blocked_host(host: str) -> bool:
    normalized = host.rstrip(".").lower()
    return normalized in BLOCKED_HOSTS or normalized.endswith((".localhost", ".local"))


def validate_ip_address(raw_ip: str) -> None:
    try:
        address = ipaddress.ip_address(raw_ip)
    except ValueError as exc:
        raise UrlSafetyError(
            "INVALID_RESOLVED_ADDRESS", "The source host resolved to an invalid address."
        ) from exc

    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped

    if not address.is_global:
        raise UrlSafetyError(
            "NON_PUBLIC_ADDRESS", "Private, local, metadata, or reserved addresses are blocked."
        )


def _is_tracking_key(key: str) -> bool:
    normalized = key.lower()
    return normalized.startswith("utm_") or normalized in TRACKING_QUERY_KEYS


def _canonicalize(parsed: SplitResult) -> str:
    scheme = parsed.scheme.lower()
    host = parsed.hostname.rstrip(".").lower() if parsed.hostname else ""
    port = parsed.port
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)

    host_for_url = f"[{host}]" if ":" in host else host
    netloc = host_for_url if port is None or default_port else f"{host_for_url}:{port}"

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_key(key)
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, parsed.path or "/", query, parsed.fragment))


def validate_outbound_url(
    raw_url: str,
    *,
    resolver: Resolver = resolve_host_ips,
    allowed_ports: frozenset[int] = frozenset({80, 443}),
    require_public_dns: bool = True,
) -> str:
    """Validate and canonicalize a URL before any outbound request is made."""

    if not isinstance(raw_url, str) or not raw_url.strip():
        raise UrlSafetyError("URL_REQUIRED", "A source URL is required.")
    if len(raw_url) > 2_048:
        raise UrlSafetyError("URL_TOO_LONG", "The source URL is too long.")

    try:
        parsed = urlsplit(raw_url.strip())
    except ValueError as exc:
        raise UrlSafetyError("INVALID_URL", "The source URL is invalid.") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise UrlSafetyError("INVALID_SCHEME", "Only HTTP and HTTPS URLs are allowed.")
    if not parsed.hostname:
        raise UrlSafetyError("HOST_REQUIRED", "The source URL must include a host.")
    if parsed.username is not None or parsed.password is not None:
        raise UrlSafetyError(
            "URL_CREDENTIALS_NOT_ALLOWED", "Credentials in source URLs are not allowed."
        )

    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise UrlSafetyError("INVALID_PORT", "The source URL has an invalid port.") from exc
    if port not in allowed_ports:
        raise UrlSafetyError("PORT_NOT_ALLOWED", "The source URL uses a disallowed port.")

    host = parsed.hostname.rstrip(".").lower()
    if _is_blocked_host(host):
        raise UrlSafetyError("HOST_NOT_ALLOWED", "Local and metadata hostnames are blocked.")

    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        validate_ip_address(host)

    if require_public_dns:
        resolved_ips = list(resolver(host, port))
        if not resolved_ips:
            raise UrlSafetyError("DNS_RESOLUTION_FAILED", "The source host returned no addresses.")
        for resolved_ip in resolved_ips:
            validate_ip_address(resolved_ip)

    return _canonicalize(parsed)


def validate_redirect_target(
    base_url: str,
    location: str,
    *,
    resolver: Resolver = resolve_host_ips,
    allowed_ports: frozenset[int] = frozenset({80, 443}),
    require_public_dns: bool = True,
) -> str:
    """Resolve and fully revalidate every redirect target."""

    redirected = urljoin(base_url, location)
    return validate_outbound_url(
        redirected,
        resolver=resolver,
        allowed_ports=allowed_ports,
        require_public_dns=require_public_dns,
    )
