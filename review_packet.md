# Review packet: SAME / SCUMM hoist checkpoint

UPDATE: prepared while gameplay remains paused. No reset, amend, clean, force-push, or split was performed.

## Commit scope

- Full commit: `3c88f54516bb04700ce353fb51e1d4f8c0627e6e`
- Parent: `3476f816fc8766f90f790699da059ba96aee232c`
- Branch: `main`
- Intended remote: `origin` = `https://github.com/astrobleem/SNES-SAME-SCUMM.git`
- Last published base: parent `3476f81` (the repository’s initial published SCUMM import).
- Commit statistics: 457 changed files; 98,072 insertions; 2,344 deletions.
- Scope assessment: this is accumulated campaign work from the SAME/SCUMM effort (engine, cooker, validators, fixtures, documentation, audio/build support), with the current hoist additions included. It is not a narrowly isolated hoist-only commit. No known unrelated project was intentionally staged. The authoritative 73 MiB `ATLANTIS.zip` and two DOCX files remain untracked and were excluded.
- Push attempt: `git push origin main` was rejected by the safety gate because publishing the broad 457-file commit to unverified `origin/main` could export potentially sensitive project/source data. Nothing was pushed.

### Complete changed-file list

The exact name/status list is preserved below as emitted from commit `3c88f545`:

```
M	AGENTS.md
M	Makefile
M	STATUS.md
A	audio/fate_s6/ADLIB_ORACLE.md
A	audio/fate_s6/REVIEW_ADLIB_SOUND154.md
A	audio/fate_s6/REVIEW_CC7_REAUDIT.md
A	audio/fate_s6/TAD-LICENSE.txt
A	audio/fate_s6/auditions/README.md
A	audio/fate_s6/auditions/REVIEW_ROUND1.md
A	audio/fate_s6/auditions/REVIEW_ROUND2.md
A	audio/fate_s6/auditions/REVIEW_ROUND3.md
A	audio/fate_s6/auditions/REVIEW_ROUND4.md
A	audio/fate_s6/auditions/REVIEW_ROUND5.md
A	audio/fate_s6/auditions/bass_range.mml
A	audio/fate_s6/auditions/flute_zones.mml
A	audio/fate_s6/auditions/marimba_zones.mml
A	audio/fate_s6/auditions/organ_zones.mml
A	audio/fate_s6/auditions/pad_zones.mml
A	audio/fate_s6/auditions/percussion.mml
A	audio/fate_s6/fate.terrificaudio
A	audio/fate_s6/fate_tad_layout.inc.pasm
A	audio/fate_s6/m21_sound80/manifest.json
A	audio/fate_s6/m21_sound80/program_32_used_range.mml
A	audio/fate_s6/m21_sound80/program_33_used_range.mml
A	audio/fate_s6/m21_sound80/program_50_used_range.mml
A	audio/fate_s6/m21_sound80/program_57_used_range.mml
A	audio/fate_s6/m21_sound80/program_77_used_range.mml
A	audio/fate_s6/m21_sound80/program_82_used_range.mml
A	audio/fate_s6/m21_sound80/sound80_default.audit.json
A	audio/fate_s6/m21_sound80/sound80_default.mml
A	audio/fate_s6/m21_sound80/sound80_hook14.audit.json
A	audio/fate_s6/m21_sound80/sound80_hook14.mml
A	audio/fate_s6/m22_sound80/audit.json
A	audio/fate_s6/m22_sound80/instrument_bank.json
A	audio/fate_s6/m22_sound80/program_107_used_range.mml
A	audio/fate_s6/m22_sound80/program_50_used_range.mml
A	audio/fate_s6/m22_sound80/program_97_used_range.mml
A	audio/fate_s6/m22_sound80/sound80_hook14_hook8_sections.mml
A	audio/fate_s6/m22_sound80/terrific_audio_driver_m22.patch
A	audio/fate_s6/samples/Phantasia_Flute.brr
A	audio/fate_s6/samples/Phantasia_Soft_Bass.brr
A	audio/fate_s6/samples/fate154_adlib_manifest.json
A	audio/fate_s6/samples/fate154_ch1_high.wav
A	audio/fate_s6/samples/fate154_ch1_low.wav
A	audio/fate_s6/samples/fate154_ch2_mid.wav
A	audio/fate_s6/samples/fate154_ch4_mid.wav
A	audio/fate_s6/samples/fate154_ch5_high.wav
A	audio/fate_s6/samples/fate154_ch6_high.wav
A	audio/fate_s6/samples/fate154_ch6_low.wav
A	audio/fate_s6/samples/loop_safe_manifest.json
A	audio/fate_s6/samples/mt32_drum_kick.wav
A	audio/fate_s6/samples/mt32_drum_n38.wav
A	audio/fate_s6/samples/mt32_lead_flute.wav
A	audio/fate_s6/samples/mt32_marimba.wav
A	audio/fate_s6/samples/mt32_marimba_low.wav
A	audio/fate_s6/samples/mt32_organ.wav
A	audio/fate_s6/samples/mt32_organ_cycle.wav
A	audio/fate_s6/samples/mt32_p13.wav
A	audio/fate_s6/samples/mt32_p13_low.wav
A	audio/fate_s6/samples/mt32_p74.wav
A	audio/fate_s6/samples/mt32_p74_cycle.wav
A	audio/fate_s6/samples/mt32_p74_cycle_x2.wav
A	audio/fate_s6/samples/mt32_p74_cycle_x4.wav
A	audio/fate_s6/samples/mt32_p74_low.wav
A	audio/fate_s6/samples/mt32_p74_low_x2.wav
A	audio/fate_s6/samples/mt32_p74_low_x4.wav
A	audio/fate_s6/samples/mt32_p88.wav
A	audio/fate_s6/samples/mt32_p88_cycle.wav
A	audio/fate_s6/samples/mt32_p88_cycle_x2.wav
A	audio/fate_s6/samples/mt32_p88_low.wav
A	audio/fate_s6/samples/mt32_p88_x2.wav
A	audio/fate_s6/sound_117.mml
A	audio/fate_s6/sound_141.mml
A	audio/fate_s6/sound_150.mml
A	audio/fate_s6/sound_153.mml
A	audio/fate_s6/sound_154.mml
A	audio/fate_s6/sound_17.mml
A	audio/fate_s6/sound_172.mml
A	audio/fate_s6/sound_18.mml
A	audio/fate_s6/sound_183.mml
A	audio/fate_s6/sound_185.mml
A	audio/fate_s6/sound_190.mml
A	audio/fate_s6/sound_192.mml
A	audio/fate_s6/sound_201.mml
A	audio/fate_s6/sound_202.mml
A	audio/fate_s6/sound_207.mml
A	audio/fate_s6/sound_78.mml
A	audio/fate_s6/sound_81.mml
A	audio/fate_s6/sound_83.mml
A	audio/fate_s6/sound_91.mml
A	audio/m24ra/catalog.json
A	audio/m24ra/m24ra.terrificaudio
A	audio/m24ra/m24ra_async_layer_transition.mml
A	audio/m24ra/terrific_audio_driver_m24ra.patch
A	audio/m24rb/catalog.json
A	audio/m24rb/terrific_audio_driver_m24rb_content.patch
A	audio/monkey_v5/monkey154_church_bank.json
M	docs/ARCHITECTURE.md
M	docs/AUDIO.md
A	docs/INDEXED_SURFACE_PHASE0_BASELINE.md
A	docs/M23A_REPORT.md
A	docs/M23B_REPORT.md
A	docs/M23C_REPORT.md
A	docs/M24RA_REPORT.md
A	docs/M24RB1_REPORT.md
A	docs/M24RB2_REPORT.md
A	docs/M24RB_REPORT.md
A	docs/M25A_REPORT.md
A	docs/M25_AUTHENTIC_ONE_BLOCKER_REPORT.md
A	docs/M25_GET_ACTOR_FACING_REPORT.md
A	docs/M25_GET_ACTOR_WALKBOX_REPORT.md
A	docs/M25_GET_DIST_REPORT.md
A	docs/M25_MATRIX_SET_BOX_FLAGS_REPORT.md
A	docs/M25_MESSAGE_TALK_REPORT.md
A	docs/M25_MOVEMENT_PREFLIGHT_REPORT.md
A	docs/M25_PRINT_PREFLIGHT_REPORT.md
A	docs/M25_PRODUCTION_FRAME_LOOP_REPORT.md
A	docs/M25_PUT_ACTOR_REPORT.md
A	docs/M25_ROOM_LOCAL_LOOKUP_REPORT.md
A	docs/M25_SCHEDULER_RESUMPTION_REPORT.md
A	docs/M25_SET_STATE_REPORT.md
A	docs/M25_START_OBJECT_REPORT.md
A	docs/MUSIC_ARCHITECTURE.md
M	docs/NEXT_GATES.md
A	docs/PHASE6A_SNES_SURFACE_STORAGE_REPORT.md
A	docs/PHASE6B_SA1_BWRAM_STORAGE_REPORT.md
A	docs/PHASE6C_SA1_PRODUCTION_CARRIER_REPORT.md
A	docs/PHASE6D_MODE3_SURFACE_BACKEND_REPORT.md
A	docs/PHASE6E_SCUMM_ROOM49_BACKDROP_REPORT.md
A	docs/PHASE6F_SET_CAMERA_REPORT.md
A	docs/PHASE6GB_DEADLINE_ADJUDICATION.md
A	docs/PHASE6HA_GLOBAL_SCRIPT14_REPORT.md
A	docs/PHASE6HB_DENSE_GLOBAL_VARIABLES_REPORT.md
A	docs/PHASE6H_GLOBAL_VARIABLE_PREFLIGHT.md
A	docs/PHASE6I_GLOBAL_SCRIPT83_REPORT.md
A	docs/PHASE6J_WALK_ACTOR_TO_REPORT.md
A	docs/PHASE6K_SOUND_KLUDGE_FLUSH_REPORT.md
A	docs/PHASE6LA1B_GLOBAL_PRODUCER_PREFLIGHT.md
A	docs/PHASE6LA1C_SCRIPT75_ORACLE.md
A	docs/PHASE6LA1D_AUTHENTIC_START_REPORT.md
A	docs/PHASE6LA1D_DYNAMIC_CLOSURE_PREFLIGHT.md
A	docs/PHASE6LA1D_SENTENCE_CONTINUATION_REPORT.md
A	docs/PHASE6LA1_PRODUCER_CHAIN_PREFLIGHT.md
A	docs/PHASE6LA_SOUND82_PREFLIGHT.md
A	docs/PHASE6L_ACCEPTANCE.md
M	docs/SCUMM_V5.md
A	docs/SNES_MODE3_SURFACE_ABI.md
A	docs/attachments/PHASE6L_PRELIMINARY_LOAD_ROOM_WITH_EGO.patch
A	examples/profiles/m25a_nested_conformance.json
A	examples/profiles/qtma_music_conformance.json
A	examples/profiles/qtma_music_mov_runtime_conformance.json
A	examples/profiles/qtma_music_runtime_conformance.json
A	examples/profiles/qtma_music_time_runtime_conformance.json
M	examples/profiles/templates/fate_of_atlantis_demo.json
M	examples/profiles/templates/monkey1_ultimate_talkie.json
A	examples/resources/music/fate_s6_build_graph.json
A	examples/resources/music/fate_s6_compiled.json
A	examples/resources/music/monkey_v5_build_graph.json
A	examples/resources/music/monkey_v5_compiled.json
A	examples/resources/music/qtma_m10_bank.json
A	examples/resources/music/qtma_m10_build_graph.json
A	examples/resources/music/qtma_m10_compiled.json
A	examples/resources/music/qtma_m13_build_graph.json
A	examples/resources/music/qtma_m13_compiled.json
A	examples/resources/music/qtma_m13_movie.hex
A	examples/resources/music/qtma_m14_build_graph.json
A	examples/resources/music/qtma_m14_compiled.json
A	examples/resources/music/qtma_m14_movie_600.hex
A	examples/resources/music/qtma_m2_fixture.hex
A	examples/resources/music/qtma_m2_trace.json
A	examples/resources/music/qtma_m3_reference.json
A	examples/resources/scumm_v5/c29_actor_from_pos.scrp
A	examples/resources/scumm_v5/c2_m21_fate_room49_hook14.scrp
A	examples/resources/scumm_v5/c2_m22_fate_room49_no_hook8.scrp
A	examples/resources/scumm_v5/c2_m22_fate_room49_room63_hook8.scrp
A	examples/resources/scumm_v5/c2_m22_hook8_lifetime.scrp
A	examples/resources/scumm_v5/c2_m22_load_music.scrp
A	examples/resources/scumm_v5/c2_m23a_auth_room49.scrp
A	examples/resources/scumm_v5/c2_m23a_auth_room63.scrp
A	examples/resources/scumm_v5/c2_m23a_lifecycle.scrp
A	examples/resources/scumm_v5/c2_m23c_if_class.scrp
A	examples/resources/scumm_v5/c2_m23c_if_class_malformed.scrp
A	examples/resources/scumm_v5/c30_find_object.scrp
A	examples/resources/scumm_v5/c31_put_actor_in_room.scrp
A	examples/resources/scumm_v5/c32_put_actor_at_object.scrp
A	examples/resources/scumm_v5/fate_m23b_pre_thera.json
A	examples/resources/scumm_v5/fate_m23b_pre_thera_negative.json
A	examples/resources/scumm_v5/fate_m23c_pre_thera.json
A	examples/resources/scumm_v5/m19_monkey_music.scrp
A	examples/resources/scumm_v5/m20_load_music.scrp
A	examples/resources/scumm_v5/m20_save_music.scrp
A	examples/resources/scumm_v5/m20_start_music.scrp
A	examples/resources/scumm_v5/m20_stop_save_music.scrp
A	examples/resources/scumm_v5/matrix_invalid.scrp
A	examples/resources/scumm_v5/matrix_missing.scrp
A	examples/resources/scumm_v5/matrix_set_box_flags.scrp
A	examples/resources/scumm_v5/matrix_subop2.scrp
A	examples/resources/scumm_v5/matrix_subop3.scrp
A	examples/resources/scumm_v5/matrix_subop4.scrp
A	examples/resources/scumm_v5/matrix_unknown.scrp
A	labs/sa1_bwram/generated/alias-tests.inc.pasm
A	labs/sa1_bwram/generated/palette.cgram
A	labs/sa1_bwram/generated/surface-first.index8
A	labs/sa1_bwram/generated/surface-second.index8
A	labs/sa1_bwram/generated/tilemap.bin
A	labs/sa1_bwram/generated/tiles-first.8bpp
A	labs/sa1_bwram/generated/tiles-second.8bpp
A	labs/sa1_bwram/main.pasm
A	labs/snes_surface/generated/palette.cgram
A	labs/snes_surface/generated/tilemap.bin
A	labs/snes_surface/generated/tiles-first.8bpp
A	labs/snes_surface/generated/tiles-second.8bpp
A	labs/snes_surface/main.pasm
A	runtime/snes/carriers.json
A	runtime/snes/carriers/sa1_bwram_layout.json
M	runtime/snes/engine/host.pasm
A	runtime/snes/engines/m24ra_conformance.pasm
A	runtime/snes/engines/m24rb_conformance.pasm
A	runtime/snes/engines/mode3_surface_conformance.pasm
A	runtime/snes/engines/qtma_conformance.pasm
M	runtime/snes/engines/scumm_v5.pasm
M	runtime/snes/engines/scumm_v5_active.pasm
A	runtime/snes/engines/scumm_v5_camera_far.pasm
A	runtime/snes/engines/scumm_v5_m24rb_far.pasm
A	runtime/snes/engines/scumm_v5_matrix_far.pasm
A	runtime/snes/engines/scumm_v5_visual.pasm
M	runtime/snes/kernel/frame.pasm
M	runtime/snes/kernel/hardware.pasm
M	runtime/snes/kernel/memory.pasm
M	runtime/snes/main.pasm
M	runtime/snes/services/audio.pasm
A	runtime/snes/services/music_lifecycle.pasm
M	runtime/snes/services/storage.pasm
M	runtime/snes/services/video.pasm
A	runtime/snes/services/video_k1_far.pasm
A	runtime/snes/services/video_mode3.pasm
A	runtime/snes/services/video_overlay_bg2.pasm
A	runtime/snes/services/video_overlay_surface.pasm
A	runtime/snes/services/video_surface.pasm
A	runtime/snes/video_backends.json
A	runtime/snes/video_backends/bg2_index4_layout.json
A	runtime/snes/video_backends/mode3_surface_layout.json
A	runtime/snes/video_overlays.json
A	scummvm.ini
A	session_checkpoint.md
M	src/same/abi.py
M	src/same/engines/agi/engine.py
M	src/same/engines/scumm_v5/__init__.py
M	src/same/engines/scumm_v5/audio.py
A	src/same/engines/scumm_v5/cooked_room.py
A	src/same/engines/scumm_v5/costume.py
A	src/same/engines/scumm_v5/embedded_audio.py
M	src/same/engines/scumm_v5/engine.py
A	src/same/engines/scumm_v5/font.py
M	src/same/engines/scumm_v5/resources.py
M	src/same/engines/scumm_v5/room.py
A	src/same/engines/scumm_v5/room_visual.py
M	src/same/engines/scumm_v5/video.py
A	src/same/music/__init__.py
A	src/same/music/audit.py
A	src/same/music/backends/__init__.py
A	src/same/music/backends/tad_mml.py
A	src/same/music/build_graph.py
A	src/same/music/catalog.py
A	src/same/music/devices/__init__.py
A	src/same/music/devices/scumm_adlib.py
A	src/same/music/importers/__init__.py
A	src/same/music/importers/qtma.py
A	src/same/music/importers/qtma_mov.py
A	src/same/music/importers/scumm_imuse.py
A	src/same/music/instruments.py
A	src/same/music/lifecycle.py
A	src/same/music/model.py
A	src/same/music/playback.py
A	src/same/music/profile_build.py
A	src/same/music/realize.py
A	src/same/music/reference.py
A	src/same/music/segmented.py
A	src/same/music/timing.py
M	src/same/services.py
A	src/same/snes_carrier.py
A	src/same/snes_surface.py
A	src/same/snes_video_backend.py
A	src/same/snes_video_overlay.py
M	src/same/video.py
M	tests/test_agi_engine.py
M	tests/test_engine_host.py
A	tests/test_fate_adlib154_conversion.py
A	tests/test_fate_audition_pitch.py
A	tests/test_fate_tad_conversion.py
A	tests/test_fate_tad_layout.py
A	tests/test_m24ra_tad_transition.py
A	tests/test_m24rb_composite.py
A	tests/test_m25a_validator.py
A	tests/test_music_architecture.py
A	tests/test_music_audit.py
A	tests/test_music_build_graph.py
A	tests/test_music_catalog.py
A	tests/test_music_checkpoint.py
A	tests/test_music_graph_adapters.py
A	tests/test_music_importers.py
A	tests/test_music_lifecycle.py
A	tests/test_music_playback.py
A	tests/test_music_segmented.py
A	tests/test_music_tad_backend.py
A	tests/test_music_timing.py
A	tests/test_qtma_mov.py
A	tests/test_sa1_bwram_storage.py
A	tests/test_scumm_phase6ha.py
A	tests/test_scumm_phase6hb.py
A	tests/test_scumm_phase6i.py
A	tests/test_scumm_phase6j.py
A	tests/test_scumm_phase6k.py
M	tests/test_scumm_v5_adapters.py
M	tests/test_scumm_v5_audio_save.py
A	tests/test_scumm_v5_cooked_room.py
A	tests/test_scumm_v5_costume.py
A	tests/test_scumm_v5_embedded_audio.py
M	tests/test_scumm_v5_engine.py
A	tests/test_scumm_v5_font.py
M	tests/test_scumm_v5_room.py
A	tests/test_scumm_v5_room_visual.py
M	tests/test_scumm_v5_video.py
A	tests/test_snes_carrier.py
A	tests/test_snes_surface.py
A	tests/test_snes_video_backend.py
A	tests/test_snes_video_overlay.py
M	tests/test_video.py
A	tools/audit_snes_carrier_map.py
M	tools/audit_snes_rom.py
A	tools/build_fate_adlib_samples.py
A	tools/build_fate_loop_safe_samples.py
A	tools/build_fate_m24rb_composite.py
A	tools/build_fate_sound80_m22_sections.py
A	tools/build_fate_sound80_routes.py
A	tools/build_m22_tad_toolchain.py
A	tools/build_m23a_lifecycle_rooms.py
A	tools/build_m24ra_fixture.py
A	tools/build_m24ra_tad_toolchain.py
A	tools/build_m24rb_tad_toolchain.py
A	tools/build_m25a_validator_room.py
A	tools/build_monkey_v5_tad.py
A	tools/build_profile_music_rom.py
A	tools/build_qtma_music_graph.py
A	tools/build_sa1_bwram_proof.py
A	tools/build_scumm_room_visual_fixture.py
A	tools/build_scumm_v5_music_graph.py
M	tools/build_snes.ps1
M	tools/build_snes.sh
A	tools/build_snes_surface_proof.py
A	tools/capture_fate_instrument_auditions.py
A	tools/capture_fate_m21_auditions.py
A	tools/capture_fate_m22_auditions.py
A	tools/compare_scumm_set_camera_traces.py
A	tools/compare_snes_carrier_traces.py
A	tools/convert_fate_adlib154_to_tad_mml.py
A	tools/convert_fate_sound_to_tad_mml.py
A	tools/cook_scumm_v5_rooms.py
A	tools/extract_fate_adlib_patches.py
A	tools/fate_audition_pitch.py
A	tools/finalize_fate_adlib_auditions.py
A	tools/finalize_fate_adlib_oracle.py
M	tools/finalize_snes_rom.py
M	tools/generate_engine_fixtures.py
A	tools/generate_fate_tad_layout.py
A	tools/generate_fate_tad_tone.py
A	tools/generate_music_catalog.py
A	tools/generate_music_sections.py
A	tools/generate_snes_carrier.py
A	tools/generate_snes_cooked_rooms.py
M	tools/generate_snes_engine_selection.py
A	tools/generate_snes_room_visuals.py
A	tools/generate_snes_save_identity.py
A	tools/generate_snes_scumm_charset.py
A	tools/generate_snes_scumm_variables.py
A	tools/generate_snes_video_backend.py
A	tools/generate_snes_video_overlay.py
A	tools/inspect_fate_m23a_rooms.py
M	tools/lint_poppy.py
A	tools/measure_phase6gb_deadline_nexen.py
A	tools/music_graph_adapters.py
A	tools/postlink_m22_tad_sections.py
A	tools/postlink_m24rb_tad.py
A	tools/render_fate_source_reference.py
A	tools/report_snes_layout.py
A	tools/scummvm_fate154_adlib_auditions.patch
A	tools/scummvm_fate154_adlib_oracle.patch
A	tools/trace_fate_room42_graph.py
A	tools/validate_m24ra_nexen.py
A	tools/validate_mode3_surface_backend_nexen.py
A	tools/validate_monkey_v5_music.py
A	tools/validate_monkey_v5_tad_nexen.py
A	tools/validate_music_catalog_m6.py
A	tools/validate_music_lifecycle_nexen.py
A	tools/validate_qtma_music_runtime_nexen.py
A	tools/validate_sa1_bwram_proof_nexen.py
A	tools/validate_sa1_carrier_persistence_nexen.py
A	tools/validate_scumm_authentic_start.py
A	tools/validate_scumm_c29_nexen.py
A	tools/validate_scumm_c30_nexen.py
A	tools/validate_scumm_c31_nexen.py
A	tools/validate_scumm_c32_nexen.py
M	tools/validate_scumm_core_nexen.py
A	tools/validate_scumm_get_actor_facing_authentic_nexen.py
A	tools/validate_scumm_get_actor_facing_host.py
A	tools/validate_scumm_get_actor_facing_nexen.py
A	tools/validate_scumm_get_actor_walkbox_authentic_nexen.py
A	tools/validate_scumm_get_actor_walkbox_host.py
A	tools/validate_scumm_get_actor_walkbox_nexen.py
A	tools/validate_scumm_get_dist_nexen.py
A	tools/validate_scumm_m19_monkey_music_nexen.py
A	tools/validate_scumm_m20_save_nexen.py
A	tools/validate_scumm_m21_fate_route_nexen.py
A	tools/validate_scumm_m22_fate_hook8_nexen.py
A	tools/validate_scumm_m22_lifetime_nexen.py
A	tools/validate_scumm_m22_save_nexen.py
A	tools/validate_scumm_m23a_host.py
A	tools/validate_scumm_m23a_rooms_nexen.py
A	tools/validate_scumm_m23b_host.py
A	tools/validate_scumm_m23b_nexen.py
A	tools/validate_scumm_m23c_host.py
A	tools/validate_scumm_m23c_if_class_nexen.py
A	tools/validate_scumm_m23c_nexen.py
A	tools/validate_scumm_m24rb_host.py
A	tools/validate_scumm_m24rb_integrated_nexen.py
A	tools/validate_scumm_m24rb_nexen.py
A	tools/validate_scumm_m25_authentic_next_nexen.py
A	tools/validate_scumm_m25_put_actor_host.py
A	tools/validate_scumm_m25_sentence_movement_nexen.py
A	tools/validate_scumm_m25a_nested_nexen.py
A	tools/validate_scumm_matrix_nexen.py
A	tools/validate_scumm_message_malformed_nexen.py
A	tools/validate_scumm_message_talk_nexen.py
A	tools/validate_scumm_message_wait_nexen.py
A	tools/validate_scumm_phase6ha_nexen.py
A	tools/validate_scumm_phase6hb_nexen.py
A	tools/validate_scumm_phase6i_nexen.py
A	tools/validate_scumm_phase6j_nexen.py
A	tools/validate_scumm_phase6k_nexen.py
A	tools/validate_scumm_phase6l_nexen.py
A	tools/validate_scumm_put_actor_nexen.py
A	tools/validate_scumm_room49_crate_fixture_nexen.py
A	tools/validate_scumm_room49_mode3_nexen.py
A	tools/validate_scumm_room63_lscr202_nexen.py
A	tools/validate_scumm_room_local_lookup_nexen.py
M	tools/validate_scumm_s5_binding.py
M	tools/validate_scumm_s6_fate_preflight.py
A	tools/validate_scumm_s6_tad_nexen.py
A	tools/validate_scumm_scheduler_authentic_nexen.py
A	tools/validate_scumm_scheduler_nexen.py
A	tools/validate_scumm_segmented_talk_nexen.py
A	tools/validate_scumm_set_camera_mode3_nexen.py
A	tools/validate_scumm_set_camera_nexen.py
A	tools/validate_scumm_set_state_nexen.py
A	tools/validate_scumm_start_object_nexen.py
A	tools/validate_scumm_startup42_nexen.py
A	tools/validate_snes_surface_proof_nexen.py
98072 2344
```

## Publication inventory

Excluded and still present as untracked:
- `ATLANTIS.zip` (full-game source corpus; not uploaded)
- `SAME_Indexed_Surface_and_SNES_Presentation_Implementation_Spec.docx`
- `SAME_Surface_Abstraction_Proposal (1).docx`

Included commit contents require review before publication:
- source/runtime assembly and Python engine code;
- source-backed SCUMM room/script fixtures and cooked-room tooling;
- generated source-derived audio/compiler metadata and MML/BRR/WAV support files;
- validator/debug scripts and reports;
- ROM/layout/compiler configuration;
- project documentation;
- `scummvm.ini`.
Build outputs (`.sfc`, `.mss`, maps/listings and run reports) were not part of the commit unless represented by tracked source/report files. No raw ATLANTIS archive was included.

## Technical evidence

- Current handoff: `session_checkpoint.md`.
- Latest compatible ROM: `build/same-startup42-hoist-room82.sfc`; SHA-256:
  `d79dbe12a793389baa4502087e115da06322005c48d2d629d353e6e6e3aabde3`.
- ROM audit: `python3 tools/audit_snes_rom.py build/same-startup42-hoist-room82.sfc` => PASS; LoROM 1 MiB, reset `$8000`, NMI `$80DE`, IRQ `$8109`; bank 0 end `$F558`, 2663 bytes free before header.
- Focused unit test: `PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q` => 116 passed.
- Formatting: `git diff --check` => PASS.
- Build command used:
  `SAME_SNES_ENGINE=scumm_v5 SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23C=1 SAME_BUILD_M24RB=1 SAME_BUILD_SCUMM_M25A_VALIDATOR=1 SAME_BUILD_SCUMM_SCENARIO_FIXTURE=1 SAME_BUILD_SCUMM_M25_MOVEMENT=1 SAME_M25A_VALIDATOR_CASE=startup42 SAME_FATE_DEMO_ARCHIVE=$PWD/ATLANTIS.zip SAME_TAD_PREBUILT_DIR=build/music-m8-fate SAME_BUILD_SCUMM_PHASE6L_A1D=1 SAME_SNES_OUTPUT=build/same-startup42-hoist-room82.sfc bash tools/build_snes.sh`
- Fresh checkpoint command:
  `PYTHONUNBUFFERED=1 PYTHONPATH=/home/chad/Mesen2/python python3 -u tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-startup42-hoist-room82.sfc --output build/hoist-room82-before2 --frames 880 --light --minimal-observation --port 44324 --pre-event-trace-start 99999 --save-state build/hoist-room82-before2.mss`
- Hoist command:
  `PYTHONUNBUFFERED=1 PYTHONPATH=/home/chad/Mesen2/python python3 -u tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-startup42-hoist-room82.sfc --output build/hoist-room82-run2 --load-state build/hoist-room82-before2.mss --frames 3200 --light --minimal-observation --port 44325 --sentence 8 500 497`
- Latest hoist report: `build/hoist-room82-run2/report.json`. It records sentence publication/consumption, error 0, but the run ended with script 2/program 210 still at PC 0 in room 42; room 82 transition was not observed.
- Scenario manifests: `build/m25a-validator/startup42/manifest.json` and `build/m25a-validator/startup42/room42/manifest.json`. These are generated, not committed.
- Resume-state identities: requested `startup42-fullcone2-hoist.mss` belongs to ROM `1dae97ccbaf4aa9432312ab0357c6ce1fa72c04c22225127c9d351a17de0e98c`, which is unavailable. Do not load it with another ROM. Compatible older diagnostic pair: `build/current-hoist.mss` + `build/same-startup42-excd-suit-fullcone.sfc`, ROM `cf87e214...`. Fresh checkpoint above matches only the fresh `d79dbe...` ROM.
- Tool/runtime identities: Poppy DLL SHA `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`; Nexen wrapper `/home/chad/NexenTrace/run/nexen-wrapper`; Mesen Python tooling `/home/chad/Mesen2/python`.

## Priority code review: headless C23/Talk/waitForMessage

Primary production excerpt in `runtime/snes/engines/scumm_v5.pasm`:

```asm
ScummV5_Op_Print__text_done:
    lda.l SAME_SCUMM_C23_RAW_INDEX
    sta.l SAME_SCUMM_C23_LAST_LENGTH
    .if SAME_BUILD_SCUMM_M23A
        lda.l SAME_SCUMM_C23_LAST_SLOT
        bne ScummV5_Op_Print__text_no_talk
        jsl ScummV5_Talk_Begin_Far
        ...
```

The earlier fixture-only acknowledgment was rejected during review and has now
been removed. Headless fixture builds use the same `ScummV5_Talk_Begin_Far`,
`Talk_FrameBegin_Far`, and `Talk_FrameEnd_Far` logical lifecycle as production;
presentation remains optional. Thus delivery/decode does not equal logical
completion, and `waitForMessage` retains its authored delay/ownership boundary.
The normal production talk lifecycle is unchanged.

Relevant tests:
- `test_headless_fixture_retains_logical_message_lifetime_without_presentation` checks that the fixture no longer clears C23/talk state and uses the existing Talk lifecycle.
- `test_wait_for_message_retries_then_resumes_after_published_completion` verifies wait blocks until completion/clear and then resumes.
- `tools/validate_scumm_message_wait_nexen.py` proves fresh power-on, parent/child descriptors, 64-jiffy completion, resume, and `debugger_writes=0`.

## What the hoist run proved vs did not prove

Observed dynamically on the pre-correction hoist ROM: fresh boot reached room
42 with error 0; sentence `(8,500,497)` was published and consumed into C20;
no room-0 request or SCUMM error was reported; actor-2 source placement and
prior movement-width fix remain present. The corrected startup42 ROM builds
and audits cleanly but has not yet had a replacement hoist observation.

Not yet proven dynamically on the fresh room-82 image: LSCR 207 completion, `setState(500,0)`, bit 444, room 82 installation, destination ENCD/EXCD, or downstream room-82 script lifecycle. The latest report’s script-2 slot remaining at PC 0 is the next investigation point.

This packet is source-only as requested and gameplay is paused. The corrected
ROM is `build/same-startup42-hoist-room82-talklifecycle.sfc`, SHA-256
`821e58555d1c2cc979bb781a93f269908f083bbd62dcffe68a20e98d1f956ec6`.
