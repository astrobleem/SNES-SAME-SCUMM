"""Versioned source-neutral cooked SCUMM room visuals.

The record deliberately contains decoded linear INDEX8 rows and RGB8 palette
bytes.  Target generators may segment rows for their mapper, but the record is
not a target framebuffer, crop, tile image, or precomposed screen.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

from ...errors import ResourceError


MAGIC = b"SC5VIS\0\0"
VERSION = 1
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
    if magic != MAGIC or version != VERSION or header_size != HEADER.size:
        raise ResourceError("room visual magic, schema, or header size differs")
    if pixel_format != PIXEL_FORMAT_INDEX8 or palette_format != PALETTE_FORMAT_RGB8:
        raise ResourceError("room visual format is unsupported")
    if expected_room is not None and room != expected_room:
        raise ResourceError("room visual room identity differs")
    if width <= 0 or height <= 0 or pitch < width or palette_count != 256:
        raise ResourceError("room visual dimensions, pitch, or palette count differ")
    expected_rows = height * ROW.size
    if palette_offset != HEADER.size or row_directory_offset != palette_offset + 768:
        raise ResourceError("room visual palette or row-directory offset differs")
    if pixel_offset != row_directory_offset + expected_rows:
        raise ResourceError("room visual pixel offset differs")
    if pixel_length != pitch * height or pixel_offset + pixel_length != len(data):
        raise ResourceError("room visual pixel bounds differ")
    for y in range(height):
        offset, length = ROW.unpack_from(data, row_directory_offset + y * ROW.size)
        if offset != pixel_offset + y * pitch or length < width or offset + length > len(data):
            raise ResourceError("room visual row directory is malformed")
    palette = bytes(data[palette_offset:row_directory_offset])
    pixels = bytes(data[pixel_offset:])
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
