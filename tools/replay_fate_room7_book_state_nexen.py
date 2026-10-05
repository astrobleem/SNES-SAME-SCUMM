#!/usr/bin/env python3
"""Run one ROM-bound, same-ROM state-assisted room7 book interaction."""
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
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--state-source-report", type=Path, required=True)
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/ATLANTIS.zip"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44982)
    parser.add_argument("--max-action-frames", type=int, default=3600)
    args = parser.parse_args()

    rom = args.rom.resolve()
    state_path = args.state.resolve()
    source_report_path = args.state_source_report.resolve()
    archive = args.archive.resolve()
    nexen = args.nexen.resolve()
    for path in (rom, state_path, source_report_path, archive, nexen):
        if not path.is_file():
            parser.error(f"required input does not exist: {path}")

    rom_sha = hashlib.sha256(rom.read_bytes()).hexdigest()
    state_sha = hashlib.sha256(state_path.read_bytes()).hexdigest()
    source_report_sha = hashlib.sha256(source_report_path.read_bytes()).hexdigest()
    source_report = json.loads(source_report_path.read_text(encoding="utf-8"))
    state_provenance = source_report.get("room7_same_rom_state_assist", {})
    if source_report.get("rom_sha256") != rom_sha:
        parser.error("state source report is not for the supplied ROM")
    if state_provenance.get("rom_sha256") != rom_sha:
        parser.error("saved state is not recorded as coming from the supplied ROM")
    if Path(state_provenance.get("path", "")).resolve() != state_path:
        parser.error("saved-state path differs from the source report")
    if source_report.get("room7_entry", {}).get("status") != (
        "authored-room-entry-complete"
    ):
        parser.error("source report does not establish completed room7 entry")

    identity_path = rom.with_suffix(".build_identity.json")
    identity_sha = hashlib.sha256(identity_path.read_bytes()).hexdigest()
    map_path, _symbols = _load_rom_symbols(rom)
    map_sha = hashlib.sha256(map_path.read_bytes()).hexdigest()
    listing_path = rom.with_suffix(".lst")
    variable_layout = _parse_variable_layout(listing_path.read_text(encoding="utf-8"))
    nexen_sha = hashlib.sha256(nexen.read_bytes()).hexdigest()

    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, "/home/chad/Mesen2/python")
    from fate_replay import replay_room7_lost_dialogue_interaction, room4_synchronous_input_edge
    from replay_fate_room4_cold_nexen import (
        _authentic_room7_book_source,
        _observe_action,
        _room7_runtime_context,
        _snapshot,
    )
    import mesen_mcp.session as mesen_session

    mesen_session.validate_mesen_build = lambda _path: None
    report: dict[str, Any] = {
        "result": "running",
        "evidence_class": (
            "same-ROM state-assisted native diagnostic; not cold-start acceptance"
        ),
        "rom_sha256": rom_sha,
        "map": str(map_path),
        "map_sha256": map_sha,
        "build_identity": str(identity_path),
        "build_identity_sha256": identity_sha,
        "state": str(state_path),
        "state_sha256": state_sha,
        "state_source_report": str(source_report_path),
        "state_source_report_sha256": source_report_sha,
        "nexen": str(nexen),
        "nexen_sha256": nexen_sha,
        "starting_head": source_report.get("starting_head"),
    }
    report["room7_book_source"] = _authentic_room7_book_source(archive, identity_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    owned_session = mesen_session.McpSession(
        rom=rom,
        mesen=nexen,
        cwd=ROOT,
        port=args.port,
        boot_wait=2.0,
        socket_timeout=300.0,
        stderr_log=args.output.with_suffix(".nexen-stderr.log"),
    )
    try:
        with owned_session as session:
            session.pause()
            report["state_load"] = session.load_state(state_path)
            session.pause()
            before = _snapshot(session)
            report["before"] = before
            report["before_runtime_context"] = _room7_runtime_context(
                session,
                variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
            )

            def exact_edge(pulse_session: Any, mask: int, predicate: Any) -> dict[str, Any]:
                return room4_synchronous_input_edge(pulse_session, mask, predicate)

            report["action"] = replay_room7_lost_dialogue_interaction(
                session,
                variable_base=variable_layout["base"],
                variable_count=variable_layout["count"],
                pulse=exact_edge,
            )
            baseline = report["action"]["submission_count_before"]
            report["post_action"] = _observe_action(
                session,
                baseline=baseline,
                max_frames=args.max_action_frames,
                rom=rom,
                symbol_banks={
                    "Same_Input_Poll__edge_sequence_done": 0,
                    "ScummV5_Talk_FrameBegin_Far": 9,
                    "ScummV5_Talk_FrameBegin_Far__publish": 9,
                    "ScummV5_Controller_Frame_Far": 9,
                    "ScummV5_Controller_Frame__generic_ready": 9,
                    "ScummV5_Controller_Frame__select_verb_a_pressed": 9,
                    "ScummV5_Controller_Frame__done": 9,
                    "ScummV5_Talk_FrameEnd_Far": 9,
                    "ScummV5_Talk_FrameEnd_Far__done": 9,
                },
                exact_frame_observation=False,
            )
            report["final"] = _snapshot(session)
            if report["final"]["room"] == 7:
                report["final_runtime_context"] = _room7_runtime_context(
                    session,
                    variable_base=variable_layout["base"],
                    variable_count=variable_layout["count"],
                )
            report["result"] = "pass"
    except Exception as exc:
        process = getattr(owned_session, "_proc", None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
                process.wait(timeout=5)
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        raise
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"FATE room7 same-ROM replay: {report['result']} ({rom_sha})")
    print(args.output)
    return 0


def _load_rom_symbols(rom: Path) -> tuple[Path, dict[str, Any]]:
    from validate_scumm_startup42_nexen import verified_symbol_map_for_rom

    return verified_symbol_map_for_rom(rom)


def _parse_variable_layout(listing: str) -> dict[str, int]:
    from replay_fate_room4_cold_nexen import _parse_rom_variable_layout

    return _parse_rom_variable_layout(listing)


if __name__ == "__main__":
    raise SystemExit(main())
