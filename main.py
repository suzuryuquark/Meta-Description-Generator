import flet as ft
import time
import core_logic
import ui_components

def main(page: ft.Page):
    page.title = "AI Meta Description Generator"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.window.width = 1200
    page.window.height = 1200
    page.window.center()
    page.scroll = ft.ScrollMode.AUTO
    page.update()

    # API Key handling
    api_key_input = ft.TextField(
        label="Gemini APIキー",
        password=True,
        can_reveal_password=True,
        width=400,
        hint_text="APIキーを入力してください"
    )

    def save_api_key(e):
        page.client_storage.set("gemini_api_key", api_key_input.value)
        show_status("APIキーを保存しました")
        page.update()

    save_key_btn = ft.IconButton(
        icon=ft.Icons.SAVE,
        tooltip="APIキーを保存",
        on_click=save_api_key
    )

    # Global Instruction
    global_instruction_input = ft.TextField(
        label="サイト共通の指示",
        hint_text="例：トーン＆マナー、ターゲット層、必須キーワードなど",
        multiline=True,
        min_lines=2,
        max_lines=3,
        width=800
    )

    # Target Keywords
    target_keywords_input = ft.TextField(
        label="ターゲットキーワード (カンマ区切り)",
        hint_text="例：SEO, AI, 自動化",
        width=800
    )

    # Load settings
    if page.client_storage.contains_key("gemini_api_key"):
        api_key_input.value = page.client_storage.get("gemini_api_key")
    if page.client_storage.contains_key("global_instruction"):
        global_instruction_input.value = page.client_storage.get("global_instruction")
    if page.client_storage.contains_key("target_keywords"):
        target_keywords_input.value = page.client_storage.get("target_keywords")

    # URL Inputs (Domain + Path)
    domain_input = ft.TextField(
        label="ドメイン (https://...)",
        width=400,
        hint_text="https://example.com",
    )
    path_input = ft.TextField(
        label="パス (/page/...)",
        width=700,
        hint_text="/about",
        autofocus=True
    )

    if page.client_storage.contains_key("last_domain"):
        domain_input.value = page.client_storage.get("last_domain")

    generate_btn = ft.ElevatedButton(
        text="生成する",
        icon=ft.Icons.AUTO_AWESOME,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.BLUE_600,
            padding=20,
        )
    )

    status_text = ft.Text("")
    results_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    
    # State variables
    current_website_text = ""
    target_refine_card = None # To know which card to update

    # Refinement Dialog Controls
    refine_instruction_input = ft.TextField(
        label="修正の指示",
        hint_text="例：もっと短くして、問いかけ調で、など",
        multiline=True,
        autofocus=True
    )

    def close_refine_dialog(e):
        page.close(refine_dialog)

    def refine_description_submit(e):
        if not refine_instruction_input.value:
            return
        
        close_refine_dialog(None)
        show_status("修正案を生成中...")
        page.update()

        try:
            # Get original description from the target card
            # New Structure:
            # 0: ListTile (Pattern Label)
            # 1: Text("Google検索結果プレビュー")
            # 2: Container (SERP Preview)
            # 3: Divider
            # 4: Text("タイトルタグ")
            # 5: TextField (Title Tag)
            # 6: Row (Title Actions)
            # 7: Divider
            # 8: Text("メタディスクリプション")
            # 9: TextField (Meta Description)
            # 10: Row (Desc Actions)
            # 11: Container (Refine Button)
            
            # Description is at index 9
            original_desc = target_refine_card.content.content.controls[9].value
            
            refined_text = core_logic.refine_description(
                api_key_input.value,
                current_website_text,
                original_desc,
                global_instruction_input.value,
                target_keywords_input.value,
                refine_instruction_input.value
            )
            
            # Update the card (Description Field at index 9)
            target_refine_card.content.content.controls[9].value = refined_text
            
            # Update char count (Row at index 10 -> Text at index 0)
            target_refine_card.content.content.controls[10].controls[0].value = f"{len(refined_text)}文字"
            
            # Update copy data (Row at index 10 -> CopyBtn at index 1)
            target_refine_card.content.content.controls[10].controls[1].data = refined_text
            
            # Update SERP Preview (Container at index 2 -> Column -> Text at index 2)
            # SERP Preview Structure: Container -> Column -> [Row(Url), Title, Desc]
            target_refine_card.content.content.controls[2].content.controls[2].value = refined_text
            
            # Visual Feedback (Flash Green)
            original_color = target_refine_card.color
            target_refine_card.color = ft.Colors.GREEN_50
            target_refine_card.update()
            
            show_status("修正完了！")
            
            time.sleep(1.5)
            target_refine_card.color = original_color
            target_refine_card.update()

        except Exception as ex:
            show_error(str(ex))

    refine_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("修正して再生成"),
        content=refine_instruction_input,
        actions=[
            ft.TextButton("キャンセル", on_click=close_refine_dialog),
            ft.ElevatedButton("再生成", on_click=refine_description_submit),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_refine_dialog(e):
        nonlocal target_refine_card
        target_refine_card = e.control.data # We will store the card ref in the button data
        refine_instruction_input.value = ""
        page.open(refine_dialog)

    def show_error(message):
        status_text.value = f"エラー: {message}"
        status_text.color = ft.Colors.RED
        status_text.update()

    def show_status(message):
        status_text.value = message
        status_text.color = ft.Colors.BLUE
        status_text.update()

    def copy_to_clipboard(e):
        page.set_clipboard(e.control.data)
        page.show_snack_bar(ft.SnackBar(content=ft.Text("コピーしました！")))

    def generate_descriptions_click(e):
        api_key = api_key_input.value
        # Combine URL
        domain = domain_input.value.strip().rstrip('/')
        path = path_input.value.strip().lstrip('/')
        url = f"{domain}/{path}"
        
        global_inst = global_instruction_input.value

        # Save settings
        page.client_storage.set("global_instruction", global_inst)
        page.client_storage.set("target_keywords", target_keywords_input.value)
        page.client_storage.set("last_domain", domain)

        if not api_key:
            show_error("APIキーを入力してください")
            return
        if not domain:
            show_error("ドメインを入力してください")
            return

        results_column.controls.clear()
        show_status("Webサイトを解析中...")
        generate_btn.disabled = True
        page.update()

        try:
            # 1. Fetch Content
            nonlocal current_website_text
            current_website_text = core_logic.fetch_website_content(url)
            
            # 2. Generate with Gemini
            show_status("AIが説明文を生成中...")
            suggestions = core_logic.generate_descriptions(
                api_key, 
                current_website_text, 
                global_inst, 
                target_keywords_input.value
            )

            # 3. Display Results
            for item in suggestions:
                card = ui_components.create_result_card(
                    item, 
                    domain_input.value, 
                    path_input.value, 
                    copy_to_clipboard, 
                    open_refine_dialog
                )
                results_column.controls.append(card)
            
            show_status("生成完了！")

        except Exception as ex:
            show_error(str(ex))
        
        generate_btn.disabled = False
        page.update()

    generate_btn.on_click = generate_descriptions_click

    # Layout
    page.add(
        ft.Column([
            ft.Text("AI Meta Description Generator", size=30, weight=ft.FontWeight.BOLD),
            ft.Text("WebサイトのURLから最適なdescriptionを3パターン提案します。", size=16, color=ft.Colors.GREY_700),
            ft.Divider(),
            ft.Row([
                api_key_input,
                save_key_btn
            ], alignment=ft.MainAxisAlignment.START),
            global_instruction_input,
            target_keywords_input,
            ft.Row([
                domain_input,
                ft.Text("/", size=20),
                path_input
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            generate_btn,
            status_text,
            ft.Divider(),
            results_column
        ], spacing=20)
    )

if __name__ == "__main__":
    ft.app(target=main)
