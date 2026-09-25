#!/usr/bin/env python3
"""Prove non-SCUMM QTMA play/completion/stop through real S-SMP/DSP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_scumm_s6_tad_nexen import (
    DEFAULT_NEXEN, GateFailure, require, tad_state, u16, wav_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/same-qtma-m11.sfc"
CAPTURE_FRAMES = 480


def audio_trace(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", 0x7E2B30, 0x3A)
    count = raw[0]
    return {
        "count": count,
        "opcodes": list(raw[1:1 + count]),
        "sources": list(raw[9:9 + count]),
        "destinations": list(raw[17:17 + count]),
        "arg0": [u16(raw, 0x1A + index * 2) for index in range(count)],
        "arg1": [u16(raw, 0x2A + index * 2) for index in range(count)],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44031)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (
        args.output or ROOT / "build" / f"qtma-m11-runtime-{rom_hash[:16]}"
    ).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    wav_path = output / "qtma-runtime-tad.wav"
    report: dict[str, object] = {
        "gate": "M11-QTMA-runtime", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash,
        "capture_frames": CAPTURE_FRAMES, "fresh_power_on": True,
    }

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port, boot_wait=2.0,
            socket_timeout=60.0, stderr_log=output / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            session.record_audio(wav_path)
            transitions: list[dict[str, int]] = []
            prior_status = 0
            for _index in range(CAPTURE_FRAMES):
                step = session.run_frames(1)
                require(
                    step["framesAdvanced"] == 1 and not step["timedOut"],
                    "QTMA runtime frame timed out",
                )
                raw = session.read_memory("snesMemory", 0x7E2210, 0x1A)
                frame = u16(raw, 0)
                status = u16(raw, 0x18)
                if status != prior_status:
                    transitions.append({"frame": frame, "status": status})
                    prior_status = status
            session.stop_audio()

            audio = wav_evidence(wav_path)
            trace = audio_trace(session)
            final_tad = tad_state(session)
            kernel = session.read_memory("snesMemory", 0x7E2000, 0x0A)
            engine = session.read_memory("snesMemory", 0x7E2220, 0x0C)
            require(engine[0] == 4 and engine[1] == 2,
                    f"QTMA engine identity/lifecycle differs: {engine[0:2].hex()}")
            require(u16(engine, 8) == 2, "QTMA completion status was not retained")
            require(transitions == [
                {"frame": 120, "status": 1},
                {"frame": 423, "status": 2},
            ], f"QTMA play/completion schedule differs: {transitions}")
            require(trace == {
                "count": 2, "opcodes": [0, 1], "sources": [6, 6],
                "destinations": [4, 4], "arg0": [1, 0], "arg1": [0, 0],
            }, f"generic audio service trace differs: {trace}")
            require(u16(kernel, 8) == 0, "required event packet was rejected")
            require(
                final_tad["state"] == 0x82 and final_tad["ready"] == 1
                and final_tad["next_song"] == 0 and final_tad["rejected"] == 0,
                f"TAD completion/blank state differs: {final_tad}",
            )
            require(
                audio["peak"] > 100 and audio["peak"] < 32767
                and audio["mean_square"] > 1000,
                f"QTMA real-DSP capture is silent or clipped: {audio}",
            )
            require(
                audio["first_audible_seconds"] is not None
                and 2.30 <= audio["first_audible_seconds"] <= 2.50,
                f"QTMA entrance timing differs: {audio}",
            )
            require(
                audio["last_audible_seconds"] is not None
                and 4.90 <= audio["last_audible_seconds"] <= 5.20,
                f"QTMA tail timing differs: {audio}",
            )
            report.update({
                "result": "pass", "status_transitions": transitions,
                "audio_service_trace": trace, "final_tad_state": final_tad,
                "audio": audio,
            })
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if wav_path.exists():
            try:
                report["audio"] = wav_evidence(wav_path)
            except Exception:
                pass
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"M11 QTMA runtime: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"M11 QTMA runtime: PASS ({rom_hash})")
    print(report_path)
    print(hashlib.sha256(report_path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
