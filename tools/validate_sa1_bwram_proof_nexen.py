#!/usr/bin/env python3
"""Fresh-emulator acceptance for the Phase 6B reset-held SA-1 carrier."""

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
DEFAULT_ROM = ROOT / "build/sa1-bwram-proof/same-sa1-bwram-proof.sfc"
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)
EVIDENCE = 0x7E1000


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit_rom(raw: bytes) -> dict[str, object]:
    require(len(raw) == 0x40000, "SA-1 proof ROM is not finalized to 256 KiB")
    title = raw[0x7FC0:0x7FD5].rstrip(b"\0 ")
    require(title == b"SAME SA1 BWRAM PROOF", f"unexpected proof title {title!r}")
    require(raw[0x7FD5] == 0x23, "map mode is not SA-1 slow LoROM $23")
    require(raw[0x7FD6] == 0x35, "cartridge type is not SA-1+RAM+battery $35")
    require(raw[0x7FD7] == 0x08, "ROM-size header does not declare 256 KiB")
    require(raw[0x7FD8] == 0x07, "RAM-size header does not declare 128 KiB")
    complement = int.from_bytes(raw[0x7FDC:0x7FDE], "little")
    checksum = int.from_bytes(raw[0x7FDE:0x7FE0], "little")
    require(checksum ^ complement == 0xFFFF, "checksum pair is not inverse")
    require(sum(raw) & 0xFFFF == checksum, "checksum does not match ROM byte sum")
    vectors = {
        "nmi": int.from_bytes(raw[0x7FFA:0x7FFC], "little"),
        "reset": int.from_bytes(raw[0x7FFC:0x7FFE], "little"),
        "irq": int.from_bytes(raw[0x7FFE:0x8000], "little"),
    }
    require(all(0x8000 <= value <= 0xFFFF for value in vectors.values()), "invalid vectors")
    return {
        "title": title.decode("ascii"),
        "map_mode": raw[0x7FD5],
        "cartridge_type": raw[0x7FD6],
        "rom_size_code": raw[0x7FD7],
        "bwram_size_code": raw[0x7FD8],
        "checksum": checksum,
        "vectors": vectors,
    }


def stable_sa1_state(state: dict[str, object]) -> dict[str, object]:
    return {
        key: state[key]
        for key in ("pc", "k", "a", "x", "y", "sp", "d", "dbr", "ps", "emulationMode")
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--output", type=Path, default=ROOT / "build/sa1-bwram-proof/nexen")
    parser.add_argument("--port", type=int, default=44092)
    args = parser.parse_args()
    rom = args.rom.resolve()
    nexen = args.nexen.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    require(rom.is_file(), f"proof ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen unavailable: {nexen}")

    raw_rom = rom.read_bytes()
    rom_audit = audit_rom(raw_rom)
    manifest = json.loads((rom.parent / "manifest.json").read_text(encoding="utf-8"))
    generated = ROOT / "labs/sa1_bwram/generated"
    expected_surface = (generated / "surface-first.index8").read_bytes() + (
        generated / "surface-second.index8"
    ).read_bytes()
    expected_tiles = (generated / "tiles-first.8bpp").read_bytes() + (
        generated / "tiles-second.8bpp"
    ).read_bytes()
    expected_map = (generated / "tilemap.bin").read_bytes()
    expected_cgram = (generated / "palette.cgram").read_bytes()
    require(len(expected_surface) == len(expected_tiles) == 0xE000, "asset size differs")
    reference_path = rom.parent / "reference.png"
    reference = Image.open(reference_path).convert("RGB")

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    mcp_session.validate_mesen_build = lambda _path: None
    with mcp_session.McpSession(
        rom=rom,
        mesen=nexen,
        cwd=ROOT,
        port=args.port,
        boot_wait=2.0,
        socket_timeout=90.0,
        stderr_log=output / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0, "power reset did not reach frame zero")
        sa1_at_reset = session.get_cpu_state("Sa1")
        require(stable_sa1_state(sa1_at_reset) == {
            "pc": 0, "k": 0, "a": 0, "x": 0, "y": 0, "sp": 0x1FF,
            "d": 0, "dbr": 0, "ps": 0x34, "emulationMode": True,
        }, "SA-1 architectural reset state differs")

        terminal_frame = None
        for frame in range(1, 301):
            run = session.run_frames(1)
            require(run["framesAdvanced"] == 1 and not run["timedOut"], "carrier boot timed out")
            if session.read_memory("snesMemory", EVIDENCE + 1, 1)[0] == 0xFF:
                terminal_frame = frame
                break
        require(terminal_frame is not None, "carrier did not reach terminal proof stage")
        evidence = session.read_memory("snesMemory", EVIDENCE, 0x20)
        require(evidence[0] == 0xB6 and evidence[1] == 0xFF, "proof status/stage differs")
        require(evidence[2] == 0x7F, "BWPA/SBWE boundary proof did not complete")
        require(evidence[3] == 0x7F, "seven BMAPS band tests did not complete")
        require(evidence[4] == 1, "banks $40 and $41 did not prove distinct")
        require(evidence[5] == 1, "tile-record isolation proof did not complete")
        require(evidence[6:10] == bytes((0x20, 0, 0, 3)), "SA-1 control shadows differ")
        require(evidence[11] == 1 and evidence[12] == 0, "active DMA/error evidence differs")
        require(evidence[0x10] == evidence[0x11], "protected write below BWPA boundary stuck")
        require(evidence[0x12] == (evidence[0x10] ^ 0xFF), "SBWE bypass did not write protected byte")

        sa1_terminal = session.get_cpu_state("Sa1")
        require(stable_sa1_state(sa1_terminal) == stable_sa1_state(sa1_at_reset),
                "SA-1 executed or changed architectural state")
        require(sa1_terminal["cycleCount"] > sa1_at_reset["cycleCount"],
                "emulator did not advance reset-held SA-1 time")

        bank40 = session.read_memory("snesMemory", 0x400000, 0x10000)
        bank41 = session.read_memory("snesMemory", 0x410000, 0x10000)
        require(bank40[0x0800] == 0xA5, "first writable byte does not retain sentinel")
        require(bank40[0x1000] == 0x5A, "backend reserve does not retain sentinel")
        require(bank40[0x2000:] == expected_surface, "complete live surface differs")
        require(bank41[:0xE000] == expected_tiles, "complete planar shadow differs")
        require(bank41[0xE000:0xE200] == expected_cgram, "complete CGRAM shadow differs")
        require(bank41[0xFFFF] == 0xEF, "last configured BW-RAM byte differs")
        require(bank40[0x2000] != bank41[0x2000], "bank $41 mirrors bank $40")
        surface_probe_offsets = (
            0, 7, 8, 255, 256, 0x1FFF, 0x2000, 0x3FFF, 0x4000,
            0x5FFF, 0x6000, 0x7FFF, 0x8000, 0x9FFF, 0xA000,
            0xBFFF, 0xC000, 0xDFFF,
        )
        surface_probes = {
            f"40:{0x2000 + offset:04X}": bank40[0x2000 + offset]
            for offset in surface_probe_offsets
        }
        require(
            all(
                surface_probes[f"40:{0x2000 + offset:04X}"] == expected_surface[offset]
                for offset in surface_probe_offsets
            ),
            "selected pixel/row/tile/8-KiB boundary probes differ",
        )

        save_low = session.read_memory("snesSaveRam", 0, 0x10000)
        save_high = session.read_memory("snesSaveRam", 0x10000, 0x10000)
        require(save_low == bank40 and save_high == bank41,
                "emulator cartridge-RAM view differs from direct BW-RAM banks")

        vram = session.read_memory("snesVideoRam", 0, 0x10000)
        cgram = session.read_memory("snesCgRam", 0, 512)
        require(vram[:0xE000] == expected_tiles, "BW-RAM-sourced character VRAM differs")
        require(vram[0xE000:0xE800] == expected_map, "static tilemap differs")
        require(cgram == expected_cgram, "BW-RAM-sourced CGRAM differs")
        ppu = session.get_ppu_state()
        require(not ppu["forcedBlank"] and ppu["brightness"] == 15, "display did not enable")
        require(ppu["bgMode"] == 3 and ppu["mainScreenLayers"] == 1, "Mode-3 BG1 state differs")
        require(ppu["layers"][0]["tilemapAddr"] == 0x7000, "BG1 tilemap address differs")
        require(ppu["layers"][0]["chrAddr"] == 0, "BG1 character address differs")

        shot = session.take_screenshot(format="base64")
        full_bytes = base64.b64decode(shot["base64"])
        full_path = output / "emulator-full.png"
        full_path.write_bytes(full_bytes)
        full = Image.open(io.BytesIO(full_bytes)).convert("RGB")
        require(full.width == 256 and full.height >= 224, "screenshot dimensions differ")
        visible = full.crop((0, 0, 256, 224))
        require(ImageChops.difference(visible, reference).getbbox() is None,
                "visible emulator pixels differ from independent reference")
        visible_path = output / "emulator-visible.png"
        visible.save(visible_path)

        dma = session.read_memory("snesMemory", 0x7E223A, 14)
        pending = int.from_bytes(dma[2:4], "little")
        committed = int.from_bytes(dma[4:6], "little")
        rejected = int.from_bytes(dma[10:12], "little")
        require(committed == 31 and pending == 0 and rejected == 0,
                f"production DMA counters differ: committed={committed}, pending={pending}, rejected={rejected}")

    report = {
        "gate": "Phase 6B SA-1 BW-RAM carrier and surface-storage proof",
        "result": "pass",
        "fresh_power_on": True,
        "debugger_writes": 0,
        "terminal_frame": terminal_frame,
        "rom": {"path": str(rom), "bytes": len(raw_rom), "sha256": sha256(raw_rom), **rom_audit},
        "requested_bwram_bytes": 0x20000,
        "observed_bwram_bytes": len(save_low) + len(save_high),
        "sa1": {
            "ccnt": 0x20,
            "reset_asserted": True,
            "architectural_state_at_reset": stable_sa1_state(sa1_at_reset),
            "architectural_state_at_terminal": stable_sa1_state(sa1_terminal),
            "executed_instructions": False,
        },
        "protection": {
            "bwpa": 3,
            "protected_bytes": 0x0800,
            "sbwe_final": 0,
            "below_boundary_rejected": True,
            "first_writable_address": "40:0800",
            "sbwe_bypass_proven_and_restored": True,
        },
        "hashes": {
            "live_surface": sha256(bank40[0x2000:]),
            "planar_shadow": sha256(bank41[:0xE000]),
            "cgram_shadow": sha256(bank41[0xE000:0xE200]),
            "reference_png": sha256(reference_path.read_bytes()),
            "emulator_visible_png": sha256(visible_path.read_bytes()),
            "emulator_full_png": sha256(full_path.read_bytes()),
        },
        "surface_boundary_probes": surface_probes,
        "bmaps": {
            "window": "00-3F/80-BF:6000-7FFF",
            "selectors": {str(selector): f"40:{selector * 0x2000:04X}-{selector * 0x2000 + 0x1FFF:04X}"
                          for selector in range(1, 8)},
            "direct_to_window": True,
            "window_to_direct": True,
            "both_cpu_mirrors": True,
            "final_selector": 0,
        },
        "dma": {
            "engine": "S-CPU MDMA channel 7 via Same_Dma_Enqueue/Same_Video_Commit",
            "sa1_dma_used": False,
            "committed_descriptors": committed,
            "forced_blank_tile_chunks": 28,
            "normal_nmi_tile_descriptors": 1,
            "vram_matches_bwram_shadow": True,
        },
        "layout": manifest["layout"],
        "battery_persistence_tested": False,
    }
    report_path = output / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": "pass",
        "report": str(report_path),
        "rom_sha256": report["rom"]["sha256"],
        "surface_sha256": report["hashes"]["live_surface"],
        "emulator_visible_png_sha256": report["hashes"]["emulator_visible_png"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
