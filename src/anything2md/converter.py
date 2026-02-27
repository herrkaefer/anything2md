from __future__ import annotations

from pathlib import Path
from typing import Callable
from typing import Literal
from typing import Sequence
from urllib.parse import urlparse

import httpx

from .client import CloudflareClient
from .config import CloudflareCredentials, ConvertOptions
from .errors import (
    APIError,
    FileReadError,
    HTTPError,
    InvalidResponseError,
    NetworkError,
    UnsupportedFormatError,
)
from .formats import from_filename, from_mime_type
from .models import ConversionResult, SupportedFormatInfo


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

    def convert_url(
        self,
        url: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ConversionResult:
        self._notify(progress_callback, f"Downloading URL: {url}")
        try:
            response = self._download_session.get(url, timeout=self.options.timeout)
        except httpx.HTTPError as exc:
            raise NetworkError(exc) from exc

        if not 200 <= response.status_code < 300:
            raise HTTPError(response.status_code, response.text)

        filename = self._inferred_filename(url, response)
        self._notify(
            progress_callback,
            f"Downloaded {len(response.content)} bytes, inferred filename '{filename}'.",
        )
        return self.convert_bytes(
            response.content,
            filename,
            progress_callback=progress_callback,
        )

    def convert_bytes(
        self,
        data: bytes,
        filename: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ConversionResult:
        if from_filename(filename) is None:
            raise UnsupportedFormatError(filename)
        self._notify(progress_callback, f"Uploading '{filename}' to Cloudflare Workers AI.")
        results = self._client.to_markdown([(data, filename)])
        if not results:
            raise InvalidResponseError()
        result = results[0]
        if result.is_error:
            raise APIError([result.error or f"Conversion failed for file: {filename}"])
        self._notify(progress_callback, "Conversion completed.")
        return result

    def convert_file(
        self,
        file_path: str | Path,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ConversionResult:
        path = Path(file_path)
        self._notify(progress_callback, f"Reading local file: {path}")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise FileReadError(exc) from exc
        self._notify(progress_callback, f"Read {len(data)} bytes from local file.")
        return self.convert_bytes(data, path.name, progress_callback=progress_callback)

    def convert_batch(self, files: Sequence[tuple[bytes, str]]) -> list[ConversionResult]:
        for _, filename in files:
            if from_filename(filename) is None:
                raise UnsupportedFormatError(filename)
        return self._client.to_markdown(files)

    def supported_formats(self) -> list[SupportedFormatInfo]:
        return self._client.supported_formats()

    def convert_web_url(
        self,
        url: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ConversionResult:
        self._notify(progress_callback, f"Trying Markdown for Agents for URL: {url}")

        try:
            response = self._download_session.get(
                url,
                headers={"Accept": "text/markdown"},
                timeout=self.options.timeout,
            )
            content_type = response.headers.get("content-type", "").lower()

            if 200 <= response.status_code < 300 and "text/markdown" in content_type:
                token_header = response.headers.get("x-markdown-tokens")
                tokens: int | None
                if token_header is None:
                    tokens = None
                else:
                    try:
                        tokens = int(token_header)
                    except ValueError:
                        tokens = None
                self._notify(progress_callback, "Markdown for Agents succeeded.")
                return ConversionResult(
                    name=url,
                    mime_type="text/markdown",
                    format="markdown",
                    tokens=tokens,
                    markdown=response.text,
                    error=None,
                )

            self._notify(
                progress_callback,
                "Markdown for Agents unavailable for this URL, falling back to Browser Rendering.",
            )
        except httpx.HTTPError:
            self._notify(
                progress_callback,
                "Markdown for Agents request failed, falling back to Browser Rendering.",
            )

        self._notify(progress_callback, f"Rendering webpage URL via Cloudflare Browser Rendering: {url}")
        markdown = self._client.markdown_from_url(url)
        self._notify(progress_callback, "Webpage conversion completed.")
        return ConversionResult(
            name=url,
            mime_type="text/html",
            format="markdown",
            tokens=None,
            markdown=markdown,
            error=None,
        )

    def convert_remote_url(
        self,
        url: str,
        strategy: Literal["auto", "download", "browser"] = "auto",
        progress_callback: Callable[[str], None] | None = None,
    ) -> ConversionResult:
        if strategy == "download":
            return self.convert_url(url, progress_callback=progress_callback)
        if strategy == "browser":
            return self.convert_web_url(url, progress_callback=progress_callback)

        if self._looks_like_supported_document_url(url):
            return self.convert_url(url, progress_callback=progress_callback)
        return self.convert_web_url(url, progress_callback=progress_callback)

    def convert(self, input_value: str | Path) -> ConversionResult:
        text = str(input_value)
        parsed = urlparse(text)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return self.convert_remote_url(text, strategy="auto")
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

    @staticmethod
    def _looks_like_supported_document_url(url: str) -> bool:
        candidate = Path(urlparse(url).path).name
        return bool(candidate and from_filename(candidate) is not None)

    @staticmethod
    def _notify(callback: Callable[[str], None] | None, message: str) -> None:
        if callback is not None:
            callback(message)
