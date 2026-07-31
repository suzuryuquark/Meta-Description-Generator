from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, Field, RootModel, field_validator

TITLE_MAX_CHARS = 32
DESCRIPTION_MIN_CHARS = 100
DESCRIPTION_MAX_CHARS = 150
SUGGESTION_COUNT = 3
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"


class MetaSuggestion(BaseModel):
    """A validated title and meta description proposal."""

    title: str = Field(min_length=1, description="提案パターンの特徴を表す短い名称")
    title_tag: str = Field(min_length=1, description="生成したタイトルタグ")
    description: str = Field(
        min_length=DESCRIPTION_MIN_CHARS,
        max_length=DESCRIPTION_MAX_CHARS,
        description="100文字以上150文字以下のmeta description",
    )

    @field_validator("title", "title_tag", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("生成結果の文字列フィールドを空にはできません")
        return stripped

    @field_validator("description")
    @classmethod
    def validate_stripped_description_length(cls, value: str) -> str:
        if not DESCRIPTION_MIN_CHARS <= len(value) <= DESCRIPTION_MAX_CHARS:
            raise ValueError(
                f"descriptionは{DESCRIPTION_MIN_CHARS}文字以上"
                f"{DESCRIPTION_MAX_CHARS}文字以下である必要があります"
            )
        return value


SuggestionList = Annotated[
    list[MetaSuggestion],
    Field(min_length=SUGGESTION_COUNT, max_length=SUGGESTION_COUNT),
]


class GenerationSuggestions(RootModel[SuggestionList]):
    """Exactly three validated metadata proposals."""


class RefinementResult(BaseModel):
    """A validated rewritten meta description."""

    description: str = Field(
        min_length=DESCRIPTION_MIN_CHARS,
        max_length=DESCRIPTION_MAX_CHARS,
        description="100文字以上150文字以下の修正後meta description",
    )

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        stripped = value.strip()
        if not DESCRIPTION_MIN_CHARS <= len(stripped) <= DESCRIPTION_MAX_CHARS:
            raise ValueError(
                f"descriptionは{DESCRIPTION_MIN_CHARS}文字以上"
                f"{DESCRIPTION_MAX_CHARS}文字以下である必要があります"
            )
        return stripped


@dataclass(frozen=True, slots=True)
class GeminiModelInfo:
    """A model that can generate text through the Gemini API."""

    model_id: str
    display_name: str
    stage: str

    @property
    def option_label(self) -> str:
        return f"{self.display_name} [{self.stage}]"
