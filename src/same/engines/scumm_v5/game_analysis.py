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
    room_compilations: dict[int, RoomBundleCompilation]

    def files(self) -> dict[str, bytes]:
        return {
            "game.json": canonical_json(self.game_ir.to_dict()),
            "census.json": canonical_json(self.census),
            "executables.json": canonical_json(self.executables),
            "dependency_graph.json": canonical_json(self.dependency_graph),
            "reachability.json": canonical_json(self.reachability),
            "capabilities.json": canonical_json(self.capabilities),
            "unsupported_frontier.json": canonical_json(self.unsupported_frontier),
            "opaque_analysis.json": canonical_json(self.opaque_analysis),
            "capacity.json": canonical_json(self.capacity),
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
            f"Static closure complete: {'yes' if complete else 'no'}", "",
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
    "script-lifecycle": ("start_script", "chain_script", "stop_script", "yield"),
    "variables-and-control-flow": (
        "write_variable", "increment_variable", "decrement_variable", "jump",
        "branch_equal_zero", "branch_not_equal_zero", "branch_equal",
        "branch_not_equal", "branch_less_than", "branch_greater_than",
        "branch_less_equal", "branch_greater_equal",
    ),
    "object-execution-and-state": (
        "start_object", "set_object_state", "set_object_class", "matrix_ops",
    ),
    "room-lifecycle": ("load_room", "load_room_with_ego", "put_actor_in_room"),
    "actors-and-movement": (
        "animate_actor", "walk_actor_to", "put_actor", "actor_ops",
        "actor_follow_camera", "wait_for_actor",
    ),
    "text-and-dialog": ("print_text", "print_ego"),
    "waits-and-timers": ("wait", "delay"),
    "cutscenes": ("begin_cutscene", "end_cutscene"),
    "audio": ("start_music", "start_sound", "stop_sound", "sound_kludge"),
    "resource-services": ("resource_routines", "cursor_command"),
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
        if ins.operation == "stop_script" or ins.operation == "opaque_bytecode_tail":
            continue
        if ins.operation == "jump":
            if ins.branch_target is not None:
                pending.append((ins.branch_target, conditional))
            continue
        if ins.operation.startswith("branch_"):
            if ins.branch_target is not None:
                pending.append((ins.branch_target, True))
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
            operands = dict(ins.operands)
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
            if ins.operation in {"start_script", "chain_script"}:
                target_number = _direct(operands.get("script"))
                if target_number is None:
                    candidates = [f"GlobalScript({number})" for number in sorted(global_ids)]
                    operand = operands.get("script")
                    if room is not None:
                        candidates.extend(identity for (owner_room, _local), identity in room_to_scripts.items()
                                           if owner_room == room)
                    else:
                        candidates.extend(room_to_scripts.values())
                    edges.append(_edge(source, None, ins.operation, "DYNAMIC", ins.pc,
                                       expression=f"script selector {operand!r}",
                                       candidates=candidates,
                                       detail="indirect selector is not guessed"))
                elif target_number < game.global_script_count:
                    target = f"GlobalScript({target_number})"
                    if target not in nodes:
                        nodes[target] = {"identity": target, "node_type": "executable",
                                         "analysis_status": "UNRESOLVED",
                                         "diagnostic": "directory slot has no available script body"}
                    edges.append(_edge(source, target, ins.operation,
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
            elif ins.operation == "start_object":
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
            elif ins.operation in {"load_room", "load_room_with_ego"}:
                room_number = _direct(operands.get("room"))
                if room_number is None:
                    edges.append(_edge(source, None, ins.operation, "DYNAMIC", ins.pc,
                                       expression=f"room operand {operands.get('room')!r}"))
                else:
                    target = f"RoomEntry({room_number})"
                    if target not in nodes:
                        nodes[target] = {"identity": target, "node_type": "executable",
                                         "analysis_status": "UNRESOLVED",
                                         "diagnostic": "target room has no decoded ENCD body"}
                    edges.append(_edge(source, target,
                                       ins.operation, certainty if target in scripts else "UNRESOLVED",
                                       ins.pc))
                    if room is not None:
                        exit_target = f"RoomExit({room})"
                        if exit_target in scripts:
                            edges.append(_edge(source, exit_target, "outgoing-room-exit",
                                               "CONDITIONAL_STATIC", ins.pc))
                    if ins.operation == "load_room_with_ego":
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
            elif ins.operation == "actor_follow_camera":
                actor = _direct(operands.get("actor"))
                placements = [item for item in script.instructions
                              if item.operation == "put_actor_in_room"
                              and _direct(dict(item.operands).get("actor")) == actor
                              and _direct(dict(item.operands).get("room")) is not None]
                if actor is not None and placements:
                    followed_room = _direct(dict(placements[-1].operands).get("room"))
                    target = f"RoomEntry({followed_room})"
                    edges.append(_edge(source, target,
                                       "actor-follow-camera-room",
                                       certainty if target in scripts else "UNRESOLVED", ins.pc))
                else:
                    edges.append(_edge(source, None, "actor-follow-camera-room", "DYNAMIC", ins.pc,
                                       expression="followed actor's room is runtime state",
                                       candidates=[f"RoomEntry({number})" for number in room_ids]))
            elif ins.operation == "put_actor_in_room":
                target_room = _direct(operands.get("room"))
                target = None if target_room is None else f"RoomEntry({target_room})"
                edges.append(_edge(source, target, "actor-placement-room",
                                   certainty if target_room is not None else "DYNAMIC", ins.pc,
                                   expression=None if target_room is not None else
                                   "actor destination room operand is indirect",
                                   detail="actor room assignment; does not itself assert a scene transition"))
            elif ins.operation in {"start_sound", "stop_sound", "start_music"}:
                resource = _direct(operands.get("resource"))
                target = None if resource is None else f"Sound({resource})"
                edges.append(_edge(source, target, "sound-reference",
                                   certainty if resource is not None else "DYNAMIC", ins.pc,
                                   expression=None if resource is not None else "resource operand is indirect",
                                   domain="resource"))
            elif ins.operation == "actor_ops":
                for selector in operands.get("selectors", []):
                    subop = int(selector["subop"])
                    if subop not in (1, 3):
                        continue
                    raw = selector["values"][0] if selector.get("values") else None
                    number = _direct(raw)
                    target = f"{'Costume' if subop == 1 else 'Sound'}({number})" if number is not None else None
                    edges.append(_edge(source, target, "costume-reference" if subop == 1 else "sound-reference",
                                       certainty if number is not None else "DYNAMIC", ins.pc,
                                       expression=None if number is not None else f"actorOps operand {raw!r}",
                                       domain="resource"))
                    actor_id = _direct(operands.get("actor"))
                    if subop == 1 and actor_id is not None and number is not None:
                        edges.append(_edge(f"Actor({actor_id})", target, "actor-uses-costume",
                                           certainty, ins.pc, domain="resource"))
            elif ins.operation == "resource_routines":
                subop = int(operands.get("subop", 0))
                number = _direct(operands.get("resource"))
                category = {1: "GlobalScript", 2: "Sound", 3: "Costume", 4: "RoomResource",
                            18: "Charset", 19: "Charset"}.get(subop, "Resource")
                target = f"{category}({number})" if number is not None else None
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
        group = _capability_group(operation)
        opcodes = sorted({instruction.opcode for _, instruction in occurrences})
        is_opaque = operation == "opaque_bytecode_tail"
        if is_opaque:
            frontend = "UNSUPPORTED"
            ir_status = "PARTIAL"
            host_status = "UNKNOWN"
            reason = "instruction width/semantics are not decoded; tail remains opaque"
        else:
            frontend = "SUPPORTED"
            ir_status = "SUPPORTED"
            handler_hits = [opcode in handlers for opcode in opcodes]
            host_status = ("UNSUPPORTED" if handler_hits and not any(handler_hits) else
                           "PARTIAL" if not all(handler_hits) else "PARTIAL")
            reason = ("dispatch handler exists, but operation-level conformance is not certified"
                      if all(handler_hits) else
                      "one or more decoded opcode variants have no host dispatch handler")
        record = {
            "capability": group,
            "operation": operation,
            "opcodes": [f"0x{opcode:02X}" for opcode in opcodes],
            "front_end_decode": {"status": frontend,
                                 "evidence": "shared SCUMM v5 decode_script result"},
            "ir_representation": {"status": ir_status,
                                  "evidence": "InstructionIR retains source PC and operands"},
            "snes_backend": {"status": "PARTIAL",
                             "evidence": "source script bytes are retained in SC5C; no per-op lowering certification"},
            "host_runtime": {"status": host_status, "evidence": reason},
            "snes_runtime": {"status": "UNKNOWN",
                             "evidence": "whole-game census does not certify native semantics"},
            "save_restore": {"status": "UNKNOWN",
                             "evidence": "not inferred from opcode decoding"},
            "native_conformance": {"status": "UNKNOWN",
                                   "evidence": "not inferred from source analysis"},
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
                "front_end_decode", "ir_representation", "snes_backend",
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
    dimension_names = ("front_end_decode", "ir_representation", "snes_backend",
                       "host_runtime", "snes_runtime", "save_restore", "native_conformance")
    severity = {"SUPPORTED": 0, "NOT_APPLICABLE": 0, "PARTIAL": 1,
                "UNKNOWN": 2, "UNSUPPORTED": 3}
    for group in sorted(set(_OP_TO_CAPABILITY.values()) | {"other-or-opaque"}):
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
    capabilities, frontier = analyze_capabilities(scripts, reachability, paths)
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
    max_body = max((len(script.program) for script in scripts.values()), default=0)
    max_fanout = max((sum(edge["source"] == node and edge["domain"] == "execution"
                          for edge in graph["edges"]) for node in scripts), default=0)
    capacity = {
        "executable_identities": {"value": total_programs,
                                  "epistemic": parsed_room_epistemic},
        "rooms_inventoried": {"value": len(game.rooms), "epistemic": "EXACT"},
        "rooms_semantically_parsed": {"value": len(compilations), "epistemic": "EXACT"},
        "objects": {"value": object_count, "epistemic": parsed_room_epistemic},
        "object_verb_entries": {"value": verb_count,
                                 "epistemic": parsed_room_epistemic},
        "largest_room_executable_bundle": {"value": max_room_bundle,
                                           "epistemic": parsed_room_epistemic},
        "largest_script_body_bytes": {"value": max_body,
                                       "epistemic": parsed_room_epistemic},
        "largest_known_execution_fanout": {"value": max_fanout, "epistemic": "EXACT_FOR_DECODED_EDGES"},
        "possible_program_selector_demand": {"value": total_programs, "epistemic": "STATIC_LOWER_BOUND"},
        "current_default_backend_selector_pool": (backend_selector_capacity or {
            "value": None, "epistemic": "UNKNOWN",
            "reason": "no SNES backend capacity provider was supplied; analysis allocates no selectors",
        }),
        "runtime_slot_pressure": {"value": None, "epistemic": "UNKNOWN",
                                   "reason": "dynamic scheduling and runtime coexistence are not bounded by static graph depth"},
    }
    return GameAnalysis(game, census, executable_report, graph, reachability,
                        capabilities, frontier, opaque, capacity, compilations)


def game_analysis_hash(files: dict[str, bytes]) -> str:
    """Hash a canonical output set independent of the destination directory."""
    entries = [{"path": name, "sha256": sha256(content)} for name, content in sorted(files.items())]
    return sha256(canonical_json(entries))
