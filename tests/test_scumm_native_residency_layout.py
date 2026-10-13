"""Source-level guards for the feature-gated native residency layout."""

from __future__ import annotations

from pathlib import Path
import re
import json
import subprocess
import sys
import tempfile
import unittest

from tools.validate_scumm_native_residency_nexen import (
    LIVE_ROOM_ACTIVE_BASE, LIVE_ROOM_ACTIVE_CAPACITY, git_identity,
)
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
    def test_live_room_validator_reads_the_audited_active_record_region(self) -> None:
        layout = json.loads((ROOT / "runtime/snes/carriers/sa1_bwram_layout.json")
                            .read_text(encoding="utf-8"))
        active = layout["live_room_active"]
        self.assertEqual(int(active["address"].replace(":", ""), 16),
                         LIVE_ROOM_ACTIVE_BASE)
        self.assertEqual(active["bytes"], LIVE_ROOM_ACTIVE_CAPACITY)

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
            "three-page streamed-program cache", "Mode-3 live staging",
        ])
        resolver = next(row for row in report["regions"]
                        if row["owner"] == "resident_resolver")
        self.assertEqual((resolver["start"], resolver["end_exclusive"], resolver["bytes"]),
                         ("$7E8C00", "$7E8FC0", 960))
        self.assertEqual(report["bwram_aliases"], [{
            "owner": "SCUMM checked ProgramUnit page cache",
            "address": "$41E800", "bytes": 0x800,
            "exclusive_with": "Mode-3 conformance fixture engine",
            "active_mode3_staging_unaffected": True,
        }])

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

    def test_first_brk_capture_is_explicit_and_requires_diagnostic_storage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="same-first-brk-selection-") as raw:
            output = Path(raw) / "active_engine.inc.pasm"
            subprocess.run([
                sys.executable, str(ROOT / "tools/generate_snes_engine_selection.py"),
                "--engine", "scumm_v5", "--capture-first-brk",
                "--output", str(output),
            ], check=True, capture_output=True, text=True)
            config = output.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_BUILD_CAPTURE_FIRST_BRK = $01", config)

            invalid = subprocess.run([
                sys.executable, str(ROOT / "tools/generate_snes_engine_selection.py"),
                "--engine", "scumm_v5", "--capture-first-brk",
                "--disable-reset-diagnostics", "--output",
                str(Path(raw) / "invalid.inc.pasm"),
            ], capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("requires reset diagnostics storage", invalid.stderr)

    def test_live_room_pcm_diagnostic_is_feature_gated_by_room_storage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="same-live-room-pcm-selection-") as raw:
            output = Path(raw) / "active_engine.inc.pasm"
            command = [
                sys.executable, str(ROOT / "tools/generate_snes_engine_selection.py"),
                "--engine", "scumm_v5", "--msu1-storage",
                "--scumm-msu1-programs", "--scumm-msu1-live-room-resources",
                "--scumm-room-visual", "--scumm-m23a", "--m24rb",
                "--scumm-dynamic-program-residency",
                "--scumm-msu1-live-room-pcm-track", "101",
                "--output", str(output),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            config = output.with_name("build_config.inc.pasm").read_text()
            self.assertIn("SAME_SCUMM_MSU1_LIVE_ROOM_PCM_TEST_TRACK = $0065", config)
            self.assertIn("SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES = $01", config)

            invalid = subprocess.run(
                [sys.executable, str(ROOT / "tools/generate_snes_engine_selection.py"),
                 "--engine", "scumm_v5", "--scumm-msu1-live-room-pcm-track", "1",
                 "--output", str(Path(raw) / "invalid.inc.pasm")],
                capture_output=True, text=True,
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("requires live room resources", invalid.stderr)

    def test_live_room_provider_budget_is_bounded_and_other_clients_keep_64(self) -> None:
        source = (ROOT / "runtime/snes/services/storage_msu1.pasm").read_text()
        self.assertIn(".if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES", source)
        self.assertIn("SAME_MSU1_STEP_BUDGET         = $0100", source)
        self.assertIn("SAME_MSU1_STEP_BUDGET         = $0040", source)
        self.assertIn("request copying uses SAME_MSU1_STEP_BUDGET", source)
        self.assertIn("cmp #SAME_BWRAM_LIVE_ROOM_PENDING_SIZE+1", source)

    def test_live_room_pending_read_capacity_tracks_audited_buffer_layout(self) -> None:
        layout = json.loads(
            (ROOT / "runtime/snes/carriers/sa1_bwram_layout.json").read_text()
        )
        pending = layout["backend_reserved"]["allocations"]["live_room_pending"]
        self.assertEqual(pending["bytes"], 0x0A00)
        source = (ROOT / "runtime/snes/services/storage_msu1.pasm").read_text()
        pending_guard = source.split(
            "Same_Msu1_ReadBegin__dest_pending_high_ok:", 1
        )[1].split("Same_Msu1_ReadBegin__dest_pending_capacity_ok16:", 1)[0]
        self.assertIn("SAME_BWRAM_LIVE_ROOM_PENDING_SIZE+1", pending_guard)
        self.assertNotIn("cmp #$0801", pending_guard)

    def test_live_walkbox_geometry_copy_preserves_each_two_byte_coordinate(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        loader = source.split("ScummV5_LiveRoom_LoadGeometry_Far__copy:", 1)[1]
        loader = loader.split("ScummV5_LiveRoom_LoadGeometry_Far__bad:", 1)[0]
        self.assertIn("lda.l SCUMM_LIVE_ROOM_BASE,x", loader)
        self.assertIn("sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK,x", loader)
        self.assertIn(
            "lda.l SCUMM_LIVE_ROOM_TEMP0\n"
            "    inc\n"
            "    inc\n"
            "    sta.l SCUMM_LIVE_ROOM_TEMP0",
            loader,
        )
        self.assertIn(
            "lda.l SCUMM_LIVE_ROOM_TEMP1\n"
            "    inc\n"
            "    inc\n"
            "    sta.l SCUMM_LIVE_ROOM_TEMP1",
            loader,
        )

    def test_streamed_program_accepts_only_the_exact_final_body_boundary(self) -> None:
        programs = (ROOT / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        terminal = programs.split(
            "ScummV5_MsuProgram_FindPage_Far__terminal_candidate:", 1
        )[1].split("ScummV5_MsuProgram_FindPage_Far__found:", 1)[0]
        self.assertIn("SAME_SCUMM_MSU_PAGE_SCAN_COUNT", terminal)
        self.assertIn("cmp #$0001", terminal)
        self.assertIn("ScummV5_MsuProgramRecords,x", terminal)
        self.assertIn("cmp.l SAME_SCUMM_MSU_PAGE_REQUEST_PC", terminal)
        self.assertIn(
            "cmp.l SAME_SCUMM_PROGRAM_SIZE\n    bcc ScummV5_Engine_Frame__start_runnable",
            (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text(),
        )

    def test_stream_error_diagnostic_sites_are_unique(self) -> None:
        tags: list[tuple[str, int]] = []
        for path in (ROOT / "runtime/snes/engines").glob("*.pasm"):
            source = path.read_text()
            for raw in re.findall(
                r"lda\s+#\$([0-9A-Fa-f]{2})\s*\n\s*"
                r"jsl\s+ScummV5_Stream_RecordErrorSite_FarEntry",
                source,
                re.IGNORECASE,
            ):
                tags.append((str(path.relative_to(ROOT)), int(raw, 16)))
        self.assertTrue(tags)
        values = [tag for _, tag in tags]
        self.assertEqual(len(values), len(set(values)), tags)

    def test_stream_error_capture_uses_only_the_c25_verified_scratch_gap(self) -> None:
        address = symbols()
        capture_start = address["SAME_SCUMM_STREAM_ERROR_REQUEST_ID"]
        capture_end = address["SAME_SCUMM_STREAM_ERROR_CAPTURE_VALID"] + 1
        c25_record_start = 0x7E5F0E
        c25_record_end = c25_record_start + 5
        c25_counters_start = 0x7E5F20
        self.assertEqual(capture_start, 0x7E5F13)
        self.assertEqual(capture_end, 0x7E5F19)
        self.assertLessEqual(c25_record_end, capture_start)
        self.assertLess(capture_end, c25_counters_start)

    def test_third_checked_program_page_aliases_only_the_mode3_fixture_workspace(self) -> None:
        memory = MEMORY.read_text()
        self.assertIn("SAME_SCUMM_MSU_PROGRAM_CACHE2           = $41E800", memory)
        self.assertIn("SAME_SCUMM_MSU_PROGRAM_CACHE2_END       = $41F000", memory)
        report = audit_wram()
        self.assertEqual(report["bwram_aliases"][0]["address"], "$41E800")
        video = json.loads(
            (ROOT / "runtime/snes/video_backends/mode3_surface_layout.json").read_text()
        )
        self.assertEqual(video["fixture"], {"address": "41:E800", "bytes": 2048})
        provider = (ROOT / "runtime/snes/services/storage_msu1.pasm").read_text()
        self.assertIn("cmp #<SAME_SCUMM_MSU_PROGRAM_CACHE2", provider)
        self.assertIn("cmp #SAME_SCUMM_MSU_PROGRAM_CACHE_SLOT_SIZE+1", provider)
        cache_check = provider.split(
            "Same_Msu1_ReadBegin__dest_bwram_ok:", 1
        )[1].split("Same_Msu1_ReadBegin__bwram_cache_page_low_ok:", 1)[0]
        self.assertRegex(
            cache_check,
            r"sep #\$20\s+\.a8\s+lda\.l SAME_MSU1_DESTINATION\s+"
            r"cmp #<SAME_SCUMM_MSU_PROGRAM_CACHE2",
        )
        programs = (ROOT / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        self.assertIn("SAME_SCUMM_MSU_PROGRAM_CACHE2,x", programs)
        target2 = programs.split(
            "ScummV5_MsuProgram_EnsureSelected_Far__target2:", 1
        )[1].split("ScummV5_MsuProgram_EnsureSelected_Far__destination_ready:", 1)[0]
        self.assertIn("lda #SAME_SCUMM_MSU_PROGRAM_CACHE2_BANK", target2)
        self.assertIn("SAME_SCUMM_MSU_PROGRAM_CACHE2_BANK      = $41", MEMORY.read_text())
        self.assertIn("SAME_SCUMM_MSU_CACHE_GENERATION2", programs)
        self.assertIn("SAME_SCUMM_MSU_CACHE_PINS2", programs)
        lookup = programs.split(
            "ScummV5_MsuProgram_EnsureSelected_Far__check_slot1:", 1
        )[1].split(
            "ScummV5_MsuProgram_EnsureSelected_Far__check_slot2:", 1
        )[0]
        self.assertIn(
            "jml ScummV5_MsuProgram_EnsureSelected_Far__check_slot2", lookup
        )

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
