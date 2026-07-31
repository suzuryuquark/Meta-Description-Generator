import flet as ft

from services.error_service import ErrorService
from services.export_service import ExportService
from services.gemini_service import GeminiService
from services.storage_service import StorageService
from ui.bulk_view import BulkView
from ui.dialogs import DialogManager
from ui.generate_view import GenerateView
from ui.history_view import HistoryView


async def main(page: ft.Page):
    page.title = "AI Meta Description Generator"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.window.width = 1200
    page.window.height = 1200
    page.window.center()
    page.scroll = None

    async def handle_disconnect(e):
        import os

        os._exit(0)

    page.on_disconnect = handle_disconnect

    # Initialize Services
    storage = StorageService(page)
    export_service = ExportService()
    gemini_service = GeminiService()
    error_service = ErrorService(page)
    dialogs = DialogManager(page)

    # Status Bar State
    status_text = ft.Text("")
    status_container = ft.Container(
        content=status_text,
        padding=10,
        bgcolor=ft.Colors.BLUE_GREY_50,
        border=ft.border.only(top=ft.BorderSide(1, ft.Colors.BLUE_GREY_100)),
        width=float("inf"),
        height=50,
    )

    async def show_status(message):
        status_text.value = message
        status_text.color = ft.Colors.BLUE
        status_text.update()

    async def show_error(message):
        status_text.value = f"エラー: {message}"
        status_text.color = ft.Colors.RED
        status_text.update()

    # Views
    history_view = HistoryView(
        page, storage, export_service, error_service, show_status, show_error
    )

    generate_view = GenerateView(
        page,
        storage,
        error_service,
        gemini_service,
        show_status,
        show_error,
        load_history_cmd=history_view.load_history,
    )

    bulk_view = BulkView(
        page,
        storage,
        error_service,
        gemini_service,
        show_status,
        show_error,
        load_history_cmd=history_view.load_history,
        get_settings=lambda: {
            "api_key": generate_view.api_key_input.value,
            "model": generate_view.model_dropdown.value,
            "global_instruction": generate_view.global_instruction_input.value,
            "target_keywords": generate_view.target_keywords_input.value,
            "tone": generate_view.tone_dropdown.value,
        },
    )

    def toggle_theme(_):
        page.theme_mode = (
            ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        )
        page.update()

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.AUTO_AWESOME),
        title=ft.Text("AI Meta Description Generator"),
        bgcolor=ft.Colors.BLUE_GREY_50,
        actions=[
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(
                        text="CSVエクスポート",
                        icon=ft.Icons.DOWNLOAD,
                        on_click=history_view.export_click,
                    ),
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(
                        text="テーマ切替",
                        on_click=toggle_theme,
                    ),
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(
                        text="GitHub",
                        on_click=lambda _: page.launch_url(
                            "https://github.com/suzuryuquark/Meta-Description-Generator"
                        ),
                    ),
                    ft.PopupMenuItem(
                        text="更新履歴", on_click=lambda _: dialogs.show_changelog_dialog()
                    ),
                    ft.PopupMenuItem(text="情報", on_click=lambda _: dialogs.show_about_dialog()),
                ]
            ),
        ],
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="生成", icon=ft.Icons.CREATE, content=generate_view),
            ft.Tab(text="一括生成", icon=ft.Icons.BATCH_PREDICTION, content=bulk_view),
            ft.Tab(text="履歴", icon=ft.Icons.HISTORY, content=history_view),
        ],
        expand=True,
    )

    page.add(ft.Column([tabs, status_container], expand=True))

    # Initial Load
    await storage.migrate_settings()
    await generate_view.initialize()
    await history_view.load_history()
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
