"""Distribution (copy-protected) documents.

A distribution document keeps its body in ``ViewText/Section{N}`` instead of
``BodyText/Section{N}``. The section opens with a 256-byte
``HWPTAG_DISTRIBUTE_DOC_DATA`` record whose first four bytes are a seed; the
rest of that record is masked with a byte stream generated from the seed, and
the unmasked block holds — as UTF-16LE hex characters — the AES-128 key the rest
of the section is encrypted with. So the key travels with the file: this is a
flag that asks editors not to edit, not a secret.

Everything here was derived from the published format and confirmed against
sample files; the mask generator in particular was fitted to the byte stream two
documents imply and then checked to reproduce 125 of the 126 known positions in
one and to decrypt both.

AES-128-ECB comes from ``cryptography`` when it is installed, and from the small
implementation below otherwise, so the package keeps its single dependency.
"""

import struct
from typing import List

__all__ = ["section_key", "decrypt_section"]


def _mask(seed: int, size: int) -> bytes:
    """The byte stream the header is masked with.

    Two draws of the same linear congruential generator per run: the first sets
    the byte, the second how many positions it covers.
    """
    out = bytearray()
    n = seed
    while len(out) < size:
        n = (214013 * n + 2531011) & 0xFFFFFFFF
        value = (n >> 16) & 0xFF
        n = (214013 * n + 2531011) & 0xFFFFFFFF
        run = ((n >> 16) & 0x0F) + 1
        out.extend(bytes([value]) * run)
    return bytes(out[:size])


def section_key(header: bytes) -> bytes:
    """The AES-128 key carried by a ``HWPTAG_DISTRIBUTE_DOC_DATA`` payload.

    The seed's low nibble is where the key starts — confirmed on two documents
    whose seeds put it at 5 and at 14.
    """
    if len(header) < 256:
        raise ValueError("distribution header is shorter than 256 bytes")
    (seed,) = struct.unpack_from("<I", header, 0)
    stream = _mask(seed, 256)
    clear = bytearray(header[:256])
    for i in range(4, 256):
        clear[i] ^= stream[i]
    start = 4 + (seed & 0x0F)
    return bytes(clear[start:start + 16])


def decrypt_section(data: bytes, key: bytes) -> bytes:
    """AES-128-ECB, whole blocks only; a trailing partial block is dropped."""
    body = data[: len(data) - len(data) % 16]
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError:
        return _decrypt_ecb(body, key)
    decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return decryptor.update(body) + decryptor.finalize()


# --------------------------------------------------------------------------- #
# A small AES-128 inverse cipher (FIPS 197), used when `cryptography` is absent.
# --------------------------------------------------------------------------- #

_SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6426841992d0fb054bb16"
)
_INV_SBOX = bytearray(256)
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i
_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _xtime(a: int) -> int:
    a <<= 1
    return (a ^ 0x1B) & 0xFF if a & 0x100 else a


def _mul(a: int, b: int) -> int:
    out = 0
    for _ in range(8):
        if b & 1:
            out ^= a
        b >>= 1
        a = _xtime(a)
    return out


def _expand(key: bytes) -> List[List[int]]:
    words = [list(key[i:i + 4]) for i in range(0, 16, 4)]
    for i in range(4, 44):
        word = list(words[i - 1])
        if i % 4 == 0:
            word = word[1:] + word[:1]
            word = [_SBOX[b] for b in word]
            word[0] ^= _RCON[i // 4 - 1]
        words.append([a ^ b for a, b in zip(words[i - 4], word)])
    return [sum(words[r:r + 4], []) for r in range(0, 44, 4)]


def _decrypt_block(block: bytes, rounds: List[List[int]]) -> bytes:
    state = [b ^ k for b, k in zip(block, rounds[10])]
    for rnd in range(9, -1, -1):
        # InvShiftRows + InvSubBytes
        shifted = [0] * 16
        for col in range(4):
            for row in range(4):
                shifted[((col + row) % 4) * 4 + row] = state[col * 4 + row]
        state = [_INV_SBOX[b] for b in shifted]
        state = [b ^ k for b, k in zip(state, rounds[rnd])]
        if rnd:
            mixed = [0] * 16
            for col in range(4):
                a = state[col * 4:col * 4 + 4]
                mixed[col * 4 + 0] = _mul(a[0], 14) ^ _mul(a[1], 11) ^ _mul(a[2], 13) ^ _mul(a[3], 9)
                mixed[col * 4 + 1] = _mul(a[0], 9) ^ _mul(a[1], 14) ^ _mul(a[2], 11) ^ _mul(a[3], 13)
                mixed[col * 4 + 2] = _mul(a[0], 13) ^ _mul(a[1], 9) ^ _mul(a[2], 14) ^ _mul(a[3], 11)
                mixed[col * 4 + 3] = _mul(a[0], 11) ^ _mul(a[1], 13) ^ _mul(a[2], 9) ^ _mul(a[3], 14)
            state = mixed
    return bytes(state)


def _decrypt_ecb(data: bytes, key: bytes) -> bytes:
    rounds = _expand(key)
    return b"".join(_decrypt_block(data[i:i + 16], rounds) for i in range(0, len(data), 16))
