#!/usr/bin/env python3
"""Run the generated C2 SCUMM v5 fixture matrix in one short Nexen session."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build" / "same-engine-host.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
STATE_ADDRESS = 0x7E2300
STATE_LENGTH = 0x64
FIXTURE_REQUEST = 0x7E235E


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object, variable_base: int) -> dict[str, object]:
    raw = session.read_memory("snesMemory", STATE_ADDRESS, STATE_LENGTH)
    variable_bytes = session.read_memory("snesMemory", variable_base, 16 * 2)
    return {
        "pc": u16(raw, 0x00),
        "status": raw[0x02],
        "error": raw[0x03],
        "delay": u16(raw, 0x04),
        "last_opcode": raw[0x06],
        "frame_count": u16(raw, 0x08),
        "frame_ops": u16(raw, 0x0A),
        "total_ops": u16(raw, 0x0C),
        "variables": [u16(variable_bytes, index * 2) for index in range(16)],
        "fixture_request": raw[0x5E],
        "fixture_active": raw[0x5F],
    }


def step_video_frame(session: object) -> int:
    for _ in range(20):
        run = session.run_frames(1)
        if run["framesAdvanced"] == 1:
            return 1
    raise GateFailure(f"one-frame step made no progress: {run}")


def assert_fields(name: str, observed: dict[str, object], expected: dict[str, object]) -> None:
    for key, value in expected.items():
        if key == "variable_expectations":
            variables = observed["variables"]
            for index, expected_value in value.items():
                actual = variables[int(index)]
                require(actual == expected_value,
                        f"{name}: variable[{index}]={actual!r}, expected {expected_value!r}")
            continue
        require(observed[key] == value, f"{name}: {key}={observed[key]!r}, expected {value!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43987)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--only-extended", action="store_true",
                        help="run only the signed arithmetic/control-flow success fixture")
    args = parser.parse_args()

    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    variables_manifest_path = rom.with_suffix(rom.suffix + ".variables.json")
    try:
        variables_manifest = json.loads(variables_manifest_path.read_text(encoding="utf-8"))
        require(variables_manifest.get("format") == "same-scumm-v5-global-variables",
                "unexpected generated global-variable manifest")
        variable_base = int(str(variables_manifest["table_base"]), 16)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise GateFailure(f"invalid generated variable manifest: {exc}") from exc
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    extended_fixture = ROOT / "examples" / "resources" / "scumm_v5" / "c2_extended.scrp"
    output = (args.output or ROOT / "build" / f"scumm-c2-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C2-independent-scumm-matrix",
        "result": "running",
        "rom": str(rom),
        "rom_sha256": rom_hash,
        "fresh_power_on": True,
        "frame_limit": 119,
        "selected_case": "extended-only" if args.only_extended else "full-matrix",
        "semantic_operations": [
            "write_variable", "multiply", "divide", "and", "or",
            "decrement_variable", "branch_less_than", "branch_greater_than",
            "branch_less_equal", "branch_greater_equal", "branch_not_equal",
            "branch_equal_zero", "branch_not_equal_zero", "delay_variable",
            "stop_object_code",
        ],
        "host_reference": {
            "fixture": "examples/resources/scumm_v5/c2_extended.scrp",
            "fixture_sha256": hashlib.sha256(extended_fixture.read_bytes()).hexdigest(),
            "test": "tests.test_scumm_v5_engine.ScummV5EngineTests.test_c2_extended_fixture_has_exact_signed_trace",
        },
        "global_variable_table_base": f"${variable_base:06X}",
        "variable_manifest": str(variables_manifest_path.relative_to(ROOT)),
        "fixture_initial_globals_seeded": 16,
        "donor_rom_used": False,
        "screenshots_captured": False,
        "audio_captured": False,
        "cases": [],
    }

    base_variable_expectations = {
        "0": 0, "1": 13, "2": 0xFFFE, "3": 0x1111,
        "4": 0, "5": 2,
    }
    success = [
        {"pc": 96, "status": 3, "error": 0, "delay": 2, "last_opcode": 0x2B, "frame_count": 1, "frame_ops": 17, "total_ops": 17, "variable_expectations": base_variable_expectations},
        {"pc": 96, "status": 3, "error": 0, "delay": 1, "last_opcode": 0x2B, "frame_count": 2, "frame_ops": 0, "total_ops": 17, "variable_expectations": base_variable_expectations},
        {"pc": 96, "status": 3, "error": 0, "delay": 0, "last_opcode": 0x2B, "frame_count": 3, "frame_ops": 0, "total_ops": 17, "variable_expectations": base_variable_expectations},
        {"pc": 102, "status": 4, "error": 0, "delay": 0, "last_opcode": 0x00, "frame_count": 4, "frame_ops": 2, "total_ops": 19, "variable_expectations": {**base_variable_expectations, "6": 13}},
    ]
    failures = [
        (2, "unknown_opcode", {"pc": 1, "status": 0xFF, "error": 3, "last_opcode": 0x2F, "frame_ops": 1, "total_ops": 1}),
        (3, "bad_variable", {"pc": 3, "status": 0xFF, "error": 2, "last_opcode": 0x1A, "frame_ops": 1, "total_ops": 1}),
        (4, "truncated_operand", {"pc": 2, "status": 0xFF, "error": 1, "last_opcode": 0x1A, "frame_ops": 1, "total_ops": 1}),
        (5, "budget_exhaustion", {"pc": 96, "status": 0xFF, "error": 4, "last_opcode": 0x46, "frame_ops": 32, "total_ops": 32, "variable_expectations": {"0": 32}}),
        (6, "division_by_zero", {"pc": 10, "status": 0xFF, "error": 6, "last_opcode": 0x5B, "frame_ops": 2, "total_ops": 2, "variable_expectations": {"0": 0, "1": 9}}),
        (7, "jump_escape", {"pc": 0x8002, "status": 0xFF, "error": 1, "last_opcode": 0x18, "frame_ops": 1, "total_ops": 1}),
        (8, "delay_range", {"pc": 1, "status": 0xFF, "error": 5, "last_opcode": 0x2E, "frame_ops": 1, "total_ops": 1}),
    ]

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom,
            mesen=nexen,
            cwd=ROOT,
            port=args.port,
            boot_wait=2.0,
            socket_timeout=30.0,
            stderr_log=output / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")

            # Let reset/boot initialize the control bytes before selecting the
            # first case; otherwise Engine_Boot correctly overwrites a write
            # made while the reset vector has not executed yet.
            step_video_frame(session)
            report["bootstrap"] = snapshot(session, variable_base)
            # The micro-fixture's host VM starts with zeroed globals. Some
            # native diagnostic profiles intentionally use a source-sized
            # table without the full-game startup initializer, so establish
            # the same explicit precondition before asking it to execute.
            session.write_memory("snesMemory", variable_base, "00" * (16 * 2))
            session.write_u8(FIXTURE_REQUEST, 1)
            extended_observations: list[dict[str, object]] = []
            completed: dict[int, dict[str, object]] = {}
            # Some feature-complete SCUMM builds spend several video frames
            # in reset/audio initialization before the first semantic engine
            # frame.  Wait for the fixture's VM frame counter, not an assumed
            # video-frame offset; the global gate below still bounds the run.
            for _ in range(32):
                step_video_frame(session)
                state = snapshot(session, variable_base)
                state["video_frame"] = session.get_state()["frameCount"]
                extended_observations.append(state)
                frame = int(state["frame_count"])
                if state["fixture_active"] == 1 and 1 <= frame <= 4 and frame not in completed:
                    completed[frame] = state
                if frame == 4:
                    break
            report["extended_observations"] = extended_observations
            require(sorted(completed) == [1, 2, 3, 4], f"extended: observed completed ticks {sorted(completed)}")
            for index, expectation in enumerate(success, start=1):
                assert_fields("extended", completed[index], expectation)
            report["cases"].append({"id": 1, "name": "extended", "result": "pass", "timeline": [completed[index] for index in range(1, 5)]})

            for fixture_id, name, expectation in (() if args.only_extended else failures):
                # VM error is terminal for that cold engine instance. Start
                # each fail-closed case from a fresh boot rather than relying
                # on an errored scheduler to accept another fixture request.
                session.pause()
                session.tool("reset_emulator", {"power": True})
                session.pause()
                require(session.get_state()["frameCount"] == 0,
                        f"{name}: power reset did not reach frame zero")
                case_video_frames = step_video_frame(session)
                session.write_memory("snesMemory", variable_base, "00" * (16 * 2))
                session.write_u8(FIXTURE_REQUEST, fixture_id)
                observations = []
                terminal = None
                for _ in range(32):
                    case_video_frames += step_video_frame(session)
                    state = snapshot(session, variable_base)
                    state["video_frame"] = session.get_state()["frameCount"]
                    observations.append(state)
                    if state["fixture_active"] == fixture_id and state["status"] == 0xFF:
                        terminal = state
                        break
                if terminal is None:
                    report["failed_case_observations"] = {
                        "id": fixture_id, "name": name, "observations": observations,
                    }
                    raise GateFailure(f"{name}: no error terminal state")
                assert_fields(name, terminal, expectation)
                report["cases"].append({"id": fixture_id, "name": name, "result": "pass", "terminal": terminal, "observations": observations, "video_frames": case_video_frames})

            report["video_frames_used"] = session.get_state()["frameCount"]
            require(int(report["video_frames_used"]) < 120, "last isolated case exceeded its 119-frame limit")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C2 SCUMM matrix: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"C2 SCUMM matrix: PASS ({len(report['cases'])} cases, {report['video_frames_used']} video frames)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
