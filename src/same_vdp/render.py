from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PIL import Image

from .trace import TraceError
from .vdp import VDPState, cram_components

PaletteOutput = Literal["genesis", "snes"]


@dataclass(frozen=True)
class NameEntry:
    tile: int
    palette: int
    priority: int
    hflip: bool
    vflip: bool


def decode_name_entry(word: int) -> NameEntry:
    return NameEntry(
        tile=word & 0x07FF,
        hflip=bool(word & 0x0800),
        vflip=bool(word & 0x1000),
        palette=(word >> 13) & 0x03,
        priority=(word >> 15) & 0x01,
    )


def rgb3_to_rgb8(value: int) -> int:
    return round((value & 7) * 255 / 7)


def rgb3_to_snes5(value: int) -> int:
    return round((value & 7) * 31 / 7)


def snes5_to_rgb8(value: int) -> int:
    value &= 31
    return (value << 3) | (value >> 2)


def palette_rgb(state: VDPState, index: int, output: PaletteOutput) -> tuple[int, int, int]:
    red3, green3, blue3 = cram_components(state.cram[index & 0x3F])
    if output == "genesis":
        return rgb3_to_rgb8(red3), rgb3_to_rgb8(green3), rgb3_to_rgb8(blue3)
    if output == "snes":
        return (
            snes5_to_rgb8(rgb3_to_snes5(red3)),
            snes5_to_rgb8(rgb3_to_snes5(green3)),
            snes5_to_rgb8(rgb3_to_snes5(blue3)),
        )
    raise ValueError(f"unknown palette output {output!r}")


def tile_pixel(state: VDPState, tile: int, x: int, y: int) -> int:
    address = ((tile & 0x07FF) * 32 + (y & 7) * 4 + ((x & 7) >> 1)) & 0xFFFF
    packed = state.vram[address]
    return (packed >> 4) & 0x0F if not (x & 1) else packed & 0x0F


def _signed_scroll(word: int) -> int:
    # Mode-5 scroll values are 10-bit. Treating them modulo plane dimensions
    # is sufficient for the frame-static milestone.
    return word & 0x03FF


def full_screen_scroll(state: VDPState) -> tuple[int, int]:
    if (state.registers[11] & 0x03) != 0:
        raise TraceError("milestone 0 supports only full-screen horizontal scroll mode")
    base = state.hscroll_base
    horizontal_a = _signed_scroll(state.read_vram_word(base))
    vertical_a = state.vsram[0] & 0x03FF
    return horizontal_a, vertical_a


def render_plane_a(state: VDPState, output: PaletteOutput = "genesis") -> Image.Image:
    if not state.mode5:
        raise TraceError("Mode 5 is not enabled")
    width = state.width
    height = state.height
    image = Image.new("RGB", (width, height), palette_rgb(state, state.backdrop_index, output))
    if not state.display_enabled:
        return image

    plane_width, plane_height = state.plane_size
    horizontal_scroll, vertical_scroll = full_screen_scroll(state)
    pixels = image.load()
    base = state.plane_a_base

    for screen_y in range(height):
        source_y = (screen_y + vertical_scroll) % (plane_height * 8)
        tile_y, pixel_y = divmod(source_y, 8)
        for screen_x in range(width):
            # Positive Genesis H-scroll moves the plane right, so source lookup moves left.
            source_x = (screen_x - horizontal_scroll) % (plane_width * 8)
            tile_x, pixel_x = divmod(source_x, 8)
            entry_address = (base + ((tile_y * plane_width + tile_x) * 2)) & 0xFFFF
            entry = decode_name_entry(state.read_vram_word(entry_address))
            tx = 7 - pixel_x if entry.hflip else pixel_x
            ty = 7 - pixel_y if entry.vflip else pixel_y
            color = tile_pixel(state, entry.tile, tx, ty)
            if color == 0:
                continue
            pixels[screen_x, screen_y] = palette_rgb(state, entry.palette * 16 + color, output)
    return image
