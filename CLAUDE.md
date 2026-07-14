# syhwp — developer guide

Pure-Python reader for Korean **HWP 5.x** and **HWPX** documents → text, Markdown,
HTML. MIT-licensed. See `README.md` for usage and `DESIGN.md` for the file-format
internals (record tags, control ids, byte offsets).

## ⚠️ The one rule that must never be broken: clean-room provenance

syhwp can be MIT-licensed *only* because it is a clean-room implementation of
HANCOM's **public** HWP 5.0 / OWPML specifications.

- Implement from the spec and your own analysis of sample files
  (`python scripts/inspect_hwp.py FILE`).
- **Never read or copy from `pyhwp`** — it is AGPL-3.0. Deriving from it would
  make syhwp a derivative work and void the MIT license.
- Apache-licensed projects (`hwp.js`, `hwp-rs`) may be consulted for behaviour
  cross-checks only; do not port their code (that pulls in Apache-2.0 + NOTICE
  obligations). Work from the spec.
- When adding a record/control, note the spec section or the empirical evidence
  in a code comment or the commit message.

## Commands

    pip install -e ".[test]"             # dev install (only runtime dep: olefile)
    pytest -q                            # run the test suite
    python scripts/inspect_hwp.py FILE   # dump a file's internal structure
    python -m syhwp FILE --markdown      # try extraction from the CLI
    uv build                             # build wheel + sdist

Real sample documents go in `tests/data/` — **gitignored**, never commit
copyrighted files. `tests/test_corpus.py` runs over whatever is there and skips
in CI.

## Architecture

    src/syhwp/
      __init__.py   public API: detect_format / open / extract_text|markdown|html
      models.py     Document, Paragraph, Table, Cell, Equation, Image
      _records.py   HWP5 record iterator
      _hwp5.py      HWP5 (OLE) reader
      _hwpx.py      HWPX (OWPML) reader
      _markdown.py  GFM table rendering
      __main__.py   CLI

`open(path)` detects the format by magic bytes and returns a `Document` (an
ordered list of `Paragraph` / `Table` / `Equation` / `Image` blocks). The
`extract_*` helpers render it to text / markdown / HTML.

## Conventions

- Pure Python 3.9+ — use `typing.List` / `Optional`, not `X | Y`. One runtime
  dependency (`olefile`); HWPX uses the standard library only.
- **Robustness first**: skip unknown records/elements and never crash on
  malformed input — raise a `SyhwpError` subclass instead. Keep the fuzz tests
  (`tests/test_fuzz.py`) passing.
- Public API lives in `__init__.__all__`; internal modules are `_`-prefixed.
- When you nail down a new byte offset, confirm it empirically (e.g. brute-force
  against a known-shape sample, as the table `LIST_HEADER` offset was) rather than
  guessing, and document it in `DESIGN.md`.

## Skills

- `inspect-sample` — inspect a sample file's internal structure when extending
  the parser or debugging extraction.
- `release` — cut a new PyPI release (version bump → tag → trusted publishing).

## Release (summary)

Bump the version in **both** `pyproject.toml` and `src/syhwp/__init__.py`, commit,
then push a `vX.Y.Z` tag. `.github/workflows/publish.yml` publishes to PyPI via
trusted publishing (OIDC — no token). The job needs `permissions: id-token: write`
**and** `contents: read` (checkout fails on a private repo without the latter).
See the `release` skill for the full checklist.
