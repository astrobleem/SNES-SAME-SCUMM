#!/usr/bin/env python3
"""Fail-closed WRAM ownership audit for resolver-enabled SCUMM builds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "runtime/snes/kernel/memory.pasm"

# Intervals are half-open. Their endpoints are ownership boundaries declared
# in memory.pasm; unrelated ownership overlap fails closed.
REGIONS = (
    ("program_cache_page2", "SAME_SCUMM_MSU_PROGRAM_CACHE2_OWNER_START",
     "SAME_SCUMM_MSU_PROGRAM_CACHE2_OWNER_END"),
    ("generated_variables_and_stack_guard", "SAME_SCUMM_VARIABLES_RESERVED_START",
     "SAME_SCUMM_VARIABLES_RESERVED_END"),
    ("program_cache", "SAME_SCUMM_MSU_PROGRAM_CACHE_BASE",
     "SAME_SCUMM_MSU_PROGRAM_CACHE_END"),
    ("event_queue", "SAME_EVENT_HEAD", "SAME_INPUT_HELD"),
    ("program_cache_page_lookup", "SAME_SCUMM_MSU_PAGE_REQUEST_PC",
     "SAME_SCUMM_MSU_PAGE_LOOKUP_END"),
    ("program_cache_waiters", "SAME_SCUMM_MSU_CACHE_WAITER_SELECTOR0",
     "SAME_SCUMM_MSU_CACHE_WAITER_END"),
    ("program_cache_metadata", "SAME_SCUMM_MSU_CACHE_STATE0",
     "SAME_SCUMM_MSU_ROOM_STATE_END"),
    ("input_edges", "SAME_INPUT_HELD", "SAME_FRAME_COUNTER"),
    ("kernel_frame_tad", "SAME_FRAME_COUNTER", "SAME_TAD_STATE_END"),
    ("c4_scheduler", "SAME_SCUMM_C4_SLOT_STATUS", "SAME_SCUMM_C4_STATE_END"),
    ("owner_scratch", "SAME_SCUMM_OWNER_INDEX", "SAME_SCUMM_OWNER_INDEX_END"),
    ("streamed_scheduler_fairness", "SAME_SCUMM_C4_SCHED_CURSOR",
     "SAME_SCUMM_C4_SCHED_FAIR_END"),
    ("controller_and_interaction", "SAME_SCUMM_CONTROLLER_RENDER_X",
     "SAME_SCUMM_OBJECT_COUNT"),
    ("c19", "SAME_SCUMM_C19_STACK_POINTER", "SAME_SCUMM_C19_STATE_END"),
    ("save_validator_status", "SAME_SAVE_STATUS", "SAME_SCUMM_MUSIC_ROUTE_KIND"),
    ("room_lifecycle", "SAME_SCUMM_M23A_ACTIVE_RECORD", "SAME_SCUMM_M23A_STATE_END"),
    ("save_staging_max", "SAME_SAVE_STAGING", "SAME_SAVE_STAGING_MAX_END"),
    ("m23b_continuations", "SAME_SCUMM_M23B_STATE", "SAME_SCUMM_M23A_RETURN_VALID"),
    ("m23b_nested_child_slots", "SAME_SCUMM_M23B_NEST_CHILD_SLOTS",
     "SAME_SCUMM_M23B_NEST_CHILD_SLOTS_END"),
    ("room_return_continuation", "SAME_SCUMM_M23A_RETURN_VALID",
     "SAME_SCUMM_M23A_REQUEST_API_ACTIVE_END"),
    ("object_name_lengths", "SAME_SCUMM_OBJECT_NAME_LENGTH",
     "SAME_SCUMM_RESIDENT_WRAM_BASE"),
    ("resident_resolver", "SAME_SCUMM_RESIDENT_WRAM_BASE",
     "SAME_SCUMM_RESIDENT_WRAM_END"),
    ("encoded_object_names", "SAME_SCUMM_OBJECT_NAMES",
     "SAME_SCUMM_OBJECT_NAMES_END"),
)


def symbols() -> dict[str, int]:
    result: dict[str, int] = {}
    for line in MEMORY.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*\$([0-9A-Fa-f]+)(?:\s|$)", line)
        if match:
            result[match.group(1)] = int(match.group(2), 16)
    return result


def parse_address(value: str) -> int:
    bank, offset = value.split(":", 1)
    return (int(bank, 16) << 16) | int(offset, 16)


def audit() -> dict[str, Any]:
    values = symbols()
    intervals: list[dict[str, Any]] = []
    for owner, first, after in REGIONS:
        if first not in values or after not in values:
            raise ValueError(f"WRAM ownership boundary is missing: {first} / {after}")
        start, end = values[first], values[after]
        if start >= end:
            raise ValueError(f"invalid WRAM interval for {owner}: ${start:06X}-${end:06X}")
        intervals.append({
            "owner": owner, "start": f"${start:06X}", "end_exclusive": f"${end:06X}",
            "bytes": end - start, "start_symbol": first, "end_symbol": after,
        })
    ordered = sorted(intervals, key=lambda item: int(item["start"][1:], 16))
    overlaps = []
    for left, right in zip(ordered, ordered[1:]):
        if int(left["end_exclusive"][1:], 16) > int(right["start"][1:], 16):
            overlaps.append({"left": left["owner"], "right": right["owner"]})
    if overlaps:
        raise ValueError(f"SCUMM WRAM ownership overlaps: {overlaps}")
    resolver = next(item for item in intervals if item["owner"] == "resident_resolver")
    if resolver["bytes"] != 960:
        raise ValueError(f"resident resolver WRAM span changed: {resolver['bytes']} bytes")
    cache = next(item for item in intervals if item["owner"] == "program_cache")
    if cache["bytes"] != 0x1000:
        raise ValueError(f"ProgramUnit base cache span changed: {cache['bytes']} bytes")
    bwram = json.loads((ROOT / "runtime/snes/carriers/sa1_bwram_layout.json").read_text())
    video = json.loads((ROOT / "runtime/snes/video_backends/mode3_surface_layout.json").read_text())
    fixture_address = parse_address(str(video["fixture"]["address"]))
    page2 = next(item for item in intervals if item["owner"] == "program_cache_page2")
    if (page2["start"], page2["end_exclusive"], page2["bytes"]) != (
            "$7F1000", "$7F1800", 0x800):
        raise ValueError("third ProgramUnit page must occupy the audited bank-$7F gap")
    if fixture_address < 0x41E800 or fixture_address >= 0x41F000:
        raise ValueError("Mode-3 fixture alias bounds changed")
    runtime_source = (ROOT / "runtime/snes/services/video_mode3.pasm").read_text()
    live_constants = (ROOT / "tools/generate_snes_carrier.py").read_text()
    video_surface_source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
    if "SAME_VIDEO_SURFACE_STATE              = SAME_BWRAM_VIDEO_SURFACE_STATE" not in video_surface_source:
        raise ValueError("video surface state must use its generated BWRAM allocation")
    if "SAME_BWRAM_VIDEO_SURFACE_STATE" not in live_constants:
        raise ValueError("carrier generator omits the video surface state allocation")
    tile_shadow = bwram["tile_shadow"]
    pixel_stage_address = parse_address(str(tile_shadow["address"]))
    if "SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE = SAME_BWRAM_TILE_SHADOW_BASE" not in live_constants:
        raise ValueError("live SC5VIS staging must declare its tile-shadow alias")
    if "SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES" not in runtime_source or (
        "sta.l SAME_BWRAM_CONTROL_TILE_VALID" not in runtime_source
    ):
        raise ValueError("live SC5VIS publication must invalidate the aliased tile shadow")
    active = bwram["live_room_active"]
    active_start = parse_address(str(active["address"]))
    active_end = active_start + int(active["bytes"])
    fixture_end = parse_address(str(video["fixture"]["address"])) + int(video["fixture"]["bytes"])
    reserved_start = parse_address(str(video["reserved"]["address"]))
    reserved_end = reserved_start + int(video["reserved"]["bytes"])
    if (active_start != fixture_address or active_end != reserved_end
            or fixture_end != reserved_start
            or int(active["bytes"]) != 6144
            or set(active.get("exclusive_with", ())) != {
                "runtime/snes/video_backends/mode3_surface_layout.json:fixture",
                "runtime/snes/video_backends/mode3_surface_layout.json:reserved",
            }):
        raise ValueError("live-room active metadata alias must exactly cover the audited fixture/reserved span")
    if "SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE" not in live_constants:
        raise ValueError("carrier constants omit the audited active-room metadata capacity")
    return {
        "format": "same-scumm-residency-wram-ownership-v1",
        "result": "pass",
        "interval_convention": "half-open",
        "features_coexist": ["resolver", "controller/input", "name cache",
                             "save validator", "C4", "C19", "room lifecycle",
                             "three-page streamed-program cache", "Mode-3 live staging"],
        "bwram_aliases": [],
        "wram_cache_page2": {
            "address": page2["start"], "bytes": page2["bytes"],
            "exclusive_with": [],
        },
        "bwram_lifetime_aliases": [{
            "owner": "SCUMM checked SC5VIS pixel staging",
            "address": f"${pixel_stage_address:06X}",
            "bytes": tile_shadow["bytes"],
            "aliases": "Mode-3 encoded tile shadow",
            "lifetime": "incoming visual transfer through checked publication",
            "coherency": "full room present invalidates shadow before re-encoding",
        }],
        "live_room_metadata_alias": {
            "address": f"${active_start:06X}", "bytes": int(active["bytes"]),
            "exclusive_with": ["Mode-3 fixture workspace", "Mode-3 reserved alias"],
            "active_video_staging_overlaps": False,
        },
        "regions": intervals,
        "overlaps": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"result": "pass", "regions": len(report["regions"]),
                      "output": str(args.output) if args.output else None}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
