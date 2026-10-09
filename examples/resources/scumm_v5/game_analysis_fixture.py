"""Deterministic copyright-free two-room raw SCUMM v5 analysis fixture."""

from __future__ import annotations

import struct
import zipfile
from io import BytesIO

from .room_bundle_fixture import room1, room2

XOR_KEY = 0x69


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def _directory(rooms: bytes, offsets: list[int]) -> bytes:
    return struct.pack("<H", len(rooms)) + rooms + b"".join(
        struct.pack("<I", value) for value in offsets
    )


def _script(number: int, body: bytes) -> bytes:
    return _chunk(b"SCRP", body)


def _data_only_object(object_id: int, index: int) -> bytes:
    """An OBCD resource with ordinary metadata but no VERB program table."""
    header = struct.pack(
        "<HBBBBBBhhB", object_id, 1, 1, 1, 1, 0, 0,
        40 + index, 20 + index, 0,
    )
    return _chunk(b"OBCD", _chunk(b"CDHD", header))


def raw_pair(*, data_only_objects: int = 0,
             extra_global_scripts: int = 0,
             cross_bank_body_size: int = 0) -> tuple[bytes, bytes]:
    # Global 1 has an unconditional start, a conditional start, a direct room
    # transition, and a variable script selector. Global 2 contains a known-
        # width semantic-only debug command before a StartScript dependency, then an
    # unregistered byte to prove only genuine structural uncertainty stops it.
    globals_ = {
        1: bytes((0x0A, 2, 0xFF, 0x28, 0x45, 0xC0, 3, 0,
                  0x0A, 3, 0xFF, 0x6B, 1, 0,
                  0x72, 2, 0x8A, 0, 0, 0xFF, 0)),
        2: bytes((0x24, 0, 0, 1, 0, 0, 0, 0,
                  0x6B, 1, 0, 0x0A, 4, 0xFF,
        # ResourceRoutines LOAD_SOUND is structurally understood even though
        # its runtime semantics are not certified. The final unregistered
        # byte is genuine structural uncertainty.
                  0x0C, 2, 5, 0x2F, 0x72, 1, 0)),
        # Global 3 is conditionally started by Global 1. Its known-width,
        # semantically unsupported debug command must not hide the following
        # static StartScript dependency.
        3: bytes((0x6B, 1, 0, 0x0A, 4, 0xFF, 0)),
        # Global 4 is started by known global dependencies, yields, then
        # requests room 2. Operation presence makes its source identity a
        # possible cross-room continuation candidate; it does not prove that
        # a particular activation is live at the transition.
        4: bytes((0x80, 0x72, 2, 0x00)),
        # A known-width jump with a truncated word operand is malformed rather
        # than an unknown-width/unsupported decode.
        5: bytes((0x18,)),
    }
    if not 0 <= extra_global_scripts <= 194:
        raise ValueError("extra_global_scripts must fit the 200-slot fixture directory")
    for number in range(6, 6 + extra_global_scripts):
        globals_[number] = bytes((0xA0,))
    if cross_bank_body_size:
        if not 16 <= cross_bank_body_size <= 0x7FFF:
            raise ValueError("cross_bank_body_size must be in 16..32767")
        if extra_global_scripts < 2:
            raise ValueError("cross-bank fixture requires globals 6 and 7")
        # Reach the second-bank marker through SCUMM's normal dynamic global
        # resolver so the native test proves body fetch, not just placement.
        globals_[1] = bytes((0x0A, 7, 0xFF)) + globals_[1]
        # A large, valid instruction stream ending in stopScript instructions
        # fills the first body page. Global 7's state mutation then occupies a
        # distinct page and is executed by the bounded native fetch test.
        globals_[6] = bytes((0xA0,)) * (cross_bank_body_size - 1) + b"\x00"
        globals_[7] = bytes((0x1A, 200, 0, 0x5A, 0xA5, 0xA0))
    room1_container = bytearray(_chunk(b"ROOM", room1()))
    offsets = [0] * 200
    room_slots = bytearray(200)
    for number, body in globals_.items():
        offsets[number] = len(room1_container)
        room_slots[number] = 1
        room1_container.extend(_script(number, body))
    room2_source = room2(data_only_objects=data_only_objects)
    room2_container = _chunk(b"ROOM", room2_source)
    lflf1 = _chunk(b"LFLF", bytes(room1_container))
    lflf2 = _chunk(b"LFLF", room2_container)

    loff_size = 8 + 11
    first_header_offset = 8 + loff_size
    first_payload_offset = first_header_offset + 8
    second_header_offset = first_header_offset + len(lflf1)
    second_payload_offset = second_header_offset + 8
    loff = bytes((2, 1)) + struct.pack("<I", first_payload_offset) + bytes((2,)) + struct.pack(
        "<I", second_payload_offset
    )
    data_plain = _chunk(b"LECF", _chunk(b"LOFF", loff) + lflf1 + lflf2)

    object_count = 256
    dobj = struct.pack("<H", object_count) + bytes(object_count) + b"".join(
        struct.pack("<I", 0) for _ in range(object_count)
    )
    dscr = _directory(bytes(room_slots), offsets)
    dsou = _directory(b"", [])
    index_plain = _chunk(b"DOBJ", dobj) + _chunk(b"DSCR", dscr) + _chunk(b"DSOU", dsou)
    return (bytes(value ^ XOR_KEY for value in index_plain),
            bytes(value ^ XOR_KEY for value in data_plain))


def source_zip(*, data_only_objects: int = 0,
               extra_global_scripts: int = 0,
               cross_bank_body_size: int = 0) -> bytes:
    index, data = raw_pair(data_only_objects=data_only_objects,
                           extra_global_scripts=extra_global_scripts,
                           cross_bank_body_size=cross_bank_body_size)
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in (("fixture/ANALYSIS.000", index),
                              ("fixture/ANALYSIS.001", data)):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, payload)
    return output.getvalue()
