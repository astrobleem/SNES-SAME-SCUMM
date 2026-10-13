#!/usr/bin/env python3
"""Generate a deterministic copyright-free full-source bank-layout fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from examples.resources.scumm_v5.game_analysis_fixture import source_zip


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extra-global-scripts", type=int, default=180)
    parser.add_argument("--cross-bank-body-size", type=lambda value: int(value, 0),
                        default=0x7FFC)
    parser.add_argument("--data-only-objects", type=int, default=64)
    args = parser.parse_args()
    payload = source_zip(
        data_only_objects=args.data_only_objects,
        extra_global_scripts=args.extra_global_scripts,
        cross_bank_body_size=args.cross_bank_body_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and args.output.read_bytes() != payload:
        raise SystemExit(
            f"refusing to replace a different existing fixture archive: {args.output}"
        )
    args.output.write_bytes(payload)
    marker_body = bytes((0x1A, 200, 0, 0x5A, 0xA5, 0xA0))
    report = {
        "schema": "same_scumm_v5_whole_source_layout_fixture_v1",
        "archive_sha256": hashlib.sha256(payload).hexdigest(),
        "selector_units_expected_lower_bound": args.extra_global_scripts + 11,
        "extra_global_scripts": args.extra_global_scripts,
        "data_only_objects": args.data_only_objects,
        "large_program": "GlobalProgram(6)",
        "large_program_bytes": args.cross_bank_body_size,
        "marker_program": "GlobalProgram(7)",
        "marker_program_sha256": hashlib.sha256(marker_body).hexdigest(),
        "marker_variable": 200,
        "marker_value": 0xA55A,
    }
    report_path = args.output.with_suffix(args.output.suffix + ".json")
    report_payload = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if report_path.exists() and report_path.read_text(encoding="utf-8") != report_payload:
        raise SystemExit(
            f"refusing to replace a different existing fixture manifest: {report_path}"
        )
    report_path.write_text(report_payload, encoding="utf-8")
    print(json.dumps({"archive": str(args.output), "report": str(report_path), **report},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
