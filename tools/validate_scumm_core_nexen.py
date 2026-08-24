#!/usr/bin/env python3
"""Validate the independent SCUMM v5 semantic nucleus in under 120 frames."""

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
STATE_LENGTH = 0x48


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", STATE_ADDRESS, STATE_LENGTH)
    variables = [u16(raw, 0x20 + index * 2) for index in range(16)]
    return {
        "pc": u16(raw, 0x00),
        "status": raw[0x02],
        "error": raw[0x03],
        "delay": u16(raw, 0x04),
        "last_opcode": raw[0x06],
        "frame_count": u16(raw, 0x08),
        "frame_ops": u16(raw, 0x0A),
        "total_ops": u16(raw, 0x0C),
        "variables": variables,
    }


def assert_checkpoint(observed: dict[str, object], expected: dict[str, object]) -> None:
    for key, value in expected.items():
        require(observed[key] == value, f"frame {observed['frame_count']}: {key}={observed[key]!r}, expected {value!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43986)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-core-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "C1-independent-scumm-core",
        "result": "running",
        "rom": str(rom),
        "rom_sha256": rom_hash,
        "fresh_power_on": True,
        "frame_limit": 119,
        "donor_rom_used": False,
        "screenshots_captured": False,
        "audio_captured": False,
        "timeline": [],
        "observations": [],
    }
    expected = [
        {"pc": 40, "status": 2, "error": 0, "delay": 0, "last_opcode": 0x80, "frame_ops": 7, "total_ops": 7, "variables": [0, 12, 0x1111] + [0] * 13},
        {"pc": 47, "status": 3, "error": 0, "delay": 2, "last_opcode": 0x2E, "frame_ops": 2, "total_ops": 9, "variables": [0, 13, 0x1111] + [0] * 13},
        {"pc": 47, "status": 3, "error": 0, "delay": 1, "last_opcode": 0x2E, "frame_ops": 0, "total_ops": 9, "variables": [0, 13, 0x1111] + [0] * 13},
        {"pc": 47, "status": 3, "error": 0, "delay": 0, "last_opcode": 0x2E, "frame_ops": 0, "total_ops": 9, "variables": [0, 13, 0x1111] + [0] * 13},
        {"pc": 61, "status": 4, "error": 0, "delay": 0, "last_opcode": 0x00, "frame_ops": 3, "total_ops": 12, "variables": [0, 13, 0x1111, 13] + [0] * 12},
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
            observed_frames: dict[int, dict[str, object]] = {}
            for _ in range(12):
                for _attempt in range(20):
                    run = session.run_frames(1)
                    if run["framesAdvanced"] == 1:
                        break
                require(run["framesAdvanced"] == 1, f"one-frame step made no progress: {run}")
                state = snapshot(session)
                state["video_frame"] = session.get_state()["frameCount"]
                state["cpu"] = session.get_cpu_state()
                report["observations"].append(state)
                frame = int(state["frame_count"])
                if 1 <= frame <= len(expected) and frame not in observed_frames:
                    observed_frames[frame] = state
                if frame >= len(expected):
                    break

            require(len(observed_frames) == len(expected), f"only observed semantic frames {sorted(observed_frames)}")
            for index, expectation in enumerate(expected, start=1):
                observed = observed_frames[index]
                assert_checkpoint(observed, expectation)
                report["timeline"].append(observed)
            report["video_frames_used"] = session.get_state()["frameCount"]
            require(int(report["video_frames_used"]) < 120, "gate exceeded its 119-frame limit")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"C1 SCUMM core: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"C1 SCUMM core: PASS ({report['video_frames_used']} video frames)")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
