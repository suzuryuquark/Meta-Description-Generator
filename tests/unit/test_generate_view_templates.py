import asyncio
from types import SimpleNamespace
from typing import Any, cast

from models.generation import DEFAULT_OUTPUT_LANGUAGE
from ui.generate_view import GenerateView


class FakeStorage:
    def __init__(self, templates):
        self.templates = templates

    async def get_templates(self):
        return self.templates

    async def save_templates(self, templates):
        self.templates = templates


async def noop_status(_message):
    return None


def make_view(storage: FakeStorage) -> GenerateView:
    view = GenerateView(
        page=SimpleNamespace(),
        storage=cast(Any, storage),
        error_service=None,
        gemini_service=cast(Any, None),
        website_fetch_service=cast(Any, None),
        show_status=noop_status,
        show_error=noop_status,
        load_history_cmd=None,
    )
    view.update = lambda: None
    return view


def test_template_saves_and_restores_output_language():
    storage = FakeStorage({"英語サイト": {}})
    view = make_view(storage)
    view.template_dropdown.value = "英語サイト"
    view.output_language_dropdown.value = "英語"

    asyncio.run(view.save_template_click(None))

    assert storage.templates["英語サイト"]["output_language"] == "英語"

    view.output_language_dropdown.value = DEFAULT_OUTPUT_LANGUAGE
    event = SimpleNamespace(control=SimpleNamespace(value="英語サイト"))
    asyncio.run(view.on_template_change(event))

    assert view.output_language_dropdown.value == "英語"


def test_existing_template_without_language_defaults_to_japanese():
    storage = FakeStorage({"既存": {"instruction": "共通指示"}})
    view = make_view(storage)
    view.output_language_dropdown.value = "英語"
    event = SimpleNamespace(control=SimpleNamespace(value="既存"))

    asyncio.run(view.on_template_change(event))

    assert view.output_language_dropdown.value == DEFAULT_OUTPUT_LANGUAGE


def test_legacy_string_template_defaults_to_japanese():
    storage = FakeStorage({"旧形式": "共通指示"})
    view = make_view(storage)
    view.output_language_dropdown.value = "英語"
    event = SimpleNamespace(control=SimpleNamespace(value="旧形式"))

    asyncio.run(view.on_template_change(event))

    assert view.global_instruction_input.value == "共通指示"
    assert view.output_language_dropdown.value == DEFAULT_OUTPUT_LANGUAGE
