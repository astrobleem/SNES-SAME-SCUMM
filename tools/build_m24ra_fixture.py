#!/usr/bin/env python3
"""Build the copyright-free M24R-A synthetic TAD fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import wave


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_tone(path: Path) -> None:
    rate = 32_000
    frames = 3_200
    pcm = bytearray()
    for index in range(frames):
        phase = index * 440.0 / rate
        value = sum(math.sin(math.tau * phase * harmonic) / harmonic for harmonic in range(1, 9))
        value *= 0.22
        pcm += struct.pack("<h", max(-32767, min(32767, round(value * 32767))))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compiler, output = args.compiler.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    tone = ROOT / "build/m24ra/synthetic-layer-tone.wav"
    write_tone(tone)
    project = ROOT / "audio/m24ra/m24ra.terrificaudio"
    subprocess.run([
        str(compiler), "asar-export", "--lorom",
        "--output-asm", str(output / "tad.asm"),
        "--output-bin", str(output / "tad.bin"),
        "--output-inc", str(output / "tad.inc"),
        str(project),
    ], cwd=ROOT, check=True)
    assembly = (output / "tad.asm").read_text(encoding="utf-8")
    if "m24ra_async_layer_transition" not in (output / "tad.inc").read_text(encoding="utf-8"):
        raise RuntimeError("synthetic song missing from compiler output")
    report = {
        "schema": "same_m24ra_fixture_v1",
        "project_sha256": digest(project),
        "mml_sha256": digest(ROOT / "audio/m24ra/m24ra_async_layer_transition.mml"),
        "tone_sha256": digest(tone),
        "compiler_sha256": digest(compiler),
        "tad_bin_sha256": digest(output / "tad.bin"),
        "tad_bin_bytes": (output / "tad.bin").stat().st_size,
        "contains_audio_driver": "Tad_AudioDriver" in assembly,
        "group_a_long_note_ticks": 4000,
        "admission_ticks": [19, 38, 63, 94, 125],
        "admission_voices": [7, 6, 5, 4, 3],
        "fade_ticks": 256,
        "tick_hz": 125,
    }
    (output / "fixture-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
