"""Copyright-free source pixels; independent viewport and CRC oracles."""
import hashlib
import random
import unittest
import zlib

from same.engines.scumm_v5.room_visual import (
    HEADER, ROW, ResourceError, camera_viewport, decode_room_visual,
    encode_camera_room_visual,
)
from test_scumm_v5_room_visual import fixture


class CameraResourcesTests(unittest.TestCase):
    def test_strip_encoding_is_lossless_including_pitch_and_palette(self):
        for width,height,pitch in ((13,5,17),(640,144,640),(1280,200,1280),(1,1,1)):
            source=fixture(width=width,height=height,pitch=pitch)
            encoded,strips=encode_camera_room_visual(source)
            before,after=decode_room_visual(source),decode_room_visual(encoded)
            self.assertEqual((after.pixels,after.palette,after.width,after.height,after.pitch),
                             (before.pixels,before.palette,width,height,pitch))
            self.assertEqual(encode_camera_room_visual(encoded),(encoded,strips))
            self.assertEqual(HEADER.unpack_from(encoded)[1],2)
            for d in strips:
                chunk=encoded[d['offset']:d['offset']+d['length']]
                self.assertLessEqual(len(chunk),3132)
                self.assertEqual(d['crc32'],f'{zlib.crc32(chunk)&0xffffffff:08x}')
                for y in range(height):
                    start=y*pitch+d['x']; n=d['width']
                    self.assertEqual(chunk[y*8:y*8+n],before.pixels[start:start+n])

    def test_corruption_truncation_bad_directory_and_padding_rejected(self):
        body,ds=encode_camera_room_visual(fixture())
        for at in (ds[0]['offset'], HEADER.size+768, len(body)-1):
            bad=bytearray(body);bad[at]^=1
            with self.assertRaises(ResourceError):decode_room_visual(bytes(bad))
        with self.assertRaises(ResourceError):decode_room_visual(body[:-1])
        bad=bytearray(body);bad[-1]=1
        bad[HEADER.size-32:HEADER.size]=bytes(32)
        bad[HEADER.size-32:HEADER.size]=hashlib.sha256(bad).digest()
        with self.assertRaisesRegex(ResourceError,'padding'):decode_room_visual(bytes(bad))
        with self.assertRaisesRegex(ResourceError,'scratch'):
            encode_camera_room_visual(fixture(width=8,height=392,pitch=8))

    def test_camera_preserves_world_pixels_and_clamps_at_edges(self):
        rng=random.Random(52)
        for width,height in ((640,144),(1280,200),(64,48),(256,224)):
            v=decode_room_visual(fixture(width=width,height=height,pitch=width))
            for xstart in (-1000,0,64,320,10000,*[rng.randrange(-100,1300) for _ in range(12)]):
                for yc in (0,100,200):
                    out,g=camera_viewport(v,xstart=xstart,ycenter=yc)
                    want=bytearray(256*224)
                    cw,ch=min(256,width),min(192,height)
                    sx=max(0,min(width-cw,xstart+32));sy=max(0,min(height-ch,yc-ch//2))
                    dx,dy=(256-cw)//2,(192-ch)//2
                    for y in range(ch):
                        for x in range(cw):want[(dy+y)*256+dx+x]=v.pixels[(sy+y)*width+sx+x]
                    self.assertEqual(out,bytes(want))
                    self.assertEqual((g['source_x'],g['source_y']),(sx,sy))

    def test_package_camera_directory_keeps_all_strips_and_old_mode(self):
        import tempfile
        from pathlib import Path
        from same.engines.scumm_v5.program_storage import build_program_storage
        from same.package import inspect_package
        for width in (13,640,1280):
            original=fixture(width=width,height=144,pitch=width)
            directory={"entries":[{"program_unit_id":0,"identity":"GlobalProgram(1)"}]}
            with tempfile.TemporaryDirectory() as temp:
                paths=[Path(temp)/str(i) for i in range(2)]
                reports=[build_program_storage(directory,{"GlobalProgram(1)":b"\x00"},p,
                           room_visual_resources={7:original},visual_reserved_bottom=32,
                           visual_projection="camera-viewport",projection_directory_bank=19)
                         for p in paths]
                self.assertEqual(reports[0],reports[1])
                self.assertEqual((paths[0]/"scumm-programs.msu").read_bytes(),
                                 (paths[1]/"scumm-programs.msu").read_bytes())
                inspect_package(paths[0]/"scumm-programs.msu",verify=True)
                r=reports[0]['visual_records'][0]
                self.assertEqual(r['pixel_payload_length'],((width+7)//8)*8*144)
                self.assertEqual(r['pixel_length'],8*144)
                self.assertEqual(len(r['strips']),(width+7)//8)
                raw=(paths[0]/"scumm-programs.msu").read_bytes()
                for strip in r['strips']:
                    offset=r['package_offset']+strip['offset']
                    self.assertEqual(f"{zlib.crc32(raw[offset:offset+strip['length']])&0xffffffff:08x}",strip['crc32'])
                include=(paths[0]/'scumm_msu1_programs.inc.pasm').read_text()
                self.assertIn('SCUMM_MSU1_CAMERA_VIEWPORT = 1',include)
                self.assertIn('ScummV5_MsuCameraStripCrcs:',include)
