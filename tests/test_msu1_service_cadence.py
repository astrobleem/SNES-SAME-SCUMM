"""NMI-epoch admission of the real provider leaf (host instruction evidence)."""
import re
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class ServiceCadenceTests(unittest.TestCase):
    def machine(self, state=4):
        m = StripMachine()
        source = (ROOT / 'runtime/snes/services/storage_msu1.pasm').read_text()
        for name, expr in re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+)', source, re.M):
            try: m.symbols[name] = m.value(expr)
            except (NameError, SyntaxError): pass
        body = source.split('Same_Msu1_Process:', 1)[1].split('Same_Msu1_VerifyPrefixStep:', 1)[0]
        m.code, m.labels, m.calls, m.service_writes = [], {}, [], []
        for raw in body.splitlines():
            line = raw.split(';')[0].strip()
            if not line or line.startswith('.'): continue
            if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
            else: m.code.append(line)
        def service(name, p, a):
            self.assertIn(name, ('Same_Msu1_ReadStep', 'Same_Msu1_VerifyPrefixStep',
                                 'Same_Msu1_VerifyTail'))
            m.calls.append((name, m.get('SAME_FRAME_COUNTER')))
            return p, a
        m.service = service
        m.put('SAME_MSU1_STATUS', state, 1)
        m.put('SAME_MSU1_LAST_SERVICE_FRAME', 65535)
        return m

    def test_repeated_phase_offers_never_start_two_quanta_in_one_epoch(self):
        for state, expected in ((1, 'Same_Msu1_VerifyPrefixStep'),
                                (2, 'Same_Msu1_VerifyTail'), (4, 'Same_Msu1_ReadStep')):
            m = self.machine(state)
            for frame in (0, 0, 0, 1, 1, 4, 4, 65535, 65535, 0, 0):
                m.put('SAME_FRAME_COUNTER', frame)
                m.consume()
            self.assertEqual(m.calls, [(expected, f) for f in (0, 1, 4, 65535, 0)])

    def test_idle_terminal_and_error_states_do_not_spend_read_budget(self):
        for state in (0, 3, 5, 255):
            m = self.machine(state)
            m.put('SAME_FRAME_COUNTER', 7)
            m.consume()
            self.assertEqual(m.calls, [])
            self.assertEqual(m.get('SAME_MSU1_LAST_SERVICE_FRAME'), 65535)
            m.put('SAME_MSU1_STATUS', 4, 1)
            m.consume()
            self.assertEqual(m.calls, [('Same_Msu1_ReadStep', 7)])

    def test_slow_engine_can_service_a_request_again_without_another_tick(self):
        m = self.machine()
        # Three opportunities in one logical turn, separated by real NMIs.
        # No engine tick, data cursor change, or new request is manufactured.
        for frame in (40, 44, 46):
            m.put('SAME_FRAME_COUNTER', frame)
            m.consume()
        self.assertEqual(m.calls, [('Same_Msu1_ReadStep', f) for f in (40, 44, 46)])

    def test_nmi_during_quantum_does_not_erase_the_next_epoch(self):
        m = self.machine()
        def service(name, p, a):
            m.calls.append((name, m.get('SAME_FRAME_COUNTER')))
            m.put('SAME_FRAME_COUNTER', m.get('SAME_FRAME_COUNTER') + 1)
            return p, a
        m.service = service
        m.consume()
        self.assertEqual(m.get('SAME_MSU1_LAST_SERVICE_FRAME'), 0)
        m.consume()
        self.assertEqual(m.calls, [('Same_Msu1_ReadStep', 0), ('Same_Msu1_ReadStep', 1)])

    def test_kernel_has_bounded_offers_with_no_nmi_provider_call(self):
        source = (ROOT / 'runtime/snes/kernel/frame.pasm').read_text()
        self.assertEqual(source.count('jsr Same_Storage_Process'), 3)
        main = (ROOT / 'runtime/snes/main.pasm').read_text()
        nmi = main.split('Same_Nmi:', 1)[-1].split('    rti', 1)[0]
        self.assertNotIn('jsr Same_Storage_Process', nmi)
