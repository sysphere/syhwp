# syhwp

[![PyPI](https://img.shields.io/pypi/v/syhwp.svg)](https://pypi.org/project/syhwp/)
[![Python versions](https://img.shields.io/pypi/pyversions/syhwp.svg)](https://pypi.org/project/syhwp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/sysphere/syhwp/actions/workflows/ci.yml/badge.svg)](https://github.com/sysphere/syhwp/actions/workflows/ci.yml)

[English](README.md) · **한국어**

**한글(HWP · HWPX) 문서를 파이썬으로 읽는** 순수 파이썬 라이브러리입니다. 한컴오피스
한글이 만든 `.hwp`(구형 바이너리)·`.hwpx`(OWPML) 파일에서 **텍스트·표·수식·이미지**를
**평문 · GitHub 마크다운 · HTML**로 추출합니다. 의존성은 작은 것 하나뿐이고 라이선스는
허용적인 **MIT**입니다.

**한글 파일을 파이썬에서 읽거나 변환**해야 할 때 — 검색, RAG/LLM 파이프라인, 데이터
마이그레이션, 단순 텍스트 추출 등 — 그리고 AGPL 라이선스인 `pyhwp`를 쓸 수 없을 때
`syhwp`를 쓰세요.

```python
import syhwp

text = syhwp.extract_text("보고서.hwp")        # 평문
md   = syhwp.extract_markdown("보고서.hwpx")   # 마크다운 (표는 파이프 표로)
html = syhwp.extract_html("보고서.hwp")        # 단독 HTML
```

`.hwp`(구형 바이너리)와 `.hwpx`(OWPML)는 자동으로 감지되어 동일하게 처리됩니다.

## 설치

```bash
pip install syhwp
```

런타임 의존성은 [`olefile`](https://pypi.org/project/olefile/)(BSD) 하나뿐이며,
HWPX 파싱은 파이썬 표준 라이브러리만 사용합니다. Python 3.9–3.13, 모든 OS에서 동작합니다.

## 명령줄 도구

```bash
syhwp 보고서.hwp              # 마크다운 (기본)
syhwp 보고서.hwp --text       # 평문
syhwp 보고서.hwpx --html      # HTML
python -m syhwp 보고서.hwp    # 위와 동일
```

## 출력 예시

문서의 표는 GitHub 마크다운 표로 나옵니다:

```markdown
■ 도로의 구조·시설 기준에 관한 규칙, 해설 신구대비표

| 이전 (2020) | 개정 (2021) | 비고 |
| --- | --- | --- |
| … 설계속도 120 110 100 …  최소 정지시거 215 185 155 … | … 225 195 170 … |  |
```

수식은 스크립트(`[수식: …]`)로, 이미지는 `[그림]` 자리표시자로 나와서 내용이 조용히
사라지지 않습니다.

## 라이브러리 API

편의 함수 — 경로를 받아 문자열을 반환합니다:

| 함수 | 반환 |
| --- | --- |
| `extract_text(path)` | 평문 |
| `extract_markdown(path)` | GFM 마크다운, 표는 파이프 표 |
| `extract_html(path)` | 단독 HTML 문서 |
| `detect_format(path)` | `"hwp5"` 또는 `"hwpx"` |

`open()`으로 구조화 접근:

```python
doc = syhwp.open("보고서.hwp")        # -> Document
doc.version                            # 예: "5.1.0.1"
doc.text, doc.markdown, doc.html       # 렌더링된 형태

for table in doc.tables:               # Table(n_rows, n_cols, cells)
    print(table.to_markdown())
    for cell in table.cells:           # Cell(row, col, text, row_span, col_span)
        ...

for para in doc.paragraphs:            # Paragraph(text)
    print(para.text)

for eq in doc.equations:               # Equation(script)
    print(eq.script)
```

`doc.blocks`는 읽기 순서대로 모든 블록을 `Paragraph` / `Table` / `Equation` /
`Image`로 담습니다. 예외는 모두 `syhwp.SyhwpError` 하위입니다
(`UnsupportedFormatError`, `InvalidHwpError`, `EncryptedDocumentError`).

## 지원 범위

| | HWP 5.x (`.hwp`) | HWPX (`.hwpx`) |
| --- | --- | --- |
| 텍스트 | ✅ | ✅ |
| 표 → 그리드 / 마크다운 / HTML | ✅ | ✅ |
| 수식 (스크립트) | ✅ | ✅ |
| 이미지 자리표시자 | ✅ | ✅ |
| 문서 버전 | ✅ | ✅ |

- **견고성 우선:** 모르는 레코드/요소는 건너뛰고, 손상·비정상 입력은 크래시 대신 타입이
  지정된 `SyhwpError`를 던집니다(퍼즈 테스트됨).
- **서버·Java·Rust 불필요** — 순수 파이썬, 의존성 하나.

## 한계

- 암호 문서는 읽을 수 없습니다 → `EncryptedDocumentError`. **배포용(복사방지)**
  문서는 읽습니다 — 열쇠가 파일 안에 함께 들어 있어서, 그 표시는 비밀을 지키는 것이
  아니라 편집하지 말라는 뜻입니다. `syhwp[fast]` (또는 `cryptography` 설치)이면
  내장 순수 파이썬 AES 보다 약 90배 빠르게 풉니다.
- 병합 셀은 모델(`row_span`/`col_span`)에 담기지만, 마크다운은 셀 병합을 못 하므로
  가려진 셀은 빈칸으로 둡니다.
- HWP 3.x 이하(5.0 이전의 다른 포맷)는 지원하지 않습니다.

## 왜 또 다른 HWP 라이브러리인가

*`pyhwp` 대안*, *AGPL 아닌 HWP 파서*, Java·Rust 툴체인 없이 `.hwp`를 읽는 방법을
찾으셨다면 — 그 공백을 `syhwp`가 메웁니다. 기존 파이썬 옵션은 상용/SaaS 사용에 각각
걸림돌이 있습니다:

| 라이브러리 | 라이선스 | 비고 |
| --- | --- | --- |
| `pyhwp` | AGPL-3.0 | 네트워크 카피레프트 — 폐쇄/SaaS에 부적합 |
| `libhwp` (hwp-rs) | Apache-2.0 | 미유지, Python 3.12+ 휠 없음 |
| `pyhwpx` | — | Windows 전용(COM 자동화) |

`syhwp`는 허용적 라이선스의, 유지되는, 순수 파이썬 옵션을 지향하며 HWPX 지원과
마크다운/HTML 출력을 더합니다.

## 동작 원리

`syhwp`는 한컴이 공개한 *HWP 5.0 바이너리 포맷*과 *OWPML(HWPX)* 규격에서 도출한
**클린룸 구현**입니다. AGPL인 `pyhwp`의 코드를 참조하거나 포함하지 않으며, 그래서 MIT
라이선스가 가능합니다. 레코드/요소 레이아웃과 파싱 세부는 [DESIGN.md](DESIGN.md) 참고.

## 기여

기여 환영합니다 — [CONTRIBUTING.md](CONTRIBUTING.md) 참고. 개발 도구
`python scripts/inspect_hwp.py <파일>`로 문서 내부 구조를 덤프해 새 레코드/요소 지원을
추가할 수 있습니다.

## 라이선스

MIT © 2026 sysphere
