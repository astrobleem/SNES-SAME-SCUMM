#!/usr/bin/env python3
"""Minimal fail-closed audit for the Poppy-produced LoROM engine-host bootstrap."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
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
        if (map_mode & 0x2F) not in {0x20, 0x21}:
            errors.append(f"unexpected map mode ${map_mode:02X}")
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
        f"SNES ROM audit: PASS ({len(raw)} bytes, reset=${reset:04X}, "
        f"nmi=${nmi:04X}, irq=${irq:04X})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
