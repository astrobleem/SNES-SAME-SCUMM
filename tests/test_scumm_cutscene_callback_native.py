"""Execute small production cutscene bridge blocks; not emulator acceptance."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class CutsceneCallbackNative(unittest.TestCase):
    def machine(self, code):
        m=StripMachine();m.code=[];m.labels={};m.service_writes=[]
        m.symbols.update(SCUMM_V5_MAX_SCRIPT_SLOTS=25, SAME_SCUMM_LOCAL_COUNT=32,
                         SCUMM_VM_STOPPED=4, SCUMM_VM_ERROR=255)
        for raw in code.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        return m

    def test_clear_entire_argument_frame_without_crossing_guards(self):
        s=(ROOT/'runtime/snes/engines/scumm_v5_cutscene_callbacks.inc.pasm').read_text()
        code=s.split('ScummV5_Cutscene_ClearArgs_Far:',1)[1].split('ScummV5_Cutscene_StartCallback_Far:',1)[0]
        m=self.machine(code);base=m.symbols['SAME_SCUMM_C4_ARGS']
        m.ram[base-1:base+65]=b'\xa5'*66
        m.consume()
        self.assertEqual(m.ram[base:base+64],bytes(64))
        self.assertEqual((m.ram[base-1],m.ram[base+64]),(0xa5,0xa5))

    def test_callback_index_survives_child_and_clears_on_caller_resume(self):
        s=(ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        code=s.split('ScummV5_Engine_Frame__next:',1)[1].split('    lda.l SAME_SCUMM_C18_NESTED',1)[0]+'rtl\n'
        for current,expected in ((3,1),(1,255)):
            with self.subTest(current=current):
                m=self.machine(code);m.put('SAME_SCUMM_C4_CURRENT_SLOT',current,1)
                m.put('SAME_SCUMM_C19_SCRIPT_INDEX',1,1);m.consume()
                self.assertEqual(m.get('SAME_SCUMM_C19_SCRIPT_INDEX',1),expected)

    def test_freeze_preserves_callback_caller_and_freezes_unrelated_scripts(self):
        s=(ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        body=s.split('ScummV5_Op_FreezeScripts__freeze_scan:',1)[1].split('    jmp ScummV5_Engine_Frame__next',1)[0]
        code=('sep #$20\nrep #$10\nldx #$0000\n'
              'ScummV5_Op_FreezeScripts__freeze_scan:\n'+body+'rtl\n')
        for owner in (1,255):
            with self.subTest(owner=owner):
                m=self.machine(code);m.put('SAME_SCUMM_C4_CURRENT_SLOT',3,1)
                m.put('SAME_SCUMM_C19_SCRIPT_INDEX',owner,1);m.put('SAME_SCUMM_CONDITION',1,1)
                for slot in range(5):m.ram[m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+slot]=2
                m.consume()
                self.assertEqual(list(m.ram[m.symbols['SAME_SCUMM_C4_SLOT_FREEZE_COUNT']:m.symbols['SAME_SCUMM_C4_SLOT_FREEZE_COUNT']+5]),[1,0 if owner==1 else 1,1,0,1])

    def test_live_optional_verb_absence_is_not_resolution_failure(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_msu_live_room.pasm').read_text()
        code=source.split('ScummV5_LiveRoom_ObjectProgramResolve_Far:',1)[1].split('; Controller and direct verb',1)[0]
        for entry, binding_ok, previous_error in ((0,False,0),(0,False,32),
                                                   (18,True,0),(18,False,0),(18,False,32)):
            with self.subTest(entry=entry,binding_ok=binding_ok,previous_error=previous_error):
                m=self.machine(code);m.symbols['SCUMM_ERR_SCRIPT']=11
                m.put('SAME_SCUMM_ERROR',previous_error,1);calls=[]
                def service(name,p,a):
                    calls.append(name)
                    if name=='ScummV5_LiveRoom_VerbQuery_Far':
                        m.put('SAME_SCUMM_VERB_RESULT',entry)
                        return p & ~32,a # query returns A16
                    self.assertEqual(name,'ScummV5_Resident_ResolveProgramUnit_Far')
                    return (p|1 if binding_ok else p & ~1),0xD0
                m.service=service
                carry,_=m.consume()
                self.assertEqual(carry,bool(entry and binding_ok))
                self.assertEqual(len(calls),2 if entry else 1)
                self.assertEqual(m.get('SAME_SCUMM_ERROR',1),
                                 previous_error or (11 if entry and not binding_ok else 0))
