#!/usr/bin/env python3
"""Bounded S6 preflight against the redistributable Fate of Atlantis demo."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5 import (
    LucasartsScummV5ResourceProvider, ScummV5Charset, decode_room, parse_game_policy,
)
from same.engines.scumm_v5.engine import ScriptSlot
from same.errors import EngineExecutionError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
DEFAULT_ARCHIVE = Path("/home/chad/fatedemo-box.zip")
DEFAULT_OUTPUT = ROOT / "build/scumm-s6-fate-preflight/report.json"
ARCHIVE_SHA256 = "558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798"
MEMBERS = {
    "index": "FATEDEMO/PLAYFATE.000",
    "data": "FATEDEMO/PLAYFATE.001",
    "notice": "FATEDEMO/READ.ME",
}
REDISTRIBUTION_TEXT = (
    "You may freely copy and distribute this disk\r\n"
    "provided you do not alter or eliminate any\r\n"
    "copyright or trademark notices."
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def mounted_host(profile, raw: dict[str, bytes]) -> EngineHost:
    resources = MemoryResourceProvider(
        {
            "game.index": raw["index"],
            "game.data": raw["data"],
            "distribution.notice": raw["notice"],
        },
        kinds={"game.index": "SCIX", "game.data": "SCDT", "distribution.notice": "TEXT"},
    )
    services = HostServices.create(profile, resources=resources)
    host = EngineHost(profile, default_registry(), services=services)
    host.boot()
    require(
        isinstance(host.services.resources, LucasartsScummV5ResourceProvider),
        "raw v5 provider was not mounted",
    )
    return host


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    archive = args.archive.resolve()
    archive_bytes = archive.read_bytes()
    require(sha256(archive_bytes) == ARCHIVE_SHA256, "Fate demo archive identity differs")
    with zipfile.ZipFile(archive) as bundle:
        raw = {name: bundle.read(member) for name, member in MEMBERS.items()}
    notice = raw["notice"].decode("ascii")
    require(REDISTRIBUTION_TEXT in notice, "redistribution permission is absent")

    profile = load_profile(PROFILE, verify_resources=False)
    policy = parse_game_policy(profile)
    require(policy is not None, "Fate profile has no structured SCUMM policy")
    require(policy.audio_source == "embedded", "Fate audio policy is not embedded")

    host = mounted_host(profile, raw)
    provider = host.services.resources
    keys = provider.keys()
    families = {
        prefix: tuple(key for key in keys if key.startswith(prefix + "."))
        for prefix in ("room", "script", "sound", "costume", "charset")
    }
    expected_counts = {"room": 10, "script": 74, "sound": 28, "costume": 25, "charset": 4}
    observed_counts = {name: len(values) for name, values in families.items()}
    require(observed_counts == expected_counts, f"resource counts differ: {observed_counts}")

    expected_rooms = {
        "room.42": ((408, 144), [17, 18, 28, 67, 68]),
        "room.48": ((488, 144), [17, 28, 67, 68]),
        "room.49": ((640, 144), [18, 28, 68]),
        "room.63": ((408, 144), [28, 68]),
        "room.68": ((320, 200), [18]),
        "room.69": ((320, 144), [17, 18, 27, 28, 68]),
        "room.75": ((1280, 200), [14, 16, 26, 66]),
        "room.82": ((544, 144), [67]),
        "room.83": ((320, 200), [17, 18, 27, 28, 67, 68]),
        "room.98": ((8, 200), [34]),
    }
    decoded_rooms = {}
    for key, (dimensions, codecs) in expected_rooms.items():
        decoded = decode_room(provider.read(key), key=key)
        observed = ((decoded.width, decoded.height), sorted(set(decoded.strip_codecs)))
        require(observed == (dimensions, codecs), f"{key} decode differs: {observed}")
        decoded_rooms[key] = {
            "dimensions": list(dimensions),
            "strip_codecs": codecs,
            "object_ids": [obj.object_id for obj in decoded.objects],
            "entry_code": decoded.entry_script is not None,
            "exit_code": decoded.exit_script is not None,
            "local_scripts": [script_id for script_id, _ in decoded.local_scripts],
            "pixels_sha256": sha256(decoded.pixels),
        }

    selected = {}
    for key in ("script.1", "room.42", "sound.1", "costume.2", "charset.1"):
        data = provider.read(key)
        stat = provider.stat(key)
        selected[key] = {
            "kind": stat.kind,
            "size": stat.size,
            "sha256": sha256(data),
            "source": stat.source,
        }
    fate_font = ScummV5Charset(provider.read("charset.1"), key="charset.1")
    fate_three = fate_font.glyph(ord("3"))
    require(fate_three is not None, "Fate charset 1 has no digit-three glyph")
    require(
        (fate_three.width, fate_three.height, fate_three.x_offset, fate_three.y_offset)
        == (6, 8, 0, 0),
        "Fate digit-three glyph metrics differ",
    )

    # Pin the real room-75 ENCD frontier. Insert only scheduler yields between
    # its two exact commands so queue persistence is separately observable.
    room_75 = provider.read("room.75")
    encd_offset = room_75.find(b"ENCD")
    require(encd_offset >= 0, "Fate room 75 has no ENCD chunk")
    encd_size = int.from_bytes(room_75[encd_offset + 4 : encd_offset + 8], "big")
    require(encd_size >= 8, "Fate room 75 ENCD chunk is truncated")
    encd = room_75[encd_offset + 8 : encd_offset + encd_size]
    queue_bytes = encd[0xE7:0xEC]
    flush_bytes = encd[0xEC:0xF1]
    require(queue_bytes == bytes.fromhex("4c010b00ff"), "Fate command-11 bytes differ")
    require(flush_bytes == bytes.fromhex("4c01ffffff"), "Fate flush bytes differ")
    sound_host = mounted_host(profile, raw)
    sound_host.engine.state.scripts = [
        ScriptSlot(
            "room.75/ENCD-frontier",
            queue_bytes + b"\x80" + flush_bytes + b"\x80\x00",
            number=0,
        )
    ]
    sound_host.tick()
    queued_sound = sound_host.engine.inspect_state()["sound_kludge"]
    require(queued_sound == {"queue": [[11]], "history": [], "result": 0},
            "Fate command 11 did not remain queued across the inserted yield")
    require(
        not [packet for packet in sound_host.services.packet_history if packet["service_name"] == "AUDIO"],
        "Fate queued command emitted audio early",
    )
    sound_host.tick()
    flushed_sound = sound_host.engine.inspect_state()["sound_kludge"]
    require(flushed_sound == {"queue": [], "history": [[11]], "result": 0},
            "Fate command -1 did not flush command 11")
    sound_packets = [
        {key: packet[key] for key in ("opcode", "arg0", "arg1", "source", "destination")}
        for packet in sound_host.services.packet_history
        if packet["service_name"] == "AUDIO"
    ]
    require(
        sound_packets == [
            {"opcode": 1, "arg0": 0, "arg1": 0, "source": 6, "destination": 4},
            {"opcode": 3, "arg0": 0xFFFFFFFF, "arg1": 0, "source": 6, "destination": 4},
            {"opcode": 10, "arg0": 0, "arg1": 0, "source": 6, "destination": 4},
            {"opcode": 8, "arg0": 0, "arg1": 0, "source": 6, "destination": 4},
        ],
        f"Fate command 11 normalized audio differs: {sound_packets}",
    )

    # Pin and execute the exact four saveRestoreVerbs records from real script
    # 19. Copyright-free verbOps prefixes provide active records to move; the
    # bytes under test remain unmodified Fate data.
    script_19 = provider.read("script.19")
    save_verbs_offset = 0x117
    save_verbs_bytes = script_19[save_verbs_offset : save_verbs_offset + 20]
    require(
        save_verbs_bytes == bytes.fromhex(
            "ab01010c01ab01657005ab01646401ab01343701"
        ),
        "Fate script 19 saveRestoreVerbs bytes differ",
    )
    expected_saved = [
        *( (verb_id, 1) for verb_id in range(1, 13) ),
        *( (verb_id, 5) for verb_id in range(101, 113) ),
        (100, 1),
        *( (verb_id, 1) for verb_id in range(52, 56) ),
    ]
    verb_prefix = b"".join(bytes((0x7A, verb_id, 0x09, 0xFF)) for verb_id, _ in expected_saved)
    saved_verb_host = mounted_host(profile, raw)
    saved_verb_host.engine.state.scripts = [
        ScriptSlot(
            "script.19/saveRestoreVerbs-frontier",
            verb_prefix + save_verbs_bytes + b"\x80\x00",
            number=19,
        )
    ]
    saved_verb_host.tick()
    saved_verb_state = saved_verb_host.engine.inspect_state()
    observed_saved = [
        (record["id"], record["bank"])
        for record in saved_verb_state["saved_verbs"]
    ]
    require(observed_saved == expected_saved, "Fate saved-verb banks differ")
    require(
        not set(saved_verb_state["verbs"]).intersection(
            str(verb_id) for verb_id, _ in expected_saved
        ),
        "Fate saved verbs remained in the active namespace",
    )

    # C27/C28: resolve room 75's exact local script 200 and execute both of its
    # canonical animateActor requests across their real breakHere boundaries.
    decoded_75 = decode_room(room_75, key="room.75")
    local_identities = [script_id for script_id, _ in decoded_75.local_scripts]
    require(local_identities == list(range(200, 209)), "Fate room 75 LSCR identities differ")
    require(decoded_75.entry_script is not None, "Fate room 75 has no decoded entry code")
    local_host = mounted_host(profile, raw)
    local_host.engine.state.scripts = [
        ScriptSlot("room.75/load", bytes((0x72, 75, 0x80)), number=0)
    ]
    local_host.tick()
    local_host.engine.state.scripts = [
        ScriptSlot("room.75/ENCD", decoded_75.entry_script, number=0, room=75)
    ]
    try:
        local_host.tick()
    except EngineExecutionError as exc:
        local_next_error = str(exc)
    else:
        raise RuntimeError("Fate room 75 entry did not reach local script 205's frontier")
    local_first = local_host.engine.inspect_state()
    local_200 = [slot for slot in local_first["scripts"] if slot["number"] == 200]
    require(
        len(local_200) == 1
        and local_200[0]["resource"] == "room.75/LSCR.200"
        and local_200[0]["room"] == 75
        and local_200[0]["pc"] == 0x83B,
        f"Fate room-local script resolution differs: {local_200}",
    )
    require(
        local_first["actors"]["10"]["animation"] == 250,
        "Fate local script 200 first animation differs",
    )
    require(
        "opcode $D5 is not implemented" in local_next_error
        and "script room.75/LSCR.205, offset $0004" in local_next_error,
        f"Fate next local-script frontier differs: {local_next_error}",
    )
    local_host.engine.state.scripts = [
        slot for slot in local_host.engine.state.scripts if slot.number == 200
    ]
    require(local_host.context is not None, "Fate local-script host has no engine context")
    local_host.engine.tick(local_host.context)
    local_second = local_host.engine.inspect_state()
    local_200_second = [slot for slot in local_second["scripts"] if slot["number"] == 200]
    require(
        len(local_200_second) == 1 and local_200_second[0]["pc"] == 0x83F,
        f"Fate room-local second yield differs: {local_200_second}",
    )
    require(
        local_second["actors"]["10"]["animation"] == 6,
        "Fate local script 200 second animation differs",
    )

    # SAME save states remain available even though this demo intentionally
    # disables the original game's save/load menu.
    before = host.engine.inspect_state()
    saved = host.save(0)
    host.engine.state.variables[0] = 1234
    host.load(0)
    after = host.engine.inspect_state()
    require(after == before, "engine save-state round trip changed boot state")

    # Use a second host to pin the raw-room crossing and bounded boot completion.
    frontier_host = mounted_host(profile, raw)
    try:
        frontier_host.tick(pointer=(319, 199), pointer_buttons=((0, True),))
    except EngineExecutionError as exc:
        raise RuntimeError(f"Fate did not cross the raw-room frontier: {exc}") from exc
    room_state = frontier_host.engine.inspect_state()
    room_video = room_state["video"]
    require(room_state["room"] == 68, "Fate did not enter room 68")
    require(room_video["format"] == "raw-v5", "Fate room did not use the raw-v5 adapter")
    require(room_video["dimensions"] == [320, 200], "Fate room dimensions differ")
    require(room_video["strip_codecs"] == [18], "Fate room strip codecs differ")
    require(
        room_video["logical_sha256"]
        == "2f633aec02b1b7f5e22adc70e18aa15fff9a668b3b15d5c829ae1b1907e57490",
        "Fate decoded logical room image differs",
    )
    require(
        room_state["room_hash"]
        == "31539e278fb6a3485bd02859a4c6363b633814a6316fd7c61050f8ecb0e90581",
        "Fate projected room image differs",
    )
    draw_state = None
    null_state = None
    boot_state = None
    boot_frame = -1
    for frame in range(1, 600):
        try:
            buttons = ((0, False),) if frame == 1 else ()
            frontier_host.tick(pointer=(319, 199), pointer_buttons=buttons)
            candidate = frontier_host.engine.inspect_state()
            if draw_state is None and candidate["object_draw_queue"] == [939]:
                draw_state = candidate
            if frame == 523:
                null_state = candidate
            if (
                candidate["room"] == 75
                and not any(slot["number"] == 1 for slot in candidate["scripts"])
            ):
                boot_state = candidate
                boot_frame = frame
                break
        except EngineExecutionError as exc:
            raise RuntimeError(f"Fate boot failed at frame {frame}: {exc}") from exc
    require(boot_frame == 524, f"Fate boot completion frame differs: {boot_frame}")
    require(null_state is not None and boot_state is not None, "Fate boot checkpoints are absent")
    next_frontier_state = null_state
    require(draw_state is not None, "Fate never exposed object 939 draw intent")
    require(draw_state["object_states"] == {"939": 1}, "Fate drawObject state differs")
    require(draw_state["object_draw_queue"] == [939], "Fate draw queue differs")
    require(
        draw_state["room_objects"].get("939")
        == {"position": [24, 32], "size": [272, 144], "walk": [0, 0], "state": 1},
        "Fate object 939 geometry/state differs",
    )
    require(next_frontier_state["room"] == 0, "Fate did not enter the null room")
    require(next_frontier_state["video"] is None, "Fate null room retained a room adapter")
    require(next_frontier_state["room_objects"] == {}, "Fate null room retained local objects")
    require(next_frontier_state["object_draw_queue"] == [], "Fate null room retained draw intent")
    require(next_frontier_state["object_states"] == {"939": 1}, "Fate null room lost global object state")
    require(
        next_frontier_state["print"]["slots"][0]
        == {
            "position": [160, 8], "right": 319, "height": 0, "color": 15,
            "charset": 0, "center": True, "overhead": True,
        },
        "Fate print-slot defaults differ",
    )
    require(next_frontier_state["print"]["messages"] == [], "Fate setup-only print emitted text")
    require(
        next_frontier_state["room_hash"]
        == "29085ca155744dcd9a3cb40e9314da21d470d8da98a1b762a13389521ac19a9b",
        "Fate null-room presentation differs",
    )
    require(boot_state["room"] == 75, "Fate boot did not enter room 75")
    require(boot_state["operations"] == 653, "Fate boot operation count differs")
    require(boot_state["last_opcode"] == 0x62, "Fate boot terminal opcode differs")
    require(
        boot_state["room_hash"]
        == "03c2fbb7571a6848f81d73fe70b06bb0451de2969327a6bd722e7b7f0e37c46c",
        "Fate room 75 presentation differs",
    )
    require(
        boot_state["video"] == {
            "mode": "room",
            "logical_sha256": "b63a1147fe8a63eccbfe9da27667582df8b82d61f3653bfb29da4a038dff5a1e",
            "format": "raw-v5", "dimensions": [1280, 200],
            "strip_codecs": [14, 16, 26, 66],
            "projection": [512, 0, 0, 12, 256, 200],
        },
        "Fate room 75 adapter state differs",
    )
    require(
        boot_state["cutscenes"] == {
            "stack_pointer": 0,
            "sentinel": {"data": 0, "override_pc": None, "override_slot": None},
            "records": [], "script_index": None,
        },
        "Fate boot left cutscene/override state armed",
    )
    main_slots = [slot for slot in boot_state["scripts"] if slot["resource"] == "script.1"]
    random_boot_slots = [slot for slot in boot_state["scripts"] if slot["number"] == 75]
    require(
        len(main_slots) == 1 and main_slots[0]["pc"] == 13168 and not main_slots[0]["active"],
        "Fate main boot script did not retire at the canonical PC",
    )
    require(
        len(random_boot_slots) == 1
        and random_boot_slots[0]["pc"] == 7
        and random_boot_slots[0]["delay"] == 225,
        "Fate post-boot random-delay helper differs",
    )
    frontier_state = room_state
    require(frontier_state["random_state"] == 0xE270, "Fate random state differs")
    require(frontier_state["variables"].get("442") == 19, "Fate post-expression variable 442 differs")
    random_slots = [slot for slot in frontier_state["scripts"] if slot["number"] == 75]
    require(len(random_slots) == 1, "Fate random-delay script slot differs")
    require(
        random_slots[0]["pc"] == 7 and random_slots[0]["delay"] == 226,
        "Fate random-delay script did not consume the generated value",
    )
    cutscene_slots = [slot for slot in frontier_state["scripts"] if slot["number"] == 74]
    callback_slots = [slot for slot in frontier_state["scripts"] if slot["resource"] == "script.20"]
    require(
        len(cutscene_slots) == 1
        and cutscene_slots[0]["pc"] == 19
        and cutscene_slots[0]["cutscene_override"] == 1,
        "Fate cutscene owner state differs",
    )
    require(
        len(callback_slots) == 1
        and callback_slots[0]["pc"] == 146
        and not callback_slots[0]["active"]
        and callback_slots[0]["number"] == 0,
        "Fate cutscene-start callback state differs",
    )
    require(
        frontier_state["cutscenes"] == {
            "stack_pointer": 1,
            "sentinel": {"data": 0, "override_pc": None, "override_slot": None},
            "records": [{"data": 0, "override_pc": None, "override_slot": None}],
            "script_index": None,
        },
        f"Fate cutscene stack differs: {frontier_state['cutscenes']}",
    )
    resource_mapper = bytes(frontier_state["resource_mapper"])
    require(len(resource_mapper) == 128, "Fate pseudo-room mapper size differs")
    require(sum(room != 0 for room in resource_mapper) == 100, "Fate pseudo-room count differs")
    require(
        sha256(resource_mapper) == "d0261cd24b58bfae0f72c0cdf1b78811de6db8f9240cd08b937661ac59360d4c",
        "Fate pseudo-room mapper contents differ",
    )
    iq_string = frontier_state["strings"].get("31")
    require(isinstance(iq_string, dict), "Fate string 31 allocation is absent")
    iq_raw = bytes(iq_string["raw"])
    require(
        iq_raw == bytes((100,)) * 169 + b"\0",
        "absent iq-points data altered string 31",
    )
    require(
        frontier_state["room_ops"]["auxiliary_files"] == {},
        "Fate roomOps unexpectedly persisted auxiliary data",
    )
    require(
        frontier_state["room_ops"]["fade_effect"] == 257,
        "Fate cutscene-start room effect differs",
    )
    resource_ops = frontier_state["resource_ops"]
    require(
        all(not ids for ids in resource_ops["loaded"].values())
        and all(not ids for ids in resource_ops["locked"].values())
        and resource_ops["last_object"] is None,
        "Fate clear-heap resource intent differs",
    )
    actors = frontier_state["actors"]
    require(set(actors) == {"1", "2", "4"}, f"Fate initialized actors differ: {sorted(actors)}")
    expected_actors = {
        "1": {"costume": 2, "talk_color": 15, "name": list(b"Indy\0")},
        "2": {"costume": 28, "talk_color": 13, "name": list(b"Sophia\0")},
        "4": {"costume": 0, "talk_color": 14, "name": list(b"\0")},
    }
    observed_actors = {
        actor_id: {key: actors[actor_id][key] for key in expected}
        for actor_id, expected in expected_actors.items()
    }
    require(observed_actors == expected_actors, f"Fate actor initialization differs: {observed_actors}")
    require(frontier_state["camera_follow_actor"] == 1, "Fate camera-follow actor differs")
    require(
        frontier_state["object_classes"] == {"2": [13]},
        f"Fate object-class state differs: {frontier_state['object_classes']}",
    )
    verbs = frontier_state["verbs"]
    expected_verb_ids = [
        *range(1, 13),
        *range(50, 56),
        *range(100, 113),
        *range(129, 133),
    ]
    require(sorted(map(int, verbs)) == expected_verb_ids, f"Fate verb ids differ: {sorted(verbs)}")
    verb_sha256 = sha256(
        json.dumps(verbs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    require(
        verb_sha256 == "529832847d12cfba47ae6c11e2896fb937e3454aa332ac095b4e64691599ae6c",
        f"Fate verb state differs: {verb_sha256}",
    )
    input_state = dict(frontier_state["input"])
    require(input_state["cursor"] == [319, 199], "logical pointer did not reach the engine")
    require(input_state["pressed_buttons"] == [], "doSentence $FE did not clear the click edge")
    require(input_state["held_buttons"] == ["primary"], "doSentence $FE released the held pointer")
    require(frontier_state["sentences"] == [], "Fate doSentence cancellation left queued state")
    room_68 = provider.read("room.68")
    require(room_68.startswith(b"RMHD"), "Fate room 68 raw header differs")
    require(len(room_68) == 19376, "Fate room 68 size differs")
    require(
        sha256(room_68) == "5dd186865274ec69a538bd488825538b6b434e9a8098e07da5d2e9aeeae014ce",
        "Fate room 68 identity differs",
    )
    variables = frontier_state["variables"]
    expected_ranges = {
        "127": 0, "128": 0xB0, "129": 0xB0, "130": 0xB0,
        "131": 0xB0, "132": 0xB0, "133": 0xB0, "134": 0,
        "135": 0x9C, "136": 0xA5, "137": 0xAE, "138": 0xB7,
        "139": 0xC0, "140": 0xC0,
    }
    observed_ranges = {key: variables.get(key, 0) for key in expected_ranges}
    require(observed_ranges == expected_ranges, f"Fate setVarRange state differs: {observed_ranges}")

    core = ROOT / "src/same/engines/scumm_v5/engine.py"
    core_text = core.read_text(encoding="utf-8").lower()
    require("indy4" not in core_text and "atlantis" not in core_text, "game policy entered opcode core")

    report = {
        "gate": "S6",
        "result": "incomplete",
        "s6_gate_passed": False,
        "preflight": "pass",
        "archive": str(archive),
        "archive_sha256": sha256(archive_bytes),
        "redistribution_permission_present": True,
        "notice_sha256": sha256(raw["notice"]),
        "profile": PROFILE.relative_to(ROOT).as_posix(),
        "profile_sha256": sha256(PROFILE.read_bytes()),
        "policy": {
            "audio_source": policy.audio_source,
            "copy_protection": policy.copy_protection_mode,
            "costume_template": policy.costume_key_template,
            "charset_template": policy.charset_key_template,
        },
        "raw_sources": {name: {"size": len(data), "sha256": sha256(data)} for name, data in raw.items()},
        "resource_counts": observed_counts,
        "decoded_rooms": decoded_rooms,
        "selected_resources": selected,
        "logical_input_before_frontier": input_state,
        "save_state": {
            "menu_supported_by_demo": False,
            "same_round_trip": True,
            "schema": saved.schema,
            "payload_sha256": sha256(saved.payload),
        },
        "boot_frontier": None,
        "sound_kludge": {
            "crossed_opcode": "$4C",
            "room": 75,
            "chunk": "ENCD",
            "queue_offset": "$00E7",
            "flush_offset": "$00EC",
            "queue_bytes": queue_bytes.hex(),
            "flush_bytes": flush_bytes.hex(),
            "queued": queued_sound,
            "flushed": flushed_sound,
            "audio_packets": sound_packets,
        },
        "save_restore_verbs": {
            "crossed_opcode": "$AB",
            "script": 19,
            "offset": f"${save_verbs_offset:04X}",
            "bytes": save_verbs_bytes.hex(),
            "saved": [list(identity) for identity in observed_saved],
        },
        "room_local_scripts": {
            "room": 75,
            "chunk": "LSCR",
            "script_ids": local_identities,
            "resolved_script": 200,
            "resource": local_200[0]["resource"],
            "crossed_opcode": "$11",
            "first_offset": "$0837",
            "second_offset": "$083B",
            "animations": [250, 6],
        },
        "boot_completion": {
            "frame": boot_frame,
            "operations": boot_state["operations"],
            "last_opcode": f"${boot_state['last_opcode']:02X}",
            "main_script_pc": main_slots[0]["pc"],
            "room": boot_state["room"],
            "room_sha256": boot_state["room_hash"],
            "zero_depth_override": {
                "opcode": "$58", "script": 21, "offset": "$0004",
                "sentinel_cleared": True,
            },
        },
        "resource_routines": {
            "crossed_opcode": "$0C",
            "operation": "clearHeap",
            "loaded": resource_ops["loaded"],
            "locked": resource_ops["locked"],
            "last_object": resource_ops["last_object"],
        },
        "actor_ops": {
            "crossed_opcode": "$13",
            "actors": observed_actors,
        },
        "actor_follow_camera": {
            "crossed_opcode": "$D2",
            "actor": frontier_state["camera_follow_actor"],
        },
        "set_class": {
            "crossed_opcode": "$5D",
            "object_classes": frontier_state["object_classes"],
        },
        "verb_ops": {
            "crossed_opcode": "$7A",
            "verb_ids": expected_verb_ids,
            "verbs_sha256": verb_sha256,
            "active_scripts": [
                [slot["number"], slot["pc"]] for slot in frontier_state["scripts"]
            ],
        },
        "expression": {
            "crossed_opcode": "$AC",
            "script": 132,
            "completed_before_slot_reuse": True,
        },
        "cutscene": {
            "crossed_opcodes": ["$40", "$58"],
            "owner_script": 74,
            "owner_pc": cutscene_slots[0]["pc"],
            "owner_override_depth": cutscene_slots[0]["cutscene_override"],
            "stack": frontier_state["cutscenes"],
            "start_callback_script": 20,
            "start_callback_pc": callback_slots[0]["pc"],
            "start_callback_complete": True,
            "room_effect": frontier_state["room_ops"]["fade_effect"],
        },
        "do_sentence": {
            "crossed_opcode": "$19",
            "verb": "$FE",
            "sentence_queue": frontier_state["sentences"],
            "sentence_script": frontier_state["variables"].get("33", 0),
            "callback_complete": True,
            "click_edge_cleared": True,
            "held_pointer_preserved": True,
        },
        "raw_room_frontier": {
            "crossed_opcode": "$72",
            "script": 74,
            "script_pc": cutscene_slots[0]["pc"],
            "room": 68,
            "resource_size": len(room_68),
            "resource_prefix": room_68[:4].decode("ascii"),
            "resource_sha256": sha256(room_68),
            "format": room_video["format"],
            "dimensions": room_video["dimensions"],
            "strip_codecs": room_video["strip_codecs"],
            "logical_sha256": room_video["logical_sha256"],
            "projected_sha256": room_state["room_hash"],
        },
        "draw_object": {
            "crossed_opcode": "$05",
            "script": 74,
            "offset": "$0033",
            "object": 939,
            "object_record": draw_state["room_objects"]["939"],
            "object_states": draw_state["object_states"],
            "draw_queue": draw_state["object_draw_queue"],
        },
        "null_room": {
            "crossed_opcode": "$72",
            "script": 74,
            "offset": "$0078",
            "room": next_frontier_state["room"],
            "video": next_frontier_state["video"],
            "room_objects": next_frontier_state["room_objects"],
            "draw_queue": next_frontier_state["object_draw_queue"],
            "global_object_states": next_frontier_state["object_states"],
            "projected_sha256": next_frontier_state["room_hash"],
        },
        "animate_actor": {
            "opcode": "$11",
            "operation": "animateActor",
            "room": 75,
            "script": 200,
            "offsets": ["$0837", "$083B"],
            "animations": [250, 6],
        },
        "next_opcode_frontier": {
            "opcode": "$D5",
            "operation": "getActorFromPos",
            "room": 75,
            "script": 205,
            "offset": "$0004",
        },
        "print_defaults": next_frontier_state["print"],
        "font": {
            "resource": "charset.1", "format": "raw-v5-char",
            "digit_three_metrics": [
                fate_three.width, fate_three.height,
                fate_three.x_offset, fate_three.y_offset,
            ],
        },
        "room_ops_load_string": {
            "filename": "iq-points",
            "destination_string": 31,
            "absent_file_preserved_destination": True,
            "destination_sha256": sha256(iq_raw),
        },
        "get_random_nr": {
            "script": 75,
            "maximum": 255,
            "result_variable": 442,
            "result": 226,
            "delay": 226,
            "frontier_variable_value": 19,
            "random_state": 0xE270,
        },
        "pseudo_rooms": {
            "entries": 128,
            "mapped_entries": 100,
            "mapper_sha256": sha256(resource_mapper),
            "mapped_rooms": {
                str(index): room for index, room in enumerate(resource_mapper) if room
            },
        },
        "set_var_range_127_140": observed_ranges,
        "remaining_gate_proofs": ["actor behavior", "embedded audio playback"],
        "opcode_core_game_identity_branch": False,
        "opcode_core_sha256": sha256(core.read_bytes()),
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("S6 Fate demo preflight: PASS (S6 remains incomplete)")
    print(output)
    print(sha256(output.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
