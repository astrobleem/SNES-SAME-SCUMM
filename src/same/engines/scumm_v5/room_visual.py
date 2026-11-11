"""Versioned source-neutral cooked SCUMM room visuals.

The record deliberately contains decoded linear INDEX8 rows and RGB8 palette
bytes.  Target generators may segment rows for their mapper, but the record is
not a target framebuffer, crop, tile image, or precomposed screen.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib

from ...errors import ResourceError


MAGIC = b"SC5VIS\0\0"
VERSION = 1
STRIP_VERSION = 2
STRIP_WIDTH = 8
PIXEL_FORMAT_INDEX8 = 1
PALETTE_FORMAT_RGB8 = 1
HEADER = struct.Struct("<8sHHHHHHHHHIIII32s32s32s32s32s32s32s")
ROW = struct.Struct("<II")


def _sha(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


@dataclass(frozen=True, slots=True)
class CookedRoomVisual:
    room: int
    width: int
    height: int
    pitch: int
    palette: bytes
    pixels: bytes
    archive_sha256: str
    index_sha256: str
    data_sha256: str
    room_sha256: str
    decoded_palette_sha256: str
    decoded_pixels_sha256: str
    record_sha256: str

    def visible_row(self, y: int) -> bytes:
        if not 0 <= y < self.height:
            raise IndexError("room visual row is outside the surface")
        start = y * self.pitch
        return self.pixels[start : start + self.width]


def encode_room_visual(
    *,
    room: int,
    width: int,
    height: int,
    pitch: int,
    palette: bytes,
    pixels: bytes,
    archive_sha256: str,
    index_sha256: str,
    data_sha256: str,
    room_sha256: str,
) -> bytes:
    if not 0 <= room <= 0xFFFF:
        raise ResourceError("room visual room ID must fit u16")
    if width <= 0 or height <= 0 or pitch < width:
        raise ResourceError("room visual dimensions or pitch are invalid")
    if len(palette) != 256 * 3:
        raise ResourceError("room visual palette must contain 256 RGB8 entries")
    if len(pixels) != pitch * height:
        raise ResourceError("room visual pixel payload length differs")
    try:
        identities = tuple(bytes.fromhex(value) for value in (
            archive_sha256, index_sha256, data_sha256, room_sha256,
        ))
    except ValueError as exc:
        raise ResourceError("room visual source identity is not SHA-256") from exc
    if any(len(value) != 32 for value in identities):
        raise ResourceError("room visual source identity is not SHA-256")
    palette_offset = HEADER.size
    row_directory_offset = palette_offset + len(palette)
    pixel_offset = row_directory_offset + height * ROW.size
    rows = b"".join(ROW.pack(pixel_offset + y * pitch, pitch) for y in range(height))
    palette_hash = _sha(palette)
    pixel_hash = _sha(pixels)
    header = HEADER.pack(
        MAGIC, VERSION, HEADER.size, PIXEL_FORMAT_INDEX8, PALETTE_FORMAT_RGB8,
        room, width, height, pitch, 256,
        palette_offset, row_directory_offset, pixel_offset, len(pixels),
        *identities, palette_hash, pixel_hash, bytes(32),
    )
    prefix = header + palette + rows + pixels
    digest = _sha(prefix)
    mutable = bytearray(prefix)
    mutable[HEADER.size - 32 : HEADER.size] = digest
    return bytes(mutable)


def decode_room_visual(data: bytes, *, expected_room: int | None = None) -> CookedRoomVisual:
    if len(data) < HEADER.size:
        raise ResourceError("room visual is shorter than its header")
    values = HEADER.unpack_from(data)
    (
        magic, version, header_size, pixel_format, palette_format,
        room, width, height, pitch, palette_count,
        palette_offset, row_directory_offset, pixel_offset, pixel_length,
        archive_hash, index_hash, data_hash, room_hash,
        palette_hash, pixel_hash, record_hash,
    ) = values
    if magic != MAGIC or version not in (VERSION, STRIP_VERSION) or header_size != HEADER.size:
        raise ResourceError("room visual magic, schema, or header size differs")
    if pixel_format != PIXEL_FORMAT_INDEX8 or palette_format != PALETTE_FORMAT_RGB8:
        raise ResourceError("room visual format is unsupported")
    if expected_room is not None and room != expected_room:
        raise ResourceError("room visual room identity differs")
    if width <= 0 or height <= 0 or pitch < width or palette_count != 256:
        raise ResourceError("room visual dimensions, pitch, or palette count differ")
    row_count = height if version == VERSION else (pitch + STRIP_WIDTH - 1) // STRIP_WIDTH
    expected_rows = row_count * ROW.size
    if palette_offset != HEADER.size or row_directory_offset != palette_offset + 768:
        raise ResourceError("room visual palette or row-directory offset differs")
    if pixel_offset != row_directory_offset + expected_rows:
        raise ResourceError("room visual pixel offset differs")
    expected_length = pitch * height if version == VERSION else row_count * STRIP_WIDTH * height
    if pixel_length != expected_length or pixel_offset + pixel_length != len(data):
        raise ResourceError("room visual pixel bounds differ")
    for index in range(row_count):
        offset, length = ROW.unpack_from(data, row_directory_offset + index * ROW.size)
        stride = pitch if version == VERSION else STRIP_WIDTH * height
        valid_length = (width <= length and offset + length <= len(data)
                        if version == VERSION else length == stride)
        if offset != pixel_offset + index * stride or not valid_length:
            raise ResourceError("room visual row directory is malformed")
    palette = bytes(data[palette_offset:row_directory_offset])
    pixels = bytes(data[pixel_offset:])
    if version == STRIP_VERSION:
        logical = bytearray(pitch * height)
        for strip in range(row_count):
            width_here = min(STRIP_WIDTH, pitch - strip * STRIP_WIDTH)
            for y in range(height):
                start = (strip * height + y) * STRIP_WIDTH
                if any(pixels[start + width_here:start + STRIP_WIDTH]):
                    raise ResourceError("room visual strip padding is not canonical zero")
                dest = y * pitch + strip * STRIP_WIDTH
                logical[dest:dest + width_here] = pixels[start:start + width_here]
        pixels = bytes(logical)
    if _sha(palette) != palette_hash or _sha(pixels) != pixel_hash:
        raise ResourceError("room visual decoded payload identity differs")
    mutable = bytearray(data)
    mutable[HEADER.size - 32 : HEADER.size] = bytes(32)
    if _sha(mutable) != record_hash:
        raise ResourceError("room visual complete record identity differs")
    return CookedRoomVisual(
        room, width, height, pitch, palette, pixels,
        archive_hash.hex(), index_hash.hex(), data_hash.hex(), room_hash.hex(),
        palette_hash.hex(), pixel_hash.hex(), _sha(data).hex(),
    )


def project_room_visual(
    data: bytes,
    *,
    target_width: int,
    target_height: int,
    reserved_bottom: int = 0,
) -> tuple[bytes, dict[str, int | str]]:
    """Project an indexed source room onto a bounded target surface.

    The complete source image is aspect-fit with nearest-neighbour sampling;
    unused target rows/columns use palette index zero.  This preserves source
    palette indices and never invents colors.  The returned SC5VIS record
    retains the original source provenance while its pixel digest describes
    the deterministic target-surface projection.
    """
    visual = decode_room_visual(data)
    if target_width <= 0 or target_height <= 0:
        raise ResourceError("room visual target dimensions must be positive")

    if type(reserved_bottom) is not int or not 0 <= reserved_bottom < target_height:
        raise ResourceError("reserved text viewport is outside target surface")
    viewport_height = target_height - reserved_bottom

    # Compare rational scale factors without floating-point rounding.
    if target_width * visual.height <= viewport_height * visual.width:
        content_width = target_width
        content_height = max(1, visual.height * target_width // visual.width)
    else:
        content_height = viewport_height
        content_width = max(1, visual.width * viewport_height // visual.height)
    offset_x = (target_width - content_width) // 2
    offset_y = (viewport_height - content_height) // 2

    pixels = bytearray(target_width * target_height)
    for out_y in range(content_height):
        source_y = min(
            visual.height - 1,
            (2 * out_y + 1) * visual.height // (2 * content_height),
        )
        source_row = source_y * visual.pitch
        target_row = (offset_y + out_y) * target_width + offset_x
        for out_x in range(content_width):
            source_x = min(
                visual.width - 1,
                (2 * out_x + 1) * visual.width // (2 * content_width),
            )
            pixels[target_row + out_x] = visual.pixels[source_row + source_x]

    projected = encode_room_visual(
        room=visual.room,
        width=target_width,
        height=target_height,
        pitch=target_width,
        palette=visual.palette,
        pixels=bytes(pixels),
        archive_sha256=visual.archive_sha256,
        index_sha256=visual.index_sha256,
        data_sha256=visual.data_sha256,
        room_sha256=visual.room_sha256,
    )
    return projected, {
        **({"reserved_bottom": reserved_bottom} if reserved_bottom else {}),
        "source_width": visual.width,
        "source_height": visual.height,
        "source_pitch": visual.pitch,
        "source_pixels_sha256": visual.decoded_pixels_sha256,
        "target_width": target_width,
        "target_height": target_height,
        "content_width": content_width,
        "content_height": content_height,
        "offset_x": offset_x,
        "offset_y": offset_y,
        "sampling": "nearest_neighbor_aspect_fit",
        "border_palette_index": 0,
    }


def encode_camera_room_visual(data: bytes) -> tuple[bytes, list[dict[str, int | str]]]:
    """SC5VIS v2: the same logical image in independently checked 8px strips.

    SAMEPKG and the source codecs are unchanged. v1 remains readable. No crop,
    resize, palette conversion, or duplicate full-image payload is stored.
    The existing header pixel hash identifies reconstructed logical rows;
    the record hash covers the physical directory, strips and canonical padding.
    Runtime per-strip CRCs additionally permit bounded checked reads.
    """
    visual = decode_room_visual(data)
    if STRIP_WIDTH * visual.height > 3132:
        raise ResourceError("camera strip exceeds native pending scratch capacity")
    count = (visual.pitch + STRIP_WIDTH - 1) // STRIP_WIDTH
    palette_offset = HEADER.size
    directory_offset = palette_offset + 768
    pixel_offset = directory_offset + count * ROW.size
    payload = bytearray()
    descriptors = []
    for strip in range(count):
        body = bytearray()
        x = strip * STRIP_WIDTH
        width_here = min(STRIP_WIDTH, visual.pitch - x)
        for y in range(visual.height):
            body.extend(visual.pixels[y * visual.pitch + x:y * visual.pitch + x + width_here])
            body.extend(bytes(STRIP_WIDTH - width_here))
        descriptors.append(dict(index=strip, x=x, width=width_here,
                                offset=pixel_offset + len(payload), length=len(body),
                                crc32=f"{zlib.crc32(body) & 0xffffffff:08x}",
                                sha256=_sha(body).hex()))
        payload.extend(body)
    header = HEADER.pack(
        MAGIC, STRIP_VERSION, HEADER.size, PIXEL_FORMAT_INDEX8, PALETTE_FORMAT_RGB8,
        visual.room, visual.width, visual.height, visual.pitch, 256,
        palette_offset, directory_offset, pixel_offset, len(payload),
        *(bytes.fromhex(h) for h in (visual.archive_sha256, visual.index_sha256,
                                    visual.data_sha256, visual.room_sha256)),
        _sha(visual.palette), _sha(visual.pixels), bytes(32),
    )
    result = bytearray(header + visual.palette + b"".join(
        ROW.pack(d["offset"], d["length"]) for d in descriptors) + payload)
    result[HEADER.size - 32:HEADER.size] = _sha(result)
    return bytes(result), descriptors


def camera_viewport(visual: CookedRoomVisual, *, xstart: int, ycenter: int = 100,
                    width: int = 256, height: int = 224, reserved_bottom: int = 32
                    ) -> tuple[bytes, dict[str, int]]:
    """Host oracle for the existing 320px SCUMM camera on a bounded display.

    World coordinates and pixels are not scaled. Short rooms are centered in
    the scene area; the bottom interface is separate. Clamp only at room edges.
    """
    if not 0 < width <= 320 or not 0 <= reserved_bottom < height <= 224:
        raise ResourceError("invalid camera viewport")
    cw, ch = min(width, visual.width), min(height - reserved_bottom, visual.height)
    sx = max(0, min(visual.width - cw, xstart + (320 - width) // 2))
    sy = max(0, min(visual.height - ch, ycenter - ch // 2))
    dx, dy = (width - cw) // 2, (height - reserved_bottom - ch) // 2
    pixels = bytearray(width * height)
    for y in range(ch):
        start = (sy + y) * visual.pitch + sx
        dest = (dy + y) * width + dx
        pixels[dest:dest + cw] = visual.pixels[start:start + cw]
    return bytes(pixels), dict(source_x=sx, source_y=sy, dest_x=dx, dest_y=dy,
                              copy_width=cw, copy_height=ch)
