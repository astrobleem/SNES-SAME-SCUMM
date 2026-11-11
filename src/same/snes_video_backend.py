"""Build-time and reference contract for SAME's selectable SNES video backend."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .snes_carrier import parse_address
from .snes_surface import (
    CGRAM_BYTES,
    DMA_DESCRIPTOR_LIMIT,
    DMA_FRAME_BUDGET,
    PaletteRange,
    TileRun,
    TILE_BYTES,
    VISIBLE_TILE_COUNT,
    build_static_tilemap,
    build_tile_runs,
)
from .video import Rect


@dataclass(frozen=True, slots=True)
class BackendRegion:
    name: str
    address: int
    size: int

    @property
    def end(self) -> int:
        return self.address + self.size


@dataclass(frozen=True, slots=True)
class VideoBackendDescription:
    name: str
    backend_id: int
    required_carrier: str | None
    layout: dict[str, Any] | None
    config_sha256: str
    layout_sha256: str | None


@dataclass(frozen=True, slots=True)
class Mode3DmaBatch:
    palette_ranges: tuple[PaletteRange, ...] = ()
    tile_runs: tuple[TileRun, ...] = ()

    @property
    def byte_length(self) -> int:
        return sum(item.byte_length for item in self.palette_ranges) + sum(
            item.byte_length for item in self.tile_runs
        )


@dataclass(frozen=True, slots=True)
class SurfaceDirtyPacket:
    x: int
    y: int
    width: int
    height: int

    @property
    def arg0(self) -> int:
        return self.x | self.y << 16

    @property
    def arg1(self) -> int:
        return self.width | self.height << 16

    @classmethod
    def unpack(cls, arg0: int, arg1: int) -> "SurfaceDirtyPacket":
        return cls(arg0 & 0xFFFF, arg0 >> 16 & 0xFFFF, arg1 & 0xFFFF, arg1 >> 16 & 0xFFFF)

    def clipped(self) -> Rect | None:
        if self.width == 0 or self.height == 0:
            raise ValueError("SURFACE_DIRTY width and height must be nonzero")
        return Rect(self.x, self.y, self.width, self.height).clipped(256, 224)


@dataclass(frozen=True, slots=True)
class PaletteWritePacket:
    first: int
    count: int

    @property
    def arg0(self) -> int:
        return self.first | self.count << 16

    def validate(self, arg1: int = 0) -> None:
        if arg1 != 0 or self.count <= 0 or self.first >= 256 or self.first + self.count > 256:
            raise ValueError("invalid PALETTE_WRITE range")


def validate_present(generation: int, arg1: int, committed: int, idle: bool) -> None:
    if generation <= 0 or generation <= committed or arg1 != 0 or not idle:
        raise ValueError("invalid PRESENT request")


def default_video_backend(root: Path) -> str:
    config = json.loads((root / "runtime/snes/video_backends.json").read_text(encoding="utf-8"))
    if config.get("default") != "legacy_backdrop":
        raise ValueError("legacy_backdrop must remain the default video backend")
    return "legacy_backdrop"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate_mode3_layout(layout: dict[str, Any]) -> tuple[BackendRegion, ...]:
    if layout.get("format") != "same-snes-mode3-backend-layout" or layout.get("version") != 1:
        raise ValueError("unsupported Mode-3 backend layout")
    if parse_address(layout["staging_address"]) != 0x41E200 or layout.get("staging_bytes") != 0x1E00:
        raise ValueError("Mode-3 staging range differs from Phase 6C")
    expected = {
        "live_palette": (0x41E200, 0x0300),
        "candidate_tiles": (0x41E500, 0x0073),
        "pending_tiles": (0x41E573, 0x0073),
        "inflight_tiles": (0x41E5E6, 0x0073),
        "candidate_palette": (0x41E65A, 0x0020),
        "pending_palette": (0x41E67A, 0x0020),
        "inflight_palette": (0x41E69A, 0x0020),
        "tile_scratch": (0x41E6BA, 0x0040),
        "inflight_records": (0x41E6FA, 0x0040),
        "scroll_hdma": (0x41E73A, 10),
        "work": (0x41E750, 0x00B0),
        "fixture": (0x41E800, 0x0800),
        "reserved": (0x41F000, 0x1000),
    }
    regions = []
    for name, (address, size) in expected.items():
        record = layout.get(name)
        if not isinstance(record, dict) or (parse_address(record["address"]), record.get("bytes")) != (address, size):
            raise ValueError(f"Mode-3 region {name} differs")
        regions.append(BackendRegion(name, address, size))
    work_allocations = layout["work"].get("allocations", {})
    for name, offset, size, owner in (
            ("backend_scratch", 0, 36, "Mode-3 backend scratch"),
            ("actor_explicit_animation", 36, 4, "generic SCUMM actor animation state")):
        if work_allocations.get(name) != {"offset": offset, "bytes": size, "owner": owner}:
            raise ValueError(f"Mode-3 {name} suballocation differs")
    pose_state = work_allocations.get("actor_pose_state")
    if pose_state != {
            "offset": 48,
            "bytes": 128,
            "owner": "generic SCUMM actor renderer",
    }:
        raise ValueError("Mode-3 actor pose state suballocation differs")
    if pose_state["offset"] < 0x24 or pose_state["offset"] + pose_state["bytes"] > layout["work"]["bytes"]:
        raise ValueError("Mode-3 actor pose state overlaps work fields or exceeds its owner")
    ordered = tuple(sorted(regions, key=lambda item: item.address))
    for left, right in zip(ordered, ordered[1:]):
        if left.end > right.address:
            raise ValueError(f"Mode-3 regions overlap: {left.name}, {right.name}")
    if ordered[0].address != 0x41E200 or ordered[-1].end != 0x420000:
        raise ValueError("Mode-3 regions do not cover the accepted staging range")
    retained = layout.get("retained_viewport", {})
    if retained != {"scene_height":192, "visible_columns":32, "physical_columns":33,
                    "guard_tiles":24, "vram_character_end":58880,
                    "vram_tilemap_start":61440, "vram_tilemap_bytes":4096,
                    "hdma_channel":6, "hud_scroll_x":0}:
        raise ValueError("retained viewport VRAM/HDMA ownership differs")
    if retained["vram_character_end"] > retained["vram_tilemap_start"]:
        raise ValueError("retained characters overlap tilemap")
    if retained["vram_tilemap_start"] + retained["vram_tilemap_bytes"] != 65536:
        raise ValueError("retained viewport escapes physical VRAM")
    if layout["inflight_records"].get("record_bytes") != 8:
        raise ValueError("inflight records must contain only their four used words")
    if layout.get("active_convert_tile_budget") != 4:
        raise ValueError("active conversion budget differs")
    if layout.get("dma_byte_budget") != DMA_FRAME_BUDGET or layout.get("dma_descriptor_limit") != DMA_DESCRIPTOR_LIMIT:
        raise ValueError("Mode-3 DMA limits differ from the kernel")
    return ordered


def load_video_backend(root: Path, name: str, *, carrier: str) -> VideoBackendDescription:
    config_path = root / "runtime/snes/video_backends.json"
    raw = config_path.read_bytes()
    config = json.loads(raw)
    if config.get("format") != "same-snes-video-backends" or config.get("version") != 1:
        raise ValueError("unsupported SNES video-backend schema")
    record = config.get("backends", {}).get(name)
    if not isinstance(record, dict):
        raise ValueError(f"unknown SNES video backend {name!r}")
    required = record.get("required_carrier")
    if required is not None and carrier != required:
        raise ValueError(f"video backend {name} requires carrier {required}")
    layout = None
    layout_hash = None
    if record.get("layout") is not None:
        layout_path = root / record["layout"]
        layout_raw = layout_path.read_bytes()
        layout = json.loads(layout_raw)
        validate_mode3_layout(layout)
        layout_hash = _sha(layout_raw)
    return VideoBackendDescription(
        name=name,
        backend_id=int(record["id"]),
        required_carrier=required,
        layout=layout,
        config_sha256=_sha(raw),
        layout_sha256=layout_hash,
    )


def combined_dma_plan(
    palette_ranges: Iterable[PaletteRange],
    tiles: Iterable[int],
    *,
    byte_budget: int = DMA_FRAME_BUDGET,
    descriptor_limit: int = DMA_DESCRIPTOR_LIMIT,
) -> tuple[tuple[PaletteRange, ...], tuple[object, ...], tuple[int, ...]]:
    """Palette-first deterministic batch; unscheduled tiles remain pending."""

    selected_palette: list[PaletteRange] = []
    bytes_used = 0
    descriptors = 0
    for item in palette_ranges:
        if descriptors >= descriptor_limit or bytes_used + item.byte_length > byte_budget:
            break
        selected_palette.append(item)
        bytes_used += item.byte_length
        descriptors += 1
    ordered_tiles = tuple(sorted(set(tiles)))
    tile_limit = (byte_budget - bytes_used) // TILE_BYTES
    selected_tiles: list[int] = []
    runs = []
    for tile in ordered_tiles:
        if not 0 <= tile < VISIBLE_TILE_COUNT or len(selected_tiles) >= tile_limit:
            break
        starts = not selected_tiles or tile != selected_tiles[-1] + 1
        if starts and descriptors + len(runs) >= descriptor_limit:
            break
        selected_tiles.append(tile)
        runs = list(build_tile_runs(selected_tiles))
    return tuple(selected_palette), tuple(runs), ordered_tiles[len(selected_tiles) :]


def mode3_dma_batches(
    palette_ranges: Iterable[PaletteRange],
    tiles: Iterable[int],
) -> tuple[Mode3DmaBatch, ...]:
    """Mirror the production palette-first, bounded, non-dropping planner."""

    batches: list[Mode3DmaBatch] = []
    remaining_palette = list(palette_ranges)
    while remaining_palette:
        selected: list[PaletteRange] = []
        byte_length = 0
        while remaining_palette and len(selected) < DMA_DESCRIPTOR_LIMIT:
            item = remaining_palette[0]
            if item.byte_length > DMA_FRAME_BUDGET:
                raise ValueError("palette range exceeds one DMA batch")
            if byte_length + item.byte_length > DMA_FRAME_BUDGET:
                break
            selected.append(remaining_palette.pop(0))
            byte_length += item.byte_length
        batches.append(Mode3DmaBatch(palette_ranges=tuple(selected)))

    remaining_tiles = tuple(sorted(set(tiles)))
    while remaining_tiles:
        _, runs, pending = combined_dma_plan((), remaining_tiles)
        if not runs:
            raise ValueError("tile work cannot fit in a bounded DMA batch")
        batches.append(Mode3DmaBatch(tile_runs=tuple(runs)))
        remaining_tiles = pending
    return tuple(batches)


def mode3_static_tilemap() -> bytes:
    return build_static_tilemap()


def mode3_retained_tilemap() -> bytes:
    """Two SNES screen maps; the initial 32-column scene retains legacy IDs.

    The second map starts with the guard column. Unused entries are not
    visible until the NMI-owned column/scroll transaction installs them.
    """
    result = bytearray(4096)
    result[:2048] = build_static_tilemap()
    for row in range(24):
        off = 2048 + row * 64
        result[off:off + 2] = (896 + row).to_bytes(2, "little")
    return bytes(result)


@dataclass(frozen=True, slots=True)
class RetainedCameraStep:
    """Immutable backend work ticket; source coordinates are pixel coordinates.

    A 33-column ring has one spare column only at tile-aligned positions.
    Stop at an alignment boundary before reusing it. This prevents DMA into
    a column still sampled by the old, sub-tile-scrolled display.
    """
    epoch: int
    generation: int
    previous_x: int
    source_x: int
    columns: tuple[int, ...]
    base_x: int = 0

    @property
    def hofs(self) -> int:
        return (self.source_x - self.base_x) & 511

    @property
    def character_bytes(self) -> int:
        return len(self.columns) * 24 * 64


def retained_scene_tile(column: int, row: int, *, base_column: int = 0) -> int:
    if not 0 <= row < 24:
        raise ValueError("retained scene row outside 192-pixel viewport")
    physical_column = (column - base_column) % 33
    return row * 32 + physical_column if physical_column < 32 else 896 + row


def retained_map_offset(column: int, row: int) -> int:
    """Byte offset in SNES 64x32 tilemap (two adjacent 32x32 screens)."""
    if not 0 <= row < 32:
        raise ValueError("tilemap row outside 32-row map")
    column &= 63
    return (column // 32) * 2048 + (row * 32 + column % 32) * 2


def retained_scroll_hdma(hofs: int) -> bytes:
    """Mode-2 writes the two HOFS latch bytes; fixed HUD begins at line192.

    Entries without bit7 write once and hold for the stated scanline count.
    The first192 lines scroll; the remaining32 display lines use HOFS0.
    """
    value = (hofs & 511).to_bytes(2, "little")
    return b'\x7f' + value + b'\x41' + value + b'\x20\0\0\0'


class RetainedCameraPlanner:
    """Reference for the existing Mode-3 backend's retained tile ownership.

    This class plans storage/commit transitions, not SCUMM camera semantics.
    It never changes the authored target, silently drops work, or certifies IO.
    Callers supply checked column bytes and a completed DMA fence separately.
    """
    def __init__(self, room_width: int, source_x: int = 0, *, epoch: int = 1):
        if room_width < 256 or source_x % 8 or not 0 <= source_x <= room_width - 256:
            raise ValueError("invalid source viewport")
        self.width = room_width
        self.x = source_x
        self.base_x = source_x
        self.epoch = epoch
        self.generation = 0
        self.tags: list[int | None] = [None] * 33
        for column in self.visible(source_x):
            self.tags[self.slot(column)] = column
        self.pending: RetainedCameraStep | None = None
        self.checked: set[int] = set()
        self.uploaded: set[int] = set()

    def slot(self, column: int) -> int:
        return (column - self.base_x // 8) % 33

    @staticmethod
    def visible(x: int) -> range:
        return range(x // 8, (x + 255) // 8 + 1)

    def request(self, target: int, generation: int) -> RetainedCameraStep:
        if self.pending is not None:
            raise RuntimeError("camera publication already owns the ring")
        if generation <= self.generation:
            raise ValueError("stale presentation generation")
        target = max(0, min(self.width - 256, target))
        if target > self.x:
            x = min(target, (self.x // 8 + 1) * 8)
        elif target < self.x:
            x = max(target, ((self.x - 1) // 8) * 8)
        else:
            x = self.x
        columns = tuple(c for c in self.visible(x) if self.tags[self.slot(c)] != c)
        old_slots = {self.slot(c) for c in self.visible(self.x)}
        if any(self.slot(c) in old_slots for c in columns):
            raise AssertionError("attempt to overwrite visible character data")
        ticket = RetainedCameraStep(self.epoch, generation, self.x, x, columns, self.base_x)
        self.pending, self.checked, self.uploaded = ticket, set(), set()
        return ticket

    def validate_column(self, ticket: RetainedCameraStep, column: int, pixels: bytes) -> None:
        self._ticket(ticket)
        if column not in ticket.columns or len(pixels) != 8 * 192:
            raise ValueError("wrong checked column identity or extent")
        self.checked.add(column)

    def dma_completed(self, ticket: RetainedCameraStep, column: int) -> None:
        self._ticket(ticket)
        if column not in self.checked:
            raise ValueError("unvalidated column cannot be published")
        self.uploaded.add(column)

    def commit(self, ticket: RetainedCameraStep) -> int:
        self._ticket(ticket)
        if set(ticket.columns) != self.uploaded:
            raise RuntimeError("column DMA is still pending")
        for column in ticket.columns:
            self.tags[self.slot(column)] = column
        self.x, self.generation, self.pending = ticket.source_x, ticket.generation, None
        return ticket.hofs

    def abort(self, ticket: RetainedCameraStep) -> None:
        self._ticket(ticket)
        # Uploaded guard bytes were not visible. Their prior tag is no longer
        # usable, even though the committed viewport and generation survive.
        for column in self.uploaded:
            self.tags[self.slot(column)] = None
        self.pending = None

    def _ticket(self, ticket: RetainedCameraStep) -> None:
        if ticket != self.pending or ticket.epoch != self.epoch:
            raise ValueError("stale camera work ticket")


def decode_retained_mode3(vram: bytes, *, hofs: int) -> bytes:
    """Decode the committed 64x32 Mode-3 map, including fixed lower HUD.

    Reads physical tile references/flip bits, not a reconstructed source map.
    The observer supplies the independently captured HDMA scroll table value.
    """
    from .snes_surface import decode_snes_8bpp_tile
    if len(vram) != 65536 or not 0 <= hofs <= 511:
        raise ValueError("invalid retained VRAM capture/scroll")
    tiles = {}
    pixels = bytearray()
    for y in range(224):
        for x in range(256):
            sx = x + (hofs if y < 192 else 0)
            offset = 0xf000 + retained_map_offset(sx // 8, y // 8)
            entry = int.from_bytes(vram[offset:offset+2], "little")
            tile = entry & 1023
            if tile >= 920:
                raise ValueError("visible tile references non-character VRAM")
            if tile not in tiles:
                tiles[tile] = decode_snes_8bpp_tile(vram[tile*64:tile*64+64])
            tx, ty = sx & 7, y & 7
            if entry & 0x4000: tx = 7 - tx
            if entry & 0x8000: ty = 7 - ty
            pixels.append(tiles[tile][ty][tx])
    return bytes(pixels)
