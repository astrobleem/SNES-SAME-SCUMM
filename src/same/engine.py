"""Reusable SAME engine lifecycle and registry.

This layer is deliberately broader than ScummVM: a native engine, bytecode
interpreter, or foreign-machine personality can implement the same lifecycle.
SCUMM v5 and AGI are the first concrete clients.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, ClassVar, Iterable, Mapping

from .abi import Endpoint, EngineOpcode, SaveOpcode, Service
from .capabilities import EngineCapability, capability_names
from .errors import (
    EngineCompatibilityError,
    EngineExecutionError,
    EngineLifecycleError,
    EngineRegistrationError,
    SaveFormatError,
)
from .profile import EngineProfile
from .savegame import SaveEnvelope
from .services import HostServices, InputEvent


class Lifecycle(str, Enum):
    CREATED = "created"
    PROBED = "probed"
    RUNNING = "running"
    SUSPENDED = "suspended"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class EngineDescriptor:
    identifier: str
    name: str
    version: str
    families: tuple[str, ...]
    required_capabilities: EngineCapability
    optional_capabilities: EngineCapability = EngineCapability.NONE
    save_schema: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.identifier,
            "name": self.name,
            "version": self.version,
            "families": list(self.families),
            "required_capabilities": list(capability_names(self.required_capabilities)),
            "optional_capabilities": list(capability_names(self.optional_capabilities)),
            "save_schema": self.save_schema,
        }


@dataclass(frozen=True, slots=True)
class ProbeResult:
    supported: bool
    confidence: int
    reason: str

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 100:
            raise ValueError("probe confidence must be in 0..100")

    def to_dict(self) -> dict[str, object]:
        return {
            "supported": self.supported,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class FrameResult:
    operations: int = 0
    yielded: bool = False
    halted: bool = False
    presented: bool = False
    diagnostics: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "operations": self.operations,
            "yielded": self.yielded,
            "halted": self.halted,
            "presented": self.presented,
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True, slots=True)
class EngineContext:
    profile: EngineProfile
    services: HostServices
    negotiated_capabilities: EngineCapability


class Engine(ABC):
    descriptor: ClassVar[EngineDescriptor]

    @classmethod
    def probe(cls, profile: EngineProfile, services: HostServices) -> ProbeResult:
        if profile.engine_id != cls.descriptor.identifier:
            return ProbeResult(False, 0, "profile selects a different engine")
        return ProbeResult(True, 100, "profile engine id matches")

    @abstractmethod
    def boot(self, context: EngineContext) -> None:
        """Initialize engine state and load the initial resources."""

    @abstractmethod
    def tick(self, context: EngineContext) -> FrameResult:
        """Run one profile tick without owning platform timing."""

    def handle_event(self, context: EngineContext, event: InputEvent) -> None:
        del context, event

    @abstractmethod
    def save_state(self, context: EngineContext) -> bytes:
        """Return only engine payload; the host wraps it in a save envelope."""

    @abstractmethod
    def load_state(self, context: EngineContext, payload: bytes) -> None:
        """Restore a payload previously returned by :meth:`save_state`."""

    def suspend(self, context: EngineContext) -> None:
        del context

    def resume(self, context: EngineContext) -> None:
        del context

    def shutdown(self, context: EngineContext) -> None:
        del context

    def inspect_state(self) -> Mapping[str, object]:
        return {}


EngineFactory = Callable[[], Engine]


class EngineRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, EngineFactory] = {}
        self._descriptors: dict[str, EngineDescriptor] = {}

    def register(self, engine_type: type[Engine], *, replace: bool = False) -> None:
        descriptor = engine_type.descriptor
        if descriptor.identifier in self._factories and not replace:
            raise EngineRegistrationError(
                f"engine {descriptor.identifier!r} is already registered"
            )
        self._factories[descriptor.identifier] = engine_type
        self._descriptors[descriptor.identifier] = descriptor

    def create(self, identifier: str) -> Engine:
        try:
            return self._factories[identifier]()
        except KeyError as exc:
            choices = ", ".join(sorted(self._factories)) or "(none)"
            raise EngineRegistrationError(
                f"engine {identifier!r} is not registered; choices: {choices}"
            ) from exc

    def descriptor(self, identifier: str) -> EngineDescriptor:
        try:
            return self._descriptors[identifier]
        except KeyError as exc:
            raise EngineRegistrationError(f"engine {identifier!r} is not registered") from exc

    def descriptors(self) -> tuple[EngineDescriptor, ...]:
        return tuple(self._descriptors[key] for key in sorted(self._descriptors))

    def to_dict(self) -> list[dict[str, object]]:
        return [descriptor.to_dict() for descriptor in self.descriptors()]


class EngineHost:
    def __init__(
        self,
        profile: EngineProfile,
        registry: EngineRegistry,
        *,
        services: HostServices | None = None,
    ) -> None:
        self.profile = profile
        self.registry = registry
        self.services = services or HostServices.create(profile)
        self.engine = registry.create(profile.engine_id)
        self.lifecycle = Lifecycle.CREATED
        self.probe_result: ProbeResult | None = None
        self.negotiated_capabilities = EngineCapability.NONE
        self.context: EngineContext | None = None
        self.frame_results: list[FrameResult] = []

    def _require(self, *states: Lifecycle) -> None:
        if self.lifecycle not in states:
            expected = ", ".join(state.value for state in states)
            raise EngineLifecycleError(
                f"operation requires lifecycle {expected}; current state is {self.lifecycle.value}"
            )

    def probe(self) -> ProbeResult:
        self._require(Lifecycle.CREATED, Lifecycle.PROBED)
        result = self.engine.probe(self.profile, self.services)
        self.probe_result = result
        if not result.supported:
            raise EngineCompatibilityError(
                f"{self.engine.descriptor.identifier} rejected profile: {result.reason}"
            )
        descriptor = self.engine.descriptor
        required = descriptor.required_capabilities | self.profile.required_capabilities
        missing = required & ~self.services.capabilities
        if missing:
            raise EngineCompatibilityError(
                "host is missing required capabilities: "
                + ", ".join(capability_names(missing))
            )
        optional = descriptor.optional_capabilities | self.profile.optional_capabilities
        self.negotiated_capabilities = required | (optional & self.services.capabilities)
        self.context = EngineContext(
            self.profile, self.services, self.negotiated_capabilities
        )
        self.lifecycle = Lifecycle.PROBED
        self.services.events.emit(
            service=Service.ENGINE,
            opcode=EngineOpcode.PROBE,
            arg0=result.confidence,
            source=Endpoint.HOST,
            destination=Endpoint.ENGINE,
        )
        return result

    def boot(self) -> None:
        if self.lifecycle is Lifecycle.CREATED:
            self.probe()
        self._require(Lifecycle.PROBED)
        assert self.context is not None
        try:
            self.engine.boot(self.context)
        except Exception as exc:
            self.lifecycle = Lifecycle.FAILED
            raise EngineExecutionError(f"engine boot failed: {exc}") from exc
        self.lifecycle = Lifecycle.RUNNING
        self.services.events.emit(
            service=Service.ENGINE,
            opcode=EngineOpcode.READY,
            source=Endpoint.ENGINE,
            destination=Endpoint.KERNEL,
        )
        self.services.flush_events()

    def tick(
        self,
        *,
        input_word: int = 0,
        pointer: tuple[int, int] | None = None,
        pointer_buttons: Iterable[tuple[int, bool]] = (),
        text: str = "",
    ) -> FrameResult:
        self._require(Lifecycle.RUNNING)
        assert self.context is not None
        frame = self.services.clock.frame + 1
        self.services.clock.advance(frame)
        self.services.input.sample_word(frame, input_word)
        if pointer is not None:
            self.services.input.move_pointer(frame, pointer[0], pointer[1])
            self.services.video.move_cursor(pointer[0], pointer[1])
        for button, pressed in pointer_buttons:
            self.services.input.set_pointer_button(frame, button, pressed)
        self.services.input.submit_text(frame, text)
        try:
            for event in self.services.input.drain():
                self.engine.handle_event(self.context, event)
            result = self.engine.tick(self.context)
        except Exception as exc:
            self.lifecycle = Lifecycle.FAILED
            raise EngineExecutionError(f"engine tick {frame} failed: {exc}") from exc
        if result.operations > self.profile.max_ops_per_tick:
            self.lifecycle = Lifecycle.FAILED
            raise EngineExecutionError(
                f"engine consumed {result.operations} operations; profile limit is "
                f"{self.profile.max_ops_per_tick}"
            )
        if result.presented:
            self.services.present()
        self.frame_results.append(result)
        self.services.flush_events()
        if result.halted:
            self.shutdown()
        return result

    def suspend(self) -> None:
        self._require(Lifecycle.RUNNING)
        assert self.context is not None
        self.engine.suspend(self.context)
        self.lifecycle = Lifecycle.SUSPENDED

    def resume(self) -> None:
        self._require(Lifecycle.SUSPENDED)
        assert self.context is not None
        self.engine.resume(self.context)
        self.lifecycle = Lifecycle.RUNNING

    def save(self, slot: int) -> SaveEnvelope:
        self._require(Lifecycle.RUNNING, Lifecycle.SUSPENDED)
        assert self.context is not None
        payload = self.engine.save_state(self.context)
        envelope = SaveEnvelope(
            engine_id=self.engine.descriptor.identifier,
            game_id=self.profile.game_id,
            schema=self.engine.descriptor.save_schema,
            payload=payload,
        )
        self.services.saves.write(slot, envelope.pack())
        self.services.events.emit(
            service=Service.SAVE,
            opcode=SaveOpcode.WRITE_SLOT,
            arg0=slot,
            arg1=len(payload),
            source=Endpoint.ENGINE,
            destination=Endpoint.HOST,
        )
        self.services.flush_events()
        return envelope

    def load(self, slot: int) -> SaveEnvelope:
        self._require(Lifecycle.RUNNING, Lifecycle.SUSPENDED)
        assert self.context is not None
        envelope = SaveEnvelope.unpack(self.services.saves.read(slot))
        descriptor = self.engine.descriptor
        if envelope.engine_id != descriptor.identifier:
            raise SaveFormatError(
                f"slot {slot} belongs to engine {envelope.engine_id}, not {descriptor.identifier}"
            )
        if envelope.game_id != self.profile.game_id:
            raise SaveFormatError(
                f"slot {slot} belongs to game {envelope.game_id}, not {self.profile.game_id}"
            )
        if envelope.schema != descriptor.save_schema:
            raise SaveFormatError(
                f"slot {slot} schema {envelope.schema} is incompatible with "
                f"schema {descriptor.save_schema}"
            )
        self.engine.load_state(self.context, envelope.payload)
        self.services.events.emit(
            service=Service.SAVE,
            opcode=SaveOpcode.READ_SLOT,
            arg0=slot,
            arg1=len(envelope.payload),
            source=Endpoint.HOST,
            destination=Endpoint.ENGINE,
        )
        self.services.flush_events()
        return envelope

    def shutdown(self) -> None:
        if self.lifecycle is Lifecycle.STOPPED:
            return
        self._require(Lifecycle.RUNNING, Lifecycle.SUSPENDED, Lifecycle.FAILED)
        if self.context is not None:
            self.engine.shutdown(self.context)
        self.lifecycle = Lifecycle.STOPPED
        self.services.events.emit(
            service=Service.ENGINE,
            opcode=EngineOpcode.STOPPED,
            source=Endpoint.ENGINE,
            destination=Endpoint.KERNEL,
        )
        self.services.flush_events()

    def report(self) -> dict[str, object]:
        return {
            "profile": self.profile.to_dict(),
            "engine": self.engine.descriptor.to_dict(),
            "lifecycle": self.lifecycle.value,
            "probe": None if self.probe_result is None else self.probe_result.to_dict(),
            "negotiated_capabilities": list(
                capability_names(self.negotiated_capabilities)
            ),
            "frames": len(self.frame_results),
            "frame_results": [result.to_dict() for result in self.frame_results],
            "state": dict(self.engine.inspect_state()),
            "video": {
                "presents": [record.to_dict() for record in self.services.video.presented],
                "current_sha256": self.services.video.surface.hash(),
            },
            "audio": {
                "music_track": self.services.audio.music_track,
                "speech_track": self.services.audio.speech_track,
                "commands": self.services.audio.command_history,
            },
            "debug": {
                "markers": self.services.debug.log,
                "counters": self.services.debug.counters,
            },
            "events": {
                "remaining": len(self.services.events.ring),
                "history_count": len(self.services.packet_history),
                "stats": {
                    "pushed": self.services.events.ring.stats.pushed,
                    "popped": self.services.events.ring.stats.popped,
                    "rejected": self.services.events.ring.stats.rejected,
                    "dropped": self.services.events.ring.stats.dropped,
                    "high_water": self.services.events.ring.stats.high_water,
                },
            },
        }
