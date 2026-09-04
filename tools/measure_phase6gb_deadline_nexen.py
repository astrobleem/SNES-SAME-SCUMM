#!/usr/bin/env python3
"""Measure the Phase 6G-B S5-to-NMI deadline without debugger writes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
OVERLAY_WORK = 0x41F614
FRAME_COUNTER = 0x7E2210
CURRENT_GENERATION = OVERLAY_WORK + 0x02
TRACE = {
    "S5": OVERLAY_WORK + 0xBC,
    "S6_entry": OVERLAY_WORK + 0xC8,
    "S6_exit": OVERLAY_WORK + 0xCA,
    "S7_entry": OVERLAY_WORK + 0xCC,
    "S7_exit": OVERLAY_WORK + 0xCE,
    "S8_entry": OVERLAY_WORK + 0xD0,
    "S8_exit": OVERLAY_WORK + 0xD2,
    "S9_entry": OVERLAY_WORK + 0xD4,
    "S9_exit": OVERLAY_WORK + 0xD6,
    "NMI_entry": OVERLAY_WORK + 0xD8,
    "NMI_exit": OVERLAY_WORK + 0xDA,
}


def sample(session, label: str) -> dict[str, object]:
    cpu = session.get_cpu_state("Snes")
    ppu = session.get_ppu_state()
    return {
        "label": label,
        "cycle_count": cpu["cycleCount"],
        "pc": cpu["pc"], "k": cpu["k"], "sp": cpu["sp"],
        "ps": cpu["ps"], "dbr": cpu["dbr"],
        "scanline": ppu["scanline"], "emulator_ppu_frame": ppu["frameCount"],
        "same_frame_counter": session.read_u16(FRAME_COUNTER),
        "overlay_generation": session.read_u16(CURRENT_GENERATION),
    }


def wait_hit(session, handle: int, max_frames: int, label: str) -> dict[str, object]:
    result = session.run_until(max_frames=max_frames, hook_handle=handle)
    if result.get("reason") != "hookFired":
        raise RuntimeError(f"{label} hook did not fire: {result}")
    row = sample(session, label)
    row["run_until"] = result
    row["notifications"] = session.drain_notifications(timeout=0.05)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=NEXEN)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=44260)
    args = parser.parse_args()
    if not args.rom.is_file() or not args.nexen.is_file() or not os.access(args.nexen, os.X_OK):
        raise SystemExit("ROM or Nexen unavailable")
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output / "s5.mss"
    with mcp_session.McpSession(
        rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=ROOT, port=args.port,
        boot_wait=2.0, socket_timeout=90.0, stderr_log=args.output / "nexen-stderr.log",
    ) as session:
        session.pause(); session.tool("reset_emulator", {"power": True}); session.pause()
        hooks = {name: session.add_write_hook(address) for name, address in TRACE.items()}
        nmi_hook = session.add_write_hook(FRAME_COUNTER)
        # S5 also fires for earlier actor-1 overlays; retain the actor-2 generation 3 hit.
        while True:
            s5 = wait_hit(session, hooks["S5"], 1100, "S5")
            if s5["overlay_generation"] == 3:
                break
            # Advance beyond an earlier overlay acceptance.  run_until leaves
            # the CPU stopped on the hooked store, so calling it again without
            # advancing would observe that same write indefinitely.
            session.run_frames(1)
        session.save_state(checkpoint)
        nmi_after_s5 = wait_hit(session, nmi_hook, 2, "NMI_after_S5")
        available_cycles = nmi_after_s5["cycle_count"] - s5["cycle_count"]

        session.load_state(checkpoint)
        sequence = [s5]
        for name in ("S6_entry", "S7_entry"):
            sequence.append(wait_hit(session, hooks[name], 2, name))
        sequence.append(wait_hit(session, nmi_hook, 2, "NMI_299_entry"))
        for name in ("S7_exit", "S6_exit", "S8_entry", "S8_exit", "S9_entry", "S9_exit"):
            sequence.append(wait_hit(session, hooks[name], 2, name))
        sequence.append(wait_hit(session, nmi_hook, 2, "NMI_300_entry"))
        by_name = {row["label"]: row for row in sequence}
        notifications = [note for row in sequence + [nmi_after_s5]
                         for note in row.get("notifications", [])]
        raw_events = [note["params"] for note in notifications
                      if note.get("method") == "notifications/mesen/hookFired"]
        s5_cycle = min(event["cycleCount"] for event in raw_events
                       if event.get("handle") == hooks["S5"] and event["cycleCount"] >= 44_000_000)
        def first(handle: int) -> dict[str, object]:
            return min((event for event in raw_events
                        if event.get("handle") == handle and event["cycleCount"] >= s5_cycle),
                       key=lambda event: event["cycleCount"])
        exact = {name: first(handle) for name, handle in hooks.items()}
        nmi_entries = sorted((event for event in raw_events
                              if event.get("handle") == hooks["NMI_entry"]
                              and event["cycleCount"] >= s5_cycle), key=lambda event: event["cycleCount"])
        nmi_exits = sorted((event for event in raw_events
                            if event.get("handle") == hooks["NMI_exit"]
                            and event["cycleCount"] >= s5_cycle), key=lambda event: event["cycleCount"])
        exact["NMI_299_entry"] = nmi_entries[0]
        exact["NMI_299_counter_write"] = first(nmi_hook)
        exact["NMI_299_exit"] = nmi_exits[0]
        exact["NMI_300_entry"] = nmi_entries[1]
        nmi_cost = exact["NMI_299_exit"]["cycleCount"] - exact["NMI_299_entry"]["cycleCount"]
        cell_elapsed = exact["S7_exit"]["cycleCount"] - exact["S7_entry"]["cycleCount"]
        costs = {
            "available_s5_to_nmi_299_cpu_cycles": exact["NMI_299_entry"]["cycleCount"] - exact["S5"]["cycleCount"],
            "nmi_299_cpu_cycles": nmi_cost,
            "cell_enumeration_and_4bpp_cpu_cycles": cell_elapsed - nmi_cost,
            "tilemap_cpu_cycles": exact["S8_exit"]["cycleCount"] - exact["S8_entry"]["cycleCount"],
            "descriptor_enqueue_cpu_cycles": exact["S9_exit"]["cycleCount"] - exact["S9_entry"]["cycleCount"],
            "total_s6_s9_cpu_cycles_excluding_nmi": exact["S9_exit"]["cycleCount"] - exact["S6_entry"]["cycleCount"] - nmi_cost,
        }
        evidence = {
            "format": "same-phase6gb-deadline-evidence",
            "rom": str(args.rom), "sequence": sequence, "deadline": nmi_after_s5,
            "exact_hook_events": exact,
            "costs": costs,
            "note": "cycleCount is the emulator S-CPU cycle counter; this API exposes scanline but not dot/master-cycle state.",
        }
        (args.output / "deadline.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(costs, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
