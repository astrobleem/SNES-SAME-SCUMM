"""Versioned, source-bound cooked SCUMM v5 ROOM records.

The record retains the complete original ROOM payload.  Its directory only
describes executable subchunks; it does not rewrite or extract script bodies.
Host builds bind the record with SHA-256, while the cartridge can validate the
same fixed header, bounds, CRC32, and additive checksum without implementing
SHA-256 on the S-CPU.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib

from ...errors import ResourceError


MAGIC = b"SC5ROOM\0"
VERSION = 1
FLAG_REGISTRATION_ONLY = 1
HEADER = struct.Struct("<8sHHHHIIIIIHH32s32s32s32s32s32s")
SCRIPT = struct.Struct("<4sHHIIIIII32s32s")
TRAILER_SIZE = 32


def _sha(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def identity_digest(value: str) -> bytes:
    return _sha(value.encode("utf-8"))


def additive16(data: bytes) -> int:
    return sum(data) & 0xFFFF


@dataclass(frozen=True, slots=True)
class CookedScriptSource:
    kind: str
    number: int
    identity: str
    original_file_offset: int
    original_room_offset: int
    original_chunk_offset: int
    cooked_record_offset: int
    normalized_script_offset: int
    program: bytes
    sha256: str

    def runtime_map(self, instruction_offset: int) -> dict[str, int]:
        if not 0 <= instruction_offset <= len(self.program):
            raise ResourceError("runtime instruction offset lies outside cooked script")
        return {
            "original_file_offset": self.original_file_offset + instruction_offset,
            "original_room_offset": self.original_room_offset + instruction_offset,
            "original_chunk_offset": self.original_chunk_offset + instruction_offset,
            "cooked_record_offset": self.cooked_record_offset + instruction_offset,
            "normalized_script_offset": self.normalized_script_offset + instruction_offset,
            "runtime_instruction_offset": instruction_offset,
        }


@dataclass(frozen=True, slots=True)
class CookedRoomRecord:
    room: int
    flags: int
    profile_sha256: str
    game_identity_sha256: str
    archive_sha256: str
    index_sha256: str
    data_sha256: str
    room_sha256: str
    record_sha256: str
    compact_checksum: int
    room_payload: bytes
    scripts: tuple[CookedScriptSource, ...]

    @property
    def registration_only(self) -> bool:
        return bool(self.flags & FLAG_REGISTRATION_ONLY)

    @property
    def entry(self) -> CookedScriptSource | None:
        return next((item for item in self.scripts if item.kind == "ENCD"), None)

    @property
    def exit(self) -> CookedScriptSource | None:
        return next((item for item in self.scripts if item.kind == "EXCD"), None)

    @property
    def locals(self) -> tuple[CookedScriptSource, ...]:
        return tuple(item for item in self.scripts if item.kind == "LSCR")


@dataclass(frozen=True, slots=True)
class ScriptChunkInput:
    kind: str
    number: int
    identity: str
    chunk_header_room_offset: int
    body_chunk_offset: int
    body_length: int


def encode_cooked_room(
    room_payload: bytes,
    *,
    room: int,
    flags: int,
    original_room_file_offset: int,
    profile_sha256: str,
    game_identity_sha256: str,
    archive_sha256: str,
    index_sha256: str,
    data_sha256: str,
    scripts: tuple[ScriptChunkInput, ...],
) -> bytes:
    if not 0 <= room <= 255:
        raise ResourceError("cooked room number must fit u8")
    if not room_payload:
        raise ResourceError("cooked ROOM payload must not be empty")
    if flags & ~FLAG_REGISTRATION_ONLY:
        raise ResourceError("cooked room has unsupported flags")
    table_offset = HEADER.size
    room_offset = table_offset + len(scripts) * SCRIPT.size
    record_length = room_offset + len(room_payload) + TRAILER_SIZE
    entries = bytearray()
    ranges: list[tuple[int, int]] = []
    identities: set[str] = set()
    for item in scripts:
        if item.kind not in {"ENCD", "EXCD", "LSCR"}:
            raise ResourceError(f"unsupported cooked script kind {item.kind!r}")
        if item.identity in identities:
            raise ResourceError(f"duplicate cooked script identity {item.identity!r}")
        identities.add(item.identity)
        body_room_offset = item.chunk_header_room_offset + item.body_chunk_offset
        body_end = body_room_offset + item.body_length
        if (
            item.chunk_header_room_offset < 0
            or item.body_chunk_offset < 8
            or item.body_length < 0
            or body_end > len(room_payload)
        ):
            raise ResourceError(f"cooked script {item.identity!r} lies outside ROOM payload")
        ranges.append((body_room_offset, body_end))
        program = room_payload[body_room_offset:body_end]
        entries.extend(SCRIPT.pack(
            item.kind.encode("ascii"), item.number, 0,
            original_room_file_offset + body_room_offset,
            body_room_offset,
            item.body_chunk_offset,
            room_offset + body_room_offset,
            0,
            len(program),
            _sha(program), identity_digest(item.identity),
        ))
    ordered = sorted(ranges)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        raise ResourceError("cooked script ranges overlap")
    room_crc = zlib.crc32(room_payload) & 0xFFFFFFFF
    header = HEADER.pack(
        MAGIC, VERSION, HEADER.size, flags, room,
        record_length, table_offset, len(scripts), room_offset,
        0, 0, 0,
        bytes.fromhex(profile_sha256), bytes.fromhex(game_identity_sha256),
        bytes.fromhex(archive_sha256), bytes.fromhex(index_sha256),
        bytes.fromhex(data_sha256), _sha(room_payload),
    )
    prefix = bytearray(header + entries + room_payload)
    checksum = additive16(prefix)
    struct.pack_into("<H", prefix, 36, checksum)
    # CRC and checksum stay outside the digest area so cartridge validation is
    # bounded and does not require SHA-256.
    struct.pack_into("<I", prefix, 32, room_crc)
    return bytes(prefix) + _sha(prefix)


def decode_cooked_room(
    data: bytes,
    *,
    expected_room: int | None = None,
    expected_profile_sha256: str | None = None,
    expected_game_identity_sha256: str | None = None,
    expected_archive_sha256: str | None = None,
    expected_index_sha256: str | None = None,
    expected_data_sha256: str | None = None,
) -> CookedRoomRecord:
    if len(data) < HEADER.size + TRAILER_SIZE:
        raise ResourceError("cooked room record is truncated")
    unpacked = HEADER.unpack_from(data)
    (
        magic, version, header_size, flags, room,
        record_length, table_offset, script_count, room_offset,
        room_crc, compact_checksum, reserved,
        profile_hash, game_hash, archive_hash, index_hash, data_hash, room_hash,
    ) = unpacked
    if magic != MAGIC or version != VERSION or header_size != HEADER.size:
        raise ResourceError("cooked room magic, schema, or header size differs")
    if flags & ~FLAG_REGISTRATION_ONLY or reserved:
        raise ResourceError("cooked room flags are unsupported")
    if record_length != len(data):
        raise ResourceError("cooked room record length differs")
    if table_offset != HEADER.size:
        raise ResourceError("cooked room script table offset differs")
    table_end = table_offset + script_count * SCRIPT.size
    if table_end != room_offset or room_offset > len(data) - TRAILER_SIZE:
        raise ResourceError("cooked room script table or ROOM offset is invalid")
    prefix = bytearray(data[:-TRAILER_SIZE])
    if _sha(prefix) != data[-TRAILER_SIZE:]:
        raise ResourceError("cooked room whole-record SHA-256 differs")
    stored_crc = room_crc
    stored_sum = compact_checksum
    struct.pack_into("<I", prefix, 32, 0)
    struct.pack_into("<H", prefix, 36, 0)
    room_payload = data[room_offset:-TRAILER_SIZE]
    if zlib.crc32(room_payload) & 0xFFFFFFFF != stored_crc:
        raise ResourceError("cooked room payload CRC32 differs")
    if additive16(prefix) != stored_sum:
        raise ResourceError("cooked room compact checksum differs")
    checks = (
        (expected_room, room, "room"),
        (expected_profile_sha256, profile_hash.hex(), "profile"),
        (expected_game_identity_sha256, game_hash.hex(), "game"),
        (expected_archive_sha256, archive_hash.hex(), "archive"),
        (expected_index_sha256, index_hash.hex(), "index"),
        (expected_data_sha256, data_hash.hex(), "data"),
    )
    for expected, observed, label in checks:
        if expected is not None and expected != observed:
            raise ResourceError(f"cooked room {label} identity differs")
    if _sha(room_payload) != room_hash:
        raise ResourceError("cooked room original ROOM identity differs")
    scripts_out: list[CookedScriptSource] = []
    ranges: list[tuple[int, int]] = []
    identities: set[bytes] = set()
    for index in range(script_count):
        base = table_offset + index * SCRIPT.size
        (
            kind_raw, number, entry_flags, original_file_offset,
            original_room_offset, original_chunk_offset, cooked_offset,
            normalized_offset, program_length, program_hash, identity_hash,
        ) = SCRIPT.unpack_from(data, base)
        try:
            kind = kind_raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ResourceError("cooked script kind is not ASCII") from exc
        if kind not in {"ENCD", "EXCD", "LSCR"} or entry_flags:
            raise ResourceError("cooked script kind or flags are invalid")
        if identity_hash in identities:
            raise ResourceError("cooked script identity is duplicated")
        identities.add(identity_hash)
        if cooked_offset != room_offset + original_room_offset:
            raise ResourceError("cooked script source mapping is inconsistent")
        end = cooked_offset + program_length
        if cooked_offset < room_offset or end > len(data) - TRAILER_SIZE:
            raise ResourceError("cooked script lies outside ROOM payload")
        ranges.append((cooked_offset, end))
        program = data[cooked_offset:end]
        if _sha(program) != program_hash:
            raise ResourceError("cooked script payload identity differs")
        identity = f"room.{room}/{kind}" if kind != "LSCR" else f"room.{room}/LSCR.{number}"
        if identity_digest(identity) != identity_hash:
            raise ResourceError("cooked script stable identity differs")
        scripts_out.append(CookedScriptSource(
            kind, number, identity, original_file_offset, original_room_offset,
            original_chunk_offset, cooked_offset, normalized_offset, program,
            program_hash.hex(),
        ))
    ordered = sorted(ranges)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        raise ResourceError("cooked script ranges overlap")
    if sum(item.kind == "ENCD" for item in scripts_out) > 1 or sum(
        item.kind == "EXCD" for item in scripts_out
    ) > 1:
        raise ResourceError("cooked room contains duplicate ENCD or EXCD")
    return CookedRoomRecord(
        room, flags, profile_hash.hex(), game_hash.hex(), archive_hash.hex(),
        index_hash.hex(), data_hash.hex(), room_hash.hex(),
        data[-TRAILER_SIZE:].hex(), stored_sum, room_payload, tuple(scripts_out),
    )
