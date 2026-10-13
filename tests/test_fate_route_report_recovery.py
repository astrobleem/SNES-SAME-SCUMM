from __future__ import annotations

import unittest

from recover_completed_fate_msu_route_report import recover_completed_report


def _reports() -> tuple[dict, dict, dict]:
    identity = {
        "rom_sha256": "a" * 64,
        "map_sha256": "b" * 64,
        "build_identity_sha256": "c" * 64,
        "archive_sha256": "d" * 64,
        "program_directory_sha256": "e" * 64,
    }
    prefix = {**identity}
    resume = {
        **identity,
        "prefix_report_sha256": "f" * 64,
        "room5_entry": {
            "status": "authored-room-entry-complete",
            "final": {"room": 5, "error": 0},
        },
    }
    action_specs = (
        ("room5_rope_action", "room5 rope"),
        ("room6_books_action", "room6 books on statues"),
        ("room7_book_action", "room7 Lost Dialogue of Plato"),
        ("room7_cat118_action", "room7 object118 verb10"),
        ("room7_cat119_action", "room7 object119 verb10"),
    )
    partial = {
        **identity,
        "result": "fail",
        "failure": "UnboundLocalError: room5_entry was not assigned",
        "prefix_report_sha256": "f" * 64,
        "resume_report_sha256": "g" * 64,
        "room5_entry": resume["room5_entry"],
        "room_observations": {},
        "room7_after_cat118_context": {
            "selected_variables": {"214": 1, "217": 1, "218": 0},
        },
        "room7_cat_local_dispatches": [
            {"program_unit_identity": "RoomLocalProgram(room=7,local=207)"},
            {"program_unit_identity": "RoomLocalProgram(room=7,local=201)"},
        ],
        "residency_summary": {
            "stale_reference_detections": 0,
            "exhaustions": 0,
            "duplicate_program_unit_bindings": 0,
        },
        "final_snapshot": {
            "room": 3, "phase": 0, "error": 0, "lifecycle": 2,
            "actor1_room": 3, "actor1_x": 71, "actor1_y": 142,
            "slots": [{
                "program_unit_identity": "RoomLocalProgram(room=3,local=213)",
                "status": 1,
            }],
        },
    }
    for room in (5, 6, 7, 3):
        partial[f"room{room}_entry"] = {
            "status": "authored-room-entry-complete",
            "final": {"room": room, "error": 0},
        }
    partial["room5_entry"] = resume["room5_entry"]
    partial["controller_submissions"] = []
    for index, (key, name) in enumerate(action_specs, 121):
        before, after = index, index + 1
        partial[key] = {
            "result": "submitted authentic action once",
            "submission_count_before": before,
            "submission_count_after": after,
        }
        partial["controller_submissions"].append({
            "action": name, "before": before, "after": after,
        })
    return partial, prefix, resume


class FateRouteReportRecoveryTests(unittest.TestCase):
    def _recover(self, partial, prefix, resume):
        return recover_completed_report(
            partial, prefix, resume,
            partial_sha256="1" * 64,
            prefix_sha256="f" * 64,
            resume_sha256="g" * 64,
        )

    def test_recovers_only_report_assembly_failure_after_all_native_checks(self) -> None:
        partial, prefix, resume = _reports()
        recovered = self._recover(partial, prefix, resume)
        self.assertEqual(recovered["result"], "pass")
        self.assertEqual(recovered["final_snapshot"]["room"], 3)
        self.assertTrue(recovered["report_recovery"]["native_execution_complete"])

    def test_does_not_recover_native_state_failure(self) -> None:
        partial, prefix, resume = _reports()
        partial["final_snapshot"]["error"] = 1
        with self.assertRaisesRegex(ValueError, "final state"):
            self._recover(partial, prefix, resume)

    def test_does_not_recover_unrelated_harness_failure(self) -> None:
        partial, prefix, resume = _reports()
        partial["failure"] = "TimeoutError: emulator did not settle"
        with self.assertRaisesRegex(ValueError, "only the known"):
            self._recover(partial, prefix, resume)


if __name__ == "__main__":
    unittest.main()
