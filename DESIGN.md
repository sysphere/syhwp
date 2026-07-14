# syhwp — Design

## Goal

A pure-Python, permissively licensed reader for Korean HWP 5.x (legacy binary)
and HWPX (OWPML) documents, producing plain text and GFM markdown (tables as
pipe tables). Primary use case: feeding Korean office documents into RAG /
search / LLM pipelines where AGPL (`pyhwp`) and brittle/unmaintained bindings
(`libhwp`) are not acceptable.

Design priorities, in order: **(1) permissive license, (2) robustness on
real-world files, (3) zero-friction deployment (pure Python, one BSD dep),
(4) fidelity (tables).**

## Clean-room provenance

Implemented solely from HANCOM's published specifications:
- *한글 문서 파일 형식 5.0* (HWP 5.0 binary record format) — OLE/CFBF container,
  record stream layout, control characters.
- *OWPML* (HWPX) — OPC/ZIP package, section XML.

No code or structure is taken from the AGPL `pyhwp`. Apache-licensed references
(`hwp.js`, `hwp-rs`) may be consulted for cross-checking behaviour only; any
substantial reuse would require carrying Apache-2.0 + NOTICE, which we avoid by
working from the spec. This provenance is what permits the MIT license.

## Formats

### HWP 5.x (`_hwp5.py`)
OLE compound file (magic `D0CF11E0…`). Relevant streams:
- `FileHeader` — 32-byte signature `"HWP Document File"`, then version (uint32)
  and properties (uint32). Property bit 0 = compressed, bit 1 = password,
  bit 2 = distribution (copy-protected). Bits 1/2 ⇒ body is encrypted ⇒ we raise
  `EncryptedDocumentError`.
- `BodyText/Section{N}` — the content. If compressed, raw DEFLATE
  (`zlib.decompress(data, -15)`).
- `DocInfo` — styles / char shapes / bindata map. **Not required for text or
  table extraction**, so we do not parse it. (This is a robustness win: `libhwp`
  panics inside DocInfo style parsing on files we read fine.)

**Records** (`_records.py`): each record is a uint32 header —
`tag = bits 0–9`, `level = bits 10–19`, `size = bits 20–31`; if `size == 0xFFF`
the real size is the following uint32 — then `size` bytes of payload. Unknown
tags are skipped.

**Text** (`HWPTAG_PARA_TEXT`, tag 67): UTF-16LE code units with inline control
characters. Control chars occupying 8 code units (extended/inline objects):
`{1–9, 11, 12, 14–23}`; occupying 1 unit (char controls): `{0, 10, 13, 24–31}`,
of which 10/13 map to a newline. Everything else is literal text.

**Tables** are reconstructed from the record tree (built from each record's
`level`). A table is a `HWPTAG_CTRL_HEADER` (tag 71) whose first 4 payload bytes
are the little-endian control id `"tbl "` (i.e. `b" lbt"`). Its children are:
- `HWPTAG_TABLE` (tag 77): `n_rows` (uint16 @4), `n_cols` (uint16 @6).
- repeated `HWPTAG_LIST_HEADER` (tag 72) — one per cell: `n_paragraphs`
  (uint16 @0), then `col`/`row`/`col_span`/`row_span` (uint16 @8/@10/@12/@14) —
  each followed by its `n_paragraphs` `HWPTAG_PARA_HEADER` (tag 66) subtrees,
  which hold the cell's text. Cells are placed into a `n_rows × n_cols` grid and
  rendered as GFM. Nested tables (a table inside a cell) linearize into that
  cell's text. (Offsets were derived empirically from the public format, not
  from `pyhwp` — see the clean-room note.)

### HWPX (`_hwpx.py`)
ZIP package (magic `PK\x03\x04`, mimetype `application/hwp+zip`). Text and tables
live in `Contents/section{N}.xml` as OWPML. Parsed with the standard library
(`zipfile` + `xml.etree.ElementTree`), matching elements by local name
(namespace-agnostic): `p` (paragraph), `t` (text run), `tbl`/`tr`/`tc`
(table/row/cell). Tables render to GFM via `_markdown.py`.

## Public API (`__init__.py`)
- `detect_format(path) -> "hwp5" | "hwpx"`
- `extract_text(path) -> str`
- `extract_markdown(path) -> str`

## Roadmap
- **v0 (done):** format detection; HWP5 text extraction; HWPX text + tables;
  encryption detection. Verified on real government documents, including files
  that crash `libhwp`.
- **v0.1 (done):** HWP5 **table grid reconstruction** — walk the record tree by
  `level`, detect `CTRL_HEADER` with ctrl-id `tbl `, read the `TABLE` record
  (rows/cols) and per-cell `LIST_HEADER`, group cell paragraphs into a grid → GFM.
- **v0.2 (next):** structured API (`open() -> Document` with paragraphs/tables),
  cell merge (`col_span`/`row_span`) rendering, inline object metadata,
  footnotes/captions, a real test corpus + fuzz hardening.
- **later:** optional richer output (styles), performance, streaming.

## Non-goals
- Writing/editing HWP files (read-only).
- Rendering/layout fidelity (we target content extraction, not pixel fidelity).
- Decrypting password/distribution-protected documents.
- HWP 3.x and earlier (different, pre-5.0 format).
