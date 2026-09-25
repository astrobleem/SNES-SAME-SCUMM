#!/usr/bin/env python3
"""Build M22's bounded sound-80 hook-8 section arrangement and audit."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from same.engines.scumm_v5.embedded_audio import (
    EmbeddedMidiEvent, EmbeddedMidiTrack, ScummV5EmbeddedSound,
)
from build_fate_sound80_routes import (
    PROGRAM_ROLES, ZONE_DEFINITIONS, audition_mml, load_sound,
)
from convert_fate_sound_to_tad_mml import (
    CHANNEL_NAMES, INSTRUMENTS, NOTE_NAMES, TICKS_PER_SECOND, TadNote,
    allocate_voices, collect_notes, quantize_notes, virtualize_polyphony,
)


SOURCE_BOUNDARY = 68160
SOURCE_DESTINATION = 1920
SOURCE_DEFAULT_END = 79680
SOURCE_HOOK_END = 13440
NORMALIZED_BOUNDARY = 8644
CONTINUATION_TICKS = 1500
BOUNDARY_TOKEN = 1
NEW_PROGRAM_AUDITIONS = {
    50: (34, 35, 36, 40),
    97: (66, 78),
    107: (54, 56, 59, 61, 63, 66),
}
NEW_PROGRAM_ROLES = {
    50: ("bass", "pad-main"),
    97: ("flute-mid",),
    107: ("pad-main",),
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _route_sound(sound: ScummV5EmbeddedSound, *, hook: bool) -> ScummV5EmbeddedSound:
    prefix = sound.tracks[0]
    body = sound.tracks[3]
    first_jump_us = prefix.time_at_tick(90, sound.division)
    body_origin_us = body.time_at_tick(1920, sound.division)
    boundary_us = first_jump_us + body.time_at_tick(SOURCE_BOUNDARY, sound.division) - body_origin_us
    selected: list[EmbeddedMidiEvent] = []

    def append(track: EmbeddedMidiTrack, first: int, last: int, base_us: int, origin_us: int) -> None:
        for event in track.events:
            if event.tick < first:
                continue
            if event.tick >= last:
                break
            if event.status >= 0xf0:
                continue
            time_us = base_us + event.time_us - origin_us
            selected.append(replace(
                event, time_us=time_us,
                tick=round(time_us * sound.division * 2 / 1_000_000),
            ))

    append(prefix, 0, 90, 0, 0)
    append(body, 1920, SOURCE_BOUNDARY, first_jump_us, body_origin_us)
    if hook:
        append(body, SOURCE_DESTINATION, SOURCE_HOOK_END, boundary_us, body_origin_us)
        source_end = SOURCE_HOOK_END
        branch = [3, SOURCE_BOUNDARY, 3, SOURCE_DESTINATION]
    else:
        append(body, SOURCE_BOUNDARY + 1, SOURCE_DEFAULT_END, boundary_us,
               body.time_at_tick(SOURCE_BOUNDARY, sound.division))
        source_end = SOURCE_DEFAULT_END
        branch = None
    end_us = boundary_us + CONTINUATION_TICKS * 1_000_000 // TICKS_PER_SECOND
    # Close only notes still live at the bounded fixture end. This is an
    # explicit test-section cutoff, not a claim about cue completion.
    active: dict[tuple[int, int], int] = {}
    for event in sorted(selected, key=lambda item: item.time_us):
        op, channel = event.status & 0xf0, event.status & 0x0f
        key = (channel, event.data[0]) if event.data else (0, 0)
        if op == 0x90 and event.data[1]:
            active[key] = active.get(key, 0) + 1
        elif op in (0x80, 0x90) and key in active:
            active[key] -= 1
            if not active[key]:
                del active[key]
    for (channel, note), count in sorted(active.items()):
        selected.extend(EmbeddedMidiEvent(
            round(end_us * sound.division * 2 / 1_000_000), end_us,
            0x80 | channel, (note, 0),
        ) for _ in range(count))
    selected.sort(key=lambda item: item.time_us)
    track = EmbeddedMidiTrack(
        duration_us=end_us,
        duration_ticks=round(end_us * sound.division * 2 / 1_000_000),
        events=tuple(selected), tempo_map=((0, 0, 500_000),),
    )
    routed = ScummV5EmbeddedSound(
        key=sound.key, rendition=sound.rendition, priority=sound.priority,
        midi_format=0, track_count=1, division=sound.division,
        duration_us=end_us, events=tuple(selected), tracks=(track,),
        imuse_events=((),), sha256=sound.sha256,
    )
    return routed


def _arrange(sound: ScummV5EmbeddedSound) -> list[list[TadNote]]:
    notes, _decisions = virtualize_polyphony(80, quantize_notes(80, collect_notes(sound)))
    lanes = allocate_voices(notes)
    while len(lanes) < 8:
        lanes.append([])
    return lanes


def _note_token(note: int) -> tuple[int, str]:
    return note // 12 - 1, NOTE_NAMES[note % 12]


def _segment_tokens(notes: list[TadNote], start: int, end: int, *, prefix: bool) -> list[str]:
    cursor = start
    instrument = volume = octave = None
    tokens = ["q0"] if prefix else []
    for note in notes:
        a, b = max(start, note.start), min(end, note.end)
        if a >= b:
            continue
        if a > cursor:
            tokens.append(f"r%{a - cursor}")
        crossing_in = note.start < start
        crossing_out = note.end > end
        if crossing_in:
            tokens.append(f"w%{b - a}")
        else:
            if note.instrument != instrument:
                tokens.append(f"@{note.instrument}")
                instrument = note.instrument
            if note.volume != volume:
                tokens.append(f"V{note.volume}")
                volume = note.volume
            octave_value, pitch = _note_token(note.midi_note)
            if octave_value != octave:
                tokens.append(f"o{octave_value}")
                octave = octave_value
            tokens.append(f"{pitch}%{b - a}")
        if crossing_out:
            tokens.append("&")
        cursor = b
    if cursor < end:
        tokens.append(f"r%{end - cursor}")
    return tokens


def build_mml(default: list[list[TadNote]], hook: list[list[TadNote]]) -> bytes:
    lines = [
        "#Title Fate sound 80 hook14 with delayed hook8 boundary",
        "#Game Indiana Jones and the Fate of Atlantis interactive demo",
        "#Author SAME M22 bounded compiled-section arrangement",
        "#Timer 64", "#ZenLen 192", "",
        "; Source hook-8 boundary: track 3 tick 68160.",
        "; Runtime selector executes at normalized TAD tick 8644, not at a source tick.",
    ]
    lines.extend(f"@{index} {name}" for index, (name, _role) in enumerate(INSTRUMENTS))
    lines.append("")
    end = NORMALIZED_BOUNDARY + CONTINUATION_TICKS
    for index in range(8):
        lines.append(f"!m22_default_{index} " + " ".join(
            _segment_tokens(default[index], NORMALIZED_BOUNDARY, end, prefix=False)))
    for index in range(8):
        lines.append(f"!m22_hook8_{index} " + " ".join(
            _segment_tokens(hook[index], NORMALIZED_BOUNDARY, end, prefix=False)))
    lines.append("")
    for index, channel in enumerate(CHANNEL_NAMES):
        prefix = _segment_tokens(default[index], 0, NORMALIZED_BOUNDARY, prefix=True)
        placeholder = (
            f"\\asm {{ call_subroutine m22_default_{index} | disable_echo | disable_echo }}"
        )
        lines.append(f"{channel} " + " ".join(prefix + [placeholder]))
    lines.append("")
    return "\n".join(lines).encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = load_sound(args.archive.resolve())
    default, hook = _arrange(_route_sound(source, hook=False)), _arrange(_route_sound(source, hook=True))
    # Prefix lane identity is a hard invariant: the selector changes only the
    # continuation and therefore cannot repair a divergent pre-boundary layout.
    prefix_fingerprints = []
    for index in range(8):
        def fp(lane: list[TadNote]) -> list[tuple[int, int, int, int, int]]:
            return [(n.start, min(n.end, NORMALIZED_BOUNDARY), n.midi_note, n.program, n.instrument)
                    for n in lane if n.start < NORMALIZED_BOUNDARY]
        if fp(default[index]) != fp(hook[index]):
            raise RuntimeError(f"route prefix lane {index} differs before boundary")
        prefix_fingerprints.append(fp(default[index]))
    mml = build_mml(default, hook)
    (args.output / "sound80_hook14_hook8_sections.mml").write_bytes(mml)
    programs: dict[str, set[int]] = {"default": set(), "hook8": set()}
    for name, lanes in (("default", default), ("hook8", hook)):
        for lane in lanes:
            programs[name].update(n.program for n in lane if n.start >= NORMALIZED_BOUNDARY)
    auditions = {}
    for program, notes in NEW_PROGRAM_AUDITIONS.items():
        PROGRAM_ROLES[program] = NEW_PROGRAM_ROLES[program]
        raw = audition_mml(program, notes)
        filename = f"program_{program}_used_range.mml"
        (args.output / filename).write_bytes(raw)
        auditions[str(program)] = {
            "status": "human-timbre-pending", "used_notes": list(notes),
            "mml": filename, "mml_sha256": sha(raw),
            "zones": [ZONE_DEFINITIONS[role][0] for role in NEW_PROGRAM_ROLES[program]],
        }
    bank = {
        "schema": "same_fate_sound80_m22_instrument_bank_v1",
        "parent_manifest": "audio/fate_s6/samples/loop_safe_manifest.json",
        "parent_sha256": sha((Path(__file__).resolve().parents[1] /
                              "audio/fate_s6/samples/loop_safe_manifest.json").read_bytes()),
        "programs": {},
    }
    all_roles = dict(PROGRAM_ROLES)
    all_roles.update(NEW_PROGRAM_ROLES)
    for program in (32, 33, 50, 57, 77, 82, 97, 107):
        selected = []
        for role in all_roles[program]:
            name, path, root_hz, envelope, loop, first, last = ZONE_DEFINITIONS[role]
            sample = Path(__file__).resolve().parents[1] / path
            selected.append({
                "role": role, "zone": name, "source": path,
                "source_sha256": sha(sample.read_bytes()), "root_hz": root_hz,
                "coverage": [first, last], "envelope": envelope, "loop": loop,
            })
        bank["programs"][str(program)] = selected
    bank_raw = (json.dumps(bank, indent=2, sort_keys=True) + "\n").encode()
    (args.output / "instrument_bank.json").write_bytes(bank_raw)
    boundary_us = source.tracks[0].time_at_tick(90, source.division)
    boundary_us += (source.tracks[3].time_at_tick(SOURCE_BOUNDARY, source.division)
                    - source.tracks[3].time_at_tick(SOURCE_DESTINATION, source.division))
    audit = {
        "schema": "same_fate_sound80_m22_sections_v1",
        "logical_sound_id": 80, "source_sha256": source.sha256,
        "cue_route_history": {"kind": "hook", "value": 14,
                              "identity": "room49-hook14"},
        "current_section": "hook14-pre-hook8-boundary",
        "boundary": {
            "source_track": 3, "source_tick": SOURCE_BOUNDARY,
            "time_us": boundary_us, "normalized_tad_tick": NORMALIZED_BOUNDARY,
            "quantization_error_us": round(NORMALIZED_BOUNDARY * 1_000_000 / 125) - boundary_us,
            "token": BOUNDARY_TOKEN,
        },
        "continuations": {
            "default": {"source_track": 3, "source_tick": SOURCE_BOUNDARY + 1,
                        "section": "default-after-hook8", "programs": sorted(programs["default"])},
            "hook8": {"consumed_branch": [3, SOURCE_BOUNDARY, 3, SOURCE_DESTINATION],
                      "first_destination_notes": [[3, 1923], [3, 1924], [3, 1925]],
                      "section": "hook8-track3-1920", "programs": sorted(programs["hook8"])},
        },
        "continuation_ticks": CONTINUATION_TICKS,
        "runtime_executes_source_tick": False,
        "instrument_bank": "fate-s6-m21-reviewed-plus-m22-p50-low-p97-p107-pending",
        "instrument_bank_sha256": sha(bank_raw),
        "new_program_auditions": auditions,
        "mml_sha256": sha(mml),
        "prefix_lane_fingerprints": prefix_fingerprints,
    }
    identity_material = json.dumps(audit, sort_keys=True, separators=(",", ":")).encode()
    audit["section_plan_identity"] = sha(identity_material)
    raw = (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode()
    (args.output / "audit.json").write_bytes(raw)
    print(f"source={source.sha256} boundary={NORMALIZED_BOUNDARY} mml={sha(mml)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
