#!/usr/bin/env python3
"""Compare target-neutral Phase 6F semantics across production carriers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalized(report: dict[str, object]) -> dict[str, object]:
    semantics = dict(report["semantics"])
    return {
        "immediate": {key: value for key, value in dict(report["immediate"]).items() if key != "frame"},
        "published": {key: value for key, value in dict(report["published"]).items() if key != "frame"},
        "semantics": semantics,
        "next_blocker": report["next_blocker"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs=3, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    reports = [json.loads(path.read_text()) for path in args.reports]
    normalized_reports = [normalized(report) for report in reports]
    baseline = normalized_reports[0]
    differences = {
        str(args.reports[index]): current
        for index, current in enumerate(normalized_reports[1:], 1)
        if current != baseline
    }
    output = {
        "format": "same-phase6f-cross-carrier-camera",
        "version": 1,
        "result": "pass" if not differences else "fail",
        "roms": [{"path": str(path), "sha256": reports[index]["rom_sha256"]}
                 for index, path in enumerate(args.reports)],
        "compared": baseline,
        "excluded": ["host/emulator frame number", "header/checksum", "carrier/backend state"],
        "differences": differences,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    if differences:
        raise RuntimeError(f"Phase 6F cross-carrier divergence: {sorted(differences)}")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
