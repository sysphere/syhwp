"""Unit tests for HWP5 payload parsers (synthetic bytes, no sample files)."""

import struct

from syhwp._hwp5 import (
    cell_address,
    is_table_control,
    table_dimensions,
)


def test_table_dimensions():
    # property (4 bytes) | n_rows (u16 @4) | n_cols (u16 @6)
    payload = struct.pack("<IHH", 0x4000006, 15, 3)
    assert table_dimensions(payload) == (15, 3)


def test_cell_address():
    # n_para (u16 @0) | 6 bytes list-property | col,row,colSpan,rowSpan (u16 @8..)
    payload = struct.pack("<H", 3) + b"\x00" * 6 + struct.pack("<HHHH", 2, 5, 1, 1)
    n_para, col, row, col_span, row_span = cell_address(payload)
    assert (n_para, col, row, col_span, row_span) == (3, 2, 5, 1, 1)


def test_is_table_control():
    # CTRL_HEADER stores the id little-endian: "tbl " -> b" lbt".
    assert is_table_control(b"tbl "[::-1] + b"\x00" * 12)
    assert not is_table_control(b"secd"[::-1] + b"\x00" * 12)
    assert not is_table_control(b"gso "[::-1] + b"\x00" * 12)


# --------------------------------------------------------------------------- #
# Nested lists: text boxes, footnotes, captions
#
# A record list is (tag, level, payload), so a document shape can be written out
# here without a sample file — which is how these cases are pinned without
# committing anything copyrighted.
# --------------------------------------------------------------------------- #

from syhwp._hwp5 import (  # noqa: E402
    HWPTAG_CTRL_HEADER,
    HWPTAG_LIST_HEADER,
    HWPTAG_PARA_HEADER,
    HWPTAG_PARA_TEXT,
    HWPTAG_SHAPE_COMPONENT,
    HWPTAG_TABLE,
    _build_tree,
    _emit_paragraph,
)
from syhwp.models import Image, Paragraph, Table  # noqa: E402


def _text(value):
    return value.encode("utf-16-le")


def _ctrl(ctrl_id):
    return ctrl_id.encode("ascii")[::-1] + b"\x00" * 12


def _cell(n_para, col, row, col_span=1, row_span=1):
    return struct.pack("<H", n_para) + b"\x00" * 6 + struct.pack(
        "<HHHH", col, row, col_span, row_span
    )


def _emit(records):
    root = _build_tree(records)
    blocks = []
    for node in root.children:
        if node.tag == HWPTAG_PARA_HEADER:
            _emit_paragraph(node, blocks)
    return blocks


def test_text_box_text_is_emitted():
    """A drawing object holds its text in a list under SHAPE_COMPONENT."""
    blocks = _emit([
        (HWPTAG_PARA_HEADER, 0, b""),
        (HWPTAG_CTRL_HEADER, 1, _ctrl("gso ")),
        (HWPTAG_SHAPE_COMPONENT, 2, b""),
        (HWPTAG_LIST_HEADER, 3, _cell(1, 0, 0)),
        (HWPTAG_PARA_HEADER, 3, b""),
        (HWPTAG_PARA_TEXT, 4, _text("상자 안의 글")),
    ])

    assert [type(b).__name__ for b in blocks] == ["Paragraph"]
    assert blocks[0].text == "상자 안의 글"


def test_a_drawing_without_text_is_still_an_image():
    """The other half of the rule: a picture-only document stays recognisable."""
    blocks = _emit([
        (HWPTAG_PARA_HEADER, 0, b""),
        (HWPTAG_CTRL_HEADER, 1, _ctrl("gso ")),
        (HWPTAG_SHAPE_COMPONENT, 2, b""),
    ])

    assert [type(b).__name__ for b in blocks] == ["Image"]


def test_table_caption_is_emitted_and_is_not_a_cell():
    """The caption list precedes the TABLE record; the cell lists follow it."""
    blocks = _emit([
        (HWPTAG_PARA_HEADER, 0, b""),
        (HWPTAG_CTRL_HEADER, 1, _ctrl("tbl ")),
        (HWPTAG_LIST_HEADER, 2, _cell(1, 2, 0, 8504, 0)),   # caption list
        (HWPTAG_PARA_HEADER, 2, b""),
        (HWPTAG_PARA_TEXT, 3, _text("표 1. 분기별 매출")),
        (HWPTAG_TABLE, 2, struct.pack("<IHH", 0, 1, 1)),
        (HWPTAG_LIST_HEADER, 2, _cell(1, 0, 0)),            # the one cell
        (HWPTAG_PARA_HEADER, 2, b""),
        (HWPTAG_PARA_TEXT, 3, _text("100")),
    ])

    assert [type(b).__name__ for b in blocks] == ["Paragraph", "Table"]
    assert blocks[0].text == "표 1. 분기별 매출"
    table = blocks[1]
    assert (table.n_rows, table.n_cols) == (1, 1)
    assert [c.text for c in table.cells] == ["100"]
    assert "표 1." not in table.to_markdown()


def test_a_footnote_is_emitted_where_it_is_anchored():
    """Footnotes and endnotes store their text the same way a text box does."""
    blocks = _emit([
        (HWPTAG_PARA_HEADER, 0, b""),
        (HWPTAG_PARA_TEXT, 1, _text("본문")),
        (HWPTAG_CTRL_HEADER, 1, _ctrl("fn  ")),
        (HWPTAG_LIST_HEADER, 2, _cell(1, 0, 0)),
        (HWPTAG_PARA_HEADER, 2, b""),
        (HWPTAG_PARA_TEXT, 3, _text("각주 내용")),
    ])

    assert [b.text for b in blocks] == ["본문", "각주 내용"]


def test_a_table_inside_a_text_box_stays_a_table():
    """Nesting neither flattens a table nor emits its cells twice."""
    blocks = _emit([
        (HWPTAG_PARA_HEADER, 0, b""),
        (HWPTAG_CTRL_HEADER, 1, _ctrl("gso ")),
        (HWPTAG_SHAPE_COMPONENT, 2, b""),
        (HWPTAG_LIST_HEADER, 3, _cell(1, 0, 0)),
        (HWPTAG_PARA_HEADER, 3, b""),
        (HWPTAG_CTRL_HEADER, 4, _ctrl("tbl ")),
        (HWPTAG_TABLE, 5, struct.pack("<IHH", 0, 1, 1)),
        (HWPTAG_LIST_HEADER, 5, _cell(1, 0, 0)),
        (HWPTAG_PARA_HEADER, 5, b""),
        (HWPTAG_PARA_TEXT, 6, _text("셀")),
    ])

    assert [type(b).__name__ for b in blocks] == ["Table"]
    assert [c.text for c in blocks[0].cells] == ["셀"]
