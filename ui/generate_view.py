import asyncio
import datetime

import flet as ft

import ui_components
from models.generation import (
    DEFAULT_GEMINI_MODEL,
)
from services.gemini_service import GeminiService
from services.storage_service import StorageService
from services.website_fetch_service import WebsiteFetchService


class GenerateView(ft.Container):
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
    ):
        super().__init__()
        self.page = page
        self.storage = storage
        self.error_service = error_service
        self.gemini_service = gemini_service
        self.website_fetch_service = website_fetch_service
        self.show_status = show_status
        self.show_error = show_error
        self.load_history_cmd = load_history_cmd
        self.padding = 10
        self.expand = True

        self.current_website_text = ""

        self.build_ui()

    def build_ui(self):
        # API Key
        self.api_key_input = ft.TextField(
            label="Gemini APIキー",
            password=True,
            can_reveal_password=True,
            width=400,
            border=ft.InputBorder.OUTLINE,
            filled=True,
        )
        self.save_key_btn = ft.IconButton(
            icon=ft.Icons.SAVE, tooltip="APIキーを保存", on_click=self.save_api_key_click
        )

        self.model_dropdown = ft.Dropdown(
            label="使用するGeminiモデル",
            width=600,
            editable=True,
            enable_filter=True,
            enable_search=True,
            value=DEFAULT_GEMINI_MODEL,
            options=[
                ft.dropdown.Option(
                    key=DEFAULT_GEMINI_MODEL,
                    text=DEFAULT_GEMINI_MODEL,
                )
            ],
            helper_text="一覧から選択するか、モデルIDを直接入力できます",
            on_change=self.on_model_change,
        )
        self.refresh_models_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="利用可能なモデル一覧を更新",
            on_click=lambda e: self.page.run_task(self.refresh_models_click, e),
        )

        # Templates
        self.template_dropdown = ft.Dropdown(
            label="テンプレートを選択", width=300, options=[], on_change=self.on_template_change
        )

        # Instructions & Keywords
        self.global_instruction_input = ft.TextField(
            label="サイト共通の指示",
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=800,
            border=ft.InputBorder.OUTLINE,
            filled=True,
        )
        self.target_keywords_input = ft.TextField(
            label="ターゲットキーワード (カンマ区切り)",
            width=800,
            border=ft.InputBorder.OUTLINE,
            filled=True,
        )

        # URL Inputs
        self.domain_input = ft.TextField(
            label="ドメイン (https://...)", width=400, border=ft.InputBorder.OUTLINE, filled=True
        )
        self.path_input = ft.TextField(
            label="パス (/page/...)", width=700, border=ft.InputBorder.OUTLINE, filled=True
        )

        # Tone
        self.tone_dropdown = ft.Dropdown(
            label="トーン＆スタイル",
            width=800,
            options=[
                ft.dropdown.Option("SEO重視 (デフォルト)"),
                ft.dropdown.Option("プロフェッショナル (信頼感重視)"),
                ft.dropdown.Option("親しみやすい (カジュアル)"),
                ft.dropdown.Option("キャッチー (クリック誘発)"),
                ft.dropdown.Option("メリット強調 (ベネフィット前面)"),
            ],
            value="SEO重視 (デフォルト)",
        )

        self.generate_btn = ft.ElevatedButton(
            text="生成する",
            icon=ft.Icons.AUTO_AWESOME,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            on_click=lambda e: self.page.run_task(self.generate_descriptions_click, e),
        )

        self.results_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        self.content = ft.Column(
            [
                ft.Text(
                    "WebサイトのURLから最適なdescriptionを3パターン提案します。",
                    size=16,
                    color=ft.Colors.GREY_700,
                ),
                ft.Divider(),
                ft.Row(
                    [self.api_key_input, self.save_key_btn], alignment=ft.MainAxisAlignment.START
                ),
                ft.Row(
                    [self.model_dropdown, self.refresh_models_btn],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Row(
                    [
                        self.template_dropdown,
                        ft.IconButton(
                            ft.Icons.ADD_BOX_OUTLINED,
                            tooltip="新規テンプレートとして保存",
                            on_click=self.new_template_click,
                        ),
                        ft.IconButton(
                            ft.Icons.SAVE,
                            tooltip="現在のテンプレートに上書き保存",
                            on_click=self.save_template_click,
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE,
                            tooltip="選択中のテンプレートを削除",
                            on_click=self.delete_template_click,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                self.global_instruction_input,
                self.target_keywords_input,
                ft.Row(
                    [self.domain_input, ft.Text("/", size=20), self.path_input],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.tone_dropdown,
                self.generate_btn,
                ft.Divider(),
                self.results_column,
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
        )

    async def initialize(self):
        # API key is preserved
        self.api_key_input.value = await self.storage.get_api_key() or ""
        saved_model = await self.storage.get_gemini_model()
        self.model_dropdown.value = saved_model
        self.model_dropdown.options = [ft.dropdown.Option(key=saved_model, text=saved_model)]

        # Other fields are cleared on startup as requested
        self._clear_inputs(include_instruction=True)

        await self.load_templates()
        self.template_dropdown.value = None  # Ensure unselected on start
        self.update()

    def _clear_inputs(self, include_instruction=True):
        if include_instruction:
            self.global_instruction_input.value = ""
        self.target_keywords_input.value = ""
        self.domain_input.value = ""
        self.path_input.value = ""
        self.tone_dropdown.value = "SEO重視 (デフォルト)"
        self.results_column.controls.clear()

    async def load_templates(self):
        templates = await self.storage.get_templates()
        self.template_dropdown.options = [ft.dropdown.Option(name) for name in templates.keys()]
        # 現在選択されているテンプレートが存在しなくなった場合はクリアする
        if self.template_dropdown.value not in templates:
            self.template_dropdown.value = None
        self.update()

    async def on_template_change(self, e):
        templates = await self.storage.get_templates()
        name = e.control.value
        if name in templates:
            data = templates[name]
            if isinstance(data, dict):
                self.global_instruction_input.value = data.get("instruction", "")
                self.target_keywords_input.value = data.get("keywords", "")
                self.domain_input.value = data.get("domain", "")
                self.path_input.value = data.get("path", "")
                self.tone_dropdown.value = data.get("tone", "SEO重視 (デフォルト)")
            else:
                # Legacy support for string-only templates
                self.global_instruction_input.value = data
            self.update()

    async def save_api_key_click(self, e):
        await self.storage.save_api_key(self.api_key_input.value)
        await self.storage.save_gemini_model(
            (self.model_dropdown.value or DEFAULT_GEMINI_MODEL).strip()
        )
        await self.show_status("APIキーを保存しました")

    async def on_model_change(self, e):
        model_name = (e.control.value or "").strip()
        if model_name:
            await self.storage.save_gemini_model(model_name)

    async def refresh_models_click(self, e):
        api_key = (self.api_key_input.value or "").strip()
        if not api_key:
            return await self.show_error("モデル一覧の取得にはAPIキーが必要です")

        current_model = (self.model_dropdown.value or DEFAULT_GEMINI_MODEL).strip()
        self.refresh_models_btn.disabled = True
        await self.show_status("利用可能なGeminiモデルを取得中...")
        self.update()
        try:
            models = await asyncio.to_thread(self.gemini_service.list_models, api_key)
            options = [
                ft.dropdown.Option(
                    key=model.model_id,
                    text=model.option_label,
                )
                for model in models
            ]
            if current_model not in {model.model_id for model in models}:
                options.insert(
                    0,
                    ft.dropdown.Option(
                        key=current_model,
                        text=f"{current_model} [現在の設定]",
                    ),
                )
            self.model_dropdown.options = options
            self.model_dropdown.value = current_model
            await self.show_status(f"利用可能なモデルを{len(models)}件取得しました")
        except Exception as ex:
            if not await self.error_service.handle_exception(ex, "モデル一覧取得"):
                await self.show_error(str(ex))
        finally:
            self.refresh_models_btn.disabled = False
            self.update()

    async def save_template_click(self, e):
        # Overwrite current selection
        name = self.template_dropdown.value
        if not name:
            return await self.show_error(
                "上書きするテンプレートを選択してください。新規作成は '+' ボタンを使用してください。"
            )

        templates = await self.storage.get_templates()
        templates[name] = {
            "instruction": self.global_instruction_input.value,
            "keywords": self.target_keywords_input.value,
            "domain": self.domain_input.value,
            "path": self.path_input.value,
            "tone": self.tone_dropdown.value,
        }
        await self.storage.save_templates(templates)
        await self.show_status(f"テンプレート '{name}' を更新しました")

    async def new_template_click(self, e):
        async def confirm_save(e):
            name = name_input.value.strip()
            if not name:
                return
            templates = await self.storage.get_templates()
            if name in templates:
                # Basic name duplication check
                self.page.open(
                    ft.SnackBar(content=ft.Text("同じ名前のテンプレートが既に存在します。"))
                )
                return

            templates[name] = {
                "instruction": self.global_instruction_input.value,
                "keywords": self.target_keywords_input.value,
                "domain": self.domain_input.value,
                "path": self.path_input.value,
                "tone": self.tone_dropdown.value,
            }
            await self.storage.save_templates(templates)
            self.page.close(dialog)
            await self.load_templates()

            # Select the new template
            self.template_dropdown.value = name

            # Clear other fields (except the instruction that was just saved)
            self._clear_inputs(include_instruction=False)

            self.update()
            await self.show_status(f"新規テンプレート '{name}' を作成しました")

        name_input = ft.TextField(label="新規テンプレート名", autofocus=True)
        dialog: ft.AlertDialog
        dialog = ft.AlertDialog(
            title=ft.Text("新規テンプレートとして保存"),
            content=name_input,
            actions=[
                ft.TextButton("キャンセル", on_click=lambda _: self.page.close(dialog)),
                ft.ElevatedButton("作成", on_click=confirm_save),
            ],
        )
        self.page.open(dialog)

    async def delete_template_click(self, e):
        name = self.template_dropdown.value
        if not name:
            return await self.show_error("削除するテンプレートを選択してください。")

        async def confirm_delete(e):
            templates = await self.storage.get_templates()
            if name in templates:
                del templates[name]
                await self.storage.save_templates(templates)
                self.page.close(dialog)

                # Clear value first, then reload to ensure consistency
                self.template_dropdown.value = None
                await self.load_templates()

                # Clear all fields on delete
                self._clear_inputs(include_instruction=True)

                self.update()
                await self.show_status(f"テンプレート '{name}' を削除しました")

        dialog: ft.AlertDialog
        dialog = ft.AlertDialog(
            title=ft.Text("テンプレートの削除"),
            content=ft.Text(f"テンプレート '{name}' を削除してもよろしいですか？"),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda _: self.page.close(dialog)),
                ft.ElevatedButton(
                    "削除", on_click=confirm_delete, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE
                ),
            ],
        )
        self.page.open(dialog)

    async def generate_descriptions_click(self, e):
        api_key = self.api_key_input.value
        model_name = (self.model_dropdown.value or "").strip()
        domain = self.domain_input.value.strip().rstrip("/")
        path = self.path_input.value.strip().lstrip("/")
        url = f"{domain}/{path}"

        # Save current settings
        await self.storage.save_global_instruction(self.global_instruction_input.value)
        await self.storage.save_target_keywords(self.target_keywords_input.value)
        await self.storage.save_last_domain(domain)
        if model_name:
            await self.storage.save_gemini_model(model_name)

        if not api_key:
            return await self.show_error("APIキーを入力してください")
        if not model_name:
            return await self.show_error("使用するGeminiモデルを指定してください")
        if not domain:
            return await self.show_error("ドメインを入力してください")

        self.results_column.controls.clear()
        await self.show_status("Webサイトを解析中...")
        self.generate_btn.disabled = True
        self.update()

        try:
            self.current_website_text = await asyncio.to_thread(
                self.website_fetch_service.fetch_text, url
            )

            await self.show_status("AIが説明文を生成中...")
            suggestions = await asyncio.to_thread(
                self.gemini_service.generate_descriptions,
                api_key,
                model_name,
                self.current_website_text,
                self.global_instruction_input.value,
                self.target_keywords_input.value,
                tone=self.tone_dropdown.value,
            )

            cards = []
            for item in suggestions:
                card = ui_components.create_result_card(
                    item,
                    domain,
                    path,
                    model_name,
                    self.copy_to_clipboard,
                    self.open_refine_dialog,
                    self.save_result_history_click,
                )
                self.results_column.controls.append(card)
                cards.append(card)

            await self.save_to_history(cards)
            await self.load_history_cmd()
            await self.show_status("生成完了！")

        except Exception as ex:
            if not await self.error_service.handle_exception(ex, "通常生成"):
                await self.show_error(str(ex))

        self.generate_btn.disabled = False
        self.update()

    async def save_to_history(self, cards: list[ui_components.ResultCard]):
        history = await self.storage.get_history()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for card in cards:
            history.append(self._history_entry(card, timestamp, "生成結果"))
        await self.storage.save_history(history)

    async def save_result_history_click(self, e):
        card = e.control.data
        if not isinstance(card, ui_components.ResultCard):
            return await self.show_error("保存対象の生成結果を特定できませんでした")
        await self.persist_result_card(card)
        await self.load_history_cmd()
        await self.show_status("編集内容を履歴へ反映しました")

    async def persist_result_card(self, card: ui_components.ResultCard):
        history = await self.storage.get_history()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_entry = self._history_entry(card, timestamp, "編集済み")
        for index, entry in enumerate(history):
            if entry.get("id") == card.history_id:
                updated_entry["timestamp"] = entry.get("timestamp", timestamp)
                updated_entry["updated_at"] = timestamp
                history[index] = updated_entry
                break
        else:
            history.append(updated_entry)
        await self.storage.save_history(history)

    @staticmethod
    def _history_entry(
        card: ui_components.ResultCard, timestamp: str, status: str
    ) -> dict[str, str]:
        return {
            "id": card.history_id,
            "url": card.url,
            "timestamp": timestamp,
            "model": card.model_name,
            "status": status,
            "pattern": card.pattern,
            "title_tag": card.title_tag,
            "description": card.description,
        }

    async def copy_to_clipboard(self, e):
        self.page.set_clipboard(e.control.data)
        self.page.open(ft.SnackBar(content=ft.Text("コピーしました！")))

    async def open_refine_dialog(self, e):
        target_card = e.control.data
        if not isinstance(target_card, ui_components.ResultCard):
            return await self.show_error("修正対象の生成結果を特定できませんでした")
        refine_input = ft.TextField(label="修正の指示", multiline=True, autofocus=True, filled=True)

        async def submit(e):
            if not refine_input.value:
                return
            self.page.close(dialog)
            await self.show_status("修正案を生成中...")

            try:
                model_name = (self.model_dropdown.value or "").strip()
                refined = await asyncio.to_thread(
                    self.gemini_service.refine_description,
                    self.api_key_input.value,
                    model_name,
                    self.current_website_text,
                    target_card.description,
                    self.global_instruction_input.value,
                    self.target_keywords_input.value,
                    refine_input.value,
                )

                target_card.model_name = model_name
                target_card.set_description(refined)
                await self.persist_result_card(target_card)
                await self.load_history_cmd()
                orig_color = target_card.color
                target_card.color = ft.Colors.GREEN_50
                target_card.update()
                await self.show_status("修正完了！")
                await asyncio.sleep(1.5)
                target_card.color = orig_color
                target_card.update()
            except Exception as ex:
                if not await self.error_service.handle_exception(ex, "修正生成"):
                    await self.show_error(str(ex))

        dialog: ft.AlertDialog
        dialog = ft.AlertDialog(
            title=ft.Text("修正して再生成"),
            content=ft.Column(
                [
                    ft.Text(
                        "特定の要望（例：「もっと柔らかい表現に」「専門用語を増やして」等）を入力して、説明文を書き直します。"
                    ),
                    refine_input,
                ],
                tight=True,
                width=500,
            ),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda _: self.page.close(dialog)),
                ft.ElevatedButton("再生成", on_click=submit),
            ],
        )
        self.page.open(dialog)
