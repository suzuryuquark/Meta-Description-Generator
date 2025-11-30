import flet as ft
import time
import os
import csv
import datetime
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
    
    # --- Menu Bar Logic ---
    def toggle_theme_mode(e):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        page.update()

    def open_github(e):
        page.launch_url("https://github.com/suzuryuquark/Meta-Description-Generator")

    def show_about_dialog(e):
        current_year = datetime.datetime.now().year
        page.open(ft.AlertDialog(
            title=ft.Text("バージョン情報"),
            content=ft.Text(f"AI Meta Description Generator v1.1.0\n\n© {current_year} suzuryuquark"),
        ))

    def show_changelog_dialog(e):
        changelog_content = "更新履歴が見つかりませんでした。"
        if os.path.exists("CHANGELOG.md"):
            with open("CHANGELOG.md", "r", encoding="utf-8") as f:
                changelog_content = f.read()
        
        page.open(ft.AlertDialog(
            title=ft.Text("更新履歴"),
            content=ft.Container(
                content=ft.Markdown(changelog_content),
                width=600,
                height=400,
            ),
        ))

    # --- CSV Export Logic ---
    def save_csv(e: ft.FilePickerResultEvent):
        if e.path:
            try:
                with open(e.path, mode='w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ドメイン', 'パス', 'パターン', 'タイトルタグ', '文字数', 'メタディスクリプション', '文字数'])
                    
                    # Construct URL from inputs
                    domain = domain_input.value.rstrip('/')
                    path = path_input.value.lstrip('/')

                    for card in results_column.controls:
                        # Extract data from UI structure
                        # Card -> Container -> Column -> controls
                        # [0]: ListTile (Pattern)
                        # [5]: TextField (Title)
                        # [9]: TextField (Description)
                        content_col = card.content.content
                        pattern = content_col.controls[0].title.value
                        title = content_col.controls[5].value
                        desc = content_col.controls[9].value
                        writer.writerow([domain, path, pattern, title, len(title), desc, len(desc)])
                
                show_status(f"CSVを保存しました: {e.path}")
            except Exception as ex:
                show_error(f"保存に失敗しました: {str(ex)}")

    csv_picker = ft.FilePicker(on_result=save_csv)
    page.overlay.append(csv_picker)

    def export_csv_click(e):
        if not results_column.controls:
            show_error("保存するデータがありません")
            return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_picker.save_file(file_name=f"meta_descriptions_{timestamp}.csv", allowed_extensions=["csv"])

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.AUTO_AWESOME),
        leading_width=40,
        title=ft.Text("AI Meta Description Generator"),
        center_title=False,
        bgcolor=ft.Colors.BLUE_GREY_50,
        actions=[
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(text="CSVエクスポート", icon=ft.Icons.DOWNLOAD, on_click=export_csv_click),
                    ft.PopupMenuItem(), # Divider
                    ft.PopupMenuItem(text="ダークモード切替", on_click=toggle_theme_mode),
                    ft.PopupMenuItem(), # Divider
                    ft.PopupMenuItem(text="GitHubリポジトリ", on_click=open_github),
                    ft.PopupMenuItem(text="更新履歴", on_click=show_changelog_dialog),
                    ft.PopupMenuItem(text="バージョン情報", on_click=show_about_dialog),
                ]
            ),
        ],
    )
    
    page.update()

    # API Key handling
    api_key_input = ft.TextField(
        label="Gemini APIキー",
        password=True,
        can_reveal_password=True,
        width=400,
        hint_text="APIキーを入力してください",
        border=ft.InputBorder.OUTLINE,
        filled=True
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
        width=800,
        border=ft.InputBorder.OUTLINE,
        filled=True
    )

    # Target Keywords
    target_keywords_input = ft.TextField(
        label="ターゲットキーワード (カンマ区切り)",
        hint_text="例：SEO, AI, 自動化",
        width=800,
        border=ft.InputBorder.OUTLINE,
        filled=True
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
        border=ft.InputBorder.OUTLINE,
        filled=True
    )
    path_input = ft.TextField(
        label="パス (/page/...)",
        width=700,
        hint_text="/about",
        autofocus=True,
        border=ft.InputBorder.OUTLINE,
        filled=True
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
        autofocus=True,
        border=ft.InputBorder.OUTLINE,
        filled=True
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
            print(f"Original: {original_desc}")
            print(f"Refined: {refined_text}")

            # Update the card (Description Field at index 9)
            target_refine_card.content.content.controls[9].value = refined_text
            
            # Update char count (Row at index 10 -> Text at index 0)
            count_text = target_refine_card.content.content.controls[10].controls[0]
            count_text.value = f"{len(refined_text)}文字"
            
            # Validation Logic for Refinement
            if len(refined_text) > 120:
                count_text.color = ft.Colors.RED
                count_text.weight = ft.FontWeight.BOLD
            else:
                count_text.color = ft.Colors.GREY
                count_text.weight = ft.FontWeight.NORMAL
            
            # Update copy data (Row at index 10 -> CopyBtn at index 1)
            target_refine_card.content.content.controls[10].controls[1].data = refined_text
            
            # Update SERP Preview (Container at index 2 -> Column -> Text at index 2)
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
            # ft.Text("AI Meta Description Generator", size=30, weight=ft.FontWeight.BOLD), # Removed as it's now in AppBar
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
