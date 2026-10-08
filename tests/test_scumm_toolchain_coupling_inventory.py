from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/scumm-toolchain/fate_coupling.json"
CLASSIFICATIONS = {
    "GENERIC_SCUMM_SEMANTIC",
    "COMPILER_DERIVABLE_DATA",
    "FATE_PROFILE_DATA",
    "TEMPORARY_BRINGUP_HOOK",
    "TEST_FIXTURE_ONLY",
    "TRUE_FATE_SPECIFIC_QUIRK",
}
EXPECTED_COUNTS = {
    "GENERIC_SCUMM_SEMANTIC": 2,
    "COMPILER_DERIVABLE_DATA": 12,
    "FATE_PROFILE_DATA": 3,
    "TEMPORARY_BRINGUP_HOOK": 2,
    "TEST_FIXTURE_ONLY": 5,
    "TRUE_FATE_SPECIFIC_QUIRK": 0,
}


class ScummToolchainCouplingInventoryTests(unittest.TestCase):
    def test_machine_inventory_has_unique_classified_entries_and_current_counts(self) -> None:
        inventory = json.loads(AUDIT.read_text(encoding="utf-8"))
        self.assertEqual("same-scumm-fate-coupling-audit-v1", inventory["schema"])
        self.assertEqual(CLASSIFICATIONS, set(inventory["classifications"]))

        entries = inventory["entries"]
        ids = [entry["id"] for entry in entries]
        self.assertEqual(len(ids), len(set(ids)))
        for entry in entries:
            for field in (
                "path", "region", "why", "current_consumer",
                "desired_destination", "migration_action",
            ):
                self.assertTrue(entry[field], f"{entry['id']} lacks {field}")
            self.assertIn(entry["classification"], CLASSIFICATIONS)

        actual = Counter(entry["classification"] for entry in entries)
        self.assertEqual(
            {name: actual[name] for name in CLASSIFICATIONS}, inventory["counts"]
        )
        self.assertEqual(EXPECTED_COUNTS, inventory["counts"])
        self.assertEqual([], inventory["true_fate_specific_quirks"])

        audit = (ROOT / "docs/scumm-toolchain/FATE_COUPLING_AUDIT.md").read_text(encoding="utf-8")
        for classification, count in EXPECTED_COUNTS.items():
            self.assertIn(f"| `{classification}` | {count} |", audit)

    def test_historical_migration_ledger_links_to_canonical_audit_documents(self) -> None:
        ledger = (ROOT / "docs/SCUMM_TOOLCHAIN_MIGRATION.md").read_text(encoding="utf-8")
        for name in (
            "CURRENT_ARCHITECTURE.md", "FATE_COUPLING_AUDIT.md", "fate_coupling.json",
            "IR.md", "COMPILER_PIPELINE.md", "CAPABILITY_ANALYSIS.md",
            "RUNTIME_BOUNDARY.md", "MIGRATION_PLAN.md", "FIRST_MILESTONE.md",
            "MILESTONE_2.md",
            "MILESTONE_4_RESIDENCY.md",
            "MILESTONE_5_PROGRAM_UNITS.md",
            "CAPABILITY_FRONTIER_BURN_DOWN.md",
        ):
            self.assertIn(name, ledger)
            self.assertTrue((ROOT / "docs/scumm-toolchain" / name).is_file())

    def test_whole_game_analyzer_has_no_fate_progression_constants(self) -> None:
        production = (
            ROOT / "src/same/engines/scumm_v5/game_analysis.py",
            ROOT / "src/same/engines/scumm_v5/program_units.py",
            ROOT / "src/same/engines/scumm_v5/residency.py",
            ROOT / "src/same/engines/scumm_v5/residency_contract.py",
            ROOT / "tools/compile_scumm_game.py",
        )
        forbidden = ("GlobalScript(144)", "RoomLocal(room=7", "object=118",
                     "object=119", "local=207", "bit:69", "RoomEntry(42)")
        for path in production:
            content = path.read_text(encoding="utf-8")
            for identity in forbidden:
                self.assertNotIn(identity, content, f"{path} hardcodes {identity}")


if __name__ == "__main__":
    unittest.main()
