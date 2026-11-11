"""Submitting an unchanged selection must not queue another caption ahead of talk."""
from pathlib import Path
import unittest
from test_scumm_controller_hud_text import HudMachine

ROOT=Path(__file__).resolve().parents[1]

class SubmissionDamageTests(unittest.TestCase):
    def test_primary_and_secondary_keep_pending_hud_work_without_inventing_it(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        for label in ('select_verb_a_pressed','select_secondary_submit'):
            block=source.split('ScummV5_Controller_Frame__'+label+':',1)[1].split('jmp ScummV5_Controller_Frame__hud',1)[0]
            for dirty in (0,1):
                with self.subTest(label=label,dirty=dirty):
                    m=HudMachine(6,4);m.put('SAME_SCUMM_CONTROLLER_HUD_DIRTY',dirty,1)
                    m.put('SAME_SCUMM_CONTROLLER_SUBMISSIONS',23,1)
                    m.code=[('php','')];m.labels={}
                    for line in block.splitlines():
                        line=line.split(';')[0].strip()
                        if not line or line.startswith('.'):continue
                        op,_,arg=line.partition(' ');m.code.append((op,arg))
                    m.code += [('plp',''),('rtl','')];m.run()
                    self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_HUD_DIRTY',1),dirty)
                    self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_MODE',1),2)
                    self.assertEqual(m.get('SAME_SCUMM_SENTENCE_API_PENDING',1),1)
                    self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_SUBMISSIONS',1),24)
                    self.assertEqual(m.get('SAME_SCUMM_SENTENCE_API_VERB',1),7)
                    self.assertEqual(m.get('SAME_SCUMM_SENTENCE_API_OBJECT1'),3)
                    self.assertEqual(m.get('SAME_VIDEO_TEXT_CONTROLLER_VALID',1),0)

if __name__=='__main__':unittest.main()
