import math
from dataclasses import dataclass, field


def estimate_prompt_tokens(text: str) -> int:
    """Conservatively estimate tokens without making an additional API request."""

    units = 0.0
    for character in text:
        if character.isspace():
            units += 0.1
        elif ord(character) < 128:
            units += 0.25
        else:
            units += 1.0
    return math.ceil(units)


def truncate_to_token_budget(text: str, maximum_tokens: int) -> str:
    if maximum_tokens <= 0:
        return ""
    if estimate_prompt_tokens(text) <= maximum_tokens:
        return text
    lower = 0
    upper = len(text)
    while lower < upper:
        middle = (lower + upper + 1) // 2
        if estimate_prompt_tokens(text[:middle]) <= maximum_tokens:
            lower = middle
        else:
            upper = middle - 1
    return text[:lower]


@dataclass(frozen=True, slots=True)
class PageMetadata:
    """Metadata extracted from an untrusted web page."""

    title: str = ""
    description: str = ""
    canonical_url: str = ""
    robots: str = ""
    language: str = ""
    open_graph: dict[str, str] = field(default_factory=dict)
    structured_data: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FetchedPage:
    """A bounded, validated representation of a fetched web page."""

    requested_url: str
    final_url: str
    metadata: PageMetadata
    content: str

    def to_prompt_text(self, maximum_tokens: int = 12_000) -> str:
        metadata_lines = [
            f"取得URL: {self.final_url}",
            f"Title: {self.metadata.title}",
            f"Current Description: {self.metadata.description}",
            f"Canonical: {self.metadata.canonical_url}",
            f"Robots: {self.metadata.robots}",
            f"Language: {self.metadata.language}",
        ]
        metadata_lines.extend(
            f"{key}: {value}" for key, value in sorted(self.metadata.open_graph.items())
        )
        metadata_lines.extend(f"Structured Data: {item}" for item in self.metadata.structured_data)
        prefix = "\n".join(line for line in metadata_lines if not line.endswith(": "))
        separator = "\n\n本文:\n"
        return truncate_to_token_budget(f"{prefix}{separator}{self.content}", maximum_tokens)
