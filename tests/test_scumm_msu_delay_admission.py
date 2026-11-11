"""Sleeping C4 slots must not fetch code merely to decrement their timers."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class DelayAdmissionTests(unittest.TestCase):
    def machine(self):
        m = StripMachine()
        source = (ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
        source = source.split('ScummV5_MsuProgram_ServiceDelay_Far:', 1)[1]
        source = source.split('ScummV5_MsuProgram_Reset_Far:', 1)[0]
        m.code = []; m.labels = {}; m.symbols['SCUMM_VM_DELAYED'] = 3
        for raw in source.splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'): continue
            if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
            else: m.code.append(line)
        return m

    def test_delay_ticks_without_provider_cache_pc_or_binding_writes(self):
        for slot in (0, 1, 24):
            for delay in (1, 2, 65535):
                with self.subTest(slot=slot, delay=delay):
                    m = self.machine()
                    m.put('SAME_SCUMM_C4_SCHED_SLOT', slot, 1)
                    m.put(m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+slot, 3, 1)
                    at = m.symbols['SAME_SCUMM_C4_SLOT_DELAY']+slot*2
                    m.put(at, delay)
                    serviced, writes = m.consume()
                    self.assertTrue(serviced); self.assertEqual(m.get(at), delay-1)
                    self.assertEqual(set(writes), {at, at+1, m.symbols['SAME_SCUMM_C4_SLOT_DIDEXEC']+slot})
                    self.assertEqual(m.get(m.symbols['SAME_SCUMM_C4_SLOT_DIDEXEC']+slot, 1), 1)

    def test_runnable_and_resource_wait_slots_keep_normal_checked_admission(self):
        for status, delay in ((1, 0), (2, 0), (3, 0), (5, 12)):
            with self.subTest(status=status, delay=delay):
                m = self.machine(); m.put('SAME_SCUMM_C4_SCHED_SLOT', 2, 1)
                m.put(m.symbols['SAME_SCUMM_C4_SLOT_STATUS']+2, status, 1)
                m.put(m.symbols['SAME_SCUMM_C4_SLOT_DELAY']+4, delay)
                serviced, writes = m.consume()
                self.assertFalse(serviced); self.assertEqual(writes, [])

    def test_gate_runs_after_freeze_check_before_code_page_admission(self):
        source = (ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        source = source.split('ScummV5_C4_Scheduler_Frame:', 1)[1]
        self.assertLess(source.index('lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x'),
                        source.index('jsl ScummV5_MsuProgram_ServiceDelay_Far'))
        self.assertLess(source.index('jsl ScummV5_MsuProgram_ServiceDelay_Far'),
                        source.index('jsr ScummV5_Engine_RunSelected'))


class ProviderAdmissionTests(unittest.TestCase):
    def test_authenticated_inflight_read_does_not_freeze_unrelated_activations(self):
        for status, runnable in ((0, False), (1, False), (2, False),
                                 (3, True), (4, True), (5, True), (255, False)):
            with self.subTest(status=status):
                m = StripMachine()
                source = (ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
                source = source.split('ScummV5_MsuProgram_FrameReady_Far__provider:', 1)[1]
                source = source.split('; M23A calls this', 1)[0]
                m.code = []; m.labels = {}; m.service_writes = []
                m.symbols.update(SAME_MSU1_STATE_READY=3, SAME_MSU1_STATE_READING=4,
                                 SAME_MSU1_STATE_READ_OK=5, SAME_MSU1_STATE_ERROR=255,
                                 SCUMM_VM_WAIT_RESOURCE=5, SCUMM_VM_ERROR=4,
                                 SCUMM_ERR_RESOURCE=0x0C)
                for raw in source.splitlines():
                    line = raw.split(';', 1)[0].strip()
                    if not line or line.startswith('.'): continue
                    if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
                    else: m.code.append(line)
                def service(name, p, a):
                    self.assertEqual(name, 'ScummV5_Stream_RecordErrorSite_FarEntry')
                    return p, a
                m.service = service
                m.put('SAME_MSU1_STATUS', status, 1)
                admitted, writes = m.consume()
                self.assertEqual(admitted, runnable)
                if runnable: self.assertEqual(writes, [])
                elif status == 255:
                    self.assertEqual(m.get('SAME_SCUMM_ERROR', 1), 0x0C)
                else: self.assertEqual(m.get('SAME_SCUMM_STATUS', 1), 5)

    def test_room_transaction_and_checked_page_guards_remain_in_force(self):
        source = (ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
        frame = source.split('ScummV5_MsuProgram_FrameReady_Far:', 1)[1].split('; Completion holds', 1)[0]
        self.assertIn('jsl ScummV5_MsuRoom_Service_Far\n    bcc ScummV5_MsuProgram_FrameReady_Far__room_result', frame)
        self.assertIn('cmp #SAME_MSU1_STATE_READING\n    bne ScummV5_MsuProgram_EnsureSelected_Far__read_idle\n    jmp ScummV5_MsuProgram_EnsureSelected_Far__pending', source)
