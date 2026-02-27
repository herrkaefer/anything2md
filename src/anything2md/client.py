from __future__ import annotations

import time
from typing import Sequence

import httpx

from .config import CloudflareCredentials, ConvertOptions
from .errors import APIError, HTTPError, InvalidResponseError, NetworkError, UnsupportedFormatError
from .formats import from_filename
from .models import ConversionResult


_RETRYABLE_NETWORK_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)


class CloudflareClient:
    def __init__(
        self,
        credentials: CloudflareCredentials,
        options: ConvertOptions = ConvertOptions(),
        session: httpx.Client | None = None,
    ) -> None:
        self.credentials = credentials
        self.options = options
        self._session = session or httpx.Client(timeout=options.timeout)

    def to_markdown(self, files: Sequence[tuple[bytes, str]]) -> list[ConversionResult]:
        if not files:
            return []

        multipart: list[tuple[str, tuple[str, bytes, str]]] = []
        for data, filename in files:
            fmt = from_filename(filename)
            if fmt is None:
                raise UnsupportedFormatError(filename)
            multipart.append(("files", (filename, data, fmt.mime_type)))

        endpoint = (
            f"https://api.cloudflare.com/client/v4/accounts/{self.credentials.account_id}/"
            "ai/tomarkdown"
        )
        headers = {"Authorization": f"Bearer {self.credentials.api_token}"}

        attempt = 0
        while True:
            try:
                response = self._session.post(
                    endpoint,
                    headers=headers,
                    files=multipart,
                    timeout=self.options.timeout,
                )
            except _RETRYABLE_NETWORK_EXCEPTIONS as exc:
                if self._should_retry_network(attempt):
                    self._sleep_before_retry(attempt)
                    attempt += 1
                    continue
                raise NetworkError(exc) from exc
            except httpx.HTTPError as exc:
                raise NetworkError(exc) from exc

            if not 200 <= response.status_code < 300:
                if self._should_retry_status(response.status_code, attempt):
                    self._sleep_before_retry(attempt)
                    attempt += 1
                    continue
                raise HTTPError(response.status_code, response.text)

            try:
                payload = response.json()
            except ValueError as exc:
                raise InvalidResponseError() from exc

            success = bool(payload.get("success", False))
            if not success:
                messages = self._extract_messages(payload)
                raise APIError(messages)

            result_payload = payload.get("result", [])
            if not isinstance(result_payload, list):
                raise InvalidResponseError()

            try:
                return [ConversionResult.from_api_item(item) for item in result_payload]
            except (TypeError, ValueError, KeyError) as exc:
                raise InvalidResponseError() from exc

    def close(self) -> None:
        self._session.close()

    def _should_retry_status(self, status_code: int, attempt: int) -> bool:
        return attempt < self.options.max_retry_count and (
            status_code == 429 or status_code >= 500
        )

    def _should_retry_network(self, attempt: int) -> bool:
        return attempt < self.options.max_retry_count

    def _sleep_before_retry(self, attempt: int) -> None:
        base = max(0.0, self.options.retry_base_delay)
        if base <= 0:
            return
        time.sleep(base * (2**attempt))

    @staticmethod
    def _extract_messages(payload: dict) -> list[str]:
        values: list[str] = []
        for key in ("errors", "messages"):
            entries = payload.get(key, [])
            if not isinstance(entries, list):
                continue
            for item in entries:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, dict):
                    message = item.get("message")
                    if isinstance(message, str):
                        values.append(message)
        return values
