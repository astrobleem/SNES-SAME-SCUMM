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
VERSION = 3
SECTIONED_VERSION = 4
HEADER = struct.Struct("<8sHHBB" + "H" * 18 + "32s")
MAX_ACTIVE_BYTES = 0x1800  # Audited 41:E800-FFFF metadata alias in live-resource builds.
MAX_SOURCE_RECORD_BYTES = 0xFFFF
MAX_PENDING_BYTES = 0x0C3C  # Packed SA-1 backend allocation, after renderer/live-room state.
MAX_LIVE_RECORD_BYTES = MAX_SOURCE_RECORD_BYTES
LIVE_ROOM_CHUNK_BYTES = 0x0800  # Checked MSU read quantum for oversized live records.
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
    section_sizes: Mapping[str, int]
    object_names: tuple[tuple[int, bytes], ...]
    portal_indices: tuple[int | None, ...]
    portal_records: tuple[bytes, ...]
    payload: bytes
    source_room_sha256: str
    crc32: int
    sha256: str
    route_matrix: bytes = b""


def _checked_u16(value: int, what: str) -> int:
    if isinstance(value, bool) or not 0 <= value <= 0xFFFF:
        raise ResourceError(f"live room {what} does not fit u16")
    return value


def _validate_route_values(routes: bytes, box_count: int, *, room: int) -> None:
    """SCUMM BOXM cells are walkbox indices; 0xFF means no route."""
    if len(routes) != box_count * box_count:
        raise ResourceError(f"room {room} movement matrix is not square")
    if box_count == 0:
        return
    for index in range(0, len(routes), box_count):
        source = index // box_count
        _validate_route_row(
            routes[index:index + box_count], box_count, room=room, source=source,
        )


def _validate_route_row(routes: bytes, box_count: int, *, room: int, source: int) -> None:
    for index, value in enumerate(routes):
        if value != 0xFF and value >= box_count:
            raise ResourceError(
                f"room {room} BOXM route {source}->{index} names "
                f"walkbox {value}, outside 0..{box_count - 1}"
            )


def _encode_portal_directory(dense: bytes, box_count: int, room: int) -> bytes:
    """Encode v3 sorted sparse pairs and deduplicated portal descriptors."""
    pair_count = box_count * box_count
    if len(dense) != pair_count * PORTAL.size:
        raise ResourceError(f"room {room} portal table geometry differs")
    descriptors: list[bytes] = []
    descriptor_ids: dict[bytes, int] = {}
    pairs: list[tuple[int, int]] = []
    for offset in range(0, len(dense), PORTAL.size):
        record = dense[offset:offset + PORTAL.size]
        kind, fixed, low, high = PORTAL.unpack(record)
        if kind == 0:
            if fixed or low or high:
                raise ResourceError(f"room {room} has noncanonical empty portal data")
            continue
        if kind not in (1, 2):
            raise ResourceError(f"room {room} has unsupported portal kind {kind}")
        descriptor_id = descriptor_ids.get(record)
        if descriptor_id is None:
            descriptor_id = len(descriptors)
            descriptor_ids[record] = descriptor_id
            descriptors.append(record)
        pair_index = offset // PORTAL.size
        source, destination = divmod(pair_index, box_count)
        pairs.append((source * box_count + destination, descriptor_id))
    if len(pairs) > 0xFFFF or len(descriptors) > 0xFFFF:
        raise ResourceError(f"room {room} portal directory exceeds u16 counts")
    return (struct.pack("<HH", len(pairs), len(descriptors))
            + b"".join(struct.pack("<HH", key, value) for key, value in pairs)
            + b"".join(descriptors))


def _encode_route_rows(dense: bytes, box_count: int, room: int) -> bytes:
    """Encode each BOXM row using its smallest lossless native representation."""
    _validate_route_values(dense, box_count, room=room)
    modes = bytearray()
    row_offsets = [0]
    payload = bytearray()
    for source in range(box_count):
        row = dense[source * box_count:(source + 1) * box_count]
        runs = bytearray()
        index = 0
        while index < box_count:
            value = row[index]
            end = index + 1
            while end < box_count and row[end] == value and end - index < 255:
                end += 1
            runs.extend((end - index, value))
            index = end
        sparse = bytearray()
        for destination, value in enumerate(row):
            if value != 0xFF:
                sparse.extend((destination, value))
        candidates = ((len(row), 0, row), (len(runs), 1, runs),
                      (len(sparse), 2, sparse))
        _size, mode, encoded = min(candidates, key=lambda item: (item[0], item[1]))
        modes.append(mode)
        payload.extend(encoded)
        if len(payload) > 0xFFFF:
            raise ResourceError(f"room {room} compact route rows exceed u16 offsets")
        row_offsets.append(len(payload))
    directory_bytes = 4 + len(modes) + len(row_offsets) * 2
    return (struct.pack("<BBH", 1, box_count, directory_bytes)
            + modes + b"".join(struct.pack("<H", value) for value in row_offsets)
            + payload)


def _encode_portal_rows(dense: bytes, box_count: int, room: int) -> bytes:
    """Encode sparse portal pairs row-locally with packed destination/ID bits."""
    if len(dense) != box_count * box_count * PORTAL.size:
        raise ResourceError(f"room {room} portal table geometry differs")
    descriptors: list[bytes] = []
    descriptor_ids: dict[bytes, int] = {}
    rows: list[list[tuple[int, int]]] = [[] for _ in range(box_count)]
    for pair_index in range(box_count * box_count):
        offset = pair_index * PORTAL.size
        record = dense[offset:offset + PORTAL.size]
        kind, fixed, low, high = PORTAL.unpack(record)
        if kind == 0:
            if fixed or low or high:
                raise ResourceError(f"room {room} has noncanonical empty portal data")
            continue
        if kind not in (1, 2):
            raise ResourceError(f"room {room} has unsupported portal kind {kind}")
        descriptor_id = descriptor_ids.get(record)
        if descriptor_id is None:
            descriptor_id = len(descriptors)
            descriptor_ids[record] = descriptor_id
            descriptors.append(record)
        source, destination = divmod(pair_index, box_count)
        rows[source].append((destination, descriptor_id))
    if len(descriptors) > 0xFFFF:
        raise ResourceError(f"room {room} portal descriptor count exceeds u16")
    destination_bits = max(1, (box_count - 1).bit_length())
    descriptor_bits = max(1, (len(descriptors) - 1).bit_length())
    pair_bits = destination_bits + descriptor_bits
    pair_bytes = (pair_bits + 7) // 8
    if pair_bytes > 3:
        raise ResourceError(f"room {room} packed portal pair exceeds 24 bits")
    row_offsets = [0]
    pairs = bytearray()
    for row in rows:
        row.sort()
        for destination, descriptor_id in row:
            packed = destination | (descriptor_id << destination_bits)
            pairs.extend(packed.to_bytes(pair_bytes, "little"))
        if len(pairs) // pair_bytes > 0xFFFF:
            raise ResourceError(f"room {room} portal pair count exceeds u16")
        row_offsets.append(len(pairs) // pair_bytes)
    header = struct.pack("<HHBBB", sum(map(len, rows)), len(descriptors),
                         pair_bytes, destination_bits, descriptor_bits)
    return (header + b"".join(struct.pack("<H", value) for value in row_offsets)
            + pairs + b"".join(descriptors))


def encode_live_room_sections(
    record: Mapping[str, object], *, program_units: Sequence[Mapping[str, object]],
    max_active_size: int = 0xFFFF,
) -> tuple[bytes, bytes]:
    """Build sectioned v4 metadata: active tables and a separately checked BOXM."""
    # Reuse the canonical v3 projection for all shared tables and source checks.
    legacy = encode_live_room(record, program_units=program_units, max_size=0xFFFF)
    decoded = decode_live_room(legacy, expected_room=int(record["room"]))
    room = int(record["room"])
    values = HEADER.unpack_from(legacy)
    offsets = list(map(int, values[12:22]))
    box_count = decoded.box_count
    route_data = _encode_route_rows(bytes(record["box_routes"]), box_count, room)
    portals_data = _encode_portal_rows(bytes(record["portals"]), box_count, room)
    old_routes, old_portals = offsets[2], offsets[3]
    old_objects = offsets[4]
    sections = (
        ("flags", legacy[offsets[0]:offsets[1]]),
        ("geometry", legacy[offsets[1]:old_routes]),
        ("portals", portals_data),
        ("objects", legacy[old_objects:offsets[5]]),
        ("names", legacy[offsets[5]:offsets[6]]),
        ("object_walk", legacy[offsets[6]:offsets[7]]),
        ("verbs", legacy[offsets[7]:offsets[8]]),
        ("locals", legacy[offsets[8]:offsets[9]]),
        ("bundles", legacy[offsets[9]:int(values[22])]),
    )
    active_offsets: dict[str, int] = {}
    active = bytearray(HEADER.size)
    for name, payload in sections:
        active_offsets[name] = len(active)
        active.extend(payload)
    if not HEADER.size <= len(active) <= max_active_size <= 0xFFFF:
        raise ResourceError(
            f"room {room} sectioned live metadata is {len(active)} bytes; "
            f"audited active limit is {max_active_size}"
        )
    original_source_hash = values[23]
    header_offsets = (
        active_offsets["flags"], active_offsets["geometry"], 0xFFFF,
        active_offsets["portals"], active_offsets["objects"],
        active_offsets["names"], active_offsets["object_walk"],
        active_offsets["verbs"], active_offsets["locals"],
        active_offsets["bundles"],
    )
    header = HEADER.pack(
        MAGIC, SECTIONED_VERSION, HEADER.size, room, int(record.get("flags", 0)),
        decoded.box_count, decoded.object_count, decoded.verb_count,
        decoded.local_count, decoded.bundle_count, decoded.entry_program_unit,
        decoded.exit_program_unit, *header_offsets, len(active), original_source_hash,
    )
    active[:HEADER.size] = header
    return bytes(active), route_data


def encode_live_room(
    record: Mapping[str, object], *, program_units: Sequence[Mapping[str, object]],
    max_size: int = MAX_LIVE_RECORD_BYTES,
) -> bytes:
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
    _validate_route_values(routes, box_count, room=room)
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
    if max_size <= 0 or max_size > 0xFFFF:
        raise ResourceError("live-room encoding limit must fit a nonzero u16")
    if len(body) > max_size:
        limit_detail = f"selected live-room record limit is {max_size} bytes"
        raise ResourceError(
            f"room {room} live metadata is {len(body)} bytes; {limit_detail}"
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


def decode_live_room(
    data: bytes, *, expected_room: int | None = None,
    max_size: int = MAX_SOURCE_RECORD_BYTES, route_data: bytes | None = None,
) -> LiveRoomRecord:
    if len(data) < HEADER.size:
        raise ResourceError("live room record is truncated")
    values = HEADER.unpack_from(data)
    magic, version, header_size, room, flags = values[:5]
    if magic != MAGIC or version not in (2, VERSION, SECTIONED_VERSION) or header_size != HEADER.size or flags & ~0x01:
        raise ResourceError("live room identity, schema, or flags differ")
    if expected_room is not None and room != expected_room:
        raise ResourceError("live room canonical room identity differs")
    counts = tuple(int(value) for value in values[5:12])
    box_count, object_count, verb_count, local_count, bundle_count, entry, exit_ = counts
    offsets_raw = tuple(int(value) for value in values[12:22])
    total_size = int(values[22])
    source_hash = values[23]
    if max_size <= 0 or max_size > 0xFFFF:
        raise ResourceError("live-room validation limit must fit a nonzero u16")
    if total_size != len(data) or total_size > max_size:
        raise ResourceError("live room length exceeds its validated active-resource range")
    if source_hash == bytes(32):
        raise ResourceError("live room provenance identity is empty")
    if version == SECTIONED_VERSION:
        if route_data is None:
            raise ResourceError("sectioned live room is missing its checked route resource")
        decoded = _decode_sectioned_live_room(
            bytes(data), bytes(route_data), expected_room=expected_room,
            max_size=max_size,
        )
        return decoded
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
    _validate_route_values(
        bytes(data[offsets_raw[2]:offsets_raw[2] + lengths[2]]),
        box_count, room=room,
    )

    portals_offset, objects_offset = offsets_raw[3:5]
    if portals_offset != expected or objects_offset > total_size:
        raise ResourceError("live room portal directory is out of bounds or noncanonical")
    portal_indices: list[int | None] = [None] * (box_count * box_count)
    if version == 2:
        portal_index_bytes = box_count * box_count * 2
        portal_values_offset = portals_offset + portal_index_bytes
        if (portal_values_offset > objects_offset
                or objects_offset + object_count * OBJECT.size > total_size):
            raise ResourceError("live room portal directory is out of bounds or noncanonical")
        portal_value_bytes = objects_offset - portal_values_offset
        if portal_value_bytes % PORTAL.size:
            raise ResourceError("live room sparse portal payload has a partial record")
        portal_count = portal_value_bytes // PORTAL.size
        for index in range(box_count * box_count):
            value = struct.unpack_from("<H", data, portals_offset + index * 2)[0]
            if value == 0xFFFF:
                continue
            if value >= portal_count:
                raise ResourceError("live room portal index exceeds sparse portal records")
            portal_indices[index] = value
        portal_records = tuple(
            bytes(data[portal_values_offset + index * PORTAL.size:
                       portal_values_offset + (index + 1) * PORTAL.size])
            for index in range(portal_count)
        )
        portal_storage_size = objects_offset - portals_offset
    else:
        if portals_offset + 4 > objects_offset:
            raise ResourceError("live room v3 portal header is truncated")
        edge_count, portal_count = struct.unpack_from("<HH", data, portals_offset)
        pair_rows_offset = portals_offset + 4
        portal_values_offset = pair_rows_offset + edge_count * 4
        expected_objects_offset = portal_values_offset + portal_count * PORTAL.size
        if (expected_objects_offset != objects_offset
                or objects_offset + object_count * OBJECT.size > total_size):
            raise ResourceError("live room v3 portal sections overlap or escape record")
        previous_key = -1
        for row_index in range(edge_count):
            key, value = struct.unpack_from("<HH", data, pair_rows_offset + row_index * 4)
            if key <= previous_key or key >= box_count * box_count or value >= portal_count:
                raise ResourceError("live room v3 portal pair row is invalid or noncanonical")
            previous_key = key
            portal_indices[key] = value
        portal_records = tuple(
            bytes(data[portal_values_offset + index * PORTAL.size:
                       portal_values_offset + (index + 1) * PORTAL.size])
            for index in range(portal_count)
        )
        if len(set(portal_records)) != len(portal_records):
            raise ResourceError("live room v3 portal descriptors are not deduplicated")
        for descriptor in portal_records:
            kind, _fixed, _low, _high = PORTAL.unpack(descriptor)
            if kind not in (1, 2):
                raise ResourceError("live room v3 portal descriptor kind is invalid")
        portal_storage_size = objects_offset - portals_offset
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
    section_sizes = {
        "header": HEADER.size,
        "flags": box_count,
        "geometry": box_count * 18,
        "routes": box_count * box_count,
        "portals": portal_storage_size,
        "objects": object_count * OBJECT.size,
        "names": object_walk_offset - names_offset,
        "object_walk": object_count * OBJECT_WALK.size,
        "verbs": verb_count * VERB.size,
        "locals": local_count * LOCAL.size,
        "bundles": bundle_count * 2,
    }
    return LiveRoomRecord(
        room, flags, box_count, object_count, verb_count, local_count, bundle_count,
        entry, exit_, decoded_offsets, section_sizes, tuple(object_names), tuple(portal_indices),
        portal_records, bytes(data), source_hash.hex(),
        zlib.crc32(data) & 0xFFFFFFFF, hashlib.sha256(data).hexdigest(),
        bytes(data[offsets_raw[2]:offsets_raw[3]]),
    )


def _decode_sectioned_live_room(
    active: bytes, routes: bytes, *, expected_room: int | None, max_size: int,
) -> LiveRoomRecord:
    """Validate v4 section extents, then normalize to the common v3 IR view."""
    values = HEADER.unpack_from(active)
    _magic, _version, _header_size, room, flags = values[:5]
    counts = tuple(int(value) for value in values[5:12])
    box_count, object_count, verb_count, local_count, bundle_count, entry, exit_ = counts
    offsets = tuple(map(int, values[12:22]))
    total_size = int(values[22])
    source_hash = values[23]
    if expected_room is not None and room != expected_room:
        raise ResourceError("sectioned live room canonical identity differs")
    if total_size != len(active) or total_size > max_size or source_hash == bytes(32):
        raise ResourceError("sectioned live room length or provenance differs")
    if offsets[2] != 0xFFFF:
        raise ResourceError("sectioned live room must externalize its route matrix")
    flags_off, geometry_off, _route_sentinel, portals_off, objects_off, names_off, \
        object_walk_off, verbs_off, locals_off, bundles_off = offsets
    expected = HEADER.size
    if flags_off != expected:
        raise ResourceError("sectioned live room flags offset is noncanonical")
    expected += box_count
    if geometry_off != expected:
        raise ResourceError("sectioned live room geometry offset is noncanonical")
    expected += box_count * 18
    if portals_off != expected or objects_off < portals_off:
        raise ResourceError("sectioned live room portal extent is invalid")
    if objects_off + object_count * OBJECT.size > len(active):
        raise ResourceError("sectioned live room object table is truncated")
    portal = active[portals_off:objects_off]
    if len(portal) < 7:
        raise ResourceError("sectioned live room portal header is truncated")
    edge_count, descriptor_count, pair_bytes, destination_bits, descriptor_bits = struct.unpack_from(
        "<HHBBB", portal,
    )
    if (pair_bytes not in (1, 2, 3) or destination_bits != max(1, (box_count - 1).bit_length())
            or descriptor_bits != max(1, (descriptor_count - 1).bit_length())
            or pair_bytes != (destination_bits + descriptor_bits + 7) // 8):
        raise ResourceError("sectioned live room portal bit layout is invalid")
    row_table = 7
    pair_table = row_table + 2 * (box_count + 1)
    descriptor_table = pair_table + edge_count * pair_bytes
    if descriptor_table + descriptor_count * PORTAL.size != len(portal):
        raise ResourceError("sectioned live room portal sections overlap or escape")
    row_offsets = tuple(struct.unpack_from("<H", portal, row_table + row * 2)[0]
                        for row in range(box_count + 1))
    if row_offsets[0] != 0 or row_offsets[-1] != edge_count:
        raise ResourceError("sectioned live room portal row directory endpoints differ")
    portal_indices: list[int | None] = [None] * (box_count * box_count)
    previous_global = -1
    for source in range(box_count):
        start, end = row_offsets[source], row_offsets[source + 1]
        if start > end or end > edge_count:
            raise ResourceError("sectioned live room portal row range is invalid")
        previous_destination = -1
        for pair_index in range(start, end):
            pos = pair_table + pair_index * pair_bytes
            packed = int.from_bytes(portal[pos:pos + pair_bytes], "little")
            destination_mask = (1 << destination_bits) - 1
            destination = packed & destination_mask
            descriptor_id = packed >> destination_bits
            key = source * box_count + destination
            if (destination >= box_count or destination <= previous_destination
                    or descriptor_id >= descriptor_count or key <= previous_global):
                raise ResourceError("sectioned live room portal pair is invalid")
            previous_destination = destination
            previous_global = key
            portal_indices[key] = descriptor_id
    portal_records = tuple(
        portal[descriptor_table + index * PORTAL.size:
               descriptor_table + (index + 1) * PORTAL.size]
        for index in range(descriptor_count)
    )
    if len(set(portal_records)) != descriptor_count:
        raise ResourceError("sectioned live room portal descriptors are not deduplicated")
    for descriptor in portal_records:
        if PORTAL.unpack(descriptor)[0] not in (1, 2):
            raise ResourceError("sectioned live room portal descriptor kind is invalid")

    if len(routes) < 4:
        raise ResourceError("sectioned live room route resource is truncated")
    route_version, route_boxes, directory_size = struct.unpack_from("<BBH", routes)
    if route_version != 1 or route_boxes != box_count:
        raise ResourceError("sectioned live room route identity/schema differs")
    mode_start = 4
    offsets_start = mode_start + box_count
    payload_start = offsets_start + 2 * (box_count + 1)
    if directory_size != payload_start or payload_start > len(routes):
        raise ResourceError("sectioned live room route directory size differs")
    route_offsets = tuple(struct.unpack_from("<H", routes, offsets_start + row * 2)[0]
                          for row in range(box_count + 1))
    route_payload = routes[payload_start:]
    if route_offsets[0] != 0 or route_offsets[-1] != len(route_payload):
        raise ResourceError("sectioned live room route offsets do not cover payload")
    route_matrix = bytearray()
    for source in range(box_count):
        start, end = route_offsets[source], route_offsets[source + 1]
        if start > end or end > len(route_payload):
            raise ResourceError("sectioned live room route row is out of bounds")
        mode = routes[mode_start + source]
        row_data = route_payload[start:end]
        if mode == 0:
            row = row_data
        elif mode == 1:
            if len(row_data) & 1:
                raise ResourceError("sectioned live room RLE route row is truncated")
            expanded = bytearray()
            for pos in range(0, len(row_data), 2):
                run, value = row_data[pos:pos + 2]
                if run == 0 or len(expanded) + run > box_count:
                    raise ResourceError("sectioned live room RLE route run is invalid")
                expanded.extend(bytes((value,)) * run)
            row = bytes(expanded)
        elif mode == 2:
            if len(row_data) & 1:
                raise ResourceError("sectioned live room sparse route row is truncated")
            expanded = bytearray(b"\xFF" * box_count)
            previous_destination = -1
            for pos in range(0, len(row_data), 2):
                destination, value = row_data[pos:pos + 2]
                if destination >= box_count or destination <= previous_destination or value == 0xFF:
                    raise ResourceError("sectioned live room sparse route entry is invalid")
                expanded[destination] = value
                previous_destination = destination
            row = bytes(expanded)
        else:
            raise ResourceError("sectioned live room route row mode is unknown")
        if len(row) != box_count:
            raise ResourceError("sectioned live room route row expands to the wrong width")
        _validate_route_row(row, box_count, room=room, source=source)
        route_matrix.extend(row)

    # Validate the remaining active tables by rebuilding the canonical v3
    # projection and passing it through the established strict decoder.
    if names_off != objects_off + object_count * OBJECT.size:
        raise ResourceError("sectioned live room names offset is noncanonical")
    if not names_off <= object_walk_off <= verbs_off <= locals_off <= bundles_off <= len(active):
        raise ResourceError("sectioned live room table ordering is invalid")
    lengths = {
        "flags": box_count,
        "geometry": box_count * 18,
        "portals": len(_encode_portal_directory(
            b"".join(portal_records[index] if index is not None else bytes(PORTAL.size)
                     for index in portal_indices), box_count, room,
        )),
        "objects": object_count * OBJECT.size,
        "names": object_walk_off - names_off,
        "object_walk": object_count * OBJECT_WALK.size,
        "verbs": verb_count * VERB.size,
        "locals": local_count * LOCAL.size,
        "bundles": bundle_count * 2,
    }
    active_sections = {
        "flags": active[flags_off:flags_off + lengths["flags"]],
        "geometry": active[geometry_off:geometry_off + lengths["geometry"]],
        "objects": active[objects_off:objects_off + lengths["objects"]],
        "names": active[names_off:object_walk_off],
        "object_walk": active[object_walk_off:object_walk_off + lengths["object_walk"]],
        "verbs": active[verbs_off:verbs_off + lengths["verbs"]],
        "locals": active[locals_off:locals_off + lengths["locals"]],
        "bundles": active[bundles_off:bundles_off + lengths["bundles"]],
    }
    if bundles_off + lengths["bundles"] != len(active):
        raise ResourceError("sectioned live room has unclaimed trailing bytes")
    portal_dense = b"".join(
        portal_records[index] if index is not None else bytes(PORTAL.size)
        for index in portal_indices
    )
    sections = (
        ("flags", active_sections["flags"]),
        ("geometry", active_sections["geometry"]),
        ("routes", bytes(route_matrix)),
        ("portals", _encode_portal_directory(portal_dense, box_count, room)),
        ("objects", active_sections["objects"]),
        ("names", active_sections["names"]),
        ("object_walk", active_sections["object_walk"]),
        ("verbs", active_sections["verbs"]),
        ("locals", active_sections["locals"]),
        ("bundles", active_sections["bundles"]),
    )
    if HEADER.size + sum(len(payload) for _name, payload in sections) > MAX_SOURCE_RECORD_BYTES:
        raise ResourceError(
            "sectioned live room normalized representation exceeds the bounded "
            f"{MAX_SOURCE_RECORD_BYTES}-byte host validation limit"
        )
    normalized = bytearray(HEADER.size)
    normalized_offsets: dict[str, int] = {}
    for name, payload in sections:
        normalized_offsets[name] = len(normalized)
        normalized.extend(payload)
    header = HEADER.pack(
        MAGIC, VERSION, HEADER.size, room, flags,
        box_count, object_count, verb_count, local_count, bundle_count, entry, exit_,
        *(normalized_offsets[name] for name, _payload in sections), len(normalized), source_hash,
    )
    normalized[:HEADER.size] = header
    # max_size constrains the compact v4 active buffer above. The normalized
    # host projection is a separate, bounded source-era representation and may
    # legitimately be larger (for example, sparse routes expand to a matrix).
    decoded = decode_live_room(
        bytes(normalized), expected_room=room,
        max_size=MAX_SOURCE_RECORD_BYTES,
    )
    return LiveRoomRecord(
        decoded.room, decoded.flags, decoded.box_count, decoded.object_count,
        decoded.verb_count, decoded.local_count, decoded.bundle_count,
        decoded.entry_program_unit, decoded.exit_program_unit, decoded.offsets,
        decoded.section_sizes, decoded.object_names, decoded.portal_indices,
        decoded.portal_records, bytes(active), decoded.source_room_sha256,
        zlib.crc32(active) & 0xFFFFFFFF, hashlib.sha256(active).hexdigest(),
        bytes(route_matrix),
    )
