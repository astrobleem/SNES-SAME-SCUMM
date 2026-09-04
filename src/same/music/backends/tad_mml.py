"""Compile resolved sampled notes to bounded Terrific Audio Driver MML."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Iterable

from ..model import ControllerEvent, SequenceIR


_CHANNELS = "ABCDEFGH"
_NOTE_NAMES = ("c", "c+", "d", "d+", "e", "f", "f+", "g", "g+", "a", "a+", "b")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class TadCompileError(ValueError):
    def __init__(self, source: str, tick: int | None, detail: str) -> None:
        self.source = source
        self.tick = tick
        location = "song" if tick is None else f"tick {tick}"
        super().__init__(f"TAD compile {source!r} {location}: {detail}")


class TadPanPolicy(str, Enum):
    STEREO_CC10 = "stereo_cc10"
    MONO_CENTER = "mono_center"


@dataclass(frozen=True, slots=True)
class SampledNote:
    start: int
    end: int
    midi_note: int
    volume: int
    zone_name: str
    part_id: int
    note_id: int
    volume_changes: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.start < self.end:
            raise ValueError("sampled note lifetime is invalid")
        if not 0 <= self.midi_note <= 127 or not 0 <= self.volume <= 255:
            raise ValueError("sampled note pitch or volume is invalid")
        if not self.zone_name or self.part_id < 0 or self.note_id < 0:
            raise ValueError("sampled note identity is invalid")
        previous = self.start
        for tick, volume in self.volume_changes:
            if not self.start < tick < self.end or tick <= previous:
                raise ValueError("sampled note volume automation is not ordered inside its lifetime")
            if not 0 <= volume <= 255:
                raise ValueError("sampled note automated volume is invalid")
            previous = tick


@dataclass(frozen=True, slots=True)
class TadInstrument:
    zone_name: str
    mml_name: str

    def __post_init__(self) -> None:
        if not self.zone_name or not _NAME.fullmatch(self.mml_name):
            raise ValueError("TAD instrument identity is invalid")


@dataclass(frozen=True, slots=True)
class TadMmlSong:
    mml: str
    voice_count: int
    instrument_names: tuple[str, ...]
    loop: tuple[int, int] | None
    pan_policy: TadPanPolicy
    tick_bias: int = 0
    release_adjustments: tuple[int, ...] = ()


def _fail(sequence: SequenceIR, tick: int | None, detail: str) -> TadCompileError:
    return TadCompileError(sequence.provenance.source, tick, detail)


def _pan_value(value_q16: int) -> int:
    midi = max(0, min(127, int(value_q16) >> 16))
    return (midi * 128 + 63) // 127


def _part_pan_events(
    sequence: SequenceIR, policy: TadPanPolicy,
) -> dict[int, tuple[tuple[int, int], ...]]:
    output: dict[int, list[tuple[int, int]]] = {part.part_id: [] for part in sequence.parts}
    for event in sequence.events:
        payload = event.payload
        if not isinstance(payload, ControllerEvent):
            continue
        if payload.controller == 7:
            continue  # Resolved note volumes already contain CC7 response.
        if payload.controller != 10:
            raise _fail(
                sequence, event.tick,
                f"controller {payload.controller} has no sampled TAD policy "
                f"(source sample {event.provenance.sample})",
            )
        pan = 64 if policy is TadPanPolicy.MONO_CENTER else _pan_value(payload.value_q16)
        entries = output[payload.part_id]
        if entries and entries[-1][0] == event.tick:
            entries[-1] = (event.tick, pan)
        elif not entries or entries[-1][1] != pan:
            entries.append((event.tick, pan))
    return {part: tuple(events) for part, events in output.items()}


def _allocate(
    sequence: SequenceIR, notes: tuple[SampledNote, ...], voice_limit: int,
) -> tuple[tuple[SampledNote, ...], ...]:
    voices: list[list[SampledNote]] = []
    for note in notes:
        lane = next((voice for voice in voices if voice[-1].end <= note.start), None)
        if lane is None:
            if len(voices) >= voice_limit:
                active = sorted(
                    item.note_id for voice in voices for item in voice
                    if item.start <= note.start < item.end
                )
                raise _fail(
                    sequence, note.start,
                    f"voice limit {voice_limit} exhausted by active notes {active}; "
                    f"requested {note.note_id}",
                )
            lane = []
            voices.append(lane)
        lane.append(note)
    return tuple(tuple(voice) for voice in voices)


def _shift_note(note: SampledNote, bias: int) -> SampledNote:
    if not bias:
        return note
    return replace(
        note,
        start=note.start + bias,
        end=note.end + bias,
        volume_changes=tuple((tick + bias, volume) for tick, volume in note.volume_changes),
    )


def _expand_one_tick_rests(
    sequence: SequenceIR,
    voices: tuple[tuple[SampledNote, ...], ...],
    target_end: int,
) -> tuple[tuple[tuple[SampledNote, ...], ...], tuple[int, ...]]:
    output: list[tuple[SampledNote, ...]] = []
    adjusted: list[int] = []
    for voice in voices:
        lane = list(voice)
        for index in range(len(lane) - 1):
            if lane[index + 1].start - lane[index].end != 1:
                continue
            previous = lane[index]
            if previous.end - previous.start <= 2:
                raise _fail(
                    sequence, previous.end,
                    f"one-tick rest after minimum-length note {previous.note_id} is unrepresentable",
                )
            shortened_end = previous.end - 1
            if any(tick >= shortened_end for tick, _ in previous.volume_changes):
                raise _fail(
                    sequence, shortened_end,
                    f"release adjustment would erase note {previous.note_id} automation",
                )
            lane[index] = replace(previous, end=shortened_end)
            adjusted.append(previous.note_id)
        if target_end - lane[-1].end == 1:
            previous = lane[-1]
            if previous.end - previous.start <= 2:
                raise _fail(
                    sequence, previous.end,
                    f"one-tick tail after minimum-length note {previous.note_id} is unrepresentable",
                )
            shortened_end = previous.end - 1
            if any(tick >= shortened_end for tick, _ in previous.volume_changes):
                raise _fail(
                    sequence, shortened_end,
                    f"tail adjustment would erase note {previous.note_id} automation",
                )
            lane[-1] = replace(previous, end=shortened_end)
            adjusted.append(previous.note_id)
        output.append(tuple(lane))
    return tuple(output), tuple(adjusted)


def _note_name(midi_note: int) -> tuple[int, str]:
    return midi_note // 12 - 1, _NOTE_NAMES[midi_note % 12]


def _pan_at(events: tuple[tuple[int, int], ...], tick: int) -> int:
    pan = 64
    for changed_tick, changed_pan in events:
        if changed_tick > tick:
            break
        pan = changed_pan
    return pan


def compile_tad_mml(
    sequence: SequenceIR,
    notes: Iterable[SampledNote],
    instruments: Iterable[TadInstrument],
    *,
    title: str = "SAME compiled sampled song",
    author: str = "SAME generic sampled backend",
    pan_policy: TadPanPolicy = TadPanPolicy.STEREO_CC10,
    voice_limit: int = 8,
) -> TadMmlSong:
    """Compile an already-resolved song; no importer or device policy enters here."""
    if "\n" in title or "\n" in author or not title or not author:
        raise _fail(sequence, None, "title and author must be nonempty single lines")
    if sequence.source_time_scale != 125:
        raise _fail(
            sequence, None,
            f"time scale {sequence.source_time_scale} cannot map exactly to TAD timer 64",
        )
    if not 1 <= voice_limit <= len(_CHANNELS):
        raise ValueError("TAD voice limit must be in 1..8")
    if sequence.loop is not None and sequence.loop[1] != sequence.end_tick:
        raise _fail(sequence, sequence.loop[1], "TAD backend requires a whole-song suffix loop")

    instrument_list = tuple(instruments)
    by_zone = {instrument.zone_name: index for index, instrument in enumerate(instrument_list)}
    if not instrument_list or len(by_zone) != len(instrument_list):
        raise _fail(sequence, None, "TAD instruments must have unique nonempty zones")
    names = [instrument.mml_name for instrument in instrument_list]
    if len(names) != len(set(names)):
        raise _fail(sequence, None, "TAD instruments repeat an MML name")

    source_notes = tuple(sorted(
        notes, key=lambda note: (note.start, note.midi_note, note.end, note.note_id),
    ))
    if not source_notes:
        raise _fail(sequence, None, "sampled song has no notes")
    note_ids: set[int] = set()
    part_ids = {part.part_id for part in sequence.parts}
    loop_start = sequence.loop[0] if sequence.loop is not None else None
    for note in source_notes:
        if note.note_id in note_ids:
            raise _fail(sequence, note.start, f"sampled note id {note.note_id} is repeated")
        note_ids.add(note.note_id)
        if note.part_id not in part_ids:
            raise _fail(sequence, note.start, f"sampled note references unknown part {note.part_id}")
        if note.end > sequence.end_tick:
            raise _fail(sequence, note.end, "sampled note exceeds sequence end")
        if note.zone_name not in by_zone:
            raise _fail(sequence, note.start, f"zone {note.zone_name!r} has no TAD instrument")
        if loop_start is not None and note.start < loop_start < note.end:
            raise _fail(sequence, loop_start, f"note {note.note_id} crosses the loop boundary")
        if note.end - note.start < 2:
            raise _fail(sequence, note.start, f"note {note.note_id} is shorter than two TAD ticks")

    pan_events = _part_pan_events(sequence, pan_policy)
    first_boundary = min(
        [note.start for note in source_notes if note.start > 0]
        + ([loop_start] if loop_start is not None and loop_start > 0 else [])
        or [2]
    )
    tick_bias = 1 if first_boundary == 1 else 0
    ordered = tuple(_shift_note(note, tick_bias) for note in source_notes)
    if tick_bias:
        pan_events = {
            part: tuple((tick + tick_bias if tick else 0, pan) for tick, pan in events)
            for part, events in pan_events.items()
        }
    target_end = sequence.end_tick + tick_bias
    target_loop = (
        None if sequence.loop is None
        else (sequence.loop[0] + tick_bias, sequence.loop[1] + tick_bias)
    )
    loop_start = target_loop[0] if target_loop is not None else None
    voices = _allocate(sequence, ordered, voice_limit)
    voices, release_adjustments = _expand_one_tick_rests(
        sequence, voices, target_end,
    )
    lines = [
        f"#Title {title}", f"#Author {author}", "#Timer 64", "#ZenLen 192", "",
        f"; SAME sampled backend; pan_policy={pan_policy.value}; "
        f"source={sequence.provenance.source}",
        f"; tick_bias={tick_bias}; one_tick_release_adjustments="
        f"{','.join(map(str, release_adjustments)) or 'none'}",
    ]
    lines.extend(
        f"@{index} {instrument.mml_name}"
        for index, instrument in enumerate(instrument_list)
    )
    lines.append("")

    for voice_index, voice in enumerate(voices):
        tokens = ["q0"]
        cursor = 0
        current_instrument = current_volume = current_octave = current_pan = None
        emitted_loop = False
        for note in voice:
            if loop_start is not None and not emitted_loop and loop_start <= note.start:
                if cursor < loop_start:
                    tokens.append(f"r%{loop_start - cursor}")
                    cursor = loop_start
                tokens.append("L")
                emitted_loop = True
            if note.start > cursor:
                tokens.append(f"r%{note.start - cursor}")
            instrument = by_zone[note.zone_name]
            if instrument != current_instrument:
                tokens.append(f"@{instrument}")
                current_instrument = instrument
            if note.volume != current_volume:
                tokens.append(f"V{note.volume}")
                current_volume = note.volume
            part_pan = pan_events[note.part_id]
            initial_pan = _pan_at(part_pan, note.start)
            if initial_pan != current_pan:
                tokens.append(f"p{initial_pan}")
                current_pan = initial_pan
            octave, pitch = _note_name(note.midi_note)
            if octave != current_octave:
                tokens.append(f"o{octave}")
                current_octave = octave
            changes: dict[int, dict[str, int]] = {}
            for tick, volume in note.volume_changes:
                changes.setdefault(tick, {})["volume"] = volume
            for tick, pan in part_pan:
                if note.start < tick < note.end:
                    changes.setdefault(tick, {})["pan"] = pan
            if changes:
                boundaries = sorted(changes)
                tokens.extend((f"{pitch}%{boundaries[0] - note.start}", "&"))
                for index, tick in enumerate(boundaries):
                    change = changes[tick]
                    if "volume" in change and change["volume"] != current_volume:
                        current_volume = change["volume"]
                        tokens.append(f"V{current_volume}")
                    if "pan" in change and change["pan"] != current_pan:
                        current_pan = change["pan"]
                        tokens.append(f"p{current_pan}")
                    end = boundaries[index + 1] if index + 1 < len(boundaries) else note.end
                    tokens.append(f"w%{end - tick}")
            else:
                tokens.append(f"{pitch}%{note.end - note.start}")
            cursor = note.end
        if loop_start is not None and not emitted_loop:
            if cursor < loop_start:
                tokens.append(f"r%{loop_start - cursor}")
                cursor = loop_start
            tokens.append("L")
        if cursor < target_end:
            tokens.append(f"r%{target_end - cursor}")
        lines.append(f"{_CHANNELS[voice_index]} " + " ".join(tokens))
    lines.append("")
    return TadMmlSong(
        "\n".join(lines), len(voices), tuple(names), target_loop, pan_policy,
        tick_bias, release_adjustments,
    )
