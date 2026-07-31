import datetime

import flet as ft

import ui_components
from services.export_service import ExportService
from services.storage_service import StorageService


class HistoryView(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        storage: StorageService,
        export_service: ExportService,
        error_service,
        show_status,
        show_error,
    ):
        super().__init__()
        self.page = page
        self.storage = storage
        self.export_service = export_service
        self.error_service = error_service
        self.show_status = show_status
        self.show_error = show_error
        self.padding = 10
        self.expand = True

        self.build_ui()

    def build_ui(self):
        self.history_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        # FilePicker for Export
        self.csv_picker = ft.FilePicker(on_result=self.on_export_result)
        self.page.overlay.append(self.csv_picker)

        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("最近の生成履歴 (最大50件)", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "CSVエクスポート",
                                    icon=ft.Icons.DOWNLOAD,
                                    on_click=lambda e: self.page.run_task(self.export_click, e),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_SWEEP,
                                    tooltip="履歴をクリア",
                                    on_click=lambda e: self.page.run_task(
                                        self.clear_history_click, e
                                    ),
                                ),
                            ],
                            spacing=10,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.history_column,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )

    async def load_history(self):
        history = await self.storage.get_history()
        self.history_column.controls.clear()
        for entry in reversed(history):
            card = ui_components.create_history_card(entry, self.copy_to_clipboard)
            self.history_column.controls.append(card)
        self.update()

    async def clear_history_click(self, e):
        await self.storage.clear_history()
        await self.load_history()

    async def export_click(self, e):
        history = await self.storage.get_history()
        if not history:
            return await self.show_error("保存する履歴がありません")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_picker.save_file(
            file_name=f"meta_descriptions_{timestamp}.csv", allowed_extensions=["csv"]
        )

    async def on_export_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            try:
                history = await self.storage.get_history()
                self.export_service.export_history_to_csv(e.path, history)
                await self.show_status(f"CSVを保存しました: {e.path}")
            except Exception as ex:
                if not await self.error_service.handle_exception(ex, "CSVエクスポート"):
                    await self.show_error(f"保存に失敗しました: {str(ex)}")

    async def copy_to_clipboard(self, e):
        self.page.set_clipboard(e.control.data)
        self.page.open(ft.SnackBar(content=ft.Text("コピーしました！")))
