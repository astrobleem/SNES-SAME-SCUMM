"""Host instruction-runner coverage of native mailbox/activation boundaries.

Resolver/C4 services are bounded test doubles here; Nexen independently runs
source-compiled scripts with the actual resolver, cache and scheduler.
"""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


def machine(entry, prefix=''):
    m=StripMachine();m.code=[];m.labels={};active=[True];arms=[]
    text=(ROOT/'runtime/snes/engines/scumm_v5_input_script.inc.pasm').read_text()
    for raw in (prefix+'\n'+text).splitlines():
        line=raw.split(';')[0].strip()
        if line in ('.if SAME_BUILD_SCUMM_ROOM_SERVICE','.if SAME_BUILD_SCUMM_MSU1_PROGRAMS'):
            arms.append(True);active.append(active[-1]);continue
        if line=='.else':active[-1]=active[-2] and not arms[-1];continue
        if line=='.endif':active.pop();arms.pop();continue
        if not active[-1] or not line or line.startswith('.'):continue
        if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
        else:m.code.append(line)
    m.entry=0 if prefix else m.labels[entry]
    m.symbols.update(SCUMM_V5_MAX_SCRIPT_SLOTS=25,SCUMM_V5_NUM_GLOBAL_SCRIPTS=200,
                     SCUMM_VM_RUNNING=1,SCUMM_VM_STOPPED=4,SCUMM_ERR_SCRIPT=6,
                     SCUMM_ERR_SLOT_CAPACITY=7)
    m.calls=[];m.service_writes=[]
    def service(name,p,a):
        m.calls.append(name)
        if name.endswith('ResolveLocal') or name.endswith('ResolveGlobal'):
            return p|1, 0xD2
        if name.endswith('SetError'):m.put('SAME_SCUMM_ERROR',a,1)
        return p,a
    m.service=service
    return m


class InputNativeMailboxTests(unittest.TestCase):
    def queue(self,area=2,value=0,mode=1):
        return machine('ScummV5_Input_Queue_Far',f'rep #$30\nlda #{area}\nldx #{value}\nldy #{mode}\njmp ScummV5_Input_Queue_Far')

    def installed(self,m):
        m.put(m.symbols['SAME_SCUMM_M23B_VARIABLES']+64,204)
        m.put('SAME_SCUMM_C7_USERPUT_STATE',1)
        m.put('SAME_SCUMM_M23A_ACTIVE_ROOM',17,1)
        m.put('SAME_INPUT_EDGE_SEQUENCE',1)

    def test_each_area_exact_args_busy_and_repeated_edge(self):
        for area in range(1,6):
            m=self.queue(area,41,2);self.installed(m)
            owned,_=m.consume();self.assertTrue(owned)
            self.assertEqual([m.get('SAME_SCUMM_INPUT_'+n) for n in ('AREA','VALUE','MODE')],[area,41,2])
            self.assertEqual(m.get('SAME_SCUMM_INPUT_ACCEPTED'),1)
            m.consume();self.assertEqual(m.get('SAME_SCUMM_INPUT_ACCEPTED'),1)
            m.put('SAME_SCUMM_INPUT_PENDING',0,1)
            m.consume();self.assertEqual(m.get('SAME_SCUMM_INPUT_ACCEPTED'),1)
            m.put('SAME_INPUT_EDGE_SEQUENCE',2);m.consume()
            self.assertEqual(m.get('SAME_SCUMM_INPUT_ACCEPTED'),2)

    def test_absent_and_disabled_callback_never_queue_sentence(self):
        m=self.queue();owned,_=m.consume();self.assertFalse(owned)
        self.installed(m);m.put('SAME_SCUMM_C7_USERPUT_STATE',0)
        owned,_=m.consume();self.assertTrue(owned)
        self.assertEqual(m.get('SAME_SCUMM_INPUT_PENDING',1),0)
        self.assertEqual(m.get('SAME_SCUMM_SENTENCE_API_PENDING',1),0)

    def test_allocate_exact_local_frame_and_no_neighbor_write(self):
        for number,resolve in ((19,'Global'),(204,'Local')):
            m=machine('ScummV5_Input_Process_Far')
            for n,v,size in [('PENDING',1,1),('SCRIPT',number,1),('ROOM',17,1),('AREA',2,2),('VALUE',41,2),('MODE',1,2)]:m.put('SAME_SCUMM_INPUT_'+n,v,size)
            m.put('SAME_SCUMM_M23A_ACTIVE_ROOM',17,1)
            base=m.symbols['SAME_SCUMM_C4_SLOT_LOCALS']+64
            m.ram[base-2:base+66]=b'\xcc'*68
            m.consume()
            self.assertIn('ScummV5_Camera_FarCall_Resolve'+resolve,m.calls)
            self.assertEqual(m.get('SAME_SCUMM_INPUT_ALLOCATED'),1)
            self.assertEqual(m.get('SAME_SCUMM_INPUT_PENDING',1),0)
            self.assertEqual(bytes(m.ram[base:base+64]),b'\x02\0\x29\0\x01\0'+bytes(58))
            self.assertEqual(bytes(m.ram[base-2:base]),b'\xcc\xcc')
            self.assertEqual(bytes(m.ram[base+64:base+66]),b'\xcc\xcc')
            m.consume();self.assertEqual(m.get('SAME_SCUMM_INPUT_ALLOCATED'),1)

    def test_accepted_input_waits_for_nested_storage_then_allocates_once(self):
        m=machine('ScummV5_Input_Process_Far')
        m.put('SAME_SCUMM_INPUT_PENDING',1,1);m.put('SAME_SCUMM_INPUT_SCRIPT',204,1)
        m.put(m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+4,5,1)
        m.put(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_SLOT']+4,2,1)
        m.consume();self.assertEqual(m.calls,[])
        self.assertEqual(m.get('SAME_SCUMM_INPUT_PENDING',1),1)
        m.put(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_SLOT']+4,0,1)
        m.consume();self.assertEqual(m.get('SAME_SCUMM_INPUT_ALLOCATED'),1)
        self.assertEqual(m.get('SAME_SCUMM_INPUT_PENDING',1),0)

    def test_room_change_cancels_pending_event_before_resolve(self):
        m=machine('ScummV5_Input_Process_Far')
        m.put('SAME_SCUMM_INPUT_PENDING',1,1);m.put('SAME_SCUMM_INPUT_ROOM',17,1)
        m.put('SAME_SCUMM_M23A_ACTIVE_ROOM',18,1);m.consume()
        self.assertEqual(m.calls,[])
        self.assertEqual(m.get('SAME_SCUMM_INPUT_PENDING',1),0)
        self.assertEqual(m.get('SAME_SCUMM_INPUT_ALLOCATED'),0)

    def test_native_menu_dispatch_keeps_visible_selection_without_c20(self):
        import test_scumm_controller_menu as menu
        for mode, selection, area in ((1, 11, 1), (2, 91, 3)):
            helper=menu.ControllerMenuOwnershipTests()
            m=helper.frame_machine();helper.verb(m,11)
            q=self.queue()
            offset=len(m.code)
            m.code.extend(q.code)
            m.labels.update({label: offset+index for label,index in q.labels.items()})
            self.installed(m)
            m.put('SAME_SCUMM_PLAY_UI_MODE',mode,1)
            m.put('SAME_SCUMM_PLAY_UI_SELECTION',selection)
            m.put('SAME_SCUMM_CONTROLLER_VERB',11,1)
            m.put(m.symbols['SAME_SCUMM_M23B_VARIABLES']+2,1)
            m.put(m.symbols['SAME_SCUMM_OBJECT_OWNERS']+91,1,1)
            m.put('SAME_INPUT_PRESSED',0x80)
            m.consume()
            self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MODE',1),0)
            self.assertEqual([m.get('SAME_SCUMM_INPUT_'+n) for n in ('AREA','VALUE','MODE')],[area,selection,1])
            self.assertEqual(m.get('SAME_SCUMM_SENTENCE_API_PENDING',1),0)
            self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_VERB',1),11)

    def test_same_room_request_retires_old_input_and_loading_rejects_new_input(self):
        m=machine('ScummV5_Input_Process_Far')
        m.put('SAME_SCUMM_INPUT_PENDING',1,1)
        m.put('SAME_SCUMM_M23A_REQUEST_COUNT',1,1)
        m.consume()
        self.assertEqual(m.get('SAME_SCUMM_INPUT_PENDING',1),0)
        self.assertEqual(m.calls,[])
        for phase in (1,3,4,5):
            m=self.queue();self.installed(m);m.put('SAME_SCUMM_M23A_PHASE',phase,1)
            self.assertTrue(m.consume()[0])
            self.assertEqual(m.get('SAME_SCUMM_INPUT_ACCEPTED'),0)

    def test_cursor_command_publishes_signed_script_visible_state(self):
        text=(ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        code=text.split('ScummV5_Op_CursorCommand__done:',1)[1].split('ScummV5_Op_StringOps:',1)[0]
        code=code.replace('jmp ScummV5_Engine_Frame__next','rtl')
        for cursor,user in ((1,1),(0,0),(0xffff,0xfffe),(3,2)):
            m=machine('',prefix=code)
            m.put('SAME_SCUMM_C7_CURSOR_STATE',cursor)
            m.put('SAME_SCUMM_C7_USERPUT_STATE',user)
            m.consume()
            base=m.symbols['SAME_SCUMM_VARIABLES']
            self.assertEqual(m.get(base+104),cursor)
            self.assertEqual(m.get(base+106),user)
