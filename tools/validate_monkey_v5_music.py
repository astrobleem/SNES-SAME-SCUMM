#!/usr/bin/env python3
"""Inventory user-supplied Monkey v5 music and validate one shared-path cue."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
import zipfile

from same.engines.scumm_v5.embedded_audio import ScummV5EmbeddedSound
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.music import (
    InstrumentBank, realize_scumm_adlib_notes, render_reference, sequence_trace,
)
from same.music.devices import extract_scumm_adlib_patches
from same.music.importers import ScummImuseTimeline, import_scumm_adlib_sequence
from same.profile import load_profile
from same.resources import MemoryResourceProvider


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json"
BANK = ROOT / "audio/monkey_v5/monkey154_church_bank.json"
MEMBERS = {
    "index": "_monkeypacks_backup/talkie/monkey.000",
    "data": "_monkeypacks_backup/talkie/monkey.001",
}
SELECTED_SOUND = 154
REFERENCE_RATE = 8_000


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: object, *, pretty: bool = False) -> bytes:
    if pretty:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _renditions(raw: bytes, key: str) -> list[str]:
    if len(raw) < 8 or raw[:4] != b"SOU ":
        return []
    if int.from_bytes(raw[4:8], "big") != len(raw) - 8:
        raise RuntimeError(f"{key} has a noncanonical SOU size")
    result: list[str] = []
    offset = 8
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise RuntimeError(f"{key} has a truncated child header")
        tag = raw[offset : offset + 4].decode("ascii")
        size = int.from_bytes(raw[offset + 4 : offset + 8], "big")
        offset += 8 + size
        if offset > len(raw):
            raise RuntimeError(f"{key} has a truncated {tag!r} child")
        result.append(tag.strip())
    return result


def _provider(archive: Path) -> tuple[LucasartsScummV5ResourceProvider, dict[str, object]]:
    with zipfile.ZipFile(archive) as bundle:
        raw = {name: bundle.read(member) for name, member in MEMBERS.items()}
        member_info = {
            name: {
                "member": MEMBERS[name],
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in raw.items()
        }
    profile = load_profile(PROFILE, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None:
        raise RuntimeError("Monkey profile has no SCUMM v5 resource policy")
    backing = MemoryResourceProvider(
        {"game.index": raw["index"], "game.data": raw["data"]},
        kinds={"game.index": "SCIX", "game.data": "SCDT"},
    )
    return LucasartsScummV5ResourceProvider(backing, policy), member_info


def _inventory(provider: LucasartsScummV5ResourceProvider) -> tuple[list[dict[str, object]], dict[str, int]]:
    records: list[dict[str, object]] = []
    counts = {"adlib": 0, "silent_stub": 0, "sbl_only": 0}
    for key in (key for key in provider.keys() if key.startswith("sound.")):
        raw = provider.read(key)
        tags = _renditions(raw, key)
        record: dict[str, object] = {
            "key": key,
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "renditions": tags,
        }
        if not tags:
            if len(raw) != 24:
                raise RuntimeError(f"{key} is an unexplained {len(raw)}-byte non-SOU sound")
            classification = "silent_stub"
        elif "ADL" in tags:
            classification = "adlib"
            decoded = ScummV5EmbeddedSound.decode(
                raw, key, rendition_order=(b"ADL ",),
            )
            record["decode"] = decoded.inspect()
        elif set(tags) == {"SBL"}:
            classification = "sbl_only"
        else:
            raise RuntimeError(f"{key} has unexplained renditions {tags}")
        record["classification"] = classification
        counts[classification] += 1
        records.append(record)
    return records, counts


def monkey_church_pipeline(provider: LucasartsScummV5ResourceProvider) -> tuple[
    ScummV5EmbeddedSound, dict[int, object], object, InstrumentBank, tuple[object, ...],
]:
    """Title adapter for the exact M4 church-cue branch and reviewed bank."""
    cue_key = f"sound.{SELECTED_SOUND}"
    sound = ScummV5EmbeddedSound.decode(
        provider.read(cue_key), cue_key, rendition_order=(b"ADL ",),
    )
    patches = extract_scumm_adlib_patches(sound)
    jumps = [
        event for track in sound.imuse_events for event in track
        if event.command == 48
    ]
    if len(jumps) != 1 or jumps[0].values != (0, 0, 1, 1):
        raise RuntimeError("selected Monkey cue no longer has its canonical whole-cue loop")
    loop_target = (jumps[0].values[2] - 1) * 480 + jumps[0].values[3]
    sequence = import_scumm_adlib_sequence(
        sound,
        patches,
        timeline=ScummImuseTimeline(
            time_scale=125,
            minimum_note_ticks=2,
            loop_source_ticks=(loop_target, jumps[0].tick),
        ),
    )
    bank = InstrumentBank.decode(BANK.read_bytes(), str(BANK))
    for zone in bank.zones:
        sample = ROOT / zone.sample_resource
        if hashlib.sha256(sample.read_bytes()).hexdigest() != zone.sample_sha256:
            raise RuntimeError(f"reviewed sample {zone.sample_resource!r} identity differs")
    resolved = realize_scumm_adlib_notes(sequence, patches, bank)
    return sound, patches, sequence, bank, resolved


def validate(archive: Path, output: Path) -> dict[str, object]:
    provider, members = _provider(archive)
    inventory, counts = _inventory(provider)
    sound, patches, sequence, bank, resolved = monkey_church_pipeline(provider)
    cue_key = f"sound.{SELECTED_SOUND}"
    jumps = [
        event for track in sound.imuse_events for event in track
        if event.command == 48
    ]
    loop_target = (jumps[0].values[2] - 1) * 480 + jumps[0].values[3]
    rendered = render_reference(
        sequence, sample_rate=REFERENCE_RATE, voice_limit=8,
    )
    pcm = struct.unpack(f"<{rendered.frames}h", rendered.pcm_s16le)
    trace = list(sequence_trace(sequence))
    actions = [asdict(action) for action in rendered.actions]
    resolved_trace = [asdict(note) for note in resolved]
    inventory_digest = hashlib.sha256(_json_bytes(inventory)).hexdigest()
    report = {
        "schema": "same_monkey_v5_music_m4_v1",
        "source": {
            "archive": archive.name,
            "archive_size": archive.stat().st_size,
            "archive_sha256": _sha256_file(archive),
            "members": members,
        },
        "inventory": {
            "provider_key_count": len(provider.keys()),
            "sound_count": len(inventory),
            "classifications": counts,
            "records_sha256": inventory_digest,
            "records": inventory,
        },
        "selection": {
            "resource": cue_key,
            "room": 78,
            "description": "church pipe-organ cue",
            "source_sha256": sound.sha256,
            "patches": {
                str(channel): patch.fingerprint
                for channel, patch in sorted(patches.items())
            },
            "source_loop": {
                "jump_tick": jumps[0].tick,
                "target_tick": loop_target,
                "canonical_ticks": sequence.loop,
            },
            "source_time_scale": sequence.source_time_scale,
            "end_tick": sequence.end_tick,
            "attacks": len(resolved),
            "pitch_range": [
                min(note.midi_note for note in resolved),
                max(note.midi_note for note in resolved),
            ],
            "peak_polyphony": sequence.peak_polyphony(),
            "requested_polyphony": {
                str(part.part_id): part.requested_polyphony for part in sequence.parts
            },
            "bank": str(BANK.relative_to(ROOT)),
            "zones": sorted({note.zone_name for note in resolved}),
            "ir_trace_sha256": hashlib.sha256(_json_bytes(trace)).hexdigest(),
            "action_trace_sha256": hashlib.sha256(_json_bytes(actions)).hexdigest(),
            "resolved_notes_sha256": hashlib.sha256(_json_bytes(resolved_trace)).hexdigest(),
            "ir_trace": trace,
            "action_trace": actions,
            "resolved_notes": resolved_trace,
        },
        "backend": {
            "name": "same_integer_reference",
            "sample_rate": rendered.sample_rate,
            "frames": rendered.frames,
            "peak_absolute": max(map(abs, pcm)),
            "clipped_samples": sum(value in (-32768, 32767) for value in pcm),
            "pcm_sha256": hashlib.sha256(rendered.pcm_s16le).hexdigest(),
            "wav_sha256": hashlib.sha256(rendered.wav).hexdigest(),
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "monkey-sound-154-reference.wav").write_bytes(rendered.wav)
    (output / "monkey-v5-music-m4.json").write_bytes(_json_bytes(report, pretty=True))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive", type=Path, default=Path("/home/chad/_monkeypacks_backup.zip"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.archive.resolve(), args.output.resolve())
    selected = report["selection"]
    backend = report["backend"]
    print(
        f"sounds={report['inventory']['sound_count']} "
        f"classes={report['inventory']['classifications']}"
    )
    print(
        f"{selected['resource']} attacks={selected['attacks']} "
        f"peak={selected['peak_polyphony']} wav_sha256={backend['wav_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
