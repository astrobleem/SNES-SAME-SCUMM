from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path

from same.engines.scumm_v5.live_room_resources import (
    HEADER, MAX_ACTIVE_BYTES, decode_live_room, encode_live_room,
)
from same.engines.scumm_v5.room_visual import decode_room_visual, encode_room_visual
from tools.validate_scumm_native_residency_nexen import live_room_ppu_generation_ready


class LiveRoomResourceTests(unittest.TestCase):
    def source_record(self) -> tuple[dict[str, object], list[dict[str, object]]]:
        units = [
            {"id": 3, "room": 4, "unit_identity": "RoomEntryProgram(4)"},
            {"id": 4, "room": 4, "unit_identity": "RoomExitProgram(4)"},
            {"id": 5, "room": 4, "unit_identity": "ObjectProgram(room=4,object=22)"},
            {"id": 6, "room": 4, "unit_identity": "RoomLocalProgram(room=4,local=9)"},
            {"id": 0, "room": None, "unit_identity": "GlobalProgram(1)"},
        ]
        record = {
            "room": 4, "raw": b"copyright-free-source-room",
            "walkbox_flags": b"\x00\x80",
            "walkbox_geometry": bytes(36),
            "box_routes": b"\x00\x01\xff\x00",
            "portals": bytes(2 * 2 * 7),
            "objects": struct.pack("<HhhhhB", 22, 10, 20, 30, 40, 1),
            "object_names": ((22, b"multi-verb"),),
            "object_walk": struct.pack("<HhhBhhB", 22, 10, 20, 2, 11, 21, 1),
            "object_programs": [{
                "id": 5, "unit_identity": "ObjectProgram(room=4,object=22)",
                "number": 22, "executable": True,
                "entrypoints": ((3, 7), (10, 12)),
            }],
            "executable_locals": [{"id": 6, "number": 9}],
            "entry": 3, "exit": 4,
        }
        return record, units

    def test_round_trip_keeps_carrier_and_verb_identities_distinct(self) -> None:
        record, units = self.source_record()
        raw = encode_live_room(record, program_units=units)
        live = decode_live_room(raw, expected_room=4)
        self.assertEqual(live.room, 4)
        self.assertEqual(live.box_count, 2)
        self.assertEqual(live.object_count, 1)
        self.assertEqual(live.verb_count, 2)
        self.assertEqual(live.local_count, 1)
        self.assertEqual(live.bundle_count, 4)
        self.assertEqual(live.entry_program_unit, 3)
        self.assertEqual(live.exit_program_unit, 4)
        verb_offset = live.offsets["verbs"]
        self.assertEqual(struct.unpack_from("<HHHH", raw, verb_offset), (22, 3, 7, 5))
        self.assertEqual(struct.unpack_from("<HHHH", raw, verb_offset + 8), (22, 10, 12, 5))
        self.assertEqual(raw[0:8], b"SC5LIVE\0")
        self.assertLessEqual(len(raw), MAX_ACTIVE_BYTES)
        self.assertEqual(live.source_room_sha256, hashlib.sha256(record["raw"]).hexdigest())

    def test_decoder_rejects_noncanonical_offsets_and_trailing_payload(self) -> None:
        record, units = self.source_record()
        raw = bytearray(encode_live_room(record, program_units=units))
        # First table offset starts immediately after the fixed header.
        struct.pack_into("<H", raw, 28, HEADER.size + 1)
        with self.assertRaisesRegex(Exception, "out of bounds or noncanonical"):
            decode_live_room(bytes(raw))
        raw = encode_live_room(record, program_units=units) + b"x"
        with self.assertRaisesRegex(Exception, "length exceeds"):
            decode_live_room(raw)

    def test_visual_source_record_is_checked_before_storage_projection(self) -> None:
        identities = [hashlib.sha256(name.encode()).hexdigest()
                      for name in ("archive", "index", "data", "room")]
        palette = bytes(value for i in range(256) for value in (i, 255 - i, i // 2))
        pixels = bytes((x + y) & 0xFF for y in range(224) for x in range(256))
        raw = encode_room_visual(
            room=4, width=256, height=224, pitch=256,
            palette=palette, pixels=pixels,
            archive_sha256=identities[0], index_sha256=identities[1],
            data_sha256=identities[2], room_sha256=identities[3],
        )
        decoded = decode_room_visual(raw, expected_room=4)
        self.assertEqual(decoded.visible_row(3), pixels[3 * 256:4 * 256])
        damaged = bytearray(raw)
        damaged[-1] ^= 1
        with self.assertRaisesRegex(Exception, "decoded payload identity"):
            decode_room_visual(bytes(damaged), expected_room=4)

    def test_ppu_sampling_accepts_superseded_generation_ticket_for_exact_content_check(self) -> None:
        class Session:
            def read_memory(self, _kind: str, address: int, length: int) -> bytes:
                control = bytearray(10)
                control[0:2] = (3).to_bytes(2, "little")
                control[3] = 1
                control[4] = 0
                control[8:10] = b"\x00\x00"
                values = {0x401010: bytes(control)}
                return values[address][:length]

        # The caller must still compare actual VRAM/CGRAM with SC5VIS. This
        # only says presentation is idle; an older ticket may have been
        # superseded by a later room generation before the sampler observed it.
        self.assertTrue(live_room_ppu_generation_ready(Session(), 1))

    def test_active_visual_validity_is_not_the_incoming_transfer_validity(self) -> None:
        root = Path(__file__).resolve().parents[1]
        programs = (root / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        live_room = (root / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        video = (root / "runtime/snes/services/video_surface.pasm").read_text()

        self.assertIn(
            "SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID = SAME_SCUMM_LIVE_ROOM_CONTROL+$21",
            programs,
        )
        self.assertIn(
            "SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED = SAME_SCUMM_LIVE_ROOM_CONTROL+$22",
            programs,
        )
        reset = programs.split("ScummV5_MsuProgram_Reset_Far:", 1)[1].split(
            "ScummV5_MsuProgram_Reset_Far__failed:", 1,
        )[0]
        self.assertIn("sta.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID", reset)
        self.assertIn("sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED", reset)
        self.assertIn("sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1F", reset)
        request = programs.split("ScummV5_MsuRoom_Request_Far:", 1)[1].split(
            "ScummV5_MsuRoom_Request_Far__coalesced:", 1,
        )[0]
        self.assertNotIn("SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID", request)
        self.assertIn("sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED", request)

        commit = (root / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        release = commit.split(
            "ScummV5_M24RB_Far_CommitRoom__old_bundle_released:", 1,
        )[0].split("; Preserve the outgoing room bundle through EXCD", 1)[1]
        self.assertIn("lda.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED", release)
        self.assertIn("bne ScummV5_M24RB_Far_CommitRoom__old_bundle_released", release)
        released = commit.split(
            "ScummV5_M24RB_Far_CommitRoom__old_bundle_released:", 1,
        )[1].split(".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES", 1)[1]
        self.assertIn("sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED", released)

        publish = live_room.split("ScummV5_LiveRoom_PublishVisual_Far:", 1)[1].split(
            "ScummV5_LiveRoom_PublishVisual_Far__bad:", 1,
        )[0]
        self.assertIn("sta.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID", publish)
        compose = video.split("Same_VideoSurface_ComposeRoom_Far:", 1)[1].split(
            "Same_VideoSurface_ComposeRoom__presented:", 1,
        )[0]
        self.assertIn("lda.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID", compose)

    def test_video_wait_holds_scheduler_until_room_commit_can_resume(self) -> None:
        root = Path(__file__).resolve().parents[1]
        m24rb = (root / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        preflight = m24rb.split("ScummV5_M24RB_Far_CommitRoom__resource_room:", 1)[1].split(
            "ScummV5_M24RB_Far_CommitRoom__first_entry:", 1,
        )[0]
        self.assertIn("SCUMM_LIVE_ROOM_STAGE_PREFLIGHT_READY", preflight)
        self.assertIn("Same_VideoSurface_CanWrite_Far", preflight)
        self.assertLess(
            m24rb.index("Same_VideoSurface_CanWrite_Far", m24rb.index(
                "ScummV5_M24RB_Far_CommitRoom__resource_room:")),
            m24rb.index("ScummV5_M24RB_Far_CommitRoom__first_entry:"),
        )
        wait = m24rb.split("ScummV5_M24RB_Far_CommitRoom__live_visual_wait:", 1)[1].split(
            "ScummV5_M24RB_Far_CommitRoom__first_entry:", 1,
        )[0]
        self.assertIn("lda #$03", wait)
        self.assertIn("sta.l SAME_SCUMM_M23A_PHASE", wait)
        self.assertIn("sta.l SAME_SCUMM_M23A_HOLD", wait)
        resume = m24rb.split("ScummV5_M24RB_Far_ResumeVisualCommit:", 1)[1].split(
            "ScummV5_M24RB_Far_ResumeVisualCommit_FarEntry:", 1,
        )[0]
        self.assertIn("jsl Same_VideoSurface_CanWrite_Far", resume)
        self.assertIn("jsr ScummV5_M24RB_Far_CommitRoom", resume)
        engine = (root / "runtime/snes/engines/scumm_v5.pasm").read_text()
        self.assertIn("jsl ScummV5_M24RB_Far_ResumeVisualCommit_FarEntry", engine)
        self.assertIn("SCUMM_LIVE_ROOM_STAGE_PREFLIGHT_READY", engine)
        load = m24rb.split(
            "ScummV5_M24RB_Far_CommitRoom__load_incoming_bundle:", 1,
        )[1].split("ScummV5_M24RB_Far_CommitRoom__new_bundle_loaded:", 1)[0]
        self.assertLess(load.index(".a8"), load.index("lda #$00"))
        self.assertLess(load.index("lda #$00"),
                        load.index("sta.l SAME_SCUMM_M23A_HOLD"))


if __name__ == "__main__":
    unittest.main()
