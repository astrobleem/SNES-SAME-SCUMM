#!/usr/bin/env python3
"""Build one deterministic SAMEPKG from a complete SCUMM v5 source edition.

This packages the generic compiler's canonical ProgramUnit directory, complete
cooked room records, live-room tables and supported indexed visual projection.
Package presence is deliberately distinct from native loadability and semantic
execution certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from compile_scumm_game import read_source
from generate_snes_cooked_rooms import OVERFLOW_PROGRAM_IDS, PRIMARY_PROGRAM_IDS
from same.engines.scumm_v5.cooked_room import decode_cooked_room
from same.engines.scumm_v5.full_source_backend import (
    build_lowering_report, validate_emitted_program_directory,
)
from same.engines.scumm_v5.game_analysis import analyze_game, canonical_json, game_analysis_hash
from same.engines.scumm_v5.live_room_resources import (
    MAX_ACTIVE_BYTES as MAX_ACTIVE_LIVE_ROOM_BYTES,
    MAX_PENDING_BYTES as MAX_PENDING_LIVE_ROOM_BYTES,
    decode_live_room,
)
from same.engines.scumm_v5.native_residency import NativeProgramDirectory
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room_visual import decode_room_visual
from same.package import inspect_package
from same.profile import load_profile
from same.resources import MemoryResourceProvider


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def load_cooked_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent.resolve()
    for row in manifest.get("records", []):
        rel = Path(str(row.get("output", "")))
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError(f"unsafe cooked SC5ROOM path: {rel}")
        record_path = (root / rel).resolve()
        if not record_path.is_relative_to(root):
            raise ValueError(f"SC5ROOM path escapes its manifest root: {rel}")
        payload = record_path.read_bytes()
        if (len(payload) != int(row["record_length"])
                or sha(payload) != str(row["record_sha256"])):
            raise ValueError(f"cooked SC5ROOM differs from its manifest: {rel}")
        decode_cooked_room(payload, expected_room=int(row["room"]))
        visual = row.get("visual")
        if visual is not None:
            visual_rel = Path(str(visual["output"]))
            if visual_rel.is_absolute() or ".." in visual_rel.parts:
                raise ValueError(f"unsafe cooked SC5VIS path: {visual_rel}")
            visual_path = (root / visual_rel).resolve()
            if not visual_path.is_relative_to(root):
                raise ValueError(f"SC5VIS path escapes its manifest root: {visual_rel}")
            visual_payload = visual_path.read_bytes()
            if (len(visual_payload) != int(visual["record_length"])
                    or sha(visual_payload) != str(visual["record_sha256"])):
                raise ValueError(f"cooked SC5VIS differs from its manifest: {visual_rel}")
            decode_room_visual(visual_payload, expected_room=int(row["room"]))
    if manifest.get("source_scope") != "ALL_AVAILABLE_EXECUTABLES":
        raise ValueError("whole-source package requires ALL_AVAILABLE_EXECUTABLES")
    return manifest


def package_room_preflight(
    cooked: dict[str, Any], storage: dict[str, Any], package_path: Path,
) -> dict[str, Any]:
    raw = package_path.read_bytes()
    live_by_room = {int(row["room"]): row for row in storage["live_room_records"]}
    route_by_room = {int(row["room"]): row for row in storage.get("live_route_records", [])}
    visual_by_room = {int(row["room"]): row for row in storage["visual_records"]}
    source_by_room = {int(row["room"]): row for row in storage["source_room_records"]}
    cooked_rooms = {int(row["room"]): row for row in cooked["records"]}
    room_ids = sorted(set(cooked_rooms) | set(live_by_room) | set(visual_by_room))
    rows: list[dict[str, Any]] = []
    for room_id in room_ids:
        source = cooked_rooms.get(room_id)
        live_row = live_by_room.get(room_id)
        visual_row = visual_by_room.get(room_id)
        source_row = source_by_room.get(room_id)
        live = None
        visual = None
        route = None
        if live_row is not None:
            start, size = int(live_row["package_offset"]), int(live_row["length"])
            route_row = route_by_room.get(room_id)
            route = None
            if route_row is not None:
                route_start, route_size = (int(route_row["package_offset"]),
                                           int(route_row["length"]))
                route = raw[route_start:route_start + route_size]
            live = decode_live_room(raw[start:start + size], expected_room=room_id,
                                    max_size=0xFFFF, route_data=route)
        if visual_row is not None:
            start, size = int(visual_row["package_offset"]), int(visual_row["length"])
            visual = decode_room_visual(raw[start:start + size], expected_room=room_id)
        src_room = None
        if source_row is not None:
            start, size = int(source_row["package_offset"]), int(source_row["length"])
            src_room = raw[start:start + size]
            if sha(src_room) != str(source_row["sha256"]):
                raise ValueError(f"packaged SC5ROOM hash mismatch for room {room_id}")
        rows.append({
            "room": room_id,
            "source_identity": None if source is None else str(source["resource_key"]),
            "source_location": None if source is None else {
                "archive_member": cooked.get("source", {}).get("data_member"),
                "member_offset": int(source["original_room_file_offset"]),
                "source_payload_bytes": int(source["original_room_length"]),
            },
            "source_room_sha256": None if source is None else source["original_room_sha256"],
            "source_room_bytes": None if source is None else int(source["original_room_length"]),
            "sc5room": {
                "status": "PACKAGED_SOURCE_RECORD" if src_room is not None else "NOT_PACKAGED",
                "bytes": None if source_row is None else int(source_row["length"]),
                "sha256": None if source_row is None else str(source_row["sha256"]),
                "package_offset": None if source_row is None else int(source_row["package_offset"]),
                "native_loadable": False,
                "reason": "complete cooked source record is retained for provenance; live mode consumes SC5LIVE/SC5VIS",
            },
            "sc5live": {
                "status": "PACKAGED" if live is not None else "MISSING",
                "bytes": None if live_row is None else int(live_row["length"]),
                "normalized_v3_semantic_bytes": (
                    None if live_row is None else
                    int(live_row.get("normalized_v3_semantic_bytes", 0))
                ),
                "external_route_bytes": (
                    None if live_row is None else int(live_row.get("external_route_bytes", 0))
                ),
                "sha256": None if live_row is None else str(live_row["sha256"]),
                "package_offset": None if live_row is None else int(live_row["package_offset"]),
                "objects": None if live is None else live.object_count,
                "object_verb_entries": None if live is None else live.verb_count,
                "room_locals": None if live is None else live.local_count,
                "walkboxes": None if live is None else live.box_count,
                "movement_matrix_bytes": None if live is None else live.box_count ** 2,
                "native_loadable": bool(live_row and live_row["native_loadable"]),
                "native_loadability_reason": None if live_row is None else live_row["native_loadability_reason"],
                "chunk_integrity": None if live_row is None else {
                    "chunk_size": int(storage["live_room_chunk_size"]),
                    "first_chunk": int(live_row["first_chunk"]),
                    "chunk_count": int(live_row["chunk_count"]),
                    "checksums": [str(chunk["crc32"]) for chunk in live_row["chunks"]],
                    "whole_record_sha256": str(live_row["sha256"]),
                    "runtime_consumed": False,
                },
                "table_bytes": None if live is None else dict(live.section_sizes),
                "storage_representation": None if live is None else {
                    "schema_version": int(live.payload[8]) | (int(live.payload[9]) << 8),
                    "active_record_bytes": len(live.payload),
                    "normalized_v3_semantic_bytes": sum(live.section_sizes.values()),
                    "external_route_bytes": 0 if route is None else len(route),
                    "active_metadata_capacity_bytes": MAX_ACTIVE_LIVE_ROOM_BYTES,
                    "pending_route_capacity_bytes": MAX_PENDING_LIVE_ROOM_BYTES,
                    "whole_record_contiguous_in_wram": False,
                },
                "runtime_consumers": None if live is None else {
                    "walkbox_flags": "copied to mutable active walkbox flag table",
                    "walkbox_geometry": "immutable; one 18-byte geometry record is loaded on demand",
                    "route_matrix": "read by active movement next-box lookup",
                    "portal_directory": "read by active movement portal lookup",
                    "objects": "installed into ordinary SCUMM object-state records",
                    "names": "copied to the shared bounded object-name cache",
                    "object_walk": "read by current object/walkbox geometry queries",
                    "verbs": "read by existing shared object-carrier dispatch",
                    "locals": "read by the current-room local-script resolver",
                    "bundles": "consumed during bundle bind/release at lifecycle boundary",
                    "header": "identity/count/offset validation and provenance; not a script body",
                },
            },
            "sc5vis": {
                "status": "PACKAGED_INDEXED_PROJECTION" if visual is not None else "MISSING_CODEC_OR_SOURCE",
                "bytes": None if visual_row is None else int(visual_row["length"]),
                "source_sha256": None if visual_row is None else str(visual_row["source_record_sha256"]),
                "sha256": None if visual_row is None else str(visual_row["sha256"]),
                "width": None if visual is None else visual.width,
                "height": None if visual is None else visual.height,
                "pixel_bytes": None if visual is None else len(visual.pixels),
                "palette_bytes": None if visual is None else len(visual.palette),
                "package_offset": None if visual_row is None else int(visual_row["package_offset"]),
                "native_loadable": visual is not None and (visual.width, visual.height) == (256, 224),
                "conversion": None if visual_row is None else visual_row["projection"],
                "fidelity_status": (
                    "MISSING" if visual is None else
                    "ASPECT_FIT_PROJECTION; NOT A NATIVE PPU EQUIVALENCE CLAIM"
                ),
                "source_geometry_warning": (
                    "source width below 64 pixels; inspect source resource interpretation"
                    if visual_row is not None and
                    int(visual_row.get("projection", {}).get("source_width", 0)) < 64
                    else None
                ),
            },
            "object_and_movement_coverage": {
                "status": "SC5LIVE_PARSED" if live is not None else "UNAVAILABLE",
                "object_count": None if live is None else live.object_count,
                "verb_count": None if live is None else live.verb_count,
                "walkbox_count": None if live is None else live.box_count,
                "route_matrix_bytes": None if live is None else live.box_count ** 2,
                "entry_program_unit": None if live is None else live.entry_program_unit,
                "exit_program_unit": None if live is None else live.exit_program_unit,
            },
            "native_room_loadable": bool(
                live is not None and live_row["native_loadable"]
                and visual is not None and (visual.width, visual.height) == (256, 224)
            ),
        })
    rows.insert(0, {
        "room": 0, "source_identity": "RoomResource(0)",
        "status": "RESOURCE_LESS_LIFECYCLE_ONLY",
        "sc5room": {"status": "NOT_APPLICABLE"},
        "sc5live": {"status": "NOT_APPLICABLE"},
        "sc5vis": {"status": "NOT_APPLICABLE"},
        "native_room_loadable": True,
        "reason": "room 0 retains bootstrap/lifecycle semantics and has no indexed source ROOM payload",
    })
    return {"schema": "same_scumm_v5_source_room_preflight_v1", "rooms": rows}


def exact_room_code_duplication(
    cooked_dir: Path, cooked: dict[str, Any], storage: dict[str, Any],
) -> dict[str, Any]:
    """Verify which executable carrier bytes are also inside complete SC5ROOMs."""
    stored = {str(row["identity"]): row for row in storage["records"]}
    count = 0
    duplicate_bytes = 0
    by_kind: dict[str, dict[str, int]] = {}
    for room in cooked["records"]:
        payload = (cooked_dir / str(room["output"])).read_bytes()
        candidates: list[tuple[str, str, int, str, dict[str, Any]]] = []
        room_id = int(room["room"])
        for row in room.get("scripts", []):
            kind, number = str(row["kind"]), int(row["number"])
            if kind == "ENCD":
                identity = f"RoomEntryProgram({room_id})"
            elif kind == "EXCD":
                identity = f"RoomExitProgram({room_id})"
            elif kind == "LSCR":
                identity = f"RoomLocalProgram(room={room_id},local={number})"
            else:
                continue
            candidates.append((identity, kind, int(row["program_length"]),
                               str(row["sha256"]), row))
        for row in room.get("objects", []):
            identity = f"ObjectProgram(room={room_id},object={int(row['object_id'])})"
            candidates.append((identity, "OBCD", int(row["obcd_length"]),
                               str(row["obcd_sha256"]), row))
        for identity, kind, length, source_hash, source_row in candidates:
            unit = stored.get(identity)
            if unit is None:
                continue
            if int(unit["length"]) != length or str(unit["sha256"]) != source_hash:
                raise ValueError(f"SC5ROOM and SC5CODE disagree for {identity}")
            offset = int(source_row["cooked_record_offset"])
            fragment = payload[offset:offset + length]
            if len(fragment) != length or sha(fragment) != source_hash:
                raise ValueError(f"SC5ROOM does not contain the declared source body for {identity}")
            count += 1
            duplicate_bytes += length
            group = by_kind.setdefault(kind, {"program_units": 0, "bytes": 0})
            group["program_units"] += 1
            group["bytes"] += length
    return {
        "program_unit_body_records_exactly_repeated_in_sc5room": count,
        "exact_repeated_body_bytes": duplicate_bytes,
        "by_source_form": dict(sorted(by_kind.items())),
        "meaning": (
            "SC5ROOM retains complete cooked room containers while SC5CODE stores "
            "selector-free executable carriers; byte identity was checked by source "
            "offset, size, and SHA-256. The current live runtime consumes SC5LIVE/SC5VIS "
            "and SC5CODE, not SC5ROOM, so these copies are retained source-room payload, "
            "not required duplicate runtime representations."
        ),
    }


def directory_endpoint_probe(native_directory: NativeProgramDirectory,
                             storage: dict[str, Any]) -> dict[str, Any]:
    entries = native_directory.document.get("entries", [])
    records = sorted(storage["records"], key=lambda row: int(row["program_unit_id"]))
    if len(entries) != len(records) or not entries:
        raise ValueError("native directory and package body collection differ in size")
    probes = []
    for index in sorted({0, len(entries) // 2, len(entries) - 1}):
        entry, record = entries[index], records[index]
        if int(entry["program_unit_id"]) != index or int(record["program_unit_id"]) != index:
            raise ValueError(f"ProgramUnit directory is not dense at ID {index}")
        if str(entry["identity"]) != str(record["identity"]):
            raise ValueError(f"ProgramUnit directory/package identity mismatch at ID {index}")
        if str(entry["sha256"]) != str(record["sha256"]):
            raise ValueError(f"ProgramUnit directory/package body mismatch at ID {index}")
        probes.append({
            "directory_index": index,
            "program_unit_id": index,
            "identity": str(entry["identity"]),
            "body_sha256": str(entry["sha256"]),
            "body_bytes": int(entry["length"]),
            "package_section": str(record["package_section"]),
            "page_count": int(record["page_count"]),
        })
    return {
        "status": "ALL_ENTRIES_RECONCILED; FIRST_MIDDLE_LAST_PROBED",
        "directory_entries": len(entries),
        "selector_values_emitted": native_directory.document.get("selector_values_emitted"),
        "probes": probes,
        "scope": "compiler/package directory validation; native FATE execution is not implied",
    }


def normalize_build_paths(value: Any, root: Path) -> Any:
    if isinstance(value, dict):
        return {key: normalize_build_paths(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_build_paths(item, root) for item in value]
    if isinstance(value, str) and value.startswith("/"):
        candidate = Path(value)
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            return value
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare-program-storage", type=Path,
                        help="optional selected-corpus program-storage.json for identity/hash reconciliation")
    args = parser.parse_args()
    source, profile_path, output = (
        args.source.resolve(), args.profile.resolve(), args.output.resolve()
    )
    if not source.is_file():
        parser.error(f"source archive does not exist or is not a file: {source}")
    if not profile_path.is_file():
        parser.error(f"profile does not exist or is not a file: {profile_path}")
    previous_selected: dict[str, Any] | None = None
    if args.compare_program_storage is not None:
        comparison_path = args.compare_program_storage.resolve()
        if not comparison_path.is_file():
            parser.error(f"selected program-storage input is not a file: {comparison_path}")
        try:
            previous_selected = json.loads(comparison_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            parser.error(f"cannot read selected program-storage JSON: {exc}")
    if output.exists() and any(output.iterdir()):
        parser.error(f"refusing non-empty package root {output}; use a fresh build directory")
    output.mkdir(parents=True, exist_ok=True)

    raw_source, source_members, source_hash = read_source(source)
    profile_bytes = profile_path.read_bytes()
    profile = load_profile(profile_path, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None or policy.resource_format != "lucasarts_scumm_v5":
        parser.error("profile must select the generic LucasArts SCUMM v5 front end")
    provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw_source), policy)
    analysis = analyze_game(
        provider, profile=profile, profile_bytes=profile_bytes,
        archive_sha256=source_hash, source_members=source_members,
        backend_selector_capacity={
            "primary_ids": len(PRIMARY_PROGRAM_IDS),
            "overflow_ids": len(OVERFLOW_PROGRAM_IDS),
            "value": len(PRIMARY_PROGRAM_IDS) + len(OVERFLOW_PROGRAM_IDS),
            "epistemic": "EXACT", "source": "current native resident selector pool",
            "selectors_allocated": False,
        },
    )
    command_env = dict(os.environ)
    command_env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT / "tools"), command_env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    cooked_dir = output / "cooked"
    backend_dir = output / "backend"
    storage_dir = output / "package"
    subprocess.run([
        sys.executable, str(ROOT / "tools/cook_scumm_v5_rooms.py"),
        "--archive", str(source), "--profile", str(profile_path),
        "--all-source-executables", "--executable", "--visuals",
        "--output-dir", str(cooked_dir),
    ], cwd=ROOT, env=command_env, check=True, stdout=subprocess.DEVNULL)
    cooked_path = cooked_dir / "manifest.json"
    cooked = load_cooked_manifest(cooked_path)

    report_path = backend_dir / "generator-report.json"
    native_path = backend_dir / "native_program_directory.json"
    backend_path = backend_dir / "backend_program_directory.json"
    subprocess.run([
        sys.executable, str(ROOT / "tools/generate_snes_cooked_rooms.py"),
        "--manifest", str(cooked_path),
        "--output", str(backend_dir / "scumm_v5_rooms.inc.pasm"),
        "--data-output", str(backend_dir / "scumm_v5_room_data.inc.pasm"),
        "--binary-dir", str(output / "segments"), "--report", str(report_path),
        "--first-bank", "32", "--far-programs", "--dynamic-program-residency",
        "--pack-source-tables", "--banked-room-directory-data",
        "--msu1-program-storage-dir", str(storage_dir),
        "--msu1-program-directory-include", str(backend_dir / "scumm_msu1_programs.inc.pasm"),
        "--msu1-program-directory-bank", "10", "--msu1-program-page-directory-bank", "12",
        "--msu1-program-cache-bytes", "0x800", "--msu1-live-room-resources",
        "--msu1-include-source-room-records",
        "--native-directory-output", str(native_path),
        "--native-directory-include", str(backend_dir / "native_program_directory.inc.pasm"),
        "--backend-directory-output", str(backend_path),
        "--reserved-bank", "9", "--reserved-bank", "83",
        "--relative-binary-paths",
    ], cwd=ROOT, env=command_env, check=True, stdout=subprocess.DEVNULL)

    generated_report = json.loads(report_path.read_text(encoding="utf-8"))
    native_directory = NativeProgramDirectory(json.loads(native_path.read_text(encoding="utf-8")))
    backend_directory = json.loads(backend_path.read_text(encoding="utf-8"))
    storage = json.loads((storage_dir / "program-storage.json").read_text(encoding="utf-8"))
    package_path = storage_dir / "scumm-programs.msu"
    storage_file = package_path.read_bytes()
    package_info = inspect_package(package_path, verify=True)
    package_sections = {row.name: row for row in package_info.sections}
    required_sections = {"SC5ROOM", "SC5LIVE", "SC5ROUT", "SC5VIS", "SC5CODE"}
    if not required_sections <= set(package_sections):
        raise ValueError(f"complete source package is missing sections: {sorted(required_sections - set(package_sections))}")

    source_entries = analysis.native_program_directory["entries"]
    source_by_identity = {str(row["identity"]): row for row in source_entries}
    generated_by_identity = {str(row["identity"]): row for row in native_directory.document["entries"]}
    storage_by_identity = {str(row["identity"]): row for row in storage["records"]}
    missing = sorted(set(source_by_identity) - set(generated_by_identity))
    extra = sorted(set(generated_by_identity) - set(source_by_identity))
    body_mismatches = []
    for identity in sorted(set(source_by_identity) & set(storage_by_identity)):
        expected_hash = str(generated_by_identity[identity].get("sha256"))
        observed_hash = str(storage_by_identity[identity].get("sha256"))
        if expected_hash != observed_hash:
            body_mismatches.append(identity)
    if missing or extra or body_mismatches or set(storage_by_identity) != set(source_by_identity):
        raise ValueError(
            "full source ProgramUnit reconciliation failed: "
            f"missing={missing[:8]}, extra={extra[:8]}, body_mismatch={body_mismatches[:8]}"
        )
    room_payloads = {
        int(row["number"]): provider.read(str(row["resource_key"]))
        for row in provider.source_catalog() if row["category"] == "room"
    }
    emission_check = validate_emitted_program_directory(analysis, generated_report, room_payloads)
    if not emission_check["complete_and_source_identical"]:
        raise ValueError("generated full ProgramUnit directory differs from source analysis")

    for row in storage["records"]:
        start, length = int(row["package_offset"]), int(row["length"])
        body = storage_file[start:start + length]
        if len(body) != length or sha(body) != str(row["sha256"]):
            raise ValueError(f"SC5CODE range/hash mismatch for {row['identity']}")

    preflight = package_room_preflight(cooked, storage, package_path)
    room_code_duplicate = exact_room_code_duplication(cooked_dir, cooked, storage)
    endpoint_probe = directory_endpoint_probe(native_directory, storage)
    write_json(output / "room-resource-preflight.json", preflight)
    write_json(output / "source-emission-check.json", emission_check)
    write_json(output / "lowering-report.json", build_lowering_report(analysis))
    analysis_files = analysis.files()
    analysis_manifest = {
        "schema": "same_scumm_v5_package_analysis_manifest_v1",
        "game_id": profile.game_id, "variant": profile.variant,
        "profile_sha256": sha(profile_bytes), "source_sha256": source_hash,
        "compiler_analysis_sha256": game_analysis_hash(analysis_files),
        "files": [{"path": name, "size": len(data), "sha256": sha(data)}
                  for name, data in sorted(analysis_files.items())],
    }
    for name, data in analysis_files.items():
        target = output / "analysis" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    write_json(output / "analysis" / "analysis_manifest.json", analysis_manifest)

    source_room_rows = storage["source_room_records"]
    live_rows = storage["live_room_records"]
    visual_rows = storage["visual_records"]
    indexed_room_ids = {int(row["room"]) for row in cooked["records"]}
    source_room_ids = {int(row["room"]) for row in source_room_rows}
    live_room_ids = {int(row["room"]) for row in live_rows}
    visual_room_ids = {int(row["room"]) for row in visual_rows}
    room_resource_coverage = {
        "indexed_room_count": len(indexed_room_ids),
        "source_room_record_count": len(source_room_ids),
        "sc5live_record_count": len(live_room_ids),
        "sc5vis_record_count": len(visual_room_ids),
        "source_room_records_missing": sorted(indexed_room_ids - source_room_ids),
        "sc5live_missing": sorted(indexed_room_ids - live_room_ids),
        "sc5vis_missing": sorted(indexed_room_ids - visual_room_ids),
        "all_indexed_rooms_accounted_for": (
            indexed_room_ids == source_room_ids == live_room_ids == visual_room_ids
        ),
        "resource_less_room_zero": "RESOURCE_LESS_LIFECYCLE_ONLY",
    }
    lower = build_lowering_report(analysis)
    program_counts = analysis.selector_demand["counts"]
    lowered_status_counts: dict[str, int] = {}
    for status in lower["program_unit_status"].values():
        lowered_status_counts[str(status)] = lowered_status_counts.get(str(status), 0) + 1
    dependencies = analysis.selector_demand.get("dependencies", [])
    edge_counts: dict[str, int] = {}
    for edge in dependencies:
        key = str(edge.get("resolution", "UNKNOWN"))
        edge_counts[key] = edge_counts.get(key, 0) + 1
    section_rows = [section.to_dict() for section in package_info.sections]
    section_payload_bytes = sum(int(section["size"]) for section in section_rows)
    leading_directory_bytes = (
        int(package_info.sections[0].offset) if package_info.sections else len(storage_file)
    )
    inter_section_padding = 0
    for previous, current in zip(package_info.sections, package_info.sections[1:]):
        inter_section_padding += int(current.offset) - (
            int(previous.offset) + int(previous.size)
        )
    trailing_bytes = len(storage_file) - (
        leading_directory_bytes + section_payload_bytes + inter_section_padding
    )
    code_hash_counts: dict[tuple[int, str], int] = {}
    for record in storage["records"]:
        key = int(record["length"]), str(record["sha256"])
        code_hash_counts[key] = code_hash_counts.get(key, 0) + 1
    repeated_code_bytes = sum(length * (count - 1)
                              for (length, _), count in code_hash_counts.items()
                              if count > 1)
    rom_directory_parts = {
        "program_records": int(storage["program_count"]) * 10,
        "room_records": int(storage["room_directory_count"]) * 10,
        "sc5live_records": int(storage["room_directory_count"]) * 10,
        "sc5vis_records": int(storage["room_directory_count"]) * 26,
        "program_page_index_and_records": int(storage["program_page_directory_bytes"]),
    }
    package_ledger = {
        "package_bytes": len(storage_file),
        "package_directory_and_header_bytes": leading_directory_bytes,
        "sections": section_rows,
        "section_payload_bytes": section_payload_bytes,
        "inter_section_padding_bytes": inter_section_padding,
        "trailing_bytes": trailing_bytes,
        "rom_directory_payload_parts": rom_directory_parts,
        "rom_directory_payload_bytes": sum(rom_directory_parts.values()),
        "sc5code_program_body_bytes": int(storage["program_body_bytes"]),
        "same_body_bytes_repeated_for_distinct_program_unit_identities": repeated_code_bytes,
        "sc5room_program_body_bytes_repeated_exactly": room_code_duplicate[
            "exact_repeated_body_bytes"
        ],
        "sc5room_exact_duplicate_validation": room_code_duplicate,
        "room_source_record_bytes": int(storage["source_room_record_bytes"]),
        "live_room_bytes": int(storage["live_room_resource_bytes"]),
        "visual_resource_bytes": int(storage["visual_resource_bytes"]),
        "storage_alignment": "all package sections declare alignment=1; no inter-section padding observed",
        "rom_payload_policy": "SC5CODE/SC5ROOM/SC5LIVE/SC5VIS payloads are SAMEPKG-owned, not cartridge ROM payload",
    }
    selected_compare: dict[str, Any] | None = None
    if previous_selected is not None:
        previous = previous_selected
        current_by_id = storage_by_identity
        missing_selected = []
        changed_selected = []
        for previous_row in previous.get("records", []):
            identity = str(previous_row["identity"])
            current = current_by_id.get(identity)
            if current is None:
                missing_selected.append(identity)
            elif (int(current["length"]) != int(previous_row["length"])
                  or str(current["sha256"]) != str(previous_row["sha256"])):
                changed_selected.append(identity)
        selected_compare = {
            "previous_program_count": int(previous.get("program_count", 0)),
            "matched_by_semantic_identity_and_body_hash": (
                len(previous.get("records", [])) - len(missing_selected) - len(changed_selected)
            ),
            "missing": missing_selected, "body_mismatches": changed_selected,
            "previous_numeric_ids_reused": False,
        }

    readiness = {
        "schema": "same_scumm_v5_whole_source_msu_readiness_v1",
        "game": {"id": profile.game_id, "variant": profile.variant,
                 "profile_sha256": sha(profile_bytes), "archive_sha256": source_hash},
        "source_corpus_represented": bool(
            emission_check["complete_and_source_identical"]
            and len(storage["records"]) == int(storage["program_count"])
            and room_resource_coverage["all_indexed_rooms_accounted_for"]
        ),
        "source_corpus_representation_scope": (
            "all discovered executable identities plus every indexed room identity "
            "in SC5ROOM/SC5LIVE/SC5VIS; non-room resource families are inventoried "
            "separately and are not claimed packaged"
        ),
        "msu_package_emitted_and_checked": True,
        "native_loadable": all(bool(row["native_room_loadable"])
                                for row in preflight["rooms"]),
        "full_directory_validation": endpoint_probe,
        "execution_certified": bool(lower["execution_release_ready"]),
        "programs": {
            "semantic_executable_identities": int(program_counts["semantic_executable_identities"]),
            "selector_units": int(program_counts["selector_units"]),
            "program_units_packaged": int(storage["program_count"]),
            "body_bytes": int(storage["program_body_bytes"]),
            "pages": int(storage["program_page_count"]),
            "fully_lowered_and_verified": int(sum(
                value == "LOWERABLE_WITH_EVIDENCE"
                for value in lower["program_unit_status"].values()
            )),
            "unverified_or_blocked": int(sum(
                value != "LOWERABLE_WITH_EVIDENCE"
                for value in lower["program_unit_status"].values()
            )),
            "lowering_status_counts": dict(sorted(lowered_status_counts.items())),
        },
        "rooms": {
            "indexed_and_cooked": len(cooked["records"]),
            "package_only_source_records": len(source_room_rows),
            "live_records": len(live_rows), "visual_records": len(visual_rows),
            "native_loadable_count": sum(bool(row["native_room_loadable"])
                                          for row in preflight["rooms"]),
            "native_blocked_count": sum(not bool(row["native_room_loadable"])
                                         for row in preflight["rooms"]),
            "resource_identity_coverage": room_resource_coverage,
        },
        "dependency_resolution_counts": dict(sorted(edge_counts.items())),
        "whole_game_readiness": analysis.whole_game_readiness,
        "resource_inventory_by_category_and_status": analysis.census["resource_status_counts"],
        "package_sections": section_rows,
        "package_bytes": len(storage_file),
        "package_sha256": sha(storage_file),
        "byte_ledger": package_ledger,
        "runtime_resident_selectors": 178,
        "native_room_capacity": {
            "active_sc5live_bytes": MAX_ACTIVE_LIVE_ROOM_BYTES,
            "pending_checked_section_bytes": MAX_PENDING_LIVE_ROOM_BYTES,
            "sc5live_chunk_bytes": int(storage["live_room_chunk_size"]),
            "sc5live_chunk_count": int(storage["live_room_chunk_count"]),
            "large_record_policy": (
                "SC5LIVE is fetched in checked chunks into pending staging, validated, "
                "then installed as a bounded active sectioned record; SC5ROUT is a "
                "separate checked resource and expanded by the existing movement consumer"
            ),
            "max_sc5live_bytes": max((int(row["length"]) for row in live_rows), default=0),
            "max_normalized_v3_semantic_bytes": max((
                int(row.get("normalized_v3_semantic_bytes", 0)) for row in live_rows
            ), default=0),
            "max_external_route_bytes": max((
                int(row.get("external_route_bytes", 0)) for row in live_rows
            ), default=0),
            "max_sc5room_bytes": max((int(row["length"]) for row in source_room_rows), default=0),
            "oversized_live_rooms": [int(row["room"]) for row in live_rows
                                     if not row["native_loadable"]],
            "oversized_active_records": [int(row["room"]) for row in live_rows
                                         if int(row["length"]) > MAX_ACTIVE_LIVE_ROOM_BYTES],
            "normalized_v3_records_exceeding_contiguous_active_capacity": [
                int(row["room"]) for row in live_rows
                if int(row.get("normalized_v3_semantic_bytes", 0))
                > MAX_ACTIVE_LIVE_ROOM_BYTES
            ],
            "room0_policy": "RESOURCE_LESS_LIFECYCLE_ONLY",
        },
        "live_metadata_validation": {
            "indexed_nonzero_rooms": len(indexed_room_ids),
            "sc5live_records_structurally_decoded": len(live_rows),
            "sc5route_records_structurally_decoded": len(storage.get("live_route_records", [])),
            "active_records_within_native_window": sum(
                int(row["length"]) <= MAX_ACTIVE_LIVE_ROOM_BYTES for row in live_rows
            ),
            "route_records_within_native_staging": sum(
                bool(row.get("native_loadable"))
                for row in storage.get("live_route_records", [])
            ),
            "records_native_loadable_by_descriptor_and_capacity": sum(
                bool(row.get("native_loadable")) for row in live_rows
            ),
            "all_live_metadata_descriptors_loadable": all(
                bool(row.get("native_loadable")) for row in live_rows
            ),
            "native_runtime_installation_sweep_performed": False,
            "note": (
                "Host validation proves format, hashes, ranges and native capacity. "
                "This is not a claim that every room was installed by the emulator."
            ),
        },
        "selected_corpus_reconciliation": selected_compare,
        "release_status": "NOT_READY",
        "release_blockers": [
            "package completeness does not certify execution semantics",
            *([f"{len([row for row in live_rows if not row['native_loadable']])} live-room records "
               "exceed active/route checked capacities: "
               + ",".join(str(row["room"]) for row in live_rows if not row["native_loadable"])]
              if any(not row["native_loadable"] for row in live_rows) else []),
            f"{lowered_status_counts.get('UNVERIFIED', 0)} ProgramUnits remain unverified and "
            f"{lowered_status_counts.get('BLOCKED', 0)} are blocked by lowering/capability status",
            f"dependency closure remains uncertain: {edge_counts.get('DYNAMIC', 0)} dynamic and "
            f"{edge_counts.get('UNRESOLVED', 0)} unresolved edges",
            "graphics, sound/iMUSE, text/charset and portable-state coverage remain partial",
            "native all-room SC5LIVE installation sweep has not been performed",
        ],
    }
    write_json(output / "whole-source-msu-readiness.json", readiness)
    # The generator's raw path field is useful while validating in-process,
    # but host-specific absolute paths do not belong in canonical artifacts.
    write_json(report_path, normalize_build_paths(generated_report, output))
    artifact_rows = []
    for path in sorted((item for item in output.rglob("*") if item.is_file()),
                       key=lambda item: item.relative_to(output).as_posix()):
        if path.name == "build-artifacts.json":
            continue
        data = path.read_bytes()
        artifact_rows.append({"path": path.relative_to(output).as_posix(),
                              "size": len(data), "sha256": sha(data)})
    write_json(output / "build-artifacts.json", {
        "schema": "same_scumm_v5_full_source_package_artifacts_v1",
        "files": artifact_rows,
    })
    print(json.dumps({
        "program_units": storage["program_count"],
        "semantic_executable_identities": program_counts["semantic_executable_identities"],
        "rooms": len(cooked["records"]), "package_bytes": len(storage_file),
        "package_sha256": sha(storage_file),
        "native_loadable_rooms": readiness["rooms"]["native_loadable_count"],
        "readiness": str(output / "whole-source-msu-readiness.json"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
