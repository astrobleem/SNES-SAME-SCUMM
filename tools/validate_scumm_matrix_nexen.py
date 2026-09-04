#!/usr/bin/env python3
"""Validate canonical SCUMM v5 matrixOps sub-op 1 in fresh Nexen processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
COMMON = 0x7E2300
FIXTURE_REQUEST = 0x7E235E
MATRIX = 0x7FFA40
FIXTURES = {
    "set_box_flags": 0x47,
    "missing": 0x48,
    "invalid": 0x49,
    "subop2": 0x4A,
    "subop3": 0x4B,
    "subop4": 0x4C,
    "unknown": 0x4D,
}


class GateFailure(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON, 0x64)
    matrix = session.read_memory("snesMemory", MATRIX, 0x125)
    return {
        "pc": u16(common), "status": common[2], "error": common[3],
        "last_opcode": common[6], "frame_ops": u16(common, 10),
        "total_ops": u16(common, 12), "fixture_active": common[0x5F],
        "program": common[0x62], "box_count": matrix[0],
        "box_flags": list(matrix[1:4]), "subopcode": matrix[0x100],
        "box": matrix[0x101], "flags": matrix[0x102],
        "executions": matrix[0x103],
    }


def step(session: object) -> None:
    for _ in range(20):
        result = session.run_frames(1)
        if result["framesAdvanced"] == 1:
            return
    raise GateFailure(f"video frame did not advance: {result}")


def run_case(mcp_session: object, rom: Path, nexen: Path, output: Path,
             name: str, fixture: int, port: int) -> dict[str, object]:
    with mcp_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=port, boot_wait=2.0,
        socket_timeout=30.0, stderr_log=output / f"{name}-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, f"{name}: reset was not frame zero")
        step(session)
        session.write_u8(FIXTURE_REQUEST, fixture)
        state = snapshot(session)
        for _ in range(12):
            step(session)
            state = snapshot(session)
            if state["fixture_active"] == fixture and state["status"] in (2, 4, 0xFF):
                if name != "set_box_flags" or state["pc"] == 39:
                    break
        return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44910)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM missing: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen unavailable: {nexen}")
    digest = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / f"build/scumm-matrix-nexen-{digest[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    cases = {
        name: run_case(mcp_session, rom, nexen, output, name, fixture, args.port + index)
        for index, (name, fixture) in enumerate(FIXTURES.items())
    }
    good = cases["set_box_flags"]
    require(good["pc"] == 39 and good["status"] == 2 and good["error"] == 0,
            f"valid matrix fixture did not yield at exact end: {good}")
    require(good["box_count"] == 3 and good["box_flags"] == [0, 0x44, 0x80],
            f"direct/variable/replacement results differ: {good}")
    require(good["executions"] == 5 and good["subopcode"] == 1
            and good["box"] == 0xFF and good["flags"] == 0x99,
            f"matrix decode trace differs: {good}")
    missing = cases["missing"]
    require(missing["pc"] == 5 and missing["status"] == 4 and missing["error"] == 0
            and missing["box_count"] == 0 and missing["executions"] == 0,
            f"missing matrix policy differs: {missing}")
    invalid = cases["invalid"]
    require(invalid["pc"] == 4 and invalid["status"] == 0xFF
            and invalid["error"] == 0x0C and invalid["executions"] == 0,
            f"invalid box policy differs: {invalid}")
    for name in ("subop2", "subop3", "subop4", "unknown"):
        state = cases[name]
        require(state["pc"] == 2 and state["status"] == 0xFF
                and state["error"] == 3 and state["executions"] == 0,
                f"{name} did not fail closed after its subopcode: {state}")
    report = {
        "gate": "matrixOps-setBoxFlags", "result": "pass", "rom": str(rom),
        "rom_sha256": digest, "fresh_process_per_case": True, "cases": cases,
    }
    path = output / "report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "report": str(path), "rom_sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
