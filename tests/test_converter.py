from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from anything2md.client import CloudflareClient
from anything2md.config import CloudflareCredentials, ConvertOptions
from anything2md.converter import MarkdownConverter
from anything2md.errors import APIError, FileReadError, UnsupportedFormatError


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


def test_convert_single_entry_requires_filename_for_raw_bytes() -> None:
    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(lambda _: httpx.Response(500)),
        download_session=make_download_session(lambda _: httpx.Response(500)),
    )

    with pytest.raises(TypeError):
        converter.transform(b"hello")


def test_convert_single_entry_accepts_file_tuple() -> None:
    def upload_handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "result": [
                {
                    "name": "inline.pdf",
                    "mimeType": "application/pdf",
                    "format": "markdown",
                    "tokens": 1,
                    "data": "# Inline",
                }
            ],
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

    result = converter.transform((b"%PDF", "inline.pdf"))
    assert result.markdown == "# Inline"


def test_convert_url_downloads_and_converts() -> None:
    def download_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "example.com"
        return httpx.Response(200, content=b"%PDF-1.4", headers={"Content-Type": "application/pdf"})

    def upload_handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "result": [
                {
                    "name": "downloaded.pdf",
                    "mimeType": "application/pdf",
                    "format": "markdown",
                    "tokens": 9,
                    "data": "# Converted",
                }
            ],
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


def test_direct_constructor_credentials_work() -> None:
    def upload_handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "result": [
                {
                    "name": "inline.pdf",
                    "mimeType": "application/pdf",
                    "format": "markdown",
                    "tokens": 2,
                    "data": "# OK",
                }
            ],
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    converter = MarkdownConverter(
        account_id="acc",
        api_token="token",
        client=make_upload_client(upload_handler),
        download_session=make_download_session(lambda _: httpx.Response(500)),
    )
    result = converter.transform(b"%PDF", filename="a.pdf")
    assert result.markdown == "# OK"


def test_convert_file() -> None:
    def upload_handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "result": [
                {
                    "name": "file.pdf",
                    "mimeType": "application/pdf",
                    "format": "markdown",
                    "tokens": 3,
                    "data": "# File",
                }
            ],
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


def test_convert_bytes_raises_api_error_for_per_file_error_result() -> None:
    def upload_handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "result": [
                {
                    "name": "bad.pdf",
                    "mimeType": "application/pdf",
                    "format": "error",
                    "error": "OCR failed",
                }
            ],
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

    with pytest.raises(APIError) as exc:
        converter.convert_bytes(b"%PDF", "sample.pdf")

    assert exc.value.messages == ["OCR failed"]


def test_supported_formats_passthrough() -> None:
    def upload_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and str(request.url).endswith("/ai/tomarkdown/supported"):
            payload = {
                "result": [{"extension": "pdf", "mimeType": "application/pdf"}],
                "success": True,
                "errors": [],
                "messages": [],
            }
            return httpx.Response(200, json=payload)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(lambda _: httpx.Response(500)),
    )

    result = converter.supported_formats()
    assert len(result) == 1
    assert result[0].extension == "pdf"
    assert result[0].mime_type == "application/pdf"


def test_convert_remote_url_auto_uses_browser_for_webpages() -> None:
    def download_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("accept") == "text/markdown"
        return httpx.Response(406, text="Not Acceptable")

    def upload_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url).endswith("/browser-rendering/markdown"):
            return httpx.Response(
                200,
                json={
                    "result": "# Web markdown",
                    "success": True,
                    "errors": [],
                    "messages": [],
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(download_handler),
    )

    result = converter.convert_remote_url("https://example.com/page")
    assert result.markdown == "# Web markdown"
    assert result.mime_type == "text/html"
    assert result.tokens is None


def test_convert_remote_url_browser_forwards_advanced_options() -> None:
    def download_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("accept") == "text/markdown"
        return httpx.Response(406, text="Not Acceptable")

    def upload_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url).endswith("/browser-rendering/markdown"):
            body = json.loads(request.read().decode("utf-8"))
            assert body == {
                "url": "https://example.com/page",
                "gotoOptions": {"waitUntil": "networkidle2"},
                "rejectRequestPattern": ["/^.*\\.(css)$/", "/analytics/"],
            }
            return httpx.Response(
                200,
                json={
                    "result": "# Web markdown",
                    "success": True,
                    "errors": [],
                    "messages": [],
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(download_handler),
    )

    result = converter.convert_remote_url(
        "https://example.com/page",
        strategy="browser",
        wait_until="networkidle2",
        reject_request_pattern=["/^.*\\.(css)$/", "/analytics/"],
    )
    assert result.markdown == "# Web markdown"
    assert result.mime_type == "text/html"


def test_convert_web_url_rejects_invalid_wait_until() -> None:
    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(lambda _: httpx.Response(500)),
        download_session=make_download_session(lambda _: httpx.Response(406, text="Not Acceptable")),
    )

    with pytest.raises(ValueError, match="wait_until"):
        converter.convert_web_url("https://example.com/page", wait_until="load")  # type: ignore[arg-type]


def test_convert_web_url_rejects_invalid_reject_request_pattern() -> None:
    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(lambda _: httpx.Response(500)),
        download_session=make_download_session(lambda _: httpx.Response(406, text="Not Acceptable")),
    )

    with pytest.raises(ValueError, match="at least one pattern"):
        converter.convert_web_url("https://example.com/page", reject_request_pattern=[])

    with pytest.raises(ValueError, match="only strings"):
        converter.convert_web_url(
            "https://example.com/page",
            reject_request_pattern=["/style/", 123],  # type: ignore[list-item]
        )


def test_convert_web_url_uses_markdown_for_agents_when_available() -> None:
    def download_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("accept") == "text/markdown"
        return httpx.Response(
            200,
            text="# Markdown for Agents",
            headers={"Content-Type": "text/markdown; charset=utf-8", "X-Markdown-Tokens": "123"},
        )

    def upload_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Browser fallback should not be called: {request.method} {request.url}")

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(download_handler),
    )

    result = converter.convert_web_url("https://example.com/page")
    assert result.markdown == "# Markdown for Agents"
    assert result.mime_type == "text/markdown"
    assert result.tokens == 123
    assert result.error is None


def test_convert_web_url_falls_back_to_browser_on_markdown_for_agents_exception() -> None:
    def download_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    def upload_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url).endswith("/browser-rendering/markdown"):
            return httpx.Response(
                200,
                json={"result": "# Fallback markdown", "success": True, "errors": [], "messages": []},
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(download_handler),
    )

    result = converter.convert_web_url("https://example.com/page")
    assert result.markdown == "# Fallback markdown"
    assert result.mime_type == "text/html"


def test_convert_web_url_falls_back_to_download_on_browser_auth_error() -> None:
    state = {"calls": 0}

    def download_handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            assert request.headers.get("accept") == "text/markdown"
            return httpx.Response(406, text="not markdown")
        return httpx.Response(200, content=b"<html><body>hi</body></html>", headers={"Content-Type": "text/html"})

    def upload_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url).endswith("/browser-rendering/markdown"):
            return httpx.Response(
                401,
                json={
                    "result": None,
                    "success": False,
                    "errors": [{"code": 10000, "message": "Authentication error"}],
                    "messages": [],
                },
            )
        if request.method == "POST" and str(request.url).endswith("/ai/tomarkdown"):
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "name": "downloaded.html",
                            "mimeType": "text/html",
                            "format": "markdown",
                            "tokens": 5,
                            "data": "# HTML fallback",
                        }
                    ],
                    "success": True,
                    "errors": [],
                    "messages": [],
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(download_handler),
    )

    result = converter.convert_web_url("https://example.com/page")
    assert result.markdown == "# HTML fallback"
    assert result.mime_type == "text/html"


def test_convert_remote_url_auto_uses_download_for_document_urls() -> None:
    def download_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"%PDF-1.4", headers={"Content-Type": "application/pdf"})

    def upload_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url).endswith("/ai/tomarkdown"):
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "name": "sample.pdf",
                            "mimeType": "application/pdf",
                            "format": "markdown",
                            "tokens": 7,
                            "data": "# File markdown",
                        }
                    ],
                    "success": True,
                    "errors": [],
                    "messages": [],
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    converter = MarkdownConverter(
        credentials=CloudflareCredentials(account_id="acc", api_token="token"),
        client=make_upload_client(upload_handler),
        download_session=make_download_session(download_handler),
    )

    result = converter.convert_remote_url("https://example.com/sample.pdf")
    assert result.markdown == "# File markdown"
    assert result.tokens == 7
