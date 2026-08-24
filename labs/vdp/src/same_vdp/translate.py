from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .render import decode_name_entry, rgb3_to_snes5, tile_pixel
from .trace import TraceError
from .vdp import VDPState, cram_components


@dataclass(frozen=True)
class TranslationBundle:
    tiles: bytes
    tilemap: bytes
    cgram: bytes
    manifest: dict[str, object]


def encode_snes_tile(pixels: list[list[int]]) -> bytes:
    if len(pixels) != 8 or any(len(row) != 8 for row in pixels):
        raise ValueError("SNES tile must be 8x8")
    output = bytearray(32)
    for y, row in enumerate(pixels):
        planes = [0, 0, 0, 0]
        for x, color in enumerate(row):
            if not 0 <= color <= 15:
                raise ValueError("4bpp pixel must be 0..15")
            bit = 7 - x
            for plane in range(4):
                planes[plane] |= ((color >> plane) & 1) << bit
        output[y * 2] = planes[0]
        output[y * 2 + 1] = planes[1]
        output[16 + y * 2] = planes[2]
        output[16 + y * 2 + 1] = planes[3]
    return bytes(output)


def decode_snes_tile(data: bytes) -> list[list[int]]:
    if len(data) != 32:
        raise ValueError("SNES 4bpp tile must be exactly 32 bytes")
    pixels = [[0] * 8 for _ in range(8)]
    for y in range(8):
        planes = [data[y * 2], data[y * 2 + 1], data[16 + y * 2], data[16 + y * 2 + 1]]
        for x in range(8):
            bit = 7 - x
            pixels[y][x] = sum(((planes[plane] >> bit) & 1) << plane for plane in range(4))
    return pixels


def genesis_tile_pixels(state: VDPState, tile_index: int) -> list[list[int]]:
    return [[tile_pixel(state, tile_index, x, y) for x in range(8)] for y in range(8)]


def snes_color_word(internal_cram: int) -> int:
    red3, green3, blue3 = cram_components(internal_cram)
    red5 = rgb3_to_snes5(red3)
    green5 = rgb3_to_snes5(green3)
    blue5 = rgb3_to_snes5(blue3)
    return red5 | (green5 << 5) | (blue5 << 10)


def le16(words: Iterable[int]) -> bytes:
    output = bytearray()
    for word in words:
        output.extend((word & 0xFF, (word >> 8) & 0xFF))
    return bytes(output)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def translate_plane_a(state: VDPState, *, case_name: str) -> TranslationBundle:
    if state.width != 256 or state.height != 224:
        raise TraceError("SNES milestone 0 accepts only Genesis H32 256x224 output")
    if state.plane_size != (32, 32):
        raise TraceError("SNES milestone 0 accepts only a 32x32 Plane A")
    if (state.registers[11] & 0x07) != 0:
        raise TraceError("SNES milestone 0 accepts only full-screen H-scroll and full-plane V-scroll")
    horizontal_scroll = state.read_vram_word(state.hscroll_base) & 0x03FF
    vertical_scroll = state.vsram[0] & 0x03FF
    if horizontal_scroll or vertical_scroll:
        raise TraceError("SNES milestone 0 requires zero scroll; scroll translation is the next gate")

    plane_words: list[int] = []
    used_tiles: set[int] = set()
    for index in range(32 * 32):
        word = state.read_vram_word(state.plane_a_base + index * 2)
        plane_words.append(word)
        used_tiles.add(word & 0x07FF)

    ordered_tiles = sorted(used_tiles)
    if len(ordered_tiles) > 1024:
        raise TraceError("SNES BG supports at most 1024 tile indices")
    remap = {source: target for target, source in enumerate(ordered_tiles)}

    tile_bytes = bytearray()
    for source_index in ordered_tiles:
        tile_bytes.extend(encode_snes_tile(genesis_tile_pixels(state, source_index)))

    snes_map_words: list[int] = []
    for word in plane_words:
        entry = decode_name_entry(word)
        snes_word = remap[entry.tile]
        snes_word |= (entry.palette & 0x07) << 10
        snes_word |= (entry.priority & 1) << 13
        snes_word |= int(entry.hflip) << 14
        snes_word |= int(entry.vflip) << 15
        snes_map_words.append(snes_word)

    # BG color 0 is the SNES backdrop. Install the Genesis selected backdrop there.
    cgram_words = [snes_color_word(value) for value in state.cram]
    cgram_words[0] = snes_color_word(state.cram[state.backdrop_index])

    tilemap_bytes = le16(snes_map_words)
    cgram_bytes = le16(cgram_words)
    tiles = bytes(tile_bytes)

    manifest: dict[str, object] = {
        "format": "same-vdp-snes-bundle",
        "version": 1,
        "case": case_name,
        "source": {
            "width": state.width,
            "height": state.height,
            "plane_a_base": f"0x{state.plane_a_base:04x}",
            "plane_size": [32, 32],
            "backdrop_index": state.backdrop_index,
        },
        "snes": {
            "mode": 1,
            "bg": 1,
            "tile_vram_word": "0x0000",
            "map_vram_word": "0x6000",
            "bg1sc": "0x60",
            "bg12nba": "0x00",
            "tile_count": len(ordered_tiles),
            "source_tile_indices": ordered_tiles,
        },
        "assets": {
            "tiles.4bpp": {"bytes": len(tiles), "sha256": sha256(tiles)},
            "tilemap.bin": {"bytes": len(tilemap_bytes), "sha256": sha256(tilemap_bytes)},
            "palette.cgram": {"bytes": len(cgram_bytes), "sha256": sha256(cgram_bytes)},
        },
    }
    return TranslationBundle(tiles=tiles, tilemap=tilemap_bytes, cgram=cgram_bytes, manifest=manifest)


def write_bundle(bundle: TranslationBundle, destination: str | Path) -> Path:
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    (output / "tiles.4bpp").write_bytes(bundle.tiles)
    (output / "tilemap.bin").write_bytes(bundle.tilemap)
    (output / "palette.cgram").write_bytes(bundle.cgram)
    (output / "manifest.json").write_text(json.dumps(bundle.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    include = "\n".join(
        [
            "; Generated by SAME-VDP. Do not edit.",
            f"SAME_TILE_BYTES = {len(bundle.tiles)}",
            f"SAME_MAP_BYTES = {len(bundle.tilemap)}",
            f"SAME_CGRAM_BYTES = {len(bundle.cgram)}",
            "SAME_TILE_VRAM = $0000",
            "SAME_MAP_VRAM = $6000",
            "",
        ]
    )
    (output / "assets.inc.pasm").write_text(include, encoding="utf-8")
    return output


def render_bundle(bundle: TranslationBundle):
    """Render the emitted SNES assets, independently of the Genesis VDP model."""
    from PIL import Image
    from .render import snes5_to_rgb8

    if len(bundle.tilemap) != 2048:
        raise ValueError("milestone-0 SNES tilemap must be 2048 bytes")
    if len(bundle.cgram) < 128:
        raise ValueError("milestone-0 CGRAM must contain 64 colors")
    if len(bundle.tiles) % 32:
        raise ValueError("SNES tile data is not record-aligned")

    palette: list[tuple[int, int, int]] = []
    for index in range(0, 128, 2):
        word = bundle.cgram[index] | (bundle.cgram[index + 1] << 8)
        palette.append(
            (
                snes5_to_rgb8(word & 0x1F),
                snes5_to_rgb8((word >> 5) & 0x1F),
                snes5_to_rgb8((word >> 10) & 0x1F),
            )
        )

    decoded_tiles = [decode_snes_tile(bundle.tiles[index:index + 32]) for index in range(0, len(bundle.tiles), 32)]
    image = Image.new("RGB", (256, 224), palette[0])
    pixels = image.load()
    for y in range(224):
        map_y, pixel_y = divmod(y, 8)
        for x in range(256):
            map_x, pixel_x = divmod(x, 8)
            map_offset = (map_y * 32 + map_x) * 2
            entry = bundle.tilemap[map_offset] | (bundle.tilemap[map_offset + 1] << 8)
            tile_index = entry & 0x03FF
            palette_index = (entry >> 10) & 0x07
            hflip = bool(entry & 0x4000)
            vflip = bool(entry & 0x8000)
            if tile_index >= len(decoded_tiles):
                raise ValueError(f"tilemap references missing SNES tile {tile_index}")
            tx = 7 - pixel_x if hflip else pixel_x
            ty = 7 - pixel_y if vflip else pixel_y
            color = decoded_tiles[tile_index][ty][tx]
            if color:
                pixels[x, y] = palette[palette_index * 16 + color]
    return image


def read_bundle(source: str | Path) -> TranslationBundle:
    root = Path(source)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    return TranslationBundle(
        tiles=(root / "tiles.4bpp").read_bytes(),
        tilemap=(root / "tilemap.bin").read_bytes(),
        cgram=(root / "palette.cgram").read_bytes(),
        manifest=manifest,
    )
