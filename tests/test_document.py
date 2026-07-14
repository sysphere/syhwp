"""Structured API tests: syhwp.open() -> Document, and the model."""

import syhwp
from syhwp import Cell, Document, Paragraph, Table


def test_open_returns_document(sample_hwpx):
    doc = syhwp.open(sample_hwpx)
    assert isinstance(doc, Document)
    assert doc.format == "hwpx"


def test_document_blocks_order(sample_hwpx):
    doc = syhwp.open(sample_hwpx)
    kinds = [type(b).__name__ for b in doc.blocks]
    # paragraph, table, paragraph
    assert kinds == ["Paragraph", "Table", "Paragraph"]


def test_document_tables_and_grid(sample_hwpx):
    doc = syhwp.open(sample_hwpx)
    assert len(doc.tables) == 1
    table = doc.tables[0]
    assert isinstance(table, Table)
    assert (table.n_rows, table.n_cols) == (2, 2)
    grid = table.grid()
    assert grid[0] == ["구분", "내용"]
    assert grid[1] == ["사업기간", "2026. 6. ~ 12."]
    assert all(isinstance(c, Cell) for c in table.cells)


def test_document_paragraphs(sample_hwpx):
    doc = syhwp.open(sample_hwpx)
    texts = [p.text for p in doc.paragraphs]
    assert any("충북 AI" in t for t in texts)
    assert any("마무리" in t for t in texts)
    assert all(isinstance(p, Paragraph) for p in doc.paragraphs)


def test_helpers_match_document(sample_hwpx):
    doc = syhwp.open(sample_hwpx)
    assert syhwp.extract_markdown(sample_hwpx) == doc.markdown
    assert syhwp.extract_text(sample_hwpx) == doc.text


def test_cell_defaults():
    c = Cell(row=0, col=1, text="x")
    assert c.row_span == 1 and c.col_span == 1
