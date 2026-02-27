from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from anything2md.client import CloudflareClient
from anything2md.config import CloudflareCredentials, ConvertOptions
from anything2md.converter import MarkdownConverter
from anything2md.errors import FileReadError, UnsupportedFormatError


def make_upload_client(upload_handler) -> CloudflareClient:
    transport = httpx.MockTransport(upload_handler)
    session = httpx.Client(transport=transport, timeout=10.0)
    credentials = CloudflareCredentials(account_id="acc", api_token="token")
    options = ConvertOptions(timeout=10.0, max_retry_count=2, retry_base_delay=0.0)
    return CloudflareClient(credentials=credentials, options=options, session=session)


def make_download_session(download_handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(download_handler), timeout=10.0)


def test_convert_bytes_throws_unsupported_format() -> None:
    def upload_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("No upload expected")

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(lambda _: httpx.Response(500)),
    )

    with pytest.raises(UnsupportedFormatError) as exc:
        converter.convert_bytes(b"hello", "note.txt")

    assert exc.value.value == "note.txt"


def test_convert_url_downloads_and_converts() -> None:
    def download_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "example.com"
        return httpx.Response(200, content=b"%PDF-1.4", headers={"Content-Type": "application/pdf"})

    def upload_handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "result": [{"name": "downloaded.pdf", "mimeType": "application/pdf", "tokens": 9, "data": "# Converted"}],
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(download_handler),
    )

    result = converter.convert_url("https://example.com/document")
    assert result.name == "downloaded.pdf"
    assert result.markdown == "# Converted"


def test_convert_file() -> None:
    def upload_handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "result": [{"name": "file.pdf", "mimeType": "application/pdf", "tokens": 3, "data": "# File"}],
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(lambda _: httpx.Response(500)),
    )

    path = Path("/tmp/test-anything2md.pdf")
    path.write_bytes(b"pdfdata")
    try:
        result = converter.convert_file(path)
    finally:
        path.unlink(missing_ok=True)

    assert result.markdown == "# File"


def test_convert_file_throws_file_read_error() -> None:
    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(lambda _: httpx.Response(500)),
        download_session=make_download_session(lambda _: httpx.Response(500)),
    )

    with pytest.raises(FileReadError):
        converter.convert_file("/tmp/does-not-exist-anything2md.pdf")


def test_convert_empty_batch_returns_empty_without_network() -> None:
    state = {"calls": 0}

    def upload_handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        return httpx.Response(200, json={"result": [], "success": True, "errors": [], "messages": []})

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(lambda _: httpx.Response(500)),
    )

    assert converter.convert_batch([]) == []
    assert state["calls"] == 0
