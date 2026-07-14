"""HWPX (OWPML) reader — standard library only (zipfile + ElementTree).

Elements are matched by local name (namespace-agnostic) so the reader tolerates
OWPML namespace-version differences:
``p`` paragraph, ``t`` text run, ``tbl``/``tr``/``tc`` table/row/cell.
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Iterator, List

from ._markdown import normalize
from .models import Cell, Document, Paragraph, Table

_SECTION_RE = re.compile(r"(?:^|/)section\d+\.xml$", re.IGNORECASE)


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _cell_text(tc) -> str:
    """All text under a cell, linearized (nested tables flatten to text)."""
    return normalize("".join(e.text or "" for e in tc.iter() if _local(e.tag) == "t"))


def _direct(el, name: str) -> List:
    """Descendant elements with the given local name, not crossing into a
    nested ``tbl`` (so an outer table doesn't absorb an inner table's rows/cells)."""
    found: List = []

    def rec(node):
        for child in node:
            ln = _local(child.tag)
            if ln == "tbl":
                continue
            if ln == name:
                found.append(child)  # don't recurse into it
            else:
                rec(child)

    rec(el)
    return found


def _build_table(tbl) -> Table:
    rows = _direct(tbl, "tr")
    n_cols = 0
    cells: List[Cell] = []
    for r, tr in enumerate(rows):
        tcs = _direct(tr, "tc")
        n_cols = max(n_cols, len(tcs))
        for c, tc in enumerate(tcs):
            cells.append(Cell(row=r, col=c, text=_cell_text(tc)))
    return Table(n_rows=len(rows), n_cols=n_cols, cells=cells)


def _emit_blocks(root, blocks: List) -> None:
    para: List[str] = []

    def flush():
        if para:
            text = normalize("".join(para))
            if text:
                blocks.append(Paragraph(text))
            para.clear()

    def rec(node):
        for child in node:
            ln = _local(child.tag)
            if ln == "tbl":
                flush()
                blocks.append(_build_table(child))
            elif ln == "t":
                para.append("".join(child.itertext()))
            elif ln == "p":
                rec(child)
                flush()  # paragraph boundary
            else:
                rec(child)

    rec(root)
    flush()


def _iter_sections(path) -> Iterator["ET.Element"]:
    with zipfile.ZipFile(path) as z:
        for name in sorted(n for n in z.namelist() if _SECTION_RE.search(n)):
            try:
                yield ET.fromstring(z.read(name))
            except ET.ParseError:
                continue


def read_document_hwpx(path) -> Document:
    """Parse an HWPX document into a :class:`Document`."""
    blocks: List = []
    for root in _iter_sections(path):
        _emit_blocks(root, blocks)
    return Document(format="hwpx", blocks=blocks)
