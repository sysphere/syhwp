"""Unit tests for the low-level HWP5 record iterator and text decoder."""

import struct

from syhwp._hwp5 import HWPTAG_PARA_TEXT, decode_para_text
from syhwp._records import iter_records


def _rec(tag, level, payload):
    assert len(payload) < 0xFFF
    header = (tag & 0x3FF) | ((level & 0x3FF) << 10) | ((len(payload) & 0xFFF) << 20)
    return struct.pack("<I", header) + payload


def test_iter_records_roundtrip():
    buf = _rec(1, 0, b"aa") + _rec(HWPTAG_PARA_TEXT, 1, b"bbbb") + _rec(3, 0, b"")
    recs = list(iter_records(buf))
    assert [(t, lv, p) for t, lv, p in recs] == [
        (1, 0, b"aa"),
        (HWPTAG_PARA_TEXT, 1, b"bbbb"),
        (3, 0, b""),
    ]


def test_iter_records_truncated_is_graceful():
    buf = _rec(1, 0, b"ok") + struct.pack("<I", 0)[:2]  # dangling partial header
    # Should not raise; yields the complete record then stops.
    recs = list(iter_records(buf))
    assert recs[0] == (1, 0, b"ok")


def test_decode_para_text_plain():
    payload = "가나다".encode("utf-16-le")
    assert decode_para_text(payload) == "가나다"


def test_decode_para_text_skips_extended_control():
    # code 11 (extended control) occupies 8 UTF-16 units; surrounding text kept.
    units = [ord("A")] + [11] * 8 + [ord("B")]
    payload = struct.pack("<%dH" % len(units), *units)
    assert decode_para_text(payload) == "AB"


def test_decode_para_text_linebreak():
    units = [ord("X"), 13, ord("Y")]  # 13 = paragraph/line break -> newline
    payload = struct.pack("<%dH" % len(units), *units)
    assert decode_para_text(payload) == "X\nY"
