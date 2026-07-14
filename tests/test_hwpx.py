"""Self-contained HWPX tests (build a synthetic OWPML package in-memory).

No copyrighted sample files are shipped; these exercise the parser end-to-end.
"""

import zipfile

import pytest

import syhwp

_SECTION = """<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"
        xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p><hp:run><hp:t>충북 AI 도입 지원 제안요청서</hp:t></hp:run></hp:p>
  <hp:p><hp:run>
    <hp:tbl>
      <hp:tr>
        <hp:tc><hp:subList><hp:p><hp:run><hp:t>구분</hp:t></hp:run></hp:p></hp:subList></hp:tc>
        <hp:tc><hp:subList><hp:p><hp:run><hp:t>내용</hp:t></hp:run></hp:p></hp:subList></hp:tc>
      </hp:tr>
      <hp:tr>
        <hp:tc><hp:subList><hp:p><hp:run><hp:t>사업기간</hp:t></hp:run></hp:p></hp:subList></hp:tc>
        <hp:tc><hp:subList><hp:p><hp:run><hp:t>2026. 6. ~ 12.</hp:t></hp:run></hp:p></hp:subList></hp:tc>
      </hp:tr>
    </hp:tbl>
  </hp:run></hp:p>
  <hp:p><hp:run><hp:t>표 뒤 마무리 문단.</hp:t></hp:run></hp:p>
</hs:sec>"""


@pytest.fixture()
def sample_hwpx(tmp_path):
    path = tmp_path / "sample.hwpx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr("version.xml", "<hv/>")
        z.writestr("Contents/section0.xml", _SECTION)
    return str(path)


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
