import datetime
import os

import flet as ft


class DialogManager:
    def __init__(self, page: ft.Page):
        self.page = page

    def show_about_dialog(self):
        current_year = datetime.datetime.now().year
        self.page.open(
            ft.AlertDialog(
                title=ft.Text("バージョン情報"),
                content=ft.Text(
                    f"AI Meta Description Generator v1.5.1\n\n© {current_year} suzuryuquark"
                ),
            )
        )

    def show_changelog_dialog(self):
        changelog_content = "更新履歴が見つかりませんでした。"
        if os.path.exists("CHANGELOG.md"):
            with open("CHANGELOG.md", encoding="utf-8") as f:
                changelog_content = f.read()

        self.page.open(
            ft.AlertDialog(
                title=ft.Text("更新履歴"),
                content=ft.Container(
                    content=ft.Markdown(changelog_content),
                    width=600,
                    height=400,
                ),
            )
        )
