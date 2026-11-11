"""Actual existing underlay instructions exchange foreground without a buffer.

Source-instruction evidence; native rendering remains a separate gate.
"""
import unittest
from test_video_surface_sparse_underlay import ServiceMachine
from test_video_surface_cursor_underlay import CursorMachine


class CameraExchangeTests(unittest.TestCase):
    def test_actor_two_swaps_preserve_opaque_zero_holes_and_new_background(self):
        m=ServiceMachine();runs=[(8*256+10,7),(9*256+12,4),(223*256+252,4)]
        m.capture(runs)
        for dest,count in runs:
            m.ram[m.surface+dest:m.surface+dest+count]=bytes(i%3 for i in range(count))
        foreground=bytes(m.ram[m.surface:m.surface+57344])
        self.assertFalse(m.call('ExchangeActorUnderlay'))
        self.assertEqual(m.get(m.header,1),0xaa)
        self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)
        m.ram[m.surface:m.surface+57344]=bytes([77])*57344
        self.assertFalse(m.call('ExchangeActorUnderlay'))
        self.assertEqual(m.get(m.header,1),0xa8)
        expected=bytearray([77])*57344
        for dest,count in runs:expected[dest:dest+count]=foreground[dest:dest+count]
        self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),expected)
        self.assertFalse(m.call('RestoreActorUnderlay'))
        self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),bytes([77])*57344)

    def test_cursor_two_swaps_keep_fixed_position_and_replace_underlay(self):
        m=CursorMachine();self.assertFalse(m.capture(240,188,16,16));m.paint_rect(240,188,16,16)
        for status in (0,0x10,0x20,0x30,0xcf,0xff):
            before=bytes(m.ram[m.surface:m.surface+57344])
            self.assertFalse(m.call('ExchangeCursorUnderlay',p=status))
            self.assertEqual(m.get(m.header,1),0xcb)
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)
            self.assertFalse(m.call('ExchangeCursorUnderlay',p=status))
            self.assertEqual(m.get(m.header,1),0xc9)
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),before)

    def test_busy_exchange_does_not_publish_or_modify_pixels(self):
        for m,name in ((ServiceMachine(),'Actor'),(CursorMachine(),'Cursor')):
            if name=='Actor':m.capture([(257,8)]);m.paint([(257,8)])
            else:m.capture();m.paint_rect()
            m.busy=True
            before=bytes(m.ram[m.surface:m.surface+57344]);header=m.get(m.header,1)
            self.assertTrue(m.call('Exchange'+name+'Underlay'))
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),before)
            self.assertEqual(m.get(m.header,1),header)

    def test_actor_rebase_clips_without_changing_foreground_or_source_identity(self):
        for delta in (-8,-7,-1,1,7,8):
            m=ServiceMachine();runs=[(256,7),(512+250,6),(40*256+80,12),(223*256+250,6)]
            m.capture(runs)
            expected=bytearray(m.original_surface)
            for dest,count in runs:
                m.ram[m.surface+dest:m.surface+dest+count]=bytes((i*53)&255 for i in range(count))
                y,x=divmod(dest,256)
                for i in range(count):
                    target=x+i-(delta if y<192 else 0)
                    if 0<=target<256:expected[y*256+target]=(i*53)&255
            self.assertFalse(m.call('ExchangeActorUnderlay'))
            m.put('MODE3_R_DELTA',delta)
            self.assertFalse(m.call('RebaseActorUnderlay'))
            self.assertEqual((m.get(m.header+1,1),m.get(m.header+2)),(4,7))
            self.assertFalse(m.call('ExchangeActorUnderlay'))
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),expected)
            self.assertFalse(m.call('RestoreActorUnderlay'))
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)


class ScrollFenceInstructionTests(unittest.TestCase):
    def test_actual_far_fence_checks_lock_and_both_generation_words(self):
        for locked,pending,committed,expected in ((0,7,7,False),(1,7,7,True),
                (0,7,6,True),(0,0x10007,7,True),(0,7,0x10007,True),
                (0,0x10007,0x10007,False)):
            m=ServiceMachine()
            m.symbols.update(SAME_MODE3_CONTROL_SURFACE_LOCKED=0x401014,
                            SAME_BWRAM_CONTROL_COMMITTED_GENERATION=0x401010,
                            SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI=0x401018)
            m.put('SAME_MODE3_CONTROL_SURFACE_LOCKED',locked,1)
            m.put('SAME_VIDEO_SURFACE_NEXT_GENERATION',pending,4)
            m.put('SAME_BWRAM_CONTROL_COMMITTED_GENERATION',committed&65535)
            m.put('SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI',committed>>16)
            for status in (0,0x20,0x30,0xcf,0xff):
                self.assertEqual(m.call('ScrollPresented',p=status),expected)


class CircularSurfaceInstructionTests(unittest.TestCase):
    def configure(self,m,origin):
        m.put('MODE3_R_ACTIVE',1,1);m.put('MODE3_R_INDEX_ORIGIN',origin)

    def physical(self,dest,origin):
        y,x=divmod(dest,256)
        return y*256+((x+origin)&255 if y<192 else x)

    def test_actor_and_cursor_journals_restore_circular_scene_and_fixed_hud(self):
        for origin in (1,7,8,127,248,255):
            for m in (ServiceMachine(),CursorMachine()):
                self.configure(m,origin)
                if isinstance(m,CursorMachine):
                    self.assertFalse(m.capture(240,188,16,16))
                    runs=[(y*256+240,16) for y in range(188,204)]
                    name='Cursor'
                else:
                    runs=[(20*256+240,16),(191*256+128,12),(192*256+248,8)]
                    m.capture(runs);name='Actor'
                for dest,count in runs:
                    for i in range(count):m.ram[m.surface+self.physical(dest+i,origin)]=0
                self.assertFalse(m.call('Exchange'+name+'Underlay'))
                self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)
                self.assertFalse(m.call('Exchange'+name+'Underlay'))
                self.assertFalse(m.call('Restore'+name+'Underlay'))
                self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)

    def test_pair_wraps_inside_row_and_preserves_neighbor_guards(self):
        for origin in (1,8,255):
            for row in (0,191,192,223):
                m=ServiceMachine();self.configure(m,origin)
                x=(255-origin)&255;dest=row*256+x
                before=bytearray(m.original_surface)
                before[self.physical(dest,origin)]=0x18
                before[self.physical(dest+1,origin)]=0xe7
                m.call('WriteIndexedPair',a=0xe718,x=dest)
                self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),bytes(before))

    def test_ring_view_recovers_every_pixel_without_moving_hud(self):
        from same.snes_video_backend import linearize_retained_index8
        pixels=bytes((x*13+y*19)&255 for y in range(224) for x in range(256))
        for origin in (0,1,8,127,255):
            physical=bytearray(pixels)
            for y in range(192):
                row=pixels[y*256:(y+1)*256]
                physical[y*256:(y+1)*256]=row[-origin:]+row[:-origin] if origin else row
            self.assertEqual(linearize_retained_index8(bytes(physical),origin=origin),pixels)
