from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConversionResult:
    """One converted file returned by Workers AI."""

    name: str
    mime_type: str
    tokens: int
    markdown: str

    @classmethod
    def from_api_item(cls, payload: dict) -> "ConversionResult":
        return cls(
            name=str(payload["name"]),
            mime_type=str(payload["mimeType"]),
            tokens=int(payload["tokens"]),
            markdown=str(payload["data"]),
        )
