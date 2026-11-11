#!/usr/bin/env python3
"""Fail-closed WRAM ownership audit for resolver-enabled SCUMM builds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from same.snes_carrier import _validate_layout
from same.snes_video_backend import validate_mode3_layout

MEMORY = ROOT / "runtime/snes/kernel/memory.pasm"

# Intervals are half-open. Their endpoints are ownership boundaries declared
# in memory.pasm; unrelated ownership overlap fails closed.
REGIONS = (
    ("actor_records_and_name_lengths", "SAME_SCUMM_C14_ACTORS", "SAME_SCUMM_C14_NAME_SIZES_END"),
    ("actor_hit_test_scratch", "SAME_SCUMM_C29_SCRATCH_BASE", "SAME_SCUMM_C29_SCRATCH_END"),
    ("actor_names_and_operands", "SAME_SCUMM_C14_NAMES", "SAME_SCUMM_C14_STATE_END"),
    ("camera_follow_intent", "SAME_SCUMM_C15_CAMERA_FOLLOWS", "SAME_SCUMM_C15_STATE_END"),
    ("playable_controller_ui", "SAME_SCUMM_PLAY_UI_BASE", "SAME_SCUMM_PLAY_UI_END"),
    ("camera_transaction", "SAME_SCUMM_VIEWPORT_STATE_BASE",
     "SAME_SCUMM_VIEWPORT_STATE_END"),
    ("retained_text_and_pending_snapshot", "SAME_SCUMM_TEXT_STORAGE_START",
     "SAME_SCUMM_TEXT_STORAGE_END"),
    ("mode3_backend_scratch", "SAME_MODE3_WORK_OWNER_START",
     "SAME_MODE3_WORK_OWNER_END"),
    ("program_cache_page2", "SAME_SCUMM_MSU_PROGRAM_CACHE2_OWNER_START",
     "SAME_SCUMM_MSU_PROGRAM_CACHE2_OWNER_END"),
    ("actor_explicit_animation", "SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION",
     "SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION_END"),
    ("actor_pose_state", "SAME_SCUMM_ACTOR_POSE_STATE_BASE",
     "SAME_SCUMM_ACTOR_POSE_STATE_END"),
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
    aliases: dict[str, str] = {}
    for line in MEMORY.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*\$([0-9A-Fa-f]+)(?:\s|$)", line)
        if match:
            result[match.group(1)] = int(match.group(2), 16)
        else:
            alias = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*([A-Z][A-Z0-9_]*)(?:\s*(?:;.*)?)$", line)
            if alias:
                aliases[alias.group(1)] = alias.group(2)
    for _ in range(len(aliases)):
        added = {name: result[target] for name, target in aliases.items()
                 if name not in result and target in result}
        if not added:
            break
        result.update(added)
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
    controller_region = next(item for item in intervals
                             if item["owner"] == "controller_and_interaction")
    underlay_scratch_start = values["SAME_VIDEO_ACTOR_UNDERLAY_SCRATCH_BASE"]
    underlay_scratch_end = values["SAME_VIDEO_ACTOR_UNDERLAY_SCRATCH_END"]
    restore_aliases = ("CALL_X", "LOOP_ROW", "LOOP_COL", "LOOP_W",
                       "LOOP_H", "LOOP_DST", "LOOP_SRC")
    underlay_fields = ("RECORD_LENGTH", "DATA_BASE", "AREA", "ROW",
                       "COLUMN", "SURFACE_CURSOR", "RECORD_CURSOR")
    expected = [underlay_scratch_start + 2 * i for i in range(7)]
    if (underlay_scratch_end - underlay_scratch_start != 14
            or underlay_scratch_start < int(controller_region["start"][1:], 16)
            or underlay_scratch_end > values["SAME_SCUMM_CONTROLLER_ROOM_READY"]
            or [values["SAME_SCUMM_CONTROLLER_RESTORE_" + name]
                for name in restore_aliases] != expected
            or [values["SAME_VIDEO_ACTOR_UNDERLAY_" + name]
                for name in underlay_fields] != expected):
        raise ValueError("actor-underlay scratch must alias only nonconcurrent restore witnesses, never room readiness")
    if not (values["SAME_SCUMM_VIEWPORT_STATE_BASE"] == values["SAME_SCUMM_RESIDENT_WRAM_END"]
            and values["SAME_SCUMM_VIEWPORT_STATE_END"] == 0x7E8FE8
            and values["SAME_SCUMM_VIEWPORT_STATE"] == values["SAME_SCUMM_VIEWPORT_STATE_BASE"]
            and values["SAME_SCUMM_VIEWPORT_STATE_END"] <= values["SAME_SCUMM_OBJECT_NAMES"]
            and values["SAME_SCUMM_VIEWPORT_MODE"] + 1 == values["SAME_SCUMM_VIEWPORT_STATE_END"]):
        raise ValueError("camera transaction must retain its separate 40-byte resolver/name padding allocation")
    if (values["SAME_SCUMM_TEXT_STORAGE_START"] < values["SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK"] + values["SAME_SCUMM_PUT_ACTOR_BOX_STRIDE"]
            or values["SAME_SCUMM_TEXT_STORAGE_END"] > values["SAME_SCUMM_PUT_ACTOR_WALKBOX"]):
        raise ValueError("retained text overlaps active geometry or actor walkbox state")
    bwram = json.loads((ROOT / "runtime/snes/carriers/sa1_bwram_layout.json").read_text())
    # Share the carrier's exact nested ownership contract; do not audit only
    # the old 2-KiB parent reservation and overlook its palette residents.
    _validate_layout(bwram)
    low = bwram["protected_low"]
    low_start = parse_address(low["address"])
    save = bwram["save_reserved"]
    save_start = parse_address(save["address"])
    save_end = save_start + save["bytes"]
    palette_owners = []
    for name, item in low["allocations"].items():
        start = low_start + item["offset"]
        end = start + item["bytes"]
        if start < save_end and save_start < end:
            raise ValueError(f"protected-low palette owner overlaps save storage: {name}")
        palette_owners.append({"name": name, "owner": item["owner"],
                               "start": f"${start:06X}", "end_exclusive": f"${end:06X}",
                               "bytes": item["bytes"], "disjoint_from_save": True})
    ordered_palette = sorted(palette_owners, key=lambda item: item["start"])
    for left, right in zip(ordered_palette, ordered_palette[1:]):
        if left["end_exclusive"] > right["start"]:
            raise ValueError("protected-low palette owners overlap")
    video = json.loads((ROOT / "runtime/snes/video_backends/mode3_surface_layout.json").read_text())
    fixture_address = parse_address(str(video["fixture"]["address"]))
    page2 = next(item for item in intervals if item["owner"] == "program_cache_page2")
    if (page2["start"], page2["end_exclusive"], page2["bytes"]) != (
            "$7F1000", "$7F1800", 0x800):
        raise ValueError("third ProgramUnit page must occupy the audited bank-$7F gap")
    pose_state = next(item for item in intervals if item["owner"] == "actor_pose_state")
    if (pose_state["start"], pose_state["end_exclusive"], pose_state["bytes"]) != (
            "$41E780", "$41E800", 0x80):
        raise ValueError("actor pose state differs from its Mode-3 work suballocation")
    if "SAME_SCUMM_ACTOR_POSE_BUFFER              = SAME_SCUMM_LIVE_ROOM_PENDING_BASE" not in MEMORY.read_text(encoding="utf-8"):
        raise ValueError("actor pose buffer must use the exclusively owned room-pending scratch")
    if "SAME_SCUMM_ACTOR_POSE_BUFFER_SIZE         = $0800" not in MEMORY.read_text(encoding="utf-8"):
        raise ValueError("actor pose chunk must remain bounded to one checked 2-KiB transfer")
    work = video["work"]
    work_start = parse_address(str(work["address"]))
    allocation = work.get("allocations", {}).get("actor_pose_state", {})
    if (allocation.get("offset"), allocation.get("bytes"),
            pose_state["bytes"]) != (0x30, 0x80, 0x80):
        raise ValueError("actor pose state suballocation differs from the Mode-3 work owner")
    if work_start + allocation["offset"] != int(pose_state["start"][1:], 16):
        raise ValueError("actor pose state address is outside its declared Mode-3 work owner")
    if allocation["offset"] + allocation["bytes"] > work["bytes"]:
        raise ValueError("actor pose state exceeds the Mode-3 work owner")
    backend = work.get("allocations", {}).get("backend_scratch", {})
    if backend != {"offset": 0, "bytes": 0x24, "owner": "Mode-3 backend scratch"}:
        raise ValueError("Mode-3 backend scratch must own work offsets $00..$23")
    if (values["SAME_MODE3_WORK_OWNER_START"] != work_start
            or values["SAME_MODE3_WORK_OWNER_END"] != work_start + 0x24):
        raise ValueError("Mode-3 backend scratch boundaries differ from generated work")
    generator = (ROOT / "tools/generate_snes_video_backend.py").read_text()
    offsets = [int(value, 16) for value in re.findall(
        r"SAME_MODE3_WORK_[A-Z0-9_]+ = SAME_MODE3_WORK\+\$([0-9A-Fa-f]+)", generator)]
    # All generated fields fit within a word; conservatively reserve two
    # bytes even for byte fields. TIMEOUT at $22 consumes the last word.
    if not offsets or max(offsets) + 2 != backend["bytes"]:
        raise ValueError("generated Mode-3 work fields exceed/differ from audited scratch")
    explicit_animation = work.get("allocations", {}).get("actor_explicit_animation", {})
    if (explicit_animation.get("offset"), explicit_animation.get("bytes"),
            explicit_animation.get("owner")) != (
                36, 4, "generic SCUMM actor animation state"):
        raise ValueError("explicit animation state differs from the Mode-3 work owner")
    if work_start + explicit_animation["offset"] != values["SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION"]:
        raise ValueError("explicit animation state address differs from its memory contract")
    if (values["SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION_END"]
            - values["SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION"] != 4):
        raise ValueError("explicit animation state must be a four-byte bitset")
    if explicit_animation["offset"] < backend["offset"] + backend["bytes"]:
        raise ValueError("explicit animation state overlaps backend scratch")
    if explicit_animation["offset"] + explicit_animation["bytes"] > allocation["offset"]:
        raise ValueError("explicit animation state overlaps actor pose state")
    if fixture_address < 0x41E800 or fixture_address >= 0x41F000:
        raise ValueError("Mode-3 fixture alias bounds changed")
    live_room_source = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
    live_constants = (ROOT / "tools/generate_snes_carrier.py").read_text()
    video_surface_source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
    if values.get("SAME_VIDEO_ACTOR_UNDERLAY_SCRATCH_SIZE") != 0x0E:
        raise ValueError("actor-underlay copy cursor must remain a bounded 14-byte scratch owner")
    if values.get("SAME_VIDEO_ACTOR_UNDERLAY_SCRATCH_END") != values["SAME_SCUMM_CONTROLLER_ROOM_READY"]:
        raise ValueError("actor-underlay scratch must end before persistent room readiness")
    if "SAME_VIDEO_DIAG_BASE                  = $7E5E90" not in video_surface_source:
        raise ValueError("actor-underlay scratch no longer meets the declared video diagnostic boundary")
    cursor_source = (ROOT / "runtime/snes/services/cursor_underlay.inc.pasm").read_text()
    for api in ("CaptureCursorUnderlay", "RestoreCursorUnderlay", "MergeCursorDamage",
                "InvalidateCursorUnderlay"):
        if f"Same_VideoSurface_{api}_Far:" not in cursor_source:
            raise ValueError(f"cursor underlay API missing: {api}")
    if ('SAME_VIDEO_CURSOR_HEADER_SIZE = $0020' not in cursor_source
            or 'SAME_VIDEO_CURSOR_PAYLOAD_SIZE = $0100' not in cursor_source
            or '.include "cursor_underlay.inc.pasm"' not in video_surface_source):
        raise ValueError("cursor underlay header/payload/include differs from ownership")
    if any(symbol in cursor_source for symbol in ("SAME_SCUMM_CURSOR_PRESENTATION",
                                                 "SAME_SCUMM_ACTOR_POSE_")):
        raise ValueError("cursor service must not borrow engine/actor memory")
    sparse_apis = ("RestoreActorUnderlay", "BeginActorUnderlay", "CaptureActorRun",
                   "CommitActorUnderlay", "InvalidateActorUnderlay")
    for api in sparse_apis:
        if f"Same_VideoSurface_{api}_Far:" not in video_surface_source:
            raise ValueError(f"sparse actor underlay API missing: {api}")
    if "Same_VideoSurface_CaptureActorUnderlay_Far:" in video_surface_source:
        raise ValueError("obsolete rectangle underlay must not coexist with sparse journal")
    if ("SAME_VIDEO_ACTOR_UNDERLAY_MAGIC       = $A8" not in video_surface_source
            or "SAME_VIDEO_ACTOR_UNDERLAY_HEADER_SIZE = $0010" not in video_surface_source):
        raise ValueError("sparse actor journal version/header differs from the RAM contract")
    restore = video_surface_source.split("Same_VideoSurface_RestoreActorUnderlay_Far:", 1)[1].split(
        "Same_VideoSurface_BeginActorUnderlay_Far:", 1)[0]
    if ("jsr Same_VideoSurface_Underlay_Validate" not in restore
            or "jsl Same_VideoSurface_WriteIndexedPixel_Far" not in restore
            or restore.index("jsr Same_VideoSurface_Underlay_Validate")
            > restore.index("jsl Same_VideoSurface_WriteIndexedPixel_Far")):
        raise ValueError("sparse underlay must validate the entire journal before pixel writes")
    consumed = restore.split("Same_VideoSurface_Underlay_Restore__record:", 1)[1].split(
        "Same_VideoSurface_Underlay_Restore__run:", 1)[0]
    if "jsr Same_VideoSurface_Underlay_ClearMagic" not in consumed:
        raise ValueError("successful sparse restore must consume the journal marker")
    if "SAME_VIDEO_SURFACE_STATE              = SAME_BWRAM_VIDEO_SURFACE_STATE" not in video_surface_source:
        raise ValueError("video surface state must use its generated BWRAM allocation")
    if "SAME_BWRAM_VIDEO_SURFACE_STATE" not in live_constants:
        raise ValueError("carrier generator omits the video surface state allocation")
    tile_shadow = bwram["tile_shadow"]
    pixel_stage_address = parse_address(str(tile_shadow["address"]))
    if "SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE = SAME_BWRAM_TILE_SHADOW_BASE" not in live_constants:
        raise ValueError("live SC5VIS staging must declare its tile-shadow alias")
    surface_source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
    mode3_source = (ROOT / "runtime/snes/services/video_mode3.pasm").read_text()
    if "Same_VideoSurface_InvalidateTileCache_Far" not in live_room_source:
        raise ValueError("live SC5VIS publication must invalidate the aliased tile shadow")
    if "sta.l SAME_BWRAM_CONTROL_TILE_VALID" not in surface_source:
        raise ValueError("surface-owned tile-cache invalidation API is missing")
    present_accept = mode3_source.split(
        "Same_Mode3_HandlePresent__accept:", 1,
    )[1].split("Same_Mode3_HandlePresent__reject:", 1)[0]
    if "sta.l SAME_BWRAM_CONTROL_TILE_VALID" in present_accept:
        raise ValueError("ordinary PRESENT must not invalidate cached tiles")
    validate_mode3_layout(video)
    retained_source = (ROOT / "runtime/snes/services/video_mode3_retained.inc.pasm").read_text()
    camera_source = (ROOT / "runtime/snes/engines/scumm_v5_camera_stream.inc.pasm").read_text()
    if "MODE3_R_HDMA = SAME_MODE3_SCROLL_HDMA" not in retained_source:
        raise ValueError("retained HDMA must survive room-staging aliases")
    if (parse_address(video['scroll_hdma']['address']), video['scroll_hdma']['bytes']) != (0x41e73a,10):
        raise ValueError("retained NMI scroll table ownership changed")
    for contract in ('Same_VideoSurface_RetireScroll_Far', 'Same_VideoSurface_ColdScroll_Far'):
        if f'jsl {contract}' not in live_room_source:
            raise ValueError('incoming room omits retained cache lifetime handoff')
    if 'cmp #$0801' not in camera_source or 'jsl Same_VideoSurface_AbortScroll_Far' not in camera_source:
        raise ValueError('same-room checked strip must respect retained guard tail')
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
                             "three-page streamed-program cache", "Mode-3 live staging",
                             "exclusive actor/room SC5ACT pending scratch"],
        "bwram_protected_low_owners": palette_owners,
        "bwram_save_reserved": {"start": f"${save_start:06X}",
                                "end_exclusive": f"${save_end:06X}",
                                "bytes": save["bytes"]},
        "bwram_aliases": [{
            "owner": "live SC5LIVE actor underlay snapshot",
            "address_rule": "$41E800 + validated active SC5LIVE total_size",
            "maximum_bytes": int(active["bytes"]),
            "aliases": "unused tail of the same active metadata allocation",
            "lifetime": "displayed actor pose until the next redraw or checked room-surface publication",
            "capacity_rule": "used = 16 + sum(4 + run_count); bounded by active allocation tail; runs stay within one 256-pixel row",
            "coherency": "capture all runs before drawing; A9 remains unpublished until Commit writes A8 last; Restore validates all records before writes and consumes magic; room publication invalidates",
        }],
        "wram_lifetime_aliases": [{
            "owner": "actor-underlay cursor during live SC5LIVE actor composition",
            "address": f"${underlay_scratch_start:06X}",
            "bytes": underlay_scratch_end - underlay_scratch_start,
            "aliases": "RestoreRect debug-only call/loop witnesses; excludes persistent room readiness",
            "lifetime": "RestoreRect bypasses its ROM row loop for live rooms; cursor use occurs only inside the underlay helpers",
            "coherency": "no simultaneous reader; persistent underlay pixels reside in the validated active-room tail",
        }],
        "wram_cache_page2": {
            "address": page2["start"], "bytes": page2["bytes"],
            "exclusive_with": [],
        },
        "retained_video_ownership": {
            "guard_head": bwram['backend_reserved']['allocations']['retained_guard_head'],
            "guard_tail": bwram['retained_guard_tail_alias'],
            "camera_transaction": bwram['backend_reserved']['allocations']['retained_viewport'],
            "persistent_hdma": video['scroll_hdma'],
            "vram": video['retained_viewport'],
            "staging_prefix_limit": 2048,
            "retirement": "idle surface and empty event/DMA queues before incoming room; HDMA table remains outside retired aliases",
        },
        "bwram_lifetime_aliases": [{
            "owner": "SCUMM checked SC5VIS pixel staging",
            "address": f"${pixel_stage_address:06X}",
            "bytes": tile_shadow["bytes"],
            "aliases": "Mode-3 encoded tile shadow",
            "lifetime": "cold incoming room only; same-room retained columns do not use tile-shadow staging",
            "coherency": "full room present invalidates shadow before re-encoding",
        }, {
            "owner": "SCUMM actor chunk / live-room transaction",
            "address": f"${parse_address(str(bwram['backend_reserved']['address'])) + int(bwram['backend_reserved']['allocations']['live_room_pending']['offset']):06X}",
            "bytes": int(bwram["backend_reserved"]["allocations"]["live_room_pending"]["bytes"]),
            "aliases": "exclusive owner field NONE/ACTOR/ROOM",
            "lifetime": "checked actor chunk until synchronous composition; complete room transaction otherwise",
            "coherency": "room request preempts actor; provider is drained before reuse",
        }],
        "live_room_metadata_alias": {
            "address": f"${active_start:06X}", "bytes": int(active["bytes"]),
            "exclusive_with": ["Mode-3 fixture workspace", "Mode-3 reserved alias"],
            "active_video_staging_overlaps": False,
            "actor_underlay_uses_only_unreferenced_tail": True,
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
