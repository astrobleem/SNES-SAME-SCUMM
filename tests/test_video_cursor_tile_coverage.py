"""Prove camera cursor candidate pruning from actual source coverage, not color.

The production facade runs in the source instruction runner. The backend
dirty-packet entry is observed; pixel encoding/native execution is separate.
"""
import random
import unittest
from test_video_surface_cursor_underlay import CursorMachine, SOURCE


class CoverageMachine(CursorMachine):
    def __init__(self):
        super().__init__()
        self.symbols['MODE3_R_NEXT']=0x401086
        self.rectangles=[]
        self.external_services={'Same_Mode3_Retained_MarkDamage_Far':self.mark}
        source=SOURCE.read_text()
        for i,name in enumerate(('CursorTileMasks','CursorWidthMasks')):
            address=0x149000+i*0x100
            self.symbols['Same_VideoSurface_'+name]=address
            section=source.split('Same_VideoSurface_'+name+':',1)[1].split('\nSame_',1)[0]
            words=[]
            for line in section.splitlines():
                if line.strip().startswith('.word'):words.extend(int(x.strip().replace('$',''),16) for x in line.split('.word')[1].split(','))
            for j,value in enumerate(words):self.put(address+j*2,value)

    def mark(self,a,x,y,p,db):
        self.rectangles.append(self.damage())
        # The backend may clobber these; the facade keeps its loop in owned
        # cursor scratch and restores its public register contract.
        return 0x1234,0x3456,0x5678,p,db


class CursorTileCoverageTests(unittest.TestCase):
    def test_all_alignment_clipping_and_dense_compatibility(self):
        rng=random.Random(0xC9)
        for x,y,w,h in [(x,y,16,16) for x in range(8) for y in range(8)]+[(249,219,7,5),(255,223,1,1),(240,192,16,16)]:
            for dense in (False,True):
                m=CoverageMachine();m.capture(x,y,w,h)
                rows=[0xFFFF if dense else rng.randrange(65536) for _ in range(h)]
                for i,mask in enumerate(rows):m.put(m.symbols['SAME_VIDEO_CURSOR_COVERAGE_LO' if i<8 else 'SAME_VIDEO_CURSOR_COVERAGE_HI']+(i%8)*2,mask)
                original=m.damage();pixels=bytes(m.ram[m.surface:m.surface+57344])
                m.call('MarkCursorCoverage',p=0)
                expected={( (x+dx)//8,(y+dy)//8) for dy,row in enumerate(rows) for dx in range(w) if row & (0x8000>>dx)}
                self.assertEqual({(a//8,b//8) for a,b,c,d in m.rectangles},expected)
                self.assertEqual(len(m.rectangles),len(expected))
                self.assertTrue(all(c==d==8 and a<256 and b<224 for a,b,c,d in m.rectangles))
                self.assertEqual(m.damage(),original)
                self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),pixels)

    def test_unaligned_camera_retains_dense_invalidation(self):
        for offset in range(1,8):
            m=CoverageMachine();m.capture(7,9,16,16);m.put('MODE3_R_NEXT',offset)
            before=m.damage();m.call('MarkCursorCoverage',p=0)
            self.assertEqual(m.rectangles,[before]);self.assertEqual(m.damage(),before)

    def test_empty_damage_does_not_mark_any_tile(self):
        m=CoverageMachine();m.put('SAME_VIDEO_SURFACE_DAMAGE_WIDTH',0)
        m.call('MarkCursorCoverage',p=0);self.assertEqual(m.rectangles,[])


if __name__=='__main__':unittest.main()
