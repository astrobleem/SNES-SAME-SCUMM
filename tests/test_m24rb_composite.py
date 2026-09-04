import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from tools.convert_fate_sound_to_tad_mml import load_sound, collect_notes, quantize_notes, virtualize_polyphony

ROOT=Path(__file__).resolve().parents[1]

class M24RBCompositeTests(unittest.TestCase):
    def test_sound82_role_priority_is_stable_and_bounded(self):
        archive=Path("/home/chad/fatedemo-box.zip")
        if not archive.exists(): self.skipTest("user-supplied Fate demo absent")
        sound=load_sound(archive,82)
        notes,decisions=virtualize_polyphony(82,quantize_notes(82,collect_notes(sound)))
        self.assertEqual(sound.sha256,"e665931c3440486624afde85035d4f1cd895a1ac097c9d915e115511b82dcb25")
        self.assertEqual(len({n.source_index for n in notes}),554)
        self.assertTrue(decisions)
        points=sorted({x for n in notes for x in (n.start,n.end)})
        self.assertLessEqual(max(sum(n.start<a and n.end>b for n in notes)
                                 for b,a in zip(points,points[1:])),8)

    def test_generated_composite_audit_binds_loop_and_schedule(self):
        path=ROOT/"build/m24rb-content/composite-audit.json"
        if not path.exists(): self.skipTest("M24R-B content has not been generated")
        audit=json.loads(path.read_text())
        self.assertEqual(audit["sources"]["82"],"e665931c3440486624afde85035d4f1cd895a1ac097c9d915e115511b82dcb25")
        self.assertEqual(audit["routes"]["sound82_loop"],[97920,1920])
        self.assertEqual(audit["room63_transition"]["admission_voices"],[7,6,5,4,3])
        self.assertFalse(audit["runtime_executes_source_tick"])

if __name__=="__main__": unittest.main()
