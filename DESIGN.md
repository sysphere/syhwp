# syhwp — design & format notes

A pure-Python, permissively-licensed reader for Korean HWP 5.x (legacy binary)
and HWPX (OWPML) documents, producing plain text, GFM markdown, and HTML.

Design priorities, in order:

1. Permissive (MIT) license.
2. Robustness on real-world files — degrade (skip) rather than crash.
3. Zero-friction deployment — pure Python, a single small dependency.
4. Fidelity — tables, equations, images.

## Clean-room provenance

Implemented solely from HANCOM's published specifications:

- *한글 문서 파일 형식 5.0* — the HWP 5.0 binary record format (OLE/CFBF
  container, record stream layout, control characters).
- *OWPML* — the HWPX package format (OPC/ZIP, section XML).

No code or structure is taken from the AGPL-licensed `pyhwp`. This provenance is
what permits the MIT license.

## Architecture

```
syhwp/
  __init__.py   public API: detect_format / open / extract_text|markdown|html
  models.py     Document, Paragraph, Table, Cell, Equation, Image
  _records.py   HWP5 record iterator
  _hwp5.py      HWP5 (OLE) reader
  _hwpx.py      HWPX (OWPML) reader
  _markdown.py  GFM table rendering
  __main__.py   command-line interface
```

`open(path)` detects the format by magic bytes and returns a `Document` — an
ordered list of blocks (`Paragraph`, `Table`, `Equation`, `Image`). The
`extract_*` helpers render that document to text, markdown, or HTML.

## HWP 5.x format (`_hwp5.py`)

OLE compound file (magic `D0CF11E0…`). Relevant streams:

- **`FileHeader`** — 32-byte signature `"HWP Document File"`, then a version
  uint32 and a properties uint32. Property bit 0 = compressed, bit 1 = password,
  bit 2 = distribution (copy-protected). Bit 1 means the body is encrypted under
  a password the file does not carry, so the reader raises
  `EncryptedDocumentError`; bit 2 is read (see below).
- **`BodyText/Section{N}`** — the content. When compressed, it is raw DEFLATE
  (`zlib.decompress(data, -15)`).
- **`ViewText/Section{N}`** — where a distribution document keeps its content
  instead; the `BodyText` streams are then stubs.
- **`DocInfo`** — fonts / styles / bindata map. Not needed for text or table
  extraction, so it is not parsed.

**Records** (`_records.py`): each record starts with a little-endian uint32
header — `tag` = bits 0–9, `level` = bits 10–19, `size` = bits 20–31; if
`size == 0xFFF` the real size is the following uint32. Unknown tags are skipped,
and truncated streams stop cleanly.

**Text** (`PARA_TEXT`, tag 67): UTF-16LE code units interleaved with control
characters. Controls occupying 8 code units: `{1–9, 11, 12, 14–23}`; occupying 1
unit: `{0, 10, 13, 24–31}` (10/13 → newline). Everything else is literal text.

**Tables** are reconstructed from the record tree (built from each record's
`level`). A table is a `CTRL_HEADER` (tag 71) whose first 4 payload bytes are the
little-endian control id `"tbl "`. Its children are:

- `TABLE` (tag 77): `n_rows` (uint16 @4), `n_cols` (uint16 @6).
- repeated `LIST_HEADER` (tag 72), one per cell: `n_paragraphs` (uint16 @0), then
  `col` / `row` / `col_span` / `row_span` (uint16 @8/@10/@12/@14), each followed
  by its `n_paragraphs` `PARA_HEADER` (tag 66) subtrees holding the cell's text.

Cells are placed into an `n_rows × n_cols` grid. Nested tables linearize into the
containing cell's text. Equations (`eqed` control → `EQEDIT` record, tag 88) are
surfaced as their script. All record offsets were derived empirically from the
public format.

**Nested lists.** Text does not live only under top-level paragraphs. A control
carries the *common object properties* first — the caption list among them — and
then its own record (`TABLE`, `SHAPE_COMPONENT` tag 76, or `EQEDIT`); anything a
text box, footnote, endnote, header or footer holds is a `LIST_HEADER` +
`PARA_HEADER` subtree below that. So the emitter walks a control's whole subtree
and hands each paragraph and each nested control to its own emitter, which is
what keeps a table inside a text box a table and a cell's text from appearing
twice. The walk is depth-capped so a malformed level chain cannot drive it into
recursion failure.

Two consequences worth stating, because both were measured as defects:

- **The caption list is not a cell list.** It precedes the `TABLE` record, and
  reading cells from the first `LIST_HEADER` made the caption a cell with a wild
  address (`(1, 2, 0, 8504, 0)` on a 1×1 table) whose text then fell outside the
  grid and vanished. Cells are read from after the `TABLE` record; the caption is
  emitted as a paragraph ahead of the table, where a reader looking for the
  table's title will find it. Captions attached below a table in the layout still
  come out ahead of it — the record order is what the reader has.
- **A drawing reports itself as an `Image` only when it holds no text.** A text
  box is a `gso` control too, so emitting a placeholder unconditionally would put
  `[그림]` in front of prose; emitting nothing would lose "this document is
  nothing but pictures", which callers check to tell a scan apart from a document
  they failed to read.

**Distribution documents** (`_crypt.py`) keep their sections in `ViewText`, each
opening with a 256-byte `HWPTAG_DISTRIBUTE_DOC_DATA` record (tag 28). Its first
four bytes are a seed; the rest of the record is masked with a byte stream from a
linear congruential generator (`n = 214013·n + 2531011`) that draws twice per run
— the first draw's `(n >> 16) & 0xFF` is the byte, the second's `((n >> 16) & 0x0F) + 1`
how far it reaches. Unmasked, the record holds UTF-16LE hex characters, and the
16 bytes at `4 + (seed & 0x0F)` are the AES-128 key the rest of the section is
encrypted with (ECB), after which the usual DEFLATE applies. The generator was
fitted to the stream one sample implies and then confirmed by a second with a
different seed; both decrypt into records that parse.

The key is *in the file*, so this flag asks editors not to edit rather than
keeping a secret — which is why reading it needs no password and is not
decryption in the password sense. AES comes from `cryptography` when present
(~90× faster, `syhwp[fast]`) and from a small bundled implementation otherwise,
checked against the FIPS 197 vector.

## HWPX format (`_hwpx.py`)

ZIP package (magic `PK\x03\x04`, mimetype `application/hwp+zip`). Content lives in
`Contents/section{N}.xml` as OWPML, parsed with the standard library (`zipfile` +
`xml.etree.ElementTree`) by matching elements on local name (namespace-agnostic):
`p` (paragraph), `t` (text run), `tbl`/`tr`/`tc` (table/row/cell), `caption`
(a table's title, hanging off `tbl` outside its rows and emitted as a paragraph
ahead of the table), `equation` (with `script`), `pic` (image). The document version comes from `version.xml`
(major.minor.micro.buildNumber).

## Roadmap

- Character-shape aware output (bold / italic from `DocInfo`).
- Hyperlinks as markdown links; richer HWPX object support.

## Non-goals

- Writing or editing HWP files (read-only).
- Pixel-perfect layout fidelity — this is content extraction.
- Decrypting password-protected documents (the password is not in the file).
- HWP 3.x and earlier (a different, pre-5.0 format).
