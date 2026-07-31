from dataclasses import dataclass
from typing import Any

import pytest

from models.generation import (
    DESCRIPTION_MIN_CHARS,
    GenerationSuggestions,
    MetaSuggestion,
    RefinementResult,
)
from services.gemini_service import (
    GeminiResponseError,
    GeminiService,
    GeminiServiceError,
)


@dataclass
class FakeModel:
    name: str
    display_name: str
    supported_actions: list[str]


class FakeResponse:
    def __init__(self, parsed: Any = None, text: str | None = None):
        self.parsed = parsed
        self.text = text


class FakeModels:
    def __init__(self, response: FakeResponse, models: list[FakeModel] | None = None):
        self.response = response
        self.available_models = models or []
        self.generate_calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs):
        self.generate_calls.append(kwargs)
        return self.response

    def list(self):
        return iter(self.available_models)


class SequenceFakeModels(FakeModels):
    def __init__(self, responses: list[FakeResponse]):
        super().__init__(responses[-1])
        self.responses = iter(responses)

    def generate_content(self, **kwargs):
        self.generate_calls.append(kwargs)
        return next(self.responses)


class FakeClient:
    def __init__(self, models: FakeModels):
        self.models = models
        self.closed = False

    def close(self):
        self.closed = True


class FakeClientFactory:
    def __init__(self, client: FakeClient):
        self.client = client
        self.api_keys: list[str] = []

    def __call__(self, api_key: str) -> FakeClient:
        self.api_keys.append(api_key)
        return self.client


def make_suggestions(length: int = DESCRIPTION_MIN_CHARS) -> GenerationSuggestions:
    return GenerationSuggestions(
        [
            MetaSuggestion(
                title=f"パターン{i}",
                title_tag=f"タイトル{i}",
                description=str(i) * length,
            )
            for i in range(1, 4)
        ]
    )


def test_generate_descriptions_passes_selected_model_and_schema():
    fake_models = FakeModels(FakeResponse(parsed=make_suggestions()))
    client = FakeClient(fake_models)
    factory = FakeClientFactory(client)
    service = GeminiService(client_factory=factory)

    result = service.generate_descriptions(
        api_key="dummy-api-key",
        model_name="models/gemini-test",
        website_text="ページ本文",
        global_instruction="指示",
        target_keywords="キーワード",
        tone="SEO重視",
    )

    assert len(result) == 3
    assert fake_models.generate_calls[0]["model"] == "gemini-test"
    config = fake_models.generate_calls[0]["config"]
    assert config.response_schema is GenerationSuggestions
    assert factory.api_keys == ["dummy-api-key"]
    assert client.closed is True


def test_generate_descriptions_rejects_invalid_description_length():
    invalid_payload = [
        {
            "title": f"パターン{i}",
            "title_tag": f"タイトル{i}",
            "description": "短" * (DESCRIPTION_MIN_CHARS - 1),
        }
        for i in range(1, 4)
    ]
    service = GeminiService(
        client_factory=FakeClientFactory(
            FakeClient(FakeModels(FakeResponse(parsed=invalid_payload)))
        )
    )

    with pytest.raises(GeminiResponseError):
        service.generate_descriptions(
            "dummy-api-key",
            "gemini-test",
            "本文",
            "",
            "",
        )


def test_generate_descriptions_retries_once_after_invalid_response():
    invalid_payload = [
        {
            "title": f"パターン{i}",
            "title_tag": f"タイトル{i}",
            "description": "短" * (DESCRIPTION_MIN_CHARS - 1),
        }
        for i in range(1, 4)
    ]
    fake_models = SequenceFakeModels(
        [
            FakeResponse(parsed=invalid_payload),
            FakeResponse(parsed=make_suggestions()),
        ]
    )
    service = GeminiService(client_factory=FakeClientFactory(FakeClient(fake_models)))

    result = service.generate_descriptions(
        "dummy-api-key",
        "gemini-test",
        "本文",
        "",
        "",
    )

    assert len(result) == 3
    assert len(fake_models.generate_calls) == 2
    assert "前回の出力は要件を満たしませんでした" in fake_models.generate_calls[1]["contents"]


def test_refine_description_passes_model_and_returns_validated_text():
    expected = "修" * DESCRIPTION_MIN_CHARS
    fake_models = FakeModels(FakeResponse(parsed=RefinementResult(description=expected)))
    client = FakeClient(fake_models)
    service = GeminiService(client_factory=FakeClientFactory(client))

    result = service.refine_description(
        "dummy-api-key",
        "gemini-refine",
        "本文",
        "元の文章",
        "",
        "",
        "柔らかく",
    )

    assert result == expected
    assert fake_models.generate_calls[0]["model"] == "gemini-refine"
    assert client.closed is True


def test_list_models_filters_generate_content_and_normalizes_names():
    fake_models = FakeModels(
        FakeResponse(),
        models=[
            FakeModel(
                name="models/gemini-stable",
                display_name="Gemini Stable",
                supported_actions=["generateContent"],
            ),
            FakeModel(
                name="models/gemini-preview",
                display_name="Gemini Preview",
                supported_actions=["GENERATE_CONTENT"],
            ),
            FakeModel(
                name="models/text-embedding",
                display_name="Embedding",
                supported_actions=["embedContent"],
            ),
        ],
    )
    client = FakeClient(fake_models)
    service = GeminiService(client_factory=FakeClientFactory(client))

    result = service.list_models("dummy-api-key")

    assert [model.model_id for model in result] == [
        "gemini-stable",
        "gemini-preview",
    ]
    assert [model.stage for model in result] == ["Stable", "Preview"]
    assert client.closed is True


def test_normalize_model_id_rejects_empty_value():
    with pytest.raises(GeminiServiceError):
        GeminiService.normalize_model_id("  ")
