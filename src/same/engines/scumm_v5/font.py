"""Source-neutral cooked SCUMM v5 charset records."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

from ...errors import ResourceError
from .video import ScummV5Charset


MAGIC = b"SC5FNT"
VERSION = 1
GLYPH_COUNT = 256
_HEADER = struct.Struct("<6sBBBBHHIII32s")
_GLYPH = struct.Struct("<BBBBbbII")


@dataclass(frozen=True, slots=True)
class CookedGlyph:
    code: int
    advance: int
    width: int
    height: int
    x_origin: int
    y_origin: int
    pixels: bytes


@dataclass(frozen=True, slots=True)
class CookedCharset:
    logical_id: int
    source_id: int
    font_height: int
    baseline: int
    line_spacing: int
    source_length: int
    source_sha256: bytes
    glyphs: tuple[CookedGlyph | None, ...]
    raw: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()


def encode_charset(
    source: bytes,
    *,
    logical_id: int,
    source_id: int,
    font_height: int = 8,
    baseline: int = 7,
    line_spacing: int = 8,
) -> bytes:
    if not all(0 <= value <= 255 for value in
               (logical_id, source_id, font_height, baseline, line_spacing)):
        raise ValueError("SC5FNT scalar is outside u8")
    decoded = ScummV5Charset(source, key=f"charset.{source_id}")
    table = bytearray()
    payload = bytearray()
    payload_base = _HEADER.size + GLYPH_COUNT * _GLYPH.size
    for code in range(GLYPH_COUNT):
        glyph = decoded.glyph(code)
        if glyph is None:
            table.extend(_GLYPH.pack(0, 0, 0, 0, 0, 0, 0, 0))
            continue
        # Schema 1 stores the decoded one-bit coverage as bounded mask bytes.
        # This remains source-neutral while avoiding a second bit-addressing
        # interpretation in the constrained target rasterizer.
        packed = bytearray(glyph.pixels)
        offset = payload_base + len(payload)
        table.extend(_GLYPH.pack(1, glyph.advance, glyph.width, glyph.height,
                                 glyph.x_offset, glyph.y_offset, offset, len(packed)))
        payload.extend(packed)
    total = payload_base + len(payload)
    return (_HEADER.pack(MAGIC, VERSION, logical_id, source_id, 1, font_height,
                         GLYPH_COUNT, baseline | line_spacing << 8, len(source), total,
                         hashlib.sha256(source).digest()) + table + payload)


def decode_charset(data: bytes, *, expected_logical_id: int | None = None) -> CookedCharset:
    if len(data) < _HEADER.size + GLYPH_COUNT * _GLYPH.size:
        raise ResourceError("SC5FNT record is truncated")
    magic, version, logical_id, source_id, bpp, font_height, count, metrics, source_length, total, source_sha = _HEADER.unpack_from(data)
    if magic != MAGIC or version != VERSION or bpp != 1 or count != GLYPH_COUNT or total != len(data):
        raise ResourceError("SC5FNT header is invalid")
    if expected_logical_id is not None and logical_id != expected_logical_id:
        raise ResourceError("SC5FNT logical charset identity differs")
    glyphs: list[CookedGlyph | None] = []
    table_end = _HEADER.size + GLYPH_COUNT * _GLYPH.size
    for code in range(GLYPH_COUNT):
        present, advance, width, height, x, y, offset, length = _GLYPH.unpack_from(data, _HEADER.size + code * _GLYPH.size)
        if not present:
            if any((advance, width, height, x, y, offset, length)):
                raise ResourceError("SC5FNT absent glyph has metadata")
            glyphs.append(None); continue
        needed = width * height
        if not 1 <= advance <= 64 or width > 64 or height > 64 or length != needed or offset < table_end or offset + length > len(data):
            raise ResourceError(f"SC5FNT glyph {code} is invalid")
        packed = data[offset:offset + length]
        if any(value not in (0, 1) for value in packed):
            raise ResourceError(f"SC5FNT glyph {code} mask is invalid")
        pixels = bytes(packed)
        glyphs.append(CookedGlyph(code, advance, width, height, x, y, pixels))
    return CookedCharset(logical_id, source_id, font_height, metrics & 0xFF,
                          metrics >> 8, source_length, source_sha, tuple(glyphs), bytes(data))
