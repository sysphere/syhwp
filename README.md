# syhwp

Pure-Python reader for Korean **HWP 5.x** and **HWPX** documents — extracts text
and tables, with no external services and a permissive license.

```python
import syhwp

# convenience
text = syhwp.extract_text("report.hwp")        # plain text
md   = syhwp.extract_markdown("report.hwpx")   # GFM markdown (tables as pipe tables)

# structured access
doc = syhwp.open("report.hwp")                 # -> Document
for table in doc.tables:                       # Table: n_rows, n_cols, cells[...]
    print(table.to_markdown())
for para in doc.paragraphs:                     # Paragraph: text
    print(para.text)
```

Format (HWP vs HWPX) is auto-detected. Works the same for `.hwp` and `.hwpx`.

Also available as a command line tool:

```bash
syhwp report.hwp                 # markdown (default); also --text / --html
python -m syhwp report.hwpx
```

## Why

The existing Python options each have a blocking flaw for use in commercial or
SaaS software:

| Library | License | Issue |
|---|---|---|
| `pyhwp` | **AGPL-3.0** | Strong network copyleft — unusable in closed/SaaS products |
| `libhwp` (hwp-rs) | Apache-2.0 | Unmaintained (0.2.0), panics on real files, no 3.12+ wheels |
| `pyhwpx` | — | Windows-only (COM automation) |

`syhwp` fills the gap: **pure Python, permissive (MIT), maintained, robust by
design** (unknown/edge records are skipped rather than crashing).

## Install

```bash
pip install syhwp
```

Only dependency: [`olefile`](https://pypi.org/project/olefile/) (BSD). HWPX
parsing uses the standard library only.

## Status

Alpha. See [DESIGN.md](DESIGN.md) for the architecture and roadmap.

- **HWP 5.x** — text and table extraction (tables reconstructed into GFM pipe
  tables); equations surfaced as their script, images/drawings as `[그림]`;
  document version exposed on `Document.version`.
- **HWPX** — text and table extraction.
- Robust by design: unknown records are skipped, and malformed / corrupt files
  raise a `SyhwpError` subclass rather than crashing (fuzz-tested).
- Password-protected / distribution (copy-protected) documents raise
  `EncryptedDocumentError` (their body streams are encrypted and cannot be read).

## Provenance / license note

`syhwp` is a **clean-room implementation** written from the publicly published
HANCOM *HWP 5.0 binary format* and *OWPML (HWPX)* specifications. It does **not**
derive from, or incorporate code from, the AGPL-licensed `pyhwp`. This is what
allows `syhwp` to be offered under the permissive MIT license.

## License

MIT © 2026 sysphere
