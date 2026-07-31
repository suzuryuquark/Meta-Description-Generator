import uuid

import flet as ft

from models.generation import (
    DESCRIPTION_MAX_CHARS,
    DESCRIPTION_MIN_CHARS,
    TITLE_MAX_CHARS,
    MetaSuggestion,
)


class ResultCard(ft.Card):
    def __init__(
        self,
        *,
        content,
        history_id: str,
        url: str,
        model_name: str,
        pattern: str,
        title_field: ft.TextField,
        description_field: ft.TextField,
        title_count: ft.Text,
        description_count: ft.Text,
        title_copy_button: ft.IconButton,
        description_copy_button: ft.IconButton,
        preview_title: ft.Text,
        preview_description: ft.Text,
    ):
        super().__init__(content=content)
        self.history_id = history_id
        self.url = url
        self.model_name = model_name
        self.pattern = pattern
        self.title_field = title_field
        self.description_field = description_field
        self.title_count = title_count
        self.description_count = description_count
        self.title_copy_button = title_copy_button
        self.description_copy_button = description_copy_button
        self.preview_title = preview_title
        self.preview_description = preview_description

    @property
    def title_tag(self) -> str:
        return self.title_field.value or ""

    @property
    def description(self) -> str:
        return self.description_field.value or ""

    def set_description(self, description: str) -> None:
        self.description_field.value = description
        self.preview_description.value = description
        self.description_copy_button.data = description
        self._set_count_style(
            self.description_count,
            len(description),
            DESCRIPTION_MIN_CHARS,
            DESCRIPTION_MAX_CHARS,
        )
        self.update()

    @staticmethod
    def _set_count_style(
        control: ft.Text,
        count: int,
        minimum: int | None,
        maximum: int,
    ) -> None:
        outside_range = (minimum is not None and count < minimum) or count > maximum
        control.value = f"{count}文字"
        control.color = ft.Colors.RED if outside_range else ft.Colors.GREY
        control.weight = ft.FontWeight.BOLD if outside_range else ft.FontWeight.NORMAL


def create_serp_preview(domain, path, title, description):
    preview_title = ft.Text(
        value=title,
        size=20,
        color="#1a0dab",
        weight=ft.FontWeight.NORMAL,
        font_family="Arial, sans-serif",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    preview_url = ft.Text(
        value=f"{domain} › {path.lstrip('/')}",
        size=14,
        color="#202124",
        font_family="Arial, sans-serif",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    preview_desc = ft.Text(
        value=description,
        size=14,
        color="#4d5156",
        font_family="Arial, sans-serif",
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    container = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.PUBLIC, size=16, color="#dadce0"),
                            bgcolor="#f1f3f4",
                            padding=4,
                            border_radius=12,
                        ),
                        ft.Column(
                            [ft.Text("Site Name", size=12, color="#202124"), preview_url], spacing=0
                        ),
                    ],
                    spacing=10,
                ),
                preview_title,
                preview_desc,
            ],
            spacing=2,
        ),
        padding=15,
        bgcolor="white",
        border_radius=8,
        border=ft.border.all(1, "#dadce0"),
        margin=ft.margin.only(bottom=10),
    )

    return container, preview_title, preview_desc


def create_history_card(entry, on_copy):
    # entry keys: url, timestamp, pattern, title_tag, description
    return ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.HISTORY, size=20),
                        title=ft.Text(
                            f"{entry.get('pattern', 'パターン')} - {entry.get('timestamp', '')}",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                        ),
                        subtitle=ft.Text(entry.get("url", ""), size=12),
                    ),
                    ft.Text(
                        f"使用モデル: {entry.get('model', '記録なし')}",
                        size=11,
                        color=ft.Colors.BLUE_GREY,
                    ),
                    ft.Text(
                        f"状態: {entry.get('status', '生成結果')}",
                        size=11,
                        color=ft.Colors.BLUE_GREY,
                    ),
                    ft.Text(
                        "タイトルタグ:",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY,
                    ),
                    ft.Text(entry.get("title_tag", ""), size=14),
                    ft.Text(
                        "メタディスクリプション:",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY,
                    ),
                    ft.Text(entry.get("description", ""), size=14),
                    ft.Row(
                        [
                            ft.TextButton(
                                "タイトルをコピー",
                                icon=ft.Icons.COPY,
                                on_click=on_copy,
                                data=entry.get("title_tag", ""),
                            ),
                            ft.TextButton(
                                "説明文をコピー",
                                icon=ft.Icons.COPY,
                                on_click=on_copy,
                                data=entry.get("description", ""),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=5,
            ),
            padding=10,
        )
    )


def create_result_card(
    item: MetaSuggestion,
    domain,
    path,
    model_name,
    on_copy,
    open_refine_dialog,
    on_save_history,
):
    # SERP Preview
    serp_preview, preview_title, preview_desc = create_serp_preview(
        domain, path, item.title_tag, item.description
    )

    def update_preview_title(e):
        preview_title.value = e.control.value
        preview_title.update()

    def update_preview_desc(e):
        preview_desc.value = e.control.value
        preview_desc.update()

    # --- Validation Logic ---
    def validate_count(text, minimum, maximum, count_control):
        count = len(text)
        count_control.value = f"{count}文字"
        if (minimum is not None and count < minimum) or count > maximum:
            count_control.color = ft.Colors.RED
            count_control.weight = ft.FontWeight.BOLD
        else:
            count_control.color = ft.Colors.GREY
            count_control.weight = ft.FontWeight.NORMAL
        count_control.update()

    # Manual Edit Logic
    def toggle_edit(e):
        text_field = e.control.data["field"]
        is_editing = not text_field.read_only

        if is_editing:  # Was editing, now finishing
            text_field.read_only = True
            text_field.border = ft.InputBorder.NONE
            e.control.icon = ft.Icons.EDIT
            e.control.tooltip = "手動修正"

            count_text = e.control.data["count_control"]
            copy_btn = e.control.data["copy_button"]

            # Update count with validation
            minimum = e.control.data.get("minimum")
            maximum = e.control.data["maximum"]
            validate_count(text_field.value, minimum, maximum, count_text)

            copy_btn.data = text_field.value

        else:  # Start editing
            text_field.read_only = False
            text_field.border = ft.InputBorder.OUTLINE
            e.control.icon = ft.Icons.CHECK
            e.control.tooltip = "完了"
            text_field.focus()

        text_field.update()
        e.control.update()
        e.control.parent.update()

    # --- Title Tag Controls ---
    title_tag_val = item.title_tag

    # Pre-calculate initial style
    title_len = len(title_tag_val)
    title_color = ft.Colors.RED if title_len > TITLE_MAX_CHARS else ft.Colors.GREY
    title_weight = ft.FontWeight.BOLD if title_len > TITLE_MAX_CHARS else ft.FontWeight.NORMAL

    title_count_text = ft.Text(f"{title_len}文字", size=12, color=title_color, weight=title_weight)

    def on_title_change(e):
        update_preview_title(e)
        validate_count(e.control.value, None, TITLE_MAX_CHARS, title_count_text)

    title_field = ft.TextField(
        value=title_tag_val,
        multiline=True,
        read_only=True,
        border=ft.InputBorder.NONE,
        text_size=16,
        color=ft.Colors.BLACK87,
        on_change=on_title_change,
    )
    title_edit_btn = ft.IconButton(
        icon=ft.Icons.EDIT,
        tooltip="手動修正",
        data={"field": title_field, "maximum": TITLE_MAX_CHARS},
        on_click=toggle_edit,
    )
    title_copy_button = ft.IconButton(
        icon=ft.Icons.COPY,
        tooltip="コピー",
        data=title_tag_val,
        on_click=on_copy,
    )
    title_edit_btn.data["count_control"] = title_count_text
    title_edit_btn.data["copy_button"] = title_copy_button
    title_actions = ft.Row(
        [
            title_count_text,
            title_copy_button,
            title_edit_btn,
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    # --- Description Controls ---
    desc_val = item.description

    # Pre-calculate initial style
    desc_len = len(desc_val)
    desc_outside_range = desc_len < DESCRIPTION_MIN_CHARS or desc_len > DESCRIPTION_MAX_CHARS
    desc_color = ft.Colors.RED if desc_outside_range else ft.Colors.GREY
    desc_weight = ft.FontWeight.BOLD if desc_outside_range else ft.FontWeight.NORMAL

    desc_count_text = ft.Text(f"{desc_len}文字", size=12, color=desc_color, weight=desc_weight)

    def on_desc_change(e):
        update_preview_desc(e)
        validate_count(
            e.control.value,
            DESCRIPTION_MIN_CHARS,
            DESCRIPTION_MAX_CHARS,
            desc_count_text,
        )

    desc_field = ft.TextField(
        value=desc_val,
        multiline=True,
        read_only=True,
        border=ft.InputBorder.NONE,
        text_size=16,
        color=ft.Colors.BLACK87,
        on_change=on_desc_change,
    )
    desc_edit_btn = ft.IconButton(
        icon=ft.Icons.EDIT,
        tooltip="手動修正",
        data={
            "field": desc_field,
            "minimum": DESCRIPTION_MIN_CHARS,
            "maximum": DESCRIPTION_MAX_CHARS,
        },
        on_click=toggle_edit,
    )
    description_copy_button = ft.IconButton(
        icon=ft.Icons.COPY,
        tooltip="コピー",
        data=desc_val,
        on_click=on_copy,
    )
    desc_edit_btn.data["count_control"] = desc_count_text
    desc_edit_btn.data["copy_button"] = description_copy_button
    desc_actions = ft.Row(
        [
            desc_count_text,
            description_copy_button,
            desc_edit_btn,
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    refine_button = ft.OutlinedButton(
        text="修正して再生成 (Descのみ)",
        icon=ft.Icons.EDIT,
        on_click=open_refine_dialog,
    )
    save_history_button = ft.OutlinedButton(
        text="編集内容を履歴へ反映",
        icon=ft.Icons.SAVE,
        on_click=on_save_history,
    )
    card_content = ft.Container(
        content=ft.Column(
            [
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE),
                    title=ft.Text(item.title, weight=ft.FontWeight.BOLD),
                ),
                ft.Text(
                    "Google検索結果プレビュー",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_GREY,
                ),
                serp_preview,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Text(
                    "タイトルタグ",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_GREY,
                ),
                title_field,
                title_actions,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Text(
                    "メタディスクリプション",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_GREY,
                ),
                desc_field,
                desc_actions,
                ft.Row(
                    [refine_button, save_history_button],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ]
        ),
        padding=15,
    )
    card = ResultCard(
        content=card_content,
        history_id=uuid.uuid4().hex,
        url=f"{domain.rstrip('/')}/{path.lstrip('/')}",
        model_name=model_name,
        pattern=item.title,
        title_field=title_field,
        description_field=desc_field,
        title_count=title_count_text,
        description_count=desc_count_text,
        title_copy_button=title_copy_button,
        description_copy_button=description_copy_button,
        preview_title=preview_title,
        preview_description=preview_desc,
    )
    refine_button.data = card
    save_history_button.data = card
    return card
