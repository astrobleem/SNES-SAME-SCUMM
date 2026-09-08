#!/usr/bin/env python3
"""Build copyright-free cooked ROOM 49 records for the M25A SNES oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import zipfile

from same.engines.scumm_v5.cooked_room import ScriptChunkInput, decode_cooked_room, encode_cooked_room
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room import decode_room
from same.resources import MemoryResourceProvider
from same.profile import load_profile


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/m25a_nested_conformance.json"
FATE_ARCHIVE = Path(os.environ.get("SAME_FATE_DEMO_ARCHIVE", "/home/chad/fatedemo-box.zip"))


def source_member(bundle: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in bundle.namelist() if name.upper().endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"archive must contain one SCUMM {suffix} member")
    return matches[0]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def selected_corpus_identity(archive: Path) -> dict[str, object]:
    """Record the real Fate corpus used by source-backed fixture helpers."""
    archive_bytes = archive.read_bytes()
    with zipfile.ZipFile(archive) as bundle:
        members = {suffix: source_member(bundle, suffix) for suffix in (".000", ".001")}
        member_hashes = {
            suffix: sha(bundle.read(member)) for suffix, member in members.items()
        }
    return {
        "archive": str(archive.resolve()),
        "archive_sha256": sha(archive_bytes),
        "index_member": members[".000"],
        "index_sha256": member_hashes[".000"],
        "data_member": members[".001"],
        "data_sha256": member_hashes[".001"],
    }


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def room(
    entry: bytes,
    locals_: tuple[tuple[int, bytes], ...],
    *,
    objects: bool = False,
    object_payloads: tuple[bytes, ...] = (),
    walkbox_count: int = 2,
    overlap_walkboxes: bool = False,
) -> bytes:
    palette = bytes(value for index in range(256) for value in (index, index, index))
    strip = bytes((1,)) + bytes(range(16))
    smap = chunk(b"SMAP", struct.pack("<I", 12) + strip)
    walkboxes = [struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255)]
    for index in range(1, walkbox_count):
        if walkbox_count == 12:
            # Keep the reusable room-49 scenario geometry connected across
            # the accepted actor checkpoint and source object coordinates.
            left, top, right, bottom = -1000, -1000, 1000, 1000
        else:
            # The copyright-free 64-box fixture uses non-degenerate strips
            # with a small interior.  The previous one-pixel boxes made the
            # boundary convention dominate the target result and could not
            # support a real portal walk.
            if walkbox_count == 64:
                # A connected, copyright-free serpentine room keeps the
                # complete route on a normal 256x128 screen while assigning
                # distinct geometry to every high-index record.  Consecutive
                # records share a portal edge; this is deliberately a real
                # multi-leg route, not a destination lookup table.
                row, ordinal = divmod(index - 1, 8)
                col = ordinal if row % 2 == 0 else 7 - ordinal
                left, top = col * 16, row * 16
                # The accessor fixture uses disjoint interiors so each
                # placement request identifies its requested record.  The
                # movement fixture opts into a four-pixel shared interval so
                # the canonical portal detector sees real successive legs.
                span = 20 if overlap_walkboxes else 15
                right, bottom = left + span, top + span
            else:
                left, top = (index - 1) * 8, 96
                right, bottom = left + 8, 120
        walkboxes.append(struct.pack(
            "<hhhhhhhhBBH", left, top, right, top,
            right, bottom, left, bottom, 0, 0, 255,
        ))
    if walkbox_count == 64:
        # A route table for the copyright-free movement fixture: from each
        # box, every later destination advances exactly one portal.  This
        # makes the target execute successive current/next-box geometry
        # reads, including boxes above the former 32-box boundary.
        matrix = b"".join(
            (bytes((source + 1, 63, source + 1, 0xFF))
             if source < 63 else bytes((0xFF,)))
            for source in range(64)
        )
    else:
        matrix = b"".join(
            bytes((source, source, source, 0xFF)) for source in range(walkbox_count)
        )
    return b"".join((
        chunk(b"RMHD", struct.pack(
            "<HHH", 8, 2, len(object_payloads) if object_payloads else (2 if objects else 0),
        )),
        chunk(b"TRNS", struct.pack("<H", 255)), chunk(b"CLUT", palette),
        chunk(b"BOXD", struct.pack("<H", walkbox_count) + b"".join(walkboxes)),
        chunk(b"BOXM", matrix),
        chunk(b"RMIM", chunk(b"RMIH", b"\x00\x00") + chunk(b"IM00", smap)),
        *(chunk(b"OBCD", payload) for payload in object_payloads),
        *(chunk(b"OBCD", chunk(b"CDHD", struct.pack(
            "<HBBBBBBhhB", object_id, x, y, width, height, 0, 0, x * 8, y * 8, 0,
        ))) for object_id, x, y, width, height in (
            ((590, 1, 1, 3, 1), (591, 4, 0, 2, 2)) if objects else ()
        ) if not object_payloads),
        chunk(b"ENCD", entry), chunk(b"EXCD", b"\x00"),
        *(chunk(b"LSCR", bytes((number,)) + program) for number, program in locals_),
    ))


def descriptors(payload: bytes) -> tuple[ScriptChunkInput, ...]:
    result: list[ScriptChunkInput] = []
    offset = 0
    while offset < len(payload):
        tag = payload[offset:offset + 4].decode("ascii")
        size = int.from_bytes(payload[offset + 4:offset + 8], "big")
        if tag in {"ENCD", "EXCD", "LSCR"}:
            if tag == "LSCR":
                number, body = payload[offset + 8], 9
                identity = f"room.49/LSCR.{number}"
            else:
                number, body = (10002 if tag == "ENCD" else 10001), 8
                identity = f"room.49/{tag}"
            result.append(ScriptChunkInput(tag, number, identity, offset, body, size - body))
        offset += size
    return tuple(result)


def set_word(variable: int, value: int) -> bytes:
    return bytes((0x1A, variable & 0xFF, variable >> 8, value & 0xFF, value >> 8))


def start_script(number: int) -> bytes:
    return bytes((0x0A, number, 0xFF))


def object_resource(
    object_id: int, entries: tuple[tuple[int, bytes], ...],
    program_prefix: bytes = b"",
    entry_offset_adjust: int = 0,
) -> bytes:
    """Build one full-header v5 OBCD with canonical relative VERB offsets."""
    header = struct.pack("<HBBBBBBhhB", object_id, 1, 1, 1, 1, 0, 0, 8, 8, 0)
    table_size = len(entries) * 3 + 1
    relative = 8 + table_size + entry_offset_adjust
    table = bytearray()
    programs = bytearray(program_prefix)
    for verb, program in entries:
        table.extend((verb, relative & 0xFF, relative >> 8))
        programs.extend(program)
        relative += len(program)
    table.append(0)
    return chunk(b"CDHD", header) + chunk(b"VERB", bytes(table + programs))


def startobject_scripts() -> tuple[
    bytes, tuple[tuple[int, bytes], ...], tuple[bytes, ...]
]:
    """Multiple copyright-free OBCD programs through the production path."""
    def start_object(object_id: int, verb: int, *arguments: int) -> bytes:
        encoded = bytearray((0x37, object_id & 0xFF, object_id >> 8, verb))
        for argument in arguments:
            encoded.extend((0, argument & 0xFF, argument >> 8))
        encoded.append(0xFF)
        return bytes(encoded)

    entry = b"".join((
        start_object(100, 10, 0xFFFE),
        start_object(100, 8),
        start_object(100, 9),  # canonical $FF fallback
        start_object(101, 10),
        start_object(101, 8),  # absent, no slot allocation
        bytes((0x80, 0x00)),
    ))
    objects = (
        object_resource(100, (
            (10, bytes((0x42, 200, 0xFF))),
            (8, bytes((0x42, 201, 0xFF))),
            (0xFF, bytes((0x42, 202, 0xFF))),
        )),
        object_resource(101, ((10, bytes((0x42, 203, 0xFF))),)),
    )
    locals_ = tuple(
        (number, set_word(variable, value) + bytes((0x00,)))
        for number, variable, value in (
            (200, 10, 0xA00A), (201, 11, 0xA008),
            (202, 12, 0xA0FF), (203, 13, 0xB00A),
        )
    )
    return entry, locals_, objects


def normal_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    # Static PC sentinels in globals 10/11 make the pre-start and exact resume
    # addresses independently visible alongside the runtime context trace.
    parent = b"".join((
        set_word(0x4000, 0x1111), set_word(0x4001, 0x2222),
        set_word(10, 15), start_script(201), set_word(11, 18),
        bytes((0x46, 0x00, 0x40)), bytes((0x80,)),
        set_word(12, 27), bytes((0x00,)),
    ))
    child = b"".join((
        set_word(0x4000, 0x3333), set_word(0x4001, 0x4444),
        set_word(13, 0), bytes((0x80,)), set_word(14, 16),
        bytes((0x46, 0x00, 0x40)), bytes((0x00,)),
    ))
    return start_script(200) + bytes((0x00,)), ((200, parent), (201, child))


def depth_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    scripts = []
    for number in range(200, 224):
        # Script 223's start of 224 is the attempted 25th suspended context:
        # ENCD plus LSCR 200..223 already occupy all 25 scheduler slots.
        program = set_word(0x4000, number) + start_script(number + 1)
        program += bytes((0x46, 0x01, 0x40, 0x00))
        scripts.append((number, program))
    return start_script(200) + bytes((0x00,)), tuple(scripts)


def missing_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    parent = set_word(0x4000, 0x5151) + start_script(250) + set_word(15, 0xDEAD) + bytes((0x00,))
    return start_script(200) + bytes((0x00,)), ((200, parent),)


def outer_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    # The room-entry ENCD is an outer interpreter frame (return mode zero).
    # Its child stops immediately; ENCD must resume at PC 8, yield at PC 14,
    # resume on the next engine frame at PC 14, and terminate normally.
    entry = b"".join((
        set_word(10, 0x1010), start_script(200), set_word(11, 0x1111),
        bytes((0x80,)), set_word(12, 0x1212), bytes((0x00,)),
    ))
    child = set_word(0x4000, 0x2020) + bytes((0x00,))
    return entry, ((200, child),)


def scheduler_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    """Copyright-free integrated-pass oracle for yielded room-local slots."""
    parent = b"".join((
        set_word(0x4000, 0xA0A0), set_word(10, 0x000A),
        start_script(201), set_word(12, 0x000D), bytes((0x80,)),
        set_word(13, 0x000F), bytes((0x00,)),
    ))
    child = b"".join((
        set_word(0x4000, 0xB0B0), set_word(11, 0x000B), bytes((0x80,)),
        set_word(14, 0x000E), bytes((0x00,)),
    ))
    repeated = b"".join((
        set_word(0x4000, 0xC0C0), set_word(20, 0x0020), bytes((0x80,)),
        set_word(21, 0x0021), bytes((0x80,)), set_word(22, 0x0022),
        bytes((0x00,)),
    ))
    terminates = set_word(23, 0x0030) + bytes((0x00,))
    stopped = set_word(24, 0x0040) + bytes((0x80,)) + set_word(25, 0x0041) + bytes((0x00,))
    entry = b"".join((
        start_script(200), start_script(202), start_script(203),
        start_script(204), bytes((0x62, 204, 0x00)),
    ))
    return entry, (
        (200, parent), (201, child), (202, repeated),
        (203, terminates), (204, stopped),
    )


def putactor_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    program = bytearray()
    for index, opcode in enumerate((0x01, 0x21, 0x41, 0x61, 0x81, 0xA1, 0xC1, 0xE1)):
        actor, x, y = index + 1, 300 + index, 400 + index
        # Canonical actorOps ignore-boxes keeps this fixture about operand
        # decoding rather than the synthetic room's placement geometry.
        program.extend((0x13, actor, 0x14, 0xFF, 0x2D, actor, 49))
        if opcode & 0x80:
            program.extend(set_word(10 + index, actor))
        if opcode & 0x40:
            program.extend(set_word(20 + index, x))
        if opcode & 0x20:
            program.extend(set_word(30 + index, y))
        program.append(opcode)
        program.extend(((10 + index) & 0xFF, 0) if opcode & 0x80 else (actor,))
        program.extend(((20 + index) & 0xFF, 0) if opcode & 0x40 else (x & 0xFF, x >> 8))
        program.extend(((30 + index) & 0xFF, 0) if opcode & 0x20 else (y & 0xFF, y >> 8))
    program.append(0x80)
    return start_script(200) + bytes((0x00,)), ((200, bytes(program)),)


def room55_accessor_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    """Copyright-free target exercise: place actor 1 once in every box."""
    program = bytearray()
    # Box 0 is the canonical BOXD sentinel and is not a placement target;
    # the 63 real boxes are exercised at their distinct interior centres.
    # These coordinates deliberately make the production placement scan load
    # each high-index record rather than falling through with result_box=$FF.
    for index in range(1, 64):
        row, ordinal = divmod(index - 1, 8)
        col = ordinal if row % 2 == 0 else 7 - ordinal
        # Stay away from the inclusive/exclusive edge convention used by the
        # placement clamp, especially on the last row (y=112..128).
        x, y = col * 16 + 4, row * 16 + 4
        program.extend((0x01, 1, x & 0xFF, x >> 8, y & 0xFF, y >> 8, 0x80))
    program.append(0x00)
    return start_script(200) + bytes((0x00,)), ((200, bytes(program)),)


def room55_movement_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    """Copyright-free multi-leg route across high-numbered boxes."""
    # Start in the first valid box and route through every later portal to
    # the distinct high-index destination.  This keeps initial placement
    # ordinary while still crossing the historical 32-box boundary.
    start_x, target_x = 4, 24
    start_y, target_y = 4, 114
    # Use a normal room-entry -> LSCR handoff so movement is owned by the
    # production C4 scheduler rather than by a special direct ENCD loop.
    program = bytes((
        0x2D, 1, 49,
        0x01, 1, start_x & 0xFF, start_x >> 8, start_y & 0xFF, start_y >> 8,
        0x80,
        0x1E, 1, target_x & 0xFF, target_x >> 8, target_y & 0xFF, target_y >> 8,
        # Direct waitForActor is AE,sub-op=1,actor=1.
        0xAE, 1, 1,
    ))
    return start_script(200) + bytes((0x00,)), ((200, program),)


def putactor_invalid_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("01 20 2c 01 90 01")),)


def putactor_malformed_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("01 01 47 02")),)


def setstate_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    program = bytearray()
    for index, opcode in enumerate((0x07, 0x47, 0x87, 0xC7)):
        object_id, state = (590 if index != 2 else 591), (0, 1, 255, 0x80)[index]
        if opcode & 0x80:
            program.extend(set_word(10 + index, object_id))
        if opcode & 0x40:
            program.extend(set_word(20 + index, state))
        program.append(opcode)
        program.extend(((10 + index) & 0xFF, 0) if opcode & 0x80
                       else (object_id & 0xFF, object_id >> 8))
        program.extend(((20 + index) & 0xFF, 0) if opcode & 0x40 else (state,))
    program.extend((0x80, 0x00))
    return start_script(200) + bytes((0x00,)), ((200, bytes(program)),)


def setstate_invalid_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("07 00 10 00")),)


def setstate_malformed_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("07 4e 02")),)


def crate_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...], tuple[bytes, ...]]:
    """Standalone room-49 scenario: engine-owned checkpoint plus crate OBCD."""
    # Actor placement is performed by the reusable engine-owned checkpoint
    # helper at room commit; ENCD remains an ordinary minimal room lifecycle.
    entry = bytes((0x00,))
    objects = (object_resource(594, (
        (3, bytes.fromhex("07 52 02 01 00")),
        (4, bytes.fromhex("07 52 02 00 00")),
    )),)
    return entry, (), objects


def authored_room49_objects(object_ids: tuple[int, ...]) -> tuple[bytes, ...]:
    """Return exact source OBCD payloads from the supplied Fate archive.

    The scenario room remains deliberately small, but its executable object
    records are cooked from the real PLAYFATE room instead of being recreated
    by the fixture.  This keeps object-script coverage source-bound while
    retaining the engine-owned checkpoint setup.
    """
    if not FATE_ARCHIVE.is_file():
        raise RuntimeError(f"missing supplied Fate archive: {FATE_ARCHIVE}")
    with zipfile.ZipFile(FATE_ARCHIVE) as bundle:
        raw = {
            "game.index": bundle.read(source_member(bundle, ".000")),
            "game.data": bundle.read(source_member(bundle, ".001")),
        }
    profile = load_profile(ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
                           verify_resources=False)
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(raw), parse_game_policy(profile))
    source_room = decode_room(provider.read("room.49"), key="room.49")
    wanted = set(object_ids)
    def normalize_obcd(obcd: bytes) -> bytes:
        # PLAYFATE stores VERB entry offsets from the VERB payload's cooked
        # program origin.  The generated object resolver already uses that
        # origin; adding the VERB header here shifts every entry by eight
        # bytes (object 593 verb 8 would become authored $0F instead of $48).
        # Preserve source offsets and bytes exactly.
        cooked = bytearray(obcd[8:])
        offset = 0
        while offset + 8 <= len(cooked):
            tag = cooked[offset:offset + 4]
            size = int.from_bytes(cooked[offset + 4:offset + 8], "big")
            if size < 8 or offset + size > len(cooked):
                break
            if tag == b"VERB":
                cursor = offset + 8
                while cursor < offset + size:
                    verb = cooked[cursor]
                    cursor += 1
                    if verb == 0:
                        break
                    if cursor + 2 > offset + size:
                        break
                    entry = int.from_bytes(cooked[cursor:cursor + 2], "little")
                    cooked[cursor:cursor + 2] = entry.to_bytes(2, "little")
                    cursor += 2
                break
            offset += size
        return bytes(cooked)

    found = {item.object_id: normalize_obcd(item.obcd) for item in source_room.objects
             if item.object_id in wanted}
    missing = wanted - found.keys()
    if missing:
        raise RuntimeError(f"room.49 source OBCD missing objects: {sorted(missing)}")
    return tuple(found[object_id] for object_id in object_ids)


def _authored_global_script(number: int) -> bytes:
    """Read an authored global script from the supplied Fate resources."""
    if not FATE_ARCHIVE.is_file():
        raise RuntimeError(f"missing supplied Fate archive: {FATE_ARCHIVE}")
    with zipfile.ZipFile(FATE_ARCHIVE) as bundle:
        raw = {
            "game.index": bundle.read(source_member(bundle, ".000")),
            "game.data": bundle.read(source_member(bundle, ".001")),
        }
    profile = load_profile(ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
                           verify_resources=False)
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(raw), parse_game_policy(profile)
    )
    return provider.read(f"script.{number}")


def _authored_global_script_numbers() -> tuple[int, ...]:
    """Return the source DSCR entries which actually have global resources."""
    if not FATE_ARCHIVE.is_file():
        raise RuntimeError(f"missing supplied Fate archive: {FATE_ARCHIVE}")
    with zipfile.ZipFile(FATE_ARCHIVE) as bundle:
        raw = {
            "game.index": bundle.read(source_member(bundle, ".000")),
            "game.data": bundle.read(source_member(bundle, ".001")),
        }
    profile = load_profile(ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
                           verify_resources=False)
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(raw), parse_game_policy(profile)
    )
    available = set(provider.keys())
    return tuple(
        number for number, room_number in enumerate(provider._directories["DSCR"].rooms)
        if room_number and f"script.{number}" in available
    )


def _authored_global_classes(count: int = 600) -> bytes:
    """Serialize the source DOBJ class masks for the scenario cooker."""
    if not FATE_ARCHIVE.is_file():
        raise RuntimeError(f"missing supplied Fate archive: {FATE_ARCHIVE}")
    with zipfile.ZipFile(FATE_ARCHIVE) as bundle:
        raw = {
            "game.index": bundle.read(source_member(bundle, ".000")),
            "game.data": bundle.read(source_member(bundle, ".001")),
        }
    profile = load_profile(ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
                           verify_resources=False)
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(raw), parse_game_policy(profile)
    )
    masks = provider.global_objects.classes
    if len(masks) < count:
        masks = (*masks, *((0,) * (count - len(masks))))
    return b"".join(int(masks[index]).to_bytes(4, "little") for index in range(count))


def _authored_global_table(name: str) -> bytes:
    """Return a complete source DOBJ table for a controlled startup root."""
    if not FATE_ARCHIVE.is_file():
        raise RuntimeError(f"missing supplied Fate archive: {FATE_ARCHIVE}")
    with zipfile.ZipFile(FATE_ARCHIVE) as bundle:
        raw = {
            "game.index": bundle.read(source_member(bundle, ".000")),
            "game.data": bundle.read(source_member(bundle, ".001")),
        }
    profile = load_profile(ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
                           verify_resources=False)
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(raw), parse_game_policy(profile)
    )
    value = getattr(provider.global_objects, name)
    if name == "classes":
        return b"".join(int(item).to_bytes(4, "little") for item in value)
    return bytes(value)


def fishnet_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...], tuple[bytes, ...]]:
    """Source-backed object-595 verb-11 scenario.

    Verb 11's authored basket branch is selected with object 591 as the
    sentence's second object.  The owner prerequisite is installed by the
    fixture's engine-owned object-state setup, never by the validator.
    """
    entry = bytes((0x00,))
    # The global prelude resolves both sentence objects before selecting the
    # room walk target.  Keep both complete source CDHD records in the cooked
    # room so whereIsObject/getDist and the object-walk table use authored
    # metadata for either operand.
    return entry, (), authored_room49_objects((591, 595))


def balloon_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...], tuple[bytes, ...]]:
    """Source-backed object-593 verb-8 two-object scenario."""
    # Preserve the source object ordering needed by CDHD parent references;
    # object 593's parent index is 3 in the real room.
    return bytes((0x00,)), (), authored_room49_objects((597, 593, 594, 595, 596, 592, 590, 591))


def salvage_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...], tuple[bytes, ...]]:
    """Source-backed room-49 salvage-boat verb scenario."""
    return bytes((0x00,)), (), authored_room49_objects((592,))


def startup42_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...], tuple[bytes, ...]]:
    """Controlled startup root: ENCD launches the real global script 1."""
    # Let the authored startup/title lifecycle establish room 75 first.  The
    # scenario driver later starts the source-authored game-selection call to
    # script 1 with its documented selector argument through the normal script
    # launcher, avoiding a synthetic room context for the title prelude.
    # Canonical no-argument startScript encoding is opcode, script number,
    # vararg terminator, then stop.  The extra zero previously inserted
    # before FF was decoded as a direct argument and made the fixture fail
    # before script 1 could begin.
    # The scenario root supplies the source-documented selector as an ordinary
    # startScript vararg.  This is a fixture boundary, not a PC/slot write;
    # script 1 still executes from PC zero and evaluates its own branch.
    return bytes.fromhex("0a 01 00 13 03 ff 00"), (), ()


GET_FACING_ANGLES = (0, 70, 71, 90, 109, 110, 180, 250, 251, 270, 289, 290, 359)


def getfacing_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    program = bytearray(set_word(0, 0x7777) + set_word(31, 0x5151))
    program.append(0x80)  # expose an emulator-visible pre-query actor snapshot
    for index, _angle in enumerate(GET_FACING_ANGLES):
        program.extend((0x63, index & 0xFF, index >> 8, index + 1))
    program.extend(set_word(30, len(GET_FACING_ANGLES)))
    program.extend((0xE3, 20, 0, 30, 0))
    program.extend((0x80, 0x00))
    return start_script(200) + bytes((0x00,)), ((200, bytes(program)),)


def getfacing_invalid_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("63 00 00 20")),)


def getfacing_malformed_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("e3 00 00 01")),)


def getwalkbox_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    program = bytearray()
    for actor in (1, 2, 3):
        program.extend((0x13, actor, 0x14, 0xFF))
    program.extend(set_word(0, 0x7777))
    program.extend(set_word(5, 0x5555))
    program.extend(set_word(9, 0x9999))
    program.extend(set_word(12, 0x1212))
    program.extend(set_word(30, 3))
    program.extend(set_word(31, 0x5151))
    program.append(0x80)  # stable pre-query snapshot
    program.extend(bytes.fromhex(
        "7b 00 00 01 "      # Var[0]  = actor 1 (stored box 0)
        "7b 05 00 02 "      # Var[5]  = actor 2 (stored box 2)
        "7b 09 00 03 "      # Var[9]  = actor 3 (stored box 3)
        "fb 0c 00 1e 00"    # Var[12] = actor Var[30]
    ))
    program.extend((0x80, 0x00))
    return start_script(200) + bytes((0x00,)), ((200, bytes(program)),)


def getwalkbox_invalid_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("7b 00 00 20")),)


def getwalkbox_malformed_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("fb 00 00 01")),)


def getdist_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    program = bytearray()
    # Ordinary opcode execution establishes actor records and current-room
    # ownership; generated initial positions remain copyright-free profile data.
    program.extend(bytes((0x2D, 1, 49, 0x2D, 2, 49)))
    for variable, value in ((20, 1), (21, 2), (22, 590), (23, 591)):
        program.extend(set_word(variable, value))
    for variable in range(8):
        program.extend(set_word(variable, 0x7000 + variable))
    program.append(0x80)  # stable pre-query actor/object snapshot
    program.extend(bytes.fromhex(
        "34 00 00 01 00 02 00 "      # direct actor -> actor
        "74 01 00 01 00 16 00 "      # direct actor -> variable object
        "b4 02 00 16 00 01 00 "      # variable object -> direct actor
        "f4 03 00 16 00 17 00 "      # variable object -> variable object
        "f4 04 00 14 00 16 00 "      # variable actor -> variable object
        "f4 05 00 16 00 14 00 "      # reversed asymmetric order
        "34 06 00 63 00 01 00 "      # unresolved first
        "34 07 00 01 00 63 00"       # unresolved second
    ))
    program.extend((0x80, 0x00))
    return start_script(200) + bytes((0x00,)), ((200, bytes(program)),)


def getdist_malformed_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(200) + bytes((0x00,)), ((200, bytes.fromhex("f4 00 00 14 00")),)


def message_scripts(*, long_message: bool = False) -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    """Single-owner talk/wait fixture for target logical-lifetime proof.

    Keeping the waiter in the same authored script makes this regression
    about C23 message lifetime rather than nested-slot scheduling.  Nested
    wait ownership is covered separately by the focused SCUMM suite.
    """
    text = (b"A" * 36) + bytes((0xFF, 0x03)) + (b"B" * 12) if long_message else b"A"
    program = b"".join((
        bytes((0x13, 1, 0x14, 0xFF)),  # initialize actor 1 canonical defaults
        bytes((0x14, 1, 0x0F)) + text + bytes((0,)),
        bytes((0xAE, 0x02)),
        set_word(10, 1),
        bytes((0x00,)),
    ))
    return start_script(200) + bytes((0x00,)), ((200, program),)


def message_malformed_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    """Truncated SO_TEXTSTRING: no terminator exists inside the descriptor."""
    parent = bytes((0x13, 1, 0x14, 0xFF, 0x14, 1, 0x0F, ord("X")))
    return start_script(200) + bytes((0x00,)), ((200, parent),)


def lookup_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    """Complete sparse local directory; no LSCR runs before explicit starts."""
    entry = b"".join((
        bytes((0x80,)),
        start_script(10), start_script(200), start_script(201),
        start_script(202), start_script(208),
        bytes((0x80, 0x00)),
    ))
    locals_ = tuple(
        (number, set_word(variable, value) + bytes((0x00,)))
        for number, variable, value in (
            (200, 20, 0x0200), (201, 21, 0x0201),
            (202, 22, 0x0202), (208, 28, 0x0208),
        )
    )
    return entry, locals_


def lookup_missing_scripts() -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return start_script(203) + bytes((0x00,)), ((202, bytes((0x00,))),)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=(
        "normal", "depth", "missing", "outer", "putactor", "putactor-invalid",
        "putactor-malformed",
        "setstate", "setstate-invalid", "setstate-malformed",
        "getfacing", "getfacing-invalid", "getfacing-malformed",
        "getwalkbox", "getwalkbox-invalid", "getwalkbox-malformed",
        "getdist", "getdist-malformed",
        "message", "message-long", "message-malformed",
        "lookup", "lookup-missing",
        "startobject", "crate", "fishnet", "balloon", "salvage", "startup42", "room55", "room55-accessor", "room55-movement",
        "scheduler",
    ), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Persist corpus selection before authored resource resolution so a
    # deliberate negative-corpus failure remains diagnosable.
    (args.output_dir / "corpus_identity.json").write_text(
        json.dumps(selected_corpus_identity(FATE_ARCHIVE), indent=2, sort_keys=True) + "\n"
    )
    profile = load_profile(PROFILE, verify_resources=False)
    profile_hash = sha(PROFILE.read_bytes())
    game_hash = sha(f"{profile.engine_id}\0{profile.game_id}\0{profile.variant}".encode())
    corpus = selected_corpus_identity(FATE_ARCHIVE)
    source = {name: sha(f"M25A {args.case} copyright-free {name}".encode())
              for name in ("archive", "index", "data")}
    builders = {
        "normal": normal_scripts,
        "depth": depth_scripts,
        "missing": missing_scripts,
        "outer": outer_scripts,
        "scheduler": scheduler_scripts,
        "putactor": putactor_scripts,
        "putactor-invalid": putactor_invalid_scripts,
        "putactor-malformed": putactor_malformed_scripts,
        "setstate": setstate_scripts,
        "setstate-invalid": setstate_invalid_scripts,
        "setstate-malformed": setstate_malformed_scripts,
        "crate": crate_scripts,
        "fishnet": fishnet_scripts,
        "balloon": balloon_scripts,
        "salvage": salvage_scripts,
        "startup42": startup42_scripts,
        "room55": startup42_scripts,
        "room55-accessor": room55_accessor_scripts,
        "room55-movement": room55_movement_scripts,
        "getfacing": getfacing_scripts,
        "getfacing-invalid": getfacing_invalid_scripts,
        "getfacing-malformed": getfacing_malformed_scripts,
        "getwalkbox": getwalkbox_scripts,
        "getwalkbox-invalid": getwalkbox_invalid_scripts,
        "getwalkbox-malformed": getwalkbox_malformed_scripts,
        "getdist": getdist_scripts,
        "getdist-malformed": getdist_malformed_scripts,
        "message": message_scripts,
        "message-long": lambda: message_scripts(long_message=True),
        "message-malformed": message_malformed_scripts,
        "lookup": lookup_scripts,
        "lookup-missing": lookup_missing_scripts,
    }
    object_payloads: tuple[bytes, ...] = ()
    if args.case == "startobject":
        entry, locals_, object_payloads = startobject_scripts()
    elif args.case in {"crate", "fishnet", "balloon", "salvage", "startup42"}:
        entry, locals_, object_payloads = builders[args.case]()
    elif args.case == "room55":
        entry, locals_, object_payloads = builders[args.case]()
    elif args.case in {"room55-accessor", "room55-movement"}:
        entry, locals_ = builders[args.case]()
    elif args.case == "message-long":
        entry, locals_ = builders[args.case]()
    else:
        entry, locals_ = builders[args.case]()
    payload = room(
        entry, locals_, objects=(args.case.startswith("setstate") or args.case == "getdist"),
        object_payloads=object_payloads,
        walkbox_count=64 if args.case in {"room55-accessor", "room55-movement"} else (12 if args.case in {"crate", "fishnet", "balloon", "salvage", "startup42"} else (4 if args.case == "getwalkbox" else 2)),
        overlap_walkboxes=args.case == "room55-movement",
    )
    encoded = encode_cooked_room(
        payload, room=49, flags=0, original_room_file_offset=0x250000,
        profile_sha256=profile_hash, game_identity_sha256=game_hash,
        archive_sha256=source["archive"], index_sha256=source["index"],
        data_sha256=source["data"], scripts=descriptors(payload),
    )
    decoded = decode_cooked_room(encoded, expected_room=49)
    room_output = args.output_dir / "room-49.sc5c"
    room_output.write_bytes(encoded)
    global_scripts = []
    if args.case in {"crate", "fishnet", "balloon", "salvage", "startup42", "room55", "room55-movement"}:
        # The production sentence boundary launches VAR_SENTENCE_SCRIPT (2).
        # Keep that launcher as an ordinary generated global resource: the
        # fixture must exercise the same $37/object-program allocation path as
        # the game, while the validator supplies only the sentence mailbox.
        # Keep the launcher generic over the sentence verb: $77 is
        # startObject with a direct object and a variable entry selector;
        # local 0 is populated by the production C20 sentence launcher.
        object_id = 594 if args.case == "crate" else (595 if args.case == "fishnet" else (593 if args.case == "balloon" else 592))
        global_program = (
            # The full Fate sentence dispatcher has many unrelated branches
            # whose readiness state is not part of this focused object
            # scenario.  This is the exact source v5 startObject form used by
            # its successful sentence path: object=local1, entry=local0,
            # arguments local2 and local0.  The OBCD and all arguments remain
            # source-backed; only the reusable fixture launcher is narrowed.
            bytes.fromhex("f7 01 40 00 40 81 02 40 81 00 40 ff 00")
            if args.case in {"balloon", "salvage"} else (
            _authored_global_script(2)
            if args.case in {"fishnet", "startup42", "room55", "room55-movement"}
            else bytes((
                0x77, object_id & 0xFF, object_id >> 8, 0x0F, 0x00, 0xFF,
                0x00,
            )))
        )
        global_output = args.output_dir / "script-2.scrp"
        global_output.write_bytes(global_program)
        global_scripts.append({
            "number": 2, "resource_key": "script.2",
            "output": global_output.name, "length": len(global_program),
            "sha256": sha(global_program),
        })
        if args.case in {"fishnet", "balloon", "salvage"}:
            # The authored verb-11 basket branch starts the real global
            # script 10 after mutating object 595. Keep that dependency
            # source-bound as well; it is not a fixture replacement.
            profile = load_profile(ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json",
                                   verify_resources=False)
            with zipfile.ZipFile(FATE_ARCHIVE) as bundle:
                raw = {"game.index": bundle.read(source_member(bundle, ".000")),
                       "game.data": bundle.read(source_member(bundle, ".001"))}
            provider = LucasartsScummV5ResourceProvider(
                MemoryResourceProvider(raw), parse_game_policy(profile))
            script10 = provider.read("script.10")
            script10_output = args.output_dir / "script-10.scrp"
            script10_output.write_bytes(script10)
            global_scripts.append({
                "number": 10, "resource_key": "script.10",
                "output": script10_output.name, "length": len(script10),
                "sha256": sha(script10), "source": "PLAYFATE script 10",
            })
    if args.case in {"startup42", "room55", "room55-movement"}:
            # The root is deliberately a real startScript(1) from ENCD.  The
            # startup closure is source-backed; no script PC or slot is set by
            # the fixture.  Keep the bounded executable closure that reaches
            # the selected game-state branch; optional DSCR entries remain
            # available to the raw host but are not needlessly assigned target
            # program IDs in this fixture's finite executable namespace.
            # Room 82's authored drowning/hoist continuation chains into
            # global script 57.  Keep that real downstream edge in the
            # startup cone; script 57 in turn starts the source global 145.
            # Room 42 ENCD's first authored startScript is global 144.  Keep
            # it in the bounded startup closure; omitting it leaves the real
            # ENCD parked immediately after its launch opcode even though the
            # room resource itself validated successfully.
            for number in (1, 13, 14, 18, 20, 57, 74, 75, 132, 144, 145):
                program = _authored_global_script(number)
                script_output = args.output_dir / f"script-{number}.scrp"
                script_output.write_bytes(program)
                global_scripts.append({
                    "number": number, "resource_key": f"script.{number}",
                    "output": script_output.name, "length": len(program),
                    "sha256": sha(program), "source": f"PLAYFATE script {number}",
                    **({"append_after_rooms": True} if number in (57, 145) else {}),
                })
    elif args.case == "lookup":
        global_program = set_word(10, 0x0010) + bytes((0x00,))
        global_output = args.output_dir / "script-10.scrp"
        global_output.write_bytes(global_program)
        global_scripts.append({
            "number": 10, "resource_key": "script.10",
            "output": global_output.name, "length": len(global_program),
            "sha256": sha(global_program),
        })
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "num_global_scripts": 200,
        "profile": {"path": str(PROFILE), "sha256": profile_hash,
                    "engine": profile.engine_id, "game": profile.game_id,
                    "variant": profile.variant, "identity_sha256": game_hash},
        "source": {f"{name}_sha256": value for name, value in source.items()},
        "selected_corpus": corpus,
        "copyright": "generated copyright-free M25A nested-script fixture",
        "case": args.case,
        "actor_facings": [
            180, *GET_FACING_ANGLES,
            *([180] * (31 - len(GET_FACING_ANGLES))),
        ] if args.case == "getfacing" else [180] * 32,
        # Actor 3's point lies inside box 1 while its stored canonical field is
        # box 3. The query must return 3 without consulting geometry.
        "actor_positions": (
            [[0, 0], [0, 0], [12, 0], [4, 1]] + [[0, 0]] * 28
            if args.case == "getwalkbox" else [[0, 0]] * 32
        ),
        "actor_walkboxes": (
            [0, 0, 2, 3] + [0] * 28
            if args.case == "getwalkbox" else [0] * 32
        ),
        "records": [{
            "room": 49, "resource_key": "room.49", "output": room_output.name,
            "registration_only": False, "record_length": len(encoded),
            "record_sha256": sha(encoded), "compact_checksum": decoded.compact_checksum,
            "scripts": [{
                "identity": item.identity, "kind": item.kind, "number": item.number,
                "program_length": len(item.program), "sha256": item.sha256,
                **item.runtime_map(0),
            } for item in decoded.scripts],
        }],
        "global_scripts": global_scripts,
    }
    if args.case == "getdist":
        manifest["actor_positions"] = [[0, 0], [7, 1], [2, 1]] + [[0, 0]] * 29
        count = 600
        states = bytes(count)
        owners = bytearray(count)
        owners[590] = owners[591] = 15
        states_output = args.output_dir / "object-states.bin"
        owners_output = args.output_dir / "object-owners.bin"
        classes_output = args.output_dir / "object-classes.bin"
        states_output.write_bytes(states)
        owners_output.write_bytes(owners)
        classes_output.write_bytes(
            _authored_global_classes(count) if args.case == "fishnet" else bytes(count * 4)
        )
        manifest["global_objects"] = {
            "count": count,
            "states_output": states_output.name,
            "owners_output": owners_output.name,
            "classes_output": classes_output.name,
        }
    if args.case in {"crate", "fishnet", "balloon", "salvage", "startup42", "room55", "room55-movement"}:
        # The source DOBJ table has 1395 entries.  Script 10 reaches objects
        # above the compact 1024-entry fixture bound, so retain the complete
        # source-defined global object namespace for this scenario.
        count = 1395
        states = (_authored_global_table("states") if args.case in {"startup42", "room55", "room55-movement"}
                  else bytes(count))
        owners = (bytearray(_authored_global_table("owners"))
                  if args.case in {"startup42", "room55", "room55-movement"} else bytearray(count))
        if args.case == "fishnet":
            # The authored sentence combines held fishnet 595 with room
            # basket 591.  Script 2 therefore selects 591 as the walk target;
            # both values use the normal SCUMM owner encoding.
            owners[595] = 1
            owners[591] = 15
        elif args.case == "balloon":
            # The authored verb-8 handler requires companion object 1014 in
            # ego inventory. This is installed by the fixture's normal
            # engine-owned object tables, not by interpreter slot writes.
            owners[593] = 15
            owners[1014] = 1
        elif args.case == "salvage":
            owners[592] = 15
        states_output = args.output_dir / "object-states.bin"
        owners_output = args.output_dir / "object-owners.bin"
        classes_output = args.output_dir / "object-classes.bin"
        states_output.write_bytes(states)
        owners_output.write_bytes(owners)
        classes_output.write_bytes(
            _authored_global_classes(count) if args.case not in {"startup42", "room55"}
            else _authored_global_table("classes")
        )
        manifest["global_objects"] = {
            "count": count,
            "states_output": states_output.name,
            "owners_output": owners_output.name,
            "classes_output": classes_output.name,
        }
        if args.case in {"startup42", "room55"}:
            # Room-42 ENCD consumes source DOBJ state 488 before the first
            # semantic sentence boundary; preserve the complete source table
            # for this explicit source-root scenario only.
            manifest["source_initial_states"] = True
    path = args.output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": args.case, "manifest": str(path),
                      "record_sha256": manifest["records"][0]["record_sha256"],
                      "locals": len(locals_)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
