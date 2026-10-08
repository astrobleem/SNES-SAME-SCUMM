"""Source-bound semantic-family frontier and deterministic work ranking."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Any


_REACH_RANK = {
    "ROOT": 0, "DEFINITE": 0, "CONDITIONAL": 1, "POSSIBLE": 2,
    "UNRESOLVED": 3, "UNREACHED": 4,
}
_SUPPORT_RANK = {
    "SUPPORTED": 0, "NOT_APPLICABLE": 0, "PARTIAL": 1,
    "UNKNOWN": 2, "UNSUPPORTED": 3,
}
_SUPPORT_FIELDS = (
    "front_end_decode", "semantic_ir", "host_runtime", "snes_backend",
    "snes_runtime", "save_restore", "native_conformance",
)


def _worst_status(values: list[str]) -> str:
    return max(values, key=lambda value: _SUPPORT_RANK.get(value, 2), default="UNKNOWN")


def build_capability_frontier(
    scripts: dict[str, Any], reachability: dict[str, Any],
    paths: dict[str, list[str]], capabilities: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate instruction support by dialect family, preserving provenance.

    Reachability applies to the containing executable. The report counts both
    instruction occurrences and affected executable bodies so a large family
    in one body is not confused with broad corpus coverage.
    """
    registry = capabilities["registry_by_operation"]
    statuses = reachability["status_by_executable"]
    rows: dict[str, list[tuple[str, Any, Any]]] = defaultdict(list)
    for identity, script in sorted(scripts.items()):
        for instruction in script.instructions:
            family = instruction.opcode_family or instruction.operation
            rows[str(family)].append((identity, script, instruction))

    families: list[dict[str, Any]] = []
    for family, occurrences in sorted(rows.items()):
        semantic_gaps = [item for item in occurrences
                         if item[2].semantic_status != "SEMANTIC_IR_AVAILABLE"]
        if not semantic_gaps:
            continue
        reach_counts: Counter[str] = Counter()
        reach_bodies: dict[str, set[str]] = defaultdict(set)
        kind_counts: Counter[str] = Counter()
        affected_rooms: set[int] = set()
        examples = []
        operations = sorted({item[2].operation for item in occurrences})
        support_records = [registry[operation] for operation in operations
                           if operation in registry]
        support = {
            field: _worst_status([
                record.get(field, {}).get("status", "UNKNOWN")
                for record in support_records
            ])
            for field in _SUPPORT_FIELDS
        }
        for identity, script, instruction in semantic_gaps:
            reachable = statuses.get(identity, "UNRESOLVED")
            reach_counts[reachable] += 1
            reach_bodies[reachable].add(identity)
            kind = {
                "SCRP": "global_script", "ENCD": "room_entry", "EXCD": "room_exit",
                "LSCR": "room_local", "OBCD": "object_verb",
            }.get(script.kind, "other_executable")
            kind_counts[kind] += 1
            if script.source.room is not None:
                affected_rooms.add(int(script.source.room))
            if len(examples) < 8:
                examples.append((identity, script, instruction, reachable))

        ordered = sorted(examples, key=lambda item: (
            _REACH_RANK.get(item[3], 5), len(paths.get(item[0], [])),
            item[0], item[2].pc,
        ))
        # Select path witnesses from all gaps, not just the first source-order
        # examples, then retain the root-nearest three distinct executables.
        witnesses: dict[str, dict[str, Any]] = {}
        for identity, script, instruction in semantic_gaps:
            reachable = statuses.get(identity, "UNRESOLVED")
            if reachable == "UNREACHED":
                continue
            candidate = {
                "source_identity": identity,
                "source_pc": instruction.pc,
                "source_body_sha256": script.source.source_sha256,
                "source": asdict(script.source),
                "reachability": reachable,
                "dependency_path": paths.get(identity),
                "path_status": "KNOWN" if identity in paths else "UNRESOLVED",
                "operation": instruction.operation,
            }
            old = witnesses.get(identity)
            if old is None or (instruction.pc, instruction.operation) < (
                    old["source_pc"], old["operation"]):
                witnesses[identity] = candidate
        root_nearest = sorted(witnesses.values(), key=lambda item: (
            _REACH_RANK.get(item["reachability"], 5),
            len(item["dependency_path"] or []), item["source_identity"],
            item["source_pc"],
        ))[:3]
        reach_class = min(
            (name for name, count in reach_counts.items() if count),
            key=lambda name: _REACH_RANK.get(name, 5), default="UNREACHED",
        )
        classification = {
            "ROOT": "DEFINITE_SEMANTIC_GAP",
            "DEFINITE": "DEFINITE_SEMANTIC_GAP",
            "CONDITIONAL": "CONDITIONAL_SEMANTIC_GAP",
            "POSSIBLE": "POSSIBLE_DYNAMIC_SEMANTIC_GAP",
            "UNRESOLVED": "UNRESOLVED_REACHABILITY_GAP",
            "UNREACHED": "CORPUS_ONLY_SEMANTIC_GAP",
        }[reach_class]
        unsupported = sum(item[2].semantic_status == "SEMANTIC_UNSUPPORTED"
                          for item in semantic_gaps)
        unknown = sum(item[2].semantic_status == "SEMANTIC_UNKNOWN"
                      for item in semantic_gaps)
        structural = Counter(item[2].structural_status for item in semantic_gaps)
        op_caps = sorted({item[2].semantic_capability for item in occurrences
                          if item[2].semantic_capability})
        body_count = len({item[0] for item in semantic_gaps})
        rank = (
            _REACH_RANK.get(reach_class, 5),
            -unsupported,
            -body_count,
            -len(occurrences),
            family,
        )
        families.append({
            "family": family,
            "semantic_capabilities": op_caps,
            "operations": operations,
            "occurrences": len(occurrences),
            "semantic_gap_occurrences": len(semantic_gaps),
            "semantic_unsupported_occurrences": unsupported,
            "semantic_unknown_occurrences": unknown,
            "affected_executables": body_count,
            "rooms_affected": len(affected_rooms),
            "room_ids_for_external_acceptance": sorted(affected_rooms),
            "semantic_gap_occurrences_by_executable_kind": dict(sorted(kind_counts.items())),
            "structural_statuses_at_semantic_gap": dict(sorted(structural.items())),
            "reachability": {
                reach_class_name: {
                    "occurrences": reach_counts[reach_class_name],
                    "executables": len(reach_bodies[reach_class_name]),
                }
                for reach_class_name in sorted(reach_counts,
                    key=lambda name: _REACH_RANK.get(name, 5))
            },
            "priority_class": classification,
            "priority_key": list(rank[:-1]),
            "support": support,
            "support_scope": "aggregate of current operation-level registry evidence; not per-op conformance certification",
            "root_nearest_paths": root_nearest,
            "representative_sources": [
                {
                    "source_identity": identity, "source_pc": instruction.pc,
                    "operation": instruction.operation,
                    "raw_opcode": f"0x{instruction.opcode:02X}",
                    "subopcode": (None if instruction.subopcode is None
                                  else f"0x{instruction.subopcode:02X}"),
                    "reachability": reachable,
                    "source": asdict(script.source),
                    "source_body_sha256": script.source.source_sha256,
                    "dependency_path": paths.get(identity),
                }
                for identity, script, instruction, reachable in ordered[:5]
            ],
            "stateful_semantics_save_implication": (
                "UNKNOWN; capability census does not infer portable save coverage"
            ),
        })

    families.sort(key=lambda row: (
        _REACH_RANK.get(next((name for name, evidence in row["reachability"].items()
                              if evidence["occurrences"]), "UNREACHED"), 5),
        -row["semantic_unsupported_occurrences"],
        -row["affected_executables"], -row["occurrences"], row["family"],
    ))
    for index, row in enumerate(families, 1):
        row["priority_rank"] = index
        reachable_counts = row["reachability"]
        row["priority_reason"] = (
            f"{row['priority_class']}; {row['semantic_unsupported_occurrences']} unsupported "
            f"occurrences across {row['affected_executables']} executable bodies; "
            f"support dimensions remain independently reported"
        )

    # Semantic-IR completeness is not a proxy for executable support. Keep a
    # second, independent frontier that includes operations whose IR is
    # available but whose host/backend/runtime evidence remains partial,
    # unknown, or unsupported.
    support_families: list[dict[str, Any]] = []
    for family, occurrences in sorted(rows.items()):
        operations = sorted({item[2].operation for item in occurrences})
        records = [registry[operation] for operation in operations
                   if operation in registry]
        support = {
            field: _worst_status([
                record.get(field, {}).get("status", "UNKNOWN") for record in records
            ])
            for field in _SUPPORT_FIELDS
        }
        gaps = {name: value for name, value in support.items()
                if value not in {"SUPPORTED", "NOT_APPLICABLE"}}
        if not gaps:
            continue
        reach_counts: Counter[str] = Counter()
        reach_bodies: dict[str, set[str]] = defaultdict(set)
        body_locations: dict[str, tuple[Any, Any, Any, str]] = {}
        affected_rooms: set[int] = set()
        for identity, script, instruction in occurrences:
            reachable = statuses.get(identity, "UNRESOLVED")
            reach_counts[reachable] += 1
            reach_bodies[reachable].add(identity)
            if script.source.room is not None:
                affected_rooms.add(int(script.source.room))
            existing = body_locations.get(identity)
            candidate = (script, instruction, paths.get(identity), reachable)
            if existing is None or instruction.pc < existing[1].pc:
                body_locations[identity] = candidate
        best_reach = min(
            reach_counts, key=lambda name: _REACH_RANK.get(name, 5),
            default="UNREACHED",
        )
        execution_dimensions = ("semantic_ir", "host_runtime", "snes_backend",
                                "snes_runtime", "native_conformance")
        known_unsupported = any(
            support.get(name) == "UNSUPPORTED" for name in execution_dimensions
        )
        outcome = "BLOCKER" if known_unsupported else "UNVERIFIED"
        classification = {
            "ROOT": f"DEFINITE_{outcome}", "DEFINITE": f"DEFINITE_{outcome}",
            "CONDITIONAL": f"CONDITIONAL_{outcome}",
            "POSSIBLE": "POSSIBLE_DYNAMIC_REQUIREMENT",
            "UNRESOLVED": "UNRESOLVED_REQUIREMENT",
            "UNREACHED": "CORPUS_ONLY_REQUIREMENT",
        }[best_reach]
        examples = []
        for identity, (script, instruction, path, reachable) in sorted(
                body_locations.items(), key=lambda item: (
                    _REACH_RANK.get(item[1][3], 5),
                    len(item[1][2] or []), item[0], item[1][1].pc))[:5]:
            examples.append({
                "source_identity": identity, "source_pc": instruction.pc,
                "operation": instruction.operation,
                "raw_opcode": f"0x{instruction.opcode:02X}",
                "source": asdict(script.source),
                "source_body_sha256": script.source.source_sha256,
                "reachability": reachable, "dependency_path": path,
            })
        known_gaps = sum(value in {"PARTIAL", "UNSUPPORTED"}
                         for name, value in gaps.items()
                         if name in execution_dimensions)
        unknown_gaps = sum(value == "UNKNOWN" for value in gaps.values())
        priority_tier = (
            (0 if best_reach in {"ROOT", "DEFINITE"} else
             1 if best_reach == "CONDITIONAL" else
             2 if best_reach == "POSSIBLE" else
             3 if best_reach == "UNRESOLVED" else 7)
            if known_unsupported else
            (4 if best_reach in {"ROOT", "DEFINITE"} else
             5 if best_reach == "CONDITIONAL" else
             6 if best_reach in {"POSSIBLE", "UNRESOLVED"} else 8)
        )
        rank = (
            priority_tier,
            -known_gaps, unknown_gaps,
            -len({identity for identity, _, _ in occurrences}),
            -len(occurrences), family,
        )
        support_families.append({
            "family": family, "operations": operations,
            "occurrences": len(occurrences),
            "affected_executables": len({identity for identity, _, _ in occurrences}),
            "rooms_affected": len(affected_rooms),
            "room_ids_for_external_acceptance": sorted(affected_rooms),
            "reachability": {
                name: {"occurrences": reach_counts[name],
                       "executables": len(reach_bodies[name])}
                for name in sorted(reach_counts,
                                   key=lambda value: _REACH_RANK.get(value, 5))
            },
            "priority_class": classification,
            "priority_key": list(rank[:-1]),
            "support": support,
            "gap_dimensions": gaps,
            "dependency_path_status": "source-bound paths are evidence, not proof of runtime execution",
            "representative_sources": examples,
        })
    support_families.sort(key=lambda row: (
        row["priority_key"][0],
        -sum(value in {"PARTIAL", "UNSUPPORTED"}
             for name, value in row["gap_dimensions"].items()
             if name in {"semantic_ir", "host_runtime", "snes_backend",
                         "snes_runtime", "native_conformance"}),
        sum(value == "UNKNOWN" for value in row["gap_dimensions"].values()),
        -row["affected_executables"], -row["occurrences"], row["family"],
    ))
    for index, row in enumerate(support_families, 1):
        row["priority_rank"] = index
    gap_occurrences = sum(row["semantic_gap_occurrences"] for row in families)
    return {
        "schema": "same_scumm_v5_capability_frontier_v1",
        "grouping": "SCUMM v5 opcode family; raw flag variants are aggregated",
        "priority_policy": [
            "definite/root semantic gaps", "conditional semantic gaps",
            "possible/dynamic semantic gaps", "unresolved reachability gaps",
            "corpus-only gaps; within a tier rank by unsupported occurrences, bodies, then family size",
        ],
        "semantic_gap_occurrences": gap_occurrences,
        "semantic_unsupported_occurrences": sum(
            row["semantic_unsupported_occurrences"] for row in families),
        "semantic_unknown_occurrences": sum(
            row["semantic_unknown_occurrences"] for row in families),
        "family_count": len(families),
        "families": families,
        "support_frontier_count": len(support_families),
        "support_frontier": support_families,
        "invariant": "structural decode, semantic IR, host semantics, SNES backend/runtime support, and save coverage are independent dimensions",
    }


def build_whole_game_readiness(
    census: dict[str, Any], executables: dict[str, Any],
    opcode_coverage: dict[str, Any], capabilities: dict[str, Any],
    frontier: dict[str, Any],
) -> dict[str, Any]:
    """A conservative release-gate view; UNKNOWN is never promoted to support."""
    room_counts = census.get("room_analysis_status_counts", {})
    executable_counts = executables.get("counts", {})
    unsupported_semantics = frontier["semantic_unsupported_occurrences"]
    semantic_unknown = frontier["semantic_unknown_occurrences"]
    groups = capabilities.get("groups", {})
    dimensions = {}
    for dimension in ("semantic_ir", "host_runtime", "snes_backend", "snes_runtime"):
        statuses = [row["support_dimensions"].get(dimension, "UNKNOWN")
                    for row in groups.values()]
        dimensions[dimension] = _worst_status(statuses)
    reasons = []
    if census.get("rooms_unsupported"):
        reasons.append("one or more inventoried rooms are not semantically parsed")
    if executable_counts.get("UNSUPPORTED_DECODE", 0):
        reasons.append("executable control flow contains structurally unsupported boundaries")
    if executable_counts.get("MALFORMED", 0):
        reasons.append("one or more executable bodies are malformed or truncated")
    if unsupported_semantics:
        reasons.append("decoded reachable or corpus operations still lack normalized semantic IR")
    if semantic_unknown:
        reasons.append("semantic capability remains unknown for some structurally represented instructions")
    if dimensions["snes_backend"] != "SUPPORTED":
        reasons.append("whole-game SNES backend lowering is not certified for every observed family")
    if dimensions["snes_runtime"] != "SUPPORTED":
        reasons.append("whole-game SNES runtime semantics are not certified for every observed family")
    if dimensions["host_runtime"] != "SUPPORTED":
        reasons.append("host/reference runtime semantics are incomplete for one or more observed families")
    status = "READY" if not reasons else "NOT_READY"
    return {
        "schema": "same_scumm_v5_whole_game_readiness_v1",
        "status": status,
        "front_end": {
            "rooms_inventoried": census.get("rooms_inventoried", 0),
            "rooms_parsed": census.get("rooms_parsed", 0),
            "rooms_unsupported": list(census.get("rooms_unsupported", [])),
            "executables": dict(executable_counts),
            "structurally_decoded_occurrences": opcode_coverage["counts"].get(
                "structurally_decoded_occurrences", 0),
            "structurally_unknown_occurrences": opcode_coverage["counts"].get(
                "structurally_unknown_occurrences", 0),
            "truncated_occurrences": opcode_coverage["counts"].get(
                "truncated_occurrences", 0),
        },
        "semantics": {
            "observed_families": opcode_coverage["counts"].get(
                "semantic_families_observed", 0),
            "families_with_semantic_gaps": frontier["family_count"],
            "unsupported_occurrences": unsupported_semantics,
            "unknown_occurrences": semantic_unknown,
            "support_dimensions": dimensions,
        },
        "reachable_frontier": {
            "priority_families": [
                {"rank": row["priority_rank"], "family": row["family"],
                 "priority_class": row["priority_class"],
                 "semantic_unsupported_occurrences": row[
                     "semantic_unsupported_occurrences"],
                 "root_nearest_path": (row["root_nearest_paths"][0]
                                       if row["root_nearest_paths"] else None)}
                for row in frontier["families"][:20]
            ],
            "support_frontier": [
                {"rank": row["priority_rank"], "family": row["family"],
                 "priority_class": row["priority_class"],
                 "gap_dimensions": row["gap_dimensions"],
                 "representative": row["representative_sources"][0]
                 if row["representative_sources"] else None}
                for row in frontier["support_frontier"][:20]
            ],
            "definite_families": [row["family"] for row in frontier["families"]
                                  if row["priority_class"] == "DEFINITE_SEMANTIC_GAP"],
            "conditional_families": [row["family"] for row in frontier["families"]
                                     if row["priority_class"] == "CONDITIONAL_SEMANTIC_GAP"],
            "possible_families": [row["family"] for row in frontier["families"]
                                  if row["priority_class"] == "POSSIBLE_DYNAMIC_SEMANTIC_GAP"],
        },
        "reasons": reasons,
        "support_invariant": "decoder support is not backend/runtime certification; UNKNOWN remains a release blocker",
    }
