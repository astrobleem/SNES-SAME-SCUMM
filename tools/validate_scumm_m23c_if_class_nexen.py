#!/usr/bin/env python3
"""Copyright-free SNES oracle for canonical v5 ifClassOfIs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REQUEST = 0x7E235E
COMMON = 0x7E2300
VARIABLES = 0x7E2320
VALID_FIXTURE = 0x45
MALFORMED_FIXTURE = 0x46


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def reset(session: object) -> None:
    session.pause()
    session.tool("reset_emulator", {"power": True})
    session.pause()
    require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
    session.run_frames(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/same-scumm-v5.sfc")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44318)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require(args.rom.is_file(), f"ROM not found: {args.rom}")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen is unavailable")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    evidence = {}
    with mcp_session.McpSession(rom=args.rom.resolve(), mesen=args.nexen.resolve(),
            cwd=ROOT, port=args.port, boot_wait=2.0, socket_timeout=30.0,
            stderr_log=ROOT / "build/m23c-if-class-stderr.log") as session:
        reset(session)
        session.write_u8(FIXTURE_REQUEST, VALID_FIXTURE)
        # The copyright-free fixture deliberately exercises four independent
        # branches; allow the normal per-frame opcode budget to retire it.
        session.run_frames(16)
        common = session.read_memory("snesMemory", COMMON, 16)
        variables = session.read_memory("snesMemory", VARIABLES, 8)
        values = [u16(variables, index * 2) for index in range(4)]
        require(common[3] == 0 and values == [11, 0, 33, 0],
                f"canonical class-list results differ: error={common[3]} values={values}")
        evidence["canonical"] = {"fixture": VALID_FIXTURE, "variables": values,
                                 "error": common[3], "fresh_power_on": True}
        reset(session)
        session.write_u8(FIXTURE_REQUEST, MALFORMED_FIXTURE)
        session.run_frames(16)
        common = session.read_memory("snesMemory", COMMON, 16)
        require(common[2] == 0xFF and common[3] == 0x1F,
                f"malformed class selector did not fail closed: {list(common)}")
        evidence["malformed"] = {"fixture": MALFORMED_FIXTURE,
                                 "status": common[2], "error": common[3]}
    digest = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    report = {"gate": "M23C-canonical-ifClassOfIs-SNES", "result": "pass",
              "rom_sha256": digest, "debugger_program_or_pc_writes": 0,
              "evidence": evidence}
    output = args.output or ROOT / f"build/m23c-if-class-{digest[:16]}/report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"PASS rom={digest} report={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
