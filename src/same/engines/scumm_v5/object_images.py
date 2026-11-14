"""Original v5 state-selected OBIM images, using the shared SMAP/ZP codecs.

Image ownership is identified by IMHD, never by its position relative to OBCD.
Coverage is separate from color: an opaque source color zero remains opaque.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from collections.abc import Mapping

from ...errors import ResourceError
from .room import (_chunks, _one, _decode_strip, _decode_mask_strip,
                   _TRANSPARENT, ScummV5Room)


@dataclass(frozen=True)
class ObjectImage:
    object_id: int
    state: int
    width: int
    height: int
    pixels: bytes
    coverage: bytes
    zplanes: tuple[bytes, ...]
    source_sha256: str


def decode_object_images(raw: bytes, room: ScummV5Room) -> tuple[ObjectImage, ...]:
    """Decode original object states without changing the base ROOM pixels."""
    objects = {obj.object_id: obj for obj in room.objects}
    seen = set()
    result = []
    for obim in _chunks(raw, owner='ROOM object images'):
        if obim.tag != b'OBIM':
            continue
        children = _chunks(obim.payload, owner='OBIM')
        header = _one(children, b'IMHD', owner='OBIM').payload
        if len(header) < 16:
            raise ResourceError('v5 object IMHD truncated')
        identity, count = struct.unpack_from('<HH', header)
        if identity not in objects or identity in seen:
            raise ResourceError('object image identity missing or duplicated')
        seen.add(identity)
        obj = objects[identity]
        width, height = struct.unpack_from('<HH', header, 12)
        if (width, height) != (obj.width, obj.height):
            raise ResourceError('v5 IMHD/CDHD geometry differs')
        images = [c for c in children if c.tag[:2] == b'IM' and c.tag != b'IMHD']
        if len(images) != count:
            raise ResourceError('object image count differs')
        states = set()
        for image in images:
            try:
                state = int(image.tag[2:].decode('ascii'), 16)
            except (ValueError, UnicodeError) as exc:
                raise ResourceError('object image state tag invalid') from exc
            if not 1 <= state <= 15 or state in states:
                raise ResourceError('v5 object state image duplicated or out of range')
            states.add(state)
            if not width or width % 8 or not height or width > 2048 or height > 2048:
                raise ResourceError('object image geometry outside source bounds')
            chunks = _chunks(image.payload, owner='object state')
            smap = _one(chunks, b'SMAP', owner='object state').raw
            strips = width // 8
            directory_end = 8 + strips * 4
            if len(smap) < directory_end:
                raise ResourceError('object SMAP directory truncated')
            offsets = struct.unpack_from('<' + 'I' * strips, smap, 8)
            if any(p < directory_end or p >= len(smap) for p in offsets) or any(
                a >= b for a, b in zip(offsets, offsets[1:])
            ):
                raise ResourceError('object SMAP offsets invalid')
            pixels = bytearray(width * height)
            coverage = bytearray(width * height)
            for strip, start in enumerate(offsets):
                end = offsets[strip + 1] if strip + 1 < strips else len(smap)
                decoded, codec = _decode_strip(smap[start:end], height=height,
                                               owner=f'object {identity} state {state}')
                for y in range(height):
                    for x in range(8):
                        dst = y * width + strip * 8 + x
                        color = decoded[y * 8 + x]
                        pixels[dst] = color
                        coverage[dst] = codec not in _TRANSPARENT or color != room.transparent_index
            planes = []
            for plane in range(1, len(room.zplanes) + 1):
                tag = f'ZP{plane:02d}'.encode('ascii')
                matching = [c for c in chunks if c.tag == tag]
                if len(matching) > 1:
                    raise ResourceError('object z-plane duplicated')
                output = bytearray(strips * height)
                if matching:
                    data = matching[0].raw
                    if len(data) < 8 + strips * 2:
                        raise ResourceError('object z-plane directory truncated')
                    for strip in range(strips):
                        offset = struct.unpack_from('<H', data, 8 + strip * 2)[0]
                        if not offset:
                            continue
                        if offset < 8 + strips * 2 or offset >= len(data):
                            raise ResourceError('object z-plane offset invalid')
                        decoded = _decode_mask_strip(data[offset:], height=height,
                                                     owner=f'object {identity} {tag!r}')
                        output[strip::strips] = decoded
                planes.append(bytes(output))
            result.append(ObjectImage(identity, state, width, height, bytes(pixels),
                                      bytes(coverage), tuple(planes),
                                      hashlib.sha256(image.raw).hexdigest()))
    return tuple(result)


def compose_objects(room: ScummV5Room, images: tuple[ObjectImage, ...],
                    states: Mapping[int, int], *,
                    owners: Mapping[int, int] | None = None) -> tuple[bytes, tuple[bytes, ...]]:
    """v5 reverse-local-order painter with parent-state and clipping semantics.

Classic v5 object masks replace the affected strip, including zero rows; they
do not use the later HE transparent-mask OR flag.
"""
    lookup = {(i.object_id, i.state): i for i in images}
    pixels = bytearray(room.pixels)
    planes = [bytearray(p) for p in room.zplanes]
    pitch = room.width // 8
    for obj in reversed(room.objects):
        state = states.get(obj.object_id, 0) & 15
        if not state or not room._parent_chain_visible(obj, states):
            continue
        if owners is not None and owners.get(obj.object_id, 15) not in (0, 15):
            continue
        image = lookup.get((obj.object_id, state))
        if image is None:  # Source getObjectImage permits a state without IMxx.
            continue
        for y in range(image.height):
            ry = obj.y + y
            if not 0 <= ry < room.height:
                continue
            for x in range(image.width):
                rx = obj.x + x
                src = y * image.width + x
                if 0 <= rx < room.width and image.coverage[src]:
                    pixels[ry * room.width + rx] = image.pixels[src]
            for strip in range(image.width // 8):
                dest_strip = obj.x // 8 + strip
                if 0 <= dest_strip < pitch:
                    for plane, mask in zip(planes, image.zplanes):
                        plane[ry * pitch + dest_strip] = mask[y * (image.width // 8) + strip]
    return bytes(pixels), tuple(bytes(p) for p in planes)
