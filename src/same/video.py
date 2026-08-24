"""Target-neutral indexed-video service with SNES-friendly acceleration seams."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image

from .errors import EngineExecutionError


@dataclass(frozen=True, slots=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("rectangle width and height must not be negative")

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def clipped(self, width: int, height: int) -> "Rect | None":
        left = max(0, self.x)
        top = max(0, self.y)
        right = min(width, self.right)
        bottom = min(height, self.bottom)
        if right <= left or bottom <= top:
            return None
        return Rect(left, top, right - left, bottom - top)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(slots=True)
class CursorState:
    width: int = 0
    height: int = 0
    hotspot_x: int = 0
    hotspot_y: int = 0
    x: int = 0
    y: int = 0
    visible: bool = False
    transparent_index: int = 0
    pixels: bytes = b""


@dataclass(frozen=True, slots=True)
class PresentRecord:
    frame: int
    generation: int
    sha256: str
    dirty: tuple[Rect, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "frame": self.frame,
            "generation": self.generation,
            "sha256": self.sha256,
            "dirty": [rect.to_dict() for rect in self.dirty],
        }


class IndexedSurface:
    """An 8-bit indexed framebuffer plus a 256-entry RGB palette."""

    def __init__(self, width: int, height: int) -> None:
        if not 1 <= width <= 2048 or not 1 <= height <= 2048:
            raise ValueError("surface dimensions must be in 1..2048")
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height)
        self.palette: list[tuple[int, int, int]] = [(0, 0, 0)] * 256
        self._dirty: list[Rect] = [Rect(0, 0, width, height)]

    def _offset(self, x: int, y: int) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"pixel ({x}, {y}) lies outside {self.width}x{self.height}")
        return y * self.width + x

    def mark_dirty(self, rect: Rect) -> None:
        clipped = rect.clipped(self.width, self.height)
        if clipped is not None:
            self._dirty.append(clipped)

    def consume_dirty(self) -> tuple[Rect, ...]:
        dirty = tuple(self._dirty)
        self._dirty.clear()
        return dirty

    def set_palette(self, first: int, colors: Iterable[Sequence[int]]) -> None:
        if not 0 <= first <= 255:
            raise ValueError("first palette index must be in 0..255")
        converted: list[tuple[int, int, int]] = []
        for color in colors:
            if len(color) != 3:
                raise ValueError("palette colors must contain exactly three components")
            rgb = tuple(int(value) for value in color)
            if any(value < 0 or value > 255 for value in rgb):
                raise ValueError("palette components must be in 0..255")
            converted.append(rgb)  # type: ignore[arg-type]
        if first + len(converted) > 256:
            raise ValueError("palette write exceeds 256 entries")
        self.palette[first : first + len(converted)] = converted
        self.mark_dirty(Rect(0, 0, self.width, self.height))

    def set_pixel(self, x: int, y: int, color: int) -> None:
        if not 0 <= color <= 255:
            raise ValueError("indexed color must be in 0..255")
        self.pixels[self._offset(x, y)] = color
        self.mark_dirty(Rect(x, y, 1, 1))

    def fill(self, color: int, rect: Rect | None = None) -> None:
        if not 0 <= color <= 255:
            raise ValueError("indexed color must be in 0..255")
        target = Rect(0, 0, self.width, self.height) if rect is None else rect
        clipped = target.clipped(self.width, self.height)
        if clipped is None:
            return
        row = bytes([color]) * clipped.width
        for y in range(clipped.y, clipped.bottom):
            start = y * self.width + clipped.x
            self.pixels[start : start + clipped.width] = row
        self.mark_dirty(clipped)

    def blit(
        self,
        source: bytes | bytearray | memoryview,
        *,
        source_width: int,
        source_height: int,
        x: int = 0,
        y: int = 0,
        source_pitch: int | None = None,
        transparent_index: int | None = None,
    ) -> None:
        if source_width < 0 or source_height < 0:
            raise ValueError("source dimensions must not be negative")
        pitch = source_width if source_pitch is None else source_pitch
        if pitch < source_width:
            raise ValueError("source pitch is smaller than source width")
        raw = bytes(source)
        required = pitch * source_height
        if len(raw) < required:
            raise ValueError(f"source has {len(raw)} bytes; expected at least {required}")
        target = Rect(x, y, source_width, source_height).clipped(self.width, self.height)
        if target is None:
            return
        source_x = target.x - x
        source_y = target.y - y
        for row_index in range(target.height):
            src_start = (source_y + row_index) * pitch + source_x
            dst_start = (target.y + row_index) * self.width + target.x
            src_row = raw[src_start : src_start + target.width]
            if transparent_index is None:
                self.pixels[dst_start : dst_start + target.width] = src_row
            else:
                if not 0 <= transparent_index <= 255:
                    raise ValueError("transparent index must be in 0..255")
                for column, value in enumerate(src_row):
                    if value != transparent_index:
                        self.pixels[dst_start + column] = value
        self.mark_dirty(target)

    def hash(self) -> str:
        digest = sha256()
        digest.update(self.width.to_bytes(2, "little"))
        digest.update(self.height.to_bytes(2, "little"))
        for red, green, blue in self.palette:
            digest.update(bytes((red, green, blue)))
        digest.update(self.pixels)
        return digest.hexdigest()

    def to_image(self, cursor: CursorState | None = None) -> Image.Image:
        image = Image.frombytes("P", (self.width, self.height), bytes(self.pixels))
        flat_palette = [component for rgb in self.palette for component in rgb]
        image.putpalette(flat_palette)
        if cursor is None or not cursor.visible or not cursor.pixels:
            return image
        composed = image.convert("RGBA")
        cursor_image = Image.frombytes("P", (cursor.width, cursor.height), cursor.pixels)
        cursor_image.putpalette(flat_palette)
        rgba = cursor_image.convert("RGBA")
        alpha = bytearray(cursor.width * cursor.height)
        for index, value in enumerate(cursor.pixels):
            alpha[index] = 0 if value == cursor.transparent_index else 255
        rgba.putalpha(Image.frombytes("L", (cursor.width, cursor.height), bytes(alpha)))
        composed.alpha_composite(
            rgba,
            (cursor.x - cursor.hotspot_x, cursor.y - cursor.hotspot_y),
        )
        return composed


class VideoService:
    def __init__(self, width: int, height: int) -> None:
        self.surface = IndexedSurface(width, height)
        self.cursor = CursorState()
        self.generation = 0
        self.presented: list[PresentRecord] = []

    def define_cursor(
        self,
        pixels: bytes,
        width: int,
        height: int,
        *,
        hotspot_x: int = 0,
        hotspot_y: int = 0,
        transparent_index: int = 0,
    ) -> None:
        if width <= 0 or height <= 0 or len(pixels) != width * height:
            raise EngineExecutionError("cursor dimensions do not match cursor pixel data")
        if not (0 <= hotspot_x < width and 0 <= hotspot_y < height):
            raise EngineExecutionError("cursor hotspot lies outside cursor dimensions")
        self.cursor.width = width
        self.cursor.height = height
        self.cursor.hotspot_x = hotspot_x
        self.cursor.hotspot_y = hotspot_y
        self.cursor.transparent_index = transparent_index
        self.cursor.pixels = bytes(pixels)

    def move_cursor(self, x: int, y: int) -> None:
        self.cursor.x = max(0, min(self.surface.width - 1, int(x)))
        self.cursor.y = max(0, min(self.surface.height - 1, int(y)))

    def show_cursor(self, visible: bool = True) -> None:
        self.cursor.visible = bool(visible)

    def present(self, frame: int) -> PresentRecord:
        record = PresentRecord(
            frame=frame,
            generation=self.generation,
            sha256=self.surface.hash(),
            dirty=self.surface.consume_dirty(),
        )
        self.presented.append(record)
        self.generation += 1
        return record

    def write_png(self, path: Path, *, include_cursor: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        image = self.surface.to_image(self.cursor if include_cursor else None)
        image.save(path)
