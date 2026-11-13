"""Execute the production word compare/copy leaf, with a pending-bit ABI stub."""
from pathlib import Path
import random
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'runtime/snes/services/video_mode3.pasm'
SYMBOLS={'Same_Mode3_TileScratchLow':0xE6BA,'Same_Mode3_TileShadowLow':0,
         'SAME_MODE3_WORK_TILE':0x41E750,'SAME_MODE3_WORK_TEMP':0x41E766,
         'SAME_BWRAM_CONTROL_TILE_VALID':0x40100C,
         'SAME_MODE3_CONTROL_UNCHANGED_COUNT':0x40102C,
         'SAME_MODE3_CONTROL_CONVERTED_COUNT':0x40102A}

def run(tile, scratch, previous, valid, dbr):
    block=SOURCE.read_text().split('Same_Mode3_CommitEncodedTile:',1)[1].split('; --------------------------------------------------------------------------',1)[0]
    code=[];labels={}
    for raw in block.splitlines():
        line=raw.split(';')[0].strip()
        if not line or line.startswith('.'):continue
        if line.endswith(':'):labels[line[:-1]]=len(code)
        else:code.append(line.split(None,1))
    ram={};reads=set();writes=set();stack=[];pending=[]
    def put(n,v,width):
        for i in range(width//8):ram[n+i]=(v>>(i*8))&255
    def read(n,width):
        reads.update(range(n,n+width//8))
        return sum(ram.get(n+i,0xA5)<<(i*8) for i in range(width//8))
    for i,v in enumerate(scratch):ram[0x41E6BA+i]=v
    physical=(tile%32)*24+tile//32 if tile<768 else tile
    dest=0x410000+64*physical
    for i,v in enumerate(previous):ram[dest+i]=v
    put(SYMBOLS['SAME_MODE3_WORK_TILE'],tile,16)
    put(SYMBOLS['SAME_BWRAM_CONTROL_TILE_VALID'],valid,8)
    put(SYMBOLS['SAME_MODE3_CONTROL_UNCHANGED_COUNT'],17,16)
    put(SYMBOLS['SAME_MODE3_CONTROL_CONVERTED_COUNT'],29,16)
    a=x=y=pc=0;width=16;zero=carry=False;bank=dbr
    for count in range(800):
        op,*args=code[pc];pc+=1;arg=args[0] if args else '';mask=(1<<width)-1
        address=None;v=None
        if arg.startswith('#'):v=int(arg[2:],16)
        elif op.endswith(('.w','.l')):
            base=arg.split(',')[0];offset=y if arg.endswith(',y') else x if arg.endswith(',x') else 0
            address=SYMBOLS[base]+offset
            if op.endswith('.w'):address=(bank<<16)|(address&65535)
            if not op.startswith('sta'):v=read(address,width)
        result=None
        if op=='phb':stack.append(bank)
        elif op=='plb':bank=stack.pop()
        elif op=='pha':
            if width==16:stack.append(a>>8)
            stack.append(a&255)
        elif op=='sep':width=8 if v&32 else width
        elif op=='rep':width=16 if v&32 else width
        elif op.startswith('lda'):result=v
        elif op.startswith('sta'):put(address,a&mask,width);writes.update(range(address,address+width//8))
        elif op=='asl':result=(a&mask)<<1
        elif op=='tax':x=a&mask
        elif op=='ldy':y=v
        elif op=='inx':x=(x+1)&65535
        elif op=='iny':y=(y+1)&65535
        elif op in ('cmp.w','cpy'):
            lhs=y if op=='cpy' else a&mask;zero=lhs==v;carry=lhs>=v
        elif op=='inc':result=(a&mask)+1
        elif op in ('beq','bne','bcc'):
            if {'beq':zero,'bne':not zero,'bcc':not carry}[op]:pc=labels[arg]
        elif op=='jsr':
            if arg=='Same_Mode3_CharacterIndex':
                a=(a%32)*24+a//32 if a<768 else a
            else:
                assert arg=='Same_Mode3_SetPendingTile' and bank==dbr
                pending.append(a);a=0x1234;x=0x45;y=0x67 # helper may clobber
        elif op=='rts':
            assert not stack and bank==dbr and width==16
            allowed=set(range(dest,dest+64))|set(range(0x41E766,0x41E768))|set(range(0x40102A,0x40102E))
            assert writes<=allowed
            assert reads&set(range(0x410000,0x41E000))<=set(range(dest,dest+64))
            return bytes(ram[dest+i] for i in range(64)),pending,read(0x40102A,16),read(0x40102C,16),count
        else:raise AssertionError(op)
        if result is not None:a=(a&~mask)|(result&mask);zero=(a&mask)==0
    raise AssertionError('unbounded tile commit')

class TileShadowTests(unittest.TestCase):
    def test_all_byte_mismatch_positions_and_bank_edges(self):
        rng=random.Random(0x8B)
        for tile in (0,1,31,32,895):
            payload=bytes(rng.randrange(256) for _ in range(64))
            for mismatch in range(64):
                old=bytearray(payload);old[mismatch]^=255
                actual,pending,changed,unchanged,count=run(tile,payload,old,1,0x7E)
                self.assertEqual(actual,payload);self.assertEqual(pending,[(tile%32)*24+tile//32 if tile<768 else tile])
                self.assertEqual((changed,unchanged),(30,17));self.assertLess(count,600)

    def test_identical_and_invalid_shadow_have_distinct_publication(self):
        for byte in (0,1,128,255):
            for valid in (0,1):
                payload=bytes([byte])*64
                actual,pending,changed,unchanged,count=run(895,payload,payload,valid,0)
                self.assertEqual(actual,payload)
                self.assertEqual(pending,[] if valid else [895])
                self.assertEqual((changed,unchanged),(29,18) if valid else (30,17))
                self.assertLess(count,320)
