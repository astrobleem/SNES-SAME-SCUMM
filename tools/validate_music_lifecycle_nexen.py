#!/usr/bin/env python3
"""Prove generic compiled-music lifecycle responses through real S-SMP/DSP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_scumm_s6_tad_nexen import (
    DEFAULT_NEXEN, require, tad_state, u16, wav_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/same-qtma-m12.sfc"
CAPTURE_FRAMES = 480
ENGINE_OFFSET = 0x10
LIFECYCLE_OFFSET = 0x95A


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
    parser.add_argument("--gate", default="M12-generic-music-lifecycle")
    parser.add_argument("--duration-frames", type=int, default=288)
    parser.add_argument("--lifecycle-complete-frame", type=int, default=423)
    parser.add_argument("--engine-complete-frame", type=int, default=424)
    parser.add_argument("--last-audible-min", type=float, default=4.90)
    parser.add_argument("--last-audible-max", type=float, default=5.20)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (
        args.output or ROOT / "build" / f"music-lifecycle-m12-{rom_hash[:16]}"
    ).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    wav_path = output / "music-lifecycle-tad.wav"
    report: dict[str, object] = {
        "gate": args.gate, "result": "running",
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
            engine_transitions: list[dict[str, int]] = []
            lifecycle_transitions: list[dict[str, int]] = []
            prior_engine = 0
            prior_lifecycle = 0
            for _index in range(CAPTURE_FRAMES):
                step = session.run_frames(1)
                require(
                    step["framesAdvanced"] == 1 and not step["timedOut"],
                    "music lifecycle frame timed out",
                )
                raw = session.read_memory("snesMemory", 0x7E2210, 0x960)
                frame = u16(raw, 0)
                engine_status = u16(raw, ENGINE_OFFSET + 8)
                lifecycle_status = raw[LIFECYCLE_OFFSET]
                if engine_status != prior_engine:
                    engine_transitions.append({"frame": frame, "status": engine_status})
                    prior_engine = engine_status
                if lifecycle_status != prior_lifecycle:
                    lifecycle_transitions.append({"frame": frame, "status": lifecycle_status})
                    prior_lifecycle = lifecycle_status
            session.stop_audio()

            audio = wav_evidence(wav_path)
            trace = audio_trace(session)
            final_tad = tad_state(session)
            kernel = session.read_memory("snesMemory", 0x7E2000, 0x0A)
            engine = session.read_memory("snesMemory", 0x7E2220, 0x0C)
            lifecycle = session.read_memory("snesMemory", 0x7E2B6A, 0x06)
            report.update({
                "engine_transitions": engine_transitions,
                "lifecycle_transitions": lifecycle_transitions,
                "audio_service_trace": trace, "final_tad_state": final_tad,
                "final_lifecycle": {
                    "status": lifecycle[0], "logical_id": lifecycle[1],
                    "duration_frames": u16(lifecycle, 2),
                    "deadline_frame": u16(lifecycle, 4),
                },
                "audio": audio,
            })
            require(engine[0] == 4 and engine[1] == 2,
                    f"QTMA engine identity/lifecycle differs: {engine[0:2].hex()}")
            require(u16(engine, 8) == 3, "response-driven completion was not retained")
            require(engine_transitions == [
                {"frame": 120, "status": 1},
                {"frame": 136, "status": 2},
                {"frame": args.engine_complete_frame, "status": 3},
            ], f"engine response schedule differs: {engine_transitions}")
            require(lifecycle_transitions == [
                {"frame": 120, "status": 1},
                {"frame": 135, "status": 2},
                {"frame": args.lifecycle_complete_frame, "status": 3},
            ], f"generic lifecycle schedule differs: {lifecycle_transitions}")
            require(trace == {
                "count": 2, "opcodes": [0, 1], "sources": [6, 6],
                "destinations": [4, 4], "arg0": [1, 0], "arg1": [0, 0],
            }, f"generic audio service trace differs: {trace}")
            expected_lifecycle = bytes((
                3, 1,
                args.duration_frames & 0xFF, args.duration_frames >> 8,
                args.lifecycle_complete_frame & 0xFF,
                args.lifecycle_complete_frame >> 8,
            ))
            require(
                lifecycle == expected_lifecycle,
                f"final lifecycle state differs: {lifecycle.hex()}",
            )
            require(u16(kernel, 8) == 0, "required event packet was rejected")
            require(
                final_tad["state"] == 0x82 and final_tad["ready"] == 1
                and final_tad["next_song"] == 0 and final_tad["rejected"] == 0,
                f"TAD completion/blank state differs: {final_tad}",
            )
            require(
                audio["peak"] > 100 and audio["peak"] < 32767
                and audio["mean_square"] > 1000,
                f"music lifecycle DSP capture is silent or clipped: {audio}",
            )
            require(
                audio["first_audible_seconds"] is not None
                and 2.30 <= audio["first_audible_seconds"] <= 2.50,
                f"music lifecycle entrance timing differs: {audio}",
            )
            require(
                audio["last_audible_seconds"] is not None
                and args.last_audible_min <= audio["last_audible_seconds"]
                <= args.last_audible_max,
                f"music lifecycle tail timing differs: {audio}",
            )
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if wav_path.exists() and "audio" not in report:
            try:
                report["audio"] = wav_evidence(wav_path)
            except Exception:
                pass
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"{args.gate}: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{args.gate}: PASS ({rom_hash})")
    print(report_path)
    print(hashlib.sha256(report_path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
