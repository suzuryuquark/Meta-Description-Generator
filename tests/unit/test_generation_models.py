import pytest
from pydantic import ValidationError

from models.generation import (
    DESCRIPTION_MAX_CHARS,
    DESCRIPTION_MIN_CHARS,
    GenerationSuggestions,
    MetaSuggestion,
    RefinementResult,
)


def suggestion(description_length: int) -> MetaSuggestion:
    return MetaSuggestion(
        title="要約型",
        title_tag="テスト用タイトル",
        description="あ" * description_length,
    )


@pytest.mark.parametrize(
    "description_length",
    [DESCRIPTION_MIN_CHARS, DESCRIPTION_MAX_CHARS],
)
def test_description_accepts_range_boundaries(description_length: int):
    assert len(suggestion(description_length).description) == description_length


@pytest.mark.parametrize(
    "description_length",
    [DESCRIPTION_MIN_CHARS - 1, DESCRIPTION_MAX_CHARS + 1],
)
def test_description_rejects_values_outside_range(description_length: int):
    with pytest.raises(ValidationError):
        suggestion(description_length)


def test_generation_requires_exactly_three_suggestions():
    with pytest.raises(ValidationError):
        GenerationSuggestions([suggestion(DESCRIPTION_MIN_CHARS)] * 2)

    result = GenerationSuggestions([suggestion(DESCRIPTION_MIN_CHARS)] * 3)

    assert len(result.root) == 3


def test_refinement_uses_same_description_range():
    result = RefinementResult(description="い" * DESCRIPTION_MAX_CHARS)

    assert len(result.description) == DESCRIPTION_MAX_CHARS


def test_whitespace_is_removed_before_description_length_validation():
    with pytest.raises(ValidationError):
        MetaSuggestion(
            title="要約型",
            title_tag="タイトル",
            description=f" {'あ' * (DESCRIPTION_MIN_CHARS - 1)} ",
        )
