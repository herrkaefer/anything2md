"""anything2md package."""

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

SwiftToMarkdownConverter = MarkdownConverter

__all__ = [
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
