"""Logical SCUMM scene composition behind SAME's indexed video service."""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Mapping

from ...capabilities import EngineCapability, capability_names
from ...engine import EngineContext
from ...errors import ResourceError
from ...video import IndexedSurface, Rect

_SCENE_HEADER = struct.Struct("<4sBHHHHHBB")
_ACTOR_HEADER = struct.Struct("<hhHHBB")
_TEXT_HEADER = struct.Struct("<hhBBH")
_CURSOR_HEADER = struct.Struct("<4sBBBBBB")
_SCENE_MAGIC = b"SCN3"
_SCENE_VERSION = 1
_CURSOR_MAGIC = b"SCC3"
_CURSOR_VERSION = 1
_CHARSET_TABLE_OFFSET = 4 + 15
_CHARSET_HEADER_SIZE = _CHARSET_TABLE_OFFSET + 256 * 4
_ACCELERATORS = (
    EngineCapability.TILED_VIDEO
    | EngineCapability.SPRITE_OAM
    | EngineCapability.Z_MASK
    | EngineCapability.HDMA
    | EngineCapability.SA1_JOBS
)


@dataclass(frozen=True, slots=True)
class SceneActor:
    x: int
    y: int
    width: int
    height: int
    transparent_index: int
    priority: int
    pixels: bytes


@dataclass(frozen=True, slots=True)
class SceneText:
    x: int
    y: int
    color: int
    font_key: str
    text: str


@dataclass(frozen=True, slots=True)
class ScummScene:
    width: int
    height: int
    viewport_x: int
    viewport_y: int
    palette: tuple[tuple[int, int, int], ...]
    background: bytes
    z_mask: bytes
    actors: tuple[SceneActor, ...]
    texts: tuple[SceneText, ...]


@dataclass(frozen=True, slots=True)
class CharsetGlyph:
    width: int
    height: int
    x_offset: int
    y_offset: int
    pixels: bytes

    @property
    def advance(self) -> int:
        return max(1, self.width + max(0, self.x_offset))


def _signed_byte(value: int) -> int:
    return value - 256 if value >= 128 else value


class ScummV5Charset:
    """Strict decoder for the v5 CHAR offset-table and 1bpp glyph shape."""

    def __init__(self, data: bytes, *, key: str) -> None:
        self.data = bytes(data)
        self.key = key
        if len(self.data) < 25:
            raise ResourceError(f"SCUMM charset {key!r} is shorter than its header")
        declared = struct.unpack_from("<I", self.data, 0)[0]
        self._base = 0
        self._header_size = _CHARSET_HEADER_SIZE
        if declared == len(self.data):
            if len(self.data) < _CHARSET_HEADER_SIZE:
                raise ResourceError(
                    f"SCUMM charset {key!r} is {len(self.data)} bytes; "
                    f"expected at least {_CHARSET_HEADER_SIZE}"
                )
            self.color_map = tuple(self.data[4:_CHARSET_TABLE_OFFSET])
            self._offsets = tuple(
                struct.unpack_from("<I", self.data, _CHARSET_TABLE_OFFSET + index * 4)[0]
                for index in range(256)
            )
            return
        # The LucasArts v5 CHAR resource has a 21-byte wrapper before the
        # classic font header. Its size word excludes fifteen wrapper bytes,
        # and its glyph offsets are relative to the font header.
        if declared + 15 != len(self.data):
            raise ResourceError(
                f"SCUMM charset {key!r} declares {declared} bytes; got {len(self.data)}"
            )
        self._base = 21
        bits_per_pixel, _height, character_count = struct.unpack_from(
            "<BBH", self.data, self._base
        )
        if bits_per_pixel != 1 or not 1 <= character_count <= 256:
            raise ResourceError(
                f"SCUMM charset {key!r} has unsupported {bits_per_pixel}bpp/"
                f"{character_count}-character header"
            )
        table = self._base + 4
        self._header_size = table + character_count * 4
        if self._header_size > len(self.data):
            raise ResourceError(f"SCUMM charset {key!r} offset table is truncated")
        offsets = [0] * 256
        for index in range(character_count):
            offsets[index] = struct.unpack_from("<I", self.data, table + index * 4)[0]
        self.color_map = tuple(self.data[4:self._base])
        self._offsets = tuple(offsets)

    def glyph(self, codepoint: int) -> CharsetGlyph | None:
        if not 0 <= codepoint <= 255:
            raise ResourceError(
                f"SCUMM charset {self.key!r} cannot encode codepoint {codepoint}"
            )
        offset = self._offsets[codepoint]
        if offset == 0:
            return None
        absolute_offset = self._base + offset
        if absolute_offset < self._header_size:
            raise ResourceError(
                f"SCUMM charset {self.key!r} glyph {codepoint} points into its header"
            )
        if absolute_offset + 4 > len(self.data):
            raise ResourceError(
                f"SCUMM charset {self.key!r} glyph {codepoint} header is out of bounds"
            )
        width, height, x_offset, y_offset = self.data[absolute_offset : absolute_offset + 4]
        if width > 64 or height > 64:
            raise ResourceError(
                f"SCUMM charset {self.key!r} glyph {codepoint} is {width}x{height}"
            )
        pixel_count = width * height
        byte_count = (pixel_count + 7) // 8
        end = absolute_offset + 4 + byte_count
        if end > len(self.data):
            raise ResourceError(
                f"SCUMM charset {self.key!r} glyph {codepoint} pixels are truncated"
            )
        packed = self.data[absolute_offset + 4 : end]
        pixels = bytes(
            (packed[index // 8] >> (7 - index % 8)) & 1
            for index in range(pixel_count)
        )
        return CharsetGlyph(
            width,
            height,
            _signed_byte(x_offset),
            _signed_byte(y_offset),
            pixels,
        )


def decode_scene(data: bytes, *, key: str) -> ScummScene:
    if len(data) < _SCENE_HEADER.size:
        raise ResourceError(f"SCUMM scene {key!r} is shorter than its header")
    (
        magic,
        version,
        width,
        height,
        palette_count,
        viewport_x,
        viewport_y,
        actor_count,
        text_count,
    ) = _SCENE_HEADER.unpack_from(data, 0)
    if magic != _SCENE_MAGIC or version != _SCENE_VERSION:
        raise ResourceError(f"SCUMM scene {key!r} has unsupported magic/version")
    if not 1 <= width <= 2048 or not 1 <= height <= 2048:
        raise ResourceError(f"SCUMM scene {key!r} dimensions are invalid")
    if palette_count > 256:
        raise ResourceError(f"SCUMM scene {key!r} has too many palette entries")
    if viewport_x >= width or viewport_y >= height:
        raise ResourceError(f"SCUMM scene {key!r} viewport starts outside the scene")
    offset = _SCENE_HEADER.size
    palette_bytes = palette_count * 3
    plane_bytes = width * height
    fixed_end = offset + palette_bytes + plane_bytes * 2
    if fixed_end > len(data):
        raise ResourceError(f"SCUMM scene {key!r} palette/background/z-mask is truncated")
    palette = tuple(
        tuple(data[index : index + 3])
        for index in range(offset, offset + palette_bytes, 3)
    )
    offset += palette_bytes
    background = bytes(data[offset : offset + plane_bytes])
    offset += plane_bytes
    z_mask = bytes(data[offset : offset + plane_bytes])
    offset += plane_bytes

    actors: list[SceneActor] = []
    for actor_index in range(actor_count):
        if offset + _ACTOR_HEADER.size > len(data):
            raise ResourceError(f"SCUMM scene {key!r} actor {actor_index} header is truncated")
        x, y, actor_width, actor_height, transparent, priority = _ACTOR_HEADER.unpack_from(
            data, offset
        )
        offset += _ACTOR_HEADER.size
        size = actor_width * actor_height
        if actor_width == 0 or actor_height == 0 or offset + size > len(data):
            raise ResourceError(f"SCUMM scene {key!r} actor {actor_index} pixels are invalid")
        actors.append(
            SceneActor(
                x,
                y,
                actor_width,
                actor_height,
                transparent,
                priority,
                bytes(data[offset : offset + size]),
            )
        )
        offset += size

    texts: list[SceneText] = []
    for text_index in range(text_count):
        if offset + _TEXT_HEADER.size > len(data):
            raise ResourceError(f"SCUMM scene {key!r} text {text_index} header is truncated")
        x, y, color, key_size, text_size = _TEXT_HEADER.unpack_from(data, offset)
        offset += _TEXT_HEADER.size
        end = offset + key_size + text_size
        if key_size == 0 or end > len(data):
            raise ResourceError(f"SCUMM scene {key!r} text {text_index} payload is invalid")
        try:
            font_key = data[offset : offset + key_size].decode("ascii")
            text = data[offset + key_size : end].decode("latin-1")
        except UnicodeDecodeError as exc:
            raise ResourceError(f"SCUMM scene {key!r} text {text_index} encoding is invalid") from exc
        texts.append(SceneText(x, y, color, font_key, text))
        offset = end
    if offset != len(data):
        raise ResourceError(f"SCUMM scene {key!r} has {len(data) - offset} trailing bytes")
    return ScummScene(
        width,
        height,
        viewport_x,
        viewport_y,
        palette,
        background,
        z_mask,
        tuple(actors),
        tuple(texts),
    )


def decode_cursor(data: bytes, *, key: str) -> tuple[int, int, int, int, int, bytes]:
    if len(data) < _CURSOR_HEADER.size:
        raise ResourceError(f"SCUMM cursor {key!r} is shorter than its header")
    magic, version, width, height, hotspot_x, hotspot_y, transparent = _CURSOR_HEADER.unpack_from(
        data, 0
    )
    if magic != _CURSOR_MAGIC or version != _CURSOR_VERSION:
        raise ResourceError(f"SCUMM cursor {key!r} has unsupported magic/version")
    if width == 0 or height == 0 or hotspot_x >= width or hotspot_y >= height:
        raise ResourceError(f"SCUMM cursor {key!r} dimensions/hotspot are invalid")
    pixels = bytes(data[_CURSOR_HEADER.size :])
    if len(pixels) != width * height:
        raise ResourceError(f"SCUMM cursor {key!r} pixel count is invalid")
    return width, height, hotspot_x, hotspot_y, transparent, pixels


class ScummV5VideoAdapter:
    """Compose a canonical logical frame and project it through SAME video."""

    def __init__(self, context: EngineContext) -> None:
        self.context = context
        self.logical_surface: IndexedSurface | None = None
        self.scene: ScummScene | None = None
        self.logical_sha256 = ""
        self.mode = "baseline"
        self.accelerators: tuple[str, ...] = ()
        self.plan: dict[str, int] = {}
        self._projection = (0, 0, 0, 0, 0, 0)

    def _draw_actor(self, surface: IndexedSurface, scene: ScummScene, actor: SceneActor) -> None:
        for source_y in range(actor.height):
            target_y = actor.y + source_y
            if not 0 <= target_y < scene.height:
                continue
            for source_x in range(actor.width):
                target_x = actor.x + source_x
                if not 0 <= target_x < scene.width:
                    continue
                color = actor.pixels[source_y * actor.width + source_x]
                if color == actor.transparent_index:
                    continue
                index = target_y * scene.width + target_x
                if actor.priority >= scene.z_mask[index]:
                    surface.pixels[index] = color

    def _draw_text(
        self,
        surface: IndexedSurface,
        text: SceneText,
        font: ScummV5Charset,
    ) -> int:
        origin_x = pen_x = text.x
        pen_y = text.y
        drawn = 0
        for character in text.text:
            if character == "\n":
                pen_x = origin_x
                pen_y += 9
                continue
            glyph = font.glyph(ord(character))
            if glyph is None:
                pen_x += 4
                continue
            for glyph_y in range(glyph.height):
                target_y = pen_y + glyph.y_offset + glyph_y
                if not 0 <= target_y < surface.height:
                    continue
                for glyph_x in range(glyph.width):
                    if not glyph.pixels[glyph_y * glyph.width + glyph_x]:
                        continue
                    target_x = pen_x + glyph.x_offset + glyph_x
                    if 0 <= target_x < surface.width:
                        surface.pixels[target_y * surface.width + target_x] = text.color
            pen_x += glyph.advance
            drawn += 1
        return drawn

    @staticmethod
    def _unique_tiles(scene: ScummScene) -> int:
        tiles: set[bytes] = set()
        for y in range(0, scene.height, 8):
            for x in range(0, scene.width, 8):
                tile = bytearray(64)
                for row in range(8):
                    if y + row >= scene.height:
                        break
                    width = min(8, scene.width - x)
                    source = (y + row) * scene.width + x
                    tile[row * 8 : row * 8 + width] = scene.background[source : source + width]
                tiles.add(bytes(tile))
        return len(tiles)

    def render(self, scene_key: str, *, cursor_key: str | None = None) -> str:
        scene = decode_scene(self.context.services.resource_read(scene_key), key=scene_key)
        expected_width = self.context.profile.video.logical_width or self.context.profile.video.width
        expected_height = self.context.profile.video.logical_height or self.context.profile.video.height
        if (scene.width, scene.height) != (expected_width, expected_height):
            raise ResourceError(
                f"SCUMM scene {scene_key!r} is {scene.width}x{scene.height}; "
                f"profile logical surface is {expected_width}x{expected_height}"
            )
        surface = IndexedSurface(scene.width, scene.height)
        surface.set_palette(0, scene.palette)
        surface.pixels[:] = scene.background
        for actor in sorted(scene.actors, key=lambda item: item.priority):
            self._draw_actor(surface, scene, actor)
        fonts: dict[str, ScummV5Charset] = {}
        glyph_count = 0
        for text in scene.texts:
            font = fonts.get(text.font_key)
            if font is None:
                font = ScummV5Charset(
                    self.context.services.resource_read(text.font_key), key=text.font_key
                )
                fonts[text.font_key] = font
            glyph_count += self._draw_text(surface, text, font)
        surface.mark_dirty(Rect(0, 0, scene.width, scene.height))

        selected = self.context.negotiated_capabilities & _ACCELERATORS
        self.accelerators = capability_names(selected)
        self.mode = "accelerated" if selected else "baseline"
        self.plan = {
            "unique_tiles": self._unique_tiles(scene) if selected & EngineCapability.TILED_VIDEO else 0,
            "oam_objects": len(scene.actors) if selected & EngineCapability.SPRITE_OAM else 0,
            "z_mask_pixels": sum(value != 0 for value in scene.z_mask)
            if selected & EngineCapability.Z_MASK
            else 0,
            "glyphs": glyph_count,
        }
        self.logical_surface = surface
        self.scene = scene
        self.logical_sha256 = surface.hash()
        self._project()

        if cursor_key is not None:
            width, height, hotspot_x, hotspot_y, transparent, pixels = decode_cursor(
                self.context.services.resource_read(cursor_key), key=cursor_key
            )
            self.context.services.video.define_cursor(
                pixels,
                width,
                height,
                hotspot_x=hotspot_x,
                hotspot_y=hotspot_y,
                transparent_index=transparent,
            )
        self.context.services.debug.marker("scumm_v5.scene", int(self.logical_sha256[:8], 16))
        return self.logical_sha256

    def _project(self) -> None:
        assert self.scene is not None and self.logical_surface is not None
        target = self.context.services.video.surface
        scene = self.scene
        width = min(target.width, scene.width - scene.viewport_x)
        height = min(target.height, scene.height - scene.viewport_y)
        destination_x = max(0, (target.width - width) // 2)
        destination_y = max(0, (target.height - height) // 2)
        target.fill(0)
        target.set_palette(0, scene.palette)
        cropped = b"".join(
            self.logical_surface.pixels[
                (scene.viewport_y + row) * scene.width
                + scene.viewport_x : (scene.viewport_y + row) * scene.width
                + scene.viewport_x
                + width
            ]
            for row in range(height)
        )
        target.blit(
            cropped,
            source_width=width,
            source_height=height,
            x=destination_x,
            y=destination_y,
        )
        self._projection = (
            scene.viewport_x,
            scene.viewport_y,
            destination_x,
            destination_y,
            width,
            height,
        )

    def move_cursor(self, logical_x: int, logical_y: int) -> None:
        source_x, source_y, destination_x, destination_y, width, height = self._projection
        physical_x = destination_x + logical_x - source_x
        physical_y = destination_y + logical_y - source_y
        physical_x = max(destination_x, min(destination_x + width - 1, physical_x))
        physical_y = max(destination_y, min(destination_y + height - 1, physical_y))
        self.context.services.video.move_cursor(physical_x, physical_y)

    def inspect(self) -> Mapping[str, object]:
        return {
            "mode": self.mode,
            "accelerators": list(self.accelerators),
            "logical_sha256": self.logical_sha256,
            "plan": dict(self.plan),
            "projection": list(self._projection),
        }
