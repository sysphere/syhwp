"""Shared fixtures — a synthetic HWPX package built in-memory (no sample files)."""

import zipfile

import pytest

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
