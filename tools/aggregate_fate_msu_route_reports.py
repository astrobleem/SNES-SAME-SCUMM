#!/usr/bin/env python3
"""Join hash-bound cold-prefix and same-ROM continuation route evidence.

The continuation may resume from an already-settled room-6 checkpoint. Keep
historical actions in that checkpoint's provenance, but count the controller
submissions actually made after the resume boundary exactly once.
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def final_of(report: dict[str, Any], key: str) -> dict[str, Any]:
    value = report.get(key)
    require(isinstance(value, dict), f"missing route checkpoint {key}")
    final = value.get("final")
    require(isinstance(final, dict), f"checkpoint {key} has no final snapshot")
    return final


def action(name: str, before: int, after: int) -> dict[str, Any]:
    return {"action": name, "before": before, "after": after,
            "submission_delta": (after - before) & 0xFF}


def build_aggregate(prefix_path: Path, continuation_path: Path) -> dict[str, Any]:
    prefix = json.loads(prefix_path.read_text(encoding="utf-8"))
    continuation = json.loads(continuation_path.read_text(encoding="utf-8"))
    require(prefix.get("rom_sha256") == continuation.get("rom_sha256"),
            "prefix and continuation use different ROM identities")
    require(prefix.get("build_identity_sha256") ==
            continuation.get("build_identity_sha256"),
            "prefix and continuation use different build identities")
    require(prefix.get("archive_sha256") == continuation.get("archive_sha256"),
            "prefix and continuation use different source archives")
    continuation_profile = continuation.get("game_profile")
    if continuation_profile is not None:
        require(prefix.get("game_profile") == continuation_profile,
                "prefix and continuation use different canonical profiles")
    require(continuation.get("prefix_report_sha256") == sha256(prefix_path),
            "continuation does not bind to the supplied cold-prefix report")
    require(continuation.get("result") == "pass",
            "same-ROM route continuation did not pass: "
            f"{continuation.get('failure', continuation.get('result'))}")

    open_action = prefix.get("room4_replay", {})
    open_before = int(open_action.get("precondition", {}).get("submissions", -1))
    open_after = int(open_action.get("final", {}).get("submissions", -1))
    use = prefix.get("room4_use_action", {})
    route_actions = [
        action("room4 Open trapdoor", open_before, open_after),
        action("room4 Use trapdoor", int(use.get("submission_count_before", -1)),
               int(use.get("submission_count_after", -1))),
    ]
    observed_actions = (
        ("room5 rope", continuation.get("room5_rope_action")),
        ("room6 books on statues", continuation.get("room6_books_action")),
        ("room7 Lost Dialogue of Plato", continuation.get("room7_book_action")),
        ("room7 object118 verb10", continuation.get("room7_cat118_action")),
        ("room7 object119 verb10", continuation.get("room7_cat119_action")),
    )
    for name, record in observed_actions:
        require(isinstance(record, dict), f"missing authored action {name}")
        route_actions.append(action(
            name, int(record.get("submission_count_before", -1)),
            int(record.get("submission_count_after", -1)),
        ))
    require(len(route_actions) == 7
            and all(row["submission_delta"] == 1 for row in route_actions),
            f"route does not contain seven single submissions: {route_actions}")
    require([row["before"] for row in route_actions] == list(range(
        route_actions[0]["before"], route_actions[0]["before"] + 7)),
        f"authored submission counters are not contiguous: {route_actions}")

    room5 = continuation.get("room5_entry", {})
    room6 = continuation.get("room6_entry", {})
    room7 = continuation.get("room7_entry", {})
    room3 = continuation.get("room3_entry", {})
    for room, entry in ((5, room5), (6, room6), (7, room7), (3, room3)):
        require(entry.get("status") == "authored-room-entry-complete"
                and entry.get("final", {}).get("room") == room
                and entry.get("final", {}).get("error") == 0,
                f"room {room} did not pass authored entry: {entry.get('status')}")

    final = continuation.get("final_snapshot")
    require(isinstance(final, dict), "continuation has no settled final snapshot")
    require((final.get("room"), final.get("phase"), final.get("error"),
             final.get("lifecycle"), final.get("actor1_room"),
             final.get("actor1_x"), final.get("actor1_y")) ==
            (3, 0, 0, 2, 3, 71, 142),
            f"final room-3 state differs from accepted checkpoint: "
            f"{ {k: final.get(k) for k in ('room','phase','error','lifecycle',
                'actor1_room','actor1_x','actor1_y')} }")
    require(any(slot.get("program_unit_identity") ==
                "RoomLocalProgram(room=3,local=213)"
                and slot.get("status") not in (0, 4)
                for slot in final.get("slots", [])),
            "room-local 213 is not active at the settled checkpoint")
    dispatches = continuation.get("room7_cat_local_dispatches", [])
    require({row.get("program_unit_identity") for row in dispatches} >= {
        "RoomLocalProgram(room=7,local=207)",
        "RoomLocalProgram(room=7,local=201)",
    }, "room-7 object verbs did not naturally dispatch LSCR207 and LSCR201")
    telemetry = final.get("residency", {})
    for key in ("stale_reference_detections", "exhaustions",
                "duplicate_program_unit_bindings"):
        require(int(telemetry.get(key, 0)) == 0,
                f"nonzero resolver safety counter {key}: {telemetry.get(key)}")

    # Compare the two builds at the same lifecycle boundary. The immediate
    # post-transition observation can be captured before the incoming ENCD has
    # settled in one build and after it has settled in the other because MSU
    # reads are asynchronous. The independently recorded authored-entry
    # completion snapshots are the canonical room checkpoints.
    checkpoints = {
        "post_use": {"final": room5["final"]},
        "post_room5_rope": {"final": room6["final"]},
        "post_room6_books": {"final": room7["final"]},
        "post_room7_book": continuation.get("checkpoints", {}).get(
            "post_room7_book"),
        "post_room7_cat118": continuation.get("checkpoints", {}).get(
            "post_room7_cat118"),
        "post_room7_cat119": {"final": room3["final"]},
    }
    for name, row in checkpoints.items():
        require(isinstance(row, dict) and isinstance(row.get("final"), dict),
                f"missing differential checkpoint {name}")
    aggregate = {
        "schema": "same-fate-msu-bounded-route-aggregate-v1",
        "result": "pass",
        "evidence_class": (
            "cold same-ROM MSU prefix plus hash-bound room-6 settled checkpoint "
            "continuation; each authored action submitted once"
        ),
        "rom_sha256": prefix.get("rom_sha256"),
        "map_sha256": prefix.get("map_sha256"),
        "build_identity_sha256": prefix.get("build_identity_sha256"),
        "archive_sha256": prefix.get("archive_sha256"),
        "game_profile": prefix.get("game_profile"),
        "program_directory_sha256": prefix.get("native_program_directory", {}).get(
            "sha256"),
        "prefix_report_sha256": sha256(prefix_path),
        "continuation_report_sha256": sha256(continuation_path),
        "continuation_resume_report_sha256": continuation.get(
            "resume_report_sha256"),
        "dynamic_residency": prefix.get("dynamic_residency"),
        "route": [0, 68, 0, 4, 5, 6, 7, 3],
        "route_actions": route_actions,
        "controller_submissions_exactly_once": True,
        **{name: {"final": row["final"]} for name, row in checkpoints.items()},
        "final_snapshot": final,
        "room_entries": {str(room): entry.get("frames_observed")
                         for room, entry in ((5, room5), (6, room6),
                                             (7, room7), (3, room3))},
        "room7_object_verb_dispatches": [
            {k: row.get(k) for k in ("program_unit_identity", "script",
                                     "binding_generation", "room")}
            for row in dispatches
        ],
        "room7_after_cat118_context": continuation.get(
            "room7_after_cat118_context"),
        "residency": telemetry,
        "semantic_execution_verified": True,
        "continuation_report_failure_reconciled": (
            "The emulator route completed. The helper's loaded process had copied "
            "the pre-resume five-action ledger and then replayed four post-room-6 "
            "actions, so only its final ledger-count assertion failed. The source "
            "now filters resume history to the one prior rope action; this report "
            "uses before/after counters from the actual seven authored actions."
        ),
    }
    return aggregate


def normalize_static_checkpoints(static_path: Path) -> dict[str, Any]:
    """Project ROM-backed observations onto the same settled room boundaries."""
    static = json.loads(static_path.read_text(encoding="utf-8"))
    require(static.get("result") == "pass", "static control is not a passing replay")
    projected = copy.deepcopy(static)
    sources = {
        "post_use": "post_transition_idle",
        "post_room5_rope": "room6_entry",
        "post_room6_books": "room7_entry",
        "post_room7_cat119": "room7_cat_result_entry",
    }
    for target, source in sources.items():
        projected[target] = {"final": final_of(static, source)}
    projected["checkpoint_normalization"] = {
        "rule": "Compare matched authored-room-entry-complete states after "
                "asynchronous room transitions; preserve immediate transition "
                "observations separately in each original replay report.",
        "source_fields": sources,
    }
    return projected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--continuation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--static", type=Path)
    parser.add_argument("--static-output", type=Path)
    args = parser.parse_args()
    try:
        result = build_aggregate(args.prefix.resolve(), args.continuation.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(result))
        if args.static is not None:
            require(args.static_output is not None,
                    "--static-output is required together with --static")
            static = normalize_static_checkpoints(args.static.resolve())
            static["checkpoint_projection_sha256"] = hashlib.sha256(
                canonical_json({key: static[key] for key in (
                    "post_use", "post_room5_rope", "post_room6_books",
                    "post_room7_book", "post_room7_cat118",
                    "post_room7_cat119", "final_snapshot",
                )})
            ).hexdigest()
            args.static_output.parent.mkdir(parents=True, exist_ok=True)
            args.static_output.write_bytes(canonical_json(static))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output": str(args.output), "result": result["result"],
                      "actions": len(result["route_actions"]),
                      "final_room": result["final_snapshot"]["room"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
