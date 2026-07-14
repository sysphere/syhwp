"""syhwp — pure-Python reader for Korean HWP 5.x and HWPX documents.

Clean-room implementation from the public HANCOM HWP 5.0 / OWPML specifications.
No AGPL, no external services. See DESIGN.md for architecture and provenance.

    import syhwp
    text = syhwp.extract_text("report.hwp")
    md   = syhwp.extract_markdown("report.hwpx")
"""

from .exceptions import (
    EncryptedDocumentError,
    InvalidHwpError,
    SyhwpError,
    UnsupportedFormatError,
)

__version__ = "0.0.1"

__all__ = [
    "detect_format",
    "extract_text",
    "extract_markdown",
    "SyhwpError",
    "UnsupportedFormatError",
    "InvalidHwpError",
    "EncryptedDocumentError",
]

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_MAGIC = b"PK\x03\x04"


def detect_format(path) -> str:
    """Return ``"hwp5"`` or ``"hwpx"`` by inspecting the file's magic bytes."""
    with open(path, "rb") as f:
        head = f.read(8)
    if head.startswith(_OLE_MAGIC):
        return "hwp5"
    if head.startswith(_ZIP_MAGIC):
        return "hwpx"
    raise UnsupportedFormatError(f"Not an HWP or HWPX file: {path!r}")


def extract_text(path) -> str:
    """Extract plain text from an HWP 5.x or HWPX document."""
    if detect_format(path) == "hwp5":
        from ._hwp5 import extract_text_hwp5

        return extract_text_hwp5(path)
    from ._hwpx import extract_text_hwpx

    return extract_text_hwpx(path)


def extract_markdown(path) -> str:
    """Extract GFM markdown (tables as pipe tables) from HWP 5.x or HWPX."""
    if detect_format(path) == "hwp5":
        from ._hwp5 import extract_markdown_hwp5

        return extract_markdown_hwp5(path)
    from ._hwpx import extract_markdown_hwpx

    return extract_markdown_hwpx(path)
