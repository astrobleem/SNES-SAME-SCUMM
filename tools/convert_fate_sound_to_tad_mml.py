#!/usr/bin/env python3
"""Convert a bounded Fate ROL track into zoned Terrific Audio Driver MML."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
import zipfile

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.embedded_audio import ScummV5EmbeddedSound
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
CATALOG = ROOT / "examples/resources/music/fate_s6_compiled.json"
MEMBERS = {
    "index": "FATEDEMO/PLAYFATE.000",
    "data": "FATEDEMO/PLAYFATE.001",
    "notice": "FATEDEMO/READ.ME",
}
TICKS_PER_SECOND = 125
CHANNEL_NAMES = "ABCDEFGH"
NOTE_NAMES = ("c", "c+", "d", "d+", "e", "f", "f+", "g", "g+", "a", "a+", "b")

# This intentionally fails closed. Extend the tables only when a program has a
# reviewed SNES role; never silently substitute every MT-32 patch with one pad.
DEFAULT_PROGRAM_ROLES = {
    50: "pad",
    57: "flute",
}
# Some cues use an MT-32 program outside the register where its nominal role is
# viable on S-DSP. These cue-specific bands document the arrangement decision
# instead of hiding it in a global program alias. Bounds are inclusive.
FATE_ATMOSPHERIC_BANDS = {
        32: ((24, 59, "bass"), (60, 95, "pad")),
        36: ((24, 59, "bass"), (60, 95, "pad")),
        50: ((36, 95, "pad"),),
        92: ((36, 95, "pad"),),
        97: ((48, 95, "flute"),),
}
FATE_PROGRAM_ZERO_IMPACT_BANDS = {
    0: ((24, 35, "bass"), (36, 83, "marimba")),
}
FATE_PROGRAM_ZERO_MARIMBA_BANDS = {
    0: ((36, 83, "marimba"),),
}
SOUND_PROGRAM_BANDS = {
    82: {
        # M24R-B's source-bound composite.  Program 112 is a short struck
        # texture in this cue, so the reviewed marimba sample is a closer
        # envelope/role match than silently treating it as a sustained pad.
        32: ((36, 59, "bass"), (60, 95, "pad")),
        35: ((36, 95, "pad"),),
        50: ((24, 35, "bass"), (36, 95, "pad")),
        82: ((24, 35, "bass"), (36, 95, "pad")),
        112: ((36, 83, "marimba"),),
    },
    80: {
        # M21's bounded sound-80 realization.  Programs 32/33/77/82 are
        # deliberately cue-local pending the isolated listener gate.
        32: ((36, 95, "pad"),),
        33: ((36, 95, "pad"),),
        50: ((24, 35, "bass"), (36, 95, "pad")),
        57: ((24, 47, "bass"), (48, 95, "flute")),
        73: ((48, 95, "flute"),),
        77: ((24, 59, "bass"), (60, 95, "flute")),
        # M24R-B reaches the hook-7/marker-8 lead-in below M21's original
        # range.  The low notes are fundamental support, not the upper pad
        # role, and therefore use the reviewed bass zone explicitly.
        82: ((24, 35, "bass"), (36, 95, "pad")),
        92: ((36, 95, "pad"),),
        # M22's default continuation reaches these two source patches.  They
        # are cue-local choices and remain human-timbre-pending until the
        # generated isolated auditions are accepted.
        97: ((48, 95, "flute"),),
        107: ((36, 95, "pad"),),
        112: ((36, 83, "marimba"),),
    },
    18: {
        50: ((36, 95, "pad"),),
        57: ((48, 95, "flute"),),
        92: ((36, 95, "pad"),),
    },
    78: {
        73: ((72, 95, "flute"),),
        82: ((36, 71, "pad"),),
        91: ((36, 71, "pad"),),
    },
    81: {
        0: ((36, 83, "marimba"),),
        32: ((24, 59, "bass"), (60, 95, "pad")),
        82: ((36, 95, "pad"),),
        90: ((36, 95, "pad"),),
        92: ((36, 95, "pad"),),
    },
    83: FATE_ATMOSPHERIC_BANDS,
    91: {
        32: ((24, 47, "bass"), (48, 107, "effect-tone")),
    },
    117: {
        121: ((24, 47, "bass"), (48, 107, "effect-tone")),
    },
    150: {
        0: ((36, 83, "marimba"),),
        33: ((24, 59, "bass"), (60, 95, "pad")),
        36: ((24, 59, "bass"), (60, 95, "pad")),
        56: ((24, 59, "bass"),),
        92: ((36, 95, "pad"),),
    },
    153: {
        0: ((36, 83, "marimba"),),
        32: ((24, 59, "bass"), (60, 95, "pad")),
        36: ((24, 59, "bass"), (60, 95, "pad")),
        50: ((24, 35, "bass"), (36, 95, "pad")),
        92: ((36, 95, "pad"),),
        97: ((48, 95, "flute"), (96, 107, "effect-tone")),
    },
    141: FATE_PROGRAM_ZERO_MARIMBA_BANDS,
    154: FATE_ATMOSPHERIC_BANDS,
    183: FATE_PROGRAM_ZERO_MARIMBA_BANDS,
    185: FATE_PROGRAM_ZERO_MARIMBA_BANDS,
    190: FATE_PROGRAM_ZERO_IMPACT_BANDS,
    192: FATE_PROGRAM_ZERO_IMPACT_BANDS,
    201: FATE_PROGRAM_ZERO_MARIMBA_BANDS,
    202: FATE_PROGRAM_ZERO_MARIMBA_BANDS,
    207: FATE_PROGRAM_ZERO_MARIMBA_BANDS,
}
# Polyphony reduction is opt-in per cue. This policy preserves stronger notes;
# exact ties preserve the lower register and therefore discard the highest
# whisper layer first. Every omission is emitted into the generated MML audit.
SOUND_VOICE_REDUCTION = {
    83: "quietest-then-highest",
}
SOUND_VOICE_VIRTUALIZATION = {
    82: "fate82-role-priority",
    80: "merge-sustained-identical-then-protect-outer-strongest",
    18: "merge-identical-then-duck-program-50",
    81: "merge-identical-at-capacity",
    150: "merge-sustained-identical-then-protect-outer-strongest",
    153: "merge-sustained-identical-then-protect-outer-strongest",
    183: "merge-identical-then-protect-outer-strongest",
}
SOUND_TICK_QUANTUM = {
    82: 2,   # Composite key-off events must meet TAD's two-tick minimum.
    80: 2,   # TAD key-off notes require at least two ticks.
    91: 2,   # Preserve the rapid run at TAD's minimum key-off duration.
    117: 2,  # The same run plus sustained harmony uses the same grid.
    150: 2,  # Dense sustain handoffs require TAD's minimum key-off duration.
    153: 2,  # Whisper attacks still require TAD's minimum key-off duration.
    183: 2,  # TAD key-off notes require at least two ticks.
}
# Sound 150 ends with six notes held to the track-cleanup boundary even though
# its only active CC7 envelope fades by 18.679 seconds and no new musical event
# follows 21.903 seconds. Static SNES loop sources turn that interactive hold
# into an objectionable 84-second drone, so retain the logical note lifetimes
# while sliding terminal loop voices to silence at the source fade boundary.
SOUND_TERMINAL_FADE = {
    150: {
        "sentinel_tick": round(90 * TICKS_PER_SECOND),
        "fade_end_tick": round(18.679 * TICKS_PER_SECOND),
    },
}
INSTRUMENTS = (
    ("mt32_p88_cycle", "pad-low"),
    ("mt32_p88_cycle_x2", "pad-high"),
    ("mt32_p74_cycle", "flute-low"),
    ("mt32_p74_cycle_x2", "flute-mid"),
    ("mt32_p74_cycle_x4", "flute-high"),
    ("ph_bass", "bass"),
    ("mt32_marimba", "marimba"),
    ("fate_tone", "effect-tone"),
)


@dataclass(frozen=True)
class SourceNote:
    start_us: int
    end_us: int
    midi_note: int
    velocity: int
    channel_volume: int
    program: int
    volume_changes: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class TadNote:
    start: int
    end: int
    midi_note: int
    volume: int
    instrument: int
    program: int
    velocity_product: int
    source_index: int
    volume_changes: tuple[tuple[int, int], ...] = ()
    attack: bool = True


@dataclass(frozen=True)
class VoiceDecision:
    action: str
    start: int
    end: int
    program: int
    midi_note: int
    peer_program: int | None = None
    source_index: int | None = None


def _zone(role: str, note: int) -> int:
    if role == "pad":
        if not 36 <= note <= 95:
            raise ValueError(f"pad note {note} is outside reviewed C2..B6 range")
        return 0 if note < 72 else 1
    if role == "flute":
        if not 48 <= note <= 95:
            raise ValueError(f"flute note {note} is outside reviewed C3..B6 range")
        return 2 if note < 64 else 3 if note < 84 else 4
    if role == "bass":
        if not 24 <= note <= 59:
            raise ValueError(f"bass note {note} is outside reviewed C1..B3 range")
        return 5
    if role == "marimba":
        if not 36 <= note <= 83:
            raise ValueError(f"marimba note {note} is outside reviewed C2..B5 range")
        return 6
    if role == "effect-tone":
        if not 48 <= note <= 107:
            raise ValueError(f"effect-tone note {note} is outside reviewed C3..B7 range")
        return 7
    raise ValueError(f"unknown reviewed role {role!r}")


def _role(sound_id: int, program: int, note: int) -> str:
    sound_bands = SOUND_PROGRAM_BANDS.get(sound_id)
    if sound_bands is not None:
        try:
            bands = sound_bands[program]
        except KeyError as exc:
            raise ValueError(
                f"MT-32 program {program} has no reviewed SNES role for sound {sound_id}"
            ) from exc
        for first, last, role in bands:
            if first <= note <= last:
                return role
        raise ValueError(
            f"MT-32 program {program} note {note} has no reviewed SNES band for sound {sound_id}"
        )
    try:
        return DEFAULT_PROGRAM_ROLES[program]
    except KeyError as exc:
        raise ValueError(f"MT-32 program {program} has no reviewed SNES role") from exc


def collect_notes(sound: ScummV5EmbeddedSound) -> list[SourceNote]:
    if sound.track_count != 1:
        raise ValueError("multi-track iMUSE sounds require an explicit branch arrangement")
    programs = [0] * 16
    volumes = [127] * 16
    active: dict[
        tuple[int, int],
        list[tuple[int, int, int, int, list[tuple[int, int]]]],
    ] = {}
    notes: list[SourceNote] = []
    for event in sound.tracks[0].events:
        command = event.status & 0xF0
        channel = event.status & 0x0F
        if command == 0xC0:
            programs[channel] = event.data[0]
        elif command == 0xB0 and event.data[0] == 7:
            for (active_channel, _note), stack in active.items():
                if active_channel == channel:
                    for entry in stack:
                        entry[4].append((event.time_us, event.data[1]))
            volumes[channel] = event.data[1]
        elif command == 0x90 and event.data[1] != 0:
            active.setdefault((channel, event.data[0]), []).append(
                (event.time_us, event.data[1], volumes[channel], programs[channel], [])
            )
        elif command in (0x80, 0x90):
            stack = active.get((channel, event.data[0]))
            if not stack:
                raise ValueError(f"note-off without note-on at tick {event.tick}")
            start_us, velocity, channel_volume, program, volume_changes = stack.pop(0)
            notes.append(SourceNote(
                start_us, event.time_us, event.data[0], velocity, channel_volume, program,
                tuple(volume_changes),
            ))
    if any(stack for stack in active.values()):
        raise ValueError("unterminated notes require an explicit arrangement decision")
    return sorted(notes, key=lambda note: (note.start_us, note.midi_note, note.end_us))


def quantize_notes(sound_id: int, notes: list[SourceNote]) -> list[TadNote]:
    output = []
    quantum = SOUND_TICK_QUANTUM.get(sound_id, 1)
    for source_index, note in enumerate(notes):
        role = _role(sound_id, note.program, note.midi_note)
        start = round(note.start_us * TICKS_PER_SECOND / 1_000_000 / quantum) * quantum
        end = max(
            start + quantum,
            round(note.end_us * TICKS_PER_SECOND / 1_000_000 / quantum) * quantum,
        )
        # Preserve the original 0..127 velocity/CC7 product on TAD's 0..255
        # fine-volume scale.  The former 17-step coarse conversion erased the
        # lower half of long fades and was the root of audible hanging tails.
        volume = max(
            1, min(255, round(note.velocity * note.channel_volume * 192 / (127 * 127))),
        )
        changes_by_tick: dict[int, int] = {}
        for time_us, channel_volume in note.volume_changes:
            tick = round(time_us * TICKS_PER_SECOND / 1_000_000 / quantum) * quantum
            tick = max(start, min(end, tick))
            changed_volume = max(
                0,
                min(255, round(note.velocity * channel_volume * 192 / (127 * 127))),
            )
            if tick == start:
                volume = changed_volume
            elif tick < end:
                changes_by_tick[tick] = changed_volume
        volume_changes = []
        current_volume = volume
        for tick, changed_volume in sorted(changes_by_tick.items()):
            if changed_volume != current_volume:
                volume_changes.append((tick, changed_volume))
                current_volume = changed_volume
        output.append(TadNote(
            start, end, note.midi_note, volume, _zone(role, note.midi_note),
            note.program, note.velocity * note.channel_volume, source_index,
            tuple(volume_changes),
        ))
    return output


def reduce_polyphony(sound_id: int, notes: list[TadNote]) -> tuple[list[TadNote], list[TadNote]]:
    policy = SOUND_VOICE_REDUCTION.get(sound_id)
    if policy is None:
        return notes, []
    if policy != "quietest-then-highest":
        raise ValueError(f"unknown voice-reduction policy {policy!r}")

    kept: list[TadNote] = []
    omitted: list[TadNote] = []
    for note in notes:
        active = [candidate for candidate in kept if candidate.end > note.start]
        if len(active) < len(CHANNEL_NAMES):
            kept.append(note)
            continue
        candidates = active + [note]
        loser = min(
            candidates,
            key=lambda candidate: (
                candidate.velocity_product,
                -candidate.midi_note,
                candidate.end - candidate.start,
                -candidate.start,
            ),
        )
        omitted.append(loser)
        if loser is not note:
            kept.remove(loser)
            kept.append(note)
    return sorted(kept, key=lambda note: (note.start, note.midi_note, note.end)), omitted


def _coalesce_decisions(decisions: list[VoiceDecision]) -> list[VoiceDecision]:
    output: list[VoiceDecision] = []
    for decision in sorted(
        decisions,
        key=lambda item: (
            item.action, item.program, item.midi_note,
            -1 if item.peer_program is None else item.peer_program,
            -1 if item.source_index is None else item.source_index, item.start,
        ),
    ):
        if output and (
            output[-1].action == decision.action
            and output[-1].program == decision.program
            and output[-1].midi_note == decision.midi_note
            and output[-1].peer_program == decision.peer_program
            and output[-1].source_index == decision.source_index
            and output[-1].end == decision.start
        ):
            output[-1] = replace(output[-1], end=decision.end)
        else:
            output.append(decision)
    return sorted(output, key=lambda item: (item.start, item.action, item.midi_note))


def _coalesce_segments(segments: list[TadNote]) -> list[TadNote]:
    output: list[TadNote] = []
    for segment in sorted(segments, key=lambda note: (note.source_index, note.start)):
        if output and (
            output[-1].source_index == segment.source_index
            and output[-1].end == segment.start
            and output[-1].midi_note == segment.midi_note
            and output[-1].instrument == segment.instrument
            and output[-1].program == segment.program
            and output[-1].velocity_product == segment.velocity_product
            and not segment.attack
        ):
            previous = output[-1]
            changes = list(previous.volume_changes)
            previous_end_volume = previous.volume
            for _tick, changed_volume in previous.volume_changes:
                previous_end_volume = changed_volume
            if segment.volume != previous_end_volume:
                changes.append((segment.start, segment.volume))
            changes.extend(segment.volume_changes)
            output[-1] = replace(previous, end=segment.end, volume_changes=tuple(changes))
        else:
            output.append(segment)
    return sorted(output, key=lambda note: (note.start, note.midi_note, note.end))


def _volume_at(note: TadNote, tick: int) -> int:
    volume = note.volume
    for change_tick, changed_volume in note.volume_changes:
        if change_tick > tick:
            break
        volume = changed_volume
    return volume


def _slice_note(note: TadNote, start: int, end: int) -> TadNote:
    return replace(
        note,
        start=start,
        end=end,
        volume=_volume_at(note, start),
        volume_changes=tuple(
            (tick, volume)
            for tick, volume in note.volume_changes
            if start < tick < end
        ),
        attack=note.attack and start == note.start,
    )


def virtualize_polyphony(
    sound_id: int, notes: list[TadNote],
) -> tuple[list[TadNote], list[VoiceDecision]]:
    policy = SOUND_VOICE_VIRTUALIZATION.get(sound_id)
    if policy is None:
        return notes, []
    if policy not in {
        "merge-identical-at-capacity",
        "merge-sustained-identical-then-protect-outer-strongest",
        "merge-identical-then-duck-program-50",
        "merge-identical-then-protect-outer-strongest",
        "fate82-role-priority",
    }:
        raise ValueError(f"unknown voice-virtualization policy {policy!r}")

    boundaries = sorted({value for note in notes for value in (note.start, note.end)})
    segments: list[TadNote] = []
    decisions: list[VoiceDecision] = []
    for start, end in zip(boundaries, boundaries[1:]):
        active = [note for note in notes if note.start <= start and note.end >= end]
        if not active:
            continue

        unique: list[TadNote] = []
        if policy in {
            "merge-identical-at-capacity",
            "merge-sustained-identical-then-protect-outer-strongest",
        }:
            if len(active) <= len(CHANNEL_NAMES):
                unique.extend(active)
            else:
                groups: dict[tuple[int, int], list[TadNote]] = {}
                for note in active:
                    groups.setdefault((note.instrument, note.midi_note), []).append(note)
                merge_candidates: list[tuple[TadNote, TadNote]] = []
                for group in groups.values():
                    winner = max(
                        group,
                        key=lambda note: (
                            note.start == start, note.velocity_product, -note.source_index,
                        ),
                    )
                    merge_candidates.extend(
                        (loser, winner)
                        for loser in group
                        if loser is not winner and (
                            policy == "merge-identical-at-capacity" or loser.start != start
                        )
                    )
                required = len(active) - len(CHANNEL_NAMES)
                selected = sorted(
                    merge_candidates,
                    key=lambda pair: (
                        pair[0].velocity_product, -pair[0].midi_note,
                        pair[0].source_index,
                    ),
                )[:required]
                merged = {loser for loser, _winner in selected}
                unique.extend(note for note in active if note not in merged)
                decisions.extend(
                    VoiceDecision(
                        "MERGE", start, end, loser.program, loser.midi_note, winner.program,
                    )
                    for loser, winner in selected
                )
        else:
            groups: dict[tuple[int, int], list[TadNote]] = {}
            for note in active:
                groups.setdefault((note.instrument, note.midi_note), []).append(note)
            for group in groups.values():
                winner = max(
                    group,
                    key=lambda note: (
                        note.program != 50, note.velocity_product, -note.source_index,
                    ),
                )
                unique.append(winner)
                decisions.extend(
                    VoiceDecision("MERGE", start, end, loser.program, loser.midi_note, winner.program)
                    for loser in group if loser is not winner
                )

        excess = len(unique) - len(CHANNEL_NAMES)
        if excess > 0:
            if policy == "merge-identical-at-capacity":
                raise ValueError(
                    f"sound {sound_id} exceeds capacity after identical-pitch merging"
                )
            if policy == "merge-identical-then-duck-program-50":
                duckable = sorted(
                    (note for note in unique if note.program == 50),
                    key=lambda note: (
                        note.velocity_product, -note.midi_note,
                        note.end - note.start, -note.start,
                    ),
                )
                if len(duckable) < excess:
                    raise ValueError(
                        f"sound {sound_id} needs {excess} more virtual voices outside its duckable bed"
                    )
                ducked = set(duckable[:excess])
                action = "DUCK"
            elif policy == "fate82-role-priority":
                # Preserve melody (35/82), the lowest fundamental, and struck
                # program-112 accents.  Interior pad/chord doublings lose in a
                # stable velocity/duration/source-order ranking.  Identical
                # pitch+zone doublings were already merged above.
                def importance(note: TadNote) -> tuple[int, int, int, int, int]:
                    melodic = int(note.program in (35, 82))
                    bass = int(note.midi_note < 48)
                    struck = int(note.program == 112)
                    return (
                        melodic * 4 + bass * 3 + struck * 2,
                        note.velocity_product,
                        note.end - note.start,
                        -abs(note.midi_note - 54),
                        -note.source_index,
                    )
                winners = set(sorted(unique, key=importance, reverse=True)[:len(CHANNEL_NAMES)])
                ducked = set(unique) - winners
                action = "DUCK_ROLE"
            else:
                low = min(unique, key=lambda note: note.midi_note)
                high = max(unique, key=lambda note: note.midi_note)
                protected = {low, high}
                protected.update(note for note in unique if note.start == start)
                if len(protected) > len(CHANNEL_NAMES):
                    raise ValueError(
                        f"sound {sound_id} has {len(protected)} simultaneous protected attacks"
                    )
                interior = sorted(
                    (note for note in unique if note not in protected),
                    key=lambda note: (
                        note.velocity_product, note.end - note.start,
                        -note.midi_note, -note.start,
                    ),
                    reverse=True,
                )
                protected.update(interior[:len(CHANNEL_NAMES) - len(protected)])
                ducked = set(unique) - protected
                action = "DUCK_CHORD"
            decisions.extend(
                VoiceDecision(
                    action, start, end, note.program, note.midi_note,
                    source_index=note.source_index,
                )
                for note in ducked
            )
            unique = [note for note in unique if note not in ducked]

        segments.extend(_slice_note(note, start, end) for note in unique)

    arranged = _coalesce_segments(segments)
    allocate_voices(arranged)
    coalesced = _coalesce_decisions(decisions)
    finalized = []
    for decision in coalesced:
        if decision.action != "DUCK_CHORD":
            finalized.append(decision)
            continue
        restored = any(
            note.source_index == decision.source_index and note.start >= decision.end
            for note in arranged
        )
        finalized.append(replace(
            decision, action="DUCK_RESTORE" if restored else "DUCK_END",
        ))
    return arranged, finalized


def allocate_voices(notes: list[TadNote]) -> list[list[TadNote]]:
    voices: list[list[TadNote]] = []
    for note in notes:
        lane = next((voice for voice in voices if voice[-1].end <= note.start), None)
        if lane is None:
            if len(voices) == len(CHANNEL_NAMES):
                raise ValueError("arrangement exceeds the eight S-DSP voices")
            lane = []
            voices.append(lane)
        lane.append(note)
    return voices


def _note_token(note: int) -> tuple[int, str]:
    return note // 12 - 1, NOTE_NAMES[note % 12]


def render_mml(sound_id: int, sound: ScummV5EmbeddedSound) -> str:
    notes, decisions = virtualize_polyphony(
        sound_id, quantize_notes(sound_id, collect_notes(sound)),
    )
    notes, omitted = reduce_polyphony(sound_id, notes)
    voices = allocate_voices(notes)
    final_tick = round(sound.duration_us * TICKS_PER_SECOND / 1_000_000)
    lines = [
        f"#Title Fate demo sound {sound_id}",
        "#Game Indiana Jones and the Fate of Atlantis interactive demo",
        "#Author SAME zoned ROL conversion",
        "#Timer 64",
        "#ZenLen 192",
        "",
        "; Generated from canonical ROL event times at 125 TAD ticks/second.",
        "; Every program/range mapping is an explicit reviewed arrangement policy.",
    ]
    if omitted:
        lines.append(f"; Voice reduction policy: {SOUND_VOICE_REDUCTION[sound_id]}.")
        lines.extend(
            "; OMIT "
            f"program {note.program} MIDI {note.midi_note} at {note.start / TICKS_PER_SECOND:.3f}s "
            f"for {(note.end - note.start) / TICKS_PER_SECOND:.3f}s "
            f"(velocity*CC7={note.velocity_product}); nine-voice collision."
            for note in omitted
        )
    if decisions:
        lines.append(
            f"; Voice virtualization policy: {SOUND_VOICE_VIRTUALIZATION[sound_id]}."
        )
        for decision in decisions:
            duration = (decision.end - decision.start) / TICKS_PER_SECOND
            timing = f"at {decision.start / TICKS_PER_SECOND:.3f}s for {duration:.3f}s"
            if decision.action == "MERGE":
                lines.append(
                    f"; MERGE program {decision.program} MIDI {decision.midi_note} "
                    f"into program {decision.peer_program} {timing}."
                )
            elif decision.action in ("DUCK", "DUCK_ROLE"):
                lines.append(
                    f"; DUCK program {decision.program} MIDI {decision.midi_note} {timing}."
                )
            elif decision.action == "DUCK_RESTORE":
                lines.append(
                    f"; DUCK program {decision.program} MIDI {decision.midi_note} {timing}; "
                    f"RESTORE at {decision.end / TICKS_PER_SECOND:.3f}s."
                )
            else:
                lines.append(
                    f"; DUCK program {decision.program} MIDI {decision.midi_note} {timing}; "
                    "source note ends here."
                )
    if SOUND_TICK_QUANTUM.get(sound_id, 1) > 1:
        lines.append("; Timing uses TAD's two-tick minimum key-off quantum.")
    controller_note_count = sum(bool(note.volume_changes) for note in notes)
    controller_change_count = sum(len(note.volume_changes) for note in notes)
    if controller_change_count:
        lines.append(
            f"; Preserved {controller_change_count} active-note CC7 fine-volume changes "
            f"across {controller_note_count} arranged notes without sample retrigger."
        )
    terminal_fade = SOUND_TERMINAL_FADE.get(sound_id)
    if terminal_fade is not None:
        lines.append(
            "; Terminal interactive hold retains source timing but fades static loop "
            f"voices to silence by {terminal_fade['fade_end_tick'] / TICKS_PER_SECOND:.3f}s."
        )
    lines.extend(f"@{index} {name}" for index, (name, _role) in enumerate(INSTRUMENTS))
    lines.append("")
    for voice_index, voice in enumerate(voices):
        channel = CHANNEL_NAMES[voice_index]
        cursor = 0
        current_instrument = current_volume = current_octave = None
        tokens = ["q0"]
        for note in voice:
            if note.start > cursor:
                tokens.append(f"r%{note.start - cursor}")
            if note.instrument != current_instrument:
                tokens.append(f"@{note.instrument}")
                current_instrument = note.instrument
            if note.volume != current_volume:
                tokens.append(f"V{note.volume}")
                current_volume = note.volume
            octave, pitch = _note_token(note.midi_note)
            if octave != current_octave:
                tokens.append(f"o{octave}")
                current_octave = octave
            if (
                terminal_fade is not None
                and note.end >= terminal_fade["sentinel_tick"]
                and note.start < terminal_fade["fade_end_tick"]
            ):
                fade_ticks = min(256, terminal_fade["fade_end_tick"] - note.start)
                fade_start = terminal_fade["fade_end_tick"] - fade_ticks
                if note.start < fade_start:
                    prior_changes = tuple(
                        change for change in note.volume_changes if change[0] < fade_start
                    )
                    if prior_changes:
                        first_tick = prior_changes[0][0]
                        tokens.extend((f"{pitch}%{first_tick - note.start}", "&"))
                        for change_index, (change_tick, changed_volume) in enumerate(
                            prior_changes
                        ):
                            next_tick = (
                                prior_changes[change_index + 1][0]
                                if change_index + 1 < len(prior_changes)
                                else fade_start
                            )
                            tokens.extend((
                                f"V{changed_volume}", f"w%{next_tick - change_tick}",
                            ))
                            current_volume = changed_volume
                    else:
                        tokens.extend((f"{pitch}%{fade_start - note.start}", "&"))
                    tokens.extend((
                        f"Vs-{current_volume},{fade_ticks}",
                        f"w%{note.end - fade_start}",
                    ))
                    current_volume = 0
                    cursor = note.end
                    continue
                tokens.append(f"Vs-{note.volume},{fade_ticks}")
            if note.volume_changes:
                first_tick = note.volume_changes[0][0]
                tokens.extend((f"{pitch}%{first_tick - note.start}", "&"))
                for change_index, (change_tick, changed_volume) in enumerate(
                    note.volume_changes
                ):
                    next_tick = (
                        note.volume_changes[change_index + 1][0]
                        if change_index + 1 < len(note.volume_changes)
                        else note.end
                    )
                    tokens.extend((f"V{changed_volume}", f"w%{next_tick - change_tick}"))
                    current_volume = changed_volume
            else:
                tokens.append(f"{pitch}%{note.end - note.start}")
            cursor = note.end
        if cursor < final_tick:
            tokens.append(f"r%{final_tick - cursor}")
        lines.append(f"{channel} " + " ".join(tokens))
    lines.append("")
    return "\n".join(lines)


def load_sound(archive: Path, sound_id: int) -> ScummV5EmbeddedSound:
    with zipfile.ZipFile(archive) as bundle:
        raw = {name: bundle.read(member) for name, member in MEMBERS.items()}
    resources = MemoryResourceProvider(
        {
            "game.index": raw["index"], "game.data": raw["data"],
            "distribution.notice": raw["notice"],
            "music.catalog": CATALOG.read_bytes(),
        },
        kinds={
            "game.index": "SCIX", "game.data": "SCDT",
            "distribution.notice": "TEXT", "music.catalog": "MCAT",
        },
    )
    profile = load_profile(PROFILE, verify_resources=False)
    host = EngineHost(profile, default_registry(), services=HostServices.create(profile, resources=resources))
    host.boot()
    key = f"sound.{sound_id}"
    return ScummV5EmbeddedSound.decode(host.services.resources.read(key), key)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--sound", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sound = load_sound(args.archive.resolve(), args.sound)
    rendered = render_mml(args.sound, sound)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    source_notes = collect_notes(sound)
    virtualized, decisions = virtualize_polyphony(
        args.sound, quantize_notes(args.sound, source_notes),
    )
    retained, omitted = reduce_polyphony(args.sound, virtualized)
    represented_sources = {note.source_index for note in retained}
    print(
        f"{args.output}: {len(represented_sources)}/{len(source_notes)} source notes represented, "
        f"{len(source_notes) - len(represented_sources)} omitted, "
        f"{len(decisions) + len(omitted)} voice decisions, "
        f"{sound.duration_us / 1_000_000:.3f} seconds"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
