"""Copyright-free native font/viewport compilation; not emulator evidence."""
from pathlib import Path
import json
import tempfile
import unittest
from same.engines.scumm_v5.font import decode_charset
from same.engines.scumm_v5.room_visual import project_room_visual, decode_room_visual, encode_room_visual
from same.engines.scumm_v5.program_storage import _projection_directory
from tools.generate_snes_scumm_charset import emit_native_v2
from tools.generate_snes_video_overlay import generate
from test_scumm_v5_font_multibit import source_font

ROOT = Path(__file__).resolve().parents[1]

class SurfaceTextTests(unittest.TestCase):
    def test_native_directory_preserves_identity_slots_and_wide_glyphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            sources={2:source_font(2,67,15,-2,1,[i%4 for i in range(67*15)]),
                     1:source_font(1,13,16,0,-1,[1]*208)}
            report=emit_native_v2(sources,root/'font.bin',root/'font.inc',root/'font.json')
            raw=(root/'font.bin').read_bytes();directory=(root/'font.directory.bin').read_bytes()
            for row in report['records']:
                i=row['logical_id'];at=int.from_bytes(directory[i*2:i*2+2],'little')
                f=decode_charset(raw[at:at+row['length']],expected_logical_id=i)
                self.assertEqual(f.source_id,i)
                self.assertEqual(f.sha256,row['sha256'])
            self.assertEqual(directory[:2],b'\xff\xff')
            self.assertEqual(decode_charset(raw[report['records'][1]['offset']:]).glyphs[65].width,67)
            other=root/'second';other.mkdir()
            same=emit_native_v2(dict(reversed(list(sources.items()))),other/'font.bin',other/'font.inc',other/'font.json')
            self.assertEqual(same,report)
            self.assertEqual((other/'font.bin').read_bytes(),raw)

    def test_bank_capacity_rejected_before_any_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            sources={i:source_font(4,255,255,0,0,[1]*(255*255)) for i in range(2)}
            with self.assertRaisesRegex(ValueError,'32 KiB'):
                emit_native_v2(sources,root/'font.bin',root/'font.inc',root/'font.json')
            self.assertEqual(list(root.iterdir()),[])

    def test_declared_viewport_for_tall_and_wide_rooms_and_projection_directory(self):
        for w,h in ((320,200),(100,500),(256,224)):
            raw=encode_room_visual(room=1,width=w,height=h,pitch=w,
                palette=bytes(768),pixels=bytes([73])*(w*h),
                archive_sha256='00'*32,index_sha256='01'*32,
                data_sha256='02'*32,room_sha256='03'*32)
            projected,meta=project_room_visual(raw,target_width=256,target_height=224,reserved_bottom=32)
            image=decode_room_visual(projected)
            self.assertEqual(image.pixels[192*256:],bytes(32*256))
            self.assertLessEqual(meta['offset_y']+meta['content_height'],192)
            _projection_directory([dict(room=1,width=256,height=224,pitch=256,projection=meta)])
            bad=dict(meta,reserved_bottom=0)
            with self.assertRaises(ValueError):
                _projection_directory([dict(room=1,width=256,height=224,pitch=256,projection=bad)])

    def test_surface_text_has_no_metadata_or_bg2_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            generate('surface_index8','sa1_bwram','mode3_surface',root,root/'manifest.json')
            constants=(root/'video_overlay_constants.inc.pasm').read_text()
            self.assertIn('SAME_VIDEO_SCENE_BOTTOM = $00C0',constants)
            self.assertNotIn('$41F',constants)
            self.assertNotIn('Bg2',(root/'video_overlay_code.inc.pasm').read_text())
            layout=json.loads((ROOT/'runtime/snes/carriers/sa1_bwram_layout.json').read_text())
            record=layout['protected_low']['allocations']['text_presentation']
            self.assertEqual((record['offset'],record['bytes']),(1920,128))

class TextObserverFenceTests(unittest.TestCase):
    def test_only_matching_completed_visible_text_passes_even_during_later_animation(self):
        from tools.validate_scumm_source_font_nexen import text_is_presented
        raw=bytearray(128)
        raw[2:4]=raw[4:6]=b'\x07\0'
        raw[0x68:0x6a]=b'\x01\0'
        state=dict(room=4,actor_render_valid=1,mode3_state=2,surface_packets_pending=True)
        self.assertTrue(text_is_presented(raw,state))
        for offset,value in ((0,1),(0,2),(0,3),(4,6),(4,0),(0x68,0)):
            altered=bytearray(raw);altered[offset]=value
            with self.subTest(offset=offset,value=value):self.assertFalse(text_is_presented(altered,state))

class NativeTalkScannerTests(unittest.TestCase):
    def test_actual_begin_scan_keeps_encoded_span_and_excludes_control_operands_from_timing(self):
        from test_scumm_controller_hud_text import HudMachine
        from same.engines.scumm_v5.engine import ScummV5Engine
        source = (ROOT/'runtime/snes/engines/scumm_v5_matrix_far.pasm').read_text()
        block = source.split('ScummV5_Talk_Begin_Far__scan_setup:',1)[1]
        block = block.split('ScummV5_Talk_Begin_Far__message_ready:',1)[0]
        for raw in (b'AB\0', b'A\xff\x01B\0',
                    b'A\xff\x0c\xf0\0B\xff\x0e\x02\0C\0',
                    b'A\xff\x0c\xf0\0B\xff\x03C\0'):
            with self.subTest(raw=raw):
                m = HudMachine(1,1)
                m.code=[('php','')];m.labels={};enabled=True
                for line in block.splitlines():
                    line=line.split(';',1)[0].strip()
                    if line.startswith('.if'):
                        self.assertEqual(line,'.if SAME_VIDEO_OVERLAY_INDEXED')
                        enabled=True
                    elif line=='.else': enabled=False
                    elif line=='.endif': enabled=True
                    elif not enabled or not line or line.startswith('.'):continue
                    elif line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                    else:
                        op,_,arg=line.partition(' ');m.code.append((op,arg))
                m.code.extend([('plp',''),('rtl','')])
                for i,value in enumerate(raw):m.put(m.symbols['SAME_SCUMM_TALK_RAW']+i,value,1)
                m.run()
                segment,cursor,final=ScummV5Engine._talk_segment(bytearray(raw),0)
                self.assertEqual(m.get('SAME_SCUMM_TALK_CURSOR',1),cursor if not final else cursor-1)
                self.assertEqual(m.get('SAME_SCUMM_TALK_SEGMENT_LENGTH',1),len(segment)-1)
                self.assertEqual(m.get('SAME_SCUMM_TALK_SEGMENT_GLYPHS',1),ScummV5Engine._talk_glyph_count(segment))
                self.assertEqual(m.get('SAME_SCUMM_TALK_HAVE_MSG',1),1 if final else 255)

if __name__=='__main__':unittest.main()
