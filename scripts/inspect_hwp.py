#!/usr/bin/env python3
"""Dump the internal structure of an HWP 5.x or HWPX file.

A debugging aid for extending syhwp: shows the streams / records / control ids
(HWP5) or zip entries / element histograms (HWPX) so you can see how a document
is built before adding parser support for it.

    python scripts/inspect_hwp.py FILE
"""

import re
import struct
import sys
import zlib
from collections import Counter

_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP = b"PK\x03\x04"


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def inspect_hwp5(path: str) -> None:
    import olefile

    from syhwp._records import iter_records

    ole = olefile.OleFileIO(path)
    try:
        fh = ole.openstream("FileHeader").read()
        (ver,) = struct.unpack_from("<I", fh, 32)
        (flags,) = struct.unpack_from("<I", fh, 36)
        print("format:  hwp5")
        print(
            "version: %d.%d.%d.%d"
            % ((ver >> 24) & 0xFF, (ver >> 16) & 0xFF, (ver >> 8) & 0xFF, ver & 0xFF)
        )
        print(
            "flags:   0x%x (compressed=%d password=%d distribution=%d)"
            % (flags, flags & 1, (flags >> 1) & 1, (flags >> 2) & 1)
        )
        print("streams:")
        for entry in ole.listdir():
            print("  ", "/".join(entry))

        compressed = bool(flags & 1)
        for entry in ole.listdir():
            if len(entry) == 2 and entry[0] == "BodyText":
                raw = ole.openstream(entry).read()
                data = zlib.decompress(raw, -15) if compressed else raw
                recs = list(iter_records(data))
                tags = Counter(t for t, _lv, _p in recs)
                ctrls = Counter(
                    p[:4][::-1].decode("latin1", "replace")
                    for t, _lv, p in recs
                    if t == 71 and len(p) >= 4  # CTRL_HEADER
                )
                print("\n%s — %d records" % ("/".join(entry), len(recs)))
                print("  tag histogram:", dict(sorted(tags.items())))
                print("  control ids:  ", dict(ctrls))
    finally:
        ole.close()


def inspect_hwpx(path: str) -> None:
    import xml.etree.ElementTree as ET
    import zipfile

    with zipfile.ZipFile(path) as z:
        print("format:  hwpx")
        try:
            a = ET.fromstring(z.read("version.xml")).attrib
            print(
                "version: "
                + ".".join(a.get(k, "?") for k in ("major", "minor", "micro", "buildNumber"))
            )
        except (KeyError, ET.ParseError):
            pass
        print("entries:")
        for name in z.namelist():
            print("  ", name)
        for name in sorted(z.namelist()):
            if re.search(r"section\d+\.xml$", name, re.IGNORECASE):
                root = ET.fromstring(z.read(name))
                tags = Counter(_local(e.tag) for e in root.iter())
                print("\n%s element histogram:" % name, dict(sorted(tags.items())))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/inspect_hwp.py FILE", file=sys.stderr)
        return 2
    path = sys.argv[1]
    with open(path, "rb") as f:
        head = f.read(8)
    if head.startswith(_OLE):
        inspect_hwp5(path)
    elif head.startswith(_ZIP):
        inspect_hwpx(path)
    else:
        print("not an HWP or HWPX file", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
