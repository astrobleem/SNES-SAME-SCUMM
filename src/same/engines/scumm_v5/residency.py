"""ProgramUnit-aware SCUMM executable residency and selector planning."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .program_units import build_program_unit_model


_REACH_RANK = {"ROOT": 0, "DEFINITE": 1, "CONDITIONAL": 2,
               "POSSIBLE": 3, "UNRESOLVED": 4, "UNREACHED": 5}
_SEMANTIC_SCOPE_BY_KIND = {
    "SCRP": "GLOBAL", "ENCD": "ROOM_ENTRY", "EXCD": "ROOM_EXIT",
    "LSCR": "ROOM_LOCAL", "OBCD": "OBJECT_VERB",
}


def _fit(value: int | None, capacity: int | None, epistemic: str) -> str:
    if value is None or capacity is None:
        return "UNKNOWN"
    if epistemic == "NOT_COMPARABLE":
        return "NOT_COMPARABLE"
    if value > capacity:
        return "DEFINITELY_EXCEEDS" if epistemic in {"EXACT", "STATIC_LOWER_BOUND"} else "MAY_EXCEED"
    if epistemic == "EXACT":
        return "DEFINITELY_FITS"
    if epistemic == "CONSERVATIVE_CANDIDATE_BOUND":
        return "CANDIDATE_SET_MAY_EXCEED"
    return "FITS_KNOWN_LOWER_BOUND; UNKNOWN_TAIL_REMAINS"


def _room_from_unit(unit: dict[str, Any]) -> int | None:
    room = unit.get("owner", {}).get("room")
    return None if room is None else int(room)


def _room_from_identity(identity: str | None) -> int | None:
    if not identity:
        return None
    for marker in ("RoomEntryProgram(", "RoomExitProgram("):
        if identity.startswith(marker):
            try:
                return int(identity[len(marker):-1])
            except ValueError:
                return None
    marker = "room="
    if marker in identity:
        try:
            return int(identity.split(marker, 1)[1].split(",", 1)[0].split(")", 1)[0])
        except ValueError:
            return None
    return None


def _edge_phase(edge: dict[str, Any], source_unit: dict[str, Any] | None,
                target_unit: dict[str, Any] | None) -> tuple[str, str]:
    kind = edge.get("kind")
    if edge.get("domain") == "resource":
        return "RESOURCE_CATALOG", "RESOURCE_OWNERSHIP_NOT_EXECUTION_COEXISTENCE"
    if kind == "chain_script":
        return "SCRIPT_REPLACEMENT", "REPLACEMENT_CALLER_CONTINUATION_NOT_REQUIRED"
    if kind in {"load_room", "load_room_with_ego"}:
        return "ROOM_TRANSITION", "STAGED_TARGET_ENTRY_AFTER_TRANSITION_COMMIT"
    if kind == "outgoing-room-exit":
        return "ROOM_EXIT", "OUTGOING_STAGE_ONLY"
    if kind in {"start_script", "start-object", "room-local-script"}:
        return "NESTED_OR_STARTED_EXECUTION", "MAY_COEXIST_WITH_CALLER; SCHEDULER_OVERLAP_UNKNOWN"
    if kind == "player-invocable-verb":
        return "SENTENCE_DISPATCH", "ROOM_BUNDLE_DIRECTORY_LOOKUP"
    if kind == "actor-follow-camera-room":
        return "CAMERA_SCENE_CHANGE", "DYNAMIC_SCENE_DEPENDENCY_NOT_SCRIPT_CALL"
    return "UNKNOWN", "UNKNOWN"


def build_residency_plan(
    scripts: dict[str, Any],
    dependency_graph: dict[str, Any],
    reachability: dict[str, Any],
    *,
    backend_selector_capacity: int | None,
    runtime_script_slot_capacity: int | None = 25,
    program_unit_model: dict[str, Any] | None = None,
    room_compilations: dict[int, Any] | None = None,
) -> dict[str, Any]:
    """Analyze selector addressability using backend ProgramUnits, not IR scripts.

    Semantic source corpus counts are reported alongside, never used as a
    proxy for selector demand. Runtime liveness is not inferred from a
    dependency union; scheduler slot capacity is only a hard upper bound.
    """
    if program_unit_model is None:
        program_unit_model = build_program_unit_model(
            scripts, room_compilations or {}, dependency_graph, reachability)
    units = {unit["identity"]: unit for unit in program_unit_model["program_units"]}
    semantic_to_unit = program_unit_model["semantic_to_program_unit_index"]
    statuses = reachability.get("status_by_executable", {})

    semantic_by_scope = Counter(_SEMANTIC_SCOPE_BY_KIND.get(script.kind, "UNKNOWN_DYNAMIC")
                                for script in scripts.values())
    semantic_by_room: dict[int, list[str]] = defaultdict(list)
    for identity, script in scripts.items():
        if script.kind != "SCRP":
            semantic_by_room[int(script.source.room)].append(identity)

    global_units = sorted(identity for identity, unit in units.items()
                          if unit["kind"] == "GLOBAL")
    global_edges = [edge for edge in program_unit_model["dependencies"]
                    if edge.get("domain") == "execution"
                    and edge.get("kind") in {"start_script", "chain_script"}]
    static_globals = {edge["target_program_unit"] for edge in global_edges
                      if isinstance(edge.get("target_program_unit"), str)
                      and edge["target_program_unit"].startswith("GlobalProgram(")
                      and edge.get("resolution") == "STATIC"}
    conditional_globals = {edge["target_program_unit"] for edge in global_edges
                           if isinstance(edge.get("target_program_unit"), str)
                           and edge["target_program_unit"].startswith("GlobalProgram(")
                           and edge.get("resolution") == "CONDITIONAL_STATIC"}
    dynamic_global_edges = [edge for edge in global_edges
                            if edge.get("resolution") == "DYNAMIC"]
    dynamic_globals = {target for edge in dynamic_global_edges
                       for target in edge.get("candidate_program_units", [])
                       if target.startswith("GlobalProgram(")}

    global_records = []
    yield_candidates = []
    yield_transition_candidates = []
    global_reach_counts: Counter[str] = Counter()
    for unit_id in global_units:
        unit = units[unit_id]
        identity = unit["semantic_executable_identities"][0] if unit["semantic_executable_identities"] else None
        script = scripts.get(identity)
        operations = set(unit.get("operations", []))
        reaches = unit.get("reachability", "UNRESOLVED")
        global_reach_counts[reaches] += 1
        has_yield = "yield" in operations
        has_transition = bool(operations & {"load_room", "load_room_with_ego"})
        if has_yield:
            yield_candidates.append(unit_id)
        if has_yield and has_transition:
            yield_transition_candidates.append(unit_id)
        global_records.append({
            "program_unit": unit_id,
            "semantic_identity": identity,
            "reachability": reaches,
            "analysis_status": unit["analysis_status"],
            "may_yield": has_yield,
            "contains_room_transition": has_transition,
            "may_retain_identity_across_room_change": has_yield,
            "evidence_scope": "OPERATION_PRESENCE_ONLY_NOT_PROOF_OF_LIVE_OVERLAP",
        })

    room_units: dict[int, set[str]] = defaultdict(set)
    for unit_id, unit in units.items():
        room = _room_from_unit(unit)
        if room is not None:
            room_units[room].add(unit_id)
    indexed_rooms: set[int] = set()
    for node in dependency_graph.get("nodes", []):
        if node.get("node_type") == "resource" and node.get("category") == "room":
            try:
                indexed_rooms.add(int(node["identity"].removeprefix("RoomResource(").removesuffix(")")))
            except (KeyError, ValueError):
                pass
    unparsed_rooms = sorted(indexed_rooms - set(room_units))

    dependency_unit_rows = []
    for edge in program_unit_model["dependencies"]:
        source_unit = units.get(edge["source_program_unit"])
        target_unit = units.get(edge["target_program_unit"] or "")
        phase, coexistence = _edge_phase(edge, source_unit, target_unit)
        source_room = _room_from_unit(source_unit) if source_unit else None
        target_room = _room_from_unit(target_unit) if target_unit else _room_from_identity(
            edge.get("target_semantic_identity"))
        dependency_unit_rows.append({
            **edge,
            "caller_scope": source_unit.get("residency_scope") if source_unit else "UNKNOWN",
            "callee_scope": target_unit.get("residency_scope") if target_unit else "UNKNOWN",
            "phase": phase,
            "coexistence": coexistence,
            "crosses_room_partition": bool(
                source_room is not None and target_room is not None
                and source_room != target_room),
        })

    room_rows = []
    for room in sorted(room_units):
        unit_ids = room_units[room]
        counts = Counter(units[unit_id]["kind"] for unit_id in unit_ids)
        semantic_ids = sorted(semantic_by_room.get(room, []))
        object_verb_ids = [identity for identity in semantic_ids
                           if scripts[identity].kind == "OBCD"]
        direct_static: set[str] = set()
        direct_conditional: set[str] = set()
        direct_dynamic: set[str] = set()
        dynamic_rows = []
        cross_targets: set[str] = set()
        for edge in program_unit_model["dependencies"]:
            if edge["source_program_unit"] not in unit_ids:
                continue
            if edge.get("kind") in {"start_script", "chain_script"}:
                target = edge.get("target_program_unit")
                if target and target.startswith("GlobalProgram("):
                    if edge.get("resolution") == "STATIC":
                        direct_static.add(target)
                    elif edge.get("resolution") == "CONDITIONAL_STATIC":
                        direct_conditional.add(target)
                if edge.get("resolution") == "DYNAMIC":
                    candidates = {value for value in edge.get("candidate_program_units", [])
                                  if value.startswith("GlobalProgram(")}
                    direct_dynamic.update(candidates)
                    dynamic_rows.append({
                        "source_program_unit": edge["source_program_unit"],
                        "source_semantic_identity": edge["source_semantic_identity"],
                        "source_pc": edge.get("source_pc"),
                        "candidate_program_units": sorted(candidates),
                        "expression": edge.get("expression"),
                    })
            target = edge.get("target_program_unit")
            target_room = _room_from_identity(target) if target else None
            if target_room is not None and target_room != room and edge.get("kind") in {
                "load_room", "load_room_with_ego", "actor-follow-camera-room",
                "actor-placement-room"}:
                cross_targets.add(target)

        static_units = unit_ids | direct_static | direct_conditional
        candidate_units = static_units | direct_dynamic
        unknown_local_tail = any(units[unit_id]["analysis_status"] == "PARTIAL_OPAQUE"
                                 for unit_id in unit_ids)
        unresolved_static_target = any(
            edge["source_program_unit"] in unit_ids
            and edge.get("target_semantic_identity") is not None
            and edge.get("target_program_unit") is None
            and edge.get("resolution") == "UNRESOLVED"
            for edge in program_unit_model["dependencies"]
        )
        static_epistemic = ("STATIC_LOWER_BOUND"
                            if unknown_local_tail or unresolved_static_target
                            else "EXACT")
        room_rows.append({
            "room": room,
            "bundle": f"RoomBundle({room})",
            "semantic_executable_identities": semantic_ids,
            "semantic_executable_count": len(semantic_ids),
            "semantic_object_verb_count": len(object_verb_ids),
            "program_unit_identities": sorted(unit_ids),
            "program_unit_count": len(unit_ids),
            "room_lifecycle_units": counts.get("ROOM_ENTRY", 0) + counts.get("ROOM_EXIT", 0),
            "room_entry_units": counts.get("ROOM_ENTRY", 0),
            "room_exit_units": counts.get("ROOM_EXIT", 0),
            "local_units": counts.get("ROOM_LOCAL", 0),
            "object_units": counts.get("OBJECT", 0),
            "other_units": counts.get("OTHER", 0),
            "global_program_units_required": sorted(direct_static | direct_conditional),
            "global_dependency_scope": (
                "direct static/conditional StartScript or chainScript targets from this room bundle; "
                "global-to-global targets are represented in the global resolver sets, not folded "
                "into this room-local count"
            ),
            "static_global_program_units": sorted(direct_static),
            "conditional_global_program_units": sorted(direct_conditional),
            "dynamic_global_candidate_units": sorted(direct_dynamic),
            "dynamic_dependencies": dynamic_rows,
            "cross_room_dependencies": sorted(cross_targets),
            "total_static_addressable_program_units": {
                "value": len(static_units), "epistemic": static_epistemic,
                "selector_capacity_fit": _fit(len(static_units), backend_selector_capacity,
                                               static_epistemic),
                "members": sorted(static_units),
            },
            "total_conservative_candidate_program_units": {
                "value": len(candidate_units), "epistemic": "CONSERVATIVE_CANDIDATE_BOUND",
                "selector_capacity_fit": _fit(len(candidate_units), backend_selector_capacity,
                                               "CONSERVATIVE_CANDIDATE_BOUND"),
                "members": sorted(candidate_units),
                "scope": "decoded static/conditional targets plus decoded dynamic candidate universe; not simultaneously live; opaque tails may add targets",
            },
            "simultaneous_residency": {
                "value": None, "epistemic": "UNKNOWN",
                "active_descriptor_upper_bound": runtime_script_slot_capacity,
                "reason": "dependency/addressability sets do not prove scheduler overlap; each live activation pins its ProgramUnit, while inactive bundle entries resolve on demand",
            },
            "opaque_program_units": sorted(unit_id for unit_id in unit_ids
                                            if units[unit_id]["analysis_status"] == "PARTIAL_OPAQUE"),
        })
    room_rows.sort(key=lambda row: (-row["program_unit_count"], row["room"]))

    all_unit_ids = set(units)
    total_semantic = len(scripts)
    max_room = room_rows[0] if room_rows else None
    maximum_static = max((row["total_static_addressable_program_units"]["value"]
                          for row in room_rows), default=0)
    maximum_candidate = max((row["total_conservative_candidate_program_units"]["value"]
                             for row in room_rows), default=0)
    largest_static_room = max(room_rows, key=lambda row: (
        row["total_static_addressable_program_units"]["value"], -row["room"]), default=None)
    largest_candidate_room = max(room_rows, key=lambda row: (
        row["total_conservative_candidate_program_units"]["value"], -row["room"]), default=None)

    transitions = []
    for edge in dependency_unit_rows:
        if edge.get("kind") not in {"load_room", "load_room_with_ego"}:
            continue
        outgoing = _room_from_identity(edge.get("source_program_unit"))
        incoming = _room_from_identity(edge.get("target_program_unit"))
        if incoming is None:
            incoming = _room_from_identity(edge.get("target_semantic_identity"))
        outgoing_size = len(room_units.get(outgoing, ())) if outgoing is not None else None
        incoming_size = len(room_units.get(incoming, ())) if incoming is not None else None
        transitions.append({
            "source_program_unit": edge["source_program_unit"],
            "source_semantic_identity": edge["source_semantic_identity"],
            "source_pc": edge.get("source_pc"),
            "outgoing_room": outgoing,
            "incoming_room": incoming,
            "resolution": edge["resolution"],
            "lifecycle": ["OUTGOING_EXECUTION", "OUTGOING_EXCD", "ROOM_COMMIT", "INCOMING_ENCD"],
            "bundle_overlap": "NOT_REQUIRED_BY_STAGED_ROOM_LIFECYCLE",
            "addressable_program_units": {
                "value": max(outgoing_size, incoming_size)
                if outgoing_size is not None and incoming_size is not None else None,
                "epistemic": "STATIC_LOWER_BOUND",
            },
            "surviving_activation_bindings": "UNKNOWN; preserve canonical identity for surviving global slots",
        })

    active_bound = runtime_script_slot_capacity
    unit_kind_counts = Counter(unit["kind"] for unit in units.values())
    semantic_kind_counts = Counter(_SEMANTIC_SCOPE_BY_KIND.get(script.kind, "OTHER")
                                   for script in scripts.values())
    live_binding = {
        "value": None,
        "epistemic": "UNKNOWN",
        "upper_bound": active_bound,
        "upper_bound_epistemic": "EXACT_RUNTIME_DESCRIPTOR_LIMIT" if active_bound is not None else "UNKNOWN",
        "interpretation": "No static schedule proves an exact concurrent ProgramUnit count. Under the proposed resolve-on-activation contract, distinct selector pins cannot exceed live C4 activations; room bundle catalog entries use local unit indices, not pins.",
    }
    scenarios = [
        {"name": "largest_room_bundle", "value": max_room["program_unit_count"] if max_room else 0,
         "epistemic": "STATIC_LOWER_BOUND" if unparsed_rooms else "EXACT",
         "comparison": "ADDRESSABLE_PROGRAM_UNIT_SET"},
        {"name": "largest_room_plus_static_and_conditional_globals",
         "value": largest_static_room["total_static_addressable_program_units"]["value"]
         if largest_static_room else 0,
         "epistemic": largest_static_room["total_static_addressable_program_units"]["epistemic"]
         if largest_static_room else "UNKNOWN",
         "comparison": "ADDRESSABLE_PROGRAM_UNIT_SET"},
        {"name": "largest_room_plus_decoded_dynamic_candidate_universe",
         "value": largest_candidate_room["total_conservative_candidate_program_units"]["value"]
         if largest_candidate_room else 0,
         "epistemic": "CONSERVATIVE_CANDIDATE_BOUND",
         "comparison": "CANDIDATE_UNIVERSE_NOT_SIMULTANEOUS_RESIDENCY"},
        {"name": "whole_known_program_unit_corpus_if_single_static_map",
         "value": len(all_unit_ids),
         "epistemic": "STATIC_LOWER_BOUND" if unparsed_rooms else "EXACT",
         "comparison": "ADDRESSABLE_PROGRAM_UNIT_SET_IF_ALL_COMPILED_TO_ONE_MAP"},
        {"name": "simultaneously_pinned_live_activations",
         "value": None, "epistemic": "UNKNOWN",
         "upper_bound": active_bound,
         "comparison": "SIMULTANEOUS_RESIDENCY"},
    ]
    for scenario in scenarios:
        scenario["selector_capacity_fit"] = _fit(
            scenario.get("value"), backend_selector_capacity, scenario["epistemic"])

    global_reach = Counter(unit["reachability"] for unit in units.values()
                           if unit["kind"] == "GLOBAL")
    semantic_identity_records = program_unit_model["semantic_to_program_unit"]
    dynamic_candidate_union = sorted({target for edge in dynamic_global_edges
                                      for target in edge.get("candidate_program_units", [])
                                      if target.startswith("GlobalProgram(")})
    unresolved_edges = [edge for edge in dependency_unit_rows
                        if edge.get("resolution") in {"DYNAMIC", "UNRESOLVED"}
                        or edge.get("target_semantic_identity") is not None
                        and edge.get("target_program_unit") is None]

    pin_causes = [
        {"cause": "active_script_slot", "state": "SAME_SCUMM_C4_SLOT_PROGRAM (25 byte entries)",
         "lifetime": "activation allocation through stop/replacement/retirement",
         "release": "slot is cleared or safely replaced", "canonical_identity_currently_stored": "not as a standalone identity; slot number/ownership context accompanies byte"},
        {"cause": "yielded_or_delayed_slot", "state": "same occupied C4 slot retains program selector, PC, delay, locals",
         "lifetime": "across scheduler frames until resumed and retired", "release": "resume then retire/replace",
         "canonical_identity_currently_stored": "not in selector field"},
        {"cause": "nested_parent_child", "state": "parent and child C4 slot program bytes; C4_PARENT_PROGRAM is temporary allocation scratch",
         "lifetime": "both activations until child returns or parent is aborted", "release": "child return/stop or lifecycle retirement",
         "canonical_identity_currently_stored": "not in selector bytes"},
        {"cause": "room_transition_continuation", "state": "M23A_RETURN_PROGRAM/RETURN_SLOT/RETURN_PC plus surviving C4 slot",
         "lifetime": "pending room transaction; room/local caller may be invalidated, global caller may survive",
         "release": "transaction completion or invalidation", "canonical_identity_currently_stored": "no; return program is a selector scratch snapshot"},
        {"cause": "cutscene_override", "state": "C19_OVERRIDE_PC and C19_OVERRIDE_SLOT; owning selector remains in C4_SLOT_PROGRAM",
         "lifetime": "until override resumes/clears or slot retires", "release": "override completion or slot retirement",
         "canonical_identity_currently_stored": "through owning slot only"},
        {"cause": "sentence_script", "state": "ordinary C4 slot program selector allocated by sentence dispatch",
         "lifetime": "sentence activation", "release": "sentence script retirement",
         "canonical_identity_currently_stored": "not in selector field"},
        {"cause": "room_entry_exit_directory", "state": "M23A_ENTRY_PROGRAM/EXIT_PROGRAM selector snapshots and generated room record",
         "lifetime": "active room lifecycle/resource directory use", "release": "room record replacement",
         "canonical_identity_currently_stored": "room identity/record provides context; selector itself is not relocatable"},
        {"cause": "host_save", "state": "host ScriptSlot serializes resource/script identity, PC, locals and scheduler state",
         "lifetime": "portable host save", "release": "save discarded", "canonical_identity_currently_stored": "yes"},
        {"cause": "emulator_savestate", "state": "raw WRAM snapshot contains selector bytes",
         "lifetime": "savestate lifetime", "release": "discard snapshot", "canonical_identity_currently_stored": "only recoverable with matching ROM/program tables"},
    ]

    return {
        "schema": "same_scumm_v5_program_unit_residency_v2",
        "identity_layers": {
            "semantic_executable": "canonical source-level SCUMM body identity; preserved per script/verb",
            "program_unit": "selector-bearing backend body/table unit; object OBCD may contain multiple semantic verb scripts",
            "resident_binding": "temporary mapping from ProgramUnit identity to a currently assigned selector",
            "selector": "byte handle consumed by existing VM fetch/size dispatch; not a semantic identity",
            "bundle": "resource ownership/loading group; current room bundle includes lifecycle, locals and object OBCD units",
            "pin": "reason an active continuation/dispatch reference forbids reassignment of its ResidentBinding",
        },
        "counts": {
            "semantic_executable_identities": total_semantic,
            "semantic_by_scope": {name: semantic_kind_counts.get(name, 0) for name in
                                  ("GLOBAL", "ROOM_ENTRY", "ROOM_EXIT", "ROOM_LOCAL", "OBJECT_VERB", "OTHER", "UNKNOWN_DYNAMIC")},
            "program_units": len(units),
            "program_units_by_kind": {name: unit_kind_counts.get(name, 0) for name in
                                      ("GLOBAL", "ROOM_ENTRY", "ROOM_EXIT", "ROOM_LOCAL", "OBJECT", "OTHER")},
            "semantic_identities_mapped_exactly_once": len(semantic_identity_records),
            "unparsed_indexed_rooms": unparsed_rooms,
        },
        "global_program_units": {
            "available": len(global_units),
            "reachability_counts": {name: global_reach.get(name, 0) for name in
                                    ("ROOT", "DEFINITE", "CONDITIONAL", "POSSIBLE", "UNRESOLVED", "UNREACHED")},
            "definitely_reachable": sorted(unit["identity"] for unit in units.values()
                                            if unit["kind"] == "GLOBAL" and unit["reachability"] in {"ROOT", "DEFINITE"}),
            "conditionally_reachable": sorted(unit["identity"] for unit in units.values()
                                               if unit["kind"] == "GLOBAL" and unit["reachability"] == "CONDITIONAL"),
            "possible_or_unresolved": sorted(unit["identity"] for unit in units.values()
                                              if unit["kind"] == "GLOBAL" and unit["reachability"] in {"POSSIBLE", "UNRESOLVED"}),
            "static_targets": sorted(static_globals),
            "conditional_static_targets": sorted(conditional_globals),
            "dynamic_candidate_universe": dynamic_candidate_union,
            "dynamic_candidate_universe_count": len(dynamic_candidate_union),
            "yield_capable": sorted(yield_candidates),
            "room_transition_capable_with_yield": sorted(yield_transition_candidates),
            "potential_cross_room_identity_retention": sorted(yield_candidates),
            "simultaneously_active_global_units": live_binding,
            "records": global_records,
        },
        "room_bundles": room_rows,
        "program_unit_dependencies": dependency_unit_rows,
        "working_set_questions": {
            "A_source_corpus": {"semantic_executable_identities": total_semantic,
                                 "program_units": len(units),
                                 "epistemic": "STATIC_LOWER_BOUND_IF_ROOMS_UNPARSED" if unparsed_rooms else "EXACT"},
            "B_addressable_program_unit_set": {
                "largest_room_bundle": None if max_room is None else max_room["program_unit_count"],
                "largest_static_room_plus_global_units": maximum_static,
                "largest_decoded_dynamic_candidate_set": maximum_candidate,
                "whole_corpus_single_static_map": len(units),
                "selector_capacity": backend_selector_capacity,
            },
            "C_simultaneously_live_or_pinned": live_binding,
        },
        "selector_capacity": {
            "capacity": backend_selector_capacity,
            "scenarios": scenarios,
            "largest_room_bundle_exceeds": (None if backend_selector_capacity is None else
                [row["room"] for row in room_rows if row["program_unit_count"] > backend_selector_capacity]),
            "static_addressability_exceeds": (None if backend_selector_capacity is None else
                [row["room"] for row in room_rows
                 if row["total_static_addressable_program_units"]["value"] > backend_selector_capacity]),
            "dynamic_candidate_bound_may_exceed": (None if backend_selector_capacity is None else
                [row["room"] for row in room_rows
                 if row["total_conservative_candidate_program_units"]["value"] > backend_selector_capacity]),
            "interpretation": "Compare selector capacity only with selector-bearing ProgramUnit addressability sets, never semantic executable identity counts or dynamic candidate universes interpreted as live sets.",
        },
        "simultaneous_residency": {
            "largest_proven_exact_set": {"value": None, "epistemic": "UNKNOWN",
                                         "reason": "Static dependency edges do not establish which activations overlap at runtime."},
            "distinct_active_binding_upper_bound": live_binding,
            "room_transition": "outgoing EXCD/cleanup then commit then incoming ENCD; only surviving activation ProgramUnits remain pinned across the staged handoff",
        },
        "pinning_contract": {
            "causes": pin_causes,
            "selector_reuse_invariant": "A selector may be rebound only after every live slot, continuation, transaction, and directory reference to its old ProgramUnit is removed or represented by a canonical identity that can be resolved again.",
            "current_selector_references": [
                "C4_SLOT_PROGRAM: durable per-activation selector (25 entries)",
                "PROGRAM_SELECT: current fetch/dispatch scratch",
                "C4_PARENT_PROGRAM: temporary nested-allocation scratch copied from parent slot",
                "M23A_RETURN_PROGRAM: pending room transaction selector snapshot, paired with return slot/validity/PC",
                "M23A_ENTRY_PROGRAM/EXIT_PROGRAM: active lifecycle selector snapshots",
                "C19 override records: store PC and slot index; rely on that slot's selector rather than storing another selector",
                "scenario return-program fields: fixture/diagnostic-gated snapshots, not portable production identity",
            ],
        },
        "save_restore": {
            "host_save": "serializes canonical source resource/script identity, PC, locals and scheduler state; reconstructs body from provider",
            "native_custom_save": "current custom envelope does not serialize live C4 script slots; not a portable active-selector save",
            "emulator_savestate": "raw WRAM preserves ephemeral selector bytes; restore requires the exact compatible ROM/program tables",
            "future_portable_save_recommendation": "serialize canonical ProgramUnit identity and PC/locals/ownership/continuation graph; resolve and pin bindings during restore",
        },
        "dynamic_resolution_policy": {
            "global": "resolve canonical GlobalProgram identity on invocation; bind/pin only the selected target, not its entire candidate universe",
            "room_local": "resolve RoomLocalProgram through the active RoomBundle directory/local index",
            "object_verb": "resolve semantic verb through active ObjectProgram's entry table; the OBCD unit is the selector-bearing target",
            "room_transition": "load target room bundle after outgoing stage; do not require both complete room bundles resident",
            "exhaustion": "never reuse a pinned selector; return/defer a deterministic capacity failure or suspend resolution until a binding can be released",
        },
        "residency_manifest_contract": {
            "manifest_file": "residency_manifest.json",
            "selector_values": "none",
            "contains": ["ProgramUnit identities", "room bundle membership", "global resolver candidates", "cross-bundle dependencies", "pinning requirements", "unresolved edges"],
        },
        "recommendation": {
            "choice": "B",
            "model": "canonical ProgramUnit identity -> bundle identity/local unit index -> ResidentBinding -> ephemeral selector",
            "reason": "Object-verb semantic multiplicity reduces materially at the backend-unit layer, but the complete source ProgramUnit corpus still exceeds 178 and the current immutable build-global selector map cannot page/reuse IDs. A small resolver/binder is needed to compile/load partitions safely while pinning live activations.",
            "not_implemented": True,
        },
        "next_milestone": {
            "recommendation": "Generate a selector-free ProgramUnit directory with bundle-local unit indices, then validate a generic binding/pinning simulator contract before changing the native ABI.",
            "scope": "compiler manifest plus resolver contract; no production runtime paging yet",
        },
        "uncertainty": {
            "unparsed_rooms": unparsed_rooms,
            "opaque_or_partial_units": sorted(unit["identity"] for unit in units.values()
                                                if unit["analysis_status"] == "PARTIAL_OPAQUE"),
            "unresolved_residency_edge_count": len(unresolved_edges),
            "effect": "ProgramUnit mapping is exact for parsed resources; whole-game counts are lower bounds while rooms remain unparsed. Dynamic candidate universes and static addressability are not runtime liveness proofs.",
        },
    }
