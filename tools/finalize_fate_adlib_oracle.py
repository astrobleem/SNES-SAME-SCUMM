#!/usr/bin/env python3
"""Turn an SDL disk-driver s16le capture into a timed Fate AdLib oracle WAV."""

from __future__ import annotations

import argparse
from array import array
import hashlib
from pathlib import Path
import wave


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample-rate", type=int, default=44_100)
    parser.add_argument("--lead-us", type=int, default=148_806)
    parser.add_argument("--tail-us", type=int, default=1_000_000)
    parser.add_argument("--tail-threshold", type=int, default=16)
    args = parser.parse_args()
    if args.sample_rate <= 0 or args.lead_us < 0 or args.tail_us < 0:
        parser.error("sample rate and timing arguments must not be negative")
    if not 0 <= args.tail_threshold <= 32767:
        parser.error("tail threshold is outside signed 16-bit PCM")

    samples = array("h")
    raw = args.raw.read_bytes()
    if len(raw) % 4:
        raise RuntimeError("capture is not complete stereo signed-16 PCM")
    samples.frombytes(raw)
    if not samples or not any(samples):
        raise RuntimeError("capture contains no audible samples")
    levels = tuple(
        max(abs(samples[index]), abs(samples[index + 1]))
        for index in range(0, len(samples), 2)
    )
    first = next(index for index, value in enumerate(levels) if value)
    last = max(
        index for index, value in enumerate(levels)
        if value >= args.tail_threshold
    )
    lead_frames = round(args.lead_us * args.sample_rate / 1_000_000)
    tail_frames = round(args.tail_us * args.sample_rate / 1_000_000)
    end = min(len(levels), last + 1 + tail_frames)
    result = array("h", (0 for _ in range(lead_frames * 2)))
    result.extend(samples[first * 2 : end * 2])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(args.output), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(args.sample_rate)
        output.writeframes(result.tobytes())
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"frames={len(result) // 2}")
    print(f"duration={len(result) / 2 / args.sample_rate:.6f}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
