import asyncio
from types import SimpleNamespace
from typing import Any, cast

from models.bulk import BulkItemStatus
from models.generation import DESCRIPTION_MIN_CHARS, MetaSuggestion
from services.gemini_service import GeminiServiceError
from services.rate_limiter import AsyncRateLimiter
from services.website_fetch_service import WebsiteFetchError
from ui.bulk_view import BulkView


class FakeStorage:
    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []

    async def get_history(self):
        return self.history

    async def save_history(self, history):
        self.history = history


class FakeWebsiteFetchService:
    def __init__(self, failing_urls: set[str] | None = None) -> None:
        self.failing_urls = failing_urls or set()
        self.calls: list[str] = []

    def fetch_text(self, url: str) -> str:
        self.calls.append(url)
        if url in self.failing_urls:
            raise WebsiteFetchError("Webサイトの取得に失敗しました")
        return url


class FakeGeminiService:
    def __init__(self, critical_url: str | None = None) -> None:
        self.critical_url = critical_url

    def generate_descriptions(self, _api_key, _model_name, website_text, *_args, **_kwargs):
        if website_text == self.critical_url:
            raise GeminiServiceError("Gemini APIエラー (503): service unavailable")
        return [
            MetaSuggestion(
                title="テスト",
                title_tag="テストタイトル",
                description="説" * DESCRIPTION_MIN_CHARS,
            )
        ]


class FakeErrorService:
    def __init__(self, is_critical: bool) -> None:
        self.is_critical = is_critical
        self.calls: list[Exception] = []

    async def handle_exception(self, exc: Exception, _context: str) -> bool:
        self.calls.append(exc)
        return self.is_critical


async def noop_async(*_args) -> None:
    return None


def make_view(
    website_service: FakeWebsiteFetchService,
    gemini_service: FakeGeminiService,
    error_service: FakeErrorService,
) -> BulkView:
    view = BulkView(
        page=cast(Any, SimpleNamespace()),
        storage=cast(Any, FakeStorage()),
        error_service=error_service,
        gemini_service=cast(Any, gemini_service),
        website_fetch_service=cast(Any, website_service),
        show_status=noop_async,
        show_error=noop_async,
        load_history_cmd=noop_async,
        get_settings=lambda: {
            "api_key": "dummy-api-key",
            "model": "gemini-test",
            "global_instruction": "",
            "target_keywords": "",
            "tone": "SEO重視",
            "output_language": "日本語",
        },
        rate_limiter=AsyncRateLimiter(minimum_interval_seconds=0),
    )
    view.update = lambda: None
    return view


def test_critical_error_retries_failed_and_not_run_urls_in_original_order():
    urls = [f"https://example.com/{index}" for index in range(1, 6)]
    website_service = FakeWebsiteFetchService()
    gemini_service = FakeGeminiService(critical_url=urls[2])
    view = make_view(website_service, gemini_service, FakeErrorService(is_critical=True))

    asyncio.run(view._run_urls(urls, skipped_count=0))

    assert view.items[urls[0]].status is BulkItemStatus.SUCCESS
    assert view.items[urls[1]].status is BulkItemStatus.SUCCESS
    assert view.items[urls[2]].status is BulkItemStatus.FAILED
    assert view.items[urls[3]].status is BulkItemStatus.NOT_RUN
    assert view.items[urls[4]].status is BulkItemStatus.NOT_RUN
    assert view.retryable_urls == urls[2:]
    assert "失敗 1件 / 未実行 2件" in view.status_text.value

    website_service.calls.clear()
    gemini_service.critical_url = None
    asyncio.run(view.retry_failed_click(None))

    assert website_service.calls == urls[2:]
    assert all(item.status is BulkItemStatus.SUCCESS for item in view.items.values())
    assert view.retryable_urls == []


def test_per_url_fetch_failure_does_not_mark_later_urls_not_run():
    urls = ["https://example.com/failure", "https://example.com/success"]
    website_service = FakeWebsiteFetchService(failing_urls={urls[0]})
    error_service = FakeErrorService(is_critical=True)
    view = make_view(website_service, FakeGeminiService(), error_service)

    asyncio.run(view._run_urls(urls, skipped_count=0))

    assert view.items[urls[0]].status is BulkItemStatus.FAILED
    assert view.items[urls[1]].status is BulkItemStatus.SUCCESS
    assert view.retryable_urls == [urls[0]]
    assert error_service.calls == []


def test_user_cancelled_urls_are_not_automatically_retryable():
    urls = ["https://example.com/1", "https://example.com/2"]
    view = make_view(
        FakeWebsiteFetchService(),
        FakeGeminiService(),
        FakeErrorService(is_critical=True),
    )
    view._prepare_job(urls)

    cancelled_count = view._cancel_remaining(urls)

    assert cancelled_count == 2
    assert all(item.status is BulkItemStatus.CANCELLED for item in view.items.values())
    assert view.retryable_urls == []
