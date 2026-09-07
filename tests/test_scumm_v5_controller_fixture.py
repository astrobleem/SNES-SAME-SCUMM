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

    def test_actor_compositor_recomputes_each_row_from_frame_base(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        row = source.split("ScummV5_Controller_RenderActor__row:", 1)[1].split(
            "ScummV5_Controller_RenderActor__pixel:", 1)[0]
        pixel = source.split("ScummV5_Controller_RenderActor__pixel:", 1)[1].split(
            "ScummV5_Controller_RenderActor__transparent:", 1)[0]
        self.assertIn("adc.l SAME_SCUMM_CONTROLLER_RENDER_SRC", row)
        self.assertIn("sta.l SAME_SCUMM_CONTROLLER_RENDER_ROWSRC", row)
        self.assertIn("adc.l SAME_SCUMM_CONTROLLER_RENDER_ROWSRC", pixel)
        self.assertNotIn("sta.l SAME_SCUMM_CONTROLLER_RENDER_SRC", row)

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

    def test_dirty_present_publishes_full_surface_origin(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_PushDirtyPresent:", 1)[1].split(
            "Same_VideoSurface_PushDirtyPresent__generation_ok:", 1)[0]
        self.assertIn("sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0", block)
        self.assertIn("sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02", block)
        self.assertIn("lda #$0100", block)
        self.assertIn("lda #$00E0", block)

    def test_native_visual_readiness_requires_displayed_planes(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        self.assertIn("accepted_present > 0", validator)
        self.assertIn("event_count == 0", validator)
        self.assertIn("capture_native", validator)
        self.assertIn("ImageChops.difference", validator)
        self.assertIn("reference_path", validator)
        self.assertIn("visualfix26-run1/01-ready.png", validator)
        self.assertIn("landmark = (0, 40, 256, 184)", validator)
        self.assertIn("visible overlay is legitimately left", validator)

    def test_native_dialogue_capture_waits_for_printable_segment(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        self.assertIn('talk_scene["talk_segment_length"] >= 8', validator)
        self.assertIn('"04-dialogue-active.png"', validator)

    def test_controller_talk_completion_hides_visual_but_keeps_fixture_lifetime(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm").read_text()
        stop = source.split("ScummV5_Talk_Stop_Far:", 1)[1].split(
            "ScummV5_Talk_Stop_Far__done:", 1)[0]
        self.assertIn("SAME_BUILD_SCUMM_CONTROLLER_FIXTURE", stop)
        self.assertIn("Same_VideoText_Hide_Far", stop)
        self.assertIn("SAME_SCUMM_TALK_ACTIVE", stop)

    def test_active_talk_retries_presentation_without_shortening_message_lifetime(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm").read_text()
        block = source.split("ScummV5_Talk_FrameBegin_Far:", 1)[1].split(
            "ScummV5_Talk_FrameEnd_Far:", 1)[0]
        self.assertIn("SAME_SCUMM_TALK_VISUAL_STATUS", block)
        self.assertIn("Same_VideoText_ShowSegment_Far", block)
        self.assertIn("SAME_SCUMM_TALK_DELAY", block)

    def test_talk_overlay_skips_encoded_controls_but_keeps_logical_raw_stream(self) -> None:
        source = (ROOT / "runtime/snes/services/video_overlay_surface.pasm").read_text()
        block = source.split("Same_VideoOverlay_RasterSegmentFast15:", 1)[1].split(
            "; Input A=u8 encoded glyph", 1)[0]
        self.assertGreaterEqual(block.count("SAME_SCUMM_TALK_RAW"), 4)
        self.assertIn("__validate_control", block)
        self.assertIn("__glyph_control", block)

    def test_cursor_redraw_does_not_restart_full_surface_generation(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        cursor = source.split("ScummV5_Controller_RenderCursor__changed:", 1)[1]
        self.assertIn("Same_VideoSurface_CanWrite_Far", cursor)
        self.assertIn("SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID", cursor)
        self.assertNotIn("Same_VideoSurface_PushDirtyPresent_Far", cursor)

    def test_cursor_is_composed_before_the_single_actor_present(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        actor = source.split("ScummV5_Controller_RenderActor_Far:", 1)[1].split(
            "ScummV5_Controller_RenderActor__done:", 1)[0]
        self.assertIn("ScummV5_Controller_DrawCursor_Far", actor)
        self.assertIn("Same_VideoSurface_PushDirtyPresent_Far", actor)
        cursor = source.split("ScummV5_Controller_DrawCursor_Far:", 1)[1].split(
            "ScummV5_Controller_RenderCursor_Far:", 1)[0]
        self.assertIn("rtl", cursor)


if __name__ == "__main__":
    unittest.main()
