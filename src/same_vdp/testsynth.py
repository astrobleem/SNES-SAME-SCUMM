from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .trace import TRACE_MAGIC, TRACE_VERSION, write_trace
from .vdp import CRAM_WRITE, VRAM_WRITE, command_words, cram_bus_word, register_word, words_from_bytes


@dataclass
class TraceBuilder:
    name: str
    events: list[dict[str, object]]

    @classmethod
    def begin(cls, name: str) -> "TraceBuilder":
        builder = cls(name=name, events=[])
        builder.comment("Mode-5 H32 synthetic workload; no foreign CPU required")
        # Enter Mode 5 with display disabled before issuing two-word commands.
        builder.ctrl(register_word(1, 0x04))
        builder.ctrl(register_word(2, 0x30))   # Plane A at VRAM 0xc000
        builder.ctrl(register_word(4, 0x07))   # Plane B at VRAM 0xe000
        builder.ctrl(register_word(7, 0x00))   # Backdrop CRAM index 0
        builder.ctrl(register_word(11, 0x00))  # Full-screen H, full-plane V scroll
        builder.ctrl(register_word(12, 0x00))  # H32, no shadow/highlight
        builder.ctrl(register_word(13, 0x3C))  # H-scroll table at VRAM 0xf000
        builder.ctrl(register_word(15, 0x02))  # Auto-increment two bytes
        builder.ctrl(register_word(16, 0x00))  # 32x32 planes
        return builder

    def comment(self, text: str) -> None:
        self.events.append({"op": "comment", "text": text})

    def ctrl(self, value: int) -> None:
        self.events.append({"op": "ctrl", "value": f"0x{value:04x}"})

    def data_words(self, values: list[int]) -> None:
        self.events.append({"op": "data_words", "values": [f"0x{value:04x}" for value in values]})

    def upload(self, address: int, code: int, values: list[int]) -> None:
        first, second = command_words(address, code)
        self.ctrl(first)
        self.ctrl(second)
        self.data_words(values)

    def finish(self) -> None:
        self.ctrl(register_word(1, 0x44))  # Mode 5 + display enabled
        self.events.append({"op": "frame", "label": "frame0000"})


def flatten_tile(pixels: list[list[int]]) -> bytes:
    if len(pixels) != 8 or any(len(row) != 8 for row in pixels):
        raise ValueError("Genesis tile must be 8x8")
    output = bytearray()
    for row in pixels:
        for x in range(0, 8, 2):
            output.append(((row[x] & 0x0F) << 4) | (row[x + 1] & 0x0F))
    return bytes(output)


def palette_words(colors: dict[int, tuple[int, int, int]]) -> list[int]:
    result = [0] * 64
    for index, (red, green, blue) in colors.items():
        result[index] = cram_bus_word(red, green, blue)
    return result


def map_word(tile: int, *, palette: int = 0, hflip: bool = False, vflip: bool = False, priority: int = 0) -> int:
    return (
        (tile & 0x07FF)
        | (int(hflip) << 11)
        | (int(vflip) << 12)
        | ((palette & 0x03) << 13)
        | ((priority & 1) << 15)
    )


def blank_map(fill: int = 0) -> list[int]:
    return [fill] * (32 * 32)


def common_upload(builder: TraceBuilder, colors: dict[int, tuple[int, int, int]], tiles: list[list[list[int]]], tilemap: list[int]) -> None:
    builder.upload(0x0000, CRAM_WRITE, palette_words(colors))
    tile_bytes = b"".join(flatten_tile(tile) for tile in tiles)
    builder.upload(0x0000, VRAM_WRITE, words_from_bytes(tile_bytes))
    builder.upload(0xC000, VRAM_WRITE, tilemap)
    # Explicit zero scroll values at the configured table and in VSRAM's reset state.
    builder.upload(0xF000, VRAM_WRITE, [0x0000, 0x0000])


def case_01() -> TraceBuilder:
    builder = TraceBuilder.begin("01_solid_palette")
    colors = {0: (0, 0, 0), 1: (7, 0, 7)}
    tile = [[1] * 8 for _ in range(8)]
    common_upload(builder, colors, [tile], blank_map(map_word(0)))
    builder.finish()
    return builder


def case_02() -> TraceBuilder:
    builder = TraceBuilder.begin("02_single_tile")
    colors = {0: (0, 0, 1), 1: (7, 7, 0), 2: (0, 7, 7), 3: (7, 0, 0)}
    blank = [[0] * 8 for _ in range(8)]
    glyph: list[list[int]] = []
    for y in range(8):
        row: list[int] = []
        for x in range(8):
            if x in (0, 7) or y in (0, 7):
                row.append(1)
            elif x == y:
                row.append(3)
            elif x + y == 7:
                row.append(2)
            else:
                row.append(0)
        glyph.append(row)
    tilemap = blank_map(map_word(0))
    tilemap[13 * 32 + 15] = map_word(1)
    common_upload(builder, colors, [blank, glyph], tilemap)
    builder.finish()
    return builder


def case_03() -> TraceBuilder:
    builder = TraceBuilder.begin("03_tile_flip")
    colors = {0: (0, 0, 0), 1: (7, 2, 0), 2: (0, 7, 2), 3: (2, 0, 7)}
    blank = [[0] * 8 for _ in range(8)]
    asymmetric = [[0] * 8 for _ in range(8)]
    for y in range(8):
        for x in range(8):
            if x <= y // 2:
                asymmetric[y][x] = 1
            if x == 6 and y < 5:
                asymmetric[y][x] = 2
            if y == 6 and 2 <= x <= 5:
                asymmetric[y][x] = 3
    tilemap = blank_map(map_word(0))
    placements = [
        (12, 12, False, False),
        (17, 12, True, False),
        (12, 16, False, True),
        (17, 16, True, True),
    ]
    for x, y, hflip, vflip in placements:
        tilemap[y * 32 + x] = map_word(1, hflip=hflip, vflip=vflip)
    common_upload(builder, colors, [blank, asymmetric], tilemap)
    builder.finish()
    return builder


def case_04() -> TraceBuilder:
    builder = TraceBuilder.begin("04_plane_a")
    colors: dict[int, tuple[int, int, int]] = {0: (0, 0, 0)}
    ramps = [
        [(0, 0, 0), (7, 1, 1), (7, 4, 0), (7, 7, 1)],
        [(0, 0, 0), (1, 7, 1), (0, 7, 5), (1, 4, 7)],
        [(0, 0, 0), (1, 2, 7), (5, 1, 7), (7, 1, 4)],
        [(0, 0, 0), (4, 4, 4), (6, 6, 6), (7, 7, 7)],
    ]
    for palette, ramp in enumerate(ramps):
        for offset, rgb in enumerate(ramp):
            colors[palette * 16 + offset] = rgb

    blank = [[0] * 8 for _ in range(8)]
    checker = [[1 if ((x ^ y) & 1) else 2 for x in range(8)] for y in range(8)]
    stripes = [[1 + ((x // 2) % 3) for x in range(8)] for _ in range(8)]
    diamond = [[1 + ((abs(x - 3) + abs(y - 3)) % 3) for x in range(8)] for y in range(8)]
    corners = [[3 if (x in (0, 7) and y in (0, 7)) else (1 if x == y else 2 if x + y == 7 else 0) for x in range(8)] for y in range(8)]
    tiles = [blank, checker, stripes, diamond, corners]

    tilemap = blank_map(map_word(0))
    for y in range(28):
        for x in range(32):
            tile = 1 + ((x // 4 + y // 3) % 4)
            palette = ((x // 8) + (y // 7)) % 4
            tilemap[y * 32 + x] = map_word(
                tile,
                palette=palette,
                hflip=bool((x // 4) & 1),
                vflip=bool((y // 4) & 1),
                priority=(x + y) & 1,
            )
    common_upload(builder, colors, tiles, tilemap)
    builder.finish()
    return builder


CASES: dict[str, Callable[[], TraceBuilder]] = {
    "01_solid_palette": case_01,
    "02_single_tile": case_02,
    "03_tile_flip": case_03,
    "04_plane_a": case_04,
}


def write_case(name: str, destination: str | Path) -> Path:
    try:
        builder = CASES[name]()
    except KeyError as exc:
        raise ValueError(f"unknown synthetic case {name!r}") from exc
    header = {
        "format": TRACE_MAGIC,
        "version": TRACE_VERSION,
        "name": builder.name,
        "video": {"width": 256, "height": 224, "timing": "ntsc", "mode": "h32"},
        "scope": "frame-static-mode5",
    }
    path = Path(destination)
    write_trace(path, header, builder.events)
    return path
