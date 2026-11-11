"""Source-neutral cooked SCUMM v5 charset records."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib

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
    version: int = 1
    bits_per_pixel: int = 1
    color_map: bytes = bytes(16)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()


def encode_charset(
    source: bytes,
    *,
    logical_id: int,
    source_id: int,
    font_height: int | None = None,
    baseline: int | None = None,
    line_spacing: int | None = None,
    version: int = 1,
) -> bytes:
    if version == 2:
        return _encode_multibit(source, logical_id, source_id, font_height, baseline, line_spacing)
    font_height = 8 if font_height is None else font_height
    baseline = 7 if baseline is None else baseline
    line_spacing = 8 if line_spacing is None else line_spacing
    if version != 1:
        raise ValueError("unsupported SC5FNT version")
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
    if len(data) >= 7 and data[:6] == MAGIC and data[6] == 2:
        return _decode_multibit(data, expected_logical_id)
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


# V2 retains the V1 identity header, followed by 16 source-slot colors and a
# fixed glyph directory. Advances are signed words (width + signed bearing).
# Glyph payloads are packed MSB-first with no row padding; a trailing CRC32
# covers header, map, directory and payload. Runtime palette overrides are NOT
# baked into these immutable source slots. V1 native consumers remain V1-only.
_GLYPH2 = struct.Struct("<BhBBbbII")
_MAX_V2_SIZE = _HEADER.size + 16 + 256 * _GLYPH2.size + 256 * ((255 * 255 * 4 + 7) // 8) + 4


def _encode_multibit(source, logical_id, source_id, height, baseline, spacing):
    decoded = ScummV5Charset(source, key=f"charset.{source_id}", allow_multibit=True)
    height = (source[22] if decoded._base == 21 else 8) if height is None else height
    baseline = max(0, height-1) if baseline is None else baseline
    spacing = height if spacing is None else spacing
    if not all(isinstance(v, int) and 0 <= v <= 255
               for v in (logical_id, source_id, height, baseline, spacing)):
        raise ValueError("SC5FNT scalar is outside u8")
    if height == 0 or spacing == 0:
        raise ValueError("SC5FNT v2 height and line spacing must be positive")
    bpp = decoded.bits_per_pixel
    # Classic resource.cpp loadCharset uses resource+14..28; our provider
    # strips its eight-byte chunk header, hence source+6..20. Synthetic legacy
    # wrappers have their 15 colors directly after the size word.
    colors = bytes([0]) + (source[6:21] if decoded._base == 21 else source[4:19])
    table, payload = bytearray(), bytearray()
    start = _HEADER.size + 16 + GLYPH_COUNT * _GLYPH2.size
    for code in range(GLYPH_COUNT):
        g = decoded.glyph(code)
        if g is None:
            table.extend(bytes(_GLYPH2.size))
            continue
        packed = bytearray((len(g.pixels) * bpp + 7) // 8)
        for n, slot in enumerate(g.pixels):
            packed[n*bpp//8] |= slot << (8-bpp-(n*bpp % 8))
        table.extend(_GLYPH2.pack(1, g.width + g.x_offset, g.width, g.height,
                                 g.x_offset, g.y_offset, start+len(payload), len(packed)))
        payload.extend(packed)
    total = start + len(payload) + 4
    raw = (_HEADER.pack(MAGIC, 2, logical_id, source_id, bpp, height, GLYPH_COUNT,
                        baseline | spacing << 8, len(source), total,
                        hashlib.sha256(source).digest()) + colors + table + payload)
    return raw + struct.pack("<I", zlib.crc32(raw))


def _decode_multibit(data, expected):
    data = bytes(data)
    start = _HEADER.size + 16 + GLYPH_COUNT * _GLYPH2.size
    if not start+4 <= len(data) <= _MAX_V2_SIZE:
        raise ResourceError("SC5FNT v2 size is invalid")
    magic, version, logical, source, bpp, height, count, metrics, length, total, sha = _HEADER.unpack_from(data)
    if (magic != MAGIC or version != 2 or bpp not in (1, 2, 4) or count != 256
            or total != len(data) or not 1 <= height <= 255
            or metrics > 65535 or metrics >> 8 == 0):
        raise ResourceError("SC5FNT v2 header is invalid")
    if expected is not None and logical != expected:
        raise ResourceError("SC5FNT logical charset identity differs")
    if zlib.crc32(data[:-4]) != struct.unpack_from("<I", data, len(data)-4)[0]:
        raise ResourceError("SC5FNT v2 CRC differs")
    colors = data[_HEADER.size:_HEADER.size+16]
    if colors[0] != 0:
        raise ResourceError("SC5FNT v2 transparent slot metadata is invalid")
    glyphs, cursor = [], start
    for code in range(256):
        values = _GLYPH2.unpack_from(data, _HEADER.size+16+code*_GLYPH2.size)
        present, advance, width, h, x, y, offset, size = values
        if not present:
            if any(values): raise ResourceError("SC5FNT v2 absent glyph has metadata")
            glyphs.append(None)
            continue
        needed = (width*h*bpp+7)//8
        if (present != 1 or advance != width+x
                or offset != cursor or size != needed or cursor+size > len(data)-4):
            raise ResourceError(f"SC5FNT v2 glyph {code} is invalid")
        packed = data[cursor:cursor+size]
        used = width*h*bpp % 8
        if used and packed[-1] & ((1 << (8-used))-1):
            raise ResourceError("SC5FNT v2 noncanonical padding")
        pixels = bytes((packed[n*bpp//8] >> (8-bpp-n*bpp%8)) & ((1<<bpp)-1)
                       for n in range(width*h))
        glyphs.append(CookedGlyph(code, advance, width, h, x, y, pixels))
        cursor += size
    if cursor != len(data)-4:
        raise ResourceError("SC5FNT v2 unclaimed payload")
    return CookedCharset(logical, source, height, metrics&255, metrics>>8,
                          length, sha, tuple(glyphs), bytes(data), 2, bpp, colors)


def raster_glyph(font: CookedCharset, code: int, *, ink: int, x: int, y: int,
                 width: int, height: int, color_map: bytes | None = None) -> tuple[bytes, bytes]:
    """Bounded glyph oracle: separate INDEX8 and opacity, including opaque zero.

    x/y are pen coordinates. This is glyph rasterization, not SCUMM string
    control interpretation; unknown characters fail instead of substitution.
    """
    if not 0 < width <= 256 or not 0 < height <= 224 or not 0 <= ink <= 255:
        raise ResourceError("glyph raster bounds/style invalid")
    if not 0 <= code <= 255 or font.glyphs[code] is None:
        raise ResourceError("glyph is absent")
    colors = bytearray(font.color_map if color_map is None else color_map)
    if len(colors) != 16:
        raise ResourceError("charset color map must have 16 entries")
    colors[1] = ink
    g = font.glyphs[code]
    pixels, opaque = bytearray(width*height), bytearray(width*height)
    for row in range(g.height):
        for col in range(g.width):
            slot = g.pixels[row*g.width+col]
            dx, dy = x+g.x_origin+col, y+g.y_origin+row
            if slot and 0 <= dx < width and 0 <= dy < height:
                pixels[dy*width+dx] = colors[slot]
                opaque[dy*width+dx] = 1
    return bytes(pixels), bytes(opaque)
