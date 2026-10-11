#!/usr/bin/env python3
"""Cook complete, source-bound SCUMM v5 ROOM records for a profile build."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room import decode_room, iter_scumm_chunks
from same.engines.scumm_v5.room_compiler import (
    compile_room_payload, decode_script, profile_game_identity, source_member_pair,
)
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
    return source_member_pair(bundle.namelist())


def chunks(data: bytes) -> list[tuple[str, int, int, bytes]]:
    return [
        (item.tag, item.offset, item.size, item.payload)
        for item in iter_scumm_chunks(data, owner="SCUMM room cooker")
    ]


def game_identity(profile) -> str:
    return profile_game_identity(profile)


def prepend_fixture_global_script(
    original: bytes, target_script: int, prefix_script: int
) -> tuple[bytes, dict[str, object]]:
    """Build an explicitly synthetic prefix wrapper without losing its source.

    The wrapper remains useful for controlled mid-game fixtures, but its
    executable bytes must never be labelled as an unchanged authored global.
    Keep the original body separately and bind both byte streams by hash.
    """
    prefix = bytes((0x0A, prefix_script & 0xFF, 0xFF))
    transformed = prefix + original
    return transformed, {
        "kind": "synthetic-fixture-wrapper",
        "target_script": target_script,
        "operation": f"prepend startScript({prefix_script})",
        "prefix_bytes": prefix.hex(),
        "original_length": len(original),
        "original_sha256": sha(original),
        "transformed_length": len(transformed),
        "transformed_sha256": sha(transformed),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--rooms", type=int, nargs="+", default=(49, 63))
    parser.add_argument("--global-scripts", type=int, nargs="*", default=())
    parser.add_argument(
        "--all-source-executables", action="store_true",
        help="cook every indexed room and every available global executable",
    )
    parser.add_argument(
        "--global-script-set",
        help="profile-owned key from options.snes_global_script_sets",
    )
    parser.add_argument(
        "--prepend-global-script", type=int, nargs=2, metavar=("TARGET", "SCRIPT"),
        help="prepend authored startScript(SCRIPT) to global TARGET",
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
    provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw), policy)
    selected_global_scripts = tuple(args.global_scripts)
    selected_rooms = tuple(args.rooms)
    if args.all_source_executables:
        if args.global_scripts or args.global_script_set or args.prepend_global_script:
            parser.error("--all-source-executables cannot be combined with selected globals or wrappers")
        catalog = provider.source_catalog()
        selected_rooms = tuple(sorted(
            int(row["number"]) for row in catalog if row["category"] == "room"
        ))
        selected_global_scripts = tuple(sorted(
            int(row["number"]) for row in catalog
            if row["category"] == "global-script" and row["status"] == "INVENTORIED"
        ))
    if args.prepend_global_script is not None and len(args.prepend_global_script) != 2:
        raise RuntimeError("--prepend-global-script requires TARGET and SCRIPT")
    prepend_target, prepend_script = args.prepend_global_script or (None, None)
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
    for room_number in selected_rooms:
        key = f"room.{room_number}"
        room_payload = provider.read(key)
        decoded_room = decode_room(room_payload, key=key)
        source_location = provider.source_location(key)
        original_room_file_offset = int(source_location["payload_offset"])
        compilation = compile_room_payload(
            room_payload, room_number=room_number,
            game_name=f"{profile.game_id}:{profile.variant}", resource_key=key,
            source_member=members["game.data"],
            source_container_offset=int(source_location["container_offset"]),
            original_room_file_offset=original_room_file_offset,
            profile_sha256=profile_hash, game_identity_sha256=game_hash,
            archive_sha256=archive_hash, index_sha256=index_hash, data_sha256=data_hash,
            global_script_count=provider.global_script_count,
            global_object_states=provider.global_objects.states,
            global_object_owners=provider.global_objects.owners,
            global_object_classes=provider.global_objects.classes,
            executable=args.executable,
        )
        output = args.output_dir / f"room-{room_number}.sc5c"
        output.write_bytes(compilation.cooked_record)
        visual_manifest = None
        visual_rooms = set(selected_rooms if args.visuals == [] else (args.visuals or ()))
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
        record_manifest = dict(compilation.record_manifest)
        record_manifest["output"] = output.name
        if visual_manifest is not None:
            record_manifest["visual"] = visual_manifest
        records.append(record_manifest)
    global_scripts = []
    global_transformations = []
    for number in selected_global_scripts:
        key = policy.script_key_template.format(script=number)
        original_program = provider.read(key)
        program = original_program
        transformation = None
        if number == prepend_target:
            if prepend_script is None:
                raise RuntimeError("global-script prepend is incomplete")
            program, transformation = prepend_fixture_global_script(
                original_program, number, prepend_script
            )
        source_location = provider.source_location(key)
        source_room = int(source_location["source_room"])
        directory_offset = int(source_location["chunk_offset"]) - int(source_location["container_offset"]) - 8
        chunk_header_offset = int(source_location["chunk_offset"])
        payload_offset = chunk_header_offset + 8
        output = args.output_dir / f"script-{number}.scrp"
        output.write_bytes(program)
        script_manifest = {
            "number": number,
            "resource_key": key,
            "output": output.name,
            "length": len(program),
            "sha256": sha(program),
            "source_length": len(original_program),
            "source_sha256": sha(original_program),
            "namespace": "WIO_GLOBAL",
            "directory_tag": "DSCR",
            "directory_room": source_room,
            "directory_offset": directory_offset,
            "source_member": MEMBERS["game.data"],
            "encrypted_chunk_offset": chunk_header_offset,
            "decoded_chunk_offset": chunk_header_offset,
            "decoded_payload_offset": payload_offset,
            "chunk_length": len(program) + 8,
        }
        global_ir = decode_script(
            program, identity=f"{key}/SCRP.{number}", kind="SCRP", number=number,
            room=source_room, resource_key=key,
            game_name=f"{profile.game_id}:{profile.variant}",
            source_member=members["game.data"],
            resource_offset=int(source_location["container_offset"]),
            source_offset=payload_offset, source_body_sha256=sha(program),
        )
        script_manifest["instruction_spans"] = [
            [item.pc, item.instruction_width]
            for item in global_ir.instructions if item.instruction_width > 0
        ]
        script_manifest["opaque_ranges"] = (
            [[global_ir.opaque_from_pc, len(program)]]
            if global_ir.opaque_from_pc is not None else []
        )
        if transformation is None:
            script_manifest["content_provenance"] = "authentic-resource-unchanged"
        else:
            original_output = args.output_dir / f"script-{number}.source.scrp"
            original_output.write_bytes(original_program)
            transformation["original_output"] = original_output.name
            transformation["executed_output"] = output.name
            script_manifest["identity"] = f"synthetic.wrapper.global.{number}"
            script_manifest["content_provenance"] = "synthetic-fixture-wrapper"
            script_manifest["transformation"] = transformation
            global_transformations.append(transformation)
        global_scripts.append(script_manifest)
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "num_global_scripts": provider.global_script_count,
        "synthetic_global_transformations": global_transformations,
        "profile": {
            "path": args.profile.name, "sha256": profile_hash,
            "engine": profile.engine_id, "game": profile.game_id,
            "variant": profile.variant, "identity_sha256": game_hash,
        },
        "source": {
            "archive": args.archive.name, "archive_sha256": archive_hash,
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
        "source_scope": ("ALL_AVAILABLE_EXECUTABLES" if args.all_source_executables
                         else "EXPLICIT_SELECTION"),
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
