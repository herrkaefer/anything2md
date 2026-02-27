from __future__ import annotations

import httpx

import anything2md
from anything2md import MarkdownConverter
from anything2md.client import CloudflareClient
from anything2md.config import CloudflareCredentials


def test_module_callable_returns_converter() -> None:
    converter = anything2md(account_id="acc", api_token="token")
    assert isinstance(converter, MarkdownConverter)
    converter.close()


def test_factory_function_returns_converter() -> None:
    converter = anything2md.anything2md(account_id="acc", api_token="token")
    assert isinstance(converter, MarkdownConverter)
    converter.close()


def test_callable_converter_can_convert_bytes() -> None:
    def upload_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "name": "x.pdf",
                        "mimeType": "application/pdf",
                        "format": "markdown",
                        "tokens": 1,
                        "data": "# ok",
                    }
                ],
                "success": True,
                "errors": [],
                "messages": [],
            },
        )

    upload_session = httpx.Client(transport=httpx.MockTransport(upload_handler), timeout=10.0)
    download_session = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500)), timeout=10.0)
    converter = anything2md(
        account_id="acc",
        api_token="token",
        client=CloudflareClient(
            credentials=CloudflareCredentials(account_id="acc", api_token="token"),
            session=upload_session,
        ),
        download_session=download_session,
    )

    result = converter.transform(b"%PDF", filename="x.pdf")
    assert result.markdown == "# ok"
    converter.close()
