import asyncio

import flet as ft

import core_logic
from services.storage_service import StorageService


class BulkView(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        storage: StorageService,
        error_service,
        show_status,
        show_error,
        load_history_cmd,
        get_settings,
    ):
        super().__init__()
        self.page = page
        self.storage = storage
        self.error_service = error_service
        self.show_status = show_status
        self.show_error = show_error
        self.load_history_cmd = load_history_cmd
        self.get_settings = get_settings
        self.padding = 10
        self.expand = True

        self.build_ui()

    def build_ui(self):
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

        self.status_text = ft.Text("")
        self.progress_bar = ft.ProgressBar(width=800, color=ft.Colors.BLUE, visible=False)
        self.results_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        self.content = ft.Column(
            [
                ft.Text(
                    "複数のサイトURLからメタデータを一括生成します。",
                    size=16,
                    color=ft.Colors.GREY_700,
                ),
                ft.Divider(),
                self.urls_input,
                self.generate_btn,
                self.status_text,
                self.progress_bar,
                ft.Divider(),
                self.results_column,
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
        )

    async def generate_bulk_click(self, e):
        raw_urls = [u.strip() for u in self.urls_input.value.split("\n") if u.strip()]
        if not raw_urls:
            return await self.show_error("URLを入力してください")

        # Remove duplicates while preserving order
        urls = list(dict.fromkeys(raw_urls))
        if len(urls) < len(raw_urls):
            await self.show_status(f"重複するURLを {len(raw_urls) - len(urls)} 件除外しました")

        # Limit checked for safety and stability
        if len(urls) > 50:
            return await self.show_error(
                f"一度に生成できるのは50件までです (現在{len(urls)}件)。件数を減らして再試行してください。"
            )

        settings = self.get_settings()
        api_key = settings.get("api_key")
        if not api_key:
            return await self.show_error("APIキーを入力してください")

        self.generate_btn.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.results_column.controls.clear()
        await self.show_status(f"一括生成を開始します ({len(urls)}件)")
        self.update()

        success_count = 0
        for i, url in enumerate(urls):
            try:
                self.status_text.value = f"処理中 ({i+1}/{len(urls)}): {url}"
                self.update()

                # Fetch and Generate
                text = await asyncio.to_thread(core_logic.fetch_website_content, url)
                suggestions = await asyncio.to_thread(
                    core_logic.generate_descriptions,
                    api_key,
                    text,
                    settings.get("global_instruction"),
                    settings.get("target_keywords"),
                    tone=settings.get("tone"),
                )

                if suggestions:
                    for item in suggestions:
                        res_card = ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.ListTile(
                                            title=ft.Text(url, weight=ft.FontWeight.BOLD),
                                            subtitle=ft.Text(
                                                f"パターン: {item['title']}",
                                                weight=ft.FontWeight.W_500,
                                            ),
                                        ),
                                        ft.Text(f"Title: {item.get('title_tag', '')}", size=12),
                                        ft.Text(f"Desc: {item['description']}", size=12),
                                    ]
                                ),
                                padding=10,
                            )
                        )
                        self.results_column.controls.append(res_card)

                    await self.save_to_history(url, suggestions)
                    success_count += 1

                self.progress_bar.value = (i + 1) / len(urls)
                self.update()
                await asyncio.sleep(1)  # Rate limit protection

            except Exception as ex:
                if await self.error_service.handle_exception(ex, f"一括生成 ({url})"):
                    # Critical error (Quota etc.) - stop processing
                    await self.show_error("致命的なエラーのため一括生成を中断しました")
                    break
                else:
                    # Individual URL Error - show simple message and continue
                    err_msg = str(ex)
                    display_err = err_msg.split(".")[0] if "." in err_msg else err_msg
                    self.results_column.controls.append(
                        ft.Text(f"エラー ({url}): {display_err}", color=ft.Colors.RED)
                    )
                self.update()

        await self.load_history_cmd()
        self.generate_btn.disabled = False
        self.progress_bar.visible = False
        self.status_text.value = f"完了！ {success_count}/{len(urls)} 件成功"
        await self.show_status("一括生成が完了しました")
        self.update()

    async def save_to_history(self, url, suggestions):
        history = await self.storage.get_history()
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in suggestions:
            history.append(
                {
                    "url": url,
                    "timestamp": timestamp,
                    "pattern": item["title"],
                    "title_tag": item.get("title_tag", ""),
                    "description": item["description"],
                }
            )
        await self.storage.save_history(history)
