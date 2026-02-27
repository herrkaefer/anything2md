from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ConversionResult:
    """One converted file returned by Workers AI."""

    name: str
    mime_type: str
    format: Literal["markdown", "error"]
    tokens: int | None
    markdown: str
    error: str | None

    @classmethod
    def from_api_item(cls, payload: dict) -> "ConversionResult":
        result_format = str(payload.get("format", "markdown"))
        if result_format not in {"markdown", "error"}:
            raise ValueError(f"Unsupported result format: {result_format}")

        tokens_value = payload.get("tokens")
        markdown_value = payload.get("data")
        error_value = payload.get("error")

        tokens = int(tokens_value) if tokens_value is not None else None
        markdown = str(markdown_value) if markdown_value is not None else ""
        error = str(error_value) if error_value is not None else None

        return cls(
            name=str(payload["name"]),
            mime_type=str(payload["mimeType"]),
            format=result_format,
            tokens=tokens,
            markdown=markdown,
            error=error,
        )

    @property
    def is_error(self) -> bool:
        return self.format == "error"


@dataclass(frozen=True)
class SupportedFormatInfo:
    """One supported input format returned by /ai/tomarkdown/supported."""

    extension: str
    mime_type: str

    @classmethod
    def from_api_item(cls, payload: dict) -> "SupportedFormatInfo":
        return cls(
            extension=str(payload["extension"]),
            mime_type=str(payload["mimeType"]),
        )
