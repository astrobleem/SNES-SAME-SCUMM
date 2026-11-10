from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ScummV5ControllerFixtureTests(unittest.TestCase):
    def test_actor_publisher_does_not_resolve_uninitialized_c14_records(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        publish = source.split("ScummV5_Controller_PublishActorVisual_Far:", 1)[1].split(
            "ScummV5_Controller_PublishActorVisual__c14_ready:", 1
        )[0]
        self.assertIn("lda.l SAME_SCUMM_C14_INITIALIZED", publish)
        self.assertIn("bne ScummV5_Controller_PublishActorVisual__c14_ready", publish)
        self.assertIn("sta.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME", publish)
        self.assertIn("sta.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE", publish)
        self.assertIn("jml ScummV5_Controller_PublishActorVisual__done", publish)
        self.assertNotIn("SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_COSTUME", publish)

    def test_actor_renderer_waits_for_initialized_c14_before_pose_lookup(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        render = source.split("ScummV5_Controller_RenderActor_Far:", 1)[1].split(
            "ScummV5_Controller_RenderActor__done:", 1
        )[0]
        guard = render.split("ScummV5_Controller_RenderActor__c14_ready:", 1)[0]
        self.assertIn("lda.l SAME_SCUMM_C14_INITIALIZED", guard)
        self.assertIn("bne ScummV5_Controller_RenderActor__c14_ready", guard)
        self.assertIn("jml ScummV5_Controller_RenderActor__done", guard)
        self.assertLess(
            render.index("lda.l SAME_SCUMM_C14_INITIALIZED"),
            render.index("lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT"),
        )
        self.assertIn("jsl ScummV5_ActorPose_Ensure_Far", render)

    def test_far_fixture_aliases_preserve_the_data_bank(self) -> None:
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            from generate_engine_fixtures import far_fixture_include
        finally:
            sys.path.pop(0)

        far = far_fixture_include("ScummV5_C2_Program_c19_cutscene:\n    .byte $18\n")
        self.assertIn(
            "ScummV5_C2_Program_c19_cutscene = $090000+ScummV5_Far_C2_Program_c19_cutscene",
            far,
        )

    def test_controller_uses_production_sentence_tuple_and_supports_secondary_object(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        self.assertGreaterEqual(source.count("sta.l SAME_SCUMM_SENTENCE_API_PENDING"), 2)
        self.assertEqual(source.count("sta.l SAME_SCUMM_SENTENCE_API_OBJECT1+1"), 0)
        self.assertIn("ScummV5_Controller_Frame__select_secondary:", source)
        self.assertIn("ScummV5_Controller_Frame__select_secondary_ready:", source)
        self.assertIn("sta.l SAME_SCUMM_SENTENCE_API_OBJECT2", source)
        self.assertIn("ScummV5_QueueSentence", (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text())

    def test_secondary_selection_uses_source_hit_and_preserves_one_object_path(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        secondary = source.split("ScummV5_Controller_Frame__select_secondary:", 1)[1].split(
            "ScummV5_Controller_Frame__select_secondary_ready:", 1
        )[0]
        self.assertIn("ScummV5_Generic_Object_HitTest_Far", secondary)
        self.assertIn("SAME_SCUMM_INTERACTION_OBJECT", secondary)
        self.assertIn("SAME_SCUMM_SENTENCE_API_OBJECT2", secondary)
        self.assertIn("lda #$04", secondary)
        self.assertIn("and #$0040", source)
        self.assertIn("cmp #$03", source)
        self.assertIn("cmp #$04", source)

    def test_secondary_object_is_cleared_at_room_and_cursor_lifecycle_boundaries(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        reset = source.split("ScummV5_Controller_ResetInteractionOnRoomInstall_Far:", 1)[1].split(
            "ScummV5_Controller_Frame_Far:", 1
        )[0]
        invalidate = source.split(
            "ScummV5_Controller_InvalidateSelectionOnCursorMove_Far:", 1
        )[1].split("ScummV5_Controller_InvalidateSelectionOnCursorMove__done:", 1)[0]
        self.assertIn("sta.l SAME_SCUMM_SENTENCE_API_OBJECT2", reset)
        self.assertIn("__secondary", invalidate)
        self.assertIn("sta.l SAME_SCUMM_SENTENCE_API_OBJECT2", invalidate)
        self.assertIn("ScummV5_Controller_Frame__action_pending_reentry", source)
        reentry = source.split("ScummV5_Controller_Frame__action_pending_reentry:", 1)[1].split(
            "ScummV5_Controller_Frame__hud:", 1
        )[0]
        self.assertIn("sta.l SAME_SCUMM_SENTENCE_API_OBJECT2", reentry)

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

    def test_empty_room_click_starts_canonical_ego_walk_not_a_sentence(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        selection = source.split(
            "ScummV5_Controller_Frame__mode_select_fallback:", 1
        )[1].split("ScummV5_Controller_Frame__select_verb:", 1)[0]
        miss = selection.split(
            "ScummV5_Controller_Frame__walk_miss_done:", 1
        )[0]
        self.assertIn("SAME_SCUMM_M23B_VARIABLES+2 ; VAR_EGO", miss)
        self.assertIn("SAME_SCUMM_C14_A_PRESENT", miss)
        self.assertIn("SAME_SCUMM_C14_A_ROOM", miss)
        self.assertIn("ScummV5_PutActor_Adjust_Far", miss)
        self.assertIn("ScummV5_Movement_StartNormalized_Far", miss)
        self.assertIn("SAME_SCUMM_MOVE_QUERY_DIR", miss)
        self.assertNotIn("SAME_SCUMM_SENTENCE_API_PENDING", miss)

    def test_controller_cycles_authored_verbs_and_uses_selected_object(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        cycle = source.split("ScummV5_Controller_Frame__select_verb:", 1)[1].split(
            "ScummV5_Controller_Frame__action_pending:", 1
        )[0]
        self.assertIn("ScummV5_Generic_Verb_Next_Far", cycle)
        self.assertIn("SAME_SCUMM_CONTROLLER_OBJECT", cycle)
        submit = source.split("ScummV5_Controller_Frame__select_verb_a_pressed:", 1)[1].split(
            "ScummV5_Controller_Frame__action_pending:", 1
        )[0]
        self.assertIn("SAME_SCUMM_SENTENCE_API_OBJECT1", submit)
        self.assertNotIn("#$EA", submit)

    def test_semantic_sentence_submit_is_not_gated_by_hud_render_status(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        submit = source.split(
            "ScummV5_Controller_Frame__select_verb_a_pressed:", 1
        )[1].split("ScummV5_Controller_Frame__action_pending:", 1)[0]
        self.assertNotIn("SAME_SCUMM_TALK_VISUAL_STATUS", submit)
        # Active authored dialogue still owns the normal controller gate;
        # only an inactive overlay's presentation failure is non-semantic.
        active_talk_gate = source.split(
            "ScummV5_Controller_Frame__stack_ok:", 1
        )[1].split("ScummV5_Controller_Frame__talk_ok:", 1)[0]
        self.assertIn("SAME_SCUMM_TALK_ACTIVE", active_talk_gate)

    def test_talk_owned_input_edge_cannot_reach_generic_controller_after_talk(self) -> None:
        controller = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        generic = controller.split(
            "ScummV5_Controller_Frame__generic_ready:", 1
        )[1].split("ScummV5_Controller_Frame__stack_ok:", 1)[0]
        self.assertIn("SAME_INPUT_TALK_OWNED_VALID", generic)
        self.assertIn("SAME_INPUT_EDGE_SEQUENCE", generic)
        self.assertLess(
            generic.index("SAME_INPUT_TALK_OWNED_VALID"),
            generic.index("SAME_SCUMM_CONTROLLER_ROOM_READY"),
        )
        input_service = (ROOT / "runtime/snes/services/input.pasm").read_text()
        poll = input_service.split("Same_Input_Poll:", 1)[1]
        self.assertIn("SAME_INPUT_EDGE_SEQUENCE", poll)
        self.assertIn("SAME_SCUMM_TALK_ACTIVE", poll)
        self.assertIn("sta.l SAME_INPUT_TALK_OWNED_SEQUENCE", poll)
        self.assertIn("sta.l SAME_INPUT_TALK_OWNED_VALID", poll)
        memory = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
        self.assertIn("SAME_INPUT_EDGE_SEQUENCE    = $7E2208", memory)

    def test_generated_room_metadata_exports_generic_hit_and_verb_services(self) -> None:
        source = (ROOT / "tools/generate_snes_cooked_rooms.py").read_text()
        self.assertIn('"ScummV5_Generic_Object_HitTest_Far:"', source)
        self.assertIn('"ScummV5_Generic_Object_ValidateSelected_Far:"', source)
        self.assertIn('"ScummV5_Generic_Verb_First_Far:"', source)
        self.assertIn('"ScummV5_Generic_Verb_Next_Far:"', source)
        self.assertIn("SAME_SCUMM_SETSTATE_LOCAL_RECORDS", source)

    def test_generated_verb_cycle_skips_current_entry_before_returning_next(self) -> None:
        source = (ROOT / "tools/generate_snes_cooked_rooms.py").read_text()
        block = source.split('"ScummV5_Generic_Verb_Next_Far:"', 1)[1].split(
            '"ScummV5_Verb_Query_Far:"', 1
        )[0]
        self.assertIn(
            'f"    bra ScummV5_Generic_Verb_Next_Far__skip_{entry_index}"',
            block,
        )
        self.assertLess(
            block.index('sta.l SAME_SCUMM_INTERACTION_VERB_AFTER'),
            block.index('bra ScummV5_Generic_Verb_Next_Far__skip_{entry_index}'),
        )

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

    def test_controller_has_generic_sentence_completion_not_state_policy(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        self.assertIn("ScummV5_Controller_Frame__action_pending:", source)
        self.assertIn("SAME_SCUMM_SENTENCE_API_PENDING", source)
        self.assertIn("SAME_SCUMM_C20_COUNT", source)
        self.assertIn("SAME_SCUMM_TALK_ACTIVE", source)
        self.assertIn("ScummV5_Controller_RefreshSelection_Far", source)
        for forbidden in (
            "check_opened", "submit_inspect", "select_inspect",
            "OPEN LOCKER", "INSPECT", "WALKING",
        ):
            self.assertNotIn(forbidden, source)

    def test_cursor_motion_reenters_generic_object_selection(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        self.assertIn(
            "ScummV5_Controller_InvalidateSelectionOnCursorMove_Far:", source)
        self.assertEqual(
            source.count(
                "jsl ScummV5_Controller_InvalidateSelectionOnCursorMove_Far"),
            4,
        )
        helper = source.split(
            "ScummV5_Controller_InvalidateSelectionOnCursorMove_Far:", 1)[1].split(
                "ScummV5_Controller_InvalidateSelectionOnCursorMove__done:", 1
            )[0]
        self.assertIn("cmp #$01", helper)
        self.assertIn("sta.l SAME_SCUMM_CONTROLLER_MODE", helper)
        self.assertIn("sta.l SAME_SCUMM_CONTROLLER_OBJECT", helper)
        self.assertIn("sta.l SAME_SCUMM_CONTROLLER_VERB", helper)

    def test_walking_validator_fences_semantic_snapshot_before_success_witness(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        self.assertIn("wait_for_semantic_moving_snapshot", validator)
        self.assertIn('session.add_write_hook(\n            0x7E5E46', validator)
        semantic = validator.index("semantic_snapshot = wait_for_semantic_moving_snapshot")
        witness = validator.index("walking_witness = wait_for_moving_publication")
        commit = validator.index("walking_commit = wait_for_committed_generation")
        self.assertLess(semantic, witness)
        self.assertLess(witness, commit)
        self.assertIn('"stage": "semantic_moving_snapshot"', validator)

    def test_validator_requires_completed_logical_frame_fence(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        advance = validator.split("def advance_logical_safe", 1)[1].split("\ndef tap", 1)[0]
        self.assertIn("logical-frame observation fence is not installed", advance)
        self.assertNotIn("advance_safe(session, 1)", advance)

    def test_validator_installs_fence_before_post_startup_semantic_polling(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        install = validator.rindex('LOGICAL_FRAME_HOOK = session.add_exec_hook(')
        readiness = validator.index('require(ready >= 6')
        first_fenced_poll = validator.index('advance_logical_safe(session)', install)
        self.assertLess(readiness, install)
        self.assertLess(install, first_fenced_poll)
        self.assertIn('completed logical-frame fence', validator)

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
        publication = source.split(
            "ScummV5_Controller_PublishActorVisual_Far:", 1
        )[1].split("ScummV5_Controller_PublishActorVisual__done:", 1)[0]
        frame_selection = publication.split(
            "ScummV5_Controller_PublishActorVisual__stand_frame:", 1
        )[0]
        self.assertIn("SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_WALK_FRAME,x", frame_selection)
        self.assertIn(".a8", frame_selection)
        self.assertIn("lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_STAND_FRAME,x", publication)
        self.assertIn("sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME", publication)
        self.assertIn("ScummV5_Controller_PublishActorVisual_Far", source)

    def test_actor_animation_uses_source_loop_bounds_not_fixed_mask(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        publication = source.split(
            "ScummV5_Controller_PublishActorVisual_Far:", 1
        )[1].split("ScummV5_Controller_PublishActorVisual__done:", 1)[0]
        self.assertGreaterEqual(
            publication.count("adc.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH"), 2
        )
        self.assertIn("SAME_SCUMM_ACTOR_POSE_LOOP_START", publication)
        self.assertIn("SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH", publication)
        self.assertNotIn("and #$07", publication)

    def test_actor_animation_key_waits_for_checked_pose_presentation(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        advance = source.split(
            "ScummV5_Controller_PublishActorVisual__advance_pose_step:", 1
        )[1].split("ScummV5_Controller_PublishActorVisual__pose_step_limit_max:", 1)[0]
        self.assertLess(
            advance.index("lda.l SAME_SCUMM_ACTOR_POSE_STATE"),
            advance.index("lda.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH"),
        )
        self.assertIn(
            "bne ScummV5_Controller_PublishActorVisual__save_pose_key", advance
        )
        render_success = source.split(
            "ScummV5_Controller_RenderActor__present_success:", 1
        )[1].split("ScummV5_Controller_RenderActor__full_compose_retry:", 1)[0]
        self.assertIn("sta.l SAME_SCUMM_ACTOR_POSE_STATE", render_success)

    def test_actor_provider_destination_matches_as_three_bytes(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        block = source.split("ScummV5_ActorPose_ProviderMatches_Far:", 1)[1].split(
            "ScummV5_ActorPose_ProviderMatches__no:", 1
        )[0]
        self.assertIn("sep #$20\n    .a8\n    lda.l SAME_MSU1_DESTINATION", block)
        self.assertIn("lda.l SAME_MSU1_DESTINATION+1\n    cmp #>SAME_SCUMM_ACTOR_POSE_BUFFER", block)
        self.assertIn("lda.l SAME_MSU1_DESTINATION+2\n    cmp #SAME_SCUMM_LIVE_ROOM_PENDING_BANK", block)
        self.assertNotIn(".a16\n    lda.l SAME_MSU1_DESTINATION", block)
        self.assertIn("rep #$20\n    .a16\n    lda.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH", block)

    def test_actor_blit_preserves_packed_destination_abi(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        call = source.split("Same_VideoSurface_BlitIndexedRect_Far", 1)[0].split(
            "ScummV5_Controller_RenderActor__frame_base:", 1)[1]
        self.assertIn("lda.l SAME_SCUMM_CONTROLLER_RENDER_BASE", call)
        self.assertIn("ldy #$0000", call)
        self.assertIn("lda.l SAME_SCUMM_CONTROLLER_RENDER_SRC\n    tay", call)
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
        self.assertNotIn("\n    pla\n", failure)
        self.assertIn("SAME_VIDEO_DIAG_BLIT_EXITS", failure)

    def test_surface_blit_rejects_destination_overflow_before_pixel_store(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_BlitIndexedRect_Far:", 1)[1].split(
            "Same_VideoSurface_BlitIndexedRect__row:", 1)[0]
        self.assertIn("cmp #$0101", block)
        self.assertIn("cmp #$00E1", block)
        self.assertLess(block.index("Same_VideoSurface_BlitIndexedRect__right_bound_ok:"),
                        source.index("Same_VideoSurface_BlitIndexedRect__row:"))
        self.assertLess(block.index("Same_VideoSurface_BlitIndexedRect__bottom_bound_ok:"),
                        source.index("Same_VideoSurface_BlitIndexedRect__row:"))

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
        self.assertIn("source-backed pose is already validated", compose)

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
        engine = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        controller = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        install = visual.split("ScummV5_RoomVisual_Installed_Far:", 1)[1].split(
            "    plp", 1)[0]
        self.assertIn("Same_VideoSurface_RoomInstalled_Far", visual)
        self.assertIn("ScummV5_Controller_ResetInteractionOnRoomInstall_Far", engine)
        mismatch = controller.split("ScummV5_Controller_RenderActor_Far:", 1)[1].split(
            "ScummV5_Controller_RenderActor__room_ok:", 1)[0]
        self.assertNotIn("SAME_SCUMM_CONTROLLER_RENDER_VALID", mismatch)
        self.assertIn("SAME_SCUMM_CONTROLLER_RENDER_ROOM", controller)

    def test_generic_frame_has_no_fate_room_gate_and_has_lifecycle_readiness(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        generic = source.split("ScummV5_Controller_Frame__generic_ready:", 1)[1].split(
            "ScummV5_Controller_Frame__phase_ok:", 1
        )[0]
        self.assertNotIn("cmp #$2A", generic)
        self.assertNotIn("cmp #$44", generic)
        self.assertIn("SAME_SCUMM_CONTROLLER_ROOM_READY", generic)
        self.assertIn("SAME_SCUMM_C22_NULL_SCENE", generic)

    def test_room_install_reset_is_independent_of_actor_visual_mask(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        install = source.split("ScummV5_M23A_CommitRoom:", 1)[1].split(
            "ScummV5_Op_LoadRoom:", 1
        )[0]
        self.assertIn("SAME_BUILD_SCUMM_CONTROLLER", install)
        self.assertIn("SAME_SCUMM_CONTROLLER_ROOM_READY", install)

    def test_generic_controller_production_path_has_no_room42_object_policy(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        frame = source.split("ScummV5_Controller_Frame_Far:", 1)[1].split(
            "ScummV5_Controller_Frame__room68:", 1
        )[0]
        self.assertNotIn("#$01EA", frame)
        self.assertNotIn("#$00BE", frame)
        self.assertNotIn("#$00F1", frame)
        self.assertNotIn("#$004C", frame)
        self.assertIn("ScummV5_Generic_Object_HitTest_Far", source)

    def test_controller_capability_is_separate_from_fixture(self) -> None:
        selection = (ROOT / "tools/generate_snes_engine_selection.py").read_text()
        build = (ROOT / "tools/build_snes.sh").read_text()
        main = (ROOT / "runtime/snes/main.pasm").read_text()
        frame = (ROOT / "runtime/snes/kernel/frame.pasm").read_text()
        visual = (ROOT / "runtime/snes/engines/scumm_v5_visual.pasm").read_text()
        controller = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        self.assertIn("--scumm-controller", selection)
        self.assertIn("SAME_BUILD_SCUMM_CONTROLLER =", selection)
        self.assertIn("SAME_BUILD_SCUMM_CONTROLLER:-0", build)
        self.assertIn(".if SAME_BUILD_SCUMM_CONTROLLER\n.include \"engines/scumm_v5_controller_far.pasm\"", main)
        self.assertIn(".if SAME_BUILD_SCUMM_CONTROLLER\n    ; Sample fixture input", frame)
        self.assertIn("SAME_BUILD_SCUMM_CONTROLLER", main)
        self.assertIn(".if SAME_BUILD_SCUMM_CONTROLLER\n    ; The established room-installed callback", controller)
        self.assertIn("SAME_BUILD_SCUMM_CONTROLLER_FIXTURE", controller)

    def test_conformance_room_service_far_capability_is_generated_from_its_own_inputs(self) -> None:
        generator = ROOT / "tools/generate_snes_engine_selection.py"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "active_engine.inc.pasm"
            subprocess.run(
                [
                    "python3", str(generator), "--engine", "scumm_v5",
                    "--scumm-controller-conformance", "--output", str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            config = output.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_BUILD_SCUMM_M23A = $00", config)
            self.assertIn("SAME_BUILD_SCUMM_ROOM_SERVICE = $01", config)
            self.assertIn("SAME_BUILD_SCUMM_ROOM_SERVICE_FAR = $01", config)
            self.assertIn("SAME_BUILD_M24RB = $00", config)
            self.assertIn(
                "SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE_NO_ROOT_ROOM = $00", config
            )
            self.assertIn("SAME_BUILD_SCUMM_C19_NATIVE_FIXTURE = $00", config)

            no_room_output = Path(tmp) / "no-room-active_engine.inc.pasm"
            subprocess.run(
                [
                    "python3", str(generator), "--engine", "scumm_v5",
                    "--scumm-controller-conformance",
                    "--scumm-controller-conformance-no-root-room",
                    "--output", str(no_room_output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            no_room_config = no_room_output.with_name("build_config.inc.pasm").read_text()
            self.assertIn(
                "SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE_NO_ROOT_ROOM = $01",
                no_room_config,
            )

            native_fixture_output = Path(tmp) / "c19-active_engine.inc.pasm"
            subprocess.run(
                [
                    "python3", str(generator), "--engine", "scumm_v5",
                    "--scumm-controller-conformance",
                    "--scumm-controller-conformance-no-root-room",
                    "--scumm-c19-native-fixture",
                    "--output", str(native_fixture_output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            native_fixture_config = native_fixture_output.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_BUILD_SCUMM_C19_NATIVE_FIXTURE = $01", native_fixture_config)

            invalid_no_room = subprocess.run(
                [
                    "python3", str(generator), "--engine", "scumm_v5",
                    "--scumm-controller-conformance-no-root-room",
                    "--output", str(no_room_output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(invalid_no_room.returncode, 0)
            self.assertIn("requires SCUMM v5 controller conformance", invalid_no_room.stderr)
            output_m24rb = Path(tmp) / "m24rb-active_engine.inc.pasm"
            subprocess.run(
                [
                    "python3", str(generator), "--engine", "scumm_v5",
                    "--m24rb", "--output", str(output_m24rb),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            config_m24rb = output_m24rb.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_BUILD_SCUMM_ROOM_SERVICE_FAR = $01", config_m24rb)

    def test_title_start_routing_is_disabled_unless_both_rooms_are_explicit(self) -> None:
        generator = ROOT / "tools/generate_snes_engine_selection.py"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "default.inc.pasm"
            subprocess.run(
                ["python3", str(generator), "--engine", "scumm_v5", "--output", str(output)],
                check=True, capture_output=True, text=True,
            )
            default_config = output.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_BUILD_SCUMM_TITLE_START = $00", default_config)

            output = Path(tmp) / "explicit.inc.pasm"
            subprocess.run(
                [
                    "python3", str(generator), "--engine", "scumm_v5",
                    "--scumm-title-start-room", "75",
                    "--scumm-title-target-room", "49",
                    "--output", str(output),
                ],
                check=True, capture_output=True, text=True,
            )
            explicit_config = output.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_BUILD_SCUMM_TITLE_START = $01", explicit_config)
            self.assertIn("SCUMM_V5_TITLE_START_ROOM = $4B", explicit_config)
            self.assertIn("SCUMM_V5_TITLE_TARGET_ROOM = $31", explicit_config)

            rejected = subprocess.run(
                [
                    "python3", str(generator), "--engine", "scumm_v5",
                    "--scumm-title-start-room", "0", "--output", str(output),
                ],
                capture_output=True, text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("requires both start-room and target-room", rejected.stderr)

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

    def test_indexed_surface_service_is_independent_of_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "generated"
            manifest = Path(tmp) / "manifest.json"
            subprocess.run(
                [
                    "python3", str(ROOT / "tools/generate_snes_video_overlay.py"),
                    "--overlay", "none", "--carrier", "sa1_bwram",
                    "--backend", "mode3_surface", "--surface-available",
                    "--output-dir", str(output), "--manifest", str(manifest),
                ], check=True, cwd=ROOT, capture_output=True, text=True,
            )
            include = (output / "video_overlay_constants.inc.pasm").read_text()
            metadata = json.loads(manifest.read_text())
            self.assertIn("SAME_VIDEO_SURFACE_AVAILABLE = $01", include)
            self.assertIn("SAME_VIDEO_OVERLAY_BG2 = $00", include)
            self.assertTrue(metadata["surface_available"])

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

    def test_state_neutral_action_does_not_assume_dialogue(self) -> None:
        validator = (ROOT / "tools/validate_scumm_room42_controller_nexen.py").read_text()
        self.assertIn("state-neutral action completion/reselection", validator)
        self.assertIn('"moving1"] == 0', validator)
        self.assertIn('"04-state-neutral-complete.png"', validator)

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

    def test_runtime_named_hud_retries_busy_text_publication(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        block = source.split("ScummV5_Controller_Frame__hud:", 1)[1].split(
            "ScummV5_Controller_Frame__done:", 1)[0]
        self.assertIn("SAME_SCUMM_TALK_VISUAL_STATUS", block)
        self.assertIn("ScummV5_Controller_ShowHud_Far", block)
        self.assertIn("ScummV5_Controller_Frame__hud_done", block)
        self.assertIn("SAME_SCUMM_CONTROLLER_HUD_DIRTY", block)
        self.assertIn("SAME_VIDEO_TEXT_SERVICE_AVAILABLE", block)

    def test_talk_overlay_skips_encoded_controls_but_keeps_logical_raw_stream(self) -> None:
        source = (ROOT / "runtime/snes/services/video_overlay_surface.pasm").read_text()
        block = source.split("Same_VideoOverlay_RasterSegmentFast15:", 1)[1].split(
            "; Input A=u8 encoded glyph", 1)[0]
        self.assertGreaterEqual(block.count("SAME_SCUMM_TALK_RAW"), 4)
        self.assertIn("__validate_control", block)
        self.assertIn("__glyph_control", block)

    def test_overlay_descriptor_clamps_content_to_initialized_raster(self) -> None:
        source = (ROOT / "runtime/snes/services/video_overlay_surface.pasm").read_text()
        block = source.split("Same_VideoOverlay_ShowTalkSegment__ready:", 1)[1].split(
            "Same_VideoOverlay_ShowTalkSegment__visual_error:", 1)[0]
        self.assertIn("SAME_OVERLAY_MAX_WIDTH-1", block)
        self.assertIn("SAME_OVERLAY_MAX_HEIGHT-1", block)
        self.assertIn("SAME_OVERLAY_DESCRIPTOR_CONTENT_X1", block)
        self.assertIn("SAME_OVERLAY_DESCRIPTOR_CONTENT_Y1", block)
        self.assertNotIn("SAME_OVERLAY_MAX_CELLS =", block)

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

    def test_msu_actor_transfer_waits_for_surface_presentation_ownership(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_visual.pasm").read_text()
        phase = source.split("ScummV5_Visual_Frame_Far:", 1)[1].split(
            ".elseif SAME_BUILD_SCUMM_CONTROLLER_FIXTURE", 1)[0]
        pending_gate = phase.index("SAME_VIDEO_SURFACE_PENDING_VISUAL")
        write_gate = phase.index("Same_VideoSurface_CanWrite_Far")
        actor_call = phase.index("ScummV5_Controller_RenderActor_Far")
        self.assertLess(pending_gate, actor_call)
        self.assertLess(write_gate, actor_call)
        self.assertIn("bne ScummV5_Visual_Frame__skip_actor", phase[pending_gate:])
        self.assertIn("bcs ScummV5_Visual_Frame__skip_actor", phase[write_gate:])

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

    def test_action_completion_revalidates_source_object_and_authored_verbs(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        block = source.split("ScummV5_Controller_Frame__action_pending:", 1)[1].split(
            "ScummV5_Controller_Frame__hud:", 1
        )[0]
        self.assertIn("SAME_SCUMM_C31_MOVING+1", block)
        self.assertIn("ScummV5_Controller_RefreshSelection_Far", block)
        refresh = source.split("ScummV5_Controller_RefreshSelection_Far:", 1)[1]
        self.assertIn("ScummV5_Generic_Object_ValidateSelected_Far", refresh)
        self.assertNotIn("ScummV5_Generic_Object_HitTest_Far", refresh)
        self.assertIn("ScummV5_Generic_Verb_First_Far", refresh)

    def test_hud_uses_runtime_scumm_names(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        self.assertIn("ScummV5_Controller_BuildHudText_Far", source)
        self.assertIn("SAME_SCUMM_C17_V_NAME_LENGTH", source)
        self.assertIn("SAME_SCUMM_OBJECT_NAMES", source)
        for forbidden in ("HudHover", "HudVerb", "HudInspect", "HudWalk"):
            self.assertNotIn(forbidden, source)

    def test_object_name_cache_cannot_overlap_c17(self) -> None:
        import re
        source = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
        values = {
            name: int(value, 16)
            for name, value in re.findall(
                r"^(SAME_[A-Z0-9_]+)\s*=\s*\$([0-9A-Fa-f]+)",
                source, re.MULTILINE)
        }
        names_end = (
            values["SAME_SCUMM_OBJECT_NAMES"]
            + values["SAME_SCUMM_OBJECT_NAME_COUNT"]
            * values["SAME_SCUMM_OBJECT_NAME_STRIDE"]
        )
        self.assertEqual(names_end, values["SAME_SCUMM_OBJECT_NAMES_END"])
        self.assertLessEqual(names_end, values["SAME_SCUMM_C10_STATE"])
        self.assertLessEqual(names_end, values["SAME_SCUMM_C17_VERBS"])

    def test_room_surface_clear_uses_word_bounded_writes(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_Clear:", 1)[1].split(
            "Same_VideoSurface_ComputeProjection:", 1)[0]
        self.assertIn("php", block)
        self.assertIn("lda #$0000", block)
        self.assertIn("inx\n    inx", block)
        self.assertIn("plp", block)

    def test_full_projection_skips_redundant_surface_clear(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_ClearForProjection:", 1)[1].split(
            "Same_VideoSurface_ComputeProjection:", 1)[0]
        self.assertIn("SAME_VIDEO_SURFACE_COPY_WIDTH", block)
        self.assertIn("cmp #$0100", block)
        self.assertIn("SAME_VIDEO_SURFACE_COPY_HEIGHT", block)
        self.assertIn("cmp #$00E0", block)
        self.assertIn("Same_VideoSurface_Clear", block)

    def test_projection_blit_has_bounded_word_copy_and_zero_remainder_guard(self) -> None:
        source = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        block = source.split("Same_VideoSurface_BlitProjection:", 1)[1].split(
            "Same_VideoSurface_PushPresentation:", 1)[0]
        self.assertIn("SAME_VIDEO_SURFACE_DP_PIXEL_COUNT", block)
        self.assertIn("cmp #$0008", block)
        self.assertIn("Same_VideoSurface_BlitProjection__remainder", block)
        remainder = block.split(
            "Same_VideoSurface_BlitProjection__remainder:", 1)[1].split(
            "Same_VideoSurface_BlitProjection__tail:", 1)[0]
        self.assertIn("lda SAME_VIDEO_SURFACE_DP_PIXEL_COUNT", remainder)
        self.assertIn("beq Same_VideoSurface_BlitProjection__tail", remainder)
        self.assertIn("sta.l SAME_BWRAM_SURFACE_BASE,x", block)


if __name__ == "__main__":
    unittest.main()
