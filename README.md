# syhwp

Pure-Python reader for Korean **HWP 5.x** and **HWPX** documents. Extracts text,
tables, equations and images as plain text, GitHub-flavored **Markdown**, or
**HTML** — with a single small dependency and a permissive (MIT) license.

```python
import syhwp

text = syhwp.extract_text("report.hwp")        # plain text
md   = syhwp.extract_markdown("report.hwpx")   # markdown (tables as pipe tables)
html = syhwp.extract_html("report.hwp")        # standalone HTML
```

The format (HWP vs HWPX) is detected automatically, so `.hwp` and `.hwpx` are
handled the same way.

## Install

```bash
pip install syhwp
```

The only runtime dependency is [`olefile`](https://pypi.org/project/olefile/)
(BSD). HWPX parsing uses the standard library alone.

## Command line

```bash
syhwp report.hwp              # markdown (default)
syhwp report.hwp --text       # plain text
syhwp report.hwpx --html      # HTML
python -m syhwp report.hwp    # equivalent
```

## Library API

Convenience functions — each takes a path and returns a string:

- `extract_text(path)` — plain text
- `extract_markdown(path)` — GFM markdown; tables become pipe tables
- `extract_html(path)` — a standalone HTML document
- `detect_format(path)` — `"hwp5"` or `"hwpx"`

Structured access via `open()`:

```python
doc = syhwp.open("report.hwp")      # -> Document
doc.version                          # e.g. "5.1.0.1"
doc.text, doc.markdown, doc.html     # rendered forms

for table in doc.tables:             # Table(n_rows, n_cols, cells)
    print(table.to_markdown())
    for cell in table.cells:         # Cell(row, col, text, row_span, col_span)
        ...

for para in doc.paragraphs:          # Paragraph(text)
    print(para.text)

for eq in doc.equations:             # Equation(script)
    print(eq.script)
```

Blocks appear in reading order in `doc.blocks` as `Paragraph`, `Table`,
`Equation`, or `Image`.

## Features

- **HWP 5.x** (legacy OLE binary) and **HWPX** (OWPML) in one library.
- Tables reconstructed into a grid (Markdown pipe tables / HTML `<table>`).
- Equations surfaced as their script; images/drawings as a `[그림]` placeholder.
- Robust by design: unknown records are skipped, and malformed or corrupt input
  raises a typed `SyhwpError` instead of crashing (fuzz-tested).
- Pure Python 3.9–3.13, one dependency, no external services or servers.

## Limitations

- Password-protected and *distribution* (copy-protected) documents cannot be
  read — their body is encrypted; these raise `EncryptedDocumentError`.
- Merged table cells are captured in the model (`row_span` / `col_span`), but
  Markdown output leaves the covered cells blank (Markdown cannot merge cells).
- HWP 3.x and earlier (a different, pre-5.0 format) are not supported.

## Why another HWP library?

The existing Python options each have a blocker for commercial or SaaS use:

| Library | License | Note |
|---|---|---|
| `pyhwp` | AGPL-3.0 | Network copyleft — unsuitable for closed / SaaS use |
| `libhwp` (hwp-rs) | Apache-2.0 | Unmaintained; no Python 3.12+ wheels |
| `pyhwpx` | — | Windows-only (COM automation) |

`syhwp` aims to be the permissively-licensed, maintained, pure-Python option, and
adds HWPX support and Markdown / HTML output.

## Provenance

`syhwp` is a **clean-room implementation** written from HANCOM's publicly
published *HWP 5.0 binary format* and *OWPML (HWPX)* specifications. It does not
derive from or incorporate the AGPL-licensed `pyhwp`, which is what allows the
permissive MIT license.

See [DESIGN.md](DESIGN.md) for architecture and file-format notes.

## License

MIT © 2026 sysphere
