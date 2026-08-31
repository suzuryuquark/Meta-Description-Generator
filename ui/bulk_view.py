import asyncio
import uuid

import flet as ft

from models.bulk import BulkItemState, BulkItemStatus
from models.generation import DEFAULT_OUTPUT_LANGUAGE, MetaSuggestion
from services.gemini_service import GeminiService
from services.rate_limiter import AsyncRateLimiter
from services.storage_service import StorageService
from services.website_fetch_service import WebsiteFetchError, WebsiteFetchService

MAX_BULK_URLS = 50

STATUS_COLORS = {
    BulkItemStatus.PENDING: ft.Colors.BLUE_GREY,
    BulkItemStatus.FETCHING: ft.Colors.BLUE,
    BulkItemStatus.GENERATING: ft.Colors.DEEP_PURPLE,
    BulkItemStatus.SUCCESS: ft.Colors.GREEN,
    BulkItemStatus.FAILED: ft.Colors.RED,
    BulkItemStatus.CANCELLED: ft.Colors.ORANGE,
}

STATUS_ICONS = {
    BulkItemStatus.PENDING: ft.Icons.SCHEDULE,
    BulkItemStatus.FETCHING: ft.Icons.DOWNLOAD,
    BulkItemStatus.GENERATING: ft.Icons.AUTO_AWESOME,
    BulkItemStatus.SUCCESS: ft.Icons.CHECK_CIRCLE,
    BulkItemStatus.FAILED: ft.Icons.ERROR,
    BulkItemStatus.CANCELLED: ft.Icons.CANCEL,
}


class BulkView(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        storage: StorageService,
        error_service,
        gemini_service: GeminiService,
        website_fetch_service: WebsiteFetchService,
        show_status,
        show_error,
        load_history_cmd,
        get_settings,
        rate_limiter: AsyncRateLimiter | None = None,
    ) -> None:
        super().__init__()
        self.page = page
        self.storage = storage
        self.error_service = error_service
        self.gemini_service = gemini_service
        self.website_fetch_service = website_fetch_service
        self.show_status = show_status
        self.show_error = show_error
        self.load_history_cmd = load_history_cmd
        self.get_settings = get_settings
        self.rate_limiter = rate_limiter or AsyncRateLimiter()
        self.padding = 10
        self.expand = True
        self.items: dict[str, BulkItemState] = {}
        self.item_status_controls: dict[str, tuple[ft.Icon, ft.Text, ft.Text]] = {}
        self.failed_urls: list[str] = []
        self._cancel_requested = False
        self._is_running = False

        self.build_ui()

    def build_ui(self) -> None:
        self.urls_input = ft.TextField(
            label="URLリスト (最大50件 / 1行に1つのURL)",
            hint_text="https://example.com/page1\nhttps://example.com/page2",
            multiline=True,
            min_lines=5,
            max_lines=10,
            width=800,
            border=ft.InputBorder.OUTLINE,
            filled=True,
        )

        self.generate_btn = ft.ElevatedButton(
            text="一括生成を開始",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            on_click=lambda e: self.page.run_task(self.generate_bulk_click, e),
        )
        self.cancel_btn = ft.OutlinedButton(
            text="キャンセル",
            icon=ft.Icons.CANCEL,
            disabled=True,
            on_click=self.cancel_bulk_click,
        )
        self.retry_failed_btn = ft.OutlinedButton(
            text="失敗URLだけ再実行",
            icon=ft.Icons.REFRESH,
            disabled=True,
            on_click=lambda e: self.page.run_task(self.retry_failed_click, e),
        )

        self.status_text = ft.Text("")
        self.progress_bar = ft.ProgressBar(width=800, color=ft.Colors.BLUE, visible=False)
        self.item_status_column = ft.Column(spacing=6)
        self.results_column = ft.Column(spacing=10)

        self.content = ft.Column(
            [
                ft.Text(
                    "複数のサイトURLからメタデータを一括生成します。",
                    size=16,
                    color=ft.Colors.GREY_700,
                ),
                ft.Divider(),
                self.urls_input,
                ft.Row([self.generate_btn, self.cancel_btn, self.retry_failed_btn]),
                self.status_text,
                self.progress_bar,
                self.item_status_column,
                ft.Divider(),
                self.results_column,
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
        )

    async def generate_bulk_click(self, _event) -> None:
        raw_urls = [
            url.strip() for url in (self.urls_input.value or "").splitlines() if url.strip()
        ]
        if not raw_urls:
            await self.show_error("URLを入力してください")
            return

        urls = list(dict.fromkeys(raw_urls))
        duplicate_count = len(raw_urls) - len(urls)
        if len(urls) > MAX_BULK_URLS:
            await self.show_error(
                f"一度に生成できるのは{MAX_BULK_URLS}件までです "
                f"(現在{len(urls)}件)。件数を減らして再試行してください。"
            )
            return
        await self._run_urls(urls, skipped_count=duplicate_count)

    async def retry_failed_click(self, _event) -> None:
        if self._is_running or not self.failed_urls:
            return
        await self._run_urls(list(self.failed_urls), skipped_count=0)

    def cancel_bulk_click(self, _event) -> None:
        if self._is_running:
            self._cancel_requested = True
            self.cancel_btn.disabled = True
            self.status_text.value = (
                "キャンセルしています。現在の処理が終了するまでお待ちください..."
            )
            self.update()

    async def _run_urls(self, urls: list[str], *, skipped_count: int) -> None:
        settings = self.get_settings()
        api_key = (settings.get("api_key") or "").strip()
        model_name = (settings.get("model") or "").strip()
        if not api_key:
            await self.show_error("APIキーを入力してください")
            return
        if not model_name:
            await self.show_error("使用するGeminiモデルを指定してください")
            return

        self._prepare_job(urls)
        success_count = 0
        failed_count = 0
        cancelled_count = 0

        try:
            for index, url in enumerate(urls):
                if self._is_cancel_requested():
                    cancelled_count += self._cancel_remaining(urls[index:])
                    break

                try:
                    self._set_item_status(url, BulkItemStatus.FETCHING)
                    self.status_text.value = f"取得中 ({index + 1}/{len(urls)}): {url}"
                    self.update()
                    website_text = await asyncio.to_thread(
                        self.website_fetch_service.fetch_text, url
                    )

                    if self._is_cancel_requested():
                        self._set_item_status(url, BulkItemStatus.CANCELLED)
                        cancelled_count += 1
                        cancelled_count += self._cancel_remaining(urls[index + 1 :])
                        break

                    await self.rate_limiter.acquire()
                    self._set_item_status(url, BulkItemStatus.GENERATING)
                    self.status_text.value = f"生成中 ({index + 1}/{len(urls)}): {url}"
                    self.update()
                    suggestions = await asyncio.to_thread(
                        self.gemini_service.generate_descriptions,
                        api_key,
                        model_name,
                        website_text,
                        settings.get("global_instruction"),
                        settings.get("target_keywords"),
                        tone=settings.get("tone"),
                        output_language=(
                            settings.get("output_language") or DEFAULT_OUTPUT_LANGUAGE
                        ),
                    )

                    if self._is_cancel_requested():
                        self._set_item_status(url, BulkItemStatus.CANCELLED)
                        cancelled_count += 1
                        cancelled_count += self._cancel_remaining(urls[index + 1 :])
                        break

                    self._append_results(url, suggestions)
                    await self.save_to_history(url, suggestions, model_name)
                    self._set_item_status(
                        url, BulkItemStatus.SUCCESS, f"{len(suggestions)}案を履歴へ保存"
                    )
                    success_count += 1
                except Exception as exc:
                    failed_count += 1
                    self.failed_urls.append(url)
                    message = self._safe_error_message(exc)
                    self._set_item_status(url, BulkItemStatus.FAILED, message)
                    if not isinstance(exc, WebsiteFetchError):
                        is_critical = await self.error_service.handle_exception(
                            exc, f"一括生成 ({url})"
                        )
                        if is_critical:
                            cancelled_count += self._cancel_remaining(urls[index + 1 :])
                            break
                finally:
                    self.progress_bar.value = (index + 1) / len(urls)
                    self.update()
        finally:
            try:
                await self.load_history_cmd()
            finally:
                self._finish_job(success_count, failed_count, skipped_count, cancelled_count)

    def _prepare_job(self, urls: list[str]) -> None:
        self._is_running = True
        self._cancel_requested = False
        self.failed_urls = []
        self.items = {url: BulkItemState(url) for url in urls}
        self.item_status_controls.clear()
        self.item_status_column.controls.clear()
        self.results_column.controls.clear()
        for url in urls:
            self._create_status_row(url)
        self.generate_btn.disabled = True
        self.retry_failed_btn.disabled = True
        self.cancel_btn.disabled = False
        self.urls_input.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.status_text.value = f"一括生成を開始します ({len(urls)}件)"
        self.update()

    def _finish_job(
        self,
        success_count: int,
        failed_count: int,
        skipped_count: int,
        cancelled_count: int,
    ) -> None:
        self._is_running = False
        self.generate_btn.disabled = False
        self.cancel_btn.disabled = True
        self.retry_failed_btn.disabled = not self.failed_urls
        self.urls_input.disabled = False
        self.progress_bar.visible = False
        self.status_text.value = (
            f"完了: 成功 {success_count}件 / 失敗 {failed_count}件 / "
            f"スキップ {skipped_count}件 / キャンセル {cancelled_count}件"
        )
        self.update()

    def _cancel_remaining(self, urls: list[str]) -> int:
        for url in urls:
            self._set_item_status(url, BulkItemStatus.CANCELLED)
        return len(urls)

    def _is_cancel_requested(self) -> bool:
        return self._cancel_requested

    def _create_status_row(self, url: str) -> None:
        icon = ft.Icon(
            STATUS_ICONS[BulkItemStatus.PENDING], color=STATUS_COLORS[BulkItemStatus.PENDING]
        )
        status = ft.Text(BulkItemStatus.PENDING.value, width=90)
        message = ft.Text("", size=11, color=ft.Colors.BLUE_GREY)
        self.item_status_controls[url] = (icon, status, message)
        self.item_status_column.controls.append(
            ft.Container(
                content=ft.Row(
                    [icon, ft.Text(url, expand=True, selectable=True), status, message],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=8,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=6,
            )
        )

    def _set_item_status(self, url: str, status: BulkItemStatus, message: str = "") -> None:
        self.items[url].update(status, message)
        icon, status_text, message_text = self.item_status_controls[url]
        icon.name = STATUS_ICONS[status]
        icon.color = STATUS_COLORS[status]
        status_text.value = status.value
        status_text.color = STATUS_COLORS[status]
        message_text.value = message

    def _append_results(self, url: str, suggestions: list[MetaSuggestion]) -> None:
        for item in suggestions:
            self.results_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    title=ft.Text(url, weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text(
                                        f"パターン: {item.title}", weight=ft.FontWeight.W_500
                                    ),
                                ),
                                ft.Text(f"Title: {item.title_tag}", size=12),
                                ft.Text(f"Desc: {item.description}", size=12),
                            ]
                        ),
                        padding=10,
                    )
                )
            )

    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        if isinstance(exc, WebsiteFetchError):
            return str(exc)
        return "生成処理に失敗しました"

    async def save_to_history(
        self, url: str, suggestions: list[MetaSuggestion], model_name: str
    ) -> None:
        history = await self.storage.get_history()
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in suggestions:
            history.append(
                {
                    "url": url,
                    "id": uuid.uuid4().hex,
                    "timestamp": timestamp,
                    "model": model_name,
                    "status": "生成結果",
                    "pattern": item.title,
                    "title_tag": item.title_tag,
                    "description": item.description,
                }
            )
        await self.storage.save_history(history)
