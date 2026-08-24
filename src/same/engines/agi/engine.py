"""A reusable Sierra AGI v2 execution core for SAME.

The logic parser accepts the decoded AGI resource structure used by original
interpreters: a little-endian bytecode length, bytecode, and the optional
message section.  Milestone 0.2 implements the state/control core needed to
prove King's Quest-style logic runs behind the same engine ABI as SCUMM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import struct
from typing import Mapping

from ...capabilities import EngineCapability
from ...engine import Engine, EngineContext, EngineDescriptor, FrameResult, ProbeResult
from ...errors import EngineExecutionError, ResourceError, SaveFormatError
from ...profile import EngineProfile
from ...services import InputEvent, InputEventType

_PICTURE_HEADER = struct.Struct("<4sBHHH")
_PICTURE_MAGIC = b"AGIP"
_PICTURE_VERSION = 1


@dataclass(frozen=True, slots=True)
class AgiLogic:
    bytecode: bytes
    messages: tuple[str, ...]


@dataclass(slots=True)
class AgiState:
    variables: list[int] = field(default_factory=lambda: [0] * 256)
    flags: list[bool] = field(default_factory=lambda: [False] * 256)
    strings: list[str] = field(default_factory=lambda: [""] * 24)
    current_room: int = 0
    previous_room: int = 0
    player_control: bool = True
    ego_x: int = 80
    ego_y: int = 100
    ego_direction: int = 0
    frames: int = 0
    operations: int = 0
    last_opcode: int = 0
    messages: list[str] = field(default_factory=list)


class AgiEngine(Engine):
    descriptor = EngineDescriptor(
        identifier="agi_v2",
        name="SAME Sierra AGI v2",
        version="0.2.0",
        families=("agi-v2", "sierra-agi"),
        required_capabilities=(
            EngineCapability.INDEXED8_SURFACE
            | EngineCapability.DIRTY_RECTS
            | EngineCapability.PALETTE_256
            | EngineCapability.DIGITAL_INPUT
            | EngineCapability.TEXT_INPUT
            | EngineCapability.RANDOM_ACCESS_RESOURCES
            | EngineCapability.TIMER_60HZ
            | EngineCapability.AUDIO_MUSIC
            | EngineCapability.AUDIO_SFX
        ),
        optional_capabilities=(
            EngineCapability.POINTER_INPUT
            | EngineCapability.TILED_VIDEO
            | EngineCapability.SPRITE_OAM
            | EngineCapability.SA1_JOBS
            | EngineCapability.DEBUG_ORACLE
        ),
        save_schema=1,
    )

    def __init__(self) -> None:
        self.state = AgiState()
        self.logic0 = AgiLogic(b"\x00", ())
        self._context: EngineContext | None = None

    @classmethod
    def probe(cls, profile: EngineProfile, services: object) -> ProbeResult:
        del services
        if profile.engine_id != cls.descriptor.identifier:
            return ProbeResult(False, 0, "profile selects another engine")
        try:
            profile.binding(str(profile.options.get("logic0", "logic.0")))
        except KeyError:
            return ProbeResult(False, 20, "profile has no AGI logic 0 resource")
        return ProbeResult(True, 100, "AGI profile has logic 0")

    @staticmethod
    def parse_logic(raw: bytes) -> AgiLogic:
        if len(raw) < 2:
            raise ResourceError("AGI logic resource is shorter than its length word")
        bytecode_size = int.from_bytes(raw[0:2], "little")
        bytecode_end = 2 + bytecode_size
        if bytecode_end > len(raw):
            raise ResourceError(
                f"AGI logic bytecode declares {bytecode_size} bytes, "
                f"but resource has only {len(raw) - 2}"
            )
        bytecode = raw[2:bytecode_end]
        if bytecode_end == len(raw):
            return AgiLogic(bytecode, ())
        if len(raw) < bytecode_end + 3:
            raise ResourceError("AGI logic message section is truncated")
        message_count = raw[bytecode_end]
        messages_size = int.from_bytes(raw[bytecode_end + 1 : bytecode_end + 3], "little")
        offsets_start = bytecode_end + 3
        strings_start = offsets_start + message_count * 2
        section_end = bytecode_end + 1 + messages_size
        if strings_start > len(raw) or section_end > len(raw):
            raise ResourceError("AGI logic message table lies outside the resource")
        messages: list[str] = []
        for index in range(message_count):
            offset = int.from_bytes(
                raw[offsets_start + index * 2 : offsets_start + index * 2 + 2],
                "little",
            )
            if offset == 0:
                messages.append("")
                continue
            absolute = bytecode_end + 1 + offset
            if absolute >= section_end:
                raise ResourceError(f"AGI message {index + 1} offset is invalid")
            end = raw.find(b"\0", absolute, section_end)
            if end < 0:
                raise ResourceError(f"AGI message {index + 1} has no terminator")
            messages.append(raw[absolute:end].decode("latin-1"))
        return AgiLogic(bytecode, tuple(messages))

    def boot(self, context: EngineContext) -> None:
        self._context = context
        logic_key = str(context.profile.options.get("logic0", "logic.0"))
        self.logic0 = self.parse_logic(context.services.resource_read(logic_key))
        self.state = AgiState()
        self.state.current_room = int(context.profile.options.get("initial_room", 0))
        self.state.variables[0] = self.state.current_room
        self._load_picture(context, self.state.current_room, required=False)
        context.services.debug.marker("agi_v2.boot", self.state.current_room)

    def handle_event(self, context: EngineContext, event: InputEvent) -> None:
        del context
        if event.type is InputEventType.DIGITAL:
            directions = {
                "up": 1,
                "up_right": 2,
                "right": 3,
                "down_right": 4,
                "down": 5,
                "down_left": 6,
                "left": 7,
                "up_left": 8,
            }
            if event.action in directions:
                self.state.ego_direction = directions[event.action] if event.pressed else 0
                self.state.variables[6] = self.state.ego_direction
        elif event.type is InputEventType.TEXT:
            self.state.strings[0] += event.text

    def tick(self, context: EngineContext) -> FrameResult:
        self.state.frames += 1
        self._move_ego(context)
        operations = self._run_logic(context, self.logic0)
        self.state.operations += operations
        return FrameResult(
            operations=operations,
            yielded=True,
            halted=False,
            presented=True,
            diagnostics={
                "room": self.state.current_room,
                "ego": [self.state.ego_x, self.state.ego_y],
                "last_opcode": self.state.last_opcode,
            },
        )

    def _run_logic(self, context: EngineContext, logic: AgiLogic) -> int:
        code = logic.bytecode
        pc = 0
        operations = 0
        max_ops = context.profile.max_ops_per_tick
        while pc < len(code):
            if operations >= max_ops:
                raise EngineExecutionError("AGI logic 0 exhausted the per-tick opcode budget")
            opcode = code[pc]
            pc += 1
            self.state.last_opcode = opcode
            operations += 1

            def args(count: int) -> bytes:
                nonlocal pc
                if pc + count > len(code):
                    raise EngineExecutionError(
                        f"AGI opcode ${opcode:02X} at {pc - 1} needs {count} arguments"
                    )
                result = code[pc : pc + count]
                pc += count
                return result

            if opcode == 0x00:  # return
                break
            if opcode == 0x01:  # increment
                (var,) = args(1)
                self.state.variables[var] = min(255, self.state.variables[var] + 1)
            elif opcode == 0x02:  # decrement
                (var,) = args(1)
                self.state.variables[var] = max(0, self.state.variables[var] - 1)
            elif opcode == 0x03:  # assignn
                var, value = args(2)
                self.state.variables[var] = value
            elif opcode == 0x04:  # assignv
                dst, src = args(2)
                self.state.variables[dst] = self.state.variables[src]
            elif opcode == 0x05:  # addn
                var, value = args(2)
                self.state.variables[var] = (self.state.variables[var] + value) & 0xFF
            elif opcode == 0x06:  # addv
                dst, src = args(2)
                self.state.variables[dst] = (
                    self.state.variables[dst] + self.state.variables[src]
                ) & 0xFF
            elif opcode == 0x07:  # subn
                var, value = args(2)
                self.state.variables[var] = (self.state.variables[var] - value) & 0xFF
            elif opcode == 0x08:  # subv
                dst, src = args(2)
                self.state.variables[dst] = (
                    self.state.variables[dst] - self.state.variables[src]
                ) & 0xFF
            elif opcode == 0x09:  # lindirectv
                pointer_var, source_var = args(2)
                self.state.variables[self.state.variables[pointer_var]] = self.state.variables[
                    source_var
                ]
            elif opcode == 0x0A:  # rindirect
                destination, pointer_var = args(2)
                self.state.variables[destination] = self.state.variables[
                    self.state.variables[pointer_var]
                ]
            elif opcode == 0x0B:  # lindirectn
                pointer_var, value = args(2)
                self.state.variables[self.state.variables[pointer_var]] = value
            elif opcode == 0x0C:  # set
                (flag,) = args(1)
                self.state.flags[flag] = True
            elif opcode == 0x0D:  # reset
                (flag,) = args(1)
                self.state.flags[flag] = False
            elif opcode == 0x0E:  # toggle
                (flag,) = args(1)
                self.state.flags[flag] = not self.state.flags[flag]
            elif opcode == 0x0F:  # set.v
                (var,) = args(1)
                self.state.flags[self.state.variables[var]] = True
            elif opcode == 0x10:  # reset.v
                (var,) = args(1)
                self.state.flags[self.state.variables[var]] = False
            elif opcode == 0x11:  # toggle.v
                (var,) = args(1)
                flag = self.state.variables[var]
                self.state.flags[flag] = not self.state.flags[flag]
            elif opcode == 0x12:  # new.room
                (room,) = args(1)
                self._new_room(context, room)
                break
            elif opcode == 0x13:  # new.room.v
                (var,) = args(1)
                self._new_room(context, self.state.variables[var])
                break
            elif opcode == 0x63:  # sound resource, end flag
                sound, end_flag = args(2)
                self.state.flags[end_flag] = False
                context.services.audio.play_sfx(sound)
                self.state.flags[end_flag] = True
            elif opcode == 0x64:  # stop.sound
                context.services.audio.stop_sfx()
            elif opcode == 0x83:  # program.control
                self.state.player_control = False
            elif opcode == 0x84:  # player.control
                self.state.player_control = True
            else:
                raise EngineExecutionError(
                    f"AGI v2 opcode ${opcode:02X} is not implemented (offset {pc - 1})"
                )
        return operations

    def _new_room(self, context: EngineContext, room: int) -> None:
        self.state.previous_room = self.state.current_room
        self.state.current_room = room & 0xFF
        self.state.variables[1] = self.state.previous_room
        self.state.variables[0] = self.state.current_room
        self.state.flags[5] = True  # new-room execution flag in AGI convention
        self._load_picture(context, self.state.current_room, required=False)
        context.services.debug.marker("agi_v2.room", self.state.current_room)

    def _move_ego(self, context: EngineContext) -> None:
        if not self.state.player_control:
            return
        direction = self.state.ego_direction
        dx = (0, 0, 1, 1, 1, 0, -1, -1, -1)[direction]
        dy = (0, -1, -1, 0, 1, 1, 1, 0, -1)[direction]
        self.state.ego_x = max(0, min(context.profile.video.width - 1, self.state.ego_x + dx))
        self.state.ego_y = max(0, min(context.profile.video.height - 1, self.state.ego_y + dy))

    def _load_picture(self, context: EngineContext, picture: int, *, required: bool) -> None:
        template = str(context.profile.options.get("picture_key_template", "picture.{picture}"))
        key = template.format(picture=picture)
        if not context.services.resources.contains(key):
            if required:
                raise ResourceError(f"AGI picture {picture} has no binding {key!r}")
            return
        raw = context.services.resource_read(key)
        if len(raw) < _PICTURE_HEADER.size:
            raise ResourceError(f"AGI cooked picture {key!r} is truncated")
        magic, version, width, height, palette_count = _PICTURE_HEADER.unpack_from(raw, 0)
        if magic != _PICTURE_MAGIC or version != _PICTURE_VERSION:
            raise ResourceError(f"AGI cooked picture {key!r} has unsupported header")
        palette_bytes = palette_count * 3
        pixel_offset = _PICTURE_HEADER.size + palette_bytes
        expected = pixel_offset + width * height
        if len(raw) != expected:
            raise ResourceError(
                f"AGI cooked picture {key!r} is {len(raw)} bytes; expected {expected}"
            )
        if width != context.profile.video.width or height != context.profile.video.height:
            raise ResourceError(
                f"AGI picture is {width}x{height}; profile is "
                f"{context.profile.video.width}x{context.profile.video.height}"
            )
        colors = [
            tuple(raw[index : index + 3])
            for index in range(_PICTURE_HEADER.size, pixel_offset, 3)
        ]
        context.services.video.surface.set_palette(0, colors)
        context.services.video.surface.blit(
            raw[pixel_offset:], source_width=width, source_height=height
        )

    def save_state(self, context: EngineContext) -> bytes:
        del context
        data = {
            "variables": self.state.variables,
            "flags": [index for index, value in enumerate(self.state.flags) if value],
            "strings": self.state.strings,
            "room": self.state.current_room,
            "previous_room": self.state.previous_room,
            "player_control": self.state.player_control,
            "ego": [self.state.ego_x, self.state.ego_y, self.state.ego_direction],
            "frames": self.state.frames,
            "operations": self.state.operations,
        }
        return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def load_state(self, context: EngineContext, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SaveFormatError(f"invalid AGI save payload: {exc}") from exc
        if not isinstance(data, dict):
            raise SaveFormatError("AGI save payload root must be an object")

        variables_raw = data.get("variables")
        if not isinstance(variables_raw, list) or len(variables_raw) != 256:
            raise SaveFormatError("AGI save has the wrong variable count")
        variables = [int(value) for value in variables_raw]
        if any(value < 0 or value > 255 for value in variables):
            raise SaveFormatError("AGI save variable is outside byte range")

        flags = [False] * 256
        flags_raw = data.get("flags", [])
        if not isinstance(flags_raw, list):
            raise SaveFormatError("AGI save flag list must be an array")
        for raw_index in flags_raw:
            index = int(raw_index)
            if not 0 <= index < len(flags):
                raise SaveFormatError(f"AGI save flag index {index} is invalid")
            flags[index] = True

        strings_raw = data.get("strings")
        if not isinstance(strings_raw, list) or len(strings_raw) != 24:
            raise SaveFormatError("AGI save has the wrong string-slot count")
        strings = [str(value) for value in strings_raw]

        room = int(data.get("room", -1))
        previous_room = int(data.get("previous_room", -1))
        if not 0 <= room <= 255 or not 0 <= previous_room <= 255:
            raise SaveFormatError("AGI save room numbers must be in 0..255")
        ego = data.get("ego")
        if not isinstance(ego, list) or len(ego) != 3:
            raise SaveFormatError("AGI save ego state must contain x, y, and direction")
        ego_x, ego_y, ego_direction = map(int, ego)
        if not (
            0 <= ego_x < context.profile.video.width
            and 0 <= ego_y < context.profile.video.height
        ):
            raise SaveFormatError("AGI save ego position lies outside the configured surface")
        if not 0 <= ego_direction <= 8:
            raise SaveFormatError("AGI save ego direction must be in 0..8")
        frames = int(data.get("frames", 0))
        operations = int(data.get("operations", 0))
        if frames < 0 or operations < 0:
            raise SaveFormatError("AGI save counters must not be negative")

        self.state.variables = variables
        self.state.flags = flags
        self.state.strings = strings
        self.state.current_room = room
        self.state.previous_room = previous_room
        self.state.player_control = bool(data.get("player_control", True))
        self.state.ego_x = ego_x
        self.state.ego_y = ego_y
        self.state.ego_direction = ego_direction
        self.state.frames = frames
        self.state.operations = operations
        self._load_picture(context, self.state.current_room, required=False)

    def inspect_state(self) -> Mapping[str, object]:
        return {
            "room": self.state.current_room,
            "previous_room": self.state.previous_room,
            "ego": [self.state.ego_x, self.state.ego_y, self.state.ego_direction],
            "player_control": self.state.player_control,
            "variables": {
                str(index): value
                for index, value in enumerate(self.state.variables)
                if value != 0
            },
            "flags": [index for index, value in enumerate(self.state.flags) if value],
            "strings": {
                str(index): value
                for index, value in enumerate(self.state.strings)
                if value
            },
            "frames": self.state.frames,
            "operations": self.state.operations,
            "last_opcode": self.state.last_opcode,
        }
