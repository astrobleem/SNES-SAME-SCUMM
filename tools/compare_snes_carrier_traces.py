#!/usr/bin/env python3
"""Compare target-neutral M25 checkpoints from two production carriers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FINAL_FIELDS = (
    "frame",
    "logical_tick",
    "engine_lifecycle",
    "engine_frame_busy",
    "scumm_status",
    "last_opcode",
    "program",
    "pc",
    "active_room",
    "scumm_current_room",
    "movement_tick",
    "wait_blocks",
    "wait_releases",
    "actor",
    "get_dist",
    "start_object",
    "slots",
    "message_state",
    "audio_packet_count",
    "dma",
)


def normalized(report: dict[str, object]) -> dict[str, object]:
    final = report["final"]
    assert isinstance(final, dict)
    return {key: final.get(key) for key in FINAL_FIELDS if key in final}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ordinary", type=Path)
    parser.add_argument("sa1", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ordinary = json.loads(args.ordinary.read_text(encoding="utf-8"))
    sa1 = json.loads(args.sa1.read_text(encoding="utf-8"))
    left = normalized(ordinary)
    right = normalized(sa1)
    differences = {
        key: {"ordinary": left.get(key), "sa1_bwram": right.get(key)}
        for key in sorted(set(left) | set(right))
        if left.get(key) != right.get(key)
    }
    result = {
        "format": "same-snes-cross-carrier-m25",
        "version": 1,
        "result": "pass" if not differences else "fail",
        "ordinary_rom_sha256": ordinary["rom_sha256"],
        "sa1_rom_sha256": sa1["rom_sha256"],
        "compared": left,
        "excluded_carrier_policy": (
            "ROM header/checksum, carrier ID, BW-RAM control block, and CPU cycle count"
        ),
        "differences": differences,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if differences:
        raise RuntimeError(f"cross-carrier M25 divergence: {sorted(differences)}")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
