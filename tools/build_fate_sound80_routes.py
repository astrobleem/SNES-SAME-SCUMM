#!/usr/bin/env python3
"""Build and audit M21's two bounded Fate sound-80 compiled routes."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import zipfile

from same.engines.scumm_v5.embedded_audio import (
    EmbeddedMidiEvent, EmbeddedMidiTrack, ScummV5EmbeddedSound,
)
from convert_fate_sound_to_tad_mml import render_mml


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "3692a73673d619461b6215bae731832752610c99c166bbbf5978beb30afd5ed0"
MEMBERS = {"index": "FATEDEMO/PLAYFATE.000", "data": "FATEDEMO/PLAYFATE.001"}
ROUTES = {
    "default": {"kind": "default", "value": 0, "branch": [0, 100, 0, 1920], "end_tick": 28795},
    "hook14": {"kind": "hook", "value": 14, "branch": [0, 90, 3, 1920], "end_tick": 21600},
}
PROGRAM_AUDITIONS = {
    32: (63, 64),
    33: (49, 55, 60, 67, 71, 72, 79, 85),
    50: (40, 45, 50, 54),
    57: (49, 55, 60, 63, 64, 72, 80),
    77: (30, 36, 42, 48, 54, 56),
    82: (47, 48, 52, 56),
}
ZONE_DEFINITIONS = {
    "pad-main": ("mt32_p88_cycle", "audio/fate_s6/samples/mt32_p88_cycle.wav", 500.0,
                 "adsr 15 1 7 0", "loop_reset_filter:0", 36, 71),
    "pad-high": ("mt32_p88_cycle_x2", "audio/fate_s6/samples/mt32_p88_cycle_x2.wav", 1000.0,
                 "adsr 15 1 7 0", "loop_reset_filter:0", 72, 95),
    "flute-low": ("mt32_p74_cycle", "audio/fate_s6/samples/mt32_p74_cycle.wav", 166.666667,
                  "adsr 15 1 7 0", "loop_reset_filter:0", 48, 63),
    "flute-mid": ("mt32_p74_cycle_x2", "audio/fate_s6/samples/mt32_p74_cycle_x2.wav", 333.333333,
                  "adsr 15 1 7 0", "loop_reset_filter:0", 64, 83),
    "bass": ("ph_bass", "audio/fate_s6/samples/Phantasia_Soft_Bass.brr", 111.111,
             "adsr 15 7 7 12", "none", 24, 59),
}
PROGRAM_ROLES = {
    32: ("pad-main",), 33: ("pad-main", "pad-high"), 50: ("pad-main",),
    57: ("flute-low", "flute-mid"), 77: ("bass",), 82: ("pad-main",),
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _mml_note(note: int) -> str:
    names = ("c", "c+", "d", "d+", "e", "f", "f+", "g", "g+", "a", "a+", "b")
    return f"o{note // 12 - 1} {names[note % 12]}"


def _instrument_index(note: int, roles: tuple[str, ...]) -> int:
    for role in roles:
        if ZONE_DEFINITIONS[role][5] <= note <= ZONE_DEFINITIONS[role][6]:
            return {"pad-main": 0, "pad-high": 1, "flute-low": 2,
                    "flute-mid": 3, "bass": 5}[role]
    raise RuntimeError(f"audition note {note} has no selected zone")


def audition_mml(program: int, notes: tuple[int, ...]) -> bytes:
    roles = PROGRAM_ROLES[program]
    sequence = []
    for note in notes:
        sequence.append(f"@{_instrument_index(note, roles)} V64 {_mml_note(note)}%48 r%16")
    # Repeat the endpoints more slowly so attacks, tails, and the complete used
    # range can be judged independently of the scale.
    for note in (notes[0], notes[-1]):
        sequence.append(f"@{_instrument_index(note, roles)} V64 {_mml_note(note)}%112 r%32")
    return (f"#Title Fate sound 80 program {program} used-range audition\n"
            "#Game Indiana Jones and the Fate of Atlantis interactive demo\n"
            "#Author SAME M21 isolated instrument gate\n#Timer 64\n#ZenLen 192\n\n"
            "@0 mt32_p88_cycle\n@1 mt32_p88_cycle_x2\n"
            "@2 mt32_p74_cycle\n@3 mt32_p74_cycle_x2\n"
            "@4 mt32_p74_cycle_x4\n@5 ph_bass\n\n"
            + "A q0 " + " ".join(sequence) + " r%96\n").encode()


def load_sound(archive: Path) -> ScummV5EmbeddedSound:
    # Reuse the strict resource provider rather than copying archive offsets.
    from same.engines import default_registry
    from same.engine import EngineHost
    from same.profile import load_profile
    from same.resources import MemoryResourceProvider
    from same.services import HostServices
    profile = load_profile(
        ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
        verify_resources=False,
    )
    with zipfile.ZipFile(archive) as bundle:
        raw = {name: bundle.read(member) for name, member in MEMBERS.items()}
        raw["notice"] = bundle.read("FATEDEMO/READ.ME")
    resources = MemoryResourceProvider(
        {"game.index": raw["index"], "game.data": raw["data"],
         "distribution.notice": raw["notice"],
         "music.catalog": (ROOT / "examples/resources/music/fate_s6_compiled.json").read_bytes()},
        kinds={"game.index": "SCIX", "game.data": "SCDT", "distribution.notice": "TEXT",
               "music.catalog": "MCAT"},
    )
    host = EngineHost(profile, default_registry(), services=HostServices.create(profile, resources=resources))
    host.boot()
    source = host.services.resources.read("sound.80")
    sound = ScummV5EmbeddedSound.decode(source, "sound.80", rendition_order=(b"ROL ",))
    if sound.sha256 != SOURCE_SHA256:
        raise RuntimeError(f"Fate sound 80 identity differs: {sound.sha256}")
    return sound


def flatten(sound: ScummV5EmbeddedSound, route: dict[str, object]) -> tuple[ScummV5EmbeddedSound, dict[str, object]]:
    from_track, branch_tick, target_track, target_tick = route["branch"]
    source_prefix = sound.tracks[from_track]
    target = sound.tracks[target_track]
    prefix_us = source_prefix.time_at_tick(branch_tick, sound.division)
    target_origin_us = target.time_at_tick(target_tick, sound.division)
    end_tick = int(route["end_tick"])
    end_us = prefix_us + target.time_at_tick(end_tick, sound.division) - target_origin_us
    selected: list[EmbeddedMidiEvent] = []
    active: dict[tuple[int, int], int] = {}
    first_note = None
    programs = [0] * 16
    program_ranges: dict[int, list[int]] = {}
    for event in source_prefix.events:
        if event.tick >= branch_tick:
            break
        if event.status < 0xF0:
            selected.append(event)
            if event.status & 0xF0 == 0xC0:
                programs[event.status & 0x0F] = event.data[0]
            elif event.status & 0xF0 == 0x90 and event.data[1]:
                raise RuntimeError("M21 route prefix unexpectedly contains a note-on")
    for event in target.events:
        if event.tick < target_tick:
            continue
        if event.tick >= end_tick:
            break
        shifted_us = prefix_us + event.time_us - target_origin_us
        shifted_tick = round(shifted_us * sound.division * 2 / 1_000_000)
        copied = replace(event, tick=shifted_tick, time_us=shifted_us)
        if event.status >= 0xF0:
            continue
        command, channel = event.status & 0xF0, event.status & 0x0F
        if command == 0xC0:
            programs[channel] = event.data[0]
        elif command == 0x90 and event.data[1]:
            active[(channel, event.data[0])] = active.get((channel, event.data[0]), 0) + 1
            program_ranges.setdefault(programs[channel], []).append(event.data[0])
            if first_note is None:
                first_note = {"track": target_track, "tick": event.tick, "time_us": shifted_us}
        elif command in (0x80, 0x90):
            key = (channel, event.data[0])
            if key in active:
                active[key] -= 1
                if not active[key]:
                    del active[key]
        selected.append(copied)
    for (channel, note), count in sorted(active.items()):
        selected.extend(
            EmbeddedMidiEvent(end_tick, end_us, 0x80 | channel, (note, 0))
            for _ in range(count)
        )
    # Stable time sorting retains source order for same-timestamp program,
    # controller, and note events.
    selected.sort(key=lambda event: event.time_us)
    synthetic_track = EmbeddedMidiTrack(
        duration_us=end_us, duration_ticks=round(end_us * sound.division * 2 / 1_000_000),
        events=tuple(selected), tempo_map=((0, 0, 500_000),),
    )
    flattened = ScummV5EmbeddedSound(
        key=sound.key, rendition=sound.rendition, priority=sound.priority,
        midi_format=0, track_count=1, division=sound.division, duration_us=end_us,
        events=tuple(selected), tracks=(synthetic_track,), imuse_events=((),), sha256=sound.sha256,
    )
    branch = list(route["branch"])
    audit = {
        "schema": "same_scumm_v5_compiled_route_audit_v1",
        "logical_sound_id": 80, "source_resource": "sound.80",
        "source_sha256": sound.sha256,
        "route": {"kind": route["kind"], "value": route["value"]},
        "consumed_branch": {
            "source_track": branch[0], "source_tick": branch[1],
            "target_track": branch[2], "target_tick": branch[3],
        },
        "runtime_executes_source_branch": False,
        "prefix": {"note_on_count": 0, "sustained_voice_count": 0, "duration_us": prefix_us},
        "first_destination_note": first_note,
        "section_end": {"track": target_track, "tick": end_tick, "time_us": end_us},
        "program_ranges": {
            str(program): {"first": min(notes), "last": max(notes), "note_count": len(notes)}
            for program, notes in sorted(program_ranges.items())
        },
    }
    route_material = json.dumps(audit, sort_keys=True, separators=(",", ":")).encode()
    audit["route_identity"] = sha(route_material)
    return flattened, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sound = load_sound(args.archive.resolve())
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "same_fate_sound80_routes_v1", "source_sha256": sound.sha256,
                "routes": [], "instrument_gate": {"status": "human-timbre-pending",
                "programs": {}}}
    for name, route in ROUTES.items():
        flattened, audit = flatten(sound, route)
        mml = render_mml(80, flattened).encode()
        (args.output / f"sound80_{name}.mml").write_bytes(mml)
        audit_raw = (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode()
        (args.output / f"sound80_{name}.audit.json").write_bytes(audit_raw)
        manifest["routes"].append({
            "name": name, "mml_sha256": sha(mml), "audit_sha256": sha(audit_raw), **audit,
        })
    for program, notes in PROGRAM_AUDITIONS.items():
        mml = audition_mml(program, notes)
        filename = f"program_{program}_used_range.mml"
        (args.output / filename).write_bytes(mml)
        selected = []
        for role in PROGRAM_ROLES[program]:
            name, path, root_hz, envelope, loop, first, last = ZONE_DEFINITIONS[role]
            raw = (ROOT / path).read_bytes()
            selected.append({"role": role, "zone": name, "source": path,
                             "source_sha256": sha(raw), "root_hz": root_hz,
                             "coverage": [first, last], "envelope": envelope, "loop": loop})
        manifest["instrument_gate"]["programs"][str(program)] = {
            "used_range": [min(notes), max(notes)], "audition_notes": list(notes),
            "audition_mml": filename, "audition_mml_sha256": sha(mml),
            "selected_zones": selected,
        }
    manifest_raw = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    (args.output / "manifest.json").write_bytes(manifest_raw)
    print(f"sound80={sound.sha256} routes=2 manifest={sha(manifest_raw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
