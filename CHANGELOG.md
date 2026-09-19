# Changelog

All notable changes to syhwp are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.0.8] — 2026-09-19

Text that lives outside top-level paragraphs, and distribution documents.

- **Distribution (copy-protected, 배포용) documents are read.** Their content
  sits in `ViewText` under AES-128 whose key the file carries in a masked header,
  so the flag asks editors not to edit rather than keeping a secret. HANCOM's own
  published HWP 5.0 specification is such a document: it now extracts 55,931
  characters and 166 tables. `syhwp[fast]` (or any `cryptography` install)
  decrypts ~90× faster than the bundled pure-Python AES; neither is required.

- **Text boxes, footnotes, endnotes, headers and footers are read.** The HWP 5.x
  emitter now walks a control's whole subtree instead of only its top-level
  paragraphs. Measured on a 2.2 MB annual report: all 3,326 of its characters sat
  under `gso` controls, so the document used to extract as empty.
- **Table captions are read**, in both formats — the caption is emitted as a
  paragraph ahead of its table. In HWP 5.x it was also being mistaken for a cell,
  which put it outside the grid and dropped it; in HWPX it was never visited.
  Equation and drawing captions come through the same way.
- A drawing reports itself as an `Image` only when it holds no text, so a text
  box no longer renders a `[그림]` placeholder in front of its own prose.
- `EncryptedDocumentError` now means "password-protected" only.

Measured over 85 public documents (60 government forms from the National Law
Information Center, 25 feature fixtures): before, 8 files extracted nothing and 7
more lost text; after, the only files that extract nothing are the two that hold
nothing but pictures and the three that are password- or distribution-locked, and
no file loses a run. Government forms — 182 tables, 6,862 cells — were unaffected,
which is the regression this set exists to catch.

## [0.0.7] — 2026-07-14

Discoverability and documentation.

- Expanded `README.md` (output example, supported-formats table, clearer
  positioning); added a Korean `README.ko.md` and status badges.
- Enriched PyPI metadata — keywords, classifiers, and a keyword-rich description
  — to improve search discoverability.

## [0.0.6] — 2026-07-14

Documentation and developer tooling (no library code changes).

- Rewrote `README.md` with an API reference; trimmed `DESIGN.md` to a clean
  format/architecture reference.
- Added a developer guide (`CLAUDE.md`), `CONTRIBUTING.md`, and this changelog.
- Added `scripts/inspect_hwp.py` and Claude Code skills (`inspect-sample`,
  `release`).

## [0.0.5] — 2026-07-14

Initial public release.

- HWP 5.x (legacy OLE binary) and HWPX (OWPML) reading in one library, with
  automatic format detection.
- Text, GFM Markdown (tables as pipe tables), and HTML output.
- Structured `Document` API: `paragraphs`, `tables`, `equations`, `version`;
  `Table` / `Cell` with `row_span` / `col_span`.
- Inline equations surfaced as their script; images as placeholders.
- Robust parsing: unknown records/elements skipped; malformed or corrupt input
  raises a typed `SyhwpError` (fuzz-tested) instead of crashing.
- CLI (`syhwp` / `python -m syhwp`) and a `py.typed` marker.
- Only runtime dependency: `olefile`. HWPX uses the standard library alone.

[Unreleased]: https://github.com/sysphere/syhwp/compare/v0.0.7...HEAD
[0.0.7]: https://github.com/sysphere/syhwp/releases/tag/v0.0.7
[0.0.6]: https://github.com/sysphere/syhwp/releases/tag/v0.0.6
[0.0.5]: https://github.com/sysphere/syhwp/releases/tag/v0.0.5
