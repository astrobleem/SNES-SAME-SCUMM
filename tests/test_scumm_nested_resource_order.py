"""Execute production C4 resource-admission instructions; not native evidence."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class NestedResourceOrder(unittest.TestCase):
    def machine(self, slot):
        m=StripMachine()
        m.symbols.update(SCUMM_V5_MAX_SCRIPT_SLOTS=25, SCUMM_VM_STOPPED=4,
                         SCUMM_VM_ERROR=255, SCUMM_VM_WAIT_RESOURCE=5,
                         SCUMM_ERR_RESOURCE=12)
        s=(ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
        s=s.split('ScummV5_MsuProgram_NestedAdmission_Far:',1)[1].split('ScummV5_MsuProgram_Reset_Far:',1)[0]
        m.code=[];m.labels={};m.service_writes=[]
        for raw in s.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        m.put('SAME_SCUMM_C4_SCHED_SLOT',slot,1)
        return m

    def activation(self,m,slot,status,selector):
        m.put(m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+slot,status,1)
        m.put(m.symbols['SAME_SCUMM_C4_SLOT_PROGRAM']+slot,selector,1)

    def ticket(self,m,parent,child,selector):
        m.put(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_SLOT']+parent,child+1,1)
        m.put(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM']+parent,selector,1)

    def test_unrelated_slot_cannot_replace_not_yet_executed_object(self):
        for child_status,allowed in ((5,1),(2,4),(3,4),(4,4),(255,4)):
            for slot in range(25):
                m=self.machine(slot)
                self.activation(m,4,5,0xee);self.activation(m,1,child_status,0xef)
                self.ticket(m,4,1,0xef)
                deferred,writes=m.consume()
                self.assertEqual(deferred,slot!=allowed,(child_status,slot))
                self.assertEqual(writes,[])

    def test_nested_waits_choose_leaf_then_unwind(self):
        for slot in (1,4,8,11):
            m=self.machine(slot)
            for z in (1,4,8):self.activation(m,z,5,0xe0+z)
            self.ticket(m,4,1,0xe1);self.ticket(m,1,8,0xe8)
            self.assertEqual(m.consume()[0],slot!=8)

    def test_no_ticket_does_not_block_independent_io_waits(self):
        for slot in range(25):
            m=self.machine(slot);self.activation(m,4,5,0xe4)
            self.assertFalse(m.consume()[0])

    def test_replaced_child_returns_to_parent_for_existing_identity_cleanup(self):
        m=self.machine(4);self.activation(m,4,5,0xe4);self.activation(m,1,5,0xe2)
        self.ticket(m,4,1,0xe1);self.assertFalse(m.consume()[0])

    def test_stopped_parent_does_not_hold_stale_ticket(self):
        for status in (0,4,255):
            m=self.machine(11);self.activation(m,4,status,0xe4)
            self.ticket(m,4,1,0xe1);self.assertFalse(m.consume()[0])

    def test_frozen_parent_releases_satisfied_ticket_but_waiting_child_runs(self):
        for status, deferred in ((5,True),(2,False),(4,False)):
            m=self.machine(11);self.activation(m,4,5,0xe4);self.activation(m,1,status,0xe1)
            self.ticket(m,4,1,0xe1)
            m.put(m.symbols['SAME_SCUMM_C4_SLOT_FREEZE_COUNT']+4,1,1)
            self.assertEqual(m.consume()[0],deferred)
            self.assertEqual(m.get(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_SLOT']+4,1),2 if status==5 else 0)

    def test_new_activation_clears_own_and_all_old_incoming_tickets(self):
        for slot in (0,1,24):
            m=self.machine(11)
            source=(ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
            source=source.split('ScummV5_MsuProgram_NewActivation_Far:',1)[1].split('; Preserve synchronous StartScript',1)[0]
            m.code=[];m.labels={}
            for raw in (f'ldx #{slot}\n'+source).splitlines():
                line=raw.split(';')[0].strip()
                if not line or line.startswith('.'):continue
                if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                else:m.code.append(line)
            for z in range(25):self.ticket(m,z,slot if z%2 else 12,0xe4)
            before=bytes(m.ram)
            m.consume()
            for z in range(25):
                cleared=z==slot or z%2 or slot==12
                self.assertEqual(m.get(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_SLOT']+z,1),0 if cleared else 13)
                self.assertEqual(m.get(m.symbols['SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM']+z,1),0 if cleared else 0xe4)

    def test_cycle_and_invalid_child_fail_bounded(self):
        for child in (4,25):
            m=self.machine(11);self.activation(m,4,5,0xe4)
            self.ticket(m,4,child,0xe4)
            self.assertTrue(m.consume()[0]);self.assertEqual(m.get('SAME_SCUMM_ERROR',1),12)
