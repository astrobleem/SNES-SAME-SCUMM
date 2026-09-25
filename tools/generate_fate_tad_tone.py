#!/usr/bin/env python3
"""Generate the reproducible source waveform used by the Fate TAD proof."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import struct
import wave


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rate = 32_000
    frames = 2_048
    # Additive saw with harmonics bounded below Nyquist. The duplicate-cycle
    # tail gives TAD's loop evaluator stable material without external samples.
    pcm = bytearray()
    for index in range(frames):
        phase = index * 440.0 / rate
        value = sum(math.sin(math.tau * phase * harmonic) / harmonic
                    for harmonic in range(1, 17)) * 0.38
        pcm += struct.pack("<h", max(-32767, min(32767, round(value * 32767))))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(args.output), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
