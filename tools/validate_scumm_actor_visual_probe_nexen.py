#!/usr/bin/env python3
"""One supervised, synthetic SCUMM actor-visibility diagnostic.

This is not a FATE gameplay test.  It drives the checked-in interpreter with
the data-only actor probe and writes acknowledgements only after capturing the
matching native indexed surface and PPU output.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from same.engines.scumm_v5.costume import ScummV5Costume

DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/"
    "linux-x64/publish/Nexen"
)

ROOM = 0x7FF2BF
ERROR = 0x7E2303
LIFECYCLE = 0x7E2221
C4_STATUS = 0x7E2380
C4_NUMBER = 0x7E2399
C4_PROGRAM = 0x7E23B2
C4_LOCALS = 0x7E2448
RESIDENT_IDS = 0x7E8C00
ACTOR_STATE = 0x41E780
ACTOR_RENDER_VALID = 0x7E5E16
ACTOR_RENDER_FACING = 0x7E5E4E
SURFACE = 0x402000
SURFACE_STATE = 0x401040
SURFACE_PRESENTED_GENERATION = SURFACE_STATE + 0x22
SURFACE_NEXT_GENERATION = SURFACE_STATE + 0x1C
SURFACE_PRESENTED_ROOM = SURFACE_STATE + 0x20
SURFACE_PENDING_VISUAL = SURFACE_STATE + 0x26
SURFACE_ROOM_GENERATION = SURFACE_STATE + 0x02
MODE3_BACKEND = 0x401000
MODE3_PENDING_GENERATION = MODE3_BACKEND + 0x0E
MODE3_COMMITTED_GENERATION = MODE3_BACKEND + 0x10
MODE3_PENDING_GENERATION_HI = MODE3_BACKEND + 0x16
MODE3_COMMITTED_GENERATION_HI = MODE3_BACKEND + 0x18
MODE3_ACCEPTED_PRESENT = 0x40101A
MODE3_CONTROL_STATE = 0x401013
MODE3_SURFACE_LOCKED = 0x401014
MODE3_LAST_STATUS = 0x401015
MODE3_PENDING_COUNT = 0x401024
MODE3_INFLIGHT_COUNT = 0x401026
EVENT_COUNT = 0x7E2004
PALETTE = 0x41E200

POLL_FRAMES = 30
MAX_LOGICAL_FRAMES = 18000
INTERNAL_DEADLINE_SECONDS = 540


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def error_store_sites(rom_path: Path) -> list[int]:
    """Return LoROM CPU addresses of `STA.l $7E:2303` instruction encodings."""
    raw = rom_path.read_bytes()
    instruction = bytes((0x8F, ERROR & 0xFF, (ERROR >> 8) & 0xFF,
                         (ERROR >> 16) & 0xFF))
    sites = []
    offset = 0
    while True:
        offset = raw.find(instruction, offset)
        if offset < 0:
            break
        bank, within = divmod(offset, 0x8000)
        sites.append((bank << 16) | (0x8000 + within))
        offset += 1
    return sites


def read_u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def decode_pose_observation(raw: bytes) -> dict:
    """Decode the phase-local actor pose fields used by visual evidence.

    Offset +0x0B aliases the palette-size scratch while validating a pose; it
    is not the accepted frame.  The committed frame is +0x03.
    """
    require(len(raw) >= 0x0C, "actor pose observation is truncated")
    return {
        "costume_id": raw[2],
        "desired_frame": raw[0],
        "accepted_frame": raw[3],
        "accepted_direction": raw[4],
        "accepted_step": raw[0x0A],
        "palette_size": raw[0x0B],
    }


def direction_index_for_facing(facing: int) -> int:
    """Use the same canonical SCUMM v5 direction partition as the cooker."""
    return ScummV5Costume.direction_index(facing)


def same_room_costume_source(first: dict, second: dict) -> bool:
    """Compare stable costume/source identity, not the per-pose ticket epoch.

    The native field at actor-state +$2B is documented as the pose-validation
    generation and advances for every fetched pose. Costume identity is the
    byte at +$02; ROM/package hashes bind that ID to the same checked data.
    """
    return (first.get("room_epoch") == second.get("room_epoch")
            and first.get("costume_id") == second.get("costume_id")
            and first.get("rom_sha256") == second.get("rom_sha256")
            and first.get("package_sha256") == second.get("package_sha256"))


def pose_is_presented(raw: bytes, *, render_valid: int,
                      render_frame: int, render_step: int,
                      render_generation: int, render_facing: int,
                      next_generation: int, backend_pending_generation: int,
                      backend_committed_generation: int,
                      backend_pending_generation_hi: int,
                      backend_committed_generation_hi: int,
                      backend_state: int, surface_locked: int,
                      pending_visual: int, presented_room: int, room: int,
                      surface_packets_pending: bool,
                      expected_frame: int | None = None,
                      expected_facing: int | None = None,
                      expected_x: int | None = None) -> bool:
    """Require actor cache commit and the production Mode-3 commit fence.

    A successful RenderActor presentation clears POSE_STATE back to zero, so
    readiness is established by the committed render key, not by requiring
    the transient READY value to remain set after presentation.  The surface
    PRESENTED_GENERATION field has no production writer; readiness instead
    requires the Mode-3 backend to have committed the exact surface generation
    and to be idle, unlocked, and free of queued surface packets.
    """
    if len(raw) < 0x7F or raw[1] not in (0, 2) or raw[0x6B] != 1:
        return False
    if (not render_valid or next_generation == 0
            or backend_pending_generation != next_generation
            or backend_committed_generation != next_generation
            or backend_pending_generation_hi != 0
            or backend_committed_generation_hi != 0
            or backend_state != 1 or surface_locked
            or pending_visual or presented_room != room
            or surface_packets_pending):
        return False
    generation = read_u16(raw, 7)
    if (raw[3] != render_frame or raw[0x0A] != render_step
            or generation != render_generation):
        return False
    if expected_frame is not None and raw[3] != expected_frame:
        return False
    if expected_facing is not None:
        if raw[4] != direction_index_for_facing(expected_facing):
            return False
        if render_facing != expected_facing:
            return False
    if expected_x is not None and read_u16(raw, 0x6C) != expected_x:
        return False
    return True


def eq_symbol(source: str, name: str) -> int:
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*\$([0-9A-Fa-f]+)\b",
                      source, re.MULTILINE)
    if not match:
        raise RuntimeError(f"exact build input lacks direct address for {name}")
    return int(match.group(1), 16)


def listing_label_offset(listing_path: Path, name: str) -> int:
    source = listing_path.read_text(encoding="utf-8")
    match = re.search(
        rf"^;\s*{re.escape(name)}\s*=\s*\$([0-9A-Fa-f]+)\s+\(Label\)",
        source, re.MULTILINE,
    )
    if not match:
        raise RuntimeError(f"ROM listing lacks actor diagnostic label {name}")
    return int(match.group(1), 16)


def validate_build(args: argparse.Namespace) -> tuple[dict, dict, dict, bytes]:
    for path in (args.rom, args.package, args.map, args.identity,
                 args.listing, args.directory, args.storage, args.audit,
                 args.poppy_inputs):
        require(path.is_file(), f"required identity-bound artifact missing: {path}")
    require(args.build_source.is_dir(),
            f"assembled source snapshot missing: {args.build_source}")

    identity = json.loads(args.identity.read_text())
    require(identity.get("diagnostics", {}).get("actor_probe", {}).get("kind")
            == "SYNTHETIC_GRAPHICS_DIAGNOSTIC",
            "ROM is not the data-only synthetic actor diagnostic")
    require(identity["diagnostics"]["actor_probe"].get("gameplay_authentic") is False
            and identity["diagnostics"]["actor_probe"].get("production_release_eligible") is False,
            "diagnostic release/authenticity boundary is not explicit")
    rom_hash = sha256(args.rom)
    package_hash = sha256(args.package)
    require(identity.get("rom", {}).get("sha256") == rom_hash,
            "ROM does not match its build identity")
    symbols = identity.get("native_symbols", {})
    require(symbols.get("map", {}).get("name") == args.map.name
            and symbols.get("map", {}).get("sha256") == sha256(args.map),
            "map is not the one bound to this ROM")
    require(symbols.get("listing", {}).get("name") == args.listing.name
            and symbols.get("listing", {}).get("sha256") == sha256(args.listing),
            "listing is not the one bound to this ROM")

    probe_identity = identity["diagnostics"]["actor_probe"]
    require(probe_identity.get("audit_sha256") == sha256(args.audit),
            "actor overlay audit SHA does not match build identity")
    audit = json.loads(args.audit.read_text())
    require(audit.get("kind") == "SYNTHETIC_GRAPHICS_DIAGNOSTIC"
            and audit.get("native_runtime_code_added") == 0,
            "unexpected diagnostic overlay or native code")
    require(audit.get("program", {}).get("sha256")
            == "e2a6b283003fd9e30230d7d9ce21e8311d8f1319284a782b8fee8e62902796a6",
            "unexpected 118-byte probe program identity")

    poppy_hash = sha256(args.poppy_inputs)
    records = identity.get("generated_inputs", [])
    poppy_record = next((row for row in records
                         if Path(row.get("path", "")).name == args.poppy_inputs.name), None)
    require(poppy_record is not None and poppy_record.get("sha256") == poppy_hash,
            "Poppy input manifest is not bound by this build identity")
    poppy_inputs = json.loads(args.poppy_inputs.read_text())
    assembly = {row["path"]: row for row in poppy_inputs.get("inputs", [])
                if row.get("kind") == "ASSEMBLY_INCLUDE"}
    memory_rel = "runtime/snes/kernel/memory.pasm"
    carrier_rel = "runtime/snes/generated/carrier_constants.inc.pasm"
    require(memory_rel in assembly and carrier_rel in assembly,
            "assembly input manifest omits the memory contracts")
    memory_path = args.build_source / memory_rel
    carrier_path = args.build_source / carrier_rel
    require(sha256(memory_path) == assembly[memory_rel]["sha256"],
            "C4/actor memory source differs from the assembled ROM inputs")
    require(sha256(carrier_path) == assembly[carrier_rel]["sha256"],
            "carrier memory source differs from the assembled ROM inputs")
    memory_text = memory_path.read_text()
    carrier_text = carrier_path.read_text()
    contracts = {
        "SAME_SCUMM_C4_SLOT_STATUS": C4_STATUS,
        "SAME_SCUMM_C4_SLOT_NUMBER": C4_NUMBER,
        "SAME_SCUMM_C4_SLOT_PROGRAM": C4_PROGRAM,
        "SAME_SCUMM_C4_SLOT_LOCALS": C4_LOCALS,
        "SAME_SCUMM_ACTOR_POSE_STATE_BASE": ACTOR_STATE,
        "SAME_SCUMM_RESIDENT_UNIT_IDS": RESIDENT_IDS,
    }
    for name, value in contracts.items():
        require(eq_symbol(memory_text, name) == value,
                f"unexpected assembled memory contract for {name}")
    require("25 * 32 signed u16 locals" in memory_text,
            "assembled C4 local layout no longer proves a 64-byte slot stride")
    require(eq_symbol(carrier_text, "SAME_BWRAM_BACKEND_BASE") == 0x401000
            and eq_symbol(carrier_text, "SAME_BWRAM_SURFACE_BASE") == SURFACE,
            "assembled SA-1 BW-RAM surface contract differs")

    directory = json.loads(args.directory.read_text())
    matches = [row for row in directory.get("global_directory", [])
               if int(row["script_number"]) == 1]
    require(len(matches) == 1 and int(matches[0]["program_unit_id"]) == 0,
            "ROM-bound full directory does not resolve boot script 1 to canonical ID 0")
    storage = json.loads(args.storage.read_text())
    require(storage.get("package_sha256") == package_hash,
            "package does not match the compiler storage directory")
    visual = [row for row in storage.get("visual_records", [])
              if int(row["room"]) == 4]
    require(len(visual) == 1 and visual[0]["pixel_length"] == 256 * 224,
            "room-4 indexed visual source is absent or malformed")
    with args.package.open("rb") as package_file:
        package_file.seek(int(visual[0]["pixel_package_offset"]))
        backdrop = package_file.read(int(visual[0]["pixel_length"]))
    require(len(backdrop) == 256 * 224
            and zlib.crc32(backdrop) & 0xFFFFFFFF == int(visual[0]["pixel_crc32"], 16),
            "room-4 source indexed backdrop failed length/CRC validation")
    return identity, audit, {"visual": visual[0], "package_sha256": package_hash}, backdrop


def selector_index(selector: int) -> int:
    if 0xD0 <= selector <= 0xFF:
        return selector - 0xD0
    if 0x4E <= selector <= 0xCF:
        return 0xFF - selector
    raise RuntimeError(f"C4 slot contains invalid resident selector ${selector:02X}")


def read_surface_packets_pending(session) -> bool:
    """Check the live FIFO only; stale packet slots are not queued work."""
    state = bytes(session.read_memory("snesMemory", 0x7E2000, 6))
    head = int.from_bytes(state[0:2], "little")
    count = int.from_bytes(state[4:6], "little")
    packets = bytes(session.read_memory("snesMemory", 0x7E2100, 16 * 0x10))
    for n in range(min(count, 16)):
        offset = ((head + n) & 0x0F) * 0x10
        service, opcode = packets[offset], packets[offset + 1]
        if service == 1 and opcode in (0x0C, 0x0D, 0x11):
            return True
    return False


def actor_bounds_on_surface(raw: bytes) -> tuple[int, int, int, int]:
    """Project the checked pose's signed half-open bounds around its foot.

    The old POSE_RENDER_BOUNDS_VALID bytes are reserved and have no runtime
    writer.  The authoritative per-pose bounds are the signed values loaded
    from the verified pose directory at offsets 0x4B..0x52.
    """
    require(len(raw) >= 0x70, "actor pose state is truncated")

    def signed_word(offset: int) -> int:
        value = int.from_bytes(raw[offset:offset + 2], "little")
        return value - 0x10000 if value & 0x8000 else value

    left, top, right, bottom = (signed_word(offset)
                                for offset in (0x4B, 0x4D, 0x4F, 0x51))
    require(left <= right and top <= bottom,
            f"invalid signed costume bounds: {(left, top, right, bottom)}")
    foot_x, foot_y = signed_word(0x6C), signed_word(0x6E)
    bounds = (max(0, foot_x + left), max(0, foot_y + top),
              min(256, foot_x + right), min(224, foot_y + bottom))
    require(bounds[0] <= bounds[2] and bounds[1] <= bounds[3],
            f"costume bounds lie outside the indexed surface: {bounds}")
    return bounds


def capture_surface(session, directory: Path, label: str,
                    backdrop: bytes) -> dict:
    pixels = session.read_memory("snesMemory", SURFACE, 256 * 224)
    palette = session.read_memory("snesMemory", PALETTE, 768)
    require(len(pixels) == len(backdrop), "incomplete indexed surface read")
    (directory / f"{label}.indexed.bin").write_bytes(pixels)
    rgb = bytearray()
    for index in pixels:
        rgb.extend(palette[index * 3:index * 3 + 3])
    (directory / f"{label}.surface.ppm").write_bytes(
        f"P6\n256 224\n255\n".encode("ascii") + rgb)
    screenshot = session.take_screenshot(format="base64").get("base64")
    require(isinstance(screenshot, str) and screenshot,
            "Nexen returned no actual PPU screenshot")
    (directory / f"{label}.ppu.png").write_bytes(base64.b64decode(screenshot))
    ppu = session.get_ppu_state()
    (directory / f"{label}.ppu-state.json").write_text(
        json.dumps(ppu, indent=2, sort_keys=True) + "\n")

    changed = [i for i, (actual, source) in enumerate(zip(pixels, backdrop))
               if actual != source]
    if changed:
        xs = [index % 256 for index in changed]
        ys = [index // 256 for index in changed]
        bounds = [min(xs), min(ys), max(xs) + 1, max(ys) + 1]
    else:
        bounds = None
    state = session.read_memory("snesMemory", ACTOR_STATE, 128)
    pose = decode_pose_observation(state)
    actor_bounds = actor_bounds_on_surface(state)
    require(actor_bounds[0] < actor_bounds[2]
            and actor_bounds[1] < actor_bounds[3],
            f"the diagnostic pose has no visible clipped bounds: {actor_bounds}")
    witness = session.read_memory("snesMemory", 0x7E5E52, 0x1A)
    present = {
        "surface_next_generation": session.read_u16(SURFACE_NEXT_GENERATION),
        # This old field is retained only so reports can prove it was not
        # mistaken for the production acknowledgement.
        "surface_presented_generation_stale": session.read_u16(SURFACE_PRESENTED_GENERATION),
        "surface_presented_room": session.read_u8(SURFACE_PRESENTED_ROOM),
        "surface_room_generation": session.read_u16(SURFACE_ROOM_GENERATION),
        "surface_pending_visual": session.read_u8(SURFACE_PENDING_VISUAL),
        "backend_pending_generation": session.read_u16(MODE3_PENDING_GENERATION),
        "backend_committed_generation": session.read_u16(MODE3_COMMITTED_GENERATION),
        "backend_pending_generation_hi": session.read_u16(MODE3_PENDING_GENERATION_HI),
        "backend_committed_generation_hi": session.read_u16(MODE3_COMMITTED_GENERATION_HI),
        "mode3_accepted_present": session.read_u16(MODE3_ACCEPTED_PRESENT),
        "mode3_state": session.read_u8(MODE3_CONTROL_STATE),
        "mode3_surface_locked": session.read_u8(MODE3_SURFACE_LOCKED),
        "mode3_last_status": session.read_u8(MODE3_LAST_STATUS),
        "mode3_pending_count": session.read_u16(MODE3_PENDING_COUNT),
        "mode3_inflight_count": session.read_u16(MODE3_INFLIGHT_COUNT),
        "event_count": session.read_u16(EVENT_COUNT),
        "surface_packets_pending": read_surface_packets_pending(session),
        "actor_witness_generation": read_u16(witness, 0x16),
        "actor_witness_valid": witness[0x18],
        "actor_composed": state[0x6B],
        "actor_pose_state": state[1],
        "actor_pose_generation": read_u16(state, 7),
        "actor_render_valid": session.read_u8(ACTOR_RENDER_VALID),
        "actor_render_facing": session.read_u16(ACTOR_RENDER_FACING),
        "actor_render_pose_frame": state[0x15],
        "actor_render_pose_step": state[0x16],
        "actor_render_generation": read_u16(state, 0x7D),
        "actor_render_valid": session.read_u8(ACTOR_RENDER_VALID),
        "actor_render_facing": session.read_u16(ACTOR_RENDER_FACING),
        "actor_render_pose_frame": state[0x15],
        "actor_render_pose_step": state[0x16],
        "actor_render_generation": read_u16(state, 0x7D),
        **pose,
        "accepted_direction": state[4],
        "room_epoch": read_u16(state, 0x29),
        "pose_validation_generation": read_u16(state, 0x2B),
        "render_bounds_valid_reserved": state[0x63],
        "pose_bounds_relative_signed": [
            int.from_bytes(state[offset:offset + 2], "little", signed=True)
            for offset in (0x4B, 0x4D, 0x4F, 0x51)],
        "actor_bounds_screen_from_pose": list(actor_bounds),
        "foot_screen": [read_u16(state, 0x6C), read_u16(state, 0x6E)],
    }
    actual_visible_pixels = sum(1 for i in changed
                                if actor_bounds[0] <= i % 256 < actor_bounds[2]
                                and actor_bounds[1] <= i // 256 < actor_bounds[3])
    return {
        "label": label,
        "indexed_surface_sha256": hashlib.sha256(pixels).hexdigest(),
        "source_backdrop_sha256": hashlib.sha256(backdrop).hexdigest(),
        "different_pixels_from_compiled_backdrop": len(changed),
        "difference_bounds_xyxy": bounds,
        "actor_bound_difference_pixels": actual_visible_pixels,
        "pose": present,
    }


class ProbeObserver:
    def __init__(self, session, output: Path, backdrop: bytes, *, deadline: float):
        self.session = session
        self.output = output
        self.backdrop = backdrop
        self.deadline = deadline
        self.logical_frames = 0
        self.last_state = {}
        self.captures = []
        self.progress: list[dict] = []
        self.slot = None
        self.locals = None
        self.last_pose_state = None

    def read_scene(self) -> dict:
        statuses = self.session.read_memory("snesMemory", C4_STATUS, 25)
        numbers = self.session.read_memory("snesMemory", C4_NUMBER, 25)
        selectors = self.session.read_memory("snesMemory", C4_PROGRAM, 25)
        resident = self.session.read_memory("snesMemory", RESIDENT_IDS, 178 * 2)
        activation = None
        for slot, (status, number, selector) in enumerate(zip(statuses, numbers, selectors)):
            if not status or number != 1:
                continue
            index = selector_index(selector)
            program_id = read_u16(resident, index * 2)
            if program_id == 0:  # GlobalProgram(1), as resolved in this build's directory.
                activation = {"slot": slot, "script_number": number,
                              "selector": selector, "program_unit_id": program_id,
                              "status": status}
                break
        if activation is not None:
            self.slot = activation["slot"]
            self.locals = C4_LOCALS + self.slot * 64
        room = self.session.read_u8(ROOM)
        error = self.session.read_u8(ERROR)
        lifecycle = self.session.read_u8(LIFECYCLE)
        if self.locals is None:
            ack = stage = None
            pc = None
        else:
            ack = self.session.read_u16(self.locals)
            stage = self.session.read_u16(self.locals + 2)
            pc = self.session.read_u16(0x7E23E4 + self.slot * 2)
        actor_pose = self.session.read_memory("snesMemory", ACTOR_STATE, 0x80)
        pose_fields = decode_pose_observation(actor_pose)
        provider = self.session.read_memory("snesMemory", 0x7E2F00, 0x80)
        state = {
            "logical_frame": self.logical_frames,
            "room": room,
            "error": error,
            "lifecycle": lifecycle,
            "activation": activation,
            "locals_base": self.locals,
            "locals_stride": 64,
            "ack": ack,
            "stage": stage,
            "pc": pc,
            "pose_state": actor_pose[1],
            "pose_composed": actor_pose[0x6B],
            "actor_scratch_owner": actor_pose[0x26],
            "actor_pose_bytes": list(actor_pose),
            "actor1_record": list(self.session.read_memory(
                "snesMemory", 0x7F3700, 0x40)),
            "provider_bytes": list(provider),
            "pose_generation": read_u16(actor_pose, 7),
            **pose_fields,
            "direction": actor_pose[4],
            "room_epoch": read_u16(actor_pose, 0x29),
            "pose_validation_generation": read_u16(actor_pose, 0x2B),
            "actor_render_valid": self.session.read_u8(ACTOR_RENDER_VALID),
            "actor_render_facing": self.session.read_u16(ACTOR_RENDER_FACING),
            "actor_render_pose_frame": actor_pose[0x15],
            "actor_render_pose_step": actor_pose[0x16],
            "actor_render_generation": read_u16(actor_pose, 0x7D),
            "surface_presented_generation_stale": self.session.read_u16(SURFACE_PRESENTED_GENERATION),
            "surface_next_generation": self.session.read_u16(SURFACE_NEXT_GENERATION),
            "surface_presented_room": self.session.read_u8(SURFACE_PRESENTED_ROOM),
            "surface_room_generation": self.session.read_u16(SURFACE_ROOM_GENERATION),
            "surface_pending_visual": self.session.read_u8(SURFACE_PENDING_VISUAL),
            "backend_pending_generation": self.session.read_u16(MODE3_PENDING_GENERATION),
            "backend_committed_generation": self.session.read_u16(MODE3_COMMITTED_GENERATION),
            "backend_pending_generation_hi": self.session.read_u16(MODE3_PENDING_GENERATION_HI),
            "backend_committed_generation_hi": self.session.read_u16(MODE3_COMMITTED_GENERATION_HI),
            "mode3_state": self.session.read_u8(MODE3_CONTROL_STATE),
            "mode3_surface_locked": self.session.read_u8(MODE3_SURFACE_LOCKED),
            "mode3_last_status": self.session.read_u8(MODE3_LAST_STATUS),
            "mode3_pending_count": self.session.read_u16(MODE3_PENDING_COUNT),
            "mode3_inflight_count": self.session.read_u16(MODE3_INFLIGHT_COUNT),
            "event_count": self.session.read_u16(EVENT_COUNT),
            "surface_packets_pending": read_surface_packets_pending(self.session),
            "actor_witness_generation": self.session.read_u16(0x7E5E68),
            "actor_witness_valid": self.session.read_u8(0x7E5E6A),
            "scumm_pc": self.session.read_u16(0x7E2300),
            "scumm_last_opcode": self.session.read_u8(0x7E2306),
            "program_select": self.session.read_u8(0x7E2362),
            "c4_current_slot": self.session.read_u8(0x7E2A88),
            "c4_active_count": self.session.read_u8(0x7E2A8A),
            "c4_statuses": list(statuses),
            "c4_numbers": list(numbers),
            "c4_selectors": list(selectors),
            "c4_boot_locals": list(self.session.read_memory("snesMemory", C4_LOCALS + 64, 8)),
            "authentic_bootstrap_started": self.session.read_u8(0x7E5673),
            "m23a_state": list(self.session.read_memory("snesMemory", 0x7FF2BE, 0x13)),
            "m23a_return": list(self.session.read_memory("snesMemory", 0x7FF467, 3)),
            "m23a_chain": list(self.session.read_memory("snesMemory", 0x7FF2D8, 2)),
            "c22_current_room": self.session.read_u8(0x7FD403),
            "c22_null_scene": self.session.read_u8(0x7FD407),
            "scumm_status": self.session.read_u8(0x7E2302),
            "provider_status": provider[0],
            "provider_error": provider[1],
            "program_cache_states": list(self.session.read_memory("snesMemory", 0x7E2F48, 2)),
            "program_cache_failures": self.session.read_u16(0x7E2F68),
            "room_load_state": self.session.read_u8(0x7E2FEB),
            "room_load_id": self.session.read_u8(0x7E2FEC),
            "room_load_failures": self.session.read_u16(0x7E2FF1),
            "live_room_stage": self.session.read_u8(0x401384),
            "engine_frame_entries": self.session.read_u16(0x7E2FAB),
            "engine_frame_returns": self.session.read_u16(0x7E2FAD),
            "engine_frame_stage": self.session.read_u8(0x7E2FAF),
            "stream_error": list(self.session.read_memory("snesMemory", 0x7E5F13, 0x10)),
            "live_room_control": list(self.session.read_memory("snesMemory", 0x401384, 0x40)),
        }
        self.last_state = state
        return state

    def advance(self, count: int = POLL_FRAMES) -> dict:
        if time.monotonic() >= self.deadline:
            raise TimeoutError(f"internal 540-second deadline; last={self.last_state}")
        if self.logical_frames + count > MAX_LOGICAL_FRAMES:
            count = MAX_LOGICAL_FRAMES - self.logical_frames
        require(count > 0, f"logical-frame budget exhausted; last={self.last_state}")
        self.session.run_frames(count)
        self.logical_frames += count
        state = self.read_scene()
        self._persist_progress_sample(state)
        return state

    def _persist_progress_sample(self, state: dict) -> None:
        pose = state["actor_pose_bytes"]
        provider = state["provider_bytes"]
        sample = {
            "logical_frame": state["logical_frame"],
            "room": state["room"],
            "error": state["error"],
            "lifecycle": state["lifecycle"],
            "stage": state["stage"],
            "pc": state["pc"],
            "pose_state": pose[1],
            "desired_frame": pose[0],
            "pose_frame": pose[3],
            "desired_direction": pose[0x13],
            "pose_direction": pose[4],
            "desired_step": pose[9],
            "accepted_step": pose[0x0A],
            "pose_generation": read_u16(pose, 7),
            "pose_composed": pose[0x6B],
            "scratch_owner": pose[0x26],
            "ticket_offset": int.from_bytes(pose[0x1A:0x1E], "little"),
            "ticket_crc32": int.from_bytes(pose[0x1E:0x22], "little"),
            "ticket_length": read_u16(pose, 0x2D),
            "provider_status": provider[0],
            "provider_error": provider[1],
            "provider_offset": int.from_bytes(provider[4:8], "little"),
            "provider_remaining": int.from_bytes(provider[0x15:0x19], "little"),
            "provider_dest_index": read_u16(provider, 0x19),
            "provider_reads_completed": read_u16(provider, 0x31),
            "surface_next_generation": state["surface_next_generation"],
            "surface_presented_generation_stale": state["surface_presented_generation_stale"],
            "actor_render_valid": state["actor_render_valid"],
            "actor_render_facing": state["actor_render_facing"],
            "actor_render_pose_frame": pose[0x15],
            "actor_render_pose_step": pose[0x16],
            "actor_render_generation": read_u16(pose, 0x7D),
        }
        self.progress.append(sample)
        path = self.output / "actor-progress.json"
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps({"kind": "SYNTHETIC_GRAPHICS_DIAGNOSTIC",
                                    "samples": self.progress}, indent=2) + "\n")
        temp.replace(path)

    def capture_timeout_boundary(self) -> None:
        """Save the actual current boundary without acknowledging the driver."""
        boundary = {"last_state": self.last_state,
                    "logical_frames": self.logical_frames}
        try:
            screenshot = self.session.take_screenshot(format="base64").get("base64")
            if screenshot:
                (self.output / "actor-timeout-ppu.png").write_bytes(
                    base64.b64decode(screenshot))
            else:
                boundary["screenshot_error"] = "Nexen returned no screenshot"
        except Exception as exc:
            boundary["screenshot_error"] = f"{type(exc).__name__}: {exc}"
        try:
            boundary["ppu_state"] = self.session.get_ppu_state()
            pixels = self.session.read_memory("snesMemory", SURFACE, 256 * 224)
            boundary["indexed_surface_sha256"] = hashlib.sha256(pixels).hexdigest()
            (self.output / "actor-timeout.indexed.bin").write_bytes(pixels)
            palette = self.session.read_memory("snesMemory", PALETTE, 768)
            rgb = bytearray()
            for index in pixels:
                rgb.extend(palette[index * 3:index * 3 + 3])
            (self.output / "actor-timeout.surface.ppm").write_bytes(
                b"P6\n256 224\n255\n" + rgb)
            boundary["presentation"] = {
                "surface_next_generation": self.session.read_u16(SURFACE_NEXT_GENERATION),
                "surface_presented_generation_stale": self.session.read_u16(SURFACE_PRESENTED_GENERATION),
                "surface_presented_room": self.session.read_u8(SURFACE_PRESENTED_ROOM),
                "backend_pending_generation": self.session.read_u16(MODE3_PENDING_GENERATION),
                "backend_committed_generation": self.session.read_u16(MODE3_COMMITTED_GENERATION),
                "backend_pending_generation_hi": self.session.read_u16(MODE3_PENDING_GENERATION_HI),
                "backend_committed_generation_hi": self.session.read_u16(MODE3_COMMITTED_GENERATION_HI),
                "backend_state": self.session.read_u8(MODE3_CONTROL_STATE),
                "surface_locked": self.session.read_u8(MODE3_SURFACE_LOCKED),
                "pending_visual": self.session.read_u8(SURFACE_PENDING_VISUAL),
                "accepted_present": self.session.read_u16(MODE3_ACCEPTED_PRESENT),
                "event_count": self.session.read_u16(EVENT_COUNT),
                "surface_packets_pending": read_surface_packets_pending(self.session),
            }
        except Exception as exc:
            boundary["surface_read_error"] = f"{type(exc).__name__}: {exc}"
        (self.output / "actor-timeout-boundary.json").write_text(
            json.dumps(boundary, indent=2, sort_keys=True) + "\n")

    def wait_stage(self, wanted: int, *, max_frames: int = 4800) -> dict:
        end = self.logical_frames + max_frames
        while self.logical_frames < end:
            state = self.read_scene()
            if state["error"]:
                self.capture_failure_boundary(state)
            require(state["error"] == 0,
                    f"SCUMM error while waiting for stage {wanted}: {state}")
            if state["stage"] == wanted:
                require(state["room"] == 4 and state["lifecycle"] == 2,
                        f"diagnostic stage {wanted} not in settled room 4: {state}")
                return state
            self.advance(min(POLL_FRAMES, end - self.logical_frames))
        self.capture_timeout_boundary()
        raise TimeoutError(f"stage {wanted} not reached within {max_frames} logical frames: {self.last_state}")

    def capture_failure_boundary(self, state: dict) -> None:
        """Persist first-error evidence while this sole MCP session is alive."""
        snapshot = {"vm": state, "cpu": self.session.get_cpu_state("Snes"),
                    "ranges": {}}
        for name, address, length in (
            ("provider", 0x7E2F00, 0x80),
            ("room_cache", 0x7E2FEB, 0x15),
            ("stream_error", 0x7E5F13, 0x10),
            ("room_control", 0x401384, 0x40),
            ("global_vm", 0x7E2300, 0x80),
            ("c4_header", 0x7E2380, 0x60),
            ("c4_boot_locals", C4_LOCALS + 64, 0x40),
            ("actor_pose", ACTOR_STATE, 0x80),
            ("actor1", 0x7F3700, 0x40),
            ("m23a", 0x7FF2BE, 0x13),
            ("c22", 0x7FD403, 0x08),
        ):
            try:
                snapshot["ranges"][name] = self.session.read_memory(
                    "snesMemory", address, length).hex()
            except Exception as exc:
                snapshot["ranges"][name] = f"read failed: {exc}"
        try:
            snap = self.session.take_screenshot(format="base64").get("base64")
            if snap:
                (self.output / "first-error-frame.png").write_bytes(base64.b64decode(snap))
        except Exception as exc:
            snapshot["screenshot_error"] = str(exc)
        (self.output / "first-error-boundary.json").write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n")

    def wait_presented_pose(self, *, max_frames: int = 1800,
                            expected_frame: int | None = None,
                            expected_facing: int | None = None,
                            expected_x: int | None = None) -> dict:
        end = self.logical_frames + max_frames
        while self.logical_frames < end:
            state = self.read_scene()
            require(state["error"] == 0, f"SCUMM error before pose presentation: {state}")
            next_generation = state["surface_next_generation"]
            pose = self.session.read_memory("snesMemory", ACTOR_STATE, 128)
            is_ready = pose_is_presented(
                pose,
                render_valid=state["actor_render_valid"],
                render_frame=state["actor_render_pose_frame"],
                render_step=state["actor_render_pose_step"],
                render_generation=state["actor_render_generation"],
                render_facing=state["actor_render_facing"],
                next_generation=next_generation,
                backend_pending_generation=state["backend_pending_generation"],
                backend_committed_generation=state["backend_committed_generation"],
                backend_pending_generation_hi=state["backend_pending_generation_hi"],
                backend_committed_generation_hi=state["backend_committed_generation_hi"],
                backend_state=state["mode3_state"],
                surface_locked=state["mode3_surface_locked"],
                pending_visual=state["surface_pending_visual"],
                presented_room=state["surface_presented_room"],
                room=state["room"],
                surface_packets_pending=state["surface_packets_pending"],
                expected_frame=expected_frame,
                expected_facing=expected_facing,
                expected_x=expected_x,
            )
            if state["room"] == 4 and state["lifecycle"] == 2 and is_ready:
                # Require the same committed generation and render key across
                # one completed logical frame before taking indexed/PPU output.
                stable_key = (
                    next_generation, state["actor_render_generation"],
                    state["actor_render_pose_frame"],
                    state["actor_render_pose_step"], state["actor_render_facing"],
                    read_u16(pose, 0x6C), read_u16(pose, 0x6E),
                )
                state = self.advance(1)
                pose = self.session.read_memory("snesMemory", ACTOR_STATE, 128)
                stable = pose_is_presented(
                    pose,
                    render_valid=state["actor_render_valid"],
                    render_frame=state["actor_render_pose_frame"],
                    render_step=state["actor_render_pose_step"],
                    render_generation=state["actor_render_generation"],
                    render_facing=state["actor_render_facing"],
                    next_generation=state["surface_next_generation"],
                    backend_pending_generation=state["backend_pending_generation"],
                    backend_committed_generation=state["backend_committed_generation"],
                    backend_pending_generation_hi=state["backend_pending_generation_hi"],
                    backend_committed_generation_hi=state["backend_committed_generation_hi"],
                    backend_state=state["mode3_state"],
                    surface_locked=state["mode3_surface_locked"],
                    pending_visual=state["surface_pending_visual"],
                    presented_room=state["surface_presented_room"],
                    room=state["room"],
                    surface_packets_pending=state["surface_packets_pending"],
                    expected_frame=expected_frame,
                    expected_facing=expected_facing,
                    expected_x=expected_x,
                )
                current_key = (
                    state["surface_next_generation"], state["actor_render_generation"],
                    state["actor_render_pose_frame"], state["actor_render_pose_step"],
                    state["actor_render_facing"], read_u16(pose, 0x6C),
                    read_u16(pose, 0x6E),
                )
                if not stable or current_key != stable_key:
                    continue
                state["pose_generation"] = read_u16(pose, 7)
                state.update(decode_pose_observation(pose))
                state["direction"] = pose[4]
                state["room_epoch"] = read_u16(pose, 0x29)
                state["pose_validation_generation"] = read_u16(pose, 0x2B)
                state["render_bounds_valid_reserved"] = pose[0x63]
                state["presentation_fence"] = "mode3-committed-stable-one-frame"
                return state
            self.advance(min(10, end - self.logical_frames))
        self.capture_timeout_boundary()
        raise TimeoutError(f"no composed actor pose reached the PPU: {self.last_state}")

    def capture_stage(self, label: str, *, expected_frame: int | None = None,
                      expected_facing: int | None = None,
                      expected_x: int | None = None) -> dict:
        state = self.wait_presented_pose(expected_frame=expected_frame,
                                         expected_facing=expected_facing,
                                         expected_x=expected_x)
        record = capture_surface(self.session, self.output, label, self.backdrop)
        record["vm"] = state
        require(record["pose"]["actor_composed"] == 1
                and record["pose"]["actor_pose_state"] in (0, 2)
                and record["pose"]["actor_render_valid"] == 1,
                f"actor pose was not composed when captured: {record}")
        require(record["actor_bound_difference_pixels"] >= 40,
                f"no clearly distinguishable actor pixels within render bounds: {record}")
        self.captures.append(record)
        (self.output / "actor-visual-observations.json").write_text(
            json.dumps({"kind": "SYNTHETIC_GRAPHICS_DIAGNOSTIC",
                        "captures": self.captures,
                        "last_vm_state": self.last_state}, indent=2) + "\n")
        return record

    def acknowledge(self, value: int) -> None:
        require(self.locals is not None, "cannot acknowledge without matching script activation")
        self.session.write_u16(self.locals, value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--listing", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--poppy-inputs", type=Path, required=True)
    parser.add_argument("--build-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=46041)
    parser.add_argument(
        "--startup-error-probe", action="store_true",
        help="stop at the first SCUMM resource-error write; do not run the actor stages",
    )
    parser.add_argument(
        "--provider-mismatch-probe", action="store_true",
        help="stop at the first actor checked-read ownership mismatch without acknowledging the probe",
    )
    parser.add_argument(
        "--room-commit-trace-probe", action="store_true",
        help="observe the first checked room COMMIT_READY boundary and one following VM frame; no acknowledgements or gameplay",
    )
    parser.add_argument(
        "--actor-code-bank-probe", action="store_true",
        help="stop on first execution at the observed ActorOps-scale bank address; no acknowledgements or gameplay",
    )
    parser.add_argument(
        "--room-publish-boundary-probe", action="store_true",
        help="observe the checked room publish/return and real ActorOps entry before the synthetic pose stages",
    )
    parser.add_argument(
        "--room-publish-step-probe", action="store_true",
        help="stop at each exact publish/ActorOps boundary to identify the first bad program-bank transition",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    identity, audit, source_records, backdrop = validate_build(args)
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK),
            f"documented Nexen installation unavailable: {args.nexen}")
    display = os.environ.get("DISPLAY", "")
    xauthority = os.environ.get("XAUTHORITY", "")
    require(bool(re.fullmatch(r":[0-9]+(?:\.[0-9]+)?", display))
            and bool(xauthority) and Path(xauthority).is_file(),
            f"validator is not under a private xvfb-run display: DISPLAY={display!r}")

    # This build is Nexen, not Mesen. Existing project validators use this
    # same explicit bypass for the pinned Nexen executable; McpSession remains
    # the sole MCP client and owns the process lifecycle.
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None

    started = time.monotonic()
    observer = None
    final = {
        "schema": "same-scumm-actor-visual-proof-v1",
        "kind": "SYNTHETIC_GRAPHICS_DIAGNOSTIC",
        "gameplay_authentic": False,
        "production_release_eligible": False,
        "rom_sha256": sha256(args.rom),
        "map_sha256": sha256(args.map),
        "build_identity_sha256": sha256(args.identity),
        "package_sha256": source_records["package_sha256"],
        "actor_probe_audit_sha256": sha256(args.audit),
        "boot_program_identity": "GlobalProgram(1)",
        "boot_program_unit_id": 0,
        "locals_stride_bytes": 64,
        "captures": [],
        "result": "NOT_VERIFIED",
    }
    try:
        from validate_scumm_startup42_nexen import verified_symbol_map_for_rom
        verified_map, _symbols = verified_symbol_map_for_rom(args.rom.resolve())
        require(verified_map.resolve() == args.map.resolve(),
                "source-bound symbol helper selected a different map")
        with mcp_session.McpSession(
            rom=args.rom.resolve(), mesen=args.nexen.resolve(), cwd=args.rom.parent,
            port=args.port, boot_wait=2.0, socket_timeout=45.0,
            stderr_log=args.output / "nexen.stderr.log",
        ) as session:
            session.pause()
            session.tool("reset_emulator", {"power": True})
            session.pause()
            initial = session.get_state()
            require(int(initial.get("frameCount", -1)) == 0,
                    f"cold reset did not reach frame 0: {initial}")
            if args.room_commit_trace_probe:
                # Enable the emulator's instruction ring before boot so the
                # first completion trace includes the path leading into the
                # pending room commit, not only instructions after capture.
                session.trace_log(count=1, cpu_type="Snes")
            if args.actor_code_bank_probe:
                # The prior read-only trace observed BRK opcodes at the
                # mapped ActorOps-scale address after room publication was
                # expected. Stop on its first execution and capture the
                # caller stream before repeated BRKs can evict it from the
                # emulator's bounded trace ring.
                session.trace_log(count=1, cpu_type="Snes")
                actor_code_address = 0x90D143
                hook = session.add_exec_hook(actor_code_address)
                try:
                    stop = session.run_until(
                        max_frames=2400, hook_handle=hook)
                    session.pause()
                    cpu = session.get_cpu_state("Snes")
                    sp = int(cpu.get("sp", 0)) & 0xFFFF
                    stack_start = max(0, sp - 0x40)
                    stack_length = min(0x60, 0x10000 - stack_start)
                    stack_bytes = session.read_memory(
                        "snesMemory", stack_start, stack_length)
                    trace = session.trace_log(count=512, cpu_type="Snes")
                    report = {
                        "kind": "SYNTHETIC_ACTOR_CODE_BANK_TRACE",
                        "gameplay_authentic": False,
                        "production_release_eligible": False,
                        "hypothesis": "the pending room transaction returns into the expected ActorOps-scale code address with an invalid program bank; catch its first execution before repeated BRKs",
                        "expected_observation": "the hook fires at the mapped address, and the preceding native instruction tail identifies the transfer/return path; otherwise report the bounded no-hit state",
                        "exit_condition": "first execution hook or 2400 logical frames, under the supervisor's 600-second process-tree deadline",
                        "hook_address": actor_code_address,
                        "run_until": stop,
                        "cpu_at_capture": cpu,
                        "hardware_stack_window_address": stack_start,
                        "hardware_stack_window": list(stack_bytes),
                        "cpu_address_disassembly": session.disassemble(
                            ((int(cpu.get("k", 0)) & 0xFF) << 16)
                            | (int(cpu.get("pc", 0)) & 0xFFFF),
                            count=24, cpu_type="Snes"),
                        "room_and_vm_state": ProbeObserver(
                            session, args.output, backdrop,
                            deadline=started + INTERNAL_DEADLINE_SECONDS,
                        ).read_scene(),
                        "mapped_code_bytes": list(session.read_memory(
                            "snesMemory", actor_code_address, 16)),
                        "bank80_alias_bytes": list(session.read_memory(
                            "snesMemory", 0x80D143, 16)),
                        "trace_tail": trace.get("rows", []),
                        "acknowledgements_written": [],
                    }
                    (args.output / "actor-code-bank-trace.json").write_text(
                        json.dumps(report, indent=2, sort_keys=True) + "\n")
                    final.update({
                        "result": "ACTOR_CODE_BANK_TRACE_CAPTURED" if stop.get("reason") in ("hook", "hookFired") else "ACTOR_CODE_BANK_HOOK_NOT_REACHED",
                        "actor_code_bank_diagnostic": "actor-code-bank-trace.json",
                    })
                    return 0 if stop.get("reason") in ("hook", "hookFired") else 2
                finally:
                    session.remove_hook(hook)
            if args.room_publish_boundary_probe:
                # This probe is bound to the exact assembled diagnostic image.
                # The source map prints 16-bit label offsets, while the linked
                # LoROM bank is recovered from the actual JSL sites in this
                # image.  In particular, $90:D143 is the observed empty-bank
                # path, whereas ActorOps itself is present at $00:CDE7.
                require(sha256(args.rom)
                        == "78d0072ffd0dec2c34a41977cdd756f65ebb3a6a92f4d306d86ad433bc952ffc",
                        "room-boundary addresses are not bound to the expected full-actor ROM")
                boundaries = {
                    "room_visual_publish_entry": 0x54904A,
                    "room_visual_publish_success": 0x098562,
                    "actor_ops_entry_bank00": 0x00CDE7,
                    "actor_ops_empty_bank90": 0x90D143,
                }
                rom_bytes = args.rom.read_bytes()
                signatures = {
                    "room_visual_publish_entry": bytes.fromhex("08 C2 30"),
                    "room_visual_publish_success": bytes.fromhex("A9 00 8F"),
                    "actor_ops_entry_bank00": bytes.fromhex("E2 20 AF"),
                    "actor_ops_empty_bank90": bytes.fromhex("00 00 00"),
                }
                for name, address in boundaries.items():
                    bank, cpu_address = address >> 16, address & 0xFFFF
                    offset = (bank & 0x7F) * 0x8000 + (cpu_address & 0x7FFF)
                    require(rom_bytes[offset:offset + len(signatures[name])]
                            == signatures[name],
                            f"ROM bytes do not match linked boundary {name} at ${address:06X}")
                handles = {session.add_exec_hook(address): name
                           for name, address in boundaries.items()}
                events = []
                cpu_samples = []
                observer = ProbeObserver(
                    session, args.output, backdrop,
                    deadline=started + INTERNAL_DEADLINE_SECONDS,
                )
                stop_reason = "frame_limit"
                frames_advanced = 0
                try:
                    while frames_advanced < 2400:
                        batch = min(10, 2400 - frames_advanced)
                        session.run_frames(batch)
                        frames_advanced += batch
                        for item in session.drain_notifications(timeout=0.0):
                            if item.get("method") != "notifications/mesen/hookFired":
                                continue
                            params = item.get("params", {})
                            handle = int(params.get("handle", -1))
                            name = handles.pop(handle, None)
                            if name is None:
                                continue
                            event = {
                                "boundary": name,
                                "hook": dict(params),
                                "cpu": session.get_cpu_state("Snes"),
                                "room_state": observer.read_scene(),
                                "logical_frame": frames_advanced,
                            }
                            events.append(event)
                            session.remove_hook(handle)
                            if name == "actor_ops_empty_bank90":
                                stop_reason = "empty_bank_execution"
                                break
                            if name == "actor_ops_entry_bank00":
                                stop_reason = "real_actor_ops_reached"
                                break
                        if stop_reason != "frame_limit":
                            break
                    boundary_report = {
                        "kind": "SYNTHETIC_ROOM_PUBLISH_BOUNDARY_TRACE",
                        "gameplay_authentic": False,
                        "production_release_eligible": False,
                        "hypothesis": "the earlier $90:D143 hook may have mistaken an empty-bank return for the real ActorOps handler; distinguish room publication success, valid ActorOps entry, and empty-bank execution",
                        "expected_observation": "room visual publish returns through its linked bank and the synthetic driver reaches ActorOps at the ROM-backed handler address, or the first missing boundary identifies the failure",
                        "exit_condition": "first valid ActorOps/empty-bank boundary or 2400 logical frames; if valid ActorOps is reached, continue directly into the normal stage-capture path within the same supervised run",
                        "boundaries": {name: hex(address) for name, address in boundaries.items()},
                        "events": events,
                        "stop_reason": stop_reason,
                        "frames_advanced": frames_advanced,
                        "final_state": observer.read_scene(),
                        "trace_tail": session.trace_log(count=128, cpu_type="Snes").get("rows", []),
                        "acknowledgements_written": [],
                    }
                    (args.output / "room-publish-boundary-trace.json").write_text(
                        json.dumps(boundary_report, indent=2, sort_keys=True) + "\n")
                    final["room_publish_boundary_probe"] = boundary_report
                    if stop_reason == "empty_bank_execution":
                        final["result"] = "EMPTY_BANK_EXECUTION_BEFORE_ACTOR_OPS"
                        (args.output / "actor-visual-observations.json").write_text(
                            json.dumps(final, indent=2, sort_keys=True) + "\n")
                        return 2
                    if stop_reason == "frame_limit":
                        final["result"] = "ACTOR_OPS_BOUNDARY_NOT_REACHED"
                        (args.output / "actor-visual-observations.json").write_text(
                            json.dumps(final, indent=2, sort_keys=True) + "\n")
                        return 2
                finally:
                    for handle in handles:
                        session.remove_hook(handle)
            if args.room_publish_step_probe:
                # Observe only addresses backed by the linked ROM bytes.
                # Earlier probes installed breakpoints at $90:CDE7/$90:D143,
                # although those locations are zero-filled in this LoROM.
                # Nexen's hook notification can arrive after the CPU has
                # advanced into an unrelated instruction stream, so those
                # empty-bank hits were not evidence of an ActorOps dispatch.
                # Trace is enabled before boot; the only ActorOps boundary
                # below is the verified handler at $00:CDE7.
                require(sha256(args.rom)
                        == "78d0072ffd0dec2c34a41977cdd756f65ebb3a6a92f4d306d86ad433bc952ffc",
                        "step-boundary addresses are not bound to the expected full-actor ROM")
                boundaries = {
                    "room_visual_publish_entry": (0x54904A, "08 C2 30"),
                    "room_visual_publish_loop_exit": (0x54906B, "22 33 80 14"),
                    "palette_service_rtl": (0x148032, "6B"),
                    "actor_underlay_invalidate_entry": (0x148CF6, "08 C2 30"),
                    "actor_underlay_invalidate_done": (0x148D20, "AB 7A FA 68 28 6B"),
                    "room_visual_publish_success_rtl": (0x5490CD, "6B"),
                    "room_visual_publish_failure": (0x5490CE, "28 38 6B"),
                    "commit_visual_success": (0x098562, "A9 00 8F"),
                    "actor_ops_entry_bank00": (0x00CDE7, "E2 20 AF"),
                }
                rom_bytes = args.rom.read_bytes()
                for name, (address, signature_hex) in boundaries.items():
                    bank, cpu_address = address >> 16, address & 0xFFFF
                    offset = (bank & 0x7F) * 0x8000 + (cpu_address & 0x7FFF)
                    signature = bytes.fromhex(signature_hex)
                    require(rom_bytes[offset:offset + len(signature)] == signature,
                            f"ROM bytes do not match {name} at ${address:06X}")
                events = []
                cpu_samples = []
                observer = ProbeObserver(
                    session, args.output, backdrop,
                    deadline=started + INTERNAL_DEADLINE_SECONDS,
                )
                frames_advanced = 0
                stop_reason = "publish_entry_not_reached"
                active_handles: set[int] = set()
                entry_handle = session.add_exec_hook(boundaries[
                    "room_visual_publish_entry"][0])
                active_handles.add(entry_handle)
                try:
                    entry_run = session.run_until(
                        max_frames=2400, hook_handle=entry_handle)
                    session.pause()
                    frames_advanced = int(
                        session.get_state().get("frameCount", frames_advanced))
                    entry_notifications = [
                        item for item in session.drain_notifications(timeout=0.0)
                        if item.get("method") == "notifications/mesen/hookFired"
                        and int(item.get("params", {}).get("handle", -1)) == entry_handle
                    ]
                    session.remove_hook(entry_handle)
                    active_handles.discard(entry_handle)
                    if entry_notifications and entry_run.get("reason") == "hookFired":
                        params = entry_notifications[0].get("params", {})
                        events.append({
                            "boundary": "room_visual_publish_entry",
                            "hook": dict(params),
                            "run_until": entry_run,
                            "cpu_after_hook": session.get_cpu_state("Snes"),
                            "logical_frames_advanced": frames_advanced,
                            "room_state": observer.read_scene(),
                            "trace": session.trace_log(count=24, cpu_type="Snes").get("rows", []),
                        })
                        stop_reason = "frame_limit"
                        ordered_boundaries = [
                            "room_visual_publish_loop_exit",
                            "palette_service_rtl",
                            "actor_underlay_invalidate_entry",
                            "actor_underlay_invalidate_done",
                            "room_visual_publish_success_rtl",
                            "room_visual_publish_failure",
                            "commit_visual_success",
                            "actor_ops_entry_bank00",
                        ]
                        boundary_handles = {
                            session.add_exec_hook(boundaries[name][0]): name
                            for name in ordered_boundaries
                        }
                        active_handles.update(boundary_handles)
                        fired_names: set[str] = set()
                        entry_frame = frames_advanced
                        frame_limit = entry_frame + 120
                        step = 0
                        while len(fired_names) < len(ordered_boundaries):
                            next_name = next(
                                (name for name in ordered_boundaries
                                 if name not in fired_names), None)
                            if next_name is None:
                                break
                            handle = next(
                                handle for handle, name in boundary_handles.items()
                                if name == next_name)
                            current_frame = int(
                                session.get_state().get("frameCount", frames_advanced))
                            remaining = frame_limit - current_frame
                            if remaining <= 0:
                                stop_reason = f"{next_name}_not_reached"
                                break
                            run_result = session.run_until(
                                max_frames=remaining, hook_handle=handle)
                            session.pause()
                            frames_advanced = int(
                                session.get_state().get("frameCount", frames_advanced))
                            cpu = session.get_cpu_state("Snes")
                            notices = [
                                item for item in session.drain_notifications(timeout=0.0)
                                if item.get("method") == "notifications/mesen/hookFired"
                                and int(item.get("params", {}).get("handle", -1))
                                in boundary_handles
                            ]
                            cpu_samples.append({
                                "step": step + 1,
                                "waited_for_boundary": next_name,
                                "diagnostic_frames_advanced": frames_advanced,
                                "run_result": run_result,
                                "cpu": cpu,
                                "live_room_stage": session.read_u8(0x401384),
                                "m23a_phase": session.read_u8(0x7FF2C2),
                                "room": session.read_u8(ROOM),
                                "error": session.read_u8(ERROR),
                            })
                            if not notices:
                                stop_reason = f"{next_name}_not_reached"
                                break
                            for item in sorted(
                                    notices,
                                    key=lambda notice: int(
                                        notice.get("params", {}).get("cycleCount", 0))):
                                params = item.get("params", {})
                                hit_handle = int(params["handle"])
                                name = boundary_handles[hit_handle]
                                fired_names.add(name)
                                events.append({
                                    "boundary": name,
                                    "hook": dict(params),
                                    "run_until": run_result,
                                    "cpu_observed_after_hook_batch": cpu,
                                    "logical_frames_advanced": frames_advanced,
                                    "room_state": observer.read_scene(),
                                    "trace": session.trace_log(count=24, cpu_type="Snes").get("rows", []),
                                })
                                if name == "actor_ops_entry_bank00":
                                    stop_reason = "real_actor_ops_entry"
                                elif name == "room_visual_publish_failure":
                                    stop_reason = "room_visual_publish_failed"
                                session.remove_hook(hit_handle)
                                active_handles.discard(hit_handle)
                            step += 1
                            if stop_reason in (
                                "real_actor_ops_entry",
                                "room_visual_publish_failed",
                            ):
                                break
                    else:
                        stop_reason = "publish_entry_not_reached"
                    report = {
                        "kind": "SYNTHETIC_ROOM_PUBLISH_STEP_TRACE",
                        "gameplay_authentic": False,
                        "production_release_eligible": False,
                        "hypothesis": "after the pixel-copy and palette hooks, determine whether actor-underlay invalidation returns before the room-publish epilogue; arm only addresses backed by this ROM and the verified ActorOps entry",
                        "expected_observation": "underlay invalidation entry/done, publish success, commit continuation, and ActorOps entry occur in order; a failure or missing edge identifies the first unresolved call boundary",
                        "exit_condition": "arm the whole copy/palette/return/commit/ActorOps chain before resuming, then wait on a single hook at a time for at most 120 total frames; never exceed the supervisor's 600-second process-tree limit",
                        "boundaries": {
                            name: {"address": hex(address), "signature": signature}
                            for name, (address, signature) in boundaries.items()
                        },
                        "frames_advanced": frames_advanced,
                        "stop_reason": stop_reason,
                        "events": events,
                        "cpu_samples": cpu_samples,
                        "final_state": observer.read_scene(),
                        "final_disassembly": (
                            session.disassemble(
                                ((int(cpu_samples[-1]["cpu"].get("k", 0)) & 0xFF) << 16)
                                | (int(cpu_samples[-1]["cpu"].get("pc", 0)) & 0xFFFF),
                                count=12, cpu_type="Snes",
                            ) if cpu_samples else []
                        ),
                        "acknowledgements_written": [],
                    }
                    (args.output / "room-publish-step-trace.json").write_text(
                        json.dumps(report, indent=2, sort_keys=True) + "\n")
                    final["room_publish_step_probe"] = report
                    if stop_reason == "room_visual_publish_failed":
                        final["result"] = "ROOM_VISUAL_PUBLISH_FAILED"
                        (args.output / "actor-visual-observations.json").write_text(
                            json.dumps(final, indent=2, sort_keys=True) + "\n")
                        return 2
                    if stop_reason != "real_actor_ops_entry":
                        final["result"] = "ROOM_PUBLISH_STEP_BOUNDARY_NOT_REACHED"
                        final["room_publish_step_stop_reason"] = stop_reason
                        (args.output / "actor-visual-observations.json").write_text(
                            json.dumps(final, indent=2, sort_keys=True) + "\n")
                        return 2
                    # If normal ActorOps entry was reached, retain this same
                    # session and fall through to the existing pose observer.
                finally:
                    for handle in active_handles:
                        session.remove_hook(handle)
            if args.startup_error_probe:
                # A single, source-neutral first-error diagnostic. Service
                # paths write the error byte directly, so supervise execution
                # hooks on every ROM-encoded STA.l $7E:2303 plus the exact
                # data hook. It never acknowledges or advances the actor
                # script; the frame ceiling covers the bounded room load and
                # stops on the first error write.
                error_sites = error_store_sites(args.rom)
                require(0 < len(error_sites) <= 128,
                        f"unexpected count of SCUMM error store sites: {len(error_sites)}")
                store_hooks = {
                    session.add_exec_hook(address): address
                    for address in error_sites
                }
                # The far service resides in bank 9 in this established
                # personality. Resolve its within-bank offsets from this
                # exact ROM listing rather than carrying stale addresses
                # across additive assembly changes.
                pose_milestones = (
                    "find", "row_found_v2", "bounds_valid", "chunk_count_valid",
                    "chunk_directory_index_ok", "span_count_nonzero",
                    "span_count_ok", "span_page_ok", "span_range_ok",
                    "chunk_length_ok", "palette_high_zero", "palette_nonzero",
                    "palette_valid", "scratch_free", "read_error", "error",
                )
                pose_labels = {
                    name: listing_label_offset(
                        args.listing, f"ScummV5_ActorPose_Ensure__{name}")
                    for name in pose_milestones
                }
                pose_hooks = {
                    session.add_exec_hook((0x09 << 16) | offset): label
                    for label, offset in pose_labels.items()
                }
                error_hook = session.add_write_hook(
                    ERROR, match_value=0x10, match_value_mask=0xFF)
                events = []
                store_hits = []
                pose_label_hits = []
                frames_advanced = 0
                all_hook_events = []
                # Frame-sized stepping lets us correlate the execution-site
                # hook with the exact error-byte write in the same frame.
                for _ in range(2400):
                    session.run_frames(1)
                    frames_advanced += 1
                    for item in session.drain_notifications(timeout=0.0):
                        if item.get("method") != "notifications/mesen/hookFired":
                            continue
                        params = item.get("params", {})
                        handle = int(params.get("handle", -1))
                        if handle in store_hooks:
                            hit = {**params, "site": store_hooks[handle]}
                            store_hits.append(hit)
                            all_hook_events.append({"kind": "error_store_exec", **hit})
                        elif handle in pose_hooks:
                            hit = {**params, "label": pose_hooks[handle]}
                            pose_label_hits.append(hit)
                            all_hook_events.append({"kind": "actor_pose_label", **hit})
                        elif (handle == error_hook
                              and int(params.get("value", -1)) == 0x10):
                            event = dict(params)
                            events.append(event)
                            all_hook_events.append({"kind": "resource_error_write", **event})
                    if events:
                        break
                session.remove_hook(error_hook)
                for handle in pose_hooks:
                    session.remove_hook(handle)
                for handle in store_hooks:
                    session.remove_hook(handle)
                cpu = session.get_cpu_state("Snes")
                pc = (((int(cpu.get("k", 0)) & 0xFF) << 16)
                      | (int(cpu.get("pc", 0)) & 0xFFFF))
                stack_pointer = int(cpu.get("sp", 0)) & 0xFFFF
                stack = list(session.read_memory(
                    "snesMemory", (stack_pointer + 1) & 0xFFFF, 16))
                scenario_error = session.read_memory("snesMemory", 0x7E5F20, 0x0F)
                snapshot = {
                    "kind": "STARTUP_FIRST_RESOURCE_ERROR_DIAGNOSTIC",
                    "hypothesis": "the first SCUMM_ERR_RESOURCE during the synthetic room/costume operation is associated with a specific actor-pose validation or checked-read boundary",
                    "expected_observation": "exact matched write plus preceding native instructions and lifecycle state",
                    "exit_condition": "stop at end of first frame containing a $10 write to SAME_SCUMM_ERROR or after 2400 logical frames",
                    "frames_advanced": frames_advanced,
                    "resource_error_write_events": events,
                    "candidate_store_instruction_count": len(error_sites),
                    "error_store_instruction_hits": store_hits,
                    "actor_pose_label_hits": pose_label_hits,
                    "ordered_hook_events": all_hook_events,
                    "store_hit_disassembly": [
                        {"site": hit["site"],
                         "instructions": session.disassemble(
                             hit["site"], count=4, cpu_type="Snes")}
                        for hit in store_hits[-4:]
                    ],
                    "cpu": cpu,
                    "stack_pointer": stack_pointer,
                    "stack_bytes_from_sp_plus_1": stack,
                    "pc_disassembly": session.disassemble(
                        pc, count=24, cpu_type="Snes"),
                    "scumm": {
                        "error": session.read_u8(ERROR),
                        "stream_error_site": session.read_u8(0x7E5F17),
                        "first_error_capture_valid": session.read_u8(0x7E5F18),
                        "preexisting_error_capture": list(scenario_error),
                        "room": session.read_u8(ROOM),
                        "lifecycle": session.read_u8(LIFECYCLE),
                        "m23a": list(session.read_memory(
                            "snesMemory", 0x7FF2BE, 0x13)),
                        "c22": list(session.read_memory(
                            "snesMemory", 0x7FD403, 0x08)),
                        "c4_statuses": list(session.read_memory(
                            "snesMemory", C4_STATUS, 25)),
                        "provider": list(session.read_memory(
                            "snesMemory", 0x7E2F00, 0x20)),
                        "provider_full": list(session.read_memory(
                            "snesMemory", 0x7E2F00, 0x80)),
                        "actor_pose_state": list(session.read_memory(
                            "snesMemory", ACTOR_STATE, 0x80)),
                        "actor1_record": list(session.read_memory(
                            "snesMemory", 0x7F3700, 0x40)),
                        "c14_initialized": session.read_u8(0x7F5F08),
                        "desired_actor": {
                            "costume": session.read_u8(0x7E5E4C),
                            "visible": session.read_u8(0x7E5E4D),
                            "facing": session.read_u16(0x7E5E4A),
                            "frame": session.read_u8(ACTOR_STATE),
                            "direction": session.read_u8(ACTOR_STATE + 0x13),
                            "step": session.read_u8(ACTOR_STATE + 0x09),
                        },
                        "actor_scratch_owner": session.read_u8(0x41E7A6),
                        "actor_scratch_prefix": list(session.read_memory(
                            "snesMemory", 0x4013C4, 32)),
                        "c14_initialized": session.read_u8(0x7F5F08),
                        "desired_actor": {
                            "costume": session.read_u8(0x7E5E4C),
                            "visible": session.read_u8(0x7E5E4D),
                            "facing": session.read_u16(0x7E5E4A),
                            "frame": session.read_u8(ACTOR_STATE),
                            "direction": session.read_u8(ACTOR_STATE + 0x13),
                            "step": session.read_u8(ACTOR_STATE + 0x09),
                        },
                        "room_loader": list(session.read_memory(
                            "snesMemory", 0x7E2FEB, 0x15)),
                    },
                }
                (args.output / "startup-first-resource-error.json").write_text(
                    json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
                final.update({
                    "result": "STARTUP_ERROR_WRITE_TRACE_CAPTURED" if events else "STARTUP_ERROR_NOT_OBSERVED",
                    "startup_error_diagnostic": "startup-first-resource-error.json",
                    "diagnostic_frames": frames_advanced,
                })
                return 0 if events else 2
            session.set_input(0, 1)
            observer = ProbeObserver(session, args.output, backdrop,
                                     deadline=started + INTERNAL_DEADLINE_SECONDS)
            if args.room_commit_trace_probe:
                trace = None
                while observer.logical_frames < 2400:
                    state = observer.advance(POLL_FRAMES)
                    if (state["room"] == 4
                            and state["live_room_stage"] == 5
                            and state["m23a_state"][4] == 5):
                        at_ready = state
                        # MCP frame advancement can return while the SNES CPU
                        # is still in the NMI that interrupted Engine_Frame.
                        # Treat a completed engine-frame return, not merely a
                        # logical video frame, as the observation boundary.
                        frame_returns_before = state["engine_frame_returns"]
                        completed_frames = []
                        after_ready = state
                        final_cpu = None
                        for _ in range(4):
                            after_ready = observer.advance(1)
                            frame_cpu = session.get_cpu_state("Snes")
                            completed_frames.append({
                                "logical_frame": after_ready["logical_frame"],
                                "engine_frame_entries": after_ready["engine_frame_entries"],
                                "engine_frame_returns": after_ready["engine_frame_returns"],
                                "m23a_phase": after_ready["m23a_state"][4],
                                "live_room_stage": after_ready["live_room_stage"],
                                "surface_room_generation": after_ready["surface_room_generation"],
                                "cpu_pc": frame_cpu.get("pc"),
                                "cpu_x": frame_cpu.get("x"),
                                "cpu_sp": frame_cpu.get("sp"),
                                "cpu_cycle_count": frame_cpu.get("cycleCount"),
                            })
                            final_cpu = frame_cpu
                            if ((after_ready["engine_frame_returns"]
                                 - frame_returns_before) & 0xFFFF) > 0:
                                break
                        cpu = final_cpu or session.get_cpu_state("Snes")
                        pc = (((int(cpu.get("k", 0)) & 0xFF) << 16)
                              | (int(cpu.get("pc", 0)) & 0xFFFF))
                        trace = {
                            "kind": "SYNTHETIC_ROOM_COMMIT_READY_TRACE",
                            "gameplay_authentic": False,
                            "production_release_eligible": False,
                            "hypothesis": "the final checked SC5VIS transfer reaches COMMIT_READY but its M23A phase-5 notification is not consumed by the ordinary engine frame",
                            "expected_observation": "after at least one completed Engine_Frame return, phase 5 is consumed and room publication advances, or the captured ownership/continuation state identifies why not",
                            "exit_condition": "capture the first room-4 COMMIT_READY/phase-5 state and at most four logical frames until Engine_Frame returns; stop searching after 2400 logical frames",
                            "frames_to_boundary": observer.logical_frames,
                            "engine_frame_returns_before": frame_returns_before,
                            "completed_frame_observations": completed_frames,
                            "engine_frame_completed": (
                                ((after_ready["engine_frame_returns"]
                                  - frame_returns_before) & 0xFFFF) > 0
                            ),
                            "at_ready": at_ready,
                            "after_completed_vm_frame": after_ready,
                            "cpu": cpu,
                            "native_stack_window": list(session.read_memory(
                                "snesMemory", 0x7E0F80, 0x80)),
                            "reset_brk_counter": session.read_u8(0x7FF47D),
                            "reset_diagnostic_window": list(session.read_memory(
                                "snesMemory", 0x7FF470, 0x20)),
                            # Retain the recent real CPU instruction stream at
                            # the blocked transaction boundary. This is an
                            # observer-only diagnostic: it does not alter the
                            # ROM personality or CPU state.
                            "trace_tail": session.trace_log(
                                count=192, cpu_type="Snes").get("rows", []),
                            "pc_disassembly": session.disassemble(pc, count=20, cpu_type="Snes"),
                            "room_loader": list(session.read_memory("snesMemory", 0x7E2FEB, 0x15)),
                            "lifecycle": list(session.read_memory("snesMemory", 0x7FF2BE, 0x42)),
                            "active_room_header": list(session.read_memory("snesMemory", 0x41E800, 0x40)),
                            "locals_stride_bytes": 64,
                            "acknowledgements_written": [],
                        }
                        (args.output / "room-commit-ready-trace.json").write_text(
                            json.dumps(trace, indent=2, sort_keys=True) + "\n")
                        final.update({
                            "result": "ROOM_COMMIT_READY_TRACE_NOT_VISUAL_ACCEPTANCE",
                            "room_commit_trace": "room-commit-ready-trace.json",
                            "logical_frames": observer.logical_frames,
                            "engine_frame_completed": trace["engine_frame_completed"],
                            "last_vm_state": after_ready,
                        })
                        (args.output / "actor-visual-observations.json").write_text(
                            json.dumps(final, indent=2, sort_keys=True) + "\n")
                        return 0
                final.update({
                    "result": "ROOM_COMMIT_READY_NOT_REACHED",
                    "logical_frames": observer.logical_frames,
                    "last_vm_state": observer.last_state,
                })
                (args.output / "actor-visual-observations.json").write_text(
                    json.dumps(final, indent=2, sort_keys=True) + "\n")
                return 2
            if args.provider_mismatch_probe:
                stage1 = observer.wait_stage(1, max_frames=6000)
                mismatch_address = (0x090000 | listing_label_offset(
                    args.listing, "ScummV5_ActorPose_Ensure__lost_request"))
                mismatch_hook = session.add_exec_hook(mismatch_address)
                frames = 0
                hit = None
                while frames < 2400 and hit is None:
                    session.run_frames(1)
                    frames += 1
                    for item in session.drain_notifications(timeout=0.0):
                        if (item.get("method") == "notifications/mesen/hookFired"
                                and int(item.get("params", {}).get("handle", -1))
                                == mismatch_hook):
                            hit = dict(item.get("params", {}))
                            break
                session.remove_hook(mismatch_hook)
                pose = session.read_memory("snesMemory", ACTOR_STATE, 0x80)
                provider = session.read_memory("snesMemory", 0x7E2F00, 0x48)
                surface = session.read_memory("snesMemory", SURFACE_STATE, 0x30)
                expected = {
                    "offset": (int.from_bytes(provider[4:8], "little"),
                               int.from_bytes(pose[0x1A:0x1E], "little")),
                    "crc32": (int.from_bytes(provider[0x11:0x15], "little"),
                              int.from_bytes(pose[0x1E:0x22], "little")),
                    "length": (int.from_bytes(provider[8:12], "little"),
                               int.from_bytes(pose[0x2D:0x2F], "little")),
                    "destination": (int.from_bytes(provider[0x0C:0x0F], "little"),
                                    0x4013C4),
                    "scratch_owner": (pose[0x26], 1),
                    "room_epoch": (int.from_bytes(pose[0x29:0x2B], "little"),
                                   int.from_bytes(surface[2:4], "little")),
                    "pose_validation_generation": (int.from_bytes(pose[0x2B:0x2D], "little"),
                                       int.from_bytes(pose[7:9], "little")),
                }
                report = {
                    "kind": "SYNTHETIC_ACTOR_PROVIDER_MISMATCH_TRACE",
                    "hypothesis": "a shared-provider descriptor or ownership field changes while the checked actor chunk is in flight",
                    "expected_observation": "first lost_request execution plus request descriptor, ticket, generation, and surface-room epoch",
                    "exit_condition": "stop at first lost_request hook or after 2400 emulator frames; no script acknowledgement",
                    "room_stage": stage1,
                    "hook_address": mismatch_address,
                    "hook": hit,
                    "emulator_frames_after_stage": frames,
                    "matches": expected,
                    "mismatches": [name for name, pair in expected.items()
                                   if pair[0] != pair[1]],
                    "pose": list(pose),
                    "provider": list(provider),
                    "surface_state": list(surface),
                    "cpu": session.get_cpu_state("Snes"),
                }
                (args.output / "provider-mismatch-trace.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True) + "\n")
                final.update({
                    "result": "FIRST_PROVIDER_MISMATCH_CAPTURED" if hit else "NO_PROVIDER_MISMATCH_OBSERVED",
                    "provider_mismatch_trace": "provider-mismatch-trace.json",
                    "diagnostic_frames": frames,
                })
                return 0 if hit else 2
            stage1 = observer.wait_stage(1, max_frames=6000)
            record1 = observer.capture_stage("01-standing", expected_frame=3,
                                             expected_facing=180)
            observer.acknowledge(1)

            stage2 = observer.wait_stage(2, max_frames=1800)
            record2 = observer.capture_stage("02-turned", expected_frame=3,
                                             expected_facing=90)
            require(record2["pose"]["accepted_direction"]
                    != record1["pose"]["accepted_direction"],
                    f"facing did not change: {record1['pose']} -> {record2['pose']}")
            observer.acknowledge(2)

            observer.wait_stage(3, max_frames=1800)
            anim1 = observer.capture_stage("03-animation-step-a", expected_frame=2)
            source_identity = {
                **anim1["pose"],
                "rom_sha256": final["rom_sha256"],
                "package_sha256": final["package_sha256"],
            }
            key1 = (anim1["pose"]["accepted_frame"], anim1["pose"]["accepted_step"])
            key2 = None
            end = observer.logical_frames + 3600
            while observer.logical_frames < end:
                observer.advance(POLL_FRAMES)
                state = observer.wait_presented_pose(max_frames=600,
                                                     expected_frame=2)
                key = (state["accepted_frame"], state["accepted_step"])
                current_identity = {
                    **state,
                    "rom_sha256": final["rom_sha256"],
                    "package_sha256": final["package_sha256"],
                }
                if key != key1 and same_room_costume_source(
                        source_identity, current_identity):
                    key2 = key
                    anim2 = observer.capture_stage("03-animation-step-b")
                    break
            require(key2 is not None,
                    f"animation did not produce a second completed pose key; first={key1} last={observer.last_state}")
            observer.acknowledge(3)

            observer.wait_stage(4, max_frames=1800)
            moved = observer.capture_stage("04-moved-restored", expected_frame=3,
                                           expected_facing=90)
            require(moved["pose"]["foot_screen"][0]
                    != record1["pose"]["foot_screen"][0],
                    "actor did not move to a changed screen position")
            old = record1["pose"]["actor_bounds_screen_from_pose"]
            new = moved["pose"]["actor_bounds_screen_from_pose"]
            require(old is not None and new is not None,
                    "old/new actor damage bounds are absent")
            old_only = 0
            pixels = (args.output / "04-moved-restored.indexed.bin").read_bytes()
            for y in range(old[1], old[3]):
                for x in range(old[0], old[2]):
                    if new[0] <= x < new[2] and new[1] <= y < new[3]:
                        continue
                    index = y * 256 + x
                    if pixels[index] != backdrop[index]:
                        old_only += 1
            require(old_only <= 8,
                    f"old actor pixels were not restored after movement: {old_only} residual pixels")
            observer.acknowledge(4)
            stage5 = observer.wait_stage(5, max_frames=600)
            final.update({
                "result": "PASS_SYNTHETIC_ACTOR_VISUAL_DIAGNOSTIC",
                "logical_frames": observer.logical_frames,
                "activation": stage5["activation"],
                "locals_base": observer.locals,
                "stages": {"standing": stage1, "turned": stage2,
                           "animation_first_key": list(key1),
                           "animation_second_key": list(key2), "moved": stage5},
                "captures": observer.captures,
                "old_position_residual_pixels": old_only,
                "diagnostic_source": audit.get("boot_identity"),
                "screen_surface": "SA-1 BW-RAM indexed 256x224 at $40:2000",
                "ppu_ack_address": SURFACE_PRESENTED_GENERATION,
        "private_display": display,
            })
            (args.output / "actor-visual-observations.json").write_text(
                json.dumps(final, indent=2, sort_keys=True) + "\n")
    except Exception as exc:
        final["result"] = "FAIL_OR_NOT_VERIFIED"
        final["error"] = f"{type(exc).__name__}: {exc}"
        if observer is not None:
            final["last_vm_state"] = observer.last_state
            final["logical_frames"] = observer.logical_frames
            final["captures"] = observer.captures
        (args.output / "actor-visual-observations.json").write_text(
            json.dumps(final, indent=2, sort_keys=True) + "\n")
        raise
    finally:
        final["elapsed_seconds"] = round(time.monotonic() - started, 3)
        final["finalized_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        (args.output / "validator-finalization.json").write_text(
            json.dumps(final, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
