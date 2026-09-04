#!/usr/bin/env python3
"""Fresh-emulator acceptance for the Phase 6A static Mode-3 surface ROM."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "build/snes-surface-proof/same-snes-surface-proof.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit_rom(raw: bytes) -> dict[str, object]:
    require(len(raw) == 0x20000, "proof ROM is not finalized to 128 KiB")
    title = raw[0x7FC0 : 0x7FD5].rstrip(b"\0 ")
    require(title == b"SAME INDEX8 MODE3", f"unexpected proof ROM title {title!r}")
    require(raw[0x7FD5] == 0x20, "proof ROM is not slow LoROM")
    require(raw[0x7FD6] == 0x00 and raw[0x7FD8] == 0x00, "proof ROM declares cartridge RAM")
    complement = int.from_bytes(raw[0x7FDC:0x7FDE], "little")
    checksum = int.from_bytes(raw[0x7FDE:0x7FE0], "little")
    require(checksum ^ complement == 0xFFFF, "proof checksum pair is not inverse")
    require(sum(raw) & 0xFFFF == checksum, "proof checksum does not match ROM byte sum")
    vectors = {
        "nmi": int.from_bytes(raw[0x7FFA:0x7FFC], "little"),
        "reset": int.from_bytes(raw[0x7FFC:0x7FFE], "little"),
        "irq": int.from_bytes(raw[0x7FFE:0x8000], "little"),
    }
    require(all(0x8000 <= value <= 0xFFFF for value in vectors.values()), "invalid proof vectors")
    return {"title": title.decode("ascii"), "checksum": checksum, "vectors": vectors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--output", type=Path, default=ROOT / "build/snes-surface-proof/nexen")
    parser.add_argument("--port", type=int, default=43985)
    args = parser.parse_args()
    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    require(rom.is_file(), f"proof ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen unavailable: {nexen}")
    raw_rom = rom.read_bytes()
    rom_audit = audit_rom(raw_rom)

    generated = ROOT / "labs/snes_surface/generated"
    expected_tiles = (generated / "tiles-first.8bpp").read_bytes() + (
        generated / "tiles-second.8bpp"
    ).read_bytes()
    expected_map = (generated / "tilemap.bin").read_bytes()
    expected_cgram = (generated / "palette.cgram").read_bytes()
    reference_path = ROOT / "build/snes-surface-proof/reference.png"
    reference = Image.open(reference_path).convert("RGB")
    require(reference.size == (256, 224), "reference image dimensions differ")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    mcp_session.validate_mesen_build = lambda _path: None
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
        run = session.run_frames(3)
        require(run["framesAdvanced"] == 3 and not run["timedOut"], "proof boot timed out")
        ppu = session.get_ppu_state()
        require(not ppu["forcedBlank"] and ppu["brightness"] == 15, "display did not enable")
        require(ppu["bgMode"] == 3, "BGMODE is not Mode 3")
        require(ppu["mainScreenLayers"] == 1 and ppu["subScreenLayers"] == 0, "BG1 layer selection differs")
        bg1 = ppu["layers"][0]
        require(bg1["tilemapAddr"] == 0x7000, "BG1 tilemap word address is not $7000")
        require(bg1["chrAddr"] == 0, "BG1 character base is not zero")
        require(bg1["hscroll"] == 0 and bg1["vscroll"] == 0x3FF, "BG1 alignment scroll differs")
        require(not bg1["largeTiles"] and not bg1["doubleWidth"] and not bg1["doubleHeight"], "BG1 map geometry differs")

        vram = session.read_memory("snesVideoRam", 0, 0x10000)
        cgram = session.read_memory("snesCgRam", 0, 512)
        require(vram[:0xE000] == expected_tiles, "emulator character VRAM differs")
        require(vram[0xE000:0xE800] == expected_map, "emulator tilemap VRAM differs")
        require(cgram == expected_cgram, "emulator CGRAM differs")

        shot = session.take_screenshot(format="base64")
        screenshot_bytes = base64.b64decode(shot["base64"])
        full_path = output / "emulator-full.png"
        full_path.write_bytes(screenshot_bytes)
        full = Image.open(io.BytesIO(screenshot_bytes)).convert("RGB")
        require(full.width == 256 and full.height >= 224, "emulator screenshot is too small")
        visible = full.crop((0, 0, 256, 224))
        difference = ImageChops.difference(visible, reference)
        require(difference.getbbox() is None, "emulator pixels differ from reference")
        visible_path = output / "emulator-visible.png"
        visible.save(visible_path)

    report = {
        "gate": "Phase 6A static SNES indexed surface",
        "result": "pass",
        "fresh_power_on": True,
        "debugger_writes": 0,
        "rom": {"path": str(rom), "bytes": len(raw_rom), "sha256": sha256(raw_rom), **rom_audit},
        "ppu": {
            "BGMODE": 3,
            "BG1SC": 0x70,
            "BG12NBA": 0,
            "TM": 1,
            "TS": 0,
            "tilemap_word_address": bg1["tilemapAddr"],
            "character_word_address": bg1["chrAddr"],
            "vertical_alignment_scroll": bg1["vscroll"],
        },
        "assets": {
            "tiles": {"bytes": len(expected_tiles), "sha256": sha256(expected_tiles)},
            "tilemap": {"bytes": len(expected_map), "sha256": sha256(expected_map)},
            "cgram": {"bytes": len(expected_cgram), "sha256": sha256(expected_cgram)},
        },
        "screenshots": {
            "reference": {"path": str(reference_path), "sha256": sha256(reference_path.read_bytes())},
            "emulator_full": {"path": str(full_path), "sha256": sha256(full_path.read_bytes()), "size": list(full.size)},
            "emulator_visible": {"path": str(visible_path), "sha256": sha256(visible_path.read_bytes()), "size": list(visible.size)},
            "different_pixels": 0,
        },
    }
    report_path = output / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": "pass", "report": str(report_path), "rom_sha256": report["rom"]["sha256"], "screenshot_sha256": report["screenshots"]["emulator_visible"]["sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
