"""HWP 5.x (legacy binary / OLE) reader.

See DESIGN.md for the format overview.

- ``extract_text_hwp5``     — plain text, streamed from the record list.
- ``extract_markdown_hwp5`` — builds a record tree (via each record's ``level``)
  and reconstructs tables into GFM pipe tables.
"""

import struct
import zlib
from typing import List, Optional, Tuple

import olefile

from ._markdown import normalize
from ._records import iter_records
from .exceptions import EncryptedDocumentError, InvalidHwpError
from .models import Cell, Document, Equation, Image, Paragraph, Table

_SIGNATURE = b"HWP Document File"

# Guard against decompression bombs — cap a single section's inflated size.
_MAX_SECTION_BYTES = 256 * 1024 * 1024

# Record tags (HWPTAG_BEGIN = 0x10).
_HWPTAG_BEGIN = 0x10
HWPTAG_PARA_HEADER = _HWPTAG_BEGIN + 50   # 66
HWPTAG_PARA_TEXT = _HWPTAG_BEGIN + 51     # 67
HWPTAG_CTRL_HEADER = _HWPTAG_BEGIN + 55   # 71
HWPTAG_LIST_HEADER = _HWPTAG_BEGIN + 56   # 72
HWPTAG_TABLE = _HWPTAG_BEGIN + 61         # 77
HWPTAG_EQEDIT = _HWPTAG_BEGIN + 72        # 88

# Control ids, as stored in CTRL_HEADER (little-endian, i.e. reversed 4-char id).
_CTRL_ID_TABLE = b"tbl "[::-1]
_CTRL_ID_EQUATION = b"eqed"[::-1]
_CTRL_ID_GSO = b"gso "[::-1]  # picture / drawing object shell

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


def _inflate(raw: bytes) -> bytes:
    """Raw-DEFLATE inflate with a size cap. Corrupt/oversized streams raise
    :class:`InvalidHwpError` rather than propagating zlib errors or OOMing."""
    try:
        d = zlib.decompressobj(-15)
        out = d.decompress(raw, _MAX_SECTION_BYTES)
        if d.unconsumed_tail:
            raise InvalidHwpError("Section too large (possible decompression bomb)")
        return out + d.flush()
    except zlib.error as e:
        raise InvalidHwpError(f"Corrupt compressed section: {e}") from e


def _version_str(fh: bytes) -> str:
    (ver,) = struct.unpack_from("<I", fh, 32)
    return "%d.%d.%d.%d" % (
        (ver >> 24) & 0xFF,
        (ver >> 16) & 0xFF,
        (ver >> 8) & 0xFF,
        ver & 0xFF,
    )


def _read_hwp5(path) -> Tuple[str, List[List[Tuple[int, int, bytes]]]]:
    """Return ``(version, [section_records, ...])`` for an HWP 5.x file.

    Raises :class:`EncryptedDocumentError` for password/distribution documents
    and :class:`InvalidHwpError` for non-HWP or structurally broken files.
    """
    if not olefile.isOleFile(path):
        raise InvalidHwpError("Not an OLE compound file (HWP 5.x)")
    try:
        ole = olefile.OleFileIO(path)
    except Exception as e:  # olefile raises various errors on corrupt containers
        raise InvalidHwpError(f"Corrupt OLE container: {e}") from e
    try:
        if not ole.exists("FileHeader"):
            raise InvalidHwpError("Missing FileHeader stream")
        fh = ole.openstream("FileHeader").read()
        if fh[: len(_SIGNATURE)] != _SIGNATURE:
            raise InvalidHwpError("Missing 'HWP Document File' signature")
        version = _version_str(fh)
        (flags,) = struct.unpack_from("<I", fh, 36)
        compressed = bool(flags & _FLAG_COMPRESSED)
        if flags & _FLAG_PASSWORD:
            raise EncryptedDocumentError("Password-protected HWP document")
        if flags & _FLAG_DISTRIBUTION:
            raise EncryptedDocumentError("Distribution (copy-protected) HWP document")

        entries = sorted(
            (
                entry
                for entry in ole.listdir()
                if len(entry) == 2
                and entry[0] == "BodyText"
                and entry[1].lower().startswith("section")
            ),
            key=lambda entry: _section_no(entry[1]),
        )
        sections = []
        for entry in entries:
            raw = ole.openstream(entry).read()
            data = _inflate(raw) if compressed else raw
            sections.append(list(iter_records(data)))
        return version, sections
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
    """Linearized text of a cell — PARA_TEXT plus inline objects (equations,
    images) in the given paragraph subtrees. Nested tables flatten into text."""
    parts: List[str] = []

    def rec(node: _Node) -> None:
        if node.tag == HWPTAG_PARA_TEXT:
            parts.append(decode_para_text(node.payload))
        elif node.tag == HWPTAG_CTRL_HEADER and len(node.payload) >= 4:
            ctrl_id = node.payload[:4]
            if ctrl_id == _CTRL_ID_EQUATION:
                script = _equation_script(node)
                parts.append("[수식: %s]" % script if script else "[수식]")
            elif ctrl_id == _CTRL_ID_GSO:
                parts.append("[그림]")
        for child in node.children:
            rec(child)

    for para in paragraphs:
        rec(para)
    return normalize(" ".join(parts))


def _build_table(ctrl: _Node) -> Optional[Table]:
    """Build a :class:`Table` from a table CTRL_HEADER node."""
    table_rec = next((c for c in ctrl.children if c.tag == HWPTAG_TABLE), None)
    if table_rec is None or len(table_rec.payload) < 8:
        return None
    n_rows, n_cols = table_dimensions(table_rec.payload)
    if n_rows <= 0 or n_cols <= 0:
        return None

    cells: List[Cell] = []
    children = ctrl.children
    i = 0
    while i < len(children):
        node = children[i]
        if node.tag == HWPTAG_LIST_HEADER and len(node.payload) >= 16:
            n_para, col, row, col_span, row_span = cell_address(node.payload)
            i += 1
            paras: List[_Node] = []
            while i < len(children) and len(paras) < n_para:
                if children[i].tag == HWPTAG_PARA_HEADER:
                    paras.append(children[i])
                i += 1
            cells.append(
                Cell(
                    row=row,
                    col=col,
                    text=_cell_text(paras),
                    row_span=max(1, row_span),
                    col_span=max(1, col_span),
                )
            )
        else:
            i += 1
    return Table(n_rows=n_rows, n_cols=n_cols, cells=cells)


def _equation_script(ctrl: _Node) -> str:
    """Extract an equation's script from a table/eqed CTRL_HEADER's EQEDIT child.

    EQEDIT payload: property (uint32), then a uint16-length-prefixed UTF-16LE
    string (HANCOM equation syntax).
    """
    eq = next((c for c in ctrl.children if c.tag == HWPTAG_EQEDIT), None)
    if eq is None or len(eq.payload) < 6:
        return ""
    (n,) = struct.unpack_from("<H", eq.payload, 4)
    return eq.payload[6:6 + n * 2].decode("utf-16-le", "replace").strip()


def _emit_paragraph(para: _Node, blocks: List) -> None:
    """Append a top-level paragraph's text, then any objects anchored in it
    (tables, equations, images) in child order."""
    text = normalize(
        " ".join(
            decode_para_text(c.payload)
            for c in para.children
            if c.tag == HWPTAG_PARA_TEXT
        )
    )
    if text:
        blocks.append(Paragraph(text))
    for c in para.children:
        if c.tag != HWPTAG_CTRL_HEADER or len(c.payload) < 4:
            continue
        ctrl_id = c.payload[:4]
        if ctrl_id == _CTRL_ID_TABLE:
            table = _build_table(c)
            if table is not None:
                blocks.append(table)
        elif ctrl_id == _CTRL_ID_EQUATION:
            blocks.append(Equation(_equation_script(c)))
        elif ctrl_id == _CTRL_ID_GSO:
            blocks.append(Image())


def read_document_hwp5(path) -> Document:
    """Parse an HWP 5.x document into a :class:`Document`."""
    version, sections = _read_hwp5(path)
    blocks: List = []
    for records in sections:
        root = _build_tree(records)
        for node in root.children:
            if node.tag == HWPTAG_PARA_HEADER:
                _emit_paragraph(node, blocks)
    return Document(format="hwp5", blocks=blocks, version=version)
