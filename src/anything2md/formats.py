from __future__ import annotations

from enum import Enum
from pathlib import Path


class SupportedFormat(str, Enum):
    pdf = "pdf"
    jpeg = "jpeg"
    png = "png"
    webp = "webp"
    svg = "svg"
    html = "html"
    xml = "xml"
    csv = "csv"
    docx = "docx"
    xlsx = "xlsx"
    xlsm = "xlsm"
    xlsb = "xlsb"
    xls = "xls"
    et = "et"
    ods = "ods"
    odt = "odt"
    numbers = "numbers"

    @property
    def mime_type(self) -> str:
        return {
            SupportedFormat.pdf: "application/pdf",
            SupportedFormat.jpeg: "image/jpeg",
            SupportedFormat.png: "image/png",
            SupportedFormat.webp: "image/webp",
            SupportedFormat.svg: "image/svg+xml",
            SupportedFormat.html: "text/html",
            SupportedFormat.xml: "application/xml",
            SupportedFormat.csv: "text/csv",
            SupportedFormat.docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            SupportedFormat.xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            SupportedFormat.xlsm: "application/vnd.ms-excel.sheet.macroEnabled.12",
            SupportedFormat.xlsb: "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
            SupportedFormat.xls: "application/vnd.ms-excel",
            SupportedFormat.et: "application/vnd.ms-excel",
            SupportedFormat.ods: "application/vnd.oasis.opendocument.spreadsheet",
            SupportedFormat.odt: "application/vnd.oasis.opendocument.text",
            SupportedFormat.numbers: "application/vnd.apple.numbers",
        }[self]

    @property
    def file_extension(self) -> str:
        return self.value


_EXTENSION_ALIASES: dict[str, SupportedFormat] = {
    "jpg": SupportedFormat.jpeg,
    "htm": SupportedFormat.html,
}


_MIME_MAP: dict[str, SupportedFormat] = {
    "application/pdf": SupportedFormat.pdf,
    "image/jpeg": SupportedFormat.jpeg,
    "image/jpg": SupportedFormat.jpeg,
    "image/png": SupportedFormat.png,
    "image/webp": SupportedFormat.webp,
    "image/svg+xml": SupportedFormat.svg,
    "text/html": SupportedFormat.html,
    "application/xhtml+xml": SupportedFormat.html,
    "application/xml": SupportedFormat.xml,
    "text/xml": SupportedFormat.xml,
    "text/csv": SupportedFormat.csv,
    "application/csv": SupportedFormat.csv,
    "application/vnd.ms-excel": SupportedFormat.xls,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": SupportedFormat.docx,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": SupportedFormat.xlsx,
    "application/vnd.ms-excel.sheet.macroenabled.12": SupportedFormat.xlsm,
    "application/vnd.ms-excel.sheet.binary.macroenabled.12": SupportedFormat.xlsb,
    "application/x-iwork-numbers-sffnumbers": SupportedFormat.numbers,
    "application/vnd.apple.numbers": SupportedFormat.numbers,
    "application/vnd.oasis.opendocument.spreadsheet": SupportedFormat.ods,
    "application/vnd.oasis.opendocument.text": SupportedFormat.odt,
}


def from_filename(filename: str) -> SupportedFormat | None:
    ext = Path(filename).suffix.lower().lstrip(".")
    if not ext:
        return None
    if ext in _EXTENSION_ALIASES:
        return _EXTENSION_ALIASES[ext]
    try:
        return SupportedFormat(ext)
    except ValueError:
        return None


def from_mime_type(mime_type: str) -> SupportedFormat | None:
    normalized = mime_type.lower().split(";", 1)[0].strip()
    if not normalized:
        return None
    return _MIME_MAP.get(normalized)
