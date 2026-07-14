# Contributing to syhwp

Thanks for your interest! syhwp is a pure-Python reader for Korean HWP 5.x and
HWPX documents.

## Development setup

```bash
git clone https://github.com/sysphere/syhwp
cd syhwp
pip install -e ".[test]"
pytest -q
```

## The clean-room rule (important)

syhwp is MIT-licensed only because it is a clean-room implementation of HANCOM's
**public** HWP 5.0 / OWPML specifications. Please:

- Implement from the spec and your own analysis of sample files.
- **Do not read or copy from `pyhwp`** (AGPL-3.0) — that would void the license.
- Do not port code from Apache-licensed projects (`hwp.js`, `hwp-rs`); consult
  them for behaviour cross-checks only.

## Adding format support

1. Put a sample document in `tests/data/` (gitignored — never commit copyrighted
   files) and dump its structure:

   ```bash
   python scripts/inspect_hwp.py tests/data/<file>
   ```

2. Cross-reference the tags / control ids / elements against `DESIGN.md`.
3. Confirm any new byte offsets empirically before hard-coding them.
4. Add tests: synthetic-byte unit tests, plus a corpus entry if you can share the
   file. Keep `pytest` green — including the fuzz tests (malformed input must
   never crash).

## Style

- Pure Python 3.9+; one runtime dependency (`olefile`); HWPX uses stdlib only.
- Keep the public surface in `syhwp/__init__.__all__`; internal modules are
  `_`-prefixed.

## Reporting bugs

Include the syhwp version, your Python version, and — if the document can be
shared — a minimal sample. Otherwise the output of
`python scripts/inspect_hwp.py <file>` is very helpful.
