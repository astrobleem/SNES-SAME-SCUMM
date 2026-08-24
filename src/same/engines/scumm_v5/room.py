"""Strict raw and cooked SCUMM v5 room decoding and presentation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import struct
from typing import Mapping

from ...engine import EngineContext
from ...errors import ResourceError
from ...video import IndexedSurface, Rect

_COOKED_HEADER = struct.Struct("<4sBHHH")
_COOKED_MAGIC = b"SC5R"
_COOKED_VERSION = 1
_CHUNK_HEADER_SIZE = 8
_MAX_ROOM_SIZE = 2048

_BASIC_VERTICAL = frozenset((*range(14, 19), *range(34, 39)))
_BASIC_HORIZONTAL = frozenset((*range(24, 29), *range(44, 49)))
_MAJOR_MINOR = frozenset(
    (*range(64, 69), *range(84, 89), *range(104, 109), *range(124, 129))
)
_TRANSPARENT = frozenset((*range(34, 39), *range(44, 49), *range(84, 89), *range(124, 129)))
_SUPPORTED_CODECS = frozenset((1, *_BASIC_VERTICAL, *_BASIC_HORIZONTAL, *_MAJOR_MINOR))


@dataclass(frozen=True, slots=True)
class ScummV5Room:
    width: int
    height: int
    palette: tuple[tuple[int, int, int], ...]
    pixels: bytes
    transparent_index: int
    source_format: str
    strip_codecs: tuple[int, ...]
    objects: tuple["ScummV5RoomObject", ...]
    entry_script: bytes | None
    exit_script: bytes | None
    local_scripts: tuple[tuple[int, bytes], ...]


@dataclass(frozen=True, slots=True)
class ScummV5RoomObject:
    object_id: int
    x: int
    y: int
    width: int
    height: int
    flags: int
    parent: int
    walk_x: int
    walk_y: int
    actor_direction: int


@dataclass(frozen=True, slots=True)
class _Chunk:
    tag: bytes
    raw: bytes

    @property
    def payload(self) -> bytes:
        return self.raw[_CHUNK_HEADER_SIZE:]


class _LsbBitReader:
    def __init__(self, data: bytes, *, owner: str) -> None:
        self._data = data
        self._owner = owner
        self._offset = 0
        self._bits = 0
        self._count = 0

    def read(self, count: int) -> int:
        while self._count < count:
            if self._offset >= len(self._data):
                raise ResourceError(f"{self._owner} compressed bits are truncated")
            self._bits |= self._data[self._offset] << self._count
            self._offset += 1
            self._count += 8
        value = self._bits & ((1 << count) - 1)
        self._bits >>= count
        self._count -= count
        return value


def _chunks(data: bytes, *, owner: str) -> tuple[_Chunk, ...]:
    result: list[_Chunk] = []
    offset = 0
    while offset < len(data):
        if offset + _CHUNK_HEADER_SIZE > len(data):
            raise ResourceError(f"{owner} has a truncated chunk header at offset {offset}")
        size = int.from_bytes(data[offset + 4 : offset + 8], "big")
        if size < _CHUNK_HEADER_SIZE:
            raise ResourceError(f"{owner} chunk at offset {offset} has invalid size {size}")
        end = offset + size
        if end > len(data):
            tag = data[offset : offset + 4].decode("latin-1")
            raise ResourceError(f"{owner} {tag} chunk is truncated")
        result.append(_Chunk(data[offset : offset + 4], bytes(data[offset:end])))
        offset = end
    return tuple(result)


def _one(chunks: tuple[_Chunk, ...], tag: bytes, *, owner: str) -> _Chunk:
    matches = tuple(chunk for chunk in chunks if chunk.tag == tag)
    name = tag.decode("ascii")
    if not matches:
        raise ResourceError(f"{owner} is missing its {name} chunk")
    if len(matches) != 1:
        raise ResourceError(f"{owner} contains duplicate {name} chunks")
    return matches[0]


def _dimensions(width: int, height: int, *, owner: str) -> None:
    if not 1 <= width <= _MAX_ROOM_SIZE or not 1 <= height <= _MAX_ROOM_SIZE:
        raise ResourceError(f"{owner} dimensions {width}x{height} are invalid")


def _decode_cooked(data: bytes, *, key: str) -> ScummV5Room:
    if len(data) < _COOKED_HEADER.size:
        raise ResourceError(f"SCUMM cooked room {key!r} is shorter than its header")
    magic, version, width, height, palette_count = _COOKED_HEADER.unpack_from(data)
    if magic != _COOKED_MAGIC or version != _COOKED_VERSION:
        raise ResourceError(f"SCUMM cooked room {key!r} has unsupported header")
    _dimensions(width, height, owner=f"SCUMM cooked room {key!r}")
    if palette_count > 256:
        raise ResourceError(f"SCUMM cooked room {key!r} has too many palette entries")
    palette_end = _COOKED_HEADER.size + palette_count * 3
    expected = palette_end + width * height
    if len(data) != expected:
        raise ResourceError(f"SCUMM cooked room {key!r} is {len(data)} bytes; expected {expected}")
    palette = tuple(
        tuple(data[index : index + 3])
        for index in range(_COOKED_HEADER.size, palette_end, 3)
    )
    return ScummV5Room(
        width,
        height,
        palette,
        bytes(data[palette_end:]),
        255,
        "cooked-sc5r",
        (),
        (),
        None,
        None,
        (),
    )


def _decode_basic(
    data: bytes, *, height: int, bit_width: int, vertical: bool, owner: str
) -> bytes:
    if len(data) < 2:
        raise ResourceError(f"{owner} compressed strip header is truncated")
    color = data[0]
    bits = _LsbBitReader(data[1:], owner=owner)
    output = bytearray(8 * height)
    increment = -1
    order = tuple(
        ((x, y) for x in range(8) for y in range(height))
        if vertical
        else ((x, y) for y in range(height) for x in range(8))
    )
    return _decode_basic_pixels(output, order, color, increment, bits, bit_width=bit_width)


def _decode_basic_pixels(
    output: bytearray,
    order: Iterable[tuple[int, int]],
    color: int,
    increment: int,
    bits: _LsbBitReader,
    *,
    bit_width: int,
) -> bytes:
    positions = tuple(order)
    for index, (x, y) in enumerate(positions):
        output[y * 8 + x] = color
        if index + 1 == len(positions):
            break
        if bits.read(1):
            if not bits.read(1):
                color = bits.read(bit_width)
                increment = -1
            elif not bits.read(1):
                color = (color + increment) & 0xFF
            else:
                increment = -increment
                color = (color + increment) & 0xFF
    return bytes(output)


def _decode_major_minor(data: bytes, *, height: int, bit_width: int, owner: str) -> bytes:
    if len(data) < 3:
        raise ResourceError(f"{owner} compressed strip header is truncated")
    color = data[0]
    bits = _LsbBitReader(data[1:], owner=owner)
    output = bytearray(8 * height)
    repeat = 0
    for index in range(len(output)):
        output[index] = color
        if index + 1 == len(output):
            break
        if repeat:
            repeat -= 1
            continue
        if not bits.read(1):
            continue
        if not bits.read(1):
            color = bits.read(bit_width)
            continue
        difference = bits.read(3) - 4
        if difference:
            color = (color + difference) & 0xFF
        else:
            count = bits.read(8)
            if count == 0:
                raise ResourceError(f"{owner} has an invalid zero-pixel repeat")
            repeat = count - 1
    return bytes(output)


def _decode_strip(data: bytes, *, height: int, owner: str) -> tuple[bytes, int]:
    if not data:
        raise ResourceError(f"{owner} strip payload is empty")
    codec = data[0]
    if codec not in _SUPPORTED_CODECS:
        raise ResourceError(f"{owner} uses unsupported strip codec {codec}")
    compressed = data[1:]
    if codec == 1:
        needed = 8 * height
        if len(compressed) < needed:
            raise ResourceError(f"{owner} raw strip is truncated")
        pixels = bytes(compressed[:needed])
    elif codec in _BASIC_VERTICAL:
        pixels = _decode_basic(
            compressed,
            height=height,
            bit_width=codec % 10,
            vertical=True,
            owner=f"{owner} codec {codec}",
        )
    elif codec in _BASIC_HORIZONTAL:
        pixels = _decode_basic(
            compressed,
            height=height,
            bit_width=codec % 10,
            vertical=False,
            owner=f"{owner} codec {codec}",
        )
    else:
        pixels = _decode_major_minor(
            compressed, height=height, bit_width=codec % 10, owner=f"{owner} codec {codec}"
        )
    return pixels, codec


def _decode_raw(data: bytes, *, key: str) -> ScummV5Room:
    owner = f"SCUMM raw v5 room {key!r}"
    top = _chunks(data, owner=owner)
    rmhd = _one(top, b"RMHD", owner=owner)
    if len(rmhd.payload) != 6:
        raise ResourceError(f"{owner} RMHD payload is {len(rmhd.payload)} bytes; expected 6")
    width, height, object_count = struct.unpack("<HHH", rmhd.payload)
    _dimensions(width, height, owner=owner)
    if width % 8:
        raise ResourceError(f"{owner} width {width} is not a whole number of strips")

    clut = _one(top, b"CLUT", owner=owner)
    if len(clut.payload) != 256 * 3:
        raise ResourceError(f"{owner} CLUT payload is {len(clut.payload)} bytes; expected 768")
    palette = tuple(
        tuple(clut.payload[index : index + 3]) for index in range(0, len(clut.payload), 3)
    )
    transparent_chunks = tuple(chunk for chunk in top if chunk.tag == b"TRNS")
    if len(transparent_chunks) > 1:
        raise ResourceError(f"{owner} contains duplicate TRNS chunks")
    if transparent_chunks:
        payload = transparent_chunks[0].payload
        if len(payload) != 2:
            raise ResourceError(f"{owner} TRNS payload is {len(payload)} bytes; expected 2")
        transparent = struct.unpack("<H", payload)[0]
        if transparent > 255:
            raise ResourceError(f"{owner} transparent index {transparent} is invalid")
    else:
        transparent = 255

    rmim = _one(top, b"RMIM", owner=owner)
    rmim_chunks = _chunks(rmim.payload, owner=f"{owner} RMIM")
    rmih = _one(rmim_chunks, b"RMIH", owner=f"{owner} RMIM")
    if len(rmih.payload) != 2:
        raise ResourceError(f"{owner} RMIH payload is {len(rmih.payload)} bytes; expected 2")
    im00 = _one(rmim_chunks, b"IM00", owner=f"{owner} RMIM")
    image_chunks = _chunks(im00.payload, owner=f"{owner} IM00")
    smap = _one(image_chunks, b"SMAP", owner=f"{owner} IM00")
    strip_count = width // 8
    table_end = _CHUNK_HEADER_SIZE + strip_count * 4
    if len(smap.raw) < table_end:
        raise ResourceError(f"{owner} SMAP strip-offset table is truncated")
    offsets = tuple(
        struct.unpack_from("<I", smap.raw, _CHUNK_HEADER_SIZE + index * 4)[0]
        for index in range(strip_count)
    )
    if any(offset < table_end or offset >= len(smap.raw) for offset in offsets):
        raise ResourceError(f"{owner} SMAP strip offset is out of bounds")
    if any(left >= right for left, right in zip(offsets, offsets[1:])):
        raise ResourceError(f"{owner} SMAP strip offsets are not strictly increasing")

    object_chunks = tuple(chunk for chunk in top if chunk.tag == b"OBCD")
    if len(object_chunks) != object_count:
        raise ResourceError(
            f"{owner} declares {object_count} objects but contains {len(object_chunks)} OBCD chunks"
        )
    objects: list[ScummV5RoomObject] = []
    object_ids: set[int] = set()
    for index, obcd in enumerate(object_chunks):
        children = _chunks(obcd.payload, owner=f"{owner} OBCD {index}")
        cdhd = _one(children, b"CDHD", owner=f"{owner} OBCD {index}")
        if len(cdhd.payload) != 13:
            raise ResourceError(
                f"{owner} OBCD {index} CDHD payload is {len(cdhd.payload)} bytes; expected 13"
            )
        object_id, x, y, object_width, object_height, flags, parent, walk_x, walk_y, direction = (
            struct.unpack("<HBBBBBBhhB", cdhd.payload)
        )
        if object_id == 0 or object_id in object_ids:
            raise ResourceError(f"{owner} OBCD {index} object id {object_id} is invalid or duplicate")
        object_ids.add(object_id)
        objects.append(
            ScummV5RoomObject(
                object_id,
                x * 8,
                y * 8,
                object_width * 8,
                object_height * 8,
                flags,
                parent,
                walk_x,
                walk_y,
                direction,
            )
        )

    entry_chunks = tuple(chunk for chunk in top if chunk.tag == b"ENCD")
    exit_chunks = tuple(chunk for chunk in top if chunk.tag == b"EXCD")
    if len(entry_chunks) > 1 or len(exit_chunks) > 1:
        raise ResourceError(f"{owner} contains duplicate entry or exit code")
    entry_script = entry_chunks[0].payload if entry_chunks else None
    exit_script = exit_chunks[0].payload if exit_chunks else None
    local_scripts: list[tuple[int, bytes]] = []
    local_ids: set[int] = set()
    for index, chunk in enumerate(item for item in top if item.tag == b"LSCR"):
        if len(chunk.payload) < 2:
            raise ResourceError(f"{owner} LSCR {index} has no script body")
        script_id = chunk.payload[0]
        if script_id in local_ids:
            raise ResourceError(f"{owner} contains duplicate local script {script_id}")
        local_ids.add(script_id)
        local_scripts.append((script_id, bytes(chunk.payload[1:])))

    pixels = bytearray([transparent]) * (width * height)
    codecs: list[int] = []
    for strip_index, start in enumerate(offsets):
        end = offsets[strip_index + 1] if strip_index + 1 < strip_count else len(smap.raw)
        strip, codec = _decode_strip(
            smap.raw[start:end],
            height=height,
            owner=f"{owner} strip {strip_index}",
        )
        codecs.append(codec)
        for y in range(height):
            destination = y * width + strip_index * 8
            source = y * 8
            for x, color in enumerate(strip[source : source + 8]):
                if codec not in _TRANSPARENT or color != transparent:
                    pixels[destination + x] = color
    return ScummV5Room(
        width,
        height,
        palette,
        bytes(pixels),
        transparent,
        "raw-v5",
        tuple(codecs),
        tuple(objects),
        None if entry_script is None else bytes(entry_script),
        None if exit_script is None else bytes(exit_script),
        tuple(local_scripts),
    )


def decode_room(data: bytes, *, key: str) -> ScummV5Room:
    """Decode a SAME cooked room or a canonical chunked SCUMM v5 room."""

    if data.startswith(_COOKED_MAGIC):
        return _decode_cooked(data, key=key)
    return _decode_raw(data, key=key)


class ScummV5RoomAdapter:
    """Present decoded room pixels through SAME while retaining a logical surface."""

    def __init__(self, context: EngineContext) -> None:
        self.context = context
        self.logical_surface: IndexedSurface | None = None
        self.room: ScummV5Room | None = None
        self.logical_sha256 = ""
        self._projection = (0, 0, 0, 0, 0, 0)

    def render(self, room_key: str) -> str:
        room = decode_room(self.context.services.resource_read(room_key), key=room_key)
        surface = IndexedSurface(room.width, room.height)
        surface.set_palette(0, room.palette)
        surface.pixels[:] = room.pixels
        surface.mark_dirty(Rect(0, 0, room.width, room.height))
        self.logical_surface = surface
        self.room = room
        self.logical_sha256 = surface.hash()
        self._project()
        self.context.services.debug.marker("scumm_v5.room_image", int(self.logical_sha256[:8], 16))
        return self.logical_sha256

    def _project(self) -> None:
        assert self.room is not None and self.logical_surface is not None
        target = self.context.services.video.surface
        width = min(target.width, self.room.width)
        height = min(target.height, self.room.height)
        source_x = max(0, (self.room.width - width) // 2)
        source_y = max(0, (self.room.height - height) // 2)
        destination_x = max(0, (target.width - width) // 2)
        destination_y = max(0, (target.height - height) // 2)
        target.fill(0)
        target.set_palette(0, self.room.palette)
        cropped = b"".join(
            self.logical_surface.pixels[
                (source_y + row) * self.room.width + source_x :
                (source_y + row) * self.room.width + source_x + width
            ]
            for row in range(height)
        )
        target.blit(cropped, source_width=width, source_height=height, x=destination_x, y=destination_y)
        self._projection = (source_x, source_y, destination_x, destination_y, width, height)

    def move_cursor(self, logical_x: int, logical_y: int) -> None:
        source_x, source_y, destination_x, destination_y, width, height = self._projection
        physical_x = destination_x + logical_x - source_x
        physical_y = destination_y + logical_y - source_y
        physical_x = max(destination_x, min(destination_x + width - 1, physical_x))
        physical_y = max(destination_y, min(destination_y + height - 1, physical_y))
        self.context.services.video.move_cursor(physical_x, physical_y)

    def inspect(self) -> Mapping[str, object]:
        return {
            "mode": "room",
            "logical_sha256": self.logical_sha256,
            "format": None if self.room is None else self.room.source_format,
            "dimensions": None if self.room is None else [self.room.width, self.room.height],
            "strip_codecs": [] if self.room is None else sorted(set(self.room.strip_codecs)),
            "projection": list(self._projection),
        }
