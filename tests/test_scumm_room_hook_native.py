"""Production hook instructions under the bounded host CPU helper.

Service stubs isolate ownership/return contracts; Nexen supplies native proof.
"""
import unittest
import test_scumm_cutscene_callback_native as native_blocks
from test_scumm_camera_native_copy import ROOT


class RoomHookNativeTests(unittest.TestCase):
    machine = native_blocks.CutsceneCallbackNative.machine

    def tick(self, kind=3, status=4):
        source=(ROOT/'runtime/snes/engines/scumm_v5_room_hooks.inc.pasm').read_text()
        code=source.split('ScummV5_RoomHook_Tick_Far:',1)[1].split('ScummV5_RoomHook_Bits:',1)[0]
        # All long tail jumps here stay inside the same test instruction list.
        code=code.replace('jml ', 'jmp ')
        m=self.machine(code)
        m.symbols.update(SCUMM_VM_RUNNING=1,SCUMM_VM_YIELDED=2,
                         SCUMM_VM_DELAYED=3,SCUMM_VM_WAIT_RESOURCE=5,SCUMM_ERR_SCRIPT=11)
        for name,value in [('M23A_PHASE',7),('ROOM_HOOK_KIND',kind),
                           ('ROOM_HOOK_SLOT',3),('ROOM_HOOK_SELECTOR',217),
                           ('C4_SLOT_STATUS',1),('C4_SLOT_PROGRAM',216),
                           ('STATUS',4),('PROGRAM_SELECT',217)]:
            m.put('SAME_SCUMM_'+name,value,1)
        m.put('SAME_SCUMM_PC',128);m.put('SAME_SCUMM_DELAY',77)
        m.put('SAME_SCUMM_C4_SLOT_PC',0);m.put('SAME_SCUMM_C4_SLOT_DELAY',0)
        m.put('SAME_SCUMM_ROOM_HOOK_EPOCH',12)
        m.put(m.symbols['SAME_SCUMM_C4_SLOT_PROGRAM']+3,217,1)
        m.put(m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+3,status,1)
        m.calls=[]
        def service(name,p,a):
            m.calls.append(name)
            if name=='ScummV5_M23A_SelectPendingChild_Far':return p&~1,0
            if name=='ScummV5_Camera_FarCall_SetError':
                m.put('SAME_SCUMM_ERROR',a,1)
            return p&~1,a
        m.service=service
        return m

    def test_normalizer_does_not_complete_unexecuted_or_io_waiting_entry(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_matrix_far.pasm').read_text()
        code=source.split('ScummV5_M23A_NormalizeEntryLifecycle_Far:',1)[1].split('; Temporary production-path',1)[0]
        for pc,status,complete in ((0,1,False),(0,5,False),(9,1,False),(10,1,True),(11,4,True)):
            with self.subTest(pc=pc,status=status):
                m=self.machine(code);m.put('SAME_SCUMM_M23A_PHASE',2,1)
                m.put('SAME_SCUMM_C4_SLOT_STATUS',status,1)
                m.put('SAME_SCUMM_C4_SLOT_PROGRAM',216,1);m.put('SAME_SCUMM_C4_SLOT_PC',pc)
                def service(name,p,a):
                    if 'GetProgramSize' in name:return (p & ~32)|1,11
                    return p&~1,a
                m.service=service;failed,_=m.consume();self.assertFalse(failed)
                self.assertEqual(m.get('SAME_SCUMM_M23A_PHASE',1),0 if complete else 2)

    def test_entry_yield_preserves_continuation_but_io_wait_stays_parked(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_room_hooks.inc.pasm').read_text()
        code=source.split('ScummV5_RoomHook_EntryBoundary_Far:',1)[1].split('ScummV5_RoomHook_Error_Far:',1)[0]
        for status in (1,2,3,5):
            for slot in (0,3):
                with self.subTest(status=status,slot=slot):
                    m=self.machine(code);m.symbols.update(SCUMM_VM_YIELDED=2,SCUMM_VM_DELAYED=3)
                    m.put('SAME_SCUMM_M23A_PHASE',2,1);m.put('SAME_SCUMM_C4_CURRENT_SLOT',slot,1)
                    m.put('SAME_SCUMM_STATUS',status,1);m.put('SAME_SCUMM_PC',73);m.put('SAME_SCUMM_DELAY',23)
                    failed,_=m.consume();self.assertFalse(failed)
                    yielded=slot==0 and status in (2,3)
                    self.assertEqual(m.get('SAME_SCUMM_M23A_PHASE',1),0 if yielded else 2)
                    self.assertEqual(m.get('SAME_SCUMM_C4_SLOT_PC'),73 if yielded else 0)
                    self.assertEqual(m.get('SAME_SCUMM_C4_SLOT_DELAY'),23 if yielded else 0)

    def test_ticket_cannot_overlap_reset_breadcrumbs(self):
        from unittest.mock import patch
        from tools import audit_scumm_residency_wram as ownership
        values=ownership.symbols()
        self.assertEqual(values['SAME_RESET_DIAG_END'],0x7ff4d3)
        self.assertGreaterEqual(values['SAME_SCUMM_ROOM_HOOK_BASE'],values['SAME_RESET_DIAG_END'])
        ownership.audit()
        values['SAME_SCUMM_ROOM_HOOK_BASE']=values['SAME_RESET_DIAG_BASE']
        values['SAME_SCUMM_ROOM_HOOK_END']=values['SAME_RESET_DIAG_BASE']+8
        with patch.object(ownership,'symbols',return_value=values):
            with self.assertRaisesRegex(ValueError,'ownership overlaps'):ownership.audit()

    def test_pre_entry_restores_slot_zero_before_direct_owner_save(self):
        m=self.tick();failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(m.get('SAME_SCUMM_M23A_PHASE',1),2)
        self.assertEqual(m.get('SAME_SCUMM_PROGRAM_SELECT',1),216)
        self.assertEqual(m.get('SAME_SCUMM_STATUS',1),1)
        self.assertEqual(m.get('SAME_SCUMM_PC'),0)
        self.assertEqual(m.get('SAME_SCUMM_DELAY'),0)
        self.assertEqual(m.get('SAME_SCUMM_ROOM_HOOK_KIND',1),0)

    def test_io_wait_is_not_source_yield_or_retirement(self):
        for status,parked in ((1,True),(5,True),(2,False),(3,False),(4,False)):
            with self.subTest(status=status):
                m=self.tick(status=status);failed,_=m.consume();self.assertFalse(failed)
                self.assertEqual(m.get('SAME_SCUMM_M23A_PHASE',1),7 if parked else 2)

    def test_stale_selector_invalid_slot_and_status_reject(self):
        for case in ('selector','slot','status'):
            with self.subTest(case=case):
                m=self.tick(status=0 if case=='status' else 4)
                if case=='selector':m.put('SAME_SCUMM_ROOM_HOOK_SELECTOR',215,1)
                if case=='slot':m.put('SAME_SCUMM_ROOM_HOOK_SLOT',25,1)
                failed,_=m.consume();self.assertTrue(failed)
                self.assertEqual(m.get('SAME_SCUMM_ERROR',1),11)

    def test_new_room_request_supersedes_old_callback_continuation(self):
        m=self.tick(status=1);service=m.service
        def redirect(name,p,a):
            if name=='ScummV5_C4_RunAllocatedNoParent_FarEntry':
                m.put('SAME_SCUMM_ROOM_HOOK_EPOCH',13)
                m.put('SAME_SCUMM_M23A_PHASE',4,1)
            return service(name,p,a)
        m.service=redirect
        failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(m.get('SAME_SCUMM_M23A_PHASE',1),4)
        self.assertEqual(m.get('SAME_SCUMM_ROOM_HOOK_KIND',1),3)


if __name__=='__main__':unittest.main()
