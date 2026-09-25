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
        "candidate_tiles": (0x41E500, 0x0070),
        "pending_tiles": (0x41E570, 0x0070),
        "inflight_tiles": (0x41E5E0, 0x0070),
        "candidate_palette": (0x41E650, 0x0020),
        "pending_palette": (0x41E670, 0x0020),
        "inflight_palette": (0x41E690, 0x0020),
        "tile_scratch": (0x41E6B0, 0x0040),
        "inflight_records": (0x41E6F0, 0x0060),
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
    ordered = tuple(sorted(regions, key=lambda item: item.address))
    for left, right in zip(ordered, ordered[1:]):
        if left.end > right.address:
            raise ValueError(f"Mode-3 regions overlap: {left.name}, {right.name}")
    if ordered[0].address != 0x41E200 or ordered[-1].end != 0x420000:
        raise ValueError("Mode-3 regions do not cover the accepted staging range")
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
