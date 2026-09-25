"""Absolute-rational normalization between symbolic-music time scales."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .model import NoteOffEvent, NoteOnEvent, ScheduledEvent, SequenceIR


class TimeScalePolicy(str, Enum):
    EXACT = "exact"
    NEAREST_ABSOLUTE = "nearest_absolute"


class TimeScaleError(ValueError):
    def __init__(self, code: str, source_tick: int, detail: str) -> None:
        self.code = code
        self.source_tick = source_tick
        super().__init__(f"music time normalization {code} at source tick {source_tick}: {detail}")


@dataclass(frozen=True, slots=True)
class TimeScaleNormalization:
    sequence: SequenceIR
    source_time_scale: int
    target_time_scale: int
    policy: TimeScalePolicy
    max_error_numerator: int
    error_denominator: int
    duration_error_numerator: int


def normalize_sequence_time_scale(
    sequence: SequenceIR,
    target_time_scale: int,
    *,
    policy: TimeScalePolicy | str = TimeScalePolicy.EXACT,
) -> TimeScaleNormalization:
    """Map absolute source ticks; never accumulate rounded delta durations."""
    target = int(target_time_scale)
    if not 1 <= target <= (1 << 32) - 1:
        raise ValueError("target music time scale must fit positive u32")
    try:
        selected = TimeScalePolicy(policy)
    except ValueError as exc:
        raise ValueError(f"unknown music time normalization policy {policy!r}") from exc
    source = sequence.source_time_scale

    def mapped(tick: int) -> tuple[int, int]:
        numerator = int(tick) * target
        quotient, remainder = divmod(numerator, source)
        if selected is TimeScalePolicy.EXACT:
            if remainder:
                raise TimeScaleError(
                    "inexact_tick", tick,
                    f"{numerator}/{source} is not an integer target tick",
                )
            value = quotient
        else:
            value = quotient + int(remainder * 2 >= source)
        error = abs(value * source - numerator)
        return value, error

    if source == target:
        return TimeScaleNormalization(
            sequence, source, target, selected, 0, source, 0,
        )

    mapped_events: list[ScheduledEvent] = []
    errors: list[int] = []
    note_starts: dict[int, tuple[int, int]] = {}
    for order, event in enumerate(sequence.events):
        target_tick, error = mapped(event.tick)
        errors.append(error)
        provenance = replace(
            event.provenance, source_tick=event.tick,
            source_time_scale=source,
        )
        mapped_events.append(ScheduledEvent(
            target_tick, order, event.payload, provenance,
        ))
        payload = event.payload
        if isinstance(payload, NoteOnEvent):
            note_starts[payload.note_id] = (event.tick, target_tick)
        elif isinstance(payload, NoteOffEvent):
            source_start, target_start = note_starts.pop(payload.note_id)
            if target_tick <= target_start:
                raise TimeScaleError(
                    "collapsed_note", event.tick,
                    f"note {payload.note_id} at {source_start}..{event.tick} "
                    f"maps to {target_start}..{target_tick}",
                )

    end_tick, duration_error = mapped(sequence.end_tick)
    loop = None
    if sequence.loop is not None:
        loop_start, loop_start_error = mapped(sequence.loop[0])
        loop_end, loop_end_error = mapped(sequence.loop[1])
        errors.extend((loop_start_error, loop_end_error))
        if loop_end <= loop_start:
            raise TimeScaleError(
                "collapsed_loop", sequence.loop[1],
                f"loop {sequence.loop} maps to {loop_start}..{loop_end}",
            )
        loop = (loop_start, loop_end)
    errors.append(duration_error)
    maximum = max(errors, default=0)
    normalized = SequenceIR(
        target, sequence.parts, tuple(mapped_events), end_tick,
        replace(sequence.provenance, source_time_scale=source), loop,
        sequence.diagnostics + (
            f"time_scale:{source}->{target}:{selected.value}:"
            f"max_error={maximum}/{source}",
        ),
    )
    return TimeScaleNormalization(
        normalized, source, target, selected, maximum, source,
        duration_error,
    )
