#!/usr/bin/env python3
"""Wrap and segment the pinned ScummVM/Nuked sound-154 patch capture."""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
from pathlib import Path
import wave


RATE = 44_100
CHANNELS = (9, 1, 2, 4, 5, 6)
# Measured onsets from the SDL disk capture. Its audio clock advances faster
# than ScummVM's wall-clock delay calls, so nominal 1.5/8.5-second scheduling
# must not be used to cut the listener files.
CUTS_SECONDS = (0.70, 7.80, 14.90, 22.00, 29.10, 35.90, 43.24)
NOTES = "C2, C3, C4, C5, C6; one-second attacks with release gaps"


def write_wave(path: Path, pcm: bytes, rate: int = RATE) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def split_capture(raw: bytes, output_dir: Path) -> list[dict[str, object]]:
    if len(raw) % 4:
        raise ValueError("capture is not complete stereo signed-16 PCM")
    samples = array("h")
    samples.frombytes(raw)
    if not samples or not any(samples):
        raise ValueError("capture is silent")
    frames = len(samples) // 2
    required = round(CUTS_SECONDS[-1] * RATE)
    if frames < required - RATE // 20:
        raise ValueError("capture ends before the final audition tail")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_wave(output_dir / "fate-sound154-all-adlib-patches-nuked.wav", raw)
    captures: list[dict[str, object]] = []
    for index, channel in enumerate(CHANNELS):
        first = round(CUTS_SECONDS[index] * RATE)
        last = min(frames, round(CUTS_SECONDS[index + 1] * RATE))
        pcm = raw[first * 4:last * 4]
        name = f"{index + 1:02d}_patch{index:02d}_ch{channel:02d}_scale.wav"
        write_wave(output_dir / name, pcm)
        captures.append({
            "file": name,
            "patch": index,
            "source_channel": channel,
            "notes": NOTES,
            "frames": last - first,
            "seconds": round((last - first) / RATE, 3),
            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        })
    return captures


def write_review(path: Path, captures: list[dict[str, object]]) -> None:
    lines = [
        "# Fate sound 154 — isolated Nuked-OPL patch review", "",
        "Listen for timbre, pitch, attack/release, and whether any octave becomes strained.",
        "These are the original AdLib definitions, not the current SNES sample bank.", "",
    ]
    for capture in captures:
        lines.extend((
            f"## {capture['file']}", "",
            f"Original iMUSE channel {capture['source_channel']}; {capture['notes']}", "",
            "- [ ] pass", "- [ ] wrong timbre", "- [ ] low strained",
            "- [ ] high strained", "- [ ] transition audible",
            "- [ ] out of tune", "- [ ] bad release/tail", "- Notes:", "", "---", "",
        ))
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raw = args.raw.read_bytes()
    captures = split_capture(raw, args.output)
    report = {
        "gate": "Fate-S6-sound154-isolated-AdLib-patches",
        "renderer": "ScummVM SCUMM iMUSE + Nuked OPL",
        "format": "stereo signed-16 PCM, 44100 Hz",
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "captures": captures,
    }
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    write_review(args.output / "REVIEW.md", captures)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
