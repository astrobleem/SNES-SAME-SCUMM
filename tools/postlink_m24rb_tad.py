#!/usr/bin/env python3
"""Replace M24R-B's audited stock marker placeholder."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes(); marker = bytes((0x2f, 5, 0x3c, 0x3c))
    positions = [i for i in range(len(raw)) if raw.startswith(marker, i)]
    if len(positions) != 1:
        raise RuntimeError(f"M24R-B marker placeholder occurs {len(positions)} times")
    output = bytearray(raw); offset = positions[0]
    output[offset:offset + 4] = bytes((0x00, 0x08, 0x3c, 0x3c))
    args.output.write_bytes(output)
    report = {"schema":"same_m24rb_postlink_v1", "offset":offset,
              "input_sha256":hashlib.sha256(raw).hexdigest(),
              "output_sha256":hashlib.sha256(output).hexdigest(),
              "source_marker":8, "runtime_executes_source_tick":False}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    return 0
if __name__ == "__main__": raise SystemExit(main())
