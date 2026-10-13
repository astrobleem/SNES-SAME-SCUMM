#!/usr/bin/env python3
"""Run bounded Nexen acceptance for the feature-gated resident resolver.

The tool consumes the exact compiler-generated directory used by a ROM build.
It covers the >178-unit room route, an isolated dynamic-global candidate
probe, pinned-pool exhaustion/stale-generation, and focused room-entry
conformance against the same generated dynamic directories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import wave
import zlib
from typing import Any

from same.engines.scumm_v5.residency_contract import (
    ResidentBindingSimulator,
    ResolverDirectory,
)
from same.package import build_package, inspect_package


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
SELECTOR_CAPACITY = 178
LIVE_ROOM_STAGE_PIXELS = 4
IDS = 0x7E8C00
GENERATIONS = 0x7E8D64
FLAGS = 0x7E8EC8
ERROR = 0x7E2303
ROOM = 0x7FF2BF
VARIABLES = 0x7E0800
STATUS = 0x7E2380
SCRIPT_NUMBERS = 0x7E2399
PROGRAMS = 0x7E23B2
SLOT_PCS = 0x7E23E4
RESIDENT_STATS = 0x7E8F7F
DIAG = 0x7E8FB0
OBJECT_NAME_LENGTH = 0x7E8800
OBJECT_NAMES = 0x7E9000
OBJECT_NAME_STRIDE = 0x20
M23A_REQUEST_DIAGNOSTICS = 0x7E5450
LOAD_EGO_ACTIVE = 0x7E7FCC
LOAD_EGO_X = 0x7E7FD0
LOAD_EGO_Y = 0x7E7FD2
C31_POSITIONS = 0x7FF1A0
C31_MOVING = 0x7FF220
C31_DEST_X = 0x7FFDE5
MOVE_DEST_Y = 0x7E7BAA
C14_ACTORS = 0x7F36C0
C14_ACTOR_ROOM = 0x16
C14_ACTOR_PRESENT = 0x1F
C15_CAMERA_FOLLOWS = 0x7F5F0A
C15_CAMERA_MODE = 0x7F5F0B
CAMERA_CURRENT_X = 0x7E7FA8
PUT_ACTOR_REQUEST_X = 0x7FFEC6
PUT_ACTOR_REQUEST_Y = 0x7FFEC8
PUT_ACTOR_RESULT_X = 0x7FFECA
PUT_ACTOR_RESULT_Y = 0x7FFECC
VIDEO_SURFACE_BASE = 0x402000
LIVE_ROOM_ACTIVE_BASE = 0x41E800
LIVE_ROOM_ACTIVE_CAPACITY = 0x1800
LIVE_ROOM_ACTIVE_WRAP_GUARD = 0x410000
M23A_ACTIVE_RECORD = 0x7FF2BE
M23A_PENDING_ROOM = 0x7FF2C1
M23A_PHASE = 0x7FF2C2
M23A_HOLD = 0x7FF2C4
M23A_ENTRY_COUNT = 0x7FF2C9
M23A_ENTRY_PROGRAM = 0x7FF2CD
M23A_EXIT_PROGRAM = 0x7FF2CE
C4_ACTIVE_COUNT = 0x7E2A8A


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def u16(raw: bytes, offset: int = 0) -> int:
    return int.from_bytes(raw[offset:offset + 2], "little")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def audit_runtime_walkbox_flags(
    source_flags: bytes,
    active_flags: bytes,
    *,
    successful_matrix_mutations: int,
    matrix_trace: list[dict[str, int]],
) -> dict[str, Any]:
    """Validate immutable room flags without mistaking SCUMM state for source.

    SC5LIVE carries the initial BOXD flag bytes.  The active matrix table is
    mutable: SCUMM v5 ``matrixOps`` sub-op 1 may overwrite individual flags,
    while sub-op 4 rebuilds the derived route matrix. Therefore exact equality
    is a valid assertion only if no successful flag mutation occurred. When
    values differ, require the engine's mutation counter and decoded-operation
    trace as evidence. The trace also records valid createBoxMatrix calls with
    the runtime's no-operand sentinel (box/flags = $FF/$FF).
    """
    require(len(active_flags) == len(source_flags),
            "active walkbox flag length differs from the published BOXD table")
    differences = [
        {"box": index, "source": source, "active": active}
        for index, (source, active) in enumerate(zip(source_flags, active_flags))
        if source != active
    ]
    if differences:
        require(successful_matrix_mutations > 0 and bool(matrix_trace),
                "active walkbox flags diverged from SC5LIVE without successful "
                "matrixOps evidence: "
                f"differences={differences[:12]!r}, "
                f"mutation_count={successful_matrix_mutations}, "
                f"trace={matrix_trace!r}")
        require(all(
            (row.get("subop") == 1
             and 0 <= row.get("box", -1) < len(source_flags))
            or (row.get("subop") == 4
                and row.get("box") == 0xFF
                and row.get("flags") == 0xFF)
            for row in matrix_trace
        ),
                f"walkbox mutation trace contains invalid records: {matrix_trace!r}")
    else:
        require(successful_matrix_mutations >= 0,
                "matrix mutation counter cannot be negative")
    return {
        "source_initial_flags_hex": source_flags.hex(),
        "active_runtime_flags_hex": active_flags.hex(),
        "matches_source_initial_flags": not differences,
        "runtime_mutation_count": successful_matrix_mutations,
        "runtime_mutation_trace": matrix_trace,
        "runtime_mutated_boxes": differences,
    }


def git_identity() -> dict[str, Any]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout
    diff = subprocess.run(
        ["git", "diff", "HEAD", "--binary"], cwd=ROOT, check=True,
        capture_output=True,
    ).stdout
    untracked_paths = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout.split(b"\0")
    untracked_files = []
    for encoded_path in filter(None, untracked_paths):
        relative = encoded_path.decode("utf-8")
        content_sha256 = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        untracked_files.append({"path": relative, "sha256": content_sha256})
    untracked_files.sort(key=lambda row: row["path"])
    untracked_digest = hashlib.sha256(json.dumps(
        untracked_files, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    tracked_diff_digest = hashlib.sha256(diff).hexdigest()
    source_content_digest = hashlib.sha256(json.dumps({
        "head": head,
        "tracked_diff_sha256": tracked_diff_digest,
        "untracked_files_sha256": untracked_digest,
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "head": head,
        "worktree_clean": not status,
        "status_sha256": hashlib.sha256(status.encode()).hexdigest(),
        "working_diff_sha256": tracked_diff_digest,
        "untracked_file_count": len(untracked_files),
        "untracked_files": untracked_files,
        "untracked_files_sha256": untracked_digest,
        "source_content_sha256": source_content_digest,
    }


def load_inputs(rom: Path, manifest_path: Path, directory_path: Path,
               program_storage_path: Path | None = None, *,
               allow_invalid_route_fixture: bool = False,
               expect_room_length_rejection: bool = False) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    directory = json.loads(directory_path.read_text(encoding="utf-8"))
    build_identity_path = rom.with_name(rom.stem + ".build_identity.json")
    map_path = rom.with_suffix(".map")
    require(build_identity_path.is_file(), f"missing build identity: {build_identity_path}")
    require(map_path.is_file(), f"missing ROM map: {map_path}")
    listing_path = rom.with_suffix(".lst")
    require(listing_path.is_file(), f"missing ROM listing: {listing_path}")
    rom_symbols: dict[str, int] = {}
    for line in listing_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"; ([A-Z][A-Z0-9_]*) = \$([0-9A-Fa-f]+)\s+\(Constant\)$", line)
        if match:
            rom_symbols[match.group(1)] = int(match.group(2), 16)
    build_identity = json.loads(build_identity_path.read_text(encoding="utf-8"))
    entries = directory.get("entries", [])
    identity_to_id = {str(row["identity"]): int(row["program_unit_id"]) for row in entries}
    require(len(identity_to_id) == len(entries), "duplicate canonical ProgramUnit identity")
    require(directory.get("selector_values_emitted") is False,
            "compiler directory must remain selector-free")
    global_count = len(directory.get("global_directory", []))
    require(len(entries) > SELECTOR_CAPACITY, "fixture corpus does not exceed selector pool")
    program_storage = None
    package_info = None
    if program_storage_path is not None:
        program_storage = json.loads(program_storage_path.read_text(encoding="utf-8"))
        package_path = program_storage_path.with_name("scumm-programs.msu")
        require(package_path.is_file(), f"missing compiler SAMEPKG: {package_path}")
        package_info = inspect_package(package_path, verify=True)
        require(sha256(package_path) == program_storage.get("package_sha256"),
                "SAMEPKG bytes do not match compiler storage manifest SHA-256")
        sections = {row.name: row for row in package_info.sections}
        require("SC5CODE" in sections,
                "compiler package must contain the SC5CODE executable section")
        live_feature = build_identity.get("explicit_environment", {}).get(
            "SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES") == "1"
        if live_feature:
            require("SC5LIVE" in sections and "SC5ROUT" in sections
                    and "SC5VIS" in sections,
                    "live-room build package must contain SC5LIVE, SC5ROUT and SC5VIS")
            require(len(program_storage.get("live_room_records", []))
                    == program_storage.get("live_room_resource_count"),
                    "SC5LIVE directory count differs from its records")
            require(len(program_storage.get("visual_records", []))
                    == program_storage.get("visual_resource_count"),
                    "SC5VIS directory count differs from its records")
            live_section = sections["SC5LIVE"]
            route_section = sections["SC5ROUT"]
            visual_section = sections["SC5VIS"]
            live_rooms = {int(row["room"]) for row in program_storage["live_room_records"]}
            route_rows = program_storage.get("live_route_records", [])
            require({int(row["room"]) for row in route_rows} == live_rooms,
                    "SC5ROUT room directory differs from sectioned SC5LIVE")
            for record in program_storage["live_room_records"]:
                offset = int(record["package_offset"])
                length = int(record["length"])
                require(live_section.offset <= offset
                        and offset + length <= live_section.offset + live_section.size,
                        f"SC5LIVE room {record.get('room')} lies outside its package section")
            for record in route_rows:
                offset = int(record["package_offset"])
                length = int(record["length"])
                require(route_section.offset <= offset
                        and offset + length <= route_section.offset + route_section.size,
                        f"SC5ROUT room {record.get('room')} lies outside its package section")
            for record in program_storage["visual_records"]:
                offset = int(record["package_offset"])
                length = int(record["length"])
                require(visual_section.offset <= offset
                        and offset + length <= visual_section.offset + visual_section.size,
                        f"SC5VIS room {record.get('room')} lies outside its package section")
                for offset_key, length_key in (("pixel_package_offset", "pixel_length"),
                                               ("palette_package_offset", "palette_length")):
                    payload_offset = int(record[offset_key])
                    payload_length = int(record[length_key])
                    require(visual_section.offset <= payload_offset
                            and payload_offset + payload_length
                            <= visual_section.offset + visual_section.size,
                            f"SC5VIS room {record.get('room')} subresource lies outside its section")
        require(program_storage.get("program_count") == len(entries),
                "storage directory does not cover the canonical ProgramUnit directory")
        storage_records = program_storage.get("records", [])
        require(len(storage_records) == len(entries),
                "storage manifest ProgramUnit record count differs")
        package_bytes = package_path.read_bytes()
        for expected_id, (entry, record) in enumerate(zip(entries, storage_records)):
            require(record.get("program_unit_id") == expected_id
                    and entry.get("program_unit_id") == expected_id
                    and record.get("identity") == entry.get("identity"),
                    f"storage body identity differs at canonical ID {expected_id}")
            require(record.get("package_section") == "SC5CODE"
                    and 0 <= int(record.get("package_offset", -1))
                    and int(record.get("length", 0)) > 0,
                    f"invalid SC5CODE body descriptor for ID {expected_id}")
            body_offset = int(record["package_offset"])
            body_length = int(record["length"])
            code_section = sections["SC5CODE"]
            require(code_section.offset <= body_offset
                    and body_offset + body_length <= code_section.offset + code_section.size,
                    f"ProgramUnit {expected_id} lies outside SC5CODE")
            body_bytes = package_bytes[body_offset:body_offset + body_length]
            require(len(body_bytes) == body_length
                    and hashlib.sha256(body_bytes).hexdigest() == record.get("sha256"),
                    f"ProgramUnit {expected_id} bytes differ from their body identity")
        room_records = program_storage.get("room_records", [])
        require(len(room_records) == program_storage.get("room_resource_count"),
                "SC5ROOM directory count differs from its records")
        if room_records:
            require("SC5ROOM" in sections,
                    "SC5ROOM records exist without an SC5ROOM package section")
            room_section = sections["SC5ROOM"]
            expected_rooms = {int(row["room"]) for row in manifest.get("records", [])}
            observed_rooms = {int(row["room"]) for row in room_records}
            require(observed_rooms == expected_rooms,
                    "SC5ROOM storage directory does not cover the source fixture rooms: "
                    f"expected={sorted(expected_rooms)}, observed={sorted(observed_rooms)}")
            for record in room_records:
                offset = int(record["package_offset"])
                length = int(record["length"])
                require(room_section.offset <= offset
                        and offset + length <= room_section.offset + room_section.size,
                        f"cooked room {record.get('room')} lies outside SC5ROOM")
                if not live_feature:
                    require(length <= 0x0800,
                            f"cooked room {record.get('room')} exceeds native staging capacity")
        require(build_identity.get("explicit_environment", {}).get(
                    "SAME_BUILD_SCUMM_MSU1_PROGRAMS") == "1",
                "MSU ProgramUnit directory was supplied to a ROM without MSU execution enabled")
    elif build_identity.get("explicit_environment", {}).get(
            "SAME_BUILD_SCUMM_MSU1_PROGRAMS") == "1":
        raise RuntimeError("MSU-enabled ROM requires --program-storage-json for acceptance")
    room_bundles = [row for row in directory.get("bundles", [])
                    if str(row.get("identity", "")).startswith("RoomBundle(")]
    global_bundle_units = [row for row in directory.get("entries", [])
                           if row.get("kind") == "GLOBAL"]
    passive = [obj for record in manifest.get("records", [])
               for obj in record.get("objects", []) if not obj.get("verb_entries")]
    passive_program_ids = {
        f"ObjectProgram(room={int(record['room'])},object={int(obj['object_id'])})"
        for record in manifest.get("records", [])
        for obj in record.get("objects", []) if not obj.get("verb_entries")
    }
    emitted_identities = {str(row.get("identity")) for row in entries}
    require(not (passive_program_ids & emitted_identities),
            "passive object incorrectly consumes a SelectorUnit: "
            f"{sorted(passive_program_ids & emitted_identities)[:8]}")
    large_live_room = manifest.get("large_live_room")
    large_live_room_accounting = None
    if (large_live_room and not allow_invalid_route_fixture
            and not expect_room_length_rejection):
        require(program_storage is not None,
                "large live-room acceptance requires compiler SAMEPKG storage")
        target_room = int(large_live_room["room"])
        live_row = next((row for row in program_storage.get("live_room_records", [])
                         if int(row["room"]) == target_room), None)
        route_row = next((row for row in program_storage.get("live_route_records", [])
                          if int(row["room"]) == target_room), None)
        require(live_row is not None and route_row is not None,
                "large fixture room has no compiler SC5LIVE/SC5ROUT descriptors")
        package_path = program_storage_path.with_name("scumm-programs.msu")
        package_bytes = package_path.read_bytes()
        live_offset, live_length = (int(live_row["package_offset"]),
                                    int(live_row["length"]))
        route_offset, route_length = (int(route_row["package_offset"]),
                                      int(route_row["length"]))
        from same.engines.scumm_v5.live_room_resources import decode_live_room
        large_live = decode_live_room(
            package_bytes[live_offset:live_offset + live_length],
            expected_room=target_room,
            route_data=package_bytes[route_offset:route_offset + route_length],
        )
        expanded_bytes = int(live_row["normalized_v3_semantic_bytes"])
        require(expanded_bytes > int(large_live_room["minimum_expanded_bytes"]),
                "large-room fixture did not exceed its expanded semantic record target: "
                f"{expanded_bytes}")
        minimum_active_bytes = int(large_live_room.get("minimum_active_bytes", 0))
        require(live_length >= minimum_active_bytes,
                "large-room fixture did not exceed the requested compact active-record "
                f"stress target: {live_length} < {minimum_active_bytes}")
        require(live_length <= LIVE_ROOM_ACTIVE_CAPACITY,
                "large-room active record exceeds audited native active metadata capacity")
        require(route_length <= 0x0C3C,
                "large-room route resource exceeds audited native checked staging capacity")
        require(large_live.box_count == int(large_live_room["walkboxes"])
                and large_live.object_count == int(large_live_room["objects"])
                and large_live.verb_count == int(large_live_room["object_verb_entries"]),
                "large-room package counts differ from generated source metadata")
        require(len(large_live.object_names) == large_live.object_count
                and all(name for _object_id, name in large_live.object_names),
                "large-room fixture does not carry every generated object name")
        require(any(value is not None for value in large_live.portal_indices)
                and len(large_live.route_matrix) == large_live.box_count ** 2,
                "large-room fixture does not exercise sparse portals and expanded route rows")
        large_live_room_accounting = {
            "room": target_room,
            "normalized_v3_semantic_bytes": expanded_bytes,
            "active_sc5live_bytes": live_length,
            "external_route_bytes": route_length,
            "walkboxes": large_live.box_count,
            "objects": large_live.object_count,
            "object_verb_entries": large_live.verb_count,
            "names": len(large_live.object_names),
            "portal_descriptors": len(large_live.portal_records),
            "passive_object_program_units": 0,
            "within_native_active_and_route_bounds": True,
        }
    return {
        "manifest": manifest,
        "directory": directory,
        "identity_to_id": identity_to_id,
        "global_count": global_count,
        "room_bundles": room_bundles,
        "global_units": global_bundle_units,
        "build_identity": build_identity,
        "rom_path": str(rom.resolve()),
        "rom_symbols": rom_symbols,
        "hashes": {
            "source_manifest_sha256": sha256(manifest_path),
            "program_unit_directory_sha256": sha256(directory_path),
            "bundle_directory_sha256": hashlib.sha256(json.dumps(
                directory.get("bundles", []), sort_keys=True,
                separators=(",", ":"),
            ).encode()).hexdigest(),
            "global_directory_sha256": hashlib.sha256(json.dumps(
                directory.get("global_directory", []), sort_keys=True,
                separators=(",", ":"),
            ).encode()).hexdigest(),
            "program_storage_sha256": (None if program_storage_path is None
                                       else sha256(program_storage_path)),
            "rom_sha256": sha256(rom),
            "map_sha256": sha256(map_path),
            "build_identity_sha256": sha256(build_identity_path),
        },
        "source": git_identity(),
        "passive_object_record_count": len(passive),
        "large_live_room_accounting": large_live_room_accounting,
        "program_storage": program_storage,
        "program_storage_package": None if program_storage_path is None else {
            "path": str(program_storage_path.with_name("scumm-programs.msu")),
            "sha256": sha256(program_storage_path.with_name("scumm-programs.msu")),
            "size_bytes": program_storage_path.with_name("scumm-programs.msu").stat().st_size,
            "sections": [row.to_dict() for row in package_info.sections],
        },
    }


def valid_bindings(session: Any) -> list[dict[str, int]]:
    raw = session.read_memory("snesMemory", IDS, SELECTOR_CAPACITY * 5)
    ids_raw = raw[:SELECTOR_CAPACITY * 2]
    generations_raw = raw[SELECTOR_CAPACITY * 2:SELECTOR_CAPACITY * 4]
    flags_raw = raw[SELECTOR_CAPACITY * 4:]
    result = []
    for index in range(SELECTOR_CAPACITY):
        if flags_raw[index] & 1:
            result.append({
                "pool_index": index,
                "selector": (0xD0 + index if index < 48 else 0xFF - index),
                "program_unit_id": u16(ids_raw, index * 2),
                "generation": u16(generations_raw, index * 2),
                "flags": flags_raw[index],
            })
    ids = [row["program_unit_id"] for row in result]
    sentinel_rows = [row for row in result if row["program_unit_id"] == 0xFFFF]
    require(not sentinel_rows,
            "native resident table marks an empty canonical-ID sentinel valid: "
            f"{sentinel_rows}")
    require(len(ids) == len(set(ids)),
            "native resident table contains duplicate canonical IDs: "
            f"{[row for row in result if ids.count(row['program_unit_id']) > 1]}")
    return result


def active_slots(session: Any) -> list[dict[str, int]]:
    statuses = session.read_memory("snesMemory", STATUS, 25)
    numbers = session.read_memory("snesMemory", SCRIPT_NUMBERS, 25)
    programs = session.read_memory("snesMemory", PROGRAMS, 25)
    pcs = session.read_memory("snesMemory", SLOT_PCS, 50)
    return [
        {"slot": i, "status": statuses[i], "script_number": numbers[i],
         "selector": programs[i], "pc": u16(pcs, i * 2)}
        for i in range(25) if statuses[i] not in (0, 4, 0xFF)
    ]


def room_lifecycle_state(session: Any) -> dict[str, int]:
    """Capture the native room handoff state for asynchronous-load failures."""
    return {
        "active_record": session.read_memory("snesMemory", M23A_ACTIVE_RECORD, 1)[0],
        "pending_room": session.read_memory("snesMemory", M23A_PENDING_ROOM, 1)[0],
        "phase": session.read_memory("snesMemory", M23A_PHASE, 1)[0],
        "hold": session.read_memory("snesMemory", M23A_HOLD, 1)[0],
        "entry_count": session.read_memory("snesMemory", M23A_ENTRY_COUNT, 1)[0],
        "entry_selector": session.read_memory("snesMemory", M23A_ENTRY_PROGRAM, 1)[0],
        "exit_selector": session.read_memory("snesMemory", M23A_EXIT_PROGRAM, 1)[0],
        "active_slots": session.read_memory("snesMemory", C4_ACTIVE_COUNT, 1)[0],
    }


def raw_slot_state(session: Any, slot: int = 0) -> dict[str, int]:
    return {
        "slot": slot,
        "status": session.read_memory("snesMemory", STATUS + slot, 1)[0],
        "script_number": session.read_memory("snesMemory", SCRIPT_NUMBERS + slot, 1)[0],
        "selector": session.read_memory("snesMemory", PROGRAMS + slot, 1)[0],
        "pc": u16(session.read_memory("snesMemory", SLOT_PCS + slot * 2, 2)),
        "where": session.read_memory("snesMemory", 0x7E7F46 + slot, 1)[0],
    }


def live_room_control_base(inputs: dict[str, Any]) -> int:
    """Return this ROM's generated live-room control address."""
    return int(inputs["rom_symbols"]["SAME_SCUMM_LIVE_ROOM_CONTROL"])


def read_live_room_control(session: Any, inputs: dict[str, Any],
                           length: int = 0x20) -> list[int]:
    return list(session.read_memory(
        "snesMemory", live_room_control_base(inputs), length,
    ))


def read_active_route_matrix(session: Any, box_count: int,
                             base: int = 0x7F2000) -> bytes:
    """Read compact semantic rows from SAME's fixed 64-byte runtime stride."""
    require(0 <= box_count <= 64, f"invalid active route box count {box_count}")
    return b"".join(
        bytes(session.read_memory("snesMemory", base + row * 64, box_count))
        for row in range(box_count)
    )


def live_room_failure_diagnostics(session: Any,
                                 inputs: dict[str, Any]) -> dict[str, Any]:
    """Capture sectioned-load progress when an external room fails to publish."""
    control = read_live_room_control(session, inputs, 0x40)
    active = bytes(session.read_memory("snesMemory", LIVE_ROOM_ACTIVE_BASE, 82))
    lifecycle = bytes(session.read_memory("snesMemory", 0x7FF2BE, 32))
    return {
        "control": control,
        "stage": control[0],
        "valid": control[1],
        "read_length": u16(control, 2),
        "record_room": active[12],
        "active_length": u16(active, 48),
        "chunk_mode": control[0x23],
        "chunk_index": u16(control, 0x24),
        "chunk_first": u16(control, 0x26),
        "chunk_count": control[0x28],
        "chunk_start": u16(control, 0x29),
        "route_length": u16(control, 0x2C),
        "route_box_count": control[0x2E],
        "validation_checkpoint": control[0x3D],
        "expected_terminal_offset": u16(control, 0x3E),
        "m23a_lifecycle": list(lifecycle),
        "room_resource": msu_program_diagnostics(session, inputs)["room_resource"],
    }


def room_metadata_probe_step(room: int, pending_room: int, stage: int,
                            target: int, remaining: int) -> int:
    """Use bounded batching until the target reaches its publication seam."""
    if remaining <= 0:
        return 0
    if room == target or (pending_room == target and stage >= 5):
        return 1
    return min(16, remaining)


def room_metadata_probe_is_published(room: int, target: int, valid: int,
                                    active_record_room: int) -> bool:
    """Require both lifecycle selection and active-record identity to agree.

    The SCUMM room byte can change while a request is still in its preflight
    or commit sequence. A diagnostic request is not accepted until the active
    SC5LIVE record itself identifies the requested room and its native valid
    flag is set.
    """
    return room == target and valid == 1 and active_record_room == target


def stats(session: Any) -> dict[str, int]:
    # Binding-event counters are live. Pinned census counters are snapshots
    # written only by RefreshDiagnostics and are reported separately.
    raw = session.read_memory("snesMemory", RESIDENT_STATS, 20)
    offsets = {
        "current_resident": 0, "peak_resident": 2,
        "binds": 8, "reuses": 10, "bundle_loads": 12,
        "bundle_releases": 14, "dynamic_global_lookups": 16,
        "exhaustions": 18,
    }
    result = {name: u16(raw, offset) for name, offset in offsets.items()}
    result["stale_rejections"] = u16(session.read_memory("snesMemory", 0x7E8F9C, 2))
    return result


def owned_pin_census(session: Any) -> dict[str, int]:
    """Return last explicit/bundle snapshot; C4 owners are sampled separately."""
    raw = session.read_memory("snesMemory", 0x7E8F83, 4)
    return {"current_owned_pins": u16(raw), "peak_owned_pins": u16(raw, 2)}


def msu_program_diagnostics(session: Any, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture provider and bytecode-cache state for native streaming evidence."""
    provider = session.read_memory("snesMemory", 0x7E2F00, 0x48)
    cache = session.read_memory("snesMemory", 0x7E2F48, 0x5A)
    cache_page2 = session.read_memory("snesMemory", 0x7E2EC3, 10)
    c19 = session.read_memory("snesMemory", 0x7E2FA2, 14)
    room = session.read_memory("snesMemory", 0x7E2FEB, 0x15)
    live_base = 0x401400 if inputs is None else live_room_control_base(inputs)
    live = session.read_memory("snesMemory", live_base, 0x0C)
    return {
        "provider_status": provider[0],
        "provider_error": provider[1],
        "seek_count": u16(provider, 0x2B),
        "bytes_read": int.from_bytes(provider[0x2D:0x31], "little"),
        "active_request_offset": int.from_bytes(provider[0x04:0x08], "little"),
        "active_request_length": int.from_bytes(provider[0x08:0x0C], "little"),
        "destination_address": int.from_bytes(provider[0x0C:0x0F], "little"),
        "destination_capacity": u16(session.read_memory("snesMemory", 0x7E2F0F, 2)),
        "expected_crc32": int.from_bytes(session.read_memory("snesMemory", 0x7E2F11, 4), "little"),
        "active_request_remaining": int.from_bytes(provider[0x15:0x19], "little"),
        "active_destination_index": u16(provider, 0x19),
        "read_count": u16(provider, 0x31),
        "timeout_count": u16(provider, 0x33),
        "range_reject_count": u16(provider, 0x35),
        "integrity_verifications": u16(provider, 0x37),
        "cache_slots": [
            {
                "state": cache[0],
                "program_unit_id": u16(cache, 2),
                "size": u16(cache, 6),
                "pins": cache[10],
                "generation": u16(cache, 12),
                "logical_page_start": u16(
                    session.read_memory("snesMemory", 0x7E2EB6, 2), 0,
                ),
            },
            {
                "state": cache[1],
                "program_unit_id": u16(cache, 4),
                "size": u16(cache, 8),
                "pins": cache[11],
                "generation": u16(cache, 14),
                "logical_page_start": u16(
                    session.read_memory("snesMemory", 0x7E2EB8, 2), 0,
                ),
            },
            {
                "state": cache_page2[0],
                "program_unit_id": u16(cache_page2, 1),
                "size": u16(cache_page2, 3),
                "pins": cache_page2[5],
                "generation": u16(cache_page2, 6),
                "logical_page_start": u16(cache_page2, 8),
                "address": 0x7F1000,
            },
        ],
        # Low seven bits are transient execution pins; bit 7 is an independent
        # checked-page completion hold owned by a WAIT_RESOURCE activation.
        # No interpreter code pointer survives a scheduler return, so at a
        # stable host-frame boundary with execution_depth == 0 these counts
        # must be zero even when yielded C4 activations remain live.
        "transient_execution_pins": [cache[10] & 0x7F,
                                     cache[11] & 0x7F,
                                     cache_page2[5] & 0x7F],
        "cache_current_bytes": u16(cache, 0x18),
        "cache_peak_bytes": u16(cache, 0x1A),
        "cache_loads": u16(cache, 0x1C),
        "cache_evictions": u16(cache, 0x1E),
        "cache_failures": u16(cache, 0x20),
        "cache_request_id": u16(cache, 0x10),
        "cache_request_slot": cache[0x12],
        "cache_completion_waiters": [
            {
                "selector": session.read_memory("snesMemory", 0x7E2ED0 + page * 2, 1)[0],
                "c4_slot": session.read_memory("snesMemory", 0x7E2ED1 + page * 2, 1)[0],
                "held": bool(session.read_memory("snesMemory", pin_address, 1)[0] & 0x80),
            }
            for page, pin_address in enumerate((0x7E2F52, 0x7E2F53, 0x7E2EC8))
        ],
        "active_cache_slot": cache[0x13],
        "active_program_unit_id": u16(cache, 0x14),
        "active_generation": u16(cache, 0x16),
        "active_selector": cache[0x27],
        "resolver_adapter_calls": u16(session.read_memory("snesMemory", 0x7E2FE4, 2)),
        "last_adapter_selector": session.read_memory("snesMemory", 0x7E2FE6, 1)[0],
        "execution_depth": session.read_memory("snesMemory", 0x7E2FB0, 1)[0],
        "cache_window_prefixes": [
            list(session.read_memory("snesMemory", 0x7E1000, 24)),
            list(session.read_memory("snesMemory", 0x7E1800, 24)),
            list(session.read_memory("snesMemory", 0x7F1000, 24)),
        ],
        "c19_failure": {
            "stage": c19[0],
            "opcode": c19[1],
            "selector": c19[2],
            "pc": u16(c19, 3),
            "slot": c19[5],
        },
        "storage_process_turns": u16(c19, 6),
        "storage_process_last_status": c19[8],
        "kernel_frame_entries": u16(c19, 9),
        "engine_frame_returns": u16(c19, 11),
        "kernel_frame_stage": c19[13],
        "room_resource": {
            "state": room[0],
            "room": room[1],
            "requests": u16(room, 2),
            "validated": u16(room, 4),
            "failures": u16(room, 6),
            "max_fetch_latency_frames": u16(room, 8),
            "last_length": u16(room, 12),
            "script_count": u16(room, 14),
            "room_data_offset": u16(room, 16),
            "staging_cache_slot": room[20],
        },
        "max_checked_fetch_latency_frames": u16(room, 8),
        "live_room": {
            "stage": live[0], "valid": live[1], "length": u16(live, 2),
            "width": u16(live, 4), "height": u16(live, 6),
            "pitch": u16(live, 8), "copy_index": u16(live, 10),
        },
    }


def external_live_room_payloads(inputs: dict[str, Any], room: int) -> dict[str, Any]:
    """Read and decode the compiler-owned SC5LIVE/SC5VIS records from SAMEPKG."""
    storage = inputs.get("program_storage") or {}
    live_row = next((row for row in storage.get("live_room_records", [])
                     if int(row["room"]) == room), None)
    route_row = next((row for row in storage.get("live_route_records", [])
                      if int(row["room"]) == room), None)
    visual_row = next((row for row in storage.get("visual_records", [])
                       if int(row["room"]) == room), None)
    if live_row is None or route_row is None or visual_row is None:
        raise RuntimeError(
            f"compiler manifest has no live room/route/visual records for room {room}"
        )
    package_path = Path(inputs["program_storage_package"]["path"])
    package = package_path.read_bytes()
    from same.engines.scumm_v5.live_room_resources import decode_live_room
    from same.engines.scumm_v5.room_visual import decode_room_visual

    live_offset = int(live_row["package_offset"])
    live_bytes = package[live_offset:live_offset + int(live_row["length"])]
    require(len(live_bytes) == int(live_row["length"]),
            f"room {room} SC5LIVE record exceeds the package boundary")
    require(hashlib.sha256(live_bytes).hexdigest() == live_row["sha256"],
            f"room {room} SC5LIVE record differs from its compiler manifest hash")
    route_offset = int(route_row["package_offset"])
    route_bytes = package[route_offset:route_offset + int(route_row["length"])]
    require(len(route_bytes) == int(route_row["length"])
            and hashlib.sha256(route_bytes).hexdigest() == route_row["sha256"],
            f"room {room} SC5ROUT record differs from its compiler manifest identity")
    live = decode_live_room(live_bytes, expected_room=room, route_data=route_bytes)
    visual_offset = int(visual_row["package_offset"])
    visual_bytes = package[visual_offset:visual_offset + int(visual_row["length"])]
    require(len(visual_bytes) == int(visual_row["length"]),
            f"room {room} SC5VIS record exceeds the package boundary")
    require(hashlib.sha256(visual_bytes).hexdigest() == visual_row["sha256"],
            f"room {room} SC5VIS record differs from its compiler manifest hash")
    visual = decode_room_visual(visual_bytes, expected_room=room)
    rom_bytes = Path(inputs["rom_path"]).read_bytes()
    require(live_bytes not in rom_bytes,
            f"room {room} live SC5LIVE payload is also embedded in the ROM")
    require(visual_bytes not in rom_bytes,
            f"room {room} SC5VIS payload is also embedded in the ROM")
    return {"live": live, "live_bytes": live_bytes,
            "route_bytes": route_bytes, "route_row": route_row,
            "visual": visual, "visual_bytes": visual_bytes,
            "visual_row": visual_row}


def check_live_room_native(session: Any, inputs: dict[str, Any], room: int) -> dict[str, Any]:
    expected = external_live_room_payloads(inputs, room)
    control = msu_program_diagnostics(session, inputs)["live_room"]
    # READ_LENGTH is shared by the staged metadata, palette, and pixel fetches;
    # after the visual reads it describes the last 57-KiB surface, not the
    # retained SC5LIVE record. Its canonical committed size is in the header.
    active_header = bytes(session.read_memory(
        "snesMemory", LIVE_ROOM_ACTIVE_BASE, 82,
    ))
    active_length = int.from_bytes(active_header[48:50], "little")
    require(82 <= active_length <= LIVE_ROOM_ACTIVE_CAPACITY,
            f"room {room} active SC5LIVE header has invalid size {active_length}")
    active = active_header + bytes(
        session.read_memory("snesMemory", LIVE_ROOM_ACTIVE_BASE + 82,
                            active_length - 82)
    )
    pixels = bytes(session.read_memory("snesMemory", 0x402000, 256 * 224))
    carrier_path = Path(inputs["rom_path"]).with_suffix(".carrier.json")
    require(carrier_path.is_file(),
            f"room {room} carrier layout manifest is missing: {carrier_path}")
    carrier = json.loads(carrier_path.read_text(encoding="utf-8"))
    reserved = carrier["layout"]["backend_reserved"]
    high, low = str(reserved["address"]).split(":", 1)
    palette_stage_offset = ((int(high, 16) << 16) | int(low, 16)) + int(
        reserved["allocations"]["live_room_palette_stage"]["offset"]
    )
    palette_length = int(
        reserved["allocations"]["live_room_palette_stage"]["bytes"]
    )
    require(palette_length == len(expected["visual"].palette),
            f"room {room} carrier palette stage has unexpected size {palette_length}")
    # The staging allocation is transaction scratch and may be reused after
    # publication. Validate the palette the video backend actually owns. Read
    # its exact address from this ROM's assembler listing so the check remains
    # bound to the build under test.
    listing_path = Path(inputs["rom_path"]).with_suffix(".lst")
    palette_constants = []
    for line in listing_path.read_text(encoding="utf-8").splitlines():
        prefix = "; SAME_MODE3_LIVE_PALETTE = $"
        if line.startswith(prefix) and line.endswith("(Constant)"):
            palette_constants.append(int(line[len(prefix):].split()[0], 16))
    require(len(palette_constants) == 1,
            f"ROM listing must define exactly one SAME_MODE3_LIVE_PALETTE constant: "
            f"{listing_path}")
    palette_offset = palette_constants[0]
    palette = bytes(session.read_memory("snesMemory", palette_offset, palette_length))
    # The live SC5LIVE flags must reach the existing movement subsystem, not
    # merely remain present in the retained metadata buffer.  Matrix_LoadActiveRoom
    # installs these exact bytes into the engine's active walkbox table.
    expected_box_flags = expected["live"].payload[
        expected["live"].offsets["flags"]:
        expected["live"].offsets["flags"] + expected["live"].box_count
    ]
    active_box_count = session.read_memory("snesMemory", 0x7FFA40, 1)[0]
    active_box_flags = bytes(session.read_memory(
        "snesMemory", 0x7FFA41, expected["live"].box_count,
    ))
    matrix_mutation_count = session.read_memory("snesMemory", 0x7FFB43, 1)[0]
    matrix_trace_count = min(
        session.read_memory("snesMemory", 0x7FFB44, 1)[0], 4,
    )
    raw_matrix_trace = bytes(session.read_memory(
        "snesMemory", 0x7FFB45, matrix_trace_count * 8,
    ))
    matrix_trace = [
        {
            "subop": raw_matrix_trace[offset],
            "box": raw_matrix_trace[offset + 1],
            "flags": raw_matrix_trace[offset + 2],
            "source_pc_before": u16(raw_matrix_trace, offset + 3),
            "source_pc_after": u16(raw_matrix_trace, offset + 5),
        }
        for offset in range(0, len(raw_matrix_trace), 8)
    ]
    # The staging transaction is reusable and may already have been reset for
    # the following request by the time the route sampler notices this room
    # value.  The published active record, exact external pixels, and palette
    # are the commit evidence; a transient stage/valid byte is not a durable
    # room identity.
    require(active[12] == room,
            f"room {room} active SC5LIVE identity is {active[12]}")
    if active != expected["live_bytes"]:
        differences = [
            {"offset": index, "active": active[index], "expected": expected["live_bytes"][index]}
            for index in range(min(len(active), len(expected["live_bytes"])))
            if active[index] != expected["live_bytes"][index]
        ][:12]
        require(False,
                f"room {room} active SC5LIVE bytes do not match the external checked record: "
                f"active={hashlib.sha256(active).hexdigest()} "
                f"expected={hashlib.sha256(expected['live_bytes']).hexdigest()} "
                f"first_differences={differences}")
    if pixels != expected["visual"].pixels:
        differences = [
            {"offset": index, "surface": pixels[index], "expected": expected["visual"].pixels[index]}
            for index in range(min(len(pixels), len(expected["visual"].pixels)))
            if pixels[index] != expected["visual"].pixels[index]
        ][:12]
        require(False,
                f"room {room} live mode-3 surface pixels differ from SC5VIS source: "
                f"surface={hashlib.sha256(pixels).hexdigest()} "
                f"expected={expected['visual'].decoded_pixels_sha256} "
                f"first_differences={differences}")
    palette_differences = [
            {"offset": index, "active": palette[index],
             "expected": expected["visual"].palette[index]}
            for index in range(len(palette))
            if palette[index] != expected["visual"].palette[index]
        ]
    require(active_box_count == expected["live"].box_count,
            f"room {room} active walkbox count {active_box_count} differs from "
            f"SC5LIVE {expected['live'].box_count}")
    route_valid = session.read_memory("snesMemory", 0x7F34FA, 1)[0]
    installed_routes = read_active_route_matrix(
        session, expected["live"].box_count,
    )
    expected_routes = bytes(expected["live"].route_matrix)
    route_differences = [
        {"offset": index, "installed": installed_routes[index],
         "expected": expected_routes[index]}
        for index in range(min(len(installed_routes), len(expected_routes)))
        if installed_routes[index] != expected_routes[index]
    ][:24]
    require(route_valid == 1 and installed_routes == expected_routes,
            f"room {room} external SC5ROUT did not become the active movement matrix: "
            f"valid={route_valid}, installed_sha256="
            f"{hashlib.sha256(installed_routes).hexdigest()}, expected_sha256="
            f"{hashlib.sha256(expected_routes).hexdigest()}, "
            f"first_differences={route_differences}, "
            f"current_room={session.read_memory('snesMemory', ROOM, 1)[0]}, "
            f"active_room={session.read_memory('snesMemory', 0x7FF2BF, 1)[0]}, "
            f"request_room={read_live_room_control(session, inputs, 0x0D)[0x0C]}")
    name_samples = []
    for index in sorted({0, len(expected["live"].object_names) // 2,
                         max(0, len(expected["live"].object_names) - 1)}):
        if index >= len(expected["live"].object_names):
            continue
        object_id, source_name = expected["live"].object_names[index]
        name_length = session.read_memory(
            "snesMemory", OBJECT_NAME_LENGTH + object_id, 1,
        )[0]
        installed_name = bytes(session.read_memory(
            "snesMemory", OBJECT_NAMES + object_id * OBJECT_NAME_STRIDE,
            min(name_length, OBJECT_NAME_STRIDE),
        ))
        require(name_length == len(source_name) and installed_name == source_name,
                f"room {room} object name {object_id} was not installed from SC5LIVE: "
                f"length={name_length}/{len(source_name)}, bytes={installed_name!r}/"
                f"{source_name!r}")
        name_samples.append({
            "object_id": object_id, "length": name_length,
            "name_sha256": hashlib.sha256(installed_name).hexdigest(),
            "matches_sc5live": True,
        })
    walkbox_flag_audit = audit_runtime_walkbox_flags(
        expected_box_flags, active_box_flags,
        successful_matrix_mutations=matrix_mutation_count,
        matrix_trace=matrix_trace,
    )

    # Resource publication is checked at the transition boundary. PPU work is
    # intentionally asynchronous, so the route sampler must not advance the
    # emulator from this callback; the final settled surface is checked by the
    # bounded presentation drain after the route has finished.
    pcm_track = int(inputs["build_identity"].get("explicit_environment", {}).get(
        "SAME_MSU1_LIVE_ROOM_PCM_TRACK", "0",
    ) or 0)
    audio_state = {
        "selected_track": u16(session.read_memory("snesMemory", 0x7E2F41, 2)),
        "play_flags": u16(session.read_memory("snesMemory", 0x7E2F43, 2)),
        "last_status": session.read_memory("snesMemory", 0x7E2F45, 1)[0],
        "hardware_status": session.read_memory("snesMemory", 0x002000, 1)[0],
    }
    if pcm_track:
        require(audio_state["selected_track"] == pcm_track
                and (audio_state["play_flags"] & 1) != 0,
                f"room {room} resource read was not concurrent with configured PCM track: "
                f"track={audio_state}")
        require((audio_state["last_status"] & 0x08) == 0
                and (audio_state["hardware_status"] & 0x08) == 0,
                f"room {room} concurrent MSU PCM reported track error: {audio_state}")
    return {
        "room": room,
        "resource_stage_at_observation": control["stage"],
        "resource_valid_at_observation": control["valid"],
        "live_record_bytes": len(active),
        "live_record_sha256": hashlib.sha256(active).hexdigest(),
        "live_record_matches_package": True,
        "object_count": expected["live"].object_count,
        "object_name_samples": name_samples,
        "verb_count": expected["live"].verb_count,
        "local_count": expected["live"].local_count,
        "walkbox_count": expected["live"].box_count,
        "active_walkbox_count": active_box_count,
        "movement_matrix_bytes": len(installed_routes),
        "movement_matrix_sha256": hashlib.sha256(installed_routes).hexdigest(),
        "movement_matrix_matches_sc5route": True,
        "active_walkbox_flags_hex": active_box_flags.hex(),
        "walkbox_flag_audit": walkbox_flag_audit,
        "surface_base": VIDEO_SURFACE_BASE,
        "surface_bytes": len(pixels),
        "surface_sha256": hashlib.sha256(pixels).hexdigest(),
        "surface_matches_sc5vis": True,
        "ppu_verified_after_settlement": False,
        "pcm_during_room_load": audio_state if pcm_track else None,
        "palette_bytes": len(palette),
        "palette_stage_address": f"${palette_stage_offset:06X}",
        "active_palette_address": f"${palette_offset:06X}",
        "palette_stage": "transaction scratch; not inspected after publication",
        "palette_sha256": hashlib.sha256(palette).hexdigest(),
        "palette_matches_sc5vis": not palette_differences,
        "palette_difference_count": len(palette_differences),
        "palette_differences": palette_differences[:32],
    }


def check_live_room_ppu(session: Any, inputs: dict[str, Any], room: int,
                        target_generation: int, *, frames_advanced: int = 0,
                        expected: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compare committed PPU pixels/palette with this room's checked SC5VIS."""
    if expected is None:
        expected = external_live_room_payloads(inputs, room)
    carrier_path = Path(inputs["rom_path"]).with_suffix(".carrier.json")
    carrier_layout = json.loads(carrier_path.read_text(encoding="utf-8"))["layout"]

    def layout_address(key: str) -> int:
        high, low = str(carrier_layout[key]["address"]).split(":", 1)
        return (int(high, 16) << 16) | int(low, 16)

    tile_shadow_base = layout_address("tile_shadow")
    cgram_shadow_base = layout_address("cgram_shadow")
    from same.snes_surface import (
        build_static_tilemap, decode_snes_8bpp_tile, encode_cgram,
        encode_surface_tiles,
    )
    from same.video import IndexedSurface
    expected_palette = [
        tuple(expected["visual"].palette[index:index + 3])
        for index in range(0, len(expected["visual"].palette), 3)
    ]
    reference_surface = IndexedSurface.wrap(
        256, 224, 256, expected["visual"].pixels, palette=expected_palette,
    )
    expected_tiles = encode_surface_tiles(reference_surface)
    expected_cgram = encode_cgram(expected_palette)
    active_surface = bytes(session.read_memory("snesMemory", VIDEO_SURFACE_BASE,
                                               256 * 224))
    vram = bytes(session.read_memory("snesVideoRam", 0, 0x10000))
    cgram = bytes(session.read_memory("snesCgRam", 0, 0x0200))
    active_palette_address = inputs["rom_symbols"]["SAME_MODE3_LIVE_PALETTE"]
    active_palette_bytes = bytes(session.read_memory(
        "snesMemory", active_palette_address, 256 * 3,
    ))
    palette_presence = bytes(session.read_memory(
        "snesMemory", inputs["rom_symbols"]["SAME_SCUMM_C10_PALETTE_PRESENT"], 32,
    ))
    scumm_palette_rgb = bytes(session.read_memory(
        "snesMemory", inputs["rom_symbols"]["SAME_SCUMM_C10_PALETTE_RGB"], 256 * 3,
    ))
    expected_effective_palette = bytearray(expected["visual"].palette)
    palette_overrides = []
    for color_index in range(256):
        if palette_presence[color_index >> 3] & (1 << (color_index & 7)):
            start = color_index * 3
            rgb = scumm_palette_rgb[start:start + 3]
            expected_effective_palette[start:start + 3] = rgb
            palette_overrides.append({"index": color_index, "rgb": list(rgb)})
    expected_effective_cgram = encode_cgram([
        tuple(expected_effective_palette[index:index + 3])
        for index in range(0, len(expected_effective_palette), 3)
    ])
    cgram_shadow = bytes(session.read_memory("snesMemory", cgram_shadow_base, 512))
    actual_palette_cgram = encode_cgram([
        tuple(active_palette_bytes[index:index + 3])
        for index in range(0, len(active_palette_bytes), 3)
    ])
    # SCUMM's compositor may have drawn actors or foreground content over the
    # room surface by the time the route reaches this observation. Discover
    # exact background tiles by comparing the full PPU character set, then
    # require a common set of those same tile indices across all room
    # checkpoints. This proves room pixels reached VRAM without assuming a
    # particular screen corner is unobscured by the live compositor.
    sample_indices = (0, 31, 864, 895)
    sampled_tiles = []
    for tile_index in sample_indices:
        start = tile_index * 64
        expected_tile = expected_tiles[start:start + 64]
        actual_tile = vram[start:start + 64]
        sampled_tiles.append({
            "index": tile_index,
            "sha256": hashlib.sha256(actual_tile).hexdigest(),
            "matches_sc5vis": actual_tile == expected_tile,
        })
    matching_tile_indices = [
        index for index in range(896)
        if vram[index * 64:(index + 1) * 64]
        == expected_tiles[index * 64:(index + 1) * 64]
    ]
    matching_set = set(matching_tile_indices)
    active_surface_view = IndexedSurface.wrap(
        256, 224, 256, active_surface, palette=expected_palette,
    )
    active_surface_tiles = encode_surface_tiles(active_surface_view)
    mismatched_tiles = []
    for index in range(896):
        if index in matching_set:
            continue
        start = index * 64
        expected_tile = expected_tiles[start:start + 64]
        actual_tile = vram[start:start + 64]
        tile_x, tile_y = index % 32, index // 32
        expected_pixels = decode_snes_8bpp_tile(expected_tile)
        actual_pixels = decode_snes_8bpp_tile(actual_tile)
        source_pixels = [
            list(active_surface[(tile_y * 8 + row) * 256 + tile_x * 8:
                                (tile_y * 8 + row) * 256 + tile_x * 8 + 8])
            for row in range(8)
        ]
        mismatched_tiles.append({
            "index": index,
            "tile_xy": [tile_x, tile_y],
            "pixel_xy": [tile_x * 8, tile_y * 8],
            "actual_sha256": hashlib.sha256(actual_tile).hexdigest(),
            "expected_sha256": hashlib.sha256(expected_tile).hexdigest(),
            "actual_equals_active_surface_encoding": (
                actual_tile == active_surface_tiles[start:start + 64]
            ),
            "tile_shadow_equals_expected": (
                bytes(session.read_memory(
                    "snesMemory", tile_shadow_base + start, 64,
                )) == expected_tile
            ),
            "tile_shadow_sha256": hashlib.sha256(bytes(session.read_memory(
                "snesMemory", tile_shadow_base + start, 64,
            ))).hexdigest(),
            "active_surface_tile_equals_sc5vis": (
                source_pixels == expected_pixels
            ),
            "differing_pixels": sum(
                actual_pixels[y][x] != expected_pixels[y][x]
                for y in range(8) for x in range(8)
            ),
            "expected_palette_indices": expected_pixels,
            "actual_palette_indices": actual_pixels,
            "active_surface_palette_indices": source_pixels,
        })
    require(matching_tile_indices,
            f"room {room} PPU contains no exact SC5VIS character tiles: "
            f"active_surface_matches_sc5vis={active_surface == expected['visual'].pixels}, "
                f"live_room={live_room_presentation_diagnostics(session, inputs)['live_room']}")
    expected_tilemap = build_static_tilemap()
    tilemap_differences = [
        {"offset": index, "actual": vram[0xE000 + index],
         "expected": expected_tilemap[index]}
        for index in range(len(expected_tilemap))
        if vram[0xE000 + index] != expected_tilemap[index]
    ]
    require(not tilemap_differences,
            f"room {room} PPU tilemap differs from the live surface backend: "
            f"differences={tilemap_differences[:16]}")
    cgram_differences = [
        {"color": index // 2, "byte": index % 2,
         "actual": cgram[index], "expected": expected_effective_cgram[index]}
        for index in range(len(expected_cgram))
        if cgram[index] != expected_effective_cgram[index]
    ]
    active_palette_differences = [
        {"offset": index, "active": active_palette_bytes[index],
         "expected": expected_effective_palette[index]}
        for index in range(len(expected_effective_palette))
        if active_palette_bytes[index] != expected_effective_palette[index]
    ]
    cgram_shadow_differences = [
        {"offset": index, "shadow": cgram_shadow[index],
         "expected": expected_effective_cgram[index]}
        for index in range(len(expected_effective_cgram))
        if cgram_shadow[index] != expected_effective_cgram[index]
    ]
    require(not active_palette_differences and not cgram_differences
            and not cgram_shadow_differences and cgram == actual_palette_cgram,
            f"room {room} active SCUMM palette/CGRAM is not the exact SC5VIS plus "
            f"recorded SCUMM override realization: "
            f"differences={cgram_differences[:32]}, "
            f"active_palette_differs_from_sc5vis="
            f"{active_palette_bytes != expected['visual'].palette}, "
            f"scumm_palette_overrides={palette_overrides}, "
            f"active_palette_unexplained_differences={active_palette_differences[:32]}, "
            f"palette_shadow_differences={cgram_shadow_differences[:16]}, "
            f"matching_tiles={len(matching_tile_indices)}, "
            f"mismatched_tiles={[{key: tile[key] for key in ('index', 'actual_sha256', 'expected_sha256', 'tile_shadow_equals_expected', 'tile_shadow_sha256')} for tile in mismatched_tiles]}")
    return {
        "room": room,
        "generation": target_generation,
        "frames_drained_after_route": frames_advanced,
        "tiles_sha256": hashlib.sha256(vram[:0xE000]).hexdigest(),
        "unoccluded_background_tiles": sampled_tiles,
        "matching_tile_count": len(matching_tile_indices),
        "matching_tile_indices": matching_tile_indices,
        "mismatched_background_tiles": mismatched_tiles,
        "active_surface_matches_sc5vis": active_surface == expected["visual"].pixels,
        "matching_tile_sha256": {
            str(index): hashlib.sha256(
                vram[index * 64:(index + 1) * 64]
            ).hexdigest()
            for index in matching_tile_indices
        },
        "background_sample_sha256": hashlib.sha256(
            b"".join(vram[index * 64:(index + 1) * 64]
                     for index in matching_tile_indices)
        ).hexdigest(),
        "tilemap_sha256": hashlib.sha256(vram[0xE000:0xE800]).hexdigest(),
        "cgram_sha256": hashlib.sha256(cgram).hexdigest(),
        "cgram_matches_active_palette": cgram == actual_palette_cgram,
        "cgram_shadow_matches_active_palette": cgram_shadow == actual_palette_cgram,
        "active_palette_matches_sc5vis": active_palette_bytes == expected["visual"].palette,
        "active_palette_sha256": hashlib.sha256(active_palette_bytes).hexdigest(),
        "active_palette_overrides": palette_overrides,
        "active_palette_differences_from_sc5vis": [
            {"offset": index, "active": active_palette_bytes[index],
             "sc5vis": expected["visual"].palette[index]}
            for index in range(len(active_palette_bytes))
            if active_palette_bytes[index] != expected["visual"].palette[index]
        ],
        "active_palette_matches_scumm_semantic_palette": not active_palette_differences,
        "background_samples_match_sc5vis_realization": True,
        "cgram_matches_sc5vis_realization": True,
    }


def live_room_ppu_status(session: Any, inputs: dict[str, Any]) -> dict[str, int]:
    """Read the compact presentation state used to schedule exact PPU checks."""
    symbols = inputs["rom_symbols"]
    control_base = symbols["SAME_BWRAM_BACKEND_BASE"]
    return {
        "committed_generation": u16(session.read_memory(
            "snesMemory", control_base + 0x10, 2,
        )),
        "state": session.read_memory(
            "snesMemory", symbols["SAME_MODE3_CONTROL_STATE"], 1,
        )[0],
        "locked": session.read_memory(
            "snesMemory", symbols["SAME_MODE3_CONTROL_SURFACE_LOCKED"], 1,
        )[0],
        "committed_generation_high": u16(session.read_memory(
            "snesMemory", symbols["SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI"], 2,
        )),
    }


def live_room_presentation_diagnostics(session: Any, inputs: dict[str, Any]) -> dict[str, Any]:
    symbols = inputs["rom_symbols"]
    surface = bytes(session.read_memory(
        "snesMemory", symbols["SAME_VIDEO_SURFACE_STATE"], 0x2C,
    ))
    video = bytes(session.read_memory("snesMemory", 0x7E5E90, 0x46))
    live = bytes(session.read_memory(
        "snesMemory", symbols["SAME_SCUMM_LIVE_ROOM_CONTROL"], 0x22,
    ))
    return {
        "mode3": {
            "control": list(session.read_memory(
                "snesMemory", symbols["SAME_BWRAM_BACKEND_BASE"], 0x40,
            )),
            "work": list(session.read_memory("snesMemory", 0x41E750, 0x30)),
            "event_count": u16(session.read_memory("snesMemory", 0x7E2004, 2)),
            "dma_pending": u16(session.read_memory("snesMemory", 0x7E223C, 2)),
            "dma_committed": u16(session.read_memory("snesMemory", 0x7E223E, 2)),
        },
        "surface": {
            "room": surface[0], "room_generation": u16(surface, 2),
            "status": surface[4], "source_x": u16(surface, 0x0C),
            "next_generation": u16(surface, 0x1C),
            "presented_room": surface[0x20],
            "presented_generation": u16(surface, 0x22),
            "presented_source_x": u16(surface, 0x24),
            "pending_visual": surface[0x26], "pending_room": surface[0x27],
            "pending_room_generation": u16(surface, 0x28),
        },
        "video": {
            "room_installs": u16(video, 0x00),
            "compose_entries": u16(video, 0x04),
            "compose_canwrite_failures": u16(video, 0x06),
            "compose_status": video[0x08],
            "compose_push_failure": video[0x09],
            "compose_exits": u16(video, 0x0A),
            "push_entries": u16(video, 0x0C),
            "push_event_before": u16(video, 0x0E),
            "push_generation": u16(video, 0x10),
            "push_fail_stage": video[0x12],
            "push_event_after": u16(video, 0x13),
            "present_handles": u16(video, 0x1C),
            "service_calls": u16(video, 0x1E),
            "backend_steps": u16(video, 0x2C),
            "convert_remaining": u16(video, 0x2E),
            "backend_stage": video[0x30],
        },
        "live_room": {
            "stage": live[0], "valid": live[1],
            "requested_room": live[0x0C], "error": live[0x1F],
        },
    }


def live_room_ppu_generation_ready(session: Any, inputs: dict[str, Any],
                                  target_generation: int) -> bool:
    """Return true when presentation is idle; the PPU bytes are authoritative.

    A room transition can capture the surface's next-generation counter before
    its deferred update is enqueued, and later room updates can supersede that
    ticket. Exact generation equality therefore misses valid presentation
    completion. Callers still compare the entire PPU realization with SC5VIS,
    so idle state is only a sampling gate, not acceptance by itself.
    """
    del target_generation  # retained in the API/report as transition provenance
    status = live_room_ppu_status(session, inputs)
    return status["committed_generation_high"] == 0 \
        and status["state"] == 1 and status["locked"] == 0


def drain_and_check_live_room_ppu(session: Any, inputs: dict[str, Any], room: int,
                                  *, max_frames: int = 4096) -> dict[str, Any]:
    """Drain a final asynchronous presentation without changing route input."""
    target_generation = u16(session.read_memory(
        "snesMemory", inputs["rom_symbols"]["SAME_VIDEO_SURFACE_STATE"] + 0x1C, 2,
    ))
    expected = external_live_room_payloads(inputs, room)
    from same.snes_surface import encode_surface_tiles
    from same.video import IndexedSurface
    palette = [
        tuple(expected["visual"].palette[index:index + 3])
        for index in range(0, len(expected["visual"].palette), 3)
    ]
    expected_surface = IndexedSurface.wrap(
        256, 224, 256, expected["visual"].pixels, palette=palette,
    )
    expected_tiles = encode_surface_tiles(expected_surface)
    initial_vram = bytes(session.read_memory("snesVideoRam", 0, 0x10000))
    initial_surface = bytes(session.read_memory(
        "snesMemory", VIDEO_SURFACE_BASE, 256 * 224,
    ))
    initial_mismatches = []
    for index in range(896):
        start = index * 64
        actual = initial_vram[start:start + 64]
        reference = expected_tiles[start:start + 64]
        if actual != reference:
            initial_mismatches.append({
                "tile": index,
                "xy": [index % 32, index // 32],
                "different_pixels": sum(a != b for a, b in zip(actual, reference)),
                "actual_sha256": hashlib.sha256(actual).hexdigest(),
                "expected_sha256": hashlib.sha256(reference).hexdigest(),
            })
    initial_presentation = {
        "target_generation": target_generation,
        "ppu_status": live_room_ppu_status(session, inputs),
        "matching_background_tiles": 896 - len(initial_mismatches),
        "mismatched_background_tiles": initial_mismatches,
        "active_surface_matches_sc5vis": (
            initial_surface == expected["visual"].pixels
        ),
        "active_surface_sha256": hashlib.sha256(initial_surface).hexdigest(),
        "expected_surface_sha256": hashlib.sha256(
            expected["visual"].pixels
        ).hexdigest(),
    }
    frames_advanced = 0
    last_validation_error: str | None = None
    while frames_advanced < max_frames:
        if live_room_ppu_generation_ready(session, inputs, target_generation):
            try:
                result = check_live_room_ppu(
                    session, inputs, room, target_generation,
                    frames_advanced=frames_advanced, expected=expected,
                )
                result["initial_presentation"] = initial_presentation
                return result
            except RuntimeError as exc:
                # An idle interval can precede a deferred surface publication.
                # Continue bounded frame progression; only exact VRAM/CGRAM
                # equality constitutes successful presentation.
                message = str(exc)
                if message == last_validation_error:
                    raise RuntimeError(
                        f"room {room} live PPU validation remained stable after "
                        f"{frames_advanced} frames: {message}; "
                        f"presentation={live_room_presentation_diagnostics(session, inputs)!r}"
                    ) from exc
                last_validation_error = message
        step = min(32, max_frames - frames_advanced)
        result = _run_exact(session, step)
        require(result["framesAdvanced"] == step and not result.get("timedOut"),
                f"live-room PPU drain did not advance exactly {step} frames: {result}")
        frames_advanced += step
    backend = inputs["rom_symbols"]["SAME_BWRAM_BACKEND_BASE"]
    scan = session.read_memory("snesMemory", backend + 0x20, 0x30)
    state = session.read_memory(
        "snesMemory", inputs["rom_symbols"]["SAME_MODE3_CONTROL_STATE"], 1,
    )[0]
    committed_low = u16(session.read_memory("snesMemory", backend + 0x10, 2))
    committed_high = u16(session.read_memory(
        "snesMemory", inputs["rom_symbols"]["SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI"], 2,
    ))
    locked = session.read_memory(
        "snesMemory", inputs["rom_symbols"]["SAME_MODE3_CONTROL_SURFACE_LOCKED"], 1,
    )[0]
    raise RuntimeError(
        f"room {room} live visual generation {target_generation} did not commit "
        f"within {max_frames} post-route frames: state={state}, "
        f"committed={committed_high:04X}:{committed_low:04X}, locked={locked}, "
        f"mode3_control={scan.hex()}"
    )


def pcm_capture_evidence(path: Path, *, active_start_frame: int,
                         transition_frames: list[int]) -> dict[str, Any]:
    """Summarize MSU PCM continuity without treating intentional sample silence as a failure."""
    with wave.open(str(path), "rb") as capture:
        require(capture.getsampwidth() == 2, "Nexen PCM capture is not 16-bit audio")
        channels = capture.getnchannels()
        sample_rate = capture.getframerate()
        raw = capture.readframes(capture.getnframes())
    frame_bytes = channels * 2
    window_frames = max(1, sample_rate // 50)  # 20 ms
    peaks: list[int] = []
    energy = peak = 0
    samples = len(raw) // 2
    for frame_start in range(0, len(raw), frame_bytes * window_frames):
        block = raw[frame_start:frame_start + frame_bytes * window_frames]
        window_peak = 0
        for offset in range(0, len(block) - 1, 2):
            value = int.from_bytes(block[offset:offset + 2], "little", signed=True)
            magnitude = abs(value)
            energy += value * value
            peak = max(peak, magnitude)
            window_peak = max(window_peak, magnitude)
        peaks.append(window_peak)
    start_window = max(0, int(active_start_frame / 60 * sample_rate / window_frames))
    active_peaks = peaks[start_window:]
    silent = [value <= 8 for value in active_peaks]
    longest_silence = run = 0
    for is_silent in silent:
        run = run + 1 if is_silent else 0
        longest_silence = max(longest_silence, run)
    transition_windows = []
    for frame in transition_frames:
        center = int(frame / 60 * sample_rate / window_frames)
        lo, hi = max(start_window, center - 25), min(len(peaks), center + 50)
        window = peaks[lo:hi]
        transition_windows.append({
            "frame": frame,
            "duration_ms": len(window) * 20,
            "silent_20ms_windows": sum(value <= 8 for value in window),
            "peak": max(window, default=0),
        })
    return {
        "sha256": sha256(path), "channels": channels, "sample_rate": sample_rate,
        "captured_frames": len(raw) // frame_bytes,
        "duration_seconds": round(len(raw) / frame_bytes / sample_rate, 3),
        "active_from_emulator_frame": active_start_frame,
        "active_silent_20ms_windows": sum(silent),
        "active_longest_silence_ms": longest_silence * 20,
        "peak": peak,
        "mean_square": energy // max(1, samples),
        "room_transition_windows": transition_windows,
        "interpretation": (
            "PCM capture is bounded emulator evidence; silence counts are reported, "
            "not classified as read-induced without waveform/source correlation."
        ),
    }


def variables(session: Any, indices: tuple[str | int, ...], *,
              base: int = VARIABLES) -> dict[str, int]:
    raw = session.read_memory("snesMemory", base, (max(indices) + 1) * 2)
    return {str(index): u16(raw, index * 2) for index in indices}


def cpu_sp(session: Any) -> int:
    return int(session.get_cpu_state("Snes")["sp"])


def identity_binding(bindings: list[dict[str, int]], identity_to_id: dict[str, int],
                     identity: str) -> dict[str, int] | None:
    target = identity_to_id[identity]
    return next((row for row in bindings if row["program_unit_id"] == target), None)


def simulator_directory(native_directory: dict[str, Any]) -> ResolverDirectory:
    """Adapt native backend metadata to the existing selector-free simulator."""
    by_id = {int(row["program_unit_id"]): row
             for row in native_directory.get("entries", [])}
    bundles = {
        str(bundle["identity"]): [
            str(by_id[int(program_unit_id)]["identity"])
            for program_unit_id in bundle.get("program_unit_ids", [])
        ]
        for bundle in native_directory.get("bundles", [])
    }
    kinds = {str(row["identity"]): str(row["kind"])
             for row in native_directory.get("entries", [])}
    globals_by_number = {
        int(row["script_number"]): str(
            by_id[int(row["program_unit_id"])]["identity"]
        )
        for row in native_directory.get("global_directory", [])
    }
    return ResolverDirectory.from_units(
        bundles, kinds=kinds, global_script_numbers=globals_by_number,
    )


def simulate_native_route(native_directory: dict[str, Any]) -> dict[str, Any]:
    """Replay the fixture's semantic schedule against the compiler oracle."""
    directory = simulator_directory(native_directory)
    simulator = ResidentBindingSimulator(directory=directory)
    global1 = simulator.begin_global(1, yielded=True, activation_id="G1")
    # Global1 starts and waits for these children before room 1's entry path.
    for number in (2, 3):
        child = simulator.begin_global(
            number, parent_activation_id=global1.activation_id,
        )
        simulator.end_activation(child.activation_id)

    simulator.begin_room("RoomBundle(1)")
    # A streamed title transition remains frame-observable while the first
    # external room record is checked, so compare the first installed bundle
    # as well as later room-to-room transitions.
    transitions = [{
        "room": 1,
        "bindings": simulator_bindings(simulator, native_directory),
    }]
    # The room's ENCD dispatches both verbs through one ObjectProgram carrier.
    for index in range(2):
        activation = simulator.begin_activation(
            "ObjectProgram(room=1,object=70)",
            room_ownership="RoomBundle(1)", activation_id=f"OBJ{index}",
        )
        simulator.end_activation(activation.activation_id)

    # The synthetic boot caller's finite yield window spans the first room
    # transition, then it stops before the second checked room record commits.
    # This models the observed SCUMM schedule instead of treating every global
    # as permanently resident for the full test route.
    simulator.end_activation(global1.activation_id)

    for outgoing, incoming in ((1, 2), (2, 3), (3, 4)):
        simulator.transition_room(
            f"RoomBundle({outgoing})", f"RoomBundle({incoming})",
        )
        if incoming == 4:
            # Room 4 ENCD starts the pressure caller before the native route's
            # first stable room-4 binding sample. Model that lifecycle work
            # before capturing the transition set, not after it.
            simulator.begin_global(4, yielded=True, activation_id="G4")
        transitions.append({
            "room": incoming,
            "bindings": simulator_bindings(simulator, native_directory),
        })

    previous_child = None
    for number in (*range(5, 191), 191, 192):
        child = simulator.begin_global(
            number, parent_activation_id="G4",
        )
        # Native scheduler overlap: the parent can reach the next dynamic
        # resolver call while the prior child's C4 slot still owns its
        # selector. Keep one prior activation live through the next bind.
        if previous_child is not None:
            simulator.end_activation(previous_child.activation_id)
        previous_child = child
    if previous_child is not None:
        simulator.end_activation(previous_child.activation_id)
    simulator.end_activation("G4")

    trace = simulator.trace
    return {
        "room_transition_bindings": transitions,
        "final_bindings": simulator_bindings(simulator, native_directory),
        "peak_resident": simulator.peak_bindings,
        "resident_count": len(simulator.resident_snapshot()["bindings"]),
        "binds": sum(item["event"] == "bind" for item in trace),
        "reuses": sum(item["event"] == "evict" for item in trace),
        "bundle_loads": sum(item["event"] == "bundle_load" for item in trace),
        "bundle_releases": sum(item["event"] == "bundle_release" for item in trace),
        "trace": trace,
    }


def simulator_bindings(simulator: ResidentBindingSimulator,
                       native_directory: dict[str, Any]) -> list[dict[str, int]]:
    id_by_identity = {str(row["identity"]): int(row["program_unit_id"])
                      for row in native_directory.get("entries", [])}
    bindings = []
    for row in simulator.resident_snapshot()["bindings"]:
        bindings.append({
            "program_unit_id": id_by_identity[str(row["program_unit"])],
            "selector": int(str(row["selector"])[1:], 16),
            "generation": int(row["generation"]),
        })
    return sorted(bindings, key=lambda item: item["program_unit_id"])


def native_bindings_for_compare(bindings: list[dict[str, int]]) -> list[dict[str, int]]:
    return sorted(({
        "program_unit_id": int(row["program_unit_id"]),
        "selector": int(row["selector"]),
        "generation": int(row["generation"]),
    } for row in bindings), key=lambda item: item["program_unit_id"])


def run_dynamic_route(args: argparse.Namespace, inputs: dict[str, Any]) -> dict[str, Any]:
    require(inputs["manifest"].get("num_global_scripts") == 254,
            "synthetic route manifest has unexpected v5 global table size")
    require(len(inputs["manifest"].get("global_scripts", [])) == 193,
            "fixture must contain 193 real global bodies")
    require(len(inputs["directory"].get("entries", [])) == 206,
            "fixture selector-unit count changed; update acceptance expectation")
    build_env = inputs["build_identity"].get("explicit_environment", {})
    if build_env.get("SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES") == "1":
        require(build_env.get("SAME_SCUMM_TITLE_START_ROOM") == "0"
                and build_env.get("SAME_SCUMM_TITLE_TARGET_ROOM") == "1",
                "live-room route build must use the generated 0->1 title-start request")
    identity_to_id = inputs["identity_to_id"]
    g1_id = identity_to_id["GlobalProgram(1)"]
    g192_id = identity_to_id["GlobalProgram(192)"]
    large_body_case = inputs["manifest"].get("large_program_body")
    large_body_record = None
    if large_body_case:
        require(large_body_case.get("identity") == "GlobalProgram(2)",
                "large-body fixture must execute GlobalProgram(2)")
        require(inputs["program_storage"] is not None,
                "large-body native acceptance requires MSU ProgramUnit storage")
        large_body_record = next(
            (row for row in inputs["program_storage"]["records"]
             if row["identity"] == "GlobalProgram(2)"), None,
        )
        require(large_body_record is not None
                and int(large_body_record["length"]) > 21002
                and int(large_body_record["page_count"]) >= 11,
                "GlobalProgram(2) is not an 11-page >21 KiB carrier")

    snapshots: list[dict[str, Any]] = []
    room_sequence: list[int] = []
    transition_events: list[dict[str, Any]] = []
    g1_initial: dict[str, int] | None = None
    g192_rebind: dict[str, Any] | None = None
    first_reuse: dict[str, Any] | None = None
    capture_after_room4: int | None = None
    error = 0
    early_slot_samples: list[dict[str, Any]] = []
    room_requests: list[dict[str, int]] = []
    room_resource_events: list[dict[str, int]] = []
    observed_pin_samples: list[dict[str, Any]] = []
    native_binding_events: list[dict[str, Any]] = []
    previous_binding_map: dict[int, dict[str, int]] = {}
    title_input: dict[str, Any] | None = None
    title_debug: dict[str, Any] = {}
    boot_ready_samples: list[dict[str, Any]] = []
    previous_room_resource_state = 0
    brk_capture: dict[str, Any] | None = None
    previous_bytes_read = 0
    observed_peak_cached_bytes = 0
    frames_with_data_progress = 0
    max_data_bytes_per_frame = 0
    data_bytes_per_frame_total = 0
    live_room_observations: list[dict[str, Any]] = []
    live_room_ppu_pending: dict[int, int] = {}
    live_room_ppu_observations: list[dict[str, Any]] = []
    live_room_ppu_expected: dict[int, dict[str, Any]] = {}
    live_room_ppu_last_mismatch: dict[int, str] = {}
    live_room_ppu_sampling: dict[int, dict[str, Any]] = {}
    runtime_error_observations: list[dict[str, Any]] = []
    pcm_track = int(inputs["build_identity"].get("explicit_environment", {}).get(
        "SAME_MSU1_LIVE_ROOM_PCM_TRACK", "0",
    ) or 0)
    pcm_capture_path = args.output.with_suffix(".pcm.wav") if pcm_track else None
    pcm_capture_end_frame = 0
    with _session(args) as session:
        _cold_reset(session)
        if pcm_capture_path is not None:
            session.record_audio(pcm_capture_path)
        # Enable the emulator's bounded instruction trace before the route so
        # a failed checked-body publication can be tied to its exact caller.
        session.trace_log(count=1, cpu_type="Snes")
        _run_exact(session, 10)
        require(session.read_memory("snesMemory", ROOM, 1)[0] == 0,
                "synthetic title route did not begin in room zero")
        # A streamed boot body is intentionally asynchronous. Wait for the
        # generated GlobalProgram(1) binding and checked cache publication
        # before submitting the title START edge; otherwise the fixture would
        # race the storage service rather than test SCUMM input semantics.
        boot_id = identity_to_id["GlobalProgram(1)"]
        boot_wait_limit = 1200 if large_body_case else 120
        for _ in range(boot_wait_limit):
            slots = active_slots(session)
            boot_slot = next((item for item in slots
                              if item["script_number"] == 1), None)
            binding = identity_binding(valid_bindings(session), identity_to_id,
                                       "GlobalProgram(1)")
            storage = msu_program_diagnostics(session, inputs)
            cache_ready = any(
                slot["state"] == 2 and slot["program_unit_id"] == boot_id
                for slot in storage["cache_slots"]
            )
            boot_ready_samples.append({
                "frame": int(session.get_state()["frameCount"]),
                "slot": boot_slot,
                "binding": binding,
                "storage": storage,
            })
            if (boot_slot is not None and boot_slot["status"] == 2
                    and boot_slot["pc"] >= 21
                    and variables(session, (6, 8)) == {"6": 2, "8": 3}
                    and binding is not None and cache_ready):
                break
            _run_exact(session, 1)
        else:
            raise RuntimeError(
                "streamed boot GlobalScript(1) did not become yielded with a "
                f"READY checked body within {boot_wait_limit} frames: "
                f"{boot_ready_samples[-1] if boot_ready_samples else None}"
            )
        room_sequence.append(0)
        start_mask = int(session.BTN_START)
        if args.stop_on_brk or args.stop_on_resource_error:
            # Diagnostic-only route capture. Stop on the precise resolver or
            # resource error write before later lifecycle handling can replace
            # it; normal acceptance retains the exact four-frame controller tap.
            expected_error = 0x10 if args.stop_on_resource_error else 0x21
            error_hook = session.add_write_hook(ERROR, match_value=expected_error)
            session.tool("set_input", {
                "port": 0,
                "buttons": start_mask | int(session.BTN_A),
                "hold": True,
                "frames": 0,
            })
            wait_result = session.run_until(
                max_frames=args.frames, hook_handle=error_hook
            )
            error_events = [
                item["params"]
                for item in session.drain_notifications(timeout=0.05)
                if item.get("method") == "notifications/mesen/hookFired"
                and int(item.get("params", {}).get("handle", -1)) == error_hook
            ]
            session.remove_hook(error_hook)
            session.tool("set_input", {
                "port": 0, "buttons": 0, "hold": True, "frames": 0,
            })
            debug_cpu = session.get_cpu_state("Snes")
            debug_pc = (((int(debug_cpu.get("k", 0)) & 0xFF) << 16)
                        | (int(debug_cpu.get("pc", 0)) & 0xFFFF))
            debug_sp = int(debug_cpu.get("sp", 0)) & 0xFFFF
            brk_capture = {
                "stop_reason": ("first_resource_error_write" if args.stop_on_resource_error
                                else "first_residency_id_error_write"),
                "wait": wait_result,
                "error_events": error_events,
                "cpu": debug_cpu,
                "pc_disassembly": session.disassemble(
                    debug_pc, count=20, cpu_type="Snes"),
                "trace": session.trace_log(count=64, cpu_type="Snes"),
                "stack": list(session.read_memory(
                    "snesMemory", (debug_sp + 1) & 0xFFFF, 18
                )),
                "scumm": {
                    "error": session.read_memory("snesMemory", ERROR, 1)[0],
                    "runtime_room": session.read_memory("snesMemory", ROOM, 1)[0],
                    "pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
                    "last_opcode": session.read_memory("snesMemory", 0x7E2306, 1)[0],
                    "program_select": session.read_memory("snesMemory", 0x7E2362, 1)[0],
                    "active_slots": active_slots(session),
                    "slot0_raw": {
                        "status": session.read_memory("snesMemory", 0x7E2380, 1)[0],
                        "number": session.read_memory("snesMemory", 0x7E2399, 1)[0],
                        "program": session.read_memory("snesMemory", 0x7E23B2, 1)[0],
                        "where": session.read_memory("snesMemory", 0x7E7F46, 1)[0],
                        "pc": u16(session.read_memory("snesMemory", 0x7E23E4, 2)),
                    },
                    "m23a": list(session.read_memory("snesMemory", 0x7FF2BE, 16)),
                    "m23a_active_room": session.read_memory("snesMemory", 0x7FF2BF, 1)[0],
                    "m23a_pending_record": session.read_memory("snesMemory", 0x7FF2C0, 1)[0],
                    "m23a_pending_room": session.read_memory("snesMemory", 0x7FF2C1, 1)[0],
                    "m23a_phase": session.read_memory("snesMemory", 0x7FF2C2, 1)[0],
                    "live_resource_diagnostics": msu_program_diagnostics(session, inputs)["room_resource"],
                    "interpreter": {
                        "program_select": session.read_memory("snesMemory", 0x7E2362, 1)[0],
                        "pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
                        "last_opcode": session.read_memory("snesMemory", 0x7E2306, 1)[0],
                        "error_program": session.read_memory("snesMemory", 0x7E5F22, 1)[0],
                        "error_pc": u16(session.read_memory("snesMemory", 0x7E5F23, 2)),
                        "error_opcode": session.read_memory("snesMemory", 0x7E5F25, 1)[0],
                        "error_slot": session.read_memory("snesMemory", 0x7E5F8D, 1)[0],
                    },
                    "live_control": read_live_room_control(session, inputs),
                    "live_room_header": list(session.read_memory(
                        "snesMemory", LIVE_ROOM_ACTIVE_BASE, 82,
                    )),
                    "live_room_header_cartridge_ram": list(session.read_memory(
                        "snesSaveRam", LIVE_ROOM_ACTIVE_BASE - 0x400000, 82,
                    )),
                    "live_validation_checkpoint": session.read_memory(
                        "snesMemory", 0x4013C1, 1,
                    )[0],
                    "live_bundle_check": u16(session.read_memory(
                        "snesMemory", live_room_control_base(inputs) + 0x3E, 2,
                    )),
                    "live_failed_prefix": list(session.read_memory(
                        "snesMemory", 0x4013B8, 8,
                    )),
                    "msu_destination": list(session.read_memory(
                        "snesMemory", 0x7E2F0C, 3,
                    )),
                    "msu_destination_index": u16(session.read_memory(
                        "snesMemory", 0x7E2F19, 2,
                    )),
                    "msu_dp_destination": list(session.read_memory(
                        "snesMemory", 0x0000D0, 3,
                    )),
                    "live_chunk_mode": session.read_memory(
                        "snesMemory", 0x4013A7, 1,
                    )[0],
                    "live_chunk_index": u16(session.read_memory(
                        "snesMemory", 0x4013A8, 2,
                    )),
                    "bundle_cursor": {
                        "directory_offset": u16(bytes(read_live_room_control(session, inputs)), 0x0E),
                        "index": u16(session.read_memory("snesMemory", 0x7E8FA0, 2)),
                        "remaining": session.read_memory("snesMemory", 0x7E8F9F, 1)[0],
                    },
                    "resolver_request_id": u16(session.read_memory("snesMemory", 0x7E8F7A, 2)),
                    "resolver_bundle_record": session.read_memory("snesMemory", 0x7E8F9E, 1)[0],
                    "resolver_failure": session.read_memory("snesMemory", 0x7E8FAB, 1)[0],
                    "resolver_error_caller": {
                        "pc": u16(session.read_memory("snesMemory", 0x7E8FAD, 2)),
                        "bank": session.read_memory("snesMemory", 0x7E8FAF, 1)[0],
                    },
                    "resident_lookup_failure": {
                        "cause": session.read_memory("snesMemory", 0x7E8FBF, 1)[0],
                        "selector": session.read_memory("snesMemory", 0x7E8FBE, 1)[0],
                        "pool_index": u16(session.read_memory("snesMemory", 0x7E8FBA, 2)),
                        "flags": u16(session.read_memory("snesMemory", 0x7E8FB8, 2)),
                        "program_unit_id": u16(session.read_memory("snesMemory", 0x7E8FBC, 2)),
                    },
                    "resolver": valid_bindings(session),
                },
            }
            title_input = {"diagnostic_interrupted": True, "wait": wait_result}
        else:
            title_input = _press_exact(session, start_mask | int(session.BTN_A))
        title_input["session_button_masks"] = {
            "start": start_mask,
            "a": int(session.BTN_A),
        }
        title_debug = {
            "input_held": u16(session.read_memory("snesMemory", 0x7E2200, 2)),
            "input_pressed": u16(session.read_memory("snesMemory", 0x7E2204, 2)),
            "joy1": u16(session.read_memory("snesMemory", 0x004218, 2)),
            "title_state": list(session.read_memory("snesMemory", 0x7E565C, 4)),
            "room": session.read_memory("snesMemory", ROOM, 1)[0],
            "phase": session.read_memory("snesMemory", 0x7FF2C2, 1)[0],
            "request_count": session.read_memory(
                "snesMemory", M23A_REQUEST_DIAGNOSTICS, 1)[0],
        }
        if brk_capture is not None:
            return {
                "format": "same-scumm-native-resident-route-diagnostic-v1",
                "mode": "dynamic-route-diagnostic",
                **inputs["hashes"],
                "build_git_identity": inputs["build_identity"].get("git"),
                "source": inputs["source"],
                "title_start_input": title_input,
                "title_start_debug": title_debug,
                "capture": brk_capture,
            }
        if args.stop_on_brk and brk_capture is None:
            # Diagnostic-only path: stop at the generic BRK vector before its
            # handler can obscure the originating instruction/stack frame.
            brk_hook = session.add_exec_hook(0x008120)
            error_write_hook = session.add_write_hook(ERROR)
            wait_result = session.run_until(
                max_frames=args.frames, hook_handle=brk_hook
            )
            error_writes = [
                item["params"]
                for item in session.drain_notifications(timeout=0.05)
                if item.get("method") == "notifications/mesen/hookFired"
                and int(item.get("params", {}).get("handle", -1))
                == error_write_hook
            ]
            session.remove_hook(error_write_hook)
            brk_cpu = session.get_cpu_state("Snes")
            brk_sp = int(brk_cpu.get("sp", 0)) & 0xFFFF
            brk_stack = list(session.read_memory(
                "snesMemory", (brk_sp + 1) & 0xFFFF, 12
            ))
            # At the BRK vector, the diagnostic handler has pushed PHP and a
            # 16-bit PHA before the hardware's native interrupt frame. The
            # hook can be serviced a few handler instructions late, so derive
            # that prefix from the sampled handler PC instead of assuming the
            # complete prologue has run.
            handler_pc = int(brk_cpu.get("pc", 0)) & 0xFFFF
            if handler_pc <= 0x8120:
                frame_index = 0
            elif handler_pc <= 0x8123:
                frame_index = 1  # PHP has run; PHA has not.
            else:
                frame_index = 3  # PHP and 16-bit PHA have run.
            return_pc = (brk_stack[frame_index + 1]
                         | (brk_stack[frame_index + 2] << 8))
            return_pbr = brk_stack[frame_index + 3]
            origin_address = (return_pbr << 16) | max(0, return_pc - 8)
            brk_capture = {
                "wait": wait_result,
                "scumm_error_writes": error_writes,
                "cpu": brk_cpu,
                "disassembly": session.disassemble(
                    ((int(brk_cpu.get("k", 0)) & 0xFF) << 16)
                    | (int(brk_cpu.get("pc", 0)) & 0xFFFF),
                    count=16,
                    cpu_type="Snes",
                ),
                "trace": session.trace_log(count=64, cpu_type="Snes"),
                "stack": list(session.read_memory(
                    "snesMemory", (brk_sp + 1) & 0xFFFF, 12
                )),
                "interrupt_return": {"pbr": return_pbr, "pc": return_pc},
                "interrupt_frame_index": frame_index,
                "origin_disassembly": session.disassemble(
                    origin_address, count=20, cpu_type="Snes"
                ),
                "origin_bytes": list(session.read_memory(
                    "snesMemory", origin_address, 24
                )),
                "reset_diagnostics": list(session.read_memory(
                    "snesMemory", 0x7FF46B, 0x80
                )),
                "provider": msu_program_diagnostics(session, inputs),
                "live_control": read_live_room_control(session, inputs),
                "m23a": list(session.read_memory(
                    "snesMemory", 0x7FF2BE, 16
                )),
                "variables": variables(session, (5, 6, 8, 9, 10, 20, 24)),
                "engine_context": {
                    "error": session.read_memory("snesMemory", ERROR, 1)[0],
                    "scumm_pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
                    "last_opcode": session.read_memory("snesMemory", 0x7E2306, 1)[0],
                    "program_select": session.read_memory("snesMemory", 0x7E2362, 1)[0],
                    "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
                    "active_slots": active_slots(session),
                    "msu_active": list(session.read_memory(
                        "snesMemory", 0x7E2F48, 40)),
                    "active_room": session.read_memory("snesMemory", ROOM, 1)[0],
                },
            }
        previous_room = session.read_memory("snesMemory", ROOM, 1)[0]
        previous_request_count = session.read_memory(
            "snesMemory", M23A_REQUEST_DIAGNOSTICS, 1)[0]
        if previous_room != room_sequence[-1]:
            room_sequence.append(previous_room)
        elapsed = 0
        stack_samples: list[dict[str, int]] = []
        while elapsed < args.frames and brk_capture is None:
            before = int(session.get_state()["frameCount"])
            # Pixel acquisition is the only long resource phase in this
            # fixture. Batch debugger calls while retaining the provider's
            # per-logical-frame 64-byte service budget; observe metadata,
            # palette, state transitions, and script execution one frame at
            # a time. This changes harness polling cost, not emulated time.
            live_control = read_live_room_control(session, inputs, 1)[0]
            step = min(64 if live_control == LIVE_ROOM_STAGE_PIXELS else 1,
                       args.frames - elapsed)
            result = session.run_frames(step)
            advanced = int(result.get("framesAdvanced", 0))
            after = int(session.get_state()["frameCount"])
            require(not result.get("timedOut") and advanced == step and after - before == advanced,
                    f"Nexen frame observation was not accounted exactly: {result}; "
                    f"frameCount {before}->{after}")
            elapsed += advanced
            frame = int(session.get_state()["frameCount"])
            room = session.read_memory("snesMemory", ROOM, 1)[0]
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            storage_frame = msu_program_diagnostics(session, inputs)
            room_storage = storage_frame["room_resource"]
            if error:
                runtime_error_observations.append({
                    "frame": frame,
                    "room": room,
                    "error": error,
                    "provider": storage_frame,
                    "live_control": read_live_room_control(session, inputs),
                    "m23a": list(session.read_memory("snesMemory", 0x7FF2BE, 16)),
                    "interpreter": {
                        "program_select": session.read_memory("snesMemory", 0x7E2362, 1)[0],
                        "pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
                        "last_opcode": session.read_memory("snesMemory", 0x7E2306, 1)[0],
                        "error_program": session.read_memory("snesMemory", 0x7E5F22, 1)[0],
                        "error_pc": u16(session.read_memory("snesMemory", 0x7E5F23, 2)),
                        "error_opcode": session.read_memory("snesMemory", 0x7E5F25, 1)[0],
                        "error_slot": session.read_memory("snesMemory", 0x7E5F8D, 1)[0],
                    },
                    "live_room_header": list(session.read_memory(
                        "snesMemory", LIVE_ROOM_ACTIVE_BASE, 82,
                    )),
                    "bundle_cursor": {
                        "directory_offset": u16(bytes(read_live_room_control(session, inputs)), 0x0E),
                        "index": u16(session.read_memory("snesMemory", 0x7E8FA0, 2)),
                        "remaining": session.read_memory("snesMemory", 0x7E8F9F, 1)[0],
                    },
                    "resident_request_id": u16(session.read_memory("snesMemory", 0x7E8F7A, 2)),
                    "resident_bundle_failure": session.read_memory("snesMemory", 0x7E8FAB, 1)[0],
                    "resident_lookup_failure": {
                        "cause": session.read_memory("snesMemory", 0x7E8FBF, 1)[0],
                        "selector": session.read_memory("snesMemory", 0x7E8FBE, 1)[0],
                        "pool_index": u16(session.read_memory("snesMemory", 0x7E8FBA, 2)),
                        "flags": u16(session.read_memory("snesMemory", 0x7E8FB8, 2)),
                        "program_unit_id": u16(session.read_memory("snesMemory", 0x7E8FBC, 2)),
                    },
                    "active_slots": active_slots(session),
                })
                break
            current_bytes_read = int(storage_frame["bytes_read"])
            data_delta = max(0, current_bytes_read - previous_bytes_read)
            if data_delta:
                frames_with_data_progress += advanced
                data_bytes_per_frame_total += data_delta
                max_data_bytes_per_frame = max(
                    max_data_bytes_per_frame,
                    (data_delta + advanced - 1) // advanced,
                )
            previous_bytes_read = current_bytes_read
            observed_peak_cached_bytes = max(
                observed_peak_cached_bytes,
                sum(int(slot["size"]) for slot in storage_frame["cache_slots"]
                    if slot["state"] in (1, 2)),
            )
            if room_storage["state"] != previous_room_resource_state:
                room_resource_events.append({
                    "frame": frame,
                    "state": room_storage["state"],
                    "requested_room": room_storage["room"],
                    "runtime_room": room,
                    "m23a_phase": session.read_memory("snesMemory", 0x7FF2C2, 1)[0],
                    "validated_count": room_storage["validated"],
                })
                previous_room_resource_state = room_storage["state"]
            if elapsed <= 8 or elapsed % 32 == 0 or room != previous_room:
                stack_samples.append({"frame": frame, "sp": cpu_sp(session), "room": room})
            request_diag = session.read_memory(
                "snesMemory", M23A_REQUEST_DIAGNOSTICS, 7)
            if request_diag[0] != previous_request_count:
                room_requests.append({
                    "frame": frame, "count": request_diag[0],
                    "target_room": request_diag[2], "outgoing_room": request_diag[3],
                    "request_program": request_diag[4],
                    "request_pc": u16(request_diag, 5),
                    "return_valid": session.read_memory(
                        "snesMemory", 0x7FF467, 1)[0],
                    "return_slot": session.read_memory(
                        "snesMemory", 0x7FF468, 1)[0],
                    "room_resource_state": room_storage["state"],
                    "runtime_room": room,
                })
                previous_request_count = request_diag[0]
            if elapsed <= 28 or room != previous_room or capture_after_room4 is not None:
                slots = active_slots(session)
                observed_bindings = valid_bindings(session)
                binding_map = {row["program_unit_id"]: row for row in observed_bindings}
                if binding_map != previous_binding_map:
                    old_by_selector = {row["selector"]: row for row in previous_binding_map.values()}
                    new_by_selector = {row["selector"]: row for row in binding_map.values()}
                    changed = [
                        {"selector": selector,
                         "old": old_by_selector.get(selector),
                         "new": new_by_selector.get(selector)}
                        for selector in sorted(old_by_selector.keys() | new_by_selector.keys())
                        if old_by_selector.get(selector) != new_by_selector.get(selector)
                    ]
                    native_binding_events.append({
                        "frame": frame, "room": room, "changed": changed,
                        "active_slots": slots,
                    })
                    previous_binding_map = binding_map
                live_selectors = {int(item["selector"]) for item in slots}
                pinned_rows = [
                    row for row in observed_bindings
                    if (row["flags"] & 0x06) or row["selector"] in live_selectors
                ]
                observed_pin_samples.append({
                    "frame": frame,
                    "resident_count": len(observed_bindings),
                    "pinned_count": len(pinned_rows),
                    "pinned_selectors": sorted(row["selector"] for row in pinned_rows),
                })
                if elapsed <= 28:
                    early_slot_samples.append({"frame": frame, "slots": slots})
                g1_slot = next((item for item in slots if item["script_number"] == 1), None)
                if room != previous_room:
                    room_sequence.append(room)
                    if inputs.get("program_storage") is not None \
                            and inputs["program_storage"].get("live_room_resource_count"):
                        live_observation = check_live_room_native(session, inputs, room)
                        target_video_generation = u16(session.read_memory(
                            "snesMemory",
                            inputs["rom_symbols"]["SAME_VIDEO_SURFACE_STATE"] + 0x1C,
                            2,
                        ))
                        live_observation["ppu_target_generation"] = target_video_generation
                        live_room_observations.append(live_observation)
                        live_room_ppu_pending[room] = target_video_generation
                        live_room_ppu_expected[room] = external_live_room_payloads(inputs, room)
                        live_room_ppu_sampling[room] = {
                            "idle_samples": 0, "ppu_checks": 0,
                            "last_status": None, "last_check_frame": None,
                            "was_idle": False,
                            "transition_diagnostics": live_room_presentation_diagnostics(session, inputs),
                            "last_presentation_diagnostics": None,
                        }
                    bindings = valid_bindings(session)
                    transition_events.append({
                        "frame": frame, "room": room, "error": error,
                        "m23a": list(session.read_memory("snesMemory", 0x7FF2BE, 16)),
                        "storage": msu_program_diagnostics(session, inputs),
                        "reset_diag": list(session.read_memory("snesMemory", 0x7FF46B, 0x20)),
                        "variables": variables(session, (5, 6, 8, 9, 10, 20, 24)),
                        "slots": slots, "bindings": bindings,
                    })
                    g1_binding = identity_binding(bindings, identity_to_id, "GlobalProgram(1)")
                    if room_sequence[-1] == 0:
                        pass
                    else:
                        if room == 1:
                            require(g1_binding is not None,
                                    "yielded GlobalScript(1) binding absent at its first "
                                    f"room transition: bindings={bindings}")
                            g1_initial = g1_binding
                            require(g1_slot is not None,
                                    "GlobalScript(1) activation was not live across its first "
                                    f"room transition: slots={slots}")
                            require(g1_slot["status"] in (2, 5),
                                    "GlobalScript(1) was not yielded/resource-waiting at its "
                                    f"first room transition: {g1_slot}")
                            continuation_state = (
                                "SCUMM_YIELDED" if g1_slot["status"] == 2
                                else "WAIT_RESOURCE_WITH_CANONICAL_BINDING"
                            )
                        elif g1_slot is not None:
                            require(g1_binding is not None and g1_initial is not None,
                                    f"live GlobalScript(1) lost its binding at room {room}")
                            require((g1_binding["selector"], g1_binding["generation"])
                                    == (g1_initial["selector"], g1_initial["generation"]),
                                    "yielded GlobalScript(1) binding moved across room transition")
                            continuation_state = "LIVE_ACROSS_ADDITIONAL_TRANSITION"
                        else:
                            continuation_state = "RETIRED_AFTER_RESUME"
                        snapshots.append({"frame": frame, "room": room,
                                          "global1": g1_binding,
                                          "global1_activation": g1_slot,
                                          "continuation_state": continuation_state,
                                          "storage": msu_program_diagnostics(session, inputs),
                                          "stats": stats(session),
                                          "resident_bindings": bindings})
                    if room == 4:
                        capture_after_room4 = elapsed + 28
                if room == 4:
                    bindings = valid_bindings(session)
                    if first_reuse is None:
                        reused = next((row for row in bindings
                                       if row["selector"] == 0xD0
                                       and row["generation"] >= 2), None)
                        if reused is not None:
                            g1_binding = identity_binding(bindings, identity_to_id,
                                                          "GlobalProgram(1)")
                            require(g1_binding is None,
                                    "selector D0 was reused while GlobalScript(1) remained "
                                    f"resident: old={g1_binding}, new={reused}, slots={slots}")
                            require(not any(item["script_number"] == 1 for item in slots),
                                    "selector D0 was reused while GlobalScript(1) activation "
                                    "remained live")
                            first_reuse = {"frame": frame, **reused}
                    binding = next((row for row in bindings
                                    if row["program_unit_id"] == g192_id), None)
                    if binding is not None and g192_rebind is None:
                        g192_rebind = {"frame": frame, **binding}
            # Observe the short idle boundary every logical frame. Full PPU
            # reads remain sparse: once on an idle edge, then at most every
            # eight frames until exact background samples match.
            for pending_room, target_generation in list(live_room_ppu_pending.items()):
                if pending_room != room:
                    continue
                status = live_room_ppu_status(session, inputs)
                sampling = live_room_ppu_sampling[pending_room]
                sampling["last_status"] = status
                ready = (status["committed_generation_high"] == 0
                         and status["state"] == 1 and status["locked"] == 0)
                sampling["idle_samples"] += int(ready)
                should_check = ready and (
                    not sampling["was_idle"] or elapsed % 8 == 0
                )
                sampling["was_idle"] = ready
                if not should_check:
                    continue
                sampling["last_presentation_diagnostics"] = (
                    live_room_presentation_diagnostics(session, inputs)
                )
                sampling["ppu_checks"] += 1
                sampling["last_check_frame"] = frame
                try:
                    ppu_row = check_live_room_ppu(
                        session, inputs, pending_room, target_generation,
                        expected=live_room_ppu_expected[pending_room],
                    )
                except RuntimeError as exc:
                    live_room_ppu_last_mismatch[pending_room] = str(exc)
                    continue
                ppu_row["observed_frame"] = frame
                ppu_row["sampling"] = dict(sampling)
                live_room_ppu_observations.append(ppu_row)
                room_row = next(row for row in live_room_observations
                                if int(row["room"]) == pending_room)
                room_row["ppu_observation"] = ppu_row
                room_row["ppu_verified_after_settlement"] = True
                del live_room_ppu_pending[pending_room]
            previous_room = room
            if (room == 4 and g192_rebind is not None and elapsed >= capture_after_room4
                    and error == 0
                    and variables(session, (20,))["20"] == 4
                    and not active_slots(session)):
                break

        live_room_ppu_observation = None
        if inputs["program_storage"] is not None \
                and inputs["program_storage"].get("live_room_resource_count"):
            settled_before_drain = {
                "room": session.read_memory("snesMemory", ROOM, 1)[0],
                "error": session.read_memory("snesMemory", ERROR, 1)[0],
                "variables": variables(session, (5, 6, 8, 9, 10, 20, 21, 22, 24, 25)),
                "slots": active_slots(session),
            }
            require(settled_before_drain["room"] == 4 and settled_before_drain["error"] == 0,
                    f"route was not settled before live PPU drain: {settled_before_drain}; "
                    f"runtime_error_observations={runtime_error_observations}; "
                    f"last_transition={transition_events[-1:]}; "
                    f"m23a={list(session.read_memory('snesMemory', 0x7FF2BE, 16))}; "
                    f"live={live_room_presentation_diagnostics(session, inputs)}")
            live_room_ppu_observation = drain_and_check_live_room_ppu(
                session, inputs, settled_before_drain["room"],
            )
            live_room_ppu_observation["observed_frame"] = int(
                session.get_state()["frameCount"]
            )
            final_room_row = next(
                row for row in live_room_observations
                if int(row["room"]) == settled_before_drain["room"]
            )
            final_room_row["ppu_observation"] = live_room_ppu_observation
            final_room_row["ppu_verified_after_settlement"] = True
            live_room_ppu_observations = [
                row for row in live_room_ppu_observations
                if int(row["room"]) != settled_before_drain["room"]
            ]
            live_room_ppu_observations.append(live_room_ppu_observation)
            live_room_ppu_pending.pop(settled_before_drain["room"], None)
            settled_after_drain = {
                "room": session.read_memory("snesMemory", ROOM, 1)[0],
                "error": session.read_memory("snesMemory", ERROR, 1)[0],
                "variables": variables(session, (5, 6, 8, 9, 10, 20, 21, 22, 24, 25)),
                "slots": active_slots(session),
            }
            require(settled_after_drain == settled_before_drain,
                    "post-route visual completion changed settled SCUMM state: "
                    f"before={settled_before_drain}, after={settled_after_drain}")
            if live_room_observations:
                live_room_observations[-1]["ppu_verified_after_settlement"] = True
                live_room_observations[-1]["ppu_observation"] = live_room_ppu_observation
            missing_ppu_rooms = sorted(
                int(row["room"]) for row in live_room_observations
                if not row.get("ppu_verified_after_settlement")
            )
            require(not missing_ppu_rooms,
                    f"actual PPU pixels/palette were not observed for live rooms: {missing_ppu_rooms}; "
                    f"pending={live_room_ppu_pending}; "
                    f"last_mismatch={live_room_ppu_last_mismatch}; "
                    f"sampling={live_room_ppu_sampling}")
            common_tile_indices = set.intersection(*(
                set(row["matching_tile_indices"])
                for row in live_room_ppu_observations
            )) if live_room_ppu_observations else set()
            require(common_tile_indices,
                    "no common PPU character tiles matched the checked SC5VIS records "
                    f"across room checkpoints: {live_room_ppu_observations}")
            common_tile_indices = sorted(common_tile_indices)
            for row in live_room_ppu_observations:
                row["cross_room_sample_indices"] = common_tile_indices
                row["cross_room_sample_sha256"] = hashlib.sha256(b"".join(
                    bytes.fromhex(row["matching_tile_sha256"][str(index)])
                    for index in common_tile_indices
                )).hexdigest()
            require(len({row["cross_room_sample_sha256"]
                         for row in live_room_ppu_observations})
                    == len(live_room_observations)
                    and len({row["cgram_sha256"] for row in live_room_ppu_observations})
                    == len(live_room_observations),
                    "live-room PPU background samples/palette did not change distinctly per room: "
                    f"{live_room_ppu_observations}")

        bindings = valid_bindings(session)
        final_room = session.read_memory("snesMemory", ROOM, 1)[0]
        marker_indices = (5, 6, 7, 8, 9, 10, 15, 20, 21, 22, 24, 25)
        if large_body_case:
            marker_indices += (50, 51, 53, 54)
        variables_final = variables(session, marker_indices)
        final_error = session.read_memory("snesMemory", ERROR, 1)[0]
        final_stats = stats(session)
        final_storage = msu_program_diagnostics(session, inputs)
        c4_count = session.read_memory("snesMemory", 0x7E2A8A, 1)[0]
        name_cache_byte = session.read_memory("snesMemory", OBJECT_NAME_LENGTH + 70, 1)[0]
        sp = cpu_sp(session)
        final_slots = active_slots(session)
        m23a_final = list(session.read_memory("snesMemory", 0x7FF2BE, 16))
        reset_diag_final = list(session.read_memory("snesMemory", 0x7FF46B, 0x80))
        cpu_final = session.get_cpu_state("Snes")
        frame_counter_final = u16(session.read_memory("snesMemory", 0x7E2210, 2))
        trace_tail = session.trace_log(count=96, cpu_type="Snes")
        cpu_address = ((int(cpu_final.get("k", 0)) & 0xFF) << 16) | (
            int(cpu_final.get("pc", 0)) & 0xFFFF
        )
        cpu_disassembly = session.disassemble(cpu_address, count=24, cpu_type="Snes")
        if pcm_capture_path is not None:
            pcm_capture_end_frame = int(session.get_state()["frameCount"])
            session.stop_audio()

    require(room_sequence == [0, 1, 2, 3, 4],
            f"unexpected synthetic room transitions: {room_sequence}; final_room={final_room}; "
            f"error={final_error}; active_slots={final_slots}; variables={variables_final}; "
            f"requests={room_requests[-20:]}; title_input={title_input}; "
            f"title={title_debug}; "
            f"stats={final_stats}; storage={final_storage}; "
            f"transitions={transition_events}; reset_diag={reset_diag_final}; "
            f"runtime_errors={runtime_error_observations}; "
            f"bindings={bindings}; m23a={m23a_final}; "
            f"cpu={cpu_final}; cpu_disassembly={cpu_disassembly}; "
            f"brk_capture={brk_capture}; "
            f"frame_counter={frame_counter_final}; sp=${sp:04X}; "
            f"trace_tail={trace_tail.get('rows', [])[-48:]}")
    require(g1_initial is not None and g1_initial["selector"] == 0xD0
            and g1_initial["generation"] == 1,
            "GlobalScript(1) did not begin in expected D0 generation 1 binding")
    require(first_reuse is not None,
            "selector D0 was not reused after its GlobalScript(1) owner retired; "
            f"room={final_room}, bindings={len(bindings)}, "
            f"d0={next((row for row in bindings if row['selector'] == 0xD0), None)}, "
            f"global1={identity_binding(bindings, identity_to_id, 'GlobalProgram(1)')}, "
            f"slots={final_slots}, vars={variables_final}, stats={final_stats}")
    require(first_reuse["generation"] == 2,
            f"selector D0 generation did not advance exactly once: {first_reuse}")
    require(g192_rebind is not None, "post-transition GlobalScript(192) binding not observed")
    require(final_room == 4 and final_error == 0, "room route ended in error or wrong room")
    storage_identity = None
    if inputs["program_storage"] is not None:
        storage = inputs["program_storage"]
        expected_room_ids = sorted(int(row["room"]) for row in inputs["manifest"]["records"])
        room_metrics = final_storage["room_resource"]
        # Live-room mode validates two room-owned records per room through
        # the shared lifecycle counter: SC5LIVE metadata and SC5VIS pixels.
        # Palette reads are CRC-checked by SAME but do not publish a separate
        # lifecycle-ready event. The legacy SC5ROOM-only mode remains one
        # validation per room.
        expected_room_validations = (
            len(expected_room_ids) * 2
            if inputs["program_storage"].get("live_room_resource_count") else
            len(expected_room_ids)
        )
        require(room_metrics["requests"] == len(expected_room_ids)
                and room_metrics["validated"] == expected_room_validations
                and room_metrics["failures"] == 0,
                "native room-resource fetch/validation counts differ from generated bundle: "
                f"expected={expected_room_ids}, metrics={room_metrics}")
        require(room_metrics["state"] == 3 and room_metrics["room"] == expected_room_ids[-1],
                f"last compiler room record did not remain validated: {room_metrics}")
        require(0 < final_storage["cache_peak_bytes"] <= 3 * 0x800
                and final_storage["cache_failures"] == 0
                and final_storage["timeout_count"] == 0,
                "native bytecode cache did not exercise both bounded windows cleanly: "
                f"{final_storage}")
        require(final_storage["execution_depth"] == 0
                and not any(final_storage["transient_execution_pins"]),
                "transient bytecode execution pins survived a scheduler boundary: "
                f"{final_storage}")
        room_transition_validations = [
            row["storage"]["room_resource"]["validated"] for row in transition_events
        ]
        require(len(room_transition_validations) == len(room_sequence) - 1
                and all(value >= index for index, value in enumerate(
                    room_transition_validations, 1)),
                "room transition became visible before its incoming SC5ROOM record was checked: "
                f"validations={room_transition_validations}; events={transition_events}")
        code_rows = {int(row["program_unit_id"]): row for row in storage["records"]}
        boot_record = code_rows[g1_id]
        high_offset_program_units = sorted(
            int(row["program_unit_id"])
            for row in storage["records"]
            if int(row["package_offset"]) > 0x01000000
        )
        # The established streamed-bytecode fixture independently exercises
        # 32-bit offsets beyond 16 MiB. The compact live-room package need not
        # add a synthetic padding section merely to repeat that provider test.
        if high_offset_program_units:
            require(int(boot_record["package_offset"]) > 0x01000000,
                    "large-offset package boot body is not beyond 16 MiB")
        require(any(
            sample["storage"]["cache_slots"][slot]["state"] == 2
            and sample["storage"]["cache_slots"][slot]["program_unit_id"] == g1_id
            for sample in boot_ready_samples
            for slot in range(len(sample["storage"]["cache_slots"]))
        ), "MSU boot executable was not observed READY in the native bytecode cache")
        observed_room_states = {int(row["state"]) for row in room_resource_events}
        require({1, 2, 3} <= observed_room_states,
                "native room fetch did not expose REQUESTED/READING/VALIDATED states: "
                f"observed={sorted(observed_room_states)}, events={room_resource_events}")
        storage_identity = {
            "package_sha256": inputs["program_storage_package"]["sha256"],
            "package_size_bytes": inputs["program_storage_package"]["size_bytes"],
            "program_directory_sha256": inputs["hashes"]["program_storage_sha256"],
            "program_units": len(storage["records"]),
            "program_units_beyond_16mib": high_offset_program_units,
            "program_body_bytes": storage["program_body_bytes"],
            "program_section": storage["package_section"],
            "room_section": storage["room_section"],
            "room_records": storage["room_records"],
            "rooms_checked_natively": expected_room_ids,
            "body_and_room_bytes_omitted_from_rom": True,
            "room_use_boundary": (
                "SC5ROOM authenticates the transition record; SC5LIVE is installed "
                "as the source for live objects, names, verbs, locals, walkboxes and "
                "movement routes; checked SC5VIS pixels/palette are copied into the "
                "live renderer surface before the incoming room is published"
            ),
        }
    require(variables_final["5"] == 1, "yielded GlobalScript(1) did not resume after room change")
    require(variables_final["24"] == 4,
            "yielded GlobalScript(1) did not resume after all four room transitions")
    require(variables_final["25"] == 1,
            "room-4 local script did not execute before starting its global caller")
    require(variables_final["9"] == 3 and variables_final["10"] == 10,
            "multi-verb ObjectProgram was not dispatched through its shared carrier")
    require(variables_final["6"] == 2 and variables_final["8"] == 3,
            "dynamic globals did not execute their expected sentinels")
    require(variables_final["20"] == 4 and variables_final["21"] == 5
            and variables_final["22"] == 6,
            "post-transition caller/child completion markers are missing: "
            f"markers={variables_final}, room={final_room}, error={final_error}, "
            f"stats={final_stats}, slots={final_slots}, SP=${sp:04X}")
    host_expected_markers = {
        "5": 1, "6": 2, "7": 192, "8": 3, "9": 3, "10": 10,
        "15": 1, "20": 4, "21": 5, "22": 6, "24": 4, "25": 1,
    }
    if large_body_case:
        host_expected_markers.update({"50": 1, "51": 0, "54": 2})
        require(variables_final["53"] == 4000,
                "large-body backward branch did not execute exactly two 2,000-op spans: "
                f"{variables_final}")
    host_native_markers = {key: variables_final[key] for key in host_expected_markers}
    require(host_native_markers == host_expected_markers,
            "native live-room route differs from copyright-free host/reference markers: "
            f"native={host_native_markers}, host={host_expected_markers}")
    require(final_stats["peak_resident"] <= SELECTOR_CAPACITY
            and final_stats["peak_resident"] == SELECTOR_CAPACITY,
            "native peak binding count did not exercise the complete selector pool")
    require(final_stats["bundle_loads"] == 4
            and final_stats["bundle_releases"] == 3
            and first_reuse is not None and first_reuse["generation"] == 2,
            "native room bundle release/reuse diagnostics are incomplete: "
            f"stats={final_stats}, first_safe_reuse={first_reuse}, "
            f"bundle_events=({final_stats['bundle_loads']},"
            f"{final_stats['bundle_releases']})")
    require(final_stats["exhaustions"] == 0 and final_error == 0,
            "ordinary route unexpectedly exhausted the selector pool")
    require(observed_pin_samples and max(row["pinned_count"]
                                         for row in observed_pin_samples) > 0,
            "native binding flags/C4 owners did not expose any live pins")
    require(c4_count == 0 and not final_slots, "fixture activations did not retire")
    require(sp == args.stack_floor,
                f"native frame stack did not return to baseline: ${sp:04X} != ${args.stack_floor:04X}; "
                f"samples={stack_samples[-24:]}; execution_depth="
                f"{final_storage['execution_depth']}; cpu={cpu_final}")

    simulator = simulate_native_route(inputs["directory"])
    native_transition_bindings = {
        int(row["room"]): native_bindings_for_compare(row["resident_bindings"])
        for row in snapshots
    }
    simulated_transition_bindings = {
        int(row["room"]): row["bindings"]
        for row in simulator["room_transition_bindings"]
    }
    native_bindings = native_bindings_for_compare(bindings)
    def binding_diff(left: list[dict[str, int]], right: list[dict[str, int]]) -> dict[str, Any]:
        left_by_id = {row["program_unit_id"]: row for row in left}
        right_by_id = {row["program_unit_id"]: row for row in right}
        return {
            "native_only": [left_by_id[key] for key in sorted(left_by_id.keys() - right_by_id.keys())[:12]],
            "simulator_only": [right_by_id[key] for key in sorted(right_by_id.keys() - left_by_id.keys())[:12]],
            "selector_or_generation": [
                {"native": left_by_id[key], "simulator": right_by_id[key]}
                for key in sorted(left_by_id.keys() & right_by_id.keys())
                if left_by_id[key] != right_by_id[key]
            ][:12],
        }
    transition_differences = {
        str(room): binding_diff(native_transition_bindings[room], simulated_transition_bindings[room])
        for room in sorted(native_transition_bindings)
        if native_transition_bindings[room] != simulated_transition_bindings[room]
    }
    final_difference = binding_diff(native_bindings, simulator["final_bindings"])
    table_matches = (
        native_transition_bindings == simulated_transition_bindings
        and native_bindings == simulator["final_bindings"]
    )
    stat_matches = all((
        final_stats["peak_resident"] == simulator["peak_resident"],
        final_stats["current_resident"] == simulator["resident_count"],
        final_stats["binds"] == simulator["binds"],
        final_stats["reuses"] == simulator["reuses"],
        final_stats["bundle_loads"] == simulator["bundle_loads"],
        final_stats["bundle_releases"] == simulator["bundle_releases"],
    ))
    live_resource_mode = bool(
        inputs["program_storage"] is not None
        and inputs["program_storage"].get("live_room_resource_count")
    )
    residency_matches = (
        table_matches if live_resource_mode else
        native_bindings == simulator["final_bindings"]
    )
    simulator_differential = {
        "comparison_basis": "same generated directory and fixture event order, "
                            "including room-4 ENCD before its first stable binding sample; "
                            "one prior child remains live through the next global resolve",
        "comparison_scope": (
            "exact transition and final tables" if live_resource_mode else
            "final table and counters; ROM-table compatibility path may expose a "
            "one-sample timing difference before its lazy room-entry global bind"
        ),
        "native_transition_tables_match": (
            native_transition_bindings == simulated_transition_bindings
        ),
        "native_final_table_matches": native_bindings == simulator["final_bindings"],
        "native_counters_match": stat_matches,
        "matches": residency_matches and stat_matches,
        "native_transition_binding_counts": {
            str(room): len(rows) for room, rows in sorted(native_transition_bindings.items())
        },
        "simulator_transition_binding_counts": {
            str(room): len(rows)
            for room, rows in sorted(simulated_transition_bindings.items())
        },
        "native_final_binding_count": len(native_bindings),
        "simulator_final_binding_count": len(simulator["final_bindings"]),
        "transition_binding_differences": transition_differences,
        "final_binding_difference_sample": final_difference,
        "native_stats": final_stats,
        "simulator_stats": {key: simulator[key] for key in (
            "peak_resident", "resident_count", "binds", "reuses",
            "bundle_loads", "bundle_releases",
        )},
        "simulator_trace": simulator["trace"],
    }
    require(simulator_differential["matches"],
            "native resolver diverged from the compiler simulator: "
            f"{json.dumps({key: value for key, value in simulator_differential.items() if key != 'simulator_trace'}, sort_keys=True)}; "
            f"native binding events near pressure: {json.dumps(native_binding_events[-24:], sort_keys=True)}")

    pcm_capture = None
    if pcm_capture_path is not None:
        pcm_start_frame = min(
            (int(row["frame"]) for row in room_resource_events if int(row["state"]) == 1),
            default=0,
        )
        pcm_capture = pcm_capture_evidence(
            pcm_capture_path, active_start_frame=pcm_start_frame,
            transition_frames=[int(row["frame"]) for row in transition_events],
        )
        require(pcm_capture["peak"] > 0 and pcm_capture["mean_square"] > 0,
                f"configured looping PCM track produced no captured audio: {pcm_capture}")
        pcm_capture["path"] = str(pcm_capture_path)
        pcm_capture["capture_end_emulator_frame"] = pcm_capture_end_frame

    return {
        "format": "same-scumm-native-resident-route-v1",
        "mode": "dynamic-route",
        **inputs["hashes"],
        "source": inputs["source"],
        "build_git_identity": inputs["build_identity"].get("git"),
        "build_identity_rom_sha256": inputs["build_identity"].get("rom", {}).get("sha256"),
        "selector_capacity": SELECTOR_CAPACITY,
        "source_selector_units": len(inputs["directory"]["entries"]),
        "source_globals": inputs["global_count"],
        "room_bundle_sizes": {row["identity"]: len(row["program_unit_ids"])
                              for row in inputs["room_bundles"]},
        "passive_object_records": inputs["passive_object_record_count"],
        "room_sequence": room_sequence,
        "room_transition_samples": snapshots,
        "native_observed_pin_census": {
            "sampling": "native binding flags plus live C4 slot selectors at observed frames",
            "peak_observed_resident": max(row["resident_count"]
                                           for row in observed_pin_samples),
            "peak_observed_pinned": max(row["pinned_count"]
                                         for row in observed_pin_samples),
            "final_observed_pinned": observed_pin_samples[-1]["pinned_count"],
            "samples": observed_pin_samples,
        },
        "title_start_input": title_input,
        "title_start_debug": title_debug,
        "boot_stream_readiness": {
            "frames_waited_after_initial_boot": len(boot_ready_samples),
            "final_sample": boot_ready_samples[-1],
        },
        "msu_program_storage": final_storage,
        "observed_io": {
            "logical_frames": elapsed,
            "data_bytes_read": int(final_storage["bytes_read"]),
            "bytes_per_logical_frame": (
                int(final_storage["bytes_read"]) / max(1, elapsed)
            ),
            "frames_with_data_progress": frames_with_data_progress,
            "average_bytes_per_progress_frame": (
                data_bytes_per_frame_total / max(1, frames_with_data_progress)
            ),
            "maximum_data_bytes_in_one_frame": max_data_bytes_per_frame,
            "peak_bytecode_cache_bytes": observed_peak_cached_bytes,
            "bytecode_cache_capacity_bytes": 2 * 0x0800,
            "max_checked_fetch_latency_frames": int(
                final_storage["max_checked_fetch_latency_frames"]
            ),
        },
        "compiler_storage_identity": storage_identity,
        "room_resource_state_events": room_resource_events,
        "room_resource_request_events": room_requests,
        "live_room_native_observations": live_room_observations,
        "live_room_ppu_observation": live_room_ppu_observation,
        "live_room_ppu_observations": live_room_ppu_observations,
        "pcm_capture": pcm_capture,
        "runtime_error_observations": runtime_error_observations,
        "nested_script_completion": {
            "caller": "GlobalProgram(4)",
            "child_markers": {"GlobalProgram(191)": variables_final["21"],
                              "GlobalProgram(192)": variables_final["22"]},
            "caller_resumed_marker": variables_final["20"],
            "source": "caller starts each child through the normal StartScript opcode, "
                     "yields at the following breakHere, then writes marker 20 after both return",
        },
        "yielded_global_initial_binding": g1_initial,
        "first_safe_reuse": first_reuse,
        "post_retirement_rebind": g192_rebind,
        "markers": variables_final,
        "large_program_body_native_acceptance": (
            {
                "identity": large_body_case["identity"],
                "length": int(large_body_record["length"]),
                "pages": int(large_body_record["page_count"]),
                "branch_targets": [int(value)
                                   for value in large_body_case["branch_targets"]],
                "expected_markers": large_body_case["expected_markers"],
                "observed_markers": {key: variables_final[key]
                                     for key in ("6", "50", "51", "53", "54")},
                "result": "yielded >21 KiB MSU-backed body resumed and crossed page boundaries",
            } if large_body_case else None
        ),
        "host_reference_differential": {
            "basis": "copyright-free generated fixture host conformance test",
            "host_expected_markers": host_expected_markers,
            "native_observed_markers": host_native_markers,
            "matches": host_native_markers == host_expected_markers,
        },
        "room_resource_mode": (
            "SAMEPKG_MSU1" if inputs["program_storage"] is not None
            and inputs["program_storage"].get("live_room_resource_count") else
            "ROM_GENERATED_TABLES"
        ),
        "final_error": final_error,
        "final_room": final_room,
        "final_active_slot_count": c4_count,
        "final_stats": final_stats,
        "final_resident_bindings": bindings,
        "simulator_differential": simulator_differential,
        "native_binding_events": native_binding_events,
        "object_name_length_70": name_cache_byte,
        "final_stack_pointer": sp,
        "result": "PASS",
    }


def run_large_program_body(args: argparse.Namespace,
                           inputs: dict[str, Any]) -> dict[str, Any]:
    """Execute a long, paged MSU body without coupling the test to room routing."""
    case = inputs["manifest"].get("large_program_body")
    require(isinstance(case, dict) and case.get("identity") == "GlobalProgram(2)",
            "large-body mode requires the compiler's GlobalProgram(2) fixture")
    storage = inputs.get("program_storage")
    require(storage is not None, "large-body mode requires compiler MSU storage metadata")
    body_record = next((row for row in storage.get("records", [])
                        if row.get("identity") == case["identity"]), None)
    require(body_record is not None and int(body_record["length"]) > 21002
            and int(body_record["page_count"]) >= 11,
            "GlobalProgram(2) is not the required >21 KiB paged body")
    package_path = Path(inputs["program_storage_package"]["path"])
    package = package_path.read_bytes()
    offset, length = int(body_record["package_offset"]), int(body_record["length"])
    body = package[offset:offset + length]
    require(len(body) == length
            and hashlib.sha256(body).hexdigest() == body_record["sha256"],
            "large body differs from the checked SAMEPKG descriptor")
    rom = Path(inputs["rom_path"]).read_bytes()
    require(body not in rom,
            "large ProgramUnit body is embedded in ROM; MSU fetch is not authoritative")

    timeline: list[dict[str, Any]] = []
    final_vars: dict[str, int] = {}
    final_slots: list[dict[str, int]] = []
    final_storage: dict[str, Any] = {}
    final_stats: dict[str, int] = {}
    final_error = 0
    final_room = 0
    final_sp = 0
    final_stream_error: dict[str, int] = {}
    with _session(args) as session:
        _cold_reset(session)
        _run_exact(session, 10)
        elapsed = 0
        while elapsed < args.frames:
            step_frames = min(16, args.frames - elapsed)
            _run_exact(session, step_frames)
            elapsed += step_frames
            final_vars = variables(session, (6, 8, 50, 51, 53, 54))
            final_slots = active_slots(session)
            final_error = session.read_memory("snesMemory", ERROR, 1)[0]
            if final_error:
                stream_error = session.read_memory("snesMemory", 0x7E5F13, 6)
                final_stream_error = {
                    "valid": session.read_memory("snesMemory", 0x7E5F18, 1)[0],
                    "program_unit_id": u16(stream_error, 0),
                    "pc": u16(stream_error, 2),
                    "site": session.read_memory("snesMemory", 0x7E5F17, 1)[0],
                    "selector_witness": list(
                        session.read_memory("snesMemory", 0x7E5F19, 7)
                    ),
                }
            final_room = session.read_memory("snesMemory", ROOM, 1)[0]
            final_storage = msu_program_diagnostics(session, inputs)
            final_stats = stats(session)
            final_sp = cpu_sp(session)
            timeline.append({
                "frame": int(session.get_state()["frameCount"]),
                "global2_active": any(row["script_number"] == 2
                                       for row in final_slots),
                "variables": final_vars,
                "cache_peak_bytes": final_storage["cache_peak_bytes"],
                "bytes_read": final_storage["bytes_read"],
            })
            if (final_vars.get("53", 0) == 4000
                    and final_vars.get("54", 0) == 2
                    and not any(row["script_number"] == 2 for row in final_slots)):
                break
            if final_error:
                stream_error = session.read_memory("snesMemory", 0x7E5F13, 6)
                raise RuntimeError(
                    f"SCUMM error ${final_error:02X} while executing large body: "
                    f"frame={timeline[-1]['frame']} vars={final_vars} "
                    f"slots={final_slots} storage={final_storage} "
                    f"stream_error={{valid:{session.read_memory('snesMemory', 0x7E5F18, 1)[0]}, "
                    f"program_unit_id:{u16(stream_error, 0)}, "
                    f"pc:{u16(stream_error, 2)}, "
                    f"site:{session.read_memory('snesMemory', 0x7E5F17, 1)[0]}}} "
                    f"page_request={{pc:{u16(session.read_memory('snesMemory', 0x7E2EAC, 4), 0)}, "
                    f"start:{u16(session.read_memory('snesMemory', 0x7E2EAE, 2), 0)}, "
                    f"length:{u16(session.read_memory('snesMemory', 0x7E2EB0, 2), 0)}}}"
                )

    expected = {str(key): int(value)
                for key, value in case["expected_markers"].items()}
    observed = {key: final_vars.get(key, 0) for key in expected}
    require(observed == expected,
            f"native large-body markers differ: {observed} != {expected}; "
            f"error={final_error} room={final_room} storage={final_storage} "
            f"stats={final_stats} stream_error={final_stream_error} "
            f"slots={final_slots} SP=${final_sp:04X}")
    require(final_error == 0 and final_room == 0,
            f"large-body execution changed room/error state: room={final_room}, "
            f"error={final_error}, variables={final_vars}, slots={final_slots}, "
            f"storage={final_storage}, stream_error={final_stream_error}")
    require(0 < final_storage["cache_peak_bytes"] <= 3 * 0x800
            and final_storage["cache_failures"] == 0
            and final_storage["provider_error"] == 0,
            f"large body exceeded or failed the bounded page cache: {final_storage}")
    require(final_storage["execution_depth"] == 0
            and not any(final_storage["transient_execution_pins"]),
            f"large-body completion leaked transient page pins: {final_storage}")
    require(final_storage["bytes_read"] >= length
            and final_storage["cache_loads"] >= int(body_record["page_count"]),
            "native execution did not fetch the complete large body through MSU pages")
    require(final_stats["exhaustions"] == 0
            and final_stats["stale_rejections"] == 0
            and final_sp >= args.stack_floor,
            f"large-body route failed runtime invariants: stats={final_stats}, SP=${final_sp:04X}")
    require(timeline and timeline[-1]["global2_active"] is False,
            f"large ProgramUnit did not complete within {args.frames} frames")
    return {
        "format": "same-scumm-native-large-program-body-v1",
        "mode": "large-program-body",
        **inputs["hashes"],
        "identity": case["identity"],
        "program_unit_id": int(body_record["program_unit_id"]),
        "body_bytes": length,
        "body_sha256": body_record["sha256"],
        "page_size_bytes": int(storage["page_size_bytes"]),
        "page_count": int(body_record["page_count"]),
        "branch_targets": [int(value) for value in case["branch_targets"]],
        "body_absent_from_rom": True,
        "frames_to_complete": 10 + elapsed,
        "diagnostic_samples": len(timeline),
        "markers": observed,
        "cache_peak_bytes": final_storage["cache_peak_bytes"],
        "cache_capacity_bytes": 3 * 0x800,
        "cache_loads": final_storage["cache_loads"],
        "bytes_read": final_storage["bytes_read"],
        "resident_stats": final_stats,
        "stack_pointer": final_sp,
        "result": "PASS",
    }


def run_program_page_failure(args: argparse.Namespace,
                             inputs: dict[str, Any]) -> dict[str, Any]:
    """Corrupt an executable page and prove it is rejected before dispatch."""
    case = inputs["manifest"].get("large_program_body")
    storage = inputs.get("program_storage")
    require(isinstance(case, dict) and storage is not None,
            "program-page-failure requires the compiler large-body fixture")
    record = next((row for row in storage.get("records", [])
                   if row.get("identity") == case.get("identity")), None)
    require(record is not None, "large ProgramUnit is absent from MSU storage")
    unit_id = int(record["program_unit_id"])
    page_index = storage["page_indices"][unit_id]
    first_page = int(page_index["first_page"])
    page_count = int(page_index["page_count"])
    pages = storage["page_records"][first_page:first_page + page_count]
    require(len(pages) == page_count and page_count >= 4,
            "large body does not have the expected checked page directory")
    branch_target = int(case["branch_targets"][0])
    target_page = next((row for row in pages
                        if int(row["start_pc"]) <= branch_target
                        < int(row["start_pc"]) + int(row["length"])), None)
    require(target_page is not None,
            "cross-page branch target is not covered by a generated page")
    page_start = int(target_page["start_pc"])
    page_length = int(target_page["length"])
    package_path = Path(inputs["program_storage_package"]["path"])
    original_package = package_path.read_bytes()
    package_offset = int(record["package_offset"])
    mutate_at = package_offset + page_start + min(32, page_length - 1)
    require(package_offset <= mutate_at < package_offset + int(record["length"]),
            "page corruption offset escapes its ProgramUnit body")
    damaged = bytearray(original_package)
    damaged[mutate_at] ^= 0x80
    require(damaged[mutate_at] != original_package[mutate_at],
            "page corruption injection did not modify a byte")

    original_rom = Path(inputs["rom_path"])
    terminal: dict[str, Any] | None = None
    with tempfile.TemporaryDirectory(prefix="same-scumm-program-page-crc-") as raw:
        root = Path(raw)
        fault_rom = root / "program-page-fault.sfc"
        shutil.copyfile(original_rom, fault_rom)
        shutil.copyfile(original_rom.with_suffix(".map"),
                        root / "program-page-fault.map")
        identity_path = original_rom.with_name(
            original_rom.stem + ".build_identity.json")
        shutil.copyfile(identity_path, root / "program-page-fault.build_identity.json")
        fault_package = root / "program-page-fault.msu"
        fault_package.write_bytes(damaged)

        original_args_rom = args.rom
        args.rom = fault_rom
        try:
            with _session(args) as session:
                _cold_reset(session)
                _run_exact(session, 10)
                elapsed = 0
                while elapsed < args.frames:
                    step = min(16, args.frames - elapsed)
                    _run_exact(session, step)
                    elapsed += step
                    error = session.read_memory("snesMemory", ERROR, 1)[0]
                    if error:
                        stream = bytes(session.read_memory("snesMemory", 0x7E5F13, 7))
                        terminal = {
                            "frame": int(session.get_state()["frameCount"]),
                            "error": error,
                            "room": session.read_memory("snesMemory", ROOM, 1)[0],
                            "variables": variables(session, (50, 51, 53, 54)),
                            "stream_error": {
                                "program_unit_id": u16(stream, 0),
                                "pc": u16(stream, 2),
                                "site": stream[4],
                                "valid": stream[5],
                            },
                            "cache": msu_program_diagnostics(session, inputs),
                            "slots": active_slots(session),
                            "stack_pointer": cpu_sp(session),
                        }
                        break
        finally:
            args.rom = original_args_rom

    require(terminal is not None,
            "corrupted executable page was not rejected within the frame bound")
    require(terminal["error"] != 0,
            "corrupted page did not produce an explicit SCUMM resource error")
    # The provider's first failing event is the checked-read CRC error (site
    # $16).  SetError's separate capture-valid latch is intentionally not
    # required here: this path reports the resource error directly from the
    # scheduler and still retains its source-bound page request fields.
    failed_pages = [row for row in terminal["cache"]["cache_slots"]
                    if row["program_unit_id"] == unit_id
                    and row["logical_page_start"] == page_start]
    require(terminal["stream_error"]["site"] == 0x16
            and terminal["stream_error"]["program_unit_id"] == unit_id
            and page_start <= terminal["stream_error"]["pc"]
            < page_start + page_length,
            f"failure did not identify the corrupted ProgramUnit page: {terminal}")
    require(terminal["cache"]["provider_error"] == 0x06
            and terminal["cache"]["cache_failures"] > 0
            and len(failed_pages) == 1
            and failed_pages[0]["state"] == 0xFF,
            f"corrupted page was not kept out of READY state: {terminal}")
    require(terminal["variables"].get("50") == 0
            and terminal["variables"].get("53") == 0
            and terminal["variables"].get("54") == 0,
            f"code after the corrupted page executed: {terminal['variables']}")
    require(terminal["cache"]["cache_failures"] > 0
            and terminal["stack_pointer"] >= args.stack_floor,
            f"page failure was not safely counted/returned: {terminal}")
    return {
        "format": "same-scumm-native-program-page-failure-v1",
        "mode": "program-page-failure",
        **inputs["hashes"],
        "identity": record["identity"],
        "program_unit_id": unit_id,
        "body_sha256": record["sha256"],
        "page": {"start_pc": page_start, "length": page_length,
                 "crc32": target_page["crc32"], "branch_target": branch_target},
        "corruption": {"package_relative_offset": mutate_at,
                       "original_byte": original_package[mutate_at],
                       "fault_byte": damaged[mutate_at],
                       "fault_package_sha256": hashlib.sha256(damaged).hexdigest()},
        "body_not_published_as_ready": True,
        "terminal": terminal,
        "result": "PASS",
    }


def run_program_page_generation_failure(
    args: argparse.Namespace, inputs: dict[str, Any],
) -> dict[str, Any]:
    """Corrupt a live cache-page generation and require stale-fetch rejection.

    The hook stops the native CPU at the real byte-fetch entry after a checked
    page for the fixture's large GlobalProgram(2) is READY. The test then
    changes only that page's generation metadata while leaving the active
    generation untouched. The interpreter must reject the next byte before
    any instruction from the stale page can run.
    """
    case = inputs["manifest"].get("large_program_body")
    storage = inputs.get("program_storage")
    require(isinstance(case, dict) and storage is not None,
            "page-generation-failure requires the compiler large-body fixture")
    record = next((row for row in storage.get("records", [])
                   if row.get("identity") == case.get("identity")), None)
    require(record is not None,
            "large ProgramUnit is absent from the MSU page directory")
    program_id = int(record["program_unit_id"])
    generation_addresses = (0x7E2F54, 0x7E2F56, 0x7E2EC9)
    from validate_scumm_startup42_nexen import mapped_cpu_address_for_rom

    fetch_pc = mapped_cpu_address_for_rom(
        Path(inputs["rom_path"]), "ScummV5_MsuProgram_FetchByte_Far", bank=9,
    )
    injected: dict[str, int] | None = None
    terminal: dict[str, Any] | None = None
    with _session(args) as session:
        _cold_reset(session)
        _run_exact(session, 10)
        hook = session.add_exec_hook(fetch_pc)
        try:
            for _ in range(args.frames):
                wait = session.run_until(max_frames=1, hook_handle=hook)
                events = [row for row in session.drain_notifications(timeout=0.01)
                          if row.get("method") == "notifications/mesen/hookFired"
                          and int(row.get("params", {}).get("handle", -1)) == hook]
                active_id = u16(session.read_memory(
                    "snesMemory", 0x7E2F5C, 2,
                ))
                if not events or active_id != program_id:
                    if wait.get("framesElapsed", 0) == 0 and not events:
                        _run_exact(session, 1)
                    continue
                slot = session.read_memory("snesMemory", 0x7E2F5B, 1)[0]
                require(slot < len(generation_addresses),
                        f"active cache slot is invalid at fetch: {slot}")
                generation_address = generation_addresses[slot]
                cached_generation = u16(session.read_memory(
                    "snesMemory", generation_address, 2,
                ))
                active_generation = u16(session.read_memory(
                    "snesMemory", 0x7E2F5E, 2,
                ))
                require(cached_generation == active_generation,
                        "fixture reached fetch with an already stale page")
                replacement = (cached_generation + 1) & 0xFFFF
                if replacement == active_generation:
                    replacement = (replacement + 1) & 0xFFFF
                session.write_memory(
                    "snesMemory", generation_address,
                    bytes((replacement & 0xFF, replacement >> 8)).hex(),
                )
                injected = {
                    "program_unit_id": active_id,
                    "cache_slot": slot,
                    "cache_generation_before": cached_generation,
                    "active_generation": active_generation,
                    "cache_generation_injected": replacement,
                }
                break
            require(injected is not None,
                    "large ProgramUnit did not reach the native fetch hook")
        finally:
            session.remove_hook(hook)

        for _ in range(min(args.frames, 120)):
            _run_exact(session, 1)
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            if error:
                stream = bytes(session.read_memory("snesMemory", 0x7E5F13, 7))
                terminal = {
                    "error": error,
                    "room": session.read_memory("snesMemory", ROOM, 1)[0],
                    "variables": variables(session, (50, 51, 53, 54)),
                    "stream_error": {
                        "program_unit_id": u16(stream, 0),
                        "pc": u16(stream, 2),
                        "site": stream[4],
                        "valid": session.read_memory("snesMemory", 0x7E5F18, 1)[0],
                    },
                    "cache": msu_program_diagnostics(session, inputs),
                    "stack_pointer": cpu_sp(session),
                }
                break

    require(terminal is not None and terminal["error"] != 0,
            f"stale page generation was not rejected: {terminal}")
    require(terminal["stream_error"]["valid"] != 0
            and terminal["stream_error"]["site"] == 0x17
            and terminal["stream_error"]["program_unit_id"] == program_id,
            f"stale page rejection lacks source-bound failure evidence: {terminal}")
    require(all(terminal["variables"].get(str(index), 0) == 0
                for index in (50, 51, 53, 54)),
            f"execution continued through stale page data: {terminal['variables']}")
    require(terminal["stack_pointer"] >= args.stack_floor,
            f"stale page rejection unbalanced native stack: {terminal}")
    return {
        "format": "same-scumm-native-program-page-generation-failure-v1",
        "mode": "page-generation-failure",
        **inputs["hashes"],
        "identity": record["identity"],
        "program_unit_id": program_id,
        "fetch_entry_cpu_address": f"${fetch_pc:06X}",
        "generation_injection": injected,
        "terminal": terminal,
        "partial_page_executed": False,
        "result": "PASS",
    }


def run_room_resource_failure(args: argparse.Namespace,
                               inputs: dict[str, Any]) -> dict[str, Any]:
    """Corrupt an incoming SC5LIVE payload and verify no room publication.

    The synthetic input must be a native route with at least two live rooms.
    Keep the SAMEPKG header and directory byte-identical, then flip one byte
    inside the incoming SC5LIVE record. This reaches the runtime's compiler-
    emitted per-resource CRC instead of failing an earlier package-identity
    check.
    """
    storage = inputs.get("program_storage")
    require(storage is not None and storage.get("live_room_resource_count", 0) >= 2,
            "room failure mode requires compiler-generated live-room records")
    build_env = inputs["build_identity"].get("explicit_environment", {})
    require(build_env.get("SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES") == "1",
            "room failure mode requires the live MSU room consumer")
    require(inputs["manifest"].get("conformance_case") == "room-resource-failure",
            "room failure mode requires its generic two-room boot fixture")
    live_records = sorted(storage.get("live_room_records", []),
                          key=lambda row: int(row["room"]))
    outgoing_room, incoming_room = (int(live_records[0]["room"]),
                                    int(live_records[1]["room"]))
    outgoing = external_live_room_payloads(inputs, outgoing_room)
    incoming_row = next(row for row in live_records
                        if int(row["room"]) == incoming_room)
    package_path = Path(inputs["program_storage_package"]["path"])
    original_package = package_path.read_bytes()
    original_info = inspect_package(package_path, verify=True)
    live_section = next(section for section in original_info.sections
                        if section.name == "SC5LIVE")
    mutate_at = int(incoming_row["package_offset"]) + min(96, int(incoming_row["length"]) - 1)
    require(live_section.offset <= mutate_at < live_section.offset + live_section.size,
            "incoming live-room corruption offset is outside SC5LIVE")

    samples: list[dict[str, int]] = []
    terminal: dict[str, Any] | None = None
    final_debug: dict[str, Any] | None = None
    previous_signature: tuple[int, int, int, int] | None = None
    fault_package_sha256: str | None = None
    original_rom = Path(inputs["rom_path"])
    original_args_rom = args.rom
    with tempfile.TemporaryDirectory(prefix="same-scumm-live-room-crc-") as raw:
        root = Path(raw)
        fault_rom = root / "room-resource-fault.sfc"
        shutil.copyfile(original_rom, fault_rom)
        shutil.copyfile(original_rom.with_suffix(".map"), root / "room-resource-fault.map")
        identity_path = original_rom.with_name(original_rom.stem + ".build_identity.json")
        shutil.copyfile(identity_path, root / "room-resource-fault.build_identity.json")

        incoming_section = next(section for section in original_info.sections
                                if section.name == "SC5LIVE")
        require(incoming_section.offset <= mutate_at
                < incoming_section.offset + incoming_section.size,
                "incoming live-room corruption offset is outside SC5LIVE")
        require(int(incoming_row["package_offset"]) <= mutate_at
                < int(incoming_row["package_offset"])
                + int(incoming_row["length"]),
                "injected byte is outside the incoming room record")
        damaged_package = bytearray(original_package)
        damaged_package[mutate_at] ^= 0x80
        fault_package = root / "room-resource-fault.msu"
        fault_package.write_bytes(damaged_package)
        # The package identity/header/directory are intentionally unchanged;
        # only this room record's expected compiler CRC now fails.
        fault_info = inspect_package(fault_package, verify=False)
        require(sha256(fault_package)
                != hashlib.sha256(original_package).hexdigest(),
                "corruption injection did not alter the package payload")
        require(fault_info.sections == original_info.sections,
                "corruption injection altered SAMEPKG directory metadata")
        fault_package_sha256 = sha256(fault_package)

        args.rom = fault_rom
        try:
            with _session(args) as session:
                _cold_reset(session)
                _run_exact(session, 10)
                elapsed = 0
                while elapsed < args.frames:
                    step = 1
                    _run_exact(session, step)
                    elapsed += step
                    room = session.read_memory("snesMemory", ROOM, 1)[0]
                    error = session.read_memory("snesMemory", ERROR, 1)[0]
                    header = bytes(session.read_memory(
                        "snesMemory", LIVE_ROOM_ACTIVE_BASE, 82,
                    ))
                    active_length = u16(header, 48)
                    active = header
                    if 82 <= active_length <= LIVE_ROOM_ACTIVE_CAPACITY:
                        active += bytes(session.read_memory(
                            "snesMemory", LIVE_ROOM_ACTIVE_BASE + 82,
                            active_length - 82,
                        ))
                    sample = {"frame": elapsed, "room": room, "error": error,
                              "active_room": active[12] if len(active) > 12 else 0xFF,
                              "active_length": active_length}
                    signature = (room, error, sample["active_room"], active_length)
                    if (elapsed == 1 or elapsed % 120 == 0 or error
                            or signature != previous_signature):
                        samples.append(sample)
                    previous_signature = signature
                    if error:
                        terminal = {
                            **sample,
                            "active_sha256": hashlib.sha256(active).hexdigest(),
                            "stream_error_capture": list(session.read_memory(
                                "snesMemory", 0x7E5F13, 6,
                            )),
                            "room_resource_failure_count": u16(
                                session.read_memory("snesMemory", 0x7E2FF1, 2),
                            ),
                            "room_resource": msu_program_diagnostics(session, inputs)["room_resource"],
                            "msu": msu_program_diagnostics(session, inputs),
                            "active_slots": active_slots(session),
                            "scumm_context": {
                                "common": list(session.read_memory(
                                    "snesMemory", 0x7E22F8, 24,
                                )),
                                "scenario_error": list(session.read_memory(
                                    "snesMemory", 0x7E5F20, 32,
                                )),
                                "lifecycle": list(session.read_memory(
                                    "snesMemory", 0x7FF2BE, 40,
                                )),
                            },
                            "error_state": error,
                            "stack_pointer": cpu_sp(session),
                        }
                        break
                if terminal is None:
                    final_debug = {
                        "sample": samples[-1] if samples else None,
                        "slots": active_slots(session),
                        "variables": variables(session, (1, 5, 6, 15, 24, 38)),
                        "msu": msu_program_diagnostics(session, inputs),
                        "room_lifecycle": list(session.read_memory(
                            "snesMemory", 0x7FF2BE, 26,
                        )),
                    }
        finally:
            args.rom = original_args_rom

    require(terminal is not None,
            f"incoming corrupted room did not fail within {args.frames} frames; "
            f"last={final_debug}")
    require(terminal["room"] == outgoing_room
            and terminal["active_room"] == outgoing_room,
            f"failed incoming room replaced outgoing live room: {terminal}")
    require(terminal["error_state"] == 0x10
            and terminal["room_resource_failure_count"] >= 1
            and terminal["room_resource"]["failures"] >= 1,
            f"incoming per-resource CRC failure was not explicit: {terminal}")
    require(terminal["active_sha256"] == hashlib.sha256(
                outgoing["live_bytes"],
            ).hexdigest(),
            "failed incoming room changed the valid outgoing SC5LIVE record")
    return {
        "format": "same-scumm-native-room-resource-failure-v1",
        "mode": "room-resource-failure",
        **inputs["hashes"],
        "rom_sha256": inputs["hashes"]["rom_sha256"],
        "canonical_package_sha256": inputs["program_storage_package"]["sha256"],
        "fault_package_sha256": fault_package_sha256,
        "injected_resource": f"SC5LIVE room {incoming_room}",
        "injected_byte_offset": mutate_at,
        "outgoing_room": outgoing_room,
        "outgoing_resource_sha256": outgoing["live"].sha256,
        "outgoing_room_preserved": True,
        "failure": terminal,
        "samples": samples,
        "result": "PASS",
    }


def run_route_value_failure(args: argparse.Namespace,
                            inputs: dict[str, Any]) -> dict[str, Any]:
    """Prove a CRC-valid sparse route with an invalid next-hop is rejected."""
    storage = inputs.get("program_storage")
    require(storage is not None,
            "route-value failure mode requires compiler-generated MSU storage")
    env = inputs["build_identity"].get("explicit_environment", {})
    require(env.get("SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES") == "1"
            and env.get("SAME_BUILD_SCUMM_MSU1_PROGRAMS") == "1"
            and env.get("SAME_SCUMM_DYNAMIC_BOOT_SCRIPT") == "1",
            "route-value failure mode requires the generic booted MSU fixture")
    room = int(args.room if args.room is not None else 1)
    route_row = next((row for row in storage.get("live_route_records", [])
                      if int(row["room"]) == room), None)
    require(route_row is not None,
            f"compiler route directory lacks diagnostic room {room}")
    package_path = Path(inputs["program_storage_package"]["path"])
    package = package_path.read_bytes()
    package_info = inspect_package(package_path, verify=True)
    section = next(row for row in package_info.sections if row.name == "SC5ROUT")
    offset, length = int(route_row["package_offset"]), int(route_row["length"])
    require(section.offset <= offset and offset + length <= section.offset + section.size,
            "diagnostic route record lies outside its CRC-verified package section")
    route = package[offset:offset + length]
    require(hashlib.sha256(route).hexdigest() == route_row["sha256"]
            and f"{zlib.crc32(route) & 0xFFFFFFFF:08x}" == route_row["crc32"],
            "invalid-route fixture bytes do not match their compiler CRC descriptor")
    box_count = route[1]
    directory_bytes = u16(route, 2)
    row = 0
    offsets_base = 4 + box_count
    row_start = u16(route, offsets_base + row * 2)
    row_end = u16(route, offsets_base + (row + 1) * 2)
    require(route[4 + row] == 2 and row_end - row_start >= 2,
            "diagnostic route is not a nonempty sparse row")
    next_hop = route[directory_bytes + row_start + 1]
    require(next_hop >= box_count and next_hop != 0xFF,
            "route-value fixture does not contain an out-of-range sparse next-hop")
    global_id = inputs["identity_to_id"].get("GlobalProgram(1)")
    require(global_id is not None, "fixture directory lacks its boot global")
    active_before: bytes
    matrix_before: bytes
    with _session(args) as session:
        _cold_reset(session)
        _run_exact(session, 10)
        boot_ready = None
        last_boot_probe: dict[str, Any] | None = None
        for _ in range(240):
            boot_slot = next((item for item in active_slots(session)
                              if item["script_number"] == 1), None)
            diagnostics = msu_program_diagnostics(session, inputs)
            cache_ready = any(item["state"] == 2
                              and item["program_unit_id"] == global_id
                              for item in diagnostics["cache_slots"])
            last_boot_probe = {
                "room": session.read_memory("snesMemory", ROOM, 1)[0],
                "error": session.read_memory("snesMemory", ERROR, 1)[0],
                "slot": boot_slot,
                "slots": active_slots(session),
                "cache_ready": cache_ready,
                "cache_slots": diagnostics["cache_slots"],
                "stream_error": bytes(session.read_memory(
                    "snesMemory", 0x7E5F13, 7,
                )).hex(),
            }
            if boot_slot is not None and boot_slot["status"] == 2 and cache_ready:
                boot_ready = {"slot": boot_slot,
                              "frame": int(session.get_state()["frameCount"])}
                break
            _run_exact(session, 1)
        require(boot_ready is not None,
                "boot global did not become cache-ready for route rejection control: "
                f"{last_boot_probe}")
        require(session.read_memory("snesMemory", ROOM, 1)[0] == 0
                and session.read_memory("snesMemory", ERROR, 1)[0] == 0,
                "route rejection control did not start in clean resource-less room 0")
        active_before = bytes(session.read_memory(
            "snesMemory", LIVE_ROOM_ACTIVE_BASE, LIVE_ROOM_ACTIVE_CAPACITY,
        ))
        active_record_room_before = active_before[12]
        active_walkbox_count_before = session.read_memory(
            "snesMemory", 0x7FFA40, 1,
        )[0]
        current_room_before = session.read_memory("snesMemory", ROOM, 1)[0]
        matrix_before = bytes(session.read_memory("snesMemory", 0x7F2000, 64 * 64))
        input_record = _press_exact(
            session, int(session.BTN_START) | int(session.BTN_A),
        )
        terminal = None
        for elapsed in range(1, args.frames + 1):
            _run_exact(session, 1)
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            if error:
                terminal = {
                    "frame": int(session.get_state()["frameCount"]),
                    "room": session.read_memory("snesMemory", ROOM, 1)[0],
                    "error": error,
                    "active_record_room": session.read_memory(
                        "snesMemory", LIVE_ROOM_ACTIVE_BASE + 12, 1,
                    )[0],
                    "active_record_length": u16(session.read_memory(
                        "snesMemory", LIVE_ROOM_ACTIVE_BASE + 48, 2,
                    )),
                    "room_resource": msu_program_diagnostics(session, inputs)["room_resource"],
                    "stream_error": list(session.read_memory(
                        "snesMemory", 0x7E5F13, 7,
                    )),
                }
                break
        require(terminal is not None,
                f"native route semantic validator did not reject the invalid value "
                f"within {args.frames} frames")
        active_after = bytes(session.read_memory(
            "snesMemory", LIVE_ROOM_ACTIVE_BASE, LIVE_ROOM_ACTIVE_CAPACITY,
        ))
        matrix_after = bytes(session.read_memory("snesMemory", 0x7F2000, 64 * 64))
        box_count_after = session.read_memory("snesMemory", 0x7FFA40, 1)[0]
        final = {
            **terminal,
            "current_room_before": current_room_before,
            "active_record_room_before": active_record_room_before,
            "active_walkbox_count_before": active_walkbox_count_before,
            "active_record_unchanged": active_after == active_before,
            "movement_matrix_unchanged": matrix_after == matrix_before,
            "active_walkbox_count": box_count_after,
            "room_lifecycle": room_lifecycle_state(session),
            "stats": stats(session),
            "stack_pointer": cpu_sp(session),
            "storage": msu_program_diagnostics(session, inputs),
        }
    require(final["error"] == 16
            and final["room"] == final["current_room_before"]
            and final["active_record_room"] == final["active_record_room_before"]
            and final["active_record_unchanged"]
            and final["movement_matrix_unchanged"]
            and final["active_walkbox_count"] == final["active_walkbox_count_before"]
            and final["stats"]["exhaustions"] == 0
            and final["stats"]["stale_rejections"] == 0,
            f"invalid route was published or failure was not explicit: {final}")
    return {
        "format": "same-scumm-native-route-value-rejection-v1",
        "mode": "route-value-failure",
        **inputs["hashes"],
        "diagnostic_scope": "copyright-free native semantic-validation control",
        "room": room,
        "package_crc_verified": True,
        "route_crc32": route_row["crc32"],
        "sparse_row": row,
        "invalid_next_hop": next_hop,
        "walkbox_count": box_count,
        "boot_ready": boot_ready,
        "controller_input": input_record,
        "final": final,
        "result": "PASS",
    }


def run_large_live_room(args: argparse.Namespace,
                        inputs: dict[str, Any]) -> dict[str, Any]:
    """Exercise a generated >19-KiB room through the native MSU room path.

    The fixture route intentionally visits the large room, a second room, and
    the large room again.  This is a bounded resource/lifecycle diagnostic,
    not gameplay progression.
    """
    large = inputs["manifest"].get("large_live_room")
    require(isinstance(large, dict) and int(large.get("room", -1)) == 1,
            "large-live-room mode requires the generated large room-1 fixture")
    env = inputs["build_identity"].get("explicit_environment", {})
    require(env.get("SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES") == "1"
            and env.get("SAME_SCUMM_TITLE_START_ROOM") == "0"
            and env.get("SAME_SCUMM_TITLE_TARGET_ROOM") == "1",
            "large-live-room diagnostic requires the generic 0->1 MSU live-room build")
    require(inputs["program_storage"] is not None,
            "large-live-room diagnostic requires compiler-generated SAMEPKG metadata")

    identity_to_id = inputs["identity_to_id"]
    boot_id = identity_to_id["GlobalProgram(1)"]
    sequence = [0]
    observations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    object_events: list[dict[str, Any]] = []
    expected_sequence = [0, 1, 2, 1]
    frame_limit = args.frames
    with _session(args) as session:
        _cold_reset(session)
        session.trace_log(count=1, cpu_type="Snes")
        _run_exact(session, 10)
        boot_ready = None
        last_boot_probe: dict[str, Any] | None = None
        for _ in range(240):
            slots = active_slots(session)
            boot_slot = next((row for row in slots if row["script_number"] == 1), None)
            storage = msu_program_diagnostics(session, inputs)
            ready = any(row["state"] == 2 and row["program_unit_id"] == boot_id
                        for row in storage["cache_slots"])
            last_boot_probe = {
                "room": session.read_memory("snesMemory", ROOM, 1)[0],
                "error": session.read_memory("snesMemory", ERROR, 1)[0],
                "slot": boot_slot,
                "slots": slots,
                "program_cache": storage["cache_slots"],
                "stream_error": bytes(session.read_memory(
                    "snesMemory", 0x7E5F13, 7,
                )).hex(),
                "live_room": live_room_failure_diagnostics(session, inputs),
            }
            if boot_slot is not None and boot_slot["status"] == 2 and ready:
                boot_ready = {"slot": boot_slot, "storage": storage,
                              "frame": int(session.get_state()["frameCount"])}
                break
            _run_exact(session, 1)
        require(boot_ready is not None,
                "compiler-generated boot global did not become yielded and cache-ready: "
                f"{last_boot_probe}")

        start_mask = int(session.BTN_START) | int(session.BTN_A)
        title_input = _press_exact(session, start_mask)
        previous_room = session.read_memory("snesMemory", ROOM, 1)[0]
        require(previous_room == 0, f"diagnostic did not start in room zero: {previous_room}")
        previous_bytes = msu_program_diagnostics(session, inputs)["bytes_read"]
        peak_cache = 0
        active_transfer_frames = 0
        final_frame = 0
        final_state: dict[str, Any] | None = None
        elapsed = 0
        last_object_exec_count = session.read_memory("snesMemory", 0x7E7F9D, 1)[0]
        object_dispatch_sample_frames = 0
        while elapsed < frame_limit:
            live_stage = read_live_room_control(session, inputs, 1)[0]
            # The provider and visual pipeline are resumable across logical
            # frames. Bounded batches avoid millions of debugger transactions
            # in the large-record diagnostic while preserving observed frame
            # deltas and never injecting input during the load.
            markers_before_step = variables(session, (200, 201, 202, 203, 204))
            current_room = session.read_memory("snesMemory", ROOM, 1)[0]
            # Once the room-local sentinel reaches the two sequential object
            # starts, sample each logical frame so a short-lived child slot
            # cannot be hidden inside a batched Nexen advance.
            object_dispatch_window = (
                current_room == 1
                and markers_before_step["201"] == 1
                and markers_before_step["202"] < 3
                and object_dispatch_sample_frames < 96
            )
            step = min(1 if object_dispatch_window else
                       (64 if live_stage == LIVE_ROOM_STAGE_PIXELS else 16),
                       frame_limit - elapsed)
            if object_dispatch_window:
                object_dispatch_sample_frames += step
            result = session.run_frames(step)
            require(not result.get("timedOut")
                    and int(result.get("framesAdvanced", 0)) == step,
                    f"large-room diagnostic frame advancement failed: {result}")
            final_frame = int(session.get_state()["frameCount"])
            elapsed += step
            room = session.read_memory("snesMemory", ROOM, 1)[0]
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            require(error == 0,
                    f"SCUMM error during large-room route: room={room}, "
                    f"provider={msu_program_diagnostics(session, inputs)}")
            diag = msu_program_diagnostics(session, inputs)
            current_bytes = int(diag["bytes_read"])
            data_delta = max(0, current_bytes - previous_bytes)
            if data_delta:
                active_transfer_frames += step
            peak_cache = max(peak_cache, sum(
                int(row["size"]) for row in diag["cache_slots"]
                if row["state"] in (1, 2)
            ))
            stage = read_live_room_control(session, inputs)[0]
            if data_delta or room != previous_room:
                events.append({
                    "frame": final_frame,
                    "room": room,
                    "bytes_read_delta": data_delta,
                    "room_resource": diag["room_resource"],
                    "live_stage": stage,
                    "lifecycle": room_lifecycle_state(session),
                    "slot0": raw_slot_state(session),
                })
            previous_bytes = current_bytes
            if room != previous_room:
                sequence.append(room)
                if room in {int(row["room"]) for row in
                            inputs["program_storage"].get("live_room_records", [])}:
                    observations.append(check_live_room_native(session, inputs, room))
                previous_room = room

            # Keep fixture sentinels out of SCUMM's reserved/system variable
            # range (notably VAR_CURRENT_LIGHTS at 9 and camera state below
            # 32). These high globals are owned only by this diagnostic.
            markers = variables(session, (200, 201, 202, 203, 204))
            object_exec_count = session.read_memory("snesMemory", 0x7E7F9D, 1)[0]
            if object_exec_count != last_object_exec_count:
                word = lambda address: int.from_bytes(
                    session.read_memory("snesMemory", address, 2), "little")
                object_events.append({
                    "frame": final_frame,
                    "exec_count_before": last_object_exec_count,
                    "exec_count_after": object_exec_count,
                    "object": word(0x7E7F91),
                    "entry": session.read_memory("snesMemory", 0x7E7F93, 1)[0],
                    "program": session.read_memory("snesMemory", 0x7E7F94, 1)[0],
                    "entry_offset": word(0x7E7F95),
                    "pc_before": word(0x7E7F97),
                    "pc_after_args": word(0x7E7F99),
                    "slot": session.read_memory("snesMemory", 0x7E7F9B, 1)[0],
                    "arg_count": session.read_memory("snesMemory", 0x7E7F9C, 1)[0],
                    "object_retired": session.read_memory("snesMemory", 0x7E7F9F, 1)[0],
                    "lscr_program": session.read_memory("snesMemory", 0x7E7FA0, 1)[0],
                    "lscr_entry_seen": session.read_memory("snesMemory", 0x7E7FA1, 1)[0],
                    "arg0": word(0x7E7FA2),
                    "arg1": word(0x7E7FA4),
                    "selector": session.read_memory("snesMemory", 0x7E7FA6, 1)[0],
                    "last_allocated": session.read_memory("snesMemory", 0x7E2A89, 1)[0],
                    "active_slots": session.read_memory("snesMemory", 0x7E2A8A, 1)[0],
                    "pending_child_slots": list(session.read_memory(
                        "snesMemory", 0x7E2F70, 8)),
                    "pending_child_programs": list(session.read_memory(
                        "snesMemory", 0x7E2F89, 8)),
                    "nest_depth": session.read_memory("snesMemory", 0x7FF465, 1)[0],
                    "nest_child_slots": list(session.read_memory(
                        "snesMemory", 0x7E5438, 8)),
                    "nest_programs": list(session.read_memory(
                        "snesMemory", 0x7E5420, 8)),
                    "slots": active_slots(session),
                })
                last_object_exec_count = object_exec_count
            if sequence == expected_sequence and room == 1 \
                    and markers == {"200": 1, "201": 1, "202": 3,
                                    "203": 10, "204": 2}:
                final_state = {
                    "room": room,
                    "error": error,
                    "variables": markers,
                    "slots": active_slots(session),
                    "bindings": valid_bindings(session),
                    "stats": stats(session),
                    "stack_pointer": cpu_sp(session),
                }
                break
        require(sequence == expected_sequence and final_state is not None,
                f"large-room diagnostic did not complete its revisit route: "
                f"sequence={sequence}, state={final_state}, "
                f"markers={variables(session, (200, 201, 202, 203, 204))}, "
                f"slots={active_slots(session)}, "
                f"lifecycle={room_lifecycle_state(session)}, "
                f"bindings={valid_bindings(session)}, "
                f"storage={msu_program_diagnostics(session, inputs)}, "
                f"stats={stats(session)}, "
                f"object_events={object_events[-12:]}, "
                f"last={events[-3:] if events else None}")
        require(final_state["error"] == 0 and len(observations) == 3,
                f"large-room resource observations incomplete: {observations}")
        require(final_state["variables"]["202"] == 3
                and final_state["variables"]["203"] == 10,
                "both verbs in the shared large-room object carrier did not execute")

        # The final room-1 visit is settled and its entry guard stops further
        # transitions.  Verify actual PPU presentation, then ensure the drain
        # did not mutate SCUMM-visible state.
        before_drain = {
            "room": session.read_memory("snesMemory", ROOM, 1)[0],
            "error": session.read_memory("snesMemory", ERROR, 1)[0],
            "variables": variables(session, (200, 201, 202, 203, 204)),
        }
        ppu = drain_and_check_live_room_ppu(session, inputs, 1)
        after_drain = {
            "room": session.read_memory("snesMemory", ROOM, 1)[0],
            "error": session.read_memory("snesMemory", ERROR, 1)[0],
            "variables": variables(session, (200, 201, 202, 203, 204)),
        }
        require(before_drain == after_drain,
                f"large-room presentation drain changed SCUMM state: "
                f"{before_drain} -> {after_drain}")
        final_storage = msu_program_diagnostics(session, inputs)
        final_bindings = valid_bindings(session)
        final_stats = stats(session)
        require(final_storage["room_resource"]["failures"] == 0
                and final_stats["exhaustions"] == 0,
                f"resource/residency diagnostics reported failures: "
                f"storage={final_storage}, stats={final_stats}")

    large_observation = next(row for row in observations
                             if row["room"] == 1)
    require(large_observation["live_record_bytes"]
            >= int(large["minimum_active_bytes"])
            and int(large["minimum_expanded_bytes"]) > 19135
            and large_observation["object_count"] == 36
            and large_observation["verb_count"] == 2
            and large_observation["walkbox_count"] == 64
            and large_observation["movement_matrix_matches_sc5route"],
            f"native large-room active/expanded record did not meet its generated "
            f"stress targets (active>={large['minimum_active_bytes']}, "
            f"expanded>{19135}): "
            f"{large_observation}")
    return {
        "format": "same-scumm-native-large-live-room-v1",
        "mode": "large-live-room",
        **inputs["hashes"],
        "diagnostic_scope": "copyright-free native resource/lifecycle control; not gameplay",
        "room_sequence": sequence,
        "expected_room_sequence": expected_sequence,
        "title_start_input": title_input,
        "boot_ready": boot_ready,
        "native_room_observations": observations,
        "ppu": ppu,
        "final_state": final_state,
        "final_storage": final_storage,
        "final_bindings": final_bindings,
        "peak_cached_program_bytes": peak_cache,
        "logical_frames_with_data_progress": active_transfer_frames,
        "room_resource_events": events,
        "object_dispatch_events": object_events,
        "result": "PASS",
    }


def run_room_metadata_probe(args: argparse.Namespace,
                            inputs: dict[str, Any]) -> dict[str, Any]:
    """Load one compiler-owned live-room record through the native lifecycle.

    This bounded diagnostic intentionally does not claim authored gameplay
    progression.  It is useful for an external whole-game package when its
    build profile selects the diagnostic room at startup.
    """
    require(args.room is not None and 0 < args.room < 256,
            "room-metadata-probe requires a valid --room")
    target = int(args.room)
    env = inputs["build_identity"].get("explicit_environment", {})
    require(env.get("SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES") == "1"
            and env.get("SAME_BUILD_SCUMM_MSU1_PROGRAMS") == "1"
            and int(env.get("SAME_SCUMM_TITLE_START_ROOM", "-1")) == 0
            and int(env.get("SAME_SCUMM_TITLE_TARGET_ROOM", "-1")) == target,
            "room-metadata-probe ROM must be an MSU live-resource build whose "
            f"diagnostic target is room {target}")
    require(inputs["program_storage"] is not None,
            "room-metadata-probe requires the compiler-owned SAMEPKG directory")
    # Resolve and hash-check the expected external tables before starting the
    # emulator.  This also rejects a hidden ROM copy of the live payload.
    expected = external_live_room_payloads(inputs, target)
    if args.expect_room_length_rejection:
        live_row = next(
            row for row in inputs["program_storage"]["live_room_records"]
            if int(row["room"]) == target
        )
        require(int(live_row["length"]) == LIVE_ROOM_ACTIVE_CAPACITY + 1
                and not live_row["native_loadable"],
                "expected-rejection mode requires a compiler directory record of "
                f"exactly {LIVE_ROOM_ACTIVE_CAPACITY + 1} bytes")
    global_id = inputs["identity_to_id"].get("GlobalProgram(1)")
    require(global_id is not None,
            "full ProgramUnit directory lacks the authentic boot global")
    # Metadata diagnostics are not gameplay. A diagnostic ROM can omit the
    # authored bootstrap so its startup script cannot replace the room request
    # before the requested SC5LIVE record is published. Keep the ordinary
    # booted mode available as a regression, but make this distinction explicit
    # in both the input requirements and report.
    authored_boot_enabled = (
        env.get("SAME_BUILD_SCUMM_AUTHENTIC_STARTUP") == "1"
        or bool(env.get("SAME_SCUMM_DYNAMIC_BOOT_SCRIPT"))
    )

    with _session(args) as session:
        _cold_reset(session)
        session.trace_log(count=1, cpu_type="Snes")
        _run_exact(session, 10)
        boot_ready = None
        if authored_boot_enabled:
            for _ in range(240):
                boot_slot = next((row for row in active_slots(session)
                                  if row["script_number"] == 1), None)
                storage = msu_program_diagnostics(session, inputs)
                ready = any(row["state"] == 2
                            and row["program_unit_id"] == global_id
                            for row in storage["cache_slots"])
                if boot_slot is not None and boot_slot["status"] == 2 and ready:
                    boot_ready = {"slot": boot_slot,
                                  "frame": int(session.get_state()["frameCount"])}
                    break
                _run_exact(session, 1)
            require(boot_ready is not None,
                    "authentic boot global did not become yielded and cache-ready")
        before = msu_program_diagnostics(session, inputs)
        require(session.read_memory("snesMemory", ROOM, 1)[0] == 0,
                "diagnostic must begin in the resource-less room-zero state")
        active_before = bytes(session.read_memory(
            "snesMemory", LIVE_ROOM_ACTIVE_BASE, LIVE_ROOM_ACTIVE_CAPACITY,
        ))
        guard_addresses = (LIVE_ROOM_ACTIVE_BASE - 1, LIVE_ROOM_ACTIVE_WRAP_GUARD)
        guard_values = (0xA5, 0x5A)
        for address, value in zip(guard_addresses, guard_values, strict=True):
            session.write_memory("snesMemory", address, f"{value:02x}")
        input_record = _press_exact(
            session, int(session.BTN_START) | int(session.BTN_A),
        )
        frames = 0
        observations: list[dict[str, Any]] = []
        previous_room = 0
        final: dict[str, Any] | None = None
        last_validation_error = None
        while frames < args.frames:
            room_now = session.read_memory("snesMemory", ROOM, 1)[0]
            pending_room = session.read_memory(
                "snesMemory", M23A_PENDING_ROOM, 1,
            )[0]
            # Metadata, palette and pixels can take many frames. Batch those
            # waits; switch to single-frame sampling only at commit-ready so
            # diagnostics can catch an authored redirect without issuing
            # thousands of debugger calls during the transfer itself.
            stage = read_live_room_control(session, inputs, 1)[0]
            step = room_metadata_probe_step(
                room_now, pending_room, stage, target, args.frames - frames,
            )
            result = session.run_frames(step)
            require(not result.get("timedOut")
                    and int(result.get("framesAdvanced", 0)) == step,
                    f"room metadata diagnostic failed to advance {step} frames: {result}")
            frames += step
            room = session.read_memory("snesMemory", ROOM, 1)[0]
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            if room != previous_room:
                observations.append({
                    "frame": int(session.get_state()["frameCount"]),
                    "room": room,
                    "room_resource": msu_program_diagnostics(session, inputs)["room_resource"],
                })
                previous_room = room
            active_header = bytes(session.read_memory(
                "snesMemory", LIVE_ROOM_ACTIVE_BASE, 82,
            ))
            live_control = read_live_room_control(session, inputs, 2)
            if room_metadata_probe_is_published(
                    room, target, live_control[1], active_header[12]):
                try:
                    live = check_live_room_native(session, inputs, target)
                    final = {
                        "room": room,
                        "error": error,
                        "lifecycle": session.read_memory(
                            "snesMemory", 0x7E2221, 1,
                        )[0],
                        "active_slots": active_slots(session),
                        "bindings": valid_bindings(session),
                        "stats": stats(session),
                        "stack_pointer": cpu_sp(session),
                        "live_room": live,
                        "storage": msu_program_diagnostics(session, inputs),
                    }
                    break
                except RuntimeError as exc:
                    last_validation_error = str(exc)
            if error != 0:
                if args.expect_room_length_rejection:
                    active_after = bytes(session.read_memory(
                        "snesMemory", LIVE_ROOM_ACTIVE_BASE,
                        LIVE_ROOM_ACTIVE_CAPACITY,
                    ))
                    guards_after = [
                        session.read_memory("snesMemory", address, 1)[0]
                        for address in guard_addresses
                    ]
                    require(error == 16 and room == 0,
                            "oversized room did not fail as a pre-commit resource error: "
                            f"room={room} error={error}")
                    require(active_after == active_before,
                            "oversized incoming record changed the active SC5LIVE allocation")
                    require(guards_after == list(guard_values),
                            f"oversized incoming record overwrote active-allocation guards: "
                            f"{guards_after}")
                    failure_storage = msu_program_diagnostics(session, inputs)
                    require(failure_storage["room_resource"]["failures"] > 0
                            and stats(session)["exhaustions"] == 0
                            and stats(session)["stale_rejections"] == 0,
                            "oversized record did not produce an isolated checked-resource "
                            f"failure: {failure_storage}")
                    return {
                        "format": "same-scumm-native-room-metadata-probe-v1",
                        "mode": "room-metadata-probe",
                        **inputs["hashes"],
                        "diagnostic_scope": "generic native pre-publication size rejection",
                        "room": target,
                        "expected_length": len(expected["live_bytes"]),
                        "terminal": {
                            "room": room,
                            "error": error,
                            "active_record_room": session.read_memory(
                                "snesMemory", LIVE_ROOM_ACTIVE_BASE + 12, 1,
                            )[0],
                            "stack_pointer": cpu_sp(session),
                        },
                        "active_record_unchanged": True,
                        "guard_addresses": list(guard_addresses),
                        "guard_values": guards_after,
                        "room_observations": observations,
                        "controller_input": input_record,
                        "storage": failure_storage,
                        "result": "PASS_EXPECTED_REJECTION",
                    }
                stream_capture = bytes(session.read_memory(
                    "snesMemory", 0x7E5F13, 7,
                ))
                raise RuntimeError(
                    f"SCUMM error before room {target} metadata was verified: "
                    f"room={room}, error={error}, "
                    f"frame={int(session.get_state()['frameCount'])}, "
                    f"lifecycle={room_lifecycle_state(session)}, "
                    f"active_slots={active_slots(session)}, "
                    f"stream_error={{'program_unit_id': {u16(stream_capture)}, "
                    f"'pc': {u16(stream_capture, 2)}, 'site': {stream_capture[4]}, "
                    f"'valid': {session.read_memory('snesMemory', 0x7E5F18, 1)[0]}}}, "
                    f"storage={msu_program_diagnostics(session, inputs)}, "
                    f"live_room_failure={live_room_failure_diagnostics(session, inputs)}, "
                    f"last_validation={last_validation_error}")
        require(final is not None,
                f"room {target} did not publish matching native SC5LIVE/SC5ROUT/SC5VIS "
                f"within {args.frames} frames; observations={observations}, "
                f"last_validation={last_validation_error}, "
                f"storage={msu_program_diagnostics(session, inputs)}")
        after = final["storage"]
        require(final["error"] == 0 and final["stats"]["exhaustions"] == 0
                and final["stats"]["stale_rejections"] == 0,
                f"room {target} metadata probe had runtime/residency errors: {final}")
        require(final["live_room"]["live_record_sha256"]
                == hashlib.sha256(expected["live_bytes"]).hexdigest(),
                "native active room metadata hash differs from SAMEPKG")
        return {
            "format": "same-scumm-native-room-metadata-probe-v1",
            "mode": "room-metadata-probe",
            **inputs["hashes"],
            "diagnostic_scope": "generic native room-resource load; not gameplay progression",
            "room": target,
            "program_unit_count": len(inputs["directory"]["entries"]),
            "room_resource_directory_count": len(
                inputs["program_storage"].get("live_room_records", []),
            ),
            "program_storage_package_sha256": (
                inputs["program_storage"]["package_sha256"]
            ),
            "authored_bootstrap_scripts_executed": authored_boot_enabled,
            "boot_global": ({"identity": "GlobalProgram(1)", "id": global_id,
                             **boot_ready} if boot_ready is not None else None),
            "controller_input": input_record,
            "room_observations": observations,
            "bytes_read_delta": int(after["bytes_read"])
                                  - int(before["bytes_read"]),
            "final": final,
            "result": "PASS",
        }


def run_candidate_probe(args: argparse.Namespace, inputs: dict[str, Any]) -> dict[str, Any]:
    directory = inputs["directory"]
    identity_to_id = inputs["identity_to_id"]
    expected = {identity_to_id[f"GlobalProgram({number})"] for number in (191, 192, 193)}
    with _session(args) as session:
        _cold_reset(session)
        result = _run_exact(session, args.frames)
        require(result["framesAdvanced"] == args.frames and not result["timedOut"],
                "candidate probe did not advance the requested emulator frames")
        bindings = valid_bindings(session)
        resident_ids = {row["program_unit_id"] for row in bindings}
        errors = session.read_memory("snesMemory", ERROR, 1)[0]
        values = variables(session, (21, 22, 23))
        final_stats = stats(session)
        sp = cpu_sp(session)
    require(resident_ids == expected,
            f"candidate probe resident IDs {sorted(resident_ids)} != selected {sorted(expected)}")
    require(len(resident_ids) == 3 and len(directory["global_directory"]) > SELECTOR_CAPACITY,
            "dynamic candidate set was prebound or is not larger than selector capacity")
    require(values == {"21": 5, "22": 6, "23": 7},
            f"candidate target execution markers mismatch: {values}")
    require(errors == 0 and final_stats["dynamic_global_lookups"] >= 2,
            "candidate resolver failed or did not process both indirect starts")
    return {
        "format": "same-scumm-native-resident-candidates-v1",
        "mode": "dynamic-candidates",
        **inputs["hashes"],
        "source": inputs["source"],
        "selector_capacity": SELECTOR_CAPACITY,
        "candidate_global_count": len(directory["global_directory"]),
        "resident_global_ids": sorted(resident_ids),
        "selected_globals": [191, 192, 193],
        "resident_count": len(bindings),
        "markers": values,
        "error": errors,
        "stats": final_stats,
        "stack_pointer": sp,
        "result": "PASS",
    }


def run_whole_source_bank_fetch(args: argparse.Namespace, inputs: dict[str, Any]) -> dict[str, Any]:
    """Execute an out-of-initial-set global through the generated far directory."""
    require(args.generator_report is not None and args.generator_report.is_file(),
            "whole-source bank-fetch acceptance requires --generator-report")
    generator = json.loads(args.generator_report.read_text(encoding="utf-8"))
    rows = {str(row.get("program_unit_identity")): row
            for row in generator.get("program_map", [])}
    large = rows.get("GlobalProgram(6)")
    marker = rows.get("GlobalProgram(7)")
    require(large is not None and marker is not None,
            "generated full-source directory omitted the cross-bank fixture programs")
    require(int(large["length"]) == 0x7FFC,
            f"large boundary program size mismatch: {large.get('length')}")
    require(int(large["bank_offset"]) + int(large["length"]) <= 0x8000,
            "large ProgramUnit crosses its declared LoROM page")
    require(int(large["rom_bank"]) != int(marker["rom_bank"]),
            "marker ProgramUnit was not placed in a different ROM page")
    marker_id = inputs["identity_to_id"].get("GlobalProgram(7)")
    require(marker_id is not None, "GlobalProgram(7) absent from canonical directory")
    with _session(args) as session:
        _cold_reset(session)
        result = _run_exact(session, args.frames)
        values = variables(session, (200,))
        errors = session.read_memory("snesMemory", ERROR, 1)[0]
        current_room = session.read_memory("snesMemory", ROOM, 1)[0]
        bindings = valid_bindings(session)
        resident_ids = {row["program_unit_id"] for row in bindings}
        slots = active_slots(session)
        final_stats = stats(session)
        sp = cpu_sp(session)
    require(result.get("framesAdvanced") == args.frames and not result.get("timedOut"),
            f"whole-source native test did not advance: {result}")
    require(values["200"] == 0xA55A,
            f"cross-bank GlobalProgram(7) did not execute its marker body: {values}")
    require(current_room == 0,
            f"cross-bank fetch control unexpectedly left the cold null scene: room={current_room}, "
            f"variables={values}, error={errors}, slots={slots}, bindings={bindings}, "
            f"stats={final_stats}")
    require(errors == 0 and sp == args.stack_floor,
            f"native fetch failed safely: error={errors}, SP=${sp:04X}, "
            f"room={current_room}, variables={values}, slots={slots}, "
            f"bindings={bindings}, stats={final_stats}")
    require(len(resident_ids) == len(bindings), "native resolver has aliased resident IDs")
    require(final_stats["dynamic_global_lookups"] >= 1,
            "global directory was bypassed instead of resolving the boot script")
    require(final_stats["exhaustions"] == 0 and final_stats["stale_rejections"] == 0,
            f"resolver diagnostic counters report failure: {final_stats}")
    return {
        "format": "same-scumm-whole-source-bank-fetch-v1",
        "mode": "whole-source-bank-fetch",
        **inputs["hashes"], "source": inputs["source"],
        "selector_capacity": SELECTOR_CAPACITY,
        "program_unit_count": len(inputs["directory"].get("entries", [])),
        "room_bundle_count": len(generator.get("rooms", [])),
        "tested_programs": {
            "GlobalProgram(6)": {key: large.get(key) for key in
                                  ("id", "rom_bank", "bank_offset", "length", "sha256")},
            "GlobalProgram(7)": {key: marker.get(key) for key in
                                  ("id", "rom_bank", "bank_offset", "length", "sha256")},
        },
        "marker_program_id": marker_id,
        "resident_program_ids": sorted(resident_ids),
        "variables": values, "room": current_room, "error": errors,
        "stats": final_stats, "stack_pointer": sp,
        "result": "PASS",
    }


def run_exhaustion(args: argparse.Namespace, inputs: dict[str, Any]) -> dict[str, Any]:
    with _session(args) as session:
        _cold_reset(session)
        # Diagnostic WRAM is not defined at power-on. The synchronous test is
        # called during ROM reset, before the normal frame loop. Wait for its
        # caller-return sentinel rather than treating random status WRAM as a
        # completed test (or assuming one video frame completed reset).
        frame = 0
        diagnostic = session.read_memory("snesMemory", DIAG, 16)
        while diagnostic[14] != 0xA5 and frame < args.frames:
            _run_exact(session, 1)
            frame += 1
            diagnostic = session.read_memory("snesMemory", DIAG, 16)
        bindings = valid_bindings(session)
        final_stats = stats(session)
        pin_census = owned_pin_census(session)
        sp = cpu_sp(session)
    report = {
        "format": "same-scumm-native-residency-exhaustion-v1",
        "mode": "pinned-exhaustion-and-stale-generation",
        **inputs["hashes"],
        "source": inputs["source"],
        "diagnostic": {
            "status": diagnostic[0], "exhaustion_error": diagnostic[1],
            "stale_rejected": diagnostic[2], "rebound_selector": diagnostic[3],
            "rebound_generation": u16(diagnostic, 4),
            "table_unchanged_on_failure": diagnostic[6],
            "caller_return_sentinel": diagnostic[14], "stage": diagnostic[15],
            "frames_to_complete": frame,
        },
        "selector_capacity": SELECTOR_CAPACITY,
        "resident_count": len(bindings),
        "peak_stats": final_stats,
        "owned_pin_census": pin_census,
        "stack_pointer": sp,
        "result": "PASS",
    }
    require(report["diagnostic"]["status"] == 1,
            f"native exhaustion control did not pass: {report['diagnostic']}; "
            f"stats={final_stats}; resident_count={len(bindings)}; SP=${sp:04X}")
    require(report["diagnostic"]["exhaustion_error"] == 0x20,
            "179th pinned binding did not report RESIDENCY_EXHAUSTED")
    require(report["diagnostic"]["stale_rejected"] == 1
            and report["diagnostic"]["rebound_selector"] == 0xD0
            and report["diagnostic"]["rebound_generation"] == 2,
            "released selector was not rebound with a new generation / stale check")
    require(report["diagnostic"]["table_unchanged_on_failure"] == 1,
            "exhaustion mutated one of the 178 pinned mappings")
    require(report["diagnostic"]["caller_return_sentinel"] == 0xA5
            and report["diagnostic"]["stage"] == 6,
            "native diagnostic did not return through the far-call boundary")
    require(len(bindings) == SELECTOR_CAPACITY
            and pin_census["peak_owned_pins"] == SELECTOR_CAPACITY
            and pin_census["current_owned_pins"] == SELECTOR_CAPACITY - 1,
            "all 178 selectors were not simultaneously pinned")
    require(final_stats["exhaustions"] == 1 and final_stats["stale_rejections"] == 1,
            "native failure counters do not match expected single events")
    return report


def run_load_room_with_ego(args: argparse.Namespace,
                           inputs: dict[str, Any]) -> dict[str, Any]:
    require(inputs["manifest"].get("conformance_case") == "load-room-with-ego",
            "the selected compiler manifest is not the LWE conformance fixture")
    global_id = inputs["identity_to_id"].get("GlobalProgram(1)")
    entry_id = inputs["identity_to_id"].get("RoomEntryProgram(1)")
    object_id = inputs["identity_to_id"].get("ObjectProgram(room=1,object=70)")
    second_entry_id = inputs["identity_to_id"].get("RoomEntryProgram(2)")
    second_object_id = inputs["identity_to_id"].get("ObjectProgram(room=2,object=72)")
    require(None not in (global_id, entry_id, object_id, second_entry_id,
                         second_object_id),
            "generated directory lacks a required source identity")
    room_one_program_units = {
        int(row["program_unit_id"]) for row in inputs["directory"].get("entries", [])
        if row.get("bundle") == "RoomBundle(1)"
    }
    require(bool(room_one_program_units),
            "generated directory lacks room-1 bundle membership")

    timeline: list[dict[str, Any]] = []
    entry_captures: dict[int, dict[str, Any]] = {}
    entry_resumes: dict[int, dict[str, Any]] = {}
    global_live_bindings: dict[int, dict[str, Any]] = {}
    room_sequence = [0]
    observed_ids: set[int] = set()
    with _session(args) as session:
        _cold_reset(session)
        _run_exact(session, 10)
        final: dict[str, Any] = {}
        for _ in range(args.frames):
            _run_exact(session, 1)
            room = session.read_memory("snesMemory", ROOM, 1)[0]
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            vars_ = variables(session, (38, 40, 41, 100, 101, 102, 103, 104, 105))
            lifecycle_pending = session.read_memory("snesMemory", LOAD_EGO_ACTIVE, 1)[0]
            actor_position = session.read_memory("snesMemory", C31_POSITIONS + 4, 4)
            actor_moving = session.read_memory("snesMemory", C31_MOVING + 1, 1)[0]
            bindings = valid_bindings(session)
            observed_ids.update(row["program_unit_id"] for row in bindings)
            if room != room_sequence[-1]:
                room_sequence.append(room)
            if room in (1, 2) and room not in global_live_bindings:
                global_binding = next((row for row in bindings
                                       if row["program_unit_id"] == global_id), None)
                global_slot = next((row for row in active_slots(session)
                                    if row["script_number"] == 1), None)
                if global_binding is not None and global_slot is not None:
                    global_live_bindings[room] = {
                        "selector": global_binding["selector"],
                        "generation": global_binding["generation"],
                        "slot": global_slot["slot"],
                        "status": global_slot["status"],
                        "program_unit_id": global_binding["program_unit_id"],
                    }
            frame = {
                "frame": int(session.get_state()["frameCount"]),
                "room": room,
                "error": error,
                "last_opcode": session.read_memory("snesMemory", 0x7E2306, 1)[0],
                "common_pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
                "program_select": session.read_memory("snesMemory", 0x7E2362, 1)[0],
                "vm_status": session.read_memory("snesMemory", 0x7E2302, 1)[0],
                "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
                "active_slots": active_slots(session),
                "cpu": session.get_cpu_state("Snes"),
                "variables": vars_,
                "load_ego_active": lifecycle_pending,
                "actor1_position": [u16(actor_position), u16(actor_position, 2)],
                "actor1_moving": actor_moving,
                "bindings": bindings,
                "stats": stats(session),
            }
            if error:
                frame["error_context"] = {
                    "common_state": session.read_memory("snesMemory", 0x7E22F8, 24).hex(),
                    "scenario_error": session.read_memory("snesMemory", 0x7E5450, 16).hex(),
                    "set_error_trace": session.read_memory("snesMemory", 0x7E5500, 8).hex(),
                    "room_lifecycle": session.read_memory("snesMemory", 0x7FF2BE, 12).hex(),
                    "room_lifecycle_tail": session.read_memory("snesMemory", 0x7FF2CA, 14).hex(),
                    "resolver_state": session.read_memory("snesMemory", 0x7E8F7A, 0x2A).hex(),
                    "resolver_error_site": session.read_memory("snesMemory", 0x7E8FAB, 1)[0],
                    "selector_lookup_caller": session.read_memory("snesMemory", 0x7E8FAC, 1)[0],
                    "resident_ids": session.read_memory("snesMemory", 0x7E8C00, 178 * 2).hex(),
                    "resident_flags": session.read_memory("snesMemory", 0x7E8EC8, 178).hex(),
                    "error_breadcrumb": session.read_memory("snesMemory", 0x7E5F20, 16).hex(),
                    "slot_statuses": list(session.read_memory("snesMemory", STATUS, 25)),
                    "program_select": session.read_memory("snesMemory", 0x7E2362, 1)[0],
                    "vm_status": session.read_memory("snesMemory", 0x7E2302, 1)[0],
                    "return_mode": session.read_memory("snesMemory", 0x7E2363, 1)[0],
                    "nested_depth": session.read_memory("snesMemory", 0x7FD335, 1)[0],
                    "fixture_active": session.read_memory("snesMemory", 0x7E235F, 1)[0],
                    "c3_statuses": [session.read_memory("snesMemory", addr, 1)[0]
                                    for addr in (0x7E2354, 0x7E235A)],
                    "c3_pcs": [u16(session.read_memory("snesMemory", addr, 2))
                               for addr in (0x7E2350, 0x7E2356)],
                    "c4_active_count": session.read_memory("snesMemory", 0x7E2A8A, 1)[0],
                    "c4_scheduler_slot": session.read_memory("snesMemory", 0x7E2B22, 1)[0],
                    "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
                    "slot_programs": list(session.read_memory("snesMemory", 0x7E23B2, 25)),
                    "slot_pcs": session.read_memory("snesMemory", 0x7E23E4, 50).hex(),
                    "cpu": session.get_cpu_state("Snes"),
                }
            capture_var, resume_var, object_value = (
                (100, 101, 70) if room == 1 else (103, 105, 72)
            )
            if room in (1, 2) and vars_[str(capture_var)] == object_value \
                    and room not in entry_captures:
                entry_captures[room] = {
                    "frame": frame["frame"], "room": room,
                    "var_walkto_obj": vars_["38"],
                    "captured_value": vars_[str(capture_var)],
                    "entry_script_pc": next((row["pc"] for row in frame["active_slots"]
                                              if row["script_number"] == 0), None),
                }
            if (room in entry_captures and room not in entry_resumes
                    and frame["frame"] > entry_captures[room]["frame"]
                    and vars_[str(resume_var)] == 0):
                entry_resumes[room] = {
                    "frame": frame["frame"], "room": room,
                    "var_walkto_obj": vars_["38"],
                    "sentinel_replaced": True,
                    "entry_script_pc": next((row["pc"] for row in frame["active_slots"]
                                              if row["script_number"] == 0), None),
                }
            if not timeline or any(frame[key] != timeline[-1][key]
                                   for key in ("room", "error", "variables",
                                               "load_ego_active", "bindings")):
                timeline.append(frame)
            final = frame
            if (room == 2 and vars_["100"] == 70 and vars_["101"] == 0
                    and vars_["103"] == 72 and vars_["104"] == 1
                    and vars_["105"] == 0
                    and lifecycle_pending == 0 and actor_moving == 0):
                break
            require(error == 0,
                    f"native VM failed during loadRoomWithEgo: {frame}; timeline={timeline}")
        require(final.get("room") == 2, f"two room transitions did not commit: {final}")
        require(room_sequence == [0, 1, 2],
                f"unexpected loadRoomWithEgo room sequence: {room_sequence}")
        require(set(entry_captures) == {1, 2},
                f"ENCD did not capture both VAR_WALKTO_OBJ values: {entry_captures}")
        require(set(entry_resumes) == {1, 2},
                f"both yielded ENCD scripts did not resume: {entry_resumes}; "
                f"captures={entry_captures}; timeline={timeline}")
        require(entry_captures[1]["captured_value"] == 70
                and entry_captures[2]["captured_value"] == 72,
                f"entry scripts observed the wrong room object: {entry_captures}")
        require(variables(session, (104,))["104"] == 1,
                "room-1 EXCD did not run before the room-2 commit")
        require(set(global_live_bindings) == {1, 2},
                f"live global binding not observed in both room bundles: {global_live_bindings}")
        first_global = global_live_bindings[1]
        second_global = global_live_bindings[2]
        require((first_global["selector"], first_global["generation"])
                == (second_global["selector"], second_global["generation"]),
                "the yielded global binding changed during the room transition: "
                f"{global_live_bindings}")
        require(final["variables"]["38"] == 0 and final["load_ego_active"] == 0,
                f"loadRoomWithEgo postamble did not retire: {final}")
        require(final["variables"]["104"] == 1,
                f"room-1 exit continuation did not run: {final['variables']}")
        final_resident_ids = {int(row["program_unit_id"]) for row in final["bindings"]}
        require(not (room_one_program_units & final_resident_ids),
                "room-1 ProgramUnits remained resident after room-2 commit: "
                f"{sorted(room_one_program_units & final_resident_ids)}")
        require(final["stats"]["bundle_loads"] == 2
                and final["stats"]["bundle_releases"] == 1,
                f"room bundle lifecycle counters mismatch: {final['stats']}")
        require(final["error"] == 0, f"SCUMM error is nonzero: {final}")

        actor_record = session.read_memory(
            "snesMemory", C14_ACTORS + 64, 64,
        )
        actor_pos = session.read_memory("snesMemory", C31_POSITIONS + 4, 4)
        actor_moving = session.read_memory("snesMemory", C31_MOVING + 1, 1)[0]
        actor = {
            "room": actor_record[C14_ACTOR_ROOM],
            "present": actor_record[C14_ACTOR_PRESENT],
            "walk_speed": [actor_record[1], actor_record[2]],
            "ignore_boxes": actor_record[0x11],
            "x": u16(actor_pos), "y": u16(actor_pos, 2),
            "moving": actor_moving,
        }
        camera = {
            "x": u16(session.read_memory("snesMemory", CAMERA_CURRENT_X, 2)),
            "follow_actor": session.read_memory(
                "snesMemory", C15_CAMERA_FOLLOWS, 1)[0],
            "mode": session.read_memory("snesMemory", C15_CAMERA_MODE, 1)[0],
        }
        walk = {
            # The normalized movement entry can reuse generic request/result
            # scratch. The dedicated LWE request remains source-stable; the
            # actor's committed movement destination is the resolved target.
            "requested": [u16(session.read_memory("snesMemory", LOAD_EGO_X, 2)),
                          u16(session.read_memory("snesMemory", LOAD_EGO_Y, 2))],
            "resolved": [u16(session.read_memory("snesMemory", C31_DEST_X + 2, 2)),
                         u16(session.read_memory("snesMemory", MOVE_DEST_Y + 2, 2))],
        }
        movement = {
            "actor1_destination": [
                u16(session.read_memory("snesMemory", 0x7FFDE5 + 2, 2)),
                u16(session.read_memory("snesMemory", 0x7E7BAA + 2, 2)),
            ],
            "actor1_walkbox": session.read_memory("snesMemory", 0x7FFDA5 + 1, 1)[0],
            "actor1_destination_box": session.read_memory(
                "snesMemory", 0x7FFDC5 + 1, 1)[0],
            "actor1_leg_target": [
                u16(session.read_memory("snesMemory", 0x7E7C8A + 2, 2)),
                u16(session.read_memory("snesMemory", 0x7E7CCA + 2, 2)),
            ],
            "actor1_fraction": [
                u16(session.read_memory("snesMemory", 0x7E7D0A + 2, 2)),
                u16(session.read_memory("snesMemory", 0x7E7D4A + 2, 2)),
            ],
            "actor1_current_box": session.read_memory("snesMemory", 0x7E7BEA + 1, 1)[0],
            "move_tick": u16(session.read_memory("snesMemory", 0x7E7EB9, 2)),
        }
        require(actor["room"] == 2 and actor["present"] == 1,
                f"Ego was not installed in the destination room: {actor}")
        require(walk["requested"] == [6, 7] and walk["resolved"] == [6, 7],
                f"optional post-entry walk operands were not applied: {walk}")
        require(actor_moving == 0 and [actor["x"], actor["y"]] == [6, 7],
                f"optional post-entry walk did not settle at its target: {actor}; {movement}")
        require(camera["follow_actor"] == 1 and camera["mode"] == 1,
                f"camera follow state does not match host semantics: {camera}")
        require(int(global_id) in observed_ids,
                "dynamic boot global was not bound through generated resolver data")
        require(final["stats"]["exhaustions"] == 0,
                "resolver exhausted during two-room conformance")

    return {
        "mode": "load-room-with-ego",
        "result": "pass",
        "source_program_units": {
            "GlobalProgram(1)": global_id,
            "RoomEntryProgram(1)": entry_id,
            "ObjectProgram(room=1,object=70)": object_id,
            "RoomEntryProgram(2)": second_entry_id,
            "ObjectProgram(room=2,object=72)": second_object_id,
        },
        "room_sequence": room_sequence,
        "timeline": timeline,
        "entry_captures": entry_captures,
        "entry_resumes": entry_resumes,
        "global_live_bindings": global_live_bindings,
        "room_one_bundle_program_unit_ids": sorted(room_one_program_units),
        "room_one_bundle_program_units_released": True,
        "final": final,
        "actor1": actor,
        "camera": camera,
        "walk": walk,
        "movement": movement,
        "observed_program_unit_ids": sorted(observed_ids),
        "resolver_directory_hashes": inputs["hashes"],
        "source_identity": inputs["source"],
    }


def run_find_inventory(args: argparse.Namespace,
                       inputs: dict[str, Any]) -> dict[str, Any]:
    require(inputs["manifest"].get("conformance_case") == "find-inventory",
            "the selected compiler manifest is not the findInventory fixture")
    global_id = inputs["identity_to_id"].get("GlobalProgram(1)")
    require(global_id is not None,
            "generated directory lacks GlobalProgram(1)")
    with _session(args) as session:
        _cold_reset(session)
        _run_exact(session, 10)
        final: dict[str, Any] = {}
        for _ in range(args.frames):
            _run_exact(session, 1)
            error = session.read_memory("snesMemory", ERROR, 1)[0]
            final = {
                "frame": int(session.get_state()["frameCount"]),
                "room": session.read_memory("snesMemory", ROOM, 1)[0],
                "error": error,
                "results": variables(session, tuple(range(50, 59))),
                "stats": stats(session),
                "active_slots": active_slots(session),
            }
            if final["results"]["58"] == 72:
                break
            require(error == 0,
                    f"native findInventory failed before publishing results: {final}")
        expected = {
            "50": 70, "51": 72, "52": 0, "53": 0, "54": 72,
            "55": 75, "56": 75, "57": 72, "58": 72,
        }
        require(final.get("results") == expected,
                f"native owner-order/index semantics differ: {final}")
        require(final["error"] == 0,
                f"native findInventory left a SCUMM error: {final}")
        require(not any(row.get("identity") == "GlobalProgram(1)"
                        for row in final["active_slots"]),
                f"findInventory conformance global did not retire: {final}")
        require(final["stats"]["exhaustions"] == 0,
                f"resolver exhausted in the findInventory control: {final}")
    return {
        "mode": "find-inventory",
        "result": "pass",
        "expected_results": expected,
        "final": final,
        "program_unit_id": int(global_id),
        "resolver_directory_hashes": inputs["hashes"],
        "source_identity": inputs["source"],
    }


def run_draw_box(args: argparse.Namespace,
                 inputs: dict[str, Any]) -> dict[str, Any]:
    require(inputs["manifest"].get("conformance_case") == "draw-box",
            "the selected compiler manifest is not the drawBox conformance fixture")
    global_id = inputs["identity_to_id"].get("GlobalProgram(1)")
    entry_id = inputs["identity_to_id"].get("RoomEntryProgram(1)")
    require(global_id is not None and entry_id is not None,
            "generated directory lacks the drawBox route identities")

    carrier_path = args.rom.with_name(args.rom.stem + ".carrier.json")
    require(carrier_path.is_file(), f"missing carrier manifest: {carrier_path}")
    carrier = json.loads(carrier_path.read_text(encoding="utf-8"))
    layout = carrier.get("layout")
    require(isinstance(layout, dict) and "backend_reserved" in layout,
            "drawBox native acceptance requires the SA-1 indexed surface carrier")
    bank_text, offset_text = str(layout["backend_reserved"]["address"]).split(":", 1)
    backend_base = (int(bank_text, 16) << 16) | int(offset_text, 16)
    surface_offset = int(layout["backend_reserved"].get("allocations", {}).get(
        "video_surface_state", {},
    ).get("offset", 0x80))
    surface_state = backend_base + surface_offset
    timeline: list[dict[str, Any]] = []
    observed_ids: set[int] = set()
    with _session(args) as session:
        _cold_reset(session)
        _run_exact(session, 10)
        final: dict[str, Any] = {}
        for _ in range(args.frames):
            _run_exact(session, 1)
            bindings = valid_bindings(session)
            observed_ids.update(row["program_unit_id"] for row in bindings)
            final = {
                "frame": int(session.get_state()["frameCount"]),
                "room": session.read_memory("snesMemory", ROOM, 1)[0],
                "error": session.read_memory("snesMemory", ERROR, 1)[0],
                "draw_box_complete": variables(session, (60,))["60"],
                "nested_depth": session.read_memory("snesMemory", 0x7FD335, 1)[0],
                "draw_box_scratch": session.read_memory("snesMemory", 0x7F34F0, 10).hex(),
                "surface_service_state": session.read_memory(
                    "snesMemory", surface_state, 0x20,
                ).hex(),
                "last_opcode": session.read_memory("snesMemory", 0x7E2306, 1)[0],
                "common_pc": u16(session.read_memory("snesMemory", 0x7E2300, 2)),
                "program_select": session.read_memory("snesMemory", 0x7E2362, 1)[0],
                "vm_status": session.read_memory("snesMemory", 0x7E2302, 1)[0],
                "current_slot": session.read_memory("snesMemory", 0x7E2A88, 1)[0],
                "active_slots": active_slots(session),
                "cpu": session.get_cpu_state("Snes"),
                "bindings": bindings,
                "stats": stats(session),
            }
            if not timeline or any(final[key] != timeline[-1][key]
                                   for key in ("room", "error", "draw_box_complete",
                                               "active_slots", "last_opcode", "common_pc")):
                timeline.append(final)
            require(final["error"] == 0,
                    f"native drawBox failed: {final}; timeline={timeline[-8:]}")
            if final["room"] == 1 and final["draw_box_complete"] == 1:
                break
        require(final.get("room") == 1 and final.get("draw_box_complete") == 1,
                f"the room-entry drawBox program did not complete: "
                f"timeline={timeline[-8:]}; final={final}")
        # Drain the ordinary video event path before inspecting the stable
        # indexed backing. The SCUMM drawBox writes the current projection;
        # the video service owns destination offsets and clipping dimensions.
        _run_exact(session, 3)
        error = session.read_memory("snesMemory", ERROR, 1)[0]
        require(error == 0, f"SCUMM error after drawBox presentation: {error}")
        destination_x = u16(session.read_memory("snesMemory", surface_state + 0x10, 2))
        destination_y = u16(session.read_memory("snesMemory", surface_state + 0x12, 2))
        copy_width = u16(session.read_memory("snesMemory", surface_state + 0x14, 2))
        copy_height = u16(session.read_memory("snesMemory", surface_state + 0x16, 2))
        surface_status = session.read_memory("snesMemory", surface_state + 0x04, 1)[0]
        require(surface_status == 1 and copy_width >= 256 and copy_height >= 53,
                "native drawBox fixture lacks the expected active room projection: "
                f"status={surface_status}, copy={copy_width}x{copy_height}")
        surface = session.read_memory("snesMemory", VIDEO_SURFACE_BASE, 256 * 224)

    def pixel(x: int, y: int) -> int:
        return surface[(destination_y + y) * 256 + destination_x + x]

    direct = [[pixel(x, y) for x in range(10, 13)] for y in (20, 21)]
    variable = [[pixel(x, y) for x in range(13, 16)] for y in range(23, 26)]
    clipped = [[pixel(x, y) for x in range(250, 256)] for y in range(50, 53)]
    boundaries = {
        "direct_left": pixel(9, 20), "direct_right": pixel(13, 20),
        "variable_left": pixel(12, 23), "variable_right": pixel(16, 25),
        "clipped_right": pixel(255, 52),
    }
    require(direct == [[201] * 3, [201] * 3],
            f"direct inclusive drawBox differs from SCUMM host semantics: {direct}")
    require(variable == [[202] * 3 for _ in range(3)],
            f"variable/reversed drawBox differs from SCUMM host semantics: {variable}")
    require(all(value != 201 for key, value in boundaries.items()
                if key.startswith("direct_")) and
            all(value != 202 for key, value in boundaries.items()
                if key.startswith("variable_")),
            f"drawBox wrote outside an inclusive rectangle: {boundaries}")
    require(clipped == [[203] * 6 for _ in range(3)],
            f"drawBox did not clip to the projected room surface: {clipped}")
    require(int(global_id) in observed_ids and int(entry_id) in observed_ids,
            "drawBox route did not execute through generated resident directories")
    require(final["stats"]["exhaustions"] == 0,
            "resolver exhausted during drawBox conformance")
    return {
        "mode": "draw-box",
        "result": "pass",
        "program_unit_ids": {
            "GlobalProgram(1)": global_id,
            "RoomEntryProgram(1)": entry_id,
        },
        "surface": {
            "base": VIDEO_SURFACE_BASE,
            "state": surface_state,
            "status": surface_status,
            "destination": [destination_x, destination_y],
            "copy": [copy_width, copy_height],
        },
        "pixels": {
            "direct_inclusive_color_201": direct,
            "variable_reversed_color_202": variable,
            "clipped_color_203": clipped,
            "outside_boundaries": boundaries,
        },
        "final": final,
        "observed_program_unit_ids": sorted(observed_ids),
        "resolver_directory_hashes": inputs["hashes"],
        "source_identity": inputs["source"],
    }


def _session(args: argparse.Namespace):
    if not args.nexen.is_file() or not os.access(args.nexen, os.X_OK):
        raise RuntimeError(f"Nexen is unavailable: {args.nexen}")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    return mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT,
        port=args.port, boot_wait=0.5, socket_timeout=120.0,
        stderr_log=args.output.with_suffix(".nexen-stderr.log"),
    )


def _cold_reset(session: Any) -> None:
    session.pause()
    session.tool("reset_emulator", {"power": True})
    session.pause()


def _run_exact(session: Any, frames: int) -> dict[str, Any]:
    result = session.run_frames(frames)
    require(result.get("framesAdvanced") == frames and not result.get("timedOut"),
            f"Nexen frame advancement mismatch: {result}")
    return result


def _press_exact(session: Any, mask: int) -> dict[str, Any]:
    """Publish a controller level across exact frames, always release it."""
    session.tool("set_input", {
        "port": 0, "buttons": mask, "hold": True, "frames": 0,
    })
    start = int(session.get_state()["frameCount"])
    try:
        # Keep the ordinary controller level through the auto-joypad seam;
        # observe every completed frame so a missing edge is diagnosable.
        samples = []
        for _ in range(4):
            _run_exact(session, 1)
            samples.append({
                "frame": int(session.get_state()["frameCount"]),
                "held": u16(session.read_memory("snesMemory", 0x7E2200, 2)),
                "pressed": u16(session.read_memory("snesMemory", 0x7E2204, 2)),
                "joy1": u16(session.read_memory("snesMemory", 0x004218, 2)),
            })
    finally:
        session.tool("set_input", {
            "port": 0, "buttons": 0, "hold": True, "frames": 0,
        })
    # Preserve the validated input cadence: one neutral frame after release.
    # The auto-joypad mirror can still report the prior sample at this seam;
    # the host controller level itself is explicitly neutralized in finally.
    release = _run_exact(session, 1)
    released_held = u16(session.read_memory("snesMemory", 0x7E2200, 2))
    return {
        "mask": mask, "press_start_frame": start,
        "press_frames": len(samples),
        "release_frames": int(release["framesAdvanced"]),
        "samples": samples,
        "held_after_cleanup": released_held,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dynamic-route", "dynamic-candidates",
                                            "large-program-body",
                                            "program-page-failure",
                                            "page-generation-failure",
                                            "room-resource-failure",
                                            "route-value-failure",
                                            "large-live-room",
                                            "room-metadata-probe",
                                            "exhaustion", "load-room-with-ego",
                                            "find-inventory", "draw-box",
                                            "whole-source-bank-fetch"),
                        required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--program-storage-json", type=Path,
                        help="compiler storage manifest paired with an MSU-enabled ROM")
    parser.add_argument("--room", type=int,
                        help="target room for the generic room-metadata-probe mode")
    parser.add_argument(
        "--expect-room-length-rejection", action="store_true",
        help="require a native pre-publication rejection for a 6145-byte SC5LIVE record",
    )
    parser.add_argument("--generator-report", type=Path,
                        help="generated program placement report for whole-source fetch mode")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=360)
    parser.add_argument("--stop-on-brk", action="store_true",
                        help="diagnostic: stop at first BRK handler entry")
    parser.add_argument("--stop-on-resource-error", action="store_true",
                        help="diagnostic: stop on the first SCUMM resource error write")
    parser.add_argument("--stack-floor", type=lambda value: int(value, 0),
                        help="override expected stack baseline for this ROM's WRAM layout")
    parser.add_argument("--port", type=int, default=46381)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(
        args.rom, args.manifest, args.directory, args.program_storage_json,
        allow_invalid_route_fixture=args.mode == "route-value-failure",
        expect_room_length_rejection=args.expect_room_length_rejection,
    )
    require(not args.expect_room_length_rejection or args.mode == "room-metadata-probe",
            "--expect-room-length-rejection is valid only with room-metadata-probe")
    if args.stack_floor is None:
        build_env = inputs["build_identity"].get("explicit_environment", {})
        args.stack_floor = 0x0FFF if build_env.get("SAME_BUILD_SCUMM_MSU1_PROGRAMS") == "1" else 0x1FFF
    if args.mode == "dynamic-route":
        report = run_dynamic_route(args, inputs)
    elif args.mode == "large-program-body":
        report = run_large_program_body(args, inputs)
    elif args.mode == "program-page-failure":
        report = run_program_page_failure(args, inputs)
    elif args.mode == "page-generation-failure":
        report = run_program_page_generation_failure(args, inputs)
    elif args.mode == "room-resource-failure":
        report = run_room_resource_failure(args, inputs)
    elif args.mode == "route-value-failure":
        report = run_route_value_failure(args, inputs)
    elif args.mode == "large-live-room":
        report = run_large_live_room(args, inputs)
    elif args.mode == "room-metadata-probe":
        report = run_room_metadata_probe(args, inputs)
    elif args.mode == "dynamic-candidates":
        report = run_candidate_probe(args, inputs)
    elif args.mode == "load-room-with-ego":
        report = run_load_room_with_ego(args, inputs)
    elif args.mode == "find-inventory":
        report = run_find_inventory(args, inputs)
    elif args.mode == "whole-source-bank-fetch":
        report = run_whole_source_bank_fetch(args, inputs)
    elif args.mode == "draw-box":
        report = run_draw_box(args, inputs)
    else:
        report = run_exhaustion(args, inputs)
    report["fixture_manifest_path"] = str(args.manifest)
    report["program_unit_directory_path"] = str(args.directory)
    report["rom_path"] = str(args.rom)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
