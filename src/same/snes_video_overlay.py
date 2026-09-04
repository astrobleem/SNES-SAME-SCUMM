"""Reference contract for the bounded target-neutral subtitle overlay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


OVERLAY_WIDTH = 80
OVERLAY_HEIGHT = 8
OVERLAY_PIXELS = OVERLAY_WIDTH * OVERLAY_HEIGHT
BLANK_TILE = 64
FIRST_DYNAMIC_TILE = 65
LAST_DYNAMIC_TILE = 191
SET_LAYER_ID = 1
SET_LAYER_HIDE = 0
SET_LAYER_SHOW_OR_REPLACE = 1


@dataclass(frozen=True, slots=True)
class SetLayerPacket:
    generation: int
    operation: int
    layer_id: int = SET_LAYER_ID

    @property
    def arg0(self) -> int:
        return self.generation

    @property
    def arg1(self) -> int:
        return self.layer_id | self.operation << 8

    @classmethod
    def unpack(cls, arg0: int, arg1: int) -> "SetLayerPacket":
        if arg0 <= 0 or arg0 > 0xFFFFFFFF or arg1 >> 16:
            raise ValueError("invalid SET_LAYER packet")
        result = cls(arg0, arg1 >> 8 & 0xFF, arg1 & 0xFF)
        if result.layer_id != SET_LAYER_ID or result.operation not in (0, 1):
            raise ValueError("invalid SET_LAYER operation")
        return result


@dataclass(frozen=True, slots=True)
class OverlayCell:
    screen_tile: int
    character: int
    palette_group: int
    planar: bytes


def encode_4bpp_tile(rows: Iterable[Iterable[int]]) -> bytes:
    matrix = tuple(tuple(row) for row in rows)
    if len(matrix) != 8 or any(len(row) != 8 for row in matrix):
        raise ValueError("4bpp tile must be 8x8")
    output = bytearray(32)
    for y, row in enumerate(matrix):
        for x, pixel in enumerate(row):
            if not 0 <= pixel <= 15:
                raise ValueError("4bpp pixel is outside 0..15")
            bit = 0x80 >> x
            for plane in range(4):
                if pixel & 1 << plane:
                    output[(plane // 2) * 16 + y * 2 + plane % 2] |= bit
    return bytes(output)


def decode_4bpp_tile(data: bytes) -> tuple[tuple[int, ...], ...]:
    """Independently reconstruct one SNES 4bpp character."""
    if len(data) != 32:
        raise ValueError("4bpp tile must contain 32 bytes")
    rows: list[tuple[int, ...]] = []
    for y in range(8):
        row = []
        for x in range(8):
            bit = 0x80 >> x
            row.append(sum(
                (1 << plane) if data[(plane // 2) * 16 + y * 2 + plane % 2] & bit else 0
                for plane in range(4)
            ))
        rows.append(tuple(row))
    return tuple(rows)


def decode_bg2_mask(characters: bytes, tilemap: bytes) -> bytes:
    """Decode the visible 256x224 BG2 plane to a binary INDEX8 mask."""
    if len(characters) != 0x1800 or len(tilemap) != 0x800:
        raise ValueError("invalid Phase-6G BG2 VRAM images")
    output = bytearray(256 * 224)
    for ty in range(28):
        for tx in range(32):
            entry = int.from_bytes(tilemap[(ty * 32 + tx) * 2:][:2], "little")
            character = entry & 0x3FF
            if character == BLANK_TILE:
                continue
            offset = (character - BLANK_TILE) * 32
            if offset < 0 or offset + 32 > len(characters):
                raise ValueError("BG2 tilemap references outside overlay characters")
            rows = decode_4bpp_tile(characters[offset:offset + 32])
            for y, row in enumerate(rows):
                for x, value in enumerate(row):
                    output[(ty * 8 + y) * 256 + tx * 8 + x] = 1 if value else 0
    return bytes(output)


def realize_overlay(pixels: bytes, *, width: int, height: int, pitch: int,
                    x: int, y: int, transparent: int = 0) -> tuple[OverlayCell, ...]:
    if not 0 < width <= OVERLAY_WIDTH or not 0 < height <= OVERLAY_HEIGHT or pitch < width or len(pixels) < pitch * height:
        raise ValueError("invalid overlay surface")
    touched: dict[int, list[list[int]]] = {}
    groups: dict[int, int] = {}
    for sy in range(height):
        py = y + sy
        if not 0 <= py < 224: continue
        for sx in range(width):
            px = x + sx
            if not 0 <= px < 256: continue
            value = pixels[sy * pitch + sx]
            if value == transparent: continue
            local = value & 15
            if local == 0: raise ValueError("nontransparent overlay index has local color zero")
            tile = py // 8 * 32 + px // 8
            group = value >> 4
            if tile in groups and groups[tile] != group:
                raise ValueError("overlay tile mixes palette groups")
            groups[tile] = group
            matrix = touched.setdefault(tile, [[0] * 8 for _ in range(8)])
            matrix[py & 7][px & 7] = local
    if len(touched) > LAST_DYNAMIC_TILE - FIRST_DYNAMIC_TILE + 1:
        raise ValueError("overlay exceeds dynamic character capacity")
    return tuple(OverlayCell(tile, FIRST_DYNAMIC_TILE + index, groups[tile], encode_4bpp_tile(touched[tile]))
                 for index, tile in enumerate(sorted(touched)))
