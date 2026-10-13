#!/usr/bin/env python3
"""Generate profile-owned SNES lookup tables for cooked SCUMM room records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import struct

from same.engines.scumm_v5.cooked_room import HEADER, decode_cooked_room
from same.engines.scumm_v5.native_residency import (
    NativeProgramDirectory, canonical_unit_identity, directory_assembly,
)
from same.engines.scumm_v5.program_storage import (
    build_program_storage, read_package_prefix_sections,
)
from same.engines.scumm_v5.live_room_resources import encode_live_room
from same.engines.scumm_v5.room_visual import decode_room_visual
from same.engines.scumm_v5.room import decode_room


KIND = {"ENCD": 1, "EXCD": 2, "LSCR": 3}

PRIMARY_PROGRAM_IDS = tuple(range(0xD0, 0x100))
OVERFLOW_PROGRAM_IDS = tuple(range(0xCF, 0x4D, -1))


def cpu_visible_rom_bank(bank: int, *, sa1_aliases: bool) -> int:
    """Return the S-CPU bank window that exposes a generated LoROM bank."""
    if bank < 0:
        raise ValueError(f"logical ROM page cannot be negative: {bank}")
    if sa1_aliases and 0x40 <= bank <= 0x4F:
        return bank + 0x40
    # In LoROM, physical banks $7E/$7F are visible only through their upper
    # mirrors.  The low-bank CPU windows are WRAM, not cartridge ROM.
    if bank in (0x7E, 0x7F):
        return bank + 0x80
    return bank


def occupied_generated_bank_origins(lines: list[str]) -> set[tuple[int, int]]:
    """Find payload-bearing generated sections, ignoring empty reservations."""
    result: set[tuple[int, int]] = set()
    bank = origin = None
    payload = False
    def finish() -> None:
        if payload and bank is not None and origin is not None:
            result.add((bank, origin))
    for line in lines:
        text = line.strip()
        match = re.fullmatch(r"\.bank\s+(\d+)", text)
        if match:
            finish(); bank = int(match.group(1)); origin = None; payload = False; continue
        match = re.fullmatch(r"\.org\s+\$([0-9A-Fa-f]+)", text)
        if match:
            finish(); origin = int(match.group(1), 16); payload = False; continue
        if not text or text.startswith(";") or text.endswith(":") or " = " in text:
            continue
        if text.startswith(".") and not re.match(r"\.(?:byte|word|long|incbin|db|dw|dl|ds|fill)\b", text, re.I):
            continue
        if bank is not None and origin is not None:
            payload = True
    finish()
    return result


def validate_generated_bank_origins(lines: list[str], *, allow_out_of_range: bool = False) -> None:
    """Reject duplicate origins; only report-only mode may retain high pages."""
    seen: dict[tuple[int, int], str] = {}
    bank = origin = None
    payload = False
    labels: list[str] = []
    def finish() -> None:
        nonlocal labels
        if not payload or bank is None or origin is None:
            return
        identity = ", ".join(labels[:4]) or "<unlabeled section>"
        if bank > 0x7F and not allow_out_of_range:
            raise RuntimeError(
                f"generated ROM payload uses logical LoROM page {bank}, outside the "
                f"supported 4 MiB mapping; CPU bank mirrors cannot extend storage; section={identity}"
            )
        key = bank, origin
        if key in seen:
            raise RuntimeError(
                f"generated ROM sections overlap at bank {bank}, origin ${origin:04X}: "
                f"{seen[key]} vs {identity}"
            )
        seen[key] = identity
        labels = []
    for line in lines:
        text = line.strip()
        match = re.fullmatch(r"\.bank\s+(\d+)", text)
        if match:
            finish(); bank = int(match.group(1)); origin = None; payload = False; labels = []; continue
        match = re.fullmatch(r"\.org\s+\$([0-9A-Fa-f]+)", text)
        if match:
            finish(); origin = int(match.group(1), 16); payload = False; labels = []; continue
        if not text or text.startswith(";") or " = " in text:
            continue
        if text.endswith(":"):
            if bank is not None and origin is not None: labels.append(text[:-1])
            continue
        if text.startswith(".") and not re.match(r"\.(?:byte|word|long|incbin|db|dw|dl|ds|fill)\b", text, re.I):
            continue
        if bank is not None and origin is not None:
            payload = True
    finish()


def generated_bank_section_census(lines: list[str]) -> list[dict[str, object]]:
    """Describe generated section starts without pretending text is machine size."""
    sections: list[dict[str, object]] = []
    bank: int | None = None
    origin: int | None = None
    start_line = 0
    labels: list[str] = []
    line_count = 0
    data_directive_bytes = 0

    def finish() -> None:
        if bank is None or origin is None or (not labels and not line_count):
            return
        sections.append({
            "logical_storage_page": bank,
            "origin": origin,
            "source_line_start": start_line,
            "source_line_count": line_count,
            "labels": labels[:8],
            "declared_data_bytes_lower_bound": data_directive_bytes,
            "machine_code_size": None,
            "machine_code_size_status": "REQUIRES_ASSEMBLER_MAP",
        })

    for line_number, line in enumerate(lines, 1):
        text = line.strip()
        match = re.fullmatch(r"\.bank\s+(\d+)", text)
        if match:
            finish()
            bank = int(match.group(1)); origin = None; start_line = line_number
            labels = []; line_count = 0; data_directive_bytes = 0
            continue
        match = re.fullmatch(r"\.org\s+\$([0-9A-Fa-f]+)", text)
        if match:
            finish()
            origin = int(match.group(1), 16); start_line = line_number
            labels = []; line_count = 0; data_directive_bytes = 0
            continue
        if not text or text.startswith(";") or " = " in text:
            continue
        if bank is None or origin is None:
            continue
        if text.endswith(":"):
            labels.append(text[:-1]); line_count += 1
            continue
        line_count += 1
        directive = re.match(r"\.(byte|word|long|db|dw|dl)\s+(.+)$", text, re.I)
        if directive:
            width = {"byte": 1, "db": 1, "word": 2, "dw": 2,
                     "long": 3, "dl": 3}[directive.group(1).lower()]
            data_directive_bytes += width * len(directive.group(2).split(","))
        elif text.lower().startswith(".incbin"):
            # The exact length is separately represented by the binary segment ledger.
            line_count += 0
    finish()
    return sections


def cpu_visible_rom_symbol(bank: int, symbol: str, *, sa1_aliases: bool) -> str:
    """Return a CPU-visible long address for a symbol in a generated LoROM bank."""
    visible_bank = cpu_visible_rom_bank(bank, sa1_aliases=sa1_aliases)
    return f"${visible_bank:02X}0000+{symbol}"


def cpu_visible_rom_address(bank: int, offset: int, *, sa1_aliases: bool) -> str:
    if not 0 <= offset < 0x8000:
        raise ValueError(f"LoROM page offset outside $8000 window: {offset}")
    visible_bank = cpu_visible_rom_bank(bank, sa1_aliases=sa1_aliases)
    return f"${visible_bank:02X}{0x8000 + offset:04X}"


def reserved_program_ids() -> set[int]:
    """Reserve every built-in personality, not just the active build."""
    from generate_engine_fixtures import poppy_fixture_include, scumm_c2_fixtures
    text = poppy_fixture_include(b"", scumm_c2_fixtures())
    return {0} | {
        int(value, 16)
        for name, value in re.findall(r"(SCUMM_C2_FIXTURE_\w+) = \$([0-9A-F]+)", text)
        if name != "SCUMM_C2_FIXTURE_COUNT"
    }


class ProgramIdAllocator:
    """Keep historical IDs first; overflow uses a separately checked pool."""

    def __init__(self, *, pool=None, reserved=None, dynamic=False):
        self.dynamic = dynamic
        self.pool = tuple(PRIMARY_PROGRAM_IDS + OVERFLOW_PROGRAM_IDS if pool is None else pool)
        reserved = reserved_program_ids() if reserved is None else set(reserved)
        if len(set(self.pool)) != len(self.pool):
            raise RuntimeError("duplicate generated program ID in allocation pool")
        if any(not isinstance(value, int) or not 0 <= value <= 0xFF for value in self.pool):
            raise RuntimeError("generated program ID is not an unsigned byte")
        if set(self.pool) & reserved:
            raise RuntimeError("generated program pool collides with reserved selector")
        self.index = 0

    def allocate(self) -> int:
        if self.dynamic:
            if self.index >= 0xFFFF:
                raise RuntimeError("canonical ProgramUnit ID space exhausted")
            value = self.index
            self.index += 1
            return value
        if self.index == len(self.pool):
            raise RuntimeError("cooked script program-id space exhausted")
        value = self.pool[self.index]
        self.index += 1
        return value


def rows(data: bytes, indent: str = "    ") -> str:
    return "\n".join(
        indent + ".byte " + ",".join(f"${value:02X}" for value in data[index:index + 16])
        for index in range(0, len(data), 16)
    )


def word_rows(values: list[int], indent: str = "    ") -> str:
    return "\n".join(
        indent + ".word " + ",".join(f"${value & 0xFFFF:04X}" for value in values[index:index + 8])
        for index in range(0, len(values), 8)
    )


def program_label_id(value: int, *, dynamic: bool) -> str:
    return f"{value:04X}" if dynamic else f"{value:02X}"


def portal_table(room) -> bytes:
    """Cook every BOXD shared-edge portal; BOXM still selects route topology."""
    output = bytearray()
    for source in room.walkboxes:
        for target in room.walkboxes:
            portal: tuple[int, int, int, int] | None = None
            first, second = source.points, target.points
            for edge_a in range(4):
                a0, a1 = first[edge_a], first[(edge_a + 1) & 3]
                for edge_b in range(4):
                    b0, b1 = second[edge_b], second[(edge_b + 1) & 3]
                    if a0[0] == a1[0] == b0[0] == b1[0]:
                        a_low, a_high = sorted((a0[1], a1[1]))
                        b_low, b_high = sorted((b0[1], b1[1]))
                        touching = ((a_high == b_low or b_high == a_low)
                                    and a_low != a_high and b_low != b_high)
                        if not (a_low > b_high or b_low > a_high or touching):
                            portal = (1, a0[0], max(a_low, b_low), min(a_high, b_high))
                            break
                    if a0[1] == a1[1] == b0[1] == b1[1]:
                        a_low, a_high = sorted((a0[0], a1[0]))
                        b_low, b_high = sorted((b0[0], b1[0]))
                        touching = ((a_high == b_low or b_high == a_low)
                                    and a_low != a_high and b_low != b_high)
                        if not (a_low > b_high or b_low > a_high or touching):
                            portal = (2, a0[1], max(a_low, b_low), min(a_high, b_high))
                            break
                if portal is not None:
                    break
            output.extend(struct.pack("<Bhhh", *(portal or (0, 0, 0, 0))))
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-output", type=Path, required=True)
    parser.add_argument(
        "--far-validator-output",
        type=Path,
        help="emit the cold cooked-record validator separately for a far ROM bank",
    )
    parser.add_argument("--long-object-fail-branch", action="store_true")
    parser.add_argument("--binary-dir", type=Path, required=True)
    parser.add_argument(
        "--relative-binary-paths", action="store_true",
        help="emit .incbin paths relative to the generated room include's directory",
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--first-bank", type=int, default=3)
    parser.add_argument(
        "--reserved-bank", type=int, action="append", default=[],
        help="LoROM bank unavailable to generated room data/code",
    )
    parser.add_argument(
        "--sa1-rom-bank-aliases", action="store_true",
        help="read generated payloads in banks $40-$4F through their $80-$8F SA-1 ROM windows",
    )
    parser.add_argument("--entry-only-room", type=int, action="append", default=[])
    parser.add_argument(
        "--executable-local-script-room", action="append", type=int,
        default=[], metavar="ROOM",
        help="keep all local scripts executable while omitting dormant room objects",
    )
    parser.add_argument("--entry-exit-room", type=int, action="append", default=[])
    parser.add_argument("--executable-local", action="append", default=[], metavar="ROOM:SCRIPT")
    parser.add_argument(
        "--append-global-script", type=int, action="append", default=[],
        help="allocate selected manifest globals after all previously ordered programs",
    )
    parser.add_argument(
        "--append-late-global-script", type=int, action="append", default=[],
        help="allocate selected manifest globals after appended local programs",
    )
    parser.add_argument(
        "--append-final-global-script", type=int, action="append", default=[],
        help="allocate selected manifest globals after every established executable identity",
    )
    parser.add_argument(
        "--append-terminal-global-script", type=int, action="append", default=[],
        help="allocate selected manifest globals after terminal room/local programs",
    )
    parser.add_argument(
        "--append-post-terminal-global-script", type=int, action="append", default=[],
        help="allocate selected manifest globals after terminal local/object programs",
    )
    parser.add_argument(
        "--append-last-global-script", type=int, action="append", default=[],
        help="allocate selected manifest globals after every other executable selection",
    )
    parser.add_argument(
        "--append-executable-local", action="append", default=[], metavar="ROOM:SCRIPT",
        help="allocate selected local scripts after ordinary programs and appended globals",
    )
    parser.add_argument(
        "--append-late-executable-local", action="append", default=[], metavar="ROOM:SCRIPT",
        help="allocate selected local scripts after late-appended globals",
    )
    parser.add_argument(
        "--append-final-executable-local", action="append", default=[], metavar="ROOM:SCRIPT",
        help="allocate selected local scripts after every established executable identity",
    )
    parser.add_argument(
        "--append-terminal-executable-local", action="append", default=[], metavar="ROOM:SCRIPT",
        help="allocate selected local scripts after all other executable selections",
    )
    parser.add_argument(
        "--append-post-terminal-executable-local", action="append", default=[], metavar="ROOM:SCRIPT",
        help="allocate selected local scripts after terminal global selections",
    )
    parser.add_argument(
        "--append-last-executable-local", action="append", default=[], metavar="ROOM:SCRIPT",
        help="allocate selected local scripts after every other executable selection",
    )
    parser.add_argument(
        "--append-ultimate-executable-local", action="append", default=[], metavar="ROOM:SCRIPT",
        help="allocate selected local scripts after every other appended program identity",
    )
    parser.add_argument(
        "--append-late-room-entry-exit", action="append", type=int, default=[], metavar="ROOM",
        help="allocate a room's ENCD/EXCD after previously selected executable identities",
    )
    parser.add_argument(
        "--append-room-entry-exit", action="append", type=int, default=[], metavar="ROOM",
        help=("allocate a room's ENCD/EXCD after ordinary room programs but before "
              "appended globals"),
    )
    parser.add_argument(
        "--append-terminal-room-entry-exit", action="append", type=int, default=[], metavar="ROOM",
        help="allocate a room's ENCD/EXCD after all established executable identities",
    )
    parser.add_argument(
        "--append-last-room-entry-exit", action="append", type=int, default=[], metavar="ROOM",
        help="allocate a room's ENCD/EXCD after every established executable identity",
    )
    parser.add_argument(
        "--executable-local-object", action="append", default=[],
        metavar="ROOM:OBJECT",
        help="make one OBCD descriptor in an entry-only room executable",
    )
    parser.add_argument(
        "--append-executable-local-object", action="append", default=[],
        metavar="ROOM:OBJECT",
        help="append one OBCD descriptor after all previously selected programs",
    )
    parser.add_argument(
        "--append-terminal-executable-local-object", action="append", default=[],
        metavar="ROOM:OBJECT",
        help="append one OBCD descriptor after every established executable identity",
    )
    parser.add_argument(
        "--append-last-executable-local-object", action="append", default=[],
        metavar="ROOM:OBJECT",
        help="append one OBCD descriptor after every other executable selection",
    )
    parser.add_argument(
        "--executable-local-room",
        action="append",
        type=int,
        default=[],
        metavar="ROOM",
        help="make every LSCR descriptor in ROOM executable and resolvable",
    )
    parser.add_argument(
        "--scenario-class-overlay", action="append", default=[], metavar="OBJECT:MASK",
        help="fixture-only OR mask applied after source DOBJ loading",
    )
    parser.add_argument(
        "--scenario-bit-overlay", action="append", default=[], metavar="BIT",
        help="fixture-only set of source-justified bit variables",
    )
    parser.add_argument(
        "--scenario-state-overlay", action="append", default=[], metavar="OBJECT:STATE",
        help="fixture-only source-justified object state at a sentence boundary",
    )
    parser.add_argument(
        "--far-programs",
        action="store_true",
        help="place executable script bytes with profile data instead of bank-0 lookup code",
    )
    parser.add_argument("--layout-only", action="store_true",
                        help="emit source directories and placement reports without assembly includes")
    parser.add_argument("--share-room-program-bodies", action="store_true",
                        help=("for whole-source layouts, point room scripts/object carriers at their "
                              "identical bytes in the complete cooked ROOM record when page-safe"))
    parser.add_argument("--share-room-directory-prefixes", action="store_true",
                        help=("for whole-source layouts, alias room integrity prefixes into their "
                              "complete cooked ROOM record when page-safe"))
    parser.add_argument(
        "--dynamic-program-residency", action="store_true",
        help="emit canonical ProgramUnit directories for the experimental native resolver",
    )
    parser.add_argument(
        "--msu1-program-storage-dir", type=Path,
        help="pack generated canonical ProgramUnit bodies into one SAMEPKG SC5CODE section",
    )
    parser.add_argument(
        "--msu1-program-prefix-package", type=Path,
        help="validated SAMEPKG v1 source for optional sections placed before SC5CODE",
    )
    parser.add_argument(
        "--msu1-program-prefix-section", action="append", default=[],
        metavar="SECTION",
        help="copy this validated source-package section before SC5CODE (repeatable)",
    )
    parser.add_argument(
        "--msu1-program-prefix-all-sections", action="store_true",
        help="copy all validated sections from the supplied SAMEPKG before SC5CODE",
    )
    parser.add_argument("--msu1-program-directory-include", type=Path)
    parser.add_argument("--msu1-program-directory-bank", type=int, default=10)
    parser.add_argument(
        "--msu1-program-page-directory-bank", type=int,
        help="ROM bank for compiler-proven bytecode page index/CRC records",
    )
    parser.add_argument("--msu1-program-cache-bytes", type=lambda value: int(value, 0), default=0x0800)
    parser.add_argument(
        "--msu1-live-room-resources", action="store_true",
        help="package compiler-owned room tables and visuals for live MSU consumers",
    )
    parser.add_argument(
        "--msu1-include-source-room-records", action="store_true",
        help=("retain complete cooked SC5ROOM records in SAMEPKG as package-only "
              "source resources; this does not make oversized records natively loadable"),
    )
    parser.add_argument(
        "--pack-source-tables", action="store_true",
        help="pack generated per-room metadata tables into bank-bounded pages",
    )
    parser.add_argument(
        "--banked-room-directory-data", action="store_true",
        help="place dynamic room/global directory arrays in generated ROM data banks",
    )
    parser.add_argument("--native-directory-output", type=Path)
    parser.add_argument("--native-directory-include", type=Path)
    parser.add_argument(
        "--backend-directory-output", type=Path,
        help="emit canonical ProgramUnit IDs with actual code bank/offset descriptors",
    )
    args = parser.parse_args()
    if args.dynamic_program_residency and not args.far_programs:
        parser.error("--dynamic-program-residency requires --far-programs")
    if args.msu1_program_storage_dir and not args.dynamic_program_residency:
        parser.error("--msu1-program-storage-dir requires --dynamic-program-residency")
    if args.msu1_program_storage_dir and not args.msu1_program_directory_include:
        parser.error("MSU ProgramUnit storage requires --msu1-program-directory-include")
    if args.msu1_live_room_resources and not args.msu1_program_storage_dir:
        parser.error("--msu1-live-room-resources requires --msu1-program-storage-dir")
    if args.msu1_include_source_room_records and not args.msu1_live_room_resources:
        parser.error("--msu1-include-source-room-records requires live-room package mode")
    if args.msu1_program_prefix_all_sections and args.msu1_program_prefix_section:
        parser.error("choose either --msu1-program-prefix-all-sections or named prefix sections")
    prefix_requested = bool(args.msu1_program_prefix_all_sections or args.msu1_program_prefix_section)
    if bool(args.msu1_program_prefix_package) != prefix_requested:
        parser.error("MSU prefix sections require both --msu1-program-prefix-package and a prefix selection")
    if args.msu1_program_prefix_section and not args.msu1_program_storage_dir:
        parser.error("MSU prefix sections require --msu1-program-storage-dir")
    if args.msu1_program_storage_dir and (
        not 0 <= args.msu1_program_directory_bank <= 0xFF
        or not 0 < args.msu1_program_cache_bytes <= 0x800
    ):
        parser.error("MSU ProgramUnit bank/cache size is outside the native ABI")
    if args.msu1_program_storage_dir and (
        args.share_room_program_bodies or args.share_room_directory_prefixes
    ):
        parser.error("MSU ProgramUnit storage cannot be combined with ROM program-body aliases")
    if args.share_room_program_bodies and not args.far_programs:
        parser.error("--share-room-program-bodies requires --far-programs")
    if args.share_room_directory_prefixes and not args.far_programs:
        parser.error("--share-room-directory-prefixes requires --far-programs")
    if args.banked_room_directory_data and not args.dynamic_program_residency:
        parser.error("--banked-room-directory-data requires --dynamic-program-residency")
    if args.banked_room_directory_data and not args.pack_source_tables:
        parser.error("--banked-room-directory-data requires --pack-source-tables")
    for output_path in (
        args.output, args.data_output, args.report, args.native_directory_output,
        args.native_directory_include, args.backend_directory_output,
        args.far_validator_output, args.msu1_program_directory_include,
    ):
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
    global_append_phases = (
        args.append_global_script,
        args.append_late_global_script,
        args.append_final_global_script,
        args.append_terminal_global_script,
        args.append_post_terminal_global_script,
        args.append_last_global_script,
    )
    for phase in global_append_phases:
        if len(set(phase)) != len(phase):
            raise RuntimeError("duplicate appended global-script selection")
    for left_index, left in enumerate(global_append_phases):
        for right in global_append_phases[left_index + 1:]:
            if set(left) & set(right):
                raise RuntimeError("global script selected for multiple append phases")
    scenario_class_overlays = []
    for raw in args.scenario_class_overlay:
        object_text, separator, mask_text = raw.partition(":")
        if not separator:
            parser.error(f"invalid --scenario-class-overlay {raw!r}; expected OBJECT:MASK")
        try:
            object_id, mask = int(object_text, 0), int(mask_text, 0)
        except ValueError:
            parser.error(f"invalid --scenario-class-overlay {raw!r}; expected numeric OBJECT:MASK")
        if not 0 <= object_id < 0x10000 or not 0 <= mask < 0x100000000:
            parser.error(f"out-of-range --scenario-class-overlay {raw!r}")
        scenario_class_overlays.append((object_id, mask))
    scenario_bit_overlays = []
    for raw in args.scenario_bit_overlay:
        try:
            bit = int(raw, 0)
        except ValueError:
            parser.error(f"invalid --scenario-bit-overlay {raw!r}; expected numeric bit")
        if not 0 <= bit < 4096:
            parser.error(f"out-of-range --scenario-bit-overlay {raw!r}")
        scenario_bit_overlays.append(bit)
    scenario_state_overlays = []
    for raw in args.scenario_state_overlay:
        object_text, separator, state_text = raw.partition(":")
        if not separator:
            parser.error(f"invalid --scenario-state-overlay {raw!r}; expected OBJECT:STATE")
        try:
            object_id, state = int(object_text, 0), int(state_text, 0)
        except ValueError:
            parser.error(f"invalid --scenario-state-overlay {raw!r}; expected numeric OBJECT:STATE")
        if not 0 <= object_id < 0x10000 or not 0 <= state <= 0xFF:
            parser.error(f"out-of-range --scenario-state-overlay {raw!r}")
        scenario_state_overlays.append((object_id, state))
    executable_locals = {
        tuple(int(value) for value in item.split(":")) for item in args.executable_local
    }
    if any(len(item) != 2 for item in executable_locals):
        raise RuntimeError("--executable-local requires ROOM:SCRIPT")
    append_executable_locals = []
    for raw in args.append_executable_local:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError("--append-executable-local requires ROOM:SCRIPT")
        item = tuple(int(value) for value in parts)
        if item in append_executable_locals:
            raise RuntimeError(f"duplicate appended executable local {item[0]}:{item[1]}")
        if item in executable_locals:
            raise RuntimeError(
                f"local script selected as both ordinary and appended: {item[0]}:{item[1]}"
            )
        append_executable_locals.append(item)
    append_late_executable_locals = []
    for raw in args.append_late_executable_local:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError("--append-late-executable-local requires ROOM:SCRIPT")
        item = tuple(int(value) for value in parts)
        if item in append_late_executable_locals:
            raise RuntimeError(f"duplicate late-appended executable local {item[0]}:{item[1]}")
        if item in append_executable_locals or item in executable_locals:
            raise RuntimeError(
                f"local script selected more than once: {item[0]}:{item[1]}"
            )
        append_late_executable_locals.append(item)
    append_final_executable_locals = []
    for raw in args.append_final_executable_local:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError("--append-final-executable-local requires ROOM:SCRIPT")
        item = tuple(int(value) for value in parts)
        if item in append_final_executable_locals:
            raise RuntimeError(f"duplicate final-appended executable local {item[0]}:{item[1]}")
        if item in executable_locals or item in append_executable_locals or item in append_late_executable_locals:
            raise RuntimeError(f"local script selected more than once: {item[0]}:{item[1]}")
        append_final_executable_locals.append(item)
    append_terminal_executable_locals = []
    for raw in args.append_terminal_executable_local:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError("--append-terminal-executable-local requires ROOM:SCRIPT")
        item = tuple(int(value) for value in parts)
        if item in append_terminal_executable_locals:
            raise RuntimeError(f"duplicate terminal-appended executable local {item[0]}:{item[1]}")
        if item in executable_locals or item in append_executable_locals or item in append_late_executable_locals or item in append_final_executable_locals:
            raise RuntimeError(f"local script selected more than once: {item[0]}:{item[1]}")
        append_terminal_executable_locals.append(item)
    append_post_terminal_executable_locals = []
    for raw in args.append_post_terminal_executable_local:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError(
                "--append-post-terminal-executable-local requires ROOM:SCRIPT"
            )
        item = tuple(int(value) for value in parts)
        if item in append_post_terminal_executable_locals:
            raise RuntimeError(
                f"duplicate post-terminal executable local {item[0]}:{item[1]}"
            )
        if (item in executable_locals or item in append_executable_locals
                or item in append_late_executable_locals
                or item in append_final_executable_locals
                or item in append_terminal_executable_locals):
            raise RuntimeError(f"local script selected more than once: {item[0]}:{item[1]}")
        append_post_terminal_executable_locals.append(item)
    append_last_executable_locals = []
    for raw in args.append_last_executable_local:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError("--append-last-executable-local requires ROOM:SCRIPT")
        item = tuple(int(value) for value in parts)
        if item in append_last_executable_locals:
            raise RuntimeError(f"duplicate last-appended executable local {item[0]}:{item[1]}")
        if (item in executable_locals or item in append_executable_locals
                or item in append_late_executable_locals
                or item in append_final_executable_locals
                or item in append_terminal_executable_locals
                or item in append_post_terminal_executable_locals):
            raise RuntimeError(f"local script selected more than once: {item[0]}:{item[1]}")
        append_last_executable_locals.append(item)
    append_ultimate_executable_locals = []
    for raw in args.append_ultimate_executable_local:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError(
                "--append-ultimate-executable-local requires ROOM:SCRIPT"
            )
        item = tuple(int(value) for value in parts)
        if item in append_ultimate_executable_locals:
            raise RuntimeError(
                f"duplicate ultimate-appended executable local {item[0]}:{item[1]}"
            )
        if (item in executable_locals or item in append_executable_locals
                or item in append_late_executable_locals
                or item in append_final_executable_locals
                or item in append_terminal_executable_locals
                or item in append_post_terminal_executable_locals
                or item in append_last_executable_locals):
            raise RuntimeError(f"local script selected more than once: {item[0]}:{item[1]}")
        append_ultimate_executable_locals.append(item)
    if set(append_executable_locals) & set(append_late_executable_locals):
        raise RuntimeError("local script selected as both appended and late-appended")
    if len(set(args.append_late_room_entry_exit)) != len(args.append_late_room_entry_exit):
        raise RuntimeError("duplicate late-appended room entry/exit selection")
    if len(set(args.append_terminal_room_entry_exit)) != len(args.append_terminal_room_entry_exit):
        raise RuntimeError("duplicate terminal-appended room entry/exit selection")
    if len(set(args.append_last_room_entry_exit)) != len(args.append_last_room_entry_exit):
        raise RuntimeError("duplicate last-appended room entry/exit selection")
    if len(set(args.append_room_entry_exit)) != len(args.append_room_entry_exit):
        raise RuntimeError("duplicate appended room entry/exit selection")
    if (set(args.append_room_entry_exit) & set(args.append_late_room_entry_exit)
            or set(args.append_room_entry_exit) & set(args.append_terminal_room_entry_exit)
            or set(args.append_late_room_entry_exit) & set(args.append_terminal_room_entry_exit)):
        raise RuntimeError("room entry/exit selected for multiple append phases")
    room_append_phases = (set(args.append_room_entry_exit),
                          set(args.append_late_room_entry_exit),
                          set(args.append_terminal_room_entry_exit),
                          set(args.append_last_room_entry_exit))
    if any(left & right for index, left in enumerate(room_append_phases)
           for right in room_append_phases[index + 1:]):
        raise RuntimeError("room entry/exit selected for multiple append phases")
    executable_local_objects = {
        tuple(int(value) for value in item.split(":"))
        for item in args.executable_local_object
    }
    if any(len(item) != 2 for item in executable_local_objects):
        raise RuntimeError("--executable-local-object requires ROOM:OBJECT")
    append_executable_local_objects = []
    for raw in args.append_executable_local_object:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError("--append-executable-local-object requires ROOM:OBJECT")
        item = tuple(int(value) for value in parts)
        if item in append_executable_local_objects:
            raise RuntimeError(f"duplicate appended executable local object {item[0]}:{item[1]}")
        if item in executable_local_objects:
            raise RuntimeError(
                f"object selected as both ordinary and appended: {item[0]}:{item[1]}"
            )
        append_executable_local_objects.append(item)
    append_terminal_executable_local_objects = []
    for raw in args.append_terminal_executable_local_object:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError(
                "--append-terminal-executable-local-object requires ROOM:OBJECT"
            )
        item = tuple(int(value) for value in parts)
        if item in append_terminal_executable_local_objects:
            raise RuntimeError(
                f"duplicate terminal-appended executable local object {item[0]}:{item[1]}"
            )
        if item in executable_local_objects or item in append_executable_local_objects:
            raise RuntimeError(
                f"object selected more than once: {item[0]}:{item[1]}"
            )
        append_terminal_executable_local_objects.append(item)
    append_last_executable_local_objects = []
    for raw in args.append_last_executable_local_object:
        parts = raw.split(":")
        if len(parts) != 2:
            raise RuntimeError("--append-last-executable-local-object requires ROOM:OBJECT")
        item = tuple(int(value) for value in parts)
        if item in append_last_executable_local_objects:
            raise RuntimeError(f"duplicate last-appended executable local object {item[0]}:{item[1]}")
        if (item in executable_local_objects or item in append_executable_local_objects
                or item in append_terminal_executable_local_objects):
            raise RuntimeError(f"object selected more than once: {item[0]}:{item[1]}")
        append_last_executable_local_objects.append(item)
    args.binary_dir.mkdir(parents=True, exist_ok=True)
    ownership_path = args.binary_dir / ".same-generated-segments.json"
    existing_names = {path.name for path in args.binary_dir.iterdir()}
    if existing_names:
        if ownership_path.name not in existing_names:
            raise RuntimeError(
                f"binary directory contains unowned/stale files: {args.binary_dir}; "
                "use a fresh directory or preserve only manifest-owned segments"
            )
        ownership = json.loads(ownership_path.read_text(encoding="utf-8"))
        owned = ownership.get("files")
        if not isinstance(owned, list):
            raise RuntimeError(f"invalid segment ownership manifest: {ownership_path}")
        expected = {str(row["path"]) for row in owned} | {ownership_path.name}
        if existing_names != expected:
            raise RuntimeError(f"binary directory contains files outside its manifest: {args.binary_dir}")
        for row in owned:
            name = str(row["path"])
            if Path(name).name != name:
                raise RuntimeError(f"unsafe owned segment path: {name}")
            path = args.binary_dir / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row.get("sha256"):
                raise RuntimeError(f"owned segment changed since its manifest: {path}")
        for row in owned:
            (args.binary_dir / str(row["path"])).unlink()
        ownership_path.unlink()
    written_segments: list[dict[str, object]] = []
    records = []
    programs = []
    global_scripts = []
    deferred_global_scripts = []
    deferred_local_scripts = []
    deferred_object_programs = []
    late_deferred_room_entry_exit_scripts = []
    terminal_deferred_room_entry_exit_scripts = []
    last_deferred_room_entry_exit_scripts = []
    global_states: bytes | None = None
    global_owners: bytes | None = None
    global_classes: tuple[int, ...] | None = None
    num_global_scripts: int | None = None
    hold_after_started_global_script: int | None = None
    actor_facings: tuple[int, ...] | None = None
    actor_positions: tuple[tuple[int, int], ...] | None = None
    actor_walkboxes: tuple[int, ...] | None = None
    program_ids = ProgramIdAllocator(dynamic=args.dynamic_program_residency)
    for manifest_path in args.manifest:
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("schema") != "same_scumm_v5_cooked_rooms_v1":
            raise RuntimeError(f"{manifest_path}: cooked-room schema differs")
        manifest_global_scripts = manifest.get("num_global_scripts")
        if (
            isinstance(manifest_global_scripts, bool)
            or not isinstance(manifest_global_scripts, int)
            or not 0 <= manifest_global_scripts <= 256
        ):
            raise RuntimeError(f"{manifest_path}: num_global_scripts must be in 0..256")
        if num_global_scripts is not None and manifest_global_scripts != num_global_scripts:
            raise RuntimeError("cooked-room manifests disagree on num_global_scripts")
        num_global_scripts = manifest_global_scripts
        gate = manifest.get("execution_gate")
        if gate is not None:
            value = gate.get("hold_after_started_global_script") if isinstance(gate, dict) else None
            if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < manifest_global_scripts:
                raise RuntimeError(f"{manifest_path}: execution gate is malformed")
            if (hold_after_started_global_script is not None
                    and hold_after_started_global_script != value):
                raise RuntimeError("cooked-room manifests disagree on execution gate")
            hold_after_started_global_script = value
        global_spec = manifest.get("global_objects")
        if global_spec is not None:
            source_states = (manifest_path.parent / global_spec["states_output"]).read_bytes()
            # Neutral interaction fixtures begin from a zero mutable table.
            # A controlled source-root manifest may opt into source DOBJ
            # states when room-entry bytecode consumes them before the first
            # semantic sentence boundary (for example actor placement gates).
            candidate = (source_states if manifest.get("source_initial_states")
                         else bytes(len(source_states)))
            if len(candidate) != int(global_spec["count"]):
                raise RuntimeError(f"{manifest_path}: global-object state count differs")
            # A source-root manifest may establish the canonical initial
            # table; companion room manifests retain the neutral legacy
            # declaration and must not erase or contradict that table.
            if (global_states is not None and candidate != global_states
                    and any(global_states)
                    and any(candidate)):
                raise RuntimeError("cooked-room manifests disagree on global-object state")
            if global_states is None or any(candidate):
                global_states = candidate
            source_owners = (manifest_path.parent / global_spec["owners_output"]).read_bytes()
            if len(source_owners) != int(global_spec["count"]):
                raise RuntimeError(f"{manifest_path}: global-object owner count differs")
            if global_owners is not None and source_owners != global_owners:
                raise RuntimeError("cooked-room manifests disagree on global-object owners")
            global_owners = bytes(source_owners)
            classes_name = global_spec.get("classes_output")
            if classes_name is not None:
                source_classes = (manifest_path.parent / classes_name).read_bytes()
                if len(source_classes) != int(global_spec["count"]) * 4:
                    raise RuntimeError(f"{manifest_path}: global-object class count differs")
                candidate_classes = tuple(
                    int.from_bytes(source_classes[index:index + 4], "little")
                    for index in range(0, len(source_classes), 4)
                )
                if global_classes is not None and candidate_classes != global_classes:
                    raise RuntimeError("cooked-room manifests disagree on global-object classes")
                global_classes = candidate_classes
        manifest_facings = manifest.get("actor_facings")
        if manifest_facings is not None:
            candidate_facings = tuple(int(value) for value in manifest_facings)
            if len(candidate_facings) != 32 or any(
                not 0 <= value <= 0xFFFF for value in candidate_facings
            ):
                raise RuntimeError(f"{manifest_path}: actor_facings must contain 32 u16 values")
            if actor_facings is not None and candidate_facings != actor_facings:
                raise RuntimeError("cooked-room manifests disagree on actor facings")
            actor_facings = candidate_facings
        manifest_positions = manifest.get("actor_positions")
        if manifest_positions is not None:
            candidate_positions = tuple(
                (int(item[0]), int(item[1])) for item in manifest_positions
            )
            if len(candidate_positions) != 32 or any(
                not -0x8000 <= value <= 0x7FFF
                for point in candidate_positions for value in point
            ):
                raise RuntimeError(f"{manifest_path}: actor_positions must contain 32 s16 pairs")
            if actor_positions is not None and candidate_positions != actor_positions:
                raise RuntimeError("cooked-room manifests disagree on actor positions")
            actor_positions = candidate_positions
        manifest_walkboxes = manifest.get("actor_walkboxes")
        if manifest_walkboxes is not None:
            candidate_walkboxes = tuple(int(value) for value in manifest_walkboxes)
            if len(candidate_walkboxes) != 32 or any(
                not 0 <= value <= 0xFF for value in candidate_walkboxes
            ):
                raise RuntimeError(f"{manifest_path}: actor_walkboxes must contain 32 u8 values")
            if actor_walkboxes is not None and candidate_walkboxes != actor_walkboxes:
                raise RuntimeError("cooked-room manifests disagree on actor walkboxes")
            actor_walkboxes = candidate_walkboxes
        manifest_deferred_room_entry_exit_scripts = []
        for source_record in manifest["records"]:
            path = manifest_path.parent / source_record["output"]
            raw = path.read_bytes()
            decoded = decode_cooked_room(raw, expected_room=int(source_record["room"]))
            decoded_room = decode_room(decoded.room_payload, key=f"room.{decoded.room}")
            visual_raw = None
            visual_spec = source_record.get("visual")
            if visual_spec is not None:
                visual_path = manifest_path.parent / str(visual_spec["output"])
                visual_raw = visual_path.read_bytes()
                decoded_visual = decode_room_visual(visual_raw, expected_room=decoded.room)
                if hashlib.sha256(visual_raw).hexdigest() != visual_spec.get("record_sha256"):
                    raise RuntimeError(
                        f"{manifest_path}: room {decoded.room} visual record hash differs"
                    )
            record_index = len(records)
            script_records = []
            source_scripts = {
                str(item["identity"]): item
                for item in source_record.get("scripts", [])
            }
            for script in decoded.scripts:
                executable = (
                    not decoded.registration_only
                    and (
                        decoded.room in args.executable_local_room
                        or decoded.room in args.executable_local_script_room
                        or (decoded.room, script.number) in executable_locals
                        or (decoded.room, script.number) in append_executable_locals
                        or (decoded.room, script.number) in append_late_executable_locals
                        or (decoded.room, script.number) in append_final_executable_locals
                        or (decoded.room, script.number) in append_terminal_executable_locals
                        or (decoded.room, script.number) in append_post_terminal_executable_locals
                        or (decoded.room, script.number) in append_last_executable_locals
                        or (decoded.room, script.number) in append_ultimate_executable_locals
                        or script.kind in {"ENCD", "EXCD"}
                        or decoded.room not in args.entry_only_room
                    )
                )
                # Entry-only rooms retain their source directory metadata but
                # do not consume scarce executable program identities for
                # dormant local scripts.
                if not executable:
                    continue
                item = {
                    "id": None, "record": record_index, "room": decoded.room,
                    "kind": KIND[script.kind], "kind_name": script.kind,
                    "number": script.number, "length": len(script.program),
                    "program": script.program, "identity": script.identity,
                    "source": script,
                    "instruction_spans": source_scripts.get(script.identity, {}).get(
                        "instruction_spans", []
                    ),
                    "opaque_ranges": source_scripts.get(script.identity, {}).get(
                        "opaque_ranges", []
                    ),
                    # Resolvability is distinct from lifecycle scheduling.
                    # Every LSCR in an executable complete room may be started;
                    # ENCD/EXCD selection remains governed by room lifecycle.
                    "executable": executable,
                }
                if (script.kind in {"ENCD", "EXCD"}
                        and decoded.room in args.append_room_entry_exit):
                    manifest_deferred_room_entry_exit_scripts.append(item)
                elif (script.kind in {"ENCD", "EXCD"}
                        and decoded.room in args.append_late_room_entry_exit):
                    late_deferred_room_entry_exit_scripts.append(item)
                elif (script.kind in {"ENCD", "EXCD"}
                        and decoded.room in args.append_terminal_room_entry_exit):
                    terminal_deferred_room_entry_exit_scripts.append(item)
                elif (script.kind in {"ENCD", "EXCD"}
                        and decoded.room in args.append_last_room_entry_exit):
                    last_deferred_room_entry_exit_scripts.append(item)
                elif ((decoded.room, script.number) in append_executable_locals
                        or (decoded.room, script.number) in append_late_executable_locals
                        or (decoded.room, script.number) in append_final_executable_locals
                        or (decoded.room, script.number) in append_terminal_executable_locals
                        or (decoded.room, script.number) in append_post_terminal_executable_locals
                        or (decoded.room, script.number) in append_last_executable_locals
                        or (decoded.room, script.number) in append_ultimate_executable_locals):
                    deferred_local_scripts.append(item)
                else:
                    item["id"] = program_ids.allocate()
                    programs.append(item)
                script_records.append(item)
            source_objects = {
                int(item["object_id"]): item for item in source_record.get("objects", [])
            }
            object_programs = []
            selected_objects_for_room = {
                object_id for room, object_id in executable_local_objects
                if room == decoded.room
            }
            selected_objects_for_room.update(
                object_id for room, object_id in append_executable_local_objects
                if room == decoded.room
            )
            selected_objects_for_room.update(
                object_id for room, object_id in append_terminal_executable_local_objects
                if room == decoded.room
            )
            selected_objects_for_room.update(
                object_id for room, object_id in append_last_executable_local_objects
                if room == decoded.room
            )
            include_objects = (
                not decoded.registration_only
                and (
                    decoded.room in args.executable_local_room
                    or any(
                        (decoded.room, int(item.object_id)) in executable_local_objects
                        for item in decoded_room.objects
                    )
                    or any(
                        (decoded.room, int(item.object_id)) in append_executable_local_objects
                        for item in decoded_room.objects
                    )
                    or any(
                        (decoded.room, int(item.object_id))
                        in append_terminal_executable_local_objects
                        for item in decoded_room.objects
                    )
                    or any(
                        (decoded.room, int(item.object_id))
                        in append_last_executable_local_objects
                        for item in decoded_room.objects
                    )
                    or decoded.room not in args.entry_only_room
                )
            )
            for local_index, item in enumerate(decoded_room.objects, 1):
                selected_object = item.object_id in selected_objects_for_room
                if not include_objects or (
                    decoded.room in args.entry_only_room
                    and selected_objects_for_room
                    and not selected_object
                ):
                    continue
                source = source_objects.get(item.object_id)
                if source is not None:
                    if (
                        int(source["local_object_index"]) != local_index
                        or int(source["obcd_room_offset"]) != item.obcd_room_offset
                        or int(source["obcd_length"]) != len(item.obcd)
                        or source["obcd_sha256"] != hashlib.sha256(item.obcd).hexdigest()
                    ):
                        raise RuntimeError(
                            f"room {decoded.room} object {item.object_id} OBCD provenance differs"
                        )
                program_item = {
                    "id": None, "record": record_index, "room": decoded.room,
                    "kind": 4, "kind_name": "OBCD", "number": item.object_id,
                    "length": len(item.obcd), "program": item.obcd,
                    "identity": f"room.{decoded.room}/object.{item.object_id}/OBCD",
                    "source": source, "executable": (
                        not decoded.registration_only
                        and (not args.dynamic_program_residency or bool(item.verb_entries))
                    ),
                    "instruction_spans": ([] if source is None else
                                           source.get("instruction_spans", [])),
                    "opaque_ranges": ([] if source is None else
                                      source.get("opaque_ranges", [])),
                    "entrypoints": item.verb_entries,
                    "local_object_index": local_index,
                }
                if not program_item["executable"]:
                    # Passive OBCD resource records stay in the room/resource
                    # metadata but never enter the resolver directory.
                    pass
                elif ((decoded.room, item.object_id) in append_executable_local_objects
                        or (decoded.room, item.object_id)
                        in append_terminal_executable_local_objects
                        or (decoded.room, item.object_id)
                        in append_last_executable_local_objects):
                    deferred_object_programs.append(program_item)
                else:
                    program_item["id"] = program_ids.allocate()
                    programs.append(program_item)
                object_programs.append(program_item)
            records.append({
                "room": decoded.room, "flags": decoded.flags, "raw": raw,
                "visual_raw": visual_raw,
                "checksum": decoded.compact_checksum, "scripts": script_records,
                "entry": next((x["id"] for x in script_records if x["kind_name"] == "ENCD"), 0),
                "exit": next((x["id"] for x in script_records if x["kind_name"] == "EXCD"), 0),
                "locals": [x for x in script_records if x["kind_name"] == "LSCR"],
                "executable_locals": [x for x in script_records
                                      if x["kind_name"] == "LSCR" and x["executable"]],
                "object_programs": object_programs,
                "walkbox_flags": bytes(box.flags for box in decoded_room.walkboxes),
                "walkbox_geometry": b"".join(
                    struct.pack(
                        "<hhhhhhhhH", *(value for point in box.points for value in point),
                        box.scale,
                    )
                    for box in decoded_room.walkboxes
                ),
                "box_routes": bytes(
                    0xFF if route is None else route
                    for route_row in decoded_room.box_routes for route in route_row
                ),
                "portals": portal_table(decoded_room),
                "objects": b"".join(
                    struct.pack(
                        "<HhhhhB",
                        item.object_id, item.x, item.y, item.width, item.height,
                        item.flags,
                    )
                    for item in decoded_room.objects
                ),
                # OBNA is the canonical source/runtime object display name.
                # Keep one bounded encoded record per room object; the target
                # loader copies it into the existing SCUMM name cache when the
                # room becomes active.
                "object_names": tuple(
                    (item.object_id, bytes(item.object_name[:32]))
                    for item in decoded_room.objects
                ),
                "object_walk": b"".join(
                    struct.pack(
                        "<HhhBhhB",
                        item.object_id,
                        item.walk_x,
                        item.walk_y,
                        item.actor_direction,
                        *decoded_room.adjust_point(item.walk_x, item.walk_y)[0],
                        decoded_room.adjust_point(item.walk_x, item.walk_y)[1],
                    )
                    for item in decoded_room.objects
                ),
                "verb_entries": tuple(
                    (item["number"], verb, offset)
                    for item in object_programs
                    for verb, offset in item["entrypoints"]
                ),
            })
            local_numbers = [item["number"] for item in script_records if item["kind_name"] == "LSCR"]
            if len(set(local_numbers)) != len(local_numbers):
                raise RuntimeError(f"room {decoded.room} has duplicate executable local-script IDs")
            if any(number < manifest_global_scripts for number in local_numbers):
                raise RuntimeError(
                    f"room {decoded.room} has LSCR below global-script boundary "
                    f"{manifest_global_scripts}"
                )
        room_order = {room: index for index, room in enumerate(args.append_room_entry_exit)}
        manifest_deferred_room_entry_exit_scripts.sort(key=lambda item: (
            room_order[int(item["room"])], 0 if item["kind_name"] == "ENCD" else 1,
        ))
        for item in manifest_deferred_room_entry_exit_scripts:
            item["id"] = program_ids.allocate()
            programs.append(item)
            room_record = records[int(item["record"])]
            room_record["entry" if item["kind_name"] == "ENCD" else "exit"] = item["id"]

        for source_script in manifest.get("global_scripts", []):
            if (source_script.get("append_after_rooms", False)
                    or int(source_script["number"]) in args.append_global_script
                    or int(source_script["number"]) in args.append_late_global_script
                    or int(source_script["number"]) in args.append_final_global_script
                    or int(source_script["number"]) in args.append_terminal_global_script
                    or int(source_script["number"]) in args.append_post_terminal_global_script
                    or int(source_script["number"]) in args.append_last_global_script):
                deferred_global_scripts.append({
                    **source_script, "_manifest_dir": str(manifest_path.parent),
                    "_late_append": int(source_script["number"]) in args.append_late_global_script,
                    "_final_append": int(source_script["number"]) in args.append_final_global_script,
                    "_terminal_append": int(source_script["number"]) in args.append_terminal_global_script,
                    "_post_terminal_append": int(source_script["number"]) in args.append_post_terminal_global_script,
                    "_last_append": int(source_script["number"]) in args.append_last_global_script,
                })
                continue
            number = int(source_script["number"])
            program = (manifest_path.parent / source_script["output"]).read_bytes()
            if len(program) != int(source_script["length"]):
                raise RuntimeError(f"global script {number} length differs")
            existing_global = next(
                (item for item in global_scripts if item["number"] == number), None
            )
            if existing_global is not None:
                if existing_global["program"] != program:
                    raise RuntimeError(
                        f"global script {number} differs between cooked-room manifests"
                    )
                # A source-root fixture manifest may provide an authored
                # global body without decoder maps, while a companion
                # source-cooked manifest carries the authoritative PC spans
                # needed by checked paging. Merge only that compiler metadata;
                # the executable bytes and canonical identity remain the
                # first, hash-verified copy.
                incoming_spans = source_script.get("instruction_spans", [])
                if incoming_spans:
                    if (existing_global.get("instruction_spans")
                            and existing_global["instruction_spans"] != incoming_spans):
                        raise RuntimeError(
                            f"global script {number} instruction maps differ between manifests"
                        )
                    existing_global["instruction_spans"] = incoming_spans
                incoming_opaque = source_script.get("opaque_ranges", [])
                if incoming_opaque:
                    if (existing_global.get("opaque_ranges")
                            and existing_global["opaque_ranges"] != incoming_opaque):
                        raise RuntimeError(
                            f"global script {number} opaque maps differ between manifests"
                        )
                    existing_global["opaque_ranges"] = incoming_opaque
                continue
            item = {
                "id": program_ids.allocate(), "record": None, "room": None,
                "kind": 0, "kind_name": "GLOBAL", "number": number,
                "length": len(program), "program": program,
                "identity": f"script.{number}", "source": source_script,
                "instruction_spans": source_script.get("instruction_spans", []),
                "opaque_ranges": source_script.get("opaque_ranges", []),
                "executable": True,
            }
            programs.append(item)
            global_scripts.append(item)
    # Downstream scenario extensions may add globals without perturbing the
    # established room/local program identities.  Their lookup IDs are still
    # generated normally, but allocation occurs after all existing records.
    # Stable partition: explicitly appended globals follow historical deferred
    # globals as well as room programs. No title/script identity policy here.
    deferred_global_scripts.sort(key=lambda item: int(item["number"]) in args.append_global_script)
    for source_script in deferred_global_scripts:
        if (source_script.get("_late_append", False)
                or source_script.get("_final_append", False)
                or source_script.get("_terminal_append", False)
                or source_script.get("_post_terminal_append", False)
                or source_script.get("_last_append", False)):
            continue
        number = int(source_script["number"])
        program = (Path(source_script["_manifest_dir"]) / source_script["output"]).read_bytes()
        if len(program) != int(source_script["length"]):
            raise RuntimeError(f"global script {number} length differs")
        existing_global = next((item for item in global_scripts if item["number"] == number), None)
        if existing_global is not None:
            if existing_global["program"] != program:
                raise RuntimeError(f"global script {number} differs between cooked-room manifests")
            continue
        item = {
            "id": program_ids.allocate(), "record": None, "room": None,
            "kind": 0, "kind_name": "GLOBAL", "number": number,
            "length": len(program), "program": program,
            "identity": f"script.{number}", "source": source_script,
            "instruction_spans": source_script.get("instruction_spans", []),
            "opaque_ranges": source_script.get("opaque_ranges", []),
            "executable": True,
        }
        programs.append(item)
        global_scripts.append(item)
    requested_locals = {(item["room"], item["number"]): item for item in deferred_local_scripts}
    if len(requested_locals) != len(deferred_local_scripts):
        raise RuntimeError("duplicate appended executable local in input manifests")
    for room, number in append_executable_locals:
        item = requested_locals.get((room, number))
        if item is None:
            raise RuntimeError(f"appended executable local absent from input manifests: {room}:{number}")
        item["id"] = program_ids.allocate()
        programs.append(item)

    for source_script in deferred_global_scripts:
        if (not source_script.get("_late_append", False)
                or source_script.get("_final_append", False)
                or source_script.get("_terminal_append", False)
                or source_script.get("_post_terminal_append", False)
                or source_script.get("_last_append", False)):
            continue
        number = int(source_script["number"])
        program = (Path(source_script["_manifest_dir"]) / source_script["output"]).read_bytes()
        if len(program) != int(source_script["length"]):
            raise RuntimeError(f"global script {number} length differs")
        existing_global = next((item for item in global_scripts if item["number"] == number), None)
        if existing_global is not None:
            if existing_global["program"] != program:
                raise RuntimeError(f"global script {number} differs between cooked-room manifests")
            continue
        item = {
            "id": program_ids.allocate(), "record": None, "room": None,
            "kind": 0, "kind_name": "GLOBAL", "number": number,
            "length": len(program), "program": program,
            "identity": f"script.{number}", "source": source_script,
            "executable": True,
        }
        programs.append(item)
        global_scripts.append(item)
    late_room_order = {room: index for index, room in enumerate(args.append_late_room_entry_exit)}
    late_deferred_room_entry_exit_scripts.sort(key=lambda item: (
        late_room_order[int(item["room"])], 0 if item["kind_name"] == "ENCD" else 1,
    ))
    for item in late_deferred_room_entry_exit_scripts:
        item["id"] = program_ids.allocate()
        programs.append(item)
        room_record = records[int(item["record"])]
        room_record["entry" if item["kind_name"] == "ENCD" else "exit"] = item["id"]
    for room, number in append_late_executable_locals:
        item = requested_locals.get((room, number))
        if item is None:
            raise RuntimeError(
                f"late-appended executable local absent from input manifests: {room}:{number}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    requested_objects = {
        (int(item["room"]), int(item["number"])): item
        for item in deferred_object_programs
    }
    if len(requested_objects) != len(deferred_object_programs):
        raise RuntimeError("duplicate appended executable local object in input manifests")
    for room, object_id in append_executable_local_objects:
        item = requested_objects.get((room, object_id))
        if item is None:
            raise RuntimeError(
                f"appended executable local object absent from input manifests: {room}:{object_id}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    # New dependency-closure locals must not change any established global,
    # room-entry, local, or object program assignment. Allocate this explicit
    # final phase only after every existing selection family is complete.
    for room, number in append_final_executable_locals:
        item = requested_locals.get((room, number))
        if item is None:
            raise RuntimeError(
                f"final-appended executable local absent from input manifests: {room}:{number}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    for number in args.append_final_global_script:
        source_script = next((
            item for item in deferred_global_scripts
            if int(item["number"]) == number and item.get("_final_append", False)
        ), None)
        if source_script is None:
            raise RuntimeError(f"final-appended global absent from input manifests: {number}")
        program = (Path(source_script["_manifest_dir"]) / source_script["output"]).read_bytes()
        if len(program) != int(source_script["length"]):
            raise RuntimeError(f"global script {number} length differs")
        existing_global = next((item for item in global_scripts if item["number"] == number), None)
        if existing_global is not None:
            if existing_global["program"] != program:
                raise RuntimeError(f"global script {number} differs between cooked-room manifests")
            continue
        item = {
            "id": program_ids.allocate(), "record": None, "room": None,
            "kind": 0, "kind_name": "GLOBAL", "number": number,
            "length": len(program), "program": program,
            "identity": f"script.{number}", "source": source_script,
            "executable": True,
        }
        programs.append(item)
        global_scripts.append(item)
    terminal_room_order = {
        room: index for index, room in enumerate(args.append_terminal_room_entry_exit)
    }
    terminal_deferred_room_entry_exit_scripts.sort(key=lambda item: (
        terminal_room_order[int(item["room"])],
        0 if item["kind_name"] == "ENCD" else 1,
    ))
    for item in terminal_deferred_room_entry_exit_scripts:
        item["id"] = program_ids.allocate()
        programs.append(item)
        room_record = records[int(item["record"])]
        room_record["entry" if item["kind_name"] == "ENCD" else "exit"] = item["id"]
    for room, number in append_terminal_executable_locals:
        item = requested_locals.get((room, number))
        if item is None:
            raise RuntimeError(
                f"terminal-appended executable local absent from input manifests: {room}:{number}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    for number in args.append_terminal_global_script:
        source_script = next((
            item for item in deferred_global_scripts
            if int(item["number"]) == number and item.get("_terminal_append", False)
        ), None)
        if source_script is None:
            raise RuntimeError(f"terminal-appended global absent from input manifests: {number}")
        program = (Path(source_script["_manifest_dir"]) / source_script["output"]).read_bytes()
        if len(program) != int(source_script["length"]):
            raise RuntimeError(f"global script {number} length differs")
        existing_global = next((item for item in global_scripts if item["number"] == number), None)
        if existing_global is not None:
            if existing_global["program"] != program:
                raise RuntimeError(f"global script {number} differs between cooked-room manifests")
            continue
        item = {
            "id": program_ids.allocate(), "record": None, "room": None,
            "kind": 0, "kind_name": "GLOBAL", "number": number,
            "length": len(program), "program": program,
            "identity": f"script.{number}", "source": source_script,
            "executable": True,
        }
        programs.append(item)
        global_scripts.append(item)
    for room, number in append_post_terminal_executable_locals:
        item = requested_locals.get((room, number))
        if item is None:
            raise RuntimeError(
                f"post-terminal executable local absent from input manifests: {room}:{number}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    for room, object_id in append_terminal_executable_local_objects:
        item = requested_objects.get((room, object_id))
        if item is None:
            raise RuntimeError(
                f"terminal-appended executable local object absent from input manifests: "
                f"{room}:{object_id}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    for number in args.append_post_terminal_global_script:
        source_script = next((
            item for item in deferred_global_scripts
            if int(item["number"]) == number
            and item.get("_post_terminal_append", False)
        ), None)
        if source_script is None:
            raise RuntimeError(
                f"post-terminal-appended global absent from input manifests: {number}"
            )
        program = (Path(source_script["_manifest_dir"]) / source_script["output"]).read_bytes()
        if len(program) != int(source_script["length"]):
            raise RuntimeError(f"global script {number} length differs")
        existing_global = next((item for item in global_scripts if item["number"] == number), None)
        if existing_global is not None:
            if existing_global["program"] != program:
                raise RuntimeError(f"global script {number} differs between cooked-room manifests")
            continue
        item = {
            "id": program_ids.allocate(), "record": None, "room": None,
            "kind": 0, "kind_name": "GLOBAL", "number": number,
            "length": len(program), "program": program,
            "identity": f"script.{number}", "source": source_script,
            "executable": True,
        }
        programs.append(item)
        global_scripts.append(item)
    last_room_order = {
        room: index for index, room in enumerate(args.append_last_room_entry_exit)
    }
    last_deferred_room_entry_exit_scripts.sort(key=lambda item: (
        last_room_order[int(item["room"])],
        0 if item["kind_name"] == "ENCD" else 1,
    ))
    for item in last_deferred_room_entry_exit_scripts:
        item["id"] = program_ids.allocate()
        programs.append(item)
        room_record = records[int(item["record"])]
        room_record["entry" if item["kind_name"] == "ENCD" else "exit"] = item["id"]
    for room, number in append_last_executable_locals:
        item = requested_locals.get((room, number))
        if item is None:
            raise RuntimeError(
                f"last-appended executable local absent from input manifests: {room}:{number}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    for room, object_id in append_last_executable_local_objects:
        item = requested_objects.get((room, object_id))
        if item is None:
            raise RuntimeError(
                f"last-appended executable local object absent from input manifests: "
                f"{room}:{object_id}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    for number in args.append_last_global_script:
        source_script = next((
            item for item in deferred_global_scripts
            if int(item["number"]) == number and item.get("_last_append", False)
        ), None)
        if source_script is None:
            raise RuntimeError(f"last-appended global absent from input manifests: {number}")
        program = (Path(source_script["_manifest_dir"]) / source_script["output"]).read_bytes()
        if len(program) != int(source_script["length"]):
            raise RuntimeError(f"global script {number} length differs")
        existing_global = next((item for item in global_scripts if item["number"] == number), None)
        if existing_global is not None:
            if existing_global["program"] != program:
                raise RuntimeError(f"global script {number} differs between cooked-room manifests")
            continue
        item = {
            "id": program_ids.allocate(), "record": None, "room": None,
            "kind": 0, "kind_name": "GLOBAL", "number": number,
            "length": len(program), "program": program,
            "identity": f"script.{number}", "source": source_script,
            "executable": True,
        }
        programs.append(item)
        global_scripts.append(item)
    # This final dependency-closure phase is intentionally after last globals
    # and OBCD selections as well as every earlier room/local selection, so a
    # newly reached LSCR cannot renumber any established executable identity.
    for room, number in append_ultimate_executable_locals:
        item = requested_locals.get((room, number))
        if item is None:
            raise RuntimeError(
                f"ultimate-appended executable local absent from input manifests: {room}:{number}"
            )
        item["id"] = program_ids.allocate()
        programs.append(item)
    if set(args.append_global_script + args.append_late_global_script + args.append_final_global_script + args.append_terminal_global_script + args.append_post_terminal_global_script + args.append_last_global_script) - {item["number"] for item in global_scripts}:
        raise RuntimeError("appended global script absent from input manifests")
    if set(append_executable_locals + append_late_executable_locals + append_final_executable_locals + append_terminal_executable_locals + append_post_terminal_executable_locals + append_last_executable_locals + append_ultimate_executable_locals) - set(requested_locals):
        raise RuntimeError("appended executable local absent from input manifests")
    selected_entry_exit_rooms = set(
        args.append_room_entry_exit
        + args.append_late_room_entry_exit
        + args.append_terminal_room_entry_exit
        + args.append_last_room_entry_exit
    )
    if selected_entry_exit_rooms - {int(item["room"]) for item in records}:
        raise RuntimeError("late-appended room entry/exit selection absent from input manifests")
    if len({item["room"] for item in records}) != len(records):
        raise RuntimeError("generated cooked-room tables contain duplicate room numbers")
    if len({item["number"] for item in global_scripts}) != len(global_scripts):
        raise RuntimeError("generated global-script tables contain duplicate numbers")

    native_directory = None
    if args.dynamic_program_residency:
        native_rows = []
        canonical_by_temp_id = {}
        canonical_identities = set()
        for item in programs:
            item["_temp_program_id"] = int(item["id"])
            identity = canonical_unit_identity(
                item["kind_name"], room=item["room"], number=int(item["number"]),
            )
            if identity in canonical_identities:
                raise RuntimeError(f"duplicate selector-bearing ProgramUnit {identity}")
            canonical_identities.add(identity)
            canonical_by_temp_id[int(item["id"])] = identity
            source = item.get("source")
            source_location = {
                key: (source.get(key) if isinstance(source, dict)
                      else getattr(source, key, None))
                for key in (
                    "source_member", "resource_key", "original_file_offset",
                    "original_room_offset", "original_chunk_offset",
                    "cooked_record_offset", "normalized_script_offset",
                    "directory_offset", "directory_room", "encrypted_chunk_offset",
                    "decoded_chunk_offset", "decoded_payload_offset", "source_length",
                    "source_sha256", "obcd_original_file_offset", "obcd_room_offset",
                    "obcd_length", "obcd_sha256", "local_object_index",
                    "verb_table_offset", "verb_table_length",
                )
            }
            source_location = {key: value for key, value in source_location.items()
                               if value is not None}
            native_rows.append({
                "identity": identity,
                "kind": ("GLOBAL" if item["kind_name"] == "GLOBAL"
                         else item["kind_name"]),
                "room": item["room"], "number": int(item["number"]),
                "length": int(item["length"]),
                "sha256": hashlib.sha256(item["program"]).hexdigest(),
                "bundle": (f"GlobalBundle({item['number']})" if item["kind_name"] == "GLOBAL"
                           else f"RoomBundle({item['room']})"),
                "source_provenance": {
                    "source_identity": item.get("identity"),
                    "body_sha256": hashlib.sha256(item["program"]).hexdigest(),
                    "body_pc_coordinate": (
                        "OBCD-relative" if item["kind_name"] == "OBCD"
                        else "program-body-relative"
                    ),
                    "source_location": source_location,
                },
                "dispatch": ({"object": int(item["number"]),
                              "verb_entrypoints": [
                                  {"verb": int(verb), "offset": int(offset)}
                                  for verb, offset in item.get("entrypoints", ())
                              ]} if item["kind_name"] == "OBCD" else {}),
            })
        native_directory = NativeProgramDirectory.from_programs(native_rows)
        id_by_identity = {
            row["identity"]: int(row["program_unit_id"])
            for row in native_directory.document["entries"]
        }
        for item in programs:
            item["id"] = id_by_identity[
                canonical_by_temp_id[int(item["_temp_program_id"])]
            ]
            del item["_temp_program_id"]
        # The temporary allocator IDs are no longer needed; recover canonical
        # identities directly from source kind/owner after stable ID sorting.
        for item in programs:
            item["unit_identity"] = canonical_unit_identity(
                item["kind_name"], room=item["room"], number=int(item["number"]),
            )
        for record in records:
            record["entry"] = next((
                int(item["id"]) for item in record["scripts"]
                if item["kind_name"] == "ENCD" and item["id"] is not None
            ), 0xFFFF)
            record["exit"] = next((
                int(item["id"]) for item in record["scripts"]
                if item["kind_name"] == "EXCD" and item["id"] is not None
            ), 0xFFFF)

    program_storage = None
    if args.msu1_program_storage_dir is not None:
        if native_directory is None:
            raise RuntimeError("MSU ProgramUnit storage requires a canonical native directory")
        storage_bodies = {
            str(item["unit_identity"]): bytes(item["program"])
            for item in programs if item["executable"]
        }
        for item in programs:
            source = item.get("source")
            if isinstance(source, dict):
                item.setdefault("instruction_spans", source.get("instruction_spans", []))
                item.setdefault("opaque_ranges", source.get("opaque_ranges", []))
        storage_page_metadata = {
            str(item["unit_identity"]): {
                "instruction_spans": item.get("instruction_spans", []),
                "opaque_ranges": item.get("opaque_ranges", []),
            }
            for item in programs if item["executable"]
        }
        # In live-resource mode SC5LIVE, SC5VIS, and SC5CODE are the checked
        # compiler-owned projections consumed by the runtime. The complete
        # SC5ROOM container contains the same script bodies plus the retained
        # source ROOM payload and can be tens of KiB; it is not a live consumer
        # and must not be staged merely as a redundant preflight copy.
        room_resources = ({} if args.msu1_live_room_resources else {
            int(record["room"]): bytes(record["raw"])
            for record in records
        })
        live_room_resources = {}
        room_visual_resources = {}
        if args.msu1_live_room_resources:
            missing_visuals = [int(record["room"]) for record in records
                               if record.get("visual_raw") is None]
            if missing_visuals:
                raise RuntimeError(
                    "live room-resource mode requires a checked SC5VIS record for every room; "
                    f"missing {missing_visuals[:8]}"
                )
            live_room_resources = {
                int(record["room"]): encode_live_room(
                    record, program_units=programs, max_size=0xFFFF,
                )
                for record in records
            }
            room_visual_resources = {
                int(record["room"]): bytes(record["visual_raw"])
                for record in records
            }
        source_room_resources = (
            {int(record["room"]): bytes(record["raw"]) for record in records}
            if args.msu1_include_source_room_records else {}
        )
        prefix_sections = read_package_prefix_sections(
            args.msu1_program_prefix_package,
            None if args.msu1_program_prefix_all_sections
            else tuple(args.msu1_program_prefix_section),
        ) if args.msu1_program_prefix_package else ()
        program_storage = build_program_storage(
            native_directory.document, storage_bodies, args.msu1_program_storage_dir,
            max_cached_body_bytes=args.msu1_program_cache_bytes,
            page_metadata=storage_page_metadata,
            prefix_sections=prefix_sections,
            room_resources=room_resources,
            source_room_resources=source_room_resources,
            live_room_resources=live_room_resources,
            room_visual_resources=room_visual_resources,
            rom_bank=args.msu1_program_directory_bank,
            page_directory_bank=(
                args.msu1_program_directory_bank + 2
                if args.msu1_program_page_directory_bank is None
                else args.msu1_program_page_directory_bank
            ),
        )
        args.msu1_program_directory_include.parent.mkdir(parents=True, exist_ok=True)
        args.msu1_program_directory_include.write_bytes(
            (args.msu1_program_storage_dir / "scumm_msu1_programs.inc.pasm").read_bytes()
        )

    if global_states is None:
        global_states = bytes(4096)
    if global_owners is None:
        global_owners = bytes(len(global_states))
    if global_classes is None:
        global_classes = (0,) * len(global_states)
    if scenario_class_overlays:
        classes = list(global_classes)
        for object_id, mask in scenario_class_overlays:
            if object_id >= len(classes):
                raise RuntimeError(f"scenario class overlay object {object_id} is outside the source table")
            classes[object_id] |= mask
        global_classes = tuple(classes)
    if actor_facings is None:
        actor_facings = (180,) * 32
    if actor_positions is None:
        actor_positions = ((0, 0),) * 32
    if actor_walkboxes is None:
        actor_walkboxes = (0,) * 32
    hold_after_started_global_program = 0
    if hold_after_started_global_script is not None:
        match = next(
            (item for item in global_scripts
             if item["number"] == hold_after_started_global_script),
            None,
        )
        if match is None:
            raise RuntimeError("execution-gate global script is not generated")
        hold_after_started_global_program = int(match["id"])

    reserved_banks = set(args.reserved_bank)

    def cpu_rom_address(bank: int) -> str:
        visible_bank = cpu_visible_rom_bank(bank, sa1_aliases=args.sa1_rom_bank_aliases)
        return f"${visible_bank:02X}8000"

    def next_free_bank(value: int) -> int:
        while value in reserved_banks:
            value += 1
        return value

    bank = next_free_bank(args.first_bank)
    data_lines = ["; Generated cooked-room bytes; never commit the source payloads."]
    room_segment_map: list[dict[str, object]] = []
    room_page = bank
    room_page_offset = 0
    room_page_open = False
    for record_index, record in enumerate(records):
        segments = []
        raw = record["raw"]
        if args.msu1_live_room_resources:
            # Live-room builds consume SC5LIVE/SC5VIS through the checked
            # resource service. Do not retain the complete cooked SC5C ROOM
            # projection in ROM as an accidental fallback copy.
            record["segments"] = segments
            continue
        source_offset = 0
        segment_index = 0
        while source_offset < len(raw):
            if not room_page_open:
                data_lines.extend((f".bank {room_page}",
                                   f".org ${0x8000 + room_page_offset:04X}"))
                room_page_open = True
            start = source_offset
            payload = raw[source_offset:source_offset + 0x8000 - room_page_offset]
            binary = args.binary_dir / f"record-{record_index}-segment-{segment_index}.bin"
            binary.write_bytes(payload)
            written_segments.append({"path": binary.name, "size": len(payload),
                                     "sha256": hashlib.sha256(payload).hexdigest()})
            label = f"ScummV5_M23A_Record_{record_index}_Segment_{segment_index}"
            include_path = (
                Path(os.path.relpath(binary, start=args.output.parent)).as_posix()
                if args.relative_binary_paths else str(binary.resolve())
            )
            data_lines.extend((f"{label}:", f'    .incbin "{include_path}"'))
            segments.append((label, len(payload), start))
            room_segment_map.append({
                "source_identity": f"RoomResource({record['room']})",
                "room": int(record["room"]), "record_index": record_index,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "source_payload_offset": start, "payload_bytes": len(payload),
                "rom_bank": room_page, "bank_offset": room_page_offset,
                "segment_index": segment_index,
                "output_member": record.get("source_record_output"), "label": label,
            })
            source_offset += len(payload)
            room_page_offset += len(payload)
            segment_index += 1
            if room_page_offset == 0x8000:
                room_page = next_free_bank(room_page + 1)
                room_page_offset = 0
                room_page_open = False
        record["segments"] = segments

    # Bank 9 is reserved by the M24R-B validator/lifecycle closure.  Keep all
    # generated data sections out of it, not just the large room payloads;
    # otherwise adding a room can move the initializer into bank 9 and the
    # later validator include silently overwrites it.
    bank = next_free_bank(room_page + (1 if room_page_open else 0))
    # Immutable header/directories are validation data, not executable code.
    # They must not be appended to the final raw-room payload bank: a room
    # directory can grow by 96 bytes when another script is selected, and
    # silently carrying that growth past $FFFF corrupts the next LoROM bank.
    # Pack complete directories into explicitly bounded profile-data banks.
    # Immutable navigation tables are emitted one table per LoROM bank.  A
    # room with many boxes has a large portal matrix; keeping all rooms in one
    # bank would make long-indexed reads cross a bank boundary silently.
    directory_bank = None
    directory_offset = 0
    expected_directory_map: list[dict[str, object]] = []
    for index, record in enumerate(records):
        if args.msu1_live_room_resources:
            # The live-room transaction validates its package record and
            # source-bound compiler projection before publication; the
            # legacy ROM-record validator is deliberately not a consumer.
            continue
        prefix = record["raw"][:HEADER.size + len(record["scripts"]) * 96]
        if len(prefix) > 0x8000:
            raise RuntimeError(
                f"room {record['room']} expected directory exceeds one LoROM bank"
            )
        directory_label = f"ScummV5_M23A_Record_{index}_ExpectedDirectory"
        record_index = int(record.get("record_index", index))
        backing = None
        if args.share_room_directory_prefixes:
            backing = next((segment for segment in room_segment_map
                            if int(segment.get("record_index", -1)) == record_index
                            and int(segment["source_payload_offset"]) == 0
                            and len(prefix) <= int(segment["payload_bytes"])
                            and int(segment["bank_offset"]) + len(prefix) <= 0x8000), None)
        if backing is not None:
            # The immutable integrity prefix is already present verbatim at
            # the start of the complete cooked ROOM record. Point the
            # validator at those bytes instead of emitting a second copy.
            if prefix != record["raw"][:len(prefix)]:
                raise RuntimeError(
                    f"room {record['room']} directory alias does not match its ROOM source"
                )
            expected_directory_map.append({
                "source_identity": f"RoomDirectory({record['room']})",
                "source_sha256": hashlib.sha256(prefix).hexdigest(),
                "payload_sha256": hashlib.sha256(prefix).hexdigest(),
                "payload_bytes": len(prefix), "rom_bank": int(backing["rom_bank"]),
                "bank_offset": int(backing["bank_offset"]),
                "label": directory_label,
                "consumer": "cooked-room integrity validator",
                "contained_in_source_identity": f"RoomResource({record['room']})",
                "contained_in_source_offset": 0,
                "storage_kind": "ROOM_RECORD_DIRECTORY_ALIAS",
                "shared_storage": True,
                "storage_alias_of": f"RoomResource({record['room']})",
                "storage_source_offset": 0,
                "storage_payload_match_verified": True,
                "storage_label": backing["label"],
            })
            local_offset = -int(backing["source_payload_offset"])
            data_lines.append(
                f"{directory_label} = {backing['label']}+${local_offset:04X}"
            )
            continue
        if directory_bank is None or directory_offset + len(prefix) > 0x8000:
            if directory_bank is not None:
                bank = directory_bank + 1
            directory_bank = next_free_bank(bank)
            directory_offset = 0
            data_lines.extend((f".bank {directory_bank}", ".org $8000"))
        expected_directory_map.append({
            "source_identity": f"RoomDirectory({record['room']})",
            "source_sha256": hashlib.sha256(prefix).hexdigest(),
            "payload_sha256": hashlib.sha256(prefix).hexdigest(),
            "payload_bytes": len(prefix), "rom_bank": directory_bank,
            "bank_offset": directory_offset,
            "label": directory_label,
            "consumer": "cooked-room integrity validator",
            "contained_in_source_identity": f"RoomResource({record['room']})",
            "contained_in_source_offset": 0,
            "storage_kind": "SEPARATE_ROOM_DIRECTORY_COPY",
            "shared_storage": False,
            "storage_payload_match_verified": True,
        })
        data_lines.extend((f"{directory_label}:", rows(prefix)))
        directory_offset += len(prefix)
    if directory_bank is not None:
        bank = directory_bank + 1
    def next_unoccupied_generated_bank(start: int) -> int:
        occupied = {page for page, _origin in occupied_generated_bank_origins(data_lines)}
        candidate = next_free_bank(start)
        while candidate in occupied:
            candidate = next_free_bank(candidate + 1)
        return candidate

    table_placement_map: list[dict[str, object]] = []

    if args.far_programs:
        program_bank = None
        program_offset = 0
        separate_program_bytes = 0
        for item in programs:
            if item["executable"]:
                if args.msu1_program_storage_dir is not None:
                    item["storage_kind"] = "SAMEPKG_MSU1_PROGRAM_BODY"
                    item["shared_storage"] = False
                    item["storage_payload_match_verified"] = True
                    continue
                shared = None
                if args.share_room_program_bodies and item.get("kind_name") != "GLOBAL":
                    source = item.get("source")
                    source_offset = (
                        source.get("cooked_record_offset") if isinstance(source, dict)
                        else getattr(source, "cooked_record_offset", None)
                    )
                    record_index = int(item["record"])
                    if source_offset is not None and 0 <= record_index < len(records):
                        source_offset = int(source_offset)
                        source_end = source_offset + len(item["program"])
                        if records[record_index]["raw"][source_offset:source_end] == item["program"]:
                            shared = next((segment for segment in room_segment_map
                                           if int(segment.get("record_index", -1)) == record_index
                                           and int(segment["source_payload_offset"]) <= source_offset
                                           and source_end <= int(segment["source_payload_offset"])
                                               + int(segment["payload_bytes"])
                                           and int(segment["bank_offset"])
                                               + source_offset - int(segment["source_payload_offset"])
                                               + len(item["program"]) <= 0x8000), None)
                if shared is not None:
                    local_offset = source_offset - int(shared["source_payload_offset"])
                    item["rom_bank"] = int(shared["rom_bank"])
                    item["bank_offset"] = int(shared["bank_offset"]) + local_offset
                    item["cpu_rom_bank"] = cpu_visible_rom_bank(
                        int(item["rom_bank"]), sa1_aliases=args.sa1_rom_bank_aliases,
                    )
                    item["cpu_address"] = 0x8000 + int(item["bank_offset"])
                    item["cpu_addressable_24bit"] = int(item["rom_bank"]) <= 0xFF
                    item["storage_kind"] = "COOKED_ROOM_RECORD_ALIAS"
                    item["shared_storage"] = True
                    item["storage_alias_of"] = shared["source_identity"]
                    item["storage_source_offset"] = source_offset
                    item["storage_payload_match_verified"] = True
                    item["storage_label"] = shared["label"]
                    data_lines.append(
                        f"ScummV5_M23A_Program_{program_label_id(item['id'], dynamic=args.dynamic_program_residency)} "
                        f"= {shared['label']}+${local_offset:04X}"
                    )
                    continue
                # Executable programs are fetched through long labels.  Keep
                # the packed program pool in explicit LoROM banks so each
                # label's bank byte remains the bank which actually contains
                # its bytes.  A fresh bank is needed only when the next
                # program would cross $FFFF; concatenating the pool in one
                # logical section lets Poppy's address arithmetic cross
                # $FFFF without changing the ROM bank and makes far fetches
                # read unrelated data.
                if program_bank is None or program_offset + len(item["program"]) > 0x8000:
                    if program_bank is not None:
                        bank = program_bank + 1
                    bank = next_free_bank(bank)
                    program_bank = bank
                    program_offset = 0
                    data_lines.extend((f".bank {program_bank}", ".org $8000"))
                item["rom_bank"] = program_bank
                item["bank_offset"] = program_offset
                item["cpu_rom_bank"] = cpu_visible_rom_bank(
                    program_bank, sa1_aliases=args.sa1_rom_bank_aliases,
                )
                item["cpu_address"] = 0x8000 + program_offset
                item["cpu_addressable_24bit"] = program_bank <= 0xFF
                item["storage_kind"] = "SEPARATE_PROGRAM_BODY"
                item["shared_storage"] = False
                item["storage_payload_match_verified"] = False
                separate_program_bytes += len(item["program"])
                if program_offset == 0:
                    pass
                else:
                    # The previous program already occupies this bank; the
                    # label remains bank-correct because the pool is packed
                    # below the 32 KiB LoROM boundary.
                    pass
                data_lines.extend((
                    f"ScummV5_M23A_Program_{program_label_id(item['id'], dynamic=args.dynamic_program_residency)}:",
                    rows(item["program"]),
                ))
                program_offset += len(item["program"])
        if program_bank is not None:
            bank = program_bank + 1
    else:
        separate_program_bytes = sum(len(item["program"]) for item in programs
                                     if item["executable"])
    if args.dynamic_program_residency:
        # Runtime selectors resolve to canonical IDs, then use these compact
        # indexed tables.  This keeps code size constant in corpus size; a
        # linear compare chain per ProgramUnit would become a second scaling
        # bottleneck despite the bounded 178-slot resident pool.
        if len(programs) > 0x1999:
            raise RuntimeError(
                "native program-pointer table exceeds one 32 KiB LoROM bank"
            )
        bank = next_unoccupied_generated_bank(bank)
        pointer_bank = bank
        data_lines.extend((
            f".bank {bank}", ".org $8000",
            "ScummV5_M23A_ProgramLengths:",
            word_rows([
                int(item["length"])
                for item in sorted(programs, key=lambda item: int(item["id"]))
            ]) or "    .word $0000",
        ))
        if args.msu1_program_storage_dir is None:
            data_lines.extend((
                "ScummV5_M23A_ProgramPointers:",
                "    .long " + ",".join(
                    f"ScummV5_M23A_Program_{program_label_id(item['id'], dynamic=True)}"
                    for item in sorted(programs, key=lambda item: int(item["id"]))
                ) if programs else "    .long $000000",
            ))
        table_placement_map.append({
            "label": ("ScummV5_M23A_ProgramLengths" if args.msu1_program_storage_dir
                      else "ScummV5_M23A_ProgramLengths+ProgramPointers"),
            "source_identity": "ProgramUnitPointerDirectory",
            "consumer": ("native MSU ProgramUnit cache bounds" if args.msu1_program_storage_dir
                         else "native dynamic ProgramUnit byte-fetch resolver"),
            "payload_bytes": len(programs) * (2 if args.msu1_program_storage_dir else 5),
            "rom_bank": pointer_bank, "bank_offset": 0,
            "representation": ("u16 program lengths; bodies are SAMEPKG-addressed"
                               if args.msu1_program_storage_dir else
                               "u16 program lengths followed by u24 relocated body pointers"),
            "source_sha256": None, "payload_sha256": None,
            "resolver_table": True,
        })
        bank += 1
    # Keep immutable navigation/object tables out of the executable-program
    # bank.  Poppy intentionally does not roll a label whose offset exceeds
    # $FFFF into a new LoROM bank, so every generated region is explicit.
    bank += 1
    bank = next_free_bank(bank)
    data_lines.extend((f".bank {bank}", ".org $8000"))
    packed_table_bank: int | None = None
    packed_table_offset = 0
    packed_table_next_bank = bank
    def append_room_table(label: str, payload: bytes) -> tuple[int, int]:
        """Append one bounded table, packing source-wide metadata when requested."""
        nonlocal packed_table_bank, packed_table_offset, packed_table_next_bank
        nonlocal bank
        if args.msu1_live_room_resources and label.startswith((
            "ScummV5_Matrix_Record_", "ScummV5_PutActor_Record_",
            "ScummV5_Movement_Record_", "ScummV5_SetState_Record_",
            "ScummV5_Verb_Record_",
        )):
            # These records are authoritative in the checked SC5LIVE payload.
            # Keep the legacy symbols linkable, but leave only one sentinel
            # byte so live mode has no hidden ROM copy of room data.
            payload = b"\0"
        if args.msu1_live_room_resources and label in {
            "ScummV5_M23A_RoomEntryProgramUnitIds",
            "ScummV5_M23A_RoomExitProgramUnitIds",
            "ScummV5_Resident_RoomBundleOffsets",
            "ScummV5_Resident_RoomBundleCounts",
            "ScummV5_Resident_RoomBundleUnitIds",
            "ScummV5_Resident_RoomLocalOffsets",
            "ScummV5_Resident_RoomLocalCounts",
            "ScummV5_Resident_RoomLocalNumbers",
            "ScummV5_Resident_RoomLocalUnitIds",
        }:
            payload = b"\xff\xff" if label.endswith(("UnitIds", "ProgramUnitIds")) else b"\0"
        if len(payload) > 0x8000:
            raise RuntimeError(f"generated table {label} exceeds one LoROM bank")
        if not args.pack_source_tables:
            target_bank = next_unoccupied_generated_bank(bank)
            data_lines.extend((
                f".bank {target_bank}", ".org $8000",
                f"{label}_Address = {cpu_rom_address(target_bank)}",
                f"{label}:", rows(payload),
            ))
            bank = target_bank + 1
            table_placement_map.append({
                "label": label, "source_identity": label,
                "consumer": "SCUMM runtime generated lookup/navigation table",
                "payload_bytes": len(payload), "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "rom_bank": target_bank, "bank_offset": 0,
                "resolver_table": label.startswith("ScummV5_Resident_")
                or "ProgramUnitIds" in label or "ProgramPointers" in label,
            })
            return target_bank, 0
        if (packed_table_bank is None
                or packed_table_offset + len(payload) > 0x8000):
            packed_table_bank = next_unoccupied_generated_bank(packed_table_next_bank)
            packed_table_next_bank = packed_table_bank + 1
            packed_table_offset = 0
            data_lines.extend((f".bank {packed_table_bank}", ".org $8000"))
        target_bank = packed_table_bank
        target_offset = packed_table_offset
        data_lines.extend((
            f"{label}_Address = " + cpu_visible_rom_address(
                target_bank, target_offset, sa1_aliases=args.sa1_rom_bank_aliases,
            ),
            f"{label}:", rows(payload),
        ))
        packed_table_offset += len(payload)
        bank = packed_table_next_bank
        table_placement_map.append({
            "label": label, "source_identity": label,
            "consumer": "SCUMM runtime generated lookup/navigation table",
            "payload_bytes": len(payload), "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "rom_bank": target_bank, "bank_offset": target_offset,
            "resolver_table": label.startswith("ScummV5_Resident_")
            or "ProgramUnitIds" in label or "ProgramPointers" in label,
        })
        return target_bank, target_offset
    for index, record in enumerate(records):
        if len(record["walkbox_flags"]) > 0xFF:
            raise RuntimeError(
                f"room {record['room']} has {len(record['walkbox_flags'])} walkboxes; "
                "SCUMM box index cannot be represented by the bounded accessor"
            )
        tables = (
            (f"ScummV5_Matrix_Record_{index}_InitialFlags", record["walkbox_flags"]),
            (f"ScummV5_PutActor_Record_{index}_Geometry", record["walkbox_geometry"]),
            (f"ScummV5_Movement_Record_{index}_Routes", record["box_routes"]),
            (f"ScummV5_Movement_Record_{index}_Portals", record["portals"]),
            (f"ScummV5_Movement_Record_{index}_ObjectWalk", record["object_walk"]),
            (f"ScummV5_SetState_Record_{index}_Objects", record["objects"]),
            (f"ScummV5_SetState_Record_{index}_ObjectNames",
             b"".join(name.ljust(32, b"\0") for _object_id, name in record["object_names"])),
        )
        for label, payload in tables:
            append_room_table(label, payload)
        verb_payload = b"".join(
            struct.pack("<HHH", object_id, verb, offset)
            for object_id, verb, offset in record["verb_entries"]
        ) or b"\0" * 6
        verb_label = f"ScummV5_Verb_Record_{index}_Entries"
        data_lines.append(
            f"ScummV5_Verb_Record_{index}_Count = ${len(record['verb_entries']):04X}"
        )
        append_room_table(verb_label, verb_payload)
    if not records:
        # The shared far verb-query closure names the first record's verb
        # table while preparing its diagnostic context, even though its room
        # dispatch will fall through to the no-room result. Provide a real
        # empty table for the supported resource-less profile instead of
        # leaving that shared reference undefined.
        data_lines.append("ScummV5_Verb_Record_0_Count = $0000")
        append_room_table("ScummV5_Verb_Record_0_Entries", b"\0" * 6)
    # C16 is a bounded sparse runtime table.  A Fate profile can describe
    # more initially-classed objects than the runtime can hold at once; keep
    # Keep a small mutation reserve for authored setClass operations.  The
    # generated source order is object-id order, so the low-id startup/object
    # set stays stable and the bounded omission is explicit in the count.
    # Keep a real dynamic reserve for authored room-entry setClass operations.
    # The full DOBJ contains more nonzero records than the 512-record runtime
    # table can hold; consuming all but sixteen slots made a burst of room-82
    # randomized actor classes fail nondeterministically at the first
    # setClass.  Preserve the source-order seed while reserving 32 records for
    # ordinary runtime mutations.
    initial_class_items = [
        (index, value) for index, value in enumerate(global_classes) if value
    ][:0x01E0]
    if args.pack_source_tables:
        append_room_table("ScummV5_SetState_InitialStates", bytes(global_states))
        append_room_table("ScummV5_ObjectOwner_InitialOwners", bytes(global_owners))
        append_room_table("ScummV5_ObjectClass_Initial",
                          b"".join(struct.pack("<HHH", index, value & 0xFFFF,
                                               (value >> 16) & 0xFFFF)
                                  for index, value in initial_class_items))
        append_room_table("ScummV5_GetActorFacing_InitialAngles",
                          b"".join(struct.pack("<H", value & 0xFFFF)
                                  for value in actor_facings))
        append_room_table("ScummV5_GetActorWalkbox_InitialPositions",
                          b"".join(struct.pack("<HH", x & 0xFFFF, y & 0xFFFF)
                                  for x, y in actor_positions))
        append_room_table("ScummV5_GetActorWalkbox_InitialBoxes", bytes(actor_walkboxes))
        data_lines.append("ScummV5_ObjectClass_InitialCount = $%04X" % len(initial_class_items))
    else:
        bank = next_free_bank(bank)
        data_lines.extend((f".bank {bank}", ".org $8000"))
        data_lines.extend((
            "ScummV5_SetState_InitialStates:", rows(global_states),
            "ScummV5_ObjectOwner_InitialOwners:", rows(global_owners),
            "ScummV5_ObjectClass_InitialCount = $%04X" % len(initial_class_items),
            "ScummV5_ObjectClass_Initial:",
            *[f"    .word ${index:04X},${value & 0xFFFF:04X},${(value >> 16) & 0xFFFF:04X}"
              for index, value in initial_class_items],
            "ScummV5_GetActorFacing_InitialAngles:",
            "    .word " + ",".join(f"${value:04X}" for value in actor_facings),
            "ScummV5_GetActorWalkbox_InitialPositions:",
            "    .word " + ",".join(
                f"${x & 0xffff:04X},${y & 0xffff:04X}" for x, y in actor_positions
            ),
            "ScummV5_GetActorWalkbox_InitialBoxes:", rows(bytes(actor_walkboxes)),
        ))
    bank += 1
    bank = next_free_bank(bank)
    data_lines.extend((f".bank {bank}", ".org $8000"))
    # This source-bound initializer is executable profile data. Both the
    # ordinary bank-0 lifecycle and the relocated lifecycle call it with JSL;
    # it never parses or special-cases a title, room number, or script.
    data_lines.extend((
        "ScummV5_Matrix_LoadActiveRoom_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_LoadActiveRoom_Far",
        ".endif",
        "    php",
        "    sep #$20", "    .a8", "    rep #$10", "    .i16",
        # The room commit path carries the active-record index in X across
        # this helper.  Object-name installation uses X as its destination
        # index, so preserve the caller's record selector as part of the
        # loader ABI rather than leaking the last name-buffer offset.
        "    phx", "    phy",
        "    lda #$00", "    sta.l SAME_SCUMM_MATRIX_BOX_COUNT",
        "    sta.l SAME_SCUMM_MATRIX_DYNAMIC_VALID",
        "    sta.l SAME_SCUMM_MATRIX_EXEC_COUNT",
        "    sta.l SAME_SCUMM_MATRIX_LAST_SUBOP",
        "    sta.l SAME_SCUMM_MATRIX_LAST_BOX",
        "    sta.l SAME_SCUMM_MATRIX_LAST_FLAGS",
        "    sta.l SAME_SCUMM_MATRIX_TRACE_COUNT",
        "    sta.l SAME_SCUMM_PUT_ACTOR_EXEC_COUNT",
        "    sta.l SAME_SCUMM_PUT_ACTOR_ACTOR",
        "    sta.l SAME_SCUMM_PUT_ACTOR_TRACE_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_BG_REDRAW",
        "    sta.l SAME_SCUMM_SETSTATE_DIRTY_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_DRAW_QUEUE_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_TRACE_COUNT",
        "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        data_lines.extend((
            f"    cmp #${index:02X}",
            f"    beq ScummV5_Matrix_LoadActiveRoom__match_{index}",
            f"    brl ScummV5_Matrix_LoadActiveRoom__next_{index}",
            f"ScummV5_Matrix_LoadActiveRoom__match_{index}:",
            "    .a8", "    .i16",
            f"    lda #${len(record['walkbox_flags']):02X}",
            "    sta.l SAME_SCUMM_MATRIX_BOX_COUNT",
            "    ldx #$0000",
            f"ScummV5_Matrix_LoadActiveRoom__copy_{index}:",
            "    .a8", "    .i16",
            f"    cpx #${len(record['walkbox_flags']):04X}",
            f"    bcs ScummV5_Matrix_LoadActiveRoom__done_{index}",
            f"    lda.l ScummV5_Matrix_Record_{index}_InitialFlags_Address,x",
            "    sta.l SAME_SCUMM_MATRIX_BOX_FLAGS,x",
            "    inx",
            f"    bra ScummV5_Matrix_LoadActiveRoom__copy_{index}",
            f"ScummV5_Matrix_LoadActiveRoom__done_{index}:",
            "    .a8", "    .i16",
            "    sep #$20", "    .a8", "    ldx #$0000",
            f"ScummV5_SetState_LoadActiveRoom__copy_{index}:",
            "    .a8", "    .i16",
            f"    cpx #${len(record['objects']):04X}",
            f"    bcs ScummV5_SetState_LoadActiveRoom__done_{index}",
            f"    lda.l ScummV5_SetState_Record_{index}_Objects_Address,x",
            "    sta.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS,x", "    inx",
            f"    bra ScummV5_SetState_LoadActiveRoom__copy_{index}",
            f"ScummV5_SetState_LoadActiveRoom__done_{index}:",
            "    .a8", "    .i16",
            # Install source OBNA names through the normal room lifecycle.
            # The controller only reads the existing SCUMM name cache; it does
            # not carry a room/object lookup table of its own.
            "    jsl ScummV5_Matrix_LoadActiveRoomNames_Far_Address",
        ))
        data_lines.extend((
            "    sep #$20", "    .a8",
            "    lda #$%02X" % (len(record["objects"]) // 11),
            "    sta.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
            "    brl ScummV5_Matrix_LoadActiveRoom__return",
        ))
        data_lines.extend((
            f"ScummV5_Matrix_LoadActiveRoom__next_{index}:", "    .a8", ".i16",
        ))
    data_lines.extend((
        "ScummV5_Matrix_LoadActiveRoom__return:",
        "    ply", "    plx", "    plp", "    rtl",
    ))
    # Populate the bounded active-room object-name cache in a separate bank.
    # Keeping this generic room-local operation out of the room-loader control
    # section prevents OBNA growth from relocating its lifecycle branches.
    name_routine_start = len(data_lines)
    matrix_helper_bank = bank
    bank = next_free_bank(bank + 1)
    data_lines.extend((
        f".bank {bank}", ".org $8000",
        "ScummV5_Matrix_LoadActiveRoomNames_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_LoadNames_Far",
        ".endif",
        "    sep #$20", "    .a8", "    rep #$10", "    .i16",
        "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        data_lines.extend((
            f"    cmp #${index:02X}",
            f"    beq ScummV5_Matrix_LoadActiveRoomNames__match_{index}",
            f"    brl ScummV5_Matrix_LoadActiveRoomNames__next_{index}",
            f"ScummV5_Matrix_LoadActiveRoomNames__match_{index}:", "    .a8", "    .i16",
            "    ldy #$0000",
        ))
        for name_index, (object_id, name) in enumerate(record["object_names"]):
            if object_id >= 0x0400:
                continue
            name_length = min(len(name), 0x20)
            data_lines.extend((
                "    sep #$20", "    .a8", "    rep #$10", "    .i16",
                f"    ldy #${(name_index * 0x20):04X}",
                f"    ldx #${(object_id << 5):04X}",
                f"ScummV5_Matrix_LoadActiveRoomNames__copy_{index}_{name_index}:", "    .a8", "    .i16",
            ))
            data_lines.extend((
                "    phx",
                "    rep #$20", "    .a16", "    tya", "    tax",
                "    sep #$20", "    .a8",
                f"    lda.l ScummV5_SetState_Record_{index}_ObjectNames_Address,x",
                "    plx",
                "    sta.l SAME_SCUMM_OBJECT_NAMES,x",
                "    iny", "    inx",
                f"    cpy #${(name_index + 1) * 0x20:04X}",
                f"    bcc ScummV5_Matrix_LoadActiveRoomNames__copy_{index}_{name_index}",
                f"    lda #${name_length:02X}",
                f"    sta.l SAME_SCUMM_OBJECT_NAME_LENGTH+${object_id:04X}",
            ))
        data_lines.extend((
            "    brl ScummV5_Matrix_LoadActiveRoomNames__done",
            f"ScummV5_Matrix_LoadActiveRoomNames__next_{index}:", "    .a8", "    .i16",
        ))
    data_lines.extend((
        "ScummV5_Matrix_LoadActiveRoomNames__done:",
        "    sep #$20", "    .a8", "    rtl",
    ))
    name_routine_lines = data_lines[name_routine_start + 2:]
    del data_lines[name_routine_start:]
    bank = matrix_helper_bank
    # Fetch one complete immutable BOXD record into the bounded working slot.
    # X is the box index on entry; the active generated room selects the ROM
    # table.  This is deliberately one path for low and high box numbers.
    data_lines.extend((
        "ScummV5_PutActor_LoadGeometry_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_LoadGeometry_Far",
        ".endif",
        "; Input X=u16 box index; output A width=8, X width=16; carry clear",
        "; on success and set on missing record/box. Callers must restore M",
        "; themselves after consuming the carry result.",
        "    sep #$20", "    .a8", "    rep #$10", "    .i16",
        "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        count = len(record["walkbox_flags"])
        data_lines.extend((
            f"    cmp #${index:02X}",
            f"    bne ScummV5_PutActor_LoadGeometry__next_{index}",
            "    rep #$20", "    .a16", f"    cpx #${count:04X}",
            f"    bcs ScummV5_PutActor_LoadGeometry__fail_{index}",
            "    txa", "    asl", "    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0",
            "    asl", "    asl", "    asl",
            "    clc", "    adc.l SAME_SCUMM_PUT_ACTOR_TEMP0", "    tax",
            f"ScummV5_PutActor_LoadGeometry__copy_{index}:",
            "    .a16", "    .i16",
            *sum(([f"lda.l ScummV5_PutActor_Record_{index}_Geometry_Address+{offset:02d},x",
                   f"sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+{offset:02d}"]
                  for offset in range(0, 0x12, 2)), []),
            "    sep #$20", "    .a8", "    clc", "    rtl",
            f"ScummV5_PutActor_LoadGeometry__fail_{index}:",
            "    sep #$20", "    .a8", "    sec", "    rtl",
            f"ScummV5_PutActor_LoadGeometry__next_{index}:", "    .a8",
        ))
    data_lines.extend(("    sec", "    rtl"))
    # Read-only profile-generated queries used by the semantic sentence and
    # movement closures.  All dispatch is selected by active record; no title,
    # room number, object number, verb, or route is embedded in engine code.
    data_lines.extend((
        "ScummV5_ObjectOwner_Query_Far:",
        "; Input X=u16 object; output A=u8 owner, carry set on success.",
        "    rep #$10", "    .i16", "    cpx #SCUMM_M23A_GLOBAL_OBJECT_COUNT",
        "    bcs ScummV5_ObjectOwner_Query_Far__fail", "    sep #$20", "    .a8",
        "    lda.l SAME_SCUMM_OBJECT_OWNERS,x", "    sec", "    rtl",
        "ScummV5_ObjectOwner_Query_Far__fail:", "    sep #$20", "    .a8",
        "    clc", "    rtl",
        "ScummV5_ObjectOwner_LoadInitial_Far:",
        "    rep #$30", "    .a16", "    .i16",
        "    ldx #$0000",
        "ScummV5_ObjectOwner_LoadInitial_Far__copy:",
        "    .a16", "    .i16",
        "    cpx #SCUMM_M23A_GLOBAL_OBJECT_COUNT", "    bcs ScummV5_ObjectOwner_LoadInitial_Far__done",
        "    sep #$20", "    .a8", "    lda.l ScummV5_ObjectOwner_InitialOwners,x",
        "    sta.l SAME_SCUMM_OBJECT_OWNERS,x", "    rep #$20", "    .a16", "    inx",
        "    bra ScummV5_ObjectOwner_LoadInitial_Far__copy",
        "ScummV5_ObjectOwner_LoadInitial_Far__done:",
        "    sep #$20", "    .a8", "    rtl",
    ))
    data_lines.extend((
        "ScummV5_ObjectClass_LoadInitial_Far:",
        "    rep #$30", "    .a16", "    .i16",
        "    lda #$0000", "    ldx #$0000",
        "ScummV5_ObjectClass_LoadInitial_Far__clear:", "    .a16", "    .i16",
        "    sta.l SAME_SCUMM_C16_RECORDS,x", "    inx", "    inx",
        "    cpx #$1000", "    bcc ScummV5_ObjectClass_LoadInitial_Far__clear",
        "    lda #$0000", "    sta.l SAME_SCUMM_C16_MASK_OFFSET",
        "    sta.l SAME_SCUMM_C16_RECORD_OFFSET",
        "ScummV5_ObjectClass_LoadInitial_Far__copy:",
        "    .a16", "    .i16",
        "    lda.l SAME_SCUMM_C16_MASK_OFFSET",
        "    cmp #(ScummV5_ObjectClass_InitialCount * 6)",
        "    bcs ScummV5_ObjectClass_LoadInitial_Far__done",
        "    tax", "    lda.l ScummV5_ObjectClass_Initial,x",
        "    pha", "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    tax",
        "    pla", "    sta.l SAME_SCUMM_C16_RECORDS+2,x",
        "    lda #$0001", "    sta.l SAME_SCUMM_C16_RECORDS,x",
        "    lda.l SAME_SCUMM_C16_MASK_OFFSET", "    clc", "    adc #$0002",
        "    tax", "    lda.l ScummV5_ObjectClass_Initial,x",
        "    pha", "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    tax", "    pla",
        "    sta.l SAME_SCUMM_C16_RECORDS+4,x",
        "    lda.l SAME_SCUMM_C16_MASK_OFFSET", "    clc", "    adc #$0004",
        "    tax", "    lda.l ScummV5_ObjectClass_Initial,x",
        "    pha", "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    tax", "    pla",
        "    sta.l SAME_SCUMM_C16_RECORDS+6,x",
        "    lda.l SAME_SCUMM_C16_MASK_OFFSET", "    clc", "    adc #$0006",
        "    sta.l SAME_SCUMM_C16_MASK_OFFSET",
        "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    clc", "    adc #$0008",
        "    sta.l SAME_SCUMM_C16_RECORD_OFFSET",
        "    bra ScummV5_ObjectClass_LoadInitial_Far__copy",
        "ScummV5_ObjectClass_LoadInitial_Far__done:",
        "    sep #$20", "    .a8", "    lda #$01", "    sta.l SAME_SCUMM_C16_INITIALIZED", "    rtl",
        "ScummV5_ObjectClass_ApplyScenarioOverlay_Far:",
        "    sep #$20", "    .a8",
        f"    lda #${len(scenario_class_overlays):02X}",
        "    beq ScummV5_ObjectClass_ApplyScenarioOverlay_Far__done",
    ))
    for overlay_index, (object_id, mask) in enumerate(scenario_class_overlays):
        data_lines.extend((
            "    rep #$20", "    .a16", f"    lda #${object_id:04X}",
            "    sta.l SAME_SCUMM_C16_OBJECT", "    jsl ScummV5_C16_FindRecord_Far",
            "    lda.l SAME_SCUMM_C16_RECORD_OFFSET", "    cmp #$FFFF",
            f"    beq ScummV5_ObjectClass_ApplyScenarioOverlay_Far__next_{overlay_index}",
            "    tax", f"    lda.l SAME_SCUMM_C16_RECORDS+4,x", "    ora #${:04X}".format(mask & 0xFFFF),
            "    sta.l SAME_SCUMM_C16_RECORDS+4,x", f"    lda.l SAME_SCUMM_C16_RECORDS+6,x",
            "    ora #${:04X}".format((mask >> 16) & 0xFFFF), "    sta.l SAME_SCUMM_C16_RECORDS+6,x",
            f"ScummV5_ObjectClass_ApplyScenarioOverlay_Far__next_{overlay_index}:",
        ))
    data_lines.extend((
        "ScummV5_ObjectClass_ApplyScenarioOverlay_Far__done:",
        "    sep #$20", "    .a8", "    rtl",
    ))
    data_lines.extend((
        "ScummV5_Bit_ApplyScenarioOverlay_Far:",
        "    php", "    rep #$30", "    .a16", "    .i16",
        f"    lda #${len(scenario_bit_overlays):02X}",
        "    beq ScummV5_Bit_ApplyScenarioOverlay_Far__done",
    ))
    for bit in scenario_bit_overlays:
        byte_index, bit_index = divmod(bit, 8)
        data_lines.extend((
            f"    ldx #${byte_index:04X}",
            "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_C7_BITS,x",
            f"    ora #${1 << bit_index:02X}", "    sta.l SAME_SCUMM_C7_BITS,x",
        ))
    data_lines.extend((
        "ScummV5_Bit_ApplyScenarioOverlay_Far__done:",
        "    plp", "    rtl",
        "ScummV5_ObjectState_ApplyScenarioOverlay_Far:", "    sep #$20", "    .a8",
        f"    lda #${len(scenario_state_overlays):02X}",
        "    beq ScummV5_ObjectState_ApplyScenarioOverlay_Far__done",
    ))
    for object_id, state in scenario_state_overlays:
        data_lines.extend((f"    lda #${state:02X}",
                           f"    sta.l SAME_SCUMM_OBJECT_STATES+${object_id:04X}"))
    data_lines.extend((
        "ScummV5_ObjectState_ApplyScenarioOverlay_Far__done:", "    rtl",
        "ScummV5_Movement_NextBox_Far:",
        "; Inputs scratch source/destination; output A=u8 next box, carry set.",
        "    sep #$20", "    .a8",
        "    lda.l SAME_SCUMM_MATRIX_DYNAMIC_VALID",
        "    beq ScummV5_Movement_NextBox_Far__static",
        "    jml ScummV5_Movement_NextBox_Dynamic_Far",
        "ScummV5_Movement_NextBox_Far__static:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_NextBox_Far",
        ".else",
        "    .a8",
        "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        count = len(record["walkbox_flags"])
        data_lines.extend((
            f"    cmp #${index:02X}", f"    beq ScummV5_Movement_NextBox_Far__match_{index}",
            f"    brl ScummV5_Movement_NextBox_Far__next_{index}",
            f"ScummV5_Movement_NextBox_Far__match_{index}:",
            "    .a8",
            "    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE", f"    cmp #${count:02X}",
            f"    bcc ScummV5_Movement_NextBox_Far__source_ok_{index}",
            "    brl ScummV5_Movement_NextBox_Far__fail",
            f"ScummV5_Movement_NextBox_Far__source_ok_{index}:",
            "    .a8",
            "    lda.l SAME_SCUMM_MOVE_ROUTE_DEST", f"    cmp #${count:02X}",
            f"    bcc ScummV5_Movement_NextBox_Far__dest_ok_{index}",
            "    brl ScummV5_Movement_NextBox_Far__fail",
            f"ScummV5_Movement_NextBox_Far__dest_ok_{index}:",
            "    rep #$20", "    .a16", "    and #$00FF",
            "    sta.l SAME_SCUMM_MOVE_ROUTE_DEST",
            "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE",
            "    rep #$20", "    .a16", "    and #$00FF",
            f"    sta.l SAME_SCUMM_MOVE_TEMP", f"    lda #${count:04X}",
            "    sta.l SAME_SCUMM_MOVE_TEMP2", "    lda #$0000",
            f"ScummV5_Movement_NextBox_Far__mul_{index}:",
            "    clc", "    adc.l SAME_SCUMM_MOVE_TEMP", "    pha",
            "    lda.l SAME_SCUMM_MOVE_TEMP2", "    dec", "    sta.l SAME_SCUMM_MOVE_TEMP2",
            f"    beq ScummV5_Movement_NextBox_Far__mul_done_{index}", "    pla",
            f"    bra ScummV5_Movement_NextBox_Far__mul_{index}",
            f"ScummV5_Movement_NextBox_Far__mul_done_{index}:", "    pla",
            "    clc", "    adc.l SAME_SCUMM_MOVE_ROUTE_DEST", "    tax",
            "    sep #$20", "    .a8", f"    lda.l ScummV5_Movement_Record_{index}_Routes_Address,x",
            "    cmp #$FF", f"    bne ScummV5_Movement_NextBox_Far__success_{index}",
            "    brl ScummV5_Movement_NextBox_Far__fail",
            f"ScummV5_Movement_NextBox_Far__success_{index}:", "    sec", "    rtl",
            f"ScummV5_Movement_NextBox_Far__next_{index}:", "    .a8",
        ))
    data_lines.extend(("ScummV5_Movement_NextBox_Far__fail:", "    clc", "    rtl", ".endif"))
    data_lines.extend((
        "ScummV5_Movement_Portal_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_Portal_Far",
        ".else",
        "; Inputs route source and route-next; publishes canonical shared edge.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        count = len(record["walkbox_flags"])
        data_lines.extend((
            f"    cmp #${index:02X}", f"    beq ScummV5_Movement_Portal_Far__match_{index}",
            f"    brl ScummV5_Movement_Portal_Far__next_{index}",
            f"ScummV5_Movement_Portal_Far__match_{index}:",
            "    .a8",
            "    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE", f"    cmp #${count:02X}",
            f"    bcc ScummV5_Movement_Portal_Far__source_ok_{index}",
            "    brl ScummV5_Movement_Portal_Far__fail",
            f"ScummV5_Movement_Portal_Far__source_ok_{index}:",
            "    .a8",
            "    lda.l SAME_SCUMM_MOVE_ROUTE_NEXT", f"    cmp #${count:02X}",
            f"    bcc ScummV5_Movement_Portal_Far__next_ok_{index}",
            "    brl ScummV5_Movement_Portal_Far__fail",
            f"ScummV5_Movement_Portal_Far__next_ok_{index}:",
            "    rep #$20", "    .a16", "    and #$00FF",
            "    sta.l SAME_SCUMM_MOVE_ROUTE_DEST",
            "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE",
            "    rep #$20", "    .a16", "    and #$00FF", "    sta.l SAME_SCUMM_MOVE_TEMP",
            f"    lda #${count:04X}", "    sta.l SAME_SCUMM_MOVE_TEMP2", "    lda #$0000",
            f"ScummV5_Movement_Portal_Far__mul_{index}:",
            "    clc", "    adc.l SAME_SCUMM_MOVE_TEMP", "    pha",
            "    lda.l SAME_SCUMM_MOVE_TEMP2", "    dec", "    sta.l SAME_SCUMM_MOVE_TEMP2",
            f"    beq ScummV5_Movement_Portal_Far__mul_done_{index}", "    pla",
            f"    bra ScummV5_Movement_Portal_Far__mul_{index}",
            f"ScummV5_Movement_Portal_Far__mul_done_{index}:", "    pla",
            "    clc", "    adc.l SAME_SCUMM_MOVE_ROUTE_DEST",
            "    sta.l SAME_SCUMM_MOVE_TEMP",
            "    asl", "    asl", "    asl", "    sec", "    sbc.l SAME_SCUMM_MOVE_TEMP",
            "    tax", "    sep #$20", "    .a8",
            f"    lda.l ScummV5_Movement_Record_{index}_Portals_Address,x",
            "    sta.l SAME_SCUMM_MOVE_PORTAL_TYPE", f"    bne ScummV5_Movement_Portal_Far__success_{index}",
            "    brl ScummV5_Movement_Portal_Far__fail",
            f"ScummV5_Movement_Portal_Far__success_{index}:",
            "    rep #$20", "    .a16",
            # Keep the far-bank relocation on the base symbol.  Poppy 0.7
            # currently drops the bank byte from ``far_label+N,x`` operands,
            # so advance X to each packed field instead of applying an
            # arithmetic expression to the long label.
            "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_Portals_Address,x", "    sta.l SAME_SCUMM_MOVE_PORTAL_FIXED",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_Portals_Address,x", "    sta.l SAME_SCUMM_MOVE_PORTAL_LOW",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_Portals_Address,x", "    sta.l SAME_SCUMM_MOVE_PORTAL_HIGH",
            "    sep #$20", "    .a8", "    sec", "    rtl",
            f"ScummV5_Movement_Portal_Far__next_{index}:", "    .a8",
        ))
    data_lines.extend(("ScummV5_Movement_Portal_Far__fail:", "    sep #$20", "    .a8", "    clc", "    rtl", ".endif"))
    data_lines.extend((
        "ScummV5_Movement_ObjectWalk_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_ObjectWalk_Far",
        ".else",
        "; Input object in scratch; output walk x/y/direction in scratch, carry set.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        data_lines.extend((
            f"    cmp #${index:02X}", f"    beq ScummV5_Movement_ObjectWalk_Far__match_{index}",
            f"    brl ScummV5_Movement_ObjectWalk_Far__next_{index}",
            f"ScummV5_Movement_ObjectWalk_Far__match_{index}:",
            "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
            f"ScummV5_Movement_ObjectWalk_Far__scan_{index}:",
            "    .a16", "    .i16",
            f"    cpx #${len(record['object_walk']):04X}",
            f"    bcc ScummV5_Movement_ObjectWalk_Far__scan_ok_{index}",
            "    brl ScummV5_Movement_ObjectWalk_Far__fail",
            f"ScummV5_Movement_ObjectWalk_Far__scan_ok_{index}:",
            "    .a16", "    .i16",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk_Address,x",
            "    cmp.l SAME_SCUMM_MOVE_OBJECT", f"    beq ScummV5_Movement_ObjectWalk_Far__found_{index}",
            "    txa", "    clc", "    adc #$000C", "    tax",
            f"    bra ScummV5_Movement_ObjectWalk_Far__scan_{index}",
            f"ScummV5_Movement_ObjectWalk_Far__found_{index}:",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk_Address,x",
            "    sta.l SAME_SCUMM_MOVE_REQUEST_X",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk_Address,x",
            "    sta.l SAME_SCUMM_MOVE_REQUEST_Y", "    sep #$20", "    .a8",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk_Address,x",
            "    sta.l SAME_SCUMM_MOVE_QUERY_DIR",
            "    inx", "    rep #$20", "    .a16",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk_Address,x",
            "    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X",
            "    inx", "    inx",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk_Address,x",
            "    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y",
            "    inx", "    inx", "    sep #$20", "    .a8",
            f"    lda.l ScummV5_Movement_Record_{index}_ObjectWalk_Address,x",
            "    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX", "    sec", "    rtl",
            f"ScummV5_Movement_ObjectWalk_Far__next_{index}:", "    .a8",
        ))
    data_lines.extend(("ScummV5_Movement_ObjectWalk_Far__fail:", "    sep #$20", "    .a8", "    clc", "    rtl", ".endif"))
    # Generic room-coordinate hit testing over the same source-backed object
    # records used by setState.  The records are copied to RAM at room load;
    # no room-specific hotspot or object policy is encoded here.  Reverse
    # source order gives the later OBCD the canonical frontmost precedence.
    def long_cond(condition, target, tag):
        inverse = {"bcc": "bcs", "bcs": "bcc", "beq": "bne", "bne": "beq"}[condition]
        return (
            f"    {inverse} ScummV5_LongBranch_{tag}",
            f"    brl {target}",
            f"ScummV5_LongBranch_{tag}:",
            "    rep #$30", "    .a16", "    .i16",
        )

    # These static lookup services use the same dense record index as the
    # active-room directory and the tables emitted above.  Keeping a second,
    # accidentally empty list made ROM-backed builds emit empty hit-test and
    # verb-query dispatchers while the live-room provider path worked from
    # its validated resource.  Preserve one source of truth for both paths.
    interaction_records = records
    data_lines.extend((
        "ScummV5_Object_HitTest_Far:",
        "; Input SAME_SCUMM_INTERACTION_X/Y; output object/flags, carry on hit.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(interaction_records):
        object_bytes = len(record["objects"])
        data_lines.extend((
            f"    cmp #${index:02X}",
            *long_cond("beq", f"ScummV5_Object_HitTest_Far__record_{index}", f"hit_dispatch_{index}"),
            f"    brl ScummV5_Object_HitTest_Far__next_{index}",
            f"ScummV5_Object_HitTest_Far__record_{index}:",
            "    rep #$30", "    .a16", "    .i16",
            f"    ldx #${max(0, object_bytes - 11):04X}",
            f"ScummV5_Object_HitTest_Far__scan_{index}:",
            "    rep #$30", "    .a16", "    .i16",
            f"    cpx #$0000", *long_cond("bcc", "ScummV5_Object_HitTest_Far__miss", f"hit_{index}_neg"),
            f"    cpx #${object_bytes:04X}",
            *long_cond("bcs", "ScummV5_Object_HitTest_Far__miss", f"hit_{index}_end"),
            "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+10,x",
            "    and #$0080",
            *long_cond("bne", f"ScummV5_Object_HitTest_Far__next_object_{index}", f"hit_{index}_hidden"),
            "    txa", "    sta.l SAME_SCUMM_INTERACTION_LIMIT",
            "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS,x",
            "    tay",
            "    tax",
            "    lda.l SAME_SCUMM_OBJECT_STATES,x",
            "    and #$0002",  # canonical object-state untouchable bit
            *long_cond("bne", f"ScummV5_Object_HitTest_Far__state_skip_{index}", f"hit_{index}_state"),
            "    lda.l SAME_SCUMM_OBJECT_OWNERS,x",
            *long_cond("bne", f"ScummV5_Object_HitTest_Far__state_skip_{index}", f"hit_{index}_owner"),
            "    lda.l SAME_SCUMM_INTERACTION_LIMIT", "    tax",
            "    lda.l SAME_SCUMM_INTERACTION_X",
            "    cmp.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+2,x",
            *long_cond("bcc", f"ScummV5_Object_HitTest_Far__next_object_{index}", f"hit_{index}_x0"),
            "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+2,x",
            "    clc",
            "    adc.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+6,x",
            "    sta.l SAME_SCUMM_INTERACTION_LIMIT",
            "    lda.l SAME_SCUMM_INTERACTION_X",
            "    cmp.l SAME_SCUMM_INTERACTION_LIMIT",
            *long_cond("bcs", f"ScummV5_Object_HitTest_Far__next_object_{index}", f"hit_{index}_x1"),
            "    lda.l SAME_SCUMM_INTERACTION_Y",
            "    cmp.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+4,x",
            *long_cond("bcc", f"ScummV5_Object_HitTest_Far__next_object_{index}", f"hit_{index}_y0"),
            "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+4,x",
            "    clc",
            "    adc.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+8,x",
            "    sta.l SAME_SCUMM_INTERACTION_LIMIT",
            "    lda.l SAME_SCUMM_INTERACTION_Y",
            "    cmp.l SAME_SCUMM_INTERACTION_LIMIT",
            *long_cond("bcs", f"ScummV5_Object_HitTest_Far__next_object_{index}", f"hit_{index}_y1"),
            "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS,x",
            "    sta.l SAME_SCUMM_INTERACTION_OBJECT",
            "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+10,x",
            "    sep #$20", "    .a8", "    sta.l SAME_SCUMM_INTERACTION_FLAGS",
            "    sec", "    rtl",
            f"ScummV5_Object_HitTest_Far__state_skip_{index}:",
            "    lda.l SAME_SCUMM_INTERACTION_LIMIT", "    tax",
            f"    brl ScummV5_Object_HitTest_Far__next_object_{index}",
            f"ScummV5_Object_HitTest_Far__next_object_{index}:",
            "    rep #$30", "    .a16", "    .i16",
            "    cpx #$0000",
            *long_cond("beq", "ScummV5_Object_HitTest_Far__miss", f"hit_{index}_done"),
            "    txa", "    sec", "    sbc #$000B", "    tax",
            f"    brl ScummV5_Object_HitTest_Far__scan_{index}",
        ))
        data_lines.extend((
            f"ScummV5_Object_HitTest_Far__next_{index}:", "    sep #$20", "    .a8",
        ))
    data_lines.extend((
        "ScummV5_Object_HitTest_Far__miss:",
        "    rep #$20", "    .a16", "    lda #$0000",
        "    sta.l SAME_SCUMM_INTERACTION_OBJECT",
        "    sep #$20", "    .a8", "    clc", "    rtl",
    ))
    # Enumerate explicit authored verbs from the generated OBCD directory.
    # 0xFF fallback handlers remain executable through Verb_Query but are not
    # presented as a cursor verb.  Next wraps in source order.
    data_lines.extend((
        "ScummV5_Verb_First_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_VerbFirst_Far",
        ".endif",
        "; Input SAME_SCUMM_VERB_OBJECT; output verb in SAME_SCUMM_VERB_RESULT.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(interaction_records):
        entries = record["verb_entries"]
        data_lines.extend((
            f"    cmp #${index:02X}", *long_cond("beq", f"ScummV5_Verb_First_Far__record_{index}", f"verb_first_dispatch_{index}"),
            f"    brl ScummV5_Verb_First_Far__next_{index}",
            f"ScummV5_Verb_First_Far__record_{index}:",
            "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
        ))
        for entry_index, (object_id, verb, _offset) in enumerate(entries):
            data_lines.extend((
                f"    lda #${object_id:04X}", "    cmp.l SAME_SCUMM_VERB_OBJECT",
                f"    bne ScummV5_Verb_First_Far__skip_{index}_{entry_index}",
                f"    lda #${verb:04X}", "    cmp #$00FF",
                f"    beq ScummV5_Verb_First_Far__skip_{index}_{entry_index}",
                "    sta.l SAME_SCUMM_VERB_RESULT", "    sec", "    rtl",
                f"ScummV5_Verb_First_Far__skip_{index}_{entry_index}:",
                "    rep #$30", "    .a16", "    .i16",
            ))
        data_lines.extend((
            "    brl ScummV5_Verb_First_Far__miss",
            f"ScummV5_Verb_First_Far__next_{index}:", "    sep #$20", "    .a8",
        ))
    data_lines.extend((
        "ScummV5_Verb_First_Far__miss:", "    rep #$20", "    .a16",
        "    lda #$0000", "    sta.l SAME_SCUMM_VERB_RESULT",
        "    sep #$20", "    .a8", "    clc", "    rtl",
        "ScummV5_Verb_Next_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_VerbNext_Far",
        ".endif",
        "; Input object/current verb; output next explicit authored verb, wrapping.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(interaction_records):
        entries = record["verb_entries"]
        data_lines.extend((
            f"    cmp #${index:02X}", *long_cond("beq", f"ScummV5_Verb_Next_Far__record_{index}", f"verb_next_dispatch_{index}"),
            f"    brl ScummV5_Verb_Next_Far__next_{index}",
            f"ScummV5_Verb_Next_Far__record_{index}:",
            "    rep #$30", "    .a16", "    .i16",
            "    lda #$0000", "    sta.l SAME_SCUMM_INTERACTION_VERB_FIRST",
            "    sta.l SAME_SCUMM_INTERACTION_VERB_AFTER",
        ))
        for entry_index, (object_id, verb, _offset) in enumerate(entries):
            data_lines.extend((
                f"    lda #${object_id:04X}", "    cmp.l SAME_SCUMM_VERB_OBJECT",
                f"    bne ScummV5_Verb_Next_Far__skip_{index}_{entry_index}",
                f"    lda #${verb:04X}", "    cmp #$00FF",
                f"    beq ScummV5_Verb_Next_Far__skip_{index}_{entry_index}",
                "    lda.l SAME_SCUMM_INTERACTION_VERB_AFTER",
                f"    bne ScummV5_Verb_Next_Far__candidate_{index}_{entry_index}",
                "    sta.l SAME_SCUMM_INTERACTION_VERB_FIRST",
                "    cmp.l SAME_SCUMM_VERB_ID",
                f"    bne ScummV5_Verb_Next_Far__skip_{index}_{entry_index}",
                "    lda #$0001", "    sta.l SAME_SCUMM_INTERACTION_VERB_AFTER",
                f"    bra ScummV5_Verb_Next_Far__skip_{index}_{entry_index}",
                f"ScummV5_Verb_Next_Far__candidate_{index}_{entry_index}:",
                "    sta.l SAME_SCUMM_VERB_RESULT", "    sec", "    rtl",
                f"ScummV5_Verb_Next_Far__skip_{index}_{entry_index}:",
                "    rep #$30", "    .a16", "    .i16",
            ))
        data_lines.extend((
            "    lda.l SAME_SCUMM_INTERACTION_VERB_FIRST",
            *long_cond("beq", "ScummV5_Verb_Next_Far__miss", f"verb_next_miss_{index}"),
            "    sta.l SAME_SCUMM_VERB_RESULT", "    sec", "    rtl",
            f"ScummV5_Verb_Next_Far__next_{index}:", "    sep #$20", "    .a8",
        ))
    data_lines.extend((
        "ScummV5_Verb_Next_Far__miss:", "    rep #$20", "    .a16",
        "    lda #$0000", "    sta.l SAME_SCUMM_VERB_RESULT",
        "    sep #$20", "    .a8", "    clc", "    rtl",
    ))
    # Compact runtime interaction index.  The old generated verb dispatch
    # remains available to the canonical query path; these four-byte records
    # let the controller enumerate the active room's authored explicit verbs
    # without duplicating a large routine for every room and entry.
    flat_verb_entries = [
        (room_index, object_id, verb)
        for room_index, record in enumerate(records)
        for object_id, verb, _offset in record["verb_entries"]
        if verb != 0xFF
    ]
    if args.msu1_live_room_resources:
        # Live-mode controller enumeration uses the active SC5LIVE verb table.
        # The global flattened table would otherwise be an unvalidated shadow.
        flat_verb_entries = []
    data_lines.append("ScummV5_Interaction_Verb_Table:")
    if flat_verb_entries:
        for start in range(0, len(flat_verb_entries), 16):
            row = flat_verb_entries[start:start + 16]
            data_lines.append("    .byte " + ",".join(
                f"${room:02X},${object_id & 0xFF:02X},${object_id >> 8:02X},${verb:02X}"
                for room, object_id, verb in row
            ))
    else:
        data_lines.append("    .byte $00,$00,$00,$00")
    table_bytes = max(4, len(flat_verb_entries) * 4)
    data_lines.extend((
        "ScummV5_Generic_Object_HitTest_Far:",
        "    rep #$30", "    .a16", "    .i16",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_SETSTATE_LOCAL_COUNT", "    bne ScummV5_Generic_Object_HitTest_Far__have_records",
        "    brl ScummV5_Generic_Object_HitTest_Far__miss",
        "ScummV5_Generic_Object_HitTest_Far__have_records:",
        "    rep #$20", "    .a16", "    lda #$0000", "    sep #$20", "    .a8",
        "    lda.l SAME_SCUMM_SETSTATE_LOCAL_COUNT", "    rep #$20", "    .a16",
        "    ldx #$0000", "    ldy #$0000",
        "ScummV5_Generic_Object_HitTest_Far__loop:", "    rep #$30", "    .a16", "    .i16",
        "    rep #$30", "    .a16", "    .i16",
        "    tya", "    cmp.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
        "    bcs ScummV5_Generic_Object_HitTest_Far__miss",
        "    lda.l SAME_SCUMM_INTERACTION_X", "    cmp.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+2,x",
        "    bcc ScummV5_Generic_Object_HitTest_Far__next",
        "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+2,x", "    clc",
        "    adc.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+6,x", "    sta.l SAME_SCUMM_INTERACTION_LIMIT",
        "    lda.l SAME_SCUMM_INTERACTION_X", "    cmp.l SAME_SCUMM_INTERACTION_LIMIT",
        "    bcs ScummV5_Generic_Object_HitTest_Far__next",
        "    lda.l SAME_SCUMM_INTERACTION_Y", "    cmp.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+4,x",
        "    bcc ScummV5_Generic_Object_HitTest_Far__next",
        "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+4,x", "    clc",
        "    adc.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+8,x", "    sta.l SAME_SCUMM_INTERACTION_LIMIT",
        "    lda.l SAME_SCUMM_INTERACTION_Y", "    cmp.l SAME_SCUMM_INTERACTION_LIMIT",
        "    bcs ScummV5_Generic_Object_HitTest_Far__next",
        "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS,x", "    sta.l SAME_SCUMM_INTERACTION_OBJECT",
        "    tya", "    sta.l SAME_SCUMM_INTERACTION_INDEX",
        "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+10,x", "    sep #$20", "    .a8",
        "    sta.l SAME_SCUMM_INTERACTION_FLAGS", "    sec", "    rtl",
        "ScummV5_Generic_Object_HitTest_Far__next:",
        "    rep #$30", "    .a16", "    .i16",
        "    iny", "    txa", "    clc", "    adc #$000B", "    tax",
        "    brl ScummV5_Generic_Object_HitTest_Far__loop",
        "ScummV5_Generic_Object_HitTest_Far__miss:", "    rep #$30", "    .a16", "    .i16",
        "    lda #$0000", "    sta.l SAME_SCUMM_INTERACTION_OBJECT", "    sep #$20", "    .a8", "    clc", "    rtl",
        "ScummV5_Generic_Object_ValidateSelected_Far:",
        "    rep #$30", "    .a16", "    .i16",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
        "    bne ScummV5_Generic_Object_ValidateSelected_Far__have_records",
        "    brl ScummV5_Generic_Object_ValidateSelected_Far__miss",
        "ScummV5_Generic_Object_ValidateSelected_Far__have_records:",
        "    rep #$20", "    .a16", "    ldx #$0000", "    ldy #$0000",
        "ScummV5_Generic_Object_ValidateSelected_Far__loop:",
        "    rep #$30", "    .a16", "    .i16",
        "    sep #$20", "    .a8",
        "    lda.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
        "    rep #$20", "    .a16",
        "    and #$00FF", "    sta.l SAME_SCUMM_INTERACTION_LIMIT",
        "    tya", "    cmp.l SAME_SCUMM_INTERACTION_LIMIT",
        "    bcs ScummV5_Generic_Object_ValidateSelected_Far__miss",
        "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS,x",
        "    cmp.l SAME_SCUMM_CONTROLLER_OBJECT",
        "    beq ScummV5_Generic_Object_ValidateSelected_Far__found",
        "    iny", "    txa", "    clc", "    adc #$000B", "    tax",
        "    brl ScummV5_Generic_Object_ValidateSelected_Far__loop",
        "ScummV5_Generic_Object_ValidateSelected_Far__found:",
        "    rep #$30", "    .a16", "    .i16",
        "    lda.l SAME_SCUMM_CONTROLLER_OBJECT",
        "    sta.l SAME_SCUMM_INTERACTION_OBJECT",
        "    tya", "    sta.l SAME_SCUMM_INTERACTION_INDEX",
        "    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+10,x",
        "    sep #$20", "    .a8", "    sta.l SAME_SCUMM_INTERACTION_FLAGS",
        "    sec", "    rtl",
        "ScummV5_Generic_Object_ValidateSelected_Far__miss:",
        "    rep #$30", "    .a16", "    .i16",
        "    lda #$0000", "    sta.l SAME_SCUMM_INTERACTION_OBJECT",
        "    sep #$20", "    .a8", "    clc", "    rtl",
        "ScummV5_Generic_Verb_First_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_GenericVerbFirst_Far",
        ".endif",
        "    rep #$30", "    .a16", "    .i16",
    ))
    for entry_index, (_room, object_id, verb) in enumerate(flat_verb_entries):
        data_lines.extend((
            f"    lda #${object_id:04X}", "    cmp.l SAME_SCUMM_INTERACTION_OBJECT",
            f"    bne ScummV5_Generic_Verb_First_Far__skip_{entry_index}",
            f"    lda #${verb:04X}", "    cmp #$00FF",
            f"    beq ScummV5_Generic_Verb_First_Far__skip_{entry_index}",
            "    sta.l SAME_SCUMM_VERB_RESULT", "    sec", "    rtl",
            f"ScummV5_Generic_Verb_First_Far__skip_{entry_index}:", "    .a16",
        ))
    data_lines.extend((
        "    sep #$20", "    .a8", "    lda #$00", "    sta.l SAME_SCUMM_VERB_RESULT", "    clc", "    rtl",
        "ScummV5_Generic_Verb_Next_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_GenericVerbNext_Far",
        ".endif",
        "    rep #$30", "    .a16", "    .i16", "    lda #$0000", "    sta.l SAME_SCUMM_INTERACTION_VERB_FIRST",
        "    lda #$0000", "    sta.l SAME_SCUMM_INTERACTION_VERB_AFTER",
    ))
    for entry_index, (_room, object_id, verb) in enumerate(flat_verb_entries):
        data_lines.extend((
            f"    lda #${object_id:04X}", "    cmp.l SAME_SCUMM_INTERACTION_OBJECT",
            f"    bne ScummV5_Generic_Verb_Next_Far__skip_{entry_index}",
            f"    lda #${verb:04X}", "    cmp #$00FF",
            f"    beq ScummV5_Generic_Verb_Next_Far__skip_{entry_index}",
            "    sta.l SAME_SCUMM_INTERACTION_LIMIT",
            "    lda.l SAME_SCUMM_INTERACTION_VERB_AFTER",
            f"    bne ScummV5_Generic_Verb_Next_Far__return_{entry_index}",
            "    lda.l SAME_SCUMM_INTERACTION_LIMIT", "    cmp.l SAME_SCUMM_VERB_ID",
            f"    bne ScummV5_Generic_Verb_Next_Far__skip_{entry_index}",
            "    lda #$0001", "    sta.l SAME_SCUMM_INTERACTION_VERB_AFTER",
            # The matching verb only arms the cycle.  Continue scanning so
            # the next authored entry is returned; falling through to the
            # return label would return the current verb again forever.
            f"    bra ScummV5_Generic_Verb_Next_Far__skip_{entry_index}",
            f"ScummV5_Generic_Verb_Next_Far__return_{entry_index}:",
            "    lda.l SAME_SCUMM_INTERACTION_LIMIT", "    sta.l SAME_SCUMM_VERB_RESULT", "    sec", "    rtl",
            f"ScummV5_Generic_Verb_Next_Far__skip_{entry_index}:", "    .a16",
        ))
    data_lines.extend((
        "    sep #$20", "    .a8", "    lda #$00", "    sta.l SAME_SCUMM_VERB_RESULT", "    clc", "    rtl",
    ))
    # OBCD verb dispatch grows with the complete executable directory. Keep
    # the variable-size query/resolve tail in its own generated bank; a valid
    # source profile can otherwise push its labels past $FFFF while Poppy
    # still emits a ROM image, yielding invalid JSL targets at runtime.
    bank += 1
    bank = next_free_bank(bank)
    data_lines.extend((f".bank {bank}", ".org $8000"))
    data_lines.extend((
        "ScummV5_Verb_Query_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_VerbQuery_Far",
        ".endif",
        "; Inputs object/verb scratch; output u16 OBCD-relative entry in result.",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
        "    sta.l $7E5465",
        "    rep #$20", "    .a16", "    lda.l SAME_SCUMM_VERB_OBJECT", "    sta.l $7E5466",
        "    lda.l SAME_SCUMM_VERB_ID", "    sta.l $7E5468",
        f"    lda.l ScummV5_Verb_Record_0_Entries_Address", "    sta.l $7E546A",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        entries = record["verb_entries"]
        lookup = [
            f"    cmp #${index:02X}", f"    beq ScummV5_Verb_Query_Far__match_{index}",
            f"    brl ScummV5_Verb_Query_Far__next_{index}",
            f"ScummV5_Verb_Query_Far__match_{index}:",
            "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
        ]
        for entry_index, (object_id, verb, offset) in enumerate(entries):
            skip = f"ScummV5_Verb_Query_Far__skip_{index}_{entry_index}"
            found = f"ScummV5_Verb_Query_Far__found_{index}_{entry_index}"
            nxt = f"ScummV5_Verb_Query_Far__entry_{index}_{entry_index + 1}"
            lookup.extend((
                f"    lda #${object_id:04X}", "    cmp.l SAME_SCUMM_VERB_OBJECT",
                f"    bne {skip}", f"    lda #${verb:04X}",
                "    cmp.l SAME_SCUMM_VERB_ID", f"    beq {found}",
                "    cmp #$00FF", f"    beq {found}",
                f"{skip}:", "    .a16", f"    bra {nxt}", f"{found}:", "    .a16",
                f"    lda #${offset:04X}", "    sta.l SAME_SCUMM_VERB_RESULT",
                "    sec", "    rtl", f"{nxt}:", "    .a16",
            ))
        lookup.extend((
            "    brl ScummV5_Verb_Query_Far__absent",
            f"ScummV5_Verb_Query_Far__next_{index}:",
            # The scan leaves A holding the last verb-table value.  Reload
            # the room generation's active record before selecting the next
            # table; otherwise a miss in an earlier room can dispatch based
            # on arbitrary table data instead of the current room. The load
            # is 8-bit, but the generated record comparisons are 16-bit:
            # explicitly clear A's stale high byte before widening it.
            "    sep #$20", "    .a8",
            "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
            "    rep #$20", "    .a16", "    and #$00FF",
        ))
        data_lines.extend(lookup)
    data_lines.extend((
        "ScummV5_Verb_Query_Far__absent:", "    .a16", "    lda #$0000",
        "    sta.l SAME_SCUMM_VERB_RESULT", "    sec", "    rtl",
    ))
    data_lines.extend((
        "ScummV5_ObjectProgram_Resolve_Far:",
        ".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES",
        "    jml ScummV5_LiveRoom_ObjectProgramResolve_Far",
        ".endif",
        "; Inputs object/verb scratch; output A=u8 OBCD program, entry in verb result.",
        "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
        "    sta.l $7E545C",
        "    rep #$20",
        "    .a16",
        "    lda.l SAME_SCUMM_VERB_OBJECT",
        "    sta.l $7E545D",
        "    sep #$20",
        "    .a8",
        "    jsl ScummV5_Verb_Query_Far", "    bcs ScummV5_ObjectProgram_Resolve_Far__verb_found",
        "    brl ScummV5_ObjectProgram_Resolve_Far__fail",
        "ScummV5_ObjectProgram_Resolve_Far__verb_found:",
        "    rep #$20",
        "    .a16",
        "    lda.l SAME_SCUMM_VERB_RESULT",
        "    sta.l $7E5461",
        "    sep #$20",
        "    .a8",
        "    rep #$20", "    .a16", "    lda.l SAME_SCUMM_VERB_RESULT",
        "    bne ScummV5_ObjectProgram_Resolve_Far__entry_found",
        "    brl ScummV5_ObjectProgram_Resolve_Far__fail16",
        "ScummV5_ObjectProgram_Resolve_Far__entry_found:",
        "    sep #$20", "    .a8", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
    ))
    for index, record in enumerate(records):
        data_lines.extend((
            f"    cmp #${index:02X}",
            f"    bne ScummV5_ObjectProgram_Resolve_Far__record_next_{index}",
            f"    brl ScummV5_ObjectProgram_Resolve_Far__record_{index}",
            f"ScummV5_ObjectProgram_Resolve_Far__record_next_{index}:", "    .a8",
        ))
    # The source-sized object table can exceed a short branch range even in a
    # focused scenario. This cold resolver therefore always uses a long
    # failure transfer.
    data_lines.extend(("    brl ScummV5_ObjectProgram_Resolve_Far__fail",))
    for index, record in enumerate(records):
        data_lines.extend((
            f"ScummV5_ObjectProgram_Resolve_Far__record_{index}:",
            "    rep #$20", "    .a16", "    lda.l SAME_SCUMM_VERB_OBJECT",
        ))
        for object_index, item in enumerate(record["object_programs"]):
            if not item["executable"]:
                continue
            unit_label = program_label_id(
                item["id"], dynamic=args.dynamic_program_residency,
            )
            match = f"ScummV5_ObjectProgram_Resolve_Far__object_match_{index}_{object_index}"
            data_lines.extend((
                f"    cmp #${item['number']:04X}",
                f"    bne {match}",
                f"    brl ScummV5_ObjectProgram_Resolve_Far__object_{unit_label}",
                f"{match}:",
                "    .a16",
            ))
        # Room/object dispatch tables can make this cold failure path larger
        # than a short-branch range when a real room is joined to a fixture.
        data_lines.extend(("    brl ScummV5_ObjectProgram_Resolve_Far__fail16",))
        for item in record["object_programs"]:
            if not item["executable"]:
                continue
            unit_label = program_label_id(
                item["id"], dynamic=args.dynamic_program_residency,
            )
            data_lines.extend((
                f"ScummV5_ObjectProgram_Resolve_Far__object_{unit_label}:",
            ))
            if args.dynamic_program_residency:
                data_lines.extend((
                    "    rep #$20", "    .a16", f"    lda #${item['id']:04X}",
                    "    jsl ScummV5_Resident_ResolveProgramUnit_Far",
                    f"    bcs ScummV5_ObjectProgram_Resolve_Far__resident_ok_{unit_label}",
                    "    brl ScummV5_ObjectProgram_Resolve_Far__fail",
                    f"ScummV5_ObjectProgram_Resolve_Far__resident_ok_{unit_label}:",
                    "    sep #$20", "    .a8",
                    "    sta.l $7E5460", "    sec", "    rtl",
                ))
            else:
                data_lines.extend((
                    "    sep #$20", "    .a8", f"    lda #${item['id']:02X}",
                    "    sta.l $7E5460", "    sec", "    rtl",
                ))
    data_lines.extend((
        "ScummV5_ObjectProgram_Resolve_Far__fail16:", "    sep #$20", "    .a8",
        "ScummV5_ObjectProgram_Resolve_Far__fail:", "    clc", "    rtl",
    ))
    data_lines.extend((
        "ScummV5_SetState_Reset_Far:",
        "    rep #$30", "    .a16", "    .i16", "    lda #$0000",
        "    sta.l SAME_SCUMM_SETSTATE_OBJECT",
        "    sta.l SAME_SCUMM_SETSTATE_PC_BEFORE",
        "    sta.l SAME_SCUMM_SETSTATE_PC_AFTER", "    ldx #$0000",
        "ScummV5_SetState_Reset_Far__copy:",
        "    .a16", "    .i16",
        f"    cpx #${len(global_states):04X}",
        "    bcs ScummV5_SetState_Reset_Far__tail",
        "    sep #$20", "    .a8",
        "    lda.l ScummV5_SetState_InitialStates,x",
        "    sta.l SAME_SCUMM_OBJECT_STATES,x", "    rep #$20", "    .a16",
        "    inx", "    bra ScummV5_SetState_Reset_Far__copy",
        "ScummV5_SetState_Reset_Far__tail:",
        "    sep #$20", "    .a8", "    lda #$00",
        "ScummV5_SetState_Reset_Far__clear:",
        "    .a8", "    .i16",
        "    cpx #$1000", "    bcs ScummV5_SetState_Reset_Far__done",
        "    sta.l SAME_SCUMM_OBJECT_STATES,x", "    inx",
        "    bra ScummV5_SetState_Reset_Far__clear",
        "ScummV5_SetState_Reset_Far__done:",
        "    .a8", "    .i16",
        "    sta.l SAME_SCUMM_SETSTATE_VALUE",
        "    sta.l SAME_SCUMM_SETSTATE_LOCAL_FOUND",
        "    sta.l SAME_SCUMM_SETSTATE_BG_REDRAW",
        "    sta.l SAME_SCUMM_SETSTATE_EXEC_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_LOCAL_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_DIRTY_COUNT",
        "    sta.l SAME_SCUMM_SETSTATE_DRAW_QUEUE_COUNT",
        "    sta.l SAME_SCUMM_GET_FACING_EXEC_COUNT",
        "    sta.l SAME_SCUMM_GET_FACING_TRACE_COUNT",
        "    sta.l SAME_SCUMM_GET_FACING_STAGE",
        "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
        "ScummV5_GetActorFacing_Reset_Far__copy:",
        "    .a16", "    .i16",
        "    lda.l ScummV5_GetActorFacing_InitialAngles,x",
        "    sta.l SAME_SCUMM_ACTOR_FACINGS,x", "    inx", "    inx",
        "    cpx #$0040", "    bcc ScummV5_GetActorFacing_Reset_Far__copy",
        "    ldx #$0000",
        "ScummV5_GetActorWalkbox_Reset_Far__copy:",
        "    .a16", ".i16",
        "    lda.l ScummV5_GetActorWalkbox_InitialPositions,x",
        "    sta.l SAME_SCUMM_C31_POSITIONS,x", "    inx", "    inx",
        "    cpx #$0080", "    bcc ScummV5_GetActorWalkbox_Reset_Far__copy",
        "    sep #$20", "    .a8",
        "    ldx #$0000",
        "ScummV5_GetActorWalkbox_Reset_Far__copy_boxes:",
        "    .a8", ".i16",
        "    lda.l ScummV5_GetActorWalkbox_InitialBoxes,x",
        "    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x",
        "    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x", "    inx",
        "    cpx #$0020", "    bcc ScummV5_GetActorWalkbox_Reset_Far__copy_boxes",
        "    rep #$20", "    .a16", "    lda #$0000", "    ldx #$0000",
        "ScummV5_Movement_Reset_Far__clear:",
        "    sep #$20", "    .a8", "    sta.l SAME_SCUMM_MOVE_STATE,x", "    inx",
        "    cpx #SAME_SCUMM_MOVE_STATE_SIZE", "    bcc ScummV5_Movement_Reset_Far__clear",
        "    rep #$20", "    .a16", "    lda #$FFFF", "    ldx #$0000",
        "ScummV5_Movement_Reset_Far__inactive_destinations:",
        "    .a16", "    .i16",
        "    sta.l SAME_SCUMM_PUT_ACTOR_DEST_X,x", "    inx", "    inx",
        "    cpx #$0040", "    bcc ScummV5_Movement_Reset_Far__inactive_destinations",
        "    lda #$01", "    sta.l SAME_SCUMM_C31_INITIALIZED",
        f"    lda #${len(global_states) & 0xff:02X}",
        "    sta.l SAME_SCUMM_OBJECT_COUNT",
        f"    lda #${len(global_states) >> 8:02X}",
        "    sta.l SAME_SCUMM_OBJECT_COUNT+1", "    rtl",
    ))
    bank += 1
    bank = next_free_bank(bank)
    # The SAME-owned cold helper closure follows this include. Give it a
    # fresh bank rather than relying on implicit overflow from generated code.
    data_lines.extend((f".bank {bank}", ".org $8000"))

    # Append the name routine after the established generated data/code
    # layout has been allocated. Forward JSL references keep the room loader
    # compact without shifting any existing generated bank.
    bank = next_free_bank(bank + 1)
    data_lines.extend((
        f".bank {bank}", ".org $8000",
        *name_routine_lines,
    ))

    banked_directory_tables: list[tuple[str, bytes]] = []
    room_numbers = bytes(item["room"] for item in records)
    room_flags = bytes(item["flags"] for item in records)
    room_script_counts = bytes(len(item["scripts"]) for item in records)
    room_local_counts = bytes(len(item["locals"]) for item in records)
    room_executable_local_counts = bytes(len(item["executable_locals"]) for item in records)
    room_descriptor_checksums = b"".join(struct.pack(
        "<H", sum(x["id"] + x["kind"] + (x["number"] & 0xFF) + x["length"]
                  for x in item["scripts"]) & 0xFFFF,
    ) for item in records) or b"\0\0"
    lines = [
        "; Generated by tools/generate_snes_cooked_rooms.py.",
        f"SCUMM_V5_NUM_GLOBAL_SCRIPTS = ${num_global_scripts:04X}",
        f"SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_ENABLED = ${1 if hold_after_started_global_script is not None else 0:02X}",
        f"SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_SCRIPT = ${(hold_after_started_global_script or 0):02X}",
        (f"SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_PROGRAM = ${hold_after_started_global_program:04X}"
         if args.dynamic_program_residency else
         f"SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_PROGRAM = ${hold_after_started_global_program:02X}"),
        f"SCUMM_M23A_ROOM_COUNT = ${len(records):02X}",
        f"SCUMM_M23A_PROGRAM_FIRST = ${program_label_id(programs[0]['id'], dynamic=args.dynamic_program_residency) if programs else ('0000' if args.dynamic_program_residency else '00')}",
        (f"SCUMM_M23A_PROGRAM_COUNT = ${len(programs):04X}" if args.dynamic_program_residency
         else f"SCUMM_M23A_PROGRAM_COUNT = ${len(programs):02X}"),
        ("; SCUMM_RESIDENT_UNIT_COUNT is emitted by the canonical directory"
         if args.dynamic_program_residency else "SCUMM_RESIDENT_UNIT_COUNT = $0000"),
        f"SCUMM_M23A_LAST_BANK = ${bank:02X}",
        f"SCUMM_M23A_GLOBAL_OBJECT_COUNT = ${len(global_states):04X}",
    ]
    if args.banked_room_directory_data:
        banked_directory_tables.extend((
            ("ScummV5_M23A_RoomNumbers", room_numbers or b"\0"),
            ("ScummV5_M23A_RoomFlags", room_flags or b"\0"),
            ("ScummV5_M23A_RoomScriptCounts", room_script_counts or b"\0"),
        ))
    else:
        lines.extend((
            "ScummV5_M23A_RoomNumbers:", rows(room_numbers) or "    .byte $00",
            "ScummV5_M23A_RoomFlags:", rows(room_flags) or "    .byte $00",
            "ScummV5_M23A_RoomScriptCounts:",
            rows(room_script_counts) or "    .byte $00",
        ))
    if not args.dynamic_program_residency:
        # Legacy byte-selector directories are unnecessary in a dynamic
        # build, where lifecycle programs resolve from canonical 16-bit IDs.
        # Omitting them also prevents stale permanent-selector metadata from
        # consuming the tightly bounded bank-0 window.
        lines.extend((
            "ScummV5_M23A_RoomEntryPrograms:",
            rows(bytes(int(item["entry"]) & 0xFF for item in records)) or "    .byte $00",
            "ScummV5_M23A_RoomExitPrograms:",
            rows(bytes(int(item["exit"]) & 0xFF for item in records)) or "    .byte $00",
        ))
    if args.banked_room_directory_data:
        banked_directory_tables.extend((
            ("ScummV5_M23A_RoomLocalCounts", room_local_counts or b"\0"),
            ("ScummV5_M23A_RoomExecutableLocalCounts",
             room_executable_local_counts or b"\0"),
            ("ScummV5_M23A_RoomDescriptorChecksums", room_descriptor_checksums),
        ))
    else:
        lines.extend((
            "ScummV5_M23A_RoomLocalCounts:",
            rows(room_local_counts) or "    .byte $00",
            "ScummV5_M23A_RoomExecutableLocalCounts:",
            rows(room_executable_local_counts) or "    .byte $00",
            "ScummV5_M23A_RoomDescriptorChecksums:",
            "    .word " + ",".join(
                f"${int.from_bytes(room_descriptor_checksums[index:index + 2], 'little'):04X}"
                for index in range(0, len(room_descriptor_checksums), 2)
            ),
        ))
    if len(programs) > len(PRIMARY_PROGRAM_IDS):
        # FIRST is allocation-first, not numeric minimum. These constants are
        # diagnostic only; resolvers below use explicit identities. Keep the
        # historical <=48 output byte-for-byte unchanged.
        if args.dynamic_program_residency:
            lines.extend((
                "; Canonical IDs are not runtime selectors.",
                f"SCUMM_M23A_PROGRAM_MIN = ${min(item['id'] for item in programs):04X}",
                f"SCUMM_M23A_PROGRAM_MAX = ${max(item['id'] for item in programs):04X}",
            ))
        else:
            lines.extend((
                "; PROGRAM_FIRST is allocation-first; PROGRAM_COUNT is cardinality, not a range.",
                f"SCUMM_M23A_PROGRAM_MIN = ${min(item['id'] for item in programs):02X}",
                f"SCUMM_M23A_PROGRAM_MAX = ${max(item['id'] for item in programs):02X}",
                "; PROGRAM_IDS_IN_ALLOCATION_ORDER = " + ",".join(f"${item['id']:02X}" for item in programs),
            ))
    if args.dynamic_program_residency:
        directory_lines = directory_assembly(native_directory).splitlines()
        if args.banked_room_directory_data:
            lines.extend(directory_lines[:4])
            global_directory = native_directory.document["global_directory"]
            banked_directory_tables.extend((
                ("ScummV5_Resident_GlobalScriptNumbers",
                 bytes(int(item["script_number"]) & 0xFF
                       for item in global_directory) or b"\0"),
                ("ScummV5_Resident_GlobalProgramUnitIds",
                 b"".join(struct.pack("<H", int(item["program_unit_id"]))
                          for item in global_directory) or b"\xff\xff"),
            ))
        else:
            lines.extend(directory_lines)
        entry_program_ids = b"".join(
            struct.pack("<H", int(record["entry"])) for record in records
        ) or b"\xff\xff"
        exit_program_ids = b"".join(
            struct.pack("<H", int(record["exit"])) for record in records
        ) or b"\xff\xff"
        if args.banked_room_directory_data:
            banked_directory_tables.extend((
                ("ScummV5_M23A_RoomEntryProgramUnitIds", entry_program_ids),
                ("ScummV5_M23A_RoomExitProgramUnitIds", exit_program_ids),
            ))
        else:
            lines.extend((
                "ScummV5_M23A_RoomEntryProgramUnitIds:",
                word_rows([int(record["entry"]) for record in records]) or "    .word $FFFF",
                "ScummV5_M23A_RoomExitProgramUnitIds:",
                word_rows([int(record["exit"]) for record in records]) or "    .word $FFFF",
            ))
        lines.append("ScummV5_Resident_RoomBundleCount = $%04X" % len(records))
        bundle_offsets = []
        bundle_ids = []
        bundle_counts = []
        local_offsets = []
        local_counts = []
        local_numbers = []
        local_ids = []
        for record in records:
            bundle_offsets.append(len(bundle_ids))
            room_units = sorted(
                int(item["id"]) for item in programs
                if item["room"] == record["room"]
            )
            bundle_ids.extend(room_units)
            bundle_counts.append(len(room_units))
            local_offsets.append(len(local_ids))
            room_locals = sorted((item for item in programs
                                  if item["room"] == record["room"]
                                  and item["kind_name"] == "LSCR"),
                                 key=lambda item: int(item["id"]))
            local_counts.append(len(room_locals))
            local_numbers.extend(int(item["number"]) for item in room_locals)
            local_ids.extend(int(item["id"]) for item in room_locals)
        if args.banked_room_directory_data:
            banked_directory_tables.extend((
                ("ScummV5_Resident_RoomBundleOffsets",
                 b"".join(struct.pack("<H", value) for value in bundle_offsets) or b"\0\0"),
                ("ScummV5_Resident_RoomBundleCounts", bytes(bundle_counts) or b"\0"),
                ("ScummV5_Resident_RoomBundleUnitIds",
                 b"".join(struct.pack("<H", value) for value in bundle_ids) or b"\xff\xff"),
                ("ScummV5_Resident_RoomLocalOffsets",
                 b"".join(struct.pack("<H", value) for value in local_offsets) or b"\0\0"),
                ("ScummV5_Resident_RoomLocalCounts", bytes(local_counts) or b"\0"),
                ("ScummV5_Resident_RoomLocalNumbers", bytes(local_numbers) or b"\0"),
                ("ScummV5_Resident_RoomLocalUnitIds",
                 b"".join(struct.pack("<H", value) for value in local_ids) or b"\xff\xff"),
            ))
        else:
            lines.extend((
                "ScummV5_Resident_RoomBundleOffsets:",
                word_rows(bundle_offsets) or "    .word $0000",
                "ScummV5_Resident_RoomBundleCounts:",
                rows(bytes(bundle_counts)) or "    .byte $00",
                "ScummV5_Resident_RoomBundleUnitIds:",
                word_rows(bundle_ids) or "    .word $FFFF",
                "ScummV5_Resident_RoomLocalOffsets:",
                word_rows(local_offsets) or "    .word $0000",
                "ScummV5_Resident_RoomLocalCounts:",
                rows(bytes(local_counts)) or "    .byte $00",
                "ScummV5_Resident_RoomLocalNumbers:",
                rows(bytes(local_numbers)) or "    .byte $00",
                "ScummV5_Resident_RoomLocalUnitIds:",
                word_rows(local_ids) or "    .word $FFFF",
            ))
    for record_index, record in enumerate(records):
        locals_ = record["executable_locals"]
        if args.dynamic_program_residency:
            # The dynamic resolver consumes the canonical flattened
            # room-local directory above.  These parallel byte-selector and
            # static-index arrays are retained only by legacy builds.
            continue
        lines.extend((
            f"; Complete executable-local directory for room {record['room']}.",
            f"ScummV5_M23A_RoomLocalNumbers_{record_index}:",
            rows(bytes(item["number"] for item in locals_)) if locals_ else "    .byte $00",
            f"ScummV5_M23A_RoomLocalIndices_{record_index}:",
            "    .word " + ",".join(
                f"${item['number'] - num_global_scripts:04X}" for item in locals_
            ) if locals_ else "    .word $0000",
            f"ScummV5_M23A_RoomLocalPrograms_{record_index}:",
            rows(bytes(int(item["id"]) & 0xFF for item in locals_)) if locals_ else "    .byte $00",
        ))
    for item in programs:
        if item["executable"] and not args.far_programs:
            lines.extend((f"ScummV5_M23A_Program_{item['id']:02X}:", rows(item["program"])))

    # Generated lookup routines keep title/resource identities out of the core.
    lines.extend((
        "ScummV5_M23A_FindRoom:",
        "    sep #$20", "    .a8", "    rep #$10", "    .i16",
        "    ldx #$0000", "ScummV5_M23A_FindRoom__loop:", "    .a8", "    .i16",
        "    cmp.l ScummV5_M23A_RoomNumbers,x",
        "    beq ScummV5_M23A_FindRoom__found", "    inx",
        "    cpx #SCUMM_M23A_ROOM_COUNT", "    bcc ScummV5_M23A_FindRoom__loop",
        "    sec", "    rts", "ScummV5_M23A_FindRoom__found:",
        "    txa", "    clc", "    rts",
    ))
    size_lines = ["    sep #$20", "    .a8"]
    if args.dynamic_program_residency:
        size_lines.extend((
            # ScummV5_FetchByte keeps the requested source PC in X across the
            # size lookup. The selector resolver uses X as its resident-table
            # scan index, so this generated service must preserve X as part of
            # its ABI rather than letting an identity lookup rewind byte fetch.
            # Selector zero is the legacy "no program" sentinel used after a
            # room lifecycle retires slot zero. It is a handled zero-length
            # program, not a miss: carry must prevent the legacy fixture
            # fallback from treating selector zero as its default program.
            "    cmp #$00", "    bne ScummV5_M23A_GetProgramSize__resident",
            "    rep #$20", "    .a16", "    lda #$0000", "    sec", "    rtl",
            "ScummV5_M23A_GetProgramSize__resident:", "    sep #$20", "    .a8",
            "    rep #$10", "    .i16", "    phx",
            "    sta.l SAME_SCUMM_RESIDENT_SELECTOR",
            ".if SAME_BUILD_SCUMM_AUTHENTIC_BOOTSTRAP",
            "    lda #$01", "    sta.l SAME_SCUMM_RESIDENT_SELECTOR_CALLER",
            "    lda.l SAME_SCUMM_RESIDENT_SELECTOR",
            ".endif",
            "    jsl ScummV5_Resident_ProgramUnitForSelector_Far",
            "    bcs ScummV5_M23A_GetProgramSize__id_ready",
            "    plx", "    clc", "    rtl",
            "ScummV5_M23A_GetProgramSize__id_ready:",
            "    rep #$20", "    .a16",
            "    lda.l SAME_SCUMM_RESIDENT_EXPECTED_ID", "    asl", "    tax",
            "    lda.l ScummV5_M23A_ProgramLengths,x", "    plx", "    sec", "    rtl",
        ))
    else:
        for item in programs:
            size_lines.extend((
                f"    cmp #${item['id']:02X}", f"    bne ScummV5_M23A_GetProgramSize__next_{item['id']:02X}",
                "    rep #$20", "    .a16", f"    lda #${item['length']:04X}",
                "    sec", "    " + ("rtl" if args.far_programs else "rts"),
                f"ScummV5_M23A_GetProgramSize__next_{item['id']:02X}:", "    .a8",
            ))
    size_lines.extend(("    clc", "    " + ("rtl" if args.far_programs else "rts")))
    if args.far_programs:
        lines.extend(("ScummV5_M23A_GetProgramSize:",
                      "    jsl ScummV5_M23A_GetProgramSize_Far_Address", "    rts"))
        data_lines.extend(("ScummV5_M23A_GetProgramSize_Far:", *size_lines))
    else:
        lines.extend(("ScummV5_M23A_GetProgramSize:", *size_lines))
    # Far-callable twin used by cold production scheduler helpers.  Both
    # resolvers are generated from the identical profile-owned directory.
    if args.dynamic_program_residency:
        data_lines.extend((
            "ScummV5_M23A_ResolveGlobalScript_Far:",
            "    jsl ScummV5_Resident_ResolveGlobalScript_Far", "    rtl",
            "ScummV5_M23A_ResolveLocalScript_Far:",
            "    jsl ScummV5_Resident_ResolveLocalScript_Far", "    rtl",
        ))
    else:
        data_lines.extend((
            "ScummV5_M23A_ResolveGlobalScript_Far:",
            "; Input A=u8 script number; output A=program and carry set.",
            "    sep #$20", "    .a8",
        ))
        for item in global_scripts:
            data_lines.extend((
                f"    cmp #${item['number'] & 0xff:02X}",
                f"    bne ScummV5_M23A_ResolveGlobalScript_Far__next_{item['id']:02X}",
                f"    lda #${item['id']:02X}", "    sec", "    rtl",
                f"ScummV5_M23A_ResolveGlobalScript_Far__next_{item['id']:02X}:", "    .a8",
            ))
        data_lines.extend(("    clc", "    rtl"))
    fetch_program_lines = [
        "ScummV5_M23A_FetchProgramByte_Far:",
        "    php", "    rep #$10", "    .i16", "    phy", "    phx",
        "    sep #$20", "    .a8",
    ]
    if args.msu1_program_storage_dir is not None:
        fetch_program_lines = [
            "ScummV5_M23A_FetchProgramByte_Far:",
            "    jsl ScummV5_MsuProgram_FetchByte_Far", "    rtl",
        ]
    elif args.dynamic_program_residency:
        fetch_program_lines.extend((
            "    sta.l SAME_SCUMM_RESIDENT_SELECTOR",
            ".if SAME_BUILD_SCUMM_AUTHENTIC_BOOTSTRAP",
            "    lda #$02", "    sta.l SAME_SCUMM_RESIDENT_SELECTOR_CALLER",
            "    lda.l SAME_SCUMM_RESIDENT_SELECTOR",
            ".endif",
            "    jsl ScummV5_Resident_ProgramUnitForSelector_Far",
            "    bcs ScummV5_M23A_FetchProgramByte__id_ready",
            "    bra ScummV5_M23A_FetchProgramByte__bad_binding",
            "ScummV5_M23A_FetchProgramByte__id_ready:",
            "    rep #$20", "    .a16",
            "    lda.l SAME_SCUMM_RESIDENT_EXPECTED_ID",
            "    sta.l SAME_SCUMM_RESIDENT_REQUEST_ID",
            "    asl", "    clc", "    adc.l SAME_SCUMM_RESIDENT_REQUEST_ID", "    tax",
            "    sep #$20", "    .a8",
            "    lda.l ScummV5_M23A_ProgramPointers,x", "    sta $F9", "    inx",
            "    lda.l ScummV5_M23A_ProgramPointers,x", "    sta $FA", "    inx",
            "    lda.l ScummV5_M23A_ProgramPointers,x", "    sta $FB",
            "    plx", "    rep #$20", "    .a16", "    txa", "    tay",
            "    sep #$20", "    .a8", "    lda [$F9],y",
            "    ply", "    plp", "    clc", "    rtl",
            "ScummV5_M23A_FetchProgramByte__bad_binding:",
            "    sep #$20", "    .a8", "    plx", "    ply", "    plp",
            "    sec", "    rtl",
        ))
    else:
        # Keep the legacy byte-selector ABI and generated code unchanged.
        fetch_program_lines = [
            "ScummV5_M23A_FetchProgramByte_Far:", "    sep #$20", "    .a8",
        ]
        for item in programs:
            if item["executable"]:
                fetch_program_lines.extend((
                    f"    cmp #${item['id']:02X}", f"    bne ScummV5_M23A_FetchProgramByte__next_{item['id']:02X}",
                    f"    lda.l ScummV5_M23A_Program_{item['id']:02X},x", "    clc",
                    "    rtl" if args.far_programs else "    rts",
                    f"ScummV5_M23A_FetchProgramByte__next_{item['id']:02X}:", "    .a8",
                ))
    fetch_program_lines.extend(("    sec", "    rtl" if args.far_programs else "    rts"))
    if args.far_programs:
        # The per-program fetch dispatch grows linearly with the executable
        # profile.  Keep its hot VM-facing ABI near-callable, but place the
        # generated dispatch body beside the far program pool so large
        # profiles do not overflow bank zero merely by adding one script.
        lines.extend((
            "ScummV5_M23A_FetchProgramByte:",
            "    jsl ScummV5_M23A_FetchProgramByte_Far_Address",
            "    rts",
        ))
        data_lines.extend(fetch_program_lines)
    else:
        fetch_program_lines[0] = "ScummV5_M23A_FetchProgramByte:"
        lines.extend(fetch_program_lines)

    if args.far_programs:
        lines.extend((
            "ScummV5_M23A_ResolveGlobalScript:",
            "; Cold profile-global lookup is owned by the generated far bank.",
            "    jsl ScummV5_M23A_ResolveGlobalScript_Far_Address", "    rts",
        ))
    else:
        lines.extend((
            "ScummV5_M23A_ResolveGlobalScript:",
            "; Input: A=script number; output A=profile-generated program with carry set.",
            "    sep #$20", "    .a8",
        ))
        for item in global_scripts:
            lines.extend((
                f"    cmp #${item['number'] & 0xff:02X}",
                f"    bne ScummV5_M23A_ResolveGlobalScript__next_{item['id']:02X}",
                f"    lda #${item['id']:02X}", "    sec", "    rts",
                f"ScummV5_M23A_ResolveGlobalScript__next_{item['id']:02X}:", "    .a8",
            ))
        lines.extend(("    clc", "    rts"))

    far_local_resolver = args.far_programs and (
        args.dynamic_program_residency or any(record["executable_locals"] for record in records)
    )
    if args.dynamic_program_residency:
        lines.extend((
            "ScummV5_M23A_ResolveLocalScript:",
            "    jsl ScummV5_M23A_ResolveLocalScript_Far_Address", "    rts",
        ))
        local_lines = []
    else:
        local_lines = [
            (
                "ScummV5_M23A_ResolveLocalScript_Far:"
                if far_local_resolver
                else "ScummV5_M23A_ResolveLocalScript:"
            ),
            "; Input: A=script number, active record; output A=program and carry set.",
            "    sep #$20", "    .a8",
        ]
    local_return = "rtl" if far_local_resolver else "rts"
    for record_index, record in enumerate(records):
        if not record["executable_locals"]:
            continue
        local_lines.extend((
            "    pha", "    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD",
            f"    cmp #${record_index:02X}", f"    bne ScummV5_M23A_ResolveLocalScript__dispatch_{record_index}",
            "    pla", f"    jmp ScummV5_M23A_ResolveLocalScript__record_{record_index}",
            f"ScummV5_M23A_ResolveLocalScript__dispatch_{record_index}:", "    .a8", "    pla",
        ))
    local_lines.extend(("    clc", f"    {local_return}"))
    for record_index, record in enumerate(records):
        if not record["executable_locals"]:
            continue
        local_lines.extend((f"ScummV5_M23A_ResolveLocalScript__record_{record_index}:", "    .a8"))
        for local in record["executable_locals"]:
            local_lines.extend((f"    cmp #${local['number'] & 0xff:02X}",
                                f"    bne ScummV5_M23A_ResolveLocalScript__next_{local['id']:02X}",
                                f"    lda #${local['id']:02X}", "    sec", f"    {local_return}",
                                f"ScummV5_M23A_ResolveLocalScript__next_{local['id']:02X}:", "    .a8"))
        local_lines.extend(("    clc", f"    {local_return}"))
    if far_local_resolver and not args.dynamic_program_residency:
        lines.extend((
            "ScummV5_M23A_ResolveLocalScript:",
            "    sep #$20", "    .a8", "    sta.l SAME_SCUMM_VERB_OBJECT",
            "    jsl ScummV5_M23A_ResolveLocalScript_Far_Address",
            "    bcc ScummV5_M23A_ResolveLocalScript__diagnostic_fail",
            "    sta.l SAME_SCUMM_MOVE_QUERY_DIR", "    sec", "    rts",
            "ScummV5_M23A_ResolveLocalScript__diagnostic_fail:",
            "    .a8",
            "    lda #$FF", "    sta.l SAME_SCUMM_MOVE_QUERY_DIR", "    clc", "    rts",
        ))
        data_lines.extend(local_lines)
    elif not args.dynamic_program_residency:
        lines.extend(local_lines)

    far_helper_bank = bank
    if banked_directory_tables:
        # Keep the data tables out of the fixed bank-0 code window. All runtime
        # consumers use long-address reads, so these are ordinary ROM data
        # tables and need no selector or runtime residency binding.
        packed_table_bank = None
        packed_table_offset = 0
        # `bank` denotes the last generated helper bank at this point.  Do not
        # append packed tables into that same 32 KiB page: the final resolver
        # routines can already occupy it in a whole-source build.
        packed_table_next_bank = next_free_bank(bank + 1)
        for label, payload in banked_directory_tables:
            append_room_table(label, payload)
        lines = [
            (f"SCUMM_M23A_LAST_BANK = ${max(0, bank - 1):02X}"
             if line.startswith("SCUMM_M23A_LAST_BANK = ") else line)
            for line in lines
        ]

    # Record validators compare the immutable header/directory byte-for-byte,
    # then checksum the complete pre-trailer record while excluding mutable
    # checksum fields 32..37 exactly as the host encoder does.
    validator_lines = ["ScummV5_M23A_ValidateRecord:", "    sep #$20", "    .a8"]
    for index in range(0 if args.msu1_live_room_resources else len(records)):
        validator_lines.extend((f"    cmp #${index:02X}", f"    bne ScummV5_M23A_ValidateRecord__dispatch_{index}",
                                f"    jmp ScummV5_M23A_ValidateRecord__{index}",
                                f"ScummV5_M23A_ValidateRecord__dispatch_{index}:", "    .a8"))
    validator_lines.extend(("    sec", "    rts"))
    for index, record in enumerate(
        () if args.msu1_live_room_resources else records
    ):
        directory_size = HEADER.size + len(record["scripts"]) * 96
        first_label = record["segments"][0][0]
        validator_lines.extend((
            f"ScummV5_M23A_ValidateRecord__{index}:",
            "    rep #$30", "    .a16", "    .i16", "    ldx #$0000",
            f"ScummV5_M23A_ValidateRecord__{index}_directory:",
            "    sep #$20", "    .a8", f"    lda.l {first_label},x",
            f"    cmp.l ScummV5_M23A_Record_{index}_ExpectedDirectory,x",
            f"    beq ScummV5_M23A_ValidateRecord__{index}_directory_ok",
            f"    jmp ScummV5_M23A_ValidateRecord__{index}_bad",
            f"ScummV5_M23A_ValidateRecord__{index}_directory_ok:", "    .a8",
            "    rep #$20", "    .a16", "    inx", f"    cpx #${directory_size:04X}",
            f"    bcc ScummV5_M23A_ValidateRecord__{index}_directory",
            "    lda #$0000", "    sta.l SAME_SCUMM_M23A_CHECKSUM",
        ))
        for segment_index, (label, size, start) in enumerate(record["segments"]):
            validator_lines.extend((
                "    ldx #$0000", f"ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}:",
                "    .a16", "    .i16",
            ))
            if segment_index == 0:
                validator_lines.extend((
                    "    cpx #$0020", f"    bcc ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}_add",
                    "    cpx #$0026", f"    bcc ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}_next",
                    f"ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}_add:", "    .a16",
                ))
            validator_lines.extend((
                "    lda #$0000", "    sta.l SAME_SCUMM_M23A_BYTE",
                "    sep #$20", "    .a8", f"    lda.l {label},x", "    sta.l SAME_SCUMM_M23A_BYTE",
                "    rep #$20", "    .a16", "    lda.l SAME_SCUMM_M23A_CHECKSUM",
                "    clc", "    adc.l SAME_SCUMM_M23A_BYTE", "    sta.l SAME_SCUMM_M23A_CHECKSUM",
            ))
            if segment_index == 0:
                validator_lines.extend((f"ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}_next:",
                                        "    .a16", "    .i16"))
            effective_size = size
            if segment_index == len(record["segments"]) - 1:
                effective_size -= 32  # host SHA-256 trailer is not in compact sum
            validator_lines.extend((
                "    inx", f"    cpx #${effective_size:04X}",
                f"    bcc ScummV5_M23A_ValidateRecord__{index}_segment_{segment_index}",
            ))
        validator_lines.extend((
            "    lda.l SAME_SCUMM_M23A_CHECKSUM", f"    cmp #${record['checksum']:04X}",
            f"    bne ScummV5_M23A_ValidateRecord__{index}_bad", "    clc", "    rts",
            f"ScummV5_M23A_ValidateRecord__{index}_bad:", "    sep #$20", "    .a8", "    sec", "    rts",
        ))

    if args.far_validator_output:
        validator_lines.extend((
            "ScummV5_M23A_ValidateRecord_FarEntry:",
            "    jsr ScummV5_M23A_ValidateRecord",
            "    rtl",
        ))
        if not args.layout_only:
            args.far_validator_output.parent.mkdir(parents=True, exist_ok=True)
            args.far_validator_output.write_text("\n".join(validator_lines) + "\n")
    else:
        lines.extend(validator_lines)
        # Poppy validates include existence even when the conditional include
        # is disabled.  Keep the conventional far-validator include inert for
        # inline-validator builds so stale labels from a prior M24 build cannot
        # collide with this generated table.
        inert_far = args.output.with_name("scumm_v5_room_validator_far.inc.pasm")
        if not args.layout_only:
            inert_far.write_text("; Validator is emitted inline for this build.\n")

    if args.far_programs:
        # Far helpers share the final generated bank. LoROM banks $7E/$7F are
        # WRAM windows, so long calls must use their $FE/$FF ROM mirrors.
        far_labels = [
            "ScummV5_Matrix_LoadActiveRoomNames_Far",
            "ScummV5_M23A_GetProgramSize_Far",
            "ScummV5_M23A_ResolveGlobalScript_Far",
            "ScummV5_M23A_FetchProgramByte_Far",
        ]
        if far_local_resolver:
            far_labels.append("ScummV5_M23A_ResolveLocalScript_Far")
        for label in far_labels:
            data_lines.append(
                f"{label}_Address = " + cpu_visible_rom_symbol(
                    far_helper_bank, label, sa1_aliases=args.sa1_rom_bank_aliases,
                )
            )

    validate_generated_bank_origins(
        data_lines + lines + (validator_lines if not args.far_validator_output else []),
        allow_out_of_range=args.layout_only,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.data_output.parent.mkdir(parents=True, exist_ok=True)
    if not args.layout_only:
        args.output.write_text("\n".join(lines) + "\n")
        args.data_output.write_text("\n".join(data_lines) + "\n")
    report = {
        "rooms": [item["room"] for item in records], "programs": len(programs),
        "program_id_namespace": ("canonical_program_unit_id"
                                  if args.dynamic_program_residency else "resident_selector"),
        "program_map": [
            {
                "id": item["id"], "identity": item["identity"],
                "program_unit_identity": item.get("unit_identity"),
                "kind": item["kind_name"], "room": item["room"],
                "number": item["number"], "length": item["length"],
                "sha256": hashlib.sha256(item["program"]).hexdigest(),
                **({
                    "rom_bank": item.get("rom_bank"),
                    "bank_offset": item.get("bank_offset"),
                    "cpu_rom_bank": item.get("cpu_rom_bank"),
                    "cpu_address": item.get("cpu_address"),
                    "cpu_addressable_24bit": item.get("cpu_addressable_24bit"),
                    "storage_kind": item.get("storage_kind"),
                    "shared_storage": bool(item.get("shared_storage", False)),
                    "storage_alias_of": item.get("storage_alias_of"),
                    "storage_source_offset": item.get("storage_source_offset"),
                    "storage_payload_match_verified": bool(
                        item.get("storage_payload_match_verified", False)
                    ),
                } if args.far_programs else {}),
            }
            for item in programs
        ],
        "program_code_bytes": sum(int(item["length"]) for item in programs
                                   if item["executable"]),
        "program_pool_banks": (0 if not args.far_programs or not programs else
                                max(int(item.get("rom_bank", 0)) for item in programs) -
                                min(int(item.get("rom_bank", 0)) for item in programs) + 1),
        "first_bank": args.first_bank,
        "last_bank": bank, "output": args.output.name, "data": args.data_output.name,
        "layout_only": args.layout_only,
        "sa1_rom_bank_aliases": args.sa1_rom_bank_aliases,
        "reserved_banks": sorted(reserved_banks),
        "room_segments": room_segment_map,
        "expected_room_directories": expected_directory_map,
        "generated_table_placements": table_placement_map,
        "generated_bank_sections": generated_bank_section_census(data_lines),
        "generated_assembly_source": {
            "room_include_text_bytes": len(("\n".join(lines) + "\n").encode("utf-8")),
            "banked_include_text_bytes": len(("\n".join(data_lines) + "\n").encode("utf-8")),
            "room_include_lines": len(lines),
            "banked_include_lines": len(data_lines),
        },
        "generated_table_payload_bytes": sum(int(item["payload_bytes"]) for item in table_placement_map),
        "resolver_table_bytes": sum(int(item["payload_bytes"]) for item in table_placement_map
                                     if item.get("resolver_table")),
        "program_pointer_directory_bytes": (
            len(programs) * (2 if args.msu1_program_storage_dir else 5)
            if args.dynamic_program_residency else 0
        ),
        "room_segment_manifest": room_segment_map,
    }
    if native_directory is not None:
        report["native_program_directory_sha256"] = native_directory.sha256
        if program_storage is not None:
            report["msu1_program_storage"] = {
                "package": str(args.msu1_program_storage_dir / "scumm-programs.msu"),
                "program_count": program_storage["program_count"],
                "body_bytes": program_storage["program_body_bytes"],
                "room_resource_count": program_storage["room_resource_count"],
                "room_resource_bytes": program_storage["room_resource_bytes"],
                "room_section": program_storage["room_section"],
                "room_records": program_storage["room_records"],
                "package_sha256": program_storage["package_sha256"],
                "directory_records_bytes": int(program_storage["program_count"]) * 10,
                "rom_directory_bank": args.msu1_program_directory_bank,
                "rom_bodies_emitted": False,
                "prefix_source_package_sha256": (
                    hashlib.sha256(args.msu1_program_prefix_package.read_bytes()).hexdigest()
                    if args.msu1_program_prefix_package else None
                ),
                "prefix_sections": [
                    {"name": name, "kind": kind, "payload_bytes": len(data),
                     "alignment": alignment,
                     "payload_sha256": hashlib.sha256(data).hexdigest()}
                    for name, kind, data, alignment in prefix_sections
                ],
            }
        directory_output = args.native_directory_output or args.output.with_name(
            "scumm_v5_native_program_directory.json"
        )
        directory_include = args.native_directory_include or args.output.with_name(
            "scumm_v5_native_program_directory.inc.pasm"
        )
        directory_output.parent.mkdir(parents=True, exist_ok=True)
        directory_include.parent.mkdir(parents=True, exist_ok=True)
        directory_output.write_bytes(native_directory.canonical_bytes())
        if not args.layout_only:
            directory_include.write_text(directory_assembly(native_directory), encoding="ascii")
        report_base = (args.report.parent if args.report is not None else args.output.parent).resolve()
        report["native_program_directory"] = os.path.relpath(
            directory_output.resolve(), start=report_base,
        )
        report["native_program_directory_include"] = os.path.relpath(
            directory_include.resolve(), start=report_base,
        )
        if args.backend_directory_output:
            backend_entries = []
            program_by_identity = {
                str(item.get("unit_identity")): item for item in programs
                if item.get("unit_identity") is not None
            }
            for entry in native_directory.document["entries"]:
                identity = str(entry["identity"])
                program = program_by_identity.get(identity)
                descriptor = None
                if program is not None:
                    descriptor = {
                        "representation": "SCUMM_V5_BYTECODE_PROGRAM_BODY",
                        "code_label": f"ScummV5_M23A_Program_{int(program['id']):04X}",
                        "rom_bank": program.get("rom_bank"),
                        "bank_offset": program.get("bank_offset"),
                        "cpu_rom_bank": program.get("cpu_rom_bank"),
                        "cpu_address": program.get("cpu_address"),
                        "cpu_addressable_24bit": program.get("cpu_addressable_24bit"),
                        "code_size": int(program["length"]),
                        "code_sha256": hashlib.sha256(program["program"]).hexdigest(),
                        "storage_kind": program.get("storage_kind"),
                        "shared_storage": bool(program.get("shared_storage", False)),
                        "storage_alias_of": program.get("storage_alias_of"),
                        "storage_source_offset": program.get("storage_source_offset"),
                        "storage_payload_match_verified": bool(
                            program.get("storage_payload_match_verified", False)
                        ),
                        "dispatch": entry.get("dispatch", {}),
                        "lowering_status": "RAW_V5_BYTECODE_RETAINED",
                        "execution_certification": "SEE_WHOLE_SOURCE_CAPABILITY_REPORT",
                    }
                backend_entries.append({**entry, "backend_descriptor": descriptor})
            backend_document = {
                "schema": "same_scumm_v5_backend_program_directory_v1",
                "canonical_directory_sha256": native_directory.sha256,
                "program_count": len(backend_entries),
                "entries": backend_entries,
            }
            args.backend_directory_output.parent.mkdir(parents=True, exist_ok=True)
            args.backend_directory_output.write_text(
                json.dumps(backend_document, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            report["backend_program_directory"] = args.backend_directory_output.name
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    ownership_path.write_text(json.dumps({
        "schema": "same_generated_room_segments_v1",
        "files": sorted(written_segments, key=lambda item: str(item["path"])),
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
