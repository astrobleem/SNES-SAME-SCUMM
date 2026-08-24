#!/usr/bin/env python3
"""Static checks for traps Poppy can otherwise accept or misreport.

This is not an assembler.  It catches the project-specific failure classes we can
prove without Poppy: missing includes, long-indexed Y, impossible STZ-long, mixed
assembler dialect, ABI drift, and missing target lifecycle labels.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

FORBIDDEN = [
    (re.compile(r"^\s*@[A-Za-z_]", re.MULTILINE), "Poppy fork mis-resolves @ local labels reached through .include"),
    (re.compile(r"\bstz\.l\b", re.IGNORECASE), "65816 has no STZ absolute-long mode"),
    (
        re.compile(r"\.l\s+[^;\n]+,\s*y\b", re.IGNORECASE),
        "65816 has no absolute-long indexed-Y mode",
    ),
    (re.compile(r"^\s*\.MEMORYMAP\b", re.IGNORECASE | re.MULTILINE), "WLA-DX directive in Poppy source"),
    (re.compile(r"^\s*\.ROMBANK", re.IGNORECASE | re.MULTILINE), "WLA-DX directive in Poppy source"),
    (re.compile(r"^\s*\.db\b", re.IGNORECASE | re.MULTILINE), "legacy assembler data directive; use Poppy .byte"),
    (re.compile(r"(?:#|=)\s*\^\s*\(?[A-Za-z_]", re.IGNORECASE), "Poppy fork still resolves standalone ^(Label) bank expressions as $00"),
]
REQUIRED_LABELS = {
    "reset",
    "nmi_handler",
    "Same_Kernel_Init",
    "Same_Frame_Run",
    "Same_Event_Push",
    "Same_Event_Pop",
    "Same_Target_Boot",
    "Same_Target_Frame",
    "Same_Target_Shutdown",
    "Same_Engine_Boot",
    "Same_Engine_Frame",
    "Same_Engine_Shutdown",
}


def include_closure(main: Path) -> list[Path]:
    visited: set[Path] = set()
    ordered: list[Path] = []

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in visited:
            return
        if not path.is_file():
            raise RuntimeError(f"missing include: {path}")
        visited.add(path)
        ordered.append(path)
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r'^\s*\.include\s+"([^"]+)"', text, re.MULTILINE):
            visit(path.parent / match.group(1))

    visit(main)
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("main", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    try:
        files = include_closure(args.main)
    except RuntimeError as exc:
        print(f"Poppy lint: FAIL: {exc}", file=sys.stderr)
        return 1
    labels: set[str] = set()
    label_locations: dict[str, tuple[Path, list[str], int]] = {}
    branch_targets: set[str] = set()
    combined = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        source_lines = text.splitlines()
        combined.append(text)
        for branch in re.finditer(r"\b(?:bcc|bcs|beq|bne|bmi|bpl|bvc|bvs|bra|brl|jmp|jml)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.IGNORECASE):
            branch_targets.add(branch.group(1))
        for pattern, message in FORBIDDEN:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{path}:{line}: {message}")
        for match in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*):", text, re.MULTILINE):
            label = match.group(1)
            if label in labels:
                errors.append(f"{path}: duplicate global label {label}")
            labels.add(label)
            line_index = text.count("\n", 0, match.start())
            label_locations[label] = (path, source_lines, line_index)
    width_immediate = re.compile(r"^(?:lda|ldx|ldy|cmp|cpx|cpy|and|ora|eor|adc|sbc|bit)\s+#", re.IGNORECASE)
    for target in sorted(branch_targets):
        location = label_locations.get(target)
        if location is None:
            continue
        path, source_lines, line_index = location
        explicit = False
        for offset in range(line_index + 1, min(len(source_lines), line_index + 16)):
            code = source_lines[offset].split(";", 1)[0].strip()
            if not code:
                continue
            if code.lower() in {".a8", ".a16", ".i8", ".i16"}:
                explicit = True
                continue
            if code.endswith(":"):
                break
            if width_immediate.match(code):
                if not explicit:
                    errors.append(
                        f"{path}:{offset + 1}: branch target {target} reaches width-dependent "
                        "immediate before .a8/.a16"
                    )
                break
            if code.lower() in {"rts", "rtl", "rti", "plp"}:
                break

    # Any symbol with a 24-bit WRAM value must be accessed explicitly with an
    # absolute-long-capable mnemonic.  A bare or `.w` operand is DBR-relative;
    # for SAME's $7E:2000+ state it lands in hardware/open-bus space rather than
    # WRAM.  This caught a real lifecycle reset bug at $7E:2222.
    far_symbols: dict[str, int] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(
            r"^\s*(SAME_[A-Z0-9_]+)\s*=\s*\$([0-9A-Fa-f]{6})\b",
            text,
            re.MULTILINE,
        ):
            value = int(match.group(2), 16)
            if value >= 0x010000:
                far_symbols[match.group(1)] = value

    instruction = re.compile(
        r"^\s*([A-Za-z][A-Za-z0-9]*)(?:\.(l|w|b))?\s+(.+?)\s*$",
        re.IGNORECASE,
    )
    for path in files:
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            code = raw_line.split(";", 1)[0].strip()
            if not code or code.startswith(".") or "=" in code:
                continue
            match = instruction.match(code)
            if match is None:
                continue
            _mnemonic, suffix, operand = match.groups()
            for symbol, value in far_symbols.items():
                if re.search(rf"\b{re.escape(symbol)}\b", operand):
                    if suffix is None or suffix.lower() != "l":
                        errors.append(
                            f"{path}:{line_number}: far WRAM symbol {symbol} "
                            f"(${value:06X}) requires explicit .l access"
                        )
                    break

    missing = sorted(REQUIRED_LABELS - labels)
    if missing:
        errors.append("missing required labels: " + ", ".join(missing))
    abi = (args.main.parent / "generated/abi.inc.pasm").resolve()
    if abi not in files:
        errors.append("main source does not include generated/abi.inc.pasm")
    elif "SAME_PACKET_SIZE                         = $10" not in abi.read_text(encoding="utf-8"):
        errors.append("generated ABI does not declare a 16-byte packet")
    if errors:
        print("Poppy lint: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(f"Poppy lint: PASS ({len(files)} files, {len(labels)} global labels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
