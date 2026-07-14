# syhwp

Korean **HWP 5.x** / **HWPX** 문서를 텍스트·마크다운으로 추출하는 순수 파이썬 라이브러리.
permissive(MIT) 라이선스로, AGPL(`pyhwp`)·미유지 바인딩(`libhwp`)의 공백을 메운다.

## ⚠️ 최우선 규칙: 클린룸 provenance

**이 프로젝트의 존재 이유가 permissive 라이선스다. 절대 깨지 말 것:**

- 구현은 **오직 Hancom 공개 스펙**(HWP 5.0 바이너리 포맷, OWPML)에서만 도출한다.
- **AGPL인 `pyhwp` 소스를 참고/복사하지 않는다.** (참고하는 순간 MIT 공개가 위반)
- Apache인 `hwp.js`/`hwp-rs`는 동작 교차검증용으로만 볼 수 있고, 실질 복제 시 Apache-2.0
  + NOTICE 승계 의무가 생기므로 코드 이식은 피한다. 스펙에서 직접 구현.
- 새 레코드/구조를 추가할 때 근거(스펙 절/필드)를 커밋 메시지나 주석에 남긴다.

## 개발 명령어

```bash
pip install -e ".[test]"     # 개발 설치 (의존성: olefile 하나)
pytest -q                    # 전체 테스트
pytest tests/test_records.py # 단위 테스트만
python -c "import syhwp; print(syhwp.extract_markdown('sample.hwpx'))"
```

로컬 실측용 실제 문서는 `tests/data/`에 두면 되지만 **커밋 금지**(.gitignore 처리,
저작권). 합성 샘플 기반 테스트만 리포에 포함한다.

## 아키텍처

```
src/syhwp/
  __init__.py    공개 API: detect_format / extract_text / extract_markdown (포맷 자동 감지)
  exceptions.py  SyhwpError ← UnsupportedFormatError / InvalidHwpError / EncryptedDocumentError
  _records.py    HWP5 레코드 순회 (헤더 uint32: tag10b/level10b/size12b, 0xFFF 확장)
  _hwp5.py       HWP5(OLE) 리더 — FileHeader 플래그, zlib(-15) 해제, PARA_TEXT(67) 디코드
  _hwpx.py       HWPX(OWPML) 리더 — zipfile+ElementTree, local-name 매칭, 표→GFM
  _markdown.py   GFM 표 렌더 공용 (normalize / escape_cell / grid_to_markdown)
```

### 핵심 포맷 사실 (자주 참조)

- **HWP5 = OLE 복합파일**(magic `D0CF11E0`). 스트림: `FileHeader`, `BodyText/Section{N}`,
  `DocInfo`(스타일 — **텍스트/표 추출엔 불필요, 파싱 안 함** → libhwp가 죽는 지점을 우회),
  `PrvText`(무압축 UTF-16LE 미리보기 지름길).
- FileHeader offset 36 properties 플래그: bit0 압축, bit1 암호, bit2 배포용. bit1/2면
  본문 암호화 → `EncryptedDocumentError`.
- 압축 섹션은 raw DEFLATE: `zlib.decompress(data, -15)`.
- PARA_TEXT 컨트롤 문자: 8 code-unit `{1-9,11,12,14-23}`, 1 unit `{0,10,13,24-31}`(10/13→개행).
- **HWPX = ZIP**(magic `PK\x03\x04`, mimetype `application/hwp+zip`). 본문
  `Contents/section{N}.xml`, 요소 로컬네임 `p/t/tbl/tr/tc`.

## 코딩 컨벤션

- 순수 파이썬, 외부 의존성은 **`olefile`(BSD)** 만. HWPX는 stdlib만.
- **견고성 우선**: 미지 레코드/요소는 raise 말고 skip. 잘린 스트림도 graceful.
  (패닉/크래시 없는 게 libhwp 대비 핵심 차별점)
- 예외는 전부 `SyhwpError` 하위. 사용자에게 명확한 사유 메시지.
- 공개 API는 `__init__.py`의 `__all__`만. 내부 모듈은 `_` 접두.
- Python 3.9+ 호환 (타입힌트 `List`/`Iterator` from typing, `X | Y` 지양).

## 로드맵 (DESIGN.md 상세)

- **v0 (현재)**: 포맷감지 + HWP5 텍스트 + HWPX 텍스트/표 + 암호감지.
- **v0.1**: HWP5 **표 그리드 재구성** — 레코드 level 트리 + CTRL_HEADER(`tbl `) +
  TABLE 레코드(행/열) + 셀 LIST_HEADER 그룹핑 → GFM.
- **v0.2**: 구조화 API(`open() → Document`), 각주/캡션, 퍼즈 하드닝, 테스트 코퍼스.

## 비목표

쓰기/편집, 레이아웃 픽셀 충실도, 암호문서 복호화, HWP 3.x(구포맷).
