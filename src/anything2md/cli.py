from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlparse

from .config import CloudflareCredentials
from .converter import MarkdownConverter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="anything2md",
        description="Convert a URL or local file into Markdown using Cloudflare Workers AI.",
    )
    parser.add_argument("input", help="Input URL (http/https) or local file path.")
    parser.add_argument("--account-id", help="Cloudflare account ID. Falls back to CLOUDFLARE_ACCOUNT_ID.")
    parser.add_argument("--api-token", help="Cloudflare API token. Falls back to CLOUDFLARE_API_TOKEN.")
    parser.add_argument("-o", "--output", help="Output markdown file path. Defaults to stdout.")
    return parser.parse_args()


def _resolve_credential(primary: str | None, env_name: str) -> str:
    value = (primary or os.getenv(env_name, "")).strip()
    if not value:
        raise SystemExit(f"Missing credential: use flag or set {env_name}.")
    return value


def _is_remote_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main() -> None:
    args = parse_args()
    account_id = _resolve_credential(args.account_id, "CLOUDFLARE_ACCOUNT_ID")
    api_token = _resolve_credential(args.api_token, "CLOUDFLARE_API_TOKEN")

    converter = MarkdownConverter(credentials=CloudflareCredentials(account_id, api_token))
    try:
        if _is_remote_url(args.input):
            result = converter.convert_url(args.input)
        else:
            result = converter.convert_file(Path(args.input).expanduser())
    finally:
        converter.close()

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.write_text(result.markdown, encoding="utf-8")
        print(str(output_path))
        return

    print(result.markdown, end="" if result.markdown.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
