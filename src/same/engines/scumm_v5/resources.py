"""Raw LucasArts SCUMM v5 resources exposed through SAME stable keys.

The adapter understands only the container/directory layer needed to locate
rooms, global scripts, and sounds.  It deliberately does not interpret room,
script, or audio semantics; those remain engine/adaptor responsibilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import struct
from typing import BinaryIO
import zlib

from ...errors import ResourceError
from ...resources import ResourceProvider, ResourceStat
from .policy import ScummV5GamePolicy

_XOR_KEY = 0x69
_DIRECTORY_TAGS = ("DSCR", "DSOU", "DCOS", "DCHR")
_REQUIRED_DIRECTORY_TAGS = ("DSCR", "DSOU")


@dataclass(frozen=True, slots=True)
class _Chunk:
    tag: str
    offset: int
    size: int
    payload: bytes


@dataclass(frozen=True, slots=True)
class _Directory:
    rooms: tuple[int, ...]
    offsets: tuple[int, ...]


def _slice(data: bytes, key: str, offset: int, length: int | None) -> bytes:
    if offset < 0:
        raise ResourceError(f"resource {key!r}: offset must not be negative")
    if offset > len(data):
        raise ResourceError(
            f"resource {key!r}: offset {offset} lies beyond size {len(data)}"
        )
    if length is not None and length < 0:
        raise ResourceError(f"resource {key!r}: length must not be negative")
    end = len(data) if length is None else min(len(data), offset + length)
    return data[offset:end]


def _chunk(data: bytes, offset: int, *, owner: str) -> _Chunk:
    if offset < 0 or offset + 8 > len(data):
        raise ResourceError(f"{owner}: chunk header at offset {offset} is out of bounds")
    tag_bytes = data[offset : offset + 4]
    try:
        tag = tag_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ResourceError(f"{owner}: non-ASCII chunk tag at offset {offset}") from exc
    size = struct.unpack_from(">I", data, offset + 4)[0]
    if size < 8:
        raise ResourceError(f"{owner}: chunk {tag!r} at offset {offset} has size {size}")
    end = offset + size
    if end > len(data):
        raise ResourceError(
            f"{owner}: chunk {tag!r} at offset {offset} ends at {end}, beyond {len(data)}"
        )
    return _Chunk(tag, offset, size, data[offset + 8 : end])


def _chunks(data: bytes, *, owner: str) -> tuple[_Chunk, ...]:
    result: list[_Chunk] = []
    offset = 0
    while offset < len(data):
        item = _chunk(data, offset, owner=owner)
        result.append(item)
        offset += item.size
    return tuple(result)


def _directory(chunk: _Chunk, *, owner: str) -> _Directory:
    data = chunk.payload
    if len(data) < 2:
        raise ResourceError(f"{owner}: {chunk.tag} directory is truncated before count")
    count = struct.unpack_from("<H", data, 0)[0]
    expected = 2 + count + count * 4
    if len(data) != expected:
        raise ResourceError(
            f"{owner}: {chunk.tag} directory is {len(data)} bytes; expected {expected}"
        )
    rooms = tuple(data[2 : 2 + count])
    offsets = tuple(
        struct.unpack_from("<I", data, 2 + count + index * 4)[0]
        for index in range(count)
    )
    return _Directory(rooms, offsets)


class LucasartsScummV5ResourceProvider:
    """Layer raw encrypted v5 index/data files over an existing provider."""

    def __init__(self, backing: ResourceProvider, policy: ScummV5GamePolicy) -> None:
        if policy.resource_format != "lucasarts_scumm_v5":
            raise ResourceError(
                f"raw SCUMM adapter cannot open format {policy.resource_format!r}"
            )
        self.backing = backing
        self.policy = policy
        self._index = self._decrypt(policy.index_key)
        self._data = self._decrypt(policy.data_key)
        self._directories = self._parse_index()
        self._rooms = self._parse_room_table()
        self._derived: dict[str, tuple[str, int]] = {}
        self._build_key_index()

    def _decrypt(self, key: str) -> bytes:
        if not self.backing.contains(key):
            raise ResourceError(f"raw SCUMM source resource {key!r} is unavailable")
        raw = self.backing.read(key)
        if not raw:
            raise ResourceError(f"raw SCUMM source resource {key!r} is empty")
        return bytes(value ^ _XOR_KEY for value in raw)

    def _parse_index(self) -> dict[str, _Directory]:
        result: dict[str, _Directory] = {}
        for item in _chunks(self._index, owner=self.policy.index_key):
            if item.tag in _DIRECTORY_TAGS:
                if item.tag in result:
                    raise ResourceError(
                        f"{self.policy.index_key}: duplicate {item.tag} directory"
                    )
                result[item.tag] = _directory(item, owner=self.policy.index_key)
        for tag in _REQUIRED_DIRECTORY_TAGS:
            if tag not in result:
                raise ResourceError(f"{self.policy.index_key}: missing {tag} directory")
        return result

    def _parse_room_table(self) -> dict[int, _Chunk]:
        root = _chunk(self._data, 0, owner=self.policy.data_key)
        if root.tag != "LECF" or root.size != len(self._data):
            raise ResourceError(
                f"{self.policy.data_key}: expected one complete LECF root chunk"
            )
        children = _chunks(root.payload, owner=f"{self.policy.data_key} LECF")
        if not children or children[0].tag != "LOFF":
            raise ResourceError(f"{self.policy.data_key}: LECF does not begin with LOFF")
        loff = children[0].payload
        if not loff:
            raise ResourceError(f"{self.policy.data_key}: LOFF is missing its room count")
        count = loff[0]
        expected = 1 + count * 5
        if len(loff) != expected:
            raise ResourceError(
                f"{self.policy.data_key}: LOFF is {len(loff)} bytes; expected {expected}"
            )
        rooms: dict[int, _Chunk] = {}
        for index in range(count):
            base = 1 + index * 5
            room = loff[base]
            payload_offset = struct.unpack_from("<I", loff, base + 1)[0]
            header_offset = payload_offset - 8
            item = _chunk(self._data, header_offset, owner=self.policy.data_key)
            if item.tag != "LFLF":
                raise ResourceError(
                    f"{self.policy.data_key}: room {room} points to {item.tag!r}, not LFLF"
                )
            if room in rooms:
                raise ResourceError(f"{self.policy.data_key}: duplicate LOFF room {room}")
            rooms[room] = item
        return rooms

    def _build_key_index(self) -> None:
        for room in sorted(self._rooms):
            key = self.policy.room_key_template.format(room=room)
            self._add_key(key, "ROOM", room)
        for tag, kind, template in (
            ("DSCR", "SCRP", self.policy.script_key_template),
            ("DSOU", "SOUN", self.policy.sound_key_template),
            ("DCOS", "COST", self.policy.costume_key_template),
            ("DCHR", "CHAR", self.policy.charset_key_template),
        ):
            if tag not in self._directories:
                continue
            directory = self._directories[tag]
            placeholder = {
                "DSCR": "script",
                "DSOU": "sound",
                "DCOS": "costume",
                "DCHR": "charset",
            }[tag]
            for number, room in enumerate(directory.rooms):
                # Demo/shareware indexes can retain entries from the complete
                # game even when the referenced LFLF is not distributed.
                # Never advertise a stable key whose bytes cannot be read.
                if room == 0 or room not in self._rooms:
                    continue
                key = template.format(**{placeholder: number})
                self._add_key(key, kind, number)

    def _add_key(self, key: str, kind: str, number: int) -> None:
        if key in self._derived or self.backing.contains(key):
            raise ResourceError(f"raw SCUMM derived resource key {key!r} is ambiguous")
        self._derived[key] = (kind, number)

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted((*self.backing.keys(), *self._derived)))

    def contains(self, key: str) -> bool:
        return key in self._derived or self.backing.contains(key)

    def _room_payload(self, room: int) -> bytes:
        try:
            lflf = self._rooms[room]
        except KeyError as exc:
            raise ResourceError(f"raw SCUMM room {room} is unavailable") from exc
        children = _chunks(lflf.payload, owner=f"room {room} LFLF")
        room_chunk = next((item for item in children if item.tag == "ROOM"), None)
        if room_chunk is None:
            raise ResourceError(f"raw SCUMM room {room} has no ROOM chunk")
        return room_chunk.payload

    def _directory_payload(self, tag: str, number: int, expected: str) -> bytes:
        directory = self._directories[tag]
        if not 0 <= number < len(directory.rooms) or directory.rooms[number] == 0:
            raise ResourceError(f"raw SCUMM {expected.lower()} {number} is unavailable")
        room = directory.rooms[number]
        try:
            lflf = self._rooms[room]
        except KeyError as exc:
            raise ResourceError(
                f"raw SCUMM {expected.lower()} {number} references missing room {room}"
            ) from exc
        offset = directory.offsets[number]
        item = _chunk(lflf.payload, offset, owner=f"room {room} LFLF")
        if item.tag != expected:
            raise ResourceError(
                f"raw SCUMM {expected.lower()} {number} points to {item.tag!r}, "
                f"expected {expected!r}"
            )
        return item.payload

    def _read_derived(self, key: str) -> bytes:
        try:
            kind, number = self._derived[key]
        except KeyError as exc:
            raise ResourceError(f"unknown resource {key!r}") from exc
        if kind == "ROOM":
            return self._room_payload(number)
        tag = {"SCRP": "DSCR", "SOUN": "DSOU", "COST": "DCOS", "CHAR": "DCHR"}[kind]
        return self._directory_payload(tag, number, kind)

    def stat(self, key: str) -> ResourceStat:
        if key not in self._derived:
            return self.backing.stat(key)
        kind, number = self._derived[key]
        data = self._read_derived(key)
        return ResourceStat(
            key=key,
            size=len(data),
            kind=kind,
            streamable=kind in {"ROOM", "SOUN"},
            crc32=zlib.crc32(data) & 0xFFFFFFFF,
            source=f"{self.policy.data_key}#{kind}[{number}]",
        )

    def read(self, key: str, offset: int = 0, length: int | None = None) -> bytes:
        if key not in self._derived:
            return self.backing.read(key, offset, length)
        return _slice(self._read_derived(key), key, offset, length)

    def open(self, key: str) -> BinaryIO:
        return BytesIO(self.read(key))
