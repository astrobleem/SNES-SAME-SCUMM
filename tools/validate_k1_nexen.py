#!/usr/bin/env python3
"""Execute SAME's K1 NMI/input/DMA ownership gate in a fresh Nexen process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build" / "same-engine-host.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
VRAM_EXPECTED = bytes.fromhex("112233445566778899aabbccddeef00f")
CGRAM_EXPECTED = bytes.fromhex("1f00e003007cff7f")
OAM_EXPECTED = bytes.fromhex("18f0253038f02630")
FORCED_EXPECTED = bytes.fromhex("deadbeef4b310001")


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def dma_snapshot(session: object) -> dict[str, int]:
    raw = session.read_memory("snesMemory", 0x7E223A, 0x10)
    return {
        "current_slot": u16(raw, 0x00),
        "pending": u16(raw, 0x02),
        "committed": u16(raw, 0x04),
        "deferred_blank": u16(raw, 0x06),
        "deferred_budget": u16(raw, 0x08),
        "rejected": u16(raw, 0x0A),
        "frame_bytes": u16(raw, 0x0C),
        "display_shadow": raw[0x0E],
    }


def input_snapshot(session: object) -> dict[str, int]:
    raw = session.read_memory("snesMemory", 0x7E2200, 0x12)
    return {
        "held": u16(raw, 0x00),
        "previous": u16(raw, 0x02),
        "pressed": u16(raw, 0x04),
        "released": u16(raw, 0x06),
        "frame_counter": u16(raw, 0x10),
    }


def source_ownership() -> dict[str, object]:
    pattern = re.compile(
        r"\b(?:MDMAEN|HDMAEN|DMAP[0-7]|BBAD[0-7]|A1T[0-7]L|A1B[0-7]|DAS[0-7]L)\b"
    )
    clients = []
    for relative in ("runtime/snes/engine", "runtime/snes/engines", "runtime/snes/targets"):
        for path in sorted((ROOT / relative).glob("*.pasm")):
            if pattern.search(path.read_text(encoding="utf-8")):
                clients.append(str(path.relative_to(ROOT)))
    dma_source = (ROOT / "runtime/snes/kernel/dma.pasm").read_text(encoding="utf-8")
    return {
        "client_channel_claims": clients,
        "descriptor_has_channel_field": "SAME_DMA_REQUEST_CHANNEL" in dma_source,
        "kernel_reserved_channel": 7,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43981)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"k1-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    ownership = source_ownership()
    report: dict[str, object] = {
        "gate": "K1",
        "result": "running",
        "rom": str(rom),
        "rom_size": rom.stat().st_size,
        "rom_sha256": rom_hash,
        "nexen": str(nexen),
        "fresh_power_on": True,
        "donors": {
            "monkey_head": "640e48359c5a17a9edd3a0c2208d62180757a2c1",
            "bor_head": "b80edcbb8020373b9652cece24fb01d6d64cfb7c",
        },
        "ownership": ownership,
    }
    require(not ownership["client_channel_claims"], "a client claims a DMA channel")
    require(not ownership["descriptor_has_channel_field"], "DMA request exposes a channel field")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    mcp_session.validate_mesen_build = lambda _path: None
    try:
        with mcp_session.McpSession(
            rom=rom,
            mesen=nexen,
            cwd=ROOT,
            port=args.port,
            boot_wait=2.0,
            socket_timeout=60.0,
            stderr_log=output / "nexen-stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
            run = session.run_frames(4)
            require(run["framesAdvanced"] == 4 and not run["timedOut"], "boot run timed out")
            dma = dma_snapshot(session)
            ppu = session.get_ppu_state()
            fixtures = {
                "vram": session.read_memory("snesVideoRam", 0x7000, 16).hex(),
                "cgram": session.read_memory("snesCgRam", 0x1E0, 8).hex(),
                "oam": session.read_memory("snesSpriteRam", 0, 8).hex(),
                "forced_sentinel": bytes(8).hex(),
                "forced_active": session.read_memory("snesVideoRam", 0x7020, 8).hex(),
            }
            report["boot"] = {"dma": dma, "ppu": ppu, "fixtures": fixtures}
            require(bytes.fromhex(fixtures["vram"]) == VRAM_EXPECTED, "VRAM fixture mismatch")
            require(bytes.fromhex(fixtures["cgram"]) == CGRAM_EXPECTED, "CGRAM fixture mismatch")
            require(bytes.fromhex(fixtures["oam"]) == OAM_EXPECTED, "OAM fixture mismatch")
            require(fixtures["forced_active"] == fixtures["forced_sentinel"], "forced-blank DMA changed the zero sentinel during active display")
            require(bytes.fromhex(fixtures["forced_active"]) != FORCED_EXPECTED, "forced-blank fixture spilled into active display")
            require(dma["committed"] == 4, "initial DMA fixture commit count mismatch")
            require(dma["pending"] == 1, "forced-blank request is not pending")
            require(dma["deferred_blank"] >= 1, "forced-blank request was not deferred")
            require(dma["deferred_budget"] == 0, "fixture exceeded NMI byte budget")
            require(dma["rejected"] == 0, "fixture request was rejected")
            require(dma["display_shadow"] == 0x0F, "display shadow is not active")

            start_input = input_snapshot(session)
            session.tool("set_input", {"port": 0, "buttons": 0x040, "hold": True})
            held_frames = 120
            timeline = []
            frames_advanced = 0
            pressed = None
            for frame in range(4):
                step = session.run_frames(1)
                require(step["framesAdvanced"] == 1 and not step["timedOut"], "held-input step failed")
                frames_advanced += 1
                state = input_snapshot(session)
                if state["pressed"] & 0x0200:
                    timeline.append({"frame": frame + 1, **state})
                    pressed = state
                    break
            require(pressed is not None, "held Left never produced a press edge")
            require(pressed["pressed"] == 0x0200, "held Left press edge was not exact")
            step = session.run_frames(1)
            require(step["framesAdvanced"] == 1 and not step["timedOut"], "post-edge step failed")
            frames_advanced += 1
            after_edge = input_snapshot(session)
            require(after_edge["pressed"] == 0, "held Left repeated on the next frame")
            remaining = held_frames - frames_advanced
            step = session.run_frames(remaining)
            require(step["framesAdvanced"] == remaining and not step["timedOut"], "bulk held-input run failed")
            held = input_snapshot(session)
            dma_after_hold = dma_snapshot(session)
            report["held_input"] = {
                "frames": held_frames,
                "press_edges": 1,
                "edge_timeline": timeline,
                "after_edge": after_edge,
                "final": held,
                "frame_counter_delta": (held["frame_counter"] - start_input["frame_counter"]) & 0xFFFF,
            }
            report["after_hold_dma"] = dma_after_hold
            require(held["held"] == 0x0200, "held Left state was lost")
            require(held["pressed"] == 0, "held Left edge repeated at final frame")
            require(report["held_input"]["frame_counter_delta"] == held_frames, "NMI frame pacing drifted")
            require(dma_after_hold["committed"] == 4 and dma_after_hold["pending"] == 1, "deferred request committed during active display")
            require(dma_after_hold["deferred_blank"] > dma["deferred_blank"], "blank deferral counter did not advance")
            require(session.read_memory("snesVideoRam", 0x7020, 8) == bytes(8), "forced-blank target changed during held-input run")

            session.tool("set_input", {"port": 0, "buttons": 0, "hold": True})
            session.run_frames(2)
            released = input_snapshot(session)
            report["release"] = released
            require(released["held"] == 0, "Left release did not clear held state")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"K1: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"K1: PASS ({rom_hash})")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
