"""Native menu enumeration reads runtime C17/owner state; no source corpus."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


def machine():
    m=StripMachine()
    source=(ROOT/'runtime/snes/engines/scumm_v5_controller_menu.inc.pasm').read_text()
    source=source.split('ScummV5_Controller_MenuNext_Far:',1)[1].split('.if SAME_VIDEO_TEXT_SERVICE_AVAILABLE',1)[0]
    m.code=[];m.labels={};m.symbols['SCUMM_M23A_GLOBAL_OBJECT_COUNT']=128
    for raw in source.splitlines():
        line=raw.split(';')[0].strip()
        if not line or line.startswith('.'):continue
        if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
        else:m.code.append(line)
    return m


class _MenuHelpers:
    def verb(self,m,index,*,present=1,mode=1,length=6):
        base=m.symbols['SAME_SCUMM_C17_VERBS']+index*96
        for name,value in [('PRESENT',present),('MODE',mode),('NAME_LENGTH',length)]:
            m.put(base+m.symbols['SAME_SCUMM_C17_V_'+name],value,1)


class ControllerMenuTests(_MenuHelpers, unittest.TestCase):
    def test_hidden_saved_and_unnamed_verbs_are_not_resurrected(self):
        m=machine();m.put('SAME_SCUMM_PLAY_UI_MODE',1,1)
        self.verb(m,3,mode=0);self.verb(m,5,present=0);self.verb(m,7,length=1)
        self.verb(m,9);self.verb(m,200)
        m.put('SAME_SCUMM_PLAY_UI_TEMP',1);m.put('SAME_SCUMM_PLAY_UI_SELECTION',255)
        got=[]
        for _ in range(3):
            found,_=m.consume();self.assertTrue(found);got.append(m.get('SAME_SCUMM_PLAY_UI_SELECTION'))
        self.assertEqual(got,[9,200,9])
        m.put('SAME_SCUMM_PLAY_UI_TEMP',65535);m.consume()
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_SELECTION'),200)
        self.verb(m,9,mode=0);self.verb(m,200,mode=0)
        found,_=m.consume();self.assertFalse(found);self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_SELECTION'),65535)

    def test_inventory_is_owned_ordered_and_updates_without_guest_writes(self):
        m=machine();m.put('SAME_SCUMM_PLAY_UI_MODE',2,1)
        m.put(m.symbols['SAME_SCUMM_M23B_VARIABLES']+2,1)
        owners=m.symbols['SAME_SCUMM_OBJECT_OWNERS']
        for i,owner in [(0,1),(4,1),(7,2),(91,1),(127,1)]:m.put(owners+i,owner,1)
        original=bytes(m.ram[owners:owners+128])
        m.put('SAME_SCUMM_PLAY_UI_TEMP',1);m.put('SAME_SCUMM_PLAY_UI_SELECTION',127)
        got=[]
        for _ in range(4):
            found,_=m.consume();self.assertTrue(found);got.append(m.get('SAME_SCUMM_PLAY_UI_SELECTION'))
        self.assertEqual(got,[4,91,127,4]);self.assertEqual(m.ram[owners:owners+128],original)
        m.put(owners+91,2,1);m.consume();self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_SELECTION'),127)

    def test_empty_inventory_terminates_without_fabricated_object(self):
        m=machine();m.put('SAME_SCUMM_PLAY_UI_MODE',2,1)
        m.put(m.symbols['SAME_SCUMM_M23B_VARIABLES']+2,1)
        m.put('SAME_SCUMM_PLAY_UI_TEMP',1)
        found,writes=m.consume();self.assertFalse(found)
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_SELECTION'),65535)
        self.assertFalse(any(0x402000<=a<0x410000 for a in writes))


class ControllerMenuTextTests(_MenuHelpers, unittest.TestCase):
    def text_machine(self):
        m=machine()
        source=(ROOT/'runtime/snes/engines/scumm_v5_controller_menu.inc.pasm').read_text()
        first=source.split('ScummV5_Controller_MenuText_Far:',1)[1].split('ScummV5_Controller_MenuEmpty:',1)[0]
        following=source.split('ScummV5_Controller_MenuNext_Far:',1)[1].split('.if SAME_VIDEO_TEXT_SERVICE_AVAILABLE',1)[0]
        m.code=[];m.labels={}
        for raw in (first+'\nScummV5_Controller_MenuNext_Far:\n'+following).splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        m.symbols['ScummV5_Controller_MenuEmpty']=0x100000
        m.ram[0x100000:0x100010]=b'Inventory empty\0'
        return m

    def name(self,m,index,text):
        self.verb(m,index,length=len(text)+1)
        addr=m.symbols['SAME_SCUMM_C17_VERBS']+index*96+m.symbols['SAME_SCUMM_C17_V_NAME']
        m.ram[addr:addr+len(text)+1]=text+b'\0'

    def test_two_source_names_newline_guards_and_selection_preserved(self):
        m=self.text_machine();self.name(m,9,b'Look at');self.name(m,11,b'Pick up')
        m.put('SAME_SCUMM_PLAY_UI_MODE',1,1);m.put('SAME_SCUMM_PLAY_UI_SELECTION',9)
        m.put('SAME_SCUMM_C17_RECORD_OFFSET',9*96)
        base=m.symbols['SAME_VIDEO_TEXT_CONTROLLER_BUFFER'];m.put(base-1,0xAA,1);m.put(base+34,0xBB,1)
        m.consume();n=m.get('SAME_VIDEO_TEXT_CONTROLLER_LENGTH',1)
        self.assertEqual(m.ram[base:base+n],b'>Look at\xff\x01 Pick up')
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_SELECTION'),9)
        self.assertEqual(m.get('SAME_SCUMM_C17_RECORD_OFFSET'),9*96)
        self.assertEqual(m.get(base-1,1),0xAA);self.assertEqual(m.get(base+34,1),0xBB)

    def test_long_names_bounded_and_empty_inventory_explicit(self):
        m=self.text_machine();self.name(m,9,b'A'*40);self.name(m,11,b'B'*40)
        m.put('SAME_SCUMM_PLAY_UI_MODE',1,1);m.put('SAME_SCUMM_PLAY_UI_SELECTION',9);m.consume()
        base=m.symbols['SAME_VIDEO_TEXT_CONTROLLER_BUFFER'];n=m.get('SAME_VIDEO_TEXT_CONTROLLER_LENGTH',1)
        self.assertEqual(n,30);self.assertEqual(m.ram[base:base+n],b'>'+b'A'*13+b'\xff\x01 '+b'B'*13)
        m.put('SAME_SCUMM_PLAY_UI_MODE',2,1);m.put('SAME_SCUMM_PLAY_UI_SELECTION',65535);m.consume()
        self.assertEqual(m.ram[base:base+16],b'Inventory empty\0')

class ControllerMenuOwnershipTests(_MenuHelpers, unittest.TestCase):
    def frame_machine(self):
        m=machine();m.code=[];m.labels={}
        source=(ROOT/'runtime/snes/engines/scumm_v5_controller_menu.inc.pasm').read_text()
        for raw in source.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        return m

    def test_script_disables_an_open_page_before_accept(self):
        m=self.frame_machine();self.verb(m,11)
        m.put('SAME_SCUMM_PLAY_UI_MODE',1,1);m.put('SAME_SCUMM_PLAY_UI_SELECTION',11)
        m.put('SAME_SCUMM_PLAY_UI_SAVED_MODE',0,1)
        self.verb(m,11,mode=0);m.put('SAME_INPUT_PRESSED',0x80)
        owned,_=m.consume();self.assertTrue(owned)
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MODE',1),0)
        self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_MODE',1),0)
        self.assertEqual(m.get('SAME_SCUMM_SENTENCE_API_PENDING',1),0)

    def test_inventory_chooses_a_real_enabled_verb_and_rechecks_owner(self):
        m=self.frame_machine();self.verb(m,11)
        m.put('SAME_SCUMM_M23B_VARIABLES' ,0)
        m.put(m.symbols['SAME_SCUMM_M23B_VARIABLES']+2,1)
        owner=m.symbols['SAME_SCUMM_OBJECT_OWNERS']+91;m.put(owner,1,1)
        m.put('SAME_INPUT_PRESSED',0x1000)
        owned,_=m.consume();self.assertTrue(owned)
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MODE',1),2)
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_SELECTION'),91)
        self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_VERB',1),11)
        m.put(owner,2,1);m.put('SAME_INPUT_PRESSED',0x80);m.consume()
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MODE',1),0)
        self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_OBJECT'),0)
        self.assertEqual(m.get('SAME_SCUMM_SENTENCE_API_PENDING',1),0)


    def test_physical_snes_b_closes_page_without_submitting_or_changing_selection(self):
        for button, expected_mode in ((0x8000, 0), (0x0040, 1)):
            m=self.frame_machine();self.verb(m,11)
            m.put('SAME_SCUMM_PLAY_UI_MODE',1,1);m.put('SAME_SCUMM_PLAY_UI_SELECTION',11)
            m.put('SAME_SCUMM_PLAY_UI_SAVED_MODE',5,1)
            m.put('SAME_SCUMM_CONTROLLER_OBJECT',91);m.put('SAME_INPUT_PRESSED',button)
            owned,_=m.consume();self.assertTrue(owned)
            self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MODE',1),expected_mode)
            self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_OBJECT'),91)
            self.assertEqual(m.get('SAME_SCUMM_SENTENCE_API_PENDING',1),0)
            if button==0x8000:self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_MODE',1),5)
