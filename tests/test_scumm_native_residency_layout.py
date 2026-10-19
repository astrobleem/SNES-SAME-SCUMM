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
    LIVE_ROOM_ACTIVE_BASE, LIVE_ROOM_ACTIVE_CAPACITY,
    audit_runtime_walkbox_flags, git_identity, room_metadata_probe_is_published,
    room_metadata_probe_step,
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
    def test_authentic_bootstrap_uses_far_body_with_room_service(self) -> None:
        main = (ROOT / "runtime/snes/main.pasm").read_text(encoding="utf-8")
        engine = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text(
            encoding="utf-8")
        helper = (ROOT / "runtime/snes/engines/scumm_v5_bootstrap_far.pasm").read_text(
            encoding="utf-8")
        bank9 = main.split(".bank 9\n.org $8000", 1)[1].split(".bank", 1)[0]
        self.assertIn('engines/scumm_v5_bootstrap_far.pasm', bank9)
        self.assertIn(".if SAME_BUILD_SCUMM_ROOM_SERVICE_FAR", engine)
        self.assertIn("jsl ScummV5_AuthenticBootstrap_Far", engine)
        self.assertIn("jsl ScummV5_Resident_ResolveGlobalScript_Far", helper)
        self.assertIn("SAME_SCUMM_C4_SLOT_LOCALS+$0040", helper)

    def test_mutable_walkbox_flags_require_runtime_matrixops_evidence(self) -> None:
        initial = bytes([0, 0, 0, 0])
        same = audit_runtime_walkbox_flags(
            initial, initial, successful_matrix_mutations=0, matrix_trace=[],
        )
        self.assertTrue(same["matches_source_initial_flags"])

        with self.assertRaisesRegex(RuntimeError, "without successful matrixOps"):
            audit_runtime_walkbox_flags(
                initial, bytes([0, 0x80, 0, 0]),
                successful_matrix_mutations=0, matrix_trace=[],
            )

        changed = audit_runtime_walkbox_flags(
            initial, bytes([0, 0x80, 0, 0]),
            successful_matrix_mutations=1,
            matrix_trace=[{
                "subop": 1, "box": 1, "flags": 0x80,
                "source_pc_before": 0x10, "source_pc_after": 0x14,
            }],
        )
        self.assertFalse(changed["matches_source_initial_flags"])
        self.assertEqual(changed["runtime_mutated_boxes"], [
            {"box": 1, "source": 0, "active": 0x80},
        ])

    def test_walkbox_mutation_trace_must_name_valid_matrixops_box(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "invalid records"):
            audit_runtime_walkbox_flags(
                bytes([0]), bytes([0x80]), successful_matrix_mutations=1,
                matrix_trace=[{
                    "subop": 1, "box": 2, "flags": 0x80,
                    "source_pc_before": 0, "source_pc_after": 4,
                }],
            )

    def test_walkbox_trace_accepts_create_box_matrix_sentinel(self) -> None:
        result = audit_runtime_walkbox_flags(
            bytes([0, 0, 0, 0]), bytes([0, 0x80, 0, 0]),
            successful_matrix_mutations=1,
            matrix_trace=[
                {"subop": 1, "box": 1, "flags": 0x80,
                 "source_pc_before": 0x10, "source_pc_after": 0x14},
                {"subop": 4, "box": 0xFF, "flags": 0xFF,
                 "source_pc_before": 0x14, "source_pc_after": 0x16},
            ],
        )
        self.assertEqual(len(result["runtime_mutation_trace"]), 2)
        self.assertEqual(result["runtime_mutated_boxes"], [
            {"box": 1, "source": 0, "active": 0x80},
        ])

        with self.assertRaisesRegex(RuntimeError, "invalid records"):
            audit_runtime_walkbox_flags(
                bytes([0]), bytes([0x80]), successful_matrix_mutations=1,
                matrix_trace=[{
                    "subop": 4, "box": 0, "flags": 0xFF,
                    "source_pc_before": 0, "source_pc_after": 2,
                }],
            )

    def test_live_room_validator_reads_the_audited_active_record_region(self) -> None:
        layout = json.loads((ROOT / "runtime/snes/carriers/sa1_bwram_layout.json")
                            .read_text(encoding="utf-8"))
        active = layout["live_room_active"]
        self.assertEqual(LIVE_ROOM_ACTIVE_BASE, 0x41E800)
        self.assertEqual(LIVE_ROOM_ACTIVE_CAPACITY, 0x1800)
        self.assertEqual(int(active["address"].replace(":", ""), 16),
                         LIVE_ROOM_ACTIVE_BASE)
        self.assertEqual(active["bytes"], LIVE_ROOM_ACTIVE_CAPACITY)

    def test_live_room_length_boundary_reloads_u16_after_a8_checkpoint(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        validator = source.split("ScummV5_LiveRoom_Validate_Far:", 1)[1].split(
            "ScummV5_LiveRoom_Validate_Far__bad:", 1,
        )[0]
        after_checkpoint = validator.split(
            "lda #$C1 ; identity/schema/length checks passed", 1,
        )[1].split("ScummV5_LiveRoom_Validate_Far__maximum_size_ok:", 1)[0]
        self.assertIsNotNone(re.search(
            r"rep #\$20\s+\.a16\s+.*?"
            r"lda\.l SCUMM_LIVE_ROOM_VALIDATION_BASE\+\$30\s+"
            r"cmp #SCUMM_LIVE_ROOM_HEADER_SIZE",
            after_checkpoint,
            re.S,
        ))
        self.assertIn("cmp #SCUMM_LIVE_ROOM_MAX_SIZE+1", after_checkpoint)

    def test_room_metadata_probe_batches_transfer_then_samples_commit_seam(self) -> None:
        self.assertEqual(room_metadata_probe_step(0, 98, 1, 98, 100), 16)
        self.assertEqual(room_metadata_probe_step(0, 98, 4, 98, 100), 16)
        self.assertEqual(room_metadata_probe_step(0, 98, 5, 98, 100), 1)
        self.assertEqual(room_metadata_probe_step(98, 0, 0, 98, 100), 1)
        self.assertEqual(room_metadata_probe_step(0, 0, 0, 98, 3), 3)

    def test_room_metadata_probe_requires_matching_published_active_identity(self) -> None:
        self.assertTrue(room_metadata_probe_is_published(98, 98, 1, 98))
        self.assertFalse(room_metadata_probe_is_published(98, 98, 0, 68))
        self.assertFalse(room_metadata_probe_is_published(98, 98, 1, 68))
        self.assertFalse(room_metadata_probe_is_published(68, 98, 1, 98))

    def test_live_object_walk_uses_the_ten_byte_compact_row_stride(self) -> None:
        runtime = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm")
        source = runtime.read_text(encoding="utf-8")
        body = source.split("ScummV5_LiveRoom_ObjectWalk_Far__found:\n", 1)[1]
        body = body.split("ScummV5_LiveRoom_ObjectWalk_Far__bad:", 1)[0]
        body = "\n".join(line.split(";", 1)[0] for line in body.splitlines())

        # OBJECT records include a u16 ID (11 bytes), while compact
        # OBJECT_WALK rows omit that ID and are <hhBhhB (10 bytes). The
        # lookup must use 2*i + 8*i, not the object-table stride.
        self.assertRegex(
            body,
            re.compile(r"lda\.l SCUMM_LIVE_ROOM_TEMP0\s+asl\s+"
            r"sta\.l SCUMM_LIVE_ROOM_TEMP2.*?"
            r"lda\.l SCUMM_LIVE_ROOM_TEMP0\s+asl\s+asl\s+asl\s+"
            r"clc\s+adc\.l SCUMM_LIVE_ROOM_TEMP2\s+"
            r"clc\s+adc\.l SCUMM_LIVE_ROOM_BASE\+"
            r"SCUMM_LIVE_ROOM_OBJECT_WALK_OFFSET", re.S),
        )

    def test_live_portal_pair_index_zero_extends_adjacent_u8_route_next(self) -> None:
        runtime = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm")
        source = runtime.read_text(encoding="utf-8")
        body = source.split("ScummV5_LiveRoom_Portal_Far:", 1)[1]
        body = body.split("ScummV5_LiveRoom_Portal_Far__bad:", 1)[0]
        body = "\n".join(line.split(";", 1)[0].strip() for line in body.splitlines())
        self.assertRegex(
            body,
            re.compile(
                r"lda\.l SAME_SCUMM_MOVE_ROUTE_NEXT\s+"
                r"and #\$00FF\s+"
                r"sta\.l SCUMM_LIVE_ROOM_TEMP5\s+"
                r"lda\.l SCUMM_LIVE_ROOM_TEMP2\s+clc\s+"
                r"adc\.l SCUMM_LIVE_ROOM_TEMP5\s+"
                r"sta\.l SCUMM_LIVE_ROOM_TEMP2"
            ),
        )

        # ROUTE_NEXT is followed immediately by PORTAL_TYPE in WRAM. A byte
        # value 1 next to the prior portal kind 24 must preserve both the
        # contamination defense and the high byte of a large pair index.
        next_u8, adjacent_portal_type = 1, 24
        self.assertEqual(20 * 20 + next_u8, 401)
        self.assertNotEqual(20 * 20 + (adjacent_portal_type << 8 | next_u8), 401)

    def test_live_room_v3_uses_validated_sparse_portal_directory(self) -> None:
        runtime = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm")
        source = runtime.read_text(encoding="utf-8")
        validator = source.split("ScummV5_LiveRoom_Validate_Far:", 1)[1]
        validator = validator.split("ScummV5_LiveRoom_Validate_Far__bad:", 1)[0]
        portal = source.split("ScummV5_LiveRoom_Portal_Far:", 1)[1]
        portal = portal.split("ScummV5_LiveRoom_Portal_Far__bad:", 1)[0]

        # V2 remains accepted; v3 is validated as a bounded pair-row and
        # descriptor section, then queried without expanding the dense matrix.
        self.assertIn("cmp #$0002", validator)
        self.assertIn("cmp #$0003", validator)
        self.assertIn("ScummV5_LiveRoom_Validate_Far__portal_v3_start:", validator)
        self.assertIn("ScummV5_LiveRoom_Validate_Far__portal_descriptors_no_overflow:", validator)
        self.assertIn("cmp #$0003", portal)
        self.assertIn("ScummV5_LiveRoom_Portal_Far__v3_search:", portal)
        self.assertIn("ScummV5_LiveRoom_Portal_Far__v3_found:", portal)
        self.assertIn("ScummV5_LiveRoom_Portal_Far__load_descriptor:", portal)

        layout = json.loads((ROOT / "runtime/snes/carriers/sa1_bwram_layout.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(layout["backend_reserved"]["allocations"]["live_room_pending"]["bytes"],
                         3132)
        self.assertEqual(layout["live_room_active"]["bytes"], 6144)

    def test_v4_final_validation_reads_installed_active_record(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        self.assertIn(
            "SCUMM_LIVE_ROOM_VALIDATION_BASE = SAME_SCUMM_LIVE_ROOM_STAGING_BASE",
            source,
        )
        self.assertIn(
            "SCUMM_LIVE_ROOM_VALIDATION_BASE = SCUMM_LIVE_ROOM_PENDING",
            source,
        )
        validator = source.split("ScummV5_LiveRoom_Validate_Far:", 1)[1]
        validator = validator.split("ScummV5_LiveRoom_Validate_Far__bad:", 1)[0]
        self.assertIn("SCUMM_LIVE_ROOM_VALIDATION_BASE+$30", validator)
        self.assertNotIn("SCUMM_LIVE_ROOM_PENDING", validator)

    def test_global_resolver_uses_a_wide_directory_index(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_resident_resolver.pasm").read_text()
        resolver = source.split("ScummV5_Resident_ResolveGlobalScript_Far:", 1)[1]
        resolver = resolver.split("ScummV5_Resident_ResolveLocalScript_Far:", 1)[0]
        self.assertIn("rep #$10\n    .i16\n    ldx #$0000", resolver)

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
            "exclusive actor/room SC5ACT pending scratch",
        ])
        resolver = next(row for row in report["regions"]
                        if row["owner"] == "resident_resolver")
        self.assertEqual((resolver["start"], resolver["end_exclusive"], resolver["bytes"]),
                         ("$7E8C00", "$7E8FC0", 960))
        self.assertEqual(report["bwram_aliases"], [{
            "owner": "live SC5LIVE actor underlay snapshot",
            "address_rule": "$41E800 + validated active SC5LIVE total_size",
            "maximum_bytes": 6144,
            "aliases": "unused tail of the same active metadata allocation",
            "lifetime": "displayed actor pose until the next redraw or checked room-surface publication",
            "capacity_rule": "16-byte checked header + clipped pose bounds must fit before active allocation end",
            "coherency": "valid marker is written last and invalidated on new checked background publication",
        }])
        self.assertEqual(report["wram_lifetime_aliases"], [{
            "owner": "actor-underlay cursor during live SC5LIVE actor composition",
            "address": "$7E5E82", "bytes": 14,
            "aliases": "RestoreRect debug-only width/height/destination/source witnesses plus the six-byte gap before video diagnostics",
            "lifetime": "RestoreRect bypasses its ROM row loop for live rooms; cursor use occurs only inside the underlay helpers",
            "coherency": "no simultaneous reader; persistent underlay pixels reside in the validated active-room tail",
        }])
        self.assertEqual(report["wram_cache_page2"], {
            "address": "$7F1000", "bytes": 0x800, "exclusive_with": [],
        })
        variables = next(row for row in report["regions"]
                         if row["owner"] == "generated_variables_and_stack_guard")
        self.assertEqual((variables["start"], variables["end_exclusive"]),
                         ("$7E0800", "$7E1000"))
        self.assertEqual(report["bwram_lifetime_aliases"], [{
            "owner": "SCUMM checked SC5VIS pixel staging",
            "address": "$410000", "bytes": 0xE000,
            "aliases": "Mode-3 encoded tile shadow",
            "lifetime": "incoming visual transfer through checked publication",
            "coherency": "full room present invalidates shadow before re-encoding",
        }, {
            "owner": "SCUMM actor chunk / live-room transaction",
            "address": "$4013C4", "bytes": 3132,
            "aliases": "exclusive owner field NONE/ACTOR/ROOM",
            "lifetime": "checked actor chunk until synchronous composition; complete room transaction otherwise",
            "coherency": "room request preempts actor; provider is drained before reuse",
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
        self.assertEqual((pending["offset"], pending["bytes"]), (0x3C4, 0x0C3C))
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

    def test_program_lookup_cannot_overwrite_identity_of_inflight_read(self) -> None:
        programs = (ROOT / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        memory = MEMORY.read_text()
        ensure = programs.split("ScummV5_MsuProgram_EnsureSelected_Far:", 1)[1].split(
            "ScummV5_MsuProgram_EnsureSelected_Far__find_slot:", 1
        )[0]
        allocator = programs.split("ScummV5_MsuProgram_EnsureSelected_Far__find_slot:", 1)[1].split(
            "ScummV5_MsuProgram_EnsureSelected_Far__choose0:", 1
        )[0]
        chosen = programs.split("ScummV5_MsuProgram_EnsureSelected_Far__chosen:", 1)[1].split(
            "ScummV5_MsuProgram_EnsureSelected_Far__directory_id_valid:", 1
        )[0]
        self.assertIn("SAME_SCUMM_MSU_PAGE_REQUEST_ID          = $7E2ECD", memory)
        self.assertIn("sta.l SAME_SCUMM_MSU_PAGE_REQUEST_ID", ensure)
        self.assertNotIn("sta.l SAME_SCUMM_MSU_CACHE_REQUEST_ID", ensure)
        self.assertIn("cmp #SAME_MSU1_STATE_READING", allocator)
        self.assertIn("ScummV5_MsuProgram_EnsureSelected_Far__pending", allocator)
        self.assertIn(
            "lda.l SAME_SCUMM_MSU_PAGE_REQUEST_ID\n"
            "    sta.l SAME_SCUMM_MSU_CACHE_REQUEST_ID",
            chosen,
        )

    def test_program_body_length_checks_the_upper_word_without_overlapping_destination(self) -> None:
        programs = (ROOT / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        memory = MEMORY.read_text()
        check = programs.split(
            "; The directory body remains the full logical source body.", 1
        )[1].split(
            "ScummV5_MsuProgram_EnsureSelected_Far__body_length_high_zero:", 1
        )[0]
        self.assertIn(".a16\n    ; REQUEST_LENGTH+2 is already the complete upper u16", check)
        self.assertIn("lda.l SAME_MSU1_REQUEST_LENGTH+2", check)
        self.assertNotIn("ora.l SAME_MSU1_REQUEST_LENGTH+3", check)
        self.assertIn("SAME_MSU1_REQUEST_LENGTH      = $7E2F08", memory)
        self.assertIn("SAME_MSU1_DESTINATION         = $7E2F0C", memory)

    def test_all_bytecode_windows_pinned_is_a_retryable_resource_wait(self) -> None:
        programs = (ROOT / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        saturated = programs.split(
            "ScummV5_MsuProgram_EnsureSelected_Far__exhausted:", 1
        )[1].split("ScummV5_MsuProgram_EnsureSelected_Far__pending:", 1)[0]
        self.assertIn("temporarily pinned", saturated)
        self.assertIn("jml ScummV5_MsuProgram_EnsureSelected_Far__pending", saturated)
        self.assertNotIn("SCUMM_ERR_RESIDENCY_EXHAUSTED", saturated)

    def test_nested_stopped_return_releases_its_transient_bytecode_pin(self) -> None:
        engine = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        return_path = engine.split(
            "ScummV5_Engine_Frame__return_success:", 1
        )[1].split("ScummV5_Engine_Frame__outer_return_success:", 1)[0]
        self.assertIn(".if SAME_BUILD_SCUMM_MSU1_PROGRAMS", return_path)
        self.assertIn("jsl ScummV5_MsuProgram_Leave_Far", return_path)
        self.assertLess(
            return_path.index("jsl ScummV5_MsuProgram_Leave_Far"),
            return_path.index("lda.l SAME_SCUMM_RETURN_MODE"),
        )
        self.assertIn("nested RETURN_MODE calls", return_path)
        self.assertIn("all cache pages became permanently", return_path)

    def test_m25a_nested_calls_suspend_and_reacquire_bytecode_pages(self) -> None:
        far = (ROOT / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        nested = far.split(
            "ScummV5_M23B_RunNestedChild_FarEntry:", 1
        )[1].split("ScummV5_M25A_RunNestedChild__success:", 1)[0]
        self.assertIn(".if SAME_BUILD_SCUMM_MSU1_PROGRAMS", nested)
        self.assertLess(
            nested.index("jsl ScummV5_MsuProgram_SuspendActive_Far"),
            nested.index("jsl ScummV5_M25A_FarCall_RunSelected"),
        )
        self.assertIn("SAME_SCUMM_MSU_PENDING_CHILD_SLOT", nested)
        self.assertIn("SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM", nested)
        self.assertLess(
            nested.index("lda.l SAME_SCUMM_C4_SLOT_PC,x"),
            nested.index("jsl ScummV5_MsuProgram_ResumeActive_Far"),
        )
        self.assertIn("SCUMM_VM_WAIT_RESOURCE", nested)
        self.assertIn("SCUMM_VM_ERROR", nested)

    def test_room_lifecycle_services_exact_pending_nested_child(self) -> None:
        engine = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        far = (ROOT / "runtime/snes/engines/scumm_v5_m24rb_far.pasm").read_text()
        lifecycle_far = (
            ROOT / "runtime/snes/engines/scumm_v5_msu_lifecycle_far.pasm"
        ).read_text()
        memory = MEMORY.read_text()
        lifecycle = engine.split(
            "ScummV5_Engine_Frame__m23a_run_room_script:", 1
        )[1].split("ScummV5_Engine_Frame__m23a_owner_slot_zero:", 1)[0]
        helper = lifecycle_far.split(
            "ScummV5_M23A_RunPendingLifecycleChild_FarEntry:", 1
        )[1]
        nested = far.split(
            "ScummV5_M23B_RunNestedChild_FarEntry:", 1
        )[1].split("ScummV5_M25A_RunNestedChild__success:", 1)[0]
        self.assertIn(
            "ScummV5_M23A_RunPendingLifecycleChild_FarEntry", lifecycle
        )
        self.assertIn("SAME_SCUMM_MSU_PENDING_CHILD_SLOT", helper)
        self.assertIn("SAME_SCUMM_C4_SLOT_STATUS,x", helper)
        self.assertIn("cmp #SCUMM_VM_RUNNING", helper)
        self.assertIn("cmp #SCUMM_VM_WAIT_RESOURCE", helper)
        self.assertIn("cmp #SCUMM_VM_YIELDED", helper)
        self.assertIn("ScummV5_M23A_RunSelected_FarThunk", helper)
        self.assertIn("ScummV5_M23A_SaveCurrentSlot_FarThunk", helper)
        self.assertIn(
            "ScummV5_M23A_RunSelected_FarThunk:\n    jsr ScummV5_Engine_RunSelected",
            engine,
        )
        self.assertIn("SAME_SCUMM_M23B_NEST_CHILD_SLOTS,x", nested)
        self.assertIn(
            "SAME_SCUMM_M23B_NEST_CHILD_SLOTS        = $7E5438",
            memory,
        )
        self.assertIn(
            "SAME_SCUMM_M23B_NEST_CHILD_SLOTS_END    = $7E5450",
            memory,
        )

    def test_bytecode_context_stack_uses_bounded_byte_indices(self) -> None:
        engine = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        enter = engine.split(
            "ScummV5_Engine_RunSelected__msu_depth_ok:", 1
        )[1].split("ScummV5_Engine_RunSelected__msu_select1:", 1)[0]
        programs = (ROOT / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        leave = programs.split(
            "ScummV5_MsuProgram_Leave_Far__active:", 1
        )[1].split("ScummV5_MsuProgram_Leave_Far__unpin1:", 1)[0]
        self.assertRegex(enter, r"sep #\$10\s+\.i8\s+tax")
        self.assertRegex(leave, r"sep #\$10\s+\.i8\s+tax")
        self.assertIn("bounded 25-entry continuation stack", enter)
        self.assertIn("saved parent cache context", leave)


    def test_completed_program_read_is_reconciled_before_room_read_starts(self) -> None:
        programs = (ROOT / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        live = (ROOT / "runtime/snes/engines/scumm_v5_msu_live_room.pasm").read_text()
        frame_ready = programs.split("ScummV5_MsuProgram_FrameReady_Far:", 1)[1].split(
            "ScummV5_MsuProgram_FrameReady_Far__room_failed:", 1
        )[0]
        live_start = live.split("ScummV5_MsuLiveRoom_Start_Far:", 1)[1].split(
            "ScummV5_MsuLiveRoom_Start_Far__metadata:", 1
        )[0]
        self.assertIn("jsl ScummV5_MsuProgram_ReconcileRead_Far", frame_ready)
        self.assertLess(
            frame_ready.index("jsl ScummV5_MsuProgram_ReconcileRead_Far"),
            frame_ready.index("jsl ScummV5_MsuRoom_Service_Far"),
        )
        self.assertIn("SAME_SCUMM_MSU_CACHE_REQUEST_SLOT", live_start)
        self.assertIn("ScummV5_MsuLiveRoom_Start_Far__wait", live_start)

    def test_completed_program_page_is_pinned_until_waiter_can_resume(self) -> None:
        programs = (ROOT / "runtime/snes/engines/scumm_v5_msu_programs.pasm").read_text()
        memory = MEMORY.read_text()
        reconcile = programs.split(
            "ScummV5_MsuProgram_ReconcileRead_Far__ready1:", 1
        )[1].split("ScummV5_MsuProgram_ReconcileRead_Far__count:", 1)[0]
        self.assertIn("SAME_SCUMM_MSU_CACHE_WAITER_SELECTOR0   = $7E2ED0", memory)
        self.assertIn("SAME_SCUMM_MSU_CACHE_WAITER_SLOT2       = $7E2ED5", memory)
        self.assertEqual(reconcile.count("ora #$80"), 3)
        self.assertNotIn("CACHE_COMPLETION_SLOT", programs + memory)
        allocator = programs.split(
            "ScummV5_MsuProgram_EnsureSelected_Far__find_slot:", 1
        )[1].split("ScummV5_MsuProgram_EnsureSelected_Far__read_idle:", 1)[0]
        request = programs.split("ScummV5_MsuProgram_EnsureSelected_Far__request:", 1)[1].split(
            "ScummV5_MsuProgram_EnsureSelected_Far__read_failed:", 1
        )[0]
        waiter_check = programs.split(
            "ScummV5_MsuProgram_ValidatePageWaiter_Far:", 1
        )[1].split("ScummV5_MsuProgram_ClearPageWaiter_Far:", 1)[0]
        release = programs.split(
            "ScummV5_MsuProgram_ReleasePageWaiter_Far:", 1
        )[1].split("ScummV5_MsuProgram_RecordPageWaiter_Far:", 1)[0]
        self.assertNotIn("CACHE_COMPLETION_SLOT", allocator)
        self.assertNotIn("completion_unclaimed", allocator)
        self.assertIn("SAME_MSU1_STATE_READING", allocator)
        self.assertIn("ScummV5_MsuProgram_RecordPageWaiter_Far", request)
        record = programs.split(
            "ScummV5_MsuProgram_RecordPageWaiter_Far:", 1
        )[1].split("ScummV5_MsuProgram_FrameReady_Far__provider:", 1)[0]
        self.assertIn("SAME_SCUMM_C4_SLOT_STATUS", waiter_check)
        self.assertIn("SAME_SCUMM_C4_SLOT_PROGRAM", waiter_check)
        self.assertIn("SAME_SCUMM_C4_SLOT_PROGRAM,x", record)
        self.assertNotIn("SAME_SCUMM_PROGRAM_SELECT", record)
        self.assertIn("SAME_SCUMM_MSU_CACHE_WAITER_SLOT0", release)
        self.assertIn("SAME_SCUMM_MSU_CACHE_WAITER_SELECTOR2", release)
        self.assertEqual(release.count("ScummV5_MsuProgram_ClearPageWaiter_Far"), 3)
        reset = programs.split("ScummV5_MsuProgram_Reset_Far:", 1)[1].split(
            "ScummV5_MsuProgram_Reset_Far__failed:", 1
        )[0]
        self.assertIn("sta.l SAME_SCUMM_MSU_CACHE_WAITER_SELECTOR0", reset)
        self.assertIn("sta.l SAME_SCUMM_MSU_CACHE_WAITER_SLOT2", reset)

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

    def test_third_checked_program_page_is_disjoint_from_variables_and_room_metadata(self) -> None:
        memory = MEMORY.read_text()
        self.assertIn("SAME_SCUMM_MSU_PROGRAM_CACHE2           = $7F1000", memory)
        self.assertIn("SAME_SCUMM_MSU_PROGRAM_CACHE2_END       = $7F1800", memory)
        report = audit_wram()
        self.assertEqual(report["wram_cache_page2"]["address"], "$7F1000")
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
        self.assertIn("SAME_SCUMM_MSU_PROGRAM_CACHE2_BANK      = $7F", MEMORY.read_text())
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

    def test_high_program_unit_ids_do_not_leak_accumulator_b_into_pool_indexes(self) -> None:
        source = RESOLVER.read_text(encoding="utf-8")
        candidate = source.split(
            "ScummV5_Resident_ResolveProgramUnit_Far__generation_ready:", 1
        )[1].split(
            "ScummV5_Resident_ResolveProgramUnit_Far__reuse:", 1
        )[0]
        set_valid = source.split(
            "ScummV5_Resident_ResolveProgramUnit_Far__set_valid:", 1
        )[1].split(
            "; Input X=pool index", 1
        )[0]
        pin = source.split("ScummV5_Resident_SetPin_Far:", 1)[1].split(
            "ScummV5_Resident_UnpinProgram_Far:", 1
        )[0]
        wide_pool_index = (
            "    rep #$20\n"
            "    .a16\n"
            "    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX\n"
            "    tax\n"
            "    sep #$20\n"
            "    .a8\n"
        )
        self.assertIn(wide_pool_index, candidate)
        self.assertIn(wide_pool_index, set_valid)
        self.assertIn(wide_pool_index, pin)

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
