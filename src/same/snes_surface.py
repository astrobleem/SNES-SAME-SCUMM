"""Reference realization of a 256x224 indexed surface for SNES Mode 3 BG1.

This module is deliberately host-only.  It defines no service-packet ABI and
does not activate a production SNES video backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .video import IndexedSurface, PixelFormat, Rect


SURFACE_WIDTH = 256
SURFACE_HEIGHT = 224
TILE_SIZE = 8
TILES_WIDE = 32
TILES_HIGH = 28
VISIBLE_TILE_COUNT = TILES_WIDE * TILES_HIGH
TILE_BYTES = 64
DMA_FRAME_BUDGET = 0x0800
DMA_DESCRIPTOR_LIMIT = 8
TILE_DATA_BYTES = VISIBLE_TILE_COUNT * TILE_BYTES
TILEMAP_BYTES = 32 * 32 * 2
CGRAM_BYTES = 256 * 2

TILE_VRAM_BYTE_ADDRESS = 0x0000
TILEMAP_VRAM_BYTE_ADDRESS = 0xE000
TILEMAP_VRAM_WORD_ADDRESS = TILEMAP_VRAM_BYTE_ADDRESS // 2
VRAM_BYTES_USED = TILE_DATA_BYTES + TILEMAP_BYTES
VRAM_BYTES_REMAINING = 0x10000 - VRAM_BYTES_USED

BGMODE = 0x03
BG1SC = 0x70
BG12NBA = 0x00
TM = 0x01
TS = 0x00


@dataclass(frozen=True, slots=True)
class SnesIndexedSurfaceBundle:
    tiles_8bpp: bytes
    tilemap: bytes
    cgram: bytes
    width: int = SURFACE_WIDTH
    height: int = SURFACE_HEIGHT
    tile_vram_byte_address: int = TILE_VRAM_BYTE_ADDRESS
    tilemap_vram_byte_address: int = TILEMAP_VRAM_BYTE_ADDRESS


@dataclass(frozen=True, slots=True)
class TileRun:
    first_tile: int
    tile_count: int

    @property
    def vram_byte_address(self) -> int:
        return self.first_tile * TILE_BYTES

    @property
    def byte_length(self) -> int:
        return self.tile_count * TILE_BYTES


@dataclass(frozen=True, slots=True)
class PaletteRange:
    first_color: int
    color_count: int

    @property
    def byte_offset(self) -> int:
        return self.first_color * 2

    @property
    def byte_length(self) -> int:
        return self.color_count * 2


@dataclass(frozen=True, slots=True)
class TileTransferPlan:
    """One bounded future NMI slice plus the work that must remain pending."""

    runs: tuple[TileRun, ...]
    scheduled_tiles: tuple[int, ...]
    pending_tiles: tuple[int, ...]

    @property
    def byte_length(self) -> int:
        return len(self.scheduled_tiles) * TILE_BYTES


def _validate_tile(pixels: Sequence[Sequence[int]]) -> None:
    if len(pixels) != TILE_SIZE or any(len(row) != TILE_SIZE for row in pixels):
        raise ValueError("SNES 8bpp tile must be exactly 8x8")
    if any(not isinstance(pixel, int) or not 0 <= pixel <= 0xFF for row in pixels for pixel in row):
        raise ValueError("SNES 8bpp pixels must be integers in 0..255")


def encode_snes_8bpp_tile(pixels: Sequence[Sequence[int]]) -> bytes:
    """Encode one indexed tile in SNES planes 0/1, 2/3, 4/5, 6/7 order."""

    _validate_tile(pixels)
    output = bytearray(TILE_BYTES)
    for y, row in enumerate(pixels):
        planes = [0] * 8
        for x, color in enumerate(row):
            bit = 7 - x
            for plane in range(8):
                planes[plane] |= ((color >> plane) & 1) << bit
        for pair in range(4):
            base = pair * 16 + y * 2
            output[base] = planes[pair * 2]
            output[base + 1] = planes[pair * 2 + 1]
    return bytes(output)


def decode_snes_8bpp_tile(data: bytes | bytearray | memoryview) -> list[list[int]]:
    """Independently decode one 64-byte SNES 8bpp character."""

    raw = bytes(data)
    if len(raw) != TILE_BYTES:
        raise ValueError("SNES 8bpp tile data must be exactly 64 bytes")
    result: list[list[int]] = []
    for y in range(TILE_SIZE):
        row: list[int] = []
        for x in range(TILE_SIZE):
            mask = 0x80 >> x
            value = 0
            for plane in range(8):
                pair = plane // 2
                plane_offset = pair * 16 + y * 2 + (plane & 1)
                if raw[plane_offset] & mask:
                    value |= 1 << plane
            row.append(value)
        result.append(row)
    return result


def rgb8_to_bgr555(red: int, green: int, blue: int) -> int:
    for component in (red, green, blue):
        if not isinstance(component, int) or not 0 <= component <= 0xFF:
            raise ValueError("RGB8 components must be integers in 0..255")
    return (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)


def bgr555_to_rgb8(word: int) -> tuple[int, int, int]:
    if not 0 <= word <= 0x7FFF:
        raise ValueError("BGR555 word must be in 0..0x7fff")

    def expand(value: int) -> int:
        return (value << 3) | (value >> 2)

    return (expand(word & 0x1F), expand((word >> 5) & 0x1F), expand((word >> 10) & 0x1F))


def encode_cgram(palette: Sequence[Sequence[int]]) -> bytes:
    if len(palette) != 256:
        raise ValueError("SNES indexed surface palette must contain 256 colors")
    result = bytearray(CGRAM_BYTES)
    for index, color in enumerate(palette):
        if len(color) != 3:
            raise ValueError("palette colors must contain exactly three components")
        word = rgb8_to_bgr555(color[0], color[1], color[2])
        result[index * 2] = word & 0xFF
        result[index * 2 + 1] = word >> 8
    return bytes(result)


def decode_cgram(cgram: bytes | bytearray | memoryview) -> tuple[tuple[int, int, int], ...]:
    raw = bytes(cgram)
    if len(raw) != CGRAM_BYTES:
        raise ValueError("SNES indexed surface CGRAM image must be exactly 512 bytes")
    return tuple(
        bgr555_to_rgb8(raw[offset] | (raw[offset + 1] << 8))
        for offset in range(0, CGRAM_BYTES, 2)
    )


def build_static_tilemap() -> bytes:
    result = bytearray(TILEMAP_BYTES)
    for tile_y in range(32):
        for tile_x in range(32):
            tile = tile_y * TILES_WIDE + tile_x if tile_y < TILES_HIGH else 0
            offset = (tile_y * 32 + tile_x) * 2
            result[offset] = tile & 0xFF
            result[offset + 1] = (tile >> 8) & 0x03
    return bytes(result)


def encode_surface_tiles(surface: IndexedSurface) -> bytes:
    if surface.format is not PixelFormat.INDEX8:
        raise ValueError("SNES surface realization accepts only indexed8")
    if (surface.width, surface.height) != (SURFACE_WIDTH, SURFACE_HEIGHT):
        raise ValueError("SNES surface realization requires exactly 256x224 pixels")
    output = bytearray(TILE_DATA_BYTES)
    cursor = 0
    for tile_y in range(TILES_HIGH):
        for tile_x in range(TILES_WIDE):
            pixels = [
                list(surface._visible_row(tile_y * 8 + row)[tile_x * 8 : tile_x * 8 + 8])
                for row in range(8)
            ]
            output[cursor : cursor + TILE_BYTES] = encode_snes_8bpp_tile(pixels)
            cursor += TILE_BYTES
    return bytes(output)


def realize_indexed_surface(surface: IndexedSurface) -> SnesIndexedSurfaceBundle:
    return SnesIndexedSurfaceBundle(
        tiles_8bpp=encode_surface_tiles(surface),
        tilemap=build_static_tilemap(),
        cgram=encode_cgram(surface.palette),
    )


def decode_bundle_indexed(bundle: SnesIndexedSurfaceBundle) -> bytes:
    """Decode only the emitted byte assets, not encoder intermediates."""

    if len(bundle.tiles_8bpp) != TILE_DATA_BYTES:
        raise ValueError("SNES surface bundle must contain exactly 57344 tile bytes")
    if len(bundle.tilemap) != TILEMAP_BYTES:
        raise ValueError("SNES surface bundle must contain exactly 2048 tilemap bytes")
    decoded_tiles = [
        decode_snes_8bpp_tile(bundle.tiles_8bpp[offset : offset + TILE_BYTES])
        for offset in range(0, TILE_DATA_BYTES, TILE_BYTES)
    ]
    pixels = bytearray(SURFACE_WIDTH * SURFACE_HEIGHT)
    for y in range(SURFACE_HEIGHT):
        tile_y, pixel_y = divmod(y, 8)
        for x in range(SURFACE_WIDTH):
            tile_x, pixel_x = divmod(x, 8)
            map_offset = (tile_y * 32 + tile_x) * 2
            entry = bundle.tilemap[map_offset] | (bundle.tilemap[map_offset + 1] << 8)
            tile = entry & 0x03FF
            if tile >= len(decoded_tiles):
                raise ValueError(f"tilemap references unavailable tile {tile}")
            tx = 7 - pixel_x if entry & 0x4000 else pixel_x
            ty = 7 - pixel_y if entry & 0x8000 else pixel_y
            pixels[y * SURFACE_WIDTH + x] = decoded_tiles[tile][ty][tx]
    return bytes(pixels)


def candidate_tiles(rectangles: Iterable[Rect]) -> tuple[int, ...]:
    """Translate clipped display rectangles into stable row-major tile IDs."""

    seen: set[int] = set()
    result: list[int] = []
    for rectangle in rectangles:
        clipped = rectangle.clipped(SURFACE_WIDTH, SURFACE_HEIGHT)
        if clipped is None:
            continue
        x0 = clipped.x // 8
        y0 = clipped.y // 8
        x1 = (clipped.right - 1) // 8
        y1 = (clipped.bottom - 1) // 8
        for tile_y in range(y0, y1 + 1):
            for tile_x in range(x0, x1 + 1):
                tile = tile_y * TILES_WIDE + tile_x
                if tile not in seen:
                    seen.add(tile)
                    result.append(tile)
    return tuple(result)


def changed_tiles(
    current_tiles: bytes,
    committed_tiles: bytes,
    candidates: Iterable[int],
) -> tuple[int, ...]:
    if len(current_tiles) != TILE_DATA_BYTES or len(committed_tiles) != TILE_DATA_BYTES:
        raise ValueError("tile shadows must each contain exactly 57344 bytes")
    result: list[int] = []
    for tile in candidates:
        if not 0 <= tile < VISIBLE_TILE_COUNT:
            raise ValueError(f"candidate tile {tile} is outside the visible surface")
        start = tile * TILE_BYTES
        if current_tiles[start : start + TILE_BYTES] != committed_tiles[start : start + TILE_BYTES]:
            result.append(tile)
    return tuple(result)


def build_tile_runs(tiles: Iterable[int]) -> tuple[TileRun, ...]:
    ordered = sorted(set(tiles))
    if any(not 0 <= tile < VISIBLE_TILE_COUNT for tile in ordered):
        raise ValueError("tile run contains an out-of-range tile")
    if not ordered:
        return ()
    runs: list[TileRun] = []
    first = previous = ordered[0]
    for tile in ordered[1:]:
        if tile != previous + 1:
            runs.append(TileRun(first, previous - first + 1))
            first = tile
        previous = tile
    runs.append(TileRun(first, previous - first + 1))
    return tuple(runs)


def plan_tile_transfers(
    tiles: Iterable[int],
    *,
    byte_budget: int = DMA_FRAME_BUDGET,
    descriptor_limit: int = DMA_DESCRIPTOR_LIMIT,
) -> TileTransferPlan:
    """Partition fixed-slot tile work without dropping over-budget updates.

    This is a reference policy only; it does not enqueue production DMA.  Tiles
    are scheduled in deterministic VRAM order.  Any work that cannot fit both
    limits is returned verbatim as pending work for a later commit.
    """

    ordered = tuple(sorted(set(tiles)))
    if any(not 0 <= tile < VISIBLE_TILE_COUNT for tile in ordered):
        raise ValueError("tile transfer contains an out-of-range tile")
    if byte_budget < 0:
        raise ValueError("DMA byte budget must be non-negative")
    if descriptor_limit < 0:
        raise ValueError("DMA descriptor limit must be non-negative")

    tile_budget = byte_budget // TILE_BYTES
    scheduled: list[int] = []
    run_count = 0
    previous: int | None = None
    for tile in ordered:
        starts_run = previous is None or tile != previous + 1
        if len(scheduled) >= tile_budget or (starts_run and run_count >= descriptor_limit):
            break
        if starts_run:
            run_count += 1
        scheduled.append(tile)
        previous = tile
    scheduled_tuple = tuple(scheduled)
    return TileTransferPlan(
        runs=build_tile_runs(scheduled_tuple),
        scheduled_tiles=scheduled_tuple,
        pending_tiles=ordered[len(scheduled_tuple) :],
    )


def changed_palette_ranges(current: bytes, committed: bytes) -> tuple[PaletteRange, ...]:
    if len(current) != CGRAM_BYTES or len(committed) != CGRAM_BYTES:
        raise ValueError("CGRAM shadows must each contain exactly 512 bytes")
    changed = [
        index
        for index in range(256)
        if current[index * 2 : index * 2 + 2] != committed[index * 2 : index * 2 + 2]
    ]
    if not changed:
        return ()
    ranges: list[PaletteRange] = []
    first = previous = changed[0]
    for color in changed[1:]:
        if color != previous + 1:
            ranges.append(PaletteRange(first, previous - first + 1))
            first = color
        previous = color
    ranges.append(PaletteRange(first, previous - first + 1))
    return tuple(ranges)
