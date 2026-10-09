"""Measured LoROM placement ledger and pre-assembly capacity validation.

LoROM CPU banks are aliases, not storage IDs.  This module keeps logical
generator pages, physical 32 KiB pages, and CPU addresses separate and never
infers an assembled-code size from generated assembly text.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

LOROM_PAGE_BYTES = 0x8000
LOROM_MAX_PAGES = 128
LOROM_MAX_BYTES = LOROM_PAGE_BYTES * LOROM_MAX_PAGES


def physical_lorom_page(cpu_bank: int) -> int:
    if not 0 <= cpu_bank <= 0xFF:
        raise ValueError(f"CPU bank ${cpu_bank:X} is not an 8-bit address")
    if cpu_bank in (0x7E, 0x7F):
        raise ValueError(f"CPU bank ${cpu_bank:02X} is WRAM, not a ROM window")
    return cpu_bank & 0x7F


def _cpu_bank(page: int, sa1_aliases: bool) -> int:
    if not 0 <= page <= 0xFF:
        raise ValueError("logical page is outside the 24-bit bank namespace")
    if sa1_aliases and 0x40 <= page <= 0x4F:
        return page + 0x40
    if page in (0x7E, 0x7F):
        return page + 0x80
    return page


def _placement(item: dict[str, Any], *, purpose: str, source: str,
               payload_bytes: int, offset: int, consumer: str,
               sa1_aliases: bool, source_sha256: str | None = None,
               alignment: int = 1) -> dict[str, Any]:
    page = int(item["rom_bank"])
    if offset < 0 or offset >= LOROM_PAGE_BYTES:
        raise ValueError(f"{source}: invalid page offset {offset}")
    if payload_bytes < 0 or offset + payload_bytes > LOROM_PAGE_BYTES:
        raise ValueError(
            f"{source}: {payload_bytes} bytes at offset {offset} cross a LoROM page"
        )
    try:
        cpu = _cpu_bank(page, sa1_aliases)
        physical = physical_lorom_page(cpu)
    except ValueError:
        cpu = physical = None
    return {
        "purpose": purpose,
        "source_identity": source,
        "source_sha256": source_sha256 or item.get("source_sha256") or item.get("sha256"),
        "payload_sha256": item.get("payload_sha256"),
        "payload_bytes": payload_bytes,
        "generated_code_bytes": int(item.get("generated_code_bytes", 0)),
        "file_offset": page * LOROM_PAGE_BYTES + offset,
        "logical_storage_page": page,
        "page_offset": offset,
        "physical_lorom_page": physical,
        "target_cpu_bank": cpu,
        "target_address": None if cpu is None else 0x8000 + offset,
        "alignment_bytes": int(item.get("alignment_bytes", alignment)),
        "consumer": consumer,
        "contains_same_bytes_as": [],
    }


def preflight_lorom_layout(
    generator_report: dict[str, Any], *, capacity_pages: int | None = None,
    capacity_bytes: int | None = None,
) -> dict[str, Any]:
    if capacity_bytes is None:
        capacity_bytes = LOROM_MAX_BYTES if capacity_pages is None else capacity_pages * LOROM_PAGE_BYTES
    if not 0 < capacity_bytes <= LOROM_MAX_BYTES:
        raise ValueError(f"unsupported LoROM target capacity {capacity_bytes}; maximum is {LOROM_MAX_BYTES}")
    pages = capacity_bytes // LOROM_PAGE_BYTES
    if capacity_pages is not None and capacity_pages != pages:
        raise ValueError("capacity_pages conflicts with capacity_bytes")
    issues: list[dict[str, Any]] = []
    if capacity_bytes % LOROM_PAGE_BYTES:
        issues.append({"kind": "UNSUPPORTED_TARGET_IMAGE_SIZE", "capacity_bytes": capacity_bytes})
    sa1 = bool(generator_report.get("sa1_rom_bank_aliases", False))
    placements: list[dict[str, Any]] = []
    placements.extend(generator_report.get("room_segments", []))
    placements.extend(generator_report.get("expected_room_directories", []))
    placements.extend(generator_report.get("generated_table_placements", []))
    placements.extend(x for x in generator_report.get("program_map", []) if x.get("rom_bank") is not None)
    room_segments = generator_report.get("room_segments", [])
    verified_aliases: dict[int, dict[str, Any]] = {}
    alias_items = [
        item for item in generator_report.get("program_map", [])
        if item.get("storage_kind") == "COOKED_ROOM_RECORD_ALIAS"
    ] + [
        item for item in generator_report.get("expected_room_directories", [])
        if item.get("storage_kind") == "ROOM_RECORD_DIRECTORY_ALIAS"
    ]
    for item in alias_items:
        source = str(item.get("storage_alias_of", ""))
        source_offset = item.get("storage_source_offset")
        size = int(item.get("length", item.get("payload_bytes", 0)))
        if not item.get("storage_payload_match_verified") or source_offset is None:
            issues.append({"kind": "UNVERIFIED_SHARED_PROGRAM_STORAGE",
                           "source": str(item.get("program_unit_identity",
                                                  item.get("source_identity", "unknown"))),
                           "detail": "room-resource alias lacks verified byte equality/provenance"})
            continue
        source_offset = int(source_offset)
        segment = next((row for row in room_segments
                        if str(row.get("source_identity")) == source
                        and int(row.get("source_payload_offset", -1)) <= source_offset
                        and source_offset + size <= int(row.get("source_payload_offset", -1))
                            + int(row.get("payload_bytes", 0))), None)
        if segment is None:
            issues.append({"kind": "SHARED_PROGRAM_STORAGE_SOURCE_MISSING",
                           "source": str(item.get("program_unit_identity",
                                                  item.get("source_identity", "unknown"))),
                           "detail": "no emitted complete-room segment contains aliased bytes"})
            continue
        expected_offset = int(segment["bank_offset"]) + source_offset - int(segment["source_payload_offset"])
        item_size = int(item.get("length", item.get("payload_bytes", 0)))
        if (int(item.get("rom_bank", -1)) != int(segment["rom_bank"])
                or int(item.get("bank_offset", -1)) != expected_offset
                or item_size > LOROM_PAGE_BYTES - expected_offset):
            issues.append({"kind": "SHARED_RESOURCE_STORAGE_ADDRESS_MISMATCH",
                           "source": str(item.get("program_unit_identity",
                                                  item.get("source_identity", "unknown"))),
                           "backing_source": source,
                           "expected_bank": int(segment["rom_bank"]),
                           "expected_offset": expected_offset,
                           "detail": "resource alias does not point at its exact room-record byte range"})
            continue
        verified_aliases[id(item)] = segment

    owner_intervals: dict[int, list[tuple[int, int, int, str, dict[str, Any]]]] = defaultdict(list)
    out_of_capacity: dict[int, list[str]] = defaultdict(list)
    unrepresentable: dict[int, list[str]] = defaultdict(list)
    for item in placements:
        bank = int(item["rom_bank"])
        source = str(item.get("source_identity", item.get("program_unit_identity", item.get("identity", "unknown"))))
        if item.get("segment_index") is not None:
            source += f"/segment-{int(item['segment_index'])}"
        if bank > 0xFF:
            unrepresentable[bank].append(source)
            continue
        try:
            cpu = _cpu_bank(bank, sa1)
            physical = physical_lorom_page(cpu)
        except ValueError as exc:
            issues.append({"kind": "NON_ROM_CPU_BANK", "logical_bank": bank, "source": source, "detail": str(exc)})
            continue
        if bank >= pages:
            out_of_capacity[bank].append(source)
        offset = int(item.get("bank_offset", 0))
        size = int(item.get("payload_bytes", item.get("length", 0)))
        owner_intervals[physical].append((bank, offset, offset + size, source, item))
    overlap_groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for physical, intervals in sorted(owner_intervals.items()):
        for index, (bank, start, end, source, item) in enumerate(intervals):
            for other_bank, other_start, other_end, other_source, other_item in intervals[index + 1:]:
                if start < other_end and other_start < end:
                    pair = ((id(item) in verified_aliases
                             and verified_aliases[id(item)] is other_item)
                            or (id(other_item) in verified_aliases
                                and verified_aliases[id(other_item)] is item))
                    if pair:
                        continue
                    kind = "MIRRORED_STORAGE_OVERLAP" if bank != other_bank else "PHYSICAL_STORAGE_OVERLAP"
                    overlap_groups[(kind, physical)].append({
                        "logical_banks": [bank, other_bank],
                        "sources": [source, other_source],
                        "overlap_interval": [max(start, other_start), min(end, other_end)],
                    })
    for bank, sources in sorted(unrepresentable.items()):
        issues.append({"kind": "CPU_BANK_UNREPRESENTABLE", "logical_bank": bank,
                       "sources": sorted(set(sources)),
                       "detail": "logical bank cannot be represented by a 24-bit SNES address"})
    for bank, sources in sorted(out_of_capacity.items()):
        issues.append({"kind": "PHYSICAL_ROM_PAGE_OUT_OF_CAPACITY", "logical_bank": bank,
                       "physical_page": bank & 0x7F, "capacity_pages": pages,
                       "sources": sorted(set(sources)),
                       "detail": "logical payload page exceeds configured physical ROM capacity"})
    for (kind, physical), collisions in sorted(overlap_groups.items()):
        issues.append({"kind": kind, "physical_page": physical,
                       "conflict_count": len(collisions), "conflicts": collisions,
                       "detail": "placed payload intervals overlap in one physical LoROM page"})
    reserved = sorted({int(x) for x in generator_report.get("reserved_banks", [])})
    for item in placements:
        bank = int(item["rom_bank"])
        if bank in reserved:
            issues.append({"kind": "RESERVED_PAGE_OCCUPIED", "logical_bank": bank,
                           "source": str(item.get("source_identity", item.get("label", "unknown")))})
    highwater = int(generator_report.get("last_bank", -1)) + 1
    if highwater > pages:
        issues.append({"kind": "LOGICAL_SPAN_EXCEEDS_CAPACITY",
                       "logical_page_highwater_exclusive": highwater,
                       "capacity_pages": pages,
                       "required_span_bytes": highwater * LOROM_PAGE_BYTES,
                       "capacity_bytes": pages * LOROM_PAGE_BYTES})
    return {"result": "pass" if not issues else "reject", "capacity_pages": pages,
            "capacity_bytes": capacity_bytes, "logical_page_highwater_exclusive": highwater,
            "required_span_bytes": highwater * LOROM_PAGE_BYTES,
            "reserved_banks": reserved, "issues": issues}


def _page_layout(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_page: dict[int, list[tuple[int, int, str]]] = defaultdict(list)
    for row in rows:
        page, start = int(row["logical_storage_page"]), int(row["page_offset"])
        by_page[page].append((start, start + int(row["payload_bytes"]), str(row["source_identity"])))
    output = []
    for page, intervals in sorted(by_page.items()):
        intervals.sort()
        cursor = unique = gaps = overlap = highwater = 0
        for start, end, _ in intervals:
            highwater = max(highwater, end)
            gaps += max(0, start - cursor)
            overlap += max(0, min(cursor, end) - start)
            unique += max(0, end - max(start, cursor))
            cursor = max(cursor, end)
        try:
            physical = physical_lorom_page(_cpu_bank(page, False))
        except ValueError:
            physical = None
        output.append({"logical_storage_page": page, "physical_lorom_page": physical,
                       "source_identities": [source for _, _, source in intervals],
                       "payload_bytes_sum": sum(end - start for start, end, _ in intervals),
                       "unique_occupied_bytes": unique, "internal_gap_bytes": gaps,
                       "overlap_bytes": overlap, "highwater_offset": highwater,
                       "tail_padding_bytes": LOROM_PAGE_BYTES - highwater})
    return output


def build_layout_ledger(generator_report: dict[str, Any], cooked_manifest: dict[str, Any],
                        *, capacity_bytes: int = LOROM_MAX_BYTES) -> dict[str, Any]:
    """Account every byte placement once and cross-reference identical payloads."""
    sa1 = bool(generator_report.get("sa1_rom_bank_aliases", False))
    room_rows: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    program_rows: list[dict[str, Any]] = []
    for item in generator_report.get("room_segments", []):
        room_rows.append(_placement(item, purpose="complete cooked ROOM source/resource record",
            source=str(item["source_identity"]), payload_bytes=int(item["payload_bytes"]),
            offset=int(item.get("bank_offset", 0)), consumer="room-resource validation and room/resource parser",
            sa1_aliases=sa1, alignment=1))
    for item in generator_report.get("expected_room_directories", []):
        row = _placement(item, purpose="room integrity/dispatch directory",
            source=str(item.get("source_identity", item.get("label", "room directory"))),
            payload_bytes=int(item["payload_bytes"]), offset=int(item.get("bank_offset", 0)),
            consumer=str(item.get("consumer", "SCUMM room integrity validator")), sa1_aliases=sa1)
        if item.get("contained_in_source_identity") is not None:
            row["duplicated_from"] = {
                "source_identity": item["contained_in_source_identity"],
                "source_offset": int(item.get("contained_in_source_offset", 0)),
                "relationship": "same generated prefix bytes are also emitted in complete room resource",
            }
        row.update({"storage_kind": item.get("storage_kind", "SEPARATE_ROOM_DIRECTORY_COPY"),
                    "shared_storage": bool(item.get("shared_storage", False)),
                    "storage_alias_of": item.get("storage_alias_of"),
                    "storage_source_offset": item.get("storage_source_offset"),
                    "storage_payload_match_verified": bool(
                        item.get("storage_payload_match_verified", False)
                    )})
        table_rows.append(row)
    for item in generator_report.get("generated_table_placements", []):
        row = _placement(item, purpose="generated runtime lookup/navigation table",
            source=str(item.get("source_identity", item.get("label", "table"))),
            payload_bytes=int(item["payload_bytes"]), offset=int(item.get("bank_offset", 0)),
            consumer=str(item.get("consumer", "SCUMM runtime")), sa1_aliases=sa1)
        for key in ("label", "representation", "resolver_table"):
            if key in item:
                row[key] = item[key]
        table_rows.append(row)
    seen: dict[tuple[int, str], list[str]] = defaultdict(list)
    program_bytes = 0
    for item in generator_report.get("program_map", []):
        if item.get("rom_bank") is None:
            continue
        identity = str(item.get("program_unit_identity", item.get("identity")))
        row = _placement(item, purpose="executable bytecode carrier", source=identity,
            payload_bytes=int(item["length"]), offset=int(item.get("bank_offset", 0)),
            consumer="resident resolver bytecode fetch path", sa1_aliases=sa1)
        row.update({"payload_sha256": item.get("sha256"),
                    "program_unit_identity": item.get("program_unit_identity"),
                    "kind": item.get("kind"), "room": item.get("room"),
                    "program_id": item.get("id"),
                    "storage_kind": item.get("storage_kind", "SEPARATE_PROGRAM_BODY"),
                    "shared_storage": bool(item.get("shared_storage", False)),
                    "storage_alias_of": item.get("storage_alias_of"),
                    "storage_source_offset": item.get("storage_source_offset"),
                    "storage_payload_match_verified": bool(
                        item.get("storage_payload_match_verified", False)
                    )})
        program_rows.append(row)
        program_bytes += int(item["length"])
        digest = str(item.get("sha256", ""))
        if digest:
            seen[(int(item["length"]), digest)].append(identity)
    all_rows = room_rows + table_rows + program_rows
    separately_stored_program_rows = [row for row in program_rows if not row["shared_storage"]]
    for row in all_rows:
        digest = row.get("payload_sha256") or row.get("source_sha256")
        key = (int(row["payload_bytes"]), str(digest or ""))
        row["contains_same_bytes_as"] = sorted(set(seen.get(key, [])) - {str(row["source_identity"])})
    program_hashes: set[tuple[int, str]] = set()
    repeated_program_bytes = repeated_program_count = 0
    for row in program_rows:
        key = (int(row["payload_bytes"]), str(row.get("source_sha256", "")))
        if key in program_hashes:
            repeated_program_count += 1
            repeated_program_bytes += key[0]
        else:
            program_hashes.add(key)
    separate_program_hashes: set[tuple[int, str]] = set()
    repeated_separate_program_bytes = repeated_separate_program_count = 0
    for row in separately_stored_program_rows:
        digest = str(row.get("source_sha256", ""))
        key = (int(row["payload_bytes"]), digest)
        if digest and key in separate_program_hashes:
            repeated_separate_program_count += 1
            repeated_separate_program_bytes += key[0]
        else:
            separate_program_hashes.add(key)
    body_by_key = {(str(x.get("kind")), -1 if x.get("room") is None else int(x["room"]),
                    -1 if x.get("number") is None else int(x["number"])):
                   (int(x["length"]), str(x.get("sha256", "")))
                   for x in generator_report.get("program_map", []) if x.get("kind") != "GLOBAL"}
    duplicate_count = duplicate_bytes = 0
    mismatches = []
    for record in cooked_manifest.get("records", []):
        room = int(record["room"])
        for script in record.get("scripts", []):
            key = (str(script["kind"]), room, int(script["number"]))
            if body_by_key.get(key) == (int(script["program_length"]), str(script["sha256"])):
                duplicate_count += 1
                duplicate_bytes += int(script["program_length"])
            else:
                mismatches.append(str(script.get("identity", key)))
    room_page = _page_layout(room_rows)
    program_page = _page_layout(separately_stored_program_rows)
    emitted_table_rows = [row for row in table_rows if not row.get("shared_storage")]
    table_page = _page_layout(emitted_table_rows)
    generated_source = generator_report.get("generated_assembly_source", {})
    table_payload = sum(int(r["payload_bytes"]) for r in emitted_table_rows)
    room_payload = sum(int(r["payload_bytes"]) for r in room_rows)
    last_bank = int(generator_report.get("last_bank", -1))
    highwater = last_bank + 1
    span = highwater * LOROM_PAGE_BYTES
    room_padding = sum(int(x["tail_padding_bytes"]) for x in room_page)
    program_padding = sum(int(x["tail_padding_bytes"]) for x in program_page)
    table_padding = sum(int(x["tail_padding_bytes"]) for x in table_page)
    page_purposes: dict[int, set[str]] = defaultdict(set)
    for row in all_rows:
        page_purposes[int(row["logical_storage_page"])].add(str(row["purpose"]))
    sections: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for section in generator_report.get("generated_bank_sections", []):
        sections[int(section["logical_storage_page"])].append(section)
    reserved = set(int(x) for x in generator_report.get("reserved_banks", []))
    roles = []
    for page in range(highwater):
        purposes = sorted(page_purposes.get(page, set()))
        assembly = sections.get(page, [])
        if page in reserved and not purposes:
            role = "EXPLICITLY_RESERVED_RUNTIME_PAGE"
        elif purposes and assembly:
            role = "PAYLOAD_WITH_GENERATED_ASSEMBLY_SECTION"
        elif purposes:
            role = "MEASURED_PAYLOAD_PAGE"
        elif assembly:
            role = "GENERATED_ASSEMBLY_SECTION_SIZE_REQUIRES_ASSEMBLER_MAP"
        elif page < int(generator_report.get("first_bank", 32)):
            role = "NATIVE_RUNTIME_OR_HEADER_PREFIX_RESERVED_BY_BACKEND"
        else:
            role = "GENERATOR_ALLOCATION_GAP_OR_ALIGNMENT_RESERVE"
        roles.append({"logical_storage_page": page, "role": role,
                      "payload_purposes": purposes, "generated_assembly_source_sections": assembly})
    separately_stored_program_bytes = sum(
        int(row["payload_bytes"]) for row in separately_stored_program_rows
    )
    aliased_program_bytes = program_bytes - separately_stored_program_bytes
    report_payload = room_payload + separately_stored_program_bytes + table_payload
    preflight = preflight_lorom_layout(generator_report, capacity_bytes=capacity_bytes)
    return {
        "schema": "same_scumm_v5_lorom_layout_ledger_v2",
        "target": {"mapping": "LoROM 32KiB pages; CPU bank mirrors share physical pages",
                   "physical_rom_capacity_bytes": capacity_bytes,
                   "physical_rom_capacity_pages": capacity_bytes // LOROM_PAGE_BYTES,
                   "logical_page_highwater_exclusive": highwater,
                   "logical_page_span_bytes": span,
                   "mapped_span_is_theoretical_minimum": False,
                   "occupied_logical_pages_with_payload": len({int(x["logical_storage_page"]) for x in all_rows}),
                   "occupied_physical_lorom_pages_with_payload": len({x["physical_lorom_page"] for x in all_rows if x["physical_lorom_page"] is not None})},
        "totals": {
            "complete_room_resource_payload_bytes": room_payload,
            "program_unit_body_bytes": program_bytes,
            "program_unit_bodies_shared_with_room_records": aliased_program_bytes,
            "separately_emitted_program_body_bytes": separately_stored_program_bytes,
            "program_unit_bodies_shared_with_room_record_count": sum(
                1 for row in program_rows if row["shared_storage"]
            ),
            "program_unit_unique_body_bytes_by_sha256": sum(k[0] for k in program_hashes),
            "identical_program_body_repetitions": repeated_program_count,
            "identical_program_body_repeated_bytes": repeated_program_bytes,
            "exact_room_body_duplicates": duplicate_count,
            "exact_room_body_duplicate_bytes": duplicate_bytes,
            "generated_room_directories_and_lookup_table_bytes": table_payload,
            "generated_table_payload_bytes_reported_by_generator": generator_report.get("generated_table_payload_bytes"),
            "program_pointer_directory_bytes": sum(int(x["payload_bytes"]) for x in table_rows if x.get("representation") == "u16 program lengths followed by u24 relocated body pointers"),
            "runtime_resolver_tables_are_subset_of_generated_table_payload": True,
            "runtime_resolver_tables_bytes_subset": sum(
                int(row["payload_bytes"]) for row in table_rows if row.get("resolver_table")
            ),
            "room_directory_duplicate_bytes": sum(
                int(row["payload_bytes"]) for row in emitted_table_rows if row.get("duplicated_from")
            ),
            "room_directory_duplicate_count": sum(
                1 for row in emitted_table_rows if row.get("duplicated_from")
            ),
            "room_directory_content_shared_bytes": sum(
                int(row["payload_bytes"]) for row in table_rows if row.get("shared_storage")
            ),
            "room_directory_content_shared_count": sum(
                1 for row in table_rows if row.get("shared_storage")
            ),
            "room_page_tail_padding_bytes": room_padding,
            "program_bank_tail_padding_bytes": program_padding,
            "table_page_tail_padding_bytes": table_padding,
            "physically_placed_payload_bytes_non_double_counted": report_payload,
            "physical_payload_formula": "room segments + separately stored program bodies + emitted tables/directories",
            "program_bodies_also_present_in_cooked_record_bytes": duplicate_bytes,
            "program_bodies_also_present_in_cooked_record_count": duplicate_count,
            "program_body_duplicate_bytes_avoided_by_verified_aliasing": aliased_program_bytes,
            "room_directory_duplicate_content_bytes_still_emitted": sum(
                int(row["payload_bytes"]) for row in emitted_table_rows if row.get("duplicated_from")
            ),
            "identical_separate_program_body_bytes_still_emitted": repeated_separate_program_bytes,
            "identical_separate_program_body_repetitions_still_emitted": repeated_separate_program_count,
            "known_duplicate_content_still_emitted_bytes": repeated_separate_program_bytes + sum(
                int(row["payload_bytes"]) for row in emitted_table_rows if row.get("duplicated_from")
            ),
            "generated_assembly_source_text_bytes": sum(int(generated_source.get(k, 0)) for k in ("room_include_text_bytes", "banked_include_text_bytes")),
            "generated_assembly_source_lines": sum(int(generated_source.get(k, 0)) for k in ("room_include_lines", "banked_include_lines")),
            "generated_dispatch_machine_code_bytes": None,
            "generated_dispatch_machine_code_status": "NOT_ASSEMBLED: capacity preflight result is authoritative",
            "base_runtime_machine_code_bytes": None,
            "base_runtime_machine_code_note": "Requires a successful assembler map; source text is not machine size",
            "unclassified_remainder_of_logical_span_bytes": max(0, span - report_payload - room_padding - program_padding - table_padding),
            "unclassified_remainder_note": "Includes fixed runtime/header, generated code whose machine size needs a map, reserved pages, and allocation gaps; not a lower bound",
        },
        "segments": sorted(all_rows, key=lambda x: (int(x["logical_storage_page"]), int(x["page_offset"]), str(x["source_identity"]))),
        "page_layout": {"room_resources": room_page, "program_bodies": program_page, "runtime_directories_and_tables": table_page},
        "logical_page_roles": roles,
        "room_bodies_not_exactly_reconciled": mismatches,
        "layout_preflight": preflight,
    }
