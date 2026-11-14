import hashlib
import struct
import unittest
import zlib
import tempfile
from pathlib import Path
from same.package import inspect_package
from same.engines.scumm_v5.program_storage import build_program_storage
from same.errors import ResourceError
from same.engines.scumm_v5.room_masks import (
    encode_room_masks, decode_room_masks, decode_block, native_directory, HEADER, ENTRY, RAW, RLE,
)

class RoomMaskTests(unittest.TestCase):
    def fixture(self):
        width,height=32,300
        planes=(bytes((y*17+x*63)&255 if x in (1,3) else 0 for y in range(height) for x in range(4)),
                bytes(255 if x==2 and 100<y<270 else 0 for y in range(height) for x in range(4)))
        raw=encode_room_masks(room=7,width=width,height=height,planes=planes,source_room_sha256=hashlib.sha256(b'original fixture').hexdigest(),walkbox_masks=bytes((0,1,3)))
        return raw,planes

    def test_roundtrip_original_strip_order_planes_and_block_boundaries(self):
        raw,planes=self.fixture();r=decode_room_masks(raw,expected_room=7)
        self.assertEqual(r.planes,planes)
        self.assertEqual(r.walkbox_masks,bytes((0,1,3)))
        self.assertEqual(len(r.blocks),16)
        self.assertEqual({b['codec'] for b in r.blocks},{0,1,2})
        for plane in (1,2):
            for y in range(300):
                for x in range(32):
                    self.assertEqual(r.covered(plane,x,y),bool(planes[plane-1][y*4+x//8]&(0x80>>(x&7))))
        self.assertFalse(r.covered(0,2,2));self.assertFalse(r.covered(1,-1,2))
        with self.assertRaises(ResourceError):r.covered(3,1,1)
        self.assertEqual(raw,self.fixture()[0])

    def test_checked_corruption_truncation_alias_and_wrong_identity(self):
        raw,_=self.fixture();r=decode_room_masks(raw)
        index=next(i for i,b in enumerate(r.blocks) if b['length'])
        entry=HEADER.size+index*ENTRY.size
        for mutation in ('pixel','offset','length','flags','tail','truncate'):
            data=bytearray(raw)
            if mutation=='pixel':data[r.blocks[index]['offset']]^=1
            elif mutation=='offset':struct.pack_into('<I',data,entry,HEADER.size)
            elif mutation=='length':struct.pack_into('<H',data,entry+4,257)
            elif mutation=='flags':data[entry+7]=1
            elif mutation=='tail':data.append(0)
            else:data.pop()
            with self.subTest(mutation=mutation),self.assertRaises(ResourceError):decode_room_masks(bytes(data))
        with self.assertRaises(ResourceError):decode_room_masks(raw,expected_room=8)

    def test_crc_valid_invalid_rle_cannot_expand_out_of_bounds(self):
        for data,rows in ((b'\xff\x80',200),(b'\x01\xff',4),(b'\x01',4)):
            with self.assertRaises(ResourceError):
                decode_block(data,codec=RLE,rows=rows,crc32=zlib.crc32(data)&0xffffffff)
        self.assertEqual(decode_block(b'\xff\x80',codec=RLE,rows=256,crc32=zlib.crc32(b'\xff\x80')&0xffffffff),b'\x80'*256)

    def test_unrepresentable_source_geometry_rejected(self):
        for width,height,planes in ((7,1,(b'0',)),(8,0,(b'',)),(8,1,()),(8,1,(b'',))):
            with self.assertRaises(ResourceError):
                encode_room_masks(room=1,width=width,height=height,planes=planes,source_room_sha256='00'*32)

    def test_samepkg_checked_blocks_and_deterministic_native_directory(self):
        raw, planes = self.fixture()
        directory = {"entries": [{"program_unit_id": 0, "identity": "GlobalProgram(1)",
                     "bundle": "global", "dispatch": {"kind": "global"},
                     "source_provenance": {"body_offset": 0}}]}
        results = []
        with tempfile.TemporaryDirectory() as temporary:
            for n in (0, 1):
                root = Path(temporary) / str(n)
                result = build_program_storage(directory, {"GlobalProgram(1)": b"\x00"},
                                               root, room_mask_resources={7: raw})
                package = (root / 'scumm-programs.msu').read_bytes()
                info = inspect_package(root / 'scumm-programs.msu', verify=True)
                self.assertEqual(next(s.kind for s in info.sections if s.name == 'SC5MASK'), 'SCVZ')
                row = result['mask_records'][0]
                start = row['package_offset']
                self.assertEqual(package[start:start+row['length']], raw)
                self.assertEqual(decode_room_masks(package[start:start+row['length']]).planes, planes)
                for b in row['blocks']:
                    start = b['package_offset']
                    checked = package[start:start+b['length']]
                    decode_block(checked, codec=b['codec'], rows=b['rows'], crc32=int(b['crc32'],16))
                include = (root / 'scumm_msu1_programs.inc.pasm').read_bytes()
                self.assertIn(b'ScummV5_MsuMaskRooms:', include)
                results.append((package, include))
            self.assertEqual(results[0], results[1])

    def test_native_directory_rejects_unrepresentable_checked_ranges(self):
        raw, _ = self.fixture()
        mask = decode_room_masks(raw)
        row = dict(room=7, width=mask.width, height=mask.height, planes=len(mask.planes),
                   blocks=[dict(b, package_offset=b['offset']) for b in mask.blocks])
        self.assertIn('ScummV5_MsuMaskBlocks0:', native_directory([row]))
        self.assertIn('SCUMM_MSU1_MASK_ROOM_ADDRESS = $608000', native_directory([row]))
        for room in (-1, 256):
            with self.assertRaises(ResourceError): native_directory([dict(row, room=room)])
        with self.assertRaises(ResourceError): native_directory([row, row])
        with self.assertRaises(ResourceError): native_directory([row], bank=127)
        bad = dict(row, blocks=[dict(row['blocks'][0], package_offset=0xffffffff, length=2)])
        with self.assertRaises(ResourceError): native_directory([bad])

    def test_walkbox_plane_bounds_and_native_metadata_capacity(self):
        for masks in (bytes(257),):
            with self.assertRaises(ResourceError):
                encode_room_masks(room=1,width=8,height=1,planes=(b'0',b'1'),source_room_sha256='00'*32,walkbox_masks=masks)
        raw, _=self.fixture();mask=decode_room_masks(raw)
        row=dict(room=7,width=mask.width,height=mask.height,planes=len(mask.planes),walkbox_masks=list(mask.walkbox_masks),blocks=[dict(b,package_offset=b['offset']) for b in mask.blocks])
        text=native_directory([row])
        self.assertIn('$03,$00,$00,$01,$03',text)

    def test_original_walkbox_selector_is_preserved_for_runtime_clamping(self):
        masks = bytes((0, 1, 2, 4, 255))
        raw = encode_room_masks(room=1, width=8, height=1, planes=(b'\x80',),
                                source_room_sha256='00'*32, walkbox_masks=masks)
        decoded = decode_room_masks(raw)
        self.assertEqual(decoded.walkbox_masks, masks)
        row = dict(room=1, width=8, height=1, planes=1, walkbox_masks=list(masks),
                   blocks=[dict(b, package_offset=b['offset']) for b in decoded.blocks])
        self.assertIn('$05,$00,$00,$01,$02,$04,$FF', native_directory([row]))
