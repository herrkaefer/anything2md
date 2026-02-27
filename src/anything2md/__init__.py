"""anything2md package."""

import sys
from types import ModuleType
from typing import Any

from .config import CloudflareCredentials, ConvertOptions
from .converter import MarkdownConverter
from .errors import (
    APIError,
    Anything2MDError,
    FileReadError,
    HTTPError,
    InvalidResponseError,
    NetworkError,
    UnsupportedFormatError,
)
from .models import ConversionResult, SupportedFormatInfo


def anything2md(*args: Any, **kwargs: Any) -> MarkdownConverter:
    """Factory shorthand for MarkdownConverter(...)."""
    return MarkdownConverter(*args, **kwargs)


class _Anything2MDModule(ModuleType):
    def __call__(self, *args: Any, **kwargs: Any) -> MarkdownConverter:
        return MarkdownConverter(*args, **kwargs)


sys.modules[__name__].__class__ = _Anything2MDModule

SwiftToMarkdownConverter = MarkdownConverter

__all__ = [
    "anything2md",
    "Anything2MDError",
    "UnsupportedFormatError",
    "NetworkError",
    "FileReadError",
    "HTTPError",
    "APIError",
    "InvalidResponseError",
    "CloudflareCredentials",
    "ConvertOptions",
    "ConversionResult",
    "SupportedFormatInfo",
    "MarkdownConverter",
    "SwiftToMarkdownConverter",
]
