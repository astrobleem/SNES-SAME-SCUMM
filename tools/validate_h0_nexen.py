#!/usr/bin/env python3
"""Execute SAME's H0 engine-host gate in a fresh Nexen process."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build" / "same-engine-host.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def u16(raw: bytes, offset: int) -> int:
    return raw[offset] | (raw[offset + 1] << 8)


def snapshot(session: object) -> dict[str, int]:
    event = session.read_memory("snesMemory", 0x7E2000, 12)
    state = session.read_memory("snesMemory", 0x7E2200, 0x32)
    return {
        "event_head": u16(event, 0),
        "event_tail": u16(event, 2),
        "event_count": u16(event, 4),
        "event_dropped": u16(event, 6),
        "event_rejected": u16(event, 8),
        "event_sequence": u16(event, 10),
        "input_held": u16(state, 0),
        "input_previous": u16(state, 2),
        "input_pressed": u16(state, 4),
        "input_released": u16(state, 6),
        "frame_counter": u16(state, 0x10),
        "backdrop": u16(state, 0x12),
        "audio_opcode": state[0x14],
        "audio_arg0": int.from_bytes(state[0x16:0x1A], "little"),
        "engine_id": state[0x20],
        "engine_lifecycle": state[0x21],
        "engine_last_status": state[0x22],
        "engine_frame_ops": u16(state, 0x24),
        "engine_total_ops": u16(state, 0x26),
    }


def capture(session: object, destination: Path) -> dict[str, object]:
    shot = session.take_screenshot(format="base64")
    data = base64.b64decode(shot["base64"])
    destination.write_bytes(data)
    with Image.open(io.BytesIO(data)) as image:
        rgb = image.convert("RGB")
        colors = rgb.getcolors(maxcolors=rgb.width * rgb.height)
        center = rgb.getpixel((rgb.width // 2, rgb.height // 2))
        return {
            "path": str(destination),
            "sha256": hashlib.sha256(data).hexdigest(),
            "width": rgb.width,
            "height": rgb.height,
            "unique_colors": len(colors) if colors is not None else None,
            "center_rgb": list(center),
        }


def assert_health(state: dict[str, int], label: str) -> None:
    require(state["event_count"] == 0, f"{label}: event queue did not drain")
    require(state["event_dropped"] == 0, f"{label}: packet was dropped")
    require(state["event_rejected"] == 0, f"{label}: required packet was rejected")


def wait_for_held(
    session: object, expected: int, label: str, *, max_frames: int = 4
) -> tuple[dict[str, int], list[dict[str, int]]]:
    timeline: list[dict[str, int]] = []
    for _ in range(max_frames):
        run = session.run_frames(1)
        require(run["framesAdvanced"] == 1 and not run["timedOut"], f"{label}: frame step failed")
        state = snapshot(session)
        timeline.append(state)
        if state["input_held"] == expected:
            return state, timeline
    raise GateFailure(f"{label}: held state did not reach ${expected:04X}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=43980)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"h0-nexen-{rom_hash[:16]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report: dict[str, object] = {
        "gate": "H0",
        "result": "running",
        "rom": str(rom),
        "rom_size": rom.stat().st_size,
        "rom_sha256": rom_hash,
        "nexen": str(nexen),
        "fresh_power_on": True,
        "checkpoints": {},
        "inputs": {},
    }

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    # Nexen is a self-contained publish, unlike the split Mesen layout expected
    # by the reusable package validator. Its executable identity is checked above.
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

            run = session.run_frames(2)
            require(run["framesAdvanced"] == 2 and not run["timedOut"], "two-frame boot timed out")
            boot = snapshot(session)
            report["checkpoints"]["boot_frame_2"] = boot
            require(boot["engine_id"] == 1, "demo engine id is not $01")
            require(boot["engine_lifecycle"] == 2, "engine lifecycle is not RUNNING")
            require(boot["engine_last_status"] == 0x0A, "last engine status is not READY")
            require(boot["engine_frame_ops"] == 1, "frame operation count is not one")
            require(boot["engine_total_ops"] >= 1, "total operation count did not start")
            require(boot["frame_counter"] >= 1, "WRAM frame counter did not start")
            require(boot["backdrop"] == 0x0010, "boot backdrop is not dark red")
            assert_health(boot, "boot")
            report["checkpoints"]["boot_screenshot"] = capture(session, output / "boot.png")

            # Nexen's frame zero boundary precedes the first game-visible NMI,
            # so the two counters may have a constant one-frame phase offset.
            # Prove the rate instead: every later video frame must contribute
            # exactly one increment to SAME_FRAME_COUNTER.
            run = session.run_frames(178)
            require(run["framesAdvanced"] == 178 and not run["timedOut"], "frame-180 run timed out")
            frame_180 = snapshot(session)
            report["checkpoints"]["frame_180"] = frame_180
            require(
                ((frame_180["frame_counter"] - boot["frame_counter"]) & 0xFFFF) == 178,
                "WRAM frame counter did not increment once per later video frame",
            )
            require(frame_180["engine_total_ops"] > boot["engine_total_ops"], "operation count did not advance")
            require(frame_180["event_sequence"] > boot["event_sequence"], "event sequence did not advance")
            assert_health(frame_180, "frame 180")

            controls = (
                ("left", 0x040, 0x0200, 0x7C00, (0, 0, 255)),
                ("right", 0x080, 0x0100, 0x03E0, (0, 255, 0)),
                ("b", 0x002, 0x8000, 0x001F, (255, 0, 0)),
                ("a", 0x001, 0x0080, 0x7FFF, (255, 255, 255)),
            )
            for name, tool_mask, snes_mask, backdrop, expected_rgb in controls:
                session.tool("set_input", {"port": 0, "buttons": tool_mask, "hold": True})
                pressed, press_timeline = wait_for_held(session, snes_mask, f"{name} press")
                report["inputs"][name] = {
                    "press_timeline": press_timeline,
                    "pressed": pressed,
                }
                require(pressed["input_pressed"] == snes_mask, f"{name}: press edge mismatch")
                require(pressed["backdrop"] == backdrop, f"{name}: backdrop mismatch")
                assert_health(pressed, name)
                session.run_frames(1)
                visible = snapshot(session)
                report["inputs"][name]["visible"] = visible
                require(visible["input_held"] == snes_mask, f"{name}: held bit did not persist")
                require(visible["input_pressed"] == 0, f"{name}: press edge repeated")
                require(visible["backdrop"] == backdrop, f"{name}: shadow changed before commit")
                assert_health(visible, f"{name} visible")
                shot = capture(session, output / f"{name}.png")
                report["inputs"][name]["screenshot"] = shot
                require(tuple(shot["center_rgb"]) == expected_rgb, f"{name}: visible RGB mismatch")
                session.tool("set_input", {"port": 0, "buttons": 0, "hold": True})
                released, release_timeline = wait_for_held(session, 0, f"{name} release")
                report["inputs"][name]["release_timeline"] = release_timeline
                report["inputs"][name]["released"] = released
                require(released["input_released"] == snes_mask, f"{name}: release edge mismatch")

            # Hold Left long enough to prove it creates only one press edge and
            # does not accumulate queue loss.
            session.tool("set_input", {"port": 0, "buttons": 0x040, "hold": True})
            long_press, long_press_timeline = wait_for_held(session, 0x0200, "long hold press")
            require(long_press["input_pressed"] == 0x0200, "long hold initial press edge mismatch")
            session.run_frames(240)
            held = snapshot(session)
            require(held["input_held"] == 0x0200, "long hold lost the Left held bit")
            require(held["input_pressed"] == 0, "long hold repeated the Left press edge")
            assert_health(held, "long hold")
            session.tool("set_input", {"port": 0, "buttons": 0, "hold": True})
            long_release, long_release_timeline = wait_for_held(session, 0, "long hold release")
            require(long_release["input_released"] == 0x0200, "long hold release edge mismatch")
            report["checkpoints"]["long_hold_press"] = long_press
            report["checkpoints"]["long_hold_press_timeline"] = long_press_timeline
            report["checkpoints"]["long_hold"] = held
            report["checkpoints"]["long_hold_release"] = long_release
            report["checkpoints"]["long_hold_release_timeline"] = long_release_timeline

            session.tool("set_input", {"port": 0, "buttons": 0x008, "hold": True})
            start, start_timeline = wait_for_held(session, 0x1000, "Start press")
            report["inputs"]["start"] = {"timeline": start_timeline, "pressed": start}
            require(start["audio_opcode"] == 0, "Start did not route MUSIC_PLAY")
            require(start["audio_arg0"] == 1, "Start did not route music track 1")
            assert_health(start, "Start")
            session.tool("set_input", {"port": 0, "buttons": 0, "hold": True})
            start_release, start_release_timeline = wait_for_held(session, 0, "Start release")
            report["inputs"]["start"]["release_timeline"] = start_release_timeline
            report["inputs"]["start"]["released"] = start_release

            report["checkpoints"]["final_screenshot"] = capture(session, output / "final.png")
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"H0: FAIL: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"H0: PASS ({rom_hash})")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
