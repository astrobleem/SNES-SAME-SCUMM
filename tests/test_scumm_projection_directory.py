"""Decode emitted native ABI and compare samples with actual SC5VIS output."""
import struct
import unittest

from same.engines.scumm_v5.program_storage import _record_include, _projection_directory
from same.engines.scumm_v5.room_visual import (
    encode_room_visual, decode_room_visual, project_room_visual,
)


def row(room=4, sw=320, sh=200):
    return dict(room=room, package_offset=0, pixel_package_offset=100,
                pixel_length=57344, pixel_crc32='12345678',
                palette_package_offset=60000, palette_length=768,
                palette_crc32='87654321', width=256, height=224, pitch=256,
                projection=dict(source_width=sw, source_height=sh))


def emitted(include, label):
    lines = include.split(label + ':\n', 1)[1].splitlines()
    data = bytearray()
    for line in lines:
        if not line.startswith('    .byte '):
            break
        data.extend(int(value.strip()[1:], 16) for value in line[10:].split(','))
    return bytes(data)


class ProjectionDirectoryTests(unittest.TestCase):
    def include(self, rows, records=None):
        return _record_include(records or [], [], max(r['room'] for r in rows) + 1,
                               10, visual_records=rows)

    def test_native_abi_320x200_and_unchanged_visual_rows(self):
        include = self.include([row()])
        offsets = struct.unpack('<256H', emitted(include, 'ScummV5_MsuVisualProjectionOffsets'))
        self.assertEqual(offsets[4], 0)
        self.assertEqual(set(offsets[:4] + offsets[5:]), {0xFFFF})
        data = emitted(include, 'ScummV5_MsuVisualProjectionData')
        self.assertEqual(len(data), 844)
        self.assertEqual(struct.unpack_from('<6H', data), (320, 200, 256, 160, 0, 32))
        self.assertEqual(struct.unpack_from('<5H', data, 12), (0, 1, 3, 4, 5))
        visual = emitted(include, 'ScummV5_MsuVisualRecords')
        self.assertEqual(len(visual), 5 * 26)
        self.assertEqual(visual[:4 * 26], bytes(4 * 26))
        self.assertEqual(visual[4 * 26:], struct.pack(
            '<IHI IHI HHH', 100, 57344, 0x12345678, 60000, 768, 0x87654321, 256, 224, 256))
        self.assertIn('SCUMM_MSU1_PROJECTION_HEADER_SIZE = $000C', include)

    def test_identity_compatibility_and_geometry_deduplication(self):
        identity = row(1, 256, 224)
        old = row(255)
        del old['projection']
        offsets, data = _projection_directory([row(9), old, identity, row(4)])
        words = struct.unpack('<256H', offsets)
        self.assertEqual(words[1], words[255])
        self.assertEqual(words[4], words[9])
        self.assertNotEqual(words[1], words[4])
        self.assertEqual(len(data), 972 + 844)
        self.assertEqual(struct.unpack_from('<6H', data), (256, 224, 256, 224, 0, 0))
        self.assertEqual(struct.unpack_from('<256H', data, 12), tuple(range(256)))
        self.assertEqual(struct.unpack_from('<224H', data, 524), tuple(range(224)))
        self.assertEqual(_projection_directory([identity, row(4), row(9), old]), (offsets, data))

    def test_samples_match_real_projection_and_manifest_keys(self):
        for sw, sh in [(320, 200), (320, 144), (200, 320), (17, 13), (1, 600), (600, 1)]:
            with self.subTest(source=(sw, sh)):
                pixels = bytes((x * 73 + y * 29) % 256 for y in range(sh) for x in range(sw))
                source = encode_room_visual(
                    room=4, width=sw, height=sh, pitch=sw, pixels=pixels, palette=bytes(768),
                    archive_sha256='00' * 32, index_sha256='00' * 32,
                    data_sha256='00' * 32, room_sha256='00' * 32)
                projected, metadata = project_room_visual(source, target_width=256, target_height=224)
                entry = row()
                entry['projection'] = metadata  # actual storage manifest schema
                include = self.include([entry])
                data = emitted(include, 'ScummV5_MsuVisualProjectionData')
                rw, rh, cw, ch, ox, oy = struct.unpack_from('<6H', data)
                self.assertEqual((rw, rh), (sw, sh))
                xs = struct.unpack_from(f'<{cw}H', data, 12)
                ys = struct.unpack_from(f'<{ch}H', data, 12 + 2 * cw)
                output = bytearray(256 * 224)
                for y, sy in enumerate(ys):
                    for x, sx in enumerate(xs):
                        output[(oy + y) * 256 + ox + x] = pixels[sy * sw + sx]
                self.assertEqual(bytes(output), decode_room_visual(projected).pixels)

    def test_rejects_invalid_or_inconsistent_source_quality_metadata(self):
        for key, value in [('source_width', 0), ('source_height', 65536),
                           ('source_width', True), ('source_height', '200'),
                           ('source_pitch', 319), ('content_width', 255),
                           ('offset_y', 0), ('target_width', 320),
                           ('sampling', 'crop'), ('border_palette_index', 1)]:
            entry = row()
            entry['projection'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.include([entry])
        for metadata in [None, {}, {'source_width': 320}]:
            entry = row()
            entry['projection'] = metadata
            with self.assertRaises(ValueError):
                self.include([entry])
        for key, value in [('room', 256), ('width', 257), ('height', 225), ('pitch', 255)]:
            entry = row()
            entry[key] = value
            with self.assertRaises(ValueError):
                self.include([entry])

    def test_u16_bounds_and_directory_bank_capacity_include_projection(self):
        _, data = _projection_directory([row(0, 65535, 65535)])
        self.assertEqual(struct.unpack_from('<2H', data), (65535, 65535))
        with self.assertRaisesRegex(ValueError, 'u16 offset'):
            _projection_directory([row(i, 320 + i, 200) for i in range(100)])
        # Existing directories fit; added 512+844 bytes must reject the bank.
        records = [dict(program_unit_id=i, package_offset=0, length=1, crc32='00000000')
                   for i in range(3200)]
        with self.assertRaisesRegex(ValueError, 'LoROM data bank'):
            self.include([row()], records)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            _projection_directory([row(), row()])

    def test_separate_bank_placement_capacity_and_collision_guards(self):
        records = [dict(program_unit_id=i, package_offset=0, length=1, crc32='00000000')
                   for i in range(3200)]
        include = _record_include(records, [], 5, 10, visual_records=[row()],
                                  projection_directory_bank=19)
        before, after = include.split('.bank 19\n.org $8000\n')
        self.assertIn('ScummV5_MsuVisualRecords:', before)
        self.assertNotIn('ScummV5_MsuVisualRecords:', after)
        self.assertEqual(len(emitted(after, 'ScummV5_MsuVisualProjectionOffsets')), 512)
        self.assertEqual(len(emitted(after, 'ScummV5_MsuVisualProjectionData')), 844)
        for bank in [10, 11, 12, -1, 128, True]:
            with self.subTest(bank=bank), self.assertRaises(ValueError):
                _record_include([], [], 5, 10, visual_records=[row()],
                                projection_directory_bank=bank)
        with self.assertRaisesRegex(ValueError, 'projection directory exceeds'):
            _record_include([], [], 45, 10,
                            visual_records=[row(i, 320 + i, 200) for i in range(45)],
                            projection_directory_bank=19)


if __name__ == '__main__':
    unittest.main()
