#!/usr/bin/env python3
"""Materialize the latest identity-verified native replay journal snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fate_replay_evidence import atomic_write_report, recover_latest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = recover_latest(args.journal.resolve())
        atomic_write_report(args.output.resolve(), report)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "output": str(args.output.resolve()),
        "result": report.get("result"),
        "journal_sequence": report["evidence_recovery"]["journal_sequence"],
        "provenance": report["evidence_recovery"]["provenance"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
