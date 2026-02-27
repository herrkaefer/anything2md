from __future__ import annotations

import os

import pytest

import anything2md


REQUIRED_ENV_VARS = (
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_API_TOKEN",
)


def _missing_required_env() -> list[str]:
    return [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]


def _integration_urls() -> list[str]:
    # Can be overridden by env for private/stable fixtures.
    return [
        os.getenv(
            "ANYTHING2MD_TEST_PDF_URL",
            "https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/somatosensory.pdf",
        ),
        os.getenv(
            "ANYTHING2MD_TEST_IMAGE_URL",
            "https://pub-979cb28270cc461d94bc8a169d8f389d.r2.dev/cat.jpeg",
        ),
        os.getenv("ANYTHING2MD_TEST_WEB_URL", "https://example.com"),
    ]


@pytest.mark.integration
def test_real_cloudflare_transform_validates_markdown_and_error_fields() -> None:
    missing = _missing_required_env()
    if missing:
        pytest.skip("Missing env vars for integration test: " + ", ".join(missing))

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    api_token = os.environ["CLOUDFLARE_API_TOKEN"]

    with anything2md(account_id=account_id, api_token=api_token) as converter:
        for url in _integration_urls():
            result = converter.transform(url)

            # Pass criteria: no per-file conversion error and non-empty markdown output.
            assert result.error is None or result.error == ""
            assert result.markdown.strip() != ""
            assert result.format == "markdown"
