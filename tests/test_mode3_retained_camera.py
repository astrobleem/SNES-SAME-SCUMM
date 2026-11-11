"""Retained Mode-3 ownership oracle. Host evidence, not native acceptance."""
import unittest
import copy
import json
from pathlib import Path
from same.snes_video_backend import (
    RetainedCameraPlanner, retained_scene_tile, retained_map_offset,
    retained_scroll_hdma,
)
from same.snes_surface import encode_snes_8bpp_tile, decode_snes_8bpp_tile


def pixel(x, y):
    return ((x * 13) ^ (x >> 8) ^ (y * 37)) & 255


class RetainedCameraTests(unittest.TestCase):
    def test_layout_and_no_visible_alias_across_both_wraps(self):
        for origin in range(-70, 140):
            tiles = {retained_scene_tile(c, y)
                     for c in range(origin, origin+33) for y in range(24)}
            self.assertEqual(len(tiles), 792)
            self.assertTrue(tiles.isdisjoint(range(768,896)))
            self.assertLess(max(tiles)*64+63,0xf000)
        offsets = {retained_map_offset(x,y) for x in range(64) for y in range(32)}
        self.assertEqual(offsets,set(range(0,4096,2)))
        self.assertEqual(0xf000+4096,65536)

    def test_one_pixel_tile_repeated_reverse_and_boundaries(self):
        p=RetainedCameraPlanner(1536)
        g=0
        for target in (1,7,8,9,256,513,1001,1280,9999,-99,9,8,7,0):
            target=max(0,min(1280,target))
            while p.x!=target:
                g+=1;before=p.x;t=p.request(target,g)
                self.assertLessEqual(abs(t.source_x-before),8)
                self.assertLessEqual(len(t.columns),1)
                old=set(p.visible(before))
                for c in t.columns:
                    self.assertNotIn(c%33,{v%33 for v in old})
                    p.validate_column(t,c,bytes(1536));p.dma_completed(t,c)
                self.assertEqual(p.commit(t),p.x&511)
                self.assertTrue(all(p.tags[c%33]==c for c in p.visible(p.x)))

    def test_nonzero_cold_origin_keeps_native_physical_identity(self):
        p = RetainedCameraPlanner(640,32)
        self.assertEqual(p.slot(4),0)
        self.assertEqual(retained_scene_tile(4,0,base_column=4),0)
        ticket = p.request(40,1)
        self.assertEqual(ticket.columns,(36,))
        self.assertEqual(p.slot(36),32)
        p.validate_column(ticket,36,bytes(1536));p.dma_completed(ticket,36)
        self.assertEqual(p.commit(ticket),8)
        with self.assertRaises(ValueError): RetainedCameraPlanner(640,1)

    def test_deferred_crc_failure_and_stale_work_leave_committed_origin(self):
        p=RetainedCameraPlanner(640);t=p.request(1,1)
        with self.assertRaises(RuntimeError):p.commit(t)
        with self.assertRaises(ValueError):p.dma_completed(t,t.columns[0])
        with self.assertRaises(ValueError):p.validate_column(t,t.columns[0],bytes(1535))
        self.assertEqual((p.x,p.generation),(0,0))
        p.abort(t)
        with self.assertRaises(ValueError):p.commit(t)
        t=p.request(1,2)
        p.validate_column(t,t.columns[0],bytes(1536))
        with self.assertRaises(RuntimeError):p.commit(t) # queue refusal/deferred DMA
        p.dma_completed(t,t.columns[0]);p.commit(t)
        with self.assertRaises(ValueError):p.request(8,2)
        q=RetainedCameraPlanner(640,epoch=2)
        with self.assertRaises(ValueError):q.commit(t)

    def test_full_raster_from_retained_tiles_and_fixed_hud(self):
        p=RetainedCameraPlanner(1280);vram=bytearray(65536);tilemap=bytearray(4096)
        def load_column(c):
            for row in range(24):
                tile=retained_scene_tile(c,row)
                vram[tile*64:tile*64+64]=encode_snes_8bpp_tile(
                    [[pixel(c*8+x,row*8+y) for x in range(8)] for y in range(8)])
        def map_column(c):
            for row in range(24):
                off=retained_map_offset(c,row)
                tilemap[off:off+2]=retained_scene_tile(c,row).to_bytes(2,'little')
        for c in p.visible(p.x):load_column(c);map_column(c)
        # HUD is a fixed32x4 map below the HDMA split, with full8-bit colors.
        for row in range(24,28):
            for c in range(32):
                tile=row*32+c;vram[tile*64:tile*64+64]=encode_snes_8bpp_tile(
                    [[pixel(c*8+x,1000+row*8+y) for x in range(8)] for y in range(8)])
                off=retained_map_offset(c,row);tilemap[off:off+2]=tile.to_bytes(2,'little')
        generation=0
        for target in (1,8,263,520,9,0,1024):
            while p.x!=target:
                generation+=1;t=p.request(target,generation)
                for c in t.columns:
                    p.validate_column(t,c,bytes(pixel(c*8+x,y) for y in range(192) for x in range(8)))
                    load_column(c);p.dma_completed(t,c)
                for c in t.columns:map_column(c) # same NMI boundary as scroll
                p.commit(t)
            decoded={t:decode_snes_8bpp_tile(vram[t*64:t*64+64]) for t in range(920)}
            for y in range(224):
                for x in range(256):
                    sx=x+(p.x if y<192 else 0)
                    off=retained_map_offset(sx//8,y//8)
                    tile=int.from_bytes(tilemap[off:off+2],'little')
                    self.assertEqual(decoded[tile][y&7][sx&7],pixel(sx,y if y<192 else 1000+y))
        self.assertEqual(retained_scroll_hdma(513),b'\x7f\x01\0\x41\x01\0\x20\0\0\0')


class RetainedLayoutTests(unittest.TestCase):
    def test_extra_tiles_and_staging_have_explicit_disjoint_ownership(self):
        from same.snes_carrier import _validate_layout
        from same.snes_video_backend import validate_mode3_layout
        root=Path(__file__).resolve().parents[1]
        carrier=json.loads((root/'runtime/snes/carriers/sa1_bwram_layout.json').read_text())
        video=json.loads((root/'runtime/snes/video_backends/mode3_surface_layout.json').read_text())
        _validate_layout(carrier); validate_mode3_layout(video)
        head=carrier['backend_reserved']['allocations']['retained_guard_head']
        tail=carrier['retained_guard_tail_alias']
        self.assertEqual(head['bytes']+tail['bytes'],24*64)
        self.assertEqual(head['offset']+head['bytes'],0x384) # live-room control follows
        self.assertEqual(0x401bc4-0x4013c4,2048) # actor/read prefix remains exclusive
        for key,value in [('address','40:13C4'),('bytes',3133)]:
            bad=copy.deepcopy(carrier);bad['retained_guard_tail_alias'][key]=value
            with self.assertRaises(ValueError):_validate_layout(bad)
        for key,value in [('vram_tilemap_start',0xe000),('physical_columns',34),('hdma_channel',7)]:
            bad=copy.deepcopy(video);bad['retained_viewport'][key]=value
            with self.assertRaises(ValueError):validate_mode3_layout(bad)

    def test_legacy_palette_destination_survives_with_explicit_retirement(self):
        root=Path(__file__).resolve().parents[1]
        s=(root/'runtime/snes/engines/scumm_v5_msu_live_room.pasm').read_text()
        self.assertEqual(s.count('#<SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE'),2)
        self.assertEqual(s.count('#>SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE'),2)
        video=json.loads((root/'runtime/snes/video_backends/mode3_surface_layout.json').read_text())
        self.assertEqual(video['scroll_hdma']['address'],'41:E73A')
        self.assertIn('Same_VideoSurface_RetireScroll_Far',s)
