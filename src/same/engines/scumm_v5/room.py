"""Strict raw and cooked SCUMM v5 room decoding and presentation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import struct
from typing import Callable, Mapping

from ...engine import EngineContext
from ...errors import ResourceError
from ...video import IndexedSurface, Rect
from .costume import ScummV5Costume

_COOKED_HEADER = struct.Struct("<4sBHHH")
_COOKED_MAGIC = b"SC5R"
_COOKED_VERSION = 1
_CHUNK_HEADER_SIZE = 8
_MAX_ROOM_SIZE = 2048

# Canonical phase order used by classic costumes for scaled offsets and source
# reduction. Horizontal reduction deliberately permits later source columns to
# overwrite an unadvanced destination column.
_COSTUME_SCALE_TABLE = bytes.fromhex(
    "fffd7dbd3ddd5d9d1ded6dad2dcd4d8d0df575b535d5559515e565a525c54585"
    "05f979b939d9599919e969a929c9498909f171b131d1519111e161a121c14181"
    "01fb7bbb3bdb5b9b1beb6bab2bcb4b8b0bf373b333d3539313e363a323c34383"
    "03f777b737d7579717e767a727c7478707ef6faf2fcf4f8f0fdf5f9f1fbf3f7f"
    "008040c020a060e0109050d030b070f0088848c828a868e8189858d838b878f8"
    "048444c424a464e4149454d434b474f40c8c4ccc2cac6cec1c9c5cdc3cbc7cfc"
    "028242c222a262e2129252d232b272f20a8a4aca2aaa6aea1a9a5ada3aba7afa"
    "068646c626a666e6169656d636b676f60e8e4ece2eae6eee1e9e5ede3ebe7efe"
)


def _scaled_cel_origin(
    actor_x: int,
    actor_y: int,
    x_move: int,
    y_move: int,
    scale_x: int,
    scale_y: int,
    draw_to_right: bool,
) -> tuple[int, int, int, int]:
    """Mirror classic paintCelByleRLECommon's scaled anchor arithmetic."""
    x_step = -1
    x_distance = x_move
    if x_distance < 0:
        x_distance = -x_distance
        x_step = 1
    if draw_to_right:
        x_index = (128 - x_distance) & 0xFF
        for offset in range(x_distance):
            if _COSTUME_SCALE_TABLE[(x_index + offset) & 0xFF] < scale_x:
                actor_x -= x_step
    else:
        x_index = (128 + x_distance) & 0xFF
        for offset in range(x_distance):
            if _COSTUME_SCALE_TABLE[(x_index - offset) & 0xFF] < scale_x:
                actor_x += x_step

    y_step = -1
    y_distance = y_move
    if y_distance < 0:
        y_distance = -y_distance
        y_step = 1
    y_index = (128 - y_distance) & 0xFF
    for offset in range(y_distance):
        if _COSTUME_SCALE_TABLE[(y_index + offset) & 0xFF] < scale_y:
            actor_y -= y_step
    return actor_x, actor_y, x_index, y_index

_BASIC_VERTICAL = frozenset((*range(14, 19), *range(34, 39)))
_BASIC_HORIZONTAL = frozenset((*range(24, 29), *range(44, 49)))
_MAJOR_MINOR = frozenset(
    (*range(64, 69), *range(84, 89), *range(104, 109), *range(124, 129))
)
_TRANSPARENT = frozenset((*range(34, 39), *range(44, 49), *range(84, 89), *range(124, 129)))
_SUPPORTED_CODECS = frozenset((1, *_BASIC_VERTICAL, *_BASIC_HORIZONTAL, *_MAJOR_MINOR))


def _trunc_div(numerator: int, denominator: int) -> int:
    quotient = abs(numerator) // abs(denominator)
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def _closest_point_on_line(
    start: tuple[int, int], end: tuple[int, int], point: tuple[int, int]
) -> tuple[int, int]:
    start_x, start_y = start
    end_x, end_y = end
    point_x, point_y = point
    x_delta, y_delta = end_x - start_x, end_y - start_y
    if end_x == start_x:
        result_x, result_y = start_x, point_y
    elif end_y == start_y:
        result_x, result_y = point_x, start_y
    else:
        distance = x_delta * x_delta + y_delta * y_delta
        if abs(x_delta) > abs(y_delta):
            a = _trunc_div(start_x * y_delta, x_delta)
            b = _trunc_div(point_x * x_delta, y_delta)
            c = _trunc_div(
                (a + b - start_y + point_y) * y_delta * x_delta, distance
            )
            result_x = c
            result_y = _trunc_div(c * y_delta, x_delta) - a + start_y
        else:
            a = _trunc_div(start_y * x_delta, y_delta)
            b = _trunc_div(point_y * y_delta, x_delta)
            c = _trunc_div(
                (a + b - start_x + point_x) * y_delta * x_delta, distance
            )
            result_x = _trunc_div(c * x_delta, y_delta) - a + start_x
            result_y = c
    if abs(y_delta) < abs(x_delta):
        if (x_delta > 0 and result_x < start_x) or (x_delta < 0 and result_x > start_x):
            return start
        if (x_delta > 0 and result_x > end_x) or (x_delta < 0 and result_x < end_x):
            return end
    else:
        if (y_delta > 0 and result_y < start_y) or (y_delta < 0 and result_y > start_y):
            return start
        if (y_delta > 0 and result_y > end_y) or (y_delta < 0 and result_y < end_y):
            return end
    return result_x, result_y


def _v5_point_in_box_bounds(
    points: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]],
    x: int,
    y: int,
) -> tuple[int, int, int]:
    """Return classic v5's adjusted point and coarse actor-coordinate distance.

    This mirrors ``checkXYInBoxBounds`` rather than using Euclidean polygon
    projection.  The original uses an 8x2 actor-coordinate distance and a
    binary search along sloping box sides; those details affect which box wins.
    """
    ul, ur, lr, ll = points
    if y < ul[1]:
        dest_y, x_min, x_max = ul[1], ul[0], ur[0]
    elif y >= ll[1]:
        dest_y, x_min, x_max = ll[1], ll[0], lr[0]
    elif x >= ul[0] and x >= ll[0] and x < ur[0] and x < lr[0]:
        dest_y = y
        x_min = x_max = x
    else:
        dest_y = y
        upper_left, lower_left = ul[0], ll[0]
        upper_right, lower_right = ur[0], lr[0]
        top, bottom = ul[1], ll[1]
        while True:
            x_min = _trunc_div(upper_left + lower_left, 2)
            x_max = _trunc_div(upper_right + lower_right, 2)
            current_y = _trunc_div(top + bottom, 2)
            if current_y < y:
                top, upper_left, upper_right = current_y, x_min, x_max
            elif current_y > y:
                bottom, lower_left, lower_right = current_y, x_min, x_max
            else:
                break
    dest_x = min(max(x, x_min), x_max)
    x_distance = abs(x - dest_x)
    y_distance = abs(y - dest_y) // 4
    distance = (
        (x_distance // 2) + y_distance
        if x_distance < y_distance
        else (y_distance // 2) + x_distance
    )
    return dest_x, dest_y, distance


@dataclass(frozen=True, slots=True)
class ScummV5Room:
    width: int
    height: int
    palette: tuple[tuple[int, int, int], ...]
    pixels: bytes
    transparent_index: int
    source_format: str
    strip_codecs: tuple[int, ...]
    zplanes: tuple[bytes, ...]
    walkboxes: tuple["ScummV5Walkbox", ...]
    box_routes: tuple[tuple[int | None, ...], ...]
    objects: tuple["ScummV5RoomObject", ...]
    entry_script: bytes | None
    exit_script: bytes | None
    local_scripts: tuple[tuple[int, bytes], ...]

    def next_box(self, source: int, destination: int) -> int | None:
        if source == destination and 0 <= source < len(self.walkboxes):
            return destination
        if not (
            0 <= source < len(self.box_routes)
            and 0 <= destination < len(self.walkboxes)
        ):
            return None
        return self.box_routes[source][destination]

    def hit_test_object(
        self,
        x: int,
        y: int,
        *,
        object_states: Mapping[int, int] | None = None,
        object_owners: Mapping[int, int] | None = None,
    ) -> "ScummV5RoomObject | None":
        """Return the frontmost selectable CDHD containing a room point.

        SCUMM v5 searches local objects in resource order (the first matching
        record wins).  Parent-state visibility is part of the CDHD semantics;
        CDHD flag $80 means parent state 1, otherwise the low nibble is the
        required parent state.  A CDHD flag is not a generic hidden bit.
        """
        for item in self.objects:
            if not item.selectable or not item.contains_point(x, y):
                continue
            if object_states is not None and not self._parent_chain_visible(item, object_states):
                continue
            if object_owners is not None and object_owners.get(item.object_id, 0):
                continue
            return item
        return None

    def _parent_chain_visible(
        self,
        item: "ScummV5RoomObject",
        object_states: Mapping[int, int],
    ) -> bool:
        """Apply the v5 CDHD parent-state chain for one local object."""
        index = self.objects.index(item) + 1
        depth = 0
        while item.parent:
            if not 1 <= item.parent <= len(self.objects):
                return False
            parent = self.objects[item.parent - 1]
            required = 1 if item.flags == 0x80 else item.flags & 0x0F
            if object_states.get(parent.object_id, 0) & 0x0F != required:
                return False
            item = parent
            index = item.parent
            depth += 1
            if depth > len(self.objects):
                return False
        return True

    def adjust_point(self, x: int, y: int) -> tuple[tuple[int, int], int]:
        """Apply the v5 walk-box destination adjustment, newest box first."""
        usable = tuple(box for box in reversed(self.walkboxes[1:]) if not box.flags & 0x80)
        for box in usable:
            if box.contains(x, y):
                return (x, y), box.index
        best_point, best_box, best_distance = (x, y), 0xFF, None
        for box in usable:
            point = box.closest_point(x, y)
            distance = (x - point[0]) ** 2 + (y - point[1]) ** 2
            if best_distance is None or distance < best_distance:
                best_point, best_box, best_distance = point, box.index, distance
        return best_point, best_box

    def adjust_actor_point_v5(
        self, x: int, y: int, *, ignore_boxes: bool = False
    ) -> tuple[tuple[int, int], int]:
        """Mirror v5 ``Actor::adjustXYToBeInBox`` for actor placement."""
        if ignore_boxes:
            return (x, y), 0xFF
        first_box = 1
        for threshold in (30, 80, 0):
            best_point = (x, y)
            best_box = 0xFF
            best_distance = 0xFFFF
            for box in reversed(self.walkboxes[first_box:]):
                if box.flags & 0x80:
                    continue
                point_x, point_y, distance = _v5_point_in_box_bounds(box.points, x, y)
                if distance == 0:
                    return (point_x, point_y), box.index
                if distance < best_distance:
                    best_point = (point_x, point_y)
                    best_box = box.index
                    best_distance = distance
            if threshold == 0 or threshold * threshold >= best_distance:
                return best_point, best_box
        return (x, y), 0xFF

    def route_gate(
        self,
        source: int,
        next_box: int,
        destination_box: int,
        position: tuple[int, int],
        destination: tuple[int, int],
    ) -> tuple[bool, tuple[int, int] | None]:
        """Find the common-edge gate used by the canonical v5 walker.

        A true result means the final destination can be approached directly.
        """
        if not (0 <= source < len(self.walkboxes) and 0 <= next_box < len(self.walkboxes)):
            return False, None
        first = list(self.walkboxes[source].points)
        second = list(self.walkboxes[next_box].points)
        for _ in range(4):
            for _ in range(4):
                a0, a1 = first[0], first[1]
                b0, b1 = second[0], second[1]
                if a0[0] == a1[0] == b0[0] == b1[0]:
                    a_low, a_high = sorted((a0[1], a1[1]))
                    b_low, b_high = sorted((b0[1], b1[1]))
                    touching_only = (
                        (a_high == b_low or b_high == a_low)
                        and a_low != a_high and b_low != b_high
                    )
                    if not (a_low > b_high or b_low > a_high or touching_only):
                        pos = position[1]
                        if next_box == destination_box:
                            diff_x = destination[0] - position[0]
                            diff_y = destination[1] - position[1]
                            if diff_x:
                                weighted = diff_y * (a0[0] - position[0])
                                offset = _trunc_div(weighted, diff_x)
                                if (
                                    offset == 0
                                    and (weighted <= 0 or diff_x <= 0)
                                    and (weighted >= 0 or diff_x >= 0)
                                ):
                                    offset = -1
                                pos += offset
                        q = min(max(pos, b_low), b_high)
                        q = min(max(q, a_low), a_high)
                        if q == pos and next_box == destination_box:
                            return True, None
                        return False, (a0[0], q)
                if a0[1] == a1[1] == b0[1] == b1[1]:
                    a_low, a_high = sorted((a0[0], a1[0]))
                    b_low, b_high = sorted((b0[0], b1[0]))
                    touching_only = (
                        (a_high == b_low or b_high == a_low)
                        and a_low != a_high and b_low != b_high
                    )
                    if not (a_low > b_high or b_low > a_high or touching_only):
                        pos = position[0]
                        if next_box == destination_box:
                            diff_x = destination[0] - position[0]
                            diff_y = destination[1] - position[1]
                            if diff_y:
                                pos += _trunc_div(diff_x * (a0[1] - position[1]), diff_y)
                        q = min(max(pos, b_low), b_high)
                        q = min(max(q, a_low), a_high)
                        if q == pos and next_box == destination_box:
                            return True, None
                        return False, (q, a0[1])
                first = first[1:] + first[:1]
            second = second[1:] + second[:1]
        return False, None


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
    verb_entries: tuple[tuple[int, int], ...] = ()
    obcd: bytes = b""
    obcd_room_offset: int = 0
    verb_table_offset: int = 0
    verb_table_length: int = 0

    def verb_entrypoint(self, verb: int) -> int:
        """Return canonical full-header v5 OBCD-relative VERB entrypoint."""
        for entry, offset in self.verb_entries:
            if entry == verb or entry == 0xFF:
                return offset
        return 0

    @property
    def authored_verbs(self) -> tuple[int, ...]:
        """Explicit VERB entries, preserving source order.

        The 0xFF entry is SCUMM's OBCD fallback and is deliberately not
        presented as a selectable UI verb.  It remains available through
        :meth:`verb_entrypoint` for script execution.
        """
        return tuple(verb for verb, _ in self.verb_entries if verb != 0xFF)

    def contains_point(self, x: int, y: int) -> bool:
        """Return whether a room/world point is in the CDHD rectangle.

        CDHD coordinates are room coordinates.  SCUMM's rectangle convention
        is half-open: the left/top edge is included and the right/bottom edge
        is excluded.  This also makes adjacent object rectangles unambiguous.
        """
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    @property
    def selectable(self) -> bool:
        """Whether this CDHD is eligible for generic cursor selection.

        CDHD flags are retained as source metadata.  In v5, bit 7 is the
        parent-state shorthand, not a generic non-selectable flag; class 32
        untouchability is runtime class state and is checked by the caller.
        """
        return True


@dataclass(slots=True)
class ScummV5Walkbox:
    index: int
    upper_left: tuple[int, int]
    upper_right: tuple[int, int]
    lower_right: tuple[int, int]
    lower_left: tuple[int, int]
    mask: int
    flags: int
    scale: int

    @property
    def points(self) -> tuple[tuple[int, int], ...]:
        return (self.upper_left, self.upper_right, self.lower_right, self.lower_left)

    def closest_point(self, x: int, y: int) -> tuple[int, int]:
        best, best_distance = (x, y), None
        for start, end in zip(self.points, (*self.points[1:], self.points[0])):
            point = _closest_point_on_line(start, end, (x, y))
            distance = (x - point[0]) ** 2 + (y - point[1]) ** 2
            if best_distance is None or distance < best_distance:
                best, best_distance = point, distance
        return best

    def contains(self, x: int, y: int) -> bool:
        points = self.points
        if not (
            min(point[0] for point in points) <= x <= max(point[0] for point in points)
            and min(point[1] for point in points) <= y <= max(point[1] for point in points)
        ):
            return False
        if (
            (self.upper_left == self.upper_right and self.lower_right == self.lower_left)
            or (self.upper_left == self.lower_left and self.upper_right == self.lower_right)
        ):
            closest_x, closest_y = _closest_point_on_line(
                self.upper_left, self.lower_right, (x, y)
            )
            if (x - closest_x) ** 2 + (y - closest_y) ** 2 <= 4:
                return True
        return all(
            (end_y - start_y) * (x - start_x)
            <= (y - start_y) * (end_x - start_x)
            for (start_x, start_y), (end_x, end_y) in zip(points, (*points[1:], points[0]))
        )


@dataclass(frozen=True, slots=True)
class _Chunk:
    tag: bytes
    raw: bytes
    offset: int = 0

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
        result.append(_Chunk(data[offset : offset + 4], bytes(data[offset:end]), offset))
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
        (),
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


def _decode_mask_strip(data: bytes, *, height: int, owner: str) -> bytes:
    """Decode one classic ZPxx strip to one eight-pixel mask byte per row."""
    output = bytearray()
    source = 0
    while len(output) < height:
        if source >= len(data):
            raise ResourceError(f"{owner} mask RLE is truncated")
        packet = data[source]
        source += 1
        repeated = bool(packet & 0x80)
        count = packet & 0x7F if repeated else packet
        if count == 0:
            count = 256
        count = min(count, height - len(output))
        if repeated:
            if source >= len(data):
                raise ResourceError(f"{owner} repeated mask RLE is truncated")
            output.extend((data[source],) * count)
            source += 1
        else:
            if source + count > len(data):
                raise ResourceError(f"{owner} literal mask RLE is truncated")
            output.extend(data[source : source + count])
            source += count
    return bytes(output)


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

    zplane_count = struct.unpack("<H", rmih.payload)[0]
    if zplane_count > 4:
        raise ResourceError(f"{owner} declares unsupported z-plane count {zplane_count}")
    zplane_chunks = tuple(
        chunk for chunk in image_chunks
        if len(chunk.tag) == 4 and chunk.tag[:2] == b"ZP" and chunk.tag[2:].isdigit()
    )
    expected_zplane_tags = tuple(
        f"ZP{plane:02d}".encode("ascii") for plane in range(1, zplane_count + 1)
    )
    if tuple(chunk.tag for chunk in zplane_chunks) != expected_zplane_tags:
        found = ", ".join(chunk.tag.decode("ascii") for chunk in zplane_chunks) or "none"
        expected = ", ".join(tag.decode("ascii") for tag in expected_zplane_tags) or "none"
        raise ResourceError(f"{owner} z-plane chunks are {found}; expected {expected}")
    zplanes: list[bytes] = []
    z_table_end = _CHUNK_HEADER_SIZE + strip_count * 2
    for plane_index, zplane in enumerate(zplane_chunks, 1):
        if len(zplane.raw) < z_table_end:
            raise ResourceError(f"{owner} ZP{plane_index:02d} strip-offset table is truncated")
        z_offsets = tuple(
            struct.unpack_from("<H", zplane.raw, _CHUNK_HEADER_SIZE + strip * 2)[0]
            for strip in range(strip_count)
        )
        positive_offsets = tuple(offset for offset in z_offsets if offset)
        if any(offset < z_table_end or offset >= len(zplane.raw) for offset in positive_offsets):
            raise ResourceError(f"{owner} ZP{plane_index:02d} strip offset is out of bounds")
        if any(left >= right for left, right in zip(positive_offsets, positive_offsets[1:])):
            raise ResourceError(
                f"{owner} ZP{plane_index:02d} strip offsets are not strictly increasing"
            )
        packed = bytearray(strip_count * height)
        for strip_index, start in enumerate(z_offsets):
            if not start:
                continue
            end = next(
                (offset for offset in z_offsets[strip_index + 1:] if offset), len(zplane.raw)
            )
            decoded = _decode_mask_strip(
                zplane.raw[start:end],
                height=height,
                owner=f"{owner} ZP{plane_index:02d} strip {strip_index}",
            )
            for y, mask in enumerate(decoded):
                packed[y * strip_count + strip_index] = mask
        zplanes.append(bytes(packed))

    boxd = _one(top, b"BOXD", owner=owner)
    if len(boxd.payload) < 2:
        raise ResourceError(f"{owner} BOXD box count is truncated")
    walkbox_count = struct.unpack_from("<H", boxd.payload)[0]
    if not 1 <= walkbox_count <= 255:
        raise ResourceError(f"{owner} BOXD box count {walkbox_count} is invalid")
    expected_boxd_size = 2 + walkbox_count * 20
    if len(boxd.payload) != expected_boxd_size:
        raise ResourceError(
            f"{owner} BOXD payload is {len(boxd.payload)} bytes; expected {expected_boxd_size}"
        )
    walkboxes: list[ScummV5Walkbox] = []
    for box_index in range(walkbox_count):
        values = struct.unpack_from("<hhhhhhhhBBH", boxd.payload, 2 + box_index * 20)
        mask = values[8]
        if mask > zplane_count:
            raise ResourceError(
                f"{owner} BOXD box {box_index} mask {mask} exceeds {zplane_count} z-planes"
            )
        walkboxes.append(ScummV5Walkbox(
            box_index,
            (values[0], values[1]),
            (values[2], values[3]),
            (values[4], values[5]),
            (values[6], values[7]),
            mask,
            values[9],
            values[10],
        ))

    boxm = _one(top, b"BOXM", owner=owner)
    box_routes: list[tuple[int | None, ...]] = []
    matrix_offset = 0
    for source_box in range(walkbox_count):
        routes: list[int | None] = [None] * walkbox_count
        previous_end = -1
        while True:
            if matrix_offset >= len(boxm.payload):
                raise ResourceError(f"{owner} BOXM row {source_box} is truncated")
            range_start = boxm.payload[matrix_offset]
            matrix_offset += 1
            if range_start == 0xFF:
                break
            if matrix_offset + 2 > len(boxm.payload):
                raise ResourceError(f"{owner} BOXM row {source_box} triple is truncated")
            range_end = boxm.payload[matrix_offset]
            next_box = boxm.payload[matrix_offset + 1]
            matrix_offset += 2
            if (
                range_start > range_end
                or range_end >= walkbox_count
                or next_box >= walkbox_count
                or range_start <= previous_end
            ):
                raise ResourceError(f"{owner} BOXM row {source_box} contains an invalid route")
            for destination in range(range_start, range_end + 1):
                routes[destination] = next_box
            previous_end = range_end
        box_routes.append(tuple(routes))
    trailing_matrix = boxm.payload[matrix_offset:]
    if trailing_matrix not in (b"", b"\x00"):
        raise ResourceError(f"{owner} BOXM has unexpected trailing data")

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
        verb_entries: list[tuple[int, int]] = []
        verb_table_offset = 0
        verb_table_length = 0
        child_offset = _CHUNK_HEADER_SIZE
        verb_chunks = tuple(item for item in children if item.tag == b"VERB")
        if len(verb_chunks) > 1:
            raise ResourceError(f"{owner} OBCD {index} contains duplicate VERB chunks")
        for child in children:
            if child.tag == b"VERB":
                verb_table_offset = child_offset
                verb_table_length = len(child.raw)
                cursor = 0
                terminated = False
                while cursor < len(child.payload):
                    entry = child.payload[cursor]
                    cursor += 1
                    if entry == 0:
                        terminated = True
                        break
                    if cursor + 2 > len(child.payload):
                        raise ResourceError(
                            f"{owner} OBCD {index} VERB entry {entry} is truncated"
                        )
                    relative = struct.unpack_from("<H", child.payload, cursor)[0]
                    cursor += 2
                    entrypoint = child_offset + relative
                    if entrypoint >= len(obcd.raw):
                        raise ResourceError(
                            f"{owner} OBCD {index} VERB entry {entry} is out of bounds"
                        )
                    verb_entries.append((entry, entrypoint))
                if not terminated:
                    raise ResourceError(f"{owner} OBCD {index} VERB table is unterminated")
            child_offset += len(child.raw)
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
                tuple(verb_entries),
                obcd.raw,
                obcd.offset,
                verb_table_offset,
                verb_table_length,
            )
        )
    for item in objects:
        if item.parent > len(objects):
            raise ResourceError(
                f"{owner} object {item.object_id} parent index {item.parent} is out of bounds"
            )
    for local_index, item in enumerate(objects, 1):
        seen: set[int] = set()
        current_index = local_index
        while objects[current_index - 1].parent:
            if current_index in seen:
                raise ResourceError(f"{owner} object hierarchy contains a cycle")
            seen.add(current_index)
            current_index = objects[current_index - 1].parent

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
        tuple(zplanes),
        tuple(walkboxes),
        tuple(box_routes),
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
        self.backdrop_surface: IndexedSurface | None = None
        self.logical_surface: IndexedSurface | None = None
        self.room: ScummV5Room | None = None
        self.logical_sha256 = ""
        self._projection = (0, 0, 0, 0, 0, 0)
        self._camera_xstart: int | None = None
        self.composition_surface: IndexedSurface | None = None
        self.actor_draws: list[dict[str, object]] = []

    def render(self, room_key: str, *, room_data: bytes | None = None) -> str:
        room = decode_room(
            self.context.services.resource_read(room_key) if room_data is None else room_data,
            key=room_key,
        )
        backdrop_palette = [(0, 0, 0)] * 256
        backdrop_palette[: len(room.palette)] = room.palette
        backdrop = IndexedSurface.wrap(
            room.width,
            room.height,
            room.width,
            room.pixels,
            palette=backdrop_palette,
        )
        surface = IndexedSurface(room.width, room.height)
        surface.set_palette(0, room.palette)
        surface.blit_surface(backdrop)
        self.backdrop_surface = backdrop
        self.logical_surface = surface
        self.room = room
        self.logical_sha256 = surface.hash()
        self.project()
        self.context.services.debug.marker("scumm_v5.room_image", int(self.logical_sha256[:8], 16))
        return self.logical_sha256

    def render_actors(
        self,
        actors: Mapping[int, object],
        *,
        current_room: int,
        costume_key: Callable[[int], str],
        object_classes: Mapping[int, set[int]] | None = None,
        project: bool = True,
    ) -> str:
        """Recompose the raw room and visible actors' current costume poses."""
        if (
            self.room is None
            or self.backdrop_surface is None
            or self.logical_surface is None
        ):
            raise ResourceError("SCUMM room actors cannot render before their room")
        surface = self.logical_surface
        surface.blit_surface(self.backdrop_surface)
        self.actor_draws = []
        for actor_id, actor in sorted(
            actors.items(), key=lambda item: (getattr(item[1], "position")[1], item[0])
        ):
            costume_id = int(getattr(actor, "costume"))
            if (
                not getattr(actor, "visible")
                or getattr(actor, "room") != current_room
                or costume_id == 0
            ):
                continue
            key = costume_key(costume_id)
            if not self.context.services.resources.contains(key):
                raise ResourceError(
                    f"SCUMM visible actor {actor_id} costume {costume_id} has no resource {key!r}"
                )
            costume = ScummV5Costume(self.context.services.resource_read(key), key=key)
            frame_value = getattr(actor, "costume_frame", None)
            if frame_value is None:
                frame_value = int(getattr(actor, "init_frame"))
                setattr(actor, "costume_frame", frame_value)
                setattr(actor, "costume_step", 0)
                setattr(actor, "animation_progress", 0)
            frame = int(frame_value)
            step = int(getattr(actor, "costume_step", 0))
            facing = int(getattr(actor, "facing", 180))
            pose = costume.decode_pose(frame, facing=facing, step=step)
            actor_x, actor_y = getattr(actor, "position")
            actor_y -= int(getattr(actor, "elevation"))
            x_move = y_move = 0
            bounds: list[int] | None = None
            actor_pixels: set[tuple[int, int]] = set()
            occluded = 0
            palette_overrides = getattr(actor, "palette")
            scale_x, scale_y = (int(value) for value in getattr(actor, "scale"))
            force_clip = int(getattr(actor, "force_clip", 0))
            walkbox = self.walkbox_at(actor_x, actor_y)
            setattr(actor, "walkbox", 0xFF if walkbox is None else walkbox.index)
            classes = set() if object_classes is None else object_classes.get(actor_id, set())
            if force_clip > 0:
                z_plane = min(force_clip, len(self.room.zplanes))
            elif 20 in classes or bool(getattr(actor, "ignore_boxes")) or walkbox is None:
                z_plane = 0
            else:
                z_plane = min(walkbox.mask, len(self.room.zplanes))
            strip_count = self.room.width // 8
            for cel in pose.cels:
                relative_x = x_move + cel.relative_x
                relative_y = y_move + cel.relative_y
                if scale_x == 255 and scale_y == 255:
                    target_x = actor_x + relative_x if pose.draw_to_right else actor_x - relative_x
                    target_y = actor_y + relative_y
                    x_index = y_index = 128
                else:
                    target_x, target_y, x_index, y_index = _scaled_cel_origin(
                        actor_x, actor_y, relative_x, relative_y,
                        scale_x, scale_y, pose.draw_to_right,
                    )
                x_step = 1 if pose.draw_to_right else -1
                for source_x in range(cel.width):
                    column_y = target_y
                    column_y_index = y_index
                    for source_y in range(cel.height):
                        draw_row = (
                            scale_y == 255
                            or _COSTUME_SCALE_TABLE[column_y_index] < scale_y
                        )
                        color_slot = cel.pixels[source_x * cel.height + source_y]
                        if draw_row and color_slot != 0 and (
                            0 <= target_x < self.room.width
                            and 0 <= column_y < self.room.height
                        ):
                            masked = bool(
                                z_plane
                                and self.room.zplanes[z_plane - 1][
                                    column_y * strip_count + target_x // 8
                                ] & (0x80 >> (target_x & 7))
                            )
                            if masked:
                                occluded += 1
                            else:
                                color = int(
                                    palette_overrides.get(color_slot, costume.palette[color_slot])
                                )
                                surface.pixels[column_y * self.room.width + target_x] = color
                                actor_pixels.add((target_x, column_y))
                                if bounds is None:
                                    bounds = [target_x, column_y, target_x, column_y]
                                else:
                                    bounds[0] = min(bounds[0], target_x)
                                    bounds[1] = min(bounds[1], column_y)
                                    bounds[2] = max(bounds[2], target_x)
                                    bounds[3] = max(bounds[3], column_y)
                        if draw_row:
                            column_y += 1
                        column_y_index = (column_y_index + 1) & 0xFF
                    if (
                        scale_x == 255
                        or _COSTUME_SCALE_TABLE[x_index] < scale_x
                    ):
                        target_x += x_step
                    x_index = (x_index + x_step) & 0xFF
                x_move += cel.move_x
                y_move -= cel.move_y
            setattr(actor, "hitbox", (0, 0, 0, 0) if bounds is None else tuple(bounds))
            self.actor_draws.append(
                {
                    "actor": actor_id,
                    "costume": costume_id,
                    "frame": frame,
                    "step": step,
                    "facing": facing,
                    "scale": [scale_x, scale_y],
                    "walkbox": None if walkbox is None else walkbox.index,
                    "z_plane": z_plane,
                    "occluded": occluded,
                    "cels": len(pose.cels),
                    "pixels": len(actor_pixels),
                    "bounds": bounds,
                }
            )
        self.logical_sha256 = surface.hash()
        if project:
            self.project()
        self.context.services.debug.marker(
            "scumm_v5.costume_frame", int(self.logical_sha256[:8], 16)
        )
        return self.logical_sha256

    def walkbox_at(self, x: int, y: int) -> ScummV5Walkbox | None:
        if self.room is None:
            return None
        return next(
            (
                box for box in reversed(self.room.walkboxes[1:])
                if not box.flags & 0x80 and box.contains(x, y)
            ),
            None,
        )

    def project(self) -> None:
        assert self.room is not None and self.logical_surface is not None
        video = self.context.services.video
        target = video.surface
        width = min(target.width, self.room.width)
        height = min(target.height, self.room.height)
        source_x = self._projected_source_x(width)
        source_y = max(0, (self.room.height - height) // 2)
        destination_x = max(0, (target.width - width) // 2)
        destination_y = max(0, (target.height - height) // 2)
        video.fill(0)
        video.set_palette(0, self.room.palette)
        video.blit_surface(
            self.logical_surface,
            source_rect=Rect(source_x, source_y, width, height),
            x=destination_x,
            y=destination_y,
        )
        self._projection = (source_x, source_y, destination_x, destination_y, width, height)
        self.logical_sha256 = self.logical_surface.hash()

    def prepare_composition(self) -> IndexedSurface:
        """Build the screen-relative logical frame below runtime overlays."""
        assert self.room is not None and self.logical_surface is not None
        video = self.context.services.video
        target = video.surface
        width = min(target.width, self.room.width)
        height = min(target.height, self.room.height)
        source_x = self._projected_source_x(width)
        source_y = max(0, (self.room.height - height) // 2)
        destination_x = max(0, (target.width - width) // 2)
        destination_y = max(0, (target.height - height) // 2)
        surface = self.composition_surface
        if surface is None or (surface.width, surface.height) != (target.width, target.height):
            surface = IndexedSurface(target.width, target.height)
            self.composition_surface = surface
        surface.fill(0)
        surface.set_palette(0, self.room.palette)
        surface.blit_surface(
            self.logical_surface,
            source_rect=Rect(source_x, source_y, width, height),
            x=destination_x,
            y=destination_y,
        )
        return surface

    def _projected_source_x(self, width: int) -> int:
        if self._camera_xstart is None:
            return max(0, (self.room.width - width) // 2)  # type: ignore[union-attr]
        logical_width = (
            self.context.profile.video.logical_width
            or self.context.profile.video.width
        )
        inset = max(0, (logical_width - width) // 2)
        return min(
            max(0, self.room.width - width),  # type: ignore[union-attr]
            max(0, self._camera_xstart + inset),
        )

    def publish_camera_viewport(self, xstart: int) -> bool:
        """Publish SCUMM's strip-aligned virtual-screen origin for projection."""
        assert self.room is not None
        width = min(self.context.services.video.surface.width, self.room.width)
        before = self._projection
        self._camera_xstart = xstart
        desired_x = self._projected_source_x(width)
        return before != (
            desired_x,
            max(0, (self.room.height - min(self.context.services.video.surface.height, self.room.height)) // 2),
            max(0, (self.context.services.video.surface.width - width) // 2),
            max(0, (self.context.services.video.surface.height - min(self.context.services.video.surface.height, self.room.height)) // 2),
            width,
            min(self.context.services.video.surface.height, self.room.height),
        )

    def project_composition(self) -> None:
        """Project the already composed logical-screen frame once."""
        assert self.room is not None and self.composition_surface is not None
        video = self.context.services.video
        video.fill(0)
        video.set_palette(0, self.room.palette)
        video.blit_surface(self.composition_surface)

    def move_cursor(self, logical_x: int, logical_y: int) -> None:
        source_x, source_y, destination_x, destination_y, width, height = self._projection
        physical_x = destination_x + logical_x - source_x
        physical_y = destination_y + logical_y - source_y
        physical_x = max(destination_x, min(destination_x + width - 1, physical_x))
        physical_y = max(destination_y, min(destination_y + height - 1, physical_y))
        self.context.services.video.move_cursor(physical_x, physical_y)

    def room_point_from_cursor(self, logical_x: int, logical_y: int) -> tuple[int, int]:
        """Convert a logical cursor point back to the room/world projection."""
        source_x, source_y, destination_x, destination_y, _width, _height = self._projection
        return source_x + logical_x - destination_x, source_y + logical_y - destination_y

    def hit_test_cursor(
        self,
        logical_x: int,
        logical_y: int,
        *,
        object_states: Mapping[int, int] | None = None,
        object_owners: Mapping[int, int] | None = None,
    ) -> ScummV5RoomObject | None:
        """Resolve a logical cursor point using the active room projection."""
        if self.room is None:
            return None
        return self.room.hit_test_object(
            *self.room_point_from_cursor(logical_x, logical_y),
            object_states=object_states,
            object_owners=object_owners,
        )

    def inspect(self) -> Mapping[str, object]:
        return {
            "mode": "room",
            "logical_sha256": self.logical_sha256,
            "format": None if self.room is None else self.room.source_format,
            "dimensions": None if self.room is None else [self.room.width, self.room.height],
            "strip_codecs": [] if self.room is None else sorted(set(self.room.strip_codecs)),
            "zplanes": 0 if self.room is None else len(self.room.zplanes),
            "walkboxes": 0 if self.room is None else len(self.room.walkboxes),
            "projection": list(self._projection),
            "actors": list(self.actor_draws),
        }
