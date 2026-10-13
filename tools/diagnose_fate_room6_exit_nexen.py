#!/usr/bin/env python3
"""Resume a ROM-bound room-4 checkpoint and capture room-6 exit state.

This is a bounded diagnostic for the accepted authored replay, not a cold
route acceptance tool. It never writes SCUMM state and submits each authored
action once through the same native controller helpers as the route runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--room4-state", type=Path, required=True)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/ATLANTIS.zip"))
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44983)
    parser.add_argument("--exit-observation-frames", type=int, default=240)
    parser.add_argument(
        "--stop-on-program-length-error", action="store_true",
        help=("diagnostic only: stop at the native ProgramUnit bad-length "
              "branch after the room4 Use submission and capture its operands"),
    )
    args = parser.parse_args()

    rom, state_path = args.rom.resolve(), args.room4_state.resolve()
    source_path, archive, nexen = (
        args.source_report.resolve(), args.archive.resolve(), args.nexen.resolve()
    )
    for path in (rom, state_path, source_path, archive, nexen):
        if not path.is_file():
            parser.error(f"required input does not exist: {path}")
    identity_path = rom.with_suffix(".build_identity.json")
    listing_path = rom.with_suffix(".lst")
    for path in (identity_path, listing_path):
        if not path.is_file():
            parser.error(f"ROM-bound sidecar is missing: {path}")

    source_report = json.loads(source_path.read_text(encoding="utf-8"))
    state_provenance = source_report.get("room4_settled_state", {})
    rom_sha = hashlib.sha256(rom.read_bytes()).hexdigest()
    if state_provenance.get("rom_sha256") != rom_sha:
        parser.error("room-4 state provenance does not match this ROM")
    if Path(state_provenance.get("path", "")).resolve() != state_path:
        parser.error("room-4 state path does not match the source report")
    state_sha = hashlib.sha256(state_path.read_bytes()).hexdigest()
    identity_sha = hashlib.sha256(identity_path.read_bytes()).hexdigest()

    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import fate_replay
    import replay_fate_room4_cold_nexen as replay
    from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom
    import mesen_mcp.session as mesen_session

    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    explicit = identity.get("explicit_environment", {})
    replay.ACTIVE_DYNAMIC_RESIDENCY = (
        explicit.get("SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY") == "1"
    )
    replay.ACTIVE_MSU_PROGRAMS = (
        explicit.get("SAME_BUILD_SCUMM_MSU1_PROGRAMS") == "1"
    )
    replay.ACTIVE_LIVE_ROOM_RESOURCES = (
        explicit.get("SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES") == "1"
    )
    if replay.ACTIVE_DYNAMIC_RESIDENCY:
        replay.ACTIVE_PROGRAM_DIRECTORY = replay._native_directory_for_build(
            identity_path
        )["by_id"]

    listing = listing_path.read_text(encoding="utf-8")
    variable_layout = replay._parse_rom_variable_layout(listing)
    symbols = {
        "Same_Input_Poll__edge_sequence_done": 0,
        "ScummV5_Talk_FrameBegin_Far": 9,
        "ScummV5_Talk_FrameBegin_Far__publish": 9,
        "ScummV5_Controller_Frame_Far": 9,
        "ScummV5_Controller_Frame__generic_ready": 9,
        "ScummV5_Controller_Frame__select_verb_a_pressed": 9,
        "ScummV5_Controller_Frame__done": 9,
        "ScummV5_Talk_FrameEnd_Far": 9,
        "ScummV5_Talk_FrameEnd_Far__done": 9,
    }
    if replay.ACTIVE_DYNAMIC_RESIDENCY:
        symbols["ScummV5_Resident_Reset_Far"] = 9

    output: dict[str, Any] = {
        "evidence_class": "same-ROM state-assisted diagnostic; not route acceptance",
        "rom_sha256": rom_sha,
        "build_identity_sha256": identity_sha,
        "room4_state": str(state_path),
        "room4_state_sha256": state_sha,
        "source_report": str(source_path),
        "source_report_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "starting_head": identity.get("git", {}).get("head"),
        "events": [],
    }
    owned = mesen_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=args.port, boot_wait=2.0,
        socket_timeout=300.0, stderr_log=args.output.with_suffix(".stderr.log"),
    )
    mesen_session.validate_mesen_build = lambda _path: None

    def pulse(session: Any, mask: int, predicate: Any) -> dict[str, Any]:
        return fate_replay.room4_synchronous_input_edge(
            session, mask, predicate, poll_interval_frames=2,
            poll_boundary_address=mapped_cpu_address_for_rom(
                rom, "Same_Input_Poll__edge_sequence_done", bank=0
            ),
            pre_press_poll_boundary_address=mapped_cpu_address_for_rom(
                rom, "Same_Input_Poll", bank=0
            ),
        )

    try:
        with owned as session:
            session.pause()
            output["state_load"] = session.load_state(state_path)
            session.pause()
            start = replay._snapshot(session)
            output["loaded_state"] = start
            if (start["room"], start["phase"], start["error"]) != (4, 0, 0):
                raise RuntimeError(f"state is not a settled room-4 checkpoint: {start!r}")

            if (start["c19_stack_pointer"], start["c19_override_script"],
                    start["c19_override_room"]) != (1, 206, 4):
                raise RuntimeError(
                    "state lacks the accepted room4 LSCR206 override: "
                    f"{start!r}"
                )
            owner_slot = start["c19_override_slot"]
            owner = next((slot for slot in start["slots"]
                          if slot["slot"] == owner_slot), None)
            if owner is None or owner["script"] != 206:
                raise RuntimeError(f"C19 owner is not the live LSCR206 slot: {owner!r}")
            output["room4_override_skip"] = fate_replay.skip_room4_authored_override(
                session, expected_override_program=owner["program"],
                expected_override_slot=owner_slot, defer_release_sample=True,
                poll_interval_frames=2,
                poll_boundary_address=mapped_cpu_address_for_rom(
                    rom, "Same_Input_Poll__edge_sequence_done", bank=0
                ),
                pre_press_poll_boundary_address=mapped_cpu_address_for_rom(
                    rom, "Same_Input_Poll", bank=0
                ),
            )
            fate_replay.finish_room4_authored_cutscene(session)
            output["room4_intro"] = replay._finish_room4_intro(
                session, max_frames=2400, rom=rom, symbol_banks=symbols
            )
            intro_state = replay._snapshot(session)
            output["after_room4_intro"] = intro_state
            if (intro_state["cursor_world_x"], intro_state["cursor_world_y"]) != (117, 138):
                raise RuntimeError(
                    "authored room4 intro did not reach recorded cursor point: "
                    f"{intro_state!r}"
                )

            open_action = fate_replay.replay_room4_open_trapdoor_prefix(
                session, pulse=pulse
            )
            output["open_action"] = open_action
            output["after_open"] = replay._observe_action(
                session, baseline=open_action["precondition"]["submissions"],
                max_frames=2400, rom=rom, symbol_banks=symbols,
            )
            if output["after_open"]["status"] != "authored-action-quiescent-in-room4":
                raise RuntimeError(f"room-4 Open did not settle: {output['after_open']!r}")

            use_action = fate_replay.replay_room4_trapdoor_use(session, pulse=pulse)
            output["use_action"] = use_action
            if args.stop_on_program_length_error:
                # Watch the diagnostic's first-error latch rather than a
                # guessed ROM PBR: the common far-code block is placed by the
                # linker, and its physical bank is not encoded in Poppy's
                # bank-local symbol value.
                hook = session.add_write_hook(
                    0x7E5F17, match_value=0x14, match_value_mask=0xFF,
                )
                try:
                    stop = session.run_until(
                        max_frames=3600, hook_handle=hook,
                    )
                    session.pause()
                    hook_events = [
                        message.get("params", message)
                        for message in session.drain_notifications(timeout=0.0)
                        if message.get("params", message).get("handle") == hook
                    ]
                    output["program_length_error_capture"] = {
                        "watch": "first-error resource site $7E5F17 == $14",
                        "hook_events": hook_events,
                        "run_until": stop,
                        "cpu": session.get_cpu_state("Snes"),
                        "request_id": replay._u16(session, 0x7E2F58),
                        "lookup_id": replay._u16(session, 0x7E2ECD),
                        "request_pc": replay._u16(session, 0x7E2EAC),
                        "page_start": replay._u16(session, 0x7E2EAE),
                        "page_length": replay._u16(session, 0x7E2EB0),
                        "page_body_length": replay._u16(session, 0x7E2EBA),
                        "body_record_length": replay._u16(session, 0x7E2F08),
                        "provider_offset": int.from_bytes(
                            session.read_memory("snesMemory", 0x7E2F04, 4),
                            "little",
                        ),
                        "provider_length": int.from_bytes(
                            session.read_memory("snesMemory", 0x7E2F08, 4),
                            "little",
                        ),
                        "cache_request_slot": session.read_u8(0x7E2F5A),
                        "cache_states": session.read_memory(
                            "snesMemory", 0x7E2F48, 2,
                        ).hex(),
                        "cache_ids": session.read_memory(
                            "snesMemory", 0x7E2F4A, 4,
                        ).hex(),
                        "cache_sizes": session.read_memory(
                            "snesMemory", 0x7E2F4E, 4,
                        ).hex(),
                        "page_lookup": session.read_memory(
                            "snesMemory", 0x7E2EAC, 0x22,
                        ).hex(),
                        "provider_status": session.read_u8(0x7E2F00),
                        "provider_error": session.read_u8(0x7E2F01),
                        "length_error_detail": {
                            "subsite": session.read_u8(0x7E5F19),
                            "page_start": replay._u16(session, 0x7E5F1A),
                            "page_length": replay._u16(session, 0x7E5F1C),
                            "body_length": replay._u16(session, 0x7E5F1E),
                            "request_length_high": replay._u16(session, 0x7E5F5E),
                        },
                        "state": replay._snapshot(session),
                        "trace_tail": session.trace_log(
                            count=128, cpu_type="Snes",
                        ),
                    }
                    output["result"] = "program-length-error-diagnostic"
                    output["evidence_class"] = (
                        "same-ROM state-assisted diagnostic; not route acceptance"
                    )
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(
                        json.dumps(output, indent=2) + "\n", encoding="utf-8",
                    )
                    print(args.output)
                    return 0
                finally:
                    session.remove_hook(hook)
            output["after_use"] = replay._observe_action(
                session, baseline=use_action["submission_count_before"],
                max_frames=3600, rom=rom, symbol_banks=symbols,
                capture_execution_trace=True,
                variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
                object_count=variable_layout["object_count"],
            )
            if output["after_use"]["status"] != "room-transition":
                raise RuntimeError(f"room-4 Use did not request room 5: {output['after_use']!r}")
            output["room5_entry"] = replay._observe_no_input_lifecycle(
                session, rom=rom, symbol_banks=symbols, archive=archive,
                variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
                object_count=variable_layout["object_count"],
            )
            if output["room5_entry"]["status"] != "authored-room-entry-complete":
                raise RuntimeError(f"room 5 entry did not settle: {output['room5_entry']!r}")

            rope_action = fate_replay.replay_room5_rope_to_room6(
                session, pulse=pulse
            )
            output["rope_action"] = rope_action
            output["after_rope"] = replay._observe_action(
                session, baseline=rope_action["submission_count_before"],
                max_frames=9000, rom=rom, symbol_banks=symbols,
                capture_execution_trace=True,
                variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
                object_count=variable_layout["object_count"],
            )
            if output["after_rope"]["status"] != "room-transition":
                raise RuntimeError(f"room-5 rope did not request room 6: {output['after_rope']!r}")
            output["room6_entry"] = replay._observe_no_input_lifecycle(
                session, rom=rom, symbol_banks=symbols, archive=archive,
                variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
                object_count=variable_layout["object_count"],
            )
            if output["room6_entry"]["status"] != "authored-room-entry-complete":
                raise RuntimeError(f"room 6 entry did not settle: {output['room6_entry']!r}")

            before_path = args.output.with_name("room6-before-books.state")
            output["room6_checkpoint"] = {
                "state_path": str(before_path),
                "state_sha256": None,
                "state_save": session.save_state(before_path),
                "snapshot": replay._snapshot(session),
            }
            output["books_action"] = fate_replay.replay_room6_books_interaction(
                session, pulse=pulse
            )
            output["room6_action_submission_delta"] = (
                output["books_action"]["submission_count_after"]
                - output["books_action"]["submission_count_before"]
            ) & 0xFF

            previous = None
            max_frames = args.exit_observation_frames
            for _ in range(max_frames):
                state = replay._snapshot(session)
                signature = tuple(state.get(key) for key in (
                    "room", "m23a_phase", "m23a_current_kind", "active_record",
                    "pending_record", "pending_room", "entry_program", "exit_program",
                    "program_select", "shared_vm_pc", "interpreter_status", "return_mode",
                    "slot0", "m23a_hold", "m23a_lifecycle_trace", "c4_parent", "error",
                ))
                if signature != previous:
                    output["events"].append(state)
                    previous = signature
                if state["room"] == 7 and state["phase"] == 0:
                    break
                fate_replay.advance_bounded(session, 1)
            output["final"] = replay._snapshot(session)
            output["result"] = "room7 reached" if output["final"]["room"] == 7 else "diagnostic captured"
    except Exception as exc:
        output["result"] = "diagnostic failed"
        output["exception"] = f"{type(exc).__name__}: {exc}"
        process = getattr(owned, "_proc", None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": output.get("result"),
        "exception": output.get("exception"),
        "events": len(output.get("events", [])),
        "final": output.get("final"),
        "output": str(args.output.resolve()),
    }, indent=2, sort_keys=True))
    return 0 if output.get("result") == "room7 reached" else 1


if __name__ == "__main__":
    raise SystemExit(main())
