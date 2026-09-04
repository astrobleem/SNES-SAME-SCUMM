#!/usr/bin/env python3
"""Fail-closed audit for a selected SAME SNES production carrier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from same.snes_carrier import load_carrier


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("--carrier", choices=("lorom", "sa1_bwram"), default="lorom")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        raw = args.rom.read_bytes()
    except OSError as exc:
        parser.error(str(exc))
    errors: list[str] = []
    if len(raw) < 0x8000 or len(raw) & (len(raw) - 1):
        errors.append(f"ROM size {len(raw)} is not a power of two >= 32 KiB")
    if len(raw) >= 0x8000:
        title = raw[0x7FC0 : 0x7FC0 + 21].rstrip(b"\0 ")
        if not title.startswith(b"SAME ENGINE HOST"):
            errors.append(f"unexpected LoROM title {title!r}")
        map_mode = raw[0x7FD5]
        cartridge_type = raw[0x7FD6]
        rom_size_code = raw[0x7FD7]
        ram_size = raw[0x7FD8]
        if args.carrier == "lorom":
            if map_mode != 0x20:
                errors.append(f"ordinary LoROM map mode is ${map_mode:02X}, expected $20")
            if (cartridge_type, ram_size) not in {(0x00, 0x00), (0x02, 0x01)}:
                errors.append(
                    f"ordinary LoROM cartridge/RAM pair is "
                    f"${cartridge_type:02X}/${ram_size:02X}"
                )
        else:
            if (map_mode, cartridge_type, ram_size) != (0x23, 0x35, 0x07):
                errors.append(
                    "SA-1 carrier header is "
                    f"${map_mode:02X}/${cartridge_type:02X}/${ram_size:02X}, "
                    "expected $23/$35/$07"
                )
            expected_size_code = len(raw).bit_length() - 11
            if rom_size_code != expected_size_code:
                errors.append(
                    f"SA-1 ROM size code is ${rom_size_code:02X}, expected "
                    f"${expected_size_code:02X} for {len(raw)} bytes"
                )
        if not 0x05 <= rom_size_code <= 0x0C:
            errors.append(f"invalid ROM size code ${rom_size_code:02X}")
        if args.manifest is not None:
            try:
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
                if manifest.get("carrier") != args.carrier:
                    errors.append("carrier manifest selects a different carrier")
                description = load_carrier(
                    ROOT, args.carrier, save_enabled=bool(manifest.get("save_enabled"))
                )
                expected_header = manifest.get("header")
                if not isinstance(expected_header, dict):
                    errors.append("carrier manifest has no header record")
                else:
                    expected = (
                        description.map_mode,
                        description.cartridge_type,
                        int(expected_header.get("rom_size", -1)),
                        description.ram_size,
                    )
                    if (map_mode, cartridge_type, rom_size_code, ram_size) != expected:
                        errors.append("ROM header differs from generated carrier manifest")
                if manifest.get("carrier_config_sha256") != description.config_sha256:
                    errors.append("carrier manifest config identity is stale")
                if manifest.get("layout_sha256") != description.layout_sha256:
                    errors.append("carrier manifest layout identity is stale")
                save = manifest.get("save")
                if not isinstance(save, dict) or (
                    int(str(save.get("base", "-1")), 16), save.get("bytes")
                ) != (description.save_base, description.save_bytes):
                    errors.append("carrier manifest save contract differs")
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                errors.append(f"invalid carrier manifest: {exc}")
        nmi = int.from_bytes(raw[0x7FFA:0x7FFC], "little")
        reset = int.from_bytes(raw[0x7FFC:0x7FFE], "little")
        irq = int.from_bytes(raw[0x7FFE:0x8000], "little")
        for name, vector in (("NMI", nmi), ("RESET", reset), ("IRQ", irq)):
            if not 0x8000 <= vector <= 0xFFFF:
                errors.append(f"{name} vector ${vector:04X} is outside LoROM bank code")
        checksum_complement = int.from_bytes(raw[0x7FDC:0x7FDE], "little")
        checksum = int.from_bytes(raw[0x7FDE:0x7FE0], "little")
        if (checksum ^ checksum_complement) != 0xFFFF:
            errors.append(
                f"checksum/complement are not inverse: ${checksum:04X}/${checksum_complement:04X}"
            )
        actual_checksum = sum(raw) & 0xFFFF
        if checksum != actual_checksum:
            errors.append(
                f"checksum ${checksum:04X} does not match ROM byte sum ${actual_checksum:04X}"
            )
    if errors:
        print("SNES ROM audit: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(
        f"SNES ROM audit: PASS ({args.carrier}, {len(raw)} bytes, reset=${reset:04X}, "
        f"nmi=${nmi:04X}, irq=${irq:04X})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
