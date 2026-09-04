#!/usr/bin/env python3
"""Replace audited stock call placeholders with M22 section selectors."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--default-first", type=int, default=0)
    parser.add_argument("--alternate-first", type=int, default=8)
    parser.add_argument("--boundary-token", type=int, default=1)
    parser.add_argument("--channels", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.boundary_token <= 0x7f:
        raise RuntimeError("boundary token must fit CPUIO1's low seven bits")
    source = args.input.read_bytes()
    output = bytearray(source)
    replacements = []
    for channel in range(args.channels):
        default_id = args.default_first + channel
        alternate_id = args.alternate_first + channel
        marker = bytes((0x2f, default_id, 0x3c, 0x3c))
        positions = []
        start = 0
        while True:
            found = source.find(marker, start)
            if found < 0:
                break
            positions.append(found)
            start = found + 1
        if len(positions) != 1:
            raise RuntimeError(
                f"channel {channel} placeholder occurs {len(positions)} times, expected once"
            )
        offset = positions[0]
        replacement = bytes((0x00, default_id, alternate_id, args.boundary_token))
        output[offset:offset + 4] = replacement
        replacements.append({
            "channel": channel, "offset": offset, "stock": marker.hex(),
            "compiled_selector": replacement.hex(), "default_subroutine": default_id,
            "hook_subroutine": alternate_id,
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    report = {
        "schema": "same_m22_tad_section_postlink_v1",
        "input_sha256": sha(source), "output_sha256": sha(output),
        "boundary_token": args.boundary_token, "replacements": replacements,
        "runtime_executes_source_tick": False,
        "mechanism": "compiled TAD bytecode boundary selector",
    }
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(raw)
    print(f"input={sha(source)} output={sha(output)} selectors={len(replacements)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
