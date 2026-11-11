"""A8 child identity must not carry an unrelated hidden B byte into X16."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class LifecycleChildWidthTests(unittest.TestCase):
    def machine(self, high):
        m=StripMachine()
        m.symbols['SCUMM_V5_MAX_SCRIPT_SLOTS']=25
        source=(ROOT/'runtime/snes/engines/scumm_v5_msu_lifecycle_far.pasm').read_text()
        source=source.split('ScummV5_M23A_RunPendingLifecycleChild_FarEntry:',1)[1]
        source=source.split('ScummV5_M23A_RunPendingLifecycleChild_FarEntry__identity_valid:',1)[0]
        m.code=['rep #$30',f'lda #${high<<8:04X}'];m.labels={}
        for raw in source.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        m.labels['ScummV5_M23A_RunPendingLifecycleChild_FarEntry__identity_valid']=len(m.code)
        m.code+=['sec','rtl']
        for name in ('stale','no_child'):
            m.labels['ScummV5_M23A_RunPendingLifecycleChild_FarEntry__'+name]=len(m.code)
            m.code+=['clc','rtl']
        return m

    def test_exact_child_identity_with_all_hidden_accumulator_bytes(self):
        m=self.machine(0)
        for high in range(256):
            with self.subTest(high=high):
                m.code[1]=f'lda #${high<<8:04X}' 
                m.put('SAME_SCUMM_MSU_PENDING_CHILD_SLOT',2,1)
                m.put('SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM',0xF7,1)
                m.put(m.symbols['SAME_SCUMM_C4_SLOT_PROGRAM']+1,0xF7,1)
                valid,_=m.consume();self.assertTrue(valid)
                self.assertEqual(m.get('SAME_SCUMM_C4_SCAN_SLOT',1),1)

    def test_stale_selector_and_invalid_slot_still_reject(self):
        for slot,actual in ((2,0xF6),(26,0xF7),(255,0xF7)):
            m=self.machine(0xA5)
            m.put('SAME_SCUMM_MSU_PENDING_CHILD_SLOT',slot,1)
            m.put('SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM',0xF7,1)
            m.put(m.symbols['SAME_SCUMM_C4_SLOT_PROGRAM']+1,actual,1)
            valid,_=m.consume();self.assertFalse(valid)
