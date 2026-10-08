"""Whole-source SCUMM v5 inventory and conservative dependency analysis.

Room structure and executable decoding deliberately delegate to the existing
room bundle compiler. This module adds game scope, source identities, graph
certainty, and capability evidence; it is not a second bytecode parser.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable

from ...errors import ResourceError
from ...profile import EngineProfile
from .resources import LucasartsScummV5ResourceProvider
from .room_compiler import (
    RoomBundleCompilation, ScriptIR, _static_value, compile_room_payload,
    decode_script, profile_game_identity, sha256,
)
from .residency import build_residency_plan
from .program_units import build_program_unit_model, build_residency_manifest
from .selector_demand import build_selector_demand_model, build_selector_directory
from .native_residency import NativeProgramDirectory, directory_assembly
from .v5_opcode_schema import opcode_schema, schema_coverage
from .capability_frontier import (
    build_capability_frontier, build_whole_game_readiness,
)


_OPERATION_SUPPORT_EVIDENCE: dict[str, dict[str, tuple[str, str]]] = {
    "draw_box": {
        "host_runtime": (
            "SUPPORTED",
            "conformance tests cover direct/variable operands, inclusive/reversed bounds, "
            "viewport projection, clipping, and color writes",
        ),
        "snes_runtime": (
            "UNSUPPORTED",
            "native path currently consumes the instruction operands without drawing pixels",
        ),
    },
    "get_actor_width": {
        "host_runtime": (
            "SUPPORTED",
            "conformance tests cover direct/variable actor operands and actorOps width mutation",
        ),
        "snes_backend": (
            "SUPPORTED",
            "the SNES backend retains the SCUMM v5 opcode and compiles to the native dispatch path",
        ),
        "snes_backend": (
            "SUPPORTED",
            "the SCUMM v5 backend retains the canonical opcode and its runtime directory dispatches it",
        ),
        "snes_runtime": (
            "SUPPORTED",
            "native C14 conformance verifies direct and variable-selected width queries against actorOps state",
        ),
        "native_conformance": (
            "SUPPORTED",
            "bounded C14 Nexen control checks actor 1 width 35 and actor 2 default width 24",
        ),
        "save_restore": (
            "NOT_APPLICABLE",
            "getActorWidth is read-only; actor and variable persistence are owned by their existing state records",
        ),
        "save_restore": (
            "NOT_APPLICABLE",
            "getActorWidth is read-only; width persistence is owned by actor state and ordinary variable state",
        ),
    },
    "walk_actor_to_actor": {
        "host_runtime": (
            "SUPPORTED",
            "conformance covers direct and variable actor IDs, explicit and automatic stand-off distance, and invalid/nonresident actors",
        ),
        "snes_backend": (
            "SUPPORTED",
            "SCUMM bytecode is retained and routed through the generic native movement dispatch",
        ),
        "snes_runtime": (
            "SUPPORTED",
            "bounded native C32 conformance checks actor-relative destination and room state without VM error",
        ),
        "native_conformance": (
            "SUPPORTED",
            "Nexen C32 movement fixture reaches the expected actor-relative destination and balanced terminal state",
        ),
        "save_restore": (
            "PARTIAL",
            "host actor/script records preserve movement continuation; portable SNES save coverage is not yet certified",
        ),
    },
    "load_room_with_ego": {
        "host_runtime": (
            "SUPPORTED",
            "generic conformance tests cover direct/variable operands, destination preflight, "
            "entry-object placement, optional walk, and VAR_WALKTO_OBJ across ENCD yield",
        ),
        "snes_runtime": (
            "PARTIAL",
            "native request/room-commit/postamble implementation exists; operation-level "
            "semantic conformance remains incomplete",
        ),
    },
}


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode()


def executable_identity(script: ScriptIR) -> str:
    if script.kind == "SCRP":
        return f"GlobalScript({script.number})"
    if script.kind == "ENCD":
        return f"RoomEntry({script.source.room})"
    if script.kind == "EXCD":
        return f"RoomExit({script.source.room})"
    if script.kind == "LSCR":
        return f"RoomLocal(room={script.source.room},local={script.number})"
    if script.kind == "OBCD":
        return (f"ObjectVerb(room={script.source.room},object={script.object_id},"
                f"verb={script.verb_id})")
    return f"Executable(kind={script.kind},source={script.identity})"


def executable_analysis_status(script: ScriptIR) -> str:
    """Classify incomplete decode without turning its tail into success."""
    if script.decode_complete:
        return "COMPLETE"
    tail = next((item for item in script.instructions
                 if item.operation == "opaque_bytecode_tail"), None)
    if tail is not None and tail.structural_status in {"TRUNCATED", "MALFORMED"}:
        return "MALFORMED"
    if tail is not None and tail.structural_status in {
        "STRUCTURAL_UNKNOWN", "UNSUPPORTED_DECODE",
    }:
        return "UNSUPPORTED_DECODE"
    diagnostic = (tail.diagnostic or "") if tail is not None else ""
    lowered = diagnostic.lower()
    if lowered.startswith("truncated") or "exceeds bounded" in lowered:
        return "MALFORMED"
    if "width" in lowered or "requires string decoder" in lowered:
        return "UNSUPPORTED_DECODE"
    return "PARTIAL_OPAQUE"


@dataclass(frozen=True, slots=True)
class GameIR:
    schema: str
    game_id: str
    game_variant: str
    game_identity_sha256: str
    profile_sha256: str
    source: dict[str, Any]
    global_script_count: int
    rooms: tuple[dict[str, Any], ...]
    global_scripts: tuple[ScriptIR, ...]
    resources: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "game": {
                "id": self.game_id, "variant": self.game_variant,
                "identity_sha256": self.game_identity_sha256,
                "profile_sha256": self.profile_sha256,
            },
            "source": self.source,
            "global_script_count": self.global_script_count,
            "rooms": [item["room_ir"] for item in self.rooms],
            "global_scripts": [item.to_dict() for item in self.global_scripts],
            "resources": list(self.resources),
        }


@dataclass(frozen=True, slots=True)
class GameAnalysis:
    game_ir: GameIR
    census: dict[str, Any]
    executables: dict[str, Any]
    dependency_graph: dict[str, Any]
    reachability: dict[str, Any]
    capabilities: dict[str, Any]
    unsupported_frontier: dict[str, Any]
    opaque_analysis: dict[str, Any]
    capacity: dict[str, Any]
    opcode_coverage: dict[str, Any]
    program_units: dict[str, Any]
    residency_manifest: dict[str, Any]
    residency: dict[str, Any]
    selector_demand: dict[str, Any]
    selector_directory: dict[str, Any]
    native_program_directory: dict[str, Any]
    selector_residency: dict[str, Any]
    capability_frontier: dict[str, Any]
    whole_game_readiness: dict[str, Any]
    room_compilations: dict[int, RoomBundleCompilation]

    def files(self) -> dict[str, bytes]:
        return {
            "game.json": canonical_json(self.game_ir.to_dict()),
            "census.json": canonical_json(self.census),
            "executables.json": canonical_json(self.executables),
            "dependency_graph.json": canonical_json(self.dependency_graph),
            "reachability.json": canonical_json(self.reachability),
            "capabilities.json": canonical_json(self.capabilities),
            "capability_frontier.json": canonical_json(self.capability_frontier),
            "whole_game_readiness.json": canonical_json(self.whole_game_readiness),
            "unsupported_frontier.json": canonical_json(self.unsupported_frontier),
            "opaque_analysis.json": canonical_json(self.opaque_analysis),
            "capacity.json": canonical_json(self.capacity),
            "opcode_coverage.json": canonical_json(self.opcode_coverage),
            "program_units.json": canonical_json(self.program_units),
            "residency_manifest.json": canonical_json(self.residency_manifest),
            "residency.json": canonical_json(self.residency),
            "selector_demand.json": canonical_json(self.selector_demand),
            "selector_directory.json": canonical_json(self.selector_directory),
            "native_program_directory.json": canonical_json(self.native_program_directory),
            "native_program_directory.inc.pasm": directory_assembly(
                NativeProgramDirectory(self.native_program_directory)
            ).encode("ascii"),
            "selector_residency.json": canonical_json(self.selector_residency),
            "summary.md": self.summary_markdown().encode(),
        }

    def summary_markdown(self) -> str:
        graph = self.dependency_graph["counts"]
        reach = self.reachability["counts"]
        complete = self.opaque_analysis["closure_complete"]
        return "\n".join((
            f"# SCUMM source analysis: {self.game_ir.game_id}", "",
            f"Edition: {self.game_ir.game_variant}",
            f"Rooms: {self.census['counts'].get('room', 0)}",
            f"Global script slots: {self.game_ir.global_script_count}",
            f"Executable identities: {self.executables['counts']['total']}",
            f"Graph nodes / edges: {self.dependency_graph['counts']['nodes']} / "
            f"{self.dependency_graph['counts']['edges']}",
            f"Edge certainty: static {graph['STATIC']}, conditional "
            f"{graph['CONDITIONAL_STATIC']}, dynamic {graph['DYNAMIC']}, "
            f"unresolved {graph['UNRESOLVED']}",
            f"Reachability: {', '.join(f'{key.lower()} {value}' for key, value in reach.items())}",
            f"Structural opcode families observed: {self.opcode_coverage['counts']['semantic_families_observed']}",
            "Structural frontiers: "
            f"unknown {self.opcode_coverage['counts']['structurally_unknown_occurrences']}, "
            f"truncated {self.opcode_coverage['counts']['truncated_occurrences']}, "
            f"malformed {self.opcode_coverage['counts']['malformed_occurrences']}",
            f"Static closure complete: {'yes' if complete else 'no'}", "",
            f"Semantic executable identities: {self.program_units['counts']['semantic_executable_identities']}",
            f"Legacy backend program records: {self.program_units['counts']['program_units']}",
            f"Current dispatch SelectorUnits: {self.selector_demand['counts']['selector_units']}",
            f"Largest legacy backend record bundle: {self.residency['working_set_questions']['B_addressable_program_unit_set']['largest_room_bundle']}",
            f"Largest callable room SelectorUnit bundle: {self.selector_demand['room_capacity_summary']['largest_room_selector_unit_count']}",
            f"Largest known static room+global SelectorUnit set: {self.selector_demand['room_capacity_summary']['largest_static_room_plus_global_set']}",
            f"Current selector capacity: {self.selector_residency['selector_capacity']['capacity']}",
            f"Semantic frontier: {self.capability_frontier['semantic_unsupported_occurrences']} unsupported occurrences across {self.capability_frontier['family_count']} families",
            f"Whole-game readiness: {self.whole_game_readiness['status']}",
            f"Selector-unit residency recommendation: {self.selector_residency['recommendation']['choice']}",
            "Semantic executable count, resource records, emitted legacy IDs, callable SelectorUnits, and simultaneous pins are distinct; see selector_demand.json and selector_residency.json.", "",
            "Opaque analysis remains incomplete; absence of a decoded edge is not proof "
            "that an opaque tail contains no dependency or capability.", "",
        ))


def _resource_member(source_members: dict[str, str], key: str) -> str:
    return source_members[key]


def build_game_ir(
    provider: LucasartsScummV5ResourceProvider,
    *,
    profile: EngineProfile,
    profile_bytes: bytes,
    archive_sha256: str,
    source_members: dict[str, str],
) -> tuple[GameIR, dict[int, RoomBundleCompilation]]:
    """Build a whole-game IR using the room compiler for every room."""
    policy = provider.policy
    profile_sha = sha256(profile_bytes)
    game_identity = profile_game_identity(profile)
    index_bytes = provider.backing.read(policy.index_key)
    data_bytes = provider.backing.read(policy.data_key)
    index_categories = {"global-object-table", "resource-directory"}
    resources = [dict(
        row,
        source_member=source_members["game.index"] if row["category"] in index_categories
        else source_members["game.data"],
    ) for row in provider.source_catalog()]
    resources.extend((
        {"identity": "IndexContainer", "category": "source-container",
         "kind": "SCIX", "status": "INVENTORIED",
         "source_member": source_members["game.index"],
         "payload_length": len(index_bytes), "payload_sha256": sha256(index_bytes)},
        {"identity": "DataContainer", "category": "source-container",
         "kind": "SCDT", "status": "INVENTORIED",
         "source_member": source_members["game.data"],
         "payload_length": len(data_bytes), "payload_sha256": sha256(data_bytes)},
    ))
    resources.sort(key=lambda item: (str(item["category"]), int(item.get("number", -1)),
                                     str(item["identity"])))
    room_rows = [row for row in resources if row["category"] == "room"]
    compilations: dict[int, RoomBundleCompilation] = {}
    rooms: list[dict[str, Any]] = []
    game_name = f"{profile.game_id}:{profile.variant}"
    for row in room_rows:
        number = int(row["number"])
        key = str(row["resource_key"])
        try:
            compilation = compile_room_payload(
                provider.read(key), room_number=number, game_name=game_name,
                resource_key=key, source_member=_resource_member(source_members, "game.data"),
                source_container_offset=int(row["container_offset"]),
                original_room_file_offset=int(row["payload_offset"]),
                profile_sha256=profile_sha, game_identity_sha256=game_identity,
                archive_sha256=archive_sha256, index_sha256=sha256(index_bytes),
                data_sha256=sha256(data_bytes),
                global_script_count=provider.global_script_count,
                global_object_states=provider.global_objects.states,
                global_object_owners=provider.global_objects.owners,
                global_object_classes=provider.global_objects.classes,
            )
        except ResourceError as exc:
            # Keep the source census complete when one resource exceeds the
            # current room decoder. The room is inventoried but contributes no
            # fabricated executables or semantic claims.
            rooms.append({
                "room": number,
                "source_identity": {
                    "resource_key": key,
                    "source_member": source_members["game.data"],
                    "container_offset": row["container_offset"],
                    "room_payload_offset": row["payload_offset"],
                    "room_sha256": row["payload_sha256"],
                },
                "analysis_status": "UNSUPPORTED",
                "diagnostic": str(exc),
                "room_ir": None,
                "capabilities": None,
            })
            continue
        compilations[number] = compilation
        rooms.append({
            "room": number,
            "source_identity": {
                "resource_key": key,
                "source_member": source_members["game.data"],
                "container_offset": row["container_offset"],
                "room_payload_offset": row["payload_offset"],
                "room_sha256": row["payload_sha256"],
            },
            "analysis_status": "SEMANTIC_IR",
            # This projection is the room compiler's canonical representation,
            # not a second room parser or room-specific analysis path.
            "room_ir": compilation.room_ir.to_dict(),
            "capabilities": compilation.capabilities.to_dict(),
        })

    globals_ir: list[ScriptIR] = []
    for row in resources:
        if row["category"] != "global-script" or row["status"] != "INVENTORIED":
            continue
        number = int(row["number"])
        key = str(row["resource_key"])
        location = provider.source_location(key)
        body = provider.read(key)
        globals_ir.append(decode_script(
            body, identity=f"GlobalScript({number})", kind="SCRP", number=number,
            room=int(location["source_room"]), resource_key=key,
            game_name=game_name, source_member=source_members["game.data"],
            resource_offset=int(location["container_offset"]),
            source_offset=int(location["payload_offset"]),
            source_body_sha256=sha256(body),
        ))
    globals_ir.sort(key=lambda item: int(item.number or 0))
    source = {
        "archive_sha256": archive_sha256,
        "index_member": source_members["game.index"],
        "index_sha256": sha256(index_bytes),
        "data_member": source_members["game.data"],
        "data_sha256": sha256(data_bytes),
        "dialect": "SCUMM v5",
        "global_object_table_entries": len(provider.global_objects.states),
    }
    return GameIR(
        "same_scumm_v5_game_ir_v1", profile.game_id, profile.variant,
        game_identity, profile_sha, source, provider.global_script_count,
        tuple(rooms), tuple(globals_ir), tuple(resources),
    ), compilations


def _all_scripts(game: GameIR,
                 compilations: dict[int, RoomBundleCompilation]) -> dict[str, ScriptIR]:
    result = {executable_identity(item): item for item in game.global_scripts}
    for compilation in compilations.values():
        for item in compilation.room_ir.scripts:
            result[executable_identity(item)] = item
    return result


_CAPABILITY_GROUPS: dict[str, tuple[str, ...]] = {
    "script-lifecycle": (
        "start_script", "chain_script", "stop_script", "stop_object_code", "yield",
        "freeze_scripts",
    ),
    "variables-and-control-flow": (
        "write_variable", "increment_variable", "decrement_variable", "jump",
        "set_var_range",
        "expression", "add", "subtract", "multiply", "divide", "and", "or",
        "branch_equal_zero", "branch_not_equal_zero", "branch_equal",
        "branch_not_equal", "branch_less_than", "branch_greater_than",
        "branch_less_equal", "branch_greater_equal",
    ),
    "object-execution-and-state": (
        "start_object", "set_object_state", "set_object_class", "set_object_name",
        "set_object_owner", "pickup_object", "get_object_state", "draw_object",
        "if_class_of_is", "find_object", "matrix_ops",
    ),
    "graphics": ("draw_box",),
    "diagnostics": ("debug_log",),
    "system-control": ("system_operation",),
    "room-lifecycle": ("load_room", "load_room_with_ego", "put_actor_in_room"),
    "actors-and-movement": (
        "animate_actor", "walk_actor_to", "put_actor", "actor_ops",
        "walk_actor_to_actor",
        "actor_follow_camera", "wait_for_actor",
        "put_actor_at_object", "walk_actor_to_object", "face_actor",
        "get_actor_room", "get_actor_elevation", "get_actor_facing",
        "get_actor_moving", "get_actor_scale", "get_actor_walkbox",
        "get_actor_width", "get_anim_counter", "get_actor_x", "get_actor_y",
        "get_closest_obj_actor", "actor_from_pos",
    ),
    "inventory": ("get_inventory_count", "get_object_owner", "set_object_owner",
                  "pickup_object", "get_verb_entrypoint", "find_inventory"),
    "text-and-dialog": ("print_text", "print_ego"),
    "waits-and-timers": ("wait", "delay", "delay_variable"),
    "cutscenes": ("begin_cutscene", "end_cutscene", "set_cutscene_override"),
    "verbs-and-sentences": (
        "submit_sentence", "cancel_sentence_queue", "save_restore_verbs",
    ),
    "audio": ("start_music", "start_sound", "stop_sound", "sound_kludge",
              "is_sound_running"),
    "camera": ("set_camera_at", "pan_camera_to"),
    "resource-services": ("resource_routines", "cursor_command", "pseudo_room_map"),
}
_OP_TO_CAPABILITY = {operation: group for group, operations in _CAPABILITY_GROUPS.items()
                     for operation in operations}


def _control_flow_certainty(script: ScriptIR) -> dict[int, str]:
    """Return STATIC only when an instruction is reachable without a branch."""
    if not script.instructions:
        return {}
    by_pc = {item.pc: item for item in script.instructions}
    entry = script.instructions[0].pc
    pending = [(entry, False)]
    visited: set[tuple[int, bool]] = set()
    certainty: dict[int, str] = {}
    while pending:
        pc, conditional = pending.pop()
        if (pc, conditional) in visited or pc not in by_pc:
            continue
        visited.add((pc, conditional))
        certainty[pc] = ("CONDITIONAL_STATIC" if conditional else "STATIC")
        ins = by_pc[pc]
        next_pc = pc + len(ins.raw_hex) // 2
        if ins.operation == "opaque_bytecode_tail" or ins.control_flow == "TERMINATOR":
            continue
        if ins.control_flow == "UNCONDITIONAL_BRANCH":
            if ins.branch_target is not None:
                pending.append((ins.branch_target, conditional))
            continue
        if ins.control_flow == "CONDITIONAL_BRANCH":
            if ins.branch_target is not None:
                pending.append((ins.branch_target, True))
            if next_pc in by_pc:
                pending.append((next_pc, True))
            continue
        if ins.control_flow == "CONDITIONAL_TERMINATOR":
            if next_pc in by_pc:
                pending.append((next_pc, True))
            continue
        if next_pc in by_pc:
            pending.append((next_pc, conditional))
    return certainty


def _direct(operand: Any) -> int | None:
    return _static_value(operand)


def _edge(source: str, target: str | None, kind: str, certainty: str,
          pc: int | None = None, *, expression: str | None = None,
          candidates: Iterable[str] = (), detail: str | None = None,
          domain: str = "execution") -> dict[str, Any]:
    return {
        "source": source, "target": target, "kind": kind,
        "resolution": certainty, "source_pc": pc,
        "expression": expression,
        "candidate_targets": sorted(set(candidates)),
        "detail": detail, "domain": domain,
    }


_STRUCTURAL_FAMILIES_WITH_DEPENDENCIES = {
    "startScript": ("start_script", ("script", "arguments")),
    "chainScript": ("chain_script", ("script", "arguments")),
    "startObject": ("start_object", ("object", "entry", "arguments")),
    "loadRoom": ("load_room", ("room",)),
    "loadRoomWithEgo": ("load_room_with_ego", ("entry_object", "room", "x", "y")),
    "actorFollowCamera": ("actor_follow_camera", ("actor",)),
    "putActorInRoom": ("put_actor_in_room", ("actor", "room")),
    "startSound": ("start_sound", ("resource",)),
    "stopSound": ("stop_sound", ("resource",)),
    "startMusic": ("start_music", ("resource",)),
}


def _dependency_view(instruction: Any) -> tuple[str, dict[str, Any]]:
    """Expose provable source references without claiming semantic IR support."""
    operation = instruction.operation
    operands = dict(instruction.operands)
    family = instruction.opcode_family
    if not operation.startswith("structural_only:") or family is None:
        return operation, operands
    mapping = _STRUCTURAL_FAMILIES_WITH_DEPENDENCIES.get(family)
    if mapping is not None:
        operation, names = mapping
        for index, name in enumerate(names):
            key = f"operand_{index}"
            if key in operands:
                operands[name] = operands[key]
    elif family == "actorOps":
        commands = operands.get("commands", [])
        operands["selectors"] = [
            {"subop": int(item["subopcode"]) & 0x1F,
             "values": item.get("values", [])}
            for item in commands
        ]
    elif family == "resourceRoutines":
        operands["subop"] = int(operands.get("subopcode", 0)) & 0x3F
    return operation, operands


def _ensure_resource_reference_node(
    nodes: dict[str, dict[str, Any]], identity: str | None, category: str,
) -> None:
    if identity is not None and identity not in nodes:
        nodes[identity] = {
            "identity": identity, "node_type": "resource", "category": category,
            "status": "UNRESOLVED_REFERENCE",
        }


def build_dependency_graph(
    game: GameIR,
    compilations: dict[int, RoomBundleCompilation],
) -> tuple[dict[str, Any], dict[str, ScriptIR]]:
    scripts = _all_scripts(game, compilations)
    resources = {str(item["identity"]): item for item in game.resources}
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    room_ids = sorted(compilations)
    global_ids = {int(item.number) for item in game.global_scripts if item.number is not None}

    for identity, script in sorted(scripts.items()):
        nodes[identity] = {
            "identity": identity, "node_type": "executable",
            "analysis_status": executable_analysis_status(script),
            "source": asdict(script.source),
        }
    for identity, resource in sorted(resources.items()):
        nodes[identity] = {
            "identity": identity, "node_type": "resource",
            "category": resource["category"], "status": resource["status"],
            "source_member": resource.get("source_member"),
            "payload_sha256": resource.get("payload_sha256"),
        }
    for room in game.rooms:
        if room.get("analysis_status") == "UNSUPPORTED":
            identity = f"RoomEntry({room['room']})"
            nodes.setdefault(identity, {
                "identity": identity, "node_type": "executable",
                "analysis_status": "UNSUPPORTED", "diagnostic": room.get("diagnostic"),
            })
    for room_number, compilation in sorted(compilations.items()):
        room_node = f"RoomResource({room_number})"
        for script in compilation.room_ir.scripts:
            identity = executable_identity(script)
            edges.append(_edge(room_node, identity, "contains-executable", "STATIC",
                               domain="resource"))
        for obj in compilation.room_ir.objects:
            object_node = f"RoomObject(room={room_number},object={obj.object_id})"
            nodes[object_node] = {"identity": object_node, "node_type": "object",
                                  "source_room": room_number,
                                  "object_id": obj.object_id,
                                  "obcd_sha256": obj.obcd_sha256}
            edges.append(_edge(room_node, object_node, "contains-object", "STATIC",
                               domain="resource"))
            for verb in obj.verbs:
                target = f"ObjectVerb(room={room_number},object={obj.object_id},verb={verb.verb_id})"
                edges.append(_edge(object_node, target, "object-verb", "STATIC",
                                   verb.entry_offset, domain="resource"))
        entry = f"RoomEntry({room_number})"
        for script in compilation.room_ir.scripts:
            if script.kind == "OBCD":
                edges.append(_edge(entry, executable_identity(script), "player-invocable-verb",
                                   "CONDITIONAL_STATIC", script.instructions[0].pc
                                   if script.instructions else None))

    # Non-executable resource inventory nodes remain distinct from executable
    # reachability. DOBJ is source metadata, not a script selector namespace.
    room_to_scripts: dict[tuple[int, int], str] = {}
    for identity, script in scripts.items():
        if script.kind == "LSCR" and script.number is not None:
            room_to_scripts[(script.source.room, script.number)] = identity
    for source, script in sorted(scripts.items()):
        certainty_by_pc = _control_flow_certainty(script)
        room = script.source.room if script.kind != "SCRP" else None
        for ins in script.instructions:
            operation, operands = _dependency_view(ins)
            certainty = certainty_by_pc.get(ins.pc, "UNRESOLVED")
            if ins.operation == "opaque_bytecode_tail":
                continue
            if "actor" in operands:
                actor_operand = operands["actor"]
                actor_id = _direct(actor_operand)
                if actor_id is not None:
                    actor_node = f"Actor({actor_id})"
                    nodes.setdefault(actor_node, {
                        "identity": actor_node, "node_type": "actor-metadata",
                        "status": "DERIVED_FROM_EXECUTABLE_REFERENCE",
                    })
                    edges.append(_edge(source, actor_node, "actor-reference", "STATIC",
                                       ins.pc, domain="resource"))
                else:
                    edges.append(_edge(source, None, "actor-reference", "DYNAMIC",
                                       ins.pc, expression=f"actor selector {actor_operand!r}",
                                       domain="resource"))
            if operation in {"start_script", "chain_script"}:
                target_number = _direct(operands.get("script"))
                if target_number is None:
                    candidates = [f"GlobalScript({number})" for number in sorted(global_ids)]
                    operand = operands.get("script")
                    if room is not None:
                        candidates.extend(identity for (owner_room, _local), identity in room_to_scripts.items()
                                           if owner_room == room)
                    else:
                        candidates.extend(room_to_scripts.values())
                    edges.append(_edge(source, None, operation, "DYNAMIC", ins.pc,
                                       expression=f"script selector {operand!r}",
                                       candidates=candidates,
                                       detail="indirect selector is not guessed"))
                elif target_number < game.global_script_count:
                    target = f"GlobalScript({target_number})"
                    if target not in nodes:
                        nodes[target] = {"identity": target, "node_type": "executable",
                                         "analysis_status": "UNRESOLVED",
                                         "diagnostic": "directory slot has no available script body"}
                    edges.append(_edge(source, target, operation,
                                       "UNRESOLVED" if target_number not in global_ids else certainty,
                                       ins.pc, detail="global script namespace"))
                elif room is not None:
                    target = room_to_scripts.get((room, target_number))
                    target = target or f"RoomLocal(room={room},local={target_number})"
                    if target not in nodes:
                        nodes[target] = {"identity": target, "node_type": "executable",
                                         "analysis_status": "UNRESOLVED",
                                         "diagnostic": "no decoded local script body in this room"}
                    edges.append(_edge(source, target, "room-local-script",
                                       certainty if target in scripts else "UNRESOLVED", ins.pc,
                                       detail=f"local selector {target_number}"))
                else:
                    candidates = [identity for (owner_room, local), identity in room_to_scripts.items()
                                  if local == target_number]
                    edges.append(_edge(source, None, "room-local-script", "DYNAMIC", ins.pc,
                                       expression=f"current room + local selector {target_number}",
                                       candidates=candidates,
                                       detail="global script has no statically known current room"))
            elif operation == "start_object":
                object_id, verb_id = _direct(operands.get("object")), _direct(operands.get("entry"))
                if object_id is None or verb_id is None or room is None:
                    edges.append(_edge(source, None, "object-verb", "DYNAMIC", ins.pc,
                                       expression="object, verb, or current room is indirect"))
                else:
                    target = f"ObjectVerb(room={room},object={object_id},verb={verb_id})"
                    if target not in nodes:
                        nodes[target] = {"identity": target, "node_type": "executable",
                                         "analysis_status": "UNRESOLVED",
                                         "diagnostic": "object/verb target is absent from parsed room metadata"}
                    edges.append(_edge(source, target,
                                       "start-object", certainty if target in scripts else "UNRESOLVED",
                                       ins.pc))
            elif operation in {"load_room", "load_room_with_ego"}:
                room_number = _direct(operands.get("room"))
                if room_number is None:
                    edges.append(_edge(source, None, operation, "DYNAMIC", ins.pc,
                                       expression=f"room operand {operands.get('room')!r}"))
                else:
                    target = f"RoomEntry({room_number})"
                    if target not in nodes:
                        nodes[target] = {"identity": target, "node_type": "executable",
                                         "analysis_status": "UNRESOLVED",
                                         "diagnostic": "target room has no decoded ENCD body"}
                    edges.append(_edge(source, target,
                                       operation, certainty if target in scripts else "UNRESOLVED",
                                       ins.pc))
                    if room is not None:
                        exit_target = f"RoomExit({room})"
                        if exit_target in scripts:
                            edges.append(_edge(source, exit_target, "outgoing-room-exit",
                                               "CONDITIONAL_STATIC", ins.pc))
                    if operation == "load_room_with_ego":
                        entry_object = _direct(operands.get("entry_object"))
                        if entry_object is None:
                            candidates = [f"RoomObject(room={room_number},object={obj.object_id})"
                                          for compilation in compilations.values()
                                          if compilation.room_ir.room == room_number
                                          for obj in compilation.room_ir.objects]
                            edges.append(_edge(source, None, "room-entry-object", "DYNAMIC", ins.pc,
                                               expression=f"entry object {operands.get('entry_object')!r}",
                                               candidates=candidates))
                        else:
                            object_node = f"RoomObject(room={room_number},object={entry_object})"
                            if object_node not in nodes:
                                nodes[object_node] = {
                                    "identity": object_node, "node_type": "object",
                                    "source_room": room_number, "object_id": entry_object,
                                    "analysis_status": "UNRESOLVED",
                                }
                            edges.append(_edge(source, object_node, "room-entry-object",
                                               certainty, ins.pc))
            elif operation == "actor_follow_camera":
                actor = _direct(operands.get("actor"))
                placements = []
                for item in script.instructions:
                    item_operation, item_operands = _dependency_view(item)
                    if (item_operation == "put_actor_in_room"
                            and _direct(item_operands.get("actor")) == actor
                            and _direct(item_operands.get("room")) is not None):
                        placements.append(item_operands)
                if actor is not None and placements:
                    followed_room = _direct(placements[-1].get("room"))
                    target = f"RoomEntry({followed_room})"
                    edges.append(_edge(source, target,
                                       "actor-follow-camera-room",
                                       certainty if target in scripts else "UNRESOLVED", ins.pc))
                else:
                    edges.append(_edge(source, None, "actor-follow-camera-room", "DYNAMIC", ins.pc,
                                       expression="followed actor's room is runtime state",
                                       candidates=[f"RoomEntry({number})" for number in room_ids]))
            elif operation == "put_actor_in_room":
                target_room = _direct(operands.get("room"))
                target = None if target_room is None else f"RoomEntry({target_room})"
                edges.append(_edge(source, target, "actor-placement-room",
                                   certainty if target_room is not None else "DYNAMIC", ins.pc,
                                   expression=None if target_room is not None else
                                   "actor destination room operand is indirect",
                                   detail="actor room assignment; does not itself assert a scene transition"))
            elif operation in {"start_sound", "stop_sound", "start_music"}:
                resource = _direct(operands.get("resource"))
                target = None if resource is None else f"Sound({resource})"
                _ensure_resource_reference_node(nodes, target, "sound")
                edges.append(_edge(source, target, "sound-reference",
                                   certainty if resource is not None else "DYNAMIC", ins.pc,
                                   expression=None if resource is not None else "resource operand is indirect",
                                   domain="resource"))
            elif operation == "actor_ops":
                for selector in operands.get("selectors", []):
                    subop = int(selector["subop"])
                    if subop not in (1, 3):
                        continue
                    raw = selector["values"][0] if selector.get("values") else None
                    number = _direct(raw)
                    target = f"{'Costume' if subop == 1 else 'Sound'}({number})" if number is not None else None
                    _ensure_resource_reference_node(
                        nodes, target, "costume" if subop == 1 else "sound")
                    edges.append(_edge(source, target, "costume-reference" if subop == 1 else "sound-reference",
                                       certainty if number is not None else "DYNAMIC", ins.pc,
                                       expression=None if number is not None else f"actorOps operand {raw!r}",
                                       domain="resource"))
                    actor_id = _direct(operands.get("actor"))
                    if subop == 1 and actor_id is not None and number is not None:
                        edges.append(_edge(f"Actor({actor_id})", target, "actor-uses-costume",
                                           certainty, ins.pc, domain="resource"))
            elif operation == "resource_routines":
                subop = int(operands.get("subop", 0))
                number = _direct(operands.get("resource"))
                category = {1: "GlobalScript", 2: "Sound", 3: "Costume", 4: "RoomResource",
                            18: "Charset", 19: "Charset"}.get(subop, "Resource")
                target = f"{category}({number})" if number is not None else None
                _ensure_resource_reference_node(nodes, target, category.lower())
                edges.append(_edge(source, target, "resource-routine-reference",
                                   certainty if number is not None else "DYNAMIC", ins.pc,
                                   expression=None if number is not None else "resource selector is indirect",
                                   domain="resource"))
    edges.sort(key=lambda item: (item["domain"], item["source"], -1 if item["source_pc"] is None else item["source_pc"],
                                 item["kind"], item["target"] or ""))
    counts = Counter(edge["resolution"] for edge in edges if edge["domain"] == "execution")
    cycles = execution_cycles(nodes, edges)
    return ({"schema": "same_scumm_v5_dependency_graph_v1",
             "nodes": [nodes[key] for key in sorted(nodes)],
             "edges": edges,
             "cycles": cycles,
             "counts": {key: counts.get(key, 0) for key in
                        ("STATIC", "CONDITIONAL_STATIC", "DYNAMIC", "UNRESOLVED")}
             | {"nodes": len(nodes), "edges": len(edges)}}, scripts)


def execution_cycles(nodes: dict[str, dict[str, Any]],
                     edges: list[dict[str, Any]]) -> list[list[str]]:
    """Find strongly connected components without recursion-depth dependence."""
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        target = edge["target"]
        if (edge["domain"] == "execution"
                and edge["resolution"] in {"STATIC", "CONDITIONAL_STATIC"}
                and target in nodes
                and nodes[target].get("node_type") == "executable"):
            adjacency[edge["source"]].append(target)
    executable_nodes = sorted(identity for identity, node in nodes.items()
                              if node.get("node_type") == "executable")
    reverse: dict[str, list[str]] = defaultdict(list)
    for source, targets in adjacency.items():
        for target in targets:
            reverse[target].append(source)
    visited: set[str] = set()
    finish: list[str] = []
    for start in executable_nodes:
        if start in visited:
            continue
        stack: list[tuple[str, bool]] = [(start, False)]
        while stack:
            node, exiting = stack.pop()
            if exiting:
                finish.append(node)
                continue
            if node in visited:
                continue
            visited.add(node)
            stack.append((node, True))
            for target in reversed(sorted(adjacency.get(node, []))):
                if target not in visited:
                    stack.append((target, False))
    assigned: set[str] = set()
    cycles: list[list[str]] = []
    for start in reversed(finish):
        if start in assigned:
            continue
        component = []
        pending = [start]
        assigned.add(start)
        while pending:
            node = pending.pop()
            component.append(node)
            for target in reverse.get(node, []):
                if target not in assigned:
                    assigned.add(target)
                    pending.append(target)
        if len(component) > 1 or start in adjacency.get(start, []):
            cycles.append(sorted(component))
    return sorted(cycles)


def _roots(profile: EngineProfile, scripts: dict[str, ScriptIR]) -> list[str]:
    options = profile.options
    result: list[str] = []
    boot = int(options.get("boot_script_number", 1))
    boot_identity = f"GlobalScript({boot})"
    result.append(boot_identity)
    initial_room = int(options.get("initial_room", 0))
    room_identity = f"RoomEntry({initial_room})"
    if initial_room:
        result.append(room_identity)
    return sorted(set(result))


_RANK = {"ROOT": 0, "DEFINITE": 1, "CONDITIONAL": 2, "POSSIBLE": 3, "UNRESOLVED": 4}


def compute_reachability(
    profile: EngineProfile,
    scripts: dict[str, ScriptIR],
    graph: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    roots = _roots(profile, scripts)
    virtual_roots = (["NullRoomLifecycle"] if int(profile.options.get("initial_room", 0)) == 0
                     else [])
    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph["edges"]:
        if edge["domain"] == "execution":
            adjacency[edge["source"]].append(edge)
    status: dict[str, str] = {root: "ROOT" for root in roots}
    paths: dict[str, list[str]] = {root: [root] for root in roots}
    queue = deque(root for root in roots if root in scripts)
    opaque_reached: list[str] = []
    while queue:
        source = queue.popleft()
        base = status[source]
        if source in scripts and not scripts[source].decode_complete:
            opaque_reached.append(source)
        for edge in adjacency.get(source, []):
            certainty = edge["resolution"]
            targets: list[str] = []
            if edge["target"] is not None:
                targets = [edge["target"]]
            elif certainty == "DYNAMIC":
                targets = edge["candidate_targets"]
            for target in targets:
                if target not in scripts:
                    continue
                if certainty == "UNRESOLVED":
                    candidate = "UNRESOLVED"
                elif certainty == "DYNAMIC":
                    candidate = "POSSIBLE"
                elif certainty == "CONDITIONAL_STATIC":
                    candidate = "CONDITIONAL"
                else:
                    candidate = ("CONDITIONAL" if base == "CONDITIONAL" else
                                 "POSSIBLE" if base == "POSSIBLE" else
                                 "UNRESOLVED" if base == "UNRESOLVED" else "DEFINITE")
                old = status.get(target)
                if old is None or _RANK[candidate] < _RANK[old]:
                    status[target] = candidate
                    paths[target] = paths[source] + [target]
                    queue.append(target)
    missing_roots = sorted(root for root in roots if root not in scripts)
    closure_incomplete = bool(opaque_reached or missing_roots) or any(
        edge["domain"] == "execution" and edge["resolution"] in {"DYNAMIC", "UNRESOLVED"}
        and edge["source"] in status
        for edge in graph["edges"]
    )
    for identity in scripts:
        if identity not in status:
            status[identity] = "UNRESOLVED" if closure_incomplete else "UNREACHED"
    counts = Counter(status.values())
    reachable_uncertain_edges = [edge for edge in graph["edges"]
                                 if edge["domain"] == "execution"
                                 and edge["source"] in paths
                                 and edge["resolution"] in {"DYNAMIC", "UNRESOLVED"}]
    report = {
        "schema": "same_scumm_v5_reachability_v1",
        "roots": roots,
        "virtual_roots": virtual_roots,
        "missing_configured_roots": sorted(root for root in roots if root not in scripts),
        "status_by_executable": dict(sorted(status.items())),
        "counts": {key: counts.get(key, 0) for key in
                   ("ROOT", "DEFINITE", "CONDITIONAL", "POSSIBLE", "UNRESOLVED", "UNREACHED")},
        "closure_complete": not closure_incomplete,
        "uncertainty_sources": {
            "reachable_opaque_executables": sorted(set(opaque_reached)),
            "missing_configured_roots": missing_roots,
            "reachable_dynamic_edges": sum(edge["resolution"] == "DYNAMIC"
                                            for edge in reachable_uncertain_edges),
            "reachable_unresolved_edges": sum(edge["resolution"] == "UNRESOLVED"
                                               for edge in reachable_uncertain_edges),
            "edge_witnesses": [{
                "path_to_source": paths[edge["source"]],
                "source_pc": edge["source_pc"], "kind": edge["kind"],
                "resolution": edge["resolution"], "target": edge["target"],
                "expression": edge["expression"],
            } for edge in reachable_uncertain_edges],
        },
    }
    return report, paths


def _capability_group(operation: str) -> str:
    return _OP_TO_CAPABILITY.get(operation, "other-or-opaque")


def _host_handlers() -> dict[int, Any]:
    try:
        from .engine import ScummV5Engine
        return ScummV5Engine()._handlers
    except Exception:
        return {}


def analyze_capabilities(
    scripts: dict[str, ScriptIR], reachability: dict[str, Any],
    paths: dict[str, list[str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    handlers = _host_handlers()
    operations: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    for identity, script in scripts.items():
        for instruction in script.instructions:
            operations[instruction.operation].append((identity, instruction))
    registry: dict[str, dict[str, Any]] = {}
    requirements_by_scope: dict[str, set[str]] = defaultdict(set)
    requirements_by_executable: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"operations": set(), "capabilities": set()})
    requirements_by_room: dict[int, dict[str, set[str]]] = defaultdict(
        lambda: {"operations": set(), "capabilities": set()})
    frontier_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    statuses = reachability["status_by_executable"]
    for operation, occurrences in sorted(operations.items()):
        declared_groups = {instruction.semantic_capability for _, instruction in occurrences
                           if instruction.semantic_capability}
        group = (next(iter(declared_groups)) if len(declared_groups) == 1
                 else _capability_group(operation))
        opcodes = sorted({instruction.opcode for _, instruction in occurrences})
        is_opaque = operation == "opaque_bytecode_tail"
        semantic_unsupported = any(
            instruction.semantic_status == "SEMANTIC_UNSUPPORTED"
            for _, instruction in occurrences
        )
        if is_opaque:
            frontend = "UNSUPPORTED"
            ir_status = "PARTIAL"
            semantic_ir = "UNKNOWN"
            host_status = "UNKNOWN"
            reason = "instruction boundary/control flow is unknown; tail remains opaque"
        else:
            frontend = "SUPPORTED"
            ir_status = "SUPPORTED"
            semantic_ir = "UNSUPPORTED" if semantic_unsupported else "SUPPORTED"
            handler_hits = [opcode in handlers for opcode in opcodes]
            host_status = ("UNSUPPORTED" if handler_hits and not any(handler_hits) else
                           "PARTIAL" if not all(handler_hits) else "PARTIAL")
            reason = ("dispatch handler exists, but operation-level conformance is not certified"
                      if all(handler_hits) else
                      "one or more decoded opcode variants have no host dispatch handler")
        support_evidence = _OPERATION_SUPPORT_EVIDENCE.get(operation, {})
        if "host_runtime" in support_evidence:
            host_status, reason = support_evidence["host_runtime"]
        snes_runtime_status, snes_runtime_evidence = support_evidence.get(
            "snes_runtime",
            ("UNKNOWN", "whole-game census does not certify native semantics"),
        )
        native_conformance_status, native_conformance_evidence = support_evidence.get(
            "native_conformance",
            ("UNKNOWN", "not inferred from source analysis"),
        )
        backend_status, backend_evidence = support_evidence.get(
            "snes_backend",
            ("PARTIAL", "source script bytes are retained in SC5C; no per-op lowering certification"),
        )
        save_restore_status, save_restore_evidence = support_evidence.get(
            "save_restore",
            ("UNKNOWN", "not inferred from opcode decoding"),
        )
        record = {
            "capability": group,
            "operation": operation,
            "opcodes": [f"0x{opcode:02X}" for opcode in opcodes],
            "front_end_decode": {"status": frontend,
                                 "evidence": "shared SCUMM v5 decode_script result"},
            "ir_representation": {"status": ir_status,
                                  "evidence": "InstructionIR retains source PC and operands"},
            "semantic_ir": {"status": semantic_ir,
                            "evidence": ("structural-only form; semantics are not normalized"
                                         if semantic_unsupported else
                                         "semantic operation and operands are normalized")},
            "snes_backend": {"status": backend_status,
                             "evidence": backend_evidence},
            "host_runtime": {"status": host_status, "evidence": reason},
            "snes_runtime": {"status": snes_runtime_status,
                             "evidence": snes_runtime_evidence},
            "save_restore": {"status": save_restore_status,
                             "evidence": save_restore_evidence},
            "native_conformance": {"status": native_conformance_status,
                                   "evidence": native_conformance_evidence},
            "occurrences": len(occurrences),
        }
        registry[operation] = record
        for identity, instruction in occurrences:
            requirements_by_executable[identity]["operations"].add(operation)
            requirements_by_executable[identity]["capabilities"].add(group)
            source_script = scripts[identity]
            if source_script.kind != "SCRP":
                requirements_by_room[source_script.source.room]["operations"].add(operation)
                requirements_by_room[source_script.source.room]["capabilities"].add(group)
            reach = statuses[identity]
            if reach in {"ROOT", "DEFINITE"}:
                scope = "definite"
            elif reach == "CONDITIONAL":
                scope = "conditional"
            elif reach == "POSSIBLE":
                scope = "possible_dynamic"
            elif reach == "UNRESOLVED":
                scope = "unresolved"
            else:
                scope = "corpus_only"
            requirements_by_scope[scope].add(group)
            if reach == "UNREACHED":
                continue
            dimensions = record
            non_supported = [name for name in (
                "front_end_decode", "ir_representation", "semantic_ir", "snes_backend",
                "host_runtime", "snes_runtime", "save_restore", "native_conformance")
                if dimensions[name]["status"] in {"PARTIAL", "UNSUPPORTED", "UNKNOWN"}]
            if non_supported:
                if is_opaque:
                    classification = "UNKNOWN_BEYOND_OPAQUE_BOUNDARY"
                elif reach in {"ROOT", "DEFINITE"}:
                    classification = "DEFINITE_BLOCKER" if host_status == "UNSUPPORTED" else "DEFINITE_UNVERIFIED"
                elif reach == "CONDITIONAL":
                    classification = "CONDITIONAL_BLOCKER" if host_status == "UNSUPPORTED" else "CONDITIONAL_UNVERIFIED"
                elif reach == "POSSIBLE":
                    classification = "POSSIBLE_DYNAMIC_REQUIREMENT"
                else:
                    classification = "UNKNOWN_BEYOND_UNCERTAINTY"
                key = (classification, identity, operation)
                item = frontier_by_key.get(key)
                if item is None:
                    item = {
                    "classification": classification,
                    "source_identity": identity, "source_pc": instruction.pc,
                    "operation": operation, "capability": group,
                    "reachability": reach,
                    "dependency_path": paths.get(identity),
                    "path_status": "KNOWN" if identity in paths else "UNRESOLVED",
                    "uncertainty_witness": (None if identity in paths else
                        next((paths.get(opaque) for opaque in reachability["uncertainty_sources"]["reachable_opaque_executables"]
                              if opaque in paths), None)),
                    "support_dimensions_not_fully_supported": non_supported,
                    "opaque_or_dynamic_uncertainty": is_opaque or reach in {"POSSIBLE", "UNRESOLVED"},
                    "diagnostic": instruction.diagnostic,
                    "occurrences": 0,
                    }
                    frontier_by_key[key] = item
                item["occurrences"] += 1
    counts_by_status: dict[str, int] = Counter(
        dimension["status"] for record in registry.values()
        for name, dimension in record.items()
        if isinstance(dimension, dict) and name not in {"occurrences"}
    )
    groups: dict[str, dict[str, Any]] = {}
    dimension_names = ("front_end_decode", "ir_representation", "semantic_ir", "snes_backend",
                       "host_runtime", "snes_runtime", "save_restore", "native_conformance")
    severity = {"SUPPORTED": 0, "NOT_APPLICABLE": 0, "PARTIAL": 1,
                "UNKNOWN": 2, "UNSUPPORTED": 3}
    for group in sorted(set(_OP_TO_CAPABILITY.values()) | {"other-or-opaque"}
                        | {str(record["capability"]) for record in registry.values()}):
        records = [record for record in registry.values() if record["capability"] == group]
        if not records:
            continue
        dimensions = {}
        for dimension in dimension_names:
            values = [record[dimension]["status"] for record in records]
            dimensions[dimension] = max(values, key=lambda value: severity[value])
        groups[group] = {
            "operations": sorted(record["operation"] for record in records),
            "support_dimensions": dimensions,
            "occurrences": sum(record["occurrences"] for record in records),
        }
    capability_report = {
        "schema": "same_scumm_v5_capability_analysis_v1",
        "support_model": {
            "SUPPORTED": "positive evidence for the named layer only",
            "PARTIAL": "some representation/dispatch exists but complete semantic support is not certified",
            "UNSUPPORTED": "current implementation has no support at the named layer",
            "UNKNOWN": "source census cannot establish support",
            "NOT_APPLICABLE": "dimension does not apply",
        },
        "registry_by_operation": registry,
        "groups": groups,
        "required_groups_by_scope": {
            scope: sorted(values) for scope, values in sorted(requirements_by_scope.items())
        },
        "whole_source_corpus": sorted(requirements_by_scope.get("corpus_only", set())
                                       | requirements_by_scope.get("definite", set())
                                       | requirements_by_scope.get("conditional", set())
                                       | requirements_by_scope.get("possible_dynamic", set())
                                       | requirements_by_scope.get("unresolved", set())),
        "requirements_by_room": {
            str(room): {key: sorted(values) for key, values in requirement.items()}
            for room, requirement in sorted(requirements_by_room.items())
        },
        "requirements_by_executable": {
            identity: {key: sorted(values) for key, values in requirement.items()}
            for identity, requirement in sorted(requirements_by_executable.items())
        },
        "status_counts_across_dimensions": dict(sorted(counts_by_status.items())),
    }
    frontier = sorted(frontier_by_key.values(), key=lambda item: (
        item["classification"], len(item["dependency_path"] or []),
        item["source_identity"], item["source_pc"], item["operation"]))
    return capability_report, {
        "schema": "same_scumm_v5_unsupported_frontier_v1",
        "items": frontier,
        "counts": dict(sorted(Counter(item["classification"] for item in frontier).items())),
    }


def build_opcode_coverage(
    scripts: dict[str, ScriptIR], reachability: dict[str, Any],
    capabilities: dict[str, Any],
) -> dict[str, Any]:
    """Summarize byte-structure and semantic status without merging layers."""
    registry = capabilities["registry_by_operation"]
    reach = reachability["status_by_executable"]
    raw_counts: Counter[int] = Counter()
    family_counts: Counter[str] = Counter()
    structural_counts: Counter[str] = Counter()
    semantic_counts: Counter[str] = Counter()
    groups: dict[tuple[int, int | None], list[tuple[str, Any]]] = defaultdict(list)
    family_rows: dict[str, dict[str, Any]] = {}
    backend_supported = runtime_supported = 0
    total = 0
    for identity, script in sorted(scripts.items()):
        for instruction in script.instructions:
            total += 1
            raw_counts[instruction.opcode] += 1
            structural_counts[instruction.structural_status] += 1
            semantic_counts[instruction.semantic_status] += 1
            if instruction.opcode_family:
                family_counts[instruction.opcode_family] += 1
                row = family_rows.setdefault(instruction.opcode_family, {
                    "occurrences": 0, "raw_variants": set(),
                    "structural_statuses": Counter(), "semantic_statuses": Counter(),
                })
                row["occurrences"] += 1
                row["raw_variants"].add(instruction.opcode)
                row["structural_statuses"][instruction.structural_status] += 1
                row["semantic_statuses"][instruction.semantic_status] += 1
            if instruction.structural_status != "STRUCTURALLY_DECODED":
                groups[(instruction.opcode, instruction.subopcode)].append((identity, instruction))
            record = registry.get(instruction.operation, {})
            backend_supported += record.get("snes_backend", {}).get("status") == "SUPPORTED"
            runtime_supported += record.get("snes_runtime", {}).get("status") == "SUPPORTED"
    examples_by_unknown = []
    for (opcode, subopcode), occurrences in sorted(groups.items()):
        rows = []
        for identity, instruction in occurrences[:5]:
            script = scripts[identity]
            rows.append({
                "source_identity": identity, "source_pc": instruction.pc,
                "source": asdict(script.source),
                "source_body_sha256": script.source.source_sha256,
                "opcode_family": instruction.opcode_family,
                "structural_status": instruction.structural_status,
                "reason": instruction.diagnostic,
                "reachability": reach.get(identity, "UNRESOLVED"),
            })
        known_reach = [(reach.get(identity, "UNRESOLVED"), instruction.pc, identity)
                       for identity, instruction in occurrences
                       if reach.get(identity) in {"ROOT", "DEFINITE", "CONDITIONAL", "POSSIBLE"}]
        earliest = min(known_reach, key=lambda item: (
            {"ROOT": 0, "DEFINITE": 1, "CONDITIONAL": 2, "POSSIBLE": 3}[item[0]],
            item[2], item[1])) if known_reach else None
        examples_by_unknown.append({
            "opcode": f"0x{opcode:02X}",
            "subopcode": None if subopcode is None else f"0x{subopcode:02X}",
            "occurrences": len(occurrences),
            "affected_executables": len({identity for identity, _ in occurrences}),
            "examples": rows,
            "earliest_reachable_occurrence": (None if earliest is None else {
                "reachability": earliest[0], "source_identity": earliest[2],
                "source_pc": earliest[1],
            }),
        })
    family_report = {
        name: {
            "occurrences": row["occurrences"],
            "raw_variants": [f"0x{value:02X}" for value in sorted(row["raw_variants"])],
            "structural_statuses": dict(sorted(row["structural_statuses"].items())),
            "semantic_statuses": dict(sorted(row["semantic_statuses"].items())),
            "schema": (None if not row["raw_variants"] else asdict(
                opcode_schema(min(row["raw_variants"]))
            )),
        }
        for name, row in sorted(family_rows.items())
    }
    return {
        "schema": "same_scumm_v5_opcode_structural_coverage_v1",
        "source_scope": "all parsed executable identities; unsupported room containers excluded",
        "counts": {
            "instruction_occurrences": total,
            "raw_opcode_variants_observed": len(raw_counts),
            "semantic_families_observed": len(family_counts),
            "structurally_decoded_occurrences": structural_counts.get("STRUCTURALLY_DECODED", 0),
            "structurally_unknown_occurrences": structural_counts.get("STRUCTURAL_UNKNOWN", 0),
            "truncated_occurrences": structural_counts.get("TRUNCATED", 0),
            "malformed_occurrences": structural_counts.get("MALFORMED", 0),
            "structurally_not_decoded_occurrences": sum(
                count for status, count in structural_counts.items()
                if status != "STRUCTURALLY_DECODED"),
            "semantic_ir_available_occurrences": semantic_counts.get("SEMANTIC_IR_AVAILABLE", 0),
            "semantic_unsupported_occurrences": semantic_counts.get("SEMANTIC_UNSUPPORTED", 0),
            "semantic_unknown_occurrences": semantic_counts.get("SEMANTIC_UNKNOWN", 0),
            "backend_supported_occurrences": backend_supported,
            "snes_runtime_supported_occurrences": runtime_supported,
        },
        "opcode_schema": schema_coverage(),
        "raw_opcode_occurrences": {f"0x{opcode:02X}": count
                                   for opcode, count in sorted(raw_counts.items())},
        "families": family_report,
        "structural_unknowns": examples_by_unknown,
        "invariant": "STRUCTURAL DECODE != SEMANTIC IR != BACKEND SUPPORT != RUNTIME SUPPORT",
    }


def analyze_game(
    provider: LucasartsScummV5ResourceProvider,
    *, profile: EngineProfile, profile_bytes: bytes,
    archive_sha256: str, source_members: dict[str, str],
    backend_selector_capacity: dict[str, Any] | None = None,
) -> GameAnalysis:
    game, compilations = build_game_ir(
        provider, profile=profile, profile_bytes=profile_bytes,
        archive_sha256=archive_sha256, source_members=source_members,
    )
    graph, scripts = build_dependency_graph(game, compilations)
    reachability, paths = compute_reachability(profile, scripts, graph)
    program_units = build_program_unit_model(scripts, compilations, graph, reachability)
    residency_manifest = build_residency_manifest(program_units)
    selector_demand = build_selector_demand_model(
        scripts, compilations, graph, reachability, program_units)
    selector_directory = build_selector_directory(selector_demand)
    native_program_directory = NativeProgramDirectory.from_selector_directory(
        selector_directory).document
    selector_plan_model = {
        "program_units": selector_demand["selector_units"],
        "semantic_to_program_unit_index": selector_demand["semantic_to_selector_index"],
        "semantic_to_program_unit": [
            {"semantic_executable": item["semantic_executable"],
             "program_unit": item["selector_unit"]}
            for item in selector_demand["semantic_executable_to_selector"]
            if item["selector_unit"] is not None],
        "dependencies": [{
            "source_program_unit": edge["source_selector_unit"],
            "source_semantic_identity": edge["source_semantic_executable"],
            "target_program_unit": edge["target_selector_unit"],
            "target_semantic_identity": edge["target_semantic_executable"],
            "target_resource_identity": edge["target_resource"],
            "kind": edge["kind"], "domain": edge.get("domain", "execution"),
            "resolution": edge["resolution"], "source_pc": edge["source_pc"],
            "expression": edge["expression"],
            "candidate_program_units": edge["candidate_selector_units"],
            "detail": edge["detail"],
        } for edge in selector_demand["dependencies"]],
    }
    selector_capacity_value = (backend_selector_capacity or {}).get("value")
    residency = build_residency_plan(
        scripts, graph, reachability,
        backend_selector_capacity=(None if selector_capacity_value is None
                                   else int(selector_capacity_value)),
        runtime_script_slot_capacity=25,
        program_unit_model=program_units,
    )
    selector_residency = build_residency_plan(
        scripts, graph, reachability,
        backend_selector_capacity=(None if selector_capacity_value is None
                                   else int(selector_capacity_value)),
        runtime_script_slot_capacity=25,
        program_unit_model=selector_plan_model,
    )
    # The historical ProgramUnit planner included passive OBCD records. Keep
    # its JSON for comparison, and publish actual selector-addressability from
    # the filtered callable-carrier projection separately.
    residency_by_room = {item["room"]: item
                         for item in selector_residency["room_bundles"]}
    selector_units_by_room: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for unit in selector_demand["selector_units"]:
        room = unit.get("owner", {}).get("room")
        if room is not None:
            selector_units_by_room[int(room)].append(unit)
    resource_records_by_room: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in selector_demand["resource_records"]:
        resource_records_by_room[int(record["room"])].append(record)
    room_selector_reports = []
    for room in sorted(compilations):
        bundle = residency_by_room.get(room, {})
        room_units = sorted(selector_units_by_room.get(room, []),
                            key=lambda item: item["identity"])
        semantic_count = sum(script.source.room == room and script.kind != "SCRP"
                             for script in scripts.values())
        static_globals = sorted(set(bundle.get("static_global_program_units", [])))
        conditional_globals = sorted(set(bundle.get("conditional_global_program_units", [])))
        dynamic_globals = sorted(set(bundle.get("dynamic_global_candidate_units", [])))
        static_addressability = sorted({item["identity"] for item in room_units}
                                       | set(static_globals) | set(conditional_globals))
        room_selector_reports.append({
            "room": room,
            "semantic_executable_identities": semantic_count,
            "resource_records": len(resource_records_by_room.get(room, [])),
            "objects_with_verb_entries": sum(
                bool(record["verb_entries"])
                for record in resource_records_by_room.get(room, [])),
            "objects_without_verb_entries": sum(
                not record["verb_entries"]
                for record in resource_records_by_room.get(room, [])),
            "executable_carriers": len(room_units),
            "selector_units": len(room_units),
            "selector_units_by_kind": dict(sorted(Counter(
                item["kind"] for item in room_units).items())),
            "room_selector_unit_identities": [item["identity"] for item in room_units],
            "direct_static_global_selector_units": static_globals,
            "conditional_static_global_selector_units": conditional_globals,
            "static_addressability_set": static_addressability,
            "static_addressability_count": len(static_addressability),
            "static_addressability_epistemic": bundle.get(
                "total_static_addressable_program_units", {}).get("epistemic", "UNKNOWN"),
            "dynamic_global_candidate_selector_units": dynamic_globals,
            "dynamic_candidate_universe_count": len(set(static_addressability)
                                                      | set(dynamic_globals)),
        })
    selector_demand["room_selector_reports"] = room_selector_reports
    selector_demand["global_selector_summary"] = {
        "global_script_slots": game.global_script_count,
        "available_global_selector_units": selector_residency[
            "global_program_units"]["available"],
        "source_slots_without_a_script_body": max(
            0, game.global_script_count - selector_residency["global_program_units"]["available"]),
        "definitely_reachable": selector_residency["global_program_units"]["definitely_reachable"],
        "conditionally_reachable": selector_residency["global_program_units"]["conditionally_reachable"],
        "possible_or_unresolved": selector_residency["global_program_units"]["possible_or_unresolved"],
        "reachability_counts": selector_residency["global_program_units"]["reachability_counts"],
        "static_targets": selector_residency["global_program_units"]["static_targets"],
        "conditional_static_targets": selector_residency["global_program_units"]["conditional_static_targets"],
        "dynamic_candidate_universe": selector_residency[
            "global_program_units"]["dynamic_candidate_universe"],
        "yield_capable": selector_residency["global_program_units"]["yield_capable"],
        "room_transition_capable_with_yield": selector_residency[
            "global_program_units"]["room_transition_capable_with_yield"],
        "candidate_universe_is_not_simultaneous_residency": True,
    }
    selector_demand["room_capacity_summary"] = {
        "largest_room_selector_unit_count": max(
            (item["selector_units"] for item in room_selector_reports), default=0),
        "largest_static_room_plus_global_set": max(
            (item["static_addressability_count"] for item in room_selector_reports), default=0),
        "largest_dynamic_candidate_universe": max(
            (item["dynamic_candidate_universe_count"] for item in room_selector_reports), default=0),
        "selector_capacity": selector_capacity_value,
        "static_room_sets_over_capacity": [
            {"room": item["room"], "count": item["static_addressability_count"]}
            for item in room_selector_reports
            if selector_capacity_value is not None
            and item["static_addressability_count"] > int(selector_capacity_value)],
    }
    capabilities, frontier = analyze_capabilities(scripts, reachability, paths)
    opcode_coverage = build_opcode_coverage(scripts, reachability, capabilities)
    capability_frontier = build_capability_frontier(
        scripts, reachability, paths, capabilities,
    )
    resource_counts = Counter(str(item["category"]) for item in game.resources)
    status_counts = Counter(str(item["status"]) for item in game.resources)
    executable_status = Counter(executable_analysis_status(item)
                                 for item in scripts.values())
    executable_kinds = Counter(
        "global-script" if item.kind == "SCRP" else
        "room-entry" if item.kind == "ENCD" else
        "room-exit" if item.kind == "EXCD" else
        "room-local" if item.kind == "LSCR" else
        "object-verb" if item.kind == "OBCD" else item.kind
        for item in scripts.values())
    unsupported_rooms = [item for item in game.rooms
                         if item.get("analysis_status") == "UNSUPPORTED"]
    parsed_room_epistemic = ("STATIC_LOWER_BOUND" if unsupported_rooms else "EXACT")
    selector_demand["source_coverage"] = {
        "rooms_inventoried": len(game.rooms),
        "rooms_parsed": len(compilations),
        "unsupported_room_identities": [item["room"] for item in unsupported_rooms],
        "source_corpus_epistemic": parsed_room_epistemic,
        "object_resource_count_scope": "parsed rooms only",
    }
    selector_demand["counts"]["epistemic"] = parsed_room_epistemic
    object_count = sum(len(item.room_ir.objects) for item in compilations.values())
    verb_count = sum(len(obj.verbs) for item in compilations.values()
                     for obj in item.room_ir.objects)
    actor_refs = set()
    string_refs = 0
    sound_refs = 0
    costume_refs = 0
    for script in scripts.values():
        for instruction in script.instructions:
            operands = dict(instruction.operands)
            if "actor" in operands:
                value = _direct(operands["actor"])
                if value is not None:
                    actor_refs.add(value)
            if instruction.operation in {"print_text", "print_ego"}:
                string_refs += sum("encoded_text_hex" in command
                                   for command in operands.get("commands", []))
            sound_refs += instruction.operation in {"start_sound", "stop_sound", "start_music"}
            if instruction.operation == "actor_ops":
                costume_refs += sum(int(selector["subop"]) == 1
                                    for selector in operands.get("selectors", []))
    census = {
        "schema": "same_scumm_v5_resource_census_v1",
        "counts": {**dict(sorted(resource_counts.items())), "object": object_count,
                   "object-verb": verb_count, "actor-reference": len(actor_refs),
                   "string-literal-reference": string_refs},
        "resource_status_counts": dict(sorted(status_counts.items())),
        "resource_counts_epistemic": "EXACT_FOR_INDEXED_RESOURCE_SLOTS",
        "global_script_slots": game.global_script_count,
        "global_scripts_available": len(game.global_scripts),
        "rooms_inventoried": resource_counts.get("room", 0),
        "rooms_parsed": len(compilations),
        "rooms_unsupported": [item["room"] for item in game.rooms
                              if item.get("analysis_status") == "UNSUPPORTED"],
        "room_analysis_status_counts": dict(sorted(Counter(
            str(item.get("analysis_status", "SEMANTIC_IR")) for item in game.rooms
        ).items())),
        "objects_parsed": object_count,
        "objects_epistemic": "STATIC_LOWER_BOUND_WHEN_ANY_ROOM_IS_UNSUPPORTED",
        "object_verbs_parsed": verb_count,
        "object_verbs_epistemic": "STATIC_LOWER_BOUND_WHEN_ANY_ROOM_IS_UNSUPPORTED",
        "global_object_table_entries": game.source["global_object_table_entries"],
        "executable_identities_by_kind": dict(sorted(executable_kinds.items())),
        "executable_analysis_status_counts": dict(sorted(executable_status.items())),
        "known_executable_identities_epistemic": (
            "STATIC_LOWER_BOUND" if any(item.get("analysis_status") == "UNSUPPORTED"
                                        for item in game.rooms) else "EXACT"
        ),
        "actor_metadata": {"status": "PARTIAL", "referenced_actor_ids": sorted(actor_refs),
                           "reason": "actor identities are derived from decoded references; complete actor table not normalized"},
        "string_resources": {"status": "PARTIAL", "encoded_literals_referenced": string_refs,
                              "reason": "text operands are retained in IR; a game-wide string table is not normalized"},
        "audio_references": {"sound_command_count": sound_refs,
                             "costume_reference_count": costume_refs},
    }
    executable_rows = []
    for identity, script in sorted(scripts.items()):
        executable_rows.append({
            "identity": identity,
            "analysis_status": executable_analysis_status(script),
            "source": asdict(script.source),
            "last_fully_decoded_pc": (script.instructions[-2].pc
                                       if not script.decode_complete and len(script.instructions) > 1
                                       else None if not script.instructions else script.instructions[-1].pc),
            "opaque_from_pc": script.opaque_from_pc,
            "opaque_opcode": next((f"0x{item.opcode:02X}" for item in script.instructions
                                    if item.operation == "opaque_bytecode_tail"), None),
            "opaque_reason": next((item.diagnostic for item in script.instructions
                                   if item.operation == "opaque_bytecode_tail"), None),
            "known_operations": [item.operation for item in script.instructions
                                 if item.operation != "opaque_bytecode_tail"],
            "program_length": len(script.program),
            "body_sha256": sha256(script.program),
        })
    executable_report = {
        "schema": "same_scumm_v5_executables_v1",
        "counts": {"total": len(scripts),
                   "total_epistemic": parsed_room_epistemic,
                   **dict(sorted(executable_status.items()))},
        "items": executable_rows,
    }
    whole_game_readiness = build_whole_game_readiness(
        census, executable_report, opcode_coverage, capabilities,
        capability_frontier,
    )
    opaque_rows = [item for item in executable_rows if item["analysis_status"] != "COMPLETE"]
    opaque = {
        "schema": "same_scumm_v5_opaque_analysis_v1",
        "incomplete_executables": opaque_rows,
        "count": len(opaque_rows),
        "reachable_incomplete": reachability["uncertainty_sources"]["reachable_opaque_executables"],
        "closure_complete": reachability["closure_complete"],
        "invariant": "OPAQUE TAIL != COMPLETE ANALYSIS; dependencies and capabilities after opaque_from_pc are unknown",
    }
    total_programs = len(scripts)
    max_room_bundle = max((len(item.room_ir.scripts) for item in compilations.values()), default=0)
    max_room_program_units = max((row["program_unit_count"]
                                  for row in residency["room_bundles"]), default=0)
    max_body = max((len(script.program) for script in scripts.values()), default=0)
    max_fanout = max((sum(edge["source"] == node and edge["domain"] == "execution"
                          for edge in graph["edges"]) for node in scripts), default=0)
    capacity = {
        "semantic_executable_identities": {"value": total_programs,
                                            "epistemic": parsed_room_epistemic},
        "backend_program_units": {"value": program_units["counts"]["program_units"],
                                  "epistemic": parsed_room_epistemic},
        "whole_known_program_unit_corpus_if_one_static_selector_map": {
            "value": program_units["counts"]["program_units"],
            "epistemic": parsed_room_epistemic,
            "comparison": "ProgramUnits only; semantic executable count is not selector demand",
        },
        "rooms_inventoried": {"value": len(game.rooms), "epistemic": "EXACT"},
        "rooms_semantically_parsed": {"value": len(compilations), "epistemic": "EXACT"},
        "objects": {"value": object_count, "epistemic": parsed_room_epistemic},
        "object_verb_entries": {"value": verb_count,
                                 "epistemic": parsed_room_epistemic},
        "largest_room_semantic_executable_bundle": {"value": max_room_bundle,
                                                     "epistemic": parsed_room_epistemic},
        "largest_room_backend_program_unit_bundle": {
            "value": max_room_program_units,
            "epistemic": "STATIC_LOWER_BOUND_IF_SOURCE_ROOMS_UNSUPPORTED"
            if any(item.get("analysis_status") == "UNSUPPORTED" for item in game.rooms)
            else "EXACT_FOR_PARSED_ROOMS",
        },
        "largest_script_body_bytes": {"value": max_body,
                                       "epistemic": parsed_room_epistemic},
        "largest_known_execution_fanout": {"value": max_fanout, "epistemic": "EXACT_FOR_DECODED_EDGES"},
        "current_default_backend_selector_pool": (backend_selector_capacity or {
            "value": None, "epistemic": "UNKNOWN",
            "reason": "no SNES backend capacity provider was supplied; analysis allocates no selectors",
        }),
        "runtime_slot_pressure": {"value": None, "epistemic": "UNKNOWN",
                                   "reason": "dynamic scheduling and runtime coexistence are not bounded by static graph depth"},
        "true_selector_units": {
            "value": selector_demand["counts"]["selector_units"],
            "epistemic": parsed_room_epistemic,
            "definition": "dispatch-reachable executable carriers after excluding data-only OBCD resources",
        },
        "object_resource_records": {
            "value": selector_demand["counts"]["resource_records"],
            "epistemic": parsed_room_epistemic,
        },
        "legacy_projected_ids_without_runtime_reference_if_included": {
            "value": selector_demand["counts"]["legacy_projected_ids_with_no_runtime_reference_if_included"],
            "epistemic": parsed_room_epistemic,
        },
    }
    return GameAnalysis(game, census, executable_report, graph, reachability,
                        capabilities, frontier, opaque, capacity, opcode_coverage,
                        program_units, residency_manifest, residency,
                        selector_demand, selector_directory, native_program_directory,
                        selector_residency, capability_frontier, whole_game_readiness,
                        compilations)


def game_analysis_hash(files: dict[str, bytes]) -> str:
    """Hash a canonical output set independent of the destination directory."""
    entries = [{"path": name, "sha256": sha256(content)} for name, content in sorted(files.items())]
    return sha256(canonical_json(entries))
