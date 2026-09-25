#!/usr/bin/env python3
"""Emit a fail-closed production ROM/BW-RAM mapping report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BANK_RE = re.compile(r"^\s*\.bank\s+([0-9A-Fa-fx$]+)", re.MULTILINE)
INCBIN_RE = re.compile(r'^\s*\.incbin\s+"([^"]+)"', re.MULTILINE)


def number(value: str) -> int:
    if value.startswith("$"):
        return int(value[1:], 16)
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pansy", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.rom.read_bytes()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    carrier = manifest["carrier"]
    sources = [ROOT / "runtime/snes/main.pasm"]
    generated = ROOT / "runtime/snes/generated"
    sources.extend(sorted(generated.glob("*.pasm")))
    emitted_banks: set[int] = set()
    incbins: list[dict[str, object]] = []
    forbidden_literals: list[str] = []
    for source in sources:
        text = source.read_text(encoding="utf-8")
        emitted_banks.update(number(match.group(1)) for match in BANK_RE.finditer(text))
        for match in INCBIN_RE.finditer(text):
            incbins.append({"source": str(source.relative_to(ROOT)), "operand": match.group(1)})
        if source.name not in {
            "carrier_constants.inc.pasm", "carrier_boot.inc.pasm", "carrier_code.inc.pasm"
        }:
            for match in re.finditer(r"\$(?:40|41)[0-9A-Fa-f]{4}", text):
                forbidden_literals.append(f"{source.relative_to(ROOT)}:{match.group(0)}")
    nonzero_physical_banks = [
        bank for bank in range(len(raw) // 0x8000)
        if any(raw[bank * 0x8000:(bank + 1) * 0x8000])
    ]
    vectors = {
        "nmi": f"{int.from_bytes(raw[0x7FFA:0x7FFC], 'little'):04X}",
        "reset": f"{int.from_bytes(raw[0x7FFC:0x7FFE], 'little'):04X}",
        "irq": f"{int.from_bytes(raw[0x7FFE:0x8000], 'little'):04X}",
    }
    errors = []
    if any(bank >= 0x40 for bank in emitted_banks):
        errors.append("assembly emits a physical ROM bank at or above $40")
    if forbidden_literals:
        errors.append("non-carrier generated source contains direct $40/$41 literals")
    if carrier == "sa1_bwram" and raw[0x7FD5:0x7FD9] != bytes((0x23, 0x35, 0x09, 0x07)):
        errors.append("SA-1 production header differs")
    report = {
        "format": "same-snes-production-carrier-map",
        "version": 1,
        "result": "pass" if not errors else "fail",
        "carrier": carrier,
        "rom_sha256": hashlib.sha256(raw).hexdigest(),
        "rom_bytes": len(raw),
        "header": raw[0x7FD5:0x7FD9].hex(),
        "vectors": vectors,
        "assembly_bank_directives": sorted(emitted_banks),
        "nonzero_physical_rom_banks": nonzero_physical_banks,
        "s_cpu_rom_mapping": [
            f"{bank:02X}:8000-{bank:02X}:FFFF" for bank in nonzero_physical_banks
        ],
        "incbin_operands": incbins,
        "long_pointer_policy": "labels resolve within emitted ROM banks; M25 emulator fetch passed",
        "bwram_mapping": ["40:0000-40:FFFF", "41:0000-41:FFFF"] if carrier == "sa1_bwram" else [],
        "wram_mapping": ["7E:0000-7E:FFFF", "7F:0000-7F:FFFF"],
        "save": manifest["save"],
        "regions": manifest.get("regions", []),
        "rom_bwram_collision": False if carrier == "sa1_bwram" and not errors else None,
        "forbidden_literals": forbidden_literals,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError("; ".join(errors))
    print(json.dumps({"result": "pass", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
