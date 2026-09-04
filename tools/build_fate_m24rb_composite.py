#!/usr/bin/env python3
"""Build M24R-B's provenance-bound sound-80/82 composite and reduction audit."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path

from same.engines.scumm_v5.embedded_audio import EmbeddedMidiEvent, EmbeddedMidiTrack, ScummV5EmbeddedSound
from build_fate_sound80_m22_sections import _arrange as arrange80, _route_sound, _segment_tokens, NORMALIZED_BOUNDARY
from convert_fate_sound_to_tad_mml import (
    CHANNEL_NAMES, INSTRUMENTS, TICKS_PER_SECOND, TadNote, allocate_voices,
    collect_notes, load_sound, quantize_notes, virtualize_polyphony,
)

ROOT = Path(__file__).resolve().parents[1]
S82_LOOP_START_SOURCE = 1920
S82_LOOP_END_SOURCE = 97920
MARKER_SENTINEL = bytes((0x2f, 5, 0x3c, 0x3c))
ADMISSION_TICKS = (19, 38, 63, 94, 125)
ADMISSION_VOICES = (7, 6, 5, 4, 3)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def route_to_marker8(sound: ScummV5EmbeddedSound) -> ScummV5EmbeddedSound:
    """Flatten only hook14 -> hook7 -> marker8, retaining authentic provenance."""
    pieces = ((0, 0, 90), (3, 1920, 21600), (2, 95520, 103390))
    selected: list[EmbeddedMidiEvent] = []
    base_us = 0
    for track_no, first, last in pieces:
        track = sound.tracks[track_no]
        origin = track.time_at_tick(first, sound.division)
        for event in track.events:
            if first <= event.tick < last and event.status < 0xf0:
                time_us = base_us + event.time_us - origin
                selected.append(replace(event, time_us=time_us,
                    tick=round(time_us * sound.division * 2 / 1_000_000)))
        base_us += track.time_at_tick(last, sound.division) - origin
    # A compiled section owns its boundary: release source voices explicitly.
    active: dict[tuple[int, int], int] = {}
    for event in sorted(selected, key=lambda item: (item.time_us, item.status)):
        op, channel = event.status & 0xf0, event.status & 15
        if not event.data:
            continue
        key = channel, event.data[0]
        if op == 0x90 and event.data[1]:
            active[key] = active.get(key, 0) + 1
        elif op in (0x80, 0x90) and key in active:
            active[key] -= 1
            if active[key] <= 0:
                del active[key]
    for (channel, note), count in sorted(active.items()):
        selected.extend(EmbeddedMidiEvent(0, base_us, 0x80 | channel, (note, 0))
                        for _ in range(count))
    selected.sort(key=lambda item: (item.time_us, item.status))
    track = EmbeddedMidiTrack(base_us, round(base_us * sound.division * 2 / 1_000_000),
                              tuple(selected), ((0, 0, 500_000),))
    return ScummV5EmbeddedSound(sound.key, sound.rendition, sound.priority, 0, 1,
        sound.division, base_us, tuple(selected), (track,), ((),), sound.sha256)


def sliced_tokens(lane: list[TadNote], start: int, end: int, *, prefix: bool = False) -> list[str]:
    # Re-key notes crossing a compiled entry boundary; logical source sustain
    # cannot be represented as an inherited DSP envelope after a section jump.
    adjusted = [replace(note, start=max(note.start, start), end=min(note.end, end))
                for note in lane if note.start < end and note.end > start
                and min(note.end, end) - max(note.start, start) >= 2]
    return _segment_tokens(adjusted, start, end, prefix=prefix)


def reduce_to_five(lanes: list[list[TadNote]]) -> tuple[list[list[TadNote]], list[dict[str, object]]]:
    notes = [note for lane in lanes for note in lane]
    points = sorted({value for note in notes for value in (note.start, note.end)})
    retained: list[TadNote] = []
    audit: list[dict[str, object]] = []
    for left, right in zip(points, points[1:]):
        active = [note for note in notes if note.start < right and note.end > left]
        if not active:
            continue
        # Primary melody, bass/fundamental, outer chord tones, then strength.
        ranked = sorted(active, key=lambda n: (
            n.program not in (57, 73, 97), n.midi_note >= 48,
            -n.velocity_product, abs(n.midi_note - 60), n.source_index,
        ))
        keep = ranked[:5]
        for note in keep:
            retained.append(replace(note, start=left, end=right))
        if len(active) > 5:
            audit.append({"start": left, "end": right, "requested": len(active),
                "retained": [[n.program, n.midi_note, n.source_index] for n in keep],
                "omitted": [[n.program, n.midi_note, n.source_index] for n in ranked[5:]],
                "reason": "protect melody, bass, structural outer voices, then strength"})
    # Coalesce identical source fragments.
    merged: list[TadNote] = []
    for note in sorted(retained, key=lambda n: (n.source_index, n.start, n.end)):
        if merged and merged[-1].source_index == note.source_index and merged[-1].end == note.start:
            merged[-1] = replace(merged[-1], end=note.end)
        else:
            merged.append(note)
    result = allocate_voices(merged)
    while len(result) < 5:
        result.append([])
    return result[:5], audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    sound80, sound82 = load_sound(args.archive, 80), load_sound(args.archive, 82)
    prelude_notes, prelude_decisions = virtualize_polyphony(
        80, quantize_notes(80, collect_notes(route_to_marker8(sound80))))
    prelude = allocate_voices(prelude_notes)
    while len(prelude) < 8: prelude.append([])
    notes82, decisions82 = virtualize_polyphony(82, quantize_notes(82, collect_notes(sound82)))
    lanes82 = allocate_voices(notes82)
    while len(lanes82) < 8: lanes82.append([])
    loop_start = round(sound82.tracks[0].time_at_tick(S82_LOOP_START_SOURCE, sound82.division)
                       * TICKS_PER_SECOND / 1_000_000)
    loop_end = round(sound82.tracks[0].time_at_tick(S82_LOOP_END_SOURCE, sound82.division)
                     * TICKS_PER_SECOND / 1_000_000)
    prelude_end = max(note.end for lane in prelude for note in lane)
    hook8 = arrange80(_route_sound(sound80, hook=True))
    incoming, overlap_audit = reduce_to_five(hook8)
    continuation_end = NORMALIZED_BOUNDARY + 6000

    lines = ["#Title Fate M24R-B bounded sound 80 + 82 composite",
             "#Game Indiana Jones and the Fate of Atlantis interactive demo",
             "#Author SAME source-bound bounded composite", "#Timer 64", "#ZenLen 192", ""]
    lines.extend(f"@{i} {name}" for i, (name, _role) in enumerate(INSTRUMENTS))
    lines.append("")
    for index in range(5):
        start = NORMALIZED_BOUNDARY + ADMISSION_TICKS[index]
        tokens = sliced_tokens(incoming[index], start, continuation_end)
        lines.append(f"!m24rb_sound80_lane_{index} " + " ".join(["[", *tokens, "]255"]))
    lines.append("!m24rb_marker_dummy r%2")
    lines.append("")
    for index, channel in enumerate(CHANNEL_NAMES):
        prefix = sliced_tokens(prelude[index], 0, prelude_end, prefix=True)
        marker = ("\\asm { call_subroutine m24rb_marker_dummy | disable_echo | disable_echo }"
                  if index == 0 else "r%2")
        initial = sliced_tokens(lanes82[index], 0, loop_start)
        loop = sliced_tokens(lanes82[index], loop_start, loop_end)
        lines.append(f"{channel} " + " ".join(prefix + [marker] + initial + ["[", *loop, "]255"]))
    mml = ("\n".join(lines) + "\n").encode()
    (output / "fate_m24rb_composite.mml").write_bytes(mml)

    project = json.loads((ROOT / "audio/fate_s6/fate.terrificaudio").read_text())
    selected = {name for name, _role in INSTRUMENTS}
    project["instruments"] = [item for item in project["instruments"] if item["name"] in selected]
    for item in project["instruments"]:
        source = (ROOT / "audio/fate_s6" / item["source"]).resolve()
        item["source"] = os.path.relpath(source, output)
    project["songs"] = [{"name": "fate_m24rb_composite", "source": "fate_m24rb_composite.mml"}]
    project_path = output / "m24rb.terrificaudio"
    project_path.write_text(json.dumps(project, indent=2) + "\n")
    compromises = [d for d in decisions82 if d.action != "KEEP"]
    audit = {
        "schema": "same_fate_m24rb_composite_v1",
        "sources": {"80": sound80.sha256, "82": sound82.sha256},
        "routes": {"sound80": [[0,0,90],[3,1920,21600],[2,95520,103390]],
                   "sound82_loop": [S82_LOOP_END_SOURCE, S82_LOOP_START_SOURCE],
                   "room63_sound80": [3,68160,3,1920]},
        "marker8": {"prelude_normalized_tick": prelude_end, "sentinel": MARKER_SENTINEL.hex()},
        "sound82": {"source_notes": len(collect_notes(sound82)), "represented_notes": len({n.source_index for n in notes82}),
                    "loop_start_tick": loop_start, "loop_end_tick": loop_end,
                    "loop_period_ticks": loop_end-loop_start,
                    "voice_decisions": [],
                    "compromise_count": len(compromises)},
        "room63_transition": {"admission_ticks": list(ADMISSION_TICKS),
            "admission_voices": list(ADMISSION_VOICES), "fade_ticks": 256,
            "incoming_reduction": overlap_audit},
        "prelude_decisions": [],
        "mml_sha256": sha(mml), "project_sha256": sha(project_path.read_bytes()),
        "runtime_executes_source_tick": False,
    }
    # frozen dataclasses have no __dict__ under slots
    def decision(item):
        return {name: getattr(item, name) for name in item.__dataclass_fields__}
    audit["sound82"]["voice_decisions"] = [decision(d) for d in decisions82]
    audit["prelude_decisions"] = [decision(d) for d in prelude_decisions]
    raw = (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode()
    (output / "composite-audit.json").write_bytes(raw)
    print(f"mml={sha(mml)} sound82={sound82.sha256} loop={loop_end-loop_start} compromises={len(compromises)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
