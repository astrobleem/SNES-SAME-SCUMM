#!/usr/bin/env python3
"""Copyright-free SNES transactional truncated actor-talk proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_scumm_message_talk_nexen import talk_snapshot
from validate_scumm_m25_authentic_next_nexen import snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=45440)
    args = parser.parse_args()
    require(args.rom.is_file() and args.manifest.is_file(), "input is missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    manifest = json.loads(args.manifest.read_text())
    require(manifest.get("case") == "message-malformed", "wrong validator manifest")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    terminal = None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=90.0,
        stderr_log=args.output.parent / "message-malformed-nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        for frame in range(1, 61):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "emulator timeout")
            talk = talk_snapshot(session, frame)
            engine = snapshot(session, frame)
            if talk["charinc"] == 4 and engine["error"]:
                terminal = {"talk": talk, "engine": engine}
                break

    require(terminal is not None, "truncated print did not fail closed")
    talk = terminal["talk"]
    require(terminal["engine"]["error"] == 0x01
            and terminal["engine"]["last_opcode"] == 0x14,
            f"truncated fetch did not report canonical EOF at print: {terminal}")
    require(talk["active"] == 0 and talk["internal_have_msg"] == 0,
            f"malformed print acquired talk ownership: {talk}")
    require(talk["start_count"] == talk["stop_count"] == talk["completion_count"] == 0,
            f"malformed print emitted lifecycle events: {talk}")
    require(talk["events"] == [] and talk["var_have_msg"] == 0,
            f"malformed print partially mutated script-visible state: {talk}")

    report = {
        "gate": "M25-copyright-free-truncated-message-SNES", "result": "pass",
        "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "record_sha256": manifest["records"][0]["record_sha256"],
        "terminal": terminal,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
