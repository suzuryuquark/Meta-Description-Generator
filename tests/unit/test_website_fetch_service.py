from collections.abc import Iterable

import pytest

from models.website import estimate_prompt_tokens
from services.website_fetch_service import (
    ResponseTooLargeError,
    UnsupportedContentTypeError,
    UrlValidationError,
    UrlValidator,
    WebsiteContentExtractor,
    WebsiteFetchService,
)


def public_resolver(_host: str, _port: int) -> Iterable[str]:
    return ["93.184.216.34"]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "http://user:password@example.com/",
        "http://localhost/",
        "http://service.localhost/",
        "https://example.com:0/",
        "https://example.com:99999/",
        "https://example.com/path\nheader",
    ],
)
def test_url_validator_rejects_unsafe_or_invalid_urls(url: str) -> None:
    validator = UrlValidator(resolver=public_resolver)

    with pytest.raises(UrlValidationError):
        validator.validate(url)


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.1", "169.254.169.254", "192.0.2.1", "::1", "fc00::1"],
)
def test_url_validator_rejects_non_global_dns_results(address: str) -> None:
    validator = UrlValidator(resolver=lambda _host, _port: [address])

    with pytest.raises(UrlValidationError):
        validator.validate("https://example.com/")


def test_url_validator_accepts_public_http_url() -> None:
    validated = UrlValidator(resolver=public_resolver).validate("https://example.com:8443/page")

    assert validated.host == "example.com"
    assert validated.port == 8443
    assert validated.addresses == ("93.184.216.34",)


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        *,
        headers: dict[str, str] | None = None,
        chunks: list[bytes] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}
        self.chunks = chunks or [b"<html><main><p>content</p></main></html>"]
        self.closed = False

    @property
    def is_redirect(self) -> bool:
        return self.status_code in {301, 302, 303, 307, 308}

    @property
    def is_permanent_redirect(self) -> bool:
        return self.status_code in {301, 308}

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield from self.chunks

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.trust_env = True

    def get(self, url: str, **_kwargs) -> FakeResponse:
        self.calls.append(url)
        return self.responses.pop(0)


def make_service(
    responses: list[FakeResponse],
    *,
    resolver=public_resolver,
    sleeper=lambda _seconds: None,
    maximum_response_bytes: int = 2 * 1024 * 1024,
) -> tuple[WebsiteFetchService, FakeSession]:
    session = FakeSession(responses)
    service = WebsiteFetchService(
        validator=UrlValidator(resolver=resolver),
        session=session,  # type: ignore[arg-type]
        sleeper=sleeper,
        maximum_response_bytes=maximum_response_bytes,
    )
    return service, session


def test_redirect_target_is_validated_before_second_request() -> None:
    response = FakeResponse(302, headers={"Location": "http://127.0.0.1/private"})
    service, session = make_service([response])

    with pytest.raises(UrlValidationError):
        service.fetch("https://example.com/start")

    assert session.calls == ["https://example.com/start"]
    assert response.closed


def test_fetch_retries_retry_after_status() -> None:
    waits: list[float] = []
    service, session = make_service(
        [
            FakeResponse(429, headers={"Retry-After": "2"}),
            FakeResponse(chunks=[b"<html><main><p>success</p></main></html>"]),
        ],
        sleeper=waits.append,
    )

    page = service.fetch("https://example.com/")

    assert page.content == "success"
    assert len(session.calls) == 2
    assert waits == [2.0]


def test_fetch_revalidates_dns_for_each_retry() -> None:
    resolutions: list[int] = []

    def resolver(_host: str, _port: int) -> Iterable[str]:
        resolutions.append(1)
        return ["93.184.216.34"]

    service, _ = make_service(
        [FakeResponse(503), FakeResponse()],
        resolver=resolver,
    )

    service.fetch("https://example.com/")

    assert len(resolutions) == 2


def test_fetch_rejects_content_length_over_limit() -> None:
    service, _ = make_service(
        [FakeResponse(headers={"Content-Type": "text/html", "Content-Length": "11"})],
        maximum_response_bytes=10,
    )

    with pytest.raises(ResponseTooLargeError):
        service.fetch("https://example.com/")


def test_fetch_stops_stream_over_limit() -> None:
    service, _ = make_service(
        [FakeResponse(chunks=[b"12345", b"678901"])], maximum_response_bytes=10
    )

    with pytest.raises(ResponseTooLargeError):
        service.fetch("https://example.com/")


def test_fetch_rejects_non_html_content() -> None:
    service, _ = make_service([FakeResponse(headers={"Content-Type": "application/pdf"})])

    with pytest.raises(UnsupportedContentTypeError):
        service.fetch("https://example.com/")


def test_extractor_prioritizes_main_and_collects_metadata() -> None:
    html = b"""
    <html lang="ja"><head>
      <title> Example  Page </title>
      <meta name="description" content="Current description">
      <meta name="robots" content="index,follow">
      <meta property="og:title" content="OG title">
      <link rel="canonical" href="/canonical">
      <script type="application/ld+json">
        {"@type":"Article","headline":"Structured headline"}
      </script>
    </head><body>
      <nav><p>navigation text</p></nav>
      <main>
        <h1>Main heading</h1><p>Repeated paragraph</p><p>Repeated paragraph</p>
        <ul><li>List item</li></ul>
        <div class="cookie-consent"><p>Cookie notice</p></div>
      </main>
      <article><p>Ignored article because main exists</p></article>
    </body></html>
    """

    page = WebsiteContentExtractor().extract(
        html, "https://example.com/start", "https://example.com/final"
    )

    assert page.metadata.title == "Example Page"
    assert page.metadata.canonical_url == "https://example.com/canonical"
    assert page.metadata.robots == "index,follow"
    assert page.metadata.language == "ja"
    assert page.metadata.open_graph == {"og:title": "OG title"}
    assert page.metadata.structured_data == ("type=Article; headline=Structured headline",)
    assert page.content.splitlines() == ["Main heading", "Repeated paragraph", "List item"]


def test_prompt_text_obeys_budget() -> None:
    html = f"<html><main><p>{'x' * 500}</p></main></html>".encode()
    extractor = WebsiteContentExtractor(maximum_prompt_tokens=120)
    page = extractor.extract(html, "https://example.com", "https://example.com")

    prompt = page.to_prompt_text(120)
    assert estimate_prompt_tokens(prompt) <= 120
    assert len(prompt) > 120


def test_extractor_summarizes_product_and_faq_structured_data() -> None:
    html = b"""
    <html><body><main><p>Content</p></main>
      <script type="application/ld+json">
      [
        {"@type":"Product","name":"Widget","brand":{"name":"Example"},
         "offers":{"price":"1000","priceCurrency":"JPY"}},
        {"@type":"FAQPage","mainEntity":[
          {"@type":"Question","name":"Question?",
           "acceptedAnswer":{"@type":"Answer","text":"Answer."}}
        ]}
      ]
      </script>
    </body></html>
    """

    page = WebsiteContentExtractor().extract(html, "https://example.com", "https://example.com")

    assert page.metadata.structured_data == (
        "type=Product; name=Widget; brand=Example; offer(price=1000,priceCurrency=JPY)",
        "type=FAQPage; questions=Question? -> Answer.",
    )
