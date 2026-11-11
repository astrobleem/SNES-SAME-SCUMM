"""Execute the actual A-edge handoff; this is host instruction evidence."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class TalkAckTests(unittest.TestCase):
    def machine(self):
        m = StripMachine()
        source = (ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        code = source.split('ScummV5_Controller_AcknowledgeTalk_Far:', 1)[1]
        m.code = []; m.labels = {}; m.calls = []; m.service_writes = []
        for raw in code.splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'): continue
            if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
            else: m.code.append(line)
        def service(label, p, a):
            self.assertEqual(label, 'ScummV5_Talk_FrameEnd_Far')
            self.assertEqual(m.get('SAME_SCUMM_TALK_DELAY'), 0)
            self.assertEqual(m.get('SAME_INPUT_TALK_OWNED_VALID', 1), 2)
            m.calls.append(label)
            return p, a
        m.service = service
        for name, value, size in [('SAME_INPUT_TALK_OWNED_VALID', 1, 1),
                                  ('SAME_INPUT_EDGE_SEQUENCE', 17, 2),
                                  ('SAME_INPUT_TALK_OWNED_SEQUENCE', 17, 2),
                                  ('SAME_SCUMM_TALK_ACTIVE', 1, 1),
                                  ('SAME_SCUMM_TALK_DELAY', 200, 2),
                                  ('SAME_INPUT_PRESSED', 128, 2)]:
            m.put(name, value, size)
        return m

    def test_one_edge_advances_once_and_retains_scene_exclusion(self):
        m = self.machine()
        acked, writes = m.consume()
        self.assertTrue(acked); self.assertEqual(len(m.calls), 1)
        allowed = {m.symbols['SAME_SCUMM_TALK_DELAY']+i for i in (0, 1)}
        allowed.add(m.symbols['SAME_INPUT_TALK_OWNED_VALID'])
        self.assertEqual(set(writes), allowed)
        m.put('SAME_SCUMM_TALK_DELAY', 90)  # next segment's own delay
        acked, writes = m.consume()
        self.assertFalse(acked); self.assertEqual(writes, [])
        self.assertEqual(m.get('SAME_SCUMM_TALK_DELAY'), 90)
        self.assertEqual(len(m.calls), 1)

    def test_only_matching_fresh_active_a_edges_acknowledge(self):
        for name, value, size in [('SAME_INPUT_TALK_OWNED_VALID', 0, 1),
                                  ('SAME_INPUT_TALK_OWNED_VALID', 2, 1),
                                  ('SAME_INPUT_EDGE_SEQUENCE', 18, 2),
                                  ('SAME_SCUMM_TALK_ACTIVE', 0, 1),
                                  ('SAME_INPUT_PRESSED', 0, 2),
                                  ('SAME_INPUT_PRESSED', 256, 2)]:
            with self.subTest(name=name, value=value):
                m = self.machine(); m.put(name, value, size)
                acked, writes = m.consume()
                self.assertFalse(acked); self.assertEqual(writes, [])
                self.assertEqual(m.calls, [])
