import unittest
import zlib
import tempfile
import copy
from pathlib import Path
from dataclasses import replace

from same.errors import ResourceError, PackageFormatError
from same.engines.scumm_v5.object_images import ObjectImage
from same.engines.scumm_v5.object_image_storage import (
    MAX_CHECKED_BYTES, compile_object_strips, object_strip_manifest,
    compile_room_object_strips, native_object_directory,
)
from test_scumm_object_images import room, obj, image as raw_image
from same.engines.scumm_v5.object_images import decode_object_images
from same.engines.scumm_v5.program_storage import build_program_storage
from same.package import inspect_package


def source(width=24, height=239, planes=3, identity=17, state=1):
    # Opaque zero and nonzero transparent source pixels both occur.
    return ObjectImage(identity, state, width, height,
                       bytes(i % 256 for i in range(width * height)),
                       bytes(i % 5 != 0 for i in range(width * height)),
                       tuple(bytes((i * 13 + p) % 256 for i in range(width // 8 * height))
                             for p in range(planes)), 'ab' * 32)


class ObjectStripStorageTests(unittest.TestCase):
    def test_native_indexes_cannot_alias_or_omit_checked_source_blocks(self):
        r=room((obj(8), obj(9, parent=1, flags=0x80)))
        _, record=compile_room_object_strips(2,r,decode_object_images(raw_image(9,3)+raw_image(8,0),r))
        record['package_offset']=0
        for field,value in (('offset',1),('length',1),('crc32',0),('local',1),
                            ('world_y',3),('rows',1),('state',2)):
            bad=copy.deepcopy(record);bad['native_blocks'][0][field]=value
            with self.subTest(field=field), self.assertRaisesRegex(ResourceError,'indexes differ'):
                native_object_directory([bad],first_bank=101)
        for mutate in (lambda r:r['native_blocks'].reverse(),
                       lambda r:r['native_blocks'].pop(),
                       lambda r:r['columns'][0].update(count=1)):
            bad=copy.deepcopy(record);mutate(bad)
            with self.assertRaisesRegex(ResourceError,'indexes differ'):
                native_object_directory([bad],first_bank=101)

    def test_samepkg_preserves_every_checked_block_and_reproduces_descriptors(self):
        r = room((obj(8),))
        resource = compile_room_object_strips(1, r, decode_object_images(raw_image(8, 0), r))
        directory = {'entries': [{'program_unit_id': 0, 'identity': 'GlobalProgram(1)',
                                 'bundle': 'global', 'dispatch': {'kind': 'global'},
                                 'source_provenance': {'body_offset': 0}}]}
        outputs = []
        with tempfile.TemporaryDirectory() as tmp:
            for attempt in range(2):
                root = Path(tmp) / str(attempt)
                result = build_program_storage(directory, {'GlobalProgram(1)': b'\0'}, root,
                                               room_object_resources={1: resource})
                path = root / 'scumm-programs.msu'
                info = inspect_package(path, verify=True)
                self.assertEqual(next(s.kind for s in info.sections if s.name == 'SC5OBJ'), 'SCVO')
                data = path.read_bytes()
                entry = result['object_image_records'][0]
                self.assertEqual(data[entry['package_offset']:entry['package_offset']+len(resource[0])], resource[0])
                outputs.append((data, (root / 'scumm_msu1_programs.inc.pasm').read_bytes()))
            self.assertEqual(*outputs)
            bad = bytearray(outputs[0][0])
            bad[entry['package_offset']] ^= 1
            path.write_bytes(bad)
            with self.assertRaisesRegex(PackageFormatError, "CRC mismatch"):
                inspect_package(path, verify=True)

    def test_room_columns_retain_parent_identity_and_reverse_painter_order(self):
        r = room((obj(8), obj(9, parent=1, flags=0x80)))
        images = decode_object_images(raw_image(9, 3) + raw_image(8, 0), r)
        data, record = compile_room_object_strips(2, r, images)
        self.assertEqual([b['local'] for b in record['native_blocks']], [2, 1])
        self.assertEqual(record['columns'], [dict(first=0, count=2), dict(first=2, count=0)])
        self.assertEqual(record['objects'][1]['parent'], 1)
        self.assertEqual(record['objects'][1]['parent_state'], 1)
        record['package_offset'] = 0x123456
        include, banks = native_object_directory([record], first_bank=101)
        self.assertEqual(banks, (101, 102))
        self.assertIn('SCUMM_MSU1_OBJECT_BLOCK_BANK = $66', include)
        self.assertIn('SCUMM_MSU1_OBJECT_BLOCK_COUNT = $0002', include)
        self.assertTrue(data)
        record['package_offset'] = 0xffffffff
        with self.assertRaisesRegex(ResourceError, 'address/length'):
            native_object_directory([record], first_bank=101)
        record['package_offset'] = 0
        with self.assertRaisesRegex(ResourceError, 'mapped LoROM'):
            native_object_directory([record], first_bank=127)

    def test_large_multiplane_image_roundtrips_every_covered_pixel_and_mask(self):
        image = source()
        data, blocks = compile_object_strips((image,))
        pixels = bytearray(len(image.pixels))
        coverage = bytearray(len(image.pixels))
        masks = [bytearray(len(p)) for p in image.zplanes]
        seen = set()
        self.assertGreater(len(data), 2048)
        for block in blocks:
            self.assertLessEqual(block.length, MAX_CHECKED_BYTES)
            colors, bits, planes = block.decode(data[block.offset:block.offset + block.length])
            for row in range(block.rows):
                y = block.first_row + row
                self.assertNotIn((block.column, y), seen)
                seen.add((block.column, y))
                start = y * image.width + block.column * 8
                pixels[start:start + 8] = colors[row * 8:row * 8 + 8]
                coverage[start:start + 8] = bits[row * 8:row * 8 + 8]
                for output, plane in zip(masks, planes):
                    output[y * (image.width // 8) + block.column] = plane[row]
        self.assertEqual(len(seen), image.width // 8 * image.height)
        self.assertEqual(coverage, image.coverage)
        self.assertEqual(pixels, bytes(c if a else 0 for c, a in zip(image.pixels, image.coverage)))
        self.assertEqual(tuple(bytes(p) for p in masks), image.zplanes)
        self.assertTrue(any(a and c == 0 for c, a in zip(pixels, coverage)))

    def test_deterministic_identity_order_and_empty_collection(self):
        a, b = source(identity=31), source(identity=3, state=2)
        self.assertEqual(compile_object_strips((a, b)), compile_object_strips((b, a)))
        self.assertEqual(compile_object_strips(()), (b'', ()))
        data, blocks = compile_object_strips((a, b))
        manifest = object_strip_manifest((a, b), blocks, data)
        self.assertEqual([i['object_id'] for i in manifest['images']], [3, 31])
        self.assertEqual(manifest['native_acceptance'], 'NOT_VERIFIED')

    def test_crc_truncation_and_semantic_corruption_are_rejected(self):
        data, blocks = compile_object_strips((source(),))
        block = blocks[0]
        raw = data[:block.length]
        for bad in (raw[:-1], raw + b'\0', bytes([raw[0] ^ 1]) + raw[1:]):
            with self.assertRaises(ResourceError):
                block.decode(bad)
        bad = bytearray(raw)
        bad[0] &= 0x7f  # uncovered pixel must have canonical zero storage
        bad[1] = 7
        with self.assertRaisesRegex(ResourceError, 'canonical zero'):
            replace(block, crc32=zlib.crc32(bad)).decode(bad)
        for changed in (dict(rows=0), dict(rows=65535), dict(planes=256),
                        dict(first_row=65535), dict(length=1025), dict(state=0)):
            with self.assertRaises(ResourceError):
                replace(block, **changed).decode(raw)

    def test_bad_decoded_source_is_not_packaged(self):
        image = source()
        for bad in (replace(image, coverage=b''), replace(image, width=25),
                    replace(image, zplanes=(b'',)), replace(image, object_id=0),
                    replace(image, coverage=bytes([2]) * len(image.coverage))):
            with self.assertRaises(ResourceError):
                compile_object_strips((bad,))
        with self.assertRaises(ResourceError):
            compile_object_strips((image, image))

    def test_exact_chunk_boundary_and_zero_plane_images(self):
        # Seven planes give 16 bytes per row; exactly 64 rows fill 1 KiB.
        for planes, height, expected in ((7, 64, [1024]), (7, 65, [1024, 16]),
                                        (0, 114, [1017, 9])):
            data, blocks = compile_object_strips((source(width=8, height=height, planes=planes),))
            self.assertEqual([b.length for b in blocks], expected)
            for b in blocks:
                b.decode(data[b.offset:b.offset + b.length])


if __name__ == '__main__':
    unittest.main()
