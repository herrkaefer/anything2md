from __future__ import annotations

from anything2md.formats import SupportedFormat, from_filename, from_mime_type


def test_from_filename() -> None:
    assert from_filename("report.pdf") == SupportedFormat.pdf
    assert from_filename("photo.jpg") == SupportedFormat.jpeg
    assert from_filename("sheet.xlsx") == SupportedFormat.xlsx


def test_from_mime_type() -> None:
    assert from_mime_type("application/pdf") == SupportedFormat.pdf
    assert from_mime_type("image/jpeg; charset=utf-8") == SupportedFormat.jpeg
    assert from_mime_type("text/xml") == SupportedFormat.xml


def test_unsupported_values_return_none() -> None:
    assert from_filename("notes.txt") is None
    assert from_mime_type("text/plain") is None


def test_each_case_has_file_extension_and_mime() -> None:
    for fmt in SupportedFormat:
        assert fmt.file_extension
        assert fmt.mime_type
