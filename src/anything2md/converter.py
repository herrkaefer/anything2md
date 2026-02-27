from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal, Sequence, TypeGuard
from urllib.parse import urlparse
import weakref

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

BytesLike = bytes | bytearray | memoryview
FileInput = tuple[BytesLike, str]


class MarkdownConverter:
    """Single-entry converter for URL/local/binary inputs."""

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        *,
        credentials: CloudflareCredentials | None = None,
        options: ConvertOptions = ConvertOptions(),
        client: CloudflareClient | None = None,
        download_session: httpx.Client | None = None,
    ) -> None:
        if credentials is not None and (account_id is not None or api_token is not None):
            raise ValueError("Provide either credentials or account_id/api_token, not both.")

        if credentials is None:
            if not account_id or not api_token:
                raise ValueError("account_id and api_token are required.")
            credentials = CloudflareCredentials(account_id=account_id, api_token=api_token)

        self.options = options
        self._client = client or CloudflareClient(credentials=credentials, options=options)
        self._download_session = download_session or httpx.Client(timeout=options.timeout)
        self._owns_client = client is None
        self._owns_download_session = download_session is None
        self._finalizer = weakref.finalize(
            self,
            MarkdownConverter._cleanup,
            self._client if self._owns_client else None,
            self._download_session if self._owns_download_session else None,
        )

    @classmethod
    def with_cloudflare(
        cls,
        account_id: str,
        api_token: str,
        timeout: float = 60.0,
        max_retry_count: int = 2,
        retry_base_delay: float = 1.0,
    ) -> "MarkdownConverter":
        options = ConvertOptions(
            timeout=timeout,
            max_retry_count=max_retry_count,
            retry_base_delay=retry_base_delay,
        )
        return cls(account_id=account_id, api_token=api_token, options=options)

    def __enter__(self) -> "MarkdownConverter":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self._finalizer.alive:
            self._finalizer()

    def transform(
        self,
        input_value: str | Path | BytesLike | FileInput | Sequence[FileInput],
        *,
        filename: str | None = None,
        url_strategy: Literal["auto", "download", "browser"] = "auto",
        progress_callback: Callable[[str], None] | None = None,
    ) -> ConversionResult | list[ConversionResult]:
        """Transform any supported input through one API.

        Supported input shapes:
        - URL string
        - local file path string/pathlib.Path
        - raw bytes (requires filename=...)
        - tuple of (bytes, filename)
        - batch list/tuple of (bytes, filename)
        """
        if isinstance(input_value, (str, Path)):
            text = str(input_value)
            parsed = urlparse(text)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                return self.convert_remote_url(
                    text,
                    strategy=url_strategy,
                    progress_callback=progress_callback,
                )
            return self.convert_file(text, progress_callback=progress_callback)

        if isinstance(input_value, (bytes, bytearray, memoryview)):
            if not filename:
                raise TypeError("filename is required when input is raw bytes.")
            return self.convert_bytes(
                bytes(input_value),
                filename,
                progress_callback=progress_callback,
            )

        if self._is_file_input(input_value):
            data, file_name = input_value
            return self.convert_bytes(bytes(data), file_name, progress_callback=progress_callback)

        if self._is_batch_file_input(input_value):
            normalized = [(bytes(data), file_name) for data, file_name in input_value]
            return self.convert_batch(normalized)

        raise TypeError("Unsupported input type for transform().")

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
        path = Path(file_path).expanduser()
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
        try:
            markdown = self._client.markdown_from_url(url)
        except HTTPError as exc:
            if exc.status_code in {401, 403}:
                self._notify(
                    progress_callback,
                    "Browser Rendering auth failed, falling back to download + Workers AI toMarkdown.",
                )
                return self.convert_url(url, progress_callback=progress_callback)
            raise
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

    @staticmethod
    def _cleanup(client: CloudflareClient | None, download_session: httpx.Client | None) -> None:
        seen: set[int] = set()
        for resource in (client, download_session):
            if resource is None:
                continue
            resource_id = id(resource)
            if resource_id in seen:
                continue
            seen.add(resource_id)
            try:
                resource.close()
            except Exception:
                pass

    @staticmethod
    def _is_file_input(value: object) -> TypeGuard[FileInput]:
        return (
            isinstance(value, tuple)
            and len(value) == 2
            and isinstance(value[0], (bytes, bytearray, memoryview))
            and isinstance(value[1], str)
        )

    @classmethod
    def _is_batch_file_input(cls, value: object) -> TypeGuard[Sequence[FileInput]]:
        if not isinstance(value, Sequence):
            return False
        if isinstance(value, (str, bytes, bytearray, memoryview, Path)):
            return False
        return all(cls._is_file_input(item) for item in value)

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
