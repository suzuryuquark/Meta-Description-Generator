import flet as ft
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import os
import time

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

    # Load settings
    if page.client_storage.contains_key("gemini_api_key"):
        api_key_input.value = page.client_storage.get("gemini_api_key")
    if page.client_storage.contains_key("global_instruction"):
        global_instruction_input.value = page.client_storage.get("global_instruction")

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
            # Structure: Card -> Container -> Column -> ListTile -> subtitle(TextField)
            original_desc = target_refine_card.content.content.controls[0].subtitle.value
            
            genai.configure(api_key=api_key_input.value)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            あなたはSEOの専門家です。
            以下のWebサイトのコンテンツと、現在提案されているmeta descriptionを元に、
            ユーザーの指示に従ってdescriptionを書き直してください。

            Webサイトのコンテンツ:
            {current_website_text}

            現在のdescription:
            {original_desc}

            サイト共通の指示:
            {global_instruction_input.value}

            ユーザーの修正指示:
            {refine_instruction_input.value}

            要件:
            - 日本語で出力すること
            - 文字数は100文字〜120文字程度
            - 出力は修正後のdescriptionのテキストのみ（JSON不要）
            """

            response = model.generate_content(prompt)
            refined_text = response.text.strip()
            
            # Update the card
            target_refine_card.content.content.controls[0].subtitle.value = refined_text
            # Update char count
            # Structure: Card -> Container -> Column -> Row -> Text (index 0)
            target_refine_card.content.content.controls[1].controls[0].value = f"{len(refined_text)}文字"
            # Update copy data
            target_refine_card.content.content.controls[1].controls[1].data = refined_text
            
            # Update copy data
            target_refine_card.content.content.controls[1].controls[1].data = refined_text
            
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

    def fetch_website_content(url):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract relevant text
            title = soup.title.string if soup.title else ""
            meta_desc = ""
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta:
                meta_desc = meta.get('content', '')
            
            # Get main content text (h1, h2, p)
            content_parts = []
            if title: content_parts.append(f"Title: {title}")
            if meta_desc: content_parts.append(f"Current Description: {meta_desc}")
            
            for tag in soup.find_all(['h1', 'h2', 'p']):
                text = tag.get_text(strip=True)
                if len(text) > 20: # Filter out short snippets
                    content_parts.append(text)
            
            # Limit content length to avoid token limits (approx 10k chars)
            full_text = "\n".join(content_parts)
            return full_text[:10000]
            
        except Exception as e:
            raise Exception(f"サイトの読み込みに失敗しました: {str(e)}")

    def generate_descriptions_click(e):
        api_key = api_key_input.value
        # Combine URL
        domain = domain_input.value.strip().rstrip('/')
        path = path_input.value.strip().lstrip('/')
        url = f"{domain}/{path}"
        
        global_inst = global_instruction_input.value

        # Save settings
        # page.client_storage.set("gemini_api_key", api_key) # User requested manual save only for API key
        page.client_storage.set("global_instruction", global_inst)
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
            current_website_text = fetch_website_content(url)
            website_text = current_website_text
            
            # 2. Generate with Gemini
            show_status("AIが説明文を生成中...")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash') # Using requested model
            
            prompt = f"""
            あなたはSEOの専門家です。以下のWebサイトのテキストコンテンツを分析し、検索エンジンの結果ページ（SERP）でクリック率を高めるための魅力的なmeta descriptionを3つ提案してください。
            
            要件:
            - 日本語で出力すること
            - 文字数は100文字〜120文字程度
            - それぞれ異なる訴求ポイント（例：メリット強調、疑問形、要約型など）を持つこと
            - 出力は以下のJSON形式のみにしてください。余計なmarkdown装飾は不要です。
            
            JSON形式:
            [
                {{"title": "パターン1の特徴", "description": "生成された説明文"}},
                {{"title": "パターン2の特徴", "description": "生成された説明文"}},
                {{"title": "パターン3の特徴", "description": "生成された説明文"}}
            ]

            Webサイトのコンテンツ:
            {website_text}

            サイト共通の指示:
            {global_instruction_input.value}
            """

            response = model.generate_content(prompt)
            
            # Parse JSON response
            text_response = response.text.strip()
            # Remove markdown code blocks if present
            if text_response.startswith("```json"):
                text_response = text_response[7:-3]
            elif text_response.startswith("```"):
                text_response = text_response[3:-3]
                
            suggestions = json.loads(text_response)

            # 3. Display Results
            for item in suggestions:
                
                # Manual Edit Logic
                def toggle_edit(e):
                    # e.control is the IconButton
                    # The TextField is stored in e.control.data['field']
                    text_field = e.control.data['field']
                    is_editing = not text_field.read_only
                    
                    if is_editing: # Was editing, now finishing
                        text_field.read_only = True
                        text_field.border = ft.InputBorder.NONE
                        e.control.icon = ft.Icons.EDIT
                        e.control.tooltip = "手動修正"
                        # Update char count and copy data
                        # e.control.parent is the Row. 
                        # Row controls: [Text(count), IconButton(Copy), IconButton(Edit)]
                        count_text = e.control.parent.controls[0]
                        copy_btn = e.control.parent.controls[1]
                        
                        count_text.value = f"{len(text_field.value)}文字"
                        copy_btn.data = text_field.value
                        
                    else: # Start editing
                        text_field.read_only = False
                        text_field.border = ft.InputBorder.OUTLINE
                        e.control.icon = ft.Icons.CHECK
                        e.control.tooltip = "完了"
                        text_field.focus()
                    
                    text_field.update()
                    e.control.update()
                    e.control.parent.update() # Update row to show new count

                desc_field = ft.TextField(
                    value=item['description'],
                    multiline=True,
                    read_only=True,
                    border=ft.InputBorder.NONE,
                    text_size=16,
                    color=ft.Colors.BLACK87
                )

                edit_btn = ft.IconButton(
                    icon=ft.Icons.EDIT,
                    tooltip="手動修正",
                    data={'field': desc_field},
                    on_click=toggle_edit
                )

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE),
                                title=ft.Text(item['title'], weight=ft.FontWeight.BOLD),
                                subtitle=desc_field,
                            ),
                            ft.Row(
                                [
                                    ft.Text(f"{len(item['description'])}文字", size=12, color=ft.Colors.GREY),
                                    ft.IconButton(
                                        icon=ft.Icons.COPY,
                                        tooltip="コピー",
                                        data=item['description'],
                                        on_click=copy_to_clipboard
                                    ),
                                    edit_btn
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                            ft.Container(
                                content=ft.OutlinedButton(
                                    text="修正して再生成",
                                    icon=ft.Icons.EDIT,
                                    on_click=open_refine_dialog,
                                    data=None # Placeholder, will be set below
                                ),
                                alignment=ft.alignment.center_right
                            )
                        ]),
                        padding=10
                    )
                )
                # Set the card as data for the refine button (which is the last control in the column)
                # Column -> Container (last) -> OutlinedButton
                card.content.content.controls[-1].content.data = card
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
            ft.Row([api_key_input, save_key_btn], alignment=ft.MainAxisAlignment.START),
            global_instruction_input,
            ft.Row([domain_input, path_input], alignment=ft.MainAxisAlignment.START),
            generate_btn,
            status_text,
            ft.Divider(),
            results_column
        ])
    )

if __name__ == "__main__":
    ft.app(target=main)
