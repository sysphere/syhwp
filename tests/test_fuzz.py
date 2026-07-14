"""Robustness: malformed input must raise SyhwpError (or degrade), never crash
with an arbitrary exception."""

import os
import random
import zipfile

import pytest

import syhwp
from syhwp import SyhwpError

_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP = b"PK\x03\x04"


def _write(tmp_path, name, data) -> str:
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def test_random_bytes_unsupported(tmp_path):
    p = _write(tmp_path, "r.bin", b"\x01\x02\x03\x04 not a document at all")
    with pytest.raises(SyhwpError):
        syhwp.open(p)


def test_ole_magic_but_garbage(tmp_path):
    p = _write(tmp_path, "g.hwp", _OLE + os.urandom(1024))
    with pytest.raises(SyhwpError):
        syhwp.open(p)


def test_zip_magic_but_garbage(tmp_path):
    p = _write(tmp_path, "g.hwpx", _ZIP + b"\x00" * 1024)
    with pytest.raises(SyhwpError):
        syhwp.open(p)


def test_empty_zip_is_graceful(tmp_path):
    p = tmp_path / "empty.hwpx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
    doc = syhwp.open(str(p))  # valid zip, no sections -> empty document
    assert doc.format == "hwpx"
    assert doc.blocks == []
    assert doc.text == "" and doc.markdown == ""


def test_fuzz_never_raises_unexpected(tmp_path):
    rnd = random.Random(20260714)
    magics = [b"", _OLE, _ZIP, b"HWP Document File"]
    for i in range(300):
        blob = rnd.choice(magics) + bytes(
            rnd.randrange(256) for _ in range(rnd.randrange(0, 400))
        )
        p = _write(tmp_path, f"f{i}.bin", blob)
        try:
            syhwp.extract_text(p)
            syhwp.extract_markdown(p)
        except SyhwpError:
            pass  # the only acceptable failure mode
