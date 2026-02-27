from __future__ import annotations

from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

import httpx

from .client import CloudflareClient
from .config import CloudflareCredentials, ConvertOptions
from .errors import (
    FileReadError,
    HTTPError,
    InvalidResponseError,
    NetworkError,
    UnsupportedFormatError,
)
from .formats import from_filename, from_mime_type
from .models import ConversionResult


class MarkdownConverter:
    """Main entry point for converting files to Markdown using Workers AI."""

    def __init__(
        self,
        credentials: CloudflareCredentials,
        options: ConvertOptions = ConvertOptions(),
        client: CloudflareClient | None = None,
        download_session: httpx.Client | None = None,
    ) -> None:
        self.options = options
        self._client = client or CloudflareClient(credentials=credentials, options=options)
        self._download_session = download_session or httpx.Client(timeout=options.timeout)

    @classmethod
    def with_cloudflare(
        cls,
        account_id: str,
        api_token: str,
        timeout: float = 60.0,
        max_retry_count: int = 2,
        retry_base_delay: float = 1.0,
    ) -> "MarkdownConverter":
        credentials = CloudflareCredentials(account_id=account_id, api_token=api_token)
        options = ConvertOptions(
            timeout=timeout,
            max_retry_count=max_retry_count,
            retry_base_delay=retry_base_delay,
        )
        return cls(credentials=credentials, options=options)

    def convert_url(self, url: str) -> ConversionResult:
        try:
            response = self._download_session.get(url, timeout=self.options.timeout)
        except httpx.HTTPError as exc:
            raise NetworkError(exc) from exc

        if not 200 <= response.status_code < 300:
            raise HTTPError(response.status_code, response.text)

        filename = self._inferred_filename(url, response)
        return self.convert_bytes(response.content, filename)

    def convert_bytes(self, data: bytes, filename: str) -> ConversionResult:
        if from_filename(filename) is None:
            raise UnsupportedFormatError(filename)
        results = self._client.to_markdown([(data, filename)])
        if not results:
            raise InvalidResponseError()
        return results[0]

    def convert_file(self, file_path: str | Path) -> ConversionResult:
        path = Path(file_path)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise FileReadError(exc) from exc
        return self.convert_bytes(data, path.name)

    def convert_batch(self, files: Sequence[tuple[bytes, str]]) -> list[ConversionResult]:
        for _, filename in files:
            if from_filename(filename) is None:
                raise UnsupportedFormatError(filename)
        return self._client.to_markdown(files)

    def convert(self, input_value: str | Path) -> ConversionResult:
        text = str(input_value)
        parsed = urlparse(text)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return self.convert_url(text)
        return self.convert_file(text)

    def close(self) -> None:
        self._client.close()
        self._download_session.close()

    def _inferred_filename(self, url: str, response: httpx.Response) -> str:
        candidate = Path(urlparse(url).path).name
        if candidate and from_filename(candidate) is not None:
            return candidate

        content_type = response.headers.get("content-type", "")
        by_mime = from_mime_type(content_type)
        if by_mime is not None:
            return f"downloaded.{by_mime.file_extension}"

        return candidate or "downloaded"
