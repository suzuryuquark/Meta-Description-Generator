import flet as ft
import traceback

class ErrorService:
    def __init__(self, page: ft.Page):
        self.page = page

    async def handle_exception(self, ex: Exception, context: str = ""):
        """
        統一的なエラーハンドリングを行います。
        429 (Quota) などの特定のエラーはダイアログで通知し、
        それ以外はスナックバーや結果エリアでの表示を想定した処理を行います。
        """
        err_msg = str(ex)
        print(f"Error in {context}: {err_msg}")
        traceback.print_exc()

        if "429" in err_msg or "quota" in err_msg.lower():
            # Critical Quota Error
            dialog = ft.AlertDialog(
                title=ft.Text("クォータ制限に達しました"),
                content=ft.Text(f"{context}中にAI APIの利用制限（クォータ）に達しました。しばらく時間をおいてから再試行するか、APIプランを確認してください。"),
                actions=[ft.TextButton("閉じる", on_click=lambda _: self.page.close(dialog))]
            )
            self.page.open(dialog)
            return True # Indicates critical error handled
        
        elif "503" in err_msg or "service unavailable" in err_msg.lower():
            # Service Temporary Unavailable
            dialog = ft.AlertDialog(
                title=ft.Text("サービスが一時的に利用不可"),
                content=ft.Text("AIサービスが一時的に混み合っているか、メンテナンス中です。数分待ってから再度お試しください。"),
                actions=[ft.TextButton("閉じる", on_click=lambda _: self.page.close(dialog))]
            )
            self.page.open(dialog)
            return True
            
        elif "制限されました" in err_msg or "ブロックされました" in err_msg or "finish_reason" in err_msg:
            # Safety Filter or Content Block
            dialog = ft.AlertDialog(
                title=ft.Text("AIによる生成制限"),
                content=ft.Text(f"{context}中にAIのガイドラインやポリシーにより生成が制限されました。指示文の内容を見直すか、別のURLでお試しください。\n\n詳細: {err_msg}"),
                actions=[ft.TextButton("閉じる", on_click=lambda _: self.page.close(dialog))]
            )
            self.page.open(dialog)
            return True

        # Generic Error Handling (could be displayed via show_error helper in views)
        return False # Indicates generic error, view should handle UI display
