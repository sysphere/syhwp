"""syhwp — pure-Python reader for Korean HWP 5.x and HWPX documents.

Clean-room implementation from the public HANCOM HWP 5.0 / OWPML specifications.
No AGPL, no external services. See DESIGN.md for architecture and provenance.

    import syhwp
    doc = syhwp.open("report.hwp")      # -> Document (paragraphs, tables)
    text = syhwp.extract_text("report.hwp")
    md   = syhwp.extract_markdown("report.hwpx")
"""

import io

from .exceptions import (
    EncryptedDocumentError,
    InvalidHwpError,
    SyhwpError,
    UnsupportedFormatError,
)
from .models import Cell, Document, Equation, Image, Paragraph, Table

__version__ = "0.0.3"

__all__ = [
    "open",
    "detect_format",
    "extract_text",
    "extract_markdown",
    "Document",
    "Paragraph",
    "Table",
    "Cell",
    "Equation",
    "Image",
    "SyhwpError",
    "UnsupportedFormatError",
    "InvalidHwpError",
    "EncryptedDocumentError",
]

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_MAGIC = b"PK\x03\x04"


def detect_format(path) -> str:
    """Return ``"hwp5"`` or ``"hwpx"`` by inspecting the file's magic bytes."""
    with io.open(path, "rb") as f:  # io.open — module-level `open` is our API below
        head = f.read(8)
    if head.startswith(_OLE_MAGIC):
        return "hwp5"
    if head.startswith(_ZIP_MAGIC):
        return "hwpx"
    raise UnsupportedFormatError(f"Not an HWP or HWPX file: {path!r}")


def open(path) -> Document:  # noqa: A001 - intentional module-level API (cf. tarfile.open)
    """Parse an HWP 5.x or HWPX document into a :class:`Document`."""
    if detect_format(path) == "hwp5":
        from ._hwp5 import read_document_hwp5

        return read_document_hwp5(path)
    from ._hwpx import read_document_hwpx

    return read_document_hwpx(path)


def extract_text(path) -> str:
    """Extract plain text from an HWP 5.x or HWPX document."""
    return open(path).text


def extract_markdown(path) -> str:
    """Extract GFM markdown (tables as pipe tables) from HWP 5.x or HWPX."""
    return open(path).markdown
