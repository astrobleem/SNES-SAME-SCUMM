"""Canonical symbolic-music model shared by importers and playback backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


def _bounded(value: int, name: str, low: int, high: int) -> int:
    value = int(value)
    if not low <= value <= high:
        raise ValueError(f"{name} must be in {low}..{high}")
    return value


@dataclass(frozen=True, slots=True)
class Provenance:
    source: str
    track: int | None = None
    sample_description: int | None = None
    sample: int | None = None
    byte_offset: int | None = None
    word_offset: int | None = None
    source_tick: int | None = None
    source_time_scale: int | None = None

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("music provenance source cannot be empty")
        for name in (
            "track", "sample_description", "sample", "byte_offset",
            "word_offset", "source_tick",
        ):
            value = getattr(self, name)
            if value is not None and int(value) < 0:
                raise ValueError(f"music provenance {name} cannot be negative")
        if self.source_time_scale is not None:
            _bounded(
                self.source_time_scale, "provenance source time scale",
                1, (1 << 32) - 1,
            )


@dataclass(frozen=True, slots=True)
class InstrumentRequest:
    portable_id: str | None = None
    synth_type: str | None = None
    synth_name: str | None = None
    instrument_name: str | None = None
    instrument_number: int | None = None
    gm_fallback: int | None = None
    patch_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if self.instrument_number is not None:
            _bounded(self.instrument_number, "instrument number", -(1 << 31), (1 << 31) - 1)
        if self.gm_fallback is not None:
            _bounded(self.gm_fallback, "GM fallback", 0, 127)
        if self.patch_fingerprint is not None:
            if len(self.patch_fingerprint) != 64:
                raise ValueError("patch fingerprint must be a SHA-256 hex digest")
            try:
                bytes.fromhex(self.patch_fingerprint)
            except ValueError as exc:
                raise ValueError("patch fingerprint must be hexadecimal") from exc
        if not any((
            self.portable_id, self.synth_type, self.synth_name,
            self.instrument_name, self.instrument_number is not None,
            self.gm_fallback is not None, self.patch_fingerprint,
        )):
            raise ValueError("instrument request must contain an identity or fallback")


@dataclass(frozen=True, slots=True)
class PartSpec:
    part_id: int
    instrument: InstrumentRequest
    requested_polyphony: int = 1
    typical_polyphony_q16: int = 1 << 16
    percussion: bool = False
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        _bounded(self.part_id, "part id", 0, 65535)
        _bounded(self.requested_polyphony, "requested polyphony", 1, 65535)
        _bounded(self.typical_polyphony_q16, "typical polyphony", 0, (1 << 31) - 1)


@dataclass(frozen=True, slots=True)
class NoteOnEvent:
    part_id: int
    note_id: int
    pitch_q8_8: int
    velocity: int

    def __post_init__(self) -> None:
        _bounded(self.part_id, "note part id", 0, 65535)
        _bounded(self.note_id, "note id", 0, (1 << 63) - 1)
        _bounded(self.pitch_q8_8, "pitch", -(1 << 31), (1 << 31) - 1)
        _bounded(self.velocity, "velocity", 0, 127)


@dataclass(frozen=True, slots=True)
class NoteOffEvent:
    part_id: int
    note_id: int
    release_velocity: int = 64

    def __post_init__(self) -> None:
        _bounded(self.part_id, "note part id", 0, 65535)
        _bounded(self.note_id, "note id", 0, (1 << 63) - 1)
        _bounded(self.release_velocity, "release velocity", 0, 127)


@dataclass(frozen=True, slots=True)
class ControllerEvent:
    part_id: int
    controller: int
    value_q16: int

    def __post_init__(self) -> None:
        _bounded(self.part_id, "controller part id", 0, 65535)
        _bounded(self.controller, "controller", 0, 65535)
        _bounded(self.value_q16, "controller value", -(1 << 31), (1 << 31) - 1)


@dataclass(frozen=True, slots=True)
class MarkerEvent:
    marker: str
    value: int = 0

    def __post_init__(self) -> None:
        if not self.marker:
            raise ValueError("marker name cannot be empty")
        _bounded(self.value, "marker value", -(1 << 63), (1 << 63) - 1)


EventPayload: TypeAlias = NoteOnEvent | NoteOffEvent | ControllerEvent | MarkerEvent


@dataclass(frozen=True, slots=True)
class ScheduledEvent:
    tick: int
    source_order: int
    payload: EventPayload
    provenance: Provenance

    def __post_init__(self) -> None:
        _bounded(self.tick, "event tick", 0, (1 << 63) - 1)
        _bounded(self.source_order, "event source order", 0, (1 << 63) - 1)


@dataclass(frozen=True, slots=True)
class SequenceIR:
    source_time_scale: int
    parts: tuple[PartSpec, ...]
    events: tuple[ScheduledEvent, ...]
    end_tick: int
    provenance: Provenance
    loop: tuple[int, int] | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _bounded(self.source_time_scale, "source time scale", 1, (1 << 32) - 1)
        _bounded(self.end_tick, "sequence end tick", 0, (1 << 63) - 1)
        ids = [part.part_id for part in self.parts]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("sequence parts must have unique ascending ids")
        part_ids = set(ids)
        previous = (-1, -1)
        source_orders: set[int] = set()
        active: dict[int, int] = {}
        for event in self.events:
            key = (event.tick, event.source_order)
            if key < previous:
                raise ValueError("sequence events are not ordered by tick and source order")
            previous = key
            if event.tick > self.end_tick:
                raise ValueError("sequence event lies after end tick")
            if event.source_order in source_orders:
                raise ValueError("sequence source order values must be unique")
            source_orders.add(event.source_order)
            payload = event.payload
            if isinstance(payload, (NoteOnEvent, NoteOffEvent, ControllerEvent)):
                if payload.part_id not in part_ids:
                    raise ValueError(f"sequence event references unknown part {payload.part_id}")
            if isinstance(payload, NoteOnEvent):
                if payload.note_id in active:
                    raise ValueError(f"sequence repeats active note id {payload.note_id}")
                active[payload.note_id] = payload.part_id
            elif isinstance(payload, NoteOffEvent):
                if active.pop(payload.note_id, None) != payload.part_id:
                    raise ValueError(f"sequence note-off {payload.note_id} has no matching note-on")
        if active:
            raise ValueError(f"sequence has unterminated notes {sorted(active)}")
        if self.loop is not None:
            start, end = self.loop
            if not 0 <= start < end <= self.end_tick:
                raise ValueError("sequence loop lies outside its timeline")

    def peak_polyphony(self) -> int:
        active: set[int] = set()
        peak = 0
        for event in self.events:
            if isinstance(event.payload, NoteOnEvent):
                active.add(event.payload.note_id)
                peak = max(peak, len(active))
            elif isinstance(event.payload, NoteOffEvent):
                active.remove(event.payload.note_id)
        return peak
