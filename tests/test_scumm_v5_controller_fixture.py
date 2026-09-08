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
        self.assertEqual(source.count("sta.l SAME_SCUMM_SENTENCE_API_OBJECT1+1"), 0)
        self.assertEqual(source.count("sta.l SAME_SCUMM_SENTENCE_API_OBJECT2+1"), 2)
        self.assertEqual(source.count("lda #$00\n    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2"), 2)
        self.assertIn("ScummV5_QueueSentence", (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text())

    def test_controller_selection_is_source_driven_not_locker_driven(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        selection = source.split("ScummV5_Controller_Frame__mode_select_fallback:", 1)[1].split(
            "ScummV5_Controller_Frame__select_verb:", 1
        )[0]
        self.assertIn("ScummV5_Generic_Object_HitTest_Far", selection)
        self.assertIn("ScummV5_Generic_Verb_First_Far", selection)
        self.assertNotIn("#$01EA", selection)
        self.assertNotIn("#$00BE", selection)
        self.assertNotIn("#$00F1", selection)
        self.assertNotIn("#$004C", selection)

    def test_controller_cycles_authored_verbs_and_uses_selected_object(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        cycle = source.split("ScummV5_Controller_Frame__select_verb:", 1)[1].split(
            "ScummV5_Controller_Frame__check_opened:", 1
        )[0]
        self.assertIn("ScummV5_Generic_Verb_Next_Far", cycle)
        self.assertIn("SAME_SCUMM_CONTROLLER_OBJECT", cycle)
        submit = source.split("ScummV5_Controller_Frame__select_verb_a_pressed:", 1)[1].split(
            "ScummV5_Controller_Frame__check_opened:", 1
        )[0]
        self.assertIn("SAME_SCUMM_SENTENCE_API_OBJECT1", submit)
        self.assertNotIn("#$EA", submit)

    def test_generated_room_metadata_exports_generic_hit_and_verb_services(self) -> None:
        source = (ROOT / "tools/generate_snes_cooked_rooms.py").read_text()
        self.assertIn('"ScummV5_Generic_Object_HitTest_Far:"', source)
        self.assertIn('"ScummV5_Generic_Verb_First_Far:"', source)
        self.assertIn('"ScummV5_Generic_Verb_Next_Far:"', source)
        self.assertIn("SAME_SCUMM_SETSTATE_LOCAL_RECORDS", source)

    def test_generated_hit_test_contract_is_room_pixel_half_open_and_frontmost(self) -> None:
        source = (ROOT / "tools/generate_snes_cooked_rooms.py").read_text()
        block = source.split('"ScummV5_Generic_Object_HitTest_Far:"', 1)[1].split(
            '"ScummV5_Generic_Verb_First_Far:"', 1
        )[0]
        self.assertIn("SAME_SCUMM_SETSTATE_LOCAL_COUNT", block)
        self.assertIn("SAME_SCUMM_SETSTATE_LOCAL_RECORDS+2", block)
        self.assertIn("SAME_SCUMM_SETSTATE_LOCAL_RECORDS+6", block)
        self.assertIn("sta.l SAME_SCUMM_INTERACTION_INDEX", block)
        self.assertIn('"    iny"', block)
        self.assertIn("SAME_SCUMM_INTERACTION_OBJECT", block)
        self.assertNotIn("and #$0002", block)
        # Canonical v5 hit testing is based on source bounds and visibility;
        # inventory ownership is not a generic hit-test exclusion.
        self.assertNotIn("SAME_SCUMM_OBJECT_OWNERS", block)
        self.assertNotIn("ldy.l", block.lower())

    def test_controller_scene_asserts_real_open_and_inspect_lifecycle(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        for stage in ("locker_hover", "object_selected", "verb_selected", "open_submitted",
                      "opened", "inspect_submitted", "inspection_complete"):
            self.assertIn(f'"stage": "{stage}"', validator)
        self.assertIn('state["object490_state"] == 1', validator)
        self.assertIn('current["error"] == 0', validator)

    def test_walking_validator_fences_semantic_snapshot_before_success_witness(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        self.assertIn("wait_for_semantic_moving_snapshot", validator)
        self.assertIn('session.add_write_hook(\n            0x7E5E4D', validator)
        semantic = validator.index("semantic_snapshot = wait_for_semantic_moving_snapshot")
        witness = validator.index("walking_witness = wait_for_moving_publication")
        commit = validator.index("walking_commit = wait_for_committed_generation")
        self.assertLess(semantic, witness)
        self.assertLess(witness, commit)
        self.assertIn('"stage": "semantic_moving_snapshot"', validator)

    def test_target_build_can_compile_witness_out_without_layout_switch(self) -> None:
        selection = (ROOT / "tools/generate_snes_engine_selection.py").read_text()
        build = (ROOT / "tools/build_snes.sh").read_text()
        self.assertIn("--scumm-controller-witness", selection)
        self.assertIn("SAME_SCUMM_CONTROLLER_WITNESS", selection)
        self.assertIn("SAME_SCUMM_CONTROLLER_WITNESS:-1", build)
        memory = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
        self.assertIn("SAME_SCUMM_CONTROLLER_STATE_END           = $7E5FEC", memory)

    def test_validator_reports_build_identity_sidecar(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        self.assertIn("build_identity_for", validator)
        self.assertIn('"build_identity": build_identity_for(args.rom)', validator)

    def test_controller_scenario_materializes_generic_actor_defaults(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        root = source.split("SAME_SCUMM_SCENARIO_SOURCE_ACTOR_INIT", 1)[1]
        self.assertIn("ScummV5_PutActor_FarCall_DefaultActor", root)
        self.assertIn("SAME_SCUMM_C14_A_COSTUME+64", root)
        self.assertIn("SAME_SCUMM_C31_POSITIONS+4", root)

    def test_actor_compositor_recomputes_each_row_from_frame_base(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        actor = source.split("ScummV5_Controller_RenderActor_Far:", 1)[1].split(
            "ScummV5_Controller_RenderActor__done:", 1)[0]
        # The accepted compositor now uses the generic bounded indexed-rect
        # service; row addressing belongs to that service rather than to a
        # SCUMM-side per-pixel loop.
        self.assertIn("Same_VideoSurface_BlitIndexedRect_Far", actor)
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_SRC", actor)
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_BASE", actor)

    def test_actor_pose_selection_reads_movement_byte_not_following_word(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        selection = source.split("; Frame zero is the source-defined standing pose.", 1)[1].split(
            "ScummV5_Controller_RenderActor__frame_base:", 1)[0]
        self.assertIn("SAME_SCUMM_CONTROLLER_DESIRED_SELECT", selection)
        self.assertIn("ScummV5_Controller_PublishActorVisual_Far", source)

    def test_actor_blit_preserves_packed_destination_abi(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        call = source.split("Same_VideoSurface_BlitIndexedRect_Far", 1)[0].split(
            "ScummV5_Controller_RenderActor__frame_base:", 1)[1]
        self.assertIn("lda.l SAME_SCUMM_CONTROLLER_RENDER_BASE", call)
        self.assertIn("lda.l SAME_SCUMM_CONTROLLER_RENDER_SRC\n    tay\n    pla", call)
        self.assertNotIn("pla\n    lda.l SAME_SCUMM_CONTROLLER_RENDER_SRC", call)

    def test_surface_blit_preserves_destination_across_diagnostics(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_BlitIndexedRect_Far:", 1)[1].split(
            "Same_VideoSurface_BlitIndexedRect__writable:", 1)[0]
        self.assertIn("; Preserve the public pixel-space destination", block)
        self.assertIn("pha\n    lda.l SAME_VIDEO_DIAG_BLIT_ENTRIES", block)
        self.assertIn("pla\n    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1", block)
        failure = source.split("Same_VideoSurface_BlitIndexedRect__fail:", 1)[1].split(
            "Same_VideoSurface_BlitIndexedRect_Far__", 1)[0]
        self.assertIn("pla", failure)

    def test_actor_cache_invalidates_for_pose_without_position_change(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        render = source.split("ScummV5_Controller_RenderActor__room_ok:", 1)[1].split(
            "ScummV5_Controller_RenderActor__pose_same:", 1)[0]
        self.assertIn("SAME_SCUMM_CONTROLLER_DESIRED_SELECT", render)
        self.assertIn("SAME_SCUMM_CONTROLLER_DESIRED_FACING", source)
        self.assertIn("SAME_SCUMM_CONTROLLER_DESIRED_COSTUME", source)
        self.assertIn("SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE", source)
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_ACTOR_SELECT", render)
        self.assertIn("jmp ScummV5_Controller_RenderActor__changed", render)
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_VALID", source)

    def test_failed_present_does_not_commit_new_actor_cache_identity(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        retry = source.split("ScummV5_Controller_RenderActor__present_retry:", 1)[1].split(
            "ScummV5_Controller_RenderActor__done:", 1)[0]
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_RETRY", retry)
        self.assertIn("SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $02", retry)
        self.assertIn("attempted composition is not accepted state", retry)

    def test_semantic_actor_snapshot_is_separate_from_accepted_render_cache(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        self.assertIn("ScummV5_Controller_PublishActorVisual_Far", source)
        self.assertIn("SAME_SCUMM_CONTROLLER_DESIRED_SELECT", source)
        success = source.split("ScummV5_Controller_RenderActor__present_result:", 1)[1].split(
            "ScummV5_Controller_RenderActor__present_retry:", 1)[0]
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_ACTOR_SELECT", success)
        retry = source.split("ScummV5_Controller_RenderActor__present_retry:", 1)[1].split(
            "ScummV5_Controller_RenderActor__done:", 1)[0]
        self.assertNotIn("SAME_SCUMM_CONTROLLER_RENDER_ACTOR_SELECT", retry)

    def test_compositor_does_not_mutate_published_pose_snapshot(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        compose = source.split("ScummV5_Controller_RenderActor__compose_actor:", 1)[1].split(
            "ScummV5_Controller_RenderActor__frame_base:", 1)[0]
        self.assertNotIn("sta.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT", compose)
        self.assertIn("DESIRED_SELECT is the semantic snapshot", compose)

    def test_publication_witness_is_success_only_and_serialized_last(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        success = source.split("ScummV5_Controller_RenderActor__present_result:", 1)[1].split(
            "ScummV5_Controller_RenderActor__present_retry:", 1)[0]
        self.assertIn("SAME_SCUMM_CONTROLLER_WITNESS_PRESENT", success)
        self.assertIn("SAME_SCUMM_CONTROLLER_WITNESS_VALID", success)
        self.assertIn("Publish the serial last", success)
        retry = source.split("ScummV5_Controller_RenderActor__present_retry:", 1)[1].split(
            "ScummV5_Controller_RenderActor__done:", 1)[0]
        self.assertNotIn("WITNESS_SERIAL", retry)

    def test_publication_witness_storage_is_inside_fixture_gap(self) -> None:
        source = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
        self.assertIn("SAME_SCUMM_CONTROLLER_WITNESS_SERIAL    = $7E5E52", source)
        self.assertIn("SAME_SCUMM_CONTROLLER_WITNESS_VALID     = $7E5E6A", source)
        self.assertIn("SAME_SCUMM_CONTROLLER_STATE_END           = $7E5FEC", source)

    def test_room_install_resets_visual_cache_but_nonmatching_render_is_inert(self) -> None:
        visual = (ROOT / "runtime/snes/engines/scumm_v5_visual.pasm").read_text()
        controller = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        install = visual.split("ScummV5_RoomVisual_Installed_Far:", 1)[1].split(
            "    plp", 1)[0]
        self.assertIn("ScummV5_Controller_ResetVisualCache_Far", install)
        mismatch = controller.split("ScummV5_Controller_RenderActor_Far:", 1)[1].split(
            "ScummV5_Controller_RenderActor__room_ok:", 1)[0]
        self.assertNotIn("SAME_SCUMM_CONTROLLER_RENDER_VALID", mismatch)
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_ROOM", controller)

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

    def test_actor_damage_compose_prepares_one_atomic_present(self) -> None:
        service = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        actor = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        damage = actor.split("ScummV5_Controller_RenderActor_Far:", 1)[1].split(
            "ScummV5_Controller_RenderActor__full_compose_retry:", 1)[0]
        self.assertIn("Same_VideoSurface_RestoreRect_Far", damage)
        self.assertIn("Same_VideoSurface_BlitIndexedRect_Far", damage)
        self.assertNotIn("Same_VideoSurface_ComposeRoom_Far", damage)
        self.assertIn("Same_VideoSurface_PushDamagePresent_Far", damage)
        self.assertIn("Same_VideoSurface_PushDirtyPresent_Far", actor)

    def test_surface_present_wrappers_preserve_result_carry_across_caller_flags(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        for name in ("Same_VideoSurface_PushDamagePresent_Far",
                     "Same_VideoSurface_PushDirtyPresent_Far"):
            block = source.split(name + ":", 1)[1].split("\n;", 1)[0]
            self.assertIn("bcs " + name + "__fail", block)
            self.assertIn("plp\n    clc\n    rtl", block)
            self.assertIn("plp\n    sec\n    rtl", block)

    def test_restore_rect_only_takes_busy_path_when_can_write_reports_locked(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_RestoreRect_Far:", 1)[1].split(
            "Same_VideoSurface_RestoreRect__busy:", 1)[0]
        self.assertIn("jsl Same_VideoSurface_CanWrite_Far\n    bcc", block)
        self.assertNotIn("jsl Same_VideoSurface_CanWrite_Far\n    brl", block)

    def test_can_write_service_preserves_clear_or_set_carry_result(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_CanWrite_Far:", 1)[1].split(
            "; Target-neutral indexed-surface write contract", 1)[0]
        self.assertIn("plp\n    clc\n    rtl", block)
        self.assertIn("Same_VideoSurface_CanWrite__no:\n    plp\n    sec\n    rtl", block)

    def test_restore_rect_decodes_xy_from_a_and_size_from_x(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_RestoreRect_Far:", 1)[1].split(
            "Same_VideoSurface_RestoreRect__width_ok:", 1)[0]
        self.assertNotIn("txa\n    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH\n    and #$00FF\n    sta.l SAME_VIDEO_SURFACE_DAMAGE_X", block)
        self.assertIn("SAME_VIDEO_SURFACE_DAMAGE_X1\n    and #$00FF\n    sta.l SAME_VIDEO_SURFACE_DAMAGE_X", block)
        self.assertIn("SAME_VIDEO_SURFACE_DAMAGE_X1\n    xba\n    and #$00FF\n    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y", block)
        self.assertIn("SAME_VIDEO_SURFACE_DAMAGE_Y1\n    and #$00FF\n    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH", block)

    def test_visual_phase_does_not_starve_input_with_idle_actor_retry(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_visual.pasm").read_text()
        phase = source.split("ScummV5_Visual_Frame_Far:", 1)[1].split(
            "ScummV5_Visual_Frame__skip_actor:", 1)[0]
        self.assertIn("SAME_SCUMM_CONTROLLER_MODE", phase)
        self.assertIn("cmp #$02", phase)

    def test_visual_phase_establishes_one_invalid_cache_baseline_before_input(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_visual.pasm").read_text()
        phase = source.split("ScummV5_Visual_Frame_Far:", 1)[1].split(
            "ScummV5_Visual_Frame__skip_actor:", 1)[0]
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_VALID", phase)
        self.assertIn("ScummV5_Visual_Frame__render_actor", phase)
        self.assertIn("CanWrite", (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text())

    def test_controller_phase_publishes_semantics_but_does_not_compose_actor(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        phase = source.split("ScummV5_Controller_Frame__done:", 1)[1].split(
            "; Publish semantic actor state", 1)[0]
        self.assertIn("SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $04", phase)
        self.assertIn("coherent desired snapshot", phase)

    def test_initial_actor_render_waits_for_room_visual_transaction(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_visual.pasm").read_text()
        phase = source.split("ScummV5_Visual_Frame_Far:", 1)[1].split(
            "ScummV5_Visual_Frame__skip_actor:", 1)[0]
        self.assertIn("SAME_VIDEO_SURFACE_PENDING_VISUAL", phase)
        self.assertIn("Same_VideoSurface_CanWrite_Far", phase)

    def test_visual_snapshot_storage_is_disjoint_from_controller_and_object_state(self) -> None:
        source = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_X           = $7E5E10", source)
        self.assertIn("SAME_SCUMM_CONTROLLER_STATE_END           = $7E5FEC", source)
        self.assertIn("SAME_SCUMM_OBJECT_COUNT                   = $7E5FF0", source)
        self.assertIn("SAME_SCUMM_SETSTATE_OBJECT                = $7E5FF2", source)
        # The snapshot/cache block must end before the controller state block;
        # this catches accidental relocation into scheduler/object storage.
        import re
        addresses = {
            name: int(value, 16)
            for name, value in re.findall(
                r"^(SAME_SCUMM_CONTROLLER_(?:RENDER_X|DESIRED_X|STATE_END|MODE))\s*=\s*\$([0-9A-Fa-f]+)",
                source, re.MULTILINE)
        }
        self.assertLess(addresses["SAME_SCUMM_CONTROLLER_RENDER_X"],
                        addresses["SAME_SCUMM_CONTROLLER_MODE"])
        self.assertLess(addresses["SAME_SCUMM_CONTROLLER_DESIRED_X"],
                        addresses["SAME_SCUMM_CONTROLLER_STATE_END"])

    def test_inspect_talk_returns_fixture_control_to_hover_mode(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        block = source.split("ScummV5_Controller_Frame__talk_ok:", 1)[1].split(
            "ScummV5_Controller_Frame__queue_ok:", 1)[0]
        self.assertIn("cmp #$04", block)
        self.assertIn("sta.l SAME_SCUMM_CONTROLLER_MODE", block)
        self.assertIn("sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY", block)


if __name__ == "__main__":
    unittest.main()
