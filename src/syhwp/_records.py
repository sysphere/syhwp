"""HWP 5.x record stream iteration.

A record stream (e.g. a decompressed ``BodyText/Section{N}``) is a flat sequence
of records. Each record starts with a little-endian uint32 header:

    bits 0..9   (10 bits)  tag id
    bits 10..19 (10 bits)  nesting level
    bits 20..31 (12 bits)  payload size

If the size field is ``0xFFF`` the true size is stored in the following uint32
(records larger than 4095 bytes). Unknown tags are yielded like any other and
left to the caller to skip.
"""

import struct
from typing import Iterator, Tuple

_HDR = struct.Struct("<I")


def iter_records(buf: bytes) -> Iterator[Tuple[int, int, bytes]]:
    """Yield ``(tag, level, payload)`` for each record in ``buf``.

    Iteration stops cleanly if the buffer ends mid-record (truncated/corrupt
    stream) rather than raising.
    """
    i, n = 0, len(buf)
    while i + 4 <= n:
        (header,) = _HDR.unpack_from(buf, i)
        i += 4
        tag = header & 0x3FF
        level = (header >> 10) & 0x3FF
        size = (header >> 20) & 0xFFF
        if size == 0xFFF:
            if i + 4 > n:
                break
            (size,) = _HDR.unpack_from(buf, i)
            i += 4
        if i + size > n:
            # truncated payload — surface what we can, then stop.
            yield tag, level, buf[i:n]
            break
        yield tag, level, buf[i:i + size]
        i += size
