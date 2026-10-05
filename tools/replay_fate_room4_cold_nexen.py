#!/usr/bin/env python3
"""Cold-run the authentic room-4 object61 input path on a ROM-bound Nexen.

The only gameplay inputs are deterministic controller edges derived from the
authentic object hitbox.  Debugger APIs are used for read-only observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "examples/replays/fate-room4-open-trapdoor.json"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)


def _u16(session: Any, address: int) -> int:
    return int.from_bytes(session.read_memory("snesMemory", address, 2), "little")


def _slots(session: Any) -> list[dict[str, int]]:
    statuses = session.read_memory("snesMemory", 0x7E2380, 24)
    numbers = session.read_memory("snesMemory", 0x7E2399, 24)
    programs = session.read_memory("snesMemory", 0x7E23B2, 24)
    pcs = session.read_memory("snesMemory", 0x7E23E4, 48)
    delays = session.read_memory("snesMemory", 0x7E2416, 48)
    freeze_resistant = session.read_memory("snesMemory", 0x7E2AD6, 24)
    freeze_counts = session.read_memory("snesMemory", 0x7E2B08, 24)
    rooms = session.read_memory("snesMemory", 0x7FF2E7, 24)
    return [
        {
            "slot": i,
            "status": statuses[i],
            "script": numbers[i],
            "program": programs[i],
            "saved_pc": int.from_bytes(pcs[i * 2:i * 2 + 2], "little"),
            "delay": int.from_bytes(delays[i * 2:i * 2 + 2], "little"),
            "freeze_resistant": freeze_resistant[i],
            "freeze_count": freeze_counts[i],
            "room_owner": rooms[i],
        }
        for i in range(24) if statuses[i] not in (0, 4)
    ]


def _snapshot(session: Any) -> dict[str, Any]:
    from fate_replay import room4_controller_snapshot

    c19_override_pc = session.read_memory("snesMemory", 0x7FD354, 10)
    c19_override_slot = session.read_memory("snesMemory", 0x7FD35E, 5)
    c19_slot_depth = session.read_memory("snesMemory", 0x7FD363, 25)
    talk_raw_length = session.read_u8(0x7E7A28)
    talk_raw = session.read_memory(
        "snesMemory", 0x7E7A30, min(talk_raw_length, 32)
    )
    bit69_byte = session.read_u8(0x7E2BA0 + (69 >> 3))
    bit35_byte = session.read_u8(0x7E2BA0 + (35 >> 3))
    room_lifecycle = session.read_memory("snesMemory", 0x7FF2BE, 8)
    actor1 = session.read_memory("snesMemory", 0x7F3700, 64)
    actor1_position = session.read_memory("snesMemory", 0x7FF1A4, 4)
    return {
        "frame": int(session.get_state()["frameCount"]),
        **room4_controller_snapshot(session),
        "active_record": room_lifecycle[0],
        "pending_record": room_lifecycle[2],
        "pending_room": room_lifecycle[3],
        "return_program": room_lifecycle[5],
        "m23a_return_valid": session.read_u8(0x7FF467),
        "m23a_return_slot": session.read_u8(0x7FF468),
        "m23a_return_mode": session.read_u8(0x7FF469),
        "m23a_return_pc": _u16(session, 0x7FF2E5),
        "bit69": int(bool(bit69_byte & (1 << (69 & 7)))),
        "bit35": int(bool(bit35_byte & (1 << (35 & 7)))),
        "bit64_71": [
            int(bool(bit69_byte & (1 << bit))) for bit in range(8)
        ],
        "object61_state": session.read_u8(0x7E6000 + 61),
        "object61_owner": session.read_u8(0x7E8000 + 61),
        "actor1_room": actor1[0x16],
        "actor1_visible": actor1[0x15],
        "actor1_x": int.from_bytes(actor1_position[:2], "little", signed=True),
        "actor1_y": int.from_bytes(actor1_position[2:], "little", signed=True),
        "actor1_moving": session.read_u8(0x7FF221),
        "current_slot": session.read_u8(0x7E2A88),
        "scheduler_slot": session.read_u8(0x7E2B22),
        "active_slot_count": session.read_u8(0x7E2A8A),
        "program_select": session.read_u8(0x7E2362),
        "shared_vm_pc": _u16(session, 0x7E2300),
        "return_mode": session.read_u8(0x7E2363),
        "nested_depth": session.read_u8(0x7FD335),
        "talk_stop_count": session.read_u8(0x7E7A2A),
        "talk_complete_count": session.read_u8(0x7E7A2B),
        "talk_raw_length": talk_raw_length,
        "talk_raw_hex": talk_raw.hex(),
        "c19": {
            "stack_pointer": session.read_u8(0x7FD348),
            "data_words": [
                _u16(session, 0x7FD34A + index * 2) for index in range(5)
            ],
            "override_pc": [
                int.from_bytes(c19_override_pc[index * 2:index * 2 + 2], "little")
                for index in range(5)
            ],
            "override_slot": list(c19_override_slot),
            "slot_depth": list(c19_slot_depth),
        },
        "slots": _slots(session),
    }


def _authentic_room4_object61_use_source(archive: Path) -> dict[str, Any]:
    """Verify the exact external source body that motivates the next action."""
    sys.path.insert(0, str(ROOT / "src"))
    from same.profile import load_profile
    from same.resources import MemoryResourceProvider
    from same.engines.scumm_v5.policy import parse_game_policy
    from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
    from same.engines.scumm_v5.room import decode_room

    profile = load_profile(
        ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
        verify_resources=False,
    )
    with zipfile.ZipFile(archive) as bundle:
        index = bundle.read("ATLANTIS/ATLANTIS.000")
        data = bundle.read("ATLANTIS/ATLANTIS.001")
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider({"game.index": index, "game.data": data}),
        parse_game_policy(profile),
    )
    room_payload = provider.read("room.4")
    decoded = decode_room(room_payload, key="room.4")
    obj = next(item for item in decoded.objects if item.object_id == 61)
    use_entry = next(offset for verb, offset in obj.verb_entries if verb == 10)
    use_program = obj.obcd[use_entry:]
    expected_prefix = bytes.fromhex(
        "28 45 80 06 00 0A C8 FF 18 03 00 0A CB FF 00"
    )
    if obj.authored_verbs != (3, 4, 9, 10, 90):
        raise RuntimeError(f"authentic object61 verb order changed: {obj.authored_verbs!r}")
    if not use_program.startswith(expected_prefix):
        raise RuntimeError(
            f"authentic object61 Use body prefix differs: {use_program[:len(expected_prefix)].hex()}"
        )
    room_source = provider._rooms[4]
    return {
        "classification": "authentic external SCUMM v5 resource",
        "archive": str(archive.resolve()),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_members": ["ATLANTIS/ATLANTIS.000", "ATLANTIS/ATLANTIS.001"],
        "room": 4,
        "lflf_source_offset": room_source.offset,
        "room_payload_size": len(room_payload),
        "room_payload_sha256": hashlib.sha256(room_payload).hexdigest(),
        "walkbox_count": len(decoded.walkboxes),
        "local_scripts": [
            {
                "script": number,
                "body_size": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
            }
            for number, body in decoded.local_scripts
        ],
        "local_scripts": [
            {
                "script": number,
                "body_size": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
            }
            for number, body in decoded.local_scripts
        ],
        "object": 61,
        "object_name": obj.object_name.rstrip(b"\0").decode("latin1"),
        "object_rectangle": [obj.x, obj.y, obj.width, obj.height],
        "object_walk_point": [obj.walk_x, obj.walk_y],
        "authored_verbs": list(obj.authored_verbs),
        "obcd_room_relative_offset": obj.obcd_room_offset,
        "obcd_sha256": hashlib.sha256(obj.obcd).hexdigest(),
        "use_entry_offset_in_obcd": use_entry,
        "use_program_size_from_entry": len(use_program),
        "use_program_sha256": hashlib.sha256(use_program).hexdigest(),
        "use_program_prefix_hex": use_program[:len(expected_prefix)].hex(),
        "bit69_branch": {
            "condition": "if bit69 == 0, start LSCR200; otherwise start LSCR203",
            "evidence": "28 45 80 06 00; 0A C8 FF; 18 03 00; 0A CB FF",
        },
    }


def _authentic_room5_rope_source(archive: Path) -> dict[str, Any]:
    """Authenticate object77's verb9 and its room6 transition dependency."""
    sys.path.insert(0, str(ROOT / "src"))
    from same.profile import load_profile
    from same.resources import MemoryResourceProvider
    from same.engines.scumm_v5.policy import parse_game_policy
    from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
    from same.engines.scumm_v5.room import decode_room

    profile = load_profile(
        ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
        verify_resources=False,
    )
    with zipfile.ZipFile(archive) as bundle:
        index = bundle.read("ATLANTIS/ATLANTIS.000")
        data = bundle.read("ATLANTIS/ATLANTIS.001")
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider({"game.index": index, "game.data": data}),
        parse_game_policy(profile),
    )
    payload = provider.read("room.5")
    decoded = decode_room(payload, key="room.5")
    source = provider._rooms[5]
    obj = next(item for item in decoded.objects if item.object_id == 77)
    rope_entry = next(offset for verb, offset in obj.verb_entries if verb == 9)
    rope_program = obj.obcd[rope_entry:]
    expected_prefix = bytes.fromhex("28 45 80 06 00 0A C9 FF 18 35 00")
    if obj.authored_verbs != (8, 9, 90):
        raise RuntimeError(f"authentic object77 verb order changed: {obj.authored_verbs!r}")
    if not rope_program.startswith(expected_prefix):
        raise RuntimeError(
            "authentic room5 object77 verb9 body prefix changed: "
            f"{rope_program[:len(expected_prefix)].hex()}"
        )
    local_script = dict(decoded.local_scripts).get(201)
    if local_script is None or len(local_script) != 137:
        raise RuntimeError("authentic room5 LSCR201 dependency is missing or changed size")
    if not local_script.endswith(bytes.fromhex("C0 72 06 A0")):
        raise RuntimeError(
            "authentic room5 LSCR201 no longer ends in endCutscene/loadRoom(6)/STOP"
        )
    return {
        "classification": "authentic external SCUMM v5 resource",
        "archive": str(archive.resolve()),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_members": ["ATLANTIS/ATLANTIS.000", "ATLANTIS/ATLANTIS.001"],
        "room": 5,
        "lflf_source_offset": source.offset,
        "room_payload_size": len(payload),
        "room_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "object": 77,
        "object_name": obj.object_name.rstrip(b"\\0").decode("latin1"),
        "object_rectangle": [obj.x, obj.y, obj.width, obj.height],
        "object_walk_point": [obj.walk_x, obj.walk_y],
        "authored_verbs": list(obj.authored_verbs),
        "obcd_sha256": hashlib.sha256(obj.obcd).hexdigest(),
        "verb9_entry_offset": rope_entry,
        "verb9_body_size": len(rope_program),
        "verb9_body_sha256": hashlib.sha256(rope_program).hexdigest(),
        "verb9_prefix_hex": rope_program[:len(expected_prefix)].hex(),
        "branch": "bit69 == 0 starts room-local script201",
        "local_script201": {
            "size": len(local_script),
            "sha256": hashlib.sha256(local_script).hexdigest(),
            "tail_hex": local_script[-4:].hex(),
            "decoded_tail": "endCutscene; loadRoom(6); STOP",
        },
    }


def _authentic_room6_books_source(archive: Path) -> dict[str, Any]:
    """Authenticate the room6 books verb and the local it dispatches."""
    sys.path.insert(0, str(ROOT / "src"))
    from same.profile import load_profile
    from same.resources import MemoryResourceProvider
    from same.engines.scumm_v5.policy import parse_game_policy
    from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
    from same.engines.scumm_v5.room import decode_room

    profile = load_profile(
        ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
        verify_resources=False,
    )
    with zipfile.ZipFile(archive) as bundle:
        index = bundle.read("ATLANTIS/ATLANTIS.000")
        data = bundle.read("ATLANTIS/ATLANTIS.001")
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider({"game.index": index, "game.data": data}),
        parse_game_policy(profile),
    )
    payload = provider.read("room.6")
    decoded = decode_room(payload, key="room.6")
    source = provider._rooms[6]
    obj = next(item for item in decoded.objects if item.object_id == 91)
    verb_entry = next(offset for verb, offset in obj.verb_entries if verb == 10)
    verb_body = obj.obcd[verb_entry:]
    expected_prefix = bytes.fromhex(
        "28 45 80 03 00 0A C8 FF 00 28 45 80 03 00 0A C8 FF 00"
    )
    local_script = dict(decoded.local_scripts).get(200)
    if obj.authored_verbs != (9, 10) or obj.object_name.rstrip(b"\0") != b"books on statues":
        raise RuntimeError("authentic room6 object91 identity/verb set changed")
    if (obj.x, obj.y, obj.width, obj.height) != (0, 40, 40, 88):
        raise RuntimeError("authentic room6 object91 hit rectangle changed")
    if not verb_body.startswith(expected_prefix):
        raise RuntimeError(
            "authentic room6 object91 verb10 no longer starts local200 under bit69=0: "
            f"{verb_body[:len(expected_prefix)].hex()}"
        )
    if local_script is None or len(local_script) != 259:
        raise RuntimeError("authentic room6 LSCR200 is missing or changed size")
    return {
        "classification": "authentic external SCUMM v5 resource",
        "archive": str(archive.resolve()),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "room": 6,
        "lflf_source_offset": source.offset,
        "room_payload_size": len(payload),
        "room_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "object": 91,
        "object_name": obj.object_name.rstrip(b"\0").decode("latin1"),
        "object_rectangle": [obj.x, obj.y, obj.x + obj.width, obj.y + obj.height],
        "object_walk_point": [obj.walk_x, obj.walk_y],
        "authored_verbs": list(obj.authored_verbs),
        "verb10_body_size": len(verb_body),
        "verb10_body_sha256": hashlib.sha256(verb_body).hexdigest(),
        "verb10_prefix_hex": verb_body[:len(expected_prefix)].hex(),
        "branch": "equalZero(bit69); bit69=0 executes startScript(200)",
        "local_script200": {
            "size": len(local_script),
            "sha256": hashlib.sha256(local_script).hexdigest(),
            "generated_program_selector": 0x93,
        },
    }


def _parse_global_script_selector(generated_source: str, script: int) -> int:
    """Read one exact selector from this ROM's generated global resolver."""
    begin = generated_source.find("ScummV5_M23A_ResolveGlobalScript_Far:")
    end = generated_source.find("ScummV5_M23A_FetchProgramByte_Far:", begin)
    if begin < 0 or end < 0:
        raise RuntimeError("generated global resolver is missing or malformed")
    resolver = generated_source[begin:end]
    match = re.search(
        rf"cmp\s+#\${script:02X}\s*\n\s*bne\s+\S+\s*\n\s*lda\s+#\$([0-9A-Fa-f]{{2}})",
        resolver,
    )
    if match is None:
        raise RuntimeError(f"generated resolver does not map global script {script}")
    return int(match.group(1), 16)


def _authentic_room7_book_source(
    archive: Path, identity_path: Path,
) -> dict[str, Any]:
    """Bind the room-7 book verb and both reached global scripts to source."""
    sys.path.insert(0, str(ROOT / "src"))
    from same.profile import load_profile
    from same.resources import MemoryResourceProvider
    from same.engines.scumm_v5.policy import parse_game_policy
    from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
    from same.engines.scumm_v5.room import decode_room

    profile = load_profile(
        ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
        verify_resources=False,
    )
    policy = parse_game_policy(profile)
    with zipfile.ZipFile(archive) as bundle:
        index = bundle.read("ATLANTIS/ATLANTIS.000")
        data = bundle.read("ATLANTIS/ATLANTIS.001")
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider({"game.index": index, "game.data": data}), policy,
    )
    room_payload = provider.read("room.7")
    decoded = decode_room(room_payload, key="room.7")
    room_source = provider._rooms[7]
    obj = next(item for item in decoded.objects if item.object_id == 133)
    entry_offset = next(offset for verb, offset in obj.verb_entries if verb == 11)
    verb_body = obj.obcd[entry_offset:]
    expected_prefix = bytes.fromhex(
        "40 01 02 00 FF 0A 90 01 15 00 01 04 00 FF "
        "07 85 00 00 5D 85 00 01 A0 00 FF"
    )
    if (obj.object_name.rstrip(b"\0") != b"book"
            or obj.authored_verbs != (9, 11, 90)
            or (obj.x, obj.y, obj.width, obj.height) != (176, 120, 24, 8)):
        raise RuntimeError("authentic room7 object133 identity/verb set changed")
    if not verb_body.startswith(expected_prefix):
        raise RuntimeError(
            "room7 object133 verb11 no longer starts Global144([21,4]) and "
            f"the expected object/bit operations: {verb_body[:len(expected_prefix)].hex()}"
        )

    script_directory = provider._directories["DSCR"]

    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    generated_path = ROOT / "runtime/snes/generated/scumm_v5_room_data.inc.pasm"
    generated_relpath = str(generated_path.relative_to(ROOT))
    generated_identity = next((item for item in identity.get("generated_inputs", [])
                               if item.get("path") == generated_relpath), None)
    if generated_identity is None:
        raise RuntimeError("ROM build identity does not bind the global resolver")
    generated_sha = hashlib.sha256(generated_path.read_bytes()).hexdigest()
    if generated_sha != generated_identity.get("sha256"):
        raise RuntimeError(
            "global resolver differs from ROM build identity: "
            f"{generated_sha} != {generated_identity.get('sha256')}"
        )
    selected_objects = set(
        identity.get("explicit_environment", {}).get(
            "SAME_SCUMM_APPEND_TERMINAL_EXECUTABLE_LOCAL_OBJECTS", ""
        ).split(",")
    )
    if "7:133" not in selected_objects:
        raise RuntimeError(
            "ROM build identity does not select the authentic room7 object133 OBCD"
        )
    generated_text = generated_path.read_text(encoding="utf-8")
    record_entries = re.search(
        r"ScummV5_Verb_Record_6_Entries:\s*\.word\s+([^\n]+)",
        generated_text,
    )
    if record_entries is None:
        raise RuntimeError("ROM-bound generated room7 verb directory is missing")
    words = [int(item[1:], 16) for item in re.findall(r"\$[0-9A-Fa-f]{4}", record_entries[1])]
    entries = list(zip(words[0::3], words[1::3], words[2::3]))
    if not {(133, 9), (133, 11), (133, 90)}.issubset(
        {(object_id, verb) for object_id, verb, _offset in entries}
    ):
        raise RuntimeError(
            "ROM-bound room7 verb directory does not expose object133's authored verbs"
        )
    if "ScummV5_M23A_Program_73:" not in generated_text:
        raise RuntimeError("ROM-bound program selector $73 for room7 object133 is missing")
    reached_globals: dict[str, dict[str, Any]] = {}
    for global_number, expected_selector in ((144, 0x84), (145, 0x83)):
        global_key = policy.script_key_template.format(script=global_number)
        global_body = provider.read(global_key)
        global_room = script_directory.rooms[global_number]
        global_offset = script_directory.offsets[global_number]
        global_lflf = provider._rooms[global_room]
        global_chunk_offset = global_lflf.offset + 8 + global_offset
        program_selector = _parse_global_script_selector(
            generated_text, global_number,
        )
        if program_selector != expected_selector:
            raise RuntimeError(
                f"Global{global_number} selector changed unexpectedly: "
                f"${program_selector:02X} != ${expected_selector:02X}"
            )
        reached_globals[str(global_number)] = {
            "resource_key": global_key,
            "source_room": global_room,
            "directory_offset": global_offset,
            "chunk_header_offset": global_chunk_offset,
            "payload_offset": global_chunk_offset + 8,
            "size": len(global_body),
            "sha256": hashlib.sha256(global_body).hexdigest(),
            "program_selector": f"${program_selector:02X}",
        }
    return {
        "classification": "authentic external SCUMM v5 resources; unchanged",
        "archive": str(archive.resolve()),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "room": 7,
        "room_lflf_source_offset": room_source.offset,
        "room_payload_size": len(room_payload),
        "room_payload_sha256": hashlib.sha256(room_payload).hexdigest(),
        "object": 133,
        "object_name": obj.object_name.rstrip(b"\0").decode("latin1"),
        "object_rectangle_half_open": [176, 120, 200, 128],
        "authored_verbs": list(obj.authored_verbs),
        "object_obcd_sha256": hashlib.sha256(obj.obcd).hexdigest(),
        "verb": 11,
        "verb_offset_in_obcd": entry_offset,
        "verb_body_size": len(verb_body),
        "verb_body_sha256": hashlib.sha256(verb_body).hexdigest(),
        "object_program_selector": "$73",
        "verb_prefix_hex": verb_body[:len(expected_prefix)].hex(),
        "decoded_prefix": (
            "cutscene; startScript(144,[21,4]); "
            "setObjectState(133,0); setClass(object 133); clearBit(218)"
        ),
        "reached_globals": reached_globals,
        "generated_resolver": str(generated_path),
        "generated_resolver_sha256": generated_sha,
    }


def _authentic_room_source(archive: Path, room_number: int) -> dict[str, Any]:
    """Return provenance for an executed room from the external game archive."""
    sys.path.insert(0, str(ROOT / "src"))
    from same.profile import load_profile
    from same.resources import MemoryResourceProvider
    from same.engines.scumm_v5.policy import parse_game_policy
    from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
    from same.engines.scumm_v5.room import decode_room

    profile = load_profile(
        ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
        verify_resources=False,
    )
    with zipfile.ZipFile(archive) as bundle:
        index = bundle.read("ATLANTIS/ATLANTIS.000")
        data = bundle.read("ATLANTIS/ATLANTIS.001")
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider({"game.index": index, "game.data": data}),
        parse_game_policy(profile),
    )
    key = f"room.{room_number}"
    payload = provider.read(key)
    decoded = decode_room(payload, key=key)
    source = provider._rooms[room_number]
    return {
        "classification": "authentic external SCUMM v5 resource",
        "archive": str(archive.resolve()),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_members": ["ATLANTIS/ATLANTIS.000", "ATLANTIS/ATLANTIS.001"],
        "room": room_number,
        "lflf_source_offset": source.offset,
        "payload_size": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "entry_script": {
            "size": len(decoded.entry_script or b""),
            "sha256": hashlib.sha256(decoded.entry_script or b"").hexdigest(),
        },
        "exit_script": {
            "size": len(decoded.exit_script or b""),
            "sha256": hashlib.sha256(decoded.exit_script or b"").hexdigest(),
        },
        "walkbox_count": len(decoded.walkboxes),
        "local_scripts": [
            {
                "script": number,
                "size": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
            for number, body in decoded.local_scripts
        ],
        "objects": [
            {
                "object": obj.object_id,
                "name": obj.object_name.rstrip(b"\\0").decode("latin1"),
                "verbs": list(obj.authored_verbs),
                "obcd_sha256": hashlib.sha256(obj.obcd).hexdigest(),
            }
            for obj in decoded.objects
        ],
    }


def _parse_room_local_program_table(source: str, room_number: int) -> dict[int, int]:
    """Parse parallel generated local-number/selector arrays for one room."""
    pattern = re.compile(
        rf"; Complete executable-local directory for room {room_number}\.\s*\n"
        rf"ScummV5_M23A_RoomLocalNumbers_(\d+):\s*\n\s*\.byte ([^\n]+)\s*\n"
        rf"ScummV5_M23A_RoomLocalIndices_\1:\s*\n\s*\.word ([^\n]+)\s*\n"
        rf"ScummV5_M23A_RoomLocalPrograms_\1:\s*\n\s*\.byte ([^\n]+)",
        re.MULTILINE,
    )
    match = pattern.search(source)
    if match is None:
        raise RuntimeError(f"generated local selector table missing for room {room_number}")
    numbers = [int(item.strip().removeprefix("$"), 16)
               for item in match.group(2).split(",")]
    programs = [int(item.strip().removeprefix("$"), 16)
                for item in match.group(4).split(",")]
    if len(numbers) != len(programs):
        raise RuntimeError(
            f"room {room_number} generated local selector arrays differ in length"
        )
    return dict(zip(numbers, programs))


def _room_local_program_table(
    room_number: int, identity_path: Path,
) -> dict[str, Any]:
    """Read this ROM's generated room-local selector table, fail-closed."""
    include = ROOT / "runtime/snes/generated/scumm_v5_rooms.inc.pasm"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    input_identity = next((item for item in identity.get("generated_inputs", [])
                           if item.get("path") == str(include.relative_to(ROOT))), None)
    if input_identity is None:
        raise RuntimeError(
            "ROM build identity does not bind the generated room-local table"
        )
    include_sha = hashlib.sha256(include.read_bytes()).hexdigest()
    if include_sha != input_identity.get("sha256"):
        raise RuntimeError(
            "generated room-local table differs from the ROM build identity: "
            f"{include_sha} != {input_identity.get('sha256')}"
        )
    selectors = _parse_room_local_program_table(
        include.read_text(encoding="utf-8"), room_number
    )
    return {
        "room": room_number,
        "include": str(include),
        "include_sha256": include_sha,
        "script_to_program": selectors,
    }


def _live_slot_locals(session: Any, slots: list[dict[str, int]]) -> list[dict[str, Any]]:
    """Read live activation locals at a single boundary, not per-frame."""
    result = []
    for descriptor in slots:
        slot = descriptor["slot"]
        raw = session.read_memory("snesMemory", 0x7E2448 + slot * 64, 64)
        result.append({
            **descriptor,
            "locals_signed": [
                int.from_bytes(raw[index:index + 2], "little", signed=True)
                for index in range(0, 64, 2)
            ],
        })
    return result


def _parse_rom_variable_layout(listing_text: str) -> dict[str, int]:
    """Read variable RAM constants from a listing already verified for this ROM."""
    wanted = {"SAME_SCUMM_VARIABLES", "SAME_SCUMM_VARIABLE_COUNT"}
    found: dict[str, int] = {}
    pattern = re.compile(
        r"^;\s*(SAME_SCUMM_VARIABLES|SAME_SCUMM_VARIABLE_COUNT)\s*=\s*\$([0-9A-Fa-f]+)\s+\(Constant\)\s*$"
    )
    for line in listing_text.splitlines():
        match = pattern.match(line)
        if match and match.group(1) in wanted:
            name, raw_value = match.groups()
            if name in found:
                raise RuntimeError(f"duplicate {name} in ROM listing")
            found[name] = int(raw_value, 16)
    missing = wanted - found.keys()
    if missing:
        raise RuntimeError(
            "ROM-bound listing lacks SCUMM variable layout constants: "
            + ", ".join(sorted(missing))
        )
    if found["SAME_SCUMM_VARIABLE_COUNT"] <= 0:
        raise RuntimeError("ROM listing declares an empty SCUMM variable table")
    return {
        "base": found["SAME_SCUMM_VARIABLES"],
        "count": found["SAME_SCUMM_VARIABLE_COUNT"],
    }


def _room7_runtime_context(
    session: Any, *, variable_base: int, variable_count: int,
) -> dict[str, Any]:
    """Capture the authored room-7 puzzle state without changing game RAM."""
    if variable_count <= 0:
        raise ValueError("SCUMM variable count must be positive")
    raw_variables = session.read_memory(
        "snesMemory", variable_base, variable_count * 2
    )
    variables = [
        int.from_bytes(raw_variables[index * 2:index * 2 + 2], "little")
        for index in range(variable_count)
    ]
    raw_bits = session.read_memory("snesMemory", 0x7E2BA0, 512)
    set_bits = [
        byte_index * 8 + bit
        for byte_index, value in enumerate(raw_bits)
        for bit in range(8)
        if value & (1 << bit)
    ]
    first_object, object_end = 112, 136
    states = session.read_memory(
        "snesMemory", 0x7E6000 + first_object, object_end - first_object
    )
    owners = session.read_memory(
        "snesMemory", 0x7E8000 + first_object, object_end - first_object
    )
    class_records = session.read_memory("snesMemory", 0x7F5F10, 0x1000)
    room_object_ids = set(range(first_object, object_end))
    class_masks: dict[str, dict[str, Any]] = {}
    for offset in range(0, len(class_records), 8):
        if not class_records[offset]:
            continue
        object_id = int.from_bytes(class_records[offset + 2:offset + 4], "little")
        if object_id not in room_object_ids:
            continue
        mask = int.from_bytes(class_records[offset + 4:offset + 8], "little")
        class_masks[str(object_id)] = {
            "mask": f"0x{mask:08x}",
            "classes": [index + 1 for index in range(32) if mask & (1 << index)],
        }
    return {
        "evidence_class": "native room-7 RAM read at stable entry; no game-state writes",
        "global_variables": {
            "base": f"${variable_base:06X}",
            "count": variable_count,
        },
        "selected_variables": {
            str(index): variables[index]
            for index in (0, 35, 53, 69, 209, 210, 212, 214, 215, 219, 442, 443)
            if index < variable_count
        },
        "nonzero_global_variables": [
            {"index": index, "value": value}
            for index, value in enumerate(variables) if value != 0
        ],
        "set_bits": set_bits,
        "objects": [
            {"object": object_id, "state": states[object_id - first_object],
             "owner": owners[object_id - first_object]}
            for object_id in range(first_object, object_end)
        ],
        "object_classes_initialized": session.read_u8(0x7F6F1B),
        "object_classes": class_masks,
    }


def _sync_controller_done(session: Any, rom: Path,
                          symbol_banks: dict[str, int]) -> dict[str, Any]:
    from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom

    select_handle = session.add_exec_hook(mapped_cpu_address_for_rom(
        rom, "ScummV5_Controller_Frame__select_verb_a_pressed",
        bank=symbol_banks["ScummV5_Controller_Frame__select_verb_a_pressed"],
    ))
    done_handle = session.add_exec_hook(mapped_cpu_address_for_rom(
        rom, "ScummV5_Controller_Frame__done",
        bank=symbol_banks["ScummV5_Controller_Frame__done"],
    ))
    try:
        result = session.run_until(max_frames=2, hook_handle=done_handle)
        session.pause()
        if result.get("reason") != "hookFired":
            raise RuntimeError(f"controller did not reach its exit: {result!r}")
        selected_events = []
        for message in session.drain_notifications(timeout=0.0):
            params = message.get("params", message)
            if params.get("handle") == select_handle:
                selected_events.append(params)
        return {
            "symbol": "ScummV5_Controller_Frame__done",
            "run_until": result,
            "cpu_at_break": session.get_cpu_state(),
            "state_at_break": _snapshot(session),
            "unexpected_sentence_submit_branch_events": selected_events,
        }
    finally:
        session.remove_hook(select_handle)
        session.remove_hook(done_handle)


def _sync_break(session: Any, name: str, address: int) -> dict[str, Any]:
    """Stop synchronously at a native instruction and bind its event to state."""
    handle = session.add_exec_hook(address)
    try:
        result = session.run_until(max_frames=2, hook_handle=handle)
        session.pause()
        if result.get("reason") != "hookFired":
            raise RuntimeError(f"native breakpoint {name} was not reached: {result!r}")
        events = []
        for message in session.drain_notifications(timeout=0.0):
            params = message.get("params", message)
            if params.get("handle") == handle:
                events.append(params)
        if not events:
            raise RuntimeError(f"native breakpoint {name} has no event-time notification")
        event = events[-1]
        return {
            "symbol": name,
            "address": f"${address:06X}",
            "run_until": result,
            "hook_event": event,
            "cpu_at_break": session.get_cpu_state(),
            "state_at_break": _snapshot(session),
        }
    finally:
        session.remove_hook(handle)


def _talk_bytes(state: dict[str, Any]) -> bytes:
    return bytes((
        state["talk_active"], state["talk_have_msg"], 0, 0,
        state["talk_delay"] & 0xFF, state["talk_delay"] >> 8,
        state["talk_generation"] & 0xFF, state["talk_generation"] >> 8,
    ))


def _finish_room4_intro(session: Any, *, max_frames: int,
                        rom: Path, symbol_banks: dict[str, int]) -> dict[str, Any]:
    """Follow timed room-4 intro messages; acknowledge only authored FF03 waits."""
    from fate_replay import advance_bounded, room4_message_ready

    start = _snapshot(session)
    baseline_submissions = start["submissions"]
    start_frame = start["frame"]
    segments: dict[int, dict[str, Any]] = {}
    acknowledgements: list[dict[str, Any]] = []
    acked: set[int] = set()
    previous_generation: int | None = None
    while int(session.get_state()["frameCount"]) - start_frame < max_frames:
        state = _snapshot(session)
        if state["error"]:
            raise RuntimeError(f"SCUMM error during room-4 intro dialogue: {state!r}")
        if state["room"] != 4:
            raise RuntimeError(f"room changed during the deterministic room-4 intro: {state!r}")
        if state["talk_active"]:
            generation = state["talk_generation"]
            if generation not in segments:
                segments[generation] = {"first": state, "last": state}
            else:
                segments[generation]["last"] = state
            if (generation not in acked
                    and room4_message_ready(_talk_bytes(state), previous_generation)):
                item = _send_talk_owned_a_edge(
                    session, rom, symbol_banks, generation,
                    purpose="explicit-message-wait",
                )
                acknowledgements.append(item)
                acked.add(generation)
                previous_generation = generation
                continue
        if (
            state["talk_active"] == 0 and state["c19_stack_pointer"] == 0
            and state["ready"] == 1 and state["mode"] == 0
            and state["input_held"] == 0 and state["input_pressed"] == 0
            and (state["x"], state["y"]) == (117, 138)
        ):
            final = _snapshot(session)
            if final["submissions"] != baseline_submissions:
                raise RuntimeError(
                    "room-4 intro acknowledgement created a sentence submission: "
                    f"{baseline_submissions} -> {final['submissions']}"
                )
            return {
                "start": start,
                "segments": segments,
                "acknowledgements": acknowledgements,
                "frames": final["frame"] - start_frame,
                "final": final,
                "sentence_submissions_during_intro": (
                    final["submissions"] - baseline_submissions
                ),
                "result": "intro completed; controller seeded at authored actor position",
            }
        remaining = max_frames - (state["frame"] - start_frame)
        step = min(1 if (state["talk_active"] and
                         (state["talk_have_msg"] == 0xFF or state["talk_delay"] <= 1))
                   else 4, remaining)
        advanced = advance_bounded(session, step)
        if advanced["frames_advanced"] != step:
            raise RuntimeError(f"room-4 intro frame advancement drifted: {advanced!r}")
    raise TimeoutError(
        f"room-4 intro did not reach controller readiness in {max_frames} frames; "
        f"segments={segments!r}; acknowledgements={acknowledgements!r}; "
        f"final={_snapshot(session)!r}"
    )


def _cold_wait_room4(session: Any, max_frames: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from fate_replay import advance_bounded

    transitions: list[dict[str, Any]] = []
    last_room: int | None = None
    elapsed = 0
    while elapsed < max_frames:
        room_state = session.read_memory("snesMemory", 0x7FF2BF, 4)
        room = room_state[0]
        phase = room_state[3]
        error = session.read_u8(0x7E2303)
        lifecycle = session.read_u8(0x7E2221)
        record = session.read_u8(0x7FF2C0)
        if room != last_room:
            transitions.append({
                "frame": int(session.get_state()["frameCount"]),
                "room": room,
                "phase": phase,
                "record": record,
                "error": error,
                "lifecycle": lifecycle,
            })
            last_room = room
        if error:
            raise RuntimeError(f"SCUMM error during cold startup: {_snapshot(session)!r}")
        if lifecycle == 0xFF:
            raise RuntimeError(f"engine failed during cold startup: {_snapshot(session)!r}")
        state = _snapshot(session)
        if (
            room == 4 and phase == 0 and error == 0 and lifecycle == 2
            and state["ready"] == 1 and state["talk_active"] == 0
            and state["mode"] == 0
        ):
            return state, transitions
        advanced = advance_bounded(session, min(5, max_frames - elapsed))
        elapsed += int(advanced["frames_advanced"])
    raise TimeoutError(
        f"cold authentic startup did not reach room4 readiness within {max_frames} "
        f"frames; last={_snapshot(session)!r}"
    )


def _send_talk_owned_a_edge(
    session: Any,
    rom: Path,
    symbol_banks: dict[str, int],
    generation: int,
    *,
    purpose: str,
) -> dict[str, Any]:
    """Deliver one normal A edge while a specific talk generation is live."""
    from fate_replay import ControllerInputLease
    from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom

    before = _snapshot(session)
    if not before["talk_active"] or before["talk_generation"] != generation:
        raise RuntimeError(f"talk-edge probe precondition changed: {before!r}")
    if before["input_held"] or before["input_pressed"]:
        raise RuntimeError(
            "talk-edge probe requires an input-poll-confirmed neutral state: "
            f"{before!r}"
        )
    sequence_before = before["edge_sequence"]
    submissions_before = before["submissions"]
    points: list[dict[str, Any]] = []
    ordered_symbols = (
        "Same_Input_Poll__edge_sequence_done",
        "ScummV5_Talk_FrameBegin_Far",
        "ScummV5_Talk_FrameBegin_Far__publish",
        "ScummV5_Controller_Frame_Far",
        "ScummV5_Controller_Frame__generic_ready",
    )
    with ControllerInputLease(session) as owned_controller:
        owned_controller.hold(0x001)
        try:
            for name in ordered_symbols:
                address = mapped_cpu_address_for_rom(
                    rom, name, bank=symbol_banks[name]
                )
                point = _sync_break(session, name, address)
                points.append(point)
                if name == "Same_Input_Poll__edge_sequence_done":
                    sampled = point["state_at_break"]
                    if sampled["edge_sequence"] == sequence_before:
                        raise RuntimeError(
                            "one A hold did not produce a sampled native edge: "
                            f"before={before!r}, sampled={sampled!r}"
                        )
                    if not sampled["input_pressed"] & 0x0080:
                        raise RuntimeError(
                            f"sampled input edge was not A: {sampled!r}"
                        )
                    if not sampled["talk_active"]:
                        raise RuntimeError(
                            "A edge was not sampled while talk remained active: "
                            f"{sampled!r}"
                        )
                    if sampled["talk_generation"] != generation:
                        raise RuntimeError(
                            "talk generation changed before its A edge was sampled: "
                            f"{sampled!r}"
                        )
            points.append(_sync_controller_done(session, rom, symbol_banks))
            points.append(_sync_break(
                session,
                "ScummV5_Talk_FrameEnd_Far",
                mapped_cpu_address_for_rom(
                    rom, "ScummV5_Talk_FrameEnd_Far",
                    bank=symbol_banks["ScummV5_Talk_FrameEnd_Far"],
                ),
            ))
            points.append(_sync_break(
                session,
                "ScummV5_Talk_FrameEnd_Far__done",
                mapped_cpu_address_for_rom(
                    rom, "ScummV5_Talk_FrameEnd_Far__done",
                    bank=symbol_banks["ScummV5_Talk_FrameEnd_Far__done"],
                ),
            ))
            # Confirm the same edge cannot be replayed against the retained
            # selection after Talk_FrameEnd has stopped the timed message.
            points.append(_sync_controller_done(session, rom, symbol_banks))
        finally:
            owned_controller.release()
    neutral = _sync_break(
        session,
        "Same_Input_Poll__edge_sequence_done (neutral after talk edge)",
        mapped_cpu_address_for_rom(
            rom, "Same_Input_Poll__edge_sequence_done",
            bank=symbol_banks["Same_Input_Poll__edge_sequence_done"],
        ),
    )
    after = _snapshot(session)
    if after["submissions"] != submissions_before:
        raise RuntimeError(
            "talk-owned A edge became an extra controller sentence: "
            f"before={submissions_before}, after={after['submissions']}"
        )
    if points[5]["unexpected_sentence_submit_branch_events"]:
        raise RuntimeError(
            "the talk-owned A edge reached the controller sentence-submit branch: "
            f"{points[5]!r}"
        )
    if points[8]["unexpected_sentence_submit_branch_events"]:
        raise RuntimeError(
            "talk-owned edge reached sentence submission after talk stopped: "
            f"{points[8]!r}"
        )
    after_talk_frame = points[7]["state_at_break"]
    after_controller = points[8]["state_at_break"]
    if purpose == "active-timed-message-input-ownership-probe":
        if (after_talk_frame["talk_active"] != 0
                or after_talk_frame["talk_have_msg"] != 0
                or after_controller["talk_owned_valid"] != 0):
            raise RuntimeError(
                "timed talk completion did not consume the edge token before "
                f"controller revalidation: frame_end={after_talk_frame!r}, "
                f"controller={after_controller!r}"
            )
    if (after["input_held"] != 0 or after["input_released"] & 0x0080 == 0
            or after["edge_sequence"] != sequence_before + 1):
        raise RuntimeError(f"A release poll did not close the same edge: {after!r}")
    return {
        "purpose": purpose,
        "generation": generation,
        "before": before,
        "press_frames": 1,
        "synchronous_native_breakpoints": points,
        "neutral_release": neutral,
        "after_release": after,
        "extra_sentence_submissions": after["submissions"] - submissions_before,
        "same_edge_owned_by_talk": (
            points[0]["state_at_break"]["talk_owned_valid"] == 1
            and points[0]["state_at_break"]["talk_owned_sequence"]
                == points[0]["state_at_break"]["edge_sequence"]
        ),
        "after_release": after,
        "same_edge_owned_by_talk": (
            points[0]["state_at_break"]["talk_owned_valid"] == 1
            and points[0]["state_at_break"]["talk_owned_sequence"]
                == points[0]["state_at_break"]["edge_sequence"]
        ),
        "extra_sentence_submissions": after["submissions"] - submissions_before,
    }


def _observe_action(session: Any, *, baseline: int,
                    max_frames: int, rom: Path,
                    symbol_banks: dict[str, int],
                    exact_frame_observation: bool = False,
                    variable_base: int | None = None,
                    variable_count: int = 0,
                    ) -> dict[str, Any]:
    from fate_replay import advance_bounded, room4_message_ready

    messages: list[dict[str, Any]] = []
    acknowledgements: list[dict[str, Any]] = []
    talk_edge_probes: list[dict[str, Any]] = []
    acked_generations: set[int] = set()
    seen_generations: set[int] = set()
    last_ack_generation: int | None = None
    previous = _snapshot(session)
    action_room = previous["room"]
    baseline_activation_identity = {
        item["slot"]: (item["script"], item["program"])
        for item in previous["slots"]
    }
    watched_activation_slots: set[int] = set()
    previous_watched_signature: tuple[Any, ...] = ()
    transitions: list[dict[str, Any]] = []
    # Exact-frame mode is used for the post-Use trace. Keep a frame-boundary
    # record of live activation descriptors so a yielded local's saved PC can
    # be followed without attributing a later poll to an earlier CPU event.
    # This is explicitly a sampled frame-boundary observation, not an
    # instruction breakpoint.
    execution_samples: list[dict[str, Any]] = []
    start_frame = previous["frame"]
    stable_frames = 0
    while int(session.get_state()["frameCount"]) - start_frame < max_frames:
        state = _snapshot(session)
        for item in state["slots"]:
            original = baseline_activation_identity.get(item["slot"])
            if original != (item["script"], item["program"]):
                watched_activation_slots.add(item["slot"])
        watched_signature = tuple(
            tuple(sorted(item.items()))
            for item in state["slots"]
            if item["slot"] in watched_activation_slots
        )
        if exact_frame_observation:
            sample = {
                "frame": state["frame"],
                "room": state["room"],
                "phase": state["phase"],
                "error": state["error"],
                "mode": state["mode"],
                "verb": state["verb"],
                "object": state["object"],
                "hit_object": state["hit_object"],
                "bit69": state["bit69"],
                "actor1_room": state["actor1_room"],
                "actor1_visible": state["actor1_visible"],
                "actor1_x": state["actor1_x"],
                "actor1_y": state["actor1_y"],
                "talk_active": state["talk_active"],
                "talk_generation": state["talk_generation"],
                "talk_delay": state["talk_delay"],
                "current_slot": state["current_slot"],
                "scheduler_slot": state["scheduler_slot"],
                "active_slot_count": state["active_slot_count"],
                "program_select": state["program_select"],
                "shared_vm_pc": state["shared_vm_pc"],
                "active_record": state["active_record"],
                "pending_record": state["pending_record"],
                "pending_room": state["pending_room"],
                "sentence_pending": state["sentence_pending"],
                "c20_count": state["c20_count"],
                "submissions": state["submissions"],
                "slots": state["slots"],
            }
            active_trace_slots = [
                item for item in state["slots"]
                if item["slot"] in watched_activation_slots
                and item["script"] in {144, 145}
            ]
            if active_trace_slots:
                sample["room7_script_locals"] = _live_slot_locals(
                    session, active_trace_slots
                )
                if variable_base is not None and variable_count > 451:
                    raw = session.read_memory(
                        "snesMemory", variable_base + 451 * 2, 2
                    )
                    sample["global_V451"] = int.from_bytes(raw, "little", signed=True)
            execution_samples.append(sample)
        if state["error"] != 0:
            raise RuntimeError(f"SCUMM error after room{action_room} sentence: {state!r}")
        if state["room"] != action_room and state["phase"] == 0:
            return {
                "status": "room-transition",
                "initial_submission_count": baseline,
                "watched_activation_slots": sorted(watched_activation_slots),
                "final": state,
                "acknowledgements": acknowledgements,
                "talk_edge_probes": talk_edge_probes,
                "messages": messages,
                "lifecycle_events": transitions,
                "frame_boundary_execution_samples": execution_samples,
            }
        if any(state[key] != previous[key] for key in (
            "room", "phase", "active_record", "pending_record", "pending_room",
        )):
            transitions.append({"before": previous, "after": state})
        if state["talk_active"]:
            generation = state["talk_generation"]
            if generation not in seen_generations:
                seen_generations.add(generation)
                messages.append({
                    "generation": generation,
                    "first_observed": state,
                })
            # Timed messages advance on their own. Only an authored FF03
            # wait at zero delay owns an acknowledgement edge.
            if (generation not in acked_generations
                    and room4_message_ready(_talk_bytes(state), last_ack_generation)):
                acknowledgement = _send_talk_owned_a_edge(
                    session, rom, symbol_banks, generation,
                    purpose="explicit-message-wait",
                )
                acked_generations.add(generation)
                acknowledgements.append(acknowledgement)
                last_ack_generation = generation
                continue
        if (
            state["room"] == previous["room"]
            # Track activations created/replaced by this sentence, but ignore
            # unrelated recurring globals whose delay counters legitimately
            # change every frame.  This prevents the old false-quiescent
            # result at LSCR200's moving saved PC without waiting forever on
            # pre-existing background daemons.
            and watched_signature == previous_watched_signature
            and state["actor1_room"] == previous["actor1_room"]
            and state["actor1_visible"] == previous["actor1_visible"]
            and state["actor1_x"] == previous["actor1_x"]
            and state["actor1_y"] == previous["actor1_y"]
            and state["talk_generation"] == previous["talk_generation"]
            and state["submissions"] == previous["submissions"]
            and state["c20_count"] == previous["c20_count"]
            and state["mode"] == previous["mode"]
            and state["talk_active"] == previous["talk_active"]
        ):
            stable_frames += max(0, state["frame"] - previous["frame"])
        else:
            stable_frames = 0
        if (
            state["submissions"] == ((baseline + 1) & 0xFF)
            and state["sentence_pending"] == 0 and state["c20_count"] == 0
            and state["talk_active"] == 0 and stable_frames >= 120
            and not any(
                item["slot"] in watched_activation_slots and item["status"] == 1
                for item in state["slots"]
            )
        ):
            result = {
                "status": f"authored-action-quiescent-in-room{action_room}",
                "initial_submission_count": baseline,
                "quiescent_frames": stable_frames,
                "watched_activation_slots": sorted(watched_activation_slots),
                "final": state,
                "acknowledgements": acknowledgements,
                "talk_edge_probes": talk_edge_probes,
                "messages": messages,
                "lifecycle_events": transitions,
                "frame_boundary_execution_samples": execution_samples,
            }
            result["final_live_slot_locals"] = _live_slot_locals(
                session, state["slots"]
            )
            if action_room == 7 and variable_base is not None:
                result["runtime_context"] = _room7_runtime_context(
                    session, variable_base=variable_base,
                    variable_count=variable_count,
                )
            return result
        previous = state
        previous_watched_signature = watched_signature
        remaining = max_frames - (state["frame"] - start_frame)
        step = min(
            1 if exact_frame_observation or (
                state["talk_active"] and state["talk_delay"] <= 12
            ) else 4,
            remaining,
        )
        advanced = advance_bounded(session, step)
        if advanced["frames_advanced"] != step:
            raise RuntimeError(f"bounded action observation drifted: {advanced!r}")
    final = _snapshot(session)
    if action_room == 7:
        return {
            "status": "active-script-boundary-in-room7",
            "initial_submission_count": baseline,
            "observed_frames": final["frame"] - start_frame,
            "watched_activation_slots": sorted(watched_activation_slots),
            "final": final,
            "final_live_slot_locals": _live_slot_locals(session, final["slots"]),
            "runtime_context": (
                _room7_runtime_context(
                    session, variable_base=variable_base,
                    variable_count=variable_count,
                )
                if variable_base is not None else None
            ),
            "acknowledgements": acknowledgements,
            "talk_edge_probes": talk_edge_probes,
            "messages": messages,
            "lifecycle_events": transitions,
            "frame_boundary_execution_samples": execution_samples,
        }
    raise TimeoutError(
        f"room{action_room} action did not reach a room transition or quiescent boundary in "
        f"{max_frames} frames: {final!r}"
    )


def _observe_no_input_lifecycle(
    session: Any, *, rom: Path, symbol_banks: dict[str, int],
    archive: Path, variable_base: int, variable_count: int,
    max_frames: int = 10000, stable_frames_required: int = 120,
) -> dict[str, Any]:
    """Follow authored room-entry work until it finishes or changes rooms."""
    from fate_replay import advance_bounded, room4_message_ready

    start = _snapshot(session)
    start_frame = start["frame"]
    previous = start
    stable_frames = 0
    seen_generations: set[int] = set()
    acked_generations: set[int] = set()
    last_ack_generation: int | None = None
    messages: list[dict[str, Any]] = []
    acknowledgements: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    lifecycle_events: list[dict[str, Any]] = []
    room_sources: dict[int, dict[str, Any]] = {
        start["room"]: _authentic_room_source(archive, start["room"])
    }

    def signature(state: dict[str, Any]) -> tuple[Any, ...]:
        # Per-frame delay counters are expected to change while an authored
        # script waits. They are recorded in event snapshots, but must not
        # turn each timer tick into a distinct state or prevent a true stable
        # boundary from being recognized.
        slot_signature = tuple(
            (
                item["slot"], item["status"], item["script"], item["program"],
                item["saved_pc"], item["freeze_resistant"],
                item["freeze_count"], item["room_owner"],
            )
            for item in state["slots"]
        )
        return (
            state["room"], state["phase"], state["active_record"],
            state["pending_record"], state["pending_room"], slot_signature,
            state["actor1_room"], state["actor1_visible"],
            state["actor1_x"], state["actor1_y"], state["actor1_moving"],
            state["object61_state"],
            state["object61_owner"], state["talk_active"],
            state["talk_have_msg"], state["talk_delay"],
            state["talk_generation"], state["mode"], state["verb"],
            state["object"], state["sentence_pending"], state["c20_count"],
            state["submissions"], state["input_held"], state["input_pressed"],
            state["bit69"], state["error"], state["lifecycle"],
        )

    previous_signature = signature(start)
    for _ in range(max_frames):
        state = _snapshot(session)
        if state["error"] != 0:
            raise RuntimeError(f"SCUMM error during no-input room lifecycle: {state!r}")
        if state["input_held"] or state["input_pressed"]:
            raise RuntimeError(
                f"room-entry observer found non-neutral controller input: {state!r}"
            )
        if state["room"] != previous["room"]:
            source = _authentic_room_source(archive, state["room"])
            room_sources[state["room"]] = source
            lifecycle_events.append({
                "frame": state["frame"],
                "outgoing_room": previous["room"],
                "incoming_room": state["room"],
                "phase": state["phase"],
                "program": state["program_select"],
                "vm_pc": state["shared_vm_pc"],
                "actor1_room": state["actor1_room"],
                "actor1_position": [state["actor1_x"], state["actor1_y"]],
                "active_record": state["active_record"],
                "pending_record": state["pending_record"],
                "pending_room": state["pending_room"],
                "live_slots": state["slots"],
            })
            return {
                "status": "room-transition",
                "start": start,
                "final": state,
                "stable_frames": 0,
                "frames_observed": state["frame"] - start_frame,
                "messages": messages,
                "acknowledgements": acknowledgements,
                "lifecycle_events": lifecycle_events,
                "room_sources": room_sources,
                "state_change_samples": samples,
                "final_live_slot_locals": _live_slot_locals(
                    session, state["slots"]
                ),
                "runtime_context": (
                    _room7_runtime_context(
                        session, variable_base=variable_base,
                        variable_count=variable_count,
                    )
                    if state["room"] == 7 else None
                ),
                "sentence_submission_delta": (
                    state["submissions"] - start["submissions"]
                ) & 0xFF,
                "controller_input_sent_outside_authored_message_ack": False,
            }
        if state["talk_active"]:
            generation = state["talk_generation"]
            if generation not in seen_generations:
                seen_generations.add(generation)
                messages.append({"generation": generation, "first_observed": state})
            if (
                generation not in acked_generations
                and room4_message_ready(_talk_bytes(state), last_ack_generation)
            ):
                ack = _send_talk_owned_a_edge(
                    session, rom, symbol_banks, generation,
                    purpose="explicit-message-wait-during-authored-room-entry",
                )
                if ack["extra_sentence_submissions"] != 0:
                    raise RuntimeError(
                        "one authored talk-acknowledgement edge also submitted the "
                        f"retained controller sentence: {ack!r}"
                    )
                acknowledgements.append(ack)
                acked_generations.add(generation)
                last_ack_generation = generation
                stable_frames = 0
                previous = _snapshot(session)
                previous_signature = signature(previous)
                continue

        current_signature = signature(state)
        finite_entry_scripts = {93, 94, 209, 210, 211, 212}
        entry_sequence_complete = not any(
            item["script"] in finite_entry_scripts for item in state["slots"]
        )
        if (
            state["phase"] == 0 and state["talk_active"] == 0
            and entry_sequence_complete
            and state["pending_room"] == state["room"]
            and state["actor1_moving"] == 0
            and current_signature == previous_signature
        ):
            stable_frames += max(0, state["frame"] - previous["frame"])
        else:
            stable_frames = 0
        if stable_frames >= stable_frames_required:
            return {
                "status": "authored-room-entry-complete",
                "start": start,
                "final": state,
                "stable_frames": stable_frames,
                "frames_observed": state["frame"] - start_frame,
                "messages": messages,
                "acknowledgements": acknowledgements,
                "lifecycle_events": lifecycle_events,
                "room_sources": room_sources,
                "state_change_samples": samples,
                "final_live_slot_locals": _live_slot_locals(
                    session, state["slots"]
                ),
                "runtime_context": (
                    _room7_runtime_context(
                        session, variable_base=variable_base,
                        variable_count=variable_count,
                    )
                    if state["room"] == 7 else None
                ),
                "sentence_submission_delta": (
                    state["submissions"] - start["submissions"]
                ) & 0xFF,
                "controller_input_sent_outside_authored_message_ack": False,
            }
        if current_signature != previous_signature:
            samples.append(state)
        previous = state
        previous_signature = current_signature
        result = advance_bounded(session, 1)
        if result["frames_advanced"] != 1:
            raise RuntimeError(f"room-entry observation frame drifted: {result!r}")

    return {
        "status": "bounded-observation-limit",
        "start": start,
        "final": _snapshot(session),
        "stable_frames": stable_frames,
        "frames_observed": int(session.get_state()["frameCount"]) - start_frame,
        "messages": messages,
        "acknowledgements": acknowledgements,
        "lifecycle_events": lifecycle_events,
        "room_sources": room_sources,
        "state_change_samples": samples,
        "final_live_slot_locals": _live_slot_locals(
            session, _snapshot(session)["slots"]
        ),
        "runtime_context": (
            _room7_runtime_context(
                session, variable_base=variable_base,
                variable_count=variable_count,
            )
            if _snapshot(session)["room"] == 7 else None
        ),
        "sentence_submission_delta": (
            int(session.read_u8(0x7E5FE9)) - start["submissions"]
        ) & 0xFF,
        "controller_input_sent_outside_authored_message_ack": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44979)
    parser.add_argument("--nexen-boot-wait", type=float, default=10.0)
    parser.add_argument("--socket-timeout", type=float, default=300.0)
    parser.add_argument("--startup-frames", type=int, default=1600)
    parser.add_argument("--action-frames", type=int, default=2400)
    parser.add_argument("--continue-trapdoor-use", action="store_true")
    parser.add_argument("--continue-room5-rope", action="store_true")
    parser.add_argument("--continue-room6-books", action="store_true")
    parser.add_argument("--continue-room7-book", action="store_true")
    parser.add_argument("--room5-action-frames", type=int, default=9000)
    parser.add_argument("--room6-action-frames", type=int, default=12000)
    parser.add_argument("--room7-action-frames", type=int, default=12000)
    parser.add_argument("--room7-save-state", type=Path)
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/ATLANTIS.zip"))
    args = parser.parse_args()
    if args.continue_room5_rope and not args.continue_trapdoor_use:
        parser.error("--continue-room5-rope requires --continue-trapdoor-use")
    if args.continue_room6_books and not args.continue_room5_rope:
        parser.error("--continue-room6-books requires --continue-room5-rope")
    if args.continue_room7_book and not args.continue_room6_books:
        parser.error("--continue-room7-book requires --continue-room6-books")

    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    if not rom.is_file() or not nexen.is_file():
        parser.error("ROM and Nexen must exist")
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    rom_sha = hashlib.sha256(rom.read_bytes()).hexdigest()
    if rom_sha != recipe["rom"]["sha256"]:
        parser.error(f"ROM SHA mismatch: {rom_sha} != {recipe['rom']['sha256']}")

    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, "/home/chad/Mesen2/python")
    from fate_replay import (
        advance_bounded,
        finish_room4_authored_cutscene,
        replay_room4_open_trapdoor_prefix,
        replay_room4_trapdoor_use,
        replay_room6_books_interaction,
        replay_room7_lost_dialogue_interaction,
        replay_room5_rope_to_room6,
        room4_synchronous_input_edge,
        skip_room4_authored_override,
    )
    from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom, verified_symbol_map_for_rom
    import mesen_mcp.session as mesen_session

    map_path, _symbols = verified_symbol_map_for_rom(rom)
    listing_path = rom.with_suffix(".lst")
    variable_layout = _parse_rom_variable_layout(
        listing_path.read_text(encoding="utf-8")
    )
    identity_path = rom.with_suffix(".build_identity.json")
    map_sha = hashlib.sha256(map_path.read_bytes()).hexdigest()
    identity_sha = hashlib.sha256(identity_path.read_bytes()).hexdigest()
    nexen_sha = hashlib.sha256(nexen.read_bytes()).hexdigest()
    if map_sha != recipe["rom"]["map_sha256"]:
        parser.error(f"map SHA mismatch: {map_sha}")
    if identity_sha != recipe["rom"]["build_identity_sha256"]:
        parser.error(f"build identity SHA mismatch: {identity_sha}")
    if nexen_sha != recipe["rom"]["nexen_sha256"]:
        parser.error(f"Nexen SHA mismatch: {nexen_sha}")

    symbols = {
        "Same_Input_Poll__edge_sequence_done": 0,
        "ScummV5_Talk_FrameBegin_Far": 9,
        "ScummV5_Talk_FrameBegin_Far__publish": 9,
        "ScummV5_Controller_Frame_Far": 9,
        "ScummV5_Controller_Frame__generic_ready": 9,
        "ScummV5_Controller_Frame__select_verb_a_pressed": 9,
        "ScummV5_Controller_Frame__done": 9,
        "ScummV5_Talk_FrameEnd_Far": 9,
        "ScummV5_Talk_FrameEnd_Far__done": 9,
    }
    report: dict[str, Any] = {
        "result": "running",
        "evidence_class": "fresh-power-on Nexen cold startup plus normal controller input",
        "rom": str(rom),
        "rom_sha256": rom_sha,
        "map": str(map_path),
        "map_sha256": map_sha,
        "build_identity": str(identity_path),
        "build_identity_sha256": identity_sha,
        "nexen": str(nexen),
        "nexen_sha256": nexen_sha,
        "nexen_boot_wait_seconds": args.nexen_boot_wait,
        "nexen_socket_timeout_seconds": args.socket_timeout,
        "starting_head": "2f8066c28f2f726c6cc1701e73ca3a8de8b9c45c",
        "hook_addresses": {},
    }
    for name, bank in symbols.items():
        report["hook_addresses"][name] = f"${mapped_cpu_address_for_rom(rom, name, bank=bank):06X}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mesen_session.validate_mesen_build = lambda _path: None

    owned_session = mesen_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port,
            boot_wait=args.nexen_boot_wait, socket_timeout=args.socket_timeout,
            stderr_log=args.output.with_suffix(".nexen-stderr.log"),
        )
    try:
        with owned_session as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            advance_bounded(session, 2)
            ready, transitions = _cold_wait_room4(session, args.startup_frames)
            report["room_transitions"] = transitions
            report["room4_ready"] = ready
            report["authentic_room4_entry"] = {
                "program": "$ED",
                "identity": "room4 ENCD",
                "body_sha256": "b787c221b19beaf99632c0748aab0fb80a85e79bac3b8a557e440e69d2c3d67b",
                "source_archive_sha256": "0f3fc396642c800069d31ab9a087b314f1bb1612d37accbe13b6013219ac94f0",
            }
            report["room4_cutscene_skip"] = skip_room4_authored_override(
                session,
                defer_release_sample=True,
            )
            try:
                report["room4_cutscene_completion"] = finish_room4_authored_cutscene(session)
            except Exception as exc:
                report["room4_cutscene_completion"] = {
                    "result": "bounded-authored-cutscene-boundary",
                    "error": f"{type(exc).__name__}: {exc}",
                }
                raise
            report["room4_intro"] = _finish_room4_intro(
                session, max_frames=2400, rom=rom, symbol_banks=symbols
            )
            def exact_edge_pulse(
                pulse_session: Any,
                mask: int,
                predicate: Any,
            ) -> dict[str, Any]:
                return room4_synchronous_input_edge(
                    pulse_session, mask, predicate
                )

            replay = replay_room4_open_trapdoor_prefix(
                session, pulse=exact_edge_pulse
            )
            report["room4_replay"] = replay
            baseline = report["room4_intro"]["final"]["submissions"]
            if replay["final"]["submissions"] != ((baseline + 1) & 0xFF):
                raise RuntimeError(
                    "room-4 action did not create exactly one sentence submission: "
                    f"{baseline} -> {replay['final']['submissions']}"
                )

            report["post_action"] = _observe_action(
                session, baseline=baseline,
                max_frames=args.action_frames, rom=rom,
                symbol_banks=symbols,
            )
            if args.continue_trapdoor_use:
                if report["post_action"]["status"] != "authored-action-quiescent-in-room4":
                    raise RuntimeError(
                        "cannot follow object61 Use: prior Open action did not reach "
                        f"the authored quiescent precondition: {report['post_action']!r}"
                    )
                report["object61_use_source"] = _authentic_room4_object61_use_source(
                    args.archive.resolve()
                )

                def exact_use_edge(
                    pulse_session: Any,
                    mask: int,
                    predicate: Any,
                ) -> dict[str, Any]:
                    return room4_synchronous_input_edge(
                        pulse_session, mask, predicate
                    )

                report["room4_use_action"] = replay_room4_trapdoor_use(
                    session, pulse=exact_use_edge
                )
                use_baseline = report["room4_use_action"]["submission_count_before"]
                report["post_use"] = _observe_action(
                    session, baseline=use_baseline,
                    max_frames=args.action_frames, rom=rom,
                    symbol_banks=symbols, exact_frame_observation=True,
                )
                if report["post_use"]["status"] == "room-transition":
                    report["post_transition_idle"] = _observe_no_input_lifecycle(
                        session, rom=rom, symbol_banks=symbols,
                        archive=args.archive.resolve(),
                        variable_base=variable_layout["base"],
                        variable_count=variable_layout["count"],
                    )
                if args.continue_room5_rope:
                    idle = report.get("post_transition_idle", {})
                    if idle.get("status") != "authored-room-entry-complete":
                        raise RuntimeError(
                            "cannot follow room5 rope before authentic room5 entry "
                            f"completes: {idle!r}"
                        )
                    if idle["final"]["room"] != 5:
                        raise RuntimeError(
                            "expected room5 after the room4 action, got "
                            f"{idle['final']!r}"
                        )
                    report["room5_rope_source"] = _authentic_room5_rope_source(
                        args.archive.resolve()
                    )
                    report["room5_rope_action"] = replay_room5_rope_to_room6(
                        session, pulse=exact_edge_pulse
                    )
                    room5_baseline = report["room5_rope_action"][
                        "submission_count_before"
                    ]
                    if report["room5_rope_action"]["submission_count_after"] != (
                        (room5_baseline + 1) & 0xFF
                    ):
                        raise RuntimeError(
                            "room5 rope sentence did not submit exactly once: "
                            f"{report['room5_rope_action']!r}"
                        )
                    report["post_room5_rope"] = _observe_action(
                        session, baseline=room5_baseline,
                        max_frames=args.room5_action_frames, rom=rom,
                        symbol_banks=symbols, exact_frame_observation=True,
                    )
                    if report["post_room5_rope"]["status"] == "room-transition":
                        report["room6_entry"] = _observe_no_input_lifecycle(
                            session, rom=rom, symbol_banks=symbols,
                            archive=args.archive.resolve(),
                            variable_base=variable_layout["base"],
                            variable_count=variable_layout["count"],
                        )
                if args.continue_room6_books:
                    entry = report.get("room6_entry", {})
                    if entry.get("status") != "authored-room-entry-complete":
                        raise RuntimeError(
                            "cannot follow room6 books before authentic room6 entry "
                            f"completes: {entry!r}"
                        )
                    if entry["final"]["room"] != 6:
                        raise RuntimeError(
                            "expected room6 before the books interaction, got "
                            f"{entry['final']!r}"
                        )
                    report["room6_books_source"] = _authentic_room6_books_source(
                        args.archive.resolve()
                    )
                    report["room6_books_action"] = replay_room6_books_interaction(
                        session, pulse=exact_edge_pulse
                    )
                    books_baseline = report["room6_books_action"][
                        "submission_count_before"
                    ]
                    if report["room6_books_action"]["submission_count_after"] != (
                        (books_baseline + 1) & 0xFF
                    ):
                        raise RuntimeError(
                            "room6 books sentence did not submit exactly once: "
                            f"{report['room6_books_action']!r}"
                        )
                    report["post_room6_books"] = _observe_action(
                        session, baseline=books_baseline,
                        max_frames=args.room6_action_frames, rom=rom,
                        symbol_banks=symbols, exact_frame_observation=True,
                    )
                    dispatches = [
                        {"frame": sample["frame"], "room": sample["room"],
                         "slot": slot["slot"], "script": slot["script"],
                         "program": slot["program"], "saved_pc": slot["saved_pc"],
                         "room_owner": slot["room_owner"]}
                        for sample in report["post_room6_books"].get(
                            "frame_boundary_execution_samples", []
                        )
                        for slot in sample["slots"]
                        if slot["script"] == 200
                    ]
                    report["room6_lscr200_observations"] = dispatches[:8]
                    if not dispatches:
                        raise RuntimeError(
                            "room6 object91 verb10 did not create an observable "
                            "LSCR200 activation"
                        )
                    observed_rooms = sorted({item["room"] for item in dispatches})
                    room_local_tables = {
                        room: _room_local_program_table(room, identity_path)
                        for room in observed_rooms
                    }
                    report["room_local_program_tables"] = {
                        str(room): room_local_tables[room]
                        for room in observed_rooms
                    }
                    report["room_local_script200_observations"] = {
                        str(room): [item for item in dispatches if item["room"] == room][:8]
                        for room in observed_rooms
                    }
                    wrong_mappings = [
                        item for item in dispatches
                        if item["script"] not in room_local_tables[item["room"]][
                            "script_to_program"
                        ] or item["program"] != room_local_tables[item["room"]][
                            "script_to_program"
                        ][item["script"]]
                    ]
                    if not any(
                        item["room"] == 6 and item["program"] == 0x93
                        for item in dispatches
                    ):
                        raise RuntimeError(
                            "room6 LSCR200 did not execute under the ROM-mapped "
                            f"selector $93: {dispatches[:8]!r}"
                        )
                    if wrong_mappings:
                        raise RuntimeError(
                            "observed room-local activation disagrees with the "
                            f"ROM-bound per-room selector table: {wrong_mappings[:8]!r}"
                        )
                    if report["post_room6_books"]["status"] == "room-transition":
                        report["room7_source"] = _authentic_room_source(
                            args.archive.resolve(), 7
                        )
                        room7_scripts = {
                            item["script"] for item in dispatches if item["room"] == 7
                        }
                        if room7_scripts and 200 not in room7_scripts:
                            raise RuntimeError(
                                "room7 transition lacks the observed authentic entry "
                                f"LSCR200 activation: {dispatches[:8]!r}"
                            )
                        report["room7_entry"] = _observe_no_input_lifecycle(
                            session, rom=rom, symbol_banks=symbols,
                            archive=args.archive.resolve(),
                            variable_base=variable_layout["base"],
                            variable_count=variable_layout["count"],
                        )
                        if report["room7_entry"]["status"] != (
                            "authored-room-entry-complete"
                        ):
                            raise RuntimeError(
                                "room7 authored entry did not reach its bounded "
                                "stable completion: "
                                f"{report['room7_entry'].get('status')!r}, "
                                f"final={report['room7_entry'].get('final')!r}"
                            )
                        if args.room7_save_state is not None:
                            session.pause()
                            room7_state_path = args.room7_save_state.resolve()
                            room7_state_path.parent.mkdir(parents=True, exist_ok=True)
                            report["room7_same_rom_state_assist"] = {
                                "path": str(room7_state_path),
                                "rom_sha256": rom_sha,
                                "save_result": session.save_state(room7_state_path),
                                "purpose": (
                                    "targeted same-ROM diagnostics only; "
                                    "not cold-start acceptance"
                                ),
                            }
                        if args.continue_room7_book:
                            report["room7_book_source"] = _authentic_room7_book_source(
                                args.archive.resolve(), identity_path,
                            )
                            report["room7_book_action"] = (
                                replay_room7_lost_dialogue_interaction(
                                    session,
                                    variable_base=variable_layout["base"],
                                    variable_count=variable_layout["count"],
                                    pulse=exact_edge_pulse,
                                )
                            )
                            room7_baseline = report["room7_book_action"][
                                "submission_count_before"
                            ]
                            if report["room7_book_action"][
                                "submission_count_after"
                            ] != ((room7_baseline + 1) & 0xFF):
                                raise RuntimeError(
                                    "room7 book sentence did not submit exactly once: "
                                    f"{report['room7_book_action']!r}"
                                )
                            report["post_room7_book"] = _observe_action(
                                session,
                                baseline=room7_baseline,
                                max_frames=args.room7_action_frames,
                                rom=rom,
                                symbol_banks=symbols,
                                exact_frame_observation=True,
                                variable_base=variable_layout["base"],
                                variable_count=variable_layout["count"],
                            )
                            report["room7_global144_observations"] = [
                                {
                                    "frame": sample["frame"],
                                    "room": sample["room"],
                                    "slot": slot["slot"],
                                    "script": slot["script"],
                                    "program": slot["program"],
                                    "saved_pc": slot["saved_pc"],
                                }
                                for sample in report["post_room7_book"].get(
                                    "frame_boundary_execution_samples", []
                                )
                                for slot in sample["slots"]
                                if slot["script"] == 144
                            ]
                            if report["post_room7_book"]["status"] == "room-transition":
                                resulting_room = report["post_room7_book"][
                                    "final"
                                ]["room"]
                                report["resulting_room_source"] = _authentic_room_source(
                                    args.archive.resolve(), resulting_room,
                                )
                                report["resulting_room_entry"] = (
                                    _observe_no_input_lifecycle(
                                        session,
                                        rom=rom,
                                        symbol_banks=symbols,
                                        archive=args.archive.resolve(),
                                        variable_base=variable_layout["base"],
                                        variable_count=variable_layout["count"],
                                    )
                                )
                            else:
                                report["post_room7_context"] = (
                                    _room7_runtime_context(
                                        session,
                                        variable_base=variable_layout["base"],
                                        variable_count=variable_layout["count"],
                                    )
                                    if report["post_room7_book"]["final"]["room"] == 7
                                    else None
                                )
            report["final_snapshot"] = _snapshot(session)
            report["result"] = "pass"
    except Exception as exc:
        # McpSession.__enter__ can fail after Popen succeeds, before Python's
        # with-statement owns cleanup. Reap only the process this runner started.
        process = getattr(owned_session, "_proc", None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
                process.wait(timeout=5)
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        raise
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"FATE room4 cold replay: {report['result']} ({rom_sha})")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
