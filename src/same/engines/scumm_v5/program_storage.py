"""Compiler-owned SAMEPKG storage for SCUMM v5 ProgramUnit bodies.

The package directory is a storage address space, not a runtime selector
table.  ProgramUnit IDs retain the stable ordering from NativeProgramDirectory
and each record points into one packed executable collection section.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zlib
from typing import Mapping

from same.package import build_package, inspect_package


PROGRAM_SECTION = "SC5CODE"
PROGRAM_SECTION_KIND = "SCVM"
ROOM_SECTION = "SC5ROOM"
ROOM_SECTION_KIND = "SCVR"
LIVE_ROOM_SECTION = "SC5LIVE"
LIVE_ROOM_SECTION_KIND = "SCVL"
VISUAL_SECTION = "SC5VIS"
VISUAL_SECTION_KIND = "SCVV"
PROGRAM_STORAGE_SCHEMA = "same_scumm_v5_msu1_program_storage_v1"
ROOM_RECORD_LIMIT = 0x0800
LIVE_ROOM_DIRECTORY_RECORD_SIZE = 10
VISUAL_DIRECTORY_RECORD_SIZE = 26


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=True) + "\n").encode("ascii")


def read_package_prefix_sections(
    package_path: Path, section_names: tuple[str, ...] | None,
) -> tuple[tuple[str, str, bytes, int], ...]:
    """Return validated, redistributable SAMEPKG sections for ordered prefixing.

    This deliberately consumes the repository's SAMEPKG v1 reader.  It does
    not copy the source package header or invent a wrapper format: callers may
    place selected section payloads before SC5CODE in a newly generated
    package, preserving the original section kind/alignment and bytes.
    """
    if section_names == ():
        return ()
    info = inspect_package(package_path, verify=True)
    raw = package_path.read_bytes()
    by_name = {section.name: section for section in info.sections}
    names = tuple(section.name for section in info.sections) if section_names is None else section_names
    if len(set(names)) != len(names):
        raise ValueError("SAMEPKG prefix section names must be unique")
    result = []
    for name in names:
        section = by_name.get(name)
        if section is None:
            raise ValueError(f"SAMEPKG prefix section not found: {name}")
        result.append((
            section.name,
            section.kind,
            raw[section.offset:section.offset + section.size],
            section.alignment,
        ))
    return tuple(result)


def _record_include(
    records: list[dict[str, object]],
    room_records: list[dict[str, object]],
    room_count: int,
    rom_bank: int | None,
    live_room_records: list[dict[str, object]] | None = None,
    visual_records: list[dict[str, object]] | None = None,
) -> str:
    live_room_records = live_room_records or []
    visual_records = visual_records or []
    for label, rows in (("live-room", live_room_records), ("visual", visual_records)):
        seen: set[int] = set()
        for row in rows:
            room = int(row["room"])
            if not 0 <= room < room_count or room in seen:
                raise ValueError(f"{label} room directory has an invalid/duplicate room {room}")
            seen.add(room)
            if not 0 <= int(row["package_offset"]) <= 0xFFFFFFFF:
                raise ValueError(f"{label} package offset does not fit u32")
            if not 0 < int(row["length"]) <= 0xFFFF:
                raise ValueError(f"{label} length does not fit a nonzero u16")
            if label == "live-room":
                if len(str(row["crc32"])) != 8:
                    raise ValueError("live-room CRC-32 must be eight hexadecimal digits")
                int(str(row["crc32"]), 16)
    for row in visual_records:
        for field in ("pixel_package_offset", "palette_package_offset"):
            if not 0 <= int(row[field]) <= 0xFFFFFFFF:
                raise ValueError(f"visual {field} does not fit u32")
        for field in ("pixel_length", "palette_length", "width", "height", "pitch"):
            if not 0 < int(row[field]) <= 0xFFFF:
                raise ValueError(f"visual {field} does not fit a nonzero u16")
        for field in ("pixel_crc32", "palette_crc32"):
            if len(str(row[field])) != 8:
                raise ValueError(f"visual {field} must be eight hexadecimal digits")
            int(str(row[field]), 16)
    directory_bytes = (
        len(records) * 10 + room_count * 10
        + room_count * LIVE_ROOM_DIRECTORY_RECORD_SIZE
        + room_count * VISUAL_DIRECTORY_RECORD_SIZE
    )
    if directory_bytes > 0x8000:
        raise ValueError(
            "SCUMM MSU ProgramUnit/room directory exceeds one LoROM data bank: "
            f"{directory_bytes} bytes"
        )
    lines = [
        "; Generated compiler-owned SCUMM ProgramUnit -> SAMEPKG directory.",
        "; Records: u32 package offset, u16 length, u32 CRC-32; IDs are array indexes.",
    ]
    if rom_bank is not None:
        if not 0 <= rom_bank <= 0xFF:
            raise ValueError("SCUMM MSU ProgramUnit directory bank must fit the LoROM bank byte")
        lines.extend((f".bank {rom_bank}", ".org $8000"))
    lines.extend([
        f"SCUMM_MSU1_PROGRAM_COUNT = ${len(records):04X}",
        "SCUMM_MSU1_PROGRAM_RECORD_SIZE = $000A",
        "ScummV5_MsuProgramRecords:",
    ])
    raw = bytearray()
    for expected_id, row in enumerate(records):
        if int(row["program_unit_id"]) != expected_id:
            raise ValueError("ProgramUnit storage records must be dense and ID ordered")
        raw += int(row["package_offset"]).to_bytes(4, "little")
        raw += int(row["length"]).to_bytes(2, "little")
        raw += int(row["crc32"], 16).to_bytes(4, "little")
    for start in range(0, len(raw), 16):
        lines.append("    .byte " + ",".join(f"${value:02X}" for value in raw[start:start + 16]))
    if not raw:
        lines.append("    .byte $00")
    lines.extend((
        f"SCUMM_MSU1_ROOM_COUNT = ${room_count:04X}",
        "SCUMM_MSU1_ROOM_RECORD_SIZE = $000A",
        "ScummV5_MsuRoomRecords:",
    ))
    room_by_id = {int(row["room"]): row for row in room_records}
    room_raw = bytearray()
    for room_id in range(room_count):
        row = room_by_id.get(room_id)
        if row is None:
            room_raw.extend(bytes(10))
        else:
            room_raw += int(row["package_offset"]).to_bytes(4, "little")
            room_raw += int(row["length"]).to_bytes(2, "little")
            room_raw += int(row["crc32"], 16).to_bytes(4, "little")
    for start in range(0, len(room_raw), 16):
        lines.append("    .byte " + ",".join(f"${value:02X}" for value in room_raw[start:start + 16]))
    if not room_raw:
        lines.append("    .byte $00")
    if live_room_records:
        lines.extend((
            f"SCUMM_MSU1_LIVE_ROOM_COUNT = ${room_count:04X}",
            f"SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE = ${LIVE_ROOM_DIRECTORY_RECORD_SIZE:04X}",
            "ScummV5_MsuLiveRoomRecords:",
        ))
        by_room = {int(row["room"]): row for row in live_room_records}
        raw = bytearray()
        for room_id in range(room_count):
            row = by_room.get(room_id)
            if row is None:
                raw.extend(bytes(LIVE_ROOM_DIRECTORY_RECORD_SIZE))
            else:
                raw += int(row["package_offset"]).to_bytes(4, "little")
                raw += int(row["length"]).to_bytes(2, "little")
                raw += int(row["crc32"], 16).to_bytes(4, "little")
        for start in range(0, len(raw), 16):
            lines.append("    .byte " + ",".join(f"${value:02X}" for value in raw[start:start + 16]))
    if visual_records:
        lines.extend((
            f"SCUMM_MSU1_VISUAL_COUNT = ${room_count:04X}",
            f"SCUMM_MSU1_VISUAL_RECORD_SIZE = ${VISUAL_DIRECTORY_RECORD_SIZE:04X}",
            "ScummV5_MsuVisualRecords:",
        ))
        by_room = {int(row["room"]): row for row in visual_records}
        raw = bytearray()
        for room_id in range(room_count):
            row = by_room.get(room_id)
            if row is None:
                raw.extend(bytes(VISUAL_DIRECTORY_RECORD_SIZE))
            else:
                raw += int(row["pixel_package_offset"]).to_bytes(4, "little")
                raw += int(row["pixel_length"]).to_bytes(2, "little")
                raw += int(row["pixel_crc32"], 16).to_bytes(4, "little")
                raw += int(row["palette_package_offset"]).to_bytes(4, "little")
                raw += int(row["palette_length"]).to_bytes(2, "little")
                raw += int(row["palette_crc32"], 16).to_bytes(4, "little")
                raw += int(row["width"]).to_bytes(2, "little")
                raw += int(row["height"]).to_bytes(2, "little")
                raw += int(row["pitch"]).to_bytes(2, "little")
        for start in range(0, len(raw), 16):
            lines.append("    .byte " + ",".join(f"${value:02X}" for value in raw[start:start + 16]))
    return "\n".join(lines) + "\n"


def build_program_storage(
    directory: Mapping[str, object],
    bodies: Mapping[str, bytes],
    output_dir: Path,
    *,
    max_cached_body_bytes: int = 0x0800,
    prefix_sections: tuple[tuple[str, str, bytes, int], ...] = (),
    room_resources: Mapping[int, bytes] | None = None,
    live_room_resources: Mapping[int, bytes] | None = None,
    room_visual_resources: Mapping[int, bytes] | None = None,
    rom_bank: int | None = None,
) -> dict[str, object]:
    """Package all selector-bearing units and emit a deterministic ROM index.

    A body larger than the native bounded cache is rejected here, before a
    misleading executable directory can be emitted.  Resource/object records
    without selector-bearing code are intentionally absent from this mapping.
    """
    entries = directory.get("entries")
    if not isinstance(entries, list):
        raise ValueError("canonical ProgramUnit directory has no entries")
    ordered = sorted(entries, key=lambda item: int(item["program_unit_id"]))
    identities = [str(item["identity"]) for item in ordered]
    if len(set(identities)) != len(identities):
        raise ValueError("canonical ProgramUnit directory contains duplicate identities")
    missing = sorted(set(identities) - set(bodies))
    extra = sorted(set(bodies) - set(identities))
    if missing or extra:
        raise ValueError(f"ProgramUnit body reconciliation failed: missing={missing[:4]}, extra={extra[:4]}")

    output_dir.mkdir(parents=True, exist_ok=True)
    body_file = output_dir / "scumm-program-bodies.bin"
    payload = bytearray()
    rows: list[dict[str, object]] = []
    for expected_id, entry in enumerate(ordered):
        unit_id = int(entry["program_unit_id"])
        if unit_id != expected_id:
            raise ValueError("canonical ProgramUnit IDs must be dense from zero")
        identity = str(entry["identity"])
        body = bytes(bodies[identity])
        if len(body) > max_cached_body_bytes:
            raise ValueError(
                f"{identity} body is {len(body)} bytes; bounded native cache limit is "
                f"{max_cached_body_bytes}"
            )
        offset = len(payload)
        crc = zlib.crc32(body) & 0xFFFFFFFF
        payload.extend(body)
        rows.append({
            "program_unit_id": unit_id,
            "identity": identity,
            "package_section": PROGRAM_SECTION,
            "section_relative_offset": offset,
            "length": len(body),
            "crc32": f"{crc:08x}",
            "sha256": hashlib.sha256(body).hexdigest(),
            "bundle": entry.get("bundle"),
            "dispatch": entry.get("dispatch", {}),
            "source_provenance": entry.get("source_provenance"),
        })
    body_file.write_bytes(payload)
    package_manifest = output_dir / "same-package.json"
    package_sections: list[dict[str, object]] = []
    used_section_names = {name for name, _kind, _data, _alignment in prefix_sections}
    for name, kind, data, alignment in prefix_sections:
        if name in {PROGRAM_SECTION, ROOM_SECTION, LIVE_ROOM_SECTION, VISUAL_SECTION}:
            raise ValueError(f"reserved SCUMM package section name {name}")
        if alignment <= 0 or alignment & (alignment - 1):
            raise ValueError(f"package section {name} alignment must be a power of two")
        prefix_file = output_dir / f"prefix-{name}.bin"
        prefix_file.write_bytes(bytes(data))
        package_sections.append({
            "name": name,
            "kind": kind,
            "path": prefix_file.name,
            "alignment": alignment,
            "flags": ["streamable", "read_only"],
        })
    room_rows: list[dict[str, object]] = []
    room_payload = bytearray()
    room_by_id = dict(room_resources or {})
    if len(room_by_id) != len(room_resources or {}):
        raise ValueError("duplicate cooked room resource identity")
    if any(isinstance(room, bool) or not 0 <= int(room) <= 255 for room in room_by_id):
        raise ValueError("cooked room IDs must fit u8")
    if room_by_id and ROOM_SECTION in used_section_names:
        raise ValueError(f"reserved SCUMM package section name {ROOM_SECTION}")
    if room_by_id:
        room_file = output_dir / "scumm-cooked-rooms.bin"
        for room_id, room_body in sorted(room_by_id.items()):
            body = bytes(room_body)
            if not body or len(body) > ROOM_RECORD_LIMIT:
                raise ValueError(
                    f"cooked room {room_id} body length {len(body)} is outside "
                    f"the bounded {ROOM_RECORD_LIMIT}-byte native staging window"
                )
            offset = len(room_payload)
            room_payload.extend(body)
            room_rows.append({
                "room": int(room_id),
                "section_relative_offset": offset,
                "length": len(body),
                "crc32": f"{zlib.crc32(body) & 0xFFFFFFFF:08x}",
                "sha256": hashlib.sha256(body).hexdigest(),
            })
        room_file.write_bytes(room_payload)
        package_sections.append({
            "name": ROOM_SECTION,
            "kind": ROOM_SECTION_KIND,
            "path": room_file.name,
            "alignment": 1,
            "flags": ["streamable", "read_only"],
        })
    live_room_rows: list[dict[str, object]] = []
    live_room_payload = bytearray()
    live_by_id = dict(live_room_resources or {})
    if any(isinstance(room, bool) or not 0 <= int(room) <= 255 for room in live_by_id):
        raise ValueError("live room IDs must fit u8")
    if live_by_id and LIVE_ROOM_SECTION in used_section_names:
        raise ValueError(f"reserved SCUMM package section name {LIVE_ROOM_SECTION}")
    if live_by_id:
        from .live_room_resources import decode_live_room

        live_file = output_dir / "scumm-live-room-resources.bin"
        for room_id, resource in sorted(live_by_id.items()):
            body = bytes(resource)
            decoded_live = decode_live_room(body, expected_room=int(room_id))
            if len(body) > 0xFFFF:
                raise ValueError(f"live room {room_id} exceeds directory length field")
            offset = len(live_room_payload)
            live_room_payload.extend(body)
            live_room_rows.append({
                "room": int(room_id), "section_relative_offset": offset,
                "length": len(body), "crc32": f"{decoded_live.crc32:08x}",
                "sha256": decoded_live.sha256,
            })
        live_file.write_bytes(live_room_payload)
        package_sections.append({
            "name": LIVE_ROOM_SECTION, "kind": LIVE_ROOM_SECTION_KIND,
            "path": live_file.name, "alignment": 1,
            "flags": ["streamable", "read_only"],
        })
    visual_rows: list[dict[str, object]] = []
    visual_payload = bytearray()
    visual_by_id = dict(room_visual_resources or {})
    if any(isinstance(room, bool) or not 0 <= int(room) <= 255 for room in visual_by_id):
        raise ValueError("visual room IDs must fit u8")
    if visual_by_id and VISUAL_SECTION in used_section_names:
        raise ValueError(f"reserved SCUMM package section name {VISUAL_SECTION}")
    if visual_by_id:
        from .room_visual import HEADER as VISUAL_HEADER, decode_room_visual

        visual_file = output_dir / "scumm-room-visual-resources.bin"
        for room_id, resource in sorted(visual_by_id.items()):
            body = bytes(resource)
            visual = decode_room_visual(body, expected_room=int(room_id))
            if len(body) > 0xFFFF:
                raise ValueError(f"room {room_id} visual record exceeds directory length field")
            header_values = VISUAL_HEADER.unpack_from(body)
            palette_offset = int(header_values[10])
            pixel_offset = int(header_values[12])
            palette = body[palette_offset:palette_offset + 768]
            pixels = body[pixel_offset:pixel_offset + len(visual.pixels)]
            if len(palette) != 768 or len(pixels) != len(visual.pixels):
                raise ValueError(f"room {room_id} visual payload bounds differ")
            base = len(visual_payload)
            visual_payload.extend(body)
            visual_rows.append({
                "room": int(room_id), "section_relative_offset": base,
                "length": len(body), "sha256": visual.record_sha256,
                "palette_relative_offset": base + palette_offset,
                "palette_length": len(palette),
                "palette_crc32": f"{zlib.crc32(palette) & 0xFFFFFFFF:08x}",
                "pixel_relative_offset": base + pixel_offset,
                "pixel_length": len(pixels),
                "pixel_crc32": f"{zlib.crc32(pixels) & 0xFFFFFFFF:08x}",
                "width": visual.width, "height": visual.height, "pitch": visual.pitch,
            })
        visual_file.write_bytes(visual_payload)
        package_sections.append({
            "name": VISUAL_SECTION, "kind": VISUAL_SECTION_KIND,
            "path": visual_file.name, "alignment": 1,
            "flags": ["streamable", "read_only"],
        })
    package_sections.append({
            "name": PROGRAM_SECTION,
            "kind": PROGRAM_SECTION_KIND,
            "path": body_file.name,
            "alignment": 1,
            "flags": ["executable", "streamable", "read_only"],
    })
    package_manifest.write_bytes(_canonical_json({
        "same_package": 1,
        "sections": package_sections,
    }))
    package_path = output_dir / "scumm-programs.msu"
    package_info = build_package(package_manifest, package_path)
    section = next(row for row in package_info.sections if row.name == PROGRAM_SECTION)
    room_section = next((row for row in package_info.sections if row.name == ROOM_SECTION), None)
    live_room_section = next((row for row in package_info.sections if row.name == LIVE_ROOM_SECTION), None)
    visual_section = next((row for row in package_info.sections if row.name == VISUAL_SECTION), None)
    prefix_descriptors = []
    for name, kind, data, alignment in prefix_sections:
        packed = next(row for row in package_info.sections if row.name == name)
        prefix_descriptors.append({
            "name": name,
            "kind": kind,
            "package_offset": packed.offset,
            "payload_bytes": packed.size,
            "alignment": alignment,
            "crc32": f"{packed.crc32:08x}",
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    for row in rows:
        row["package_offset"] = section.offset + int(row["section_relative_offset"])
    if room_rows:
        assert room_section is not None
        for row in room_rows:
            row["package_offset"] = room_section.offset + int(row["section_relative_offset"])
    if live_room_rows:
        assert live_room_section is not None
        for row in live_room_rows:
            row["package_offset"] = live_room_section.offset + int(row["section_relative_offset"])
    if visual_rows:
        assert visual_section is not None
        for row in visual_rows:
            row["package_offset"] = visual_section.offset + int(row["section_relative_offset"])
            row["palette_package_offset"] = visual_section.offset + int(row["palette_relative_offset"])
            row["pixel_package_offset"] = visual_section.offset + int(row["pixel_relative_offset"])

    directory_bytes = _canonical_json(directory)
    result: dict[str, object] = {
        "schema": PROGRAM_STORAGE_SCHEMA,
        "id_width_bits": 16,
        "selector_values_emitted": False,
        "source_directory_sha256": hashlib.sha256(directory_bytes).hexdigest(),
        "package_section": section.to_dict(),
        "prefix_sections": prefix_descriptors,
        "program_count": len(rows),
        "program_body_bytes": len(payload),
        "room_resource_count": len(room_rows),
        "room_resource_bytes": len(room_payload),
        "room_section": None if room_section is None else room_section.to_dict(),
        "room_records": room_rows,
        "room_directory_count": max(room_by_id, default=-1) + 1,
        "live_room_resource_count": len(live_room_rows),
        "live_room_resource_bytes": len(live_room_payload),
        "live_room_section": None if live_room_section is None else live_room_section.to_dict(),
        "live_room_records": live_room_rows,
        "visual_resource_count": len(visual_rows),
        "visual_resource_bytes": len(visual_payload),
        "visual_section": None if visual_section is None else visual_section.to_dict(),
        "visual_records": visual_rows,
        "max_cached_body_bytes": max_cached_body_bytes,
        "records": rows,
        "package_sha256": hashlib.sha256(package_path.read_bytes()).hexdigest(),
    }
    (output_dir / "program-storage.json").write_bytes(_canonical_json(result))
    (output_dir / "scumm_msu1_programs.inc.pasm").write_text(
        _record_include(
            rows, room_rows, max(room_by_id, default=-1) + 1, rom_bank,
            live_room_rows, visual_rows,
        ), encoding="ascii",
    )
    return result
