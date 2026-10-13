"""Reconcile source executables, OBCD resources, and actual VM selectors.

The legacy room generator assigns a selector to each included OBCD record,
including objects with no verb entries.  The native StartObject resolver is
gated by Verb_Query, so those data-only records cannot be entered by the VM.
This projection records both emitted allocation candidates and true dispatch
demand without changing the legacy backend output.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Any


def _semantic_identity(script: Any) -> str:
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


def build_selector_demand_model(
    scripts: dict[str, Any],
    room_compilations: dict[int, Any],
    dependency_graph: dict[str, Any],
    reachability: dict[str, Any],
    backend_records: dict[str, Any],
) -> dict[str, Any]:
    """Project source identities through callable carriers to selector units.

    In the current SNES dispatch ABI one callable carrier is one selector unit:
    script records are entered directly, while all verbs for one object share
    its complete OBCD and select an entry PC using the separate verb operand.
    """
    semantic_to_backend = backend_records["semantic_to_program_unit_index"]
    backend_by_id = {item["identity"]: item
                     for item in backend_records["program_units"]}
    carriers: dict[str, dict[str, Any]] = {}
    resources: list[dict[str, Any]] = []
    object_stats: Counter[str] = Counter()
    room_objects: dict[int, list[dict[str, Any]]] = defaultdict(list)

    # Every parsed OBCD is a resource record, regardless of whether it has a
    # callable verb entry. Provenance is copied from the shared RoomIR.
    for room, compilation in sorted(room_compilations.items()):
        script_by_object_verb = {
            (script.object_id, script.verb_id): script
            for script in compilation.room_ir.scripts
            if script.kind == "OBCD" and script.object_id is not None
        }
        manifest_objects = {
            int(item["object_id"]): item
            for item in compilation.record_manifest.get("objects", [])
        }
        for obj in compilation.room_ir.objects:
            backend_id = f"ObjectProgram(room={room},object={obj.object_id})"
            backend_row = backend_by_id.get(backend_id, {})
            manifest = manifest_objects.get(obj.object_id, {})
            raw_entries = manifest.get("verb_entries", [])
            ir_verbs = {verb.verb_id: verb for verb in obj.verbs}
            verb_rows = []
            for entry in raw_entries:
                verb_id = int(entry["verb"])
                verb_ir = ir_verbs.get(verb_id)
                source_script = script_by_object_verb.get((obj.object_id, verb_id))
                verb_rows.append({
                    "verb": verb_id,
                    "entry_offset": int(entry["entry_offset"]),
                    "source_offset": (verb_ir.source_offset if verb_ir else
                                      obj.source_offset + int(entry["entry_offset"])),
                    "body_sha256": verb_ir.source_sha256 if verb_ir else None,
                    "semantic_executable": (_semantic_identity(source_script)
                                             if source_script else None),
                    "analysis_status": ("SEMANTIC_IR" if source_script and
                                        source_script.decode_complete else
                                        "PARTIAL_SEMANTIC_IR" if source_script else
                                        "NO_SEMANTIC_IR_FOR_SOURCE_VERB_ENTRY"),
                    "opaque_from_pc": (source_script.opaque_from_pc
                                       if source_script else None),
                })
            decoded_count = sum(row["semantic_executable"] is not None
                                for row in verb_rows)
            if not verb_rows:
                classification = "DATA_ONLY_NO_VERB_ENTRY"
                object_stats["without_verb_entries"] += 1
            elif decoded_count == len(verb_rows):
                classification = "VERB_ENTRIES_WITH_SEMANTIC_IR"
                object_stats["with_decoded_verbs"] += 1
                if any(row["analysis_status"] == "PARTIAL_SEMANTIC_IR"
                       for row in verb_rows):
                    classification = "VERB_ENTRIES_WITH_PARTIAL_SEMANTIC_IR"
            else:
                classification = "VERB_ENTRY_WITHOUT_SEMANTIC_IR"
                object_stats["verb_entries_without_semantic_ir"] += 1
            object_stats["malformed_or_truncated_verb_entries"] += sum(
                row["analysis_status"] == "PARTIAL_SEMANTIC_IR"
                and any(item.structural_status in {"MALFORMED", "TRUNCATED"}
                        for item in script_by_object_verb[
                            (obj.object_id, row["verb"])].instructions)
                for row in verb_rows)
            object_scripts = [script_by_object_verb.get((obj.object_id, row["verb"]))
                              for row in verb_rows]
            object_scripts = [item for item in object_scripts if item is not None]
            object_stats["objects_with_incomplete_verb_decode"] += any(
                not script.decode_complete for script in object_scripts)
            object_stats["objects_with_structural_unknown_verbs"] += any(
                instruction.structural_status in {"STRUCTURAL_UNKNOWN", "UNSUPPORTED_DECODE"}
                for script in object_scripts for instruction in script.instructions)
            object_stats["objects_with_semantically_unsupported_verbs"] += any(
                instruction.semantic_status == "SEMANTIC_UNSUPPORTED"
                for script in object_scripts for instruction in script.instructions)
            object_stats["total"] += 1
            object_stats["with_verb_entries"] += bool(verb_rows)

            resource = {
                "identity": f"ObjectResource(room={room},object={obj.object_id})",
                "kind": "OBCD_RESOURCE",
                "room": room,
                "object": obj.object_id,
                "source_provenance": {
                    "game": next((script.source.game
                                  for script in compilation.room_ir.scripts), None),
                    "resource_key": compilation.room_ir.resource_key,
                    "source_member": compilation.room_ir.source_member,
                    "room_source_offset": compilation.room_ir.room_source_offset,
                    "object_source_offset": obj.source_offset,
                    "payload_offset": manifest.get("obcd_room_offset"),
                    "source_length": manifest.get("obcd_length"),
                    "source_sha256": obj.obcd_sha256,
                    "verb_table_offset": manifest.get("verb_table_offset"),
                    "verb_table_length": manifest.get("verb_table_length"),
                },
                "object_metadata": {
                    "x": obj.x, "y": obj.y, "width": obj.width,
                    "height": obj.height, "flags": obj.flags,
                    "parent": obj.parent, "owner": obj.owner,
                    "initial_state": obj.initial_state,
                    "initial_classes": obj.initial_classes,
                    "walk_x": obj.walk_x, "walk_y": obj.walk_y,
                    "actor_direction": obj.actor_direction,
                },
                "verb_entries": verb_rows,
                "has_object_resource_record": True,
                "has_decoded_verb_bodies": bool(obj.verbs),
                "has_executable_object_carrier": bool(raw_entries),
                "legacy_backend_program_record_exists": backend_id in backend_by_id,
                "legacy_selector_assigned_if_included": backend_id in backend_by_id,
                "runtime_selector_referenced": bool(raw_entries),
                "selector_required_semantically": (
                    "YES" if raw_entries else "NO"),
                "executable_carrier": backend_id if raw_entries else None,
                "selector_unit": backend_id if raw_entries else None,
                "selector_disposition": (
                    "SELECTOR_UNIT" if raw_entries else "NO_SELECTOR_REQUIRED"),
                "selector_required_by_current_dispatch": bool(raw_entries),
                "selector_reason": (
                    "OBCD_VERB_ENTRY_IS_RESOLVABLE_BY_ACTIVE_ROOM_OBJECT_AND_VERB"
                    if raw_entries else
                    "NO_VERB_ENTRY; native Verb_Query rejects before object selector lookup"),
                "legacy_generator_allocates_selector_if_included": (
                    backend_id in backend_by_id),
                "analysis_classification": classification,
            }
            resources.append(resource)
            room_objects[room].append(resource)

            if raw_entries:
                carrier = dict(backend_row)
                carrier["raw_verb_entries"] = raw_entries
                if not any(row["semantic_executable"] is not None for row in verb_rows):
                    carrier["analysis_status"] = "SOURCE_VERB_ENTRY_WITHOUT_SEMANTIC_IR"
                carrier["legacy_generator_allocates_selector_if_included"] = True
                carrier["runtime_selector_referenced"] = True
                carrier["selector_required_by_current_dispatch"] = True
                carrier["contained_semantic_executable_identities"] = list(
                    carrier.get("semantic_executable_identities", []))
                carrier["executable_carrier_identity"] = backend_id
                carrier["selector_unit_identity"] = backend_id
                carrier["dispatch_metadata"] = {
                    "path": "StartObject -> ObjectProgram_Resolve -> Verb_Query",
                    "lookup_key": ["active room record", "object id", "verb id"],
                    "selector_identifies": "complete OBCD object program",
                    "entry_pc_selected_by": "verb table OBCD-relative entry offset",
                }
                carriers[backend_id] = carrier

    # Non-object script records are entered directly through selector dispatch.
    for backend_id, backend_row in sorted(backend_by_id.items()):
        if backend_row["kind"] == "OBJECT":
            continue
        row = dict(backend_row)
        row["legacy_generator_allocates_selector_if_included"] = True
        row["runtime_selector_referenced"] = True
        row["selector_required_by_current_dispatch"] = True
        row["contained_semantic_executable_identities"] = list(
            row.get("semantic_executable_identities", []))
        row["executable_carrier_identity"] = backend_id
        row["selector_unit_identity"] = backend_id
        row["dispatch_metadata"] = {
            "path": "SCUMM program selector dispatch",
            "lookup_key": ({"script_number": row["owner"].get("global")}
                           if row["kind"] == "GLOBAL" else
                           {"room": row["owner"].get("room"), "kind": row["kind"]}),
            "selector_identifies": "complete SC5C script program record",
        }
        carriers[backend_id] = row

    semantic_rows = []
    semantic_to_selector: dict[str, str] = {}
    for script in sorted(scripts.values(), key=_semantic_identity):
        semantic = _semantic_identity(script)
        backend_id = semantic_to_backend.get(semantic)
        # The source parser creates semantic OBCD scripts only from valid verb
        # table entries. Any disagreement is surfaced as unknown, never guessed.
        selector_id = backend_id if backend_id in carriers else None
        if selector_id is None:
            disposition = "NO_SELECTOR_REQUIRED" if script.kind == "OBCD" else "UNRESOLVED_SELECTOR_DEMAND"
            reason = ("semantic OBCD identity lacks a callable carrier; inspect source mapping"
                      if script.kind == "OBCD" else
                      "backend carrier missing for semantic executable")
        else:
            disposition = "SHARED_SELECTOR_UNIT" if script.kind == "OBCD" else "ONE_SELECTOR_UNIT"
            reason = ("all verbs of one object share the OBCD selector; verb selects entry PC"
                      if script.kind == "OBCD" else
                      "current dispatch enters this script record through one selector")
            semantic_to_selector[semantic] = selector_id
        semantic_rows.append({
            "semantic_executable": semantic,
            "resource_record": (f"ObjectResource(room={script.source.room},object={script.object_id})"
                                if script.kind == "OBCD" else None),
            "executable_carrier": selector_id,
            "selector_unit": selector_id,
            "disposition": disposition,
            "reason": reason,
            "source_provenance": asdict(script.source),
        })

    carrier_for_semantic = {
        _semantic_identity(script): semantic_to_selector.get(_semantic_identity(script))
        for script in scripts.values()
    }
    dependencies = []
    for edge in backend_records.get("dependencies", []):
        source_semantic = edge.get("source_semantic_identity")
        source_unit = carrier_for_semantic.get(source_semantic)
        if source_unit is None:
            continue
        target_semantic = edge.get("target_semantic_identity")
        target_unit = carrier_for_semantic.get(target_semantic) if target_semantic else None
        # Backend dependency candidate fields are unit identities, not semantic
        # identities. Resolve by unit identity and omit data-only records.
        candidates = sorted({item for item in edge.get("candidate_program_units", [])
                             if item in carriers})
        dependencies.append({
            "source_selector_unit": source_unit,
            "source_semantic_executable": source_semantic,
            "target_selector_unit": target_unit,
            "target_semantic_executable": target_semantic,
            "target_resource": edge.get("target_resource_identity"),
            "kind": edge.get("kind"), "resolution": edge.get("resolution"),
            "domain": edge.get("domain", "execution"),
            "source_pc": edge.get("source_pc"),
            "expression": edge.get("expression"),
            "candidate_selector_units": candidates,
            "detail": edge.get("detail"),
        })
    dependencies.sort(key=lambda item: (
        item["source_selector_unit"], item["source_semantic_executable"],
        -1 if item.get("source_pc") is None else item["source_pc"],
        item.get("kind") or "", item.get("target_selector_unit") or ""))
    deps_by_carrier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in dependencies:
        deps_by_carrier[edge["source_selector_unit"]].append(edge)
    for identity, row in carriers.items():
        row["dependencies"] = deps_by_carrier.get(identity, [])

    counts = Counter(row["kind"] for row in carriers.values())
    return {
        "schema": "same_scumm_v5_true_selector_demand_v1",
        "identity_invariant": (
            "semantic executable identities, resource records, executable carriers, "
            "selector units, and runtime selector values are distinct; in the current "
            "dispatch ABI each executable carrier is one selector unit"),
        "selector_values_emitted": False,
        "backend_program_unit_projection": "legacy backend records; includes OBCD records which are emitted with IDs but unreachable when they have no verb entries",
        "semantic_executable_to_selector": semantic_rows,
        "semantic_to_selector_index": dict(sorted(semantic_to_selector.items())),
        "resource_records": sorted(resources, key=lambda item: item["identity"]),
        "executable_carriers": [carriers[key] for key in sorted(carriers)],
        "selector_units": [carriers[key] for key in sorted(carriers)],
        "dependencies": dependencies,
        "counts": {
            "semantic_executable_identities": len(scripts),
            "resource_records": len(resources),
            "executable_carriers": len(carriers),
            "selector_units": len(carriers),
            "legacy_backend_program_records_that_receive_ids_if_included": len(backend_by_id),
            "legacy_projected_ids_with_no_runtime_reference_if_included": sum(
                1 for item in resources
                if item["legacy_generator_allocates_selector_if_included"]
                and not item["selector_required_by_current_dispatch"]),
            "by_selector_unit_kind": {name: counts.get(name, 0) for name in
                                       ("GLOBAL", "ROOM_ENTRY", "ROOM_EXIT", "ROOM_LOCAL", "OBJECT", "OTHER")},
            "semantic_executables_without_selector": sum(
                item["selector_unit"] is None for item in semantic_rows),
            "max_semantic_executables_per_selector_unit": max(
                (len(row["contained_semantic_executable_identities"])
                 for row in carriers.values()), default=0),
            "objects": {
                "total": object_stats["total"],
                "with_verb_entries": object_stats["with_verb_entries"],
                "without_verb_entries": object_stats["without_verb_entries"],
                "with_decoded_verbs": object_stats["with_decoded_verbs"],
                "verb_entries_without_semantic_ir": object_stats["verb_entries_without_semantic_ir"],
                "objects_with_incomplete_verb_decode": object_stats["objects_with_incomplete_verb_decode"],
                "malformed_or_truncated_verb_entries": object_stats["malformed_or_truncated_verb_entries"],
                "objects_with_structural_unknown_verbs": object_stats["objects_with_structural_unknown_verbs"],
                "objects_with_semantically_unsupported_verbs": object_stats["objects_with_semantically_unsupported_verbs"],
            },
        },
        "room_objects": {str(room): sorted(rows, key=lambda item: item["identity"])
                         for room, rows in sorted(room_objects.items())},
    }


def build_selector_directory(model: dict[str, Any]) -> dict[str, Any]:
    """Produce stable bundle-local indexes without assigning selector bytes."""
    bundles: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in model["selector_units"]:
        bundles[unit["bundle"]].append(unit)
    bundle_rows = []
    for bundle, units in sorted(bundles.items()):
        unit_rows = []
        for local_index, unit in enumerate(sorted(units, key=lambda item: item["identity"])):
            unit_rows.append({
                "local_bundle_index": local_index,
                "selector_unit_identity": unit["identity"],
                "executable_carrier_identity": unit["executable_carrier_identity"],
                "kind": unit["kind"], "residency_scope": unit["residency_scope"],
                "owner": unit.get("owner", {}),
                "contained_semantic_executables": unit["contained_semantic_executable_identities"],
                "compiled_representation": unit["compiled_representation"],
                "dispatch_metadata": unit["dispatch_metadata"],
                "source_provenance": unit["source_provenance"],
                "dependencies": unit["dependencies"],
            })
        bundle_rows.append({"identity": bundle, "selector_units": unit_rows})
    global_directory = []
    for bundle_row in bundle_rows:
        if bundle_row["identity"] != "GlobalBundle":
            continue
        for unit in bundle_row["selector_units"]:
            script_number = unit["dispatch_metadata"].get("lookup_key", {}).get("script_number")
            if script_number is None:
                raise ValueError(
                    f"global SelectorUnit lacks canonical script number: "
                    f"{unit['selector_unit_identity']}"
                )
            global_directory.append({
                "script_number": int(script_number),
                "program_unit_identity": unit["selector_unit_identity"],
                "bundle_identity": bundle_row["identity"],
                "local_bundle_index": unit["local_bundle_index"],
            })
    global_directory.sort(key=lambda item: item["script_number"])
    room_bundle_directory = []
    for bundle_row in bundle_rows:
        if bundle_row["identity"] == "GlobalBundle":
            continue
        units = bundle_row["selector_units"]
        rooms = {item.get("owner", {}).get("room") for item in units
                 if item.get("owner", {}).get("room") is not None}
        if len(rooms) > 1:
            raise ValueError(f"room bundle has multiple room owners: {bundle_row['identity']}")
        room_bundle_directory.append({
            "bundle_identity": bundle_row["identity"],
            "room": next(iter(rooms)) if rooms else None,
            "selector_unit_count": len(units),
            "selector_units_by_kind": dict(sorted(Counter(
                item["kind"] for item in units).items())),
            "selector_unit_identities": [item["selector_unit_identity"]
                                         for item in units],
        })
    return {
        "schema": "same_scumm_v5_selector_free_directory_v2",
        "selector_values_emitted": False,
        "identity_invariant": "directory indices are bundle-local compiler identities, not runtime selectors",
        "bundles": bundle_rows,
        "room_bundle_directory": room_bundle_directory,
        "global_directory": global_directory,
        "dynamic_global_resolver": {
            "input": "runtime global script number",
            "lookup": "global_directory.script_number -> program_unit_identity",
            "candidate_count": len(global_directory),
            "prebind_candidates": False,
            "missing_target": "fail with UnknownProgramUnit; never alias",
        },
        "residency_metadata": {
            "room_bundle_policy": "eagerly bind selector units for the active room bundle",
            "global_policy": "lazy resolve and bind on dispatch; preserve while pinned",
            "selector_assignment": "deferred to runtime/backend binder",
            "pin_reasons": [
                "ACTIVE_SCRIPT_SLOT", "YIELDED_SCRIPT", "NESTED_PARENT",
                "ROOM_CONTINUATION", "CUTSCENE_OVERRIDE", "ROOM_LIFECYCLE",
                "SENTENCE_EXECUTION", "SAVE_RESTORE_RECONSTRUCTION",
            ],
        },
        "data_only_resource_records": [
            {"identity": row["identity"], "room": row["room"], "object": row["object"],
             "source_provenance": row["source_provenance"],
             "selector_disposition": row["selector_disposition"],
             "selector_reason": row["selector_reason"]}
            for row in model["resource_records"] if row["selector_unit"] is None
        ],
    }
