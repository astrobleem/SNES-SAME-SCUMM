#!/usr/bin/env python3
"""Compile one raw SCUMM v5 room into the current SAME cooked-room backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room_compiler import (
    compile_room_payload, compiler_source_manifest, compiler_source_sha256,
    profile_game_identity, source_member_pair,
)
from same.profile import load_profile
from same.resources import MemoryResourceProvider

ROOT = Path(__file__).resolve().parents[1]


def backend_environment() -> dict[str, str]:
    """Keep Python imports stable when the backend generator changes cwd."""
    environment = os.environ.copy()
    entries = [item for item in environment.get("PYTHONPATH", "").split(os.pathsep) if item]
    resolved = [str((Path.cwd() / item).resolve()) if not Path(item).is_absolute() else item
                for item in entries]
    source_root = str(ROOT / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        [source_root] + [item for item in resolved if item != source_root]
    )
    return environment


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True,
                        help="external source archive containing the SCUMM .000/.001 pair")
    parser.add_argument("--profile", type=Path, required=True,
                        help="thin SCUMM v5 source-edition profile")
    parser.add_argument("--room", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--registration-only", action="store_true",
                        help="emit a non-dispatchable source registration record")
    parser.add_argument("--require-complete-decode", action="store_true",
                        help="fail if any instruction width is outside this decoder slice")
    parser.add_argument("--snes-backend", action="store_true",
                        help="run the existing SNES room-table/selector backend")
    parser.add_argument("--far-programs", action="store_true",
                        help="use the existing primary/overflow program-ID allocator")
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()

    archive_bytes = args.archive.read_bytes()
    with zipfile.ZipFile(args.archive) as archive:
        members = source_member_pair(archive.namelist())
        raw = {key: archive.read(member) for key, member in members.items()}
    profile_bytes = args.profile.read_bytes()
    profile = load_profile(args.profile, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None or policy.resource_format != "lucasarts_scumm_v5":
        raise RuntimeError("profile must define a raw LucasArts SCUMM v5 resource policy")
    provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw), policy)
    resource_key = f"room.{args.room}"
    room_payload = provider.read(resource_key)
    location = provider.source_location(resource_key)
    profile_hash = sha(profile_bytes)
    game_hash = profile_game_identity(profile)
    archive_hash = sha(archive_bytes)
    index_hash = sha(raw["game.index"])
    data_hash = sha(raw["game.data"])
    compilation = compile_room_payload(
        room_payload,
        room_number=args.room,
        game_name=f"{profile.game_id}:{profile.variant}",
        resource_key=resource_key,
        source_member=members["game.data"],
        source_container_offset=int(location["container_offset"]),
        original_room_file_offset=int(location["payload_offset"]),
        profile_sha256=profile_hash,
        game_identity_sha256=game_hash,
        archive_sha256=archive_hash,
        index_sha256=index_hash,
        data_sha256=data_hash,
        global_script_count=provider.global_script_count,
        global_object_states=provider.global_objects.states,
        global_object_owners=provider.global_objects.owners,
        global_object_classes=provider.global_objects.classes,
        executable=not args.registration_only,
    )
    incomplete = compilation.capabilities.decode_incomplete_scripts
    if args.require_complete_decode and incomplete:
        raise RuntimeError("room has opaque bytecode: " + ", ".join(incomplete))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    room_output = f"room-{args.room}.sc5c"
    (args.output_dir / room_output).write_bytes(compilation.cooked_record)
    ir_name = f"room-{args.room}.ir.json"
    analysis_name = f"room-{args.room}.analysis.json"
    (args.output_dir / ir_name).write_bytes(compilation.ir_json())
    (args.output_dir / analysis_name).write_bytes(compilation.analysis_json())
    (args.output_dir / "global-object-states.bin").write_bytes(provider.global_objects.states)
    (args.output_dir / "global-object-owners.bin").write_bytes(provider.global_objects.owners)

    record = dict(compilation.record_manifest)
    record["output"] = room_output
    profile_id = {
        "engine": profile.engine_id,
        "game": profile.game_id,
        "variant": profile.variant,
        "identity_sha256": game_hash,
        "sha256": profile_hash,
    }
    source_id = {
        "archive_sha256": archive_hash,
        "index_member": members["game.index"],
        "index_sha256": index_hash,
        "data_member": members["game.data"],
        "data_sha256": data_hash,
    }
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "compiler_schema": "same_scumm_v5_room_bundle_v1",
        "compiler": {
            "name": "same-scumm-v5-room-bundle",
            "source_sha256": compiler_source_sha256(),
            "source_components": compiler_source_manifest(),
            "cli_sha256": sha(Path(__file__).read_bytes()),
        },
        "options": {
            "room": args.room,
            "registration_only": args.registration_only,
            "require_complete_decode": args.require_complete_decode,
            "snes_backend": args.snes_backend,
            "far_programs": args.far_programs,
        },
        "num_global_scripts": provider.global_script_count,
        "profile": profile_id,
        "source": source_id,
        "global_objects": {
            "count": len(provider.global_objects.states),
            "states_output": "global-object-states.bin",
            "states_sha256": sha(provider.global_objects.states),
            "owners_output": "global-object-owners.bin",
            "owners_sha256": sha(provider.global_objects.owners),
        },
        "records": [record],
        "global_scripts": [],
        "compiler_outputs": {
            "ir": ir_name,
            "ir_sha256": sha(compilation.ir_json()),
            "analysis": analysis_name,
            "analysis_sha256": sha(compilation.analysis_json()),
            "cooked_room": room_output,
            "cooked_room_sha256": sha(compilation.cooked_record),
        },
    }
    backend_tool = Path(__file__).resolve().with_name("generate_snes_cooked_rooms.py")
    if args.snes_backend:
        manifest["compiler"]["snes_backend_sha256"] = sha(backend_tool.read_bytes())
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    (args.output_dir / "manifest.json").write_bytes(manifest_bytes)
    if args.snes_backend:
        backend_dir = args.output_dir / "snes-backend"
        backend_dir.mkdir(exist_ok=True)
        command = [
            sys.executable,
            str(backend_tool),
            "--manifest", str(args.output_dir / "manifest.json"),
            "--output", "rooms.inc.pasm",
            "--data-output", "room-data.inc.pasm",
            "--binary-dir", "segments",
            "--report", "report.json",
            "--executable-local-room", str(args.room),
            "--relative-binary-paths",
        ]
        if args.far_programs:
            command.append("--far-programs")
        subprocess.run(command, cwd=backend_dir, env=backend_environment(), check=True)
        backend_files = []
        for path in sorted(backend_dir.rglob("*")):
            if path.is_file() and path.name != "backend-artifacts.json":
                relative = path.relative_to(backend_dir).as_posix()
                content = path.read_bytes()
                backend_files.append({
                    "path": relative, "size": len(content), "sha256": sha(content),
                })
        (backend_dir / "backend-artifacts.json").write_text(
            json.dumps({"schema": "same_scumm_snes_room_backend_artifacts_v1",
                        "files": backend_files}, indent=2, sort_keys=True) + "\n"
        )
    report = compilation.capabilities.to_dict()
    print(
        f"SCUMM v5 room {args.room}: {len(compilation.room_ir.scripts)} executable bodies, "
        f"{len(report['static_dependencies'])} static dependencies, "
        f"{len(report['dynamic_dependencies'])} dynamic dependencies, "
        f"{len(report['unsupported_operations'])} unsupported semantics, "
        f"{len(report['unclassified_operations'])} unclassified bytecode tails"
    )
    print(f"Cooked backend artifact SHA-256: {sha(compilation.cooked_record)}")
    print(f"Manifest SHA-256: {sha(manifest_bytes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
