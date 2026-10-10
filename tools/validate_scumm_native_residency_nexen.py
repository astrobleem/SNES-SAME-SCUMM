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
import subprocess
import sys
from typing import Any

from same.engines.scumm_v5.residency_contract import (
    ResidentBindingSimulator,
    ResolverDirectory,
)
from same.package import inspect_package


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
SELECTOR_CAPACITY = 178
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def u16(raw: bytes, offset: int = 0) -> int:
    return int.from_bytes(raw[offset:offset + 2], "little")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


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
               program_storage_path: Path | None = None) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    directory = json.loads(directory_path.read_text(encoding="utf-8"))
    build_identity_path = rom.with_name(rom.stem + ".build_identity.json")
    map_path = rom.with_suffix(".map")
    require(build_identity_path.is_file(), f"missing build identity: {build_identity_path}")
    require(map_path.is_file(), f"missing ROM map: {map_path}")
    build_identity = json.loads(build_identity_path.read_text(encoding="utf-8"))
    entries = directory.get("entries", [])
    identity_to_id = {str(row["identity"]): int(row["program_unit_id"]) for row in entries}
    require(len(identity_to_id) == len(entries), "duplicate canonical ProgramUnit identity")
    require(directory.get("selector_values_emitted") is False,
            "compiler directory must remain selector-free")
    global_count = len(directory.get("global_directory", []))
    require(len(entries) > SELECTOR_CAPACITY, "fixture corpus does not exceed selector pool")
    require(global_count > SELECTOR_CAPACITY,
            "dynamic global candidate universe does not exceed selector pool")
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
        require("SC5CODE" in sections and "SC5ROOM" in sections,
                "compiler package must contain both SC5CODE and SC5ROOM")
        require(program_storage.get("program_count") == len(entries),
                "storage directory does not cover the canonical ProgramUnit directory")
        storage_records = program_storage.get("records", [])
        require(len(storage_records) == len(entries),
                "storage manifest ProgramUnit record count differs")
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
        room_records = program_storage.get("room_records", [])
        room_section = sections["SC5ROOM"]
        require(len(room_records) == program_storage.get("room_resource_count"),
                "SC5ROOM directory count differs from its records")
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
    require(not any("ObjectProgram(room=1,object=71)" in row.get("identity", "")
                    for row in entries),
            "passive object incorrectly consumes a SelectorUnit")
    return {
        "manifest": manifest,
        "directory": directory,
        "identity_to_id": identity_to_id,
        "global_count": global_count,
        "room_bundles": room_bundles,
        "global_units": global_bundle_units,
        "build_identity": build_identity,
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


def msu_program_diagnostics(session: Any) -> dict[str, Any]:
    """Capture provider and bytecode-cache state for native streaming evidence."""
    provider = session.read_memory("snesMemory", 0x7E2F00, 0x48)
    cache = session.read_memory("snesMemory", 0x7E2F48, 0x5A)
    c19 = session.read_memory("snesMemory", 0x7E2FA2, 14)
    room = session.read_memory("snesMemory", 0x7E2FEB, 0x15)
    return {
        "provider_status": provider[0],
        "provider_error": provider[1],
        "seek_count": u16(provider, 0x2B),
        "bytes_read": int.from_bytes(provider[0x2D:0x31], "little"),
        "active_request_offset": int.from_bytes(provider[0x04:0x08], "little"),
        "active_request_length": int.from_bytes(provider[0x08:0x0C], "little"),
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
            },
            {
                "state": cache[1],
                "program_unit_id": u16(cache, 4),
                "size": u16(cache, 8),
                "pins": cache[11],
                "generation": u16(cache, 14),
            },
        ],
        "cache_current": u16(cache, 0x18),
        "cache_peak": u16(cache, 0x1A),
        "cache_loads": u16(cache, 0x1C),
        "cache_evictions": u16(cache, 0x1E),
        "cache_failures": u16(cache, 0x20),
        "cache_request_id": u16(cache, 0x10),
        "cache_request_slot": cache[0x12],
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
    }


def variables(session: Any, indices: tuple[int, ...]) -> dict[str, int]:
    raw = session.read_memory("snesMemory", VARIABLES, (max(indices) + 1) * 2)
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
        transitions.append({
            "room": incoming,
            "bindings": simulator_bindings(simulator, native_directory),
        })
        if incoming == 4:
            # Room 4 ENCD starts the pressure caller and yields between children.
            # The native room number becomes observable at commit, one scheduler
            # frame before that global's first resolver call.
            simulator.begin_global(4, yielded=True, activation_id="G4")

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
    identity_to_id = inputs["identity_to_id"]
    g1_id = identity_to_id["GlobalProgram(1)"]
    g192_id = identity_to_id["GlobalProgram(192)"]

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
    previous_bytes_read = 0
    observed_peak_cached_bytes = 0
    frames_with_data_progress = 0
    max_data_bytes_per_frame = 0
    data_bytes_per_frame_total = 0
    with _session(args) as session:
        _cold_reset(session)
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
        for _ in range(120):
            slots = active_slots(session)
            boot_slot = next((item for item in slots
                              if item["script_number"] == 1), None)
            binding = identity_binding(valid_bindings(session), identity_to_id,
                                       "GlobalProgram(1)")
            storage = msu_program_diagnostics(session)
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
                "READY checked body within 120 frames: "
                f"{boot_ready_samples[-1] if boot_ready_samples else None}"
            )
        room_sequence.append(0)
        start_mask = int(session.BTN_START)
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
        previous_room = session.read_memory("snesMemory", ROOM, 1)[0]
        previous_request_count = session.read_memory(
            "snesMemory", M23A_REQUEST_DIAGNOSTICS, 1)[0]
        if previous_room != room_sequence[-1]:
            room_sequence.append(previous_room)
        elapsed = 0
        stack_samples: list[dict[str, int]] = []
        while elapsed < args.frames:
            before = int(session.get_state()["frameCount"])
            # Keep room transitions frame-observable through room 4. Once the
            # Keep the entire resolver pressure route frame-observable so the
            # native allocation sequence can be compared with the simulator.
            step = 1
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
            storage_frame = msu_program_diagnostics(session)
            room_storage = storage_frame["room_resource"]
            current_bytes_read = int(storage_frame["bytes_read"])
            data_delta = max(0, current_bytes_read - previous_bytes_read)
            if data_delta:
                frames_with_data_progress += 1
                data_bytes_per_frame_total += data_delta
                max_data_bytes_per_frame = max(max_data_bytes_per_frame, data_delta)
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
                    bindings = valid_bindings(session)
                    transition_events.append({
                        "frame": frame, "room": room, "error": error,
                        "m23a": list(session.read_memory("snesMemory", 0x7FF2BE, 16)),
                        "storage": msu_program_diagnostics(session),
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
                                          "storage": msu_program_diagnostics(session),
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
            previous_room = room
            if (room == 4 and g192_rebind is not None and elapsed >= capture_after_room4
                    and error == 0
                    and variables(session, (20,))["20"] == 4
                    and not active_slots(session)):
                break

        bindings = valid_bindings(session)
        final_room = session.read_memory("snesMemory", ROOM, 1)[0]
        variables_final = variables(session, (5, 6, 7, 8, 9, 10, 15, 20, 21, 22, 24, 25))
        final_error = session.read_memory("snesMemory", ERROR, 1)[0]
        final_stats = stats(session)
        final_storage = msu_program_diagnostics(session)
        c4_count = session.read_memory("snesMemory", 0x7E2A8A, 1)[0]
        name_cache_byte = session.read_memory("snesMemory", OBJECT_NAME_LENGTH + 70, 1)[0]
        sp = cpu_sp(session)
        final_slots = active_slots(session)
        m23a_final = list(session.read_memory("snesMemory", 0x7FF2BE, 16))
        reset_diag_final = list(session.read_memory("snesMemory", 0x7FF46B, 0x20))
        cpu_final = session.get_cpu_state("Snes")
        frame_counter_final = u16(session.read_memory("snesMemory", 0x7E2210, 2))
        trace_tail = session.trace_log(count=96, cpu_type="Snes")

    require(room_sequence == [0, 1, 2, 3, 4],
            f"unexpected synthetic room transitions: {room_sequence}; final_room={final_room}; "
            f"error={final_error}; active_slots={final_slots}; variables={variables_final}; "
            f"requests={room_requests[-20:]}; title_input={title_input}; "
            f"title={title_debug}; "
            f"stats={final_stats}; storage={final_storage}; "
            f"transitions={transition_events}; reset_diag={reset_diag_final}; "
            f"bindings={bindings}; m23a={m23a_final}; "
            f"cpu={cpu_final}; frame_counter={frame_counter_final}; sp=${sp:04X}; "
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
        require(room_metrics["requests"] == len(expected_room_ids)
                and room_metrics["validated"] == len(expected_room_ids)
                and room_metrics["failures"] == 0,
                "native room-resource fetch/validation counts differ from generated bundle: "
                f"expected={expected_room_ids}, metrics={room_metrics}")
        require(room_metrics["state"] == 3 and room_metrics["room"] == expected_room_ids[-1],
                f"last compiler room record did not remain validated: {room_metrics}")
        require(final_storage["cache_peak"] == 2
                and final_storage["cache_failures"] == 0
                and final_storage["timeout_count"] == 0,
                "native bytecode cache did not exercise both bounded windows cleanly: "
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
        require(int(boot_record["package_offset"]) > 0x01000000,
                "boot executable did not exercise a ProgramUnit beyond 16 MiB")
        require(any(
            sample["storage"]["cache_slots"][slot]["state"] == 2
            and sample["storage"]["cache_slots"][slot]["program_unit_id"] == g1_id
            for sample in boot_ready_samples for slot in range(2)
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
            "program_body_bytes": storage["program_body_bytes"],
            "program_section": storage["package_section"],
            "room_section": storage["room_section"],
            "room_records": storage["room_records"],
            "rooms_checked_natively": expected_room_ids,
            "body_and_room_bytes_omitted_from_rom": True,
            "room_use_boundary": (
                "checked external cooked-room record gates EXCD/commit/ENCD; "
                "existing generated ROM tables still provide room/object/render data"
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
    require(final_stats["peak_resident"] <= SELECTOR_CAPACITY
            and final_stats["peak_resident"] == SELECTOR_CAPACITY,
            "native peak binding count did not exercise the complete selector pool")
    require(final_stats["reuses"] > 0 and final_stats["bundle_loads"] == 4
            and final_stats["bundle_releases"] == 3,
            "native room bundle release/reuse diagnostics are incomplete")
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
    simulator_differential = {
        "comparison_basis": "same generated directory and fixture event order; "
                            "one prior child remains live through the next global resolve",
        "native_transition_tables_match": (
            native_transition_bindings == simulated_transition_bindings
        ),
        "native_final_table_matches": native_bindings == simulator["final_bindings"],
        "native_counters_match": stat_matches,
        "matches": table_matches and stat_matches,
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
    surface_state = backend_base + 0x80
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
                "surface_service_state": session.read_memory("snesMemory", 0x401084, 0x20).hex(),
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
                                            "exhaustion", "load-room-with-ego",
                                            "find-inventory", "draw-box",
                                            "whole-source-bank-fetch"),
                        required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--program-storage-json", type=Path,
                        help="compiler storage manifest paired with an MSU-enabled ROM")
    parser.add_argument("--generator-report", type=Path,
                        help="generated program placement report for whole-source fetch mode")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=360)
    parser.add_argument("--stack-floor", type=lambda value: int(value, 0),
                        help="override expected stack baseline for this ROM's WRAM layout")
    parser.add_argument("--port", type=int, default=46381)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(args.rom, args.manifest, args.directory,
                         args.program_storage_json)
    if args.stack_floor is None:
        build_env = inputs["build_identity"].get("explicit_environment", {})
        args.stack_floor = 0x0FFF if build_env.get("SAME_BUILD_SCUMM_MSU1_PROGRAMS") == "1" else 0x1FFF
    if args.mode == "dynamic-route":
        report = run_dynamic_route(args, inputs)
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
