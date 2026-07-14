"""HWPX (OWPML) reader — standard library only (zipfile + ElementTree).

Elements are matched by local name (namespace-agnostic) so the reader tolerates
OWPML namespace-version differences: ``p`` paragraph, ``t`` text run,
``tbl``/``tr``/``tc`` table/row/cell, ``equation`` (with ``script``), ``pic``.
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from typing import List

from ._markdown import normalize
from .exceptions import InvalidHwpError
from .models import Cell, Document, Equation, Image, Paragraph, Table

_SECTION_RE = re.compile(r"(?:^|/)section\d+\.xml$", re.IGNORECASE)


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _cell_text(tc) -> str:
    """All text under a cell, linearized — text runs plus inline object markers
    (nested tables flatten to text)."""
    parts: List[str] = []
    for e in tc.iter():
        ln = _local(e.tag)
        if ln == "t":
            parts.append(e.text or "")
        elif ln == "script":
            parts.append(" [수식: %s] " % normalize(e.text or ""))
        elif ln == "pic":
            parts.append(" [그림] ")
    return normalize("".join(parts))


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


def _equation_script(eq) -> str:
    return normalize(
        "".join(e.text or "" for e in eq.iter() if _local(e.tag) == "script")
    )


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
            elif ln == "equation":
                flush()
                blocks.append(Equation(_equation_script(child)))
            elif ln == "pic":
                flush()
                blocks.append(Image())
            elif ln == "t":
                para.append("".join(child.itertext()))
            elif ln == "p":
                rec(child)
                flush()  # paragraph boundary
            else:
                rec(child)

    rec(root)
    flush()


def _read_version(z: zipfile.ZipFile) -> str:
    """HWPX version from version.xml (major.minor.micro.buildNumber)."""
    try:
        root = ET.fromstring(z.read("version.xml"))
    except (KeyError, ET.ParseError):
        return ""
    a = root.attrib
    parts = [a.get(k) for k in ("major", "minor", "micro", "buildNumber")]
    return ".".join(p for p in parts if p is not None) if any(parts) else ""


def read_document_hwpx(path) -> Document:
    """Parse an HWPX document into a :class:`Document`."""
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        raise InvalidHwpError(f"Corrupt HWPX (bad zip): {e}") from e
    blocks: List = []
    with z:
        version = _read_version(z)
        for name in sorted(n for n in z.namelist() if _SECTION_RE.search(n)):
            try:
                root = ET.fromstring(z.read(name))
            except ET.ParseError:
                continue
            _emit_blocks(root, blocks)
    return Document(format="hwpx", blocks=blocks, version=version)
