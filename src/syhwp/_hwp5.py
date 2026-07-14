"""HWP 5.x (legacy binary / OLE) reader.

See DESIGN.md for the format overview.

- ``extract_text_hwp5``     — plain text, streamed from the record list.
- ``extract_markdown_hwp5`` — builds a record tree (via each record's ``level``)
  and reconstructs tables into GFM pipe tables.
"""

import struct
import zlib
from typing import Iterator, List, Optional, Tuple

import olefile

from ._markdown import escape_cell, grid_to_markdown, normalize
from ._records import iter_records
from .exceptions import EncryptedDocumentError, InvalidHwpError

_SIGNATURE = b"HWP Document File"

# Record tags (HWPTAG_BEGIN = 0x10).
_HWPTAG_BEGIN = 0x10
HWPTAG_PARA_HEADER = _HWPTAG_BEGIN + 50   # 66
HWPTAG_PARA_TEXT = _HWPTAG_BEGIN + 51     # 67
HWPTAG_CTRL_HEADER = _HWPTAG_BEGIN + 55   # 71
HWPTAG_LIST_HEADER = _HWPTAG_BEGIN + 56   # 72
HWPTAG_TABLE = _HWPTAG_BEGIN + 61         # 77

# Control id for a table, as stored in CTRL_HEADER (little-endian "tbl ").
_CTRL_ID_TABLE = b"tbl "[::-1]

# FileHeader property flags.
_FLAG_COMPRESSED = 0x01
_FLAG_PASSWORD = 0x02
_FLAG_DISTRIBUTION = 0x04

# Control characters in PARA_TEXT, by how many UTF-16 code units they occupy.
_CTRL_8 = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23})
_CTRL_1 = frozenset({0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31})


# --------------------------------------------------------------------------- #
# Low-level payload parsers (pure; unit-tested)
# --------------------------------------------------------------------------- #

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


def table_dimensions(payload: bytes) -> Tuple[int, int]:
    """``HWPTAG_TABLE`` → ``(n_rows, n_cols)`` (uint16 at offsets 4 and 6)."""
    n_rows, n_cols = struct.unpack_from("<HH", payload, 4)
    return n_rows, n_cols


def cell_address(payload: bytes) -> Tuple[int, int, int, int, int]:
    """``HWPTAG_LIST_HEADER`` (table cell) →
    ``(n_paragraphs, col, row, col_span, row_span)``.

    Layout: nParagraphs (uint16 @0), list property (6 bytes), then the cell
    address as four uint16 — col @8, row @10, colSpan @12, rowSpan @14.
    """
    n_para = struct.unpack_from("<H", payload, 0)[0]
    col, row, col_span, row_span = struct.unpack_from("<HHHH", payload, 8)
    return n_para, col, row, col_span, row_span


def is_table_control(payload: bytes) -> bool:
    """True if a ``HWPTAG_CTRL_HEADER`` payload is a table control."""
    return payload[:4] == _CTRL_ID_TABLE


# --------------------------------------------------------------------------- #
# Section access
# --------------------------------------------------------------------------- #

def _section_no(name: str) -> int:
    digits = "".join(ch for ch in name if ch.isdigit())
    return int(digits) if digits else 0


def _iter_sections(path) -> Iterator[List[Tuple[int, int, bytes]]]:
    """Yield the record list of each ``BodyText/Section{N}`` in order.

    Raises :class:`EncryptedDocumentError` for password/distribution documents
    and :class:`InvalidHwpError` for non-HWP or structurally broken files.
    """
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
            yield list(iter_records(data))
    finally:
        ole.close()


# --------------------------------------------------------------------------- #
# Record tree (built from each record's `level`)
# --------------------------------------------------------------------------- #

class _Node:
    __slots__ = ("tag", "payload", "children")

    def __init__(self, tag: int, payload: bytes):
        self.tag = tag
        self.payload = payload
        self.children: List["_Node"] = []


def _build_tree(records: List[Tuple[int, int, bytes]]) -> _Node:
    """Turn a flat record list into a tree using the per-record ``level``.

    A record at level ``L`` is a child of the most recent record at level
    ``L-1``. Malformed level jumps are clamped so the walk never breaks.
    """
    root = _Node(-1, b"")
    stack: List[_Node] = [root]  # stack[L] == current parent for level-L nodes
    for tag, level, payload in records:
        if level + 1 > len(stack):
            level = len(stack) - 1  # clamp an impossible jump
        node = _Node(tag, payload)
        stack[level].children.append(node)
        del stack[level + 1:]
        stack.append(node)
    return root


def _cell_text(paragraphs: List[_Node]) -> str:
    """Linearized text of a cell — every PARA_TEXT in the given paragraph
    subtrees (so nested tables flatten into the cell text)."""
    parts: List[str] = []

    def rec(node: _Node) -> None:
        if node.tag == HWPTAG_PARA_TEXT:
            parts.append(decode_para_text(node.payload))
        for child in node.children:
            rec(child)

    for para in paragraphs:
        rec(para)
    return normalize(" ".join(parts))


def _render_table(ctrl: _Node) -> str:
    """Render a table CTRL_HEADER node as a GFM pipe table."""
    table_rec = next((c for c in ctrl.children if c.tag == HWPTAG_TABLE), None)
    if table_rec is None or len(table_rec.payload) < 8:
        return ""
    n_rows, n_cols = table_dimensions(table_rec.payload)
    if n_rows <= 0 or n_cols <= 0:
        return ""
    grid = [["" for _ in range(n_cols)] for _ in range(n_rows)]

    children = ctrl.children
    i = 0
    while i < len(children):
        node = children[i]
        if node.tag == HWPTAG_LIST_HEADER and len(node.payload) >= 16:
            n_para, col, row, _cs, _rs = cell_address(node.payload)
            i += 1
            paras: List[_Node] = []
            while i < len(children) and len(paras) < n_para:
                if children[i].tag == HWPTAG_PARA_HEADER:
                    paras.append(children[i])
                i += 1
            if 0 <= row < n_rows and 0 <= col < n_cols:
                grid[row][col] = escape_cell(_cell_text(paras))
        else:
            i += 1
    return grid_to_markdown(grid)


def _paragraph_blocks(para: _Node) -> List[str]:
    """A top-level paragraph → its text, then any tables anchored in it."""
    blocks: List[str] = []
    text = normalize(
        " ".join(
            decode_para_text(c.payload)
            for c in para.children
            if c.tag == HWPTAG_PARA_TEXT
        )
    )
    if text:
        blocks.append(text)
    for c in para.children:
        if c.tag == HWPTAG_CTRL_HEADER and is_table_control(c.payload):
            md = _render_table(c)
            if md:
                blocks.append(md)
    return blocks


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #

def extract_text_hwp5(path) -> str:
    """Extract plain text from an HWP 5.x document, in reading order.

    Table cell contents are included inline (in reading order).
    """
    parts: List[str] = []
    for records in _iter_sections(path):
        for tag, _level, payload in records:
            if tag == HWPTAG_PARA_TEXT:
                text = decode_para_text(payload)
                if text.strip():
                    parts.append(text)
    return "\n".join(parts)


def extract_markdown_hwp5(path) -> str:
    """Extract GFM markdown from an HWP 5.x document, with tables reconstructed
    into pipe tables."""
    blocks: List[str] = []
    for records in _iter_sections(path):
        root = _build_tree(records)
        for node in root.children:
            if node.tag == HWPTAG_PARA_HEADER:
                blocks.extend(_paragraph_blocks(node))
    return "\n\n".join(blocks)
