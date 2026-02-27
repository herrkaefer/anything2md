from __future__ import annotations

from anything2md.cli import _is_remote_url, parse_args


def test_is_remote_url() -> None:
    assert _is_remote_url("https://example.com/a.pdf")
    assert _is_remote_url("http://example.com/a.pdf")
    assert not _is_remote_url("/tmp/a.pdf")


def test_parse_args_accepts_browser_advanced_options(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "anything2md",
            "https://example.com",
            "--wait-until",
            "networkidle2",
            "--reject-request-pattern",
            "/^.*\\.(css)$/",
            "--reject-request-pattern",
            "/analytics/",
        ],
    )
    args = parse_args()
    assert args.wait_until == "networkidle2"
    assert args.reject_request_pattern == ["/^.*\\.(css)$/", "/analytics/"]
