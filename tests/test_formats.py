from __future__ import annotations

import pytest

from anything2md.formats import SupportedFormat, from_filename, from_mime_type


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("report.pdf", SupportedFormat.pdf),
        ("photo.jpg", SupportedFormat.jpeg),
        ("photo.jpeg", SupportedFormat.jpeg),
        ("image.png", SupportedFormat.png),
        ("image.webp", SupportedFormat.webp),
        ("vector.svg", SupportedFormat.svg),
        ("page.html", SupportedFormat.html),
        ("page.htm", SupportedFormat.html),
        ("data.xml", SupportedFormat.xml),
        ("data.csv", SupportedFormat.csv),
        ("doc.docx", SupportedFormat.docx),
        ("sheet.xlsx", SupportedFormat.xlsx),
        ("sheet.xlsm", SupportedFormat.xlsm),
        ("sheet.xlsb", SupportedFormat.xlsb),
        ("sheet.xls", SupportedFormat.xls),
        ("sheet.et", SupportedFormat.et),
        ("sheet.ods", SupportedFormat.ods),
        ("doc.odt", SupportedFormat.odt),
        ("sheet.numbers", SupportedFormat.numbers),
    ],
)
def test_from_filename_supported_formats(filename: str, expected: SupportedFormat) -> None:
    assert from_filename(filename) == expected


@pytest.mark.parametrize(
    ("mime_type", "expected"),
    [
        ("application/pdf", SupportedFormat.pdf),
        ("image/jpeg; charset=utf-8", SupportedFormat.jpeg),
        ("text/xml", SupportedFormat.xml),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", SupportedFormat.docx),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", SupportedFormat.xlsx),
        ("application/vnd.ms-excel.sheet.macroenabled.12", SupportedFormat.xlsm),
        ("application/vnd.ms-excel.sheet.binary.macroenabled.12", SupportedFormat.xlsb),
        ("application/vnd.oasis.opendocument.spreadsheet", SupportedFormat.ods),
        ("application/vnd.oasis.opendocument.text", SupportedFormat.odt),
        ("application/vnd.apple.numbers", SupportedFormat.numbers),
    ],
)
def test_from_mime_type_supported_formats(mime_type: str, expected: SupportedFormat) -> None:
    assert from_mime_type(mime_type) == expected


@pytest.mark.parametrize("filename", ["notes.txt", "archive.zip", "script.py", "audio.mp3"])
def test_unsupported_filename_returns_none(filename: str) -> None:
    assert from_filename(filename) is None


@pytest.mark.parametrize("mime_type", ["text/plain", "application/zip", "application/json", "audio/mpeg"])
def test_unsupported_mime_type_returns_none(mime_type: str) -> None:
    assert from_mime_type(mime_type) is None


def test_each_case_has_file_extension_and_mime() -> None:
    for fmt in SupportedFormat:
        assert fmt.file_extension
        assert fmt.mime_type
