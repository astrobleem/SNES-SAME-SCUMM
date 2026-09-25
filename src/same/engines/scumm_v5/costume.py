"""Strict classic SCUMM v5 costume decoding for raw-room presentation."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from ...errors import ResourceError


_COSTUME_INFO = struct.Struct("<HHhhhh")
_MAX_CEL_DIMENSION = 512


def _u16(data: bytes, offset: int, *, key: str, label: str) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ResourceError(f"SCUMM costume {key!r} {label} is out of bounds")
    return struct.unpack_from("<H", data, offset)[0]


def _resource_offset(value: int, *, size: int, key: str, label: str) -> int:
    # The raw provider strips the six-byte classic resource prefix retained by
    # the interpreter's internal base pointer. All costume offsets are relative
    # to that base, so exposed payload offsets are six bytes smaller.
    offset = value - 6
    if offset < 0 or offset >= size:
        raise ResourceError(f"SCUMM costume {key!r} {label} offset {value} is invalid")
    return offset


@dataclass(frozen=True, slots=True)
class CostumeCel:
    width: int
    height: int
    relative_x: int
    relative_y: int
    move_x: int
    move_y: int
    pixels: bytes


@dataclass(frozen=True, slots=True)
class CostumePose:
    frame: int
    direction: int
    draw_to_right: bool
    cels: tuple[CostumeCel, ...]
    commands: tuple[tuple[int, int], ...]


class ScummV5Costume:
    """Decode classic format-$58/$59 costumes exposed without chunk headers."""

    def __init__(self, data: bytes, *, key: str) -> None:
        self.data = bytes(data)
        self.key = key
        if len(self.data) < 54:
            raise ResourceError(f"SCUMM costume {key!r} is shorter than its header")
        self.animation_count = self.data[0]
        encoded_format = self.data[1]
        self.mirror = bool(encoded_format & 0x80)
        self.format = encoded_format & 0x7F
        if self.format == 0x58:
            self.color_count = 16
        elif self.format == 0x59:
            self.color_count = 32
        else:
            raise ResourceError(
                f"SCUMM costume {key!r} has unsupported format ${self.format:02X}"
            )
        tables = 2 + self.color_count + 2 + 32 + (self.animation_count + 1) * 2
        if tables > len(self.data):
            raise ResourceError(f"SCUMM costume {key!r} offset tables are truncated")
        self.palette = tuple(self.data[2 : 2 + self.color_count])
        table = 2 + self.color_count
        self._animation_commands = _resource_offset(
            _u16(self.data, table, key=key, label="animation command table"),
            size=len(self.data), key=key, label="animation command table",
        )
        self._frame_offsets = table + 2
        self._data_offsets = table + 34

    @staticmethod
    def direction_index(facing: int) -> int:
        """Convert one internal actor angle with canonical v5 boundaries."""
        if 71 <= facing <= 109:
            return 1
        if 109 <= facing <= 251:
            return 2
        if 251 <= facing <= 289:
            return 0
        return 3

    def _decode_cel(self, limb: int, command: int) -> CostumeCel:
        frame_value = _u16(
            self.data, self._frame_offsets + limb * 2,
            key=self.key, label=f"limb {limb} frame table",
        )
        frame_table = _resource_offset(
            frame_value, size=len(self.data), key=self.key, label=f"limb {limb} frame table",
        )
        cel_value = _u16(
            self.data, frame_table + command * 2,
            key=self.key, label=f"limb {limb} cel {command}",
        )
        cel_offset = _resource_offset(
            cel_value, size=len(self.data), key=self.key, label=f"limb {limb} cel {command}",
        )
        if cel_offset + _COSTUME_INFO.size > len(self.data):
            raise ResourceError(f"SCUMM costume {self.key!r} cel header is truncated")
        width, height, relative_x, relative_y, move_x, move_y = _COSTUME_INFO.unpack_from(
            self.data, cel_offset
        )
        if (
            width == 0 or height == 0
            or width > _MAX_CEL_DIMENSION or height > _MAX_CEL_DIMENSION
            or width * height > _MAX_CEL_DIMENSION * _MAX_CEL_DIMENSION
        ):
            raise ResourceError(
                f"SCUMM costume {self.key!r} cel dimensions {width}x{height} are invalid"
            )
        source = cel_offset + _COSTUME_INFO.size
        pixels = bytearray()
        shift = 4 if self.color_count == 16 else 3
        run_mask = (1 << shift) - 1
        while len(pixels) < width * height:
            if source >= len(self.data):
                raise ResourceError(f"SCUMM costume {self.key!r} cel RLE is truncated")
            packet = self.data[source]
            source += 1
            color, run = packet >> shift, packet & run_mask
            if run == 0:
                if source >= len(self.data):
                    raise ResourceError(f"SCUMM costume {self.key!r} extended RLE is truncated")
                run = self.data[source]
                source += 1
                if run == 0:
                    raise ResourceError(f"SCUMM costume {self.key!r} contains a zero RLE run")
            if len(pixels) + run > width * height:
                raise ResourceError(f"SCUMM costume {self.key!r} cel RLE overruns its dimensions")
            pixels.extend((color,) * run)
        return CostumeCel(
            width, height, relative_x, relative_y, move_x, move_y, bytes(pixels)
        )

    def _command_at_step(self, start: int, end: int, one_shot: bool, step: int) -> int:
        """Return one limb command after canonical classic-cursor advances."""
        current = start
        seen: dict[int, int] = {}
        advanced = 0
        while advanced < step:
            if current in seen:
                cycle = advanced - seen[current]
                if cycle:
                    remaining = step - advanced
                    advanced += remaining - (remaining % cycle)
                    if advanced == step:
                        break
            else:
                seen[current] = advanced
            # increaseAnim skips counter/sound commands when a sequence has
            # another position, then publishes the first drawable cursor.
            for _skip in range(end - start + 2):
                if one_shot:
                    if current != end:
                        current += 1
                else:
                    current = start if current >= end else current + 1
                command = self.data[self._animation_commands + current]
                if command not in (0x7C, 0x78) or start == end:
                    break
            else:  # pragma: no cover - bounded by validated sequence geometry
                raise ResourceError(
                    f"SCUMM costume {self.key!r} animation sequence cannot advance"
                )
            advanced += 1
        return self.data[self._animation_commands + current] & 0x7F

    def decode_pose(self, frame: int, *, facing: int = 180, step: int = 0) -> CostumePose:
        if not 0 <= frame <= 255:
            raise ResourceError(f"SCUMM costume frame {frame} must fit u8")
        if not 0 <= step <= 0xFFFFFFFF:
            raise ResourceError(f"SCUMM costume step {step} must fit u32")
        direction = self.direction_index(facing)
        animation = frame * 4 + direction
        if animation > self.animation_count:
            return CostumePose(frame, direction, direction != 0 or self.mirror, (), ())
        offset_value = _u16(
            self.data, self._data_offsets + animation * 2,
            key=self.key, label=f"animation {animation}",
        )
        if offset_value == 0:
            return CostumePose(frame, direction, direction != 0 or self.mirror, (), ())
        offset = _resource_offset(
            offset_value, size=len(self.data), key=self.key, label=f"animation {animation}",
        )
        mask = _u16(self.data, offset, key=self.key, label=f"animation {animation} mask")
        offset += 2
        cels: list[CostumeCel] = []
        commands: list[tuple[int, int]] = []
        for limb in range(16):
            if not mask & (0x8000 >> limb):
                continue
            sequence = _u16(
                self.data, offset, key=self.key, label=f"animation {animation} limb {limb}",
            )
            offset += 2
            if sequence == 0xFFFF:
                continue
            if offset >= len(self.data):
                raise ResourceError(
                    f"SCUMM costume {self.key!r} animation {animation} limb range is truncated"
                )
            extra = self.data[offset]
            offset += 1
            end = sequence + (extra & 0x7F)
            if end < sequence or self._animation_commands + end >= len(self.data):
                raise ResourceError(f"SCUMM costume {self.key!r} animation command is out of bounds")
            initial = self.data[self._animation_commands + sequence] & 0x7F
            # $79/$7A only alter an already-live limb's stopped bit during a
            # partial decode. A new full-frame decode therefore has no cel.
            if initial in (0x79, 0x7A):
                continue
            command = self._command_at_step(sequence, end, bool(extra & 0x80), step)
            commands.append((limb, command))
            if command != 0x7B:
                cels.append(self._decode_cel(limb, command))
        return CostumePose(
            frame, direction, direction != 0 or self.mirror, tuple(cels), tuple(commands)
        )
