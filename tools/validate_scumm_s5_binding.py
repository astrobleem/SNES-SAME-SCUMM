#!/usr/bin/env python3
"""Validate active SCUMM host/SNES semantic and service agreement."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from same.engine import EngineHost
from same.engines import default_registry
from same.profile import load_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_s5_conformance.json"
DEFAULT_ROM = ROOT / "build/same-scumm-v5.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
FIXTURE_REQUEST = 0x7E235E
S5_FIXTURE = 0x1E


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def host_trace() -> dict[str, object]:
    host = EngineHost(load_profile(PROFILE), default_registry())
    host.boot()
    timeline = []
    for _ in range(2):
        result = host.tick()
        state = host.engine.inspect_state()
        timeline.append(
            {
                "pc": state["scripts"][0]["pc"],
                "status": 4 if result.halted else 2,
                "error": 0,
                "frame_ops": result.operations,
                "total_ops": state["operations"],
                "variable0": state["variables"].get("0", 0),
            }
        )
    packets = [
        {
            "opcode": packet["opcode"],
            "arg0": packet["arg0"] & 0xFFFF,
            "arg1": packet["arg1"] & 0xFFFF,
            "source": packet["source"],
            "destination": packet["destination"],
        }
        for packet in host.services.packet_history
        if packet["service_name"] == "AUDIO"
    ]
    return {
        "timeline": timeline,
        "audio_packets": packets,
        "dropped": host.services.events.ring.stats.dropped,
        "rejected": host.services.events.ring.stats.rejected,
    }


def snes_snapshot(session: object) -> dict[str, object]:
    event = session.read_memory("snesMemory", 0x7E2000, 12)
    engine = session.read_memory("snesMemory", 0x7E2220, 10)
    scumm = session.read_memory("snesMemory", 0x7E2300, 0x64)
    trace = session.read_memory("snesMemory", 0x7E2B30, 0x3A)
    count = trace[0]
    packets = []
    for index in range(count):
        packets.append(
            {
                "opcode": trace[1 + index],
                "arg0": u16(trace, 0x1A + index * 2),
                "arg1": u16(trace, 0x2A + index * 2),
                "source": trace[9 + index],
                "destination": trace[17 + index],
            }
        )
    return {
        "event_sequence": u16(event, 10),
        "dropped": u16(event, 6),
        "rejected": u16(event, 8),
        "engine_id": engine[0],
        "lifecycle": engine[1],
        "engine_frame_ops": u16(engine, 4),
        "engine_total_ops": u16(engine, 6),
        "pc": u16(scumm, 0),
        "status": scumm[2],
        "error": scumm[3],
        "frame_ops": u16(scumm, 0x0A),
        "total_ops": u16(scumm, 0x0C),
        "variable0": u16(scumm, 0x20),
        "fixture_active": scumm[0x5F],
        "audio_packets": packets,
    }


def step(session: object) -> None:
    for _ in range(20):
        result = session.run_frames(1)
        if result["framesAdvanced"] == 1:
            return
    raise GateFailure(f"one-frame step made no progress: {result}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43989)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-s5-binding-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    expected = host_trace()
    report: dict[str, object] = {
        "gate": "S5-active-scumm-binding",
        "result": "running",
        "rom": str(rom),
        "rom_sha256": rom_hash,
        "fresh_power_on": True,
        "commercial_data_used": False,
        "host": expected,
        "snes": {},
    }

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
            step(session)
            baseline = snes_snapshot(session)
            require(baseline["engine_id"] == 2, "SCUMM is not the active engine")
            require(baseline["lifecycle"] == 2, "active engine is not RUNNING")
            session.write_u8(FIXTURE_REQUEST, S5_FIXTURE)
            timeline = []
            for _ in range(5):
                step(session)
                observed = snes_snapshot(session)
                if observed["fixture_active"] == S5_FIXTURE:
                    timeline.append(observed)
                if len(timeline) == 2:
                    break
            report["snes"] = {"baseline": baseline, "timeline": timeline}
            require(len(timeline) == 2, "S5 fixture did not produce two bounded ticks")

            expected_timeline = expected["timeline"]
            for index, observed in enumerate(timeline):
                host_state = expected_timeline[index]
                for field in ("pc", "status", "error", "frame_ops", "total_ops", "variable0"):
                    require(observed[field] == host_state[field], f"tick {index + 1} {field} disagrees")
                require(observed["engine_frame_ops"] == host_state["frame_ops"], f"tick {index + 1} host op count disagrees")
                require(observed["dropped"] == 0 and observed["rejected"] == 0, "SNES packet loss")
            require(timeline[-1]["audio_packets"] == expected["audio_packets"], "normalized audio packet trace disagrees")
            require(expected["dropped"] == 0 and expected["rejected"] == 0, "host packet loss")
            require(timeline[-1]["event_sequence"] - baseline["event_sequence"] == 4, "SNES did not route exactly four service packets")
            report["video_frames_used"] = session.get_state()["frameCount"]
            require(report["video_frames_used"] < 120, "S5 exceeded bounded frame limit")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"S5 SCUMM binding: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"S5 SCUMM binding: PASS (2 ticks, {report['video_frames_used']} video frames)")
    print(report_path)
    print(f"report sha256: {hashlib.sha256(report_path.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
