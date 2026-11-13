"""Execute the production cached-column decoder, including split guard storage.

This instruction runner is host evidence; native timing/raster acceptance is
separate. Expected pixels come from an independent bitplane encoder.
"""
import random
import re
import unittest

from test_video_surface_sparse_underlay import ROOT, ServiceMachine


class ColumnMachine(ServiceMachine):
    def __init__(self):
        super().__init__()
        self.symbols.update(SAME_BWRAM_RETAINED_VIEWPORT=0x401084,
                            SAME_BWRAM_LIVE_ROOM_PENDING=0x4013C4,
                            SAME_BWRAM_RETAINED_GUARD_HEAD=0x4010C4,
                            SAME_MODE3_GUARD_TAIL=0x401BC4,
                            SAME_MODE3_WORK=0x41E750,
                            Same_Mode3_CharacterOrder=0x0FF000)
        text=(ROOT/'runtime/snes/services/video_mode3_retained.inc.pasm').read_text()
        definitions=re.findall(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;\n]+)',text,re.M)
        generated=(ROOT/'tools/generate_snes_video_backend.py').read_text()
        definitions+=re.findall(r'"(SAME_MODE3_WORK_[A-Z0-9_]+) = ([^"]+)"',generated)
        for name,expr in definitions:
            try:self.symbols[name]=self.value(expr)
            except (NameError,SyntaxError):pass
        self.symbols['Same_Mode3_RowPlanes']=self.symbols['SAME_MODE3_WORK_X0']&65535
        native=(ROOT/'runtime/snes/services/video_mode3.pasm').read_text()
        code='''Same_VideoSurface_DecodeColumn_Far:
php
phb
rep #$30
pha
phx
phy
jsl Same_Mode3_Retained_ReadColumn_Far
ply
plx
pla
plb
plp
rtl
'''
        code+=text[text.index('Same_Mode3_Retained_ReadColumn_Far:'):text.index('; Populate only the newly exposed')]
        code+=text[text.index('Same_Mode3_Retained_ShadowAddress:'):text.index('Same_Mode3_CommitViewportTile:')]
        code+=native[native.index('Same_Mode3_CharacterIndex:'):native.index('Same_Mode3_CharacterOrder:')]
        self.code=[];self.labels={}
        for line in code.splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.code)
            else:self.code.append(line)
        for tile in range(768):
            self.put(0x0FF000+tile*2,(tile%32)*24+tile//32)

    def seed(self, column, pixels):
        for ty in range(24):
            if column==32:
                address=(0x4010C4+ty*64 if ty<11 else 0x401BC4+(ty-11)*64)
            else:address=0x410000+(column*24+ty)*64
            for y in range(8):
                for plane in range(8):
                    value=sum(((pixels[(ty*8+y)*8+x]>>plane)&1)<<(7-x) for x in range(8))
                    self.put(address+(plane//2)*16+y*2+plane%2,value,1)


class CachedColumnTests(unittest.TestCase):
    def test_all_physical_columns_both_banks_and_guard_split(self):
        rng=random.Random(0x65816)
        for column in range(33):
            m=ColumnMachine()
            pixels=bytes(rng.randrange(256) for _ in range(1536))
            m.seed(column,pixels)
            m.put('MODE3_R_BASE',0)
            m.put('MODE3_R_NEXT',column*8)
            m.put('MODE3_R_DELTA',-8)
            m.put(0x4013C3,0xA5,1);m.put(0x4019C4,0x5A,1)
            m.call('DecodeColumn',p=0)
            self.assertEqual(m.ram[0x4013C4:0x4019C4],pixels,column)
            self.assertEqual(m.get(0x4013C3,1),0xA5)
            self.assertEqual(m.get(0x4019C4,1),0x5A)
            self.assertEqual(m.get('MODE3_R_HEIGHT'),192)
            self.assertEqual(m.get('MODE3_R_TOP'),0)
            self.assertEqual(m.get('MODE3_R_SOURCE_Y'),0)

    def test_world_base_wrap_direction_and_all_palette_bits(self):
        for base,nxt,delta in ((32,24,-8),(32,296,8),(512,0,-1),(0,528,1)):
            column=((nxt+(255 if delta>0 else 0))//8-base//8)%33
            pixels=bytes(range(256))*6
            m=ColumnMachine();m.seed(column,pixels)
            for name,value in (('BASE',base),('NEXT',nxt),('DELTA',delta)):m.put('MODE3_R_'+name,value)
            m.call('DecodeColumn',p=0)
            self.assertEqual(m.ram[0x4013C4:0x4019C4],pixels)


if __name__=='__main__':unittest.main()
