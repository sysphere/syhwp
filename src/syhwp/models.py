"""Structured document model shared by the HWP 5.x and HWPX readers.

A :class:`Document` is an ordered list of blocks — :class:`Paragraph` or
:class:`Table` — mirroring reading order. Both block types expose ``.text`` and
``.to_markdown()`` so the document can render either representation uniformly.
"""

from dataclasses import dataclass, field
from typing import List, Union

from ._markdown import escape_cell, grid_to_markdown, normalize


@dataclass
class Cell:
    """A single table cell. ``row``/``col`` are its top-left grid position;
    ``row_span``/``col_span`` are how many rows/cols it merges (1 = no merge)."""

    row: int
    col: int
    text: str
    row_span: int = 1
    col_span: int = 1


@dataclass
class Table:
    n_rows: int
    n_cols: int
    cells: List[Cell] = field(default_factory=list)

    def grid(self) -> List[List[str]]:
        """Row-major grid of cell text. Merged cells occupy their top-left slot;
        the covered slots are left empty (GFM has no cell merging)."""
        g = [["" for _ in range(self.n_cols)] for _ in range(self.n_rows)]
        for c in self.cells:
            if 0 <= c.row < self.n_rows and 0 <= c.col < self.n_cols:
                g[c.row][c.col] = c.text
        return g

    @property
    def text(self) -> str:
        return "\n".join(" ".join(cell for cell in row).strip() for row in self.grid())

    def to_markdown(self) -> str:
        return grid_to_markdown(
            [[escape_cell(cell) for cell in row] for row in self.grid()]
        )


@dataclass
class Paragraph:
    text: str

    def to_markdown(self) -> str:
        return self.text


Block = Union[Paragraph, Table]


@dataclass
class Document:
    """A parsed HWP/HWPX document as an ordered list of blocks."""

    format: str  # "hwp5" or "hwpx"
    blocks: List[Block] = field(default_factory=list)

    @property
    def paragraphs(self) -> List[Paragraph]:
        return [b for b in self.blocks if isinstance(b, Paragraph)]

    @property
    def tables(self) -> List[Table]:
        return [b for b in self.blocks if isinstance(b, Table)]

    @property
    def text(self) -> str:
        return "\n".join(
            b.text for b in self.blocks if normalize(b.text)
        )

    @property
    def markdown(self) -> str:
        out = []
        for b in self.blocks:
            md = b.to_markdown()
            if md.strip():
                out.append(md)
        return "\n\n".join(out)
