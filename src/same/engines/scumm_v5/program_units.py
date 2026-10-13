"""Historical backend-record projection from semantic SCUMM executables.

The front end keeps each object verb body as its own semantic executable.
The existing SNES generator assigns an ID to each included OBCD record, but
empty-verb object records are not runtime-callable: ObjectProgram_Resolve is
gated by Verb_Query. `selector_demand.py` is the authoritative callable
carrier/SelectorUnit projection; this module retains all backend records for
compatibility and comparative reporting.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Any


_REACH_RANK = {
    "ROOT": 0, "DEFINITE": 1, "CONDITIONAL": 2,
    "POSSIBLE": 3, "UNRESOLVED": 4, "UNREACHED": 5,
}


def _program_unit_identity(script: Any) -> tuple[str, str, str, int | None]:
    """Return canonical unit ID, kind, residency scope, and owning room."""
    room = int(script.source.room)
    if script.kind == "SCRP" and script.number is not None:
        return f"GlobalProgram({script.number})", "GLOBAL", "GLOBAL", None
    if script.kind == "ENCD":
        return f"RoomEntryProgram({room})", "ROOM_ENTRY", "ROOM_BUNDLE", room
    if script.kind == "EXCD":
        return f"RoomExitProgram({room})", "ROOM_EXIT", "ROOM_BUNDLE", room
    if script.kind == "LSCR" and script.number is not None:
        return (f"RoomLocalProgram(room={room},local={script.number})",
                "ROOM_LOCAL", "ROOM_BUNDLE", room)
    if script.kind == "OBCD" and script.object_id is not None:
        return (f"ObjectProgram(room={room},object={script.object_id})",
                "OBJECT", "ROOM_BUNDLE", room)
    return (f"OtherProgram(room={room},kind={script.kind},identity={script.identity})",
            "OTHER", "UNKNOWN", room)


def build_program_unit_model(
    scripts: dict[str, Any],
    room_compilations: dict[int, Any],
    dependency_graph: dict[str, Any],
    reachability: dict[str, Any],
) -> dict[str, Any]:
    """Project semantic executables to legacy backend program records.

    OBCD rows are also created for parsed object records with zero verb
    programs because the current generator assigns an ID if the record is
    included. The runtime cannot reference that ID after Verb_Query fails.
    This is an allocation-candidate projection, not true selector demand.
    """
    rows: dict[str, dict[str, Any]] = {}
    semantic_to_unit: dict[str, str] = {}
    object_manifest_by_room: dict[int, dict[int, dict[str, Any]]] = {}
    script_identity_by_object_verb = {
        (script.source.room, script.object_id, script.verb_id): identity
        for identity, script in scripts.items()
        if script.kind == "OBCD" and script.object_id is not None
    }

    for room_number, compilation in sorted(room_compilations.items()):
        object_manifest_by_room[room_number] = {
            int(item["object_id"]): item
            for item in compilation.record_manifest.get("objects", [])
        }
        room_ir = compilation.room_ir
        for obj in room_ir.objects:
            unit_id = f"ObjectProgram(room={room_number},object={obj.object_id})"
            manifest = object_manifest_by_room[room_number].get(obj.object_id, {})
            rows[unit_id] = {
                "identity": unit_id,
                "kind": "OBJECT",
                "residency_scope": "ROOM_BUNDLE",
                "owner": {"room": room_number, "object": obj.object_id},
                "bundle": f"RoomBundle({room_number})",
                "semantic_executable_identities": [],
                "source_provenance": [{
                    "game": next((script.source.game for script in room_ir.scripts), None),
                    "resource_key": room_ir.resource_key,
                    "source_member": room_ir.source_member,
                    "room": room_number,
                    "resource_offset": room_ir.source_container_offset,
                    "room_source_offset": room_ir.room_source_offset,
                    "object_source_offset": obj.source_offset,
                    "object_payload_offset": manifest.get("obcd_room_offset"),
                    "source_length": manifest.get("obcd_length"),
                    "source_sha256": obj.obcd_sha256,
                    "local_object_index": manifest.get("local_object_index"),
                    "verb_table_offset": manifest.get("verb_table_offset"),
                    "verb_table_length": manifest.get("verb_table_length"),
                    "cooked_record_offset": manifest.get("cooked_record_offset"),
                    "verb_entries": [
                        {"verb": verb.verb_id, "entry_offset": verb.entry_offset,
                         "semantic_identity": script_identity_by_object_verb.get(
                             (room_number, obj.object_id, verb.verb_id)),
                         "source_offset": verb.source_offset,
                         "body_sha256": verb.source_sha256}
                        for verb in obj.verbs
                    ],
                }],
                "compiled_representation": {
                    "format": "existing SC5C room object-program/OBCD record",
                    "selector_bearing": bool(obj.verbs),
                    "legacy_generator_assigns_id_if_included": True,
                    "runtime_selector_referenced": bool(obj.verbs),
                    "body_scope": "complete OBCD object resource, not one selector per verb",
                    "object_verb_entry_table": [
                        {"verb": verb.verb_id, "entry_offset": verb.entry_offset}
                        for verb in obj.verbs
                    ],
                },
                "analysis_status": "COMPLETE" if obj.verbs else "NO_SEMANTIC_VERB_BODIES",
                "reachability": "UNREACHED",
                "operations": [],
            }

    for semantic_id, script in sorted(scripts.items()):
        unit_id, kind, scope, room = _program_unit_identity(script)
        row = rows.get(unit_id)
        if row is None:
            row = {
                "identity": unit_id,
                "kind": kind,
                "residency_scope": scope,
                "owner": ({"room": room} if room is not None else {"global": script.number}),
                "bundle": f"RoomBundle({room})" if room is not None else "GlobalBundle",
                "semantic_executable_identities": [],
                "source_provenance": [],
                "compiled_representation": {
                    "format": "existing SC5C script record",
                    "selector_bearing": True,
                    "legacy_generator_assigns_id_if_included": True,
                    "runtime_selector_referenced": True,
                    "body_scope": "one complete source script body",
                },
                "analysis_status": "COMPLETE",
                "reachability": "UNREACHED",
                "operations": [],
            }
            rows[unit_id] = row
        if semantic_id in semantic_to_unit:
            raise ValueError(f"semantic executable mapped more than once: {semantic_id}")
        semantic_to_unit[semantic_id] = unit_id
        row["semantic_executable_identities"].append(semantic_id)
        row["source_provenance"].append(asdict(script.source))
        row["operations"] = sorted(set(row["operations"]) | {
            instruction.operation for instruction in script.instructions
            if instruction.operation != "opaque_bytecode_tail"
        })
        if not script.decode_complete:
            row["analysis_status"] = "PARTIAL_OPAQUE"
        elif row["analysis_status"] == "NO_SEMANTIC_VERB_BODIES":
            row["analysis_status"] = "COMPLETE"

    if set(semantic_to_unit) != set(scripts):
        raise ValueError("every semantic executable must map to exactly one ProgramUnit")

    status_by_executable = reachability.get("status_by_executable", {})
    for row in rows.values():
        row["semantic_executable_identities"].sort()
        row["source_provenance"].sort(key=lambda item: (
            item.get("source_member", ""), item.get("source_offset", -1),
            item.get("script_kind", ""), item.get("script_number") or -1,
            item.get("object_id") or -1, item.get("verb_id") or -1,
        ))
        member_statuses = [status_by_executable.get(identity, "UNRESOLVED")
                           for identity in row["semantic_executable_identities"]]
        if member_statuses:
            row["reachability"] = min(member_statuses, key=lambda value: _REACH_RANK.get(value, 4))

    unit_dependencies = []
    for edge in dependency_graph.get("edges", []):
        source = edge.get("source")
        source_unit = semantic_to_unit.get(source)
        if source_unit is None:
            continue
        target = edge.get("target")
        target_unit = semantic_to_unit.get(target) if target is not None else None
        candidate_units = sorted({semantic_to_unit[item]
                                  for item in edge.get("candidate_targets", [])
                                  if item in semantic_to_unit})
        unit_dependencies.append({
            "source_program_unit": source_unit,
            "source_semantic_identity": source,
            "target_program_unit": target_unit,
            "target_semantic_identity": target,
            "target_resource_identity": (target if target is not None and target_unit is None else None),
            "kind": edge.get("kind"),
            "domain": edge.get("domain"),
            "resolution": edge.get("resolution"),
            "source_pc": edge.get("source_pc"),
            "expression": edge.get("expression"),
            "candidate_program_units": candidate_units,
            "detail": edge.get("detail"),
        })
    unit_dependencies.sort(key=lambda item: (
        item["source_program_unit"], item["source_semantic_identity"],
        item.get("source_pc") if item.get("source_pc") is not None else -1,
        item.get("kind") or "", item.get("target_program_unit") or "",
        item.get("target_semantic_identity") or ""))
    dependencies_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dependency in unit_dependencies:
        dependencies_by_unit[dependency["source_program_unit"]].append(dependency)
    for unit_id, row in rows.items():
        row["dependencies"] = dependencies_by_unit.get(unit_id, [])

    counts = Counter(row["kind"] for row in rows.values())
    mapping_rows = [{"semantic_executable": semantic_id,
                     "program_unit": unit_id}
                    for semantic_id, unit_id in sorted(semantic_to_unit.items())]
    return {
        "schema": "same_scumm_v5_program_units_v1",
        "identity_invariant": "semantic executable identity is permanent source identity; this historical ProgramUnit projection includes backend record allocation candidates; selector_demand.py determines callable SelectorUnits; no selector value is assigned here",
        "selector_allocation_performed": False,
        "program_units": [rows[key] for key in sorted(rows)],
        "semantic_to_program_unit": mapping_rows,
        "semantic_to_program_unit_index": dict(sorted(semantic_to_unit.items())),
        "dependencies": unit_dependencies,
        "counts": {
            "semantic_executable_identities": len(scripts),
            "program_units": len(rows),
            "selector_bearing_records": sum(
                bool(row["compiled_representation"].get("selector_bearing"))
                for row in rows.values()),
            "legacy_records_with_id_if_included": sum(
                bool(row["compiled_representation"].get("legacy_generator_assigns_id_if_included"))
                for row in rows.values()),
            "by_kind": {name: counts.get(name, 0) for name in
                        ("GLOBAL", "ROOM_ENTRY", "ROOM_EXIT", "ROOM_LOCAL", "OBJECT", "OTHER")},
            "mapped_semantic_executables": len(mapping_rows),
            "semantic_identities_per_unit_max": max(
                (len(row["semantic_executable_identities"]) for row in rows.values()), default=0),
            "object_verb_semantic_identities": sum(
                len(row["semantic_executable_identities"])
                for row in rows.values() if row["kind"] == "OBJECT"),
            "object_program_units": counts.get("OBJECT", 0),
        },
    }


def build_residency_manifest(program_unit_model: dict[str, Any]) -> dict[str, Any]:
    """Emit binding needs without assigning runtime selector values."""
    units = program_unit_model["program_units"]
    global_units = [unit for unit in units if unit["kind"] == "GLOBAL"]
    room_bundles: dict[str, list[str]] = defaultdict(list)
    for unit in units:
        room = unit["owner"].get("room")
        if room is not None:
            room_bundles[unit["bundle"]].append(unit["identity"])
    dynamic_globals = sorted({target for edge in program_unit_model["dependencies"]
                              if edge["resolution"] == "DYNAMIC"
                              for target in edge["candidate_program_units"]
                              if target.startswith("GlobalProgram(")})
    unresolved = [edge for edge in program_unit_model["dependencies"]
                  if edge["resolution"] in {"UNRESOLVED", "DYNAMIC"}
                  or (edge["target_semantic_identity"] is not None
                      and edge["target_program_unit"] is None)]
    pin_reasons = [
        {"reason": "ACTIVE_SCRIPT_SLOT", "source": "C4_SLOT_PROGRAM",
         "release": "slot retires or is replaced", "identity_recoverable": "not from selector byte alone"},
        {"reason": "YIELDED_OR_DELAYED_SLOT", "source": "same active C4 slot",
         "release": "continuation resumes and retires/replaces", "identity_recoverable": "script metadata may supplement selector"},
        {"reason": "NESTED_PARENT_CONTINUATION", "source": "parent C4 slot plus parent scratch during allocation",
         "release": "child returns or parent is aborted", "identity_recoverable": "parent slot retains selector"},
        {"reason": "ROOM_TRANSITION_CONTINUATION", "source": "M23A_RETURN_PROGRAM/RETURN_SLOT/RETURN_PC plus surviving slot",
         "release": "transition transaction completes or continuation is invalidated", "identity_recoverable": "not intrinsically canonical in return byte"},
        {"reason": "CUTSCENE_OVERRIDE", "source": "C19 override PC and slot index; selector remains in owning C4 slot",
         "release": "override resumes/clears or owning slot retires", "identity_recoverable": "by owning slot only"},
        {"reason": "SENTENCE_EXECUTION", "source": "ordinary C4 slot allocated for sentence script",
         "release": "sentence script retires", "identity_recoverable": "not from selector byte alone"},
        {"reason": "ROOM_ENTRY_EXIT_DISPATCH", "source": "M23A entry/exit selector fields and active slot",
         "release": "room lifecycle phase completes; room record remains active for directory lookups", "identity_recoverable": "room record identifies lifecycle role, not portable selector mapping"},
        {"reason": "HOST_SAVE_RECONSTRUCTION", "source": "host ScriptSlot canonical resource identity/PC/locals",
         "release": "save state ends", "identity_recoverable": "yes; host serializes source identity"},
        {"reason": "EMULATOR_SAVESTATE", "source": "raw WRAM including selector bytes",
         "release": "savestate discarded; restore requires matching ROM tables", "identity_recoverable": "no without matching build mapping"},
    ]
    return {
        "schema": "same_scumm_v5_selector_free_residency_manifest_v1",
        "selector_values_emitted": False,
        "program_units": [
            {"identity": unit["identity"], "kind": unit["kind"],
             "bundle": unit["bundle"], "residency_scope": unit["residency_scope"],
             "semantic_executable_identities": unit["semantic_executable_identities"],
             "dependencies": [{"unit": edge["target_program_unit"],
                               "source_semantic": edge["source_semantic_identity"],
                               "semantic_target": edge["target_semantic_identity"],
                               "resource_target": edge["target_resource_identity"],
                               "kind": edge["kind"], "resolution": edge["resolution"],
                               "source_pc": edge["source_pc"],
                               "candidate_units": edge["candidate_program_units"]}
                              for edge in unit["dependencies"]],
             "pinning_requirements": [item["reason"] for item in pin_reasons
                                      if (unit["kind"] == "GLOBAL" and item["reason"] in {
                                          "ACTIVE_SCRIPT_SLOT", "YIELDED_OR_DELAYED_SLOT",
                                          "NESTED_PARENT_CONTINUATION", "ROOM_TRANSITION_CONTINUATION",
                                          "CUTSCENE_OVERRIDE"})
                                      or (unit["kind"] != "GLOBAL" and item["reason"] in {
                                          "ACTIVE_SCRIPT_SLOT", "NESTED_PARENT_CONTINUATION",
                                          "CUTSCENE_OVERRIDE", "SENTENCE_EXECUTION"})]}
            for unit in units
        ],
        "persistent_candidates": sorted(unit["identity"] for unit in global_units
                                         if "yield" in unit["operations"]),
        "room_bundles": {key: sorted(value) for key, value in sorted(room_bundles.items())},
        "dynamic_global_targets": dynamic_globals,
        "unresolved_residency_edges": unresolved,
        "pinning_contract": pin_reasons,
        "invariant": "source corpus size, selector-addressable ProgramUnit set, and simultaneously pinned set are separate quantities",
    }
