from __future__ import annotations

import json

import httpx
import pytest

from anything2md.client import CloudflareClient
from anything2md.config import CloudflareCredentials, ConvertOptions
from anything2md.errors import APIError, HTTPError


def make_client(handler, *, max_retry_count: int = 2, retry_base_delay: float = 0.0) -> CloudflareClient:
    transport = httpx.MockTransport(handler)
    session = httpx.Client(transport=transport, timeout=10.0)
    credentials = CloudflareCredentials(account_id="acc", api_token="token")
    options = ConvertOptions(timeout=10.0, max_retry_count=max_retry_count, retry_base_delay=retry_base_delay)
    return CloudflareClient(credentials=credentials, options=options, session=session)


def test_to_markdown_success_decodes_data_as_markdown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/ai/tomarkdown" in str(request.url)
        assert request.headers["Authorization"] == "Bearer token"
        assert request.headers["Content-Type"].startswith("multipart/form-data; boundary=")

        payload = {
            "result": [
                {
                    "name": "file.pdf",
                    "mimeType": "application/pdf",
                    "format": "markdown",
                    "tokens": 12,
                    "data": "# Markdown",
                }
            ],
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    client = make_client(handler)
    results = client.to_markdown([(b"x", "file.pdf")])
    assert len(results) == 1
    assert results[0].markdown == "# Markdown"


def test_to_markdown_returns_empty_array_for_empty_input() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("No request expected")

    client = make_client(handler)
    assert client.to_markdown([]) == []


def test_to_markdown_retries_on_429_then_succeeds() -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(429, text="rate limited")

        payload = {
            "result": [
                {
                    "name": "file.pdf",
                    "mimeType": "application/pdf",
                    "format": "markdown",
                    "tokens": 2,
                    "data": "# Retry Success",
                }
            ],
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    client = make_client(handler, max_retry_count=2)
    result = client.to_markdown([(b"x", "file.pdf")])[0]
    assert result.markdown == "# Retry Success"
    assert state["calls"] == 2


def test_to_markdown_retries_network_error_then_succeeds() -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            raise httpx.ReadTimeout("timeout", request=request)

        payload = {
            "result": [
                {
                    "name": "file.pdf",
                    "mimeType": "application/pdf",
                    "format": "markdown",
                    "tokens": 2,
                    "data": "# Retry Success",
                }
            ],
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    client = make_client(handler, max_retry_count=2)
    result = client.to_markdown([(b"x", "file.pdf")])[0]
    assert result.markdown == "# Retry Success"
    assert state["calls"] == 2


def test_to_markdown_respects_retry_limit() -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        return httpx.Response(503, text="service unavailable")

    client = make_client(handler, max_retry_count=1)

    with pytest.raises(HTTPError) as exc:
        client.to_markdown([(b"x", "file.pdf")])

    assert exc.value.status_code == 503
    assert state["calls"] == 2


def test_to_markdown_throws_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    client = make_client(handler)

    with pytest.raises(HTTPError) as exc:
        client.to_markdown([(b"x", "file.pdf")])

    assert exc.value.status_code == 403
    assert "forbidden" in exc.value.body


def test_to_markdown_throws_api_error_when_success_false() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"result": [], "success": False, "errors": [{"message": "invalid token"}], "messages": []},
        )

    client = make_client(handler)

    with pytest.raises(APIError) as exc:
        client.to_markdown([(b"x", "file.pdf")])

    assert exc.value.messages == ["invalid token"]


def test_to_markdown_supports_per_file_error_result_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "result": [
                {
                    "name": "broken.pdf",
                    "mimeType": "application/pdf",
                    "format": "error",
                    "error": "Failed to convert file",
                }
            ],
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    client = make_client(handler)
    results = client.to_markdown([(b"x", "file.pdf")])
    assert len(results) == 1
    assert results[0].format == "error"
    assert results[0].error == "Failed to convert file"
    assert results[0].markdown == ""
    assert results[0].tokens is None


def test_supported_formats_returns_endpoint_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url).endswith("/ai/tomarkdown/supported")
        payload = {
            "result": [
                {"extension": "pdf", "mimeType": "application/pdf"},
                {"extension": "jpeg", "mimeType": "image/jpeg"},
            ],
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    client = make_client(handler)
    result = client.supported_formats()
    assert [item.extension for item in result] == ["pdf", "jpeg"]
    assert [item.mime_type for item in result] == ["application/pdf", "image/jpeg"]


def test_markdown_from_url_returns_markdown_string() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url).endswith("/browser-rendering/markdown")
        body = request.read().decode("utf-8")
        assert "\"url\":\"https://example.com\"" in body
        payload = {
            "result": "# Hello from webpage",
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    client = make_client(handler)
    markdown = client.markdown_from_url("https://example.com")
    assert markdown == "# Hello from webpage"


def test_markdown_from_url_supports_advanced_options_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url).endswith("/browser-rendering/markdown")
        body = json.loads(request.read().decode("utf-8"))
        assert body == {
            "url": "https://example.com",
            "gotoOptions": {"waitUntil": "networkidle0"},
            "rejectRequestPattern": ["/^.*\\.(png)$/"],
        }
        payload = {
            "result": "# Hello from webpage",
            "success": True,
            "errors": [],
            "messages": [],
        }
        return httpx.Response(200, json=payload)

    client = make_client(handler)
    markdown = client.markdown_from_url(
        "https://example.com",
        gotoOptions={"waitUntil": "networkidle0"},
        rejectRequestPattern=["/^.*\\.(png)$/"],
    )
    assert markdown == "# Hello from webpage"
