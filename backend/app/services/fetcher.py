"""SSRF-gated, bounded public-page retrieval for manual source import."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from app.core.config import Settings
from app.core.errors import UrlSafetyError
from app.services.url_safety import (
    validate_ip_address,
    validate_outbound_url,
    validate_redirect_target,
)

TEXT_CONTENT_TYPES = {
    "text/html",
    "text/plain",
    "application/xhtml+xml",
}
USER_AGENT = "IndustryPainRadar/0.1 (local evidence research; policy-gated fetch)"


class UnsafeContentTypeError(Exception):
    pass


class ResponseTooLargeError(Exception):
    pass


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.parts: list[str] = []
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in {"p", "br", "div", "li", "article", "section", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "template", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        elif not self._skip_depth:
            self.parts.append(data)


@dataclass(frozen=True, slots=True)
class FetchedPage:
    requested_url: str
    final_url: str
    title: str
    text: str
    status_code: int
    content_type: str


def _extract_html(html: str) -> tuple[str, str]:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    title = re.sub(r"\s+", " ", " ".join(parser.title_parts)).strip()
    return title, text


def _peer_ip(response: httpx.Response) -> str | None:
    stream = response.extensions.get("network_stream")
    if stream is None:
        return None
    get_extra_info = getattr(stream, "get_extra_info", None)
    if get_extra_info is None:
        return None
    peer = get_extra_info("server_addr")
    if isinstance(peer, tuple) and peer:
        return str(peer[0])
    return None


class SafeFetcher:
    """Fetch a single public text page with redirect and size enforcement."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fetch(self, raw_url: str) -> FetchedPage:
        current_url = validate_outbound_url(
            raw_url,
            allowed_ports=self.settings.allowed_ports,
            require_public_dns=True,
        )
        requested_url = current_url
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"}

        with httpx.Client(
            timeout=httpx.Timeout(
                connect=self.settings.connect_timeout_seconds,
                read=self.settings.fetch_timeout_seconds,
                write=self.settings.fetch_timeout_seconds,
                pool=self.settings.connect_timeout_seconds,
            ),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            for redirect_number in range(self.settings.max_redirects + 1):
                with client.stream("GET", current_url, headers=headers) as response:
                    peer_ip = _peer_ip(response)
                    if peer_ip is None:
                        raise UrlSafetyError(
                            "PEER_ADDRESS_UNAVAILABLE",
                            "The source connection address could not be verified.",
                        )
                    validate_ip_address(peer_ip)

                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise UrlSafetyError("INVALID_REDIRECT", "Redirect missing a target.")
                        if redirect_number >= self.settings.max_redirects:
                            raise UrlSafetyError("TOO_MANY_REDIRECTS", "Redirect limit exceeded.")
                        current_url = validate_redirect_target(
                            current_url,
                            location,
                            allowed_ports=self.settings.allowed_ports,
                            require_public_dns=True,
                        )
                        continue

                    if response.status_code in {401, 403}:
                        raise UrlSafetyError(
                            "SOURCE_ACCESS_BLOCKED",
                            "The source requires access that is not allowed.",
                        )
                    if response.status_code == 404:
                        raise UrlSafetyError("SOURCE_NOT_FOUND", "The source page was not found.")
                    if response.status_code >= 400:
                        raise UrlSafetyError(
                            "SOURCE_FETCH_FAILED", "The source returned an error response."
                        )

                    content_type = response.headers.get("content-type", "").split(";")[0].lower()
                    if content_type not in TEXT_CONTENT_TYPES:
                        raise UnsafeContentTypeError("Only public text pages may be imported.")

                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > self.settings.max_page_bytes:
                            raise ResponseTooLargeError("The source page exceeds the size limit.")
                        chunks.append(chunk)

                    body = b"".join(chunks)
                    encoding = response.charset_encoding or "utf-8"
                    try:
                        decoded = body.decode(encoding, errors="replace")
                    except LookupError:
                        decoded = body.decode("utf-8", errors="replace")

                    if content_type in {"text/html", "application/xhtml+xml"}:
                        title, text = _extract_html(decoded)
                    else:
                        title, text = "", decoded.strip()
                    if not text:
                        raise UrlSafetyError(
                            "SOURCE_EMPTY", "The source page had no readable text."
                        )
                    return FetchedPage(
                        requested_url=requested_url,
                        final_url=str(response.url),
                        title=title[:300],
                        text=text[:20_000],
                        status_code=response.status_code,
                        content_type=content_type,
                    )

        raise UrlSafetyError("TOO_MANY_REDIRECTS", "Redirect limit exceeded.")


def is_public_domain(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return bool(host) and "." in host and not host.endswith(".local")


def describe_fetch_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, UrlSafetyError):
        return exc.code, exc.message
    if isinstance(exc, UnsafeContentTypeError):
        return "UNSAFE_CONTENT_TYPE", str(exc)
    if isinstance(exc, ResponseTooLargeError):
        return "RESPONSE_TOO_LARGE", str(exc)
    if isinstance(exc, httpx.TimeoutException):
        return "SOURCE_TIMEOUT", "The source timed out."
    return "SOURCE_FETCH_FAILED", "The source could not be retrieved."
