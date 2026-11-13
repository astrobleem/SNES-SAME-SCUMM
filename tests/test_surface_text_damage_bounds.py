"""Execute the native rectangle/clear leaves; independent clipping oracle."""
from pathlib import Path
import random
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/'runtime/snes/services/video_overlay_indexed.inc.pasm').read_text()

class BoundsMachine:
    def __init__(self):
        self.symbols={'SAME_VIDEO_TEXT_STATE':0x400780,'SAME_VIDEO_TEXT_TOP':192,
            'SAME_VIDEO_TEXT_BOTTOM':224,'SAME_BWRAM_SURFACE_BASE':0x402000}
        for name,offset in re.findall(r'^(SAME_TEXT_\w+) = SAME_VIDEO_TEXT_STATE\+\$([0-9A-F]+)',TEXT,re.M):
            self.symbols[name]=0x400780+int(offset,16)
        for i,name in enumerate(('X','Y','WIDTH','HEIGHT')):self.symbols['SAME_VIDEO_SURFACE_DAMAGE_'+name]=0x401060+2*i
        self.code=[];self.labels={};self.mem={};self.writes=[]
        for raw in TEXT.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.') or ' = ' in line:continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.code)
            else:self.code.append(line.split(None,1))
    def address(self,n):
        return self.symbols.get(n,n)
    def put(self,n,v,size=2):
        n=self.address(n)
        for i in range(size):self.mem[n+i]=(v>>(8*i))&255
    def get(self,n,size=2):
        n=self.address(n);return sum(self.mem.get(n+i,0)<<(8*i) for i in range(size))
    def run(self,label):
        a=x=y=0;wide=16;carry=zero=negative=False;pc=self.labels[label];returns=[]
        for _ in range(100000):
            ins=self.code[pc];pc+=1;op=ins[0];arg=ins[1] if len(ins)>1 else '';mask=(1<<wide)-1
            if arg.startswith('#'):
                v=int(arg[2:],16) if arg[1]=='$' else self.symbols[arg[1:]]
            elif op.endswith('.l'):
                address=self.symbols[arg.removesuffix(',x')]+(x if arg.endswith(',x') else 0)
                v=self.get(address,wide//8)
            result=None
            if op in ('lda','lda.l'):result=v
            elif op=='sta.l':self.put(address,a&mask,wide//8);self.writes.extend(range(address,address+wide//8))
            elif op=='clc':carry=False
            elif op=='sec':carry=True
            elif op in ('adc','adc.l'):result=(a&mask)+v+carry;carry=result>mask
            elif op in ('sbc','sbc.l'):result=(a&mask)-v-(not carry);carry=result>=0
            elif op in ('cmp','cmp.l'):
                r=((a&mask)-v)&mask;carry=(a&mask)>=v;zero=r==0;negative=bool(r&(1<<(wide-1)))
            elif op in ('inc','dec'):result=(a&mask)+(1 if op=='inc' else -1)
            elif op=='tax':x=a;zero=x==0
            elif op=='tay':y=a;zero=y==0
            elif op=='inx':x=(x+1)&65535;zero=x==0
            elif op=='dey':y=(y-1)&65535;zero=y==0
            elif op=='xba':result=(a>>8)|((a&255)<<8)
            elif op=='rep':
                if v&32:wide=16
            elif op=='sep':
                if v&32:wide=8
            elif op=='jsr':returns.append(pc);pc=self.labels[arg]
            elif op=='rts':
                if returns:pc=returns.pop()
                else:return
            elif op in ('bcc','bcs','beq','bne','bmi','bpl','bra','brl','jmp'):
                yes={'bcc':not carry,'bcs':carry,'beq':zero,'bne':not zero,'bmi':negative,'bpl':not negative}.get(op,True)
                if yes:pc=self.labels[arg]
            else:raise AssertionError(ins)
            if result is not None:
                a=(a&~mask)|(result&mask);zero=(a&mask)==0;negative=bool(a&(1<<(wide-1)))
        raise AssertionError('unbounded production leaf')
    def rect(self,which):return tuple(self.get('SAME_TEXT_'+which+'_'+e) for e in ('LEFT','TOP','RIGHT','BOTTOM'))
    def setrect(self,which,rect):
        for edge,v in zip(('LEFT','TOP','RIGHT','BOTTOM'),rect):self.put('SAME_TEXT_'+which+'_'+edge,v)

class TextDamageBoundsTests(unittest.TestCase):
    def test_signed_bearings_zero_sizes_and_clipping_match_draw_region(self):
        rng=random.Random(0xC23)
        m=BoundsMachine();m.run('Same_Text_ResetBounds');expected=(256,224,0,0)
        for _ in range(600):
            px,py=rng.randrange(0,400),rng.randrange(0,450)
            bx,by=rng.randrange(-128,128),rng.randrange(-128,128)
            w,h=rng.randrange(256),rng.randrange(256)
            for key,value in [('PEN_X',px),('PEN_Y',py),('X',bx),('Y',by),('WIDTH',w),('HEIGHT',h)]:m.put('SAME_TEXT_'+key,value)
            m.run('Same_Text_GlyphBounds')
            l,t,r,b=max(0,px+bx),max(192,py+by),min(256,px+bx+w),min(224,py+by+h)
            if w and h and l<r and t<b:expected=(min(l,expected[0]),min(t,expected[1]),max(r,expected[2]),max(b,expected[3]))
            self.assertEqual(m.rect('NEW'),expected)
            if rng.randrange(3)==0:m.run('Same_Text_ResetBounds');expected=(256,224,0,0)

    def test_replace_hide_and_empty_union_clear_only_owned_pixels(self):
        cases=[((0,0,0,0),(256,224,0,0)),((2,193,90,203),(256,224,0,0)),
            ((2,193,90,203),(3,194,45,201)),((2,193,45,201),(210,213,256,224)),
            ((0,192,256,224),(0,192,256,224)),((0,0,0,0),(255,223,256,224))]
        for old,new in cases:
            with self.subTest(old=old,new=new):
                m=BoundsMachine();m.setrect('OLD',old);m.setrect('NEW',new)
                live=[r for r in (old,new) if r[0]<r[2] and r[1]<r[3]]
                rect=(min(r[0] for r in live),min(r[1] for r in live),max(r[2] for r in live),max(r[3] for r in live)) if live else (0,192,1,193)
                base=m.symbols['SAME_BWRAM_SURFACE_BASE']
                for a in range(base-4,base+57348):m.mem[a]=0xA5
                m.run('Same_Text_Clear')
                expected={base+y*256+x for y in range(rect[1],rect[3]) for x in range(rect[0],rect[2])}
                actual={a for a in m.writes if base-4<=a<base+57348}
                self.assertEqual(actual,expected)
                self.assertTrue(all(m.mem[a]==(0 if a in expected else 0xA5) for a in range(base-4,base+57348)))
                self.assertEqual(m.rect('OLD'),old);self.assertEqual(m.rect('NEW'),new)

    def test_both_layout_passes_share_bounds_and_commit_only_after_publication(self):
        self.assertIn('jsr Same_Text_GlyphBounds',TEXT.split('Same_Text_Layout_fits:',1)[1].split('Same_Text_Layout_advance:',1)[0])
        publish=TEXT.split('Same_Text_Publish:',1)[1].split('Same_Text_Publish_done:',1)[0]
        self.assertLess(publish.index('bcs Same_Text_Publish_done'),publish.index('sta.l SAME_TEXT_OLD_LEFT'))
        self.assertIn('jsr Same_Text_ResetBounds',TEXT.split('Same_Text_Hide_ready:',1)[1].split('Same_Text_Hide_cursor_ready:',1)[0])
        self.assertLess(max(v for k,v in BoundsMachine().symbols.items() if '_OLD_' in k or '_NEW_' in k),0x4007E0)

if __name__=='__main__':unittest.main()
