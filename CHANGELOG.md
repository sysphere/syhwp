# Changelog

All notable changes to syhwp are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
