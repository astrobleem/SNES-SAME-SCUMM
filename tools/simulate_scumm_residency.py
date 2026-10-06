#!/usr/bin/env python3
"""Run the pure selector-residency simulator over compiler analysis output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from same.engines.scumm_v5.residency_contract import (
    DEFAULT_SELECTOR_POOL,
    ResolverDirectory,
    simulate_analysis_directory,
)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=True) + "\n").encode("ascii")


def _summary(report: dict[str, Any]) -> str:
    capacity = report["capacity"]
    largest = report["largest_room"]
    dynamic = report["dynamic_candidate_scenario"]
    return "\n".join((
        "# SCUMM resident-binding simulation", "",
        f"Selector capacity: {report['selector_capacity']}",
        f"Room bundles / global SelectorUnits: {report['room_bundle_count']} / "
        f"{report['global_selector_unit_count']}",
        f"Largest room: {largest['room']} ({largest['selector_units']} SelectorUnits)",
        f"Largest-room yielded/dynamic scenario peak: "
        f"{largest['modeled_peak_with_live_globals_and_dynamic_lookup']}",
        f"Largest simulated resident set: "
        f"{capacity['largest_simulated_resident_set']['value']}",
        f"Conservative modeled upper bound: "
        f"{capacity['conservative_modeled_upper_bound']['value']}",
        f"Capacity sufficient for modeled bound: "
        f"{capacity['selector_capacity_sufficient_for_modeled_bound']}",
        f"Compiler-discovered room transitions simulated: "
        f"{report['room_transition_scenarios']['compiler_discovered_static_or_conditional_load_edges']}",
        f"Dynamic candidate scenario room / candidates / peak: "
        f"{dynamic['room']} / {dynamic['candidate_universe_count']} / "
        f"{dynamic['peak_resident_bindings']}",
        "Exact simultaneous runtime liveness: UNKNOWN", "",
    ))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, required=True,
                        help="directory produced by compile_scumm_game.py --analyze")
    parser.add_argument("--output", type=Path, required=True,
                        help="output directory for deterministic simulation reports")
    args = parser.parse_args()

    directory_document = _read(args.analysis_dir / "selector_directory.json")
    selector_demand = _read(args.analysis_dir / "selector_demand.json")
    dependency_graph = _read(args.analysis_dir / "dependency_graph.json")
    directory = ResolverDirectory.from_selector_directory(directory_document)
    first = simulate_analysis_directory(
        directory, selector_demand, dependency_graph,
        selector_pool=DEFAULT_SELECTOR_POOL)
    second = simulate_analysis_directory(
        directory, selector_demand, dependency_graph,
        selector_pool=DEFAULT_SELECTOR_POOL)
    first_bytes, second_bytes = _canonical_bytes(first), _canonical_bytes(second)
    differences = [] if first_bytes == second_bytes else ["simulation report bytes"]
    report = dict(first)
    report["determinism"] = {
        "runs": 2,
        "binding_trace_equal": first["largest_room"]["trace"] ==
                               second["largest_room"]["trace"],
        "peak_counts_equal": first["capacity"] == second["capacity"],
        "snapshot_restore_semantics_equal": first["portable_snapshot_restore"] ==
                                           second["portable_snapshot_restore"],
        "reports_equal": not differences,
        "differences": differences,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "simulation.json").write_bytes(_canonical_bytes(report))
    (args.output / "representative_trace.json").write_bytes(
        _canonical_bytes(report["largest_room"]["trace"]))
    (args.output / "summary.md").write_text(_summary(report), encoding="utf-8")
    print(f"Selector capacity: {report['selector_capacity']}")
    print("Largest room / room scenario peak / overall scenario peak / bound: "
          f"{report['largest_room']['room']} / "
          f"{report['largest_room']['modeled_peak_with_live_globals_and_dynamic_lookup']} / "
          f"{report['capacity']['largest_simulated_resident_set']['value']} / "
          f"{report['capacity']['conservative_modeled_upper_bound']['value']}")
    print("Dynamic candidate universe / requested-at-once: "
          f"{report['dynamic_candidate_scenario']['candidate_universe_count']} / "
          f"{report['dynamic_candidate_scenario']['max_additional_global_bindings_at_once']}")
    print(f"Deterministic reports: {report['determinism']['reports_equal']}")
    print(f"Output: {args.output}")
    return 0 if not differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
