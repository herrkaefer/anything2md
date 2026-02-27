from __future__ import annotations

from anything2md.cli import _is_remote_url


def test_is_remote_url() -> None:
    assert _is_remote_url("https://example.com/a.pdf")
    assert _is_remote_url("http://example.com/a.pdf")
    assert not _is_remote_url("/tmp/a.pdf")
