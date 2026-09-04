#!/usr/bin/env python3
"""Prove production SAME saves persist in SA-1 BW-RAM across processes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from same.savegame import SaveEnvelope


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
SAVE_STATE = 0x7FF252
SAVE_OFFSET = 0x0800
SAVE_BYTES = 0x0800
RECORD_BYTES = 0x0154
CONTROL_OFFSET = 0x1000
CONTROL_BYTES = bytes.fromhex("534131430101000002000000000000000000")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def u16(raw: bytes, offset: int) -> int:
    return int.from_bytes(raw[offset:offset + 2], "little")


def state(session: object) -> dict[str, int]:
    raw = session.read_memory("snesMemory", SAVE_STATE, 8)
    return {
        "status": raw[0],
        "error": raw[1],
        "writes": u16(raw, 2),
        "loads": u16(raw, 4),
        "rejects": u16(raw, 6),
    }


def stable_sa1(session: object) -> dict[str, object]:
    raw = session.get_cpu_state("Sa1")
    return {
        key: raw[key]
        for key in ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")
    }


def run_until(session: object, predicate: object, label: str) -> tuple[int, dict[str, int]]:
    for frame in range(1, 600):
        result = session.run_frames(1)
        require(result["framesAdvanced"] == 1 and not result["timedOut"], f"{label} timed out")
        current = state(session)
        if predicate(current):
            return frame, current
    raise RuntimeError(f"{label} did not complete: {state(session)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=45830)
    args = parser.parse_args()
    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen unavailable: {nexen}")
    raw_rom = rom.read_bytes()
    require(raw_rom[0x7FD5:0x7FD9] == bytes((0x23, 0x35, 0x09, 0x07)),
            "persistence ROM is not the accepted SA-1/BW-RAM carrier")
    save_path = Path.home() / ".config/Nexen/Saves" / f"{rom.stem}.srm"
    if save_path.exists():
        save_path.unlink()
    require(not save_path.exists(), "could not establish an absent pre-process save image")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    reset_state = {
        "pc": 0, "k": 0, "a": 0, "x": 0, "y": 0, "sp": 0x1FF,
        "d": 0, "dbr": 0, "ps": 0x34, "emulationMode": True,
    }

    process_reports: list[dict[str, object]] = []
    first_record = b""
    for process in (1, 2):
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port,
            boot_wait=2.0, socket_timeout=90.0,
            stderr_log=args.output.with_name(f"{args.output.stem}-process{process}.stderr.log"),
        ) as session:
            session.pause()
            require(stable_sa1(session) == reset_state, f"process {process}: SA-1 reset differs")
            persisted_before = session.read_memory("snesSaveRam", SAVE_OFFSET, RECORD_BYTES)
            protected_before = session.read_memory("snesSaveRam", 0, SAVE_OFFSET)
            if process == 2:
                require(persisted_before == first_record, "record did not persist into process 2")
            frame, final = run_until(
                session,
                (lambda item: item["writes"] == 1)
                if process == 1 else
                (lambda item: item["loads"] == 1),
                f"persistence process {process}",
            )
            record = session.read_memory("snesSaveRam", SAVE_OFFSET, RECORD_BYTES)
            envelope = SaveEnvelope.unpack(record)
            require(envelope.engine_id == "scumm_v5" and envelope.game_id == "indy4-fate-demo",
                    f"process {process}: save identity differs")
            require(envelope.schema == 1, f"process {process}: save schema differs")
            require(session.read_memory("snesMemory", 0x401000, len(CONTROL_BYTES)) == CONTROL_BYTES,
                    f"process {process}: carrier control record differs")
            require(stable_sa1(session) == reset_state, f"process {process}: SA-1 executed")
            require(session.read_memory("snesSaveRam", 0, SAVE_OFFSET) == protected_before,
                    f"process {process}: protected BW-RAM below save changed")
            if process == 1:
                first_record = record
            process_reports.append({
                "process": process,
                "fresh_emulator_process": True,
                "terminal_frame": frame,
                "state": final,
                "persisted_before_sha256": hashlib.sha256(persisted_before).hexdigest(),
                "record_sha256": hashlib.sha256(record).hexdigest(),
                "envelope": envelope.to_dict(),
                "sa1": reset_state,
            })

    require(save_path.is_file() and save_path.stat().st_size == 0x20000,
            "Nexen did not persist the configured 128 KiB BW-RAM image")
    persisted_image = save_path.read_bytes()
    require(persisted_image[SAVE_OFFSET:SAVE_OFFSET + RECORD_BYTES] == first_record,
            "on-disk BW-RAM save image differs from the production record")
    report = {
        "gate": "Phase 6C production SA-1 BW-RAM battery persistence",
        "result": "pass",
        "debugger_writes": 0,
        "emulator_savestate_used": False,
        "rom_sha256": hashlib.sha256(raw_rom).hexdigest(),
        "save_path": str(save_path),
        "save_image_bytes": len(persisted_image),
        "save_range": {"address": "40:0800", "bytes": SAVE_BYTES},
        "record_bytes": RECORD_BYTES,
        "processes": process_reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
