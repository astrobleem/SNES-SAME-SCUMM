"""Target-neutral indexed-video service with SNES-friendly acceleration seams."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Protocol, Sequence

from PIL import Image

from .errors import EngineExecutionError


class PixelFormat(str, Enum):
    INDEX8 = "indexed8"


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


class DirtyRegion:
    """An ordered record of display rectangles awaiting presentation."""

    def __init__(self) -> None:
        self._rects: list[Rect] = []

    @property
    def rects(self) -> tuple[Rect, ...]:
        return tuple(self._rects)

    def add(self, rect: Rect | None) -> None:
        if rect is not None:
            self._rects.append(rect)

    def consume(self) -> tuple[Rect, ...]:
        rects = tuple(self._rects)
        self._rects.clear()
        return rects


class IndexedSurface:
    """An 8-bit indexed pixel buffer plus a 256-entry RGB palette."""

    def __init__(self, width: int, height: int) -> None:
        self._validate_dimensions(width, height)
        self.width = width
        self.height = height
        self.pitch = width
        self.format = PixelFormat.INDEX8
        self.readonly = False
        self.pixels = bytearray(width * height)
        self._pixels_view = memoryview(self.pixels)
        self.palette: list[tuple[int, int, int]] = [(0, 0, 0)] * 256

    @classmethod
    def wrap(
        cls,
        width: int,
        height: int,
        pitch: int,
        pixels: object,
        *,
        palette: list[tuple[int, int, int]] | None = None,
    ) -> "IndexedSurface":
        cls._validate_dimensions(width, height)
        if pitch < width:
            raise ValueError("surface pitch must be at least the surface width")
        pixels_view = cls._byte_view(pixels)
        required = pitch * height
        if len(pixels_view) < required:
            raise ValueError(
                f"surface pixel storage has {len(pixels_view)} bytes; expected at least {required}"
            )
        if palette is not None:
            cls._validate_palette(palette)

        surface = cls.__new__(cls)
        surface.width = width
        surface.height = height
        surface.pitch = pitch
        surface.format = PixelFormat.INDEX8
        surface.readonly = pixels_view.readonly
        surface.pixels = pixels
        surface._pixels_view = pixels_view
        surface.palette = [(0, 0, 0)] * 256 if palette is None else palette
        return surface

    @staticmethod
    def _validate_dimensions(width: int, height: int) -> None:
        if not 1 <= width <= 2048 or not 1 <= height <= 2048:
            raise ValueError("surface dimensions must be in 1..2048")

    @staticmethod
    def _byte_view(storage: object) -> memoryview:
        try:
            supplied_view = memoryview(storage)
        except TypeError as exc:
            raise TypeError("surface pixel storage must be a byte-addressable buffer") from exc
        if (
            supplied_view.ndim != 1
            or supplied_view.itemsize != 1
            or not supplied_view.c_contiguous
        ):
            raise TypeError("surface pixel storage must be a contiguous one-dimensional byte buffer")
        return supplied_view if supplied_view.format == "B" else supplied_view.cast("B")

    @staticmethod
    def _buffer_owner(view: memoryview) -> object:
        owner: object = view.obj
        while isinstance(owner, memoryview):
            owner = owner.obj
        return owner

    @staticmethod
    def _validate_palette(palette: Sequence[Sequence[int]]) -> None:
        if len(palette) != 256:
            raise ValueError("surface palette must contain exactly 256 colors")
        for color in palette:
            if len(color) != 3:
                raise ValueError("palette colors must contain exactly three components")
            if any(not isinstance(value, int) or not 0 <= value <= 255 for value in color):
                raise ValueError("palette components must be integers in 0..255")

    def _require_writable(self) -> None:
        if self.readonly:
            raise TypeError("surface pixel storage is read-only")

    def _offset(self, x: int, y: int) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"pixel ({x}, {y}) lies outside {self.width}x{self.height}")
        return y * self.pitch + x

    def _visible_row(self, y: int) -> memoryview:
        if not 0 <= y < self.height:
            raise IndexError(f"row {y} lies outside surface height {self.height}")
        start = y * self.pitch
        return self._pixels_view[start : start + self.width]

    def visible_bytes(self) -> bytes:
        if self.pitch == self.width:
            return bytes(self._pixels_view[: self.width * self.height])
        return b"".join(bytes(self._visible_row(y)) for y in range(self.height))

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

    def set_pixel(self, x: int, y: int, color: int) -> Rect:
        if not 0 <= color <= 255:
            raise ValueError("indexed color must be in 0..255")
        offset = self._offset(x, y)
        self._require_writable()
        self._pixels_view[offset] = color
        return Rect(x, y, 1, 1)

    def fill(self, color: int, rect: Rect | None = None) -> Rect | None:
        if not 0 <= color <= 255:
            raise ValueError("indexed color must be in 0..255")
        self._require_writable()
        target = Rect(0, 0, self.width, self.height) if rect is None else rect
        clipped = target.clipped(self.width, self.height)
        if clipped is None:
            return None
        row = bytes([color]) * clipped.width
        for y in range(clipped.y, clipped.bottom):
            start = y * self.pitch + clipped.x
            self._pixels_view[start : start + clipped.width] = row
        return clipped

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
    ) -> Rect | None:
        if source_width < 0 or source_height < 0:
            raise ValueError("source dimensions must not be negative")
        pitch = source_width if source_pitch is None else source_pitch
        if pitch < source_width:
            raise ValueError("source pitch is smaller than source width")
        source_view = self._byte_view(source)
        required = pitch * source_height
        if len(source_view) < required:
            raise ValueError(f"source has {len(source_view)} bytes; expected at least {required}")
        return self._blit_region(
            source_view,
            source_width=source_width,
            source_height=source_height,
            source_pitch=pitch,
            source_rect=Rect(0, 0, source_width, source_height),
            x=x,
            y=y,
            transparent_index=transparent_index,
        )

    def blit_surface(
        self,
        source: "IndexedSurface",
        *,
        source_rect: Rect | None = None,
        x: int = 0,
        y: int = 0,
        transparent_index: int | None = None,
    ) -> Rect | None:
        requested = Rect(0, 0, source.width, source.height) if source_rect is None else source_rect
        return self._blit_region(
            source._pixels_view,
            source_width=source.width,
            source_height=source.height,
            source_pitch=source.pitch,
            source_rect=requested,
            x=x,
            y=y,
            transparent_index=transparent_index,
        )

    def _blit_region(
        self,
        source: memoryview,
        *,
        source_width: int,
        source_height: int,
        source_pitch: int,
        source_rect: Rect,
        x: int,
        y: int,
        transparent_index: int | None,
    ) -> Rect | None:
        if transparent_index is not None and not 0 <= transparent_index <= 255:
            raise ValueError("transparent index must be in 0..255")

        source_left = max(0, source_rect.x)
        source_top = max(0, source_rect.y)
        source_right = min(source_width, source_rect.right)
        source_bottom = min(source_height, source_rect.bottom)
        if source_right <= source_left or source_bottom <= source_top:
            return None

        destination_x = x + source_left - source_rect.x
        destination_y = y + source_top - source_rect.y
        copy_width = source_right - source_left
        copy_height = source_bottom - source_top

        destination_left = max(0, destination_x)
        destination_top = max(0, destination_y)
        destination_right = min(self.width, destination_x + copy_width)
        destination_bottom = min(self.height, destination_y + copy_height)
        if destination_right <= destination_left or destination_bottom <= destination_top:
            return None

        source_x = source_left + destination_left - destination_x
        source_y = source_top + destination_top - destination_y
        copy_width = destination_right - destination_left
        copy_height = destination_bottom - destination_top
        changed = Rect(destination_left, destination_top, copy_width, copy_height)
        self._require_writable()

        if self._buffer_owner(source) is self._buffer_owner(self._pixels_view):
            snapshot = b"".join(
                bytes(
                    source[
                        (source_y + row) * source_pitch
                        + source_x : (source_y + row) * source_pitch
                        + source_x
                        + copy_width
                    ]
                )
                for row in range(copy_height)
            )
            source = memoryview(snapshot)
            source_pitch = copy_width
            source_x = 0
            source_y = 0

        for row in range(copy_height):
            source_start = (source_y + row) * source_pitch + source_x
            destination_start = (destination_top + row) * self.pitch + destination_left
            source_row = source[source_start : source_start + copy_width]
            destination_row = self._pixels_view[
                destination_start : destination_start + copy_width
            ]
            if transparent_index is None:
                destination_row[:] = source_row
            else:
                for column, value in enumerate(source_row):
                    if value != transparent_index:
                        destination_row[column] = value

        return changed

    def hash(self) -> str:
        digest = sha256()
        digest.update(self.width.to_bytes(2, "little"))
        digest.update(self.height.to_bytes(2, "little"))
        for red, green, blue in self.palette:
            digest.update(bytes((red, green, blue)))
        digest.update(self.visible_bytes())
        return digest.hexdigest()

    def to_image(self, cursor: CursorState | None = None) -> Image.Image:
        image = Image.frombytes("P", (self.width, self.height), self.visible_bytes())
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


@dataclass(frozen=True, slots=True)
class PresentRequest:
    """Ephemeral target-neutral state supplied to a synchronous video backend."""

    surface: IndexedSurface
    dirty: tuple[Rect, ...]
    cursor: CursorState | None
    frame: int
    generation: int


class VideoBackend(Protocol):
    """Synchronous presentation boundary.

    Implementations may inspect but must not mutate ``request.surface`` and
    must not re-enter the owning :class:`VideoService` mutation facade.
    ``present`` returns before the service commits presentation bookkeeping.
    """

    def present(self, request: PresentRequest) -> PresentRecord:
        ...


class HostEvidenceBackend:
    """Produce the deterministic host evidence record used before delegation."""

    def present(self, request: PresentRequest) -> PresentRecord:
        return PresentRecord(
            frame=request.frame,
            generation=request.generation,
            sha256=request.surface.hash(),
            dirty=request.dirty,
        )


class VideoService:
    def __init__(
        self,
        width: int,
        height: int,
        backend: VideoBackend | None = None,
    ) -> None:
        self.surface = IndexedSurface(width, height)
        self._dirty = DirtyRegion()
        self._dirty.add(Rect(0, 0, width, height))
        self.cursor = CursorState()
        self.backend: VideoBackend = HostEvidenceBackend() if backend is None else backend
        self.generation = 0
        self.presented: list[PresentRecord] = []

    def set_pixel(self, x: int, y: int, color: int) -> Rect:
        changed = self.surface.set_pixel(x, y, color)
        self._dirty.add(changed)
        return changed

    def fill(self, color: int, rect: Rect | None = None) -> Rect | None:
        changed = self.surface.fill(color, rect)
        self._dirty.add(changed)
        return changed

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
    ) -> Rect | None:
        changed = self.surface.blit(
            source,
            source_width=source_width,
            source_height=source_height,
            x=x,
            y=y,
            source_pitch=source_pitch,
            transparent_index=transparent_index,
        )
        self._dirty.add(changed)
        return changed

    def blit_surface(
        self,
        source: IndexedSurface,
        *,
        source_rect: Rect | None = None,
        x: int = 0,
        y: int = 0,
        transparent_index: int | None = None,
    ) -> Rect | None:
        changed = self.surface.blit_surface(
            source,
            source_rect=source_rect,
            x=x,
            y=y,
            transparent_index=transparent_index,
        )
        self._dirty.add(changed)
        return changed

    def set_palette(self, first: int, colors: Iterable[Sequence[int]]) -> None:
        self.surface.set_palette(first, colors)
        self._dirty.add(Rect(0, 0, self.surface.width, self.surface.height))

    def mark_dirty(self, rect: Rect) -> Rect | None:
        clipped = rect.clipped(self.surface.width, self.surface.height)
        self._dirty.add(clipped)
        return clipped

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
        pending_dirty = self._dirty.rects
        request = PresentRequest(
            surface=self.surface,
            dirty=pending_dirty,
            cursor=self.cursor,
            frame=frame,
            generation=self.generation,
        )
        record = self.backend.present(request)
        # The backend contract is synchronous and non-reentrant, so this
        # consumes exactly the immutable tuple it successfully observed.
        self._dirty.consume()
        self.presented.append(record)
        self.generation += 1
        return record

    def write_png(self, path: Path, *, include_cursor: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        image = self.surface.to_image(self.cursor if include_cursor else None)
        image.save(path)
