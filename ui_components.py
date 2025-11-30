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

    # --- Validation Logic ---
    def validate_count(text, limit, count_control):
        count = len(text)
        count_control.value = f"{count}文字"
        if count > limit:
            count_control.color = ft.Colors.RED
            count_control.weight = ft.FontWeight.BOLD
        else:
            count_control.color = ft.Colors.GREY
            count_control.weight = ft.FontWeight.NORMAL
        count_control.update()

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
            
            # Update count with validation
            limit = 32 if "title" in str(text_field.data) else 120 # Hacky way to identify field, or pass limit in data
            # Better: pass limit in toggle_edit data
            limit = e.control.data.get('limit', 120)
            validate_count(text_field.value, limit, count_text)
            
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
    
    # Pre-calculate initial style
    title_len = len(title_tag_val)
    title_color = ft.Colors.RED if title_len > 32 else ft.Colors.GREY
    title_weight = ft.FontWeight.BOLD if title_len > 32 else ft.FontWeight.NORMAL
    
    title_count_text = ft.Text(f"{title_len}文字", size=12, color=title_color, weight=title_weight)

    def on_title_change(e):
        update_preview_title(e)
        validate_count(e.control.value, 32, title_count_text)

    title_field = ft.TextField(
        value=title_tag_val,
        multiline=True,
        read_only=True,
        border=ft.InputBorder.NONE,
        text_size=16,
        color=ft.Colors.BLACK87,
        on_change=on_title_change
    )
    title_edit_btn = ft.IconButton(
        icon=ft.Icons.EDIT,
        tooltip="手動修正",
        data={'field': title_field, 'limit': 32},
        on_click=toggle_edit
    )
    title_actions = ft.Row(
        [
            title_count_text,
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
    
    # Pre-calculate initial style
    desc_len = len(desc_val)
    desc_color = ft.Colors.RED if desc_len > 120 else ft.Colors.GREY
    desc_weight = ft.FontWeight.BOLD if desc_len > 120 else ft.FontWeight.NORMAL
    
    desc_count_text = ft.Text(f"{desc_len}文字", size=12, color=desc_color, weight=desc_weight)

    def on_desc_change(e):
        update_preview_desc(e)
        validate_count(e.control.value, 120, desc_count_text)

    desc_field = ft.TextField(
        value=desc_val,
        multiline=True,
        read_only=True,
        border=ft.InputBorder.NONE,
        text_size=16,
        color=ft.Colors.BLACK87,
        on_change=on_desc_change
    )
    desc_edit_btn = ft.IconButton(
        icon=ft.Icons.EDIT,
        tooltip="手動修正",
        data={'field': desc_field, 'limit': 120},
        on_click=toggle_edit
    )
    desc_actions = ft.Row(
        [
            desc_count_text,
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
