"""Source-level guards for the feature-gated native residency layout."""

from __future__ import annotations

from pathlib import Path
import re
import json
import subprocess
import sys
import tempfile
import unittest

from tools.validate_scumm_native_residency_nexen import git_identity


ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "runtime/snes/kernel/memory.pasm"
RESOLVER = ROOT / "runtime/snes/engines/scumm_v5_resident_resolver.pasm"


def symbols() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in MEMORY.read_text(encoding="utf-8").splitlines():
        match = re.match(r"(SAME_SCUMM_[A-Z0-9_]+)\s*=\s*\$([0-9A-Fa-f]+)", line)
        if match:
            values[match.group(1)] = int(match.group(2), 16)
    return values


class NativeResidencyLayoutTests(unittest.TestCase):
    def test_resident_tables_do_not_alias_live_object_name_cache(self) -> None:
        address = symbols()
        name_start = address["SAME_SCUMM_OBJECT_NAME_LENGTH"]
        name_end = name_start + 1024
        ids_start = address["SAME_SCUMM_RESIDENT_UNIT_IDS"]
        ids_end = ids_start + 178 * 2
        generations_start = address["SAME_SCUMM_RESIDENT_GENERATIONS"]
        generations_end = generations_start + 178 * 2
        flags_start = address["SAME_SCUMM_RESIDENT_FLAGS"]
        flags_end = flags_start + 178
        names_payload_start = address["SAME_SCUMM_OBJECT_NAMES"]

        self.assertGreaterEqual(ids_start, name_end)
        self.assertEqual(ids_end, generations_start)
        self.assertEqual(generations_end, flags_start)
        self.assertLessEqual(flags_end, names_payload_start)
        self.assertEqual(address["SAME_SCUMM_RESIDENT_DIAG_STAGE"] + 1, 0x7E8FC0)
        self.assertLessEqual(address["SAME_SCUMM_RESIDENT_DIAG_STAGE"] + 1,
                             names_payload_start)

    def test_selector_liveness_probe_preserves_eviction_cursor(self) -> None:
        source = RESOLVER.read_text(encoding="utf-8")
        start = source.index("ScummV5_Resident_IsSelectorLive:")
        end = source.index("; Public explicit pin API", start)
        routine = source[start:end]

        self.assertIn("    phx\n", routine)
        self.assertEqual(routine.count("    plx\n"), 2)
        self.assertLess(routine.index("    plx\n    clc"),
                        routine.index("ScummV5_Resident_IsSelectorLive__yes:"))
        self.assertIn("ScummV5_Resident_IsSelectorLive__yes:\n    plx\n    sec", routine)

    def test_diagnostic_census_counts_owned_pins_without_scheduler_mutation(self) -> None:
        source = RESOLVER.read_text(encoding="utf-8")
        start = source.index("ScummV5_Resident_RefreshDiagnostics:")
        end = source.index("ScummV5_Resident_RefreshDiagnostics_Far:", start)
        routine = source[start:end]

        self.assertIn(
            "    and #(SCUMM_RESIDENT_FLAG_ROOM_BUNDLE | SCUMM_RESIDENT_FLAG_EXPLICIT)\n"
            "    beq ScummV5_Resident_RefreshDiagnostics__next\n",
            routine,
        )
        self.assertIn("    phx\n", routine)
        self.assertEqual(routine.count("    plx\n"), 1)
        self.assertIn("ScummV5_Resident_RefreshDiagnostics__done:\n    plx\n    plp\n    rts\n", routine)
        self.assertNotIn("jsr ", routine)
        self.assertNotIn("sta.l SAME_SCUMM_RESIDENT_FLAGS,x", routine)

    def test_generated_fixture_has_large_selector_free_global_universe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="same-residency-fixture-") as raw:
            output = Path(raw)
            subprocess.run([
                sys.executable, str(ROOT / "tools/build_scumm_native_residency_fixture.py"),
                "--output-dir", str(output),
            ], check=True, capture_output=True, text=True)
            manifest = json.loads((output / "manifest.json").read_text())
            numbers = {int(item["number"]) for item in manifest["global_scripts"]}
            self.assertEqual(len(numbers), 193)
            self.assertGreater(len(numbers), 178)
            self.assertEqual(numbers, set(range(1, 194)))

            probe = (output / "global-193.bin").read_bytes()
            self.assertEqual(probe.count(bytes((0x8A, 7, 0, 0xFF))), 2)
            self.assertIn(bytes((0x1A, 7, 0, 191, 0)), probe)
            self.assertIn(bytes((0x1A, 7, 0, 192, 0)), probe)
            self.assertEqual((output / "global-191.bin").read_bytes(),
                             bytes((0x1A, 21, 0, 5, 0, 0xA0)))
            self.assertEqual((output / "global-192.bin").read_bytes(),
                             bytes((0x1A, 22, 0, 6, 0, 0xA0)))

    def test_native_evidence_fingerprints_untracked_source_files(self) -> None:
        first = git_identity()
        second = git_identity()
        self.assertEqual(first["source_content_sha256"], second["source_content_sha256"])
        self.assertEqual(first["untracked_files"], second["untracked_files"])
        self.assertEqual(first["untracked_file_count"], len(first["untracked_files"]))
        self.assertEqual(first["untracked_files"], sorted(
            first["untracked_files"], key=lambda row: row["path"],
        ))
        self.assertTrue(all(len(row["sha256"]) == 64 for row in first["untracked_files"]))
        self.assertEqual(len(first["source_content_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
