"""Execute actual dense cursor service instructions; CanWrite is the only stub."""
import re
import unittest
from test_video_surface_sparse_underlay import ServiceMachine, ROOT, pixel_leaves

SOURCE = ROOT / 'runtime/snes/services/cursor_underlay.inc.pasm'


class CursorMachine(ServiceMachine):
    def __init__(self):
        super().__init__()
        self.symbols['SAME_VIDEO_CURSOR_UNDERLAY'] = 0x400620
        self.symbols['SAME_BWRAM_SURFACE_BASE'] = self.surface
        text = SOURCE.read_text() + pixel_leaves()
        for name, expr in re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+)', text, re.M):
            self.symbols[name] = self.value(expr)
        self.header = self.symbols['SAME_VIDEO_CURSOR_UNDERLAY']
        self.code, self.labels, self.offsets = [], {}, []
        position, width = 0, 16
        for raw in text.splitlines():
            line = raw.split(';', 1)[0].strip()
            if line in ('.a8', '.a16'): width = int(line[2:])
            if not line or line.startswith('.') or '=' in line: continue
            if line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
                continue
            self.offsets.append(position)
            self.code.append(line)
            op, _, arg = line.partition(' ')
            if op in ('rep', 'sep', 'bra', 'bcc', 'bcs', 'beq', 'bne'): size = 2
            elif op in ('jmp', 'jsr'): size = 3
            elif op == 'jsl' or '.l' in op: size = 4
            elif arg.startswith('#'): size = 1 + width // 8
            else: size = 1
            position += size
        self.ram[self.header-16:self.header] = bytes([0xD3])*16
        self.ram[self.header+288:self.header+480] = bytes([0xA7])*192

    def persistent(self):
        return bytes(self.ram[self.header:self.header+16] + self.ram[self.header+32:self.header+288])

    def capture(self, x=10, y=20, w=16, h=16, **kwargs):
        return self.call('CaptureCursorUnderlay', a=y*256+x, x=w, y=h, **kwargs)

    def paint_rect(self, x=10, y=20, w=16, h=16):
        for row in range(h):
            self.ram[self.surface+(y+row)*256+x:self.surface+(y+row)*256+x+w] = bytes([255])*w


class CursorUnderlayTests(unittest.TestCase):
    def test_maximum_roundtrip_commit_last_consumption_and_neighbor_sentinels(self):
        m = CursorMachine()
        self.assertFalse(m.capture())
        self.assertEqual(m.get(m.header, 1), 0xC9)
        self.assertEqual(m.get(m.header+12), 256)
        self.assertEqual(m.writes[-1], (m.header, 1))
        m.paint_rect()
        self.assertFalse(m.call('RestoreCursorUnderlay'))
        self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]), m.original_surface)
        self.assertEqual(m.get(m.header, 1), 0)
        self.assertEqual(m.get(m.header+1, 1), 1)
        m.ram[m.surface+20*256+10] = 99
        self.assertFalse(m.call('RestoreCursorUnderlay'))
        self.assertEqual(m.ram[m.surface+20*256+10], 99)
        self.assertEqual(m.ram[m.header-16:m.header], bytes([0xD3])*16)
        self.assertEqual(m.ram[m.header+288:m.header+480], bytes([0xA7])*192)

    def test_text_strip_does_not_restore_or_dirty_a_distant_cursor(self):
        for x,y,w,h,overlap in ((10,80,16,16,False),(10,176,16,16,False),
                              (10,177,16,16,True),(10,192,16,16,True),
                              (255,223,1,1,True)):
            with self.subTest(rect=(x,y,w,h)):
                m=CursorMachine();self.assertFalse(m.capture(x,y,w,h));m.paint_rect(x,y,w,h)
                for field,value in zip(('X','Y','WIDTH','HEIGHT'),(0,192,256,32)):
                    m.put('SAME_VIDEO_SURFACE_DAMAGE_'+field,value)
                before=bytes(m.ram[m.surface:m.surface+57344]);journal=m.persistent()
                self.assertFalse(m.call('RestoreCursorOverlappingDamage'))
                if overlap:
                    self.assertEqual(m.get(m.header,1),0)
                    self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)
                    self.assertEqual(m.damage(),(0,min(y,192),256,224-min(y,192)))
                else:
                    self.assertEqual(m.persistent(),journal)
                    self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),before)
                    self.assertEqual(m.damage(),(0,192,256,32))

    def test_overlap_query_validates_journal_and_preserves_busy_owner(self):
        for corrupt in (True,False):
            m=CursorMachine();self.assertFalse(m.capture(10,190,4,4));m.paint_rect(10,190,4,4)
            for field,value in zip(('X','Y','WIDTH','HEIGHT'),(0,192,256,32)):
                m.put('SAME_VIDEO_SURFACE_DAMAGE_'+field,value)
            if corrupt:m.put(m.header+12,17)
            else:m.busy=True
            before=bytes(m.ram[m.surface:m.surface+57344]);journal=m.persistent()
            self.assertTrue(m.call('RestoreCursorOverlappingDamage'))
            self.assertEqual(m.persistent(),journal)
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),before)

    def test_damage_survives_actor_reset_and_unions_next_capture(self):
        m = CursorMachine()
        self.assertFalse(m.capture(x=10, y=20, w=4, h=5))
        self.assertFalse(m.call('RestoreCursorUnderlay'))
        # Actor Restore resets/seeds damage, then caller merges old cursor.
        for field, value in zip(('X','Y','WIDTH','HEIGHT'), (40,50,3,4)):
            m.put('SAME_VIDEO_SURFACE_DAMAGE_'+field, value)
        self.assertFalse(m.call('MergeCursorDamage'))
        self.assertEqual(m.damage(), (10,20,33,34))
        self.assertFalse(m.capture(x=2, y=60, w=1, h=2))
        self.assertEqual(m.damage(), (2,20,41,42))

    def test_busy_capture_restore_and_live_journal_rejection_preserve_persistent_state(self):
        m = CursorMachine()
        m.busy = True
        old = m.persistent(), m.damage()
        self.assertTrue(m.capture())
        self.assertEqual((m.persistent(), m.damage()), old)
        m.busy = False
        self.assertFalse(m.capture())
        old = m.persistent(), m.damage()
        self.assertTrue(m.capture(x=30))
        self.assertEqual((m.persistent(), m.damage()), old)
        m.busy = True
        self.assertTrue(m.call('RestoreCursorUnderlay'))
        self.assertEqual((m.persistent(), m.damage()), old)

    def test_invalid_rectangles_do_not_publish_or_touch_pixels_damage_or_old_journal(self):
        cases = [(0,0,0,1),(0,0,1,0),(0,0,17,16),(0,0,16,17),
                 (255,0,2,1),(0,223,1,2),(0,224,1,1),(255,255,16,16)]
        for x,y,w,h in cases:
            with self.subTest(rect=(x,y,w,h)):
                m=CursorMachine(); old=m.persistent(),m.damage()
                self.assertTrue(m.capture(x,y,w,h))
                self.assertEqual((m.persistent(),m.damage()), old)
                self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)

    def test_corrupt_journal_is_fully_validated_before_restore(self):
        for off,value in [(6,0xFFFF),(8,0),(8,17),(10,17),(12,255)]:
            m=CursorMachine(); self.assertFalse(m.capture())
            m.paint_rect(); m.put(m.header+off,value)
            before=bytes(m.ram[m.surface:m.surface+57344]); old=m.persistent(),m.damage()
            self.assertTrue(m.call('RestoreCursorUnderlay'))
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),before)
            self.assertEqual((m.persistent(),m.damage()),old)

    def test_stale_room_or_generation_discards_without_surface_writes(self):
        for field in ('SAME_VIDEO_SURFACE_ROOM','SAME_VIDEO_SURFACE_ROOM_GENERATION'):
            m=CursorMachine(); self.assertFalse(m.capture());m.paint_rect()
            before=bytes(m.ram[m.surface:m.surface+57344]); damage=m.damage()
            m.put(field,99)
            self.assertFalse(m.call('RestoreCursorUnderlay'))
            self.assertEqual(m.get(m.header),0)
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),before)
            self.assertEqual(m.damage(),damage)
            self.assertFalse(m.call('MergeCursorDamage'))
            self.assertEqual(m.damage(),damage)

    def test_all_public_entries_preserve_registers_decimal_width_and_db(self):
        for p in (0,8,0x20,0x28,0x10,0x18,0x30,0x38,0xCF):
            m=CursorMachine()
            self.assertFalse(m.capture(w=1,h=1,p=p,db=0xA5))
            self.assertFalse(m.call('RestoreCursorOverlappingDamage',p=p,db=0xA5))
            self.assertFalse(m.call('MergeCursorDamage',p=p,db=0xA5))
            self.assertFalse(m.call('RestoreCursorUnderlay',p=p,db=0xA5))
            self.assertFalse(m.call('InvalidateCursorUnderlay',p=p,db=0xA5))
            self.assertEqual(m.get(m.header),0)

    def test_edge_rectangle_and_mapped_zero_snapshot(self):
        m=CursorMachine()
        for pos in (0,223*256+255):
            m.ram[m.surface+pos]=0
            self.assertFalse(m.call('CaptureCursorUnderlay',a=pos,x=1,y=1))
            m.ram[m.surface+pos]=255
            self.assertFalse(m.call('RestoreCursorUnderlay'))
            self.assertEqual(m.ram[m.surface+pos],0)

    def test_background_projection_invalidates_before_full_cover_early_return(self):
        source=(ROOT/'runtime/snes/services/video_surface.pasm').read_text()
        body=source.split('Same_VideoSurface_ClearForProjection:',1)[1].split(
            'Same_VideoSurface_ComputeProjection:',1)[0]
        self.assertLess(body.index('jsl Same_VideoSurface_InvalidateCursorUnderlay_Far'),
                        body.index('lda.l SAME_VIDEO_SURFACE_COPY_WIDTH'))

    def test_short_branches_fit_and_no_actor_or_rom_fallback(self):
        m=CursorMachine()
        for i,line in enumerate(m.code):
            op,_,arg=line.partition(' ')
            if op in ('bra','bcc','bcs','beq','bne'):
                displacement=m.offsets[m.labels[arg]]-(m.offsets[i]+2)
                self.assertTrue(-128<=displacement<=127,(line,displacement))
        source=SOURCE.read_text()
        for forbidden in ('SAME_SCUMM_ACTOR_', 'SAME_SCUMM_CURSOR_PRESENTATION',
                          'SAME_MODE3_WORK_', 'LoadRowTablePointer', 'RestoreRect_Far'):
            self.assertNotIn(forbidden,source)


if __name__=='__main__': unittest.main()
