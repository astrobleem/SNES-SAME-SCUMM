"""Portable SAME save envelopes and save-slot stores."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import struct
import zlib

from .errors import SaveFormatError

MAGIC = b"SAMESAV\0"
VERSION = 1
_HEADER = struct.Struct("<8sHHI32s32sII")
HEADER_SIZE = _HEADER.size
_ID_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,31}$")


def _encode_id(value: str, field: str) -> bytes:
    if not _ID_RE.fullmatch(value):
        raise SaveFormatError(f"{field}={value!r} is not a valid SAME identifier")
    return value.encode("ascii").ljust(32, b"\0")


def _decode_id(raw: bytes, field: str) -> str:
    try:
        value = raw.split(b"\0", 1)[0].decode("ascii")
    except UnicodeDecodeError as exc:
        raise SaveFormatError(f"save {field} is not ASCII") from exc
    _encode_id(value, field)
    return value


@dataclass(frozen=True, slots=True)
class SaveEnvelope:
    engine_id: str
    game_id: str
    schema: int
    payload: bytes
    flags: int = 0

    def __post_init__(self) -> None:
        _encode_id(self.engine_id, "engine_id")
        _encode_id(self.game_id, "game_id")
        if not 0 <= self.schema <= 0xFFFFFFFF:
            raise SaveFormatError("save schema must fit u32")
        if not 0 <= self.flags <= 0xFFFF:
            raise SaveFormatError("save flags must fit u16")

    def pack(self) -> bytes:
        payload = bytes(self.payload)
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        return _HEADER.pack(
            MAGIC,
            VERSION,
            self.flags,
            self.schema,
            _encode_id(self.engine_id, "engine_id"),
            _encode_id(self.game_id, "game_id"),
            len(payload),
            crc,
        ) + payload

    @classmethod
    def unpack(cls, raw: bytes | bytearray | memoryview) -> "SaveEnvelope":
        data = bytes(raw)
        if len(data) < HEADER_SIZE:
            raise SaveFormatError("save is shorter than its header")
        magic, version, flags, schema, engine_raw, game_raw, size, expected_crc = (
            _HEADER.unpack_from(data, 0)
        )
        if magic != MAGIC:
            raise SaveFormatError(f"bad save magic {magic!r}")
        if version != VERSION:
            raise SaveFormatError(f"unsupported save version {version}")
        payload = data[HEADER_SIZE:]
        if len(payload) != size:
            raise SaveFormatError(
                f"save payload is {len(payload)} bytes; header declares {size}"
            )
        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise SaveFormatError(
                f"save CRC mismatch: expected {expected_crc:08x}, got {actual_crc:08x}"
            )
        return cls(
            engine_id=_decode_id(engine_raw, "engine_id"),
            game_id=_decode_id(game_raw, "game_id"),
            schema=schema,
            flags=flags,
            payload=payload,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine_id,
            "game": self.game_id,
            "schema": self.schema,
            "flags": self.flags,
            "payload_size": len(self.payload),
            "payload_crc32": f"{zlib.crc32(self.payload) & 0xFFFFFFFF:08x}",
        }


class InMemorySaveStore:
    def __init__(self) -> None:
        self._slots: dict[int, bytes] = {}

    def list_slots(self) -> tuple[int, ...]:
        return tuple(sorted(self._slots))

    def read(self, slot: int) -> bytes:
        try:
            return self._slots[self._validate_slot(slot)]
        except KeyError as exc:
            raise SaveFormatError(f"save slot {slot} is empty") from exc

    def write(self, slot: int, data: bytes) -> None:
        self._slots[self._validate_slot(slot)] = bytes(data)

    def delete(self, slot: int) -> None:
        self._slots.pop(self._validate_slot(slot), None)

    @staticmethod
    def _validate_slot(slot: int) -> int:
        slot = int(slot)
        if not 0 <= slot <= 999:
            raise SaveFormatError("save slot must be in 0..999")
        return slot


class DirectorySaveStore:
    def __init__(self, root: Path, namespace: str) -> None:
        if not _ID_RE.fullmatch(namespace):
            raise SaveFormatError(f"invalid save namespace {namespace!r}")
        self.root = root.resolve() / namespace

    @staticmethod
    def _validate_slot(slot: int) -> int:
        return InMemorySaveStore._validate_slot(slot)

    def _path(self, slot: int) -> Path:
        return self.root / f"slot-{self._validate_slot(slot):03d}.same-save"

    def list_slots(self) -> tuple[int, ...]:
        if not self.root.is_dir():
            return ()
        slots: list[int] = []
        for path in self.root.glob("slot-*.same-save"):
            try:
                slots.append(int(path.stem.split("-")[1]))
            except (IndexError, ValueError):
                continue
        return tuple(sorted(set(slots)))

    def read(self, slot: int) -> bytes:
        path = self._path(slot)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise SaveFormatError(f"cannot read save slot {slot} from {path}: {exc}") from exc

    def write(self, slot: int, data: bytes) -> None:
        path = self._path(slot)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(bytes(data))
        temporary.replace(path)

    def delete(self, slot: int) -> None:
        path = self._path(slot)
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise SaveFormatError(f"cannot delete save slot {slot}: {exc}") from exc
