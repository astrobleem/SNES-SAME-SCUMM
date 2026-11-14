"""Checked, source-space SCUMM foreground masks for the existing SAMEPKG.

One record preserves every source plane and eight-pixel strip identity. Blocks
cover at most 256 rows: zero, raw, or count/value RLE, whichever is smallest.
No background pixels or actor-specific policy are stored here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib

from ...errors import ResourceError

MAGIC = b'SC5MASK\0'
VERSION = 1
BLOCK_ROWS = 256
HEADER = struct.Struct('<8sHHHHHHHII32s32s')
ENTRY = struct.Struct('<IHBBI')  # record offset, checked size, codec, reserved, CRC
ZERO, RAW, RLE = range(3)


def _rle(data: bytes) -> bytes:
    out = bytearray()
    pos = 0
    while pos < len(data):
        end = pos + 1
        while end < len(data) and data[end] == data[pos] and end-pos < 256:
            end += 1
        out.extend((end-pos-1, data[pos]))
        pos = end
    return bytes(out)


def decode_block(data: bytes, *, codec: int, rows: int, crc32: int) -> bytes:
    if not 1 <= rows <= BLOCK_ROWS or len(data) > BLOCK_ROWS:
        raise ResourceError('mask block exceeds checked row capacity')
    if zlib.crc32(data) & 0xffffffff != crc32:
        raise ResourceError('mask block CRC mismatch')
    if codec == ZERO:
        if data or crc32:
            raise ResourceError('zero mask block has a payload')
        return bytes(rows)
    if codec == RAW:
        if len(data) != rows:
            raise ResourceError('raw mask block length differs')
        return data
    if codec != RLE or not data or len(data) % 2:
        raise ResourceError('mask block codec/length invalid')
    out = bytearray()
    for i in range(0, len(data), 2):
        count = data[i]+1
        if len(out)+count > rows:
            raise ResourceError('mask RLE expands beyond row bounds')
        out.extend(bytes((data[i+1],))*count)
    if len(out) != rows:
        raise ResourceError('mask RLE does not cover its rows')
    return bytes(out)


@dataclass(frozen=True, slots=True)
class RoomMasks:
    room: int
    width: int
    height: int
    planes: tuple[bytes, ...]
    source_room_sha256: str
    record_sha256: str
    blocks: tuple[dict, ...]
    walkbox_masks: bytes

    def covered(self, plane: int, x: int, y: int) -> bool:
        if not 0 <= plane <= len(self.planes):
            raise ResourceError('mask plane outside source directory')
        if not plane or not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return bool(self.planes[plane-1][y*(self.width//8)+x//8] & (0x80 >> (x & 7)))


def encode_room_masks(*, room: int, width: int, height: int,
                      planes: tuple[bytes, ...], source_room_sha256: str,
                      walkbox_masks: bytes = b'') -> bytes:
    if not 0 <= room <= 65535 or not 0 < width <= 65535 or width % 8 or not 0 < height <= 65535:
        raise ResourceError('mask source geometry invalid')
    if not 0 < len(planes) <= 255:
        raise ResourceError('mask record requires 1..255 original planes')
    if len(walkbox_masks) > 256:
        raise ResourceError('mask walkbox directory invalid')
    strips = width//8
    if any(len(p) != strips*height for p in planes):
        raise ResourceError('mask plane length differs from source geometry')
    try:
        source_hash = bytes.fromhex(source_room_sha256)
    except ValueError as exc:
        raise ResourceError('mask source identity invalid') from exc
    if len(source_hash) != 32:
        raise ResourceError('mask source identity must be SHA-256')
    blocks_per_strip = (height+BLOCK_ROWS-1)//BLOCK_ROWS
    count = len(planes)*strips*blocks_per_strip
    if count > 65535:
        raise ResourceError('mask block directory exceeds u16 native index')
    offset = HEADER.size + count*ENTRY.size + len(walkbox_masks)
    directory = bytearray()
    payload = bytearray()
    for plane in planes:
        for strip in range(strips):
            column = plane[strip::strips]
            for first in range(0, height, BLOCK_ROWS):
                raw = column[first:first+BLOCK_ROWS]
                if not any(raw):
                    directory.extend(ENTRY.pack(0, 0, ZERO, 0, 0))
                    continue
                packed = _rle(raw)
                codec, data = (RLE, packed) if len(packed) < len(raw) else (RAW, raw)
                directory.extend(ENTRY.pack(offset+len(payload), len(data), codec, 0,
                                            zlib.crc32(data)&0xffffffff))
                payload.extend(data)
    total = offset+len(payload)
    header = HEADER.pack(MAGIC, VERSION, room, width, height, len(planes), BLOCK_ROWS, len(walkbox_masks),
                         count, total, source_hash, hashlib.sha256(b''.join(planes)).digest())
    return header+directory+walkbox_masks+payload


def decode_room_masks(data: bytes, *, expected_room: int | None = None) -> RoomMasks:
    if len(data) < HEADER.size:
        raise ResourceError('mask header truncated')
    magic, version, room, width, height, planes, block_rows, box_count, count, total, source_hash, decoded_hash = HEADER.unpack_from(data)
    if magic != MAGIC or version != VERSION or block_rows != BLOCK_ROWS:
        raise ResourceError('mask header identity/version invalid')
    if expected_room is not None and room != expected_room:
        raise ResourceError('mask room identity mismatch')
    if not width or width % 8 or not height or not 0 < planes <= 255:
        raise ResourceError('mask geometry invalid')
    strips = width//8
    per_strip = (height+BLOCK_ROWS-1)//BLOCK_ROWS
    if count != planes*strips*per_strip or count > 65535 or total != len(data):
        raise ResourceError('mask directory bounds invalid')
    cursor = HEADER.size+count*ENTRY.size
    if cursor > len(data):
        raise ResourceError('mask directory truncated')
    if box_count > 256 or cursor+box_count > len(data):
        raise ResourceError('mask walkbox directory truncated')
    walkbox_masks = data[cursor:cursor+box_count]
    # The source renderer clamps a walkbox's byte-valued mask selector to
    # available planes. Preserve the selector, including values above N+1.
    cursor += box_count
    # Size is bounded by the canonical directory before allocating output.
    decoded = [bytearray(strips*height) for _ in range(planes)]
    rows_out = []
    for index in range(count):
        start, length, codec, reserved, crc = ENTRY.unpack_from(data, HEADER.size+index*ENTRY.size)
        plane, rest = divmod(index, strips*per_strip)
        strip, block = divmod(rest, per_strip)
        first = block*BLOCK_ROWS
        rows = min(BLOCK_ROWS, height-first)
        if reserved or codec not in (ZERO, RAW, RLE):
            raise ResourceError('mask block flags invalid')
        if codec == ZERO:
            if start or length or crc:
                raise ResourceError('zero mask descriptor invalid')
        elif start != cursor or not length or length > BLOCK_ROWS or start+length > len(data):
            raise ResourceError('mask block offset/length is not canonical')
        raw = decode_block(data[start:start+length], codec=codec, rows=rows, crc32=crc)
        for y, value in enumerate(raw, first):
            decoded[plane][y*strips+strip] = value
        if codec != ZERO:
            cursor += length
        rows_out.append(dict(plane=plane+1, strip=strip, first_row=first, rows=rows,
                             offset=start, length=length, codec=codec, crc32=f'{crc:08x}'))
    result = tuple(bytes(p) for p in decoded)
    if cursor != len(data) or hashlib.sha256(b''.join(result)).digest() != decoded_hash:
        raise ResourceError('mask coverage/hash mismatch')
    return RoomMasks(room, width, height, result, source_hash.hex(),
                     hashlib.sha256(data).hexdigest(), tuple(rows_out), walkbox_masks)


def native_directory(records: list[dict], *, bank: int = 96) -> str:
    """ROM contains identity/bounds/CRC descriptors, never original mask bytes."""
    blocks = [block for record in records for block in record['blocks']]
    if not 0 <= bank < 127 or bank+((len(blocks)+2047)//2048) > 127:
        raise ResourceError('mask descriptor banks exceed current LoROM mapping')
    if len(blocks) > 65535 or len({r['room'] for r in records}) != len(records):
        raise ResourceError('mask room/block directory is not representable')
    rooms = {r['room']: r for r in records}
    if any(not 0 <= room <= 255 for room in rooms):
        raise ResourceError('native mask room identity exceeds directory')
    lines = [f'SCUMM_MSU1_MASK_ROOM_ADDRESS = ${(bank << 16) | 0x8000:06X}',
             f'SCUMM_MSU1_MASK_ROOM_BANK = ${bank:02X}',
             f'SCUMM_MSU1_MASK_COUNT = ${len(records):04X}',
             f'SCUMM_MSU1_MASK_FIRST_BANK = ${bank+1:02X}',
             f'SCUMM_MSU1_MASK_BLOCK_COUNT = ${len(blocks):04X}']
    if not records:
        return '\n'.join(lines)+'\n'
    lines += [f'.bank {bank}', '.org $8000', 'ScummV5_MsuMaskRooms:']
    def emit(data):
        for start in range(0,len(data),16):
            lines.append('    .byte '+','.join(f'${x:02X}' for x in data[start:start+16]))
    first = 0
    box_data = bytearray()
    directory = bytearray()
    for room in range(256):
        r = rooms.get(room)
        if r is None:
            directory.extend(bytes(16));continue
        masks = bytes(r.get('walkbox_masks', []))
        if len(masks) > 256 or len(box_data)+2+len(masks) > 0x7000:
            raise ResourceError('native mask walkbox metadata exceeds bank bounds')
        box_offset = 0x9000+len(box_data)
        box_data.extend(struct.pack('<H', len(masks))+masks)
        directory.extend(struct.pack('<8H', r['width'],r['height'],r['planes'],
                                     (r['height']+255)//256,r['width']//8,first,len(r['blocks']),box_offset))
        first += len(r['blocks'])
    # The flat order must be exactly the order used by room.first.
    if [r['room'] for r in records] != sorted(rooms):
        raise ResourceError('mask room records must be sorted')
    emit(directory)
    emit(box_data)
    for page in range((len(blocks)+2047)//2048):
        lines += [f'.bank {bank+1+page}', '.org $8000',f'ScummV5_MsuMaskBlocks{page}:']
        for b in blocks[page*2048:(page+1)*2048]:
            offset=int(b['package_offset']);length=int(b['length']);codec=int(b['codec'])
            if not 0 <= offset <= 0xffffffff-length or not 0 <= length <= 256:
                raise ResourceError('native mask checked range overflow')
            emit(struct.pack('<IHHBBIH',offset,length,int(b['rows']),codec,0,int(b['crc32'],16),0))
    return '\n'.join(lines)+'\n'
