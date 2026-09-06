from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ScummV5ControllerFixtureTests(unittest.TestCase):
    def test_controller_uses_production_sentence_tuple_and_zero_object2(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        self.assertEqual(source.count("sta.l SAME_SCUMM_SENTENCE_API_PENDING"), 2)
        self.assertEqual(source.count("sta.l SAME_SCUMM_SENTENCE_API_OBJECT1+1"), 2)
        self.assertEqual(source.count("sta.l SAME_SCUMM_SENTENCE_API_OBJECT2+1"), 2)
        self.assertEqual(source.count("lda #$00\n    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2"), 2)
        self.assertIn("ScummV5_QueueSentence", (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text())

    def test_controller_scene_asserts_real_open_and_inspect_lifecycle(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        for stage in ("locker_hover", "object_selected", "verb_selected", "open_submitted",
                      "opened", "inspect_submitted", "inspection_complete"):
            self.assertIn(f'"stage": "{stage}"', validator)
        self.assertIn('state["object490_state"] == 1', validator)
        self.assertIn('current["error"] == 0', validator)

    def test_controller_scenario_materializes_generic_actor_defaults(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        root = source.split("SAME_SCUMM_SCENARIO_SOURCE_ACTOR_INIT", 1)[1]
        self.assertIn("ScummV5_PutActor_FarCall_DefaultActor", root)
        self.assertIn("SAME_SCUMM_C14_A_COSTUME+64", root)
        self.assertIn("SAME_SCUMM_C31_POSITIONS+4", root)


if __name__ == "__main__":
    unittest.main()
