#!/usr/bin/env python3
"""Validate Fate room-49 hook-14 compiled routing through the real SNES path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import wave

from same.savegame import SaveEnvelope
from validate_scumm_m19_monkey_music_nexen import audio_trace
from validate_scumm_m20_save_nexen import boot_blank, save_state, wait_save_status
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state, wav_evidence


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REQUEST = 0x7E235E
SCUMM_STATE = 0x7E2300
SCUMM_VARIABLES = 0x7E2320
EVENT_STATE = 0x7E2000
ROUTE_STATE = 0x7FF25A
ACTIVE_MUSIC = 0x7FF24D
M21 = 0x3D
SAVE = 0x3A
LOAD = 0x3B
RECORD_SIZE = 204
PROGRAM_SIZE = 136


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def route_state(session: object) -> dict[str, object]:
    raw = session.read_memory("snesMemory", ROUTE_STATE, 85)
    count = min(raw[4], 16)
    return {"kind": raw[0], "value": raw[1], "song": raw[2],
            "resolution_count": raw[3], "history_count": raw[4],
            "operations": list(raw[5:5 + count]),
            "kinds": list(raw[21:21 + count]),
            "values": list(raw[37:37 + count]),
            "songs": list(raw[53:53 + count]),
            "logical_ids": list(raw[69:69 + count])}


def wait_route(session: object, kind: int, value: int, song: int, label: str,
               limit: int = 300) -> list[dict[str, object]]:
    timeline = []
    for _ in range(limit):
        result = session.run_frames(1)
        require(result["framesAdvanced"] == 1 and not result["timedOut"], f"{label} timed out")
        route, tad = route_state(session), tad_state(session)
        item = {"frame": session.get_state()["frameCount"], "route": route, "tad": tad}
        timeline.append(item)
        if (route["kind"], route["value"], route["song"]) == (kind, value, song) \
                and tad["state"] == 0x82 and tad["ready"] and tad["next_song"] == song:
            return timeline
    raise RuntimeError(f"{label} did not reach route {(kind, value, song)}: {timeline[-1]}")


def first_audible(path: Path) -> dict[str, int]:
    with wave.open(str(path), "rb") as audio:
        rate, channels = audio.getframerate(), audio.getnchannels()
        raw = audio.readframes(audio.getnframes())
    values = struct.unpack(f"<{len(raw) // 2}h", raw)
    frame = next((i // channels for i in range(0, len(values), channels)
                  if max(abs(v) for v in values[i:i + channels]) > 8), None)
    require(frame is not None, f"{path.name} is silent")
    return {"sample": frame, "sample_rate": rate,
            "from_capture_start_us": round(frame * 1_000_000 / rate)}


def decode_record(raw: bytes) -> dict[str, object]:
    require(len(raw) == RECORD_SIZE, "M21 SRAM record size differs")
    envelope = SaveEnvelope.unpack(raw)
    payload = envelope.payload
    require(len(payload) == 116 and payload[:8] == b"SCMUSIC\0", "M21 subrecord differs")
    return {"envelope": envelope.to_dict(), "version": u16(payload, 8),
            "policy": u16(payload, 10), "logical": payload[12], "running": payload[13],
            "route_kind": payload[14], "route_value": payload[15],
            "advisory_position": int.from_bytes(payload[16:20], "little"),
            "catalog_sha256": payload[20:52].hex(), "source_sha256": payload[52:84].hex(),
            "route_identity": payload[84:116].hex()}


def mutate_route_identity(raw: bytes) -> bytes:
    envelope = SaveEnvelope.unpack(raw)
    payload = bytearray(envelope.payload)
    payload[84] ^= 1
    return SaveEnvelope(envelope.engine_id, envelope.game_id, envelope.schema,
                        bytes(payload), envelope.flags).pack()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/same-scumm-v5-fate-m21.sfc")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44160)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"scumm-m21-fate-route-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {"gate": "M21-Fate-room49-sound80-hook14", "result": "running",
        "rom": str(rom), "rom_sha256": rom_hash, "fresh_power_on": True,
        "debugger_sound_request_writes": 0, "logical_sound": 80,
        "compiled_routes": {"default": 26, "hook14": 27},
        "runtime_source_branch_execution": False,
        "normalized_tad_onset": {
            "default": {"ticks_at_125hz": 22, "time_us": 176000,
                        "source_first_note_us": 168915, "error_us": 7085},
            "hook14": {"ticks_at_125hz": 20, "time_us": 160000,
                       "source_first_note_us": 155151, "error_us": 4849}},
        "human_timbre_gate": "pending"}

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    nx = nexen
    try:
        # One fresh process proves the exact dispatcher sequence and complete
        # one-shot lifetime. Capture each selected route before its next stop.
        hook_wav, default_wav = output / "hook14-route-excerpt.wav", output / "default-route-excerpt.wav"
        with mcp_session.McpSession(rom=rom, mesen=nx, cwd=ROOT, port=args.port,
                boot_wait=2.0, socket_timeout=90.0, stderr_log=output / "lifecycle-stderr.log") as s:
            boot_blank(s)
            boot_frame = s.get_state()["frameCount"]
            s.record_audio(hook_wav)
            s.write_u8(FIXTURE_REQUEST, M21)
            hook_timeline = wait_route(s, 1, 14, 27, "room-49 hooked route")
            require(not any(item["tad"]["state"] == 0x82 and item["tad"]["ready"]
                            and item["tad"]["next_song"] == 26 for item in hook_timeline),
                    "default route reached ready/playing ownership before hook replacement")
            elapsed = s.get_state()["frameCount"] - boot_frame
            if elapsed < 105:
                s.run_frames(105 - elapsed)
            s.stop_audio()
            default_timeline = wait_route(s, 0, 0, 26, "unhooked restart")
            s.record_audio(default_wav)
            s.run_frames(70)
            s.stop_audio()
            s.run_frames(180)
            state_raw = s.read_memory("snesMemory", SCUMM_STATE, 14)
            variables = s.read_memory("snesMemory", SCUMM_VARIABLES, 8)
            route = route_state(s)
            trace = audio_trace(s)
            tad = tad_state(s)
            events = s.read_memory("snesMemory", EVENT_STATE, 10)
            require(u16(state_raw, 0) == 133 and state_raw[2] == 2 and state_raw[3] == 0,
                    f"M21 fixture terminal state differs: {state_raw.hex()}")
            require([u16(variables, i * 2) for i in range(4)] == [1, 0, 1, 1],
                    f"$7C running/stopped results differ: {variables.hex()}")
            expected_ops = [1, 3, 2, 3, 4, 1, 3, 4, 1, 3, 2, 3]
            require(route["operations"] == expected_ops and route["songs"] ==
                    [26, 26, 27, 27, 27, 26, 26, 26, 26, 26, 27, 27],
                    f"hook lifetime history differs: {route}")
            require(route["logical_ids"] == [80] * 12 and route["kind"] == 1
                    and route["value"] == 14 and route["song"] == 27,
                    f"final hook ownership differs: {route}")
            require(tad["state"] == 0x82 and tad["ready"] and tad["next_song"] == 27
                    and tad["rejected"] == 0 and u16(events, 6) == 0 and u16(events, 8) == 0,
                    f"packet/TAD loss or lifecycle state differs: {tad}, {events.hex()}")
            hook_audio, default_audio = wav_evidence(hook_wav), wav_evidence(default_wav)
            require(0 < hook_audio["peak"] < 32767 and 0 < default_audio["peak"] < 32767,
                    "route capture is silent or clipped")
            require(hook_audio["sha256"] != default_audio["sha256"],
                    "hooked and default DSP output are not observably distinct")
            report["normal_path"] = {"fixture_id": M21, "program_size": PROGRAM_SIZE,
                "opcode_history": {"last_opcode": state_raw[6], "total_ops": u16(state_raw, 12)},
                "audio_packets_first_eight": trace, "route_history": route,
                "hook_lifecycle": hook_timeline, "default_lifecycle": default_timeline,
                "tad_final": tad, "event_dropped": u16(events, 6),
                "event_rejected": u16(events, 8), "$7c_results": [1, 0, 1, 1],
                "hook_audio": hook_audio, "default_audio": default_audio,
                "hook_first_audible": first_audible(hook_wav),
                "default_first_audible": first_audible(default_wav)}

        save_records: dict[str, bytes] = {}
        save_evidence: dict[str, object] = {}
        for index, (name, kind, value, song) in enumerate((
                ("hook14", 1, 14, 27), ("default", 0, 0, 26))):
            with mcp_session.McpSession(rom=rom, mesen=nx, cwd=ROOT,
                    port=args.port + 1 + index * 2, boot_wait=2.0, socket_timeout=90.0,
                    stderr_log=output / f"{name}-save-stderr.log") as s:
                boot_blank(s)
                s.write_u8(FIXTURE_REQUEST, M21)
                timeline = wait_route(s, kind, value, song, f"{name} save setup")
                s.write_u8(FIXTURE_REQUEST, SAVE)
                written = wait_save_status(s, 1, f"{name} save")
                raw = s.read_memory("snesSaveRam", 0, RECORD_SIZE)
                decoded = decode_record(raw)
                require(decoded["version"] == 2 and decoded["policy"] == 1
                        and decoded["logical"] == 80 and decoded["running"] == 1
                        and decoded["route_kind"] == kind and decoded["route_value"] == value,
                        f"{name} save subrecord differs: {decoded}")
                save_records[name] = raw
                save_evidence[name] = {"write_state": written, "record": decoded,
                                       "record_sha256": hashlib.sha256(raw).hexdigest(),
                                       "setup_lifecycle": timeline}
            with mcp_session.McpSession(rom=rom, mesen=nx, cwd=ROOT,
                    port=args.port + 2 + index * 2, boot_wait=2.0, socket_timeout=90.0,
                    stderr_log=output / f"{name}-load-stderr.log") as s:
                boot_blank(s)
                require(s.read_memory("snesSaveRam", 0, RECORD_SIZE) == raw,
                        f"{name} SRAM did not persist across fresh processes")
                s.write_u8(FIXTURE_REQUEST, LOAD)
                loaded = wait_save_status(s, 2, f"{name} cold load")
                lifecycle = wait_route(s, kind, value, song, f"{name} deterministic restart")
                packets = audio_trace(s)
                require(packets == [
                    {"opcode": 1, "source": 6, "destination": 4, "arg0": 0, "arg1": 0},
                    {"opcode": 0, "source": 6, "destination": 4, "arg0": 80,
                     "arg1": value | kind << 8}], f"{name} cold-load packets differ: {packets}")
                require(s.read_memory("snesMemory", ACTIVE_MUSIC, 1)[0] == 80,
                        f"{name} cold load lost logical ownership")
                save_evidence[name]["cold_load"] = {"fresh_process": True,
                    "load_state": loaded, "packets": packets, "lifecycle": lifecycle,
                    "route": route_state(s), "advisory_position_honored": False}
        report["cold_save_load"] = save_evidence

        # A CRC-valid but unknown route identity must reject before either the
        # active logical route or audio-service packet history changes.
        with mcp_session.McpSession(rom=rom, mesen=nx, cwd=ROOT, port=args.port + 9,
                boot_wait=2.0, socket_timeout=90.0,
                stderr_log=output / "route-reject-stderr.log") as s:
            boot_blank(s)
            s.write_u8(FIXTURE_REQUEST, M21)
            wait_route(s, 1, 14, 27, "route rejection setup")
            before = {"route": route_state(s), "tad": tad_state(s), "packets": audio_trace(s)}
            s.write_memory("snesSaveRam", 0, mutate_route_identity(save_records["hook14"]).hex())
            s.write_u8(FIXTURE_REQUEST, LOAD)
            rejected = wait_save_status(s, 0xFF, "mismatched route identity")
            after = {"route": route_state(s), "tad": tad_state(s), "packets": audio_trace(s)}
            require(after == before, f"route-identity rejection partially mutated state: {before}, {after}")
            report["transactional_route_rejection"] = {"save_state": rejected,
                                                         "before": before, "after": after}

        audit = json.loads((ROOT / "audio/fate_s6/m21_sound80/manifest.json").read_text())
        routes = {item["name"]: item for item in audit["routes"]}
        require(routes["default"]["consumed_branch"] == {"source_track": 0, "source_tick": 100,
                "target_track": 0, "target_tick": 1920}, "default branch audit differs")
        require(routes["hook14"]["consumed_branch"] == {"source_track": 0, "source_tick": 90,
                "target_track": 3, "target_tick": 1920}, "hook branch audit differs")
        require(routes["hook14"]["prefix"]["note_on_count"] == 0
                and routes["hook14"]["prefix"]["sustained_voice_count"] == 0
                and routes["hook14"]["first_destination_note"] ==
                {"track": 3, "tick": 1923, "time_us": 155151}, "hook prefix audit differs")
        report["build_audit"] = audit
        report["result"] = "mechanical-pass-human-timbre-pending"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(f"M21 Fate route: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"M21 Fate route: MECHANICAL PASS / HUMAN TIMBRE PENDING ({rom_hash})")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
