"""HWP 5.x (legacy binary / OLE) reader.

See DESIGN.md for the format overview. This module extracts text today; table
grid reconstruction (v0.1) will build on the same record iteration.
"""

import struct
import zlib
from typing import Iterator

import olefile

from ._records import iter_records
from .exceptions import EncryptedDocumentError, InvalidHwpError

_SIGNATURE = b"HWP Document File"

# Record tags (HWPTAG_BEGIN = 0x10).
_HWPTAG_BEGIN = 0x10
HWPTAG_PARA_TEXT = _HWPTAG_BEGIN + 51  # 67

# FileHeader property flags.
_FLAG_COMPRESSED = 0x01
_FLAG_PASSWORD = 0x02
_FLAG_DISTRIBUTION = 0x04

# Control characters, by how many UTF-16 code units they occupy in PARA_TEXT.
_CTRL_8 = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23})
_CTRL_1 = frozenset({0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31})


def _section_no(name: str) -> int:
    digits = "".join(ch for ch in name if ch.isdigit())
    return int(digits) if digits else 0


def decode_para_text(payload: bytes) -> str:
    """Decode a ``HWPTAG_PARA_TEXT`` payload to a string.

    UTF-16LE code units interleaved with control characters; control chars are
    skipped (advancing 1 or 8 units), and paragraph/line breaks become newlines.
    """
    n = len(payload) // 2
    if n == 0:
        return ""
    units = struct.unpack_from("<%dH" % n, payload, 0)
    out = []
    i = 0
    while i < n:
        c = units[i]
        if c in _CTRL_1:
            if c == 10 or c == 13:
                out.append("\n")
            i += 1
        elif c in _CTRL_8:
            i += 8
        else:
            out.append(chr(c))
            i += 1
    return "".join(out)


def _iter_para_texts(path) -> Iterator[str]:
    if not olefile.isOleFile(path):
        raise InvalidHwpError("Not an OLE compound file (HWP 5.x)")
    ole = olefile.OleFileIO(path)
    try:
        if not ole.exists("FileHeader"):
            raise InvalidHwpError("Missing FileHeader stream")
        fh = ole.openstream("FileHeader").read()
        if fh[: len(_SIGNATURE)] != _SIGNATURE:
            raise InvalidHwpError("Missing 'HWP Document File' signature")
        (flags,) = struct.unpack_from("<I", fh, 36)
        compressed = bool(flags & _FLAG_COMPRESSED)
        if flags & _FLAG_PASSWORD:
            raise EncryptedDocumentError("Password-protected HWP document")
        if flags & _FLAG_DISTRIBUTION:
            raise EncryptedDocumentError("Distribution (copy-protected) HWP document")

        sections = sorted(
            (
                entry
                for entry in ole.listdir()
                if len(entry) == 2
                and entry[0] == "BodyText"
                and entry[1].lower().startswith("section")
            ),
            key=lambda entry: _section_no(entry[1]),
        )
        for entry in sections:
            raw = ole.openstream(entry).read()
            data = zlib.decompress(raw, -15) if compressed else raw
            for tag, _level, payload in iter_records(data):
                if tag == HWPTAG_PARA_TEXT:
                    yield decode_para_text(payload)
    finally:
        ole.close()


def extract_text_hwp5(path) -> str:
    """Extract plain text from an HWP 5.x document, in reading order.

    Table cell contents are included inline (in reading order); explicit table
    grid reconstruction lands in v0.1.
    """
    return "\n".join(t for t in _iter_para_texts(path) if t.strip())


def extract_markdown_hwp5(path) -> str:
    """v0: identical to :func:`extract_text_hwp5`.

    Table cell text is captured inline; GFM grid reconstruction is the v0.1
    milestone (see DESIGN.md).
    """
    return extract_text_hwp5(path)
