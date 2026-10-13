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
from tools.audit_scumm_residency_wram import audit as audit_wram


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
    def test_rom_backed_build_emits_inert_msu_program_include(self) -> None:
        build = (ROOT / "tools/build_snes.sh").read_text(encoding="utf-8")
        main = (ROOT / "runtime/snes/main.pasm").read_text(encoding="utf-8")
        self.assertIn(
            "Generated empty SCUMM ProgramUnit directory (MSU programs disabled).",
            build,
        )
        self.assertIn(
            '> runtime/snes/generated/scumm_v5_msu_programs.inc.pasm',
            build,
        )
        self.assertIn(
            '.include "generated/scumm_v5_msu_programs.inc.pasm"',
            main,
        )

    def test_winston_storage_personality_keeps_its_generated_package_directory(self) -> None:
        source = (ROOT / "runtime/snes/main.pasm").read_text()
        self.assertIn(".if SAME_BUILD_MSU1_STORAGE\n", source)
        self.assertEqual(source.count('.include "generated/msu1_package.inc.pasm"'), 1)
        self.assertIn(
            "; both diagnostic and streamed-SCUMM personalities",
            source,
        )

    def test_resolver_coexists_with_controller_names_save_validator_and_vm_state(self) -> None:
        report = audit_wram()
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["overlaps"], [])
        self.assertEqual(report["features_coexist"], [
            "resolver", "controller/input", "name cache", "save validator",
            "C4", "C19", "room lifecycle",
            "bounded streamed-program execution context",
        ])
        resolver = next(row for row in report["regions"]
                        if row["owner"] == "resident_resolver")
        self.assertEqual((resolver["start"], resolver["end_exclusive"], resolver["bytes"]),
                         ("$7E8C00", "$7E8FC0", 960))

    def test_engine_selection_allows_dynamic_residency_with_production_services(self) -> None:
        with tempfile.TemporaryDirectory(prefix="same-residency-selection-") as raw:
            output = Path(raw) / "active_engine.inc.pasm"
            subprocess.run([
                sys.executable, str(ROOT / "tools/generate_snes_engine_selection.py"),
                "--engine", "scumm_v5", "--scumm-m23a",
                "--m24rb", "--scumm-dynamic-program-residency", "--scumm-controller",
                "--scumm-save-persistence-validator", "--output", str(output),
            ], check=True, capture_output=True, text=True)
            config = output.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY = $01", config)
            self.assertIn("SAME_BUILD_M24RB = $01", config)
            self.assertIn("SAME_BUILD_SCUMM_CONTROLLER = $01", config)
            self.assertIn("SAME_BUILD_SCUMM_SAVE_PERSISTENCE_VALIDATOR = $01", config)
            self.assertIn("SAME_BUILD_SCUMM_ROOM_SERVICE_FAR = $01", config)

    def test_dynamic_boot_clears_name_cache_before_resolver_initialization(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        room_service = source.index(".if SAME_BUILD_SCUMM_ROOM_SERVICE\n")
        name_clear = source.index("ScummV5_Engine_Boot__clear_object_name_lengths:", room_service)
        resolver_reset = source.index("jsl ScummV5_Resident_Reset_Far", name_clear)
        self.assertLess(name_clear, resolver_reset)
        self.assertIn("sta.l SAME_SCUMM_OBJECT_NAME_LENGTH,x", source[name_clear:resolver_reset])

    def test_dynamic_residency_keeps_the_generic_set_object_name_cache(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        start = source.index("ScummV5_Op_SetObjectName:")
        end = source.index("; Canonical v5 $29/$69/$A9/$E9 setOwnerOf", start)
        implementation = source[start:end]
        self.assertIn(".if SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY", implementation)
        self.assertIn("jsl ScummV5_ObjectNameCache_SetName_Far", implementation)
        far_source = (ROOT / "runtime/snes/engines/scumm_v5_object_name_cache_far.pasm").read_text()
        self.assertIn("ScummV5_ObjectNameCache_SetName_Far:", far_source)
        self.assertIn("jsl ScummV5_Matrix_FarCall_FetchByte", far_source)
        self.assertIn("jsl ScummV5_ObjectNameCache_FarCall_FetchWordParam", far_source)
        self.assertIn("sta.l SAME_SCUMM_OBJECT_NAMES,x", far_source)
        self.assertIn("sta.l SAME_SCUMM_OBJECT_NAME_LENGTH,x", far_source)
        self.assertIn("ScummV5_ObjectNameCache_StoreByte_Far__advance:", far_source)
        self.assertIn("ScummV5_ObjectNameCache_FarCall_FetchWordParam:\n    jsr ScummV5_C23_FetchWordParam\n    rtl", source)
        main = (ROOT / "runtime/snes/main.pasm").read_text()
        self.assertIn('.include "engines/scumm_v5_object_name_cache_far.pasm"', main)

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

    def test_room_release_unbinds_only_after_bundle_pin_and_c4_owner_are_gone(self) -> None:
        source = RESOLVER.read_text(encoding="utf-8")
        release_start = source.index("ScummV5_Resident_ReleaseRoomBundle_Far:")
        helper_start = source.index("\nScummV5_Resident_ReleaseIfUnowned_Far:\n", release_start)
        release = source[release_start:helper_start]
        helper_end = source.index(".if SAME_BUILD_SCUMM_RESIDENCY_DIAGNOSTIC", helper_start)
        helper = source[helper_start:helper_end]

        self.assertLess(release.index("jsl ScummV5_Resident_UnpinRoomBundle_Far"),
                        release.index("jsl ScummV5_Resident_ReleaseIfUnowned_Far"))
        self.assertIn(
            "and #(SCUMM_RESIDENT_FLAG_ROOM_BUNDLE | SCUMM_RESIDENT_FLAG_EXPLICIT)",
            helper,
        )
        self.assertIn("jsr ScummV5_Resident_IsSelectorLive", helper)
        self.assertIn("sta.l SAME_SCUMM_RESIDENT_UNIT_IDS,x", helper)
        self.assertIn("sta.l SAME_SCUMM_RESIDENT_FLAGS,x", helper)
        self.assertIn("sta.l SAME_SCUMM_RESIDENT_CURRENT_COUNT", helper)

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
            object_domain = manifest["global_objects"]
            self.assertEqual(object_domain["count"], 256)
            self.assertEqual(len((output / object_domain["owners_output"]).read_bytes()), 256)
            self.assertEqual(len((output / object_domain["states_output"]).read_bytes()), 256)

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
