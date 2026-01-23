import asyncio
import flet as ft
import core_logic
import ui_components
from services.storage_service import StorageService

class GenerateView(ft.Container):
    def __init__(self, page: ft.Page, storage: StorageService, error_service, show_status, show_error, load_history_cmd):
        super().__init__()
        self.page = page
        self.storage = storage
        self.error_service = error_service
        self.show_status = show_status
        self.show_error = show_error
        self.load_history_cmd = load_history_cmd
        self.padding = 10
        self.expand = True
        
        self.current_website_text = ""
        self.target_refine_card = None
        
        self.build_ui()

    def build_ui(self):
        # API Key
        self.api_key_input = ft.TextField(
            label="Gemini APIキー", password=True, can_reveal_password=True,
            width=400, border=ft.InputBorder.OUTLINE, filled=True
        )
        self.save_key_btn = ft.IconButton(
            icon=ft.Icons.SAVE, tooltip="APIキーを保存",
            on_click=self.save_api_key_click
        )

        # Templates
        self.template_dropdown = ft.Dropdown(
            label="テンプレートを選択", width=300, options=[],
            on_change=self.on_template_change
        )
        
        # Instructions & Keywords
        self.global_instruction_input = ft.TextField(
            label="サイト共通の指示", multiline=True, min_lines=2, max_lines=3,
            width=800, border=ft.InputBorder.OUTLINE, filled=True
        )
        self.target_keywords_input = ft.TextField(
            label="ターゲットキーワード (カンマ区切り)", width=800,
            border=ft.InputBorder.OUTLINE, filled=True
        )

        # URL Inputs
        self.domain_input = ft.TextField(
            label="ドメイン (https://...)", width=400,
            border=ft.InputBorder.OUTLINE, filled=True
        )
        self.path_input = ft.TextField(
            label="パス (/page/...)", width=700,
            border=ft.InputBorder.OUTLINE, filled=True
        )

        # Tone
        self.tone_dropdown = ft.Dropdown(
            label="トーン＆スタイル", width=800,
            options=[
                ft.dropdown.Option("SEO重視 (デフォルト)"),
                ft.dropdown.Option("プロフェッショナル (信頼感重視)"),
                ft.dropdown.Option("親しみやすい (カジュアル)"),
                ft.dropdown.Option("キャッチー (クリック誘発)"),
                ft.dropdown.Option("メリット強調 (ベネフィット前面)"),
            ],
            value="SEO重視 (デフォルト)"
        )

        self.generate_btn = ft.ElevatedButton(
            text="生成する", icon=ft.Icons.AUTO_AWESOME,
            bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE,
            on_click=lambda e: self.page.run_task(self.generate_descriptions_click, e)
        )

        self.results_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

        self.content = ft.Column([
            ft.Text("WebサイトのURLから最適なdescriptionを3パターン提案します。", size=16, color=ft.Colors.GREY_700),
            ft.Divider(),
            ft.Row([self.api_key_input, self.save_key_btn], alignment=ft.MainAxisAlignment.START),
            ft.Row([
                self.template_dropdown,
                ft.IconButton(ft.Icons.ADD_BOX_OUTLINED, tooltip="新規テンプレートとして保存", on_click=self.new_template_click),
                ft.IconButton(ft.Icons.SAVE, tooltip="現在のテンプレートに上書き保存", on_click=self.save_template_click),
                ft.IconButton(ft.Icons.DELETE, tooltip="選択中のテンプレートを削除", on_click=self.delete_template_click),
            ], alignment=ft.MainAxisAlignment.START),
            self.global_instruction_input,
            self.target_keywords_input,
            ft.Row([self.domain_input, ft.Text("/", size=20), self.path_input], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.tone_dropdown,
            self.generate_btn,
            ft.Divider(),
            self.results_column
        ], spacing=20, scroll=ft.ScrollMode.AUTO)

    async def initialize(self):
        # API key is preserved
        self.api_key_input.value = await self.storage.get_api_key() or ""
        
        # Other fields are cleared on startup as requested
        self._clear_inputs(include_instruction=True)
        
        await self.load_templates()
        self.template_dropdown.value = None # Ensure unselected on start
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
        await self.show_status("APIキーを保存しました")

    async def save_template_click(self, e):
        # Overwrite current selection
        name = self.template_dropdown.value
        if not name:
            return await self.show_error("上書きするテンプレートを選択してください。新規作成は '+' ボタンを使用してください。")
        
        templates = await self.storage.get_templates()
        templates[name] = {
            "instruction": self.global_instruction_input.value,
            "keywords": self.target_keywords_input.value,
            "domain": self.domain_input.value,
            "path": self.path_input.value,
            "tone": self.tone_dropdown.value
        }
        await self.storage.save_templates(templates)
        await self.show_status(f"テンプレート '{name}' を更新しました")

    async def new_template_click(self, e):
        async def confirm_save(e):
            name = name_input.value.strip()
            if not name: return
            templates = await self.storage.get_templates()
            if name in templates:
                # Basic name duplication check
                self.page.open(ft.SnackBar(content=ft.Text("同じ名前のテンプレートが既に存在します。")))
                return
                
            templates[name] = {
                "instruction": self.global_instruction_input.value,
                "keywords": self.target_keywords_input.value,
                "domain": self.domain_input.value,
                "path": self.path_input.value,
                "tone": self.tone_dropdown.value
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
        dialog = ft.AlertDialog(
            title=ft.Text("新規テンプレートとして保存"), content=name_input,
            actions=[
                ft.TextButton("キャンセル", on_click=lambda _: self.page.close(dialog)),
                ft.ElevatedButton("作成", on_click=confirm_save),
            ]
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

        dialog = ft.AlertDialog(
            title=ft.Text("テンプレートの削除"),
            content=ft.Text(f"テンプレート '{name}' を削除してもよろしいですか？"),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda _: self.page.close(dialog)),
                ft.ElevatedButton("削除", on_click=confirm_delete, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE),
            ]
        )
        self.page.open(dialog)

    async def generate_descriptions_click(self, e):
        api_key = self.api_key_input.value
        domain = self.domain_input.value.strip().rstrip('/')
        path = self.path_input.value.strip().lstrip('/')
        url = f"{domain}/{path}"
        
        # Save current settings
        await self.storage.save_global_instruction(self.global_instruction_input.value)
        await self.storage.save_target_keywords(self.target_keywords_input.value)
        await self.storage.save_last_domain(domain)

        if not api_key: return await self.show_error("APIキーを入力してください")
        if not domain: return await self.show_error("ドメインを入力してください")

        self.results_column.controls.clear()
        await self.show_status("Webサイトを解析中...")
        self.generate_btn.disabled = True
        self.update()

        try:
            print(f"Fetching website content: {url}")
            self.current_website_text = await asyncio.to_thread(core_logic.fetch_website_content, url)
            
            await self.show_status("AIが説明文を生成中...")
            print("Generating descriptions with Gemini...")
            suggestions = await asyncio.to_thread(
                core_logic.generate_descriptions,
                api_key, self.current_website_text, 
                self.global_instruction_input.value, 
                self.target_keywords_input.value,
                tone=self.tone_dropdown.value
            )

            for item in suggestions:
                card = ui_components.create_result_card(
                    item, domain, path, 
                    self.copy_to_clipboard, self.open_refine_dialog
                )
                self.results_column.controls.append(card)
            
            await self.save_to_history(url, suggestions)
            await self.load_history_cmd()
            await self.show_status("生成完了！")

        except Exception as ex:
            if not await self.error_service.handle_exception(ex, "通常生成"):
                await self.show_error(str(ex))
        
        self.generate_btn.disabled = False
        self.update()

    async def save_to_history(self, url, suggestions):
        history = await self.storage.get_history()
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in suggestions:
            history.append({
                "url": url, "timestamp": timestamp, "pattern": item['title'],
                "title_tag": item.get('title_tag', ''), "description": item['description']
            })
        await self.storage.save_history(history)

    async def copy_to_clipboard(self, e):
        self.page.set_clipboard(e.control.data)
        self.page.open(ft.SnackBar(content=ft.Text("コピーしました！")))

    async def open_refine_dialog(self, e):
        self.target_refine_card = e.control.data
        refine_input = ft.TextField(label="修正の指示", multiline=True, autofocus=True, filled=True)
        
        async def submit(e):
            if not refine_input.value: return
            self.page.close(dialog)
            await self.show_status("修正案を生成中...")
            
            try:
                original_desc = self.target_refine_card.content.content.controls[9].value
                refined = await asyncio.to_thread(
                    core_logic.refine_description,
                    self.api_key_input.value, self.current_website_text, original_desc,
                    self.global_instruction_input.value, self.target_keywords_input.value,
                    refine_input.value
                )
                
                # Update UI
                self.target_refine_card.content.content.controls[9].value = refined
                count_text = self.target_refine_card.content.content.controls[10].controls[0]
                count_text.value = f"{len(refined)}文字"
                count_text.color = ft.Colors.RED if len(refined) > 120 else ft.Colors.GREY
                self.target_refine_card.content.content.controls[10].controls[1].data = refined
                self.target_refine_card.content.content.controls[2].content.controls[2].value = refined
                
                orig_color = self.target_refine_card.color
                self.target_refine_card.color = ft.Colors.GREEN_50
                self.target_refine_card.update()
                await self.show_status("修正完了！")
                await asyncio.sleep(1.5)
                self.target_refine_card.color = orig_color
                self.target_refine_card.update()
            except Exception as ex:
                if not await self.error_service.handle_exception(ex, "修正生成"):
                    await self.show_error(str(ex))

        dialog = ft.AlertDialog(
            title=ft.Text("修正して再生成"),
            content=ft.Column([
                ft.Text("特定の要望（例：「もっと柔らかい表現に」「専門用語を増やして」等）を入力して、説明文を書き直します。"),
                refine_input,
            ], tight=True, width=500),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda _: self.page.close(dialog)),
                ft.ElevatedButton("再生成", on_click=submit),
            ]
        )
        self.page.open(dialog)
