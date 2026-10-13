from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fate_replay_evidence as evidence


def _identity() -> dict[str, str]:
    return {
        "rom_sha256": "1" * 64,
        "map_sha256": "2" * 64,
        "build_identity_sha256": "3" * 64,
        "archive_sha256": "4" * 64,
        "program_directory_sha256": "5" * 64,
        "starting_head": "6" * 40,
    }


class FateReplayEvidenceTests(unittest.TestCase):
    def test_finalization_failure_recovers_durable_native_snapshot_without_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            journal_path = root / "route.evidence.jsonl"
            report_path = root / "route.json"
            snapshot = {
                **_identity(),
                "result": "pass",
                "final_snapshot": {"room": 3, "error": 0},
                "checkpoints": {"room4-open": {"native_frame": 220}},
                "room_observations": {
                    "5": {
                        "presentation_at_checkpoint": {
                            "full_vram_check": None,
                        },
                    },
                },
                "resume_report_sha256": "7" * 64,
            }
            journal = evidence.ReplayEvidenceJournal(journal_path)
            journal.append(snapshot)

            # Model a successful native execution followed by failure of the
            # human-readable report finalizer. The durable append happened first.
            with mock.patch.object(evidence, "atomic_write_report",
                                   side_effect=OSError("simulated report finalizer failure")):
                with self.assertRaisesRegex(OSError, "finalizer"):
                    evidence.atomic_write_report(report_path, snapshot)
            self.assertFalse(report_path.exists())

            recovered = evidence.recover_latest(journal_path)
            self.assertEqual(recovered["result"], "pass")
            self.assertEqual(recovered["final_snapshot"], snapshot["final_snapshot"])
            provenance = recovered["evidence_recovery"]["provenance"]
            self.assertIn("final_snapshot", provenance["native_observation_paths"])
            self.assertIn("checkpoints", provenance["hash_bound_reused_paths"])
            self.assertEqual(provenance["not_captured"], [
                "room_observations.5.presentation_at_checkpoint.full_vram_check",
            ])
            self.assertTrue(provenance["no_observations_inferred"])

    def test_journal_rejects_identity_changes_and_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "route.jsonl"
            journal = evidence.ReplayEvidenceJournal(path)
            journal.append({**_identity(), "result": "running"})
            changed = {**_identity(), "rom_sha256": "a" * 64, "result": "pass"}
            with self.assertRaisesRegex(ValueError, "another build identity"):
                journal.append(changed)
            path.write_bytes(path.read_bytes() + b"{}\n")
            with self.assertRaisesRegex(ValueError, "sequence/schema"):
                evidence.read_journal(path)

    def test_recovery_preserves_running_instead_of_promoting_to_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "route.jsonl"
            evidence.ReplayEvidenceJournal(path).append({
                **_identity(), "result": "running", "checkpoints": {},
            })
            recovered = evidence.recover_latest(path)
            self.assertEqual(recovered["result"], "running")
            self.assertEqual(
                recovered["evidence_recovery"]["native_execution_result_preserved_verbatim"],
                "running",
            )


if __name__ == "__main__":
    unittest.main()
