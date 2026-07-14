"""HWPX end-to-end tests (fixtures in conftest.py)."""

import pytest

import syhwp


def test_detect_hwpx(sample_hwpx):
    assert syhwp.detect_format(sample_hwpx) == "hwpx"


def test_markdown_has_table(sample_hwpx):
    md = syhwp.extract_markdown(sample_hwpx)
    assert "| 구분 | 내용 |" in md
    assert "| --- | --- |" in md
    assert "사업기간" in md and "2026. 6. ~ 12." in md
    assert "표 뒤 마무리 문단." in md


def test_text_has_content_no_pipes(sample_hwpx):
    text = syhwp.extract_text(sample_hwpx)
    assert "구분" in text and "사업기간" in text
    assert "|" not in text  # text mode does not render pipe tables


def test_unsupported_format(tmp_path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"hello, not a document")
    with pytest.raises(syhwp.UnsupportedFormatError):
        syhwp.detect_format(str(p))
