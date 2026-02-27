from __future__ import annotations


class Anything2MDError(Exception):
    """Base exception for anything2md."""


class UnsupportedFormatError(Anything2MDError):
    def __init__(self, value: str):
        super().__init__(f"Unsupported format: {value}")
        self.value = value


class NetworkError(Anything2MDError):
    def __init__(self, underlying: Exception):
        super().__init__(f"Network error: {underlying}")
        self.underlying = underlying


class FileReadError(Anything2MDError):
    def __init__(self, underlying: Exception):
        super().__init__(f"File read error: {underlying}")
        self.underlying = underlying


class HTTPError(Anything2MDError):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"HTTP error {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class APIError(Anything2MDError):
    def __init__(self, messages: list[str]):
        if messages:
            message = f"Workers AI API error: {'; '.join(messages)}"
        else:
            message = "Workers AI API returned an error."
        super().__init__(message)
        self.messages = messages


class InvalidResponseError(Anything2MDError):
    def __init__(self):
        super().__init__("Invalid response from Workers AI API.")
