from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CloudflareCredentials:
    """Cloudflare credentials required for Workers AI requests."""

    account_id: str
    api_token: str


@dataclass(frozen=True)
class ConvertOptions:
    """Runtime options for conversion requests."""

    timeout: float = 60.0
    max_retry_count: int = 2
    retry_base_delay: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_retry_count", max(0, self.max_retry_count))


BrowserWaitUntil = Literal["networkidle0", "networkidle2"]
VALID_BROWSER_WAIT_UNTIL = ("networkidle0", "networkidle2")
