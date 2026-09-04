#!/usr/bin/env python3
"""Build Monkey v5 church through SAME's generic sampled TAD backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from same.music import SampledNote, TadInstrument, TadPanPolicy, compile_tad_mml
from validate_monkey_v5_music import (
    BANK, ROOT, SELECTED_SOUND, _provider, _sha256_file, monkey_church_pipeline,
)


DEFAULT_COMPILER = ROOT.parent / "terrific-audio-driver/target/release/tad-compiler"
BASE_PROJECT = ROOT / "audio/fate_s6/fate.terrificaudio"
FATE_AUDIO = ROOT / "audio/fate_s6"
PROJECT_NAME = "monkey_m5_church"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _portable_sources(project: dict[str, object], project_dir: Path) -> None:
    for instrument in project["instruments"]:
        source = Path(instrument["source"])
        instrument["source"] = os.path.relpath((FATE_AUDIO / source).resolve(), project_dir)
    for song in project["songs"]:
        song["source"] = os.path.relpath(
            (FATE_AUDIO / song["source"]).resolve(), project_dir,
        )


def build(archive: Path, output: Path, compiler: Path) -> dict[str, object]:
    provider, members = _provider(archive)
    sound, patches, sequence, bank, resolved = monkey_church_pipeline(provider)
    sampled = tuple(SampledNote(
        note.start, note.end, note.midi_note, note.volume, note.zone_name,
        note.part_id, note.note_id, note.volume_changes,
    ) for note in resolved)
    song = compile_tad_mml(
        sequence,
        sampled,
        (
            TadInstrument("monkey154_organ_low", "mt32_p13_low"),
            TadInstrument("monkey154_organ_main", "mt32_p13"),
        ),
        title="Monkey v5 church generic sampled arrangement",
        author="SAME M5 generic sampled backend",
        pan_policy=TadPanPolicy.STEREO_CC10,
    )
    output.mkdir(parents=True, exist_ok=True)
    mml_path = output / "monkey_sound_154.mml"
    mml_path.write_text(song.mml, encoding="utf-8", newline="\n")

    project = json.loads(BASE_PROJECT.read_text(encoding="utf-8"))
    _portable_sources(project, output)
    project["_about"]["_comment"] = (
        "Generated M5 validation project; commercial-derived MML remains under build/."
    )
    project["instruments"].extend((
        {
            "name": "mt32_p13_low",
            "source": os.path.relpath(
                (ROOT / bank.zone("monkey154_organ_low").sample_resource).resolve(), output,
            ),
            "freq": 131.148,
            "loop": "loop_with_filter",
            "loop_setting": 4160,
            "evaluator": "default",
            "ignore_gaussian_overflow": False,
            "first_octave": 2,
            "last_octave": 3,
            "envelope": "adsr 15 1 7 0",
        },
        {
            "name": "mt32_p13",
            "source": os.path.relpath(
                (ROOT / bank.zone("monkey154_organ_main").sample_resource).resolve(), output,
            ),
            "freq": 592.593,
            "loop": "loop_with_filter",
            "loop_setting": 5120,
            "evaluator": "default",
            "ignore_gaussian_overflow": False,
            "first_octave": 3,
            "last_octave": 6,
            "envelope": "adsr 15 1 7 0",
        },
    ))
    project["songs"].append({"name": PROJECT_NAME, "source": mml_path.name})
    project_path = output / "monkey-m5.terrificaudio"
    project_path.write_text(
        json.dumps(project, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )

    if not compiler.is_file():
        raise RuntimeError(f"TAD compiler is unavailable: {compiler}")
    asm_path = output / "tad.asm"
    bin_path = output / "tad.bin"
    inc_path = output / "tad.inc"
    subprocess.run((
        str(compiler), "asar-export", "--lorom",
        "--output-asm", str(asm_path),
        "--output-bin", str(bin_path),
        "--output-inc", str(inc_path),
        str(project_path),
    ), check=True)
    enums = inc_path.read_text(encoding="utf-8")
    match = re.search(rf"^\s*!Song_{PROJECT_NAME}\s*=\s*(\d+)\s*$", enums, re.MULTILINE)
    if match is None or int(match.group(1)) != 26:
        raise RuntimeError("M5 compiled song ID differs from the appended project contract")
    report = {
        "schema": "same_monkey_v5_tad_m5_v1",
        "archive_sha256": _sha256_file(archive),
        "members": members,
        "source_resource": f"sound.{SELECTED_SOUND}",
        "source_sha256": sound.sha256,
        "patches": {str(channel): patch.fingerprint for channel, patch in patches.items()},
        "bank": str(BANK.relative_to(ROOT)),
        "pan_policy": song.pan_policy.value,
        "loop": song.loop,
        "tick_bias": song.tick_bias,
        "release_adjustments": list(song.release_adjustments),
        "release_adjustment_count": len(song.release_adjustments),
        "attacks": len(sampled),
        "voices": song.voice_count,
        "mml_sha256": _sha(mml_path),
        "mml_bytes": mml_path.stat().st_size,
        "project_sha256": _sha(project_path),
        "compiled_song_id": 26,
        "tad_binary_sha256": _sha(bin_path),
        "tad_binary_bytes": bin_path.stat().st_size,
        "tad_enums_sha256": _sha(inc_path),
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive", type=Path, default=Path("/home/chad/_monkeypacks_backup.zip"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, default=DEFAULT_COMPILER)
    args = parser.parse_args()
    report = build(args.archive.resolve(), args.output.resolve(), args.compiler.resolve())
    print(
        f"attacks={report['attacks']} voices={report['voices']} "
        f"song={report['compiled_song_id']} mml_sha256={report['mml_sha256']}"
    )
    print(
        f"tad_bytes={report['tad_binary_bytes']} "
        f"tad_sha256={report['tad_binary_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
