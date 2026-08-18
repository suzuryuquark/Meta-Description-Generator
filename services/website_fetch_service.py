from __future__ import annotations

import email.utils
import ipaddress
import json
import re
import socket
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup, Tag

from models.website import FetchedPage, PageMetadata

MAX_URL_LENGTH = 2_048
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_PROMPT_TOKENS = 12_000
ALLOWED_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
REMOVABLE_ELEMENT_PATTERN = re.compile(
    r"(?:cookie|consent|privacy[-_ ]?banner|navigation|navbar|footer|sidebar)",
    re.IGNORECASE,
)


class WebsiteFetchError(Exception):
    """Base class for safe, user-facing website fetch failures."""


class UrlValidationError(WebsiteFetchError):
    """Raised when a URL is malformed or points to a blocked network."""


class UnsupportedContentTypeError(WebsiteFetchError):
    """Raised when a response is not HTML or XHTML."""


class ResponseTooLargeError(WebsiteFetchError):
    """Raised when a response exceeds the configured byte limit."""


@dataclass(frozen=True, slots=True)
class ValidatedUrl:
    url: str
    host: str
    port: int
    addresses: tuple[str, ...]


Resolver = Callable[[str, int], Iterable[Any]]
Sleeper = Callable[[float], None]


class UrlValidator:
    def __init__(
        self,
        *,
        allow_private_network: bool = False,
        resolver: Resolver | None = None,
        maximum_url_length: int = MAX_URL_LENGTH,
    ) -> None:
        self.allow_private_network = allow_private_network
        self.resolver = resolver or self._resolve
        self.maximum_url_length = maximum_url_length

    def validate(self, url: str) -> ValidatedUrl:
        candidate = url.strip()
        if not candidate:
            raise UrlValidationError("URLを入力してください")
        if len(candidate) > self.maximum_url_length:
            raise UrlValidationError("URLが長すぎます")
        if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
            raise UrlValidationError("URLに制御文字を含めることはできません")

        parsed = urlsplit(candidate)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise UrlValidationError("httpまたはhttpsのURLだけを指定できます")
        if parsed.username is not None or parsed.password is not None:
            raise UrlValidationError("認証情報を含むURLは指定できません")

        host = (parsed.hostname or "").rstrip(".").lower()
        if not host or len(host) > 253 or any(character.isspace() for character in host):
            raise UrlValidationError("有効なホスト名を指定してください")
        if host == "localhost" or host.endswith(".localhost"):
            raise UrlValidationError("ローカルアドレスへのアクセスは許可されていません")

        try:
            explicit_port = parsed.port
        except ValueError as exc:
            raise UrlValidationError("有効なポート番号を指定してください") from exc
        if explicit_port == 0:
            raise UrlValidationError("有効なポート番号を指定してください")
        port = (
            explicit_port
            if explicit_port is not None
            else (443 if parsed.scheme == "https" else 80)
        )

        try:
            resolved = tuple(dict.fromkeys(self._addresses(host, port)))
        except (OSError, UnicodeError, ValueError) as exc:
            raise UrlValidationError("ホスト名を解決できませんでした") from exc
        if not resolved:
            raise UrlValidationError("ホスト名を解決できませんでした")

        if not self.allow_private_network:
            for address in resolved:
                try:
                    ip = ipaddress.ip_address(address)
                except ValueError as exc:
                    raise UrlValidationError("DNSから無効なIPアドレスが返されました") from exc
                if not ip.is_global:
                    raise UrlValidationError(
                        "ローカル、プライベート、または予約済みアドレスへのアクセスは許可されていません"
                    )
        return ValidatedUrl(candidate, host, port, resolved)

    def _addresses(self, host: str, port: int) -> Iterable[str]:
        try:
            yield str(ipaddress.ip_address(host))
            return
        except ValueError:
            pass
        for result in self.resolver(host, port):
            if isinstance(result, str):
                yield result
            else:
                yield result[4][0]

    @staticmethod
    def _resolve(host: str, port: int) -> Iterable[Any]:
        return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)


class WebsiteContentExtractor:
    def __init__(self, *, maximum_prompt_tokens: int = MAX_PROMPT_TOKENS) -> None:
        self.maximum_prompt_tokens = maximum_prompt_tokens

    def extract(self, html: bytes, requested_url: str, final_url: str) -> FetchedPage:
        soup = BeautifulSoup(html, "html.parser")
        metadata = self._metadata(soup, final_url)

        for element in soup.find_all(["script", "style", "noscript", "template", "svg"]):
            element.decompose()
        for element in soup.find_all(["nav", "footer", "header", "aside", "form", "dialog"]):
            element.decompose()
        for element in soup.find_all(self._looks_like_boilerplate):
            element.decompose()

        root = soup.find("main") or soup.find("article") or soup.body or soup
        content_parts: list[str] = []
        seen: set[str] = set()
        for element in root.find_all(["h1", "h2", "h3", "p", "li", "th", "td"]):
            text = self._normalize(element.get_text(" ", strip=True))
            fingerprint = text.casefold()
            if text and fingerprint not in seen:
                seen.add(fingerprint)
                content_parts.append(text)

        page = FetchedPage(
            requested_url=requested_url,
            final_url=final_url,
            metadata=metadata,
            content="\n".join(content_parts),
        )
        return page

    def _metadata(self, soup: BeautifulSoup, final_url: str) -> PageMetadata:
        title = self._bounded(soup.title.get_text(" ", strip=True)) if soup.title else ""
        description = self._meta_content(soup, name="description")
        robots = self._meta_content(soup, name="robots")
        language = ""
        if soup.html:
            language = self._attribute(soup.html, "lang")

        canonical_url = ""
        canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
        if isinstance(canonical, Tag):
            canonical_url = urljoin(final_url, self._attribute(canonical, "href"))

        open_graph: dict[str, str] = {}
        for meta in soup.find_all("meta"):
            property_name = self._attribute(meta, "property")
            if property_name.lower().startswith("og:"):
                content = self._attribute(meta, "content")
                if content:
                    open_graph[property_name] = self._bounded(content)

        return PageMetadata(
            title=title,
            description=description,
            canonical_url=canonical_url,
            robots=robots,
            language=language,
            open_graph=open_graph,
            structured_data=self._structured_data(soup),
        )

    def _structured_data(self, soup: BeautifulSoup) -> tuple[str, ...]:
        summaries: list[str] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text()
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            for item in self._json_ld_items(data):
                summary = self._summarize_json_ld(item)
                if summary and summary not in summaries:
                    summaries.append(summary)
        return tuple(summaries[:20])

    @staticmethod
    def _json_ld_items(data: Any) -> Iterable[dict[str, Any]]:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item
        elif isinstance(data, dict):
            graph = data.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict):
                        yield item
            else:
                yield data

    def _summarize_json_ld(self, item: dict[str, Any]) -> str:
        values: list[str] = []
        data_type = item.get("@type")
        if isinstance(data_type, list):
            values.append(f"type={','.join(str(value) for value in data_type)}")
        elif data_type:
            values.append(f"type={data_type}")
        for key in (
            "name",
            "headline",
            "description",
            "sku",
            "datePublished",
            "dateModified",
        ):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                values.append(f"{key}={self._normalize(value)[:500]}")
        brand = item.get("brand")
        if isinstance(brand, dict) and isinstance(brand.get("name"), str):
            values.append(f"brand={self._bounded(brand['name'])}")
        elif isinstance(brand, str):
            values.append(f"brand={self._bounded(brand)}")
        offers = item.get("offers")
        offer_items = offers if isinstance(offers, list) else [offers]
        for offer in offer_items[:5]:
            if not isinstance(offer, dict):
                continue
            offer_values = [
                f"{key}={self._bounded(str(offer[key]))}"
                for key in ("price", "priceCurrency", "availability")
                if offer.get(key) is not None
            ]
            if offer_values:
                values.append(f"offer({','.join(offer_values)})")
        main_entity = item.get("mainEntity")
        if isinstance(main_entity, list):
            questions: list[str] = []
            for entity in main_entity[:10]:
                if not isinstance(entity, dict) or not entity.get("name"):
                    continue
                question = self._bounded(str(entity["name"]))
                accepted_answer = entity.get("acceptedAnswer")
                if isinstance(accepted_answer, dict) and accepted_answer.get("text"):
                    question += f" -> {self._bounded(str(accepted_answer['text']))}"
                questions.append(question)
            if questions:
                values.append(f"questions={' / '.join(questions[:10])}")
        return "; ".join(values)[:2_000]

    @staticmethod
    def _meta_content(soup: BeautifulSoup, *, name: str) -> str:
        meta = soup.find("meta", attrs={"name": re.compile(f"^{re.escape(name)}$", re.I)})
        if not isinstance(meta, Tag):
            return ""
        return WebsiteContentExtractor._bounded(WebsiteContentExtractor._attribute(meta, "content"))

    @staticmethod
    def _attribute(tag: Tag, name: str) -> str:
        value = tag.get(name, "")
        return value.strip() if isinstance(value, str) else ""

    @staticmethod
    def _looks_like_boilerplate(tag: Tag) -> bool:
        class_attribute = tag.get("class")
        classes = class_attribute if isinstance(class_attribute, list) else []
        identifiers = " ".join(
            [
                WebsiteContentExtractor._attribute(tag, "id"),
                *(str(class_name) for class_name in classes),
            ]
        )
        return bool(identifiers and REMOVABLE_ELEMENT_PATTERN.search(identifiers))

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _bounded(value: str, maximum_chars: int = 500) -> str:
        return WebsiteContentExtractor._normalize(value)[:maximum_chars]


class WebsiteFetchService:
    def __init__(
        self,
        *,
        validator: UrlValidator | None = None,
        extractor: WebsiteContentExtractor | None = None,
        session: requests.Session | None = None,
        sleeper: Sleeper = time.sleep,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
        maximum_response_bytes: int = MAX_RESPONSE_BYTES,
        maximum_redirects: int = 5,
        maximum_attempts: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.validator = validator or UrlValidator()
        self.extractor = extractor or WebsiteContentExtractor()
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.sleeper = sleeper
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.maximum_response_bytes = maximum_response_bytes
        self.maximum_redirects = maximum_redirects
        self.maximum_attempts = maximum_attempts
        self.backoff_factor = backoff_factor
        self._fetch_lock = threading.Lock()

    def fetch(self, url: str) -> FetchedPage:
        with self._fetch_lock:
            return self._fetch(url)

    def _fetch(self, url: str) -> FetchedPage:
        requested_url = url.strip()
        current_url = requested_url
        for redirect_count in range(self.maximum_redirects + 1):
            response = self._request_with_retry(current_url)
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise WebsiteFetchError("リダイレクト先が指定されていません")
                if redirect_count >= self.maximum_redirects:
                    raise WebsiteFetchError("リダイレクト回数が上限を超えました")
                current_url = urljoin(current_url, location)
                continue
            try:
                self._validate_response(response)
                body = self._read_bounded(response)
            finally:
                response.close()
            return self.extractor.extract(body, requested_url, current_url)
        raise WebsiteFetchError("リダイレクト回数が上限を超えました")

    def fetch_text(self, url: str) -> str:
        return self.fetch(url).to_prompt_text(self.extractor.maximum_prompt_tokens)

    def _request_with_retry(self, url: str) -> requests.Response:
        headers = {
            "User-Agent": "MetaDescriptionGenerator/1.5 (+https://github.com/suzuryuquark/Meta-Description-Generator)",
            "Accept": "text/html,application/xhtml+xml",
        }
        for attempt in range(1, self.maximum_attempts + 1):
            self.validator.validate(url)
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=(self.connect_timeout, self.read_timeout),
                    stream=True,
                    allow_redirects=False,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt >= self.maximum_attempts:
                    raise WebsiteFetchError("Webサイトへの接続に失敗しました") from exc
                self.sleeper(self._backoff_delay(attempt, None))
                continue
            except requests.RequestException as exc:
                raise WebsiteFetchError("Webサイトの取得に失敗しました") from exc

            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response
            if attempt >= self.maximum_attempts:
                status_code = response.status_code
                response.close()
                raise WebsiteFetchError(
                    f"Webサイトが一時的に応答できませんでした (HTTP {status_code})"
                )
            retry_after = response.headers.get("Retry-After")
            response.close()
            self.sleeper(self._backoff_delay(attempt, retry_after))
        raise WebsiteFetchError("Webサイトの取得に失敗しました")

    def _validate_response(self, response: requests.Response) -> None:
        if response.status_code >= 400:
            raise WebsiteFetchError(f"WebサイトがHTTP {response.status_code}を返しました")
        content_type = response.headers.get("Content-Type", "").split(";", maxsplit=1)[0].lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedContentTypeError("HTMLまたはXHTML以外のページは取得できません")
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > self.maximum_response_bytes:
                    raise ResponseTooLargeError("Webページのサイズが上限を超えています")
            except ValueError as exc:
                raise WebsiteFetchError("不正なContent-Lengthが返されました") from exc

    def _read_bounded(self, response: requests.Response) -> bytes:
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > self.maximum_response_bytes:
                raise ResponseTooLargeError("Webページのサイズが上限を超えています")
            chunks.append(chunk)
        return b"".join(chunks)

    def _backoff_delay(self, attempt: int, retry_after: str | None) -> float:
        parsed_retry_after = self._parse_retry_after(retry_after)
        if parsed_retry_after is not None:
            return min(parsed_retry_after, 60.0)
        return float(min(self.backoff_factor * pow(2.0, attempt - 1), 10.0))

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                target = email.utils.parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if target.tzinfo is None:
                target = target.replace(tzinfo=UTC)
            return max(0.0, (target - datetime.now(UTC)).total_seconds())
