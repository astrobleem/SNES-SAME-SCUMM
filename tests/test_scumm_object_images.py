import struct
import unittest
from dataclasses import replace

from same.errors import ResourceError
from same.engines.scumm_v5.room import ScummV5Room, ScummV5RoomObject
from same.engines.scumm_v5.object_images import decode_object_images, compose_objects
from same.engines.scumm_v5.room import ScummV5RoomAdapter
from same.video import IndexedSurface
from test_scumm_v5_audio_save import make_host


def chunk(tag, payload):
    return tag + struct.pack('>I', len(payload) + 8) + payload


def obj(identity, x=0, parent=0, flags=0):
    return ScummV5RoomObject(identity, x, 0, 8, 8, flags, parent, 0, 0, 0)


def room(objects):
    return ScummV5Room(16, 8, ((0, 0, 0),) * 256, bytes([7]) * 128,
                       255, 'raw-v5', (), (bytes([255]) * 16,), (), (),
                       tuple(objects), None, None, ())


def image(identity, color, *, transparent=False, state=1, mask=0):
    strip = bytes((44, color)) + bytes(8) if transparent else bytes((1,)) + bytes([color]) * 64
    smap = chunk(b'SMAP', struct.pack('<I', 12) + strip)
    zp = chunk(b'ZP01', struct.pack('<H', 10) + bytes((0x88, mask)))
    hd = struct.pack('<8H', identity, 1, 2, 0, 0, 0, 8, 8)
    return chunk(b'OBIM', chunk(b'IMHD', hd) + chunk(f'IM{state:02X}'.encode(), smap + zp))


class ObjectImageTests(unittest.TestCase):
    def test_state_only_invalidation_recomposes_then_restores_the_room(self):
        host = make_host()
        engine = host.engine
        r = room([obj(8)])
        adapter = ScummV5RoomAdapter(host.context)
        adapter.room = r
        adapter.object_images = decode_object_images(image(8, 0), r)
        adapter.backdrop_surface = IndexedSurface.wrap(r.width, r.height, r.width, r.pixels)
        adapter.logical_surface = IndexedSurface(r.width, r.height)
        engine._video = adapter
        engine.state.actors.clear()
        engine.state.print_messages.clear()
        engine._object_owners = bytes([15]) * 16
        for state, color in ((1, 0), (0, 7), (1, 0)):
            engine.state.object_states[8] = state
            engine._actors_dirty = False
            engine._presentation_rebuild = False
            engine._background_needs_redraw = True
            engine._compose_presentation(host.context)
            self.assertEqual(bytes(adapter.logical_surface.pixels)[:8], bytes([color]) * 8)
            self.assertFalse(engine._background_needs_redraw)

    def test_identity_is_not_parallel_resource_position(self):
        r = room([obj(8), obj(9, 8)])
        images = decode_object_images(image(9, 3) + image(8, 0), r)
        pixels, masks = compose_objects(r, images, {8: 1, 9: 1})
        self.assertEqual(pixels[:16], bytes(8) + bytes([3]) * 8)
        self.assertEqual(masks, (bytes(16),))

    def test_transparency_is_codec_specific_and_zero_is_opaque(self):
        r = room([obj(8)])
        for transparent, color, expected in ((True, 255, 7), (False, 255, 255), (True, 0, 0)):
            with self.subTest(transparent=transparent, color=color):
                images = decode_object_images(image(8, color, transparent=transparent), r)
                pixels, _ = compose_objects(r, images, {8: 1})
                self.assertEqual(pixels[:8], bytes([expected]) * 8)

    def test_state_hide_replace_and_reverse_local_painter(self):
        r = room([obj(8), obj(9)])
        images = decode_object_images(image(8, 2) + image(9, 3), r)
        self.assertEqual(compose_objects(r, images, {8: 1, 9: 1})[0][:8], bytes([2]) * 8)
        self.assertEqual(compose_objects(r, images, {8: 0, 9: 1})[0][:8], bytes([3]) * 8)
        self.assertEqual(compose_objects(r, images, {})[0], r.pixels)
        self.assertEqual(compose_objects(r, images, {8: 2})[0], r.pixels)

    def test_parent_state_owner_clipping_and_mask_replacement(self):
        r = room([obj(8, -8), obj(9, 8, parent=1, flags=0x80)])
        images = decode_object_images(image(8, 2) + image(9, 3, mask=0x40), r)
        self.assertEqual(compose_objects(r, images, {9: 1})[0], r.pixels)
        pixels, masks = compose_objects(r, images, {8: 1, 9: 1})
        self.assertEqual(pixels[:16], bytes([7]) * 8 + bytes([3]) * 8)
        self.assertEqual(masks[0][:2], b'\xff\x40')
        self.assertEqual(compose_objects(r, images, {8: 1, 9: 1}, owners={9: 1})[0], r.pixels)

    def test_malformed_identity_count_geometry_and_offsets_rejected(self):
        r = room([obj(8)])
        good = image(8, 0)
        bad_offset = good.replace(struct.pack('<I', 12), struct.pack('<I', 4), 1)
        for raw in (image(9, 0), good + good, good[:-1], bad_offset):
            with self.subTest(raw=raw[:24]):
                with self.assertRaises(ResourceError): decode_object_images(raw, r)
        with self.assertRaises(ResourceError):
            decode_object_images(good, replace(r, objects=(replace(r.objects[0], width=16),)))


if __name__ == '__main__':
    unittest.main()
