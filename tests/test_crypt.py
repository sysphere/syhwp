"""Distribution documents — the mask, the key, and the AES fallback."""

import struct

import pytest

from syhwp._crypt import _decrypt_ecb, _mask, decrypt_section, section_key


def _header(seed: int, key: bytes, prefix: int) -> bytes:
    """A 256-byte distribution header carrying `key` — built by masking, which
    is the same XOR the reader undoes."""
    clear = bytearray(256)
    struct.pack_into("<I", clear, 0, seed)
    clear[4 + prefix:4 + prefix + len(key)] = key
    stream = _mask(seed, 256)
    return bytes(clear[:4]) + bytes(b ^ s for b, s in zip(clear[4:], stream[4:]))


def test_key_starts_at_the_seed_low_nibble():
    """Confirmed on two documents whose seeds put the key at 5 and at 14."""
    key = "E53741D8".encode("utf-16-le")
    assert section_key(_header(0x675B87E5, key, 5)) == key
    assert section_key(_header(0x5BF764BE, key, 14)) == key


def test_a_short_header_is_refused():
    with pytest.raises(ValueError):
        section_key(b"\x00" * 64)


def test_mask_matches_the_stream_a_document_implies():
    """The generator is fitted, so it is pinned to a value, not to itself.

    This stream is the one the sample with seed 0x675B87E5 requires: fitting it
    is what makes that document — and a second one with a different seed —
    decrypt into records that parse. Deriving the expectation from `_mask` would
    make the test agree with any generator, including a wrong one.
    """
    assert _mask(0x675B87E5, 32).hex() == (
        "db9292929292929292929292929292777777777777565656f3f3f3f3f3f3f3f3"
    )


def test_aes128_matches_the_published_vector():
    """FIPS 197, appendix C.1 — the fallback has to be right, not merely present."""
    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    cipher = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    assert _decrypt_ecb(cipher, key).hex() == "00112233445566778899aabbccddeeff"


def test_both_backends_agree():
    cryptography = pytest.importorskip("cryptography")
    del cryptography
    key = bytes(range(16))
    data = bytes((i * 7) % 256 for i in range(64))
    assert decrypt_section(data, key) == _decrypt_ecb(data, key)


def test_a_partial_trailing_block_is_dropped():
    key = bytes(range(16))
    assert len(decrypt_section(bytes(20), key)) == 16
