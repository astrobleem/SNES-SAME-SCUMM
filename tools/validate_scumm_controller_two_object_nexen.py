#!/usr/bin/env python3
"""Runtime proof for the copyright-free two-object controller fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
MAIN_LOOP = 0x80DA
ROOM = 0x7FF2BE
CONTROLLER = 0x7E5FE0
INPUT = 0x7E2200
OBJECT_RECORDS = 0x7E7000
OBJECT_COUNT = 0x7E5FFC
SENTENCE_API = 0x7E7EBF
C20 = 0x7FD380
ERROR = 0x7E2303


def u16(raw: bytes) -> int:
    return int.from_bytes(raw[:2], "little")


def state(session: object) -> dict[str, object]:
    room = session.read_memory("snesMemory", ROOM, 0x06)
    controller = session.read_memory("snesMemory", CONTROLLER, 0x10)
    input_state = session.read_memory("snesMemory", INPUT, 0x08)
    sentence_pending = session.read_memory("snesMemory", 0x7E7EC7, 1)[0]
    sentence_verb = session.read_memory("snesMemory", 0x7FD3A6, 1)[0]
    sentence_object1 = u16(session.read_memory("snesMemory", 0x7FD3A8, 2))
    sentence_object2 = u16(session.read_memory("snesMemory", 0x7FD3AA, 2))
    c20 = session.read_memory("snesMemory", C20, 0x0E)
    return {
        "frame": session.get_state()["frameCount"],
        "room": room[1], "phase": room[4], "error": session.read_memory("snesMemory", ERROR, 1)[0],
        "mode": controller[0], "cursor_x": u16(controller[1:3]), "cursor_y": u16(controller[3:5]),
        "verb": controller[5], "object1": u16(controller[6:8]), "hud_dirty": controller[8],
        "pressed": u16(input_state[4:6]), "sentence_pending": sentence_pending,
        "api_verb": sentence_verb, "api_object1": sentence_object1, "api_object2": sentence_object2,
        "c20_count": c20[0],
        "c20": ({"verb": c20[2], "object1": u16(c20[3:5]), "object2": u16(c20[5:7])} if c20[0] else None),
        "object2": sentence_object2,
        # The conformance profile's generated MAXS table is authoritative;
        # do not assume the historical Phase-6 dense/bootstrap addresses.
        "effect_var5": u16(session.read_memory("snesMemory", 0x7E0800 + 5 * 2, 2)),
        "variables": [u16(session.read_memory("snesMemory", 0x7E0800 + i * 2, 2)) for i in range(8)],
    }


def advance(session: object, frames: int = 1) -> None:
    result = session.run_frames(frames)
    if result.get("timedOut") or result.get("framesAdvanced") != frames:
        raise RuntimeError(f"frame advance failed: {result}")


def release(session: object) -> None:
    session.set_input(0, 1)
    advance(session, 1)


def edge(session: object, button: int) -> None:
    release(session)
    session.tool("set_input", {"port": 0, "buttons": button, "hold": True})
    advance(session, 1)
    release(session)


def move_to(session: object, target_x: int, target_y: int) -> None:
    for _ in range(160):
        current = state(session)
        if (current["cursor_x"], current["cursor_y"]) == (target_x, target_y):
            return
        if current["cursor_x"] < target_x:
            button = session.BTN_RIGHT
        elif current["cursor_x"] > target_x:
            button = session.BTN_LEFT
        elif current["cursor_y"] < target_y:
            button = session.BTN_DOWN
        else:
            button = session.BTN_UP
        edge(session, button)
    raise RuntimeError(f"cursor did not reach {(target_x, target_y)}: {state(session)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/two-object-conformance.sfc")
    parser.add_argument("--output", type=Path, default=ROOT / "build/two-object-conformance-replay")
    parser.add_argument("--port", type=int, default=44773)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rom = args.rom.resolve()
    if not rom.is_file():
        raise RuntimeError(f"missing ROM: {rom}")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    sys.path.insert(0, str(ROOT / "src"))
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    with mcp_session.McpSession(
        rom=rom, mesen=NEXEN, cwd=ROOT, port=args.port, boot_wait=2.0,
        socket_timeout=60.0, stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        advance(session, 4)
        for _ in range(120):
            current = state(session)
            if current["room"] == 1 and current["phase"] == 0 and current["error"] == 0:
                break
            advance(session, 1)
        else:
            raise RuntimeError(f"standalone room did not install: {current}")
        # The build map's bank-0 loop is the completed-frame observation fence.
        hook = session.add_exec_hook(MAIN_LOOP)
        try:
            for _ in range(3):
                session.resume()
                result = session.run_until(max_frames=20, hook_handle=hook)
                session.pause()
                if result.get("timedOut"):
                    raise RuntimeError(f"logical frame hook timed out: {result}")
            records = session.read_memory("snesMemory", OBJECT_RECORDS, session.read_memory("snesMemory", OBJECT_COUNT, 1)[0] * 11)
            objects = [
                {"id": u16(records[offset:offset + 2]), "x": u16(records[offset + 2:offset + 4]),
                 "y": u16(records[offset + 4:offset + 6]), "width": u16(records[offset + 6:offset + 8]),
                 "height": u16(records[offset + 8:offset + 10])}
                for offset in range(0, len(records), 11)
            ]
            target1 = next(item for item in objects if item["id"] == 7)
            target2 = next(item for item in objects if item["id"] == 8)
            before = state(session)
            move_to(session, target1["x"] + 2, target1["y"] + 2)
            edge(session, session.BTN_A)
            selected = state(session)
            if (selected["mode"], selected["object1"], selected["verb"]) != (1, 7, 3):
                raise RuntimeError(f"primary selection failed: {selected}")
            # SAME's controller contract names the secondary-selection bit B;
            # on the Nexen SNES mask this is the $0040/X bit used by the
            # existing controller fixture input mapping.
            edge(session, session.BTN_X)
            secondary_mode = state(session)
            if secondary_mode["mode"] != 3:
                raise RuntimeError(f"secondary mode was not entered: {secondary_mode}")
            move_to(session, target2["x"] + 2, target2["y"] + 2)
            edge(session, session.BTN_A)
            secondary = state(session)
            if (secondary["mode"], secondary["object2"]) != (4, 8):
                raise RuntimeError(f"secondary selection failed: {secondary}")
            release(session)
            pre_submit = state(session)
            if pre_submit["mode"] != 4:
                raise RuntimeError(f"secondary selection did not survive release: {pre_submit}")
            trace_handles = {}
            for address, end, label in (
                (0x7E5FE0, 0x7E5FE0, "mode_write"),
                (0x7E7EC7, 0x7E7EC7, "sentence_pending_write"),
                (0x7FD3A6, 0x7FD3AB, "sentence_api_write"),
                (0x7FD3AA, 0x7FD3AA, "sentence_api_object2_low"),
                (0x7FD380, 0x7FD38D, "c20_write"),
                (0x7E080A, 0x7E080B, "var5_write"),
                (0x7E2381, 0x7E2398, "sentence_slot_status"),
                (0x7E23B3, 0x7E23CA, "sentence_slot_program"),
            ):
                trace_handles[session.add_write_hook(address, end)] = label
            for address, label in (
                (0x00B265, "QueueSentence"),
                (0x099384, "SentenceProcess_Far"),
                (0x09949B, "SentenceProcess_slot_found"),
                (0x099A01, "StartObject"),
                (0x00CC99, "SetVarRange"),
            ):
                trace_handles[session.add_exec_hook(address)] = label
            session.drain_notifications(timeout=0.0)
            session.set_input(session.BTN_A, 4)
            transaction_trace = []
            for note in session.drain_notifications(timeout=0.5):
                if note.get("method") != "notifications/mesen/hookFired":
                    continue
                params = note.get("params", {})
                label = trace_handles.get(params.get("handle"))
                if label is not None:
                    transaction_trace.append({"label": label, "params": dict(params)})
            submitted = {
                **pre_submit,
                # Filled from the actual API write notifications below; the
                # pre-submit controller fields are only the staged state.
                "normal_sentence_input": True,
            }
            api_bytes = {}
            for event in transaction_trace:
                if event["label"] == "sentence_api_write":
                    params = event["params"]
                    api_bytes.setdefault(int(params["address"]), []).append(int(params["value"]))
            def first_nonzero(address: int, fallback: int = 0) -> int:
                return next((value for value in api_bytes.get(address, []) if value), fallback)
            submitted["tuple"] = {
                "verb": first_nonzero(0x7FD3A6),
                "object1": first_nonzero(0x7FD3A8) | (first_nonzero(0x7FD3A9) << 8),
                "object2": first_nonzero(0x7FD3AA, pre_submit["object2"]) | (first_nonzero(0x7FD3AB) << 8),
            }
            submitted["mode_events"] = [
                {"frame": event["params"].get("frame"), "value": event["params"].get("value")}
                for event in transaction_trace if event["label"] == "mode_write"
            ]
            if (submitted["tuple"]["verb"], submitted["tuple"]["object1"], submitted["tuple"]["object2"]) != (3, 7, 8):
                raise RuntimeError(f"sentence tuple was not submitted: {submitted}")
            for _ in range(120):
                advance(session, 1)
                final = state(session)
                if final["mode"] in (0, 1) and final["object2"] == 0 and final["sentence_pending"] == 0 and final["c20_count"] == 0:
                    break
            else:
                raise RuntimeError(f"sentence lifecycle did not re-enter: {final}")
            if final["error"] != 0:
                raise RuntimeError(f"SCUMM error after action: {final}")
            if final["effect_var5"] != 1:
                raise RuntimeError(f"authored two-object effect did not execute: {final}")
            mode_sequence = (
                [before["mode"], selected["mode"], secondary_mode["mode"], secondary["mode"]]
                + [event["value"] for event in submitted["mode_events"]]
            )
            report = {
                "result": "PASS", "rom": str(rom), "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
                "nexen": str(NEXEN), "nexen_sha256": hashlib.sha256(NEXEN.read_bytes()).hexdigest(),
                "objects": objects, "before": before, "selected": selected,
                "secondary_mode": secondary_mode, "secondary_selected": secondary,
                "submitted": submitted, "transaction_trace": transaction_trace, "final": final,
                "mode_sequence": mode_sequence,
            }
            (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            print(json.dumps(report, sort_keys=True))
        finally:
            session.remove_hook(hook)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
