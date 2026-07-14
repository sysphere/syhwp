"""HWPX (OWPML) reader — standard library only (zipfile + ElementTree).

Elements are matched by local name (namespace-agnostic) so the reader tolerates
OWPML namespace-version differences:
``p`` paragraph, ``t`` text run, ``tbl``/``tr``/``tc`` table/row/cell.
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Iterator, List

from ._markdown import escape_cell, grid_to_markdown, normalize

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


def _render_table(tbl) -> str:
    grid = [
        [escape_cell(_cell_text(tc)) for tc in _direct(tr, "tc")]
        for tr in _direct(tbl, "tr")
    ]
    return grid_to_markdown(grid)


def _blocks(root, tables_as_markdown: bool) -> List[str]:
    blocks: List[str] = []
    para: List[str] = []

    def flush():
        if para:
            text = normalize("".join(para))
            if text:
                blocks.append(text)
            para.clear()

    def rec(node):
        for child in node:
            ln = _local(child.tag)
            if ln == "tbl":
                flush()
                if tables_as_markdown:
                    md = _render_table(child)
                    if md:
                        blocks.append(md)
                else:
                    for tr in _direct(child, "tr"):
                        for tc in _direct(tr, "tc"):
                            txt = _cell_text(tc)
                            if txt:
                                blocks.append(txt)
            elif ln == "t":
                para.append("".join(child.itertext()))
            elif ln == "p":
                rec(child)
                flush()  # paragraph boundary
            else:
                rec(child)

    rec(root)
    flush()
    return blocks


def _iter_sections(path) -> Iterator["ET.Element"]:
    with zipfile.ZipFile(path) as z:
        for name in sorted(n for n in z.namelist() if _SECTION_RE.search(n)):
            try:
                yield ET.fromstring(z.read(name))
            except ET.ParseError:
                continue


def extract_markdown_hwpx(path) -> str:
    out: List[str] = []
    for root in _iter_sections(path):
        out.extend(_blocks(root, tables_as_markdown=True))
    return "\n\n".join(out)


def extract_text_hwpx(path) -> str:
    out: List[str] = []
    for root in _iter_sections(path):
        out.extend(_blocks(root, tables_as_markdown=False))
    return "\n\n".join(out)
