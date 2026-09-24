from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
import zipfile

from tools.build_m25a_validator_room import (
    depth_scripts,
    global_lookup_missing_scripts,
    missing_scripts,
    normal_scripts,
    outer_scripts,
    scheduler_scripts,
    startobject_scripts,
    startobject_replacement_scripts,
    startobject_long_replacement_scripts,
    require_fixture_room_is_unbound,
    selected_corpus_identity,
)


class M25AValidatorFixtureTests(unittest.TestCase):
    def test_startup42_build_uses_its_unbound_bootstrap_record(self) -> None:
        root = Path(__file__).resolve().parents[1]
        build = (root / "tools/build_snes.sh").read_text()
        self.assertIn(
            "ENGINE_SELECTION_ARGS+=(--scumm-scenario-start-room 254)", build,
        )
        self.assertIn(
            'M25A_FIXTURE_ROOM_ARGS+=(--fixture-room 254)', build,
        )

    def test_synthetic_startup_room_must_be_absent_from_authored_namespace(self) -> None:
        require_fixture_room_is_unbound(254, {1, 42, 49, 75, 98})
        with self.assertRaisesRegex(RuntimeError, "collides with an authored room"):
            require_fixture_room_is_unbound(49, {1, 42, 49, 75, 98})

    def test_selected_corpus_identity_records_both_scumm_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "corpus.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("ATLANTIS/ATLANTIS.000", b"index")
                bundle.writestr("ATLANTIS/ATLANTIS.001", b"data")
            identity = selected_corpus_identity(archive)
        self.assertEqual(identity["index_member"], "ATLANTIS/ATLANTIS.000")
        self.assertEqual(identity["data_member"], "ATLANTIS/ATLANTIS.001")
        self.assertEqual(identity["index_sha256"],
                         "1bc04b5291c26a46d918139138b992d2de976d6851d0893b0476b85bfbdfc6e6")
    def test_normal_fixture_has_exact_nested_resume_boundaries(self) -> None:
        entry, scripts = normal_scripts()
        programs = dict(scripts)
        self.assertEqual(entry, bytes((0x0A, 200, 0xFF, 0x00)))
        self.assertEqual(tuple(programs), (200, 201))
        self.assertEqual(programs[200][15:18], bytes((0x0A, 201, 0xFF)))
        self.assertEqual(programs[200][18], 0x1A)
        self.assertEqual(programs[200][26:28], bytes((0x80, 0x1A)))
        self.assertEqual(programs[201][15:17], bytes((0x80, 0x1A)))
        root = Path(__file__).resolve().parents[1]
        hot = (root / "runtime/snes/engines/scumm_v5.pasm").read_text()
        far = (root / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        self.assertIn("ScummV5_Op_StartScript__found:", hot)
        self.assertIn("SAME_BUILD_SCUMM_M25_MOVEMENT", hot)
        self.assertIn(
            "lda.l SAME_SCUMM_C4_LAST_ALLOCATED\n    and #$00FF\n"
            "    sta.l SAME_SCUMM_C4_CURRENT_SLOT\n    tax",
            far,
        )

    def test_depth_fixture_exercises_all_24_child_slots(self) -> None:
        _, scripts = depth_scripts()
        programs = dict(scripts)
        self.assertEqual(tuple(programs), tuple(range(200, 224)))
        for number in range(200, 224):
            self.assertEqual(programs[number][5:8],
                             bytes((0x0A, number + 1, 0xFF)))
        self.assertNotIn(224, programs)

    def test_missing_fixture_has_no_resolvable_target(self) -> None:
        _, scripts = missing_scripts()
        programs = dict(scripts)
        self.assertEqual(tuple(programs), (200,))
        self.assertEqual(programs[200][5:8], bytes((0x0A, 250, 0xFF)))
        self.assertNotIn(250, programs)

    def test_unmapped_global_start_is_a_body_requiring_instruction(self) -> None:
        entry, scripts = global_lookup_missing_scripts()
        self.assertEqual(entry, bytes((0x0A, 131, 0xFF, 0x00)))
        self.assertEqual(scripts, ())

    def test_outer_fixture_requires_zero_return_mode_after_child(self) -> None:
        entry, scripts = outer_scripts()
        self.assertEqual(tuple(dict(scripts)), (200,))
        self.assertEqual(entry[5:8], bytes((0x0A, 200, 0xFF)))
        self.assertEqual(entry[8], 0x1A)
        self.assertEqual(entry[13], 0x80)
        self.assertEqual(entry[14], 0x1A)

    def test_scheduler_fixture_covers_pass_invariants(self) -> None:
        entry, scripts = scheduler_scripts()
        programs = dict(scripts)
        self.assertEqual(tuple(programs), (200, 201, 202, 203, 204))
        self.assertIn(bytes((0x0A, 201, 0xFF)), programs[200])
        self.assertEqual(programs[200].count(0x80), 1)
        self.assertEqual(programs[201].count(0x80), 1)
        self.assertEqual(programs[202].count(0x80), 2)
        self.assertNotIn(0x80, programs[203])
        self.assertIn(bytes((0x62, 204)), entry)
        self.assertEqual(programs[204].count(0x80), 1)

    def test_startobject_fixture_uses_complete_obcd_resources(self) -> None:
        entry, scripts, objects = startobject_scripts()
        self.assertEqual(len(objects), 2)
        self.assertEqual(objects[0][:4], b"CDHD")
        self.assertIn(b"VERB", objects[0])
        self.assertIn(bytes((0x42, 200, 0xFF)), objects[0])
        self.assertIn(bytes((0x42, 201, 0xFF)), objects[0])
        self.assertIn(bytes((0x42, 202, 0xFF)), objects[0])
        self.assertIn(bytes((0x42, 203, 0xFF)), objects[1])
        self.assertEqual(tuple(dict(scripts)), (200, 201, 202, 203))
        self.assertEqual(entry.count(0x37), 5)

    def test_startobject_replacement_fixture_distinguishes_new_entry_and_old_tail(self) -> None:
        entry, scripts, objects = startobject_replacement_scripts()
        self.assertEqual(entry, bytes((
            0x1A, 10, 0, 0, 0,       # clear observable result V10
            0x1A, 11, 0, 0, 0,       # clear old-tail sentinel V11
            0x37, 100, 0, 10, 0xFF,  # start object 100 / verb 10
            0x00,
        )))
        self.assertEqual(scripts, ())
        self.assertEqual(len(objects), 1)
        encoded = objects[0]
        self.assertIn(bytes((0x37, 100, 0, 8, 0, 0xEF, 0xBE, 0xFF)), encoded)
        self.assertIn(bytes((0x9A, 10, 0, 0, 0x40, 0x80, 0x00)), encoded)
        self.assertIn(bytes((0x1A, 11, 0, 0xAD, 0xDE)), encoded)

    def test_startobject_long_replacement_crosses_operation_counter_boundary(self) -> None:
        from build_m25a_validator_room import set_word

        entry, scripts, objects = startobject_long_replacement_scripts()
        counted_operations = b"".join(
            set_word(30, 0x5000 + index) for index in range(260)
        )
        self.assertEqual(scripts, ())
        self.assertEqual(len(objects), 1)
        self.assertIn(counted_operations, objects[0])
        self.assertIn(bytes((0x37, 100, 0, 8, 0, 0xEF, 0xBE, 0xFF)), objects[0])
        self.assertIn(bytes((0x1A, 11, 0, 0xAD, 0xDE)), objects[0])

    def test_no_parent_slot_index_is_zero_extended_before_tax(self) -> None:
        """Source contract supplement; native execution is the Make target."""
        root = Path(__file__).resolve().parents[1]
        source = (root / "runtime/snes/engines/scumm_v5.pasm").read_text()
        helper = source.split("ScummV5_C4_RunAllocatedNoParent:\n", 1)[1].split(
            "ScummV5_C4_RunAllocatedNoParent_FarEntry:", 1
        )[0]
        required = (
            "lda.l SAME_SCUMM_FRAME_OPS\n"
            "    sta.l SAME_SCUMM_C4_CHAIN_OPS\n"
            "    sep #$20\n"
            "    .a8\n"
            "    lda.l SAME_SCUMM_C4_LAST_ALLOCATED\n"
            "    sta.l SAME_SCUMM_C4_CURRENT_SLOT\n"
            "    ; LAST_ALLOCATED is a byte, but this helper's caller may leave X 16-bit.\n"
            "    ; Zero-extend A before TAX so FRAME_OPS' high byte cannot become the slot.\n"
            "    rep #$30\n"
            "    .a16\n"
            "    .i16\n"
            "    and #$00FF\n"
            "    tax\n"
            "    sep #$20\n"
            "    .a8\n"
            "    lda.l SAME_SCUMM_C4_SLOT_STATUS,x"
        )
        self.assertIn(required, helper)

    def test_startobject_nested_fixture_checks_distinct_activation_return(self) -> None:
        from build_m25a_validator_room import startobject_nested_scripts

        entry, scripts, objects = startobject_nested_scripts()
        self.assertEqual(entry, bytes((
            0x1A, 10, 0, 0, 0,
            0x1A, 11, 0, 0, 0,
            0x37, 100, 0, 10, 0xFF,
            0x00,
        )))
        self.assertEqual(scripts, ())
        self.assertEqual(len(objects), 2)
        self.assertIn(bytes((0x37, 101, 0, 8, 0, 0xFE, 0xCA, 0xFF)), objects[0])
        self.assertIn(bytes((0x9A, 10, 0, 0, 0x40, 0x00)), objects[1])
        self.assertIn(bytes((0x46, 11, 0, 0x00)), objects[0])

    def test_actor_position_error_fixtures_isolate_result_and_selector_failures(self) -> None:
        from build_m25a_validator_room import (
            actor_position_result_invalid_scripts,
            actor_position_result_truncated_scripts,
            actor_position_selector_truncated_scripts,
        )

        self.assertEqual(actor_position_result_truncated_scripts(), (bytes.fromhex("43 0a"), ()))
        self.assertEqual(
            actor_position_result_invalid_scripts(),
            (bytes.fromhex("43 ff 4f"), ()),
        )
        self.assertEqual(
            actor_position_selector_truncated_scripts(),
            (bytes.fromhex("43 0a 00 01"), ()),
        )


if __name__ == "__main__":
    unittest.main()
