import flet as ft

def create_serp_preview(domain, path, title, description):
    preview_title = ft.Text(
        value=title,
        size=20,
        color="#1a0dab",
        weight=ft.FontWeight.NORMAL,
        font_family="Arial, sans-serif",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS
    )
    preview_url = ft.Text(
        value=f"{domain} › {path.lstrip('/')}",
        size=14,
        color="#202124",
        font_family="Arial, sans-serif",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS
    )
    preview_desc = ft.Text(
        value=description,
        size=14,
        color="#4d5156",
        font_family="Arial, sans-serif",
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS
    )
    
    container = ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.PUBLIC, size=16, color="#dadce0"),
                        bgcolor="#f1f3f4",
                        padding=4,
                        border_radius=12
                    ),
                    ft.Column([
                        ft.Text("Site Name", size=12, color="#202124"),
                        preview_url
                    ], spacing=0)
                ], spacing=10),
                preview_title,
                preview_desc
            ],
            spacing=2
        ),
        padding=15,
        bgcolor="white",
        border_radius=8,
        border=ft.border.all(1, "#dadce0"),
        margin=ft.margin.only(bottom=10)
    )
    
    return container, preview_title, preview_desc

def create_result_card(item, domain, path, on_copy, open_refine_dialog):
    # SERP Preview
    serp_preview, preview_title, preview_desc = create_serp_preview(
        domain, path, item.get('title_tag', ''), item['description']
    )

    def update_preview_title(e):
        preview_title.value = e.control.value
        preview_title.update()
    
    def update_preview_desc(e):
        preview_desc.value = e.control.value
        preview_desc.update()

    # Manual Edit Logic
    def toggle_edit(e):
        text_field = e.control.data['field']
        is_editing = not text_field.read_only
        
        if is_editing: # Was editing, now finishing
            text_field.read_only = True
            text_field.border = ft.InputBorder.NONE
            e.control.icon = ft.Icons.EDIT
            e.control.tooltip = "手動修正"
            
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
        e.control.parent.update()

    # --- Title Tag Controls ---
    title_tag_val = item.get('title_tag', '')
    title_field = ft.TextField(
        value=title_tag_val,
        multiline=True,
        read_only=True,
        border=ft.InputBorder.NONE,
        text_size=16,
        color=ft.Colors.BLACK87,
        on_change=update_preview_title
    )
    title_edit_btn = ft.IconButton(
        icon=ft.Icons.EDIT,
        tooltip="手動修正",
        data={'field': title_field},
        on_click=toggle_edit
    )
    title_actions = ft.Row(
        [
            ft.Text(f"{len(title_tag_val)}文字", size=12, color=ft.Colors.GREY),
            ft.IconButton(
                icon=ft.Icons.COPY,
                tooltip="コピー",
                data=title_tag_val,
                on_click=on_copy
            ),
            title_edit_btn
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    # --- Description Controls ---
    desc_val = item['description']
    desc_field = ft.TextField(
        value=desc_val,
        multiline=True,
        read_only=True,
        border=ft.InputBorder.NONE,
        text_size=16,
        color=ft.Colors.BLACK87,
        on_change=update_preview_desc
    )
    desc_edit_btn = ft.IconButton(
        icon=ft.Icons.EDIT,
        tooltip="手動修正",
        data={'field': desc_field},
        on_click=toggle_edit
    )
    desc_actions = ft.Row(
        [
            ft.Text(f"{len(desc_val)}文字", size=12, color=ft.Colors.GREY),
            ft.IconButton(
                icon=ft.Icons.COPY,
                tooltip="コピー",
                data=desc_val,
                on_click=on_copy
            ),
            desc_edit_btn
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE),
                    title=ft.Text(item['title'], weight=ft.FontWeight.BOLD),
                ),
                ft.Text("Google検索結果プレビュー", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY),
                serp_preview,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Text("タイトルタグ", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY),
                title_field,
                title_actions,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Text("メタディスクリプション", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY),
                desc_field,
                desc_actions,
                ft.Container(
                    content=ft.OutlinedButton(
                        text="修正して再生成 (Descのみ)",
                        icon=ft.Icons.EDIT,
                        on_click=open_refine_dialog,
                        data=None # Placeholder
                    ),
                    alignment=ft.alignment.center_right
                )
            ]),
            padding=15
        )
    )
    # Set the card as data for the refine button (last control)
    card.content.content.controls[-1].content.data = card
    return card
