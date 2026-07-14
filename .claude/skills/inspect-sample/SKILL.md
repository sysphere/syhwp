---
name: inspect-sample
description: Dump the internal record/element structure of an HWP or HWPX file to understand or debug how syhwp parses it. Use when extending the parser (a new record, control id, or element) or when a document doesn't extract as expected.
---

# Inspect an HWP/HWPX sample

When adding support for a new HWP 5.x record / control id or a new HWPX element,
or when a document extracts incorrectly, look at its internal structure first.

1. Put the file in `tests/data/` (gitignored — never commit copyrighted docs).
2. Dump its structure:

       python scripts/inspect_hwp.py tests/data/<file>

   HWP5 output: version, header flags, streams, and per-section record-tag and
   control-id histograms. HWPX output: version, zip entries, and per-section
   element histograms.
3. Cross-reference the tags / control ids / elements against the format notes in
   `DESIGN.md` (record tag numbers, control ids, field offsets).
4. If a new record/control is involved, confirm its byte layout **empirically**
   (e.g. brute-force an offset against a known-shape sample, the way the table
   `LIST_HEADER` cell-address offset was established) before hard-coding offsets.
   Record the evidence in a code comment and update `DESIGN.md`.
5. Add a focused unit test (synthetic bytes) and, if the file is shareable, a
   corpus entry. Keep `pytest` green, including the fuzz tests.

Follow the clean-room rule (see `CLAUDE.md`): derive everything from the public
spec and your own analysis — never from `pyhwp` (AGPL).
