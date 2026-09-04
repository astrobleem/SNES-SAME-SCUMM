#!/usr/bin/env python3
"""Copyright-free SNES waitForMessage lifecycle conformance proof."""

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
    parser.add_argument("--port", type=int, default=45340)
    args = parser.parse_args()
    require(args.rom.is_file() and args.manifest.is_file(), "input is missing")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK), "Nexen unavailable")
    manifest = json.loads(args.manifest.read_text())
    require(manifest.get("case") == "message", "wrong validator manifest")
    identities = {item["number"]: item for item in manifest["records"][0]["scripts"]}
    require({200, 201}.issubset(identities), "parent/child LSCR descriptors are absent")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    started = completed = resumed = None
    timeline = []
    previous = None
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=2.0, socket_timeout=90.0,
        stderr_log=args.output.parent / "message-wait-nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        for frame in range(1, 161):
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "emulator timeout")
            talk = talk_snapshot(session, frame)
            engine = snapshot(session, frame)
            key = (talk["active"], talk["delay"], talk["var_have_msg"],
                   talk["wait_blocks"], talk["wait_resumes"],
                   engine["error"], engine["status"])
            initialized = talk["charinc"] == 4 and talk["raw_length"] <= 32
            if initialized and key != previous:
                timeline.append({"talk": talk, "engine": engine})
                previous = key
            if (started is None and initialized and talk["start_count"] == 1
                    and talk["active"] == 1 and talk["encoded"] == [ord("A"), 0]):
                started = {"talk": talk, "engine": engine}
            if (completed is None and initialized and talk["completion_count"] == 1
                    and talk["stop_count"] == 1 and talk["generation"] == 1):
                completed = {"talk": talk, "engine": engine}
            variables = session.read_memory("snesMemory", 0x7E2320, 24)
            var10 = variables[20] | variables[21] << 8
            if var10 == 1:
                resumed = {"talk": talk, "engine": engine, "var10": var10}
                break

    require(started is not None and completed is not None and resumed is not None,
            f"message/wait lifecycle incomplete: {timeline[-1] if timeline else None}")
    start = started["talk"]
    done = completed["talk"]
    proceed = resumed["talk"]
    require(start["encoded"] == [ord("A"), 0] and start["delay"] == 64,
            f"fixture message initialization differs: {start}")
    require(start["wait_blocks"] >= 1 and start["wait_resumes"] == 0,
            f"child did not immediately block: {start}")
    require(done["completed_logical_frame"] - done["started_logical_frame"] == 16,
            f"64-jiffy completion is not 16 loops: {done}")
    require(done["var_have_msg"] == 1 and done["wait_resumes"] == 0,
            f"wait advanced in the completion loop: {done}")
    require(proceed["var_have_msg"] == 0 and proceed["wait_resumes"] == 1,
            f"wait did not resume on the published-clear loop: {proceed}")
    require(resumed["engine"]["error"] == 0 and resumed["var10"] == 1,
            f"post-wait instruction did not execute normally: {resumed}")

    report = {
        "gate": "M25-copyright-free-waitForMessage-SNES", "result": "pass",
        "fresh_power_on": True, "debugger_writes": 0,
        "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
        "manifest": str(args.manifest),
        "record_sha256": manifest["records"][0]["record_sha256"],
        "parent_descriptor": identities[200], "child_descriptor": identities[201],
        "started": started, "completed": completed, "resumed": resumed,
        "timeline": timeline,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
