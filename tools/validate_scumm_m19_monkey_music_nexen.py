#!/usr/bin/env python3
"""Prove Monkey church music through the normal SNES SCUMM runtime path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_monkey_v5_tad_nexen import loop_evidence
from validate_scumm_s6_tad_nexen import (
    DEFAULT_NEXEN, GateFailure, require, run_exact_frames, tad_state, u16,
    wav_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/same-scumm-v5-monkey-m19.sfc"
FIXTURE_REQUEST = 0x7E235E
FIXTURE_ACTIVE = 0x7E235F
SCUMM_STATE = 0x7E2300
SCUMM_VARIABLES = 0x7E2320
AUDIO_TRACE = 0x7E2B30
EVENT_STATE = 0x7E2000
TAD_PROBE_REQUEST = 0x7E225D
AUDIO_MUSIC_LOGICAL = 0x7FF24D
M19_FIXTURE_ID = 0x38
LOGICAL_SOUND = 154
COMPILED_SONG = 26
LOOP_TICKS = 7172
LOOP_CAPTURE_FRAMES = 3900


def audio_trace(session: object) -> list[dict[str, int]]:
    raw = session.read_memory("snesMemory", AUDIO_TRACE, 0x3A)
    count = min(raw[0], 8)
    return [
        {
            "opcode": raw[1 + index],
            "source": raw[9 + index],
            "destination": raw[17 + index],
            "arg0": u16(raw, 0x1A + index * 2),
            "arg1": u16(raw, 0x2A + index * 2),
        }
        for index in range(count)
    ]


def scumm_snapshot(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", SCUMM_STATE, 0x64)
    variables = session.read_memory("snesMemory", SCUMM_VARIABLES, 6)
    return {
        "pc": u16(raw, 0),
        "status": raw[2],
        "error": raw[3],
        "delay": u16(raw, 4),
        "last_opcode": raw[6],
        "frame_count": u16(raw, 8),
        "frame_ops": u16(raw, 10),
        "total_ops": u16(raw, 12),
        "fixture_active": raw[0x5F],
        "program_select": raw[0x62],
        "status_results": [u16(variables, index * 2) for index in range(3)],
        "audio_music_logical": session.read_memory(
            "snesMemory", AUDIO_MUSIC_LOGICAL, 1
        )[0],
    }


def step_frame(session: object) -> None:
    step = session.run_frames(1)
    require(
        step["framesAdvanced"] == 1 and not step["timedOut"],
        "M19 video frame timed out",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44038)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (
        args.output or ROOT / "build" / f"scumm-m19-monkey-{rom_hash[:16]}"
    ).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    lifecycle_wav = output / "monkey-m19-start-stop-restart.wav"
    loop_wav = output / "monkey-m19-restarted-loop.wav"
    report: dict[str, object] = {
        "gate": "M19-normal-path-Monkey-church",
        "result": "running",
        "rom": str(rom),
        "rom_sha256": rom_hash,
        "fresh_power_on": True,
        "fixture_id": M19_FIXTURE_ID,
        "logical_sound_id": LOGICAL_SOUND,
        "compiled_song_id": COMPILED_SONG,
        "direct_logical_request_writes": 0,
        "loop_capture_frames": LOOP_CAPTURE_FRAMES,
    }

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port, boot_wait=2.0,
            socket_timeout=90.0, stderr_log=output / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")

            boot_timeline = []
            for _ in range(300):
                step_frame(session)
                state = tad_state(session)
                boot_timeline.append({"video_frame": session.get_state()["frameCount"], **state})
                require(
                    session.read_memory("snesMemory", TAD_PROBE_REQUEST, 1)[0] == 0,
                    "debugger logical-request seam changed during boot",
                )
                if state["state"] == 0x82 and state["ready"] == 1:
                    break
            else:
                raise GateFailure(f"M19 TAD boot did not reach PLAYING: {boot_timeline[-1]}")
            require(state["next_song"] == 0 and state["rejected"] == 0,
                    f"M19 blank boot state differs: {state}")

            session.record_audio(lifecycle_wav)
            # This is the only debugger write that starts the gate. It selects
            # copyright-free bytecode; sound 154 itself is requested by $02.
            session.write_u8(FIXTURE_REQUEST, M19_FIXTURE_ID)
            transitions: list[dict[str, object]] = []
            checkpoints: dict[str, dict[str, object]] = {}
            prior_key: tuple[object, ...] | None = None
            restart_ready_frame = None
            for _ in range(2500):
                step_frame(session)
                require(
                    session.read_memory("snesMemory", TAD_PROBE_REQUEST, 1)[0] == 0,
                    "debugger logical-request seam was used",
                )
                scumm = scumm_snapshot(session)
                tad = tad_state(session)
                trace = audio_trace(session)
                report["last_runtime_observation"] = {
                    "video_frame": session.get_state()["frameCount"],
                    "scumm": scumm, "tad": tad, "audio_service_trace": trace,
                }
                key = (
                    scumm["pc"], scumm["status"], scumm["delay"],
                    tuple(scumm["status_results"]), len(trace), tad["state"],
                    tad["next_song"], scumm["audio_music_logical"],
                )
                if key != prior_key:
                    transitions.append({
                        "video_frame": session.get_state()["frameCount"],
                        "scumm": scumm, "tad": tad, "audio_packet_count": len(trace),
                    })
                    prior_key = key
                results = scumm["status_results"]
                if results[0] == 1 and "started_running" not in checkpoints:
                    checkpoints["started_running"] = transitions[-1]
                if (
                    len(trace) >= 2 and scumm["pc"] >= 21
                    and results[:2] == [1, 0] and "stopped" not in checkpoints
                ):
                    checkpoints["stopped"] = transitions[-1]
                if results == [1, 0, 1] and "restarted_running" not in checkpoints:
                    checkpoints["restarted_running"] = transitions[-1]
                if (
                    len(trace) == 3 and results == [1, 0, 1]
                    and tad["state"] == 0x82 and tad["ready"] == 1
                    and tad["next_song"] == COMPILED_SONG
                ):
                    restart_ready_frame = session.get_state()["frameCount"]
                    break
            else:
                raise GateFailure("M19 fixture did not complete start/stop/restart within 2500 frames")
            session.stop_audio()

            trace = audio_trace(session)
            require(trace == [
                {"opcode": 0, "source": 6, "destination": 4, "arg0": 154, "arg1": 1},
                {"opcode": 1, "source": 6, "destination": 4, "arg0": 0, "arg1": 0},
                {"opcode": 0, "source": 6, "destination": 4, "arg0": 154, "arg1": 1},
            ], f"normal SCUMM audio packet trace differs: {trace}")
            require(set(checkpoints) == {"started_running", "stopped", "restarted_running"},
                    f"SCUMM status checkpoints differ: {checkpoints}")
            require(any(
                item["audio_packet_count"] == 2 and item["tad"]["state"] == 0x82
                and item["tad"]["next_song"] == 0
                for item in transitions
            ), "stopMusic never completed the blank-song TAD lifecycle")

            lifecycle_audio = wav_evidence(lifecycle_wav)
            require(lifecycle_audio["peak"] > 0 and lifecycle_audio["peak"] < 32767,
                    f"M19 start/stop/restart capture is silent or clipped: {lifecycle_audio}")

            loop_start_video = session.get_state()["frameCount"]
            loop_start_counter = u16(session.read_memory("snesMemory", 0x7E2210, 2), 0)
            session.record_audio(loop_wav)
            run_exact_frames(session, LOOP_CAPTURE_FRAMES, "M19 restarted loop capture")
            session.stop_audio()
            loop_end_video = session.get_state()["frameCount"]
            loop_end_counter = u16(session.read_memory("snesMemory", 0x7E2210, 2), 0)
            require(
                session.read_memory("snesMemory", TAD_PROBE_REQUEST, 1)[0] == 0,
                "debugger logical-request seam changed during loop capture",
            )
            final_scumm = scumm_snapshot(session)
            final_tad = tad_state(session)
            loop_audio = wav_evidence(loop_wav)
            loop_proof = loop_evidence(loop_wav, LOOP_TICKS)
            kernel = session.read_memory("snesMemory", EVENT_STATE, 10)

            require(final_scumm["fixture_active"] == M19_FIXTURE_ID
                    and final_scumm["program_select"] == M19_FIXTURE_ID
                    and final_scumm["pc"] == 29 and final_scumm["status"] == 2
                    and final_scumm["error"] == 0
                    and final_scumm["status_results"] == [1, 0, 1]
                    and final_scumm["audio_music_logical"] == LOGICAL_SOUND,
                    f"M19 terminal SCUMM state differs: {final_scumm}")
            require(final_tad["state"] == 0x82 and final_tad["ready"] == 1
                    and final_tad["next_song"] == COMPILED_SONG
                    and final_tad["rejected"] == 0,
                    f"M19 final TAD state differs: {final_tad}")
            require(u16(kernel, 6) == 0 and u16(kernel, 8) == 0,
                    f"M19 event loss/rejection differs: {kernel.hex()}")
            require(loop_audio["peak"] > 0 and loop_audio["peak"] < 32767,
                    f"M19 restarted loop capture is silent or clipped: {loop_audio}")
            require(loop_proof["repeat_window_mean_square"] > 100
                    and loop_proof["correlation"] > 0.99,
                    f"M19 accepted Monkey loop is not present: {loop_proof}")
            require(loop_end_video - loop_start_video == LOOP_CAPTURE_FRAMES
                    and (loop_end_counter - loop_start_counter) & 0xFFFF == LOOP_CAPTURE_FRAMES,
                    "M19 loop capture changed video/NMI pacing")

            report.update({
                "result": "pass",
                "boot_timeline": boot_timeline,
                "runtime_transitions": transitions,
                "status_checkpoints": checkpoints,
                "restart_ready_video_frame": restart_ready_frame,
                "audio_service_trace": trace,
                "lifecycle_audio": lifecycle_audio,
                "loop_audio": loop_audio,
                "loop_evidence": loop_proof,
                "final_scumm_state": final_scumm,
                "final_tad_state": final_tad,
                "loop_video_frames": loop_end_video - loop_start_video,
                "loop_same_frame_counter_delta": (
                    loop_end_counter - loop_start_counter
                ) & 0xFFFF,
            })
            report.pop("last_runtime_observation", None)
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        for path, key in ((lifecycle_wav, "lifecycle_audio"), (loop_wav, "loop_audio")):
            if path.exists() and key not in report:
                try:
                    report[key] = wav_evidence(path)
                except Exception:
                    pass
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"M19 normal-path Monkey church: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"M19 normal-path Monkey church: PASS ({rom_hash})")
    print(report_path)
    print(hashlib.sha256(report_path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
