import csv

from models.generation import DESCRIPTION_MIN_CHARS, MetaSuggestion
from services.export_service import ExportService
from ui.generate_view import GenerateView
from ui_components import ResultCard, create_result_card


def noop(_):
    return None


def test_result_card_exposes_named_values_for_history():
    suggestion = MetaSuggestion(
        title="要約型",
        title_tag="生成タイトル",
        description="説" * DESCRIPTION_MIN_CHARS,
    )

    card = create_result_card(
        suggestion,
        "https://example.com",
        "page",
        "gemini-test",
        noop,
        noop,
        noop,
    )
    card.title_field.value = "編集タイトル"
    card.description_field.value = "編" * 120

    assert isinstance(card, ResultCard)
    entry = GenerateView._history_entry(card, "2026-07-31 12:00:00", "編集済み")
    assert entry["id"] == card.history_id
    assert entry["url"] == "https://example.com/page"
    assert entry["model"] == "gemini-test"
    assert entry["status"] == "編集済み"
    assert entry["title_tag"] == "編集タイトル"
    assert entry["description"] == "編" * 120


def test_csv_export_includes_model_and_status(tmp_path):
    output = tmp_path / "history.csv"
    ExportService.export_history_to_csv(
        str(output),
        [
            {
                "timestamp": "2026-07-31 12:00:00",
                "url": "https://example.com/page",
                "model": "gemini-test",
                "status": "編集済み",
                "pattern": "要約型",
                "title_tag": "編集タイトル",
                "description": "編" * 120,
            }
        ],
    )

    with output.open(encoding="utf-8-sig", newline="") as exported:
        rows = list(csv.reader(exported))

    assert rows[0][:5] == ["日時", "URL", "使用モデル", "状態", "パターン"]
    assert rows[1][2:4] == ["gemini-test", "編集済み"]
