import flet as ft
import os
import datetime
import asyncio
import core_logic

class DialogManager:
    def __init__(self, page: ft.Page):
        self.page = page

    def show_about_dialog(self):
        current_year = datetime.datetime.now().year
        self.page.open(ft.AlertDialog(
            title=ft.Text("バージョン情報"),
            content=ft.Text(f"AI Meta Description Generator v1.3.0\n\n© {current_year} suzuryuquark"),
        ))

    def show_changelog_dialog(self):
        changelog_content = "更新履歴が見つかりませんでした。"
        if os.path.exists("CHANGELOG.md"):
            with open("CHANGELOG.md", "r", encoding="utf-8") as f:
                changelog_content = f.read()
        
        self.page.open(ft.AlertDialog(
            title=ft.Text("更新履歴"),
            content=ft.Container(
                content=ft.Markdown(changelog_content),
                width=600,
                height=400,
            ),
        ))

    async def show_refine_dialog(self, target_card, on_refine_success, on_status, on_error):
        refine_instruction_input = ft.TextField(
            label="修正の指示",
            hint_text="例：もっと短くして、問いかけ調で、など",
            multiline=True,
            autofocus=True,
            border=ft.InputBorder.OUTLINE,
            filled=True
        )

        async def refine_submit(e):
            if not refine_instruction_input.value:
                return
            
            self.page.close(dialog)
            on_status("修正案を生成中...")
            self.page.update()

            try:
                # Assuming the structure is known to the manager or passed via target_card properties
                # But to stay decoupled, maybe target_card should expose its original_desc
                original_desc = target_card.content.content.controls[9].value
                
                # We need some state from global scope (API key, etc.)
                # This suggests we might need to pass a context object or more args
                pass 
            except Exception as ex:
                on_error(str(ex))

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("修正して再生成"),
            content=refine_instruction_input,
            actions=[
                ft.TextButton("キャンセル", on_click=lambda _: self.page.close(dialog)),
                ft.ElevatedButton("再生成", on_click=refine_submit),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dialog)

    def show_message(self, message: str, is_error: bool = False):
        # We can use a standard SnackBar or similar here if we want to replace status_text
        # But let's stick to the current UI for now.
        pass
