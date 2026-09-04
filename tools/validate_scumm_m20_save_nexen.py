#!/usr/bin/env python3
"""Prove deterministic compiled-music restart through real SNES SRAM."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import wave
import zlib

from same.savegame import SaveEnvelope
from validate_scumm_m19_monkey_music_nexen import audio_trace
from validate_scumm_s6_tad_nexen import (
    DEFAULT_NEXEN, GateFailure, require, run_exact_frames, tad_state, u16,
    wav_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/same-scumm-v5-monkey-m20.sfc"
FIXTURE_REQUEST = 0x7E235E
SCUMM_VARIABLES = 0x7E2320
ACTIVE_MUSIC = 0x7FF24D
MUSIC_POSITION = 0x7FF24E
SAVE_STATE = 0x7FF252
M20_START = 0x39
M20_SAVE = 0x3A
M20_LOAD = 0x3B
M20_STOP_SAVE = 0x3C
LOGICAL_SOUND = 154
COMPILED_SONG = 26
RECORD_SIZE = 172
PAYLOAD_OFFSET = 88
PREFIX_FRAMES = 240


def u32(raw: bytes, offset: int = 0) -> int:
    return int.from_bytes(raw[offset:offset + 4], "little")


def save_state(session: object) -> dict[str, int]:
    raw = session.read_memory("snesMemory", SAVE_STATE, 8)
    return {
        "status": raw[0], "error": raw[1], "writes": u16(raw, 2),
        "loads": u16(raw, 4), "rejects": u16(raw, 6),
    }


def step(session: object, label: str) -> None:
    result = session.run_frames(1)
    require(result["framesAdvanced"] == 1 and not result["timedOut"], f"{label} timed out")


def boot_blank(session: object) -> list[dict[str, int]]:
    session.pause()
    session.tool("reset_emulator", {"power": True})
    session.pause()
    timeline = []
    for _ in range(300):
        step(session, "M20 boot")
        state = tad_state(session)
        timeline.append(state)
        if state["state"] == 0x82 and state["ready"] == 1:
            require(state["next_song"] == 0 and state["rejected"] == 0,
                    f"cold boot did not reach clean blank song: {state}")
            return timeline
    raise GateFailure("M20 TAD boot did not become ready")


def wait_song(session: object, song: int, label: str, limit: int = 800) -> list[dict[str, int]]:
    timeline = []
    for _ in range(limit):
        step(session, label)
        state = tad_state(session)
        timeline.append(state)
        if state["state"] == 0x82 and state["ready"] == 1 and state["next_song"] == song:
            return timeline
    raise GateFailure(f"{label} did not reach TAD song {song}: {timeline[-1]}")


def wait_save_status(session: object, expected: int, label: str) -> dict[str, int]:
    for _ in range(30):
        step(session, label)
        state = save_state(session)
        if state["status"] == expected:
            return state
    raise GateFailure(f"{label} did not reach save status {expected:02x}: {state}")


def decode_record(raw: bytes) -> dict[str, object]:
    require(len(raw) == RECORD_SIZE, "M20 SRAM record length differs")
    envelope = SaveEnvelope.unpack(raw)
    payload = envelope.payload
    require(len(payload) == 84 and payload[:8] == b"SCMUSIC\0", "compiled-music subrecord differs")
    return {
        "envelope": envelope.to_dict(),
        "subrecord_version": int.from_bytes(payload[8:10], "little"),
        "policy_id": int.from_bytes(payload[10:12], "little"),
        "logical_sound_id": payload[12], "running": payload[13],
        "advisory_position": int.from_bytes(payload[16:20], "little"),
        "catalog_sha256": payload[20:52].hex(),
        "source_sha256": payload[52:84].hex(),
    }


def mono(path: Path) -> tuple[int, list[int]]:
    with wave.open(str(path), "rb") as audio:
        rate, channels = audio.getframerate(), audio.getnchannels()
        raw = audio.readframes(audio.getnframes())
    values = struct.unpack(f"<{len(raw) // 2}h", raw)
    return rate, [sum(values[i:i + channels]) // channels for i in range(0, len(values), channels)]


def prefix_correlation(reference: Path, candidate: Path) -> dict[str, object]:
    rate_a, left = mono(reference)
    rate_b, right = mono(candidate)
    require(rate_a == rate_b, "M20 prefix sample rates differ")
    first_a = next((i for i, value in enumerate(left) if abs(value) > 8), None)
    first_b = next((i for i, value in enumerate(right) if abs(value) > 8), None)
    require(first_a is not None and first_b is not None, "M20 prefix capture is silent")
    reference_start = first_a + rate_a // 10
    length = min(rate_a, len(left) - reference_start, len(right) - first_b - rate_a // 2)
    require(length >= rate_a, "M20 audible prefix is shorter than one second")
    def correlation(offset: int, stride: int) -> float | None:
        candidate_start = first_b + offset
        if candidate_start < 0 or candidate_start + length > len(right):
            return None
        a = left[reference_start:reference_start + length:stride]
        b = right[candidate_start:candidate_start + length:stride]
        dot = sum(x * y for x, y in zip(a, b))
        power_a = sum(x * x for x in a)
        power_b = sum(y * y for y in b)
        return dot / math.sqrt(max(1, power_a * power_b))
    best_offset = 0
    best = -1.0
    for offset in range(-rate_a // 2, rate_a // 2 + 1, 16):
        score = correlation(offset, 8)
        if score is not None and score > best:
            best_offset, best = offset, score
    for offset in range(best_offset - 16, best_offset + 17):
        score = correlation(offset, 2)
        if score is not None and score > best:
            best_offset, best = offset, score
    return {
        "reference_first_audible_sample": first_a,
        "candidate_first_audible_sample": first_b,
        "compared_samples": length,
        "alignment_offset_samples": best_offset,
        "correlation": round(best, 6),
    }


def mutate_record(raw: bytes, case: str) -> bytes:
    value = bytearray(raw)
    if case == "corrupt":
        value[PAYLOAD_OFFSET + 16] ^= 0x40
    elif case == "wrong_engine":
        value[16] ^= 0x01
    elif case == "wrong_game":
        value[48] ^= 0x01
    elif case == "wrong_schema":
        value[12] ^= 0x01
    elif case == "wrong_catalog":
        value[PAYLOAD_OFFSET + 20] ^= 0x01
        struct.pack_into("<I", value, 84, zlib.crc32(value[PAYLOAD_OFFSET:]) & 0xFFFFFFFF)
    else:
        raise AssertionError(case)
    return bytes(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44050)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-m20-save-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "M20-compiled-music-deterministic-cue-restart",
        "result": "running", "rom": str(rom), "rom_sha256": rom_hash,
        "storage": "real 2 KiB cartridge SRAM", "slot": 99,
        "emulator_savestate_used": False, "logical_position_honored": False,
        "restore_policy": "deterministic_cue_restart",
    }

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    valid_running_record = b""
    direct_wav = output / "direct-start-prefix.wav"
    try:
        checkpoints = (("midpoint", 1719), ("pre_loop", 3436))
        results: dict[str, object] = {}
        for index, (name, frames_after_ready) in enumerate(checkpoints):
            save_port = args.port + index * 2
            direct_path = direct_wav if index == 0 else output / f"{name}-direct-prefix.wav"
            with mcp_session.McpSession(
                rom=rom, mesen=nexen, cwd=ROOT, port=save_port, boot_wait=2.0,
                socket_timeout=90.0, stderr_log=output / f"{name}-save-stderr.log",
            ) as session:
                boot_blank(session)
                session.record_audio(direct_path)
                session.write_u8(FIXTURE_REQUEST, M20_START)
                start_timeline = wait_song(session, COMPILED_SONG, f"{name} normal $02 start")
                run_exact_frames(session, PREFIX_FRAMES, f"{name} direct prefix")
                session.stop_audio()
                remaining = max(0, frames_after_ready - PREFIX_FRAMES)
                run_exact_frames(session, remaining, f"{name} checkpoint wait")
                position_before_save = u32(session.read_memory("snesMemory", MUSIC_POSITION, 4))
                session.write_u8(FIXTURE_REQUEST, M20_SAVE)
                written = wait_save_status(session, 1, f"{name} real save service")
                raw = session.read_memory("snesSaveRam", 0, RECORD_SIZE)
                decoded = decode_record(raw)
                require(decoded["envelope"]["engine"] == "scumm_v5"
                        and decoded["envelope"]["game"] == "monkey1-ultimate-talkie"
                        and decoded["envelope"]["schema"] == 1,
                        f"{name} envelope identity differs: {decoded}")
                require(decoded["subrecord_version"] == 1 and decoded["policy_id"] == 1
                        and decoded["logical_sound_id"] == LOGICAL_SOUND
                        and decoded["running"] == 1,
                        f"{name} compiled-music subrecord differs: {decoded}")
                require(decoded["advisory_position"] == position_before_save + 1,
                        f"{name} advisory position differs")
                if name == "midpoint":
                    valid_running_record = raw
                save_evidence = {
                    "fresh_process": True, "frames_after_tad_ready": frames_after_ready,
                    "position_before_save": position_before_save,
                    "save_state": written, "record_sha256": hashlib.sha256(raw).hexdigest(),
                    "record": decoded, "start_lifecycle": start_timeline,
                    "direct_audio": wav_evidence(direct_path),
                }

            load_path = output / f"{name}-cold-load-prefix.wav"
            with mcp_session.McpSession(
                rom=rom, mesen=nexen, cwd=ROOT, port=save_port + 1, boot_wait=2.0,
                socket_timeout=90.0, stderr_log=output / f"{name}-load-stderr.log",
            ) as session:
                boot_blank(session)
                persisted = session.read_memory("snesSaveRam", 0, RECORD_SIZE)
                require(persisted == raw, f"{name} SRAM did not persist across emulator processes")
                session.record_audio(load_path)
                session.write_u8(FIXTURE_REQUEST, M20_LOAD)
                loaded = wait_save_status(session, 2, f"{name} real cold load")
                lifecycle = wait_song(session, COMPILED_SONG, f"{name} restart from beginning")
                run_exact_frames(session, PREFIX_FRAMES, f"{name} restored prefix")
                session.stop_audio()
                trace = audio_trace(session)
                require(trace == [
                    {"opcode": 1, "source": 6, "destination": 4, "arg0": 0, "arg1": 0},
                    {"opcode": 0, "source": 6, "destination": 4, "arg0": 154, "arg1": 1},
                ], f"{name} restore packet trace differs: {trace}")
                require(u16(session.read_memory("snesMemory", SCUMM_VARIABLES, 2), 0) == 1
                        and session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0] == LOGICAL_SOUND,
                        f"{name} $7C did not report running")
                restored_position = u32(session.read_memory("snesMemory", MUSIC_POSITION, 4))
                require(restored_position < decoded["advisory_position"],
                        f"{name} advisory position was incorrectly honored")
                require(tad_state(session)["rejected"] == 0,
                        f"{name} restart rejected a TAD command")
                correlation = prefix_correlation(direct_path, load_path)
                require(correlation["correlation"] > 0.99,
                        f"{name} restored audible prefix differs: {correlation}")
                results[name] = {
                    "save": save_evidence,
                    "cold_load": {
                        "fresh_process": True, "save_state": loaded,
                        "audio_packets": trace, "tad_lifecycle": lifecycle,
                        "restored_position": restored_position,
                        "audio": wav_evidence(load_path), "prefix_match": correlation,
                    },
                }
        report["running_checkpoints"] = results

        # Persist a stopped logical state, then load it in another process.
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port + 10, boot_wait=2.0,
            socket_timeout=90.0, stderr_log=output / "stopped-save-stderr.log",
        ) as session:
            boot_blank(session)
            session.write_u8(FIXTURE_REQUEST, M20_STOP_SAVE)
            stopped_written = wait_save_status(session, 1, "stopped save")
            stopped_raw = session.read_memory("snesSaveRam", 0, RECORD_SIZE)
            stopped_record = decode_record(stopped_raw)
            require(stopped_record["running"] == 0 and stopped_record["logical_sound_id"] == 0,
                    f"stopped subrecord differs: {stopped_record}")
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port + 11, boot_wait=2.0,
            socket_timeout=90.0, stderr_log=output / "stopped-load-stderr.log",
        ) as session:
            boot_blank(session)
            require(session.read_memory("snesSaveRam", 0, RECORD_SIZE) == stopped_raw,
                    "stopped SRAM did not persist across emulator processes")
            session.write_u8(FIXTURE_REQUEST, M20_LOAD)
            stopped_loaded = wait_save_status(session, 2, "stopped cold load")
            run_exact_frames(session, 60, "stopped cold load settle")
            stopped_trace = audio_trace(session)
            require(stopped_trace == [
                {"opcode": 1, "source": 6, "destination": 4, "arg0": 0, "arg1": 0},
            ], f"stopped restore emitted a play command: {stopped_trace}")
            require(u16(session.read_memory("snesMemory", SCUMM_VARIABLES, 2), 0) == 0
                    and session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0] == 0
                    and tad_state(session)["next_song"] == 0,
                    "stopped restore did not remain stopped")
        report["stopped_checkpoint"] = {
            "save_state": stopped_written, "load_state": stopped_loaded,
            "record": stopped_record, "audio_packets": stopped_trace,
            "fresh_processes": 2,
        }

        # Every invalid record is tested while music is already running. A
        # rejection must leave the packet trace, logical owner, and TAD song exact.
        rejection_results = {}
        for index, case in enumerate((
            "corrupt", "wrong_engine", "wrong_game", "wrong_schema", "wrong_catalog",
        )):
            with mcp_session.McpSession(
                rom=rom, mesen=nexen, cwd=ROOT, port=args.port + 20 + index,
                boot_wait=2.0, socket_timeout=90.0,
                stderr_log=output / f"reject-{case}-stderr.log",
            ) as session:
                boot_blank(session)
                session.write_u8(FIXTURE_REQUEST, M20_START)
                wait_song(session, COMPILED_SONG, f"{case} setup music")
                before_trace = audio_trace(session)
                before_tad = tad_state(session)
                session.write_memory(
                    "snesSaveRam", 0, mutate_record(valid_running_record, case).hex()
                )
                session.write_u8(FIXTURE_REQUEST, M20_LOAD)
                rejected = wait_save_status(session, 0xFF, f"{case} rejection")
                after_trace = audio_trace(session)
                after_tad = tad_state(session)
                require(after_trace == before_trace
                        and session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0] == LOGICAL_SOUND
                        and after_tad["state"] == before_tad["state"]
                        and after_tad["next_song"] == before_tad["next_song"]
                        and after_tad["rejected"] == before_tad["rejected"],
                        f"{case} rejection partially changed audio state")
                rejection_results[case] = {
                    "save_state": rejected, "audio_packets_before": before_trace,
                    "audio_packets_after": after_trace, "tad_before": before_tad,
                    "tad_after": after_tad, "logical_music": LOGICAL_SOUND,
                }
        report["transactional_rejections"] = rejection_results
        report["result"] = "pass"
        report["cold_emulator_processes"] = 4 + 2 + 5
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"M20 compiled-music cold restart: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"M20 compiled-music cold restart: PASS ({rom_hash})")
    print(report_path)
    print(hashlib.sha256(report_path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
