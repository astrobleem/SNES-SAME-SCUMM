"""The stable, target-neutral SAME service packet ABI.

The runtime deliberately uses one small fixed packet instead of allowing each
engine, virtual machine, or foreign-hardware adapter to invent a private
mailbox.  The same 16-byte record is used by the host oracle, S-CPU queues,
and the S-CPU/SA-1 mailbox bridge.

Revision 1 remains wire-compatible with SAME 0.1.  SAME 0.2 only adds service
and opcode values; it does not change packet layout or existing meanings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag
from pathlib import Path
import struct
from typing import Iterable, Mapping, Type

from .errors import AbiError

ABI_REVISION = 1
PACKET_SIZE = 16
_PACKET = struct.Struct("<BBBBBBHII")
assert _PACKET.size == PACKET_SIZE


class Service(IntEnum):
    KERNEL = 0
    VIDEO = 1
    AUDIO = 2
    INPUT = 3
    STORAGE = 4
    TIME = 5
    DEBUG = 6
    MEMORY = 7
    ENGINE = 8
    SAVE = 9
    JOBS = 10


class Endpoint(IntEnum):
    KERNEL = 0
    TARGET = 1  # legacy SAME 0.1 machine-personality endpoint
    SCPU = 2
    SA1 = 3
    SPC = 4
    HOST = 5
    ENGINE = 6
    PROFILE = 7
    BROADCAST = 255


class PacketFlag(IntFlag):
    NONE = 0
    ACK_REQUEST = 1 << 0
    RESPONSE = 1 << 1
    URGENT = 1 << 2
    DROP_OK = 1 << 3
    BULK = 1 << 4
    ERROR = 1 << 7


class KernelOpcode(IntEnum):
    NOP = 0
    HEARTBEAT = 1
    PANIC = 2
    LOG = 3
    BUDGET_OVERRUN = 4
    QUEUE_OVERFLOW = 5
    TARGET_READY = 6
    TARGET_STOPPED = 7
    HOST_READY = 8
    HOST_STOPPED = 9


class VideoOpcode(IntEnum):
    BEGIN_FRAME = 0
    END_FRAME = 1
    SET_BACKDROP = 2
    DEFINE_TILE = 3
    WRITE_TILEMAP = 4
    SUBMIT_SPRITE = 5
    SET_SCROLL = 6
    SET_LAYER = 7
    COMMIT = 8
    RAW_REGISTER_WRITE = 9
    SURFACE_CREATE = 10
    SURFACE_UPLOAD = 11
    SURFACE_DIRTY = 12
    PALETTE_WRITE = 13
    CURSOR_DEFINE = 14
    CURSOR_MOVE = 15
    CURSOR_SHOW = 16
    PRESENT = 17
    QUERY_CAPABILITIES = 18


class AudioOpcode(IntEnum):
    MUSIC_PLAY = 0
    MUSIC_STOP = 1
    SFX_PLAY = 2
    SFX_STOP = 3
    MASTER_VOLUME = 4
    CHIP_WRITE = 5
    PCM_STREAM_START = 6
    PCM_STREAM_STOP = 7
    FLUSH = 8
    SPEECH_PLAY = 9
    SPEECH_STOP = 10
    QUERY_CAPABILITIES = 11


class InputOpcode(IntEnum):
    SNAPSHOT = 0
    PROFILE_CHANGED = 1
    PLAYER_JOINED = 2
    PLAYER_LEFT = 3
    POINTER = 4
    TEXT = 5
    EVENT = 6


class StorageOpcode(IntEnum):
    OPEN_SECTION = 0
    READ = 1
    SEEK = 2
    CLOSE = 3
    PREFETCH = 4
    COMPLETE = 5
    FAILED = 6
    ENUMERATE = 7
    STAT = 8


class TimeOpcode(IntEnum):
    FRAME_TICK = 0
    TIMER_SET = 1
    TIMER_CANCEL = 2
    TIMER_FIRED = 3
    MONOTONIC_QUERY = 4


class DebugOpcode(IntEnum):
    TRACE = 0
    ASSERT = 1
    COUNTER = 2
    MARKER = 3
    STATE_HASH = 4
    VIDEO_HASH = 5
    AUDIO_HASH = 6


class MemoryOpcode(IntEnum):
    ALLOC = 0
    FREE = 1
    COPY = 2
    MAP = 3
    COMPLETE = 4
    FAILED = 5
    PIN = 6
    UNPIN = 7


class EngineOpcode(IntEnum):
    PROBE = 0
    BOOT = 1
    TICK = 2
    HANDLE_EVENT = 3
    SAVE = 4
    LOAD = 5
    SUSPEND = 6
    RESUME = 7
    SHUTDOWN = 8
    QUERY_CAPABILITIES = 9
    READY = 10
    STOPPED = 11
    FAILED = 12


class SaveOpcode(IntEnum):
    READ_SLOT = 0
    WRITE_SLOT = 1
    DELETE_SLOT = 2
    ENUMERATE_SLOTS = 3
    COMPLETE = 4
    FAILED = 5


class JobsOpcode(IntEnum):
    SUBMIT = 0
    CANCEL = 1
    COMPLETE = 2
    FAILED = 3
    QUERY_CAPABILITIES = 4


OPCODE_ENUMS: Mapping[Service, Type[IntEnum]] = {
    Service.KERNEL: KernelOpcode,
    Service.VIDEO: VideoOpcode,
    Service.AUDIO: AudioOpcode,
    Service.INPUT: InputOpcode,
    Service.STORAGE: StorageOpcode,
    Service.TIME: TimeOpcode,
    Service.DEBUG: DebugOpcode,
    Service.MEMORY: MemoryOpcode,
    Service.ENGINE: EngineOpcode,
    Service.SAVE: SaveOpcode,
    Service.JOBS: JobsOpcode,
}


@dataclass(frozen=True, slots=True)
class Packet:
    """One exactly-16-byte SAME service record."""

    service: int | Service
    opcode: int | IntEnum
    arg0: int = 0
    arg1: int = 0
    flags: int | PacketFlag = PacketFlag.NONE
    source: int | Endpoint = Endpoint.ENGINE
    destination: int | Endpoint = Endpoint.KERNEL
    sequence: int = 0
    revision: int = ABI_REVISION

    def __post_init__(self) -> None:
        values = {
            "revision": (int(self.revision), 0xFF),
            "service": (int(self.service), 0xFF),
            "opcode": (int(self.opcode), 0xFF),
            "flags": (int(self.flags), 0xFF),
            "source": (int(self.source), 0xFF),
            "destination": (int(self.destination), 0xFF),
            "sequence": (int(self.sequence), 0xFFFF),
            "arg0": (int(self.arg0), 0xFFFFFFFF),
            "arg1": (int(self.arg1), 0xFFFFFFFF),
        }
        for name, (value, maximum) in values.items():
            if value < 0 or value > maximum:
                raise AbiError(f"{name}={value} is outside 0..{maximum}")
        if int(self.revision) != ABI_REVISION:
            raise AbiError(
                f"packet revision {self.revision} is unsupported; expected {ABI_REVISION}"
            )
        try:
            service = Service(int(self.service))
        except ValueError as exc:
            raise AbiError(f"unknown service id {self.service}") from exc
        enum = OPCODE_ENUMS.get(service)
        if enum is not None:
            try:
                enum(int(self.opcode))
            except ValueError as exc:
                raise AbiError(f"unknown {service.name} opcode {self.opcode}") from exc

    def pack(self) -> bytes:
        return _PACKET.pack(
            int(self.revision),
            int(self.service),
            int(self.opcode),
            int(self.flags),
            int(self.source),
            int(self.destination),
            int(self.sequence),
            int(self.arg0),
            int(self.arg1),
        )

    @classmethod
    def unpack(cls, raw: bytes | bytearray | memoryview) -> "Packet":
        if len(raw) != PACKET_SIZE:
            raise AbiError(f"packet is {len(raw)} bytes; expected {PACKET_SIZE}")
        revision, service, opcode, flags, source, destination, sequence, arg0, arg1 = (
            _PACKET.unpack(bytes(raw))
        )
        return cls(
            revision=revision,
            service=service,
            opcode=opcode,
            flags=flags,
            source=source,
            destination=destination,
            sequence=sequence,
            arg0=arg0,
            arg1=arg1,
        )

    @property
    def service_name(self) -> str:
        return Service(int(self.service)).name

    @property
    def opcode_name(self) -> str:
        enum = OPCODE_ENUMS[Service(int(self.service))]
        return enum(int(self.opcode)).name

    def to_dict(self) -> dict[str, int | str]:
        return {
            "revision": int(self.revision),
            "service": int(self.service),
            "service_name": self.service_name,
            "opcode": int(self.opcode),
            "opcode_name": self.opcode_name,
            "flags": int(self.flags),
            "source": int(self.source),
            "destination": int(self.destination),
            "sequence": int(self.sequence),
            "arg0": int(self.arg0),
            "arg1": int(self.arg1),
        }


def _poppy_constant(name: str, value: int) -> str:
    width = 2 if value <= 0xFF else 4 if value <= 0xFFFF else 8
    return f"{name:<40} = ${value:0{width}X}"


def generate_poppy_include(path: Path) -> None:
    """Generate the authoritative 65816 copy of the ABI constants."""

    lines = [
        "; Generated by `same abi generate`; do not edit by hand.",
        f"; SAME service packet ABI revision {ABI_REVISION}.",
        "",
        _poppy_constant("SAME_ABI_REVISION", ABI_REVISION),
        _poppy_constant("SAME_PACKET_SIZE", PACKET_SIZE),
        _poppy_constant("SAME_PKT_REVISION", 0),
        _poppy_constant("SAME_PKT_SERVICE", 1),
        _poppy_constant("SAME_PKT_OPCODE", 2),
        _poppy_constant("SAME_PKT_FLAGS", 3),
        _poppy_constant("SAME_PKT_SOURCE", 4),
        _poppy_constant("SAME_PKT_DESTINATION", 5),
        _poppy_constant("SAME_PKT_SEQUENCE", 6),
        _poppy_constant("SAME_PKT_ARG0", 8),
        _poppy_constant("SAME_PKT_ARG1", 12),
        "",
    ]
    for member in Service:
        lines.append(_poppy_constant(f"SAME_SERVICE_{member.name}", int(member)))
    lines.append("")
    for member in Endpoint:
        lines.append(_poppy_constant(f"SAME_ENDPOINT_{member.name}", int(member)))
    lines.append("")
    for member in PacketFlag:
        if member is not PacketFlag.NONE:
            lines.append(_poppy_constant(f"SAME_FLAG_{member.name}", int(member)))
    for service, enum in OPCODE_ENUMS.items():
        lines.append("")
        lines.append(f"; {service.name} service opcodes")
        for member in enum:
            lines.append(
                _poppy_constant(
                    f"SAME_{service.name}_OP_{member.name}", int(member)
                )
            )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def packet_stream(packets: Iterable[Packet]) -> bytes:
    return b"".join(packet.pack() for packet in packets)


def unpack_packet_stream(raw: bytes) -> list[Packet]:
    if len(raw) % PACKET_SIZE:
        raise AbiError(
            f"packet stream length {len(raw)} is not divisible by {PACKET_SIZE}"
        )
    return [
        Packet.unpack(raw[offset : offset + PACKET_SIZE])
        for offset in range(0, len(raw), PACKET_SIZE)
    ]
