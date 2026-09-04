#!/usr/bin/env python3
"""Render neutral score/stem references from a Fate ROL sound.

This is deliberately not an MT-32 emulation.  It preserves source note timing,
pitch, velocity, and active-note CC7 so arrangement errors can be distinguished
from SNES timbre and sample-loop errors.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import struct
import wave

from convert_fate_sound_to_tad_mml import collect_notes, load_sound, SourceNote


def volume_at(note: SourceNote, time_us: int) -> int:
    volume = note.channel_volume
    for change_us, changed_volume in note.volume_changes:
        if change_us > time_us:
            break
        volume = changed_volume
    return volume


def render(
    notes: list[SourceNote], duration_us: int, rate: int, *, normalize: bool = False,
) -> bytes:
    frames = math.ceil(duration_us * rate / 1_000_000)
    mixed = [0.0] * frames
    # Fixed headroom keeps stems and the mix directly comparable.
    gain = 0.16 / max(1.0, math.sqrt(len(notes)))
    for note in notes:
        first = max(0, note.start_us * rate // 1_000_000)
        last = min(frames, math.ceil(note.end_us * rate / 1_000_000))
        frequency = 440.0 * 2.0 ** ((note.midi_note - 69) / 12.0)
        attack_frames = max(1, rate // 200)  # 5 ms click guard, not a new rhythm.
        release_frames = max(1, rate // 100)  # 10 ms click guard.
        for frame in range(first, last):
            elapsed = frame - first
            remaining = last - frame
            envelope = min(1.0, elapsed / attack_frames, remaining / release_frames)
            now_us = frame * 1_000_000 // rate
            dynamic = note.velocity * volume_at(note, now_us) / (127 * 127)
            phase = elapsed * frequency / rate * math.tau
            # A restrained second harmonic keeps low notes audible while remaining
            # intentionally neutral and unlike the production sample bank.
            tone = math.sin(phase) + 0.16 * math.sin(phase * 2.0)
            mixed[frame] += tone * dynamic * envelope * gain
    if normalize:
        peak = max((abs(sample) for sample in mixed), default=0.0)
        if peak:
            scale = 0.5 / peak  # -6 dBFS; preserve dynamics within this render.
            mixed = [sample * scale for sample in mixed]
    output = bytearray(frames * 2)
    for frame, sample in enumerate(mixed):
        value = max(-32767, min(32767, round(sample * 32767)))
        struct.pack_into("<h", output, frame * 2, value)
    return bytes(output)


def write_wave(path: Path, pcm: bytes, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--sound", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rate", type=int, default=44_100)
    args = parser.parse_args()
    sound = load_sound(args.archive.resolve(), args.sound)
    notes = collect_notes(sound)
    duration_us = sound.duration_us + 100_000
    write_wave(
        args.output / f"fate-sound-{args.sound}-source-neutral-mix.wav",
        render(notes, duration_us, args.rate, normalize=True), args.rate,
    )
    for program in sorted({note.program for note in notes}):
        stem = [note for note in notes if note.program == program]
        write_wave(
            args.output / f"fate-sound-{args.sound}-source-program-{program}-boosted.wav",
            render(stem, duration_us, args.rate, normalize=True), args.rate,
        )
    print(
        f"{args.output}: {len(notes)} source notes, programs "
        + ",".join(str(program) for program in sorted({note.program for note in notes}))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
