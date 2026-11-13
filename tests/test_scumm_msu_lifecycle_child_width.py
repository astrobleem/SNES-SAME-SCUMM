"""Execute the production lifecycle ticket walker, including A/B widths.

Service stubs exercise ownership only; the streamed fixture supplies native proof.
"""
import unittest
import test_scumm_cutscene_callback_native as native_blocks
from test_scumm_camera_native_copy import ROOT


class LifecycleChildWidthTests(unittest.TestCase):
    machine = native_blocks.CutsceneCallbackNative.machine
    def walker(self, high=0):
        source=(ROOT/'runtime/snes/engines/scumm_v5_msu_lifecycle_far.pasm').read_text()
        body=source.split('ScummV5_M23A_SelectLifecycleChild_Far:',1)[1]
        code=(f'rep #$30\nlda #${high<<8:04X}\njsl Walk\nphp\nrep #$20\n'
              'txa\nsta.l SAME_SCUMM_C4_PARENT_PROGRAM\n'
              'tya\nsta.l SAME_SCUMM_C4_ARGS\nplp\nrtl\nWalk:\n'+body)
        m=self.machine(code);m.symbols['SCUMM_VM_WAIT_RESOURCE']=5
        return m

    def edge(self,m,parent,child,selector=0xF7,status=5):
        m.put(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_SLOT']+parent,child+1,1)
        m.put(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM']+parent,selector,1)
        m.put(m.symbols['SAME_SCUMM_C4_SLOT_PROGRAM']+child,selector,1)
        m.put(m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+child,status,1)

    def test_exact_child_identity_with_all_hidden_accumulator_bytes(self):
        m=self.walker()
        for high in range(256):
            with self.subTest(high=high):
                m.code[1]=f'lda #${high<<8:04X}'
                self.edge(m,0,1)
                failed,_=m.consume();self.assertFalse(failed)
                self.assertEqual(m.get('SAME_SCUMM_C4_PARENT_PROGRAM'),1)
                self.assertEqual(m.get('SAME_SCUMM_C4_ARGS'),0)

    def test_descends_then_unwinds_only_completed_edge(self):
        m=self.walker();self.edge(m,0,5);self.edge(m,5,7)
        failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(m.get('SAME_SCUMM_C4_PARENT_PROGRAM'),7)
        self.assertEqual(m.get('SAME_SCUMM_C4_ARGS'),5)
        # Source yield stops descent so its immediate parent can resume.
        m.put(m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+7,2,1)
        failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(m.get('SAME_SCUMM_C4_PARENT_PROGRAM'),7)
        self.assertEqual(m.get('SAME_SCUMM_C4_ARGS'),5)

    def test_stale_selector_invalid_slot_and_cycles_reject_boundedly(self):
        for case in ('stale','invalid','cycle'):
            with self.subTest(case=case):
                m=self.walker(0xA5);self.edge(m,0,1)
                if case=='stale':m.put(m.symbols['SAME_SCUMM_C4_SLOT_PROGRAM']+1,0xF6,1)
                elif case=='invalid':m.put('SAME_SCUMM_MSU_PENDING_CHILD_SLOT',26,1)
                else:self.edge(m,1,0)
                failed,_=m.consume();self.assertTrue(failed)

    def test_runner_services_leaf_then_parent_with_balanced_stack(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_msu_lifecycle_far.pasm').read_text()
        m=self.machine(source)
        m.symbols.update(SCUMM_VM_WAIT_RESOURCE=5,SCUMM_VM_RUNNING=1,
                         SCUMM_VM_YIELDED=2,SCUMM_ERR_RESOURCE=32)
        self.edge(m,0,5);self.edge(m,5,7)
        m.put('SAME_SCUMM_C4_SLOT_STATUS',5,1)
        called=[]
        def service(name,p,a):
            if name=='ScummV5_M23A_RunSelected_FarThunk':
                slot=m.get('SAME_SCUMM_C4_CURRENT_SLOT',1);called.append(slot)
                m.put('SAME_SCUMM_STATUS',4,1)
                m.put(m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+slot,4,1)
            return p & ~1,a
        m.service=service
        failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(called,[7])
        self.assertEqual(m.get('SAME_SCUMM_MSU_PENDING_CHILD_SLOT',1),6)
        self.assertEqual(m.get(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_SLOT']+5,1),0)
        self.assertEqual(m.get('SAME_SCUMM_C4_CURRENT_SLOT',1),0)
        failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(called,[7,5])
        self.assertEqual(m.get('SAME_SCUMM_MSU_PENDING_CHILD_SLOT',1),0)
        self.assertEqual(m.get('SAME_SCUMM_RETURN_MODE',1),0)
