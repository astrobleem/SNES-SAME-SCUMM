"""Copyright-free, generated raw SCUMM v5 room source for compiler tests.

The fixture is intentionally mechanical: room 1 conditionally mutates an
object, starts LSCR 200, and transitions to room 2.  Object 100 has two
independent verb entrypoints; room 2 proves the cooked result reaches the
existing host interpreter.
"""

from __future__ import annotations

import struct


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def _background() -> bytes:
    strip = bytes((1,)) + bytes(range(16))
    smap = _chunk(b"SMAP", struct.pack("<I", 12) + strip)
    rmim = _chunk(b"RMIM", _chunk(b"RMIH", b"\0\0") + _chunk(b"IM00", smap))
    return _chunk(b"CLUT", bytes(value for color in range(256) for value in (color,) * 3)) + rmim


def _room_shell(object_count: int, *children: bytes) -> bytes:
    boxes = (
        struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255),
        struct.pack("<hhhhhhhhBBH", 0, 0, 7, 0, 7, 1, 0, 1, 0, 0, 255),
    )
    boxd = _chunk(b"BOXD", struct.pack("<H", len(boxes)) + b"".join(boxes))
    boxm = _chunk(b"BOXM", b"\0\0\0\xff\1\1\1\xff")
    return b"".join((
        _chunk(b"RMHD", struct.pack("<HHH", 8, 2, object_count)),
        _background(), boxd, boxm, *children,
    ))


def _object_100() -> bytes:
    header = struct.pack("<HBBBBBBhhB", 100, 1, 1, 1, 1, 0, 0, 4, 1, 0)
    programs = (
        (10, bytes((0x07, 100, 0, 5, 0))),
        (11, bytes((0x0A, 200, 0xFF, 0))),
        (0xFF, bytes((0x00,))),
    )
    table_length = 3 * len(programs) + 1
    next_offset = 8 + table_length
    entries = []
    bodies = []
    for verb, body in programs:
        entries.append(bytes((verb,)) + struct.pack("<H", next_offset))
        bodies.append(body)
        next_offset += len(body)
    table = b"".join(entries) + b"\0"
    return _chunk(b"OBCD", _chunk(b"CDHD", header) + _chunk(b"VERB", table + b"".join(bodies)))


def room1() -> bytes:
    # If bit 69 is zero, execute setState(100, 1); both paths then start the
    # local script and request room 2.  The branch target is a real boundary.
    entry = bytes((
        0x28, 0x45, 0x80, 0x04, 0x00,
        0x07, 100, 0, 1,
        0x37, 100, 0, 10, 0xFF,
        0x0A, 200, 0xFF,
        0x72, 2,
        0x00,
    ))
    exit_script = bytes((0x07, 100, 0, 3, 0x00))
    local = bytes((0x07, 100, 0, 2, 0x72, 2, 0x00))
    return _room_shell(
        1,
        _object_100(),
        _chunk(b"ENCD", entry),
        _chunk(b"EXCD", exit_script),
        _chunk(b"LSCR", bytes((200,)) + local),
    )


def room2() -> bytes:
    entry = bytes((0x07, 100, 0, 4, 0x00))
    return _room_shell(0, _chunk(b"ENCD", entry), _chunk(b"EXCD", b"\0"))


def source_rooms() -> dict[int, bytes]:
    return {1: room1(), 2: room2()}
