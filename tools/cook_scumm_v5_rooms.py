#!/usr/bin/env python3
"""Cook complete, source-bound SCUMM v5 ROOM records for a profile build."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

from same.engines.scumm_v5.cooked_room import (
    FLAG_REGISTRATION_ONLY, HEADER, SCRIPT, ScriptChunkInput, decode_cooked_room,
    encode_cooked_room,
)
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room import decode_room
from same.engines.scumm_v5.room_visual import encode_room_visual, decode_room_visual
from same.profile import load_profile
from same.resources import MemoryResourceProvider


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
DEFAULT_ARCHIVE = Path("/home/chad/fatedemo-box.zip")
MEMBERS = {
    "game.index": "FATEDEMO/PLAYFATE.000",
    "game.data": "FATEDEMO/PLAYFATE.001",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_members(bundle: zipfile.ZipFile) -> dict[str, str]:
    """Locate the standard SCUMM pair in demo or full-game archives."""
    names = bundle.namelist()
    result = {}
    for key, basename in (("game.index", ".000"), ("game.data", ".001")):
        matches = [name for name in names if name.upper().endswith(basename)]
        if len(matches) != 1:
            raise RuntimeError(f"archive must contain one SCUMM {basename} member")
        result[key] = matches[0]
    return result


def chunks(data: bytes) -> list[tuple[str, int, int, bytes]]:
    result = []
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise RuntimeError(f"chunk header at {offset} is truncated")
        tag = data[offset:offset + 4].decode("ascii")
        size = struct.unpack_from(">I", data, offset + 4)[0]
        if size < 8 or offset + size > len(data):
            raise RuntimeError(f"chunk {tag} at {offset} has invalid size {size}")
        result.append((tag, offset, size, data[offset + 8:offset + size]))
        offset += size
    return result


def game_identity(profile) -> str:
    return sha(f"{profile.engine_id}\0{profile.game_id}\0{profile.variant}".encode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--rooms", type=int, nargs="+", default=(49, 63))
    parser.add_argument("--global-scripts", type=int, nargs="*", default=())
    parser.add_argument(
        "--global-script-set",
        help="profile-owned key from options.snes_global_script_sets",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--executable", action="store_true",
                        help="allow entry dispatch (authentic M23A records omit this)")
    parser.add_argument(
        "--visuals", type=int, nargs="*", default=None,
        help="emit complete decoded INDEX8/RGB8 visual records (all selected rooms if empty)",
    )
    args = parser.parse_args()

    archive_bytes = args.archive.read_bytes()
    with zipfile.ZipFile(args.archive) as bundle:
        members = source_members(bundle)
        raw = {key: bundle.read(member) for key, member in members.items()}
    profile = load_profile(args.profile, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None:
        raise RuntimeError("profile has no SCUMM v5 resource policy")
    selected_global_scripts = tuple(args.global_scripts)
    execution_gate = None
    if args.global_script_set:
        if selected_global_scripts:
            raise RuntimeError("--global-script-set and --global-scripts are exclusive")
        sets = profile.options.get("snes_global_script_sets", {})
        if not isinstance(sets, dict) or args.global_script_set not in sets:
            raise RuntimeError(
                f"profile has no SNES global-script set {args.global_script_set!r}"
            )
        values = sets[args.global_script_set]
        if (
            not isinstance(values, list)
            or any(isinstance(value, bool) or not isinstance(value, int) for value in values)
            or len(set(values)) != len(values)
        ):
            raise RuntimeError("profile SNES global-script set must be unique integers")
        selected_global_scripts = tuple(values)
        gates = profile.options.get("snes_execution_gates", {})
        if not isinstance(gates, dict):
            raise RuntimeError("profile SNES execution gates must be an object")
        execution_gate = gates.get(args.global_script_set)
        if execution_gate is not None and (
            not isinstance(execution_gate, dict)
            or isinstance(execution_gate.get("hold_after_started_global_script"), bool)
            or not isinstance(execution_gate.get("hold_after_started_global_script"), int)
        ):
            raise RuntimeError("profile SNES execution gate is malformed")
    provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw), policy)
    profile_hash = sha(args.profile.read_bytes())
    game_hash = game_identity(profile)
    archive_hash = sha(archive_bytes)
    index_hash = sha(raw["game.index"])
    data_hash = sha(raw["game.data"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    global_states_output = args.output_dir / "global-object-states.bin"
    global_states_output.write_bytes(provider.global_objects.states)
    global_owners_output = args.output_dir / "global-object-owners.bin"
    global_owners_output.write_bytes(provider.global_objects.owners)
    records = []
    for room_number in args.rooms:
        key = f"room.{room_number}"
        room_payload = provider.read(key)
        decoded_room = decode_room(room_payload, key=key)
        lflf = provider._rooms[room_number]  # exact offset retained by raw provider
        room_child = next(item for item in chunks(lflf.payload) if item[0] == "ROOM")
        original_room_file_offset = lflf.offset + 8 + room_child[1] + 8
        script_inputs: list[ScriptChunkInput] = []
        chunk_manifest = []
        for tag, offset, size, payload in chunks(room_payload):
            if tag not in {"ENCD", "EXCD", "LSCR"}:
                continue
            if tag == "LSCR":
                if not payload:
                    raise RuntimeError(f"{key} LSCR at {offset} has no script number")
                number = payload[0]
                body_chunk_offset = 9
                body_length = len(payload) - 1
                identity = f"{key}/LSCR.{number}"
                if number < provider.global_script_count:
                    raise RuntimeError(
                        f"{key} LSCR {number} is below global-script boundary "
                        f"{provider.global_script_count}"
                    )
            else:
                number = 10002 if tag == "ENCD" else 10001
                body_chunk_offset = 8
                body_length = len(payload)
                identity = f"{key}/{tag}"
            script_inputs.append(ScriptChunkInput(
                tag, number, identity, offset, body_chunk_offset, body_length,
            ))
            body_room_offset = offset + body_chunk_offset
            body = room_payload[body_room_offset:body_room_offset + body_length]
            chunk_manifest.append({
                "kind": tag,
                "number": number,
                "identity": identity,
                "chunk_length": size,
                "program_length": body_length,
                "sha256": sha(body),
                "original_file_offset": original_room_file_offset + body_room_offset,
                "original_room_offset": body_room_offset,
                "original_chunk_offset": body_chunk_offset,
                "normalized_script_offset": 0,
                **({"local_script_index": number - provider.global_script_count}
                   if tag == "LSCR" else {}),
            })
        cooked = encode_cooked_room(
            room_payload,
            room=room_number,
            flags=0 if args.executable else FLAG_REGISTRATION_ONLY,
            original_room_file_offset=original_room_file_offset,
            profile_sha256=profile_hash,
            game_identity_sha256=game_hash,
            archive_sha256=archive_hash,
            index_sha256=index_hash,
            data_sha256=data_hash,
            scripts=tuple(script_inputs),
        )
        decoded = decode_cooked_room(
            cooked, expected_room=room_number,
            expected_profile_sha256=profile_hash,
            expected_game_identity_sha256=game_hash,
            expected_archive_sha256=archive_hash,
            expected_index_sha256=index_hash,
            expected_data_sha256=data_hash,
        )
        output = args.output_dir / f"room-{room_number}.sc5c"
        output.write_bytes(cooked)
        visual_manifest = None
        visual_rooms = set(args.rooms if args.visuals == [] else (args.visuals or ()))
        if room_number in visual_rooms:
            palette = b"".join(bytes(color) for color in decoded_room.palette)
            visual = encode_room_visual(
                room=room_number, width=decoded_room.width, height=decoded_room.height,
                pitch=decoded_room.width, palette=palette, pixels=decoded_room.pixels,
                archive_sha256=archive_hash, index_sha256=index_hash,
                data_sha256=data_hash, room_sha256=sha(room_payload),
            )
            decoded_visual = decode_room_visual(visual, expected_room=room_number)
            visual_output = args.output_dir / f"room-{room_number}.sc5v"
            visual_output.write_bytes(visual)
            visual_manifest = {
                "schema": "same_scumm_v5_room_visual_v1",
                "output": visual_output.name,
                "record_length": len(visual),
                "record_sha256": sha(visual),
                "pixel_format": "indexed8", "palette_format": "rgb8",
                "width": decoded_visual.width, "height": decoded_visual.height,
                "pitch": decoded_visual.pitch, "palette_entries": 256,
                "decoded_pixels_sha256": decoded_visual.decoded_pixels_sha256,
                "decoded_palette_sha256": decoded_visual.decoded_palette_sha256,
            }
        cooked_offsets = {item.identity: item.cooked_record_offset for item in decoded.scripts}
        for item in chunk_manifest:
            item["cooked_record_offset"] = cooked_offsets[item["identity"]]
        cooked_room_offset = HEADER.size + len(script_inputs) * SCRIPT.size
        object_manifest = []
        for local_index, item in enumerate(decoded_room.objects, 1):
            object_manifest.append({
                "object_id": item.object_id,
                "local_object_index": local_index,
                "obcd_original_file_offset": original_room_file_offset + item.obcd_room_offset,
                "obcd_room_offset": item.obcd_room_offset,
                "obcd_length": len(item.obcd),
                "obcd_sha256": sha(item.obcd),
                "cdhd_offset": 8,
                "verb_table_offset": item.verb_table_offset,
                "verb_table_length": item.verb_table_length,
                "verb_entries": [
                    {"verb": verb, "entry_offset": entry}
                    for verb, entry in item.verb_entries
                ],
                "cooked_record_offset": cooked_room_offset + item.obcd_room_offset,
            })
        record_manifest = {
            "room": room_number,
            "resource_key": key,
            "output": output.name,
            "registration_only": decoded.registration_only,
            "original_room_file_offset": original_room_file_offset,
            "original_room_length": len(room_payload),
            "original_room_sha256": sha(room_payload),
            "record_length": len(cooked),
            "record_sha256": sha(cooked),
            "compact_checksum": decoded.compact_checksum,
            "scripts": chunk_manifest,
            "objects": object_manifest,
        }
        if visual_manifest is not None:
            record_manifest["visual"] = visual_manifest
        records.append(record_manifest)
    global_scripts = []
    for number in selected_global_scripts:
        key = policy.script_key_template.format(script=number)
        program = provider.read(key)
        directory = provider._directories["DSCR"]
        source_room = directory.rooms[number]
        directory_offset = directory.offsets[number]
        lflf = provider._rooms[source_room]
        chunk_header_offset = lflf.offset + 8 + directory_offset
        payload_offset = chunk_header_offset + 8
        output = args.output_dir / f"script-{number}.scrp"
        output.write_bytes(program)
        global_scripts.append({
            "number": number,
            "resource_key": key,
            "output": output.name,
            "length": len(program),
            "sha256": sha(program),
            "namespace": "WIO_GLOBAL",
            "directory_tag": "DSCR",
            "directory_room": source_room,
            "directory_offset": directory_offset,
            "source_member": MEMBERS["game.data"],
            "encrypted_chunk_offset": chunk_header_offset,
            "decoded_chunk_offset": chunk_header_offset,
            "decoded_payload_offset": payload_offset,
            "chunk_length": len(program) + 8,
        })
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "num_global_scripts": provider.global_script_count,
        "profile": {
            "path": str(args.profile.resolve()), "sha256": profile_hash,
            "engine": profile.engine_id, "game": profile.game_id,
            "variant": profile.variant, "identity_sha256": game_hash,
        },
        "source": {
            "archive": str(args.archive.resolve()), "archive_sha256": archive_hash,
            "index_member": members["game.index"], "index_sha256": index_hash,
            "data_member": members["game.data"], "data_sha256": data_hash,
        },
        "global_objects": {
            "count": len(provider.global_objects.states),
            "states_output": global_states_output.name,
            "states_sha256": sha(provider.global_objects.states),
            "owners_output": global_owners_output.name,
            "owners_sha256": sha(provider.global_objects.owners),
        },
        "records": records,
        "global_scripts": global_scripts,
        **({"execution_gate": execution_gate} if execution_gate is not None else {}),
    }
    manifest_path = args.manifest or args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "manifest": str(manifest_path), "manifest_sha256": sha(manifest_path.read_bytes()),
        "records": [{"room": item["room"], "sha256": item["record_sha256"]}
                    for item in records],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
