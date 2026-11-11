"""Execute the actual HUD builder using original synthetic encoded name bytes."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'ScummV5_Controller_BuildHudText'


class HudMachine:
    def __init__(self, verb_length, object_length, flags=0x30, show=False, busy=False, verb_id=7):
        memory = (ROOT/'runtime/snes/kernel/memory.pasm').read_text()
        self.symbols = {name:int(value,16) for name,value in re.findall(
            r'^(SAME_\w+)\s*=\s*\$([0-9A-Fa-f]+)\b',memory,re.M)}
        self.symbols['SAME_OVERLAY_PRODUCER_TEMP'] = 0x406096
        source = (ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        source = source[source.index(PREFIX+'_Far:'):source.index('; Deprecated prompt storage') if show else source.index('ScummV5_Controller_ShowHud_Far:')]
        self.show, self.busy = show, busy
        self.service_styles = []
        self.symbols['SAME_VIDEO_SURFACE_DEST_X'] = 0x401050
        self.code, self.labels, self.offsets = [], {}, []
        width=16; position=0
        for raw in source.splitlines():
            line=raw.split(';',1)[0].strip()
            if line in ('.a8','.a16'): width=int(line[2:])
            if not line or line.startswith('.'): continue
            if line.endswith(':'): self.labels[line[:-1]]=len(self.code); continue
            op,_,arg=line.partition(' ')
            self.offsets.append(position)
            position += (2 if op in ('rep','sep','beq','bne','bcc','bcs','bra') else
                         3 if op in ('jmp','brl') else 4 if '.l' in op or op=='jsl' else
                         3 if op=='cpy' else 1+width//8 if arg.startswith('#') else 1)
            self.code.append((op,arg))
        self.mem={}; self.writes=[]; self.reads=[]; self.flags=flags
        self.buffer=self.symbols['SAME_VIDEO_TEXT_CONTROLLER_BUFFER']
        for address in range(self.buffer-4,self.buffer+40): self.mem[address]=0xA5
        self.put('SAME_SCUMM_CONTROLLER_VERB',verb_id,1)
        self.put('SAME_SCUMM_CONTROLLER_OBJECT',3)
        self.verb=self.symbols['SAME_SCUMM_C17_VERBS']+verb_id*96+32
        self.obj=self.symbols['SAME_SCUMM_OBJECT_NAMES']+3*32
        # Public synthetic byte strings; no archive or title-specific text.
        self.verb_bytes=bytes(65+i%26 for i in range(64))
        self.object_bytes=bytes(97+i%26 for i in range(32))
        for base,data in ((self.verb,self.verb_bytes),(self.obj,self.object_bytes)):
            for i,value in enumerate(data):self.mem[base+i]=value
        self.put('SAME_SCUMM_C17_INITIALIZED',1,1)
        self.put(self.verb-32+self.symbols['SAME_SCUMM_C17_V_PRESENT'],1,1)
        self.put(self.verb-32+self.symbols['SAME_SCUMM_C17_V_MODE'],1,1)
        self.put(self.verb-8,verb_length,1)
        self.put(self.verb-32+self.symbols['SAME_SCUMM_C17_V_COLOR'], 6, 1)
        self.put(self.verb-32+self.symbols['SAME_SCUMM_C17_V_CHARSET'], 3, 1)
        self.style_base = self.symbols['SAME_SCUMM_C23_SLOTS']
        self.style = bytes((i*17+9)&255 for i in range(12))
        for i,value in enumerate(self.style): self.mem[self.style_base+i]=value
        self.put('SAME_SCUMM_CONTROLLER_CURSOR_X',100)
        self.put('SAME_SCUMM_CONTROLLER_CURSOR_Y',90)
        self.put('SAME_SCUMM_CAMERA_VSCREEN_XSTART',20)
        self.put('SAME_VIDEO_SURFACE_DEST_X',5)
        self.put(self.symbols['SAME_SCUMM_OBJECT_NAME_LENGTH']+3,object_length,1)

    def put(self, address, value, size=2):
        if isinstance(address,str):address=self.symbols[address]
        for i in range(size):self.mem[address+i]=(value>>(i*8))&255

    def get(self,address,size=2):
        if isinstance(address,str):address=self.symbols[address]
        return sum(self.mem.get(address+i,0)<<(i*8) for i in range(size))

    def run(self):
        a,x,y,p,db=0xABCD,0x12,0x34,self.flags,0x53
        stack=[];pc=self.labels['ScummV5_Controller_ShowHud_Far'] if self.show else 0
        initial=(a,x,y,p,db);returns=[]
        for _ in range(10000):
            op,arg=self.code[pc];pc+=1
            width=8 if p&32 else 16; iw=8 if p&16 else 16;mask=(1<<width)-1
            value=address=result=None
            if arg.startswith('#'):
                term=arg[1:];value=int(term[1:],16) if term.startswith('$') else self.symbols[term]
            elif '.l' in op:
                term=re.sub(r'SAME_\w+',lambda m:str(self.symbols[m[0]]),arg.removesuffix(',x'))
                term=re.sub(r'\$([0-9A-Fa-f]+)',r'0x\1',term)
                address=eval(term,{'__builtins__':{}},{})+(x if arg.endswith(',x') else 0)
                if op!='sta.l':
                    value=self.get(address,width//8);self.reads.append((address,width//8))
            if op=='php':stack.append((p,8))
            elif op=='phb':stack.append((db,8))
            elif op=='pha':stack.append((a&mask,width))
            elif op=='phx':stack.append((x,iw))
            elif op=='phy':stack.append((y,iw))
            elif op=='pla':
                result,bits=stack.pop();assert bits==width
            elif op in ('plp','plb','plx','ply'):
                v,bits=stack.pop();assert bits==(iw if op in ('plx','ply') else 8)
                if op=='plp':p=v
                elif op=='plb':db=v
                elif op=='ply':y=v
                else:x=v
            elif op=='rep':p &= ~value
            elif op=='sep':p |= value
            elif op in ('lda','lda.l'):result=value
            elif op=='sta.l':self.put(address,a&mask,width//8);self.writes.append((address,width//8,a&mask))
            elif op=='and':result=a&value
            elif op=='asl':p=(p&~1)|int(bool(a&(1<<(width-1))));result=(a&mask)<<1
            elif op=='clc':p &= ~1
            elif op=='sec':p |= 1
            elif op=='cld':p &= ~8
            elif op in ('sbc','sbc.l'):
                assert not p&8
                result=(a&mask)-value-(1-(p&1));p=(p&~1)|int(result>=0)
            elif op in ('adc','adc.l'):
                result=(a&mask)+value+(p&1);p=(p&~1)|int(result>mask)
            elif op in ('inc','dec'):result=(a&mask)+(1 if op=='inc' else -1)
            elif op in ('tax','tay','tyx'):
                v=(y if op=='tyx' else a)&((1<<iw)-1)
                if op=='tay':y=v
                else:x=v
            elif op=='tya':result=y
            elif op=='txa':result=x
            elif op=='ldx':x=value
            elif op=='ldy':y=value
            elif op=='inx':x=(x+1)&((1<<iw)-1)
            elif op=='iny':y=(y+1)&((1<<iw)-1)
            elif op in ('cmp','cpy'):
                v=y if op=='cpy' else a&mask;p=(p&~3)|int(v>=value)|(2 if v==value else 0)
            elif op in ('beq','bne','bcc','bcs','bra','brl','jmp'):
                if {'beq':bool(p&2),'bne':not p&2,'bcc':not p&1,'bcs':bool(p&1)}.get(op,True):pc=self.labels[arg]
            elif op=='jsl':
                if arg in self.labels:
                    returns.append(pc);stack.append((0x123456,24));pc=self.labels[arg]
                else:
                    assert arg=='Same_VideoText_ShowSegment_Far'
                    self.service_styles.append(bytes(self.mem[self.style_base+i] for i in range(12)))
                    self.put('SAME_SCUMM_TALK_VISUAL_STATUS',int(self.busy),1)
                    # External service may clobber registers, DB and widths.
                    a,x,y,db=0xFEDC,0xBA98,0x7654,0x40
                    p &= ~0x30
            elif op=='rtl':
                if returns:
                    assert stack.pop()==(0x123456,24)
                    pc=returns.pop();continue
                if self.show:assert (a,x,y,p,db)==initial
                assert not stack and p==self.flags and db==0x53
                return bytes(self.mem[self.buffer+i] for i in range(32))
            else:raise AssertionError((op,arg))
            if result is not None:
                a=(a&~mask)|(result&mask);p=(p&~2)|(2 if a&mask==0 else 0)
        raise AssertionError('HUD loop did not terminate')


class HudTextTests(unittest.TestCase):
    def check_case(self, verb_length, object_length, flags=0x30):
        m=HudMachine(verb_length,object_length,flags);text=m.run()
        if verb_length==0:expected=b''
        else:
            expected=m.verb_bytes[:max(0,verb_length-1)][:31]
            if len(expected)<31:
                if expected:expected+=b' '
                expected+=m.object_bytes[:max(0,object_length-1)][:31-len(expected)]
        self.assertEqual(text[:len(expected)+1],expected+b'\0')
        self.assertEqual(m.get('SAME_VIDEO_TEXT_CONTROLLER_LENGTH',1),len(expected))
        self.assertEqual(m.get('SAME_SCUMM_TALK_RAW_LENGTH',1),len(expected))
        self.assertEqual(m.get('SAME_VIDEO_TEXT_CONTROLLER_VALID',1),int(verb_length!=0))
        self.assertEqual(m.get('SAME_SCUMM_TALK_VISUAL_STATUS',1),2*int(verb_length==0))
        # +32 length is allowed only its explicit reset/final length stores.
        length_address=m.buffer+32
        self.assertEqual([v for a,n,v in m.writes if a==length_address], [0,len(expected)])
        self.assertTrue(all(n==1 for a,n,v in m.writes if m.buffer<=a<m.buffer+34))
        self.assertEqual(bytes(m.mem[m.buffer+i] for i in range(-4,0)),b'\xA5'*4)
        self.assertEqual(bytes(m.mem[m.buffer+i] for i in range(34,40)),b'\xA5'*6)
        self.assertEqual(bytes(m.mem[m.verb+i] for i in range(64)),m.verb_bytes)
        self.assertEqual(bytes(m.mem[m.obj+i] for i in range(32)),m.object_bytes)
        for a,n in m.reads:
            if m.verb<=a<m.verb+64:self.assertLessEqual(a+n,m.verb+max(0,verb_length-1))
            if m.obj<=a<m.obj+32:self.assertLessEqual(a+n,m.obj+max(0,object_length-1))
        return m

    def test_encoded_length_boundaries_and_long_names(self):
        for verb in (0,1,2,30,31,32,33,64):
            for obj in (0,1,2,31,32):
                with self.subTest(verb=verb,object=obj):self.check_case(verb,obj)

    def test_empty_verb_never_reads_name_or_underflows_and_object_only_works(self):
        for length in (0,1):
            m=self.check_case(length,32)
            self.assertFalse(any(m.verb<=a<m.verb+64 for a,n in m.reads))

    def test_separator_and_terminator_fit_and_width_db_contract(self):
        for flags in (0,0x10,0x20,0x30):
            self.check_case(32,32,flags)
            self.check_case(31,32,flags)
            self.check_case(1,1,flags)

    def test_show_preserves_persistent_style_all_exits_and_forwards_selected_style(self):
        for flags in (0,0x10,0x20,0x30,0x39):
            for verb_length,busy in ((6,False),(6,True),(0,False)):
                with self.subTest(flags=flags,verb_length=verb_length,busy=busy):
                    m=HudMachine(verb_length,5,flags,show=True,busy=busy)
                    m.run()
                    self.assertEqual(bytes(m.mem[m.style_base+i] for i in range(12)),m.style)
                    if verb_length:
                        self.assertEqual(len(m.service_styles),1)
                        temporary=m.service_styles[0]
                        self.assertEqual(temporary[8:11],bytes((6,3,0)))
                        self.assertEqual(int.from_bytes(temporary[:2],'little'),135)
                        self.assertEqual(int.from_bytes(temporary[2:4],'little'),82)
                        self.assertEqual(temporary[11],m.style[11])
                        self.assertEqual(m.get('SAME_SCUMM_TALK_VISUAL_STATUS',1),int(busy))
                    else:
                        self.assertEqual(m.service_styles,[])
                        self.assertEqual(m.get('SAME_SCUMM_TALK_VISUAL_STATUS',1),2)

    def test_high_selected_verb_style_uses_resolved_record_offset(self):
        m=HudMachine(6,5,show=True,verb_id=255)
        m.put(m.verb-32+m.symbols['SAME_SCUMM_C17_V_COLOR'],12,1)
        m.put(m.verb-32+m.symbols['SAME_SCUMM_C17_V_CHARSET'],5,1)
        m.run()
        self.assertEqual(m.service_styles[0][8:11],bytes((12,5,0)))
        self.assertEqual(bytes(m.mem[m.style_base+i] for i in range(12)),m.style)

    def test_selected_mode_uses_authored_highlight_other_modes_normal(self):
        for mode in (0,1,2,3,4,255):
            for busy in (False,True):
                with self.subTest(mode=mode,busy=busy):
                    m=HudMachine(6,5,show=True,busy=busy,verb_id=255)
                    self.assertEqual(m.symbols['SAME_SCUMM_C17_V_HICOLOR'],3)
                    m.put('SAME_SCUMM_CONTROLLER_MODE',mode,1)
                    m.put(m.verb-32+m.symbols['SAME_SCUMM_C17_V_HICOLOR'],14,1)
                    m.run()
                    self.assertEqual(m.service_styles[0][8:11],bytes((14 if mode==1 else 6,3,0)))
                    self.assertEqual(bytes(m.mem[m.style_base+i] for i in range(12)),m.style)

    def test_frame_retries_only_busy_status(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        block=source.split('    jsl ScummV5_Controller_ShowHud_Far\n',1)[1]
        block=block.split('ScummV5_Controller_Frame__hud_done:',1)[0]
        ops=[]
        for raw in block.splitlines():
            line=raw.split(';',1)[0].strip()
            if line and not line.startswith('.'):
                op,_,arg=line.partition(' ');ops.append((op,arg))
        for status in (0,1,2):
            m=HudMachine(6,5)
            m.put('SAME_SCUMM_TALK_VISUAL_STATUS',status,1)
            m.put('SAME_SCUMM_CONTROLLER_HUD_DIRTY',0,1)
            m.code=[('php','')]+ops+[('plp',''),('rtl','')]
            m.labels={'ScummV5_Controller_Frame__hud_done':1+len(ops)}
            m.run()
            self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_HUD_DIRTY',1),int(status==1))
            self.assertEqual(m.get('SAME_SCUMM_TALK_VISUAL_STATUS',1),status)

    def test_uninitialized_absent_hidden_and_dim_verbs_never_read_names(self):
        for field, value in (('SAME_SCUMM_C17_INITIALIZED', 0),
                             ('SAME_SCUMM_C17_V_PRESENT', 0),
                             ('SAME_SCUMM_C17_V_MODE', 0),
                             ('SAME_SCUMM_C17_V_MODE', 2)):
            with self.subTest(field=field, value=value):
                m = HudMachine(6, 5, show=True)
                address = (m.symbols[field] if field.endswith('INITIALIZED')
                           else m.verb - 32 + m.symbols[field])
                m.put(address, value, 1)
                m.run()
                self.assertEqual(m.service_styles, [])
                self.assertEqual(m.get('SAME_VIDEO_TEXT_CONTROLLER_VALID', 1), 0)
                self.assertFalse(any(m.verb <= a < m.verb + 64 for a, n in m.reads))

    def test_short_branch_reach(self):
        m=HudMachine(1,1,show=True)
        for i,(op,arg) in enumerate(m.code):
            if op in ('beq','bne','bcc','bcs','bra'):
                distance=m.offsets[m.labels[arg]]-(m.offsets[i]+2)
                self.assertTrue(-128<=distance<=127,(op,arg,distance))


if __name__=='__main__':unittest.main()
