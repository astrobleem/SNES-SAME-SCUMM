"""A reusable SCUMM v5 execution core for SAME.

This is deliberately not Monkey-Island-specific.  It implements a useful,
verified subset of the real SCUMM v5 opcode map and exposes explicit gaps.  The
public SNES-SuperMonkeyIsland project is known-incomplete donor material, not a
semantic oracle. This Python implementation is the executable host reference
for independent differential fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from typing import Callable, Mapping

from ...capabilities import EngineCapability
from ...engine import Engine, EngineContext, EngineDescriptor, FrameResult, ProbeResult
from ...errors import EngineExecutionError, ProfileValidationError, ResourceError, SaveFormatError
from ...profile import EngineProfile
from ...services import InputEvent
from .audio import ScummV5AudioAdapter
from .input import ScummV5InputAdapter
from .policy import ScummV5GamePolicy, parse_game_policy
from .resources import LucasartsScummV5ResourceProvider
from .room import ScummV5RoomAdapter, ScummV5RoomObject, decode_room
from .text import ScummTextGlyph, control_argument_count, decode_scumm_v5_text
from .video import ScummV5Charset, ScummV5VideoAdapter

_MAX_SCRIPT_SLOTS = 25
_LOCAL_VARIABLE_COUNT = 32
_MAX_STRING_BYTES = 255
_ROOM_SCALE_SLOTS = 4
_RANDOM_SEED = 0xACE1
_RESOURCE_KINDS = ("script", "sound", "costume", "room", "charset")
_LOCKABLE_RESOURCE_KINDS = _RESOURCE_KINDS[:4]
_MAX_ACTORS = 32
_MAX_CLASS_OBJECTS = 512
_MAX_VERBS = 256
_MAX_SAVED_VERBS = 64
_MAX_VERB_NAME_BYTES = 64
_MAX_CUTSCENE_DEPTH = 4  # plus the canonical record-zero override sentinel
_MAX_SENTENCES = 6
_MAX_SOUND_COMMANDS = 16
_MAX_SOUND_HISTORY = 32
_MAX_LOCAL_OBJECTS = 200
_MAX_OBJECT_STATES = 4096
_MAX_PRINT_MESSAGES = 32


@dataclass(slots=True)
class ScriptSlot:
    resource_key: str
    program: bytes
    number: int = 0
    pc: int = 0
    delay: int = 0
    active: bool = True
    yielded: bool = False
    locals: list[int] = field(default_factory=lambda: [0] * 32)
    freeze_resistant: bool = False
    recursive: bool = False
    freeze_count: int = 0
    cutscene_override: int = 0
    did_exec: bool = False
    room: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "resource": self.resource_key,
            "number": self.number,
            "pc": self.pc,
            "delay": self.delay,
            "active": self.active,
            "yielded": self.yielded,
            "locals": self.locals,
            "freeze_resistant": self.freeze_resistant,
            "recursive": self.recursive,
            "freeze_count": self.freeze_count,
            "cutscene_override": self.cutscene_override,
            "room": self.room,
        }


@dataclass(slots=True)
class CutsceneState:
    data: int = 0
    override_pc: int | None = None
    override_slot: int | None = None

    def to_dict(self) -> dict[str, int | None]:
        return {
            "data": self.data,
            "override_pc": self.override_pc,
            "override_slot": self.override_slot,
        }


@dataclass(slots=True)
class SentenceState:
    verb: int
    object_a: int
    object_b: int
    freeze_count: int = 0

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "verb": self.verb,
            "object_a": self.object_a,
            "object_b": self.object_b,
            "preposition": self.object_b != 0,
            "freeze_count": self.freeze_count,
        }


@dataclass(slots=True)
class PrintSlotState:
    x: int = 2
    y: int = 5
    right: int = 319
    height: int = 0
    color: int = 15
    charset: int = 0
    center: bool = False
    overhead: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "position": [self.x, self.y],
            "right": self.right,
            "height": self.height,
            "color": self.color,
            "charset": self.charset,
            "center": self.center,
            "overhead": self.overhead,
        }


@dataclass(slots=True)
class PrintMessageState:
    actor: int
    slot: int
    style: PrintSlotState
    raw: bytearray

    def to_dict(self) -> dict[str, object]:
        return {
            "actor": self.actor,
            "slot": self.slot,
            **self.style.to_dict(),
            "raw": list(self.raw),
            "tokens": [token.to_dict() for token in decode_scumm_v5_text(self.raw)],
        }


@dataclass(slots=True)
class RoomObjectState:
    object_id: int
    x: int
    y: int
    width: int
    height: int
    walk_x: int
    walk_y: int
    state: int = 0

    @classmethod
    def from_resource(cls, item: ScummV5RoomObject, state: int) -> "RoomObjectState":
        return cls(
            item.object_id,
            item.x,
            item.y,
            item.width,
            item.height,
            item.walk_x,
            item.walk_y,
            state,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "position": [self.x, self.y],
            "size": [self.width, self.height],
            "walk": [self.walk_x, self.walk_y],
            "state": self.state,
        }


@dataclass(slots=True)
class RoomOpsState:
    room_width: int = 320
    scroll_min_x: int = 160
    scroll_max_x: int = 160
    screen_top: int = 0
    screen_bottom: int = 200
    shake_enabled: bool = False
    scale_slots: dict[int, tuple[int, int, int, int]] = field(default_factory=dict)
    intensity: tuple[int, int, int, int, int] = (255, 255, 255, 0, 255)
    fade_effect: int = 0
    rgb_intensity: tuple[int, int, int, int, int] = (255, 255, 255, 0, 255)
    shadow: tuple[int, int, int, int, int] = (255, 255, 255, 0, 255)
    transform: tuple[int, int, int, int] = (0, 0, 0, 0)
    cycle_delays: list[int] = field(default_factory=lambda: [0] * 16)
    palette_overrides: dict[int, tuple[int, int, int]] = field(default_factory=dict)
    save_load_request: tuple[int, int] = (0, 0)
    auxiliary_files: dict[str, bytearray] = field(default_factory=dict)


@dataclass(slots=True)
class ResourceOpsState:
    loaded: dict[str, set[int]] = field(
        default_factory=lambda: {kind: set() for kind in _RESOURCE_KINDS}
    )
    locked: dict[str, set[int]] = field(
        default_factory=lambda: {kind: set() for kind in _LOCKABLE_RESOURCE_KINDS}
    )
    last_object: tuple[int, int] | None = None


@dataclass(slots=True)
class ActorState:
    costume: int = 0
    walk_speed: tuple[int, int] = (8, 2)
    sound: int = 0
    init_frame: int = 1
    walk_frame: int = 2
    stand_frame: int = 3
    talk_frames: tuple[int, int] = (4, 5)
    elevation: int = 0
    palette: dict[int, int] = field(default_factory=dict)
    talk_color: int = 15
    name: bytearray = field(default_factory=lambda: bytearray(b"\0"))
    width: int = 24
    scale: tuple[int, int] = (255, 255)
    box_scale: int = 255
    force_clip: int = 0
    ignore_boxes: bool = False
    animation_speed: int = 0
    shadow: int = 0
    animation: int = 0

    def reset_defaults(self) -> None:
        """Mirror Actor::initActor(0), retaining costume, palette, and name."""
        self.walk_speed = (8, 2)
        self.sound = 0
        self.init_frame = 1
        self.walk_frame = 2
        self.stand_frame = 3
        self.talk_frames = (4, 5)
        self.elevation = 0
        self.talk_color = 15
        self.width = 24
        self.scale = (255, 255)
        self.box_scale = 255
        self.force_clip = 0
        self.ignore_boxes = False
        self.animation_speed = 0
        self.shadow = 0
        self.animation = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "costume": self.costume,
            "walk_speed": list(self.walk_speed),
            "sound": self.sound,
            "frames": [self.init_frame, self.walk_frame, self.stand_frame, *self.talk_frames],
            "elevation": self.elevation,
            "palette": {str(index): color for index, color in sorted(self.palette.items())},
            "talk_color": self.talk_color,
            "name": bytes(self.name).hex(),
            "width": self.width,
            "scale": list(self.scale),
            "box_scale": self.box_scale,
            "force_clip": self.force_clip,
            "ignore_boxes": self.ignore_boxes,
            "animation_speed": self.animation_speed,
            "shadow": self.shadow,
            "animation": self.animation,
        }


@dataclass(slots=True)
class VerbState:
    color: int = 0
    hicolor: int = 0
    dimcolor: int = 0
    background_color: int = 0
    kind: str = "text"
    charset: int = 0
    mode: int = 0
    save_id: int = 0
    key: int = 0
    center: bool = False
    position: tuple[int, int] = (0, 0)
    original_left: int = 0
    image_index: int = 0
    image_source: tuple[int, int] | None = None
    name: bytearray | None = None

    def apply_new(self, charset: int) -> None:
        """Mirror SO_VERB_NEW fields while retaining slot-owned geometry/name."""
        self.color = 2
        self.hicolor = 0
        self.dimcolor = 8
        self.kind = "text"
        self.charset = charset
        self.mode = 0
        self.save_id = 0
        self.key = 0
        self.center = False
        self.image_index = 0
        self.image_source = None

    def to_dict(self) -> dict[str, object]:
        return {
            "color": self.color,
            "hicolor": self.hicolor,
            "dimcolor": self.dimcolor,
            "background_color": self.background_color,
            "kind": self.kind,
            "charset": self.charset,
            "mode": self.mode,
            "save_id": self.save_id,
            "key": self.key,
            "center": self.center,
            "position": list(self.position),
            "original_left": self.original_left,
            "image_index": self.image_index,
            "image_source": None if self.image_source is None else list(self.image_source),
            "name": None if self.name is None else bytes(self.name).hex(),
        }


@dataclass(slots=True)
class ScummState:
    variables: list[int] = field(default_factory=lambda: [0] * 2048)
    bit_variables: list[bool] = field(default_factory=lambda: [False] * 4096)
    scripts: list[ScriptSlot] = field(default_factory=list)
    current_room: int = 0
    camera_x: int = 0
    camera_y: int = 0
    camera_follow_actor: int | None = None
    cursor_x: int = 128
    cursor_y: int = 112
    cursor_visible: bool = True
    cursor_state: int = 1
    user_input_state: int = 1
    cursor_image: tuple[int, int] = (0, 0)
    cursor_hotspot: tuple[int, int, int] = (0, 0, 0)
    cursor_id: int = 0
    charset_id: int = 0
    charset_colors: list[int] = field(default_factory=list)
    strings: dict[int, bytearray] = field(default_factory=dict)
    room_ops: RoomOpsState = field(default_factory=RoomOpsState)
    random_state: int = _RANDOM_SEED
    resource_mapper: list[int] = field(default_factory=lambda: [0] * 128)
    resource_ops: ResourceOpsState = field(default_factory=ResourceOpsState)
    actors: dict[int, ActorState] = field(default_factory=dict)
    object_classes: dict[int, set[int]] = field(default_factory=dict)
    object_states: dict[int, int] = field(default_factory=dict)
    room_objects: dict[int, RoomObjectState] = field(default_factory=dict)
    object_draw_queue: list[int] = field(default_factory=list)
    verbs: dict[int, VerbState] = field(default_factory=dict)
    saved_verbs: list[tuple[int, VerbState]] = field(default_factory=list)
    cutscene_sentinel: CutsceneState = field(default_factory=CutsceneState)
    cutscenes: list[CutsceneState] = field(default_factory=list)
    cutscene_script_index: int | None = None
    sentences: list[SentenceState] = field(default_factory=list)
    sound_queue: list[list[int]] = field(default_factory=list)
    sound_history: list[list[int]] = field(default_factory=list)
    sound_result: int = 0
    print_slots: list[PrintSlotState] = field(
        default_factory=lambda: [PrintSlotState() for _ in range(4)]
    )
    print_messages: list[PrintMessageState] = field(default_factory=list)
    operations: int = 0
    frames: int = 0
    last_opcode: int = 0
    halted: bool = False
    room_hash: str = ""


class ScummV5Engine(Engine):
    descriptor = EngineDescriptor(
        identifier="scumm_v5",
        name="SAME native SCUMM v5",
        version="0.2.0",
        families=("scumm-v5",),
        required_capabilities=(
            EngineCapability.INDEXED8_SURFACE
            | EngineCapability.DIRTY_RECTS
            | EngineCapability.PALETTE_256
            | EngineCapability.DIGITAL_INPUT
            | EngineCapability.POINTER_INPUT
            | EngineCapability.RANDOM_ACCESS_RESOURCES
            | EngineCapability.TIMER_60HZ
            | EngineCapability.AUDIO_MUSIC
            | EngineCapability.AUDIO_SFX
        ),
        optional_capabilities=(
            EngineCapability.AUDIO_SPEECH
            | EngineCapability.TILED_VIDEO
            | EngineCapability.SPRITE_OAM
            | EngineCapability.Z_MASK
            | EngineCapability.HDMA
            | EngineCapability.SA1_JOBS
            | EngineCapability.MSU1_STREAM
            | EngineCapability.DEBUG_ORACLE
        ),
        save_schema=2,
    )

    def __init__(self) -> None:
        self.state = ScummState()
        self._context: EngineContext | None = None
        self._policy: ScummV5GamePolicy | None = None
        self._input: ScummV5InputAdapter | None = None
        self._video: ScummV5VideoAdapter | ScummV5RoomAdapter | None = None
        self._audio: ScummV5AudioAdapter | None = None
        self._room_scripts: dict[int, bytes] = {}
        self._handlers: dict[int, Callable[[ScriptSlot, EngineContext], bool]] = {}
        self._install_handlers()
        self._tick_operations = 0
        self._tick_max_ops = 0
        self._in_tick = False

    @classmethod
    def probe(cls, profile: EngineProfile, services: object) -> ProbeResult:
        del services
        if profile.engine_id != cls.descriptor.identifier:
            return ProbeResult(False, 0, "profile selects another engine")
        try:
            policy = parse_game_policy(profile)
        except ProfileValidationError as exc:
            return ProbeResult(False, 10, f"invalid SCUMM game policy: {exc}")
        boot_number = int(profile.options.get("boot_script_number", 1))
        boot_key = str(
            profile.options.get(
                "boot_script",
                policy.script_key_template.format(script=boot_number)
                if policy is not None and policy.resource_format == "lucasarts_scumm_v5"
                else "script.boot",
            )
        )
        try:
            profile.binding(boot_key)
        except KeyError:
            raw_boot = (
                policy is not None
                and policy.resource_format == "lucasarts_scumm_v5"
                and boot_key == policy.script_key_template.format(script=boot_number)
            )
            if not raw_boot:
                return ProbeResult(False, 20, "profile has no boot SCUMM script resource")
        for option in ("initial_scene", "cursor_resource", "audio_manifest"):
            key = profile.options.get(option)
            if key is None:
                continue
            try:
                profile.binding(str(key))
            except KeyError:
                return ProbeResult(False, 30, f"SCUMM option {option} names unbound resource")
        return ProbeResult(True, 100, "SCUMM v5 profile has a boot script")

    def _install_handlers(self) -> None:
        for opcode in (0x00, 0xA0):
            self._handlers[opcode] = self._op_stop
        self._handlers[0x80] = self._op_break_here
        self._handlers[0x18] = self._op_jump_relative
        for opcode in (0x1A, 0x9A):
            self._handlers[opcode] = self._op_move
        self._handlers[0x46] = self._op_increment
        self._handlers[0xC6] = self._op_decrement
        for opcode in (0x5A, 0xDA):
            self._handlers[opcode] = self._op_add
        for opcode in (0x3A, 0xBA):
            self._handlers[opcode] = self._op_subtract
        for opcode in (0x1B, 0x9B):
            self._handlers[opcode] = self._op_multiply
        for opcode in (0x5B, 0xDB):
            self._handlers[opcode] = self._op_divide
        for opcode in (0x17, 0x97):
            self._handlers[opcode] = self._op_and
        for opcode in (0x57, 0xD7):
            self._handlers[opcode] = self._op_or
        self._handlers[0x28] = self._op_equal_zero
        self._handlers[0xA8] = self._op_not_equal_zero
        for opcode, operation in (
            (0x48, "eq"),
            (0xC8, "eq"),
            (0x08, "ne"),
            (0x88, "ne"),
            (0x44, "lt"),
            (0xC4, "lt"),
            (0x78, "gt"),
            (0xF8, "gt"),
            (0x38, "le"),
            (0xB8, "le"),
            (0x04, "ge"),
            (0x84, "ge"),
        ):
            self._handlers[opcode] = self._comparison(operation)
        self._handlers[0x2E] = self._op_delay
        self._handlers[0x2B] = self._op_delay_variable
        for opcode in (0x72, 0xF2):
            self._handlers[opcode] = self._op_load_room
        for opcode in (0x02, 0x82):
            self._handlers[opcode] = self._op_start_music
        self._handlers[0x20] = self._op_stop_music
        for opcode in (0x1C, 0x9C):
            self._handlers[opcode] = self._op_start_sound
        for opcode in (0x3C, 0xBC):
            self._handlers[opcode] = self._op_stop_sound
        self._handlers[0x4C] = self._op_sound_kludge
        for opcode in (0x32, 0xB2):
            self._handlers[opcode] = self._op_set_camera
        for opcode in (0x0A, 0x2A, 0x4A, 0x6A, 0x8A, 0xAA, 0xCA, 0xEA):
            self._handlers[opcode] = self._op_start_script
        for opcode in (0x62, 0xE2):
            self._handlers[opcode] = self._op_stop_script
        for opcode in (0x60, 0xE0):
            self._handlers[opcode] = self._op_freeze_scripts
        for opcode in (0x68, 0xE8):
            self._handlers[opcode] = self._op_is_script_running
        for opcode in (0x42, 0xC2):
            self._handlers[opcode] = self._op_chain_script
        for opcode in (0x26, 0xA6):
            self._handlers[opcode] = self._op_set_var_range
        for opcode in (0x33, 0x73, 0xB3, 0xF3):
            self._handlers[opcode] = self._op_room_ops
        for opcode in (0x16, 0x96):
            self._handlers[opcode] = self._op_get_random
        self._handlers[0xCC] = self._op_pseudo_room
        for opcode in (0x0C, 0x8C):
            self._handlers[opcode] = self._op_resource_routines
        for opcode in (0x13, 0x53, 0x93, 0xD3):
            self._handlers[opcode] = self._op_actor_ops
        for opcode in (0x11, 0x51, 0x91, 0xD1):
            self._handlers[opcode] = self._op_animate_actor
        for opcode in (0x52, 0xD2):
            self._handlers[opcode] = self._op_actor_follow_camera
        for opcode in (0x5D, 0xDD):
            self._handlers[opcode] = self._op_set_class
        for opcode in (0x7A, 0xFA):
            self._handlers[opcode] = self._op_verb_ops
        self._handlers[0xAB] = self._op_save_restore_verbs
        self._handlers[0xAC] = self._op_expression
        self._handlers[0x40] = self._op_cutscene
        self._handlers[0xC0] = self._op_end_cutscene
        self._handlers[0x58] = self._op_begin_override
        for opcode in (0x19, 0x39, 0x59, 0x79, 0x99, 0xB9, 0xD9, 0xF9):
            self._handlers[opcode] = self._op_do_sentence
        for opcode in (0x05, 0x85):
            self._handlers[opcode] = self._op_draw_object
        for opcode in (0x14, 0x94):
            self._handlers[opcode] = self._op_print
        self._handlers[0xD8] = self._op_print_ego
        self._handlers[0x27] = self._op_string_ops
        self._handlers[0x2C] = self._op_cursor_command

    def boot(self, context: EngineContext) -> None:
        self._context = context
        self._policy = parse_game_policy(context.profile)
        if (
            self._policy is not None
            and self._policy.resource_format == "lucasarts_scumm_v5"
            and not isinstance(context.services.resources, LucasartsScummV5ResourceProvider)
        ):
            context.services.resources = LucasartsScummV5ResourceProvider(
                context.services.resources, self._policy
            )
        boot_number = int(context.profile.options.get("boot_script_number", 1))
        boot_key = str(
            context.profile.options.get(
                "boot_script",
                self._script_key(boot_number) if self._policy is not None else "script.boot",
            )
        )
        program = context.services.resource_read(boot_key)
        if not program:
            raise ResourceError(f"SCUMM boot script {boot_key!r} is empty")
        logical_width = context.profile.video.logical_width or context.profile.video.width
        logical_height = context.profile.video.logical_height or context.profile.video.height
        self._input = ScummV5InputAdapter(logical_width, logical_height)
        self.state = ScummState(
            cursor_x=self._input.state.cursor_x,
            cursor_y=self._input.state.cursor_y,
            room_ops=RoomOpsState(
                room_width=logical_width,
                scroll_min_x=logical_width // 2,
                scroll_max_x=logical_width // 2,
                screen_bottom=logical_height,
            ),
        )
        self._room_scripts = {}
        for print_slot in self.state.print_slots:
            print_slot.right = logical_width - 1
        if not 0 <= boot_number <= 255:
            raise ResourceError("SCUMM boot script number must be in 0..255")
        self.state.scripts.append(ScriptSlot(boot_key, program, number=boot_number))
        audio_manifest = context.profile.options.get("audio_manifest")
        self._audio = (
            None
            if audio_manifest is None
            else ScummV5AudioAdapter(context, str(audio_manifest))
        )
        initial_speech = context.profile.options.get("initial_speech")
        if initial_speech is not None:
            if self._audio is None:
                raise ResourceError("SCUMM initial_speech requires an audio_manifest")
            self._audio.play_speech(int(initial_speech))
        scene_key = context.profile.options.get("initial_scene")
        if scene_key is not None:
            self._video = ScummV5VideoAdapter(context)
            cursor_key = context.profile.options.get("cursor_resource")
            self._video.render(
                str(scene_key),
                cursor_key=None if cursor_key is None else str(cursor_key),
            )
            self._video.move_cursor(self.state.cursor_x, self.state.cursor_y)
        else:
            self._video = None
            context.services.video.move_cursor(self.state.cursor_x, self.state.cursor_y)
        context.services.video.show_cursor(True)
        initial_room = int(context.profile.options.get("initial_room", 0))
        self._load_room(context, initial_room, required=False)
        context.services.debug.marker("scumm_v5.boot", initial_room)

    def _script_key(self, number: int) -> str:
        if self._context is not None and "script_key_template" in self._context.profile.options:
            template = str(self._context.profile.options["script_key_template"])
        elif self._policy is not None:
            template = self._policy.script_key_template
        else:
            template = "script.{script}"
        return template.format(script=number)

    def _room_key(self, room: int) -> str:
        if self._context is not None and "room_key_template" in self._context.profile.options:
            template = str(self._context.profile.options["room_key_template"])
        elif self._policy is not None:
            template = self._policy.room_key_template
        else:
            template = "room.{room}"
        return template.format(room=room)

    def _resource_key(self, kind: str, resource_id: int) -> str:
        if kind == "script":
            return self._script_key(resource_id)
        if kind == "room":
            return self._room_key(resource_id)
        placeholder = kind
        option = f"{kind}_key_template"
        if self._context is not None and option in self._context.profile.options:
            template = str(self._context.profile.options[option])
        elif self._policy is not None:
            template = str(getattr(self._policy, option))
        else:
            template = f"{kind}.{{{placeholder}}}"
        return template.format(**{placeholder: resource_id})

    def handle_event(self, context: EngineContext, event: InputEvent) -> None:
        if self._input is None:
            raise EngineExecutionError("SCUMM input adapter is unavailable before boot")
        logical = self._input.consume(event)
        self.state.cursor_x = logical.cursor_x
        self.state.cursor_y = logical.cursor_y
        if self._video is None:
            context.services.video.move_cursor(logical.cursor_x, logical.cursor_y)
        else:
            self._video.move_cursor(logical.cursor_x, logical.cursor_y)
        if "skip" in logical.commands:
            self._abort_cutscene()

    def tick(self, context: EngineContext) -> FrameResult:
        if self._input is not None:
            self._input.begin_frame(context.services.clock.frame)
        self.state.frames += 1
        self._tick_operations = 0
        self._tick_max_ops = context.profile.max_ops_per_tick
        self._in_tick = True
        for slot in self.state.scripts:
            slot.did_exec = False
        try:
            for slot in self.state.scripts:
                if not slot.active or slot.did_exec or slot.freeze_count:
                    continue
                if slot.delay:
                    slot.delay -= 1
                    slot.did_exec = True
                    continue
                slot.yielded = False
                self._execute_slot(slot, context)
            self._check_and_run_sentence_script(context)
        finally:
            self._in_tick = False
        if self._audio is not None:
            self._audio.tick()
        operations = self._tick_operations
        self.state.operations += operations
        self.state.halted = bool(self.state.scripts) and not any(
            slot.active for slot in self.state.scripts
        )
        # A real SCUMM frame may only dirty small rectangles.  Presenting here
        # preserves that contract; the VideoService keeps the actual dirty list.
        return FrameResult(
            operations=operations,
            yielded=any(slot.yielded for slot in self.state.scripts if slot.active),
            halted=self.state.halted,
            presented=True,
            diagnostics={
                "room": self.state.current_room,
                "active_scripts": sum(slot.active for slot in self.state.scripts),
                "last_opcode": self.state.last_opcode,
            },
        )

    def _execute_slot(self, slot: ScriptSlot, context: EngineContext) -> None:
        slot.did_exec = True
        while slot.active and not slot.yielded:
            if self._tick_operations >= self._tick_max_ops:
                raise EngineExecutionError(
                    f"SCUMM script {slot.resource_key!r} exhausted the per-tick opcode budget"
                )
            self._tick_operations += 1
            self._step(slot, context)

    def _step(self, slot: ScriptSlot, context: EngineContext) -> None:
        if slot.pc >= len(slot.program):
            slot.active = False
            return
        opcode = self._u8(slot)
        self.state.last_opcode = opcode
        try:
            handler = self._handlers[opcode]
        except KeyError as exc:
            raise EngineExecutionError(
                f"SCUMM v5 opcode ${opcode:02X} is not implemented "
                f"(script {slot.resource_key}, offset ${slot.pc - 1:04X})"
            ) from exc
        handler(slot, context)

    @staticmethod
    def _ensure(slot: ScriptSlot, count: int) -> None:
        if slot.pc + count > len(slot.program):
            raise EngineExecutionError(
                f"SCUMM script {slot.resource_key!r} ended at offset {slot.pc} "
                f"while reading {count} bytes"
            )

    def _u8(self, slot: ScriptSlot) -> int:
        self._ensure(slot, 1)
        value = slot.program[slot.pc]
        slot.pc += 1
        return value

    def _u16(self, slot: ScriptSlot) -> int:
        self._ensure(slot, 2)
        value = int.from_bytes(slot.program[slot.pc : slot.pc + 2], "little")
        slot.pc += 2
        return value

    def _s16(self, slot: ScriptSlot) -> int:
        value = self._u16(slot)
        return value - 0x10000 if value & 0x8000 else value

    def _result_var(self, slot: ScriptSlot) -> int:
        reference = self._u16(slot)
        if reference & 0x2000:
            index_reference = self._u16(slot)
            base = reference & 0x0FFF
            index = (
                self._read_var(slot, index_reference & ~0x2000)
                if index_reference & 0x2000
                else index_reference & 0x0FFF
            )
            reference = (reference & 0xC000) | (base + index)
        self._check_var(slot, reference)
        return reference

    def _check_var(self, slot: ScriptSlot, reference: int) -> None:
        if reference & 0x8000:
            index = reference & 0x0FFF
            if index >= len(self.state.bit_variables):
                raise EngineExecutionError(f"SCUMM bit variable {index} is outside the state array")
            return
        if reference & 0x4000:
            index = reference & 0x0FFF
            if index >= len(slot.locals):
                raise EngineExecutionError(
                    f"SCUMM local variable {index} is outside the script slot"
                )
            return
        if not 0 <= reference < len(self.state.variables):
            raise EngineExecutionError(f"SCUMM variable {reference} is outside the state array")

    def _read_var(self, slot: ScriptSlot, reference: int) -> int:
        self._check_var(slot, reference)
        if reference & 0x8000:
            return int(self.state.bit_variables[reference & 0x0FFF])
        if reference & 0x4000:
            return slot.locals[reference & 0x0FFF]
        return self.state.variables[reference]

    def _write_var(self, slot: ScriptSlot, reference: int, value: int) -> None:
        self._check_var(slot, reference)
        if reference & 0x8000:
            self.state.bit_variables[reference & 0x0FFF] = bool(value)
            return
        value &= 0xFFFF
        value = value - 0x10000 if value & 0x8000 else value
        if reference & 0x4000:
            slot.locals[reference & 0x0FFF] = value
        else:
            self.state.variables[reference] = value

    def _var_or_direct_byte(self, slot: ScriptSlot, mask: int) -> int:
        if self.state.last_opcode & mask:
            return self._read_var(slot, self._u16(slot)) & 0xFF
        return self._u8(slot)

    def _byte_for_flags(self, slot: ScriptSlot, flags: int, mask: int) -> int:
        if flags & mask:
            return self._read_var(slot, self._u16(slot)) & 0xFF
        return self._u8(slot)

    def _word_for_flags(self, slot: ScriptSlot, flags: int, mask: int) -> int:
        if flags & mask:
            return self._read_var(slot, self._u16(slot))
        return self._s16(slot)

    def _var_or_direct_word(self, slot: ScriptSlot, mask: int) -> int:
        if self.state.last_opcode & mask:
            return self._read_var(slot, self._u16(slot))
        return self._s16(slot)

    def _jump_condition(self, slot: ScriptSlot, condition: bool) -> None:
        offset = self._s16(slot)
        # SCUMM's helper advances by the relative offset when the condition is
        # false.  The true path falls through.
        if not condition:
            destination = slot.pc + offset
            if not 0 <= destination <= len(slot.program):
                raise EngineExecutionError(
                    f"SCUMM relative jump leaves script: {slot.pc} + {offset}"
                )
            slot.pc = destination

    def _op_stop(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        if slot.cutscene_override:
            raise EngineExecutionError(
                f"SCUMM script {slot.resource_key!r} ended with active cutscene/override "
                f"depth {slot.cutscene_override}"
            )
        slot.active = False
        slot.yielded = False
        slot.number = 0
        slot.freeze_resistant = False
        slot.recursive = False
        slot.freeze_count = 0
        return True

    @staticmethod
    def _op_break_here(slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        slot.yielded = True
        return True

    def _op_jump_relative(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        offset = self._s16(slot)
        destination = slot.pc + offset
        if not 0 <= destination <= len(slot.program):
            raise EngineExecutionError(
                f"SCUMM jump leaves script: {slot.pc} + {offset}"
            )
        slot.pc = destination
        return False

    def _op_move(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        result = self._result_var(slot)
        self._write_var(slot, result, self._var_or_direct_word(slot, 0x80))
        return False

    def _op_increment(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        result = self._result_var(slot)
        self._write_var(slot, result, self._read_var(slot, result) + 1)
        return False

    def _op_decrement(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        result = self._result_var(slot)
        self._write_var(slot, result, self._read_var(slot, result) - 1)
        return False

    def _binary_arithmetic(
        self,
        slot: ScriptSlot,
        operation: Callable[[int, int], int],
    ) -> None:
        result = self._result_var(slot)
        rhs = self._var_or_direct_word(slot, 0x80)
        self._write_var(slot, result, operation(self._read_var(slot, result), rhs))

    def _op_add(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        self._binary_arithmetic(slot, lambda lhs, rhs: lhs + rhs)
        return False

    def _op_subtract(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        self._binary_arithmetic(slot, lambda lhs, rhs: lhs - rhs)
        return False

    def _op_multiply(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        self._binary_arithmetic(slot, lambda lhs, rhs: lhs * rhs)
        return False

    def _op_divide(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        def divide(lhs: int, rhs: int) -> int:
            if rhs == 0:
                raise EngineExecutionError("SCUMM division by zero")
            return int(lhs / rhs)
        self._binary_arithmetic(slot, divide)
        return False

    def _op_and(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        self._binary_arithmetic(slot, lambda lhs, rhs: lhs & rhs)
        return False

    def _op_or(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        self._binary_arithmetic(slot, lambda lhs, rhs: lhs | rhs)
        return False

    def _op_equal_zero(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        self._jump_condition(slot, self._read_var(slot, self._u16(slot)) == 0)
        return False

    def _op_not_equal_zero(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        self._jump_condition(slot, self._read_var(slot, self._u16(slot)) != 0)
        return False

    def _comparison(self, operation: str) -> Callable[[ScriptSlot, EngineContext], bool]:
        def handler(slot: ScriptSlot, context: EngineContext) -> bool:
            del context
            lhs = self._read_var(slot, self._u16(slot))
            rhs = self._var_or_direct_word(slot, 0x80)
            conditions = {
                "eq": lhs == rhs,
                "ne": lhs != rhs,
                "lt": rhs < lhs,
                "gt": rhs > lhs,
                "le": rhs <= lhs,
                "ge": rhs >= lhs,
            }
            self._jump_condition(slot, conditions[operation])
            return False
        return handler

    def _op_delay(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        low = self._u16(slot)
        high = self._u8(slot)
        slot.delay = (high << 16) | low
        slot.yielded = True
        return True

    def _op_delay_variable(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        slot.delay = max(0, self._read_var(slot, self._u16(slot)))
        slot.yielded = True
        return True

    def _op_load_room(self, slot: ScriptSlot, context: EngineContext) -> bool:
        room = self._var_or_direct_byte(slot, 0x80)
        if room & 0x80:
            room = self.state.resource_mapper[room & 0x7F]
        self._load_room(context, room, required=True)
        return False

    def _op_print(self, slot: ScriptSlot, context: EngineContext) -> bool:
        actor = self._var_or_direct_byte(slot, 0x80)
        self._decode_print(slot, context, actor)
        return False

    def _op_print_ego(self, slot: ScriptSlot, context: EngineContext) -> bool:
        ego_actor = int(context.profile.options.get("ego_actor", 1))
        if not 0 <= ego_actor <= 255:
            raise EngineExecutionError("SCUMM ego_actor profile option must fit u8")
        self._decode_print(slot, context, ego_actor)
        return False

    def _decode_print(
        self, slot: ScriptSlot, context: EngineContext, actor: int
    ) -> None:
        text_slot = {252: 3, 253: 2, 254: 1}.get(actor, 0)
        style = replace(self.state.print_slots[text_slot])
        while True:
            flags = self._u8(slot)
            if flags == 0xFF:
                self.state.print_slots[text_slot] = style
                return
            subop = flags & 0x0F
            if subop == 0:  # SO_AT
                style.x = self._word_for_flags(slot, flags, 0x80)
                style.y = self._word_for_flags(slot, flags, 0x40)
                style.overhead = False
            elif subop == 1:  # SO_COLOR
                style.color = self._byte_for_flags(slot, flags, 0x80)
            elif subop == 2:  # SO_CLIPPED
                style.right = self._word_for_flags(slot, flags, 0x80)
            elif subop == 3:  # SO_ERASE
                width = self._word_for_flags(slot, flags, 0x80)
                height = self._word_for_flags(slot, flags, 0x40)
                raise EngineExecutionError(
                    f"SCUMM print erase {width}x{height} is not implemented"
                )
            elif subop == 4:  # SO_CENTER
                style.center = True
                style.overhead = False
            elif subop == 6:  # SO_LEFT
                style.center = False
                style.overhead = False
            elif subop == 7:  # SO_OVERHEAD
                style.overhead = True
            elif subop == 8:  # SO_SAY_VOICE is a Loom v4 facility
                offset = self._word_for_flags(slot, flags, 0x80)
                delay = self._word_for_flags(slot, flags, 0x40)
                raise EngineExecutionError(
                    f"SCUMM v5 print sayVoice {offset}/{delay} is unsupported"
                )
            elif subop == 15:  # SO_TEXTSTRING
                raw = self._read_encoded_string(slot)
                message = PrintMessageState(actor, text_slot, style, raw)
                if len(self.state.print_messages) >= _MAX_PRINT_MESSAGES:
                    self.state.print_messages.pop(0)
                self.state.print_messages.append(message)
                self._present_print(context, message)
                return
            else:
                raise EngineExecutionError(f"SCUMM print sub-op {subop} is not implemented")

    def _present_print(self, context: EngineContext, message: PrintMessageState) -> None:
        key = self._resource_key("charset", message.style.charset)
        if not context.services.resources.contains(key):
            # Some retail DCHR directories leave entry zero empty while the
            # VM's default charset number still denotes the first font.
            fallback = self._resource_key("charset", message.style.charset + 1)
            if not context.services.resources.contains(fallback):
                raise ResourceError(
                    f"SCUMM print charset {message.style.charset} has no resource binding"
                )
            key = fallback
        font = ScummV5Charset(context.services.resource_read(key), key=key)
        glyphs = [
            token.code
            for token in decode_scumm_v5_text(message.raw)
            if isinstance(token, ScummTextGlyph)
        ]
        advances = [font.glyph(code) for code in glyphs]
        text_width = sum(4 if glyph is None else glyph.advance for glyph in advances)
        pen_x = message.style.x - text_width // 2 if message.style.center else message.style.x
        logical_width = context.profile.video.logical_width or context.profile.video.width
        logical_height = context.profile.video.logical_height or context.profile.video.height
        target = context.services.video.surface
        source_x = max(0, (logical_width - target.width) // 2)
        source_y = max(0, (logical_height - target.height) // 2)
        destination_x = max(0, (target.width - logical_width) // 2)
        destination_y = max(0, (target.height - logical_height) // 2)
        for glyph in advances:
            if glyph is None:
                pen_x += 4
                continue
            for glyph_y in range(glyph.height):
                logical_y = message.style.y + glyph.y_offset + glyph_y
                physical_y = destination_y + logical_y - source_y
                if not 0 <= physical_y < target.height:
                    continue
                for glyph_x in range(glyph.width):
                    if not glyph.pixels[glyph_y * glyph.width + glyph_x]:
                        continue
                    logical_x = pen_x + glyph.x_offset + glyph_x
                    physical_x = destination_x + logical_x - source_x
                    if logical_x <= message.style.right and 0 <= physical_x < target.width:
                        target.set_pixel(physical_x, physical_y, message.style.color)
            pen_x += glyph.advance
        self.state.room_hash = target.hash()

    def _op_start_music(self, slot: ScriptSlot, context: EngineContext) -> bool:
        music = self._var_or_direct_byte(slot, 0x80)
        if self._audio is None:
            context.services.audio.play_music(music)
        else:
            self._audio.play_music(music)
        return False

    def _op_stop_music(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del slot
        if self._audio is None:
            context.services.audio.stop_music()
        else:
            self._audio.stop_music()
        return False

    def _op_start_sound(self, slot: ScriptSlot, context: EngineContext) -> bool:
        sound = self._var_or_direct_byte(slot, 0x80)
        if self._audio is None:
            context.services.audio.play_sfx(sound)
        else:
            self._audio.play_sfx(sound)
        return False

    def _op_stop_sound(self, slot: ScriptSlot, context: EngineContext) -> bool:
        sound = self._var_or_direct_byte(slot, 0x80)
        if self._audio is None:
            context.services.audio.stop_sfx(sound)
        else:
            self._audio.stop_sfx(sound)
        return False

    def _op_sound_kludge(self, slot: ScriptSlot, context: EngineContext) -> bool:
        arguments = self._word_varargs(slot)
        if not arguments:
            raise EngineExecutionError("SCUMM soundKludge command is empty")
        if arguments[0] == -1:
            self._flush_sound_commands(context)
            return False
        if len(self.state.sound_queue) >= _MAX_SOUND_COMMANDS:
            raise EngineExecutionError(
                f"SCUMM soundKludge queue exceeds {_MAX_SOUND_COMMANDS} commands"
            )
        self.state.sound_queue.append(arguments)
        return False

    def _flush_sound_commands(self, context: EngineContext) -> None:
        queued = self.state.sound_queue
        self.state.sound_queue = []
        for command in queued:
            self._dispatch_sound_command(context, command)
            self.state.sound_history.append(list(command))
            if len(self.state.sound_history) > _MAX_SOUND_HISTORY:
                del self.state.sound_history[:-_MAX_SOUND_HISTORY]
        context.services.audio.flush()

    def _dispatch_sound_command(self, context: EngineContext, arguments: list[int]) -> None:
        encoded = arguments[0] & 0xFFFF
        command = encoded & 0xFF
        parameter = encoded >> 8
        if parameter != 0:
            raise EngineExecutionError(
                f"SCUMM soundKludge command ${encoded:04X} is not implemented"
            )
        if command == 6:
            if len(arguments) != 2 or not 0 <= arguments[1] <= 127:
                raise EngineExecutionError("SCUMM soundKludge master-volume operands are invalid")
            volume = (arguments[1] << 1) | int(arguments[1] != 0)
            context.services.audio.set_master_volume(volume)
            self.state.sound_result = 0
        elif command == 8:
            if len(arguments) != 2 or not 0 <= arguments[1] <= 0xFFFF:
                raise EngineExecutionError("SCUMM soundKludge start-sound operands are invalid")
            sound = arguments[1]
            if self._audio is None:
                resource = None
                backend = "normalized"
                if self._policy is not None and self._policy.audio_source == "embedded":
                    resource = self._resource_key("sound", sound)
                    if not context.services.resources.contains(resource):
                        raise ResourceError(
                            f"SCUMM sound {sound} has no resource binding {resource!r}"
                        )
                    backend = "embedded"
                context.services.audio.play_sfx(sound, resource=resource, backend=backend)
            else:
                self._audio.play_sfx(sound)
            self.state.sound_result = 0
        elif command == 9:
            if len(arguments) != 2 or not 0 <= arguments[1] <= 0xFFFF:
                raise EngineExecutionError("SCUMM soundKludge stop-sound operands are invalid")
            if self._audio is None:
                context.services.audio.stop_sfx(arguments[1])
            else:
                self._audio.stop_sfx(arguments[1])
            self.state.sound_result = 0
        elif command in (10, 11):
            if len(arguments) != 1:
                raise EngineExecutionError("SCUMM soundKludge stop-all operands are invalid")
            if self._audio is not None:
                self._audio.music_id = None
                self._audio.music_position = 0
                self._audio.active_sfx.clear()
                self._audio.speech_id = None
                self._audio.speech_position = 0
            context.services.audio.stop_music()
            context.services.audio.stop_sfx()
            context.services.audio.stop_speech()
            self.state.sound_result = 0
        else:
            raise EngineExecutionError(
                f"SCUMM soundKludge command {command} is not implemented"
            )

    def _op_set_camera(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        self.state.camera_x = self._var_or_direct_word(slot, 0x80)
        return False

    def _op_actor_follow_camera(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Select the v5 follow-actor camera intent without backend policy."""
        del context
        actor_id = self._var_or_direct_byte(slot, 0x80)
        if not 0 <= actor_id < _MAX_ACTORS:
            raise EngineExecutionError(
                f"SCUMM actorFollowCamera actor {actor_id} is outside 0..{_MAX_ACTORS - 1}"
            )
        self.state.camera_follow_actor = actor_id
        return False

    def _op_set_class(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Apply canonical v5 object-class selectors to bounded sparse state."""
        del context
        object_id = self._var_or_direct_word(slot, 0x80) & 0xFFFF
        while True:
            selector = self._u8(slot)
            if selector == 0xFF:
                return False
            raw_class = self._word_for_flags(slot, selector, 0x80) & 0xFFFF
            if raw_class == 0:
                self.state.object_classes.pop(object_id, None)
                continue
            class_id = raw_class & 0x7F
            if not 1 <= class_id <= 32:
                raise EngineExecutionError(
                    f"SCUMM setClass class {class_id} is outside 1..32"
                )
            classes = self.state.object_classes.get(object_id)
            if raw_class & 0x80:
                if classes is None:
                    if len(self.state.object_classes) >= _MAX_CLASS_OBJECTS:
                        raise EngineExecutionError(
                            f"SCUMM setClass exceeds {_MAX_CLASS_OBJECTS} modified objects"
                        )
                    classes = set()
                    self.state.object_classes[object_id] = classes
                classes.add(class_id)
            elif classes is not None:
                classes.discard(class_id)
                if not classes:
                    del self.state.object_classes[object_id]

    def _op_verb_ops(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Apply canonical v5 verb-slot configuration without presentation policy."""
        del context
        verb_id = self._var_or_direct_byte(slot, 0x80)
        verb = self.state.verbs.get(verb_id)
        persistent = verb is not None
        if verb is None:
            verb = VerbState()
        while True:
            flags = self._u8(slot)
            if flags == 0xFF:
                return False
            subop = flags & 0x1F
            if subop == 1:  # SO_VERB_IMAGE
                image_object = self._word_for_flags(slot, flags, 0x80) & 0xFFFF
                if persistent:
                    verb.image_source = (self.state.current_room, image_object)
                    verb.kind = "image"
            elif subop == 2:  # SO_VERB_NAME
                name = self._read_encoded_string(slot)
                if len(name) > _MAX_VERB_NAME_BYTES:
                    raise EngineExecutionError(
                        f"SCUMM verb name exceeds {_MAX_VERB_NAME_BYTES} bytes"
                    )
                verb.name = name
                verb.kind = "text"
                verb.image_index = 0
                verb.image_source = None
            elif subop == 3:  # SO_VERB_COLOR
                verb.color = self._byte_for_flags(slot, flags, 0x80)
            elif subop == 4:  # SO_VERB_HICOLOR
                verb.hicolor = self._byte_for_flags(slot, flags, 0x80)
            elif subop == 5:  # SO_VERB_AT
                left = self._word_for_flags(slot, flags, 0x80)
                top = self._word_for_flags(slot, flags, 0x40)
                verb.position = (left, top)
                verb.original_left = left
            elif subop == 6:  # SO_VERB_ON
                verb.mode = 1
            elif subop == 7:  # SO_VERB_OFF
                verb.mode = 0
            elif subop == 8:  # SO_VERB_DELETE
                self.state.verbs.pop(verb_id, None)
                persistent = False
            elif subop == 9:  # SO_VERB_NEW
                if not persistent:
                    if len(self.state.verbs) >= _MAX_VERBS:
                        raise EngineExecutionError(
                            f"SCUMM verbOps exceeds {_MAX_VERBS} verb identities"
                        )
                    verb = VerbState()
                    self.state.verbs[verb_id] = verb
                    persistent = True
                verb.apply_new(self.state.charset_id)
            elif subop == 16:  # SO_VERB_DIMCOLOR
                verb.dimcolor = self._byte_for_flags(slot, flags, 0x80)
            elif subop == 17:  # SO_VERB_DIM
                verb.mode = 2
            elif subop == 18:  # SO_VERB_KEY
                verb.key = self._byte_for_flags(slot, flags, 0x80)
            elif subop == 19:  # SO_VERB_CENTER
                verb.center = True
            elif subop == 20:  # SO_VERB_NAME_STR
                string_id = self._word_for_flags(slot, flags, 0x80) & 0xFFFF
                name = self.state.strings.get(string_id)
                if name is not None and len(name) > _MAX_VERB_NAME_BYTES:
                    raise EngineExecutionError(
                        f"SCUMM verb name string {string_id} exceeds "
                        f"{_MAX_VERB_NAME_BYTES} bytes"
                    )
                verb.name = None if name is None else bytearray(name)
                verb.kind = "text"
                verb.image_index = 0
                verb.image_source = None
            elif subop == 22:  # SO_VERB_OBJECT
                image_object = self._word_for_flags(slot, flags, 0x80) & 0xFFFF
                room = self._byte_for_flags(slot, flags, 0x40)
                if persistent and verb.image_index != image_object:
                    verb.image_source = (room, image_object)
                    verb.kind = "image"
                    verb.image_index = image_object
            elif subop == 23:  # SO_VERB_BKCOLOR
                verb.background_color = self._byte_for_flags(slot, flags, 0x80)
            else:
                raise EngineExecutionError(f"SCUMM verbOps sub-op {subop} is invalid for v5")

    def _op_save_restore_verbs(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Move verb slots between the active namespace and numbered save banks."""
        del context
        operation = self._u8(slot)
        first = self._u8(slot)
        last = self._u8(slot)
        save_id = self._u8(slot)
        if operation not in (1, 2, 3):
            raise EngineExecutionError(
                f"SCUMM saveRestoreVerbs sub-op {operation} is invalid for v5"
            )
        if first > last:
            return False
        for verb_id in range(first, last + 1):
            if operation == 1:
                verb = self.state.verbs.get(verb_id)
                if verb is None or verb.save_id != 0 or save_id == 0:
                    continue
                if len(self.state.saved_verbs) >= _MAX_SAVED_VERBS:
                    raise EngineExecutionError(
                        f"SCUMM saveRestoreVerbs exceeds {_MAX_SAVED_VERBS} saved slots"
                    )
                verb.save_id = save_id
                self.state.saved_verbs.append((verb_id, verb))
                del self.state.verbs[verb_id]
            elif operation == 2:
                if save_id == 0:
                    continue
                saved_index = next(
                    (
                        index
                        for index, (saved_id, verb) in enumerate(self.state.saved_verbs)
                        if saved_id == verb_id and verb.save_id == save_id
                    ),
                    None,
                )
                if saved_index is None:
                    continue
                _, verb = self.state.saved_verbs.pop(saved_index)
                self.state.verbs.pop(verb_id, None)
                verb.save_id = 0
                self.state.verbs[verb_id] = verb
            elif save_id == 0:
                self.state.verbs.pop(verb_id, None)
            else:
                saved_index = next(
                    (
                        index
                        for index, (saved_id, verb) in enumerate(self.state.saved_verbs)
                        if saved_id == verb_id and verb.save_id == save_id
                    ),
                    None,
                )
                if saved_index is not None:
                    self.state.saved_verbs.pop(saved_index)
        return False

    @staticmethod
    def _expression_s32(value: int) -> int:
        value &= 0xFFFFFFFF
        return value - 0x100000000 if value & 0x80000000 else value

    def _op_expression(self, slot: ScriptSlot, context: EngineContext) -> bool:
        destination = self._result_var(slot)
        # Canonical v5 uses one shared 256-entry signed-int expression stack.
        self._expression_stack: list[int] = []

        def push(value: int) -> None:
            if len(self._expression_stack) >= 256:
                raise EngineExecutionError("SCUMM expression stack overflow")
            self._expression_stack.append(self._expression_s32(value))

        def pop() -> int:
            if not self._expression_stack:
                raise EngineExecutionError("SCUMM expression stack underflow")
            return self._expression_stack.pop()

        while True:
            token = self._u8(slot)
            if token == 0xFF:
                break
            operation = token & 0x1F
            if operation == 1:
                push(self._word_for_flags(slot, token, 0x80))
            elif operation == 2:
                rhs = pop()
                push(pop() + rhs)
            elif operation == 3:
                rhs = pop()
                push(pop() - rhs)
            elif operation == 4:
                rhs = pop()
                push(pop() * rhs)
            elif operation == 5:
                rhs = pop()
                if rhs == 0:
                    raise EngineExecutionError("SCUMM expression division by zero")
                push(int(pop() / rhs))
            elif operation == 6:
                nested_opcode = self._u8(slot)
                self.state.last_opcode = nested_opcode
                try:
                    nested = self._handlers[nested_opcode]
                except KeyError as exc:
                    raise EngineExecutionError(
                        f"SCUMM v5 opcode ${nested_opcode:02X} is not implemented "
                        f"inside expression (script {slot.resource_key}, "
                        f"offset ${slot.pc - 1:04X})"
                    ) from exc
                nested(slot, context)
                push(self._read_var(slot, 0))
            # Reserved token classes are canonical no-ops.
        self._write_var(slot, destination, pop())
        return False

    def _word_varargs(self, slot: ScriptSlot) -> list[int]:
        values: list[int] = []
        while True:
            selector = self._u8(slot)
            if selector == 0xFF:
                return values
            if len(values) >= _LOCAL_VARIABLE_COUNT:
                raise EngineExecutionError(
                    f"SCUMM script {slot.resource_key!r} has too many local arguments"
                )
            reference_or_value = self._u16(slot)
            value = (
                self._read_var(slot, reference_or_value)
                if selector & 0x80
                else reference_or_value
            )
            value &= 0xFFFF
            values.append(value - 0x10000 if value & 0x8000 else value)

    def _run_cutscene_callback(
        self,
        owner: ScriptSlot,
        context: EngineContext,
        variable: int,
        arguments: list[int],
    ) -> None:
        number = self.state.variables[variable] & 0xFF
        if number == 0:
            return
        owner_index = self.state.scripts.index(owner)
        child = self._allocate_script_slot(
            context,
            number,
            arguments,
            freeze_resistant=False,
            recursive=False,
        )
        self.state.cutscene_script_index = owner_index
        try:
            if self._in_tick:
                self._execute_slot(child, context)
        finally:
            self.state.cutscene_script_index = None

    def _op_cutscene(self, slot: ScriptSlot, context: EngineContext) -> bool:
        arguments = self._word_varargs(slot)
        if len(self.state.cutscenes) >= _MAX_CUTSCENE_DEPTH:
            raise EngineExecutionError("SCUMM cutscene stack overflow")
        if slot.cutscene_override >= 0xFF:
            raise EngineExecutionError("SCUMM script cutscene override depth overflow")
        slot.cutscene_override += 1
        self.state.cutscenes.append(
            CutsceneState(data=arguments[0] if arguments else 0)
        )
        self._run_cutscene_callback(slot, context, 35, arguments)
        return False

    def _op_end_cutscene(self, slot: ScriptSlot, context: EngineContext) -> bool:
        if not self.state.cutscenes:
            raise EngineExecutionError("SCUMM cutscene stack underflow")
        record = self.state.cutscenes[-1]
        if slot.cutscene_override:
            slot.cutscene_override -= 1
        self._write_var(slot, 5, 0)
        if record.override_pc is not None and slot.cutscene_override:
            slot.cutscene_override -= 1
        self.state.cutscenes.pop()
        self._run_cutscene_callback(slot, context, 36, [record.data])
        return False

    def _op_begin_override(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        enabled = self._u8(slot)
        # The original VM keeps entry zero as a valid sentinel even when the
        # active cutscene depth is zero. Scripts may clear or install an
        # override there; only endCutscene treats depth zero as underflow.
        record = (
            self.state.cutscenes[-1]
            if self.state.cutscenes
            else self.state.cutscene_sentinel
        )
        if enabled:
            self._ensure(slot, 3)
            record.override_pc = slot.pc
            record.override_slot = self.state.scripts.index(slot)
            slot.pc += 3  # skip the following jump opcode and signed displacement
        else:
            record.override_pc = None
            record.override_slot = None
        self._write_var(slot, 5, 0)
        return False

    def _abort_cutscene(self) -> None:
        record = (
            self.state.cutscenes[-1]
            if self.state.cutscenes
            else self.state.cutscene_sentinel
        )
        if record.override_pc is None or record.override_slot is None:
            return
        if not 0 <= record.override_slot < len(self.state.scripts):
            raise EngineExecutionError("SCUMM cutscene override slot is invalid")
        slot = self.state.scripts[record.override_slot]
        if not 0 <= record.override_pc <= len(slot.program):
            raise EngineExecutionError("SCUMM cutscene override PC is invalid")
        slot.pc = record.override_pc
        slot.active = True
        slot.yielded = False
        slot.freeze_count = 0
        if slot.cutscene_override:
            slot.cutscene_override -= 1
        self._write_var(slot, 5, 1)
        record.override_pc = None
        record.override_slot = None

    def _op_do_sentence(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        opcode = self.state.last_opcode
        verb = self._var_or_direct_byte(slot, 0x80)
        if verb == 0xFE:
            self.state.sentences.clear()
            self._stop_script_number(self.state.variables[33] & 0xFF)
            if self._input is not None:
                self._input.clear_clicked_status()
            return False
        object_a = self._var_or_direct_word(slot, 0x40) & 0xFFFF
        object_b = self._var_or_direct_word(slot, 0x20) & 0xFFFF
        if len(self.state.sentences) >= _MAX_SENTENCES:
            raise EngineExecutionError("SCUMM sentence queue overflow")
        self.state.sentences.append(SentenceState(verb, object_a, object_b))
        return False

    @staticmethod
    def _signed_word(value: int) -> int:
        value &= 0xFFFF
        return value - 0x10000 if value & 0x8000 else value

    @classmethod
    def _object_coordinate(cls, value: int) -> int:
        return cls._signed_word(value * 8)

    def _op_draw_object(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        object_id = self._var_or_direct_word(slot, 0x80) & 0xFFFF
        selector = self._u8(slot)
        subop = selector & 0x1F
        state = 1
        position: tuple[int, int] | None = None
        if subop == 1:
            position = (
                self._word_for_flags(slot, selector, 0x80),
                self._word_for_flags(slot, selector, 0x40),
            )
        elif subop == 2:
            state = self._word_for_flags(slot, selector, 0x80)
            if not 0 <= state <= 255:
                raise EngineExecutionError(f"SCUMM drawObject state {state} must fit u8")
        elif subop != 0x1F:
            raise EngineExecutionError(f"SCUMM drawObject sub-op {subop} is not implemented")

        target = self.state.room_objects.get(object_id)
        if target is None:
            return False
        if position is not None:
            new_x = self._object_coordinate(position[0])
            new_y = self._object_coordinate(position[1])
            target.walk_x = self._signed_word(target.walk_x + new_x - target.x)
            target.walk_y = self._signed_word(target.walk_y + new_y - target.y)
            target.x = new_x
            target.y = new_y
        if len(self.state.object_draw_queue) >= _MAX_LOCAL_OBJECTS:
            raise EngineExecutionError("SCUMM draw-object queue overflow")
        self.state.object_draw_queue.append(object_id)
        rectangle = (target.x, target.y, target.width, target.height)
        for item in self.state.room_objects.values():
            if (item.x, item.y, item.width, item.height) == rectangle:
                item.state = 0
                self.state.object_states[item.object_id] = 0
        target.state = state
        self.state.object_states[object_id] = state
        return False

    def _check_and_run_sentence_script(self, context: EngineContext) -> None:
        number = self.state.variables[33] & 0xFF
        if number and any(
            candidate.active
            and candidate.number == number
            and candidate.freeze_count == 0
            for candidate in self.state.scripts
        ):
            return
        if not self.state.sentences or self.state.sentences[-1].freeze_count:
            return
        sentence = self.state.sentences.pop()
        # Canonical v3-v6 behavior drops a prepositional sentence whose two
        # objects are identical before invoking the sentence script.
        if sentence.object_b and sentence.object_b == sentence.object_a:
            return
        if number:
            self._allocate_script_slot(
                context,
                number,
                [sentence.verb, sentence.object_a, sentence.object_b],
                freeze_resistant=False,
                recursive=False,
            )

    def _stop_script_number(self, number: int) -> None:
        if number == 0:
            return
        for candidate in self.state.scripts:
            if candidate.active and candidate.number == number:
                if candidate.cutscene_override:
                    raise EngineExecutionError(
                        f"SCUMM script {candidate.resource_key!r} stopped with active "
                        f"cutscene/override depth {candidate.cutscene_override}"
                    )
                candidate.active = False
                candidate.yielded = False
                candidate.number = 0
                candidate.freeze_resistant = False
                candidate.recursive = False
                candidate.freeze_count = 0
                candidate.cutscene_override = 0

    def _allocate_script_slot(
        self,
        context: EngineContext,
        number: int,
        arguments: list[int],
        *,
        freeze_resistant: bool,
        recursive: bool,
    ) -> ScriptSlot:
        if not recursive:
            self._stop_script_number(number)
        key = self._script_key(number)
        room: int | None = None
        if context.services.resources.contains(key):
            program = context.services.resource_read(key)
        else:
            program = self._room_scripts.get(number, b"")
            if program:
                room = self.state.current_room
                key = self._local_script_key(room, number)
            else:
                raise ResourceError(
                    f"SCUMM script {number} has no resource binding "
                    "(global or current-room local)"
                )
        if not program:
            raise ResourceError(f"SCUMM script resource {key!r} is empty")
        locals_values = [0] * _LOCAL_VARIABLE_COUNT
        locals_values[: len(arguments)] = arguments
        replacement = next((item for item in self.state.scripts[1:] if not item.active), None)
        fresh = ScriptSlot(
            key,
            program,
            number=number,
            locals=locals_values,
            freeze_resistant=freeze_resistant,
            recursive=recursive,
            room=room,
        )
        if replacement is not None:
            index = self.state.scripts.index(replacement)
            self.state.scripts[index] = fresh
        elif len(self.state.scripts) < _MAX_SCRIPT_SLOTS:
            self.state.scripts.append(fresh)
        else:
            raise EngineExecutionError(
                f"SCUMM script-slot capacity exhausted ({_MAX_SCRIPT_SLOTS} slots)"
            )
        return fresh

    def _op_start_script(self, slot: ScriptSlot, context: EngineContext) -> bool:
        opcode = self.state.last_opcode
        number = self._var_or_direct_byte(slot, 0x80)
        arguments = self._word_varargs(slot)
        if number == 0:
            return False
        child = self._allocate_script_slot(
            context,
            number,
            arguments,
            freeze_resistant=bool(opcode & 0x20),
            recursive=bool(opcode & 0x40),
        )
        if self._in_tick:
            self._execute_slot(child, context)
        return False

    def _op_stop_script(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        number = self._var_or_direct_byte(slot, 0x80)
        if number == 0:
            if slot.cutscene_override:
                raise EngineExecutionError(
                    f"SCUMM script {slot.resource_key!r} stopped with active "
                    f"cutscene/override depth {slot.cutscene_override}"
                )
            slot.active = False
            slot.yielded = False
            slot.number = 0
            slot.freeze_resistant = False
            slot.recursive = False
            slot.freeze_count = 0
            slot.cutscene_override = 0
            return True
        self._stop_script_number(number)
        return not slot.active

    def _op_freeze_scripts(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        flag = self._var_or_direct_byte(slot, 0x80)
        if flag:
            force_resistant = flag >= 0x80
            for index, candidate in enumerate(self.state.scripts):
                if (
                    candidate is not slot
                    and candidate.active
                    and index != self.state.cutscene_script_index
                    and (not candidate.freeze_resistant or force_resistant)
                ):
                    candidate.freeze_count += 1
            for sentence in self.state.sentences:
                if sentence.freeze_count >= 0xFF:
                    raise EngineExecutionError("SCUMM sentence freeze depth overflow")
                sentence.freeze_count += 1
        else:
            for candidate in self.state.scripts:
                if candidate.freeze_count:
                    candidate.freeze_count -= 1
            for sentence in self.state.sentences:
                if sentence.freeze_count:
                    sentence.freeze_count -= 1
        return False

    def _op_is_script_running(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        result = self._result_var(slot)
        number = self._var_or_direct_byte(slot, 0x80)
        running = any(
            candidate.active and candidate.number == number
            for candidate in self.state.scripts
        )
        self._write_var(slot, result, int(running))
        return False

    def _op_chain_script(self, slot: ScriptSlot, context: EngineContext) -> bool:
        number = self._var_or_direct_byte(slot, 0x80)
        arguments = self._word_varargs(slot)
        freeze_resistant = slot.freeze_resistant
        recursive = slot.recursive
        slot.active = False
        slot.yielded = False
        slot.number = 0
        slot.freeze_resistant = False
        slot.recursive = False
        slot.freeze_count = 0
        if number == 0:
            return True
        replacement = self._allocate_script_slot(
            context,
            number,
            arguments,
            freeze_resistant=freeze_resistant,
            recursive=recursive,
        )
        if self._in_tick:
            self._execute_slot(replacement, context)
        return True

    def _op_cursor_command(self, slot: ScriptSlot, context: EngineContext) -> bool:
        flags = self._u8(slot)
        subop = flags & 0x1F
        if subop == 1:
            self.state.cursor_state = 1
        elif subop == 2:
            self.state.cursor_state = 0
        elif subop == 3:
            self.state.user_input_state = 1
        elif subop == 4:
            self.state.user_input_state = 0
        elif subop == 5:
            self.state.cursor_state += 1
        elif subop == 6:
            self.state.cursor_state -= 1
        elif subop == 7:
            self.state.user_input_state += 1
        elif subop == 8:
            self.state.user_input_state -= 1
        elif subop == 10:
            self.state.cursor_image = (
                self._byte_for_flags(slot, flags, 0x80),
                self._byte_for_flags(slot, flags, 0x40),
            )
        elif subop == 11:
            self.state.cursor_hotspot = (
                self._byte_for_flags(slot, flags, 0x80),
                self._byte_for_flags(slot, flags, 0x40),
                self._byte_for_flags(slot, flags, 0x20),
            )
        elif subop == 12:
            self.state.cursor_id = self._byte_for_flags(slot, flags, 0x80)
        elif subop == 13:
            self.state.charset_id = self._byte_for_flags(slot, flags, 0x80)
        elif subop == 14:
            colors: list[int] = []
            while True:
                selector = self._u8(slot)
                if selector == 0xFF:
                    break
                if len(colors) >= 16:
                    raise EngineExecutionError("SCUMM cursor charset-color list exceeds 16 entries")
                colors.append(self._word_for_flags(slot, selector, 0x80) & 0xFFFF)
            self.state.charset_colors = colors
        else:
            raise EngineExecutionError(f"SCUMM cursorCommand sub-op {subop} is not implemented")

        self._write_var(slot, 52, self.state.cursor_state)
        self._write_var(slot, 53, self.state.user_input_state)
        self.state.cursor_visible = self.state.cursor_state > 0
        context.services.video.show_cursor(self.state.cursor_visible)
        return False

    def _op_set_var_range(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        result = self._result_var(slot)
        count = self._u8(slot) or 256
        word_values = bool(self.state.last_opcode & 0x80)
        for _ in range(count):
            value = self._s16(slot) if word_values else self._u8(slot)
            self._write_var(slot, result, value)
            result += 1
        return False

    def _op_get_random(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Return a deterministic value in ScummVM's inclusive 0..max range."""
        del context
        result = self._result_var(slot)
        maximum = self._var_or_direct_byte(slot, 0x80)
        state = self.state.random_state
        state = (state >> 1) ^ (0xB400 if state & 1 else 0)
        self.state.random_state = state
        sample = state >> 8
        value = sample if maximum == 0xFF else sample % (maximum + 1)
        self._write_var(slot, result, value)
        return False

    def _op_pseudo_room(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Map high-bit pseudo-room identifiers to a physical room resource."""
        del context
        room = self._u8(slot)
        while True:
            pseudo = self._u8(slot)
            if pseudo == 0:
                return False
            if pseudo & 0x80:
                self.state.resource_mapper[pseudo & 0x7F] = room

    def _mapped_room(self, room: int) -> int:
        return self.state.resource_mapper[room & 0x7F] if room & 0x80 else room

    def _op_resource_routines(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Apply generic v5 resource cache and lock intent through SAME keys."""
        selector = self._u8(slot)
        operation = selector & 0x3F
        if operation == 17:  # SO_CLEAR_HEAP is a no-op in the generic v5 core.
            return False
        if not 1 <= operation <= 20:
            raise EngineExecutionError(
                f"SCUMM resourceRoutines sub-op {operation} is not implemented"
            )
        resource_id = self._byte_for_flags(slot, selector, 0x80)
        if operation == 20:
            room = self._mapped_room(resource_id)
            object_id = self._word_for_flags(slot, selector, 0x40) & 0xFFFF
            context.services.resource_read(self._room_key(room))
            self.state.resource_ops.loaded["room"].add(room)
            self.state.resource_ops.last_object = (room, object_id)
            return False

        if operation in (18, 19):
            kind = "charset"
            action = "load" if operation == 18 else "nuke"
        else:
            zero_based = (operation - 1) % 4
            kind = _LOCKABLE_RESOURCE_KINDS[zero_based]
            action = ("load", "nuke", "lock", "unlock")[(operation - 1) // 4]
        if kind == "room":
            resource_id = self._mapped_room(resource_id)

        loaded = self.state.resource_ops.loaded[kind]
        if action == "load":
            context.services.resource_read(self._resource_key(kind, resource_id))
            loaded.add(resource_id)
        elif action == "nuke":
            loaded.discard(resource_id)
        elif action == "lock":
            self.state.resource_ops.locked[kind].add(resource_id)
        else:
            self.state.resource_ops.locked[kind].discard(resource_id)
        return False

    def _actor(self, actor_id: int) -> ActorState:
        if not 0 <= actor_id < _MAX_ACTORS:
            raise EngineExecutionError(f"SCUMM actor {actor_id} is outside 0..{_MAX_ACTORS - 1}")
        return self.state.actors.setdefault(actor_id, ActorState())

    def _op_actor_ops(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Apply full-header v5 actor configuration as backend-neutral state."""
        del context
        actor = self._actor(self._var_or_direct_byte(slot, 0x80))
        while True:
            flags = self._u8(slot)
            if flags == 0xFF:
                return False
            subop = flags & 0x1F
            byte1 = lambda: self._byte_for_flags(slot, flags, 0x80)
            byte2 = lambda: self._byte_for_flags(slot, flags, 0x40)
            byte3 = lambda: self._byte_for_flags(slot, flags, 0x20)
            if subop == 0:  # Canonical dummy form still consumes its operand.
                byte1()
            elif subop == 1:
                actor.costume = byte1()
            elif subop == 2:
                actor.walk_speed = (byte1(), byte2())
            elif subop == 3:
                actor.sound = byte1()
            elif subop == 4:
                actor.walk_frame = byte1()
            elif subop == 5:
                actor.talk_frames = (byte1(), byte2())
            elif subop == 6:
                actor.stand_frame = byte1()
            elif subop == 7:  # Legacy animation tuple is consumed but unused in v5.
                byte1(), byte2(), byte3()
            elif subop == 8:
                actor.reset_defaults()
            elif subop == 9:
                actor.elevation = self._word_for_flags(slot, flags, 0x80)
            elif subop == 10:
                actor.init_frame, actor.walk_frame, actor.stand_frame = 1, 2, 3
                actor.talk_frames = (4, 5)
            elif subop == 11:
                palette_slot, color = byte1(), byte2()
                if palette_slot > 31:
                    raise EngineExecutionError("SCUMM actorOps palette slot is outside 0..31")
                actor.palette[palette_slot] = color
            elif subop == 12:
                actor.talk_color = byte1()
            elif subop == 13:
                actor.name = self._read_encoded_string(slot)
            elif subop == 14:
                actor.init_frame = byte1()
            elif subop == 16:
                actor.width = byte1()
            elif subop == 17:
                x, y = byte1(), byte2()
                actor.box_scale = x
                actor.scale = (x, y)
            elif subop == 18:
                actor.force_clip = 0
            elif subop == 19:
                actor.force_clip = byte1()
            elif subop in (20, 21):
                actor.ignore_boxes = subop == 20
                actor.force_clip = 0
            elif subop == 22:
                actor.animation_speed = byte1()
            elif subop == 23:
                actor.shadow = byte1()
            else:
                raise EngineExecutionError(f"SCUMM actorOps sub-op {subop} is not implemented")

    def _op_animate_actor(self, slot: ScriptSlot, context: EngineContext) -> bool:
        """Request one canonical v5 animation on a live actor."""
        del context
        actor = self._actor(self._var_or_direct_byte(slot, 0x80))
        actor.animation = self._var_or_direct_byte(slot, 0x40)
        return False

    def _room_filename(self, slot: ScriptSlot) -> str:
        raw = bytearray()
        while True:
            value = self._u8(slot)
            if value == 0:
                break
            if len(raw) >= 63:
                raise EngineExecutionError("SCUMM roomOps filename exceeds 63 bytes")
            raw.append(value)
        if not raw:
            raise EngineExecutionError("SCUMM roomOps filename is empty")
        return raw.decode("latin-1")

    @staticmethod
    def _room_range(name: str, value: int, low: int = 0, high: int = 255) -> int:
        if not low <= value <= high:
            raise EngineExecutionError(
                f"SCUMM roomOps {name} {value} is outside {low}..{high}"
            )
        return value

    def _room_color_range(
        self, name: str, red: int, green: int, blue: int, first: int, last: int
    ) -> tuple[int, int, int, int, int]:
        values = (
            self._room_range(f"{name} red", red),
            self._room_range(f"{name} green", green),
            self._room_range(f"{name} blue", blue),
            self._room_range(f"{name} first color", first),
            self._room_range(f"{name} last color", last),
        )
        if first > last:
            raise EngineExecutionError(
                f"SCUMM roomOps {name} color range {first}..{last} is reversed"
            )
        return values

    def _op_room_ops(self, slot: ScriptSlot, context: EngineContext) -> bool:
        flags = self._u8(slot)
        subop = flags & 0x1F
        state = self.state.room_ops
        if subop == 1:  # SO_ROOM_SCROLL
            minimum = self._word_for_flags(slot, flags, 0x80)
            maximum = self._word_for_flags(slot, flags, 0x40)
            half = (context.profile.video.logical_width or context.profile.video.width) // 2
            upper = max(half, state.room_width - half)
            state.scroll_min_x = min(upper, max(half, minimum))
            state.scroll_max_x = min(upper, max(half, maximum))
        elif subop == 2:  # SO_ROOM_COLOR belongs to small-header v3
            raise EngineExecutionError("SCUMM roomOps room-color is invalid for v5")
        elif subop == 3:  # SO_ROOM_SCREEN
            top = self._word_for_flags(slot, flags, 0x80)
            bottom = self._word_for_flags(slot, flags, 0x40)
            logical_height = context.profile.video.logical_height or context.profile.video.height
            if not 0 <= top <= bottom <= logical_height:
                raise EngineExecutionError(
                    f"SCUMM roomOps screen range {top}..{bottom} is outside 0..{logical_height}"
                )
            state.screen_top, state.screen_bottom = top, bottom
        elif subop == 4:  # SO_ROOM_PALETTE
            red = self._word_for_flags(slot, flags, 0x80)
            green = self._word_for_flags(slot, flags, 0x40)
            blue = self._word_for_flags(slot, flags, 0x20)
            index_flags = self._u8(slot)
            index = self._byte_for_flags(slot, index_flags, 0x80)
            rgb = tuple(
                self._room_range(f"palette {name}", value)
                for name, value in (("red", red), ("green", green), ("blue", blue))
            )
            state.palette_overrides[index] = rgb  # type: ignore[assignment]
            context.services.video.surface.set_palette(index, (rgb,))
        elif subop == 5:  # SO_ROOM_SHAKE_ON
            state.shake_enabled = True
        elif subop == 6:  # SO_ROOM_SHAKE_OFF
            state.shake_enabled = False
        elif subop == 7:  # SO_ROOM_SCALE
            first_scale = self._byte_for_flags(slot, flags, 0x80)
            first_y = self._byte_for_flags(slot, flags, 0x40)
            second_flags = self._u8(slot)
            second_scale = self._byte_for_flags(slot, second_flags, 0x80)
            second_y = self._byte_for_flags(slot, second_flags, 0x40)
            slot_flags = self._u8(slot)
            scale_slot = self._byte_for_flags(slot, slot_flags, 0x40)
            self._room_range("scale slot", scale_slot, 1, _ROOM_SCALE_SLOTS)
            state.scale_slots[scale_slot - 1] = (
                first_scale, first_y, second_scale, second_y
            )
        elif subop == 8:  # SO_ROOM_INTENSITY
            level = self._byte_for_flags(slot, flags, 0x80)
            first = self._byte_for_flags(slot, flags, 0x40)
            last = self._byte_for_flags(slot, flags, 0x20)
            state.intensity = self._room_color_range(
                "intensity", level, level, level, first, last
            )
        elif subop == 9:  # SO_ROOM_SAVEGAME
            save_flag = self._byte_for_flags(slot, flags, 0x80)
            self._byte_for_flags(slot, flags, 0x40)  # canonical slot is forced to 99
            state.save_load_request = (save_flag, 99)
        elif subop == 10:  # SO_ROOM_FADE
            state.fade_effect = self._word_for_flags(slot, flags, 0x80) & 0xFFFF
        elif subop in (11, 12):  # SO_RGB_ROOM_INTENSITY / SO_ROOM_SHADOW
            red = self._word_for_flags(slot, flags, 0x80)
            green = self._word_for_flags(slot, flags, 0x40)
            blue = self._word_for_flags(slot, flags, 0x20)
            range_flags = self._u8(slot)
            first = self._byte_for_flags(slot, range_flags, 0x80)
            last = self._byte_for_flags(slot, range_flags, 0x40)
            result = self._room_color_range(
                "rgb intensity" if subop == 11 else "shadow",
                red, green, blue, first, last,
            )
            if subop == 11:
                state.rgb_intensity = result
            else:
                state.shadow = result
        elif subop in (13, 14):  # SO_SAVE_STRING / SO_LOAD_STRING
            string_id = self._byte_for_flags(slot, flags, 0x80)
            filename = self._room_filename(slot)
            if subop == 13:
                state.auxiliary_files[filename] = bytearray(self._require_string(string_id))
            elif filename in state.auxiliary_files:
                self.state.strings[string_id] = bytearray(state.auxiliary_files[filename])
        elif subop == 15:  # SO_ROOM_TRANSFORM
            resource = self._byte_for_flags(slot, flags, 0x80)
            range_flags = self._u8(slot)
            first = self._byte_for_flags(slot, range_flags, 0x80)
            last = self._byte_for_flags(slot, range_flags, 0x40)
            time_flags = self._u8(slot)
            duration = self._byte_for_flags(slot, time_flags, 0x80)
            if first > last:
                raise EngineExecutionError(
                    f"SCUMM roomOps transform color range {first}..{last} is reversed"
                )
            state.transform = (resource, first, last, duration)
        elif subop == 16:  # SO_CYCLE_SPEED
            cycle = self._byte_for_flags(slot, flags, 0x80)
            speed = self._byte_for_flags(slot, flags, 0x40)
            self._room_range("color cycle", cycle, 1, 16)
            state.cycle_delays[cycle - 1] = 0 if speed == 0 else 0x4000 // (speed * 0x4C)
        else:
            raise EngineExecutionError(f"SCUMM roomOps sub-op {subop} is not implemented")
        return False

    def _read_encoded_string(self, slot: ScriptSlot) -> bytearray:
        encoded = bytearray()
        while True:
            value = self._u8(slot)
            encoded.append(value)
            if len(encoded) > _MAX_STRING_BYTES:
                raise EngineExecutionError(
                    f"SCUMM encoded string exceeds {_MAX_STRING_BYTES} bytes"
                )
            if value == 0:
                return encoded
            if value != 0xFF:
                continue
            code = self._u8(slot)
            encoded.append(code)
            for _ in range(control_argument_count(code)):
                encoded.append(self._u8(slot))
            if len(encoded) > _MAX_STRING_BYTES:
                raise EngineExecutionError(
                    f"SCUMM encoded string exceeds {_MAX_STRING_BYTES} bytes"
                )

    def _require_string(self, string_id: int) -> bytearray:
        try:
            return self.state.strings[string_id]
        except KeyError as exc:
            raise EngineExecutionError(f"SCUMM string {string_id} does not exist") from exc

    def _op_string_ops(self, slot: ScriptSlot, context: EngineContext) -> bool:
        del context
        flags = self._u8(slot)
        subop = flags & 0x1F
        if subop == 1:  # loadString / putCodeInString
            string_id = self._byte_for_flags(slot, flags, 0x80)
            self.state.strings[string_id] = self._read_encoded_string(slot)
        elif subop == 2:  # copyString
            destination = self._byte_for_flags(slot, flags, 0x80)
            source = self._byte_for_flags(slot, flags, 0x40)
            if destination == source:
                raise EngineExecutionError("SCUMM copyString source and destination are identical")
            source_data = self.state.strings.get(source)
            if source_data is None:
                self.state.strings.pop(destination, None)
            else:
                self.state.strings[destination] = bytearray(source_data)
        elif subop == 3:  # setStringChar
            string_id = self._byte_for_flags(slot, flags, 0x80)
            index = self._byte_for_flags(slot, flags, 0x40)
            value = self._byte_for_flags(slot, flags, 0x20)
            target = self._require_string(string_id)
            if index < len(target):
                target[index] = value
        elif subop == 4:  # getStringChar
            result = self._result_var(slot)
            string_id = self._byte_for_flags(slot, flags, 0x80)
            index = self._byte_for_flags(slot, flags, 0x40)
            source = self._require_string(string_id)
            self._write_var(slot, result, source[index] if index < len(source) else 0)
        elif subop == 5:  # createEmptyString
            string_id = self._byte_for_flags(slot, flags, 0x80)
            size = self._byte_for_flags(slot, flags, 0x40)
            self.state.strings.pop(string_id, None)
            if size:
                if size > _MAX_STRING_BYTES:
                    raise EngineExecutionError(
                        f"SCUMM string allocation {size} exceeds {_MAX_STRING_BYTES} bytes"
                    )
                self.state.strings[string_id] = bytearray(size)
        else:
            raise EngineExecutionError(f"SCUMM stringOps sub-op {subop} is not implemented")
        return False

    def _local_script_key(self, room: int, number: int) -> str:
        return f"{self._room_key(room)}/LSCR.{number}"

    def _room_script_programs(self, context: EngineContext, room: int) -> dict[int, bytes]:
        key = self._room_key(room)
        if not context.services.resources.contains(key):
            return {}
        decoded = decode_room(context.services.resource_read(key), key=key)
        return dict(decoded.local_scripts)

    def _load_room(
        self,
        context: EngineContext,
        room: int,
        *,
        required: bool,
        preserve_local_scripts: bool = False,
    ) -> None:
        if not preserve_local_scripts:
            for script in self.state.scripts:
                if script.active and script.room is not None:
                    if script.cutscene_override:
                        raise EngineExecutionError(
                            f"SCUMM local script {script.resource_key!r} changed room with active "
                            f"cutscene/override depth {script.cutscene_override}"
                        )
                    script.active = False
                    script.yielded = False
                    script.number = 0
                    script.freeze_resistant = False
                    script.recursive = False
                    script.freeze_count = 0
        key = self._room_key(room)
        if not context.services.resources.contains(key):
            # Room zero is SCUMM's resource-less null scene.  startScene(0)
            # still commits the room transition and clears local draw state;
            # it must never require a ROOM resource from a sparse game index.
            # Copyright-free conformance profiles may explicitly bind room.0,
            # in which case that fixture remains an ordinary rendered room.
            if room == 0:
                # An explicitly configured synthetic initial scene is already
                # the presentation source; the optional boot/load probe must
                # not replace it with the virtual null scene. Opcode-driven
                # transitions use required=True and always enter null room 0.
                if not required and self._video is not None:
                    self.state.current_room = 0
                    context.services.debug.marker("scumm_v5.room", 0)
                    return
                self.state.room_objects.clear()
                self.state.object_draw_queue.clear()
                self.state.current_room = 0
                self._room_scripts = {}
                surface = context.services.video.surface
                surface.set_palette(0, ((0, 0, 0),) * 256)
                surface.fill(0)
                self.state.room_hash = surface.hash()
                self._video = None
                context.services.debug.marker("scumm_v5.room", 0)
                return
            if required:
                raise ResourceError(f"SCUMM room {room} has no resource binding {key!r}")
            return
        raw = context.services.resource_read(key)
        adapter = ScummV5RoomAdapter(context)
        adapter.render(key)
        self._video = adapter
        self._room_scripts = dict(adapter.room.local_scripts)
        self.state.room_objects = {
            item.object_id: RoomObjectState.from_resource(
                item, self.state.object_states.get(item.object_id, 0)
            )
            for item in adapter.room.objects
        }
        self.state.object_draw_queue.clear()
        self.state.current_room = room
        self.state.room_ops.room_width = adapter.room.width
        self.state.room_hash = context.services.video.surface.hash()
        context.services.debug.marker("scumm_v5.room", room)

    def save_state(self, context: EngineContext) -> bytes:
        del context
        room_ops = self.state.room_ops
        data = {
            "variables": self.state.variables,
            "bits": [index for index, value in enumerate(self.state.bit_variables) if value],
            "scripts": [slot.to_dict() for slot in self.state.scripts],
            "current_room": self.state.current_room,
            "camera": [self.state.camera_x, self.state.camera_y],
            "camera_follow_actor": self.state.camera_follow_actor,
            "cursor": [
                self.state.cursor_x,
                self.state.cursor_y,
                self.state.cursor_visible,
            ],
            "cursor_command": {
                "state": self.state.cursor_state,
                "user_input": self.state.user_input_state,
                "image": list(self.state.cursor_image),
                "hotspot": list(self.state.cursor_hotspot),
                "cursor_id": self.state.cursor_id,
                "charset_id": self.state.charset_id,
                "charset_colors": self.state.charset_colors,
            },
            "strings": {
                str(string_id): bytes(value).hex()
                for string_id, value in sorted(self.state.strings.items())
            },
            "room_ops": {
                "room_width": room_ops.room_width,
                "scroll": [room_ops.scroll_min_x, room_ops.scroll_max_x],
                "screen": [room_ops.screen_top, room_ops.screen_bottom],
                "shake": room_ops.shake_enabled,
                "scale_slots": {
                    str(index): list(value)
                    for index, value in sorted(room_ops.scale_slots.items())
                },
                "intensity": list(room_ops.intensity),
                "fade_effect": room_ops.fade_effect,
                "rgb_intensity": list(room_ops.rgb_intensity),
                "shadow": list(room_ops.shadow),
                "transform": list(room_ops.transform),
                "cycle_delays": room_ops.cycle_delays,
                "palette_overrides": {
                    str(index): list(value)
                    for index, value in sorted(room_ops.palette_overrides.items())
                },
                "save_load_request": list(room_ops.save_load_request),
                "auxiliary_files": {
                    name: bytes(value).hex()
                    for name, value in sorted(room_ops.auxiliary_files.items())
                },
            },
            "random_state": self.state.random_state,
            "resource_mapper": self.state.resource_mapper,
            "resource_ops": {
                "loaded": {
                    kind: sorted(self.state.resource_ops.loaded[kind])
                    for kind in _RESOURCE_KINDS
                },
                "locked": {
                    kind: sorted(self.state.resource_ops.locked[kind])
                    for kind in _LOCKABLE_RESOURCE_KINDS
                },
                "last_object": (
                    None
                    if self.state.resource_ops.last_object is None
                    else list(self.state.resource_ops.last_object)
                ),
            },
            "actors": {
                str(actor_id): actor.to_dict()
                for actor_id, actor in sorted(self.state.actors.items())
            },
            "object_classes": {
                str(object_id): sorted(classes)
                for object_id, classes in sorted(self.state.object_classes.items())
            },
            "object_states": {
                str(object_id): state
                for object_id, state in sorted(self.state.object_states.items())
            },
            "room_objects": {
                str(object_id): item.to_dict()
                for object_id, item in sorted(self.state.room_objects.items())
            },
            "object_draw_queue": self.state.object_draw_queue,
            "verbs": {
                **{
                    str(verb_id): verb.to_dict()
                    for verb_id, verb in sorted(self.state.verbs.items())
                },
                **{
                    f"{verb_id}:{verb.save_id}:{index}": verb.to_dict()
                    for index, (verb_id, verb) in enumerate(self.state.saved_verbs)
                },
            },
            "cutscenes": [record.to_dict() for record in self.state.cutscenes],
            "cutscene_sentinel": self.state.cutscene_sentinel.to_dict(),
            "sentences": [sentence.to_dict() for sentence in self.state.sentences],
            "sound_kludge": {
                "queue": self.state.sound_queue,
                "history": self.state.sound_history,
                "result": self.state.sound_result,
            },
            "print": {
                "slots": [print_slot.to_dict() for print_slot in self.state.print_slots],
                "messages": [message.to_dict() for message in self.state.print_messages],
            },
            "operations": self.state.operations,
            "frames": self.state.frames,
            "last_opcode": self.state.last_opcode,
            "halted": self.state.halted,
            "audio": None if self._audio is None else self._audio.save_state(),
        }
        return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def load_state(self, context: EngineContext, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SaveFormatError(f"invalid SCUMM save payload: {exc}") from exc
        if not isinstance(data, dict):
            raise SaveFormatError("SCUMM save payload root must be an object")

        variables_raw = data.get("variables")
        if not isinstance(variables_raw, list) or len(variables_raw) != 2048:
            raise SaveFormatError("SCUMM save has the wrong variable count")
        variables = [int(value) for value in variables_raw]
        if any(value < -32768 or value > 32767 for value in variables):
            raise SaveFormatError("SCUMM save contains a variable outside signed 16-bit range")

        script_items = data.get("scripts")
        if not isinstance(script_items, list) or len(script_items) > 25:
            raise SaveFormatError("SCUMM save has an invalid script-slot count")
        scripts: list[ScriptSlot] = []
        for item in script_items:
            if not isinstance(item, dict):
                raise SaveFormatError("SCUMM save script entries must be objects")
            key = str(item.get("resource", ""))
            number = int(item.get("number", 0))
            room_raw = item.get("room")
            room_number = None if room_raw is None else int(room_raw)
            if room_number is None:
                try:
                    program = context.services.resources.read(key)
                except ResourceError as exc:
                    raise SaveFormatError(
                        f"SCUMM save references unavailable script resource {key!r}"
                    ) from exc
            else:
                if not 0 <= room_number <= 255:
                    raise SaveFormatError("SCUMM save local-script room is outside 0..255")
                if key != self._local_script_key(room_number, number):
                    raise SaveFormatError("SCUMM save local-script identity is invalid")
                try:
                    program = self._room_script_programs(context, room_number)[number]
                except (KeyError, ResourceError) as exc:
                    raise SaveFormatError(
                        f"SCUMM save references unavailable local script {number} "
                        f"in room {room_number}"
                    ) from exc
            locals_raw = item.get("locals", [0] * 32)
            if not isinstance(locals_raw, list) or len(locals_raw) != 32:
                raise SaveFormatError("SCUMM save script has the wrong local-variable count")
            locals_values = [int(value) for value in locals_raw]
            if any(value < -32768 or value > 32767 for value in locals_values):
                raise SaveFormatError("SCUMM save script local is outside signed 16-bit range")
            slot = ScriptSlot(
                key,
                program,
                number=number,
                pc=int(item.get("pc", -1)),
                delay=int(item.get("delay", -1)),
                active=bool(item.get("active", False)),
                yielded=bool(item.get("yielded", False)),
                locals=locals_values,
                freeze_resistant=bool(item.get("freeze_resistant", False)),
                recursive=bool(item.get("recursive", False)),
                freeze_count=int(item.get("freeze_count", 0)),
                cutscene_override=int(item.get("cutscene_override", 0)),
                room=room_number,
            )
            if not 0 <= slot.number <= 255:
                raise SaveFormatError("SCUMM save script number is outside 0..255")
            if not 0 <= slot.pc <= len(slot.program):
                raise SaveFormatError(f"SCUMM save PC lies outside resource {key!r}")
            if slot.delay < 0:
                raise SaveFormatError("SCUMM save contains a negative script delay")
            if slot.freeze_count < 0 or slot.freeze_count > 255:
                raise SaveFormatError("SCUMM save contains an invalid script freeze count")
            if slot.cutscene_override < 0 or slot.cutscene_override > 255:
                raise SaveFormatError("SCUMM save contains an invalid cutscene override depth")
            scripts.append(slot)

        cutscenes_raw = data.get("cutscenes", [])
        if not isinstance(cutscenes_raw, list) or len(cutscenes_raw) > _MAX_CUTSCENE_DEPTH:
            raise SaveFormatError("SCUMM save cutscene stack is invalid")

        def parse_cutscene_record(raw: object) -> CutsceneState:
            if not isinstance(raw, dict):
                raise SaveFormatError("SCUMM save cutscene record must be an object")
            data_value = int(raw.get("data", -0x10000))
            override_pc_raw = raw.get("override_pc")
            override_slot_raw = raw.get("override_slot")
            if not -0x8000 <= data_value <= 0x7FFF:
                raise SaveFormatError("SCUMM save cutscene data must fit s16")
            if (override_pc_raw is None) != (override_slot_raw is None):
                raise SaveFormatError("SCUMM save cutscene override is incomplete")
            if override_pc_raw is None:
                override_pc = override_slot = None
            else:
                override_pc, override_slot = int(override_pc_raw), int(override_slot_raw)
                if not 0 <= override_slot < len(scripts):
                    raise SaveFormatError("SCUMM save cutscene override slot is invalid")
                if not 0 <= override_pc <= len(scripts[override_slot].program):
                    raise SaveFormatError("SCUMM save cutscene override PC is invalid")
            return CutsceneState(data_value, override_pc, override_slot)

        cutscenes = [parse_cutscene_record(raw) for raw in cutscenes_raw]
        cutscene_sentinel = parse_cutscene_record(
            data.get("cutscene_sentinel", CutsceneState().to_dict())
        )
        if cutscene_sentinel.data != 0:
            raise SaveFormatError("SCUMM save cutscene sentinel data must be zero")
        if sum(slot.cutscene_override for slot in scripts) < len(cutscenes):
            raise SaveFormatError("SCUMM save cutscene stack has no owning script depth")

        sentences_raw = data.get("sentences", [])
        if not isinstance(sentences_raw, list) or len(sentences_raw) > _MAX_SENTENCES:
            raise SaveFormatError("SCUMM save sentence queue is invalid")
        sentences: list[SentenceState] = []
        for raw in sentences_raw:
            if not isinstance(raw, dict):
                raise SaveFormatError("SCUMM save sentence record must be an object")
            verb = int(raw.get("verb", -1))
            object_a = int(raw.get("object_a", -1))
            object_b = int(raw.get("object_b", -1))
            freeze_count = int(raw.get("freeze_count", -1))
            if not 0 <= verb <= 0xFF or not 0 <= object_a <= 0xFFFF or not 0 <= object_b <= 0xFFFF:
                raise SaveFormatError("SCUMM save sentence operands are invalid")
            if not 0 <= freeze_count <= 0xFF:
                raise SaveFormatError("SCUMM save sentence freeze depth is invalid")
            preposition = raw.get("preposition")
            if not isinstance(preposition, bool) or preposition != (object_b != 0):
                raise SaveFormatError("SCUMM save sentence preposition is noncanonical")
            sentences.append(SentenceState(verb, object_a, object_b, freeze_count))

        sound_raw = data.get("sound_kludge", {"queue": [], "history": [], "result": 0})
        if not isinstance(sound_raw, dict):
            raise SaveFormatError("SCUMM save soundKludge state must be an object")

        def parse_sound_commands(raw: object, maximum: int, name: str) -> list[list[int]]:
            if not isinstance(raw, list) or len(raw) > maximum:
                raise SaveFormatError(f"SCUMM save soundKludge {name} is invalid")
            commands: list[list[int]] = []
            for command in raw:
                if not isinstance(command, list) or not 1 <= len(command) <= _LOCAL_VARIABLE_COUNT:
                    raise SaveFormatError(f"SCUMM save soundKludge {name} command is invalid")
                values = [int(value) for value in command]
                if any(value < -0x8000 or value > 0x7FFF for value in values):
                    raise SaveFormatError(
                        f"SCUMM save soundKludge {name} value must fit s16"
                    )
                commands.append(values)
            return commands

        sound_queue = parse_sound_commands(
            sound_raw.get("queue"), _MAX_SOUND_COMMANDS, "queue"
        )
        sound_history = parse_sound_commands(
            sound_raw.get("history"), _MAX_SOUND_HISTORY, "history"
        )
        sound_result = int(sound_raw.get("result", -0x10000))
        if not -0x8000 <= sound_result <= 0x7FFF:
            raise SaveFormatError("SCUMM save soundKludge result must fit s16")

        def parse_print_style(raw: object) -> PrintSlotState:
            if not isinstance(raw, dict):
                raise SaveFormatError("SCUMM save print style must be an object")
            position = raw.get("position")
            if not isinstance(position, list) or len(position) != 2:
                raise SaveFormatError("SCUMM save print position is invalid")
            style = PrintSlotState(
                x=int(position[0]), y=int(position[1]), right=int(raw.get("right", -1)),
                height=int(raw.get("height", -1)), color=int(raw.get("color", -1)),
                charset=int(raw.get("charset", -1)), center=raw.get("center"),
                overhead=raw.get("overhead"),
            )
            if any(value < -0x8000 or value > 0x7FFF for value in (style.x, style.y, style.right)):
                raise SaveFormatError("SCUMM save print coordinate must fit s16")
            if not 0 <= style.height <= 0xFFFF or not 0 <= style.color <= 255 or not 0 <= style.charset <= 255:
                raise SaveFormatError("SCUMM save print scalar is invalid")
            if not isinstance(style.center, bool) or not isinstance(style.overhead, bool):
                raise SaveFormatError("SCUMM save print flags are invalid")
            return style

        print_raw = data.get("print")
        if print_raw is None:
            print_slots = [PrintSlotState(right=room_ops.room_width - 1) for _ in range(4)]
            print_messages: list[PrintMessageState] = []
        else:
            if not isinstance(print_raw, dict):
                raise SaveFormatError("SCUMM save print state is invalid")
            slots_raw = print_raw.get("slots")
            messages_raw = print_raw.get("messages")
            if not isinstance(slots_raw, list) or len(slots_raw) != 4:
                raise SaveFormatError("SCUMM save must contain four print slots")
            if not isinstance(messages_raw, list) or len(messages_raw) > _MAX_PRINT_MESSAGES:
                raise SaveFormatError("SCUMM save print message queue is invalid")
            print_slots = [parse_print_style(raw) for raw in slots_raw]
            print_messages = []
            for raw in messages_raw:
                if not isinstance(raw, dict):
                    raise SaveFormatError("SCUMM save print message must be an object")
                actor, text_slot = int(raw.get("actor", -1)), int(raw.get("slot", -1))
                raw_bytes = raw.get("raw")
                if not 0 <= actor <= 255 or not 0 <= text_slot < 4:
                    raise SaveFormatError("SCUMM save print message identity is invalid")
                if not isinstance(raw_bytes, list):
                    raise SaveFormatError("SCUMM save print message bytes are invalid")
                try:
                    encoded = bytearray(int(value) for value in raw_bytes)
                    decode_scumm_v5_text(encoded)
                except (ValueError, ResourceError) as exc:
                    raise SaveFormatError(f"SCUMM save print message is invalid: {exc}") from exc
                if not 1 <= len(encoded) <= _MAX_STRING_BYTES:
                    raise SaveFormatError("SCUMM save print message is too long")
                print_messages.append(
                    PrintMessageState(actor, text_slot, parse_print_style(raw), encoded)
                )

        bit_variables = [False] * 4096
        bits_raw = data.get("bits", [])
        if not isinstance(bits_raw, list):
            raise SaveFormatError("SCUMM save bit-variable list must be an array")
        for raw_index in bits_raw:
            index = int(raw_index)
            if not 0 <= index < len(bit_variables):
                raise SaveFormatError(f"SCUMM save bit-variable index {index} is invalid")
            bit_variables[index] = True

        strings_raw = data.get("strings", {})
        if not isinstance(strings_raw, dict) or len(strings_raw) > 256:
            raise SaveFormatError("SCUMM save string table is invalid")
        strings: dict[int, bytearray] = {}
        for raw_id, raw_value in strings_raw.items():
            try:
                string_id = int(raw_id)
                value = bytearray.fromhex(str(raw_value))
            except (TypeError, ValueError) as exc:
                raise SaveFormatError("SCUMM save contains an invalid encoded string") from exc
            if not 0 <= string_id <= 255:
                raise SaveFormatError(f"SCUMM save string id {string_id} is invalid")
            if not 1 <= len(value) <= _MAX_STRING_BYTES:
                raise SaveFormatError(
                    f"SCUMM save string {string_id} has invalid size {len(value)}"
                )
            strings[string_id] = value

        room_ops_raw = data.get("room_ops")
        if not isinstance(room_ops_raw, dict):
            raise SaveFormatError("SCUMM save roomOps state must be an object")
        try:
            room_width = int(room_ops_raw["room_width"])
            scroll = [int(value) for value in room_ops_raw["scroll"]]
            screen = [int(value) for value in room_ops_raw["screen"]]
            scale_raw = room_ops_raw["scale_slots"]
            intensity = tuple(int(value) for value in room_ops_raw["intensity"])
            rgb_intensity = tuple(int(value) for value in room_ops_raw["rgb_intensity"])
            shadow = tuple(int(value) for value in room_ops_raw["shadow"])
            transform = tuple(int(value) for value in room_ops_raw["transform"])
            cycle_delays = [int(value) for value in room_ops_raw["cycle_delays"]]
            palette_raw = room_ops_raw["palette_overrides"]
            save_load_request = tuple(
                int(value) for value in room_ops_raw["save_load_request"]
            )
            auxiliary_raw = room_ops_raw["auxiliary_files"]
        except (KeyError, TypeError, ValueError) as exc:
            raise SaveFormatError("SCUMM save roomOps state is malformed") from exc
        if not 1 <= room_width <= 32767 or len(scroll) != 2 or len(screen) != 2:
            raise SaveFormatError("SCUMM save roomOps geometry is invalid")
        if not isinstance(scale_raw, dict) or len(scale_raw) > _ROOM_SCALE_SLOTS:
            raise SaveFormatError("SCUMM save roomOps scale slots are invalid")
        scale_slots: dict[int, tuple[int, int, int, int]] = {}
        for raw_index, raw_values in scale_raw.items():
            index = int(raw_index)
            values = tuple(int(value) for value in raw_values)
            if not 0 <= index < _ROOM_SCALE_SLOTS or len(values) != 4:
                raise SaveFormatError("SCUMM save roomOps scale slot is invalid")
            if any(value < 0 or value > 255 for value in values):
                raise SaveFormatError("SCUMM save roomOps scale value is invalid")
            scale_slots[index] = values
        if any(len(values) != size for values, size in (
            (intensity, 5), (rgb_intensity, 5), (shadow, 5), (transform, 4),
            (save_load_request, 2),
        )):
            raise SaveFormatError("SCUMM save roomOps tuple has the wrong size")
        if len(cycle_delays) != 16 or any(value < 0 or value > 0xFFFF for value in cycle_delays):
            raise SaveFormatError("SCUMM save roomOps cycle delays are invalid")
        if not isinstance(palette_raw, dict) or len(palette_raw) > 256:
            raise SaveFormatError("SCUMM save roomOps palette overrides are invalid")
        palette_overrides: dict[int, tuple[int, int, int]] = {}
        for raw_index, raw_rgb in palette_raw.items():
            index = int(raw_index)
            rgb = tuple(int(value) for value in raw_rgb)
            if not 0 <= index <= 255 or len(rgb) != 3 or any(
                value < 0 or value > 255 for value in rgb
            ):
                raise SaveFormatError("SCUMM save roomOps palette override is invalid")
            palette_overrides[index] = rgb
        if not isinstance(auxiliary_raw, dict) or len(auxiliary_raw) > 64:
            raise SaveFormatError("SCUMM save roomOps auxiliary files are invalid")
        auxiliary_files: dict[str, bytearray] = {}
        for raw_name, raw_value in auxiliary_raw.items():
            name = str(raw_name)
            try:
                encoded_name = name.encode("latin-1")
                value = bytearray.fromhex(str(raw_value))
            except (UnicodeEncodeError, ValueError) as exc:
                raise SaveFormatError("SCUMM save roomOps auxiliary data is invalid") from exc
            if not 1 <= len(encoded_name) <= 63 or not 1 <= len(value) <= 255:
                raise SaveFormatError("SCUMM save roomOps auxiliary entry is invalid")
            auxiliary_files[name] = value
        room_ops = RoomOpsState(
            room_width=room_width,
            scroll_min_x=scroll[0],
            scroll_max_x=scroll[1],
            screen_top=screen[0],
            screen_bottom=screen[1],
            shake_enabled=bool(room_ops_raw.get("shake", False)),
            scale_slots=scale_slots,
            intensity=intensity,
            fade_effect=int(room_ops_raw.get("fade_effect", 0)),
            rgb_intensity=rgb_intensity,
            shadow=shadow,
            transform=transform,
            cycle_delays=cycle_delays,
            palette_overrides=palette_overrides,
            save_load_request=save_load_request,
            auxiliary_files=auxiliary_files,
        )

        camera = data.get("camera")
        camera_follow_raw = data.get("camera_follow_actor")
        cursor = data.get("cursor")
        cursor_command = data.get("cursor_command", {})
        if not isinstance(camera, list) or len(camera) != 2:
            raise SaveFormatError("SCUMM save camera must contain two coordinates")
        if camera_follow_raw is None:
            camera_follow_actor = None
        elif isinstance(camera_follow_raw, int) and not isinstance(camera_follow_raw, bool) and 0 <= camera_follow_raw < _MAX_ACTORS:
            camera_follow_actor = camera_follow_raw
        else:
            raise SaveFormatError("SCUMM save camera-follow actor is invalid")
        if not isinstance(cursor, list) or len(cursor) != 3:
            raise SaveFormatError("SCUMM save cursor must contain x, y, and visibility")
        if not isinstance(cursor_command, dict):
            raise SaveFormatError("SCUMM save cursor command state must be an object")
        room = int(data.get("current_room", -1))
        if not 0 <= room <= 255:
            raise SaveFormatError("SCUMM save room must be in 0..255")
        cursor_x, cursor_y = int(cursor[0]), int(cursor[1])
        logical_width = context.profile.video.logical_width or context.profile.video.width
        logical_height = context.profile.video.logical_height or context.profile.video.height
        if not (
            0 <= cursor_x < logical_width
            and 0 <= cursor_y < logical_height
        ):
            raise SaveFormatError("SCUMM save cursor lies outside the logical surface")
        operations = int(data.get("operations", 0))
        frames = int(data.get("frames", 0))
        if operations < 0 or frames < 0:
            raise SaveFormatError("SCUMM save counters must not be negative")
        random_state = int(data.get("random_state", 0))
        if not 1 <= random_state <= 0xFFFF:
            raise SaveFormatError("SCUMM save random state must be a nonzero u16")
        resource_mapper_raw = data.get("resource_mapper")
        if not isinstance(resource_mapper_raw, list) or len(resource_mapper_raw) != 128:
            raise SaveFormatError("SCUMM save resource mapper must contain 128 rooms")
        resource_mapper = [int(value) for value in resource_mapper_raw]
        if any(value < 0 or value > 255 for value in resource_mapper):
            raise SaveFormatError("SCUMM save resource mapper room must fit u8")
        resource_ops_raw = data.get("resource_ops")
        if not isinstance(resource_ops_raw, dict):
            raise SaveFormatError("SCUMM save resource intent must be an object")

        def resource_sets(name: str, kinds: tuple[str, ...]) -> dict[str, set[int]]:
            raw = resource_ops_raw.get(name)
            if not isinstance(raw, dict) or set(raw) != set(kinds):
                raise SaveFormatError(f"SCUMM save resource {name} table is invalid")
            result: dict[str, set[int]] = {}
            for kind in kinds:
                values = raw[kind]
                if not isinstance(values, list):
                    raise SaveFormatError(f"SCUMM save resource {name} ids are invalid")
                ids = [int(value) for value in values]
                if len(set(ids)) != len(ids) or any(value < 0 or value > 255 for value in ids):
                    raise SaveFormatError(f"SCUMM save resource {name} id must be a unique u8")
                result[kind] = set(ids)
            return result

        loaded_resources = resource_sets("loaded", _RESOURCE_KINDS)
        locked_resources = resource_sets("locked", _LOCKABLE_RESOURCE_KINDS)
        object_raw = resource_ops_raw.get("last_object")
        if object_raw is None:
            last_object = None
        elif isinstance(object_raw, list) and len(object_raw) == 2:
            last_object = (int(object_raw[0]), int(object_raw[1]))
            if not 0 <= last_object[0] <= 255 or not 0 <= last_object[1] <= 0xFFFF:
                raise SaveFormatError("SCUMM save loaded object reference is invalid")
        else:
            raise SaveFormatError("SCUMM save loaded object reference is invalid")
        object_classes_raw = data.get("object_classes", {})
        if not isinstance(object_classes_raw, dict) or len(object_classes_raw) > _MAX_CLASS_OBJECTS:
            raise SaveFormatError("SCUMM save object-class table is invalid")
        object_classes: dict[int, set[int]] = {}
        for object_key, classes_raw in object_classes_raw.items():
            try:
                object_id = int(object_key)
            except (TypeError, ValueError) as exc:
                raise SaveFormatError("SCUMM save object-class id is invalid") from exc
            if str(object_id) != object_key or not 0 <= object_id <= 0xFFFF:
                raise SaveFormatError("SCUMM save object-class entry is invalid")
            if not isinstance(classes_raw, list) or not classes_raw:
                raise SaveFormatError("SCUMM save object-class list is invalid")
            classes = [int(value) for value in classes_raw]
            if (
                classes != sorted(classes)
                or len(set(classes)) != len(classes)
                or any(value < 1 or value > 32 for value in classes)
            ):
                raise SaveFormatError("SCUMM save object classes must be sorted unique ids 1..32")
            object_classes[object_id] = set(classes)
        object_states_raw = data.get("object_states", {})
        if not isinstance(object_states_raw, dict) or len(object_states_raw) > _MAX_OBJECT_STATES:
            raise SaveFormatError("SCUMM save object-state table is invalid")
        object_states: dict[int, int] = {}
        for object_key, state_raw in object_states_raw.items():
            try:
                object_id, state = int(object_key), int(state_raw)
            except (TypeError, ValueError) as exc:
                raise SaveFormatError("SCUMM save object-state entry is invalid") from exc
            if str(object_id) != object_key or not 1 <= object_id <= 0xFFFF or not 0 <= state <= 255:
                raise SaveFormatError("SCUMM save object-state entry is invalid")
            object_states[object_id] = state
        room_objects_raw = data.get("room_objects", {})
        if not isinstance(room_objects_raw, dict) or len(room_objects_raw) > _MAX_LOCAL_OBJECTS:
            raise SaveFormatError("SCUMM save room-object table is invalid")
        room_objects: dict[int, RoomObjectState] = {}
        for object_key, raw in room_objects_raw.items():
            try:
                object_id = int(object_key)
            except (TypeError, ValueError) as exc:
                raise SaveFormatError("SCUMM save room-object id is invalid") from exc
            if str(object_id) != object_key or not 1 <= object_id <= 0xFFFF or not isinstance(raw, dict):
                raise SaveFormatError("SCUMM save room-object entry is invalid")

            def object_pair(name: str) -> tuple[int, int]:
                value = raw.get(name)
                if not isinstance(value, list) or len(value) != 2:
                    raise SaveFormatError(f"SCUMM save room-object {name} is invalid")
                return int(value[0]), int(value[1])

            position = object_pair("position")
            size = object_pair("size")
            walk = object_pair("walk")
            state = int(raw.get("state", -1))
            if any(value < -0x8000 or value > 0x7FFF for value in (*position, *walk)):
                raise SaveFormatError("SCUMM save room-object coordinate must fit s16")
            if any(value < 0 or value > 0xFFFF for value in size) or not 0 <= state <= 255:
                raise SaveFormatError("SCUMM save room-object size/state is invalid")
            if state != object_states.get(object_id, 0):
                raise SaveFormatError("SCUMM save room-object state is noncanonical")
            room_objects[object_id] = RoomObjectState(
                object_id, *position, *size, *walk, state
            )
        draw_queue_raw = data.get("object_draw_queue", [])
        if not isinstance(draw_queue_raw, list) or len(draw_queue_raw) > _MAX_LOCAL_OBJECTS:
            raise SaveFormatError("SCUMM save draw-object queue is invalid")
        object_draw_queue = [int(value) for value in draw_queue_raw]
        if any(value not in room_objects for value in object_draw_queue):
            raise SaveFormatError("SCUMM save draw-object queue references a nonlocal object")
        verbs_raw = data.get("verbs", {})
        if not isinstance(verbs_raw, dict) or len(verbs_raw) > _MAX_VERBS + _MAX_SAVED_VERBS:
            raise SaveFormatError("SCUMM save verb table is invalid")
        verbs: dict[int, VerbState] = {}
        saved_verbs: list[tuple[int, VerbState]] = []
        for verb_key, raw in verbs_raw.items():
            try:
                key_parts = verb_key.split(":")
                verb_id = int(key_parts[0])
            except (TypeError, ValueError) as exc:
                raise SaveFormatError("SCUMM save verb id is invalid") from exc
            active_key = len(key_parts) == 1 and str(verb_id) == verb_key
            saved_key = (
                len(key_parts) == 3
                and str(verb_id) == key_parts[0]
                and key_parts[1].isdigit()
                and key_parts[2].isdigit()
            )
            if not (active_key or saved_key) or not 0 <= verb_id <= 255 or not isinstance(raw, dict):
                raise SaveFormatError("SCUMM save verb entry is invalid")
            scalar_names = (
                "color", "hicolor", "dimcolor", "background_color", "charset", "key",
            )
            try:
                scalars = {name: int(raw[name]) for name in scalar_names}
                mode = int(raw["mode"])
                save_id = int(raw["save_id"])
                image_index = int(raw["image_index"])
                original_left = int(raw["original_left"])
            except (KeyError, TypeError, ValueError) as exc:
                raise SaveFormatError("SCUMM save verb scalar is malformed") from exc
            if any(value < 0 or value > 255 for value in scalars.values()):
                raise SaveFormatError("SCUMM save verb byte field is invalid")
            if not 0 <= mode <= 2 or not 0 <= save_id <= 0xFFFF or not 0 <= image_index <= 0xFFFF:
                raise SaveFormatError("SCUMM save verb mode or identity is invalid")
            position_raw = raw.get("position")
            if not isinstance(position_raw, list) or len(position_raw) != 2:
                raise SaveFormatError("SCUMM save verb position is invalid")
            position = (int(position_raw[0]), int(position_raw[1]))
            if any(value < -0x8000 or value > 0x7FFF for value in (*position, original_left)):
                raise SaveFormatError("SCUMM save verb coordinate must fit s16")
            kind = raw.get("kind")
            if kind not in ("text", "image"):
                raise SaveFormatError("SCUMM save verb kind is invalid")
            center = raw.get("center")
            if not isinstance(center, bool):
                raise SaveFormatError("SCUMM save verb center flag is invalid")
            image_source_raw = raw.get("image_source")
            if image_source_raw is None:
                image_source = None
            elif isinstance(image_source_raw, list) and len(image_source_raw) == 2:
                image_source = (int(image_source_raw[0]), int(image_source_raw[1]))
                if not 0 <= image_source[0] <= 255 or not 0 <= image_source[1] <= 0xFFFF:
                    raise SaveFormatError("SCUMM save verb image source is invalid")
            else:
                raise SaveFormatError("SCUMM save verb image source is invalid")
            name_raw = raw.get("name")
            if name_raw is None:
                name = None
            else:
                try:
                    name = bytearray.fromhex(str(name_raw))
                except ValueError as exc:
                    raise SaveFormatError("SCUMM save verb name is invalid") from exc
                if not name or len(name) > _MAX_VERB_NAME_BYTES or name[-1] != 0:
                    raise SaveFormatError("SCUMM save verb name must be a bounded encoded string")
                try:
                    decode_scumm_v5_text(name)
                except ResourceError as exc:
                    raise SaveFormatError(f"SCUMM save verb name is invalid: {exc}") from exc
            parsed_verb = VerbState(
                color=scalars["color"], hicolor=scalars["hicolor"],
                dimcolor=scalars["dimcolor"], background_color=scalars["background_color"],
                kind=kind, charset=scalars["charset"], mode=mode, save_id=save_id,
                key=scalars["key"], center=center, position=position,
                original_left=original_left, image_index=image_index,
                image_source=image_source, name=name,
            )
            if active_key:
                if parsed_verb.save_id != 0 or verb_id in verbs:
                    raise SaveFormatError("SCUMM save active verb has a saved identity")
                verbs[verb_id] = parsed_verb
            else:
                bank, position = int(key_parts[1]), int(key_parts[2])
                if (
                    not 1 <= bank <= 255
                    or parsed_verb.save_id != bank
                    or position != len(saved_verbs)
                    or len(saved_verbs) >= _MAX_SAVED_VERBS
                ):
                    raise SaveFormatError("SCUMM save saved-verb identity is invalid")
                saved_verbs.append((verb_id, parsed_verb))
        actors_raw = data.get("actors")
        if not isinstance(actors_raw, dict) or len(actors_raw) > _MAX_ACTORS:
            raise SaveFormatError("SCUMM save actor table is invalid")
        actors: dict[int, ActorState] = {}
        for actor_key, raw in actors_raw.items():
            try:
                actor_id = int(actor_key)
            except (TypeError, ValueError) as exc:
                raise SaveFormatError("SCUMM save actor id is invalid") from exc
            if str(actor_id) != actor_key or not 0 <= actor_id < _MAX_ACTORS or not isinstance(raw, dict):
                raise SaveFormatError("SCUMM save actor entry is invalid")
            def pair(name: str) -> tuple[int, int]:
                value = raw.get(name)
                if not isinstance(value, list) or len(value) != 2:
                    raise SaveFormatError(f"SCUMM save actor {name} is invalid")
                result = (int(value[0]), int(value[1]))
                if any(item < 0 or item > 255 for item in result):
                    raise SaveFormatError(f"SCUMM save actor {name} must contain u8 values")
                return result
            frames_raw = raw.get("frames")
            if not isinstance(frames_raw, list) or len(frames_raw) != 5:
                raise SaveFormatError("SCUMM save actor frames are invalid")
            actor_frames = tuple(int(value) for value in frames_raw)
            if any(value < 0 or value > 255 for value in actor_frames):
                raise SaveFormatError("SCUMM save actor frame must fit u8")
            palette_raw = raw.get("palette")
            if not isinstance(palette_raw, dict):
                raise SaveFormatError("SCUMM save actor palette is invalid")
            palette: dict[int, int] = {}
            for index_raw, color_raw in palette_raw.items():
                index, color = int(index_raw), int(color_raw)
                if str(index) != index_raw or not 0 <= index <= 31 or not 0 <= color <= 255:
                    raise SaveFormatError("SCUMM save actor palette entry is invalid")
                palette[index] = color
            try:
                name = bytearray.fromhex(str(raw.get("name", "")))
            except ValueError as exc:
                raise SaveFormatError("SCUMM save actor name is invalid") from exc
            if not name or len(name) > _MAX_STRING_BYTES or name[-1] != 0:
                raise SaveFormatError("SCUMM save actor name must be a terminated encoded string")
            try:
                decode_scumm_v5_text(name)
            except ResourceError as exc:
                raise SaveFormatError(f"SCUMM save actor name is invalid: {exc}") from exc
            scalar_names = (
                "costume", "sound", "talk_color", "width", "box_scale",
                "force_clip", "animation_speed", "shadow", "animation",
            )
            scalars = {name: int(raw.get(name, -1)) for name in scalar_names}
            if any(value < 0 or value > 255 for value in scalars.values()):
                raise SaveFormatError("SCUMM save actor scalar must fit u8")
            elevation = int(raw.get("elevation", -0x10000))
            if not -0x8000 <= elevation <= 0x7FFF:
                raise SaveFormatError("SCUMM save actor elevation must fit s16")
            ignore_boxes = raw.get("ignore_boxes")
            if not isinstance(ignore_boxes, bool):
                raise SaveFormatError("SCUMM save actor ignore-boxes flag is invalid")
            actors[actor_id] = ActorState(
                costume=scalars["costume"], walk_speed=pair("walk_speed"),
                sound=scalars["sound"], init_frame=actor_frames[0], walk_frame=actor_frames[1],
                stand_frame=actor_frames[2], talk_frames=(actor_frames[3], actor_frames[4]),
                elevation=elevation, palette=palette, talk_color=scalars["talk_color"],
                name=name, width=scalars["width"], scale=pair("scale"),
                box_scale=scalars["box_scale"], force_clip=scalars["force_clip"],
                ignore_boxes=ignore_boxes,
                animation_speed=scalars["animation_speed"], shadow=scalars["shadow"],
                animation=scalars["animation"],
            )
        last_opcode = int(data.get("last_opcode", 0))
        if not 0 <= last_opcode <= 255:
            raise SaveFormatError("SCUMM save last opcode must fit u8")
        audio_state = data.get("audio")
        if self._audio is None and audio_state is not None:
            raise SaveFormatError("SCUMM save has audio state but the profile has no adapter")
        if self._audio is not None and audio_state is None:
            raise SaveFormatError("SCUMM save is missing audio state")

        self.state.variables = variables
        self.state.bit_variables = bit_variables
        self.state.strings = strings
        self.state.room_ops = room_ops
        self.state.random_state = random_state
        self.state.resource_mapper = resource_mapper
        self.state.resource_ops = ResourceOpsState(
            loaded=loaded_resources,
            locked=locked_resources,
            last_object=last_object,
        )
        self.state.actors = actors
        self.state.object_classes = object_classes
        self.state.object_states = object_states
        self.state.verbs = verbs
        self.state.saved_verbs = saved_verbs
        self.state.cutscene_sentinel = cutscene_sentinel
        self.state.cutscenes = cutscenes
        self.state.cutscene_script_index = None
        self.state.sentences = sentences
        self.state.sound_queue = sound_queue
        self.state.sound_history = sound_history
        self.state.sound_result = sound_result
        self.state.print_slots = print_slots
        self.state.print_messages = print_messages
        self.state.scripts = scripts
        self.state.current_room = room
        self.state.camera_x, self.state.camera_y = map(int, camera)
        self.state.camera_follow_actor = camera_follow_actor
        self.state.cursor_x = cursor_x
        self.state.cursor_y = cursor_y
        self.state.cursor_visible = bool(cursor[2])
        self.state.cursor_state = int(cursor_command.get("state", int(self.state.cursor_visible)))
        self.state.user_input_state = int(cursor_command.get("user_input", 1))
        image = cursor_command.get("image", [0, 0])
        hotspot = cursor_command.get("hotspot", [0, 0, 0])
        colors = cursor_command.get("charset_colors", [])
        if not isinstance(image, list) or len(image) != 2:
            raise SaveFormatError("SCUMM save cursor image must contain two values")
        if not isinstance(hotspot, list) or len(hotspot) != 3:
            raise SaveFormatError("SCUMM save cursor hotspot must contain three values")
        if not isinstance(colors, list) or len(colors) > 16:
            raise SaveFormatError("SCUMM save charset colors are invalid")
        self.state.cursor_image = tuple(map(int, image))
        self.state.cursor_hotspot = tuple(map(int, hotspot))
        self.state.cursor_id = int(cursor_command.get("cursor_id", 0))
        self.state.charset_id = int(cursor_command.get("charset_id", 0))
        self.state.charset_colors = [int(value) for value in colors]
        self.state.operations = operations
        self.state.frames = frames
        self.state.last_opcode = last_opcode
        self.state.halted = bool(data.get("halted", False))
        if self._input is not None:
            self._input.state.cursor_x = cursor_x
            self._input.state.cursor_y = cursor_y
            self._input.state.held_buttons.clear()
        self._load_room(
            context,
            self.state.current_room,
            required=False,
            preserve_local_scripts=True,
        )
        resource_objects = self.state.room_objects
        if resource_objects and (set(resource_objects) != set(room_objects) or any(
            (resource_objects[object_id].width, resource_objects[object_id].height)
            != (item.width, item.height)
            for object_id, item in room_objects.items()
        )):
            raise SaveFormatError("SCUMM save room-object table does not match the room resource")
        self.state.room_objects = room_objects
        self.state.object_draw_queue = object_draw_queue
        for message in self.state.print_messages:
            self._present_print(context, message)
        for index, rgb in self.state.room_ops.palette_overrides.items():
            context.services.video.surface.set_palette(index, (rgb,))
        if self._video is None:
            context.services.video.move_cursor(self.state.cursor_x, self.state.cursor_y)
        else:
            self._video.move_cursor(self.state.cursor_x, self.state.cursor_y)
        context.services.video.show_cursor(self.state.cursor_visible)
        if self._audio is not None:
            self._audio.load_state(audio_state)

    def inspect_state(self) -> Mapping[str, object]:
        strings: dict[str, object] = {}
        for string_id, value in sorted(self.state.strings.items()):
            entry: dict[str, object] = {"raw": list(value), "size": len(value)}
            try:
                entry["tokens"] = [token.to_dict() for token in decode_scumm_v5_text(value)]
            except ResourceError as exc:
                entry["decode_error"] = str(exc)
            strings[str(string_id)] = entry
        return {
            "room": self.state.current_room,
            "camera": [self.state.camera_x, self.state.camera_y],
            "camera_follow_actor": self.state.camera_follow_actor,
            "cursor": [self.state.cursor_x, self.state.cursor_y],
            "cursor_command": {
                "state": self.state.cursor_state,
                "user_input": self.state.user_input_state,
                "image": list(self.state.cursor_image),
                "hotspot": list(self.state.cursor_hotspot),
                "cursor_id": self.state.cursor_id,
                "charset_id": self.state.charset_id,
                "charset_colors": list(self.state.charset_colors),
            },
            "bits": [
                index for index, value in enumerate(self.state.bit_variables) if value
            ],
            "strings": strings,
            "room_ops": {
                "room_width": self.state.room_ops.room_width,
                "scroll": [
                    self.state.room_ops.scroll_min_x,
                    self.state.room_ops.scroll_max_x,
                ],
                "screen": [
                    self.state.room_ops.screen_top,
                    self.state.room_ops.screen_bottom,
                ],
                "shake": self.state.room_ops.shake_enabled,
                "scale_slots": {
                    str(index): list(value)
                    for index, value in sorted(self.state.room_ops.scale_slots.items())
                },
                "intensity": list(self.state.room_ops.intensity),
                "fade_effect": self.state.room_ops.fade_effect,
                "rgb_intensity": list(self.state.room_ops.rgb_intensity),
                "shadow": list(self.state.room_ops.shadow),
                "transform": list(self.state.room_ops.transform),
                "cycle_delays": list(self.state.room_ops.cycle_delays),
                "palette_overrides": {
                    str(index): list(value)
                    for index, value in sorted(self.state.room_ops.palette_overrides.items())
                },
                "save_load_request": list(self.state.room_ops.save_load_request),
                "auxiliary_files": {
                    name: list(value)
                    for name, value in sorted(self.state.room_ops.auxiliary_files.items())
                },
            },
            "random_state": self.state.random_state,
            "resource_mapper": list(self.state.resource_mapper),
            "resource_ops": {
                "loaded": {
                    kind: sorted(self.state.resource_ops.loaded[kind])
                    for kind in _RESOURCE_KINDS
                },
                "locked": {
                    kind: sorted(self.state.resource_ops.locked[kind])
                    for kind in _LOCKABLE_RESOURCE_KINDS
                },
                "last_object": (
                    None
                    if self.state.resource_ops.last_object is None
                    else list(self.state.resource_ops.last_object)
                ),
            },
            "actors": {
                str(actor_id): {
                    **actor.to_dict(),
                    "name": list(actor.name),
                }
                for actor_id, actor in sorted(self.state.actors.items())
            },
            "object_classes": {
                str(object_id): sorted(classes)
                for object_id, classes in sorted(self.state.object_classes.items())
            },
            "object_states": {
                str(object_id): state
                for object_id, state in sorted(self.state.object_states.items())
            },
            "room_objects": {
                str(object_id): item.to_dict()
                for object_id, item in sorted(self.state.room_objects.items())
            },
            "object_draw_queue": list(self.state.object_draw_queue),
            "verbs": {
                str(verb_id): {
                    **verb.to_dict(),
                    "name": None if verb.name is None else list(verb.name),
                }
                for verb_id, verb in sorted(self.state.verbs.items())
            },
            "saved_verbs": [
                {"id": verb_id, "bank": verb.save_id, "verb": verb.to_dict()}
                for verb_id, verb in self.state.saved_verbs
            ],
            "cutscenes": {
                "stack_pointer": len(self.state.cutscenes),
                "sentinel": self.state.cutscene_sentinel.to_dict(),
                "records": [record.to_dict() for record in self.state.cutscenes],
                "script_index": self.state.cutscene_script_index,
            },
            "sentences": [sentence.to_dict() for sentence in self.state.sentences],
            "sound_kludge": {
                "queue": [list(command) for command in self.state.sound_queue],
                "history": [list(command) for command in self.state.sound_history],
                "result": self.state.sound_result,
            },
            "print": {
                "slots": [print_slot.to_dict() for print_slot in self.state.print_slots],
                "messages": [message.to_dict() for message in self.state.print_messages],
            },
            "variables": {
                str(index): value
                for index, value in enumerate(self.state.variables)
                if value != 0
            },
            "scripts": [slot.to_dict() for slot in self.state.scripts],
            "operations": self.state.operations,
            "frames": self.state.frames,
            "last_opcode": self.state.last_opcode,
            "room_hash": self.state.room_hash,
            "input": None if self._input is None else self._input.state.to_dict(),
            "video": None if self._video is None else self._video.inspect(),
            "audio": None if self._audio is None else self._audio.inspect(),
        }
