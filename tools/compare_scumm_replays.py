#!/usr/bin/env python3
"""Compare two bounded SCUMM replay reports by canonical activation identity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from same.engines.scumm_v5.game_analysis import canonical_json  # noqa: E402
from same.engines.scumm_v5.replay_differential import (  # noqa: E402
    compare_replay_reports,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", required=True, type=Path)
    parser.add_argument("--dynamic", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        static = json.loads(args.static.read_text())
        dynamic = json.loads(args.dynamic.read_text())
        result = compare_replay_reports(static, dynamic)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(result))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "output": str(args.output),
        "all_semantic_acceptance_checks_pass": result[
            "all_semantic_acceptance_checks_pass"],
        "continuation_pc_differences": len(result["continuation_pc_differences"]),
    }, sort_keys=True))
    return 0 if result["all_semantic_acceptance_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
