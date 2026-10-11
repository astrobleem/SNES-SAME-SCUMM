"""Compiler-owned, source-neutral live room tables for external providers.

This is a serialization of the already parsed RoomIR/backend projection, not a
second SCUMM ROOM parser.  The native engine consumes this bounded record for
the live table consumers that historically read generated ROM tables.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Mapping, Sequence
import zlib

from ...errors import ResourceError


MAGIC = b"SC5LIVE\0"
VERSION = 1
HEADER = struct.Struct("<8sHHBB" + "H" * 18 + "32s")
MAX_ACTIVE_BYTES = 0x0A00  # Largest accepted record, bounded by the audited pending buffer.
OBJECT = struct.Struct("<HhhhhB")
NAME = struct.Struct("<H32s")
OBJECT_WALK = struct.Struct("<HhhBhhB")
VERB = struct.Struct("<HHHH")
LOCAL = struct.Struct("<BH")


@dataclass(frozen=True, slots=True)
class LiveRoomRecord:
    room: int
    flags: int
    box_count: int
    object_count: int
    verb_count: int
    local_count: int
    bundle_count: int
    entry_program_unit: int
    exit_program_unit: int
    offsets: Mapping[str, int]
    payload: bytes
    source_room_sha256: str
    crc32: int
    sha256: str


def _checked_u16(value: int, what: str) -> int:
    if isinstance(value, bool) or not 0 <= value <= 0xFFFF:
        raise ResourceError(f"live room {what} does not fit u16")
    return value


def encode_live_room(record: Mapping[str, object], *, program_units: Sequence[Mapping[str, object]]) -> bytes:
    """Serialize cooked backend tables while preserving source identities.

    ``program_units`` contains the room's selector-bearing carriers.  The
    assigned compiler IDs are directory identities; no runtime selector is
    emitted here.
    """
    room = int(record["room"])
    if not 0 <= room <= 255:
        raise ResourceError("live room identity does not fit u8")
    room_flags = int(record.get("flags", 0))
    if room_flags & ~0x01:
        raise ResourceError(f"room {room} has unsupported cooked-room flags")
    room_units = [row for row in program_units if row.get("room") == room]
    identity_to_id = {
        str(row["unit_identity"] if row.get("unit_identity") is not None else row["identity"]): int(row["id"])
        for row in room_units if row.get("id") is not None
    }
    if len(identity_to_id) != len(room_units):
        raise ResourceError(f"room {room} has duplicate executable carrier identities")

    objects = bytes(record["objects"])
    if len(objects) % OBJECT.size:
        raise ResourceError(f"room {room} object table has a partial record")
    object_count = len(objects) // OBJECT.size
    names = bytearray()
    name_rows = tuple(record["object_names"])
    if len(name_rows) != object_count:
        raise ResourceError(f"room {room} object-name count differs from object records")
    for object_id, value in name_rows:
        raw_name = bytes(value)[:32]
        names.extend(NAME.pack(_checked_u16(int(object_id), "object ID"), raw_name.ljust(32, b"\0")))

    object_walk = bytes(record["object_walk"])
    if len(object_walk) != object_count * OBJECT_WALK.size:
        raise ResourceError(f"room {room} object-walk table count differs")
    box_flags = bytes(record["walkbox_flags"])
    box_count = len(box_flags)
    if object_count > 0xFF or box_count > 0xFF:
        raise ResourceError(f"room {room} exceeds the native u8 object/walkbox count")
    geometry = bytes(record["walkbox_geometry"])
    if len(geometry) != box_count * 18:
        raise ResourceError(f"room {room} walkbox geometry count differs")
    routes = bytes(record["box_routes"])
    if len(routes) != box_count * box_count:
        raise ResourceError(f"room {room} movement matrix is not square")
    portals = bytes(record["portals"])
    if len(portals) != box_count * box_count * 7:
        raise ResourceError(f"room {room} portal table geometry differs")

    verbs = bytearray()
    for object_program in record["object_programs"]:
        if not isinstance(object_program, Mapping) or not object_program.get("executable"):
            continue
        unit_id = object_program.get("id")
        if unit_id is None:
            raise ResourceError(f"room {room} executable object carrier has no ProgramUnit ID")
        carrier_identity = str(object_program["unit_identity"])
        if identity_to_id.get(carrier_identity) != int(unit_id):
            raise ResourceError(f"room {room} object carrier directory identity differs")
        object_id = int(object_program["number"])
        for verb_id, entry_offset in object_program.get("entrypoints", ()):
            verbs.extend(VERB.pack(
                _checked_u16(object_id, "verb object ID"),
                _checked_u16(int(verb_id), "verb ID"),
                _checked_u16(int(entry_offset), "verb entry offset"),
                _checked_u16(int(unit_id), "object ProgramUnit ID"),
            ))

    locals_rows = []
    for item in record["executable_locals"]:
        if item.get("id") is None:
            raise ResourceError(f"room {room} executable local has no ProgramUnit ID")
        number = int(item["number"])
        if not 0 <= number <= 255:
            raise ResourceError(f"room {room} local script number does not fit u8")
        locals_rows.append((number, int(item["id"])))
    locals_rows.sort()
    locals_data = b"".join(LOCAL.pack(number, _checked_u16(unit, "local ProgramUnit ID"))
                            for number, unit in locals_rows)

    bundle_ids = sorted(int(row["id"]) for row in room_units)
    bundle_data = b"".join(struct.pack("<H", _checked_u16(value, "bundle ProgramUnit ID"))
                            for value in bundle_ids)
    entry = int(record.get("entry", 0xFFFF))
    exit_ = int(record.get("exit", 0xFFFF))
    for label, value in (("entry", entry), ("exit", exit_)):
        if value != 0xFFFF and value not in bundle_ids:
            raise ResourceError(f"room {room} {label} ProgramUnit is absent from its bundle")

    sections = (
        ("flags", box_flags), ("geometry", geometry), ("routes", routes),
        ("portals", portals), ("objects", objects), ("names", bytes(names)),
        ("object_walk", object_walk), ("verbs", bytes(verbs)),
        ("locals", locals_data), ("bundles", bundle_data),
    )
    offsets: dict[str, int] = {}
    body = bytearray(HEADER.size)
    for name, data in sections:
        offsets[name] = len(body)
        body.extend(data)
    if len(body) > MAX_ACTIVE_BYTES:
        raise ResourceError(
            f"room {room} live metadata is {len(body)} bytes; audited active room buffer "
            f"is {MAX_ACTIVE_BYTES} bytes"
        )
    source_raw = bytes(record["raw"])
    source_hash = hashlib.sha256(source_raw).digest()
    header = HEADER.pack(
        MAGIC, VERSION, HEADER.size, room, room_flags,
        box_count, object_count, len(verbs) // VERB.size, len(locals_rows),
        len(bundle_ids), entry, exit_,
        *(offsets[name] for name, _ in sections), len(body), source_hash,
    )
    body[:HEADER.size] = header
    return bytes(body)


def decode_live_room(data: bytes, *, expected_room: int | None = None) -> LiveRoomRecord:
    if len(data) < HEADER.size:
        raise ResourceError("live room record is truncated")
    values = HEADER.unpack_from(data)
    magic, version, header_size, room, flags = values[:5]
    if magic != MAGIC or version != VERSION or header_size != HEADER.size or flags & ~0x01:
        raise ResourceError("live room identity, schema, or flags differ")
    if expected_room is not None and room != expected_room:
        raise ResourceError("live room canonical room identity differs")
    counts = tuple(int(value) for value in values[5:12])
    box_count, object_count, verb_count, local_count, bundle_count, entry, exit_ = counts
    offsets_raw = tuple(int(value) for value in values[12:22])
    total_size = int(values[22])
    source_hash = values[23]
    if total_size != len(data) or total_size > MAX_ACTIVE_BYTES:
        raise ResourceError("live room length exceeds its validated active-resource range")
    if source_hash == bytes(32):
        raise ResourceError("live room provenance identity is empty")
    names = ("flags", "geometry", "routes", "portals", "objects", "names",
             "object_walk", "verbs", "locals", "bundles")
    lengths = (box_count, box_count * 18, box_count * box_count,
               box_count * box_count * 7, object_count * OBJECT.size,
               object_count * NAME.size, object_count * OBJECT_WALK.size,
               verb_count * VERB.size, local_count * LOCAL.size,
               bundle_count * 2)
    expected = HEADER.size
    decoded_offsets: dict[str, int] = {}
    for name, offset, length in zip(names, offsets_raw, lengths):
        if offset != expected or offset + length > total_size:
            raise ResourceError(f"live room {name} table is out of bounds or noncanonical")
        decoded_offsets[name] = offset
        expected += length
    if expected != total_size:
        raise ResourceError("live room has unclaimed trailing bytes")
    return LiveRoomRecord(
        room, flags, box_count, object_count, verb_count, local_count, bundle_count,
        entry, exit_, decoded_offsets, bytes(data), source_hash.hex(),
        zlib.crc32(data) & 0xFFFFFFFF, hashlib.sha256(data).hexdigest(),
    )
