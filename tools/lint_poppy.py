#!/usr/bin/env python3
"""Static checks for traps Poppy can otherwise accept or misreport.

This is not an assembler.  It catches the project-specific failure classes we can
prove without Poppy: missing includes, long-indexed Y, impossible STZ-long, mixed
assembler dialect, ABI drift, and missing target lifecycle labels.
"""

from __future__ import annotations

import argparse
import ast
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


def _conditional_value(expression: str, symbols: dict[str, int | None]) -> bool | None:
    """Evaluate the small boolean subset used to guard source includes.

    Unknown expressions are kept active so lint fails closed on missing inputs.
    This only filters includes in inactive generated build branches; it does
    not preprocess or omit ordinary source text from the lint scan.
    """
    value = expression.strip().replace("&&", " and ").replace("||", " or ")
    value = re.sub(r"(?<![<>=!])!(?!=)", " not ", value)
    value = re.sub(r"\$([0-9A-Fa-f]+)", r"0x\1", value)
    unknown = False

    def substitute(match: re.Match[str]) -> str:
        nonlocal unknown
        token = match.group(0)
        if token in {"and", "or", "not"}:
            return token
        if token in symbols:
            symbol_value = symbols[token]
            if symbol_value is None:
                unknown = True
                return token
            return str(symbol_value)
        if token in {"True", "False"}:
            return token
        unknown = True
        return token

    value = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", substitute, value)
    if unknown:
        return None
    try:
        tree = ast.parse(value, mode="eval")
    except SyntaxError:
        return None
    allowed = (
        ast.Expression, ast.Constant, ast.BoolOp, ast.UnaryOp, ast.Compare,
        ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq,
    )
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        return None
    return bool(eval(compile(tree, "<poppy-include-condition>", "eval"),
                     {"__builtins__": {}}, {}))


def include_closure(main: Path) -> list[Path]:
    ordered_set: set[Path] = set()
    ordered: list[Path] = []
    active_paths: set[Path] = set()

    def parse_block(lines: list[str], start: int, path: Path,
                    nested: bool = False) -> tuple[list[tuple], int, str | None]:
        nodes: list[tuple] = []
        index = start
        while index < len(lines):
            code = lines[index].split(";", 1)[0].strip()
            lowered = code.lower()
            if lowered in {".else", ".endif"} or lowered.startswith(".elseif "):
                if not nested:
                    raise RuntimeError(f"unmatched {lowered} in {path}:{index + 1}")
                marker = (".elseif " + code[8:].strip()
                          if lowered.startswith(".elseif ") else lowered)
                return nodes, index, marker
            if lowered.startswith(".if "):
                conditional, next_index = parse_if(
                    lines, code[4:].strip(), index + 1, path
                )
                nodes.append(conditional)
                index = next_index
                continue
            include = re.match(r'^\.include\s+"([^"]+)"', code, re.IGNORECASE)
            if include:
                nodes.append(("include", include.group(1)))
            else:
                definition = re.match(
                    r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\$([0-9A-Fa-f]+)\b",
                    code,
                )
                if definition:
                    nodes.append(("assign", definition.group(1),
                                  int(definition.group(2), 16)))
            index += 1
        return nodes, index, None

    def parse_if(lines: list[str], expression: str, body_start: int,
                 path: Path) -> tuple[tuple, int]:
        then_nodes, marker, terminator = parse_block(
            lines, body_start, path, nested=True
        )
        else_nodes: list[tuple] = []
        if terminator == ".else":
            else_nodes, marker, terminator = parse_block(
                lines, marker + 1, path, nested=True
            )
        elif terminator.startswith(".elseif "):
            nested_conditional, next_index = parse_if(
                lines, terminator[8:].strip(), marker + 1, path
            )
            # The recursive .elseif parser consumes the shared .endif.
            return ("if", expression, then_nodes, [nested_conditional]), next_index
        if terminator != ".endif":
            raise RuntimeError(f"unterminated .if in {path}:{body_start}")
        return ("if", expression, then_nodes, else_nodes), marker + 1

    def merge_environments(left: dict[str, int | None],
                           right: dict[str, int | None]) -> dict[str, int | None]:
        merged: dict[str, int | None] = {}
        for name in left.keys() | right.keys():
            left_value = left.get(name)
            right_value = right.get(name)
            merged[name] = left_value if left_value == right_value else None
        return merged

    def evaluate(nodes: list[tuple], path: Path,
                 symbols: dict[str, int | None]) -> dict[str, int | None]:
        for node in nodes:
            if node[0] == "assign":
                _, name, value = node
                symbols[name] = value
            elif node[0] == "include":
                visit(path.parent / node[1], symbols)
            else:
                _, expression, then_nodes, else_nodes = node
                result = _conditional_value(expression, symbols)
                if result is True:
                    evaluate(then_nodes, path, symbols)
                elif result is False:
                    evaluate(else_nodes, path, symbols)
                else:
                    then_symbols = evaluate(then_nodes, path, dict(symbols))
                    else_symbols = evaluate(else_nodes, path, dict(symbols))
                    symbols.clear()
                    symbols.update(merge_environments(then_symbols, else_symbols))
        return symbols

    def visit(path: Path, symbols: dict[str, int | None]) -> None:
        path = path.resolve()
        if path in active_paths:
            return
        if not path.is_file():
            raise RuntimeError(f"missing include: {path}")
        if path not in ordered_set:
            ordered_set.add(path)
            ordered.append(path)
        active_paths.add(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            nodes, end, terminator = parse_block(lines, 0, path)
            if end != len(lines) or terminator is not None:
                raise RuntimeError(f"invalid conditional structure in {path}")
            evaluate(nodes, path, symbols)
        finally:
            active_paths.remove(path)

    visit(main, {})
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
    operand_symbols = re.compile(r"\bSAME_[A-Z0-9_]+\b", re.IGNORECASE)
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
            if operand.lstrip().startswith("#"):
                continue
            for token in operand_symbols.findall(operand):
                symbol = token.upper()
                value = far_symbols.get(symbol)
                if value is None:
                    continue
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
