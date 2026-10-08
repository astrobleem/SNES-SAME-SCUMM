#!/usr/bin/env python3
"""Emit every source-bound SCUMM v5 ProgramUnit through the current SNES backend.

This developer command retains complete source bytecode bodies in a banked
backend image, emits canonical resolver directories, and independently
certifies whether the selected policy permits execution. It does not imply
that graphics/audio/other resources or whole-game semantics are complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from compile_scumm_game import read_source
from generate_snes_cooked_rooms import OVERFLOW_PROGRAM_IDS, PRIMARY_PROGRAM_IDS
from same.engines.scumm_v5.full_source_backend import (
    build_lowering_report, validate_emitted_program_directory,
)
from same.engines.scumm_v5.game_analysis import (
    analyze_game, canonical_json, game_analysis_hash,
)
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.resources import MemoryResourceProvider


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="source archive/directory containing a SCUMM v5 .000/.001 pair")
    parser.add_argument("--profile", type=Path, required=True,
                        help="edition profile selecting the generic SCUMM v5 resource front end")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", choices=("strict", "experimental-diagnostic"),
                        default="strict")
    parser.add_argument("--first-bank", type=int, default=32)
    parser.add_argument("--capacity-bytes", type=lambda value: int(value, 0),
                        default=0x400000,
                        help="measured backend carrier limit (default: current 4 MiB mapping)")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    raw, members, source_hash = read_source(args.source)
    profile_bytes = args.profile.read_bytes()
    profile = load_profile(args.profile, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None or policy.resource_format != "lucasarts_scumm_v5":
        raise ValueError("profile must select the generic LucasArts SCUMM v5 resource front end")
    provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw), policy)
    analysis = analyze_game(
        provider, profile=profile, profile_bytes=profile_bytes,
        archive_sha256=source_hash, source_members=members,
        backend_selector_capacity={
            "primary_ids": len(PRIMARY_PROGRAM_IDS),
            "overflow_ids": len(OVERFLOW_PROGRAM_IDS),
            "value": len(PRIMARY_PROGRAM_IDS) + len(OVERFLOW_PROGRAM_IDS),
            "epistemic": "EXACT", "source": "current native resident selector pool",
            "selectors_allocated": False,
        },
    )

    analysis_dir = output / "analysis"
    analysis_files = analysis.files()
    manifest = {
        "schema": "same_scumm_v5_full_source_analysis_manifest_v1",
        "game_id": profile.game_id, "variant": profile.variant,
        "profile_sha256": sha256(profile_bytes), "source_sha256": source_hash,
        "compiler_analysis_sha256": game_analysis_hash(analysis_files),
        "files": [{"path": name, "size": len(value), "sha256": sha256(value)}
                  for name, value in sorted(analysis_files.items())],
    }
    for name, value in analysis_files.items():
        (analysis_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (analysis_dir / name).write_bytes(value)
    write_json(analysis_dir / "analysis_manifest.json", manifest)

    cooked = output / "cooked"
    backend = output / "backend"
    binary_dir = output / "segments"
    command_env = dict(os.environ)
    command_env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT / "tools"), command_env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    subprocess.run([
        sys.executable, str(ROOT / "tools/cook_scumm_v5_rooms.py"),
        "--archive", str(args.source.resolve()), "--profile", str(args.profile.resolve()),
        "--all-source-executables", "--executable", "--output-dir", str(cooked),
    ], cwd=ROOT, env=command_env, check=True)

    rooms_include = backend / "scumm_v5_rooms.inc.pasm"
    data_include = backend / "scumm_v5_room_data.inc.pasm"
    native_dir = backend / "native_program_directory.json"
    native_include = backend / "native_program_directory.inc.pasm"
    backend_dir = backend / "backend_program_directory.json"
    raw_report_path = backend / "generator-report.raw.json"
    subprocess.run([
        sys.executable, str(ROOT / "tools/generate_snes_cooked_rooms.py"),
        "--manifest", str(cooked / "manifest.json"),
        "--output", str(rooms_include), "--data-output", str(data_include),
        "--binary-dir", str(binary_dir), "--report", str(raw_report_path),
        "--first-bank", str(args.first_bank), "--far-programs",
        "--dynamic-program-residency", "--pack-source-tables",
        "--banked-room-directory-data",
        "--relative-binary-paths", "--native-directory-output", str(native_dir),
        "--native-directory-include", str(native_include),
        "--backend-directory-output", str(backend_dir),
        "--reserved-bank", "9", "--reserved-bank", "83",
    ], cwd=ROOT, env=command_env, check=True, stdout=subprocess.DEVNULL)

    raw_report = json.loads(raw_report_path.read_text(encoding="utf-8"))
    canonical_report = {
        key: value for key, value in raw_report.items()
        if key not in {"output", "data", "native_program_directory",
                       "native_program_directory_include", "backend_program_directory"}
    }
    write_json(backend / "generator-report.json", canonical_report)
    room_payloads = {
        int(row["number"]): provider.read(str(row["resource_key"]))
        for row in provider.source_catalog() if row["category"] == "room"
    }
    projection_check = validate_emitted_program_directory(
        analysis, canonical_report, room_payloads,
    )
    write_json(backend / "source-emission-check.json", projection_check)
    lowering = build_lowering_report(analysis)
    write_json(backend / "lowering-report.json", lowering)

    backend_document = json.loads(backend_dir.read_text(encoding="utf-8"))
    unit_status = lowering["program_unit_status"]
    for entry in backend_document["entries"]:
        status = unit_status.get(str(entry["identity"]), "BLOCKED")
        entry["backend_descriptor"]["semantic_execution_status"] = status
        entry["backend_descriptor"]["strict_executable"] = (
            status == "LOWERABLE_WITH_EVIDENCE"
        )
        entry["backend_descriptor"]["unsupported_policy"] = args.policy.upper()
    write_json(backend_dir, backend_document)
    backend_entries = backend_document["entries"]
    banks = sorted({int(row["rom_bank"]) for row in canonical_report["program_map"]
                    if row.get("rom_bank") is not None})
    code_bytes = int(canonical_report["program_code_bytes"])
    room_bytes = sum(path.stat().st_size for path in cooked.glob("room-*.sc5c"))
    bank_span_bytes = (int(canonical_report["last_bank"]) + 1) * 0x8000
    cpu_lorom_address_space_bytes = 0x100 * 0x8000
    cross_bank_edges = 0
    identities_to_bank = {
        str(row["program_unit_identity"]): int(row["rom_bank"])
        for row in canonical_report["program_map"] if row.get("rom_bank") is not None
    }
    for edge in analysis.selector_demand["dependencies"]:
        source_unit = edge.get("source_selector_unit")
        target_unit = edge.get("target_selector_unit")
        if source_unit in identities_to_bank and target_unit in identities_to_bank:
            cross_bank_edges += identities_to_bank[source_unit] != identities_to_bank[target_unit]
    descriptors = json.loads(backend_dir.read_text(encoding="utf-8"))
    directory_bytes = len((backend_dir.read_bytes()))
    rom_fit = bank_span_bytes <= args.capacity_bytes
    resource_rows = analysis.game_ir.resources
    resource_status_by_category: dict[str, dict[str, int]] = {}
    for row in resource_rows:
        category = str(row.get("category", "unknown"))
        status = str(row.get("status", "UNKNOWN"))
        bucket = resource_status_by_category.setdefault(category, {})
        bucket[status] = bucket.get(status, 0) + 1
    resource_status = {
        "schema": "same_scumm_v5_whole_source_resource_status_v1",
        "game_id": profile.game_id,
        "profile_sha256": sha256(profile_bytes),
        "source_sha256": source_hash,
        "source_inventory_by_category_and_status": {
            category: dict(sorted(statuses.items()))
            for category, statuses in sorted(resource_status_by_category.items())
        },
        "compiler_outputs": {
            "rooms": {
                "status": "STRUCTURAL_ROOM_BUNDLE_EMITTED",
                "count": len(analysis.room_compilations),
                "bytes": room_bytes,
                "visual_asset_conversion": "NOT_INCLUDED_IN_THIS_IMAGE",
            },
            "objects": {
                "status": "ROOM_OBJECT_METADATA_EMITTED",
                "resource_records": int(analysis.selector_demand["counts"]["resource_records"]),
                "object_verb_entries": int(analysis.census["object_verbs_parsed"]),
            },
            "scripts": {
                "status": "SOURCE_BYTECODE_BODIES_EMITTED_AND_HASH_RECONCILED",
                "program_units": int(canonical_report["programs"]),
                "strict_execution_certification": "INCOMPLETE",
            },
            "costumes": "INVENTORIED_ONLY; CONVERSION_NOT_INCLUDED_IN_THIS_IMAGE",
            "charsets": "INVENTORIED_ONLY; CONVERSION_NOT_INCLUDED_IN_THIS_IMAGE",
            "images_backgrounds": "ROOMS_INVENTORIED; VISUAL_CONVERSION_NOT_INCLUDED_IN_THIS_IMAGE",
            "text_strings": "SCRIPT_REFERENCES_RETAINED; COMPLETE_TEXT_RENDERING_NOT_CERTIFIED",
            "sound_imuse": "SOUND_RESOURCES_INVENTORIED; AUDIO_BINDING_NOT_INCLUDED_IN_THIS_IMAGE",
            "runtime_resource_loading": "ROOM_BUNDLE_PATH_GENERATED; WHOLE_IMAGE_NOT_LINKED",
            "portable_state": "NOT_CERTIFIED_FOR_FULL_SOURCE_DYNAMIC_RESIDENCY",
        },
    }
    write_json(output / "resource-status.json", resource_status)
    full_image = {
        "schema": "same_scumm_v5_whole_source_backend_image_v1",
        "policy": args.policy,
        "game": {"id": profile.game_id, "variant": profile.variant,
                 "profile_sha256": sha256(profile_bytes), "source_sha256": source_hash},
        "complete_source_program_directory": projection_check["complete_and_source_identical"],
        "source_census": {
            "indexed_rooms": int(analysis.census.get("rooms_inventoried", 0)),
            "parsed_rooms": int(analysis.census.get("rooms_parsed", 0)),
            "semantic_executable_identities": int(
                analysis.selector_demand["counts"]["semantic_executable_identities"]),
            "selector_units": int(analysis.selector_demand["counts"]["selector_units"]),
            "global_program_units": len(analysis.native_program_directory["global_directory"]),
            "room_bundles": len(analysis.room_compilations),
            "object_carriers": int(analysis.selector_demand["counts"]
                                    ["by_selector_unit_kind"].get("OBJECT", 0)),
            "resource_records": int(analysis.selector_demand["counts"]["resource_records"]),
        },
        "program_units_emitted": int(canonical_report["programs"]),
        "program_units_fully_lowered_and_native_verified": sum(
            value == "LOWERABLE_WITH_EVIDENCE"
            for value in lowering["program_unit_status"].values()),
        "program_units_unverified_or_blocked": sum(
            value != "LOWERABLE_WITH_EVIDENCE"
            for value in lowering["program_unit_status"].values()),
        "source_code_bytes": code_bytes,
        "room_bundle_resource_bytes": room_bytes,
        "backend_program_directory_bytes": directory_bytes,
        "program_banks": banks,
        "last_generated_bank": int(canonical_report["last_bank"]),
        "minimum_mapped_rom_span_bytes": bank_span_bytes,
        "current_backend_capacity_bytes": args.capacity_bytes,
        "cpu_lorom_address_space_bytes": cpu_lorom_address_space_bytes,
        "cpu_addressable_24bit": bank_span_bytes <= cpu_lorom_address_space_bytes,
        "program_units_outside_24bit_bank_namespace": sum(
            not bool(row.get("cpu_addressable_24bit", False))
            for row in canonical_report["program_map"]
            if row.get("program_unit_identity") is not None
        ),
        "rom_fits_current_mapping": rom_fit,
        "cross_bank_program_dependencies": int(cross_bank_edges),
        "runtime_resident_selector_capacity": 178,
        "resident_selector_values_allocated_to_source_corpus": 0,
        "unsupported_capability_operations": lowering["diagnostics_by_operation"],
        "diagnostic_image_is_release_eligible": (
            args.policy == "strict" and lowering["execution_release_ready"] and rom_fit
            and projection_check["complete_and_source_identical"]
        ),
        "unsupported_policy": (
            "STRICT_REJECTS_UNVERIFIED_OR_UNSUPPORTED_UNIT_SEMANTICS"
            if args.policy == "strict" else
            "EXPERIMENTAL_DIAGNOSTIC_BYTES_RETAINED; IMAGE_NOT_CERTIFIED_FOR_GAMEPLAY"
        ),
        "asset_execution_coverage": "SEPARATE; see resource-status.json",
        "artifacts": {
            "analysis": "analysis/", "cooked_source_bundles": "cooked/",
            "room_backend_include": "backend/scumm_v5_rooms.inc.pasm",
            "banked_code_and_data_include": "backend/scumm_v5_room_data.inc.pasm",
            "native_directory": "backend/native_program_directory.json",
            "backend_directory": "backend/backend_program_directory.json",
            "source_emission_check": "backend/source-emission-check.json",
            "lowering_report": "backend/lowering-report.json",
            "resource_status": "resource-status.json",
        },
        "resource_coverage": {
            str(key): value for key, value in analysis.census["resource_status_counts"].items()
        },
        "whole_game_readiness": analysis.whole_game_readiness,
        "generator_directory_entries": len(descriptors["entries"]),
        "generator_map_entry_count": len(canonical_report["program_map"]),
        "room_count": len(list(cooked.glob("room-*.sc5c"))),
        "global_program_count": len(analysis.native_program_directory["global_directory"]),
    }
    write_json(output / "whole-source-backend.json", full_image)
    if not projection_check["complete_and_source_identical"]:
        print("Whole-source backend emission does not match the source directory; "
              "artifacts retained for diagnosis.", file=sys.stderr)
        return 3
    if args.policy == "strict" and not full_image["diagnostic_image_is_release_eligible"]:
        print("STRICT whole-source image rejected; generated diagnostic artifacts are retained.",
              file=sys.stderr)
        print(json.dumps({
            "program_units": full_image["program_units_emitted"],
            "lowering_diagnostics": lowering["diagnostic_count"],
            "minimum_rom_span_bytes": bank_span_bytes,
            "capacity_bytes": args.capacity_bytes,
            "source_projection_complete": projection_check["complete_and_source_identical"],
            "report": str(output / "whole-source-backend.json"),
        }, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({
        "program_units": full_image["program_units_emitted"],
        "code_bytes": code_bytes, "required_rom_span_bytes": bank_span_bytes,
        "rom_fits_current_mapping": rom_fit,
        "lowering_diagnostics": lowering["diagnostic_count"],
        "release_eligible": full_image["diagnostic_image_is_release_eligible"],
        "report": str(output / "whole-source-backend.json"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
