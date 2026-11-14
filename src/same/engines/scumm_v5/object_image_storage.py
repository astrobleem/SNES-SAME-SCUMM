"""Bounded checked strips for original state-selected room-object imagery.

These are payloads and descriptors for the existing SAMEPKG service, not a
second image decoder. Rows retain source palette indexes, an independent
coverage byte, and every original foreground-plane byte. The same checked
row can supply background composition and actor occlusion.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import zlib
import struct

from ...errors import ResourceError
from .object_images import ObjectImage
from .room import ScummV5Room

MAX_CHECKED_BYTES = 1024


@dataclass(frozen=True, slots=True)
class ObjectStrip:
    object_id: int
    state: int
    column: int
    first_row: int
    rows: int
    planes: int
    offset: int
    length: int
    crc32: int

    def decode(self, data: bytes) -> tuple[bytes, bytes, tuple[bytes, ...]]:
        """Validate the entire chunk before exposing any pixels or mask rows."""
        if not 0 < self.object_id <= 65535 or not 1 <= self.state <= 15:
            raise ResourceError('object strip identity invalid')
        if (not 0 <= self.column < 8192 or not 0 <= self.first_row < 65536
                or not 0 <= self.planes <= 255 or not 0 < self.rows <= 65535
                or self.first_row + self.rows > 65535):
            raise ResourceError('object strip geometry invalid')
        stride = 9 + self.planes
        if self.length != self.rows * stride or not 0 < self.length <= MAX_CHECKED_BYTES:
            raise ResourceError('object strip checked length invalid')
        if len(data) != self.length or zlib.crc32(data) & 0xffffffff != self.crc32:
            raise ResourceError('object strip length/CRC mismatch')
        pixels, coverage = bytearray(), bytearray()
        planes = [bytearray() for _ in range(self.planes)]
        for start in range(0, self.length, stride):
            bits = data[start]
            colors = data[start + 1:start + 9]
            for x, color in enumerate(colors):
                covered = bool(bits & (0x80 >> x))
                if not covered and color:
                    raise ResourceError('uncovered object pixel is not canonical zero')
                coverage.append(covered)
                pixels.append(color)
            for n, plane in enumerate(planes):
                plane.append(data[start + 9 + n])
        return bytes(pixels), bytes(coverage), tuple(bytes(p) for p in planes)


def compile_object_strips(images: tuple[ObjectImage, ...]) -> tuple[bytes, tuple[ObjectStrip, ...]]:
    """Deterministic identity/state/column/row order, with no state selection.

    Runtime painter order and parent/owner checks belong to the installed
    object directory. All source states remain independently addressable.
    No palette-index-zero heuristic is permitted when packing coverage.
    """
    payload = bytearray()
    records = []
    identities = set()
    for image in sorted(images, key=lambda i: (i.object_id, i.state)):
        identity = (image.object_id, image.state)
        if identity in identities:
            raise ResourceError('duplicate object image state')
        identities.add(identity)
        if not 0 < image.object_id <= 65535 or not 1 <= image.state <= 15:
            raise ResourceError('object image identity invalid')
        if (not 0 < image.width <= 65528 or image.width % 8
                or not 0 < image.height <= 65535 or len(image.zplanes) > 255):
            raise ResourceError('object image geometry invalid')
        strips = image.width // 8
        if (len(image.pixels) != image.width * image.height
                or len(image.coverage) != len(image.pixels)
                or any(v not in (0, 1) for v in image.coverage)
                or any(len(p) != strips * image.height for p in image.zplanes)):
            raise ResourceError('object image decoded lengths/coverage differ')
        row_size = 9 + len(image.zplanes)
        block_rows = MAX_CHECKED_BYTES // row_size
        for column in range(strips):
            for first in range(0, image.height, block_rows):
                rows = min(block_rows, image.height - first)
                data = bytearray()
                for y in range(first, first + rows):
                    start = y * image.width + column * 8
                    coverage = image.coverage[start:start + 8]
                    bits = sum((0x80 >> x) for x, value in enumerate(coverage) if value)
                    data.append(bits)
                    data.extend(color if covered else 0 for color, covered in
                                zip(image.pixels[start:start + 8], coverage))
                    data.extend(p[y * strips + column] for p in image.zplanes)
                if len(payload) > 0xffffffff - len(data):
                    raise ResourceError('object strip payload exceeds 32-bit storage')
                record = ObjectStrip(image.object_id, image.state, column, first,
                                     rows, len(image.zplanes), len(payload), len(data),
                                     zlib.crc32(data) & 0xffffffff)
                record.decode(data)
                records.append(record)
                payload.extend(data)
    return bytes(payload), tuple(records)


def object_strip_manifest(images: tuple[ObjectImage, ...], records: tuple[ObjectStrip, ...],
                          payload: bytes) -> dict:
    """Source linkage for package generation; never an execution certificate."""
    from dataclasses import asdict
    return dict(schema='same-scumm-object-checked-strips-v1',
                native_acceptance='NOT_VERIFIED', checked_bytes=MAX_CHECKED_BYTES,
                payload_bytes=len(payload), payload_sha256=hashlib.sha256(payload).hexdigest(),
                images=[dict(object_id=i.object_id, state=i.state, width=i.width,
                             height=i.height, planes=len(i.zplanes), source_sha256=i.source_sha256)
                        for i in sorted(images, key=lambda i: (i.object_id, i.state))],
                blocks=[asdict(r) for r in records])


def compile_room_object_strips(room_id: int, room: ScummV5Room,
                               images: tuple[ObjectImage, ...]) -> tuple[bytes, dict]:
    """Index immutable source blocks by world strip and source painter order.

    Source rectangles and parent links are descriptors, not baked state.
    The installed mutable state/owner tables must select each block at use.
    """
    if not 0 <= room_id <= 255 or not 0 < room.width <= 65528 or room.width % 8:
        raise ResourceError('native object room identity/width invalid')
    if not 0 < room.height <= 65535 or len(room.objects) > 255:
        raise ResourceError('native object room geometry/count invalid')
    payload, blocks = compile_object_strips(images)
    by_id = {o.object_id: (index + 1, o) for index, o in enumerate(room.objects)}
    if len(by_id) != len(room.objects):
        raise ResourceError('native object room has duplicate local identities')
    buckets = [[] for _ in range(room.width // 8)]
    for image in images:
        if image.object_id not in by_id:
            raise ResourceError('object image has no local room metadata')
        _, obj = by_id[image.object_id]
        if (image.width, image.height) != (obj.width, obj.height) or len(image.zplanes) != len(room.zplanes):
            raise ResourceError('object image geometry/planes differ from room')
    for block in blocks:
        local, obj = by_id[block.object_id]
        if obj.x % 8 or not -32768 <= obj.x <= 32767 or not -32768 <= obj.y <= 32767:
            raise ResourceError('native v5 object placement is not a signed source strip')
        column = obj.x // 8 + block.column
        if 0 <= column < len(buckets):
            # Classic v5 drawObject clips its source height to a multiple of 8.
            # Retain all source bytes, but do not present trailing partial rows.
            visible_rows = min(block.rows, (obj.height & ~7) - block.first_row)
            if visible_rows > 0:
                row = dict(local=local, state=block.state, planes=block.planes,
                           world_y=obj.y + block.first_row, rows=visible_rows,
                           checked_rows=block.rows, offset=block.offset,
                           length=block.length, crc32=block.crc32)
                if not -32768 <= row['world_y'] <= 32767:
                    raise ResourceError('native object row position exceeds signed bounds')
                buckets[column].append(row)
    ordered = []
    columns = []
    for bucket in buckets:
        bucket.sort(key=lambda r: (-r['local'], r['state'], r['world_y']))
        columns.append(dict(first=len(ordered), count=len(bucket)))
        ordered.extend(bucket)
    if len(ordered) > 65535:
        raise ResourceError('native object block directory exceeds u16')
    objects = []
    for obj in room.objects:
        if not 0 <= obj.parent <= len(room.objects):
            raise ResourceError('native object parent is outside local directory')
        objects.append(dict(object_id=obj.object_id, x=obj.x, y=obj.y,
                            width=obj.width, height=obj.height, parent=obj.parent,
                            parent_state=1 if obj.flags == 0x80 else obj.flags & 15))
    manifest = object_strip_manifest(images, blocks, payload)
    manifest.update(room=room_id, width=room.width, height=room.height,
                    objects=objects, columns=columns, native_blocks=ordered)
    return payload, manifest


def native_object_directory(rooms: list[dict], *, first_bank: int) -> tuple[str, tuple[int, ...]]:
    """Allocate checked descriptors in normal LoROM banks; never pixel data.

    Room table: u24 metadata address, reserved byte, u16 object count and
    strip count. Metadata: 16-byte local rows then 4-byte strip indexes.
    Block table: 32-byte records, 1024 records per bank. All offsets and bank
    limits are rejected before assembly, including package address overflow.
    """
    if not 0 <= first_bank < 128 or [r['room'] for r in rooms] != sorted({r['room'] for r in rooms}):
        raise ResourceError('native object rooms/bank order invalid')
    if any(not 0 <= r['room'] < 256 for r in rooms):
        raise ResourceError('native object room directory exceeds byte identity')
    pages = [bytearray(256 * 8)]
    blocks = []
    for room in rooms:
        validate_native_object_manifest(room)
        objects, columns = room['objects'], room['columns']
        metadata = bytearray()
        for obj in objects:
            metadata.extend(struct.pack('<HhhHHHHH', obj['object_id'], obj['x'], obj['y'],
                                        obj['width'], obj['height'], obj['parent'], obj['parent_state'], 0))
        for column in columns:
            first = len(blocks) + column['first']
            if first > 65535 or not 0 <= column['count'] <= 65535:
                raise ResourceError('native object strip index overflow')
            metadata.extend(struct.pack('<HH', first, column['count']))
        if len(metadata) > 0x8000:
            raise ResourceError('native object room metadata exceeds one LoROM bank')
        if len(pages[-1]) + len(metadata) > 0x8000:
            pages.append(bytearray())
        address = ((first_bank + len(pages) - 1) << 16) | (0x8000 + len(pages[-1]))
        pages[0][room['room'] * 8:room['room'] * 8 + 8] = struct.pack('<IHH', address, len(objects), len(columns))
        pages[-1].extend(metadata)
        for block in room['native_blocks']:
            start = room['package_offset'] + block['offset']
            length = block['length']
            if not 0 <= start <= 0xffffffff - length or not 0 < length <= MAX_CHECKED_BYTES:
                raise ResourceError('native object checked address/length overflow')
            if length != block['checked_rows'] * (9 + block['planes']) or not 0 < block['rows'] <= block['checked_rows']:
                raise ResourceError('native object checked row bounds differ')
            blocks.append(struct.pack('<IHIHBBhHH12x', start, length, block['crc32'], block['local'],
                                      block['state'], block['planes'], block['world_y'],
                                      block['rows'], block['checked_rows']))
    block_bank = first_bank + len(pages)
    for start in range(0, len(blocks), 1024):
        pages.append(bytearray(b''.join(blocks[start:start + 1024])))
    if len(blocks) > 65535 or first_bank + len(pages) > 128:
        raise ResourceError('native object descriptors exceed mapped LoROM')
    lines = [f'SCUMM_MSU1_OBJECT_ROOM_ADDRESS = ${(first_bank << 16) | 0x8000:06X}',
             f'SCUMM_MSU1_OBJECT_ROOM_COUNT = ${len(rooms):04X}',
             f'SCUMM_MSU1_OBJECT_BLOCK_COUNT = ${len(blocks):04X}',
             f'SCUMM_MSU1_OBJECT_BLOCK_BANK = ${block_bank:02X}']
    banks = tuple(range(first_bank, first_bank + len(pages)))
    for bank, data in zip(banks, pages):
        lines.extend((f'.bank {bank}', '.org $8000', f'ScummV5_MsuObjectDescriptors{bank}:'))
        for start in range(0, len(data), 16):
            lines.append('    .byte ' + ','.join(f'${v:02X}' for v in data[start:start + 16]))
    return '\n'.join(lines) + '\n', banks


def validate_native_object_manifest(room: dict) -> None:
    """Bind native indexes back to the checked source blocks before assembly.

    A valid payload hash alone does not validate a second set of descriptors.
    Reconstruct the native view from the source rows and reject omissions,
    aliases, reordered painter entries and addresses into neighboring data.
    """
    objects = room['objects']
    if not 0 <= len(objects) <= 255 or len({o['object_id'] for o in objects}) != len(objects):
        raise ResourceError('native object metadata identities/count invalid')
    width = room['width']
    if not 0 < width <= 65528 or width % 8:
        raise ResourceError('native object room width invalid')
    by_id = {}
    for local, obj in enumerate(objects, 1):
        if (not 0 < obj['object_id'] <= 65535 or obj['x'] % 8
                or not -32768 <= obj['x'] <= 32767 or not -32768 <= obj['y'] <= 32767
                or not 0 <= obj['parent'] <= len(objects)
                or not 0 <= obj['parent_state'] <= 15
                or not 0 <= obj['width'] <= 65535 or not 0 <= obj['height'] <= 65535):
            raise ResourceError('native object metadata geometry/parent invalid')
        by_id[obj['object_id']] = (local, obj)
    buckets = [[] for _ in range(width // 8)]
    for raw in room['blocks']:
        block = ObjectStrip(**raw)
        if block.object_id not in by_id:
            raise ResourceError('native object block lacks local identity')
        local, obj = by_id[block.object_id]
        if (block.column * 8 >= obj['width'] or block.first_row + block.rows > obj['height']
                or not 0 <= block.offset <= room['payload_bytes'] - block.length):
            raise ResourceError('native object block exceeds source geometry/payload')
        column = obj['x'] // 8 + block.column
        rows = min(block.rows, (obj['height'] & ~7) - block.first_row)
        if 0 <= column < len(buckets) and rows > 0:
            buckets[column].append(dict(local=local, state=block.state, planes=block.planes,
                world_y=obj['y'] + block.first_row, rows=rows, checked_rows=block.rows,
                offset=block.offset, length=block.length, crc32=block.crc32))
    expected, columns = [], []
    for bucket in buckets:
        bucket.sort(key=lambda r: (-r['local'], r['state'], r['world_y']))
        columns.append(dict(first=len(expected), count=len(bucket)))
        expected.extend(bucket)
    if room['columns'] != columns or room['native_blocks'] != expected:
        raise ResourceError('native object indexes differ from checked source blocks')
