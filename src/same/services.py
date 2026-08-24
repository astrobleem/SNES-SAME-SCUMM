"""Concrete host services exposed to SAME engines."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Deque, Generic, Iterable, TypeVar

from .abi import (
    AudioOpcode,
    DebugOpcode,
    Endpoint,
    InputOpcode,
    JobsOpcode,
    SaveOpcode,
    Service,
    StorageOpcode,
    TimeOpcode,
    VideoOpcode,
)
from .capabilities import DEFAULT_HOST_CAPABILITIES, EngineCapability
from .events import EventBus
from .input import InputProfile, LogicalSnapshot, PhysicalController, profile as input_profile
from .profile import EngineProfile
from .resources import BoundResourceProvider, ResourceProvider
from .savegame import InMemorySaveStore
from .video import PresentRecord, VideoService


class InputEventType(str, Enum):
    DIGITAL = "digital"
    POINTER_MOVE = "pointer_move"
    POINTER_BUTTON = "pointer_button"
    TEXT = "text"
    QUIT = "quit"


@dataclass(frozen=True, slots=True)
class InputEvent:
    type: InputEventType
    frame: int
    action: str = ""
    pressed: bool = False
    x: int = 0
    y: int = 0
    text: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type.value,
            "frame": self.frame,
            "action": self.action,
            "pressed": self.pressed,
            "x": self.x,
            "y": self.y,
            "text": self.text,
        }


class InputService:
    def __init__(self, mapping: InputProfile, events: EventBus) -> None:
        self.mapping = mapping
        self.events = events
        self.controller = PhysicalController()
        self.logical = LogicalSnapshot(frozenset(), frozenset(), frozenset())
        self.pointer_x = 0
        self.pointer_y = 0
        self.pointer_buttons = 0
        self._queue: Deque[InputEvent] = deque()

    def sample_word(self, frame: int, word: int) -> LogicalSnapshot:
        physical = self.controller.update(word)
        logical = self.mapping.map_snapshot(physical)
        self.logical = logical
        for action in sorted(logical.pressed):
            self._queue.append(
                InputEvent(InputEventType.DIGITAL, frame, action=action, pressed=True)
            )
        for action in sorted(logical.released):
            self._queue.append(
                InputEvent(InputEventType.DIGITAL, frame, action=action, pressed=False)
            )
        if physical.pressed or physical.released or frame == 0:
            self.events.emit(
                service=Service.INPUT,
                opcode=InputOpcode.SNAPSHOT,
                arg0=physical.held,
                arg1=((physical.pressed & 0xFFFF) << 16)
                | (physical.released & 0xFFFF),
                source=Endpoint.SCPU,
                destination=Endpoint.ENGINE,
            )
        return logical

    def move_pointer(self, frame: int, x: int, y: int) -> None:
        self.pointer_x = int(x)
        self.pointer_y = int(y)
        self._queue.append(
            InputEvent(InputEventType.POINTER_MOVE, frame, x=self.pointer_x, y=self.pointer_y)
        )
        self.events.emit(
            service=Service.INPUT,
            opcode=InputOpcode.POINTER,
            arg0=((self.pointer_x & 0xFFFF) << 16) | (self.pointer_y & 0xFFFF),
            arg1=self.pointer_buttons,
            source=Endpoint.SCPU,
            destination=Endpoint.ENGINE,
        )

    def set_pointer_button(self, frame: int, button: int, pressed: bool) -> None:
        mask = 1 << int(button)
        if pressed:
            self.pointer_buttons |= mask
        else:
            self.pointer_buttons &= ~mask
        self._queue.append(
            InputEvent(
                InputEventType.POINTER_BUTTON,
                frame,
                action=f"pointer{button}",
                pressed=pressed,
                x=self.pointer_x,
                y=self.pointer_y,
            )
        )

    def submit_text(self, frame: int, text: str) -> None:
        if not text:
            return
        self._queue.append(InputEvent(InputEventType.TEXT, frame, text=text))
        for character in text:
            self.events.emit(
                service=Service.INPUT,
                opcode=InputOpcode.TEXT,
                arg0=ord(character),
                source=Endpoint.HOST,
                destination=Endpoint.ENGINE,
            )

    def request_quit(self, frame: int) -> None:
        self._queue.append(InputEvent(InputEventType.QUIT, frame))

    def drain(self) -> tuple[InputEvent, ...]:
        result = tuple(self._queue)
        self._queue.clear()
        return result


@dataclass(slots=True)
class AudioService:
    events: EventBus
    music_track: int | None = None
    speech_track: int | None = None
    master_volume: int = 255
    sfx_history: list[dict[str, int | str | None]] = field(default_factory=list)
    command_history: list[dict[str, int | str | None]] = field(default_factory=list)

    def play_music(
        self,
        track: int,
        *,
        loop: bool = True,
        resource: str | None = None,
        backend: str = "normalized",
        position: int = 0,
    ) -> None:
        self.music_track = int(track)
        self.command_history.append(
            {
                "command": "music_play",
                "track": self.music_track,
                "loop": int(loop),
                "resource": resource,
                "backend": backend,
                "position": int(position),
            }
        )
        self.events.emit(
            service=Service.AUDIO,
            opcode=AudioOpcode.MUSIC_PLAY,
            arg0=self.music_track,
            arg1=int(loop),
            source=Endpoint.ENGINE,
            destination=Endpoint.SPC,
        )

    def stop_music(self) -> None:
        self.music_track = None
        self.command_history.append({"command": "music_stop", "track": None})
        self.events.emit(
            service=Service.AUDIO,
            opcode=AudioOpcode.MUSIC_STOP,
            source=Endpoint.ENGINE,
            destination=Endpoint.SPC,
        )

    def play_sfx(
        self,
        sound: int,
        *,
        pan: int = 128,
        priority: int = 0,
        resource: str | None = None,
        backend: str = "normalized",
        position: int = 0,
    ) -> None:
        record = {
            "sound": int(sound),
            "pan": int(pan),
            "priority": int(priority),
            "resource": resource,
            "backend": backend,
            "position": int(position),
        }
        self.sfx_history.append(record)
        self.command_history.append({"command": "sfx_play", **record})
        self.events.emit(
            service=Service.AUDIO,
            opcode=AudioOpcode.SFX_PLAY,
            arg0=int(sound),
            arg1=((int(priority) & 0xFFFF) << 16) | (int(pan) & 0xFFFF),
            source=Endpoint.ENGINE,
            destination=Endpoint.SPC,
        )

    def stop_sfx(self, sound: int | None = None) -> None:
        normalized = None if sound is None else int(sound)
        self.command_history.append({"command": "sfx_stop", "sound": normalized})
        self.events.emit(
            service=Service.AUDIO,
            opcode=AudioOpcode.SFX_STOP,
            arg0=0xFFFFFFFF if normalized is None else normalized,
            source=Endpoint.ENGINE,
            destination=Endpoint.SPC,
        )

    def play_speech(
        self,
        track: int,
        *,
        resource: str | None = None,
        backend: str = "normalized",
        position: int = 0,
    ) -> None:
        self.speech_track = int(track)
        self.command_history.append(
            {
                "command": "speech_play",
                "track": int(track),
                "resource": resource,
                "backend": backend,
                "position": int(position),
            }
        )
        self.events.emit(
            service=Service.AUDIO,
            opcode=AudioOpcode.SPEECH_PLAY,
            arg0=int(track),
            source=Endpoint.ENGINE,
            destination=Endpoint.SPC,
        )

    def stop_speech(self) -> None:
        self.speech_track = None
        self.command_history.append({"command": "speech_stop", "track": None})
        self.events.emit(
            service=Service.AUDIO,
            opcode=AudioOpcode.SPEECH_STOP,
            source=Endpoint.ENGINE,
            destination=Endpoint.SPC,
        )

    def set_master_volume(self, volume: int) -> None:
        if not 0 <= int(volume) <= 255:
            raise ValueError("audio master volume must be in 0..255")
        self.master_volume = int(volume)
        self.command_history.append(
            {"command": "master_volume", "volume": self.master_volume}
        )
        self.events.emit(
            service=Service.AUDIO,
            opcode=AudioOpcode.MASTER_VOLUME,
            arg0=self.master_volume,
            source=Endpoint.ENGINE,
            destination=Endpoint.SPC,
        )

    def flush(self) -> None:
        self.command_history.append({"command": "flush"})
        self.events.emit(
            service=Service.AUDIO,
            opcode=AudioOpcode.FLUSH,
            source=Endpoint.ENGINE,
            destination=Endpoint.SPC,
        )


@dataclass(slots=True)
class ClockService:
    tick_hz: int
    events: EventBus
    frame: int = -1

    @property
    def monotonic_us(self) -> int:
        return 0 if self.frame < 0 else (self.frame * 1_000_000) // self.tick_hz

    def advance(self, frame: int) -> None:
        if frame != self.frame + 1:
            raise ValueError(
                f"clock frame must advance by one: current {self.frame}, requested {frame}"
            )
        self.frame = frame
        self.events.emit(
            service=Service.TIME,
            opcode=TimeOpcode.FRAME_TICK,
            arg0=frame,
            arg1=self.monotonic_us,
            source=Endpoint.KERNEL,
            destination=Endpoint.ENGINE,
        )


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class JobResult(Generic[T]):
    identifier: int
    value: T | None
    error: str | None


class JobService:
    """Deterministic synchronous host model for work that may be SA-1 jobs."""

    def __init__(self, events: EventBus) -> None:
        self.events = events
        self._next = 1
        self.results: dict[int, JobResult[object]] = {}

    def submit(self, operation: Callable[[], T]) -> JobResult[T]:
        identifier = self._next
        self._next += 1
        self.events.emit(
            service=Service.JOBS,
            opcode=JobsOpcode.SUBMIT,
            arg0=identifier,
            destination=Endpoint.SA1,
        )
        try:
            value = operation()
        except Exception as exc:  # engine jobs must report, not disappear
            result: JobResult[T] = JobResult(identifier, None, str(exc))
            self.events.emit(
                service=Service.JOBS,
                opcode=JobsOpcode.FAILED,
                arg0=identifier,
                destination=Endpoint.ENGINE,
            )
        else:
            result = JobResult(identifier, value, None)
            self.events.emit(
                service=Service.JOBS,
                opcode=JobsOpcode.COMPLETE,
                arg0=identifier,
                destination=Endpoint.ENGINE,
            )
        self.results[identifier] = result  # type: ignore[assignment]
        return result


@dataclass(slots=True)
class DebugService:
    events: EventBus
    log: list[dict[str, object]] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    def marker(self, name: str, value: int = 0) -> None:
        self.log.append({"kind": "marker", "name": name, "value": int(value)})
        self.events.emit(
            service=Service.DEBUG,
            opcode=DebugOpcode.MARKER,
            arg0=sum(name.encode("utf-8")) & 0xFFFFFFFF,
            arg1=int(value),
            source=Endpoint.ENGINE,
            destination=Endpoint.HOST,
        )

    def increment(self, name: str, amount: int = 1) -> int:
        value = self.counters.get(name, 0) + int(amount)
        self.counters[name] = value
        return value


@dataclass(slots=True)
class HostServices:
    profile: EngineProfile
    capabilities: EngineCapability
    events: EventBus
    resources: ResourceProvider
    saves: object
    video: VideoService
    input: InputService
    audio: AudioService
    clock: ClockService
    jobs: JobService
    debug: DebugService
    packet_history: list[dict[str, object]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        profile: EngineProfile,
        *,
        capabilities: EngineCapability = DEFAULT_HOST_CAPABILITIES,
        resources: ResourceProvider | None = None,
        saves: object | None = None,
        event_capacity: int = 128,
    ) -> "HostServices":
        events = EventBus(event_capacity)
        resources = resources or BoundResourceProvider.from_profile(profile)
        saves = saves or InMemorySaveStore()
        mapping = input_profile(profile.input_profile)
        return cls(
            profile=profile,
            capabilities=capabilities,
            events=events,
            resources=resources,
            saves=saves,
            video=VideoService(profile.video.width, profile.video.height),
            input=InputService(mapping, events),
            audio=AudioService(events),
            clock=ClockService(profile.tick_hz, events),
            jobs=JobService(events),
            debug=DebugService(events),
        )

    def flush_events(self) -> tuple[dict[str, object], ...]:
        packets = tuple(packet.to_dict() for packet in self.events.ring.drain())
        self.packet_history.extend(packets)
        return packets

    def present(self) -> PresentRecord:
        record = self.video.present(self.clock.frame)
        self.events.emit(
            service=Service.VIDEO,
            opcode=VideoOpcode.PRESENT,
            arg0=record.generation,
            arg1=int(record.sha256[:8], 16),
            source=Endpoint.ENGINE,
            destination=Endpoint.SCPU,
        )
        return record

    def resource_read(self, key: str) -> bytes:
        stat = self.resources.stat(key)
        self.events.emit(
            service=Service.STORAGE,
            opcode=StorageOpcode.READ,
            arg0=stat.size,
            arg1=stat.crc32 or 0,
            source=Endpoint.ENGINE,
            destination=Endpoint.HOST,
        )
        return self.resources.read(key)
