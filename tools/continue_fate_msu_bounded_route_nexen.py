#!/usr/bin/env python3
"""Continue the established DOS-CD FATE route from its ROM-bound room-5 state.

This is an integration harness, not a gameplay explorer.  It consumes the
room-5 checkpoint produced by the existing cold replay after the two room-4
sentences have each been submitted once, then uses the same authored replay
helpers through room 3.  The checkpoint, ROM, build identity, package, and
prefix report are all hash-bound; no state is transplanted between builds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    state_group = parser.add_mutually_exclusive_group(required=True)
    state_group.add_argument("--room5-state", type=Path)
    state_group.add_argument("--room6-state", type=Path)
    state_group.add_argument("--room6-entry-state", type=Path)
    parser.add_argument(
        "--resume-report", type=Path,
        help="same-ROM prior continuation report that owns a room-6 checkpoint",
    )
    parser.add_argument(
        "--room5-entry-report", type=Path,
        help="reuse a same-ROM report and saved state proving room-5 entry already settled",
    )
    parser.add_argument("--prefix-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/ATLANTIS.zip"))
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44980)
    parser.add_argument("--room-entry-frames", type=int, default=60000)
    parser.add_argument("--room-action-frames", type=int, default=12000)
    parser.add_argument("--checkpoint-dir", type=Path)
    args = parser.parse_args()

    rom = args.rom.resolve()
    state_path = (
        args.room5_state or args.room6_state or args.room6_entry_state
    ).resolve()
    resume_report_path = args.resume_report.resolve() if args.resume_report else None
    prefix_path = args.prefix_report.resolve()
    entry_report_path = (
        args.room5_entry_report.resolve() if args.room5_entry_report else None
    )
    archive = args.archive.resolve()
    nexen = args.nexen.resolve()
    if (args.room6_state or args.room6_entry_state) and resume_report_path is None:
        parser.error("room-6 checkpoints require their same-ROM --resume-report")
    if args.room5_state and resume_report_path is not None:
        parser.error("--resume-report is only valid with a room-6 checkpoint")
    if (args.room6_state or args.room6_entry_state) and entry_report_path is not None:
        parser.error("--room5-entry-report is only valid with --room5-state")
    required_paths = [rom, state_path, prefix_path, archive, nexen]
    if entry_report_path is not None:
        required_paths.append(entry_report_path)
    if resume_report_path is not None:
        required_paths.append(resume_report_path)
    for path in required_paths:
        if not path.is_file():
            parser.error(f"required input does not exist: {path}")
    if args.room_entry_frames <= 0 or args.room_action_frames <= 0:
        parser.error("room entry/action bounds must be positive")

    rom_sha = sha256(rom)
    state_sha = sha256(state_path)
    prefix = json.loads(prefix_path.read_text())
    if prefix.get("rom_sha256") != rom_sha:
        parser.error("prefix replay report belongs to another ROM")
    prior_entry_report = (
        json.loads(entry_report_path.read_text())
        if entry_report_path is not None else None
    )
    resume_report = (
        json.loads(resume_report_path.read_text())
        if resume_report_path is not None else None
    )
    if prior_entry_report is not None:
        prior_entry = prior_entry_report.get("room5_entry", {})
        prior_checkpoint = prior_entry_report.get("room5_state_after_entry", {})
        if prior_entry_report.get("rom_sha256") != rom_sha:
            parser.error("room-5 entry report belongs to another ROM")
        if prior_entry.get("status") != "authored-room-entry-complete":
            parser.error("room-5 entry report does not prove completed authored entry")
        if prior_checkpoint.get("rom_sha256") != rom_sha:
            parser.error("room-5 entry checkpoint report has a different ROM identity")
        prior_state_path = Path(prior_checkpoint.get("path", "")).resolve()
        if prior_state_path != state_path:
            parser.error("room-5 state is not the checkpoint bound by the entry report")
    if resume_report is not None:
        if resume_report.get("prefix_report_sha256") != sha256(prefix_path):
            parser.error("room-6 resume report is not bound to this cold-prefix report")
        checkpoint_key = (
            "room6_state_after_entry" if args.room6_entry_state
            else "room6_checkpoint_after_rope"
        )
        checkpoint = resume_report.get(checkpoint_key, {})
        if resume_report.get("rom_sha256") != rom_sha:
            parser.error("room-6 resume report belongs to another ROM")
        if Path(checkpoint.get("path", "")).resolve() != state_path:
            parser.error("room-6 state is not owned by the resume report")
        if checkpoint.get("rom_sha256") != rom_sha:
            parser.error("room-6 checkpoint report has a different ROM identity")
        if resume_report.get("result") not in ("running", "fail"):
            parser.error("room-6 resume report is not a retained partial continuation")
        saved_rope = resume_report.get("room5_rope_action", {})
        saved_post_rope = resume_report.get("checkpoints", {}).get(
            "post_room5_rope", {}
        )
        if (not saved_rope.get("result", "").startswith("submitted authentic")
                or saved_post_rope.get("status") != "room-transition"
                or saved_post_rope.get("final", {}).get("room") != 6):
            parser.error("resume report does not prove the single room-5 rope transition")
        if args.room6_entry_state:
            saved_entry = resume_report.get("room6_entry", {})
            if (saved_entry.get("status") != "authored-room-entry-complete"
                    or saved_entry.get("final", {}).get("room") != 6):
                parser.error("room-6 entry checkpoint lacks its settled lifecycle evidence")
    identity_path = rom.with_suffix(".build_identity.json")
    listing_path = rom.with_suffix(".lst")
    map_path = rom.with_suffix(".map")
    for path in (identity_path, listing_path, map_path):
        if not path.is_file():
            parser.error(f"ROM-bound sidecar is missing: {path}")
    identity = json.loads(identity_path.read_text())
    explicit = identity.get("explicit_environment", {})
    if (explicit.get("SAME_BUILD_SCUMM_DYNAMIC_FATE_EXPERIMENT") != "1"
            or explicit.get("SAME_FATE_PROFILE") !=
            "examples/profiles/templates/fate_of_atlantis_dos_cd.json"
            or explicit.get("SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES") != "1"):
        parser.error("checkpoint continuation requires the canonical dynamic DOS-CD MSU build")
    if identity.get("rom", {}).get("sha256") != rom_sha:
        parser.error("ROM bytes do not match their adjacent build identity")

    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import fate_replay
    import replay_fate_room4_cold_nexen as replay
    import mesen_mcp.session as mesen_session
    from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom
    from validate_scumm_native_residency_nexen import (
        check_live_room_native, check_live_room_ppu,
        live_room_presentation_diagnostics, live_room_ppu_generation_ready,
        live_room_ppu_status, msu_program_diagnostics,
    )

    replay.ACTIVE_DYNAMIC_RESIDENCY = True
    replay.ACTIVE_MSU_PROGRAMS = True
    replay.ACTIVE_LIVE_ROOM_RESOURCES = True
    replay.ACTIVE_PROGRAM_DIRECTORY = replay._native_directory_for_build(
        identity_path
    )["by_id"]
    replay.RESIDENCY_OBSERVER_READY = True
    replay.RESIDENCY_PREINIT_UNKNOWN_ROWS = 0
    replay.RESIDENCY_POSTINIT_UNKNOWN_ROWS.clear()
    replay.RESIDENCY_EVENTS.clear()
    replay.RESIDENCY_LAST.clear()
    replay.RESIDENCY_HISTORY.clear()
    replay.RESIDENCY_PINNED_PEAK = 0

    # Room-entry polling sends no ordinary controller input. A pending talk
    # generation remains owned by the engine until its explicit synchronized
    # acknowledgement, so bounded passive batches reduce debugger overhead
    # without merging or consuming authored submissions.
    replay._bounded_observation_step = (
        lambda start, current, maximum, *, chunk=4:
        min(128, max(0, maximum - (current - start)))
    )

    listing = listing_path.read_text()
    variable_layout = replay._parse_rom_variable_layout(listing)
    rom_symbols: dict[str, int] = {}
    for line in listing.splitlines():
        match = re.match(
            r"; ([A-Z][A-Z0-9_]*) = \$([0-9A-Fa-f]+)\s+\(Constant\)$", line,
        )
        if match:
            rom_symbols[match.group(1)] = int(match.group(2), 16)
    if "SAME_VIDEO_SURFACE_STATE" not in rom_symbols:
        parser.error("ROM listing lacks the live surface state descriptor")
    control_addresses = [
        int(line.split("= $", 1)[1].split()[0], 16)
        for line in listing.splitlines()
        if line.startswith("; SAME_SCUMM_LIVE_ROOM_CONTROL = $")
        and line.endswith("(Constant)")
    ]
    if len(control_addresses) != 1:
        parser.error("ROM listing must define one live-room control address")
    replay.LIVE_ROOM_CONTROL_ADDRESS = control_addresses[0]

    storage_root = Path(explicit["SAME_SCUMM_MSU1_PROGRAM_STORAGE_DIR"])
    if not storage_root.is_absolute():
        storage_root = ROOT / storage_root
    storage_manifest_path = storage_root / "program-storage.json"
    storage_package = storage_root / "scumm-programs.msu"
    storage_manifest = json.loads(storage_manifest_path.read_text())
    live_inputs = {
        "program_storage": storage_manifest,
        "program_storage_package": {"path": str(storage_package)},
        "rom_path": str(rom),
        "build_identity": identity,
        "rom_symbols": rom_symbols,
    }
    symbols = {
        "Same_Input_Poll__edge_sequence_done": 0,
        "Same_Input_Poll": 0,
        "ScummV5_Talk_FrameBegin_Far": 9,
        "ScummV5_Talk_FrameBegin_Far__publish": 9,
        "ScummV5_Controller_Frame_Far": 9,
        "ScummV5_Controller_Frame__generic_ready": 9,
        "ScummV5_Controller_Frame__select_verb_a_pressed": 9,
        "ScummV5_Controller_Frame__done": 9,
        "ScummV5_Talk_FrameEnd_Far": 9,
        "ScummV5_Talk_FrameEnd_Far__done": 9,
        "ScummV5_Resident_Reset_Far": 9,
    }
    output: dict[str, Any] = {
        "result": "running",
        "evidence_class": (
            "same-ROM continuation of the accepted cold dynamic route; "
            "room4 actions are already represented once in prefix"
        ),
        "rom_sha256": rom_sha,
        "map_sha256": sha256(map_path),
        "build_identity_sha256": sha256(identity_path),
        "program_directory_sha256": replay._native_directory_for_build(
            identity_path
        )["sha256"],
        "room5_state_sha256": state_sha,
        "resume_report_sha256": (
            sha256(resume_report_path) if resume_report_path is not None else None
        ),
        "prefix_report_sha256": sha256(prefix_path),
        "room5_entry_report_sha256": (
            sha256(entry_report_path) if entry_report_path is not None else None
        ),
        "archive_sha256": sha256(archive),
        "starting_head": identity.get("git", {}).get("head"),
        "prefix_actions": {
            "room4_open_submission": prefix["room4_replay"]["final"]["submissions"],
            "room4_use_submission": prefix["room4_use_action"]["submission_count_after"],
            "room5_start_submission_count": prefix["post_transition_idle"]["final"]["submissions"],
        },
        "room_observations": {},
        "controller_submissions": [],
        "checkpoints": {},
    }
    mesen_session.validate_mesen_build = lambda _path: None
    session_owner = mesen_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=300.0,
        stderr_log=args.output.with_suffix(".stderr.log"),
    )

    def pulse(session: Any, mask: int, predicate: Any) -> dict[str, Any]:
        return fate_replay.room4_synchronous_input_edge(
            session, mask, predicate, poll_interval_frames=2,
            poll_boundary_address=mapped_cpu_address_for_rom(
                rom, "Same_Input_Poll__edge_sequence_done", bank=0,
            ),
            pre_press_poll_boundary_address=mapped_cpu_address_for_rom(
                rom, "Same_Input_Poll", bank=0,
            ),
        )

    def record_room(session: Any, room: int) -> dict[str, Any]:
        consumption = check_live_room_native(session, live_inputs, room)
        target_generation = replay._u16(
            session, rom_symbols["SAME_VIDEO_SURFACE_STATE"] + 0x1C,
        )
        ready = live_room_ppu_generation_ready(
            session, live_inputs, target_generation,
        )
        frame = int(session.get_state()["frameCount"])
        metrics = msu_program_diagnostics(session, live_inputs)
        presentation = {
            "frame": frame,
            "status": live_room_ppu_status(session, live_inputs),
            "diagnostics": live_room_presentation_diagnostics(session, live_inputs),
            "target_generation": target_generation,
            "full_vram_match_checked": ready,
            "full_vram_check": (
                check_live_room_ppu(
                    session, live_inputs, room, target_generation,
                ) if ready else None
            ),
        }
        result = {
            "external_resource_consumption": consumption,
            "presentation_at_checkpoint": presentation,
            "load_metrics": {
                "frame": frame,
                "room_resource": metrics["room_resource"],
                "bytes_read_total": metrics["bytes_read"],
                "bytecode_cache_current_bytes": metrics["cache_current_bytes"],
                "bytecode_cache_peak_bytes": metrics["cache_peak_bytes"],
                "bytecode_page_loads": metrics["cache_loads"],
            },
        }
        output["room_observations"][str(room)] = result
        atomic_report(args.output.resolve(), output)
        return result

    def observe_action(
        session: Any, *, name: str, baseline: int, baseline_slots: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = replay._observe_action(
            session, baseline=baseline, max_frames=args.room_action_frames,
            rom=rom, symbol_banks=symbols, baseline_slots=baseline_slots,
            capture_execution_trace=True,
            variable_base=variable_layout["base"],
            variable_count=variable_layout["count"],
            object_count=variable_layout["object_count"],
        )
        output["checkpoints"][name] = result
        atomic_report(args.output.resolve(), output)
        return result

    try:
        with session_owner as session:
            session.pause()
            output["state_load"] = session.load_state(state_path)
            session.pause()
            expected_submissions = int(output["prefix_actions"]["room5_start_submission_count"])
            if args.room6_state:
                start = replay._snapshot(session)
                output["room6_checkpoint_before_entry"] = start
                checkpoint = resume_report["room6_checkpoint_after_rope"]
                expected_after_rope = (expected_submissions + 1) & 0xFF
                # This checkpoint is deliberately taken at the incoming-room
                # lifecycle boundary: room=6 is requested, but actor ownership
                # remains room 5 until validated room-6 publication commits.
                if (start["room"], start["phase"], start["error"],
                        start["submissions"]) != (6, 0, 0, expected_after_rope):
                    summary = {
                        key: start.get(key) for key in
                        ("frame", "room", "phase", "error", "actor1_room",
                         "pending_room", "submissions")
                    }
                    raise RuntimeError(
                        "room6 resume state does not match its route prefix: "
                        f"{summary!r}"
                    )
                if start["frame"] != checkpoint.get("frame"):
                    raise RuntimeError("room6 saved state frame differs from its owner report")
                room5_entry = resume_report.get("room5_entry")
                rope = resume_report["room5_rope_action"]
                post_rope = resume_report["checkpoints"]["post_room5_rope"]
                output["room5_entry"] = room5_entry
                output["room5_rope_action"] = rope
                output["checkpoints"]["post_room5_rope"] = post_rope
                output["room6_checkpoint_after_rope"] = checkpoint
                output["controller_submissions"] = [
                    row for row in resume_report.get("controller_submissions", [])
                    if row.get("action") == "room5 rope"
                ]
            elif args.room6_entry_state:
                start = replay._snapshot(session)
                output["room6_checkpoint_before_books"] = start
                checkpoint = resume_report["room6_state_after_entry"]
                expected_after_rope = (
                    int(output["prefix_actions"]["room5_start_submission_count"]) + 1
                ) & 0xFF
                if (start["room"], start["phase"], start["error"],
                        start["actor1_room"], start["submissions"]) != (
                        6, 0, 0, 6, expected_after_rope):
                    raise RuntimeError(
                        "room6 settled resume state does not match its route prefix: "
                        f"{ {key: start.get(key) for key in ('frame','room','phase',
                            'error','actor1_room','submissions')}!r}"
                    )
                if start["frame"] != checkpoint.get("frame"):
                    raise RuntimeError(
                        "room6 settled state frame differs from its owner report"
                    )
                room5_entry = resume_report.get("room5_entry")
                output["room5_entry"] = room5_entry
                output["room5_rope_action"] = resume_report["room5_rope_action"]
                output["checkpoints"]["post_room5_rope"] = resume_report[
                    "checkpoints"]["post_room5_rope"]
                output["room6_checkpoint_after_rope"] = resume_report[
                    "room6_checkpoint_after_rope"]
                output["room6_entry"] = resume_report["room6_entry"]
                output["room6_state_after_entry"] = checkpoint
                output["room_observations"]["6"] = resume_report[
                    "room_observations"]["6"]
                output["controller_submissions"] = [
                    row for row in resume_report.get("controller_submissions", [])
                    if row.get("action") == "room5 rope"
                ]
            else:
                start = replay._snapshot(session)
                output["room5_checkpoint_before_entry"] = start
                if (start["room"], start["phase"], start["error"], start["actor1_room"],
                        start["submissions"], start["actor1_x"], start["actor1_y"]) != (
                        5, 0, 0, 5, expected_submissions, 145, 134):
                    raise RuntimeError(f"room5 state does not match the cold prefix: {start!r}")

                if prior_entry_report is None:
                    room5_entry = replay._observe_no_input_lifecycle(
                        session, rom=rom, symbol_banks=symbols, archive=archive,
                        variable_base=variable_layout["base"],
                        variable_count=variable_layout["count"],
                        object_count=variable_layout["object_count"],
                        max_frames=args.room_entry_frames,
                    )
                else:
                    room5_entry = prior_entry_report["room5_entry"]
                    prior_final = room5_entry["final"]
                    current = replay._snapshot(session)
                    for key in (
                        "room", "phase", "error", "lifecycle", "actor1_room",
                        "actor1_x", "actor1_y", "submissions",
                    ):
                        if prior_final.get(key) != current.get(key):
                            raise RuntimeError(
                                "same-ROM settled room-5 checkpoint disagrees with its "
                                f"entry report at {key}: {current.get(key)!r} != "
                                f"{prior_final.get(key)!r}"
                            )
                    room5_entry = dict(room5_entry)
                    room5_entry["evidence_reused_from_report_sha256"] = sha256(
                        entry_report_path
                    )
                output["room5_entry"] = room5_entry
                if room5_entry.get("status") != "authored-room-entry-complete":
                    raise RuntimeError(
                        f"room5 authored entry did not settle: "
                        f"{replay._room_entry_failure_summary(room5_entry)!r}"
                    )
                if room5_entry["final"]["submissions"] != expected_submissions:
                    raise RuntimeError("room5 entry message acknowledgements submitted a sentence")
                record_room(session, 5)
                if args.checkpoint_dir:
                    checkpoint_path = args.checkpoint_dir.resolve() / "room5-entry-complete.state"
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    output["room5_state_after_entry"] = {
                        "path": str(checkpoint_path), "rom_sha256": rom_sha,
                        "save_result": session.save_state(checkpoint_path),
                    }

                before_slots = replay._snapshot(session)["slots"]
                rope = fate_replay.replay_room5_rope_to_room6(
                    # The streamed checkpoint's cursor is on the even two-pixel
                    # lattice (124,30). The authenticated object77 rectangle is
                    # [224,264) x [120,128), so (224,124) is reachable.
                    session, pulse=pulse, expected_cursor=None, target=(224, 124),
                    diagonal_navigation=True,
                )
                if rope["submission_count_after"] != ((rope["submission_count_before"] + 1) & 0xFF):
                    raise RuntimeError(f"room5 rope did not submit exactly once: {rope!r}")
                output["controller_submissions"].append({
                    "action": "room5 rope", "before": rope["submission_count_before"],
                    "after": rope["submission_count_after"],
                })
                output["room5_rope_action"] = rope
                post_rope = observe_action(
                    session, name="post_room5_rope",
                    baseline=rope["submission_count_before"], baseline_slots=before_slots,
                )
                if post_rope["status"] != "room-transition" or post_rope["final"]["room"] != 6:
                    raise RuntimeError(f"room5 rope did not reach room6: {post_rope!r}")
                if args.checkpoint_dir:
                    checkpoint_path = args.checkpoint_dir.resolve() / "room6-after-rope.state"
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    output["room6_checkpoint_after_rope"] = {
                        "path": str(checkpoint_path), "rom_sha256": rom_sha,
                        "frame": post_rope["final"]["frame"],
                        "save_result": session.save_state(checkpoint_path),
                    }

            if not args.room6_entry_state:
                room6_entry = replay._observe_no_input_lifecycle(
                    session, rom=rom, symbol_banks=symbols, archive=archive,
                    variable_base=variable_layout["base"],
                    variable_count=variable_layout["count"],
                    object_count=variable_layout["object_count"],
                    max_frames=args.room_entry_frames,
                )
                output["room6_entry"] = room6_entry
                if (room6_entry.get("status") != "authored-room-entry-complete"
                        or room6_entry["final"]["room"] != 6):
                    raise RuntimeError(
                        "room6 authored entry did not settle: "
                        f"{replay._room_entry_failure_summary(room6_entry)!r}"
                    )
                record_room(session, 6)
                if args.checkpoint_dir:
                    checkpoint_path = args.checkpoint_dir.resolve() / "room6-entry-complete.state"
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    output["room6_state_after_entry"] = {
                        "path": str(checkpoint_path), "rom_sha256": rom_sha,
                        "frame": room6_entry["final"]["frame"],
                        "save_result": session.save_state(checkpoint_path),
                    }
                    atomic_report(args.output.resolve(), output)

            before_slots = replay._snapshot(session)["slots"]
            books = fate_replay.replay_room6_books_interaction(
                session, pulse=pulse, diagonal_navigation=True,
            )
            if books["submission_count_after"] != ((books["submission_count_before"] + 1) & 0xFF):
                raise RuntimeError(f"room6 books did not submit exactly once: {books!r}")
            output["controller_submissions"].append({
                "action": "room6 books on statues",
                "before": books["submission_count_before"], "after": books["submission_count_after"],
            })
            output["room6_books_action"] = books
            post_books = observe_action(
                session, name="post_room6_books",
                baseline=books["submission_count_before"], baseline_slots=before_slots,
            )
            room6_dispatches = [
                {"room": sample["room"], "script": slot["script"],
                 "program_unit_identity": slot.get("program_unit_identity"),
                 "saved_pc": slot["saved_pc"]}
                for sample in post_books.get("frame_boundary_execution_samples", [])
                for slot in sample["slots"] if slot["script"] == 200
            ]
            if not any(row["room"] == 6 and row["program_unit_identity"] ==
                       "RoomLocalProgram(room=6,local=200)" for row in room6_dispatches):
                raise RuntimeError(f"room6 LSCR200 not observed canonically: {room6_dispatches!r}")
            output["room6_lscr200_observations"] = room6_dispatches[:8]
            if post_books["status"] != "room-transition" or post_books["final"]["room"] != 7:
                raise RuntimeError(f"room6 books did not reach room7: {post_books!r}")

            room7_entry = replay._observe_no_input_lifecycle(
                session, rom=rom, symbol_banks=symbols, archive=archive,
                variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
                object_count=variable_layout["object_count"],
                max_frames=args.room_entry_frames,
            )
            output["room7_entry"] = room7_entry
            if room7_entry.get("status") != "authored-room-entry-complete" or room7_entry["final"]["room"] != 7:
                raise RuntimeError(f"room7 authored entry did not settle: {room7_entry!r}")
            record_room(session, 7)

            before_slots = replay._snapshot(session)["slots"]
            book = fate_replay.replay_room7_lost_dialogue_interaction(
                session, variable_base=variable_layout["base"],
                variable_count=variable_layout["count"], pulse=pulse,
                diagonal_navigation=True,
            )
            if book["submission_count_after"] != ((book["submission_count_before"] + 1) & 0xFF):
                raise RuntimeError(f"Lost Dialogue action did not submit exactly once: {book!r}")
            output["controller_submissions"].append({
                "action": "room7 Lost Dialogue of Plato",
                "before": book["submission_count_before"], "after": book["submission_count_after"],
            })
            output["room7_book_action"] = book
            post_book = observe_action(
                session, name="post_room7_book",
                baseline=book["submission_count_before"], baseline_slots=before_slots,
            )
            if post_book["status"] != "authored-action-quiescent-in-room7":
                raise RuntimeError(f"room7 book action did not settle in room7: {post_book!r}")

            before_slots = replay._snapshot(session)["slots"]
            cat118 = fate_replay.replay_room7_cat_figure_use(
                session, object_id=118, variable_base=variable_layout["base"],
                variable_count=variable_layout["count"], pulse=pulse,
                diagonal_navigation=True,
            )
            if cat118["submission_count_after"] != ((cat118["submission_count_before"] + 1) & 0xFF):
                raise RuntimeError(f"object118 action did not submit once: {cat118!r}")
            output["controller_submissions"].append({
                "action": "room7 object118 verb10",
                "before": cat118["submission_count_before"], "after": cat118["submission_count_after"],
            })
            output["room7_cat118_action"] = cat118
            post_cat118 = observe_action(
                session, name="post_room7_cat118",
                baseline=cat118["submission_count_before"], baseline_slots=before_slots,
            )
            if post_cat118["status"] != "authored-action-quiescent-in-room7":
                raise RuntimeError(f"object118 action did not settle: {post_cat118!r}")
            context118 = replay._room7_runtime_context(
                session, variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
                object_count=variable_layout["object_count"],
            )
            output["room7_after_cat118_context"] = context118
            if (context118["selected_variables"]["214"] != 1
                    or context118["selected_variables"]["217"] != 1
                    or context118["selected_variables"]["218"] != 0):
                raise RuntimeError(f"object118 progression state mismatch: {context118!r}")

            before_slots = replay._snapshot(session)["slots"]
            cat119 = fate_replay.replay_room7_cat_figure_use(
                session, object_id=119, variable_base=variable_layout["base"],
                variable_count=variable_layout["count"], pulse=pulse,
                diagonal_navigation=True,
            )
            if cat119["submission_count_after"] != ((cat119["submission_count_before"] + 1) & 0xFF):
                raise RuntimeError(f"object119 action did not submit once: {cat119!r}")
            output["controller_submissions"].append({
                "action": "room7 object119 verb10",
                "before": cat119["submission_count_before"], "after": cat119["submission_count_after"],
            })
            output["room7_cat119_action"] = cat119
            post_cat119 = observe_action(
                session, name="post_room7_cat119",
                baseline=cat119["submission_count_before"], baseline_slots=before_slots,
            )
            dispatches = [
                {"room": sample["room"], "script": slot["script"],
                 "program_unit_identity": slot.get("program_unit_identity"),
                 "saved_pc": slot["saved_pc"],
                 "binding_generation": slot.get("binding_generation")}
                for sample in post_cat119.get("frame_boundary_execution_samples", [])
                for slot in sample["slots"] if slot["script"] in (201, 207)
            ]
            output["room7_cat_local_dispatches"] = dispatches
            if {row["script"] for row in dispatches} != {201, 207}:
                raise RuntimeError(f"room7 expected LSCR207/LSCR201 dispatches: {dispatches!r}")
            if any(row["program_unit_identity"] !=
                   f"RoomLocalProgram(room=7,local={row['script']})" for row in dispatches):
                raise RuntimeError(f"room7 dispatch canonical identities mismatch: {dispatches!r}")
            if post_cat119["status"] != "room-transition" or post_cat119["final"]["room"] != 3:
                raise RuntimeError(f"room7 LSCR201 did not transition to room3: {post_cat119!r}")

            room3_entry = replay._observe_no_input_lifecycle(
                session, rom=rom, symbol_banks=symbols, archive=archive,
                variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
                object_count=variable_layout["object_count"],
                max_frames=args.room_entry_frames,
            )
            output["room3_entry"] = room3_entry
            if room3_entry.get("status") != "authored-room-entry-complete" or room3_entry["final"]["room"] != 3:
                raise RuntimeError(f"room3 authored entry did not settle: {room3_entry!r}")
            if args.checkpoint_dir:
                checkpoint_path = args.checkpoint_dir.resolve() / "room3-entry-complete.state"
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                output["room3_state_after_entry"] = {
                    "path": str(checkpoint_path), "rom_sha256": rom_sha,
                    "frame": room3_entry["final"]["frame"],
                    "save_result": session.save_state(checkpoint_path),
                }
                atomic_report(args.output.resolve(), output)
            record_room(session, 3)
            final = replay._snapshot(session)
            output["final_snapshot"] = final
            if (final["room"], final["phase"], final["error"], final["lifecycle"],
                    final["actor1_room"], final["actor1_x"], final["actor1_y"]) != (
                    3, 0, 0, 2, 3, 71, 142):
                raise RuntimeError(f"final room3 state differs from accepted checkpoint: {final!r}")
            if not any(slot["script"] == 213 and slot["status"] not in (0, 4)
                       for slot in final["slots"]):
                raise RuntimeError(f"room3 local 213 is not active: {final['slots']!r}")
            if len(output["controller_submissions"]) != 5:
                raise RuntimeError("continuation must add exactly the five remaining authored submissions")
            if [row["after"] - row["before"] for row in output["controller_submissions"]] != [1] * 5:
                raise RuntimeError("a continuation action did not increment one submission")

            final["residency"] = replay._snapshot(session)["residency"]
            telemetry = final["residency"]
            if any(telemetry.get(key, 0) for key in (
                    "stale_reference_detections", "exhaustions",
                    "duplicate_program_unit_bindings")):
                raise RuntimeError(f"resolver safety counter is nonzero: {telemetry!r}")
            output["final_snapshot"] = final
            output["residency_summary"] = {
                key: telemetry.get(key) for key in (
                    "peak_resident", "observed_peak_pinned", "bind_count",
                    "reuse_count", "bundle_loads", "bundle_releases",
                    "dynamic_global_resolutions", "stale_reference_detections",
                    "exhaustions", "duplicate_program_unit_bindings",
                )
            }
            output["result"] = "pass"
            output["result_scope"] = "same-ROM route continuation"
            output["route"] = [0, 68, 0, 4, 5, 6, 7, 3]
            combined = dict(prefix)
            combined.update({
                "result": "pass",
                "evidence_class": (
                    "cold dynamic route prefix plus same-ROM, hash-bound "
                    "continuation from the prefix's room5 transition checkpoint"
                ),
                "prefix_report_sha256": sha256(prefix_path),
                "room5_entry": room5_entry,
                "room5_rope_action": rope,
                "post_room5_rope": post_rope,
                "room6_entry": room6_entry,
                "room6_books_action": books,
                "post_room6_books": post_books,
                "room6_lscr200_observations": output["room6_lscr200_observations"],
                "room7_entry": room7_entry,
                "room7_book_action": book,
                "post_room7_book": post_book,
                "room7_cat118_action": cat118,
                "post_room7_cat118": post_cat118,
                "room7_cat119_action": cat119,
                "post_room7_cat119": post_cat119,
                "room7_cat_local_dispatches": dispatches,
                "room3_entry": room3_entry,
                "final_snapshot": final,
                "msu_room_observations": {
                    **prefix.get("msu_room_observations", {}),
                    **output["room_observations"],
                },
                "residency_summary_after_continuation": output["residency_summary"],
            })
            combined_path = args.output.resolve().with_name(
                args.output.stem + ".combined-route.json"
            )
            atomic_report(combined_path, combined)
            output["combined_route_report"] = str(combined_path)
            output["combined_route_report_sha256"] = sha256(combined_path)
            atomic_report(args.output.resolve(), output)
            print(f"FATE MSU bounded route continuation PASS ({rom_sha})")
            print(args.output.resolve())
    except Exception as exc:
        output["result"] = "fail"
        output["failure"] = f"{type(exc).__name__}: {exc}"
        try:
            output["failure_snapshot"] = replay._snapshot(session)
        except Exception:
            pass
        atomic_report(args.output.resolve(), output)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
