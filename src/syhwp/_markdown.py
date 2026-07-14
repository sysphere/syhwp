"""Shared helpers for rendering extracted tables as GFM markdown."""

import re
from typing import List

_WS = re.compile(r"\s+")


def normalize(s: str) -> str:
    """Collapse whitespace and strip."""
    return _WS.sub(" ", s or "").strip()


def escape_cell(s: str) -> str:
    """Normalize a cell value and escape pipes so it is GFM-table safe."""
    return normalize(s).replace("|", "\\|")


def grid_to_markdown(grid: List[List[str]]) -> str:
    """Render a row-major grid of cell strings as a GFM pipe table.

    Ragged rows (from merged cells) are padded to the widest row. Returns an
    empty string for an empty grid.
    """
    grid = [row for row in grid if row]
    ncols = max((len(row) for row in grid), default=0)
    if ncols == 0:
        return ""
    grid = [row + [""] * (ncols - len(row)) for row in grid]
    lines = [
        "| " + " | ".join(grid[0]) + " |",
        "| " + " | ".join(["---"] * ncols) + " |",
    ]
    for row in grid[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)
