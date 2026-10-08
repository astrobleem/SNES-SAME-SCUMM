"""Whole-source executable backend reconciliation and strict readiness gate.

The existing SNES backend stores canonical SCUMM v5 bytecode bodies and lets
the generic runtime interpret them.  This module verifies complete source
coverage and independently gates execution support; retaining bytecode is not
treated as semantic lowering or runtime certification.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from typing import Any, Mapping


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_semantic_identity(script: Any) -> str:
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


def source_program_bodies(
    analysis: Any, room_source_payloads: Mapping[int, bytes],
) -> dict[str, dict[str, Any]]:
    """Return the one selector-bearing source body for each canonical unit."""
    bodies: dict[str, dict[str, Any]] = {}
    for script in analysis.game_ir.global_scripts:
        identity = f"GlobalProgram({script.number})"
        bodies[identity] = {
            "body": script.program,
            "semantic_identities": [canonical_semantic_identity(script)],
            "source_provenance": script.source.__dict__ if hasattr(script.source, "__dict__") else {
                field: getattr(script.source, field)
                for field in script.source.__dataclass_fields__
            },
        }
    for room, compilation in sorted(analysis.room_compilations.items()):
        for script in compilation.room_ir.scripts:
            if script.kind == "OBCD":
                continue
            if script.kind == "ENCD":
                identity = f"RoomEntryProgram({room})"
            elif script.kind == "EXCD":
                identity = f"RoomExitProgram({room})"
            elif script.kind == "LSCR":
                identity = f"RoomLocalProgram(room={room},local={script.number})"
            else:
                continue
            if identity in bodies:
                raise ValueError(f"duplicate source executable carrier {identity}")
            bodies[identity] = {
                "body": script.program,
                "semantic_identities": [canonical_semantic_identity(script)],
                "source_provenance": {
                    field: getattr(script.source, field)
                    for field in script.source.__dataclass_fields__
                },
            }
        source_room = room_source_payloads.get(room)
        if source_room is None:
            raise ValueError(f"whole-source analysis omitted source bytes for room {room}")
        for obj in compilation.room_ir.objects:
            if not obj.verbs:
                continue
            manifest = next((row for row in compilation.record_manifest.get("objects", [])
                             if int(row["object_id"]) == obj.object_id), None)
            if manifest is None:
                raise ValueError(f"room {room} object {obj.object_id} lacks source OBCD metadata")
            offset, length = int(manifest["obcd_room_offset"]), int(manifest["obcd_length"])
            body = source_room[offset:offset + length]
            if len(body) != length or sha256(body) != obj.obcd_sha256:
                raise ValueError(f"room {room} object {obj.object_id} OBCD source mismatch")
            identity = f"ObjectProgram(room={room},object={obj.object_id})"
            if identity in bodies:
                raise ValueError(f"duplicate source executable carrier {identity}")
            bodies[identity] = {
                "body": body,
                "semantic_identities": [
                    f"ObjectVerb(room={room},object={obj.object_id},verb={verb.verb_id})"
                    for verb in obj.verbs
                ],
                "source_provenance": {
                    "game": analysis.game_ir.game_id,
                    "resource_key": compilation.room_ir.resource_key,
                    "source_member": compilation.room_ir.source_member,
                    "room": room,
                    "object_id": obj.object_id,
                    "source_offset": obj.source_offset,
                    "source_length": length,
                    "source_sha256": obj.obcd_sha256,
                },
            }
    return bodies


def validate_emitted_program_directory(
    analysis: Any,
    backend_report: Mapping[str, Any],
    room_source_payloads: Mapping[int, bytes],
) -> dict[str, Any]:
    """Cross-check emitted code records against the canonical source directory."""
    source_bodies = source_program_bodies(analysis, room_source_payloads)
    expected = {
        str(row["identity"]): int(row["program_unit_id"])
        for row in analysis.native_program_directory["entries"]
    }
    emitted_rows = backend_report.get("program_map", [])
    emitted = {str(row["program_unit_identity"]): row for row in emitted_rows}
    missing = sorted(set(expected) - set(emitted))
    extra = sorted(set(emitted) - set(expected))
    mismatches = []
    for identity in sorted(set(expected) & set(emitted) & set(source_bodies)):
        source = source_bodies[identity]["body"]
        row = emitted[identity]
        if (int(row["id"]) != expected[identity]
                or int(row["length"]) != len(source)
                or str(row["sha256"]) != sha256(source)):
            mismatches.append({
                "program_unit": identity,
                "expected_id": expected[identity], "emitted_id": row.get("id"),
                "expected_length": len(source), "emitted_length": row.get("length"),
                "expected_sha256": sha256(source), "emitted_sha256": row.get("sha256"),
            })
    missing_bodies = sorted(set(expected) - set(source_bodies))
    result = {
        "source_program_units": len(expected),
        "emitted_program_units": len(emitted),
        "body_sources_resolved": len(source_bodies),
        "missing_program_units": missing,
        "extra_program_units": extra,
        "missing_source_bodies": missing_bodies,
        "body_or_identity_mismatches": mismatches,
        "complete_and_source_identical": not (missing or extra or missing_bodies or mismatches),
    }
    return result


def build_lowering_report(analysis: Any) -> dict[str, Any]:
    """Classify every emitted carrier using independent execution evidence."""
    registry = analysis.capabilities["registry_by_operation"]
    reachability = analysis.reachability["status_by_executable"]
    scripts: dict[str, Any] = {}
    for script in analysis.game_ir.global_scripts:
        scripts[canonical_semantic_identity(script)] = script
    for compilation in analysis.room_compilations.values():
        for script in compilation.room_ir.scripts:
            scripts[canonical_semantic_identity(script)] = script

    diagnostics: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    unit_status: dict[str, str] = {}
    family_counts: Counter[str] = Counter()
    reach_counts: Counter[str] = Counter()
    for carrier in analysis.selector_demand["executable_carriers"]:
        unit = str(carrier["identity"])
        semantic_ids = carrier.get("contained_semantic_executable_identities", [])
        status = "LOWERABLE_WITH_EVIDENCE"
        for semantic in semantic_ids:
            script = scripts.get(semantic)
            if script is None:
                status = "BLOCKED"
                diagnostics[(unit, -1, "source_mapping", "semantic_source_missing")] = {
                    "program_unit": unit, "semantic_executable": semantic,
                    "source_pc": None, "operation": "source_mapping",
                    "missing_dimension": "semantic_source_identity",
                    "status": "UNSUPPORTED",
                    "reachability": "UNRESOLVED",
                    "required_subsystem": "front_end_source_mapping",
                    "dependency_path": None,
                }
                continue
            executable_reach = reachability.get(semantic, "UNRESOLVED")
            for instruction in script.instructions:
                operation = instruction.operation
                evidence = registry.get(operation)
                required = ("snes_backend", "snes_runtime", "native_conformance")
                missing = []
                if evidence is None:
                    missing = [(name, "UNKNOWN", "operation has no capability registry row")
                               for name in required]
                else:
                    for dimension in required:
                        row = evidence.get(dimension, {})
                        dimension_status = str(row.get("status", "UNKNOWN"))
                        if dimension_status != "SUPPORTED":
                            missing.append((dimension, dimension_status,
                                            str(row.get("evidence", "no evidence"))))
                if instruction.semantic_status != "SEMANTIC_IR_AVAILABLE":
                    missing.append(("semantic_ir", instruction.semantic_status,
                                    "instruction does not have complete semantic IR"))
                if instruction.structural_status != "STRUCTURALLY_DECODED":
                    missing.append(("front_end_decode", instruction.structural_status,
                                    "instruction boundary/operands are not fully decoded"))
                if not missing:
                    continue
                if any(value == "UNSUPPORTED" for _, value, _ in missing):
                    status = "BLOCKED"
                elif status != "BLOCKED":
                    status = "UNVERIFIED"
                reach = executable_reach
                if instruction.cfg_reachability == "DECODED_UNREACHABLE":
                    reach = "UNREACHED"
                elif instruction.cfg_reachability == "CONTROL_FLOW_UNCERTAIN":
                    reach = "UNRESOLVED"
                reach_counts[reach] += 1
                for dimension, dimension_status, evidence_text in missing:
                    key = (unit, int(instruction.pc), operation, dimension)
                    diagnostics[key] = {
                        "program_unit": unit,
                        "semantic_executable": semantic,
                        "source": {
                            "member": script.source.source_member,
                            "resource_key": script.source.resource_key,
                            "room": script.source.room,
                            "script_kind": script.kind,
                            "script_number": script.number,
                            "object_id": script.object_id,
                            "verb_id": script.verb_id,
                            "source_pc": int(instruction.pc),
                            "source_byte_offset": int(instruction.source_offset),
                            "body_sha256": script.source.source_sha256,
                        },
                        "operation": operation,
                        "raw_opcode": f"0x{instruction.opcode:02X}",
                        "missing_dimension": dimension,
                        "status": dimension_status,
                        "evidence": evidence_text,
                        "reachability": reach,
                        "dependency_path": analysis.reachability.get(
                            "path_by_executable", {}).get(semantic),
                        "required_subsystem": (
                            evidence.get("capability", operation) if evidence else operation
                        ),
                    }
                    family_counts[operation] += 1
        unit_status[unit] = status
    records = sorted(diagnostics.values(), key=lambda row: (
        row["program_unit"], -1 if row.get("source", {}).get("source_pc") is None
        else row["source"]["source_pc"], row["operation"], row["missing_dimension"],
    ))
    return {
        "schema": "same_scumm_v5_whole_source_lowering_report_v1",
        "strict_policy": {
            "required_status": "SUPPORTED",
            "dimensions": ["semantic_ir", "snes_backend", "snes_runtime",
                           "native_conformance"],
            "native_conformance_is_release_evidence": True,
            "save_restore_is_reported_separately": True,
            "unsupported_operations_are_never_rewritten_as_noops": True,
        },
        "program_unit_status_counts": dict(sorted(Counter(unit_status.values()).items())),
        "program_unit_status": dict(sorted(unit_status.items())),
        "diagnostic_count": len(records),
        "diagnostics_by_operation": dict(sorted(family_counts.items())),
        "diagnostics_by_reachability": dict(sorted(reach_counts.items())),
        "diagnostics": records,
        "execution_release_ready": not records,
        "whole_game_status": "NOT_READY" if records or not analysis.whole_game_readiness.get(
            "status") == "READY" else "READY",
        "resource_completeness_is_separate": True,
    }
