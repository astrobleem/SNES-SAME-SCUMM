"""Lossless transfer planning for poses from SAME's costume decoder.

The planner preserves source palette slots, signed foot-anchor coordinates,
column-major cel samples, cumulative limb offsets, and painter's order.  It is
an adapter for the existing SC5ACT package and video surface, not a renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping, Protocol, Sequence
import zlib


class PoseError(ValueError):
    pass


class CelLike(Protocol):
    width: int
    height: int
    relative_x: int
    relative_y: int
    move_x: int
    move_y: int
    pixels: bytes


class PoseLike(Protocol):
    draw_to_right: bool
    cels: Iterable[CelLike]


@dataclass(frozen=True)
class Span:
    x: int
    y: int
    slots: bytes


@dataclass(frozen=True)
class SpanRef:
    x: int
    y: int
    offset: int
    length: int


@dataclass(frozen=True)
class Chunk:
    data: bytes
    spans: tuple[SpanRef, ...]
    crc32: int
    sha256: str


@dataclass(frozen=True)
class PosePlan:
    bounds: tuple[int, int, int, int]
    spans: tuple[Span, ...]
    palette: tuple[int, ...]
    opaque_pixels: int

    def chunks(self, capacity: int = 2048) -> tuple[Chunk, ...]:
        if (not isinstance(capacity, int) or isinstance(capacity, bool)
                or not 1 <= capacity <= 2048):
            raise PoseError('transfer capacity must be 1..2048')
        result: list[Chunk] = []
        payload = bytearray()
        refs: list[SpanRef] = []

        def flush() -> None:
            if payload:
                raw = bytes(payload)
                result.append(Chunk(raw, tuple(refs), zlib.crc32(raw) & 0xffffffff,
                                    sha256(raw).hexdigest()))
                payload.clear()
                refs.clear()

        for span in self.spans:
            consumed = 0
            while consumed < len(span.slots):
                if len(payload) == capacity:
                    flush()
                count = min(capacity - len(payload), len(span.slots) - consumed)
                refs.append(SpanRef(span.x + consumed, span.y, len(payload), count))
                payload.extend(span.slots[consumed:consumed + count])
                consumed += count
        flush()
        return tuple(result)


def _integer(value: int, lo: int, hi: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not lo <= value <= hi:
        raise PoseError(f'{label} must be an integer in {lo}..{hi}')
    return value


def compile_pose(pose: PoseLike, palette: Sequence[int], *,
                 max_decoded_samples: int = 4_194_304) -> PosePlan:
    """Flatten an unscaled decoded pose without a fixed crop or anchor shift."""
    if not 1 <= len(palette) <= 256:
        raise PoseError('palette must contain 1..256 entries')
    colors = tuple(_integer(v, 0, 255, 'palette value') for v in palette)
    _integer(max_decoded_samples, 1, 16_777_216, 'sample budget')
    painted: dict[tuple[int, int], int] = {}
    dx = dy = samples = 0
    direction = 1 if pose.draw_to_right else -1
    for cel in pose.cels:
        width = _integer(cel.width, 1, 512, 'cel width')
        height = _integer(cel.height, 1, 512, 'cel height')
        samples += width * height
        if samples > max_decoded_samples:
            raise PoseError('decoded pose exceeds host sample budget')
        raw = bytes(cel.pixels)
        if len(raw) != width * height:
            raise PoseError('cel pixel length differs from width * height')
        rx = dx + _integer(cel.relative_x, -32768, 32767, 'relative_x')
        ry = dy + _integer(cel.relative_y, -32768, 32767, 'relative_y')
        for x in range(width):
            for y in range(height):
                slot = raw[x * height + y]
                if slot == 0:
                    continue
                if slot >= len(colors):
                    raise PoseError('source color slot exceeds costume palette')
                px, py = direction * (rx + x), ry + y
                if not -32768 <= px <= 32767 or not -32768 <= py <= 32767:
                    raise PoseError('pose coordinate exceeds signed 16-bit descriptor')
                painted[px, py] = slot
        dx += _integer(cel.move_x, -32768, 32767, 'move_x')
        dy -= _integer(cel.move_y, -32768, 32767, 'move_y')
    if not painted:
        return PosePlan((0, 0, 0, 0), (), colors, 0)
    rows: dict[int, list[tuple[int, int]]] = {}
    for (x, y), slot in painted.items():
        rows.setdefault(y, []).append((x, slot))
    spans: list[Span] = []
    for y, entries in sorted(rows.items()):
        entries.sort()
        start = previous = entries[0][0]
        data = bytearray((entries[0][1],))
        for x, slot in entries[1:]:
            if x != previous + 1:
                spans.append(Span(start, y, bytes(data)))
                start, data = x, bytearray()
            data.append(slot)
            previous = x
        spans.append(Span(start, y, bytes(data)))
    xs, ys = zip(*painted)
    return PosePlan((min(xs), min(ys), max(xs) + 1, max(ys) + 1),
                    tuple(spans), colors, len(painted))


def validate_chunk(chunk: Chunk, palette_size: int, *, capacity: int = 2048) -> None:
    if not 1 <= len(chunk.data) <= capacity <= 2048:
        raise PoseError('chunk length exceeds checked transfer capacity')
    if (zlib.crc32(chunk.data) & 0xffffffff) != chunk.crc32:
        raise PoseError('pose chunk CRC mismatch')
    if sha256(chunk.data).hexdigest() != chunk.sha256:
        raise PoseError('pose chunk identity mismatch')
    cursor = 0
    for ref in chunk.spans:
        if (ref.offset != cursor or ref.length <= 0
                or ref.offset + ref.length > len(chunk.data)):
            raise PoseError('noncanonical span coverage')
        if not -32768 <= ref.x <= 32767 or not -32768 <= ref.y <= 32767:
            raise PoseError('invalid signed span origin')
        if ref.x + ref.length - 1 > 32767:
            raise PoseError('span end exceeds signed coordinate range')
        cursor += ref.length
    if cursor != len(chunk.data):
        raise PoseError('span descriptors do not cover checked payload')
    if any(slot == 0 or slot >= palette_size for slot in chunk.data):
        raise PoseError('opaque spans contain an invalid source palette slot')


def visible_runs(chunk: Chunk, palette: Sequence[int], *, anchor_x: int,
                 anchor_y: int, width: int, height: int,
                 palette_overrides: Mapping[int, int] | None = None
                 ) -> tuple[tuple[int, int, bytes], ...]:
    validate_chunk(chunk, len(palette))
    _integer(width, 1, 65535, 'surface width')
    _integer(height, 1, 65535, 'surface height')
    colors = [_integer(v, 0, 255, 'palette value') for v in palette]
    for slot, color in (palette_overrides or {}).items():
        _integer(slot, 0, len(colors) - 1, 'override slot')
        colors[slot] = _integer(color, 0, 255, 'override color')
    runs = []
    for ref in chunk.spans:
        y, x = anchor_y + ref.y, anchor_x + ref.x
        if not 0 <= y < height:
            continue
        left, right = max(0, x), min(width, x + ref.length)
        if left >= right:
            continue
        begin = ref.offset + left - x
        slots = chunk.data[begin:begin + right - left]
        runs.append((left, y, bytes(colors[slot] for slot in slots)))
    return tuple(runs)


def render_reference(background: bytes, width: int, height: int, plan: PosePlan,
                     *, anchor_x: int, anchor_y: int,
                     palette_overrides: Mapping[int, int] | None = None) -> bytes:
    if len(background) != width * height:
        raise PoseError('background size differs from dimensions')
    chunks = plan.chunks()
    for chunk in chunks:
        validate_chunk(chunk, len(plan.palette))
    output = bytearray(background)
    for chunk in chunks:
        for x, y, pixels in visible_runs(chunk, plan.palette, anchor_x=anchor_x,
                                        anchor_y=anchor_y, width=width, height=height,
                                        palette_overrides=palette_overrides):
            start = y * width + x
            output[start:start + len(pixels)] = pixels
    return bytes(output)
