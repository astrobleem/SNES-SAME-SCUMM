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
VERSION = 2
HEADER = struct.Struct("<8sHHBB" + "H" * 18 + "32s")
MAX_ACTIVE_BYTES = 0x1000
MAX_PENDING_BYTES = 0x0C3C  # Packed SA-1 backend allocation, after renderer/live-room state.
OBJECT = struct.Struct("<HhhhhB")
NAME_LENGTH = struct.Struct("<B")
SOURCE_OBJECT_WALK = struct.Struct("<HhhBhhB")
OBJECT_WALK = struct.Struct("<hhBhhB")
PORTAL = struct.Struct("<Bhhh")
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
    object_names: tuple[tuple[int, bytes], ...]
    portal_indices: tuple[int | None, ...]
    portal_records: tuple[bytes, ...]
    payload: bytes
    source_room_sha256: str
    crc32: int
    sha256: str


def _checked_u16(value: int, what: str) -> int:
    if isinstance(value, bool) or not 0 <= value <= 0xFFFF:
        raise ResourceError(f"live room {what} does not fit u16")
    return value


def _encode_portal_directory(dense: bytes, box_count: int, room: int) -> bytes:
    """Pack the dense compiler projection into a sparse pair directory.

    Each pair keeps a u16 portal-record index (FFFF means no shared edge).
    Only nonempty seven-byte portal descriptors follow the index matrix.
    """
    pair_count = box_count * box_count
    if len(dense) != pair_count * PORTAL.size:
        raise ResourceError(f"room {room} portal table geometry differs")
    indices: list[int] = []
    records = bytearray()
    portal_count = 0
    for offset in range(0, len(dense), PORTAL.size):
        record = dense[offset:offset + PORTAL.size]
        kind, fixed, low, high = PORTAL.unpack(record)
        if kind == 0:
            if fixed or low or high:
                raise ResourceError(f"room {room} has noncanonical empty portal data")
            indices.append(0xFFFF)
            continue
        if kind not in (1, 2):
            raise ResourceError(f"room {room} has unsupported portal kind {kind}")
        indices.append(portal_count)
        portal_count += 1
        records.extend(record)
    return b"".join(struct.pack("<H", index) for index in indices) + bytes(records)


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
    for index, (object_id, value) in enumerate(name_rows):
        source_object_id = OBJECT.unpack_from(objects, index * OBJECT.size)[0]
        if int(object_id) != source_object_id:
            raise ResourceError(
                f"room {room} object-name row {index} does not match its object record"
            )
        raw_name = bytes(value).split(b"\0", 1)[0][:32]
        names.extend(NAME_LENGTH.pack(len(raw_name)))
        names.extend(raw_name)

    source_object_walk = bytes(record["object_walk"])
    if len(source_object_walk) != object_count * SOURCE_OBJECT_WALK.size:
        raise ResourceError(f"room {room} object-walk table count differs")
    object_walk_rows = bytearray()
    for index in range(object_count):
        source_row = SOURCE_OBJECT_WALK.unpack_from(
            source_object_walk, index * SOURCE_OBJECT_WALK.size,
        )
        object_id = OBJECT.unpack_from(objects, index * OBJECT.size)[0]
        if source_row[0] != object_id:
            raise ResourceError(
                f"room {room} object-walk row {index} does not match its object record"
            )
        object_walk_rows.extend(OBJECT_WALK.pack(*source_row[1:]))
    object_walk = bytes(object_walk_rows)
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
    portals = _encode_portal_directory(bytes(record["portals"]), box_count, room)

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
    if len(body) > MAX_PENDING_BYTES:
        raise ResourceError(
            f"room {room} live metadata is {len(body)} bytes; audited pending room buffer "
            f"is {MAX_PENDING_BYTES} bytes"
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
    lengths = (box_count, box_count * 18, box_count * box_count)
    expected = HEADER.size
    decoded_offsets: dict[str, int] = {}
    for name, offset, length in zip(names[:3], offsets_raw[:3], lengths):
        if offset != expected or offset + length > total_size:
            raise ResourceError(f"live room {name} table is out of bounds or noncanonical")
        decoded_offsets[name] = offset
        expected += length

    portals_offset, objects_offset = offsets_raw[3:5]
    portal_index_bytes = box_count * box_count * 2
    portal_values_offset = portals_offset + portal_index_bytes
    if (portals_offset != expected or portal_values_offset > objects_offset
            or objects_offset + object_count * OBJECT.size > total_size):
        raise ResourceError("live room portal directory is out of bounds or noncanonical")
    portal_value_bytes = objects_offset - portal_values_offset
    if portal_value_bytes % PORTAL.size:
        raise ResourceError("live room sparse portal payload has a partial record")
    portal_count = portal_value_bytes // PORTAL.size
    portal_indices: list[int | None] = []
    for index in range(box_count * box_count):
        value = struct.unpack_from("<H", data, portals_offset + index * 2)[0]
        if value == 0xFFFF:
            portal_indices.append(None)
        elif value >= portal_count:
            raise ResourceError("live room portal index exceeds sparse portal records")
        else:
            portal_indices.append(value)
    portal_records = tuple(
        bytes(data[portal_values_offset + index * PORTAL.size:
                   portal_values_offset + (index + 1) * PORTAL.size])
        for index in range(portal_count)
    )
    decoded_offsets["portals"] = portals_offset
    decoded_offsets["objects"] = objects_offset
    expected = objects_offset + object_count * OBJECT.size

    names_offset, object_walk_offset = offsets_raw[5:7]
    if names_offset != expected or not names_offset <= object_walk_offset <= total_size:
        raise ResourceError("live room names table is out of bounds or noncanonical")
    decoded_offsets["names"] = names_offset
    object_names: list[tuple[int, bytes]] = []
    cursor = names_offset
    seen_object_ids: set[int] = set()
    for index in range(object_count):
        if cursor + NAME_LENGTH.size > object_walk_offset:
            raise ResourceError("live room object-name row is truncated")
        object_id = struct.unpack_from(
            "<H", data, offsets_raw[4] + index * OBJECT.size,
        )[0]
        name_length = NAME_LENGTH.unpack_from(data, cursor)[0]
        cursor += NAME_LENGTH.size
        if object_id in seen_object_ids:
            raise ResourceError(f"live room object-name ID {object_id} is duplicated")
        if name_length > 32 or cursor + name_length > object_walk_offset:
            raise ResourceError("live room object-name length exceeds its table")
        object_names.append((object_id, bytes(data[cursor:cursor + name_length])))
        seen_object_ids.add(object_id)
        cursor += name_length
    if cursor != object_walk_offset:
        raise ResourceError("live room object-name table has unclaimed bytes")
    expected = object_walk_offset
    decoded_offsets["object_walk"] = object_walk_offset

    lengths = (object_count * OBJECT_WALK.size, verb_count * VERB.size,
               local_count * LOCAL.size, bundle_count * 2)
    for name, offset, length in zip(
            names[6:], offsets_raw[6:],
            (object_count * OBJECT_WALK.size, verb_count * VERB.size,
             local_count * LOCAL.size, bundle_count * 2)):
        if offset != expected or offset + length > total_size:
            raise ResourceError(f"live room {name} table is out of bounds or noncanonical")
        decoded_offsets[name] = offset
        expected += length
    if expected != total_size:
        raise ResourceError("live room has unclaimed trailing bytes")
    return LiveRoomRecord(
        room, flags, box_count, object_count, verb_count, local_count, bundle_count,
        entry, exit_, decoded_offsets, tuple(object_names), tuple(portal_indices),
        portal_records, bytes(data), source_hash.hex(),
        zlib.crc32(data) & 0xFFFFFFFF, hashlib.sha256(data).hexdigest(),
    )
