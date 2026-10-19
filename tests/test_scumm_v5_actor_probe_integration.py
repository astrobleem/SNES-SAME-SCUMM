from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from same.engines.scumm_v5.native_residency import (
    NativeProgramDirectory, canonical_unit_identity,
)
from same.engines.scumm_v5.program_storage import build_program_storage
from tools.actor_probe_program import ProbeConfig, build_probe
from tools.generate_snes_cooked_rooms import apply_synthetic_actor_probe
from tools.validate_scumm_actor_visual_probe_nexen import (
    decode_pose_observation, direction_index_for_facing, pose_is_presented,
    same_room_costume_source, actor_bounds_on_surface,
    read_surface_packets_pending,
)


class ActorProbeIntegrationTests(unittest.TestCase):
    def test_live_actor_damage_restores_checked_room_underlay_not_empty_rom_directory(self) -> None:
        root = Path(__file__).resolve().parents[1]
        surface = (root / "runtime/snes/services/video_surface.pasm").read_text()
        controller = (root / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        live = (root / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        restore = surface.split("Same_VideoSurface_RestoreRect__height_ok:", 1)[1].split(
            "; LoadRowTablePointer uses byte loads", 1
        )[0]
        self.assertIn("Same_VideoSurface_RestoreActorUnderlay_Far", restore)
        self.assertIn("SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER", restore)
        self.assertIn("Same_VideoSurface_CaptureActorUnderlay_Far", controller)
        self.assertLess(
            controller.index("Same_VideoSurface_CaptureActorUnderlay_Far"),
            controller.index("Same_VideoSurface_BlitCheckedOpaqueRun_Far"),
        )
        self.assertIn("SAME_VIDEO_ACTOR_UNDERLAY_HEADER_SIZE", surface)
        self.assertIn("SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE+1", surface)
        self.assertIn("SAME_VIDEO_ACTOR_UNDERLAY_MAGIC", surface)
        self.assertIn("sta SAME_SCUMM_LIVE_ROOM_STAGING_OFFSET,y", surface)
        self.assertIn("Same_VideoSurface_InvalidateActorUnderlay_Far", live)
        self.assertIn("SAME_VIDEO_SURFACE_ROOM_GENERATION", surface)
        self.assertIn("SAME_SCUMM_ACTOR_POSE_RENDER_LEFT", surface)
        self.assertIn("SCUMM_ERR_RESOURCE", surface)

    def test_underlay_offsets_keep_the_full_16_bit_live_record_length(self) -> None:
        root = Path(__file__).resolve().parents[1]
        surface = (root / "runtime/snes/services/video_surface.pasm").read_text()
        for label, end_label in (
                ("Same_VideoSurface_CaptureActorUnderlay__room_valid:",
                 "Same_VideoSurface_CaptureActorUnderlay__record_length_ok:"),
                ("Same_VideoSurface_RestoreActorUnderlay_Far:",
                 "Same_VideoSurface_RestoreActorUnderlay__record_length_ok:"),
                ("Same_VideoSurface_InvalidateActorUnderlay_Far:",
                 "Same_VideoSurface_InvalidateActorUnderlay__done:")):
            with self.subTest(active_length_source=label):
                section = surface.split(label, 1)[1].split(end_label, 1)[0]
                self.assertIn("lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$30", section)
                self.assertNotIn("lda.l SAME_SCUMM_LIVE_ROOM_CONTROL+$3E", section)
        for label, end_label, length_operand in (
                ("Same_VideoSurface_RestoreActorUnderlay__header_in_range:",
                 "Same_VideoSurface_RestoreActorUnderlay__magic_ok:",
                 "lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH"),
                ("Same_VideoSurface_RestoreActorUnderlay__stale:",
                 "Same_VideoSurface_RestoreActorUnderlay__empty:",
                 "lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH"),
                ("Same_VideoSurface_InvalidateActorUnderlay_Far:",
                 "Same_VideoSurface_InvalidateActorUnderlay__done:",
                 "lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$30")):
            with self.subTest(label=label):
                section = surface.split(label, 1)[1].split(end_label, 1)[0]
                positions = []
                start = 0
                while True:
                    try:
                        position = section.index(length_operand, start)
                    except ValueError:
                        break
                    positions.append(position)
                    start = position + len(length_operand)
                self.assertTrue(positions)
                for length_load in positions:
                    width16 = section.rfind(".a16", 0, length_load)
                    width8 = section.rfind(".a8", 0, length_load)
                    self.assertGreater(width16, width8)
                if label == "Same_VideoSurface_InvalidateActorUnderlay_Far:":
                    self.assertEqual(len(positions), 2)
                    self.assertIn("clc\n    adc #SAME_VIDEO_ACTOR_UNDERLAY_HEADER_SIZE",
                                  section[positions[0]:positions[0] + 128])
                    self.assertIn("tay", section[positions[1]:positions[1] + 128])
                else:
                    self.assertIn("tay", section[positions[-1]:positions[-1] + 128])

    def test_underlay_scratch_is_a_lifetime_alias_not_an_independent_wram_gap(self) -> None:
        root = Path(__file__).resolve().parents[1]
        memory = (root / "runtime/snes/kernel/memory.pasm").read_text()
        for alias, field in (
                ("SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH", "SAME_SCUMM_CONTROLLER_RESTORE_LOOP_W"),
                ("SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE", "SAME_SCUMM_CONTROLLER_RESTORE_LOOP_H"),
                ("SAME_VIDEO_ACTOR_UNDERLAY_AREA", "SAME_SCUMM_CONTROLLER_RESTORE_LOOP_DST"),
                ("SAME_VIDEO_ACTOR_UNDERLAY_ROW", "SAME_SCUMM_CONTROLLER_RESTORE_LOOP_SRC")):
            self.assertRegex(memory, rf"{alias}\s+= {field}")
        self.assertIn("SAME_VIDEO_ACTOR_UNDERLAY_COLUMN         = $7E5E8A", memory)
        self.assertIn("SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR  = $7E5E8E", memory)

    def test_pose_bounds_underlay_is_bounded_by_the_exact_live_record_tail(self) -> None:
        active_capacity = 6144
        header = 16
        record_size = 1354  # generic synthetic layout fixture, not runtime selection
        pose_width, pose_height = 37, 53
        required = record_size + header + pose_width * pose_height
        self.assertLessEqual(required, active_capacity)
        self.assertEqual(active_capacity - required, 2813)
        self.assertLessEqual(active_capacity - header - pose_width * pose_height,
                             active_capacity)
        too_large = active_capacity - header - pose_width * pose_height + 1
        self.assertGreater(too_large + header + pose_width * pose_height, active_capacity)

    def test_live_surface_fifo_ignores_stale_slots(self) -> None:
        class MemorySession:
            def __init__(self) -> None:
                self.fifo = bytearray(0x106)
                self.fifo[0:2] = (15).to_bytes(2, "little")
                self.fifo[2:4] = (1).to_bytes(2, "little")
                self.fifo[4:6] = (2).to_bytes(2, "little")
                self.fifo[6 + 15 * 0x10] = 2  # another service
                self.fifo[6 + 15 * 0x10 + 1] = 0x0C
                self.fifo[6] = 2  # packet wrapped to slot 0
                self.fifo[7] = 0x11

            def read_memory(self, _space, address, length):
                if address == 0x7E2000:
                    return bytes(self.fifo[:length])
                if address == 0x7E2100:
                    return bytes(self.fifo[6:6 + length])
                raise AssertionError(hex(address))

        session = MemorySession()
        self.assertFalse(read_surface_packets_pending(session))
        # A stale surface packet in an unused slot must not block readiness.
        session.fifo[6 + 1 * 0x10] = 1
        session.fifo[6 + 1 * 0x10 + 1] = 0x11
        self.assertFalse(read_surface_packets_pending(session))
        # Once the slot is included in count, it is live presentation work.
        session.fifo[4:6] = (3).to_bytes(2, "little")
        self.assertTrue(read_surface_packets_pending(session))

    def test_visual_observer_reads_pose_frame_not_palette_scratch(self) -> None:
        pose = bytearray(0x80)
        pose[0] = 2  # desired frame
        pose[2] = 7  # selected costume identity
        pose[3] = 3  # accepted frame
        pose[4] = 2  # accepted direction index
        pose[0x0A] = 7
        pose[0x0B] = 16  # phase-local palette-size alias
        decoded = decode_pose_observation(pose)
        self.assertEqual(decoded["desired_frame"], 2)
        self.assertEqual(decoded["accepted_frame"], 3)
        self.assertEqual(decoded["accepted_step"], 7)
        self.assertEqual(decoded["costume_id"], 7)
        self.assertEqual(decoded["palette_size"], 16)
        self.assertNotEqual(decoded["accepted_frame"], decoded["palette_size"])

    def test_animation_steps_keep_costume_source_while_pose_generation_advances(self) -> None:
        first = {
            "room_epoch": 4, "costume_id": 7,
            "pose_validation_generation": 12, "accepted_step": 1,
            "rom_sha256": "rom", "package_sha256": "package",
        }
        second = {
            **first, "pose_validation_generation": 13, "accepted_step": 2,
        }
        self.assertTrue(same_room_costume_source(first, second))
        for field, value in (
                ("room_epoch", 5), ("costume_id", 8),
                ("rom_sha256", "other-rom"),
                ("package_sha256", "other-package")):
            with self.subTest(field=field):
                self.assertFalse(same_room_costume_source(
                    first, {**second, field: value}))

    def test_visual_observer_converts_authored_facing_to_pose_direction(self) -> None:
        self.assertEqual(direction_index_for_facing(180), 2)
        self.assertEqual(direction_index_for_facing(90), 1)

    def test_visual_bounds_come_from_signed_checked_pose_and_foot_anchor(self) -> None:
        pose = bytearray(0x80)
        for offset, value in zip((0x4B, 0x4D, 0x4F, 0x51), (-9, -40, 10, 0)):
            pose[offset:offset + 2] = value.to_bytes(2, "little", signed=True)
        pose[0x6C:0x6E] = (160).to_bytes(2, "little", signed=True)
        pose[0x6E:0x70] = (136).to_bytes(2, "little", signed=True)
        # This is reserved state and has no native production writer.
        pose[0x63] = 0
        self.assertEqual(actor_bounds_on_surface(pose), (151, 96, 170, 136))

        pose[0x6C:0x6E] = (3).to_bytes(2, "little", signed=True)
        pose[0x6E:0x70] = (5).to_bytes(2, "little", signed=True)
        self.assertEqual(actor_bounds_on_surface(pose), (0, 0, 13, 5))

    def test_visual_observer_requires_production_mode3_commit_fence(self) -> None:
        pose = bytearray(0x80)
        pose[1] = 0  # successful RenderActor clears transient READY state
        pose[3] = 3
        pose[4] = direction_index_for_facing(180)
        pose[0x0A] = 0
        # The legacy render-bounds-valid byte is unused; semantic bounds are
        # derived from the checked signed pose descriptors instead.
        pose[0x63] = 0
        pose[0x6B] = 1
        pose[0x6C:0x6E] = (160).to_bytes(2, "little")
        pose[7:9] = (12).to_bytes(2, "little")
        pose[0x7D:0x7F] = (12).to_bytes(2, "little")
        args = {
            "render_valid": 1, "render_frame": 3, "render_step": 0,
            "render_generation": 12, "render_facing": 180,
            "next_generation": 8,
            "backend_pending_generation": 8,
            "backend_committed_generation": 8,
            "backend_pending_generation_hi": 0,
            "backend_committed_generation_hi": 0,
            "backend_state": 1, "surface_locked": 0,
            "pending_visual": 0, "presented_room": 4, "room": 4,
            "surface_packets_pending": False,
            "expected_frame": 3, "expected_facing": 180,
            "expected_x": 160,
        }
        self.assertTrue(pose_is_presented(pose, **args))
        # PRESENTED_GENERATION is deliberately absent from this contract: its
        # field has no production writer, so it cannot be an acknowledgement.
        self.assertFalse(pose_is_presented(
            pose, **{**args, "backend_committed_generation": 7}))
        self.assertFalse(pose_is_presented(pose, **{**args, "backend_state": 2}))
        self.assertFalse(pose_is_presented(pose, **{**args, "surface_locked": 1}))
        self.assertFalse(pose_is_presented(
            pose, **{**args, "surface_packets_pending": True}))
        self.assertFalse(pose_is_presented(pose, **{**args, "presented_room": 3}))
        self.assertFalse(pose_is_presented(pose, **{**args, "render_valid": 0}))
        self.assertFalse(pose_is_presented(pose, **{**args, "render_generation": 11}))

    def test_native_pose_publisher_honors_animate_actor_chore_and_stationary_steps(self) -> None:
        root = Path(__file__).resolve().parents[1]
        publisher = (root / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        publisher = publisher.split(
            "ScummV5_Controller_PublishActorVisual_Far:", 1
        )[1].split("ScummV5_Controller_PublishActorVisual__done:", 1)[0]
        self.assertIn(
            "SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION+SCUMM_V5_ACTOR_RENDER_ID", publisher
        )
        self.assertIn("SAME_SCUMM_C14_A_ANIMATION,x", publisher)
        self.assertIn("cmp #$F4", publisher)  # F4..FB are direction-only commands.
        self.assertIn("cmp #$FC", publisher)  # FC..FF select stand/stop.
        self.assertIn("SAME_SCUMM_ACTOR_POSE_LAST_FRAME", publisher)
        same_pose = publisher.split(
            "ScummV5_Controller_PublishActorVisual__same_pose_direction:", 1
        )[1].split("ScummV5_Controller_PublishActorVisual__advance_pose_step:", 1)[0]
        self.assertNotIn(
            "SAME_SCUMM_CONTROLLER_DESIRED_SELECT\n"
            "    beq ScummV5_Controller_PublishActorVisual__reset_pose_step",
            same_pose,
        )
        movement = publisher.split(
            "ScummV5_Controller_PublishActorVisual__pose_done:", 1
        )[1].split("ScummV5_Controller_PublishActorVisual__movement_step_active:", 1)[0]
        self.assertIn("SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION+SCUMM_V5_ACTOR_RENDER_ID", movement)
        self.assertIn("SAME_SCUMM_C14_A_ANIMATION,x", movement)
        self.assertIn("cmp #$F4", movement)
        self.assertIn("cmp #$FC", movement)
        self.assertIn("ScummV5_Controller_PublishActorVisual__store_sample", movement)

        engine = (root / "runtime/snes/engines/scumm_v5.pasm").read_text()
        animate = engine.split("ScummV5_Op_AnimateActor__store:", 1)[1].split(
            "ScummV5_Op_AnimateActor__operand_error:", 1
        )[0]
        self.assertIn("sta.l SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION,x", animate)
        memory = (root / "runtime/snes/kernel/memory.pasm").read_text()
        self.assertRegex(memory, r"SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION\s+= \$41E750")

    def test_span_page_validation_uses_its_byte_width_and_restores_a16(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "runtime/snes/engines/scumm_v5_controller_far.pasm").read_text()
        block = source.split("ScummV5_ActorPose_Ensure__span_count_ok:", 1)[1].split(
            "ScummV5_ActorPose_Ensure__span_range_no_wrap:", 1
        )[0]
        self.assertIn("SAME_SCUMM_ACTOR_SPAN_PAGE                  = SAME_SCUMM_ACTOR_POSE_STATE_BASE+$37",
                      (root / "runtime/snes/kernel/memory.pasm").read_text())
        self.assertIn("SAME_SCUMM_ACTOR_SPAN_LOCAL_OFFSET          = SAME_SCUMM_ACTOR_POSE_STATE_BASE+$38",
                      (root / "runtime/snes/kernel/memory.pasm").read_text())
        self.assertLess(block.index("sep #$20"), block.index("lda.l SAME_SCUMM_ACTOR_SPAN_PAGE"))
        self.assertLess(block.index(".a8"), block.index("cmp #SCUMM_V5_ACTOR_SPAN_BANK_COUNT"))
        self.assertLess(block.index("bcc ScummV5_ActorPose_Ensure__span_page_ok"),
                        block.index("ScummV5_ActorPose_Ensure__span_page_ok:"))
        self.assertLess(block.index("rep #$20"), block.index("lda.l SAME_SCUMM_ACTOR_SPAN_LOCAL_OFFSET"))

    def test_overlay_feeds_directory_bodies_pages_and_package_consistently(self) -> None:
        rows = []
        programs = []
        for kind, room, number, length in (
            ("GLOBAL", None, 1, 256),
            ("GLOBAL", None, 2, 64),
            ("ENCD", 4, 0, 32),
            ("EXCD", 4, 0, 32),
            ("LSCR", 4, 9, 48),
            ("OBCD", 4, 77, 64),
        ):
            identity = canonical_unit_identity(kind, room=room, number=number)
            body = bytes(((len(programs) + 1) & 0xff,)) * length
            sha = hashlib.sha256(body).hexdigest()
            rows.append({
                "identity": identity, "kind": kind, "room": room, "number": number,
                "length": length, "sha256": sha,
                "bundle": f"GlobalBundle({number})" if room is None else f"RoomBundle({room})",
                "dispatch": ({"object": number, "verb_entrypoints": [{"verb": 1, "offset": 4}]}
                             if kind == "OBCD" else {}),
                "source_provenance": {"body_pc_coordinate": "OBCD-relative" if kind == "OBCD"
                                      else "program-body-relative"},
            })
            programs.append({
                "unit_identity": identity, "program": body, "length": length,
                "executable": True, "kind_name": kind, "room": room, "number": number,
                "instruction_spans": [[pc, 1] for pc in range(length)], "opaque_ranges": [],
            })
        directory = NativeProgramDirectory.from_programs(rows)
        original_ids = {e["identity"]: e["program_unit_id"]
                        for e in directory.document["entries"]}
        object_before = next(p["program"] for p in programs if p["kind_name"] == "OBCD")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audit_path = root / "actor-probe-audit.json"
            updated, audit = apply_synthetic_actor_probe(directory, programs, audit_path)
            body_map = {p["unit_identity"]: p["program"] for p in programs}
            page_map = {p["unit_identity"]: {
                "instruction_spans": p["instruction_spans"],
                "opaque_ranges": p["opaque_ranges"],
            } for p in programs}
            storage = build_program_storage(updated.document, body_map, root / "storage",
                                            page_metadata=page_map)

            driver, _ = build_probe(ProbeConfig(room=4, costume=2, boot_script=1))
            boot_identity = "GlobalProgram(1)"
            boot = next(p for p in programs if p["unit_identity"] == boot_identity)
            self.assertEqual(len(driver), 118)
            self.assertEqual(boot["program"][:len(driver)], driver)
            self.assertEqual(len(boot["program"]), 256)
            self.assertEqual(boot["program"][len(driver):], b"\xa0" * (256-len(driver)))
            self.assertEqual(audit["kind"], "SYNTHETIC_GRAPHICS_DIAGNOSTIC")
            self.assertFalse(audit["production_release_eligible"])
            self.assertFalse(audit["gameplay_authentic"])
            self.assertEqual(len(audit["program"]["stage_records"]), 4)
            self.assertEqual({e["identity"]: e["program_unit_id"]
                              for e in updated.document["entries"]}, original_ids)
            self.assertEqual(next(p["program"] for p in programs if p["kind_name"] == "OBCD"),
                             object_before)
            self.assertEqual([len(p["program"]) for p in programs],
                             [256, 64, 32, 32, 48, 64])
            boot_record = next(r for r in storage["records"] if r["identity"] == boot_identity)
            packed = (root / "storage" / "scumm-program-bodies.bin").read_bytes()
            offset = boot_record["section_relative_offset"]
            self.assertEqual(packed[offset:offset + 256], boot["program"])
            self.assertEqual(boot_record["sha256"], hashlib.sha256(boot["program"]).hexdigest())
            self.assertEqual(storage["program_count"], len(programs))
            self.assertTrue(audit_path.is_file())


if __name__ == "__main__":
    unittest.main()
