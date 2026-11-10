"""Original-format v5 CHAR fixtures made solely from synthetic bit patterns."""
import struct
from types import SimpleNamespace
import unittest

from same.engines.scumm_v5.engine import ScummV5Engine, PrintMessageState, PrintSlotState
from same.engines.scumm_v5.font import encode_charset
from same.engines.scumm_v5.video import ScummV5Charset, ScummV5VideoAdapter, SceneText
from same.errors import ResourceError
from same.resources import MemoryResourceProvider
from same.video import IndexedSurface


def charset(bpp, width, height, packed, *, count=3):
    # 21-byte stripped-resource wrapper, followed by the original font header.
    raw = bytearray(21)
    raw[4:21] = bytes((90, 0, 42, 0, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29))
    raw.extend(struct.pack('<BBH', bpp, height, count))
    raw.extend(bytes(count * 4))
    struct.pack_into('<I', raw, 25 + 4, 4 + count * 4)  # Only code 1 exists.
    raw.extend(struct.pack('<BBbb', width, height, -2, 3))
    raw.extend(packed)
    struct.pack_into('<I', raw, 0, len(raw)-15)
    return bytes(raw)


class CharsetMultibitTests(unittest.TestCase):
    def test_original_packed_slots_cross_rows_without_padding(self):
        cases = (
            (1, 3, 3, bytes((0xAB, 0x7F)), (1, 0, 1, 0, 1, 0, 1, 1, 0)),
            (2, 3, 2, bytes((0x1B, 0x9F)), (0, 1, 2, 3, 2, 1)),
            (4, 3, 2, bytes((0x01, 0x2F, 0x80)), (0, 1, 2, 15, 8, 0)),
        )
        for bpp, width, height, packed, slots in cases:
            with self.subTest(bpp=bpp):
                font = ScummV5Charset(charset(bpp, width, height, packed),
                                      key='synthetic', allow_multibit=True)
                glyph = font.glyph(1)
                self.assertEqual(font.bits_per_pixel, bpp)
                self.assertEqual(glyph.pixels, bytes(slots))
                self.assertEqual((glyph.width, glyph.height, glyph.x_offset, glyph.y_offset),
                                 (width, height, -2, 3))
                self.assertIsNone(font.glyph(0))
                self.assertIsNone(font.glyph(2))
                self.assertIsNone(font.glyph(255))
                # No palette mapping or boolean flattening during decoding.
                self.assertEqual(font.color_map[:4], (90, 0, 42, 0))
                self.assertIn(0, glyph.pixels)
                self.assertIn(1, glyph.pixels)  # Retained despite cmap[1] == 0.

    def test_multibit_remains_explicit_and_cooked_schema_stays_unsupported(self):
        for bpp, packed in ((2, b'\x00'), (2, b'\xff'), (4, b'\x00'), (4, b'\xff')):
            source = charset(bpp, 2, 1, packed)
            with self.subTest(bpp=bpp, packed=packed):
                # Even an all-zero multibit font must not silently become 1bpp.
                with self.assertRaisesRegex(ResourceError, 'explicit multibit'):
                    ScummV5Charset(source, key='synthetic')
                with self.assertRaisesRegex(ResourceError, 'explicit multibit'):
                    encode_charset(source, logical_id=2, source_id=2)
        font = ScummV5Charset(charset(1, 2, 1, b'\x80'), key='synthetic')
        self.assertEqual(font.glyph(1).pixels, b'\x01\x00')

    def test_host_renderers_reject_multibit_before_touching_pixels(self):
        for bpp in (2, 4):
            with self.subTest(bpp=bpp):
                source = charset(bpp, 3, 2, b'\xff\xff\xff')
                font = ScummV5Charset(source, key='synthetic', allow_multibit=True)
                target = IndexedSurface(16, 16)
                target.pixels[:] = bytes([83]) * len(target.pixels)
                before = bytes(target.pixels)
                adapter = ScummV5VideoAdapter(None)
                with self.assertRaisesRegex(ResourceError, 'requires a 1bpp charset'):
                    adapter._draw_text(target, SceneText(4, 0, 15, 'synthetic', '\x01'), font)
                self.assertEqual(bytes(target.pixels), before)

                resources = MemoryResourceProvider({'charset.2': source})
                context = SimpleNamespace(services=SimpleNamespace(
                    resources=resources, resource_read=resources.read))
                receiver = SimpleNamespace(_resource_key=lambda kind, number: f'{kind}.{number}')
                message = PrintMessageState(1, 0, PrintSlotState(charset=2), bytearray(b'\x01\0'))
                with self.assertRaisesRegex(ResourceError, 'explicit multibit'):
                    ScummV5Engine._present_print(receiver, context, message, target)
                self.assertEqual(bytes(target.pixels), before)

    def test_each_bit_depth_rejects_truncated_pixel_payload(self):
        for bpp in (1, 2, 4):
            source = bytearray(charset(bpp, 3, 3, bytes((9*bpp+7)//8)))
            source.pop()
            struct.pack_into('<I', source, 0, len(source)-15)
            with self.subTest(bpp=bpp):
                font = ScummV5Charset(bytes(source), key='synthetic', allow_multibit=True)
                with self.assertRaisesRegex(ResourceError, 'pixels are truncated'):
                    font.glyph(1)

    def test_header_table_and_glyph_bounds_fail_closed(self):
        source = charset(2, 3, 2, b'\x1b\x90')
        for length, message in ((24, 'shorter'), (28, 'offset table'), (39, 'header is out of bounds')):
            damaged = bytearray(source[:length])
            struct.pack_into('<I', damaged, 0, len(damaged)-15)
            with self.subTest(length=length), self.assertRaisesRegex(ResourceError, message):
                ScummV5Charset(bytes(damaged), key='synthetic', allow_multibit=True).glyph(1)
        damaged = bytearray(source)
        struct.pack_into('<I', damaged, 29, 4)  # Offset points into glyph table.
        with self.assertRaisesRegex(ResourceError, 'points into its header'):
            ScummV5Charset(bytes(damaged), key='synthetic', allow_multibit=True).glyph(1)
        for bpp in (0, 3, 8):
            with self.subTest(bpp=bpp), self.assertRaisesRegex(ResourceError, 'unsupported'):
                ScummV5Charset(charset(bpp, 1, 1, b'\0'), key='synthetic', allow_multibit=True)
