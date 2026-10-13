from __future__ import annotations

import unittest

from same.engines.scumm_v5.replay_differential import (
    CHECKPOINTS, SEMANTIC_STATE_FIELDS, compare_replay_reports,
)


def _report(*, dynamic: bool, pc: int = 12, status: int = 2,
            delay: int = 0) -> dict:
    snapshot = {field: 0 for field in SEMANTIC_STATE_FIELDS}
    snapshot.update({"room": 7, "lifecycle": 2, "error": 0, "actor1_room": 7})
    slot = {
        "slot": 1, "script": 201, "room_owner": 7, "status": status,
        "program": 0x80 if dynamic else 0x43, "saved_pc": pc,
        "delay": delay, "freeze_resistant": 0, "freeze_count": 0,
    }
    if dynamic:
        slot.update({"program_unit_identity": "RoomLocalProgram(room=7,local=201)",
                     "program_unit_id": 135, "binding_generation": 3})
    snapshot["slots"] = [slot]
    route = {}
    for name in CHECKPOINTS:
        route[name] = snapshot if name == "final_snapshot" else {"final": snapshot}
    return {
        "result": "pass", "dynamic_residency": dynamic,
        "rom_sha256": "a" * 64 if dynamic else "b" * 64,
        "room7_after_cat118_context": {
            "selected_variables": {"214": 1, "217": 1, "218": 0},
            "set_bits": [35],
            "objects": [{"object": 118, "state": 1, "owner": 0}],
            "inventory_owner1_objects": [],
            "book_inventory_object937_owner": 1,
        },
        **route,
    }


class ScummReplayDifferentialTests(unittest.TestCase):
    def test_ephemeral_selectors_do_not_cause_false_live_script_mismatch(self) -> None:
        result = compare_replay_reports(_report(dynamic=False), _report(dynamic=True))
        self.assertTrue(result["all_semantic_acceptance_checks_pass"])
        self.assertTrue(result["all_live_script_checks_pass"])
        self.assertTrue(all(row["active_program_units_match"]
                            for row in result["checkpoints"]))

    def test_physical_activation_slot_reassignment_is_diagnostic_only(self) -> None:
        static = _report(dynamic=False)
        dynamic = _report(dynamic=True)
        dynamic["post_use"]["final"]["slots"][0]["slot"] = 7
        result = compare_replay_reports(static, dynamic)
        self.assertTrue(result["all_semantic_acceptance_checks_pass"])
        self.assertTrue(result["all_live_script_checks_pass"])
        self.assertEqual(
            len(result["physical_slot_assignment_differences"]), len(CHECKPOINTS)
        )

    def test_transient_pc_difference_is_reported_separately(self) -> None:
        result = compare_replay_reports(
            _report(dynamic=False, pc=12), _report(dynamic=True, pc=29))
        self.assertTrue(result["all_semantic_acceptance_checks_pass"])
        self.assertTrue(result["all_live_script_checks_pass"])
        self.assertTrue(all(row["active_program_units_match"]
                            for row in result["checkpoints"]))
        self.assertEqual(len(result["continuation_pc_differences"]), len(CHECKPOINTS))

    def test_delay_tick_drift_is_reported_without_hiding_wait_state(self) -> None:
        result = compare_replay_reports(
            _report(dynamic=False, delay=7), _report(dynamic=True, delay=8))
        self.assertTrue(result["all_semantic_acceptance_checks_pass"])
        self.assertTrue(result["all_live_script_checks_pass"])
        self.assertTrue(all(row["active_program_units_match"]
                            for row in result["checkpoints"]))
        self.assertEqual(len(result["scheduler_delay_differences"]), len(CHECKPOINTS))

    def test_runnable_vs_waiting_activation_difference_fails(self) -> None:
        result = compare_replay_reports(
            _report(dynamic=False, delay=0), _report(dynamic=True, delay=1))
        self.assertFalse(result["all_semantic_acceptance_checks_pass"])
        self.assertFalse(result["all_live_script_checks_pass"])
        self.assertFalse(result["checkpoints"][0]["active_program_units_match"])

    def test_semantic_state_or_activation_status_mismatch_fails(self) -> None:
        static = _report(dynamic=False)
        dynamic = _report(dynamic=True, status=3)
        dynamic["post_use"]["final"]["actor1_x"] = 99
        result = compare_replay_reports(static, dynamic)
        first = result["checkpoints"][0]
        self.assertFalse(result["all_semantic_acceptance_checks_pass"])
        self.assertFalse(result["all_live_script_checks_pass"])
        self.assertFalse(first["semantic_state_match"])
        self.assertFalse(first["active_program_units_match"])

    def test_room7_progression_variables_and_object_state_are_compared(self) -> None:
        static = _report(dynamic=False)
        dynamic = _report(dynamic=True)
        dynamic["room7_after_cat118_context"]["selected_variables"]["217"] = 0
        result = compare_replay_reports(static, dynamic)
        self.assertTrue(result["room7_progression_context_checked"])
        self.assertFalse(result["room7_progression_context_match"])
        self.assertFalse(result["all_semantic_acceptance_checks_pass"])
        self.assertIn("selected_variables",
                      result["room7_progression_context_differences"])


if __name__ == "__main__":
    unittest.main()
