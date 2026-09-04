#!/usr/bin/env python3
"""Validate M22 deterministic-restart SRAM state for bounded hook-8 routes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from same.savegame import SaveEnvelope
from validate_scumm_m19_monkey_music_nexen import audio_trace
from validate_scumm_m20_save_nexen import boot_blank, save_state, wait_save_status
from validate_scumm_m21_fate_route_nexen import route_state, wait_route
from validate_scumm_m22_fate_hook8_nexen import m22_state, tad_extra
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REQUEST = 0x7E235E
ACTIVE_MUSIC = 0x7FF24D
SCUMM_VARIABLES = 0x7E2320
HOOKED_FIXTURE = 0x3E
CONTROL_FIXTURE = 0x3F
SAVE_FIXTURE = 0x3A
LOAD_FIXTURE = 0x40
LOGICAL_SOUND = 80
COMPILED_SONG = 27
RECORD_SIZE = 340
PAYLOAD_SIZE = 252


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def decode_record(raw: bytes) -> dict[str, object]:
    require(len(raw) == RECORD_SIZE, "M22 SRAM record size differs")
    envelope = SaveEnvelope.unpack(raw)
    payload = envelope.payload
    require(len(payload) == PAYLOAD_SIZE and payload[:8] == b"SCMUSIC\0",
            "M22 compiled-music payload differs")
    return {
        "envelope": envelope.to_dict(),
        "version": u16(payload, 8),
        "policy": u16(payload, 10),
        "logical_sound": payload[12],
        "running": payload[13],
        "route_kind": payload[14],
        "route_value": payload[15],
        "advisory_position": int.from_bytes(payload[16:20], "little"),
        "catalog_sha256": payload[20:52].hex(),
        "source_sha256": payload[52:84].hex(),
        "route_identity": payload[84:116].hex(),
        "route_history": payload[116],
        "current_section": payload[117],
        "pending_hook": payload[118],
        "boundary_token": payload[119],
        "selected_section": payload[120],
        "consumption": payload[121],
        "planned_selector": payload[122],
        "reserved": payload[123],
        "section_plan_sha256": payload[124:156].hex(),
        "instrument_bank_sha256": payload[156:188].hex(),
        "planned_route_sha256": payload[188:220].hex(),
        "route_history_sha256": payload[220:252].hex(),
    }


def fast_until(session: object, predicate, label: str, max_frames: int = 5200) -> dict[str, object]:
    """Run unthrottled while deciding completion only from emulated state."""
    start = session.get_state()["frameCount"]
    session.resume()
    deadline = time.monotonic() + 120.0
    observed: dict[str, object] = {}
    try:
        while time.monotonic() < deadline:
            state = session.get_state()
            frame = state["frameCount"]
            observed = {
                "frame": frame,
                "m22": m22_state(session),
                "tad": tad_state(session),
                "backend": tad_extra(session),
            }
            if predicate(observed):
                return observed
            if frame - start >= max_frames:
                break
            time.sleep(0.01)
    finally:
        session.pause()
    raise RuntimeError(f"{label} was not observed: {observed}")


def wait_arm(session: object, expected: bool, label: str) -> dict[str, object]:
    for _ in range(80):
        result = session.run_frames(5)
        require(result["framesAdvanced"] == 5 and not result["timedOut"], f"{label} timed out")
        state = m22_state(session)
        tad = tad_state(session)
        if state["route_history"] == 1 and tad["ready"] and tad["next_song"] == COMPILED_SONG:
            if expected and state["arm_count"] == 1:
                require(state["pending_hook"] == 8 and state["consumption"] == 1,
                        f"{label} hook state differs: {state}")
                return {"frame": session.get_state()["frameCount"], "m22": state, "tad": tad}
            if not expected and state["arm_count"] == 0:
                return {"frame": session.get_state()["frameCount"], "m22": state, "tad": tad}
    raise RuntimeError(f"{label} did not reach expected pending state")


def save_checkpoint(session: object, fixture: int, state_name: str) -> tuple[bytes, dict[str, object]]:
    boot_blank(session)
    session.write_u8(FIXTURE_REQUEST, fixture)
    armed = wait_arm(session, fixture == HOOKED_FIXTURE, f"{state_name} setup")
    if state_name == "consumed":
        boundary = fast_until(
            session,
            lambda item: item["m22"]["consume_count"] == 1,
            "live hook consumption before save",
        )
    else:
        boundary = None
    before = m22_state(session)
    session.write_u8(FIXTURE_REQUEST, SAVE_FIXTURE)
    written = wait_save_status(session, 1, f"{state_name} SRAM write")
    raw = session.read_memory("snesSaveRam", 0, RECORD_SIZE)
    decoded = decode_record(raw)
    require(decoded["version"] == 3 and decoded["policy"] == 1
            and decoded["logical_sound"] == LOGICAL_SOUND and decoded["running"] == 1,
            f"{state_name} save header differs: {decoded}")
    expected = {
        "armed": (1, 1, 8, 1, 1),
        "consumed": (2, 2, 0, 2, 1),
        "default": (1, 1, 0, 0, 0),
    }[state_name]
    actual = (decoded["route_history"], decoded["current_section"],
              decoded["pending_hook"], decoded["consumption"],
              decoded["planned_selector"])
    require(actual == expected, f"{state_name} compiled-section record differs: {actual}")
    return raw, {
        "setup": armed, "boundary": boundary, "state_before_save": before,
        "save_service": written, "record": decoded,
        "record_sha256": hashlib.sha256(raw).hexdigest(),
    }


def load_checkpoint(session: object, raw: bytes, state_name: str) -> dict[str, object]:
    boot_blank(session)
    persisted = session.read_memory("snesSaveRam", 0, RECORD_SIZE)
    require(persisted == raw, f"{state_name} SRAM did not persist across emulator processes")
    session.write_u8(FIXTURE_REQUEST, LOAD_FIXTURE)
    loaded = wait_save_status(session, 2, f"{state_name} cold load")
    lifecycle = wait_route(session, 1, 14, COMPILED_SONG, f"{state_name} deterministic restart")
    restarted = m22_state(session)
    require(session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0] == LOGICAL_SOUND,
            f"{state_name} did not restore logical sound ownership")
    require(restarted["current_section"] == 1,
            f"{state_name} did not restart at the cue's compiled beginning: {restarted}")
    planned = state_name in ("armed", "consumed")
    require((restarted["pending_hook"], restarted["consumption"]) ==
            ((8, 1) if planned else (0, 0)),
            f"{state_name} restored plan differs: {restarted}")
    require(u16(session.read_memory("snesMemory", SCUMM_VARIABLES, 2)) == 1,
            f"{state_name} $7C did not report running")
    trace = audio_trace(session)
    expected_opcodes = [1, 0, 12] if planned else [1, 0]
    require([packet["opcode"] for packet in trace] == expected_opcodes,
            f"{state_name} restore packet order differs: {trace}")
    if planned:
        eventual = fast_until(
            session,
            lambda item: item["m22"]["consume_count"] == 1,
            f"{state_name} restored planned hook consumption",
        )
        require(eventual["m22"]["route_history"] == 2
                and eventual["m22"]["current_section"] == 2,
                f"{state_name} did not reproduce the saved continuation: {eventual}")
    else:
        start = session.get_state()["frameCount"]
        session.resume()
        try:
            deadline = time.monotonic() + 120.0
            while time.monotonic() < deadline and session.get_state()["frameCount"] - start < 4700:
                time.sleep(0.01)
        finally:
            session.pause()
        eventual = {"frame": session.get_state()["frameCount"],
                    "m22": m22_state(session), "tad": tad_state(session),
                    "backend": tad_extra(session)}
        require(eventual["m22"]["consume_count"] == 0
                and eventual["m22"]["route_history"] == 1,
                f"default restore acquired a stale hook: {eventual}")
    require(tad_state(session)["rejected"] == 0,
            f"{state_name} restart rejected a TAD command")
    return {"fresh_process": True, "save_service": loaded, "lifecycle": lifecycle,
            "restart_state": restarted, "audio_packets": trace, "eventual": eventual,
            "advisory_position_honored": False}


def mutate_record(raw: bytes, case: str) -> bytes:
    envelope = SaveEnvelope.unpack(raw)
    payload = bytearray(envelope.payload)
    offsets = {
        "wrong_route": 84,
        "wrong_section": 117,
        "wrong_catalog": 20,
        "wrong_bank": 156,
    }
    payload[offsets[case]] ^= 1
    return SaveEnvelope(envelope.engine_id, envelope.game_id, envelope.schema,
                        bytes(payload), envelope.flags).pack()


def rejection_case(session: object, valid: bytes, case: str) -> dict[str, object]:
    boot_blank(session)
    session.write_u8(FIXTURE_REQUEST, HOOKED_FIXTURE)
    wait_arm(session, True, f"{case} setup")
    before = {
        "active": session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0],
        "m22": m22_state(session), "route": route_state(session),
        "tad": tad_state(session), "trace": audio_trace(session),
    }
    session.write_memory("snesSaveRam", 0, mutate_record(valid, case).hex())
    session.write_u8(FIXTURE_REQUEST, LOAD_FIXTURE)
    rejected = wait_save_status(session, 0xFF, f"{case} transactional rejection")
    after = {
        "active": session.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0],
        "m22": m22_state(session), "route": route_state(session),
        "tad": tad_state(session), "trace": audio_trace(session),
    }
    require(after == before, f"{case} rejection partially mutated music/audio state")
    return {"save_service": rejected, "before": before, "after": after,
            "crc_valid_mutation": True, "transactional": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/same-scumm-v5-fate-m22.sfc")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44240)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-m22-save-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "M22-bounded-route-deterministic-restart", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash,
        "storage": "real 2 KiB cartridge SRAM", "slot": 99,
        "emulator_savestate_used": False,
        "restore_policy": "deterministic_cue_restart",
        "saved_playback_position": "advisory_and_ignored",
        "serialized_backend_state": False,
    }
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    try:
        records: dict[str, bytes] = {}
        checkpoints: dict[str, object] = {}
        for index, (name, fixture) in enumerate((
                ("armed", HOOKED_FIXTURE), ("consumed", HOOKED_FIXTURE),
                ("default", CONTROL_FIXTURE))):
            save_port = args.port + index * 2
            with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT, port=save_port,
                    boot_wait=2.0, socket_timeout=120.0,
                    stderr_log=output / f"{name}-save-stderr.log") as session:
                raw, saved = save_checkpoint(session, fixture, name)
                records[name] = raw
            with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT, port=save_port + 1,
                    boot_wait=2.0, socket_timeout=120.0,
                    stderr_log=output / f"{name}-load-stderr.log") as session:
                loaded = load_checkpoint(session, raw, name)
            checkpoints[name] = {"save": saved, "cold_load": loaded}
        report["checkpoints"] = checkpoints
        rejections = {}
        for index, case in enumerate(("wrong_route", "wrong_section", "wrong_catalog", "wrong_bank")):
            with mcp_session.McpSession(rom=rom, mesen=nexen, cwd=ROOT,
                    port=args.port + 20 + index, boot_wait=2.0, socket_timeout=120.0,
                    stderr_log=output / f"reject-{case}-stderr.log") as session:
                rejections[case] = rejection_case(session, records["armed"], case)
        report["transactional_rejections"] = rejections
        report["fresh_emulator_processes"] = 10
        report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"M22 save/load: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"PASS rom={rom_hash} report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
