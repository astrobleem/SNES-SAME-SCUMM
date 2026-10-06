"""Conservative executable-residency and backend partition planning.

Source identities remain game-wide and selector-free. This report estimates
which source executables a room/resource partition must address; it does not
allocate backend selectors or claim a precise runtime scheduler maximum.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


_SCOPE_BY_KIND = {
    "SCRP": "GLOBAL",
    "ENCD": "ROOM_ENTRY",
    "EXCD": "ROOM_EXIT",
    "LSCR": "ROOM_LOCAL",
    "OBCD": "OBJECT_VERB",
}
_RANK = {"ROOT": 0, "DEFINITE": 1, "CONDITIONAL": 2,
         "POSSIBLE": 3, "UNRESOLVED": 4, "UNREACHED": 5}


def _scope(script: Any) -> str:
    return _SCOPE_BY_KIND.get(script.kind, "UNKNOWN_DYNAMIC")


def _epistemic_fit(value: int | None, capacity: int | None,
                   epistemic: str) -> str:
    if value is None or capacity is None:
        return "UNKNOWN"
    if value > capacity:
        return "DEFINITELY_EXCEEDS" if epistemic in {"EXACT", "STATIC_LOWER_BOUND"} else "MAY_EXCEED"
    if epistemic == "EXACT":
        return "DEFINITELY_FITS"
    if epistemic == "CONSERVATIVE_UPPER_BOUND":
        return "CONSERVATIVELY_FITS"
    return "FITS_KNOWN_SUBSET; UPPER_BOUND_UNRESOLVED"


def _global_identity(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("GlobalScript(")


def _edge_residency(edge: dict[str, Any], scopes: dict[str, str]) -> dict[str, Any]:
    source, target = edge.get("source"), edge.get("target")
    kind, resolution = edge.get("kind"), edge.get("resolution")
    caller_scope = scopes.get(source, "UNKNOWN_DYNAMIC")
    callee_scope = scopes.get(target, "UNKNOWN_DYNAMIC") if target else "UNKNOWN_DYNAMIC"
    if edge.get("domain") == "resource":
        coexistence = "RESOURCE_OWNERSHIP_NOT_EXECUTION_COEXISTENCE"
        phase = "RESOURCE_CATALOG"
    elif kind == "chain_script":
        coexistence = "REPLACEMENT; CALLER_CONTINUATION_NOT_REQUIRED_AFTER_CHAIN"
        phase = "SCRIPT_REPLACEMENT"
    elif kind in {"load_room", "load_room_with_ego"}:
        coexistence = "STAGED; TARGET_ENTRY_FOLLOWS_TRANSITION_COMMIT"
        phase = "ROOM_TRANSITION"
    elif kind == "outgoing-room-exit":
        coexistence = "OUTGOING_STAGE_ONLY"
        phase = "ROOM_EXIT"
    elif kind in {"start_script", "start-object", "room-local-script"}:
        coexistence = ("MAY_COEXIST_WITH_CALLER; exact live overlap is scheduler-dependent"
                       if target != source else
                       "SAME-IDENTITY REPLACEMENT RULE MAY REMOVE OLD CONTINUATION")
        phase = "NESTED_OR_STARTED_EXECUTION"
    elif kind == "player-invocable-verb":
        coexistence = "ROOM_DIRECTORY_LOOKUP; invocation may occur after entry script retires"
        phase = "SENTENCE_DISPATCH"
    elif kind == "actor-follow-camera-room":
        coexistence = "DYNAMIC_SCENE_DEPENDENCY; NOT A SCRIPT CALL"
        phase = "CAMERA_SCENE_CHANGE"
    else:
        coexistence = "UNKNOWN"
        phase = "UNKNOWN"
    return {
        "source": source,
        "target": target,
        "kind": kind,
        "resolution": resolution,
        "source_pc": edge.get("source_pc"),
        "caller_scope": caller_scope,
        "callee_scope": callee_scope,
        "phase": phase,
        "coexistence": coexistence,
        "crosses_room_partition": (
            caller_scope.startswith("ROOM_") and
            (callee_scope == "GLOBAL" or callee_scope.startswith("ROOM_") and
             target is not None and source is not None and
             _identity_room(source) != _identity_room(target))
        ) if target else None,
        "candidate_targets": edge.get("candidate_targets", []),
        "expression": edge.get("expression"),
    }


def _identity_room(identity: str | None) -> int | None:
    if not identity:
        return None
    if identity.startswith("RoomEntry(") or identity.startswith("RoomExit("):
        try:
            return int(identity[identity.index("(") + 1:-1])
        except ValueError:
            return None
    marker = "room="
    if marker in identity:
        try:
            return int(identity.split(marker, 1)[1].split(",", 1)[0].split(")", 1)[0])
        except ValueError:
            return None
    return None


def build_residency_plan(
    scripts: dict[str, Any],
    dependency_graph: dict[str, Any],
    reachability: dict[str, Any],
    *,
    backend_selector_capacity: int | None,
    runtime_script_slot_capacity: int | None = 25,
) -> dict[str, Any]:
    """Build deterministic source-identity residency estimates.

    Room bundles describe executable directory/address demand, not the count
    of scripts simultaneously active in C4 slots. The report keeps those
    quantities separate and labels every estimate epistemically.
    """
    scopes = {identity: _scope(script) for identity, script in scripts.items()}
    statuses = reachability.get("status_by_executable", {})
    by_scope = Counter(scopes.values())
    by_room: dict[int, list[str]] = defaultdict(list)
    for identity, script in scripts.items():
        if script.kind != "SCRP":
            by_room[int(script.source.room)].append(identity)
    for identities in by_room.values():
        identities.sort()

    execution_edges = [edge for edge in dependency_graph.get("edges", [])
                       if edge.get("domain") == "execution"]
    residency_edges = [_edge_residency(edge, scopes)
                       for edge in execution_edges]

    global_ids = sorted(identity for identity, scope in scopes.items() if scope == "GLOBAL")
    indexed_room_ids: set[int] = set()
    for node in dependency_graph.get("nodes", []):
        identity = node.get("identity", "")
        if node.get("node_type") != "resource" or node.get("category") != "room":
            continue
        try:
            indexed_room_ids.add(int(identity.removeprefix("RoomResource(").removesuffix(")")))
        except ValueError:
            continue
    unparsed_rooms = sorted(indexed_room_ids - set(by_room))
    global_static: set[str] = set()
    global_conditional: set[str] = set()
    global_dynamic_candidates: set[str] = set()
    dynamic_global_edge_count = 0
    for edge in execution_edges:
        if edge.get("kind") not in {"start_script", "chain_script"}:
            continue
        target = edge.get("target")
        resolution = edge.get("resolution")
        if _global_identity(target):
            if resolution == "STATIC":
                global_static.add(target)
            elif resolution == "CONDITIONAL_STATIC":
                global_conditional.add(target)
        if resolution == "DYNAMIC":
            candidates = {item for item in edge.get("candidate_targets", [])
                          if _global_identity(item)}
            if candidates:
                dynamic_global_edge_count += 1
                global_dynamic_candidates.update(candidates)

    global_rows: list[dict[str, Any]] = []
    persistent_candidates: list[str] = []
    transition_capable_globals: list[str] = []
    opaque_global_identities: list[str] = []
    for identity in global_ids:
        script = scripts[identity]
        operations = {instruction.operation for instruction in script.instructions
                      if instruction.operation != "opaque_bytecode_tail"}
        has_yield = "yield" in operations
        has_transition = bool(operations & {"load_room", "load_room_with_ego"})
        if not script.decode_complete:
            opaque_global_identities.append(identity)
        if has_yield:
            persistent_candidates.append(identity)
        if has_yield and has_transition:
            transition_capable_globals.append(identity)
        global_rows.append({
            "identity": identity,
            "reachability": statuses.get(identity, "UNRESOLVED"),
            "may_yield": has_yield,
            "contains_room_transition": has_transition,
            "may_retain_identity_across_room_change": has_yield,
            "evidence_scope": "OPERATION_PRESENCE_ONLY_NOT_PROOF_OF_LIVE_OVERLAP",
        })

    room_rows: list[dict[str, Any]] = []
    room_identities: dict[int, set[str]] = {}
    max_direct_demand = 0
    max_conservative_demand = 0
    for room, identities in sorted(by_room.items()):
        identity_set = set(identities)
        room_identities[room] = identity_set
        counts = Counter(scopes[item] for item in identities)
        direct_static: set[str] = set()
        direct_conditional: set[str] = set()
        dynamic_global: set[str] = set()
        dynamic_edges = []
        cross_room_targets: set[str] = set()
        for edge in execution_edges:
            if edge.get("source") not in identity_set:
                continue
            if edge.get("kind") in {"start_script", "chain_script"}:
                target = edge.get("target")
                if _global_identity(target):
                    if edge.get("resolution") == "STATIC":
                        direct_static.add(target)
                    elif edge.get("resolution") == "CONDITIONAL_STATIC":
                        direct_conditional.add(target)
                if edge.get("resolution") == "DYNAMIC":
                    candidates = {item for item in edge.get("candidate_targets", [])
                                  if _global_identity(item)}
                    dynamic_global.update(candidates)
                    dynamic_edges.append({"source": edge["source"],
                                          "source_pc": edge.get("source_pc"),
                                          "kind": edge.get("kind"),
                                          "candidate_global_count": len(candidates),
                                          "expression": edge.get("expression")})
            if edge.get("kind") in {"load_room", "load_room_with_ego",
                                    "actor-follow-camera-room"}:
                target = edge.get("target")
                target_room = _identity_room(target) if target else None
                if target_room is not None and target_room != room:
                    cross_room_targets.add(target)
        direct_demand = len(identity_set | direct_static | direct_conditional)
        dynamic_demand = len(identity_set | direct_static | direct_conditional | dynamic_global)
        max_direct_demand = max(max_direct_demand, direct_demand)
        max_conservative_demand = max(max_conservative_demand, dynamic_demand)
        room_rows.append({
            "room": room,
            "executable_identities": identities,
            "counts": {name: counts.get(name, 0) for name in (
                "ROOM_ENTRY", "ROOM_EXIT", "ROOM_LOCAL", "OBJECT_VERB",
                "OTHER_RESOURCE_LOCAL", "UNKNOWN_DYNAMIC")},
            "room_bundle_executable_count": len(identities),
            "room_bundle_count_epistemic": "EXACT_FOR_PARSED_ROOM_RESOURCE",
            "opaque_executable_identities": sorted(
                item for item in identities if not scripts[item].decode_complete),
            "direct_global_dependencies": sorted(direct_static),
            "conditional_global_candidates": sorted(direct_conditional),
            "dynamic_global_candidates": sorted(dynamic_global),
            "dynamic_script_edges": dynamic_edges,
            "cross_room_dependencies": sorted(cross_room_targets),
            "room_plus_decoded_global_targets": {
                "value": direct_demand, "epistemic": "STATIC_LOWER_BOUND",
                "scope": "union of decoded static and conditional-static global targets; opaque and dynamic dependencies are separate",
                "selector_capacity_fit": _epistemic_fit(
                    direct_demand, backend_selector_capacity, "STATIC_LOWER_BOUND"),
            },
            "room_plus_dynamic_global_candidates": {
                "value": dynamic_demand,
                "epistemic": "CONSERVATIVE_UPPER_BOUND",
                "scope": "selector-addressability if every decoded direct/conditional and dynamic global candidate is prebound; not simultaneous liveness, and opaque tails may add targets",
                "selector_capacity_fit": _epistemic_fit(
                    dynamic_demand, backend_selector_capacity, "CONSERVATIVE_UPPER_BOUND"),
            },
        })

    room_rows.sort(key=lambda row: (-row["room_bundle_executable_count"], row["room"]))
    largest = room_rows[0] if room_rows else None
    global_root_definite = sorted(identity for identity in global_ids
                                  if statuses.get(identity) in {"ROOT", "DEFINITE"})
    global_conditional_reach = sorted(identity for identity in global_ids
                                      if statuses.get(identity) == "CONDITIONAL")
    global_possible_reach = sorted(identity for identity in global_ids
                                   if statuses.get(identity) in {"POSSIBLE", "UNRESOLVED"})
    global_reach_counts = Counter(statuses.get(identity, "UNRESOLVED")
                                  for identity in global_ids)
    selector_demand_for_largest = None if largest is None else largest[
        "room_plus_decoded_global_targets"]["value"]
    all_globals_plus_largest = (None if largest is None else
                                len(set(largest["executable_identities"]) | set(global_ids)))
    max_live_global_activations = (None if runtime_script_slot_capacity is None else
                                   min(len(global_ids), runtime_script_slot_capacity))

    # Static selector directories bind every selected executable to a unique
    # build-global byte. A future paged resolver can instead pin code identities
    # needed by active C4 descriptors, whose current limit is a separate fact.
    capacity_scenarios = [
        {"name": "largest_room_directory_alone", "value": 0 if largest is None else
         largest["room_bundle_executable_count"],
         "epistemic": "STATIC_LOWER_BOUND" if unparsed_rooms else "EXACT",
         "scope": "largest among parsed rooms"},
        {"name": "largest_room_plus_decoded_global_targets",
         "value": selector_demand_for_largest,
         "epistemic": "STATIC_LOWER_BOUND",
         "scope": "known references; opaque and dynamic dependencies are not counted"},
        {"name": "largest_room_plus_all_global_bodies",
         "value": all_globals_plus_largest,
         "epistemic": "CONSERVATIVE_UPPER_BOUND",
         "scope": "known parsed room/global identities; excludes unsupported room containers"},
        {"name": "largest_room_directory_plus_live_global_slot_bound",
         "value": (None if largest is None or max_live_global_activations is None else
                   largest["room_bundle_executable_count"] + max_live_global_activations),
         "epistemic": "CONSERVATIVE_UPPER_BOUND",
         "scope": "assumes every C4 slot could retain a distinct global identity alongside the full room directory; not a proven schedule"},
        {"name": "whole_known_source_corpus", "value": len(scripts),
         "epistemic": "STATIC_LOWER_BOUND" if unparsed_rooms else "EXACT",
         "scope": "currently normalized source executable identities"},
        {"name": "maximum_live_activation_descriptors",
         "value": runtime_script_slot_capacity,
         "epistemic": "EXACT",
         "scope": "current C4 descriptor table; not selector demand"},
    ]
    for scenario in capacity_scenarios:
        scenario["selector_capacity_fit"] = _epistemic_fit(
            scenario["value"], backend_selector_capacity, scenario["epistemic"])

    room_sizes = {room: len(identities) for room, identities in room_identities.items()}
    transition_pairs = []
    for residency_edge in residency_edges:
        if residency_edge["kind"] not in {"load_room", "load_room_with_ego"}:
            continue
        outgoing = _identity_room(residency_edge["source"])
        incoming = _identity_room(residency_edge["target"])
        transition_pairs.append({
            "source": residency_edge["source"],
            "source_pc": residency_edge["source_pc"],
            "outgoing_room": outgoing,
            "incoming_room": incoming,
            "edge_resolution": residency_edge["resolution"],
            "lifecycle": ["OUTGOING_EXECUTION", "OUTGOING_EXCD", "ROOM_COMMIT",
                          "INCOMING_ENCD"],
            "room_bundle_overlap": "NOT_REQUIRED_BY_STAGED_ROOM_LIFECYCLE",
            "surviving_global_code": "UNKNOWN_ACTIVE_SET; globals may retain identity across room changes",
            "room_bundle_selector_demand": {
                "value": max(room_sizes.get(outgoing, 0), room_sizes.get(incoming, 0))
                if outgoing is not None and incoming is not None else None,
            "epistemic": "STATIC_LOWER_BOUND",
            },
        })

    return {
        "schema": "same_scumm_v5_residency_plan_v1",
        "identity_model": {
            "source_identity": "canonical, game-wide, selector-free executable identity",
            "backend_selector": "temporary build/runtime address assigned only by backend",
            "selector_allocation_performed": False,
        },
        "selector_model": {
            "current_selector_capacity": backend_selector_capacity,
            "meaning": "one build-global byte address resolving through generated size/fetch tables to a compiled program body",
            "room_directories_share_namespace": True,
            "selectors_are_reassigned_on_room_change": False,
            "active_descriptor_capacity": runtime_script_slot_capacity,
            "active_descriptor_capacity_meaning": "C4 script slots; independent from source corpus size and selector table capacity",
        },
        "counts": {
            "known_source_executables": len(scripts),
            "epistemic": "STATIC_LOWER_BOUND_IF_SOURCE_ROOMS_UNSUPPORTED",
            "by_scope": {name: by_scope.get(name, 0) for name in (
                "GLOBAL", "ROOM_ENTRY", "ROOM_EXIT", "ROOM_LOCAL", "OBJECT_VERB",
                "OTHER_RESOURCE_LOCAL", "UNKNOWN_DYNAMIC")},
            "parsed_rooms_with_executables": len(room_rows),
            "indexed_rooms_without_parsed_executables": unparsed_rooms,
            "indexed_rooms_without_parsed_executable_count": len(unparsed_rooms),
        },
        "global_residency": {
            "available_global_bodies": len(global_ids),
            "available_global_count_epistemic": "EXACT_FOR_INDEXED_GLOBAL_SCRIPT_DIRECTORY",
            "reachability_counts": {name: global_reach_counts.get(name, 0)
                                    for name in ("ROOT", "DEFINITE", "CONDITIONAL",
                                                 "POSSIBLE", "UNRESOLVED", "UNREACHED")},
            "root_or_definite": global_root_definite,
            "conditional_reachability": global_conditional_reach,
            "possible_or_unresolved_reachability": global_possible_reach,
            "static_referenced_global_targets": sorted(global_static),
            "static_referenced_global_target_count": len(global_static),
            "conditional_static_global_targets": sorted(global_conditional),
            "conditional_static_global_target_count": len(global_conditional),
            "dynamic_global_candidate_union": sorted(global_dynamic_candidates),
            "dynamic_global_candidate_count": len(global_dynamic_candidates),
            "dynamic_global_edges": dynamic_global_edge_count,
            "conservative_global_resolver_candidate_set": sorted(
                set(global_static) | set(global_conditional) | global_dynamic_candidates),
            "yielded_globals_may_cross_room_changes": sorted(persistent_candidates),
            "yielded_global_candidate_count": len(persistent_candidates),
            "yield_and_room_transition_operation_presence": sorted(transition_capable_globals),
            "yield_and_room_transition_candidate_count": len(transition_capable_globals),
            "opaque_global_executable_identities": opaque_global_identities,
            "simultaneously_live_global_activations": {
                "value": None,
                "epistemic": "UNKNOWN",
                "upper_bound": runtime_script_slot_capacity,
                "reason": "static graph does not prove activation overlap; SCUMM scheduler slot limit bounds active scripts, not all callable global bodies",
            },
            "records": global_rows,
        },
        "rooms": room_rows,
        "analysis_uncertainty": {
            "indexed_but_unparsed_room_resources": unparsed_rooms,
            "opaque_executables_by_room": {
                str(row["room"]): row["opaque_executable_identities"]
                for row in room_rows if row["opaque_executable_identities"]
            },
            "opaque_global_executables": opaque_global_identities,
            "effect": "Dependencies after opaque tails may be missing; known residency demand is a lower bound, while candidate unions cover only decoded dynamic references.",
        },
        "residency_edges": residency_edges,
        "transition_stages": transition_pairs,
        "working_set_scenarios": {
            "steady_state_room": {
                "largest_room_directory": None if largest is None else largest["room"],
                "maximum_room_bundle_executables": max(room_sizes.values(), default=0),
                "largest_room_plus_decoded_global_targets": selector_demand_for_largest,
                "largest_room_plus_all_global_candidates": max_conservative_demand,
                "static_global_set_coexists_with_every_room": True,
                "dynamic_global_live_overlap": "UNKNOWN",
            },
            "room_transition": {
                "room_bundles": "STAGED; outgoing exit/cleanup precedes incoming room execution",
                "maximum_staged_room_bundle_address_demand": max(room_sizes.values(), default=0),
                "surviving_global_activation_count": "UNKNOWN",
                "maximum_distinct_global_identities_from_slot_bound": max_live_global_activations,
                "directory_plus_global_upper_bound": (None if largest is None or
                    max_live_global_activations is None else
                    largest["room_bundle_executable_count"] + max_live_global_activations),
                "conservative_live_descriptor_upper_bound": runtime_script_slot_capacity,
                "source_identity_binding_must_survive_for_live_globals": True,
            },
            "nested_start_script": {
                "caller_and_callee_may_coexist": True,
                "identity_demand": "both identities, unless generic same-script replacement applies",
                "active_slot_bound": runtime_script_slot_capacity,
            },
            "start_object": {
                "caller_and_object_verb_may_coexist": True,
                "object_verb_scope": "owning room bundle",
                "active_slot_bound": runtime_script_slot_capacity,
            },
            "cutscene_continuation": {
                "saved_activation_identity_must_remain_resolvable": True,
                "selector_pin_or_canonical_identity_required": True,
                "active_slot_bound": runtime_script_slot_capacity,
            },
            "sentence_execution": {
                "object_verb_targets_are_room_local_resources": True,
                "all_room_verb_directories_may_be_addressable_without_being_active": True,
                "active_slot_bound": runtime_script_slot_capacity,
            },
            "dynamic_global_invocation": {
                "candidate_count": len(global_dynamic_candidates),
                "policy": "generated global resolver table; do not reserve a unique permanent native selector per source global solely for dynamic lookup",
            },
        },
        "selector_capacity": {
            "capacity": backend_selector_capacity,
            "scenarios": capacity_scenarios,
            "maximum_room_plus_direct_demand": max_direct_demand,
            "maximum_room_plus_dynamic_candidate_demand": max_conservative_demand,
            "rooms_direct_static_set_exceeds_capacity": ([] if backend_selector_capacity is None else [
                row["room"] for row in room_rows
                if row["room_plus_decoded_global_targets"]["value"] > backend_selector_capacity]),
            "rooms_known_dynamic_candidate_prebinding_may_exceed_capacity": ([] if backend_selector_capacity is None else [
                row["room"] for row in room_rows
                if row["dynamic_global_candidates"]
                and row["room_plus_dynamic_global_candidates"]["value"] > backend_selector_capacity]),
            "whole_source_corpus_fits": (None if backend_selector_capacity is None
                                         else len(scripts) <= backend_selector_capacity),
            "interpretation": "capacity applies to build-global selector addressability today; it is not the maximum number of scripts that may be active at one instant",
        },
        "save_restore": {
            "host_save_identity": "canonical resource/script identity plus room/kind/number/PC/locals; host reconstructs program bytes from source resource",
            "native_live_slot_identity": "byte program selector plus script number, PC, status and locals in each C4 slot",
            "custom_native_save_envelope": "logical game/save payload; this report found no serialization of active C4 scheduler descriptors there",
            "emulator_savestate": "captures WRAM selector bytes and is inherently tied to the matching ROM/build tables",
            "paging_implication": "persist canonical executable identity, or serialize a pinned selector->identity binding table with each active descriptor",
            "migration_recommendation": "canonical executable identity in scheduler/save boundary; resolve to a resident selector at fetch time or pin mappings for every live continuation",
        },
        "dynamic_policy": {
            "global_script": "resolve through generated global identity table at invocation; candidate set may be broad without making all globals simultaneously resident",
            "room_local": "resolve against the active room's local directory; dynamic current-room identity remains explicit",
            "object_verb": "resolve against active room/object verb metadata; do not load every room's object programs",
            "room_transition": "dynamic room target remains unresolved; require a generic room-resource loader/catalog or declared profile constraint",
            "unknown": "retain unresolved edge and block any completeness claim that depends on it",
        },
        "recommendation": {
            "choice": "B",
            "model": "canonical source executable identity -> generated resource/bundle directory -> currently resident selector binding",
            "reason": "room bundles are bounded and staged, while globals can remain live across room changes and selectors are stored in active slots. A resolver plus pinned live bindings avoids a permanent one-byte selector for every source executable without invalidating yielded continuations.",
            "not_implemented": True,
        },
        "next_milestone": {
            "recommendation": "compiler-generated executable residency manifest (semantic IDs and bundle membership only), followed by a generic runtime resolver contract",
            "scope": "analyze/map canonical IDs to global or per-room bundle-local indices; do not change the current selector ABI until active-slot pinning and save migration are specified",
        },
    }
