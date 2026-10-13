#!/usr/bin/env python3
"""Observe the authentic room-6 books continuation from its ROM-bound state."""
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
    parser.add_argument("--room6-state", type=Path, required=True)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/ATLANTIS.zip"))
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44984)
    parser.add_argument("--observe-frames", type=int, default=1200)
    parser.add_argument("--sample-stride", type=int, default=4)
    args = parser.parse_args()
    if args.observe_frames <= 0 or args.sample_stride <= 0:
        parser.error("observation frame count and stride must be positive")

    rom, state_path = args.rom.resolve(), args.room6_state.resolve()
    source_path, archive, nexen = (
        args.source_report.resolve(), args.archive.resolve(), args.nexen.resolve()
    )
    for path in (rom, state_path, source_path, archive, nexen):
        if not path.is_file():
            parser.error(f"required input does not exist: {path}")
    identity_path = rom.with_suffix(".build_identity.json")
    listing_path = rom.with_suffix(".lst")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    checkpoint = source.get("room6_checkpoint", {})
    rom_sha = hashlib.sha256(rom.read_bytes()).hexdigest()
    if source.get("rom_sha256") != rom_sha:
        parser.error("checkpoint report is not bound to this ROM")
    if Path(checkpoint.get("state_path", "")).resolve() != state_path:
        parser.error("room-6 checkpoint path differs from its source report")
    if not identity_path.is_file() or not listing_path.is_file():
        parser.error("ROM-bound build identity or listing is missing")

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
    variable_layout = replay._parse_rom_variable_layout(
        listing_path.read_text(encoding="utf-8")
    )
    symbols = {
        "Same_Input_Poll__edge_sequence_done": 0,
        "Same_Input_Poll": 0,
    }
    output: dict[str, Any] = {
        "evidence_class": "same-ROM room-6 state-assisted native diagnostic",
        "rom_sha256": rom_sha,
        "build_identity_sha256": hashlib.sha256(identity_path.read_bytes()).hexdigest(),
        "room6_state": str(state_path),
        "room6_state_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
        "source_report_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "starting_head": identity.get("git", {}).get("head"),
        "samples": [],
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
            before = replay._snapshot(session)
            output["before"] = before
            if (before["room"], before["phase"], before["error"],
                    before["actor1_room"]) != (6, 0, 0, 6):
                raise RuntimeError(f"not a settled authentic room-6 state: {before!r}")

            action = fate_replay.replay_room6_books_interaction(session, pulse=pulse)
            output["books_action"] = action
            delta = (action["submission_count_after"]
                     - action["submission_count_before"]) & 0xFF
            output["submission_delta"] = delta
            if delta != 1:
                raise RuntimeError(f"books sentence was not submitted exactly once: {action!r}")

            after_action_path = args.output.with_name("room6-after-books.state")
            output["after_action_state"] = {
                "path": str(after_action_path),
                "save_result": session.save_state(after_action_path),
            }
            output["after_action_state"]["sha256"] = hashlib.sha256(
                after_action_path.read_bytes()
            ).hexdigest()

            from fate_replay import advance_bounded
            previous_signature: tuple[Any, ...] | None = None
            elapsed = 0
            while elapsed < args.observe_frames:
                state = replay._snapshot(session)
                state["transition_diagnostics"] = {
                    "bundle_record": session.read_u8(0x7E8F9E),
                    "bundle_remaining": session.read_u8(0x7E8F9F),
                    "bundle_offset": int.from_bytes(
                        session.read_memory("snesMemory", 0x7E8FA0, 2), "little"
                    ),
                    "bundle_failure": session.read_u8(0x7E8FAB),
                    "resolver_request_id": int.from_bytes(
                        session.read_memory("snesMemory", 0x7E8F7A, 2), "little"
                    ),
                    "resolver_selector": session.read_u8(0x7E8F7C),
                    "selector_caller": session.read_u8(0x7E8FAC),
                    "resolver_error_return": session.read_memory(
                        "snesMemory", 0x7E8FAD, 3
                    ).hex(),
                    "room_request_count": session.read_u8(0x7FF2C5),
                    "room_validation_count": session.read_u8(0x7FF2C6),
                    "room_retire_count": session.read_u8(0x7FF2C8),
                    "room_entry_count": session.read_u8(0x7FF2C9),
                    "room_exit_count": session.read_u8(0x7FF2CA),
                }
                state["cpu"] = session.get_cpu_state("Snes")
                signature = tuple(state.get(key) for key in (
                    "room", "phase", "m23a_phase", "m23a_current_kind",
                    "active_record", "pending_record", "pending_room",
                    "entry_program", "exit_program", "program_select",
                    "shared_vm_pc", "interpreter_status", "return_mode", "slot0",
                    "m23a_lifecycle_trace", "m23a_hold", "c4_parent", "slots", "error",
                ))
                if signature != previous_signature:
                    output["samples"].append(state)
                    previous_signature = signature
                if state["room"] == 7 and state["phase"] == 0:
                    break
                step = min(args.sample_stride, args.observe_frames - elapsed)
                advanced = advance_bounded(session, step)
                if advanced["frames_advanced"] != step:
                    raise RuntimeError(f"frame-step drift during observation: {advanced!r}")
                elapsed += step
            output["observed_frames"] = elapsed
            output["final"] = replay._snapshot(session)
            output["final"]["transition_diagnostics"] = {
                "bundle_record": session.read_u8(0x7E8F9E),
                "bundle_remaining": session.read_u8(0x7E8F9F),
                "bundle_offset": int.from_bytes(
                    session.read_memory("snesMemory", 0x7E8FA0, 2), "little"
                ),
                "bundle_failure": session.read_u8(0x7E8FAB),
                "resolver_request_id": int.from_bytes(
                    session.read_memory("snesMemory", 0x7E8F7A, 2), "little"
                ),
                "resolver_selector": session.read_u8(0x7E8F7C),
                "selector_caller": session.read_u8(0x7E8FAC),
                "resolver_error_return": session.read_memory(
                    "snesMemory", 0x7E8FAD, 3
                ).hex(),
                "room_request_count": session.read_u8(0x7FF2C5),
                "room_validation_count": session.read_u8(0x7FF2C6),
                "room_retire_count": session.read_u8(0x7FF2C8),
                "room_entry_count": session.read_u8(0x7FF2C9),
                "room_exit_count": session.read_u8(0x7FF2CA),
            }
            output["final"]["cpu"] = session.get_cpu_state("Snes")
            output["result"] = (
                "room7 reached" if output["final"]["room"] == 7
                else "bounded room6 transition observation complete"
            )
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
    final = output.get("final", {})
    print(json.dumps({
        "result": output.get("result"), "exception": output.get("exception"),
        "submission_delta": output.get("submission_delta"),
        "samples": len(output.get("samples", [])),
        "observed_frames": output.get("observed_frames"),
        "final": {key: final.get(key) for key in (
            "frame", "room", "phase", "m23a_phase", "m23a_current_kind",
            "active_record", "pending_record", "pending_room", "entry_program",
            "exit_program", "program_select", "shared_vm_pc", "interpreter_status",
            "slot0", "m23a_lifecycle_trace", "m23a_hold", "slots", "error",
        )},
        "output": str(args.output.resolve()),
    }, indent=2, sort_keys=True))
    return 0 if output.get("result") != "diagnostic failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
