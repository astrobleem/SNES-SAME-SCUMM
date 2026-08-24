#!/usr/bin/env python3
"""Pad a headered LoROM image and write its checksum/complement pair."""

from __future__ import annotations

import argparse
from pathlib import Path


HEADER_OFFSET = 0x7FC0
CHECKSUM_COMPLEMENT_OFFSET = HEADER_OFFSET + 0x1C
CHECKSUM_OFFSET = HEADER_OFFSET + 0x1E
MINIMUM_ROM_SIZE = 0x8000


def next_power_of_two(value: int) -> int:
    size = MINIMUM_ROM_SIZE
    while size < value:
        size <<= 1
    return size


def finalize(raw: bytes) -> bytes:
    if len(raw) > 0x400000:
        raise ValueError(f"LoROM image is unexpectedly large: {len(raw)} bytes")
    size = next_power_of_two(len(raw))
    image = bytearray(raw)
    image.extend(b"\x00" * (size - len(image)))
    if len(image) < HEADER_OFFSET + 0x40:
        raise ValueError("image does not contain a complete LoROM header")

    image[CHECKSUM_COMPLEMENT_OFFSET : CHECKSUM_OFFSET + 2] = b"\x00\x00\x00\x00"
    # In the finalized image the two checksum words contribute $01FE to the
    # byte sum regardless of the checksum value: each byte and its complement
    # add to $FF.  Include that contribution when calculating the stored sum.
    checksum = (sum(image) + 0x01FE) & 0xFFFF
    complement = checksum ^ 0xFFFF
    image[CHECKSUM_COMPLEMENT_OFFSET:CHECKSUM_OFFSET] = complement.to_bytes(2, "little")
    image[CHECKSUM_OFFSET : CHECKSUM_OFFSET + 2] = checksum.to_bytes(2, "little")
    return bytes(image)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()
    raw = args.rom.read_bytes()
    finalized = finalize(raw)
    args.rom.write_bytes(finalized)
    print(f"Finalized LoROM: {args.rom} ({len(finalized)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
