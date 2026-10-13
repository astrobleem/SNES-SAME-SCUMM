#!/usr/bin/env python3
"""Runtime proof for the copyright-free two-object controller fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
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
        "controller_ready": session.read_memory("snesMemory", 0x7E5E8A, 1)[0],
        "mode": controller[0], "cursor_x": u16(controller[1:3]), "cursor_y": u16(controller[3:5]),
        "verb": controller[5], "object1": u16(controller[6:8]), "hud_dirty": controller[8],
        "pressed": u16(input_state[4:6]), "sentence_pending": sentence_pending,
        "submissions": controller[9],
        "talk_active": session.read_memory("snesMemory", 0x7E7A20, 1)[0],
        "talk_have_msg": session.read_memory("snesMemory", 0x7E7A21, 1)[0],
        "talk_delay": u16(session.read_memory("snesMemory", 0x7E7A24, 2)),
        "talk_generation": u16(session.read_memory("snesMemory", 0x7E7A26, 2)),
        "talk_stop_count": session.read_memory("snesMemory", 0x7E7A2A, 1)[0],
        "talk_edge_sequence": u16(session.read_memory("snesMemory", 0x7E2208, 2)),
        "talk_owned_sequence": u16(session.read_memory("snesMemory", 0x7E220A, 2)),
        "talk_edge_owned": session.read_memory("snesMemory", 0x7E220C, 1)[0],
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
    before = int(session.get_state()["frameCount"])
    result = session.run_frames(frames)
    after = int(session.get_state()["frameCount"])
    if (result.get("timedOut") or result.get("framesAdvanced") != frames
            or after - before != frames):
        raise RuntimeError(f"frame advance failed: {result}")


def set_level(session: object, buttons: int) -> None:
    session.tool("set_input", {
        "port": 0, "buttons": buttons, "hold": True, "frames": 0,
    })


def release(session: object) -> None:
    set_level(session, 0)
    advance(session, 1)


def edge(session: object, button: int) -> None:
    release(session)
    set_level(session, button)
    advance(session, 1)
    release(session)


def collect_hooks(session: object, handles: dict[int, str]) -> list[dict[str, object]]:
    events = []
    for note in session.drain_notifications(timeout=0.1):
        if note.get("method") != "notifications/mesen/hookFired":
            continue
        params = note.get("params", {})
        label = handles.get(params.get("handle"))
        if label is not None:
            events.append({"label": label, **dict(params)})
    return events


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
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rom = args.rom.resolve()
    if not rom.is_file():
        raise RuntimeError(f"missing ROM: {rom}")
    if not args.nexen.is_file():
        raise RuntimeError(f"missing Nexen executable: {args.nexen}")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "tools"))
    import mesen_mcp.session as mcp_session
    from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom, verified_symbol_map_for_rom
    mcp_session.validate_mesen_build = lambda _path: None
    map_path, symbols = verified_symbol_map_for_rom(rom)
    del symbols
    native = lambda symbol, bank: mapped_cpu_address_for_rom(rom, symbol, bank=bank)
    main_loop = native("Same_Main_Loop", 0)
    native_hooks = {
        "QueueSentence": native("ScummV5_QueueSentence", 0),
        "Input_Poll": native("Same_Input_Poll", 0),
        "SentenceProcess_Far": native("ScummV5_SentenceProcess_Far", 9),
        "SentenceProcess_slot_found": native("ScummV5_SentenceProcess_Far__slot_found", 9),
        "StartObject": native("ScummV5_StartObject_FarEntry", 9),
        "SetVarRange": native("ScummV5_Op_SetVarRange", 0),
        "Talk_FrameBegin": native("ScummV5_Talk_FrameBegin_Far", 9),
        "Talk_FrameEnd": native("ScummV5_Talk_FrameEnd_Far", 9),
        "Talk_Stop": native("ScummV5_Talk_Stop_Far", 9),
        "Controller_Frame": native("ScummV5_Controller_Frame_Far", 9),
        "Controller_A_submit": native("ScummV5_Controller_Frame__select_verb_a_pressed", 9),
    }
    with mcp_session.McpSession(
        rom=rom, mesen=args.nexen.resolve(), cwd=ROOT, port=args.port, boot_wait=2.0,
        socket_timeout=60.0, stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        advance(session, 4)
        for _ in range(120):
            current = state(session)
            if (current["room"] == 1 and current["phase"] == 0 and current["error"] == 0
                    and current["controller_ready"] == 1):
                break
            advance(session, 1)
        else:
            raise RuntimeError(f"standalone room did not install: {current}")
        # The build map's bank-0 loop is the completed-frame observation fence.
        hook = session.add_exec_hook(main_loop)
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
            for label in (
                "QueueSentence", "SentenceProcess_Far", "SentenceProcess_slot_found",
                "StartObject", "SetVarRange", "Talk_FrameBegin", "Talk_FrameEnd", "Talk_Stop",
            ):
                trace_handles[session.add_exec_hook(native_hooks[label])] = label
            trace_handles[session.add_write_hook(0x7E7A20)] = "talk_active_write"
            trace_handles[session.add_write_hook(0x7E7A24, 0x7E7A25)] = "talk_delay_write"
            session.drain_notifications(timeout=0.0)
            set_level(session, session.BTN_A)
            advance(session, 4)
            set_level(session, 0)
            advance(session, 1)
            transaction_trace = []
            transaction_trace.extend(
                {"label": event["label"], "params": event}
                for event in collect_hooks(session, trace_handles)
            )
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
            talk_lifecycle_trace = []
            for _ in range(120):
                advance(session, 1)
                final = state(session)
                talk_lifecycle_trace.extend(collect_hooks(session, trace_handles))
                if (final["mode"] in (0, 1) and final["object2"] == 0
                        and final["sentence_pending"] == 0 and final["c20_count"] == 0
                        and final["talk_active"] == 0):
                    break
            else:
                raise RuntimeError(
                    f"sentence/talk lifecycle did not re-enter: {final}; "
                    f"native talk events={talk_lifecycle_trace[-32:]}"
                )
            if final["error"] != 0:
                raise RuntimeError(f"SCUMM error after action: {final}")
            if final["effect_var5"] != 1:
                raise RuntimeError(f"authored two-object effect did not execute: {final}")

            # Reproduce the ownership boundary with the same synthetic room:
            # a normal one-object action starts an authored timed message,
            # then an A edge is sampled on the last talk tick. It must not be
            # reused after Talk_Stop as a second sentence.
            move_to(session, target1["x"] + 2, target1["y"] + 2)
            candidate = state(session)
            if (candidate["mode"], candidate["object1"], candidate["verb"]) != (1, 7, 3):
                edge(session, session.BTN_A)
            selected_single = state(session)
            if (selected_single["mode"], selected_single["object1"], selected_single["verb"]) != (1, 7, 3):
                raise RuntimeError(f"single-object talk fixture selection failed: {selected_single}")
            if (selected_single["talk_active"] or selected_single["c20_count"]
                    or selected_single["sentence_pending"]):
                raise RuntimeError(f"talk fixture did not begin from an idle controller: {selected_single}")
            submit_before = int(selected_single["submissions"])
            generation_before = int(selected_single["talk_generation"])
            edge(session, session.BTN_A)
            for _ in range(120):
                talking = state(session)
                if (talking["talk_active"] == 1
                        and talking["submissions"] == ((submit_before + 1) & 0xFF)
                        and talking["talk_generation"] != generation_before):
                    break
                if ((int(talking["submissions"]) - submit_before) & 0xFF) not in (0, 1):
                    raise RuntimeError(f"fixture action submitted unexpectedly: {talking}")
                advance(session, 1)
            else:
                raise RuntimeError(f"authored controller action did not start talk: {talking}")
            if talking["talk_have_msg"] != 1:
                raise RuntimeError(f"fixture did not produce an ordinary timed message: {talking}")

            talk_handles = {}
            for label in (
                "Input_Poll", "Talk_FrameBegin", "Talk_FrameEnd", "Talk_Stop", "Controller_Frame",
                "Controller_A_submit",
            ):
                talk_handles[session.add_exec_hook(native_hooks[label])] = label
            for address, label in (
                (0x7E2208, "edge_sequence_write"),
                (0x7E220A, "talk_owned_sequence_write"),
                (0x7E220C, "talk_edge_owned_write"),
                (0x7E7A20, "talk_active_write"),
                (0x7E7EC7, "sentence_pending_write"),
                (0x7E5FE9, "submission_count_write"),
            ):
                talk_handles[session.add_write_hook(address)] = label
            session.drain_notifications(timeout=0.0)
            owned_events: list[dict[str, object]] = []
            for _ in range(120):
                current_talk = state(session)
                if (current_talk["talk_active"] == 1
                        and int(current_talk["talk_delay"]) == 16):
                    break
                if current_talk["talk_active"] != 1 or int(current_talk["talk_delay"]) == 0:
                    raise RuntimeError(f"timed talk stopped before the last-tick input boundary: {current_talk}")
                advance(session, 1)
            else:
                raise RuntimeError(f"timed talk did not reach its last tick: {state(session)}")
            last_tick = state(session)
            if last_tick["talk_active"] != 1:
                raise RuntimeError(f"talk ended before ownership test: {last_tick}")

            press_start_frame = int(session.get_state()["frameCount"])
            set_level(session, session.BTN_A)
            owned_press_snapshots = []
            edge_sample = None
            for _ in range(4):
                advance(session, 1)
                edge_sample = state(session)
                owned_press_snapshots.append(edge_sample)
                owned_events.extend(collect_hooks(session, talk_handles))
                if int(edge_sample["pressed"]) & 0x0080:
                    break
                if edge_sample["talk_active"] != 1:
                    raise RuntimeError(f"talk ended before A edge was sampled: {edge_sample}")
            else:
                raise RuntimeError(f"A edge was not sampled within four frames: {owned_press_snapshots}")
            press_end_frame = int(session.get_state()["frameCount"])
            if edge_sample["talk_active"] != 1:
                raise RuntimeError(f"A edge was sampled after talk released ownership: {edge_sample}")
            if (edge_sample["talk_edge_owned"] != 1
                    or edge_sample["talk_owned_sequence"] != edge_sample["talk_edge_sequence"]):
                raise RuntimeError(f"sampled talk-time edge was not tagged at input poll: {edge_sample}")
            set_level(session, 0)
            advance(session, 1)
            owned_press_snapshots.append(state(session))
            owned_events.extend(collect_hooks(session, talk_handles))
            for _ in range(120):
                after_owned_edge = state(session)
                if (after_owned_edge["talk_active"] == 0
                        and after_owned_edge["sentence_pending"] == 0
                        and after_owned_edge["c20_count"] == 0
                        and after_owned_edge["mode"] == 1):
                    break
                advance(session, 1)
                owned_events.extend(collect_hooks(session, talk_handles))
            else:
                raise RuntimeError(f"controller did not revalidate after talk: {after_owned_edge}")
            owned_events.extend(collect_hooks(session, talk_handles))
            press_duration = press_end_frame - press_start_frame
            if not 1 <= press_duration <= 4:
                raise RuntimeError(f"talk-owned A edge duration was outside bounded exact-frame schedule: {press_duration}")
            if after_owned_edge["error"] != 0:
                raise RuntimeError(f"SCUMM error after talk-owned edge: {after_owned_edge}")
            if after_owned_edge["submissions"] != ((submit_before + 1) & 0xFF):
                diagnostic = {
                    "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
                    "map_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
                    "submit_before": submit_before,
                    "generation_before": generation_before,
                    "selected_single": selected_single,
                    "talk_started": talking,
                    "last_timed_tick": last_tick,
                    "edge_sample": edge_sample,
                    "owned_press_snapshots": owned_press_snapshots,
                    "owned_events": owned_events,
                    "after_owned_edge": after_owned_edge,
                }
                (args.output / "talk-edge-failure.json").write_text(
                    json.dumps(diagnostic, indent=2, sort_keys=True) + "\n"
                )
                raise RuntimeError(f"talk-owned A edge was reused as a sentence: {after_owned_edge}")
            if (after_owned_edge["object1"], after_owned_edge["verb"]) != (7, 3):
                raise RuntimeError(f"controller did not revalidate retained selection: {after_owned_edge}")
            if after_owned_edge["talk_edge_owned"] != 0:
                raise RuntimeError(f"talk ownership token was not consumed: {after_owned_edge}")
            if after_owned_edge["talk_owned_sequence"] != after_owned_edge["talk_edge_sequence"]:
                raise RuntimeError(f"talk ownership token names the wrong input edge: {after_owned_edge}")
            if any(event["label"] == "Controller_A_submit" for event in owned_events):
                raise RuntimeError(f"talk-owned edge entered sentence submission: {owned_events}")

            # A later, separately polled A edge remains an intentional repeat.
            later_start_frame = int(session.get_state()["frameCount"])
            set_level(session, session.BTN_A)
            advance(session, 4)
            later_end_frame = int(session.get_state()["frameCount"])
            set_level(session, 0)
            advance(session, 1)
            later_events = collect_hooks(session, talk_handles)
            repeated = state(session)
            if later_end_frame - later_start_frame != 4:
                raise RuntimeError("later A edge did not use an exact four-frame press")
            if repeated["submissions"] != ((submit_before + 2) & 0xFF):
                raise RuntimeError(f"new A edge did not submit exactly once: {repeated}")
            if sum(event["label"] == "Controller_A_submit" for event in later_events) != 1:
                raise RuntimeError(f"new A edge missed/repeated the submit handler: {later_events}")

            talk_control = {
                "selected_single": selected_single,
                "talk_started": talking,
                "last_timed_tick": last_tick,
                "talk_owned_press": {
                    "start_frame": press_start_frame, "end_frame": press_end_frame,
                    "edge_sample": edge_sample,
                    "snapshots": owned_press_snapshots,
                    "events": owned_events, "after": after_owned_edge,
                },
                "later_new_press": {
                    "start_frame": later_start_frame, "end_frame": later_end_frame,
                    "events": later_events, "after": repeated,
                },
            }
            mode_sequence = (
                [before["mode"], selected["mode"], secondary_mode["mode"], secondary["mode"]]
                + [event["value"] for event in submitted["mode_events"]]
            )
            report = {
                "result": "PASS", "rom": str(rom), "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
                "nexen": str(args.nexen.resolve()), "nexen_sha256": hashlib.sha256(args.nexen.read_bytes()).hexdigest(),
                "map": str(map_path), "map_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
                "objects": objects, "before": before, "selected": selected,
                "secondary_mode": secondary_mode, "secondary_selected": secondary,
                "submitted": submitted, "transaction_trace": transaction_trace, "final": final,
                "mode_sequence": mode_sequence, "talk_input_ownership": talk_control,
            }
            (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            print(json.dumps(report, sort_keys=True))
        finally:
            session.remove_hook(hook)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
