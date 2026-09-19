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


def _package(tmp_path, section: str) -> str:
    """A one-section HWPX package built in memory (the conftest fixture's shape)."""
    import zipfile

    path = tmp_path / "built.hwpx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr("version.xml", "<hv/>")
        z.writestr("Contents/section0.xml", section)
    return str(path)


_NS = (
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
)


def test_table_caption_is_read(tmp_path):
    """OWPML hangs the caption off the table, outside its rows.

    Measured on a 7.4 MB public report: eleven table titles — the lines a search
    is most likely to match — were the only text the reader missed.
    """
    section = (
        f"<hs:sec {_NS}><hp:p><hp:run><hp:tbl>"
        "<hp:caption><hp:subList><hp:p><hp:run>"
        "<hp:t>【최근 10년간 발표 현황】</hp:t>"
        "</hp:run></hp:p></hp:subList></hp:caption>"
        "<hp:tr><hp:tc><hp:subList><hp:p><hp:run><hp:t>분야</hp:t>"
        "</hp:run></hp:p></hp:subList></hp:tc></hp:tr>"
        "</hp:tbl></hp:run></hp:p></hs:sec>"
    )

    doc = syhwp.open(_package(tmp_path, section))

    assert [type(b).__name__ for b in doc.blocks] == ["Paragraph", "Table"]
    assert doc.blocks[0].text == "【최근 10년간 발표 현황】"
    # The caption is not a cell — the grid keeps only what the rows hold.
    assert [c.text for c in doc.blocks[1].cells] == ["분야"]


def test_caption_text_does_not_leak_into_cells(tmp_path):
    """A caption sitting inside ``hp:tbl`` must not be swept up as cell text."""
    section = (
        f"<hs:sec {_NS}><hp:p><hp:run><hp:tbl>"
        "<hp:caption><hp:subList><hp:p><hp:run><hp:t>캡션</hp:t>"
        "</hp:run></hp:p></hp:subList></hp:caption>"
        "<hp:tr><hp:tc><hp:subList><hp:p><hp:run><hp:t>값</hp:t>"
        "</hp:run></hp:p></hp:subList></hp:tc></hp:tr>"
        "</hp:tbl></hp:run></hp:p></hs:sec>"
    )

    table = syhwp.open(_package(tmp_path, section)).tables[0]

    assert "캡션" not in table.to_markdown()
