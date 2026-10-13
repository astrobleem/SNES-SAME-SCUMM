#!/usr/bin/env python3
"""Build a copyright-free four-room corpus for native selector residency."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from same.engines.scumm_v5.room_compiler import compile_room_payload, decode_script
from same.engines.scumm_v5.room_visual import encode_room_visual


GLOBAL_COUNT = 254
SOURCE_GLOBALS = 193
ROOM_COUNT = 4
GLOBAL_OBJECT_COUNT = 256


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack(">I", len(payload) + 8) + payload


def object_chunks(object_id: int = 70, *, passive_count: int = 1,
                  named: bool = False,
                  name_padding_bytes: int = 0,
                  marker_vars: tuple[int, int] = (9, 10)) -> tuple[bytes, ...]:
    """One two-verb carrier plus passive records, optionally named."""
    def cdhd(object_id: int) -> bytes:
        return chunk(b"CDHD", struct.pack(
            "<HBBBBBBhhB", object_id, 1, 1, 1, 1, 0, 0, 1, 1, 0,
        ))

    # The source entry offsets are OBCD-relative. Both verb bodies write an
    # observable marker before stopping, proving dispatch through one shared
    # object carrier rather than merely counting the metadata record.
    first_marker, second_marker = marker_vars
    verbs = bytes((
        3, 15, 0, 10, 21, 0, 0,
        0x1A, first_marker & 0xFF, first_marker >> 8, 3, 0, 0xA0,
        0x1A, second_marker & 0xFF, second_marker >> 8, 10, 0, 0xA0,
    ))
    carrier_children = cdhd(object_id) + chunk(b"VERB", verbs)
    names = []
    if named:
        names.append((object_id, f"Fixture carrier {object_id:03d}".encode()))
        names.extend(
            (passive_id, f"Fixture object {passive_id:03d}".encode())
            for passive_id in range(object_id + 1, object_id + passive_count)
        )
        remaining_padding = name_padding_bytes
        padded_names = []
        for name_id, name in names:
            padding = min(remaining_padding, 32 - len(name))
            padded_names.append((name_id, name + b"x" * padding))
            remaining_padding -= padding
        if remaining_padding:
            raise ValueError("requested object-name padding exceeds the 32-byte row limits")
        names = padded_names
        carrier_children += chunk(b"OBNA", names[0][1])
    records = [chunk(b"OBCD", carrier_children)]
    for passive_id in range(object_id + 1, object_id + passive_count):
        children = cdhd(passive_id)
        if named:
            children += chunk(b"OBNA", dict(names)[passive_id])
        records.append(chunk(b"OBCD", children))
    return tuple(records)


def raw_room(room: int, *, load_room_with_ego: bool = False,
             draw_box: bool = False,
             room_resource_failure: bool = False,
             large_live_room: bool = False,
             large_live_room_name_padding_bytes: int = 0) -> bytes:
    palette = bytes(value for index in range(256) for value in (index, index, index))
    smap = chunk(b"SMAP", struct.pack("<I", 12) + bytes((1,)) + bytes(range(16)))
    rmim = chunk(b"RMIM", chunk(b"RMIH", b"\0\0") + chunk(b"IM00", smap))
    large = room == 1 and large_live_room
    if large:
        # Keep within the native engine's 64-box limit. Two groups of
        # coincident copyright-free boxes produce a dense, deduplicated portal
        # directory; the 64x64 route matrix and names push the normalized
        # semantic record past 19 KiB while sectioned storage remains bounded.
        walkboxes = []
        for index in range(64):
            left = 0 if index < 56 else 4
            top, right, bottom = 0, left + 1, 1
            walkboxes.append(struct.pack(
                "<hhhhhhhhBBH", left, top, right, top, right, bottom,
                left, bottom, 0, 0, 255,
            ))
        walkbox_payload = struct.pack("<H", len(walkboxes)) + b"".join(walkboxes)
        boxm_payload = (b"\x01\x01\x01\xff\x00\x00\x00\xff"
                        + b"\xff" * 62)
    else:
        walkbox_payload = struct.pack("<H", 1) + struct.pack(
            "<hhhhhhhhBBH", 0, 0, 255, 0, 255, 127, 0, 127, 0, 0, 255,
        )
        boxm_payload = b"\xff"
    if room == 1 and large_live_room:
        # Diagnostic route: consume the large room, execute each shared-carrier
        # verb in its own activation turn, visit room 2, then revisit room 1.
        # The second entry stops without another transition, leaving a stable
        # native state for metadata/visual checks.
        # Revisit guard: only the second entry stops.
        # SCUMM v5's 0x28 compare-zero form branches when the variable is
        # nonzero.  The inverse 0xA8 form would branch on the initial zero
        # value and skip the first-visit body entirely.
        entry_bytes = bytearray((0x28, 200, 0, 0, 0))
        entry_bytes.extend((
            0x1A, 200, 0, 1, 0,  # revisit guard
            0x1A, 201, 0, 1, 0,  # first-visit marker
            0x37, 70, 0, 3, 0xFF,
            0x80,                # breakHere lets verb 3 finish before same-object replacement
            0x37, 70, 0, 10, 0xFF,
            0x72, 2, 0xA0,
        ))
        stop_offset = len(entry_bytes)
        struct.pack_into("<h", entry_bytes, 3, stop_offset - 5)
        entry_bytes.append(0xA0)
        entry = bytes(entry_bytes)
    elif room == 2 and large_live_room:
        entry = bytes((
            0x1A, 204, 0, 2, 0,
            0x72, 1, 0xA0,
        ))
    elif room == 1 and load_room_with_ego:
        entry = bytes((
            0x9A, 100, 0, 38, 0,  # Capture VAR_WALKTO_OBJ before entry yield.
            0x80,
            0x9A, 101, 0, 38, 0,  # It must be cleared before ENCD resumes.
            0x00,
        ))
    elif room == 2 and load_room_with_ego:
        entry = bytes((
            0x9A, 103, 0, 38, 0,  # Capture the second entry-object value.
            0x80,
            0x9A, 105, 0, 38, 0,  # The postamble must clear it before resume.
            0x00,
        ))
    elif room == 1 and draw_box:
        entry = bytes((
            0x1A, 30, 0, 15, 0,  # variable rectangle x0
            0x1A, 31, 0, 25, 0,  # variable rectangle y0
            0x1A, 32, 0, 13, 0,  # reversed variable x1
            0x1A, 33, 0, 23, 0,  # reversed variable y1
            0x1A, 34, 0, 202, 0, # variable color
            0x3F, 10, 0, 20, 0, 0x00, 12, 0, 21, 0, 201,
            # Variable x0/y0 and variable byte color with direct x1/y1.
            # Auxiliary bit $20 alone selects the color VOB.
            0xFF, 30, 0, 31, 0, 0x20, 13, 0, 23, 0, 34, 0,
            0x3F, 250, 0, 50, 0, 0x00, 44, 1, 52, 0, 203,
            0x1A, 60, 0, 1, 0,
            0x80, 0x00,
        ))
    elif room == 1:
        entry = bytes((
            0x1A, 24, 0, 1, 0,
            0x37, 70, 0, 3, 0xFF,   # StartObject(70, verb=3)
            0x37, 70, 0, 10, 0xFF,  # same object carrier, verb=10
            0x72, 2, 0xA0,
        ))
    elif room < ROOM_COUNT:
        entry = bytes((0x1A, 24, 0, room, 0, 0x72, room + 1, 0xA0))
    else:
        # Start the local executable from the room entry. The local records
        # its own marker, then starts the pressure/churn global caller. Its
        # initial yield window lets the persistent global retire before the
        # pool needs to recycle its first selector.
        entry = bytes((0x1A, 24, 0, room, 0, 0x0A, GLOBAL_COUNT,
                       0xFF, 0xA0))
    if large:
        objects = object_chunks(70, passive_count=36, named=True,
                                name_padding_bytes=large_live_room_name_padding_bytes,
                                marker_vars=(202, 203))
    elif load_room_with_ego and room in (1, 2):
        objects = object_chunks(70 if room == 1 else 72)
    else:
        objects = object_chunks() if room == 1 else ()
    exit_code = (
        bytes((0x1A, 104, 0, 1, 0, 0xA0))
        if load_room_with_ego and room == 1 else b"\xA0"
    )
    return b"".join((
        chunk(b"RMHD", struct.pack("<HHH", 8, 2, len(objects))),
        chunk(b"CLUT", palette), rmim,
        chunk(b"BOXD", walkbox_payload),
        chunk(b"BOXM", boxm_payload), *objects,
        chunk(b"ENCD", entry), chunk(b"EXCD", exit_code),
        chunk(b"LSCR", (
            bytes((GLOBAL_COUNT, 0x1A, 25, 0, 1, 0, 0x0A, 4, 0xFF, 0xA0))
            if room == ROOM_COUNT and not (
                load_room_with_ego or draw_box
            ) else bytes((GLOBAL_COUNT, 0xA0))
        )),
    ))


def large_program_body() -> bytes:
    """Build a >21 KiB valid body with a yield and cross-page branches."""
    code = bytearray((0x80,))  # retain the caller while this child yields

    def set_var(number: int, value: int) -> None:
        code.extend((0x1A, number & 0xFF, number >> 8,
                     value & 0xFF, value >> 8))

    def inc_var(number: int) -> None:
        code.extend((0x46, number & 0xFF, number >> 8))

    def inc_many(number: int, count: int) -> None:
        for index in range(count):
            inc_var(number)
            if (index + 1) % 8 == 0 and index + 1 < count:
                code.append(0x80)  # bounded yield keeps host/native ticks fair

    def comparison_branch(opcode: int, number: int, value: int, target: int) -> None:
        code.extend((opcode, number & 0xFF, number >> 8,
                     value & 0xFF, value >> 8, 0, 0))
        struct.pack_into("<h", code, len(code) - 2, target - len(code))

    # The generic v5 comparison handler takes the relative branch when its
    # comparison is false.  With direct rhs=1, lhs=0 makes the first branch
    # skip the large region; the later set to 1 is the observable marker.
    set_var(50, 0)
    set_var(51, 0)
    # Taken branch skips a distinct 6 KiB region and lands beyond three
    # validated 2 KiB cache pages. The skipped counter remains zero.
    branch_start = len(code)
    code.extend((0x38, 50, 0, 1, 0, 0, 0))
    forward_target = 0x1801
    while (forward_target - len(code)) % 3:
        forward_target += 1
    while len(code) + 3 <= forward_target:
        inc_var(51)
    if len(code) != forward_target:
        raise AssertionError("large-body forward branch target is misaligned")
    struct.pack_into("<h", code, branch_start + 5,
                     forward_target - (branch_start + 7))
    set_var(50, 1)
    while len(code) + 3 <= 15000:
        inc_many(52, min(128, (15000 - len(code)) // 3))
    if len(code) < 14000:
        raise AssertionError("large-body loop entry did not cross page boundary")

    set_var(54, 0)
    loop_start = len(code)
    inc_var(54)
    inc_many(53, 2000)
    comparison_branch(0x48, 54, 2, loop_start)
    set_var(6, 2)
    code.append(0xA0)
    if not 21002 < len(code) <= 0xFFFF:
        raise AssertionError(f"large ProgramUnit length is outside target: {len(code)}")
    return bytes(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--load-room-with-ego", action="store_true",
        help="generate a compact native loadRoomWithEgo conformance route",
    )
    parser.add_argument(
        "--find-inventory", action="store_true",
        help="generate a native ordered findInventory conformance program",
    )
    parser.add_argument(
        "--draw-box", action="store_true",
        help="generate a native indexed-surface drawBox conformance program",
    )
    parser.add_argument(
        "--live-room-resources", action="store_true",
        help="attach distinct copyright-free indexed visuals to every room for MSU-backed loading",
    )
    parser.add_argument(
        "--large-live-room", action="store_true",
        help="make room 1 a large live-room stress record; requires --live-room-resources",
    )
    parser.add_argument(
        "--large-live-room-name-padding-bytes", type=int, default=0,
        help="append bounded bytes to generated object names for exact native record-size tests",
    )
    parser.add_argument(
        "--large-program-body", action="store_true",
        help="make GlobalProgram(2) a >21 KiB yielding branch/page conformance body",
    )
    parser.add_argument(
        "--room-resource-failure", action="store_true",
        help="generate a copyright-free boot-global room1->room2 CRC-failure route",
    )
    args = parser.parse_args()
    if sum((args.load_room_with_ego, args.find_inventory, args.draw_box,
            args.room_resource_failure)) > 1:
        parser.error("choose only one focused conformance program")
    if args.large_program_body and any((args.load_room_with_ego, args.find_inventory,
                                        args.draw_box, args.room_resource_failure)):
        parser.error("--large-program-body is for the default dynamic route fixture")
    if args.large_live_room and not args.live_room_resources:
        parser.error("--large-live-room requires --live-room-resources")
    if args.large_live_room and any((args.load_room_with_ego, args.find_inventory,
                                     args.draw_box, args.room_resource_failure)):
        parser.error("--large-live-room is for the default live-room route fixture")
    if args.large_live_room_name_padding_bytes and not args.large_live_room:
        parser.error("--large-live-room-name-padding-bytes requires --large-live-room")
    if not 0 <= args.large_live_room_name_padding_bytes <= 512:
        parser.error("--large-live-room-name-padding-bytes must be in 0..512")
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ids = {
        "profile": sha(b"synthetic-resident-profile-v1"),
        "game": sha(b"synthetic-resident-game-v1"),
        "archive": sha(b"synthetic-resident-archive-v1"),
        "index": sha(b"synthetic-resident-index-v1"),
        "data": sha(b"synthetic-resident-data-v1"),
    }
    records = []
    for room in range(1, ROOM_COUNT + 1):
        payload = raw_room(
            room, load_room_with_ego=(args.load_room_with_ego
                                      or args.room_resource_failure),
            draw_box=args.draw_box,
            room_resource_failure=args.room_resource_failure,
            large_live_room=args.large_live_room,
            large_live_room_name_padding_bytes=args.large_live_room_name_padding_bytes,
        )
        compiled = compile_room_payload(
            payload, room_number=room,
            game_name="copyright-free-native-residency-fixture",
            resource_key=f"room.{room}", source_member=f"fixture/room-{room}.lflf",
            source_container_offset=0, original_room_file_offset=room * 0x10000,
            profile_sha256=ids["profile"], game_identity_sha256=ids["game"],
            archive_sha256=ids["archive"], index_sha256=ids["index"],
            data_sha256=ids["data"], global_script_count=GLOBAL_COUNT,
        )
        name = f"room-{room}.sc5c"
        (out / name).write_bytes(compiled.cooked_record)
        record = {**compiled.record_manifest, "output": name}
        if (room == 1 and args.draw_box) or args.live_room_resources:
            visual_name = "room-1.sc5v"
            if args.live_room_resources:
                visual_name = f"room-{room}.sc5v"
            visual_palette = bytes(
                value for index in range(256) for value in (
                    (index + room * 17) & 0xFF,
                    (index * 3 + room * 29) & 0xFF,
                    (index // 2 + room * 41) & 0xFF,
                )
            )
            visual_pixels = bytes(
                (x + 3 * y + 37 * room) & 0xFF
                for y in range(224) for x in range(256)
            )
            visual_payload = encode_room_visual(
                room=room if args.live_room_resources else 1,
                width=256, height=224, pitch=256,
                palette=visual_palette, pixels=visual_pixels,
                archive_sha256=ids["archive"], index_sha256=ids["index"],
                data_sha256=ids["data"], room_sha256=sha(payload),
            )
            (out / visual_name).write_bytes(visual_payload)
            record["visual"] = {
                "output": visual_name,
                "record_sha256": sha(visual_payload),
            }
        records.append(record)

    # Keep the room-transition route bounded while exercising dynamic global
    # resolution. A separate candidate-probe global selects two distant
    # members from the >178-global universe; no candidate universe is eagerly
    # bound merely because it exists.
    if args.load_room_with_ego or args.room_resource_failure:
        global_one_code = bytearray((
            0x1A, 1, 0, 1, 0,            # VAR_EGO = actor 1
            0x1A, 40, 0, 99, 0,          # decoys: first transition is direct
            0x1A, 41, 0, 99, 0,
            0x1A, 101, 0, 0x34, 0x12,    # ENCD must overwrite this after yield
            # First room entry has no optional walk, then the live caller
            # issues a second LoadRoomWithEgo transition from room 1 to room
            # 2. Room 1 EXCD must run, the room-1 bundle must retire, and the
            # same global activation must remain valid while room 2 ENCD
            # yields. In the failure variant the incoming SC5LIVE bytes can
            # be corrupted before publication without changing this route.
            0x24, 70, 0, 1, 0xFF, 0xFF, 0, 0,
            0x80,                         # let room-1 ENCD resume its postamble
            0x1A, 40, 0, 72, 0,
            0x1A, 41, 0, 2, 0,
            0x1A, 105, 0, 0x78, 0x56,
            0xE4, 40, 0, 41, 0, 6, 0, 7, 0,
            0xA0,
        ))
    elif args.draw_box:
        # Enter the fixture's authored visual room through the ordinary
        # SCUMM room-transition path, then let room 1 ENCD draw the boxes.
        global_one_code = bytearray((0x72, 1, 0xA0))
    elif args.find_inventory:
        global_one_code = bytearray()

        def set_var(number: int, value: int) -> None:
            global_one_code.extend((0x1A, number & 0xFF, number >> 8,
                                    value & 0xFF, value >> 8))

        def set_owner(object_id: int, owner: int) -> None:
            global_one_code.extend((0x29, object_id & 0xFF,
                                    object_id >> 8, owner))

        def find_direct(result: int, owner: int, ordinal: int) -> None:
            global_one_code.extend((0x3D, result & 0xFF, result >> 8,
                                    owner, ordinal))

        set_var(10, 2)
        set_var(11, 1)
        set_var(12, 0)
        for object_id in (70, 72, 75):
            set_owner(object_id, 2)
        find_direct(50, 2, 0)
        find_direct(51, 2, 1)
        find_direct(52, 2, 3)
        find_direct(53, 3, 0)
        global_one_code.extend((
            0x7D, 54, 0, 2, 11, 0,  # direct owner, variable ordinal
            0xBD, 55, 0, 10, 0, 2,  # variable owner, direct ordinal
        ))
        set_owner(72, 3)
        set_var(10, 3)
        find_direct(56, 2, 1)
        find_direct(57, 3, 0)
        global_one_code.extend((
            0xFD, 58, 0, 10, 0, 12, 0,  # variable owner and ordinal
            0xA0,
        ))
    else:
        global_one_code = bytearray((0x80,))  # retain a live caller activation
        for target in (2, 3):
            global_one_code.extend((
                0x1A, 7, 0, target, 0,      # variable 7 = selected script
                0x8A, 7, 0, 0xFF,            # dynamic StartScript(variable[7])
                0x80,                         # caller yields to the child
            ))
        # The profile's ordinary title START input enters room 1. Keep this
        # global yielded over the room-entry chain so its selector pin is
        # tested without making the same activation the transition requester.
        global_one_code.extend((0x80,) * 40)
        global_one_code.extend((
            0x1A, 5, 0, 1, 0,
            0x1A, 15, 0, 1, 0,
            0xA0,
        ))
    global_one = bytes(global_one_code)
    global_two = (
        large_program_body() if args.large_program_body else bytes((
            0x80,
            0x1A, 6, 0, 2, 0,       # marker: yielded child resumed and completed
            0xA0,
        ))
    )
    global_three = bytes((
        0x1A, 8, 0, 3, 0,       # marker: second dynamic target executed
        0xA0,
    ))
    global_four_code = bytearray()
    # Allow GlobalScript(1), which has yielded across the room chain, to
    # finish before selector pressure reaches its first evictable binding.
    global_four_code.extend((0x80,) * 40)
    # Exercise actual reuse instead of assuming the allocator should evict a
    # still-useful binding while free selectors remain. A compact SCUMM loop
    # serializes the same 5..190 targets through one caller, keeping live
    # activations bounded while the candidate universe exceeds the selector
    # pool. This prevents test-body size from dominating storage latency.
    global_four_code.extend((0x1A, 7, 0, 5, 0))
    global_loop_start = len(global_four_code)
    global_four_code.extend((
        0x8A, 7, 0, 0xFF,             # StartScript(variable[7])
        0x80,                         # wait for the child to stop
        0x46, 7, 0,                   # increment candidate
        0x38, 7, 0, 191, 0, 0, 0,    # if var[7] >= 191, exit loop
    ))
    global_loop_branch = len(global_four_code) - 2
    struct.pack_into(
        "<h", global_four_code, global_loop_branch,
        global_loop_start - len(global_four_code),
    )
    global_four_code.extend((
        0x1A, 7, 0, 191, 0,
        0x8A, 7, 0, 0xFF,
        0x80,
        0x1A, 7, 0, 192, 0,
        0x8A, 7, 0, 0xFF,
        0x80,
        0x1A, 20, 0, 4, 0,
        0xA0,
    ))
    global_four = bytes(global_four_code)
    global_191 = bytes((0x1A, 21, 0, 5, 0, 0xA0))
    global_192 = bytes((0x1A, 22, 0, 6, 0, 0xA0))
    global_193 = bytes((
        0x1A, 7, 0, 191, 0, 0x8A, 7, 0, 0xFF, 0x80,
        0x1A, 7, 0, 192, 0, 0x8A, 7, 0, 0xFF, 0x80,
        0x1A, 23, 0, 7, 0, 0xA0,
    ))
    globals_ = [(1, global_one), (2, global_two), (3, global_three), (4, global_four),
                (191, global_191), (192, global_192), (193, global_193)] + [
        (number, bytes((0xA0,))) for number in range(5, 191)
    ]
    for number, program in globals_:
        (out / f"global-{number}.bin").write_bytes(program)
    # Keep the generated SCUMM object domain truthful for this fixture.  The
    # backend otherwise uses its conservative 4096-object fallback, which is
    # larger than the legacy dense owner-table allocation in the native
    # fixture profile and would make an out-of-range inventory ordinal read
    # unrelated WRAM bytes.
    (out / "object-states.bin").write_bytes(bytes(GLOBAL_OBJECT_COUNT))
    (out / "object-owners.bin").write_bytes(bytes(GLOBAL_OBJECT_COUNT))
    manifest = {
        "schema": "same_scumm_v5_cooked_rooms_v1",
        "num_global_scripts": GLOBAL_COUNT,
        "global_objects": {
            "count": GLOBAL_OBJECT_COUNT,
            "states_output": "object-states.bin",
            "owners_output": "object-owners.bin",
        },
        "copyright": "Copyright-free generated structural/runtime fixture.",
        "conformance_case": (
            "load-room-with-ego" if args.load_room_with_ego else
            "find-inventory" if args.find_inventory else
            "draw-box" if args.draw_box else
            "room-resource-failure" if args.room_resource_failure else
            "large-program-body" if args.large_program_body else "resident-binding"
        ),
        "large_program_body": ({
            "identity": "GlobalProgram(2)",
            "length": len(global_two),
            "branch_targets": [
                int(item.branch_target) for item in decode_script(
                    global_two, identity="GlobalProgram(2)", kind="global",
                    number=2, room=0, resource_key="global.2",
                    game_name="copyright-free-native-residency-fixture",
                    source_member="fixture/global-2.bin", resource_offset=0,
                    source_offset=0,
                ).instructions if item.branch_target is not None
            ],
            "expected_markers": {
                "6": 2, "50": 1, "51": 0, "53": 4000, "54": 2,
            },
        } if args.large_program_body else None),
        "large_live_room": ({
            "room": 1, "walkboxes": 64, "objects": 36,
            "object_verb_entries": 2,
            "named_object_ids": list(range(70, 106)),
            "minimum_expanded_bytes": 19136,
            "minimum_active_bytes": 6082,
            "active_name_padding_bytes": args.large_live_room_name_padding_bytes,
            "passive_object_ids": list(range(71, 106)),
        } if args.large_live_room else None),
        "records": records,
        "global_scripts": [
            {
                "number": number,
                "output": f"global-{number}.bin",
                "length": len(program),
                "instruction_spans": [
                    [item.pc, item.instruction_width]
                    for item in decode_script(
                        program, identity=f"GlobalProgram({number})", kind="global",
                        number=number, room=0, resource_key=f"global.{number}",
                        game_name="copyright-free-native-residency-fixture",
                        source_member=f"fixture/global-{number}.bin",
                        resource_offset=0, source_offset=0,
                    ).instructions
                ],
                "opaque_ranges": [],
            }
            for number, program in globals_
        ],
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "manifest": str(manifest_path), "rooms": len(records),
        "room_local_units": len(records),
        "global_units": len(globals_),
        "object_carriers": 2 if args.load_room_with_ego else 1,
        "passive_objects": (
            35 if args.large_live_room else
            2 if args.load_room_with_ego else 1
        ),
        "large_live_room": bool(args.large_live_room),
        "program_units_lower_bound": len(records) * 3 + len(globals_) + 1,
        "boot_global": 1,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
