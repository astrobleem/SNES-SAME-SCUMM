#!/usr/bin/env python3
"""Validate and reassemble a completed MSU route report after a report-only bug.

This intentionally accepts only the known post-execution ``room5_entry``
local-variable failure. It does not turn emulator/runtime failures into passes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from same.engines.scumm_v5.game_analysis import canonical_json  # noqa: E402


EXPECTED_ACTIONS = (
    ("room5_rope_action", "room5 rope"),
    ("room6_books_action", "room6 books on statues"),
    ("room7_book_action", "room7 Lost Dialogue of Plato"),
    ("room7_cat118_action", "room7 object118 verb10"),
    ("room7_cat119_action", "room7 object119 verb10"),
)
EXPECTED_IDENTITIES = {
    "RoomLocalProgram(room=7,local=207)",
    "RoomLocalProgram(room=7,local=201)",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def identity_value(report: dict[str, Any], key: str) -> Any:
    value = report.get(key)
    if value is None and key == "program_directory_sha256":
        value = report.get("native_program_directory", {}).get("sha256")
    return value


def recover_completed_report(
    partial: dict[str, Any], prefix: dict[str, Any], resume: dict[str, Any],
    *, partial_sha256: str, prefix_sha256: str, resume_sha256: str,
) -> dict[str, Any]:
    failure = str(partial.get("failure", ""))
    require(partial.get("result") == "fail"
            and failure.startswith("UnboundLocalError:")
            and "room5_entry" in failure,
            "only the known post-execution room5_entry report-assembly bug is recoverable")
    for key in ("rom_sha256", "map_sha256", "build_identity_sha256",
                "archive_sha256", "program_directory_sha256"):
        require(identity_value(partial, key) == identity_value(prefix, key)
                == identity_value(resume, key),
                f"partial, cold prefix, and resume report disagree on {key}")
    require(partial.get("prefix_report_sha256") == prefix_sha256
            and resume.get("prefix_report_sha256") == prefix_sha256,
            "continuation evidence is not bound to this exact cold-prefix report")
    require(partial.get("resume_report_sha256") == resume_sha256,
            "partial continuation is not bound to its room-6 resume report")
    require(partial.get("room5_entry") == resume.get("room5_entry"),
            "room-5 lifecycle evidence differs from the hash-bound resume report")

    for room in (5, 6, 7, 3):
        entry = partial.get(f"room{room}_entry")
        require(isinstance(entry, dict)
                and entry.get("status") == "authored-room-entry-complete"
                and entry.get("final", {}).get("room") == room
                and entry.get("final", {}).get("error") == 0,
                f"room {room} lacks a completed error-free authored entry")

    action_rows = []
    for key, name in EXPECTED_ACTIONS:
        row = partial.get(key)
        require(isinstance(row, dict)
                and str(row.get("result", "")).startswith("submitted authentic")
                and int(row.get("submission_count_after", -1))
                - int(row.get("submission_count_before", -1)) == 1,
                f"{name} is not one successful controller submission")
        action_rows.append({
            "action": name,
            "before": int(row["submission_count_before"]),
            "after": int(row["submission_count_after"]),
        })
    require([row["before"] for row in action_rows] == list(range(
        action_rows[0]["before"], action_rows[0]["before"] + len(action_rows)
    )), "continuation submission counters are not contiguous")
    observed_submissions = partial.get("controller_submissions", [])
    require(len(observed_submissions) == len(action_rows)
            and all((observed.get("action"), observed.get("before"),
                     observed.get("after")) ==
                    (expected["action"], expected["before"], expected["after"])
                    for observed, expected in zip(observed_submissions, action_rows)),
            "continuation submission ledger differs from the five captured actions")

    final = partial.get("final_snapshot", {})
    require((final.get("room"), final.get("phase"), final.get("error"),
             final.get("lifecycle"), final.get("actor1_room"),
             final.get("actor1_x"), final.get("actor1_y")) ==
            (3, 0, 0, 2, 3, 71, 142),
            "native final state does not match the settled room-3 checkpoint")
    require(any(slot.get("program_unit_identity") ==
                "RoomLocalProgram(room=3,local=213)"
                and slot.get("status") not in (0, 4)
                for slot in final.get("slots", [])),
            "room-local 213 is not active at the final checkpoint")
    context = partial.get("room7_after_cat118_context", {})
    selected = context.get("selected_variables", {})
    require((selected.get("214"), selected.get("217"), selected.get("218"))
            == (1, 1, 0), "room-7 object-118 progression variables differ")
    dispatches = partial.get("room7_cat_local_dispatches", [])
    require({row.get("program_unit_identity") for row in dispatches}
            >= EXPECTED_IDENTITIES,
            "room-7 LSCR207/LSCR201 canonical dispatch evidence is incomplete")
    telemetry = partial.get("residency_summary", {})
    for key in ("stale_reference_detections", "exhaustions",
                "duplicate_program_unit_bindings"):
        require(int(telemetry.get(key, 0)) == 0,
                f"native residency safety counter {key} is nonzero")

    recovered = copy.deepcopy(partial)
    recovered.pop("failure", None)
    recovered["result"] = "pass"
    recovered["result_scope"] = "same-ROM route continuation"
    recovered["report_recovery"] = {
        "kind": "post-execution-report-assembly-only",
        "original_failure": failure,
        "source_partial_sha256": partial_sha256,
        "validated_prefix_sha256": prefix_sha256,
        "validated_resume_report_sha256": resume_sha256,
        "native_execution_complete": True,
        "checks_revalidated": [
            "ROM/map/build/archive/program-directory identity agreement",
            "room 5/6/7/3 authored lifecycle completion",
            "five continuation controller submissions, each exactly once",
            "room-7 progression variables and LSCR207/LSCR201 identities",
            "settled room-3 state and active room-local 213",
            "zero stale selector, duplicate binding, and exhaustion counters",
        ],
    }
    return recovered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partial", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--resume-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        partial_path = args.partial.resolve()
        prefix_path = args.prefix.resolve()
        resume_path = args.resume_report.resolve()
        recovered = recover_completed_report(
            json.loads(partial_path.read_text()),
            json.loads(prefix_path.read_text()),
            json.loads(resume_path.read_text()),
            partial_sha256=sha256(partial_path),
            prefix_sha256=sha256(prefix_path),
            resume_sha256=sha256(resume_path),
        )
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json(recovered))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output": str(output), "result": recovered["result"],
                      "final_room": recovered["final_snapshot"]["room"],
                      "recovered_report_sha256": sha256(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
