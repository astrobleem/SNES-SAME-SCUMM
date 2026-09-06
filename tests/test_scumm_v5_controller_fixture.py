from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
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

    def test_video_overlay_non_overlay_packets_reach_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "generated"
            manifest = Path(tmp) / "manifest.json"
            subprocess.run(
                [
                    "python3", str(ROOT / "tools/generate_snes_video_overlay.py"),
                    "--overlay", "bg2_index4", "--carrier", "sa1_bwram",
                    "--backend", "mode3_surface", "--output-dir", str(output),
                    "--manifest", str(manifest),
                ], check=True, cwd=ROOT, capture_output=True, text=True,
            )
            service = (output / "video_overlay_service.inc.pasm").read_text()
            self.assertIn("bcc Same_Video_Handle__overlay_not_handled", service)
            self.assertIn("Same_Video_Handle__overlay_not_handled:", service)
            self.assertNotIn("sta.l SAME_OVERLAY_STATE", service)
            self.assertNotIn("sta.l SAME_OVERLAY_ERROR_COUNT", service)
            self.assertNotIn("SAME_OVERLAY_STATE", service.split(
                "Same_Video_Handle__overlay_not_handled:", 1)[1])

    def test_native_visual_readiness_requires_displayed_planes(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        self.assertIn("accepted_present > 0", validator)
        self.assertIn("event_count == 0", validator)
        self.assertIn('session.read_memory("snesVideoRam", 0, 0xE000)', validator)
        self.assertIn('session.read_memory("snesCgRam", 0, 0x200)', validator)


if __name__ == "__main__":
    unittest.main()
