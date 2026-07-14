# syhwp

[![PyPI](https://img.shields.io/pypi/v/syhwp.svg)](https://pypi.org/project/syhwp/)
[![Python versions](https://img.shields.io/pypi/pyversions/syhwp.svg)](https://pypi.org/project/syhwp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/sysphere/syhwp/actions/workflows/ci.yml/badge.svg)](https://github.com/sysphere/syhwp/actions/workflows/ci.yml)

**English** · [한국어](README.ko.md)

Pure-Python reader for Korean **HWP** (`.hwp`) and **HWPX** (`.hwpx`) documents —
the file formats produced by **Hancom Office / 한글 (Hangul)**. Read a document
and get its text, tables, equations and images as **plain text**, GitHub-flavored
**Markdown**, or **HTML**, with a single small dependency and a permissive **MIT**
license.

Reach for `syhwp` when you need to **read or convert `.hwp` / `.hwpx` files in
Python** — for search, RAG / LLM pipelines, data migration, or plain text
extraction — and can't use the AGPL-licensed `pyhwp`.

```python
import syhwp

text = syhwp.extract_text("report.hwp")        # plain text
md   = syhwp.extract_markdown("report.hwpx")   # Markdown (tables as pipe tables)
html = syhwp.extract_html("report.hwp")        # standalone HTML
```

`.hwp` (legacy binary) and `.hwpx` (OWPML) are detected automatically and handled
the same way.

## Install

```bash
pip install syhwp
```

The only runtime dependency is [`olefile`](https://pypi.org/project/olefile/)
(BSD). HWPX parsing uses the Python standard library alone. Works on Python
3.9–3.13, on any OS.

## Command line

```bash
syhwp report.hwp              # Markdown (default)
syhwp report.hwp --text       # plain text
syhwp report.hwpx --html      # HTML
python -m syhwp report.hwp    # equivalent
```

## What the output looks like

A table in the document comes out as a GitHub-flavored Markdown table:

```markdown
■ Road structure & facilities standard — revision comparison

| Before (2020) | After (2021) | Note |
| --- | --- | --- |
| … design speed 120 110 100 …  stopping sight distance 215 185 155 … | … 225 195 170 … |  |
```

Equations are surfaced as their script (`[수식: …]`) and images as a `[그림]`
placeholder, so no content is silently dropped.

## Library API

Convenience functions — each takes a path and returns a string:

| Function | Returns |
| --- | --- |
| `extract_text(path)` | plain text |
| `extract_markdown(path)` | GFM Markdown; tables become pipe tables |
| `extract_html(path)` | a standalone HTML document |
| `detect_format(path)` | `"hwp5"` or `"hwpx"` |

Structured access via `open()`:

```python
doc = syhwp.open("report.hwp")       # -> Document
doc.version                           # e.g. "5.1.0.1"
doc.text, doc.markdown, doc.html      # rendered forms

for table in doc.tables:              # Table(n_rows, n_cols, cells)
    print(table.to_markdown())
    for cell in table.cells:          # Cell(row, col, text, row_span, col_span)
        ...

for para in doc.paragraphs:           # Paragraph(text)
    print(para.text)

for eq in doc.equations:              # Equation(script)
    print(eq.script)
```

`doc.blocks` holds every block in reading order as a `Paragraph`, `Table`,
`Equation`, or `Image`. Errors derive from `syhwp.SyhwpError`
(`UnsupportedFormatError`, `InvalidHwpError`, `EncryptedDocumentError`).

## What is supported

| | HWP 5.x (`.hwp`) | HWPX (`.hwpx`) |
| --- | --- | --- |
| Text | ✅ | ✅ |
| Tables → grid / Markdown / HTML | ✅ | ✅ |
| Equations (as script) | ✅ | ✅ |
| Image placeholders | ✅ | ✅ |
| Document version | ✅ | ✅ |

- **Robust by design:** unknown records/elements are skipped, and malformed or
  corrupt input raises a typed `SyhwpError` rather than crashing (fuzz-tested).
- **No servers, no Java, no Rust** — pure Python, one dependency.

## Limitations

- Password-protected and *distribution* (copy-protected, 배포용) documents cannot
  be read — their body is encrypted; these raise `EncryptedDocumentError`.
- Merged table cells are captured in the model (`row_span` / `col_span`), but
  Markdown output leaves the covered cells blank (Markdown cannot merge cells).
- HWP 3.x and earlier (a different, pre-5.0 format) are not supported.

## Why another HWP library?

If you searched for a *`pyhwp` alternative*, an *AGPL-free HWP parser*, or a way
to read `.hwp` files without a Java or Rust toolchain — that's the gap `syhwp`
fills. The existing Python options each have a blocker for commercial or SaaS use:

| Library | License | Note |
| --- | --- | --- |
| `pyhwp` | AGPL-3.0 | Network copyleft — unsuitable for closed / SaaS use |
| `libhwp` (hwp-rs) | Apache-2.0 | Unmaintained; no Python 3.12+ wheels |
| `pyhwpx` | — | Windows-only (COM automation) |

`syhwp` aims to be the permissively-licensed, maintained, pure-Python option, and
adds HWPX support plus Markdown / HTML output.

## How it works

`syhwp` is a **clean-room implementation** written from HANCOM's publicly
published *HWP 5.0 binary format* and *OWPML (HWPX)* specifications. It does not
derive from or incorporate the AGPL-licensed `pyhwp`, which is what allows the
permissive MIT license. See [DESIGN.md](DESIGN.md) for the record/element layout
and parsing details.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). A dev tool,
`python scripts/inspect_hwp.py <file>`, dumps a document's internal structure to
help add support for new records or elements.

## License

MIT © 2026 sysphere
