#!/usr/bin/env python3
"""Run bounded Nexen acceptance for the feature-gated resident resolver.

The tool consumes the exact compiler-generated directory used by a ROM build.
It has three modes: the >178-unit room route, an isolated dynamic-global
candidate probe, and a pinned-pool exhaustion/stale-generation diagnostic ROM.
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


def load_inputs(rom: Path, manifest_path: Path, directory_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    directory = json.loads(directory_path.read_text(encoding="utf-8"))
    build_identity_path = rom.with_name(rom.stem + ".build_identity.json")
    map_path = rom.with_suffix(".map")
    require(build_identity_path.is_file(), f"missing build identity: {build_identity_path}")
    require(map_path.is_file(), f"missing ROM map: {map_path}")
    entries = directory.get("entries", [])
    identity_to_id = {str(row["identity"]): int(row["program_unit_id"]) for row in entries}
    require(len(identity_to_id) == len(entries), "duplicate canonical ProgramUnit identity")
    require(directory.get("selector_values_emitted") is False,
            "compiler directory must remain selector-free")
    global_count = len(directory.get("global_directory", []))
    require(len(entries) > SELECTOR_CAPACITY, "fixture corpus does not exceed selector pool")
    require(global_count > SELECTOR_CAPACITY,
            "dynamic global candidate universe does not exceed selector pool")
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
        "build_identity": json.loads(build_identity_path.read_text(encoding="utf-8")),
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
            "rom_sha256": sha256(rom),
            "map_sha256": sha256(map_path),
            "build_identity_sha256": sha256(build_identity_path),
        },
        "source": git_identity(),
        "passive_object_record_count": len(passive),
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


def variables(session: Any, indices: tuple[int, ...]) -> dict[str, int]:
    raw = session.read_memory("snesMemory", VARIABLES, (max(indices) + 1) * 2)
    return {str(index): u16(raw, index * 2) for index in indices}


def cpu_sp(session: Any) -> int:
    return int(session.get_cpu_state("Snes")["sp"])


def identity_binding(bindings: list[dict[str, int]], identity_to_id: dict[str, int],
                     identity: str) -> dict[str, int] | None:
    target = identity_to_id[identity]
    return next((row for row in bindings if row["program_unit_id"] == target), None)


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
    g1_initial: dict[str, int] | None = None
    g192_rebind: dict[str, Any] | None = None
    first_reuse: dict[str, Any] | None = None
    capture_after_room4: int | None = None
    error = 0
    early_slot_samples: list[dict[str, Any]] = []
    room_requests: list[dict[str, int]] = []
    observed_pin_samples: list[dict[str, Any]] = []
    title_input: dict[str, Any] | None = None
    title_debug: dict[str, Any] = {}
    with _session(args) as session:
        _cold_reset(session)
        _run_exact(session, 10)
        require(session.read_memory("snesMemory", ROOM, 1)[0] == 0,
                "synthetic title route did not begin in room zero")
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
        while elapsed < args.frames:
            before = int(session.get_state()["frameCount"])
            # Keep room transitions frame-observable through room 4. Once the
            # terminal fixture room is active, no more room changes are
            # possible; batch its deterministic global-resolution churn to
            # avoid one MCP round trip per inert synthetic global.
            if previous_room != 4 or first_reuse is None:
                # The first safe rebind is a generation boundary, so observe
                # it one exact emulator frame at a time. Once recorded, the
                # terminal fixture's remaining deterministic churn is batched.
                step = 1
            else:
                step = min(128, args.frames - elapsed)
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
                })
                previous_request_count = request_diag[0]
            if elapsed <= 28 or room != previous_room or capture_after_room4 is not None:
                slots = active_slots(session)
                observed_bindings = valid_bindings(session)
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
                    g1_binding = identity_binding(bindings, identity_to_id, "GlobalProgram(1)")
                    if room_sequence[-1] == 0:
                        pass
                    else:
                        require(g1_binding is not None,
                                f"GlobalScript(1) binding absent at room transition {room}")
                        if g1_initial is None:
                            g1_initial = g1_binding
                        require((g1_binding["selector"], g1_binding["generation"])
                                == (g1_initial["selector"], g1_initial["generation"]),
                                "yielded GlobalScript(1) binding moved across room transition")
                        require(g1_slot is not None,
                                f"GlobalScript(1) activation not live at room transition {room}")
                        require(g1_slot["status"] == 2,
                                f"GlobalScript(1) was not yielded across room transition "
                                f"{room}: {g1_slot}")
                        snapshots.append({"frame": frame, "room": room,
                                          "global1": g1_binding,
                                          "global1_activation": g1_slot,
                                          "stats": stats(session)})
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
                    and error == 0):
                break

        bindings = valid_bindings(session)
        final_room = session.read_memory("snesMemory", ROOM, 1)[0]
        variables_final = variables(session, (5, 6, 7, 8, 9, 10, 15, 20, 21, 22, 24))
        final_error = session.read_memory("snesMemory", ERROR, 1)[0]
        final_stats = stats(session)
        c4_count = session.read_memory("snesMemory", 0x7E2A8A, 1)[0]
        name_cache_byte = session.read_memory("snesMemory", OBJECT_NAME_LENGTH + 70, 1)[0]
        sp = cpu_sp(session)
        final_slots = active_slots(session)
        m23a_final = list(session.read_memory("snesMemory", 0x7FF2BE, 16))

    require(room_sequence == [0, 1, 2, 3, 4],
            f"unexpected synthetic room transitions: {room_sequence}; final_room={final_room}; "
            f"error={final_error}; active_slots={final_slots}; variables={variables_final}; "
            f"requests={room_requests[-20:]}; title_input={title_input}; "
            f"title={title_debug}; "
            f"stats={final_stats}; m23a={m23a_final}; "
            f"sp=${sp:04X}")
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
    require(variables_final["5"] == 1, "yielded GlobalScript(1) did not resume after room change")
    require(variables_final["24"] == 4,
            "yielded GlobalScript(1) did not resume after all four room transitions")
    require(variables_final["9"] == 3 and variables_final["10"] == 10,
            "multi-verb ObjectProgram was not dispatched through its shared carrier")
    require(variables_final["6"] == 2 and variables_final["8"] == 3,
            "dynamic globals did not execute their expected sentinels")
    require(variables_final["20"] == 4 and variables_final["21"] == 5
            and variables_final["22"] == 6,
            "post-transition caller/child completion markers are missing")
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
    require(sp == 0x1FFF, f"native frame stack did not return to baseline: ${sp:04X}")

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
    parser.add_argument("--mode", choices=("dynamic-route", "dynamic-candidates", "exhaustion"),
                        required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=360)
    parser.add_argument("--port", type=int, default=46381)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(args.rom, args.manifest, args.directory)
    if args.mode == "dynamic-route":
        report = run_dynamic_route(args, inputs)
    elif args.mode == "dynamic-candidates":
        report = run_candidate_probe(args, inputs)
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
