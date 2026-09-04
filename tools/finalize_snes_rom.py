#!/usr/bin/env python3
"""Finalize a selected SAME SNES carrier and write its checksum pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from same.snes_carrier import load_carrier


HEADER_OFFSET = 0x7FC0
CHECKSUM_COMPLEMENT_OFFSET = HEADER_OFFSET + 0x1C
CHECKSUM_OFFSET = HEADER_OFFSET + 0x1E
MINIMUM_ROM_SIZE = 0x8000


def next_power_of_two(value: int) -> int:
    size = MINIMUM_ROM_SIZE
    while size < value:
        size <<= 1
    return size


def _validate_carrier_header(
    raw: bytes,
    *,
    carrier: str,
    manifest: dict[str, object] | None,
) -> None:
    if len(raw) < HEADER_OFFSET + 0x19:
        raise ValueError("image does not contain carrier header fields")
    if manifest is None:
        expected_map = 0x20 if carrier == "lorom" else 0x23
        if raw[HEADER_OFFSET + 0x15] != expected_map:
            raise ValueError(
                f"requested carrier {carrier} conflicts with map mode "
                f"${raw[HEADER_OFFSET + 0x15]:02X}"
            )
        return
    if manifest.get("carrier") != carrier:
        raise ValueError("requested carrier conflicts with generated manifest")
    save_enabled = bool(manifest.get("save_enabled"))
    description = load_carrier(ROOT, carrier, save_enabled=save_enabled)
    header = manifest.get("header")
    if not isinstance(header, dict):
        raise ValueError("carrier manifest has no header record")
    expected = bytes(
        (
            description.map_mode,
            description.cartridge_type,
            int(header["rom_size"]),
            description.ram_size,
        )
    )
    observed = raw[HEADER_OFFSET + 0x15 : HEADER_OFFSET + 0x19]
    if observed != expected:
        raise ValueError(
            f"assembled carrier header {observed.hex()} conflicts with "
            f"manifest {expected.hex()}"
        )
    if manifest.get("carrier_config_sha256") != description.config_sha256:
        raise ValueError("carrier manifest was generated from a different carrier config")
    if manifest.get("layout_sha256") != description.layout_sha256:
        raise ValueError("carrier manifest was generated from a different layout")


def finalize(
    raw: bytes,
    *,
    carrier: str = "lorom",
    manifest: dict[str, object] | None = None,
) -> bytes:
    if len(raw) > 0x400000:
        raise ValueError(f"SNES image is unexpectedly large: {len(raw)} bytes")
    if carrier not in {"lorom", "sa1_bwram"}:
        raise ValueError(f"unsupported SNES carrier {carrier!r}")
    _validate_carrier_header(raw, carrier=carrier, manifest=manifest)
    size = next_power_of_two(len(raw))
    if carrier == "sa1_bwram":
        expected_size_code = size.bit_length() - 11
        observed_size_code = raw[HEADER_OFFSET + 0x17]
        if observed_size_code != expected_size_code:
            raise ValueError(
                f"SA-1 ROM size code ${observed_size_code:02X} conflicts with "
                f"finalized size {size} (expected ${expected_size_code:02X})"
            )
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
    parser.add_argument("--carrier", choices=("lorom", "sa1_bwram"), default="lorom")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    raw = args.rom.read_bytes()
    manifest = (
        json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.manifest is not None
        else None
    )
    finalized = finalize(raw, carrier=args.carrier, manifest=manifest)
    args.rom.write_bytes(finalized)
    print(f"Finalized {args.carrier}: {args.rom} ({len(finalized)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
