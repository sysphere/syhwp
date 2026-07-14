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
