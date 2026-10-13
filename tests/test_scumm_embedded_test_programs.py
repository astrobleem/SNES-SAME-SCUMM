from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.generate_engine_fixtures import poppy_fixture_include


ROOT = Path(__file__).resolve().parents[1]


class EmbeddedTestProgramBuildTests(unittest.TestCase):
    def test_engine_selection_defaults_to_embedded_conformance_programs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="same-scumm-test-programs-") as raw:
            output = Path(raw) / "active_engine.inc.pasm"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/generate_snes_engine_selection.py"),
                    "--engine", "scumm_v5",
                    "--output", str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            config = output.with_name("build_config.inc.pasm").read_text()
        self.assertIn("SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS = $01", config)

    def test_source_backed_build_can_disable_embedded_program_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="same-scumm-test-programs-") as raw:
            output = Path(raw) / "active_engine.inc.pasm"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/generate_snes_engine_selection.py"),
                    "--engine", "scumm_v5", "--scumm-m23a",
                    "--scumm-disable-embedded-test-programs",
                    "--output", str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            config = output.with_name("build_config.inc.pasm").read_text()
        self.assertIn("SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS = $00", config)

    def test_disabling_embedded_programs_requires_source_backed_room_service(self) -> None:
        with tempfile.TemporaryDirectory(prefix="same-scumm-test-programs-") as raw:
            output = Path(raw) / "active_engine.inc.pasm"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/generate_snes_engine_selection.py"),
                    "--engine", "scumm_v5",
                    "--scumm-disable-embedded-test-programs",
                    "--output", str(output),
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires SCUMM v5 M23A source programs", result.stderr)

    def test_generated_fixture_bodies_and_fixture_requests_are_gated(self) -> None:
        include = poppy_fixture_include(b"\x00", [("extended", b"\x11\x22")])
        self.assertIn(
            "ScummV5_Conformance_Program:\n"
            ".if SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS\n"
            "    .byte $00\n"
            ".endif",
            include,
        )
        self.assertIn(
            "ScummV5_C2_Program_extended:\n"
            ".if SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS\n"
            "    .byte $11,$22\n"
            ".endif",
            include,
        )
        self.assertIn(
            ".else\nSCUMM_C2_FIXTURE_COUNT = $00\n.endif",
            include,
        )

    def test_missing_source_program_does_not_fall_through_to_fixture_bytes(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        size = source[source.index("ScummV5_GetProgramSize:\n"):
                      source.index("ScummV5_FetchSelectedByteAtX:\n")]
        fetch = source[source.index("ScummV5_FetchSelectedByteAtX:\n"):
                       source.index("; The generated include retains fixture identities")]
        for routine, miss_edge, sentinel in (
            (size, "bcs", "ScummV5_GetProgramSize__m23a"),
            (fetch, "bcc", "ScummV5_FetchSelectedByteAtX__m23a"),
        ):
            miss = routine.index(miss_edge + " " + sentinel)
            error = routine.index(".if SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS == 0", miss)
            self.assertLess(error, routine.index("cmp #SCUMM_C2_FIXTURE_EXTENDED", error))
            self.assertIn("lda #SCUMM_ERR_RESOURCE", routine[error:])
            self.assertIn("jsr ScummV5_SetError", routine[error:])

    def test_build_script_validates_and_forwards_the_layout_option(self) -> None:
        source = (ROOT / "tools/build_snes.sh").read_text()
        self.assertIn("SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS must be 0 or 1", source)
        self.assertIn("ENGINE_SELECTION_ARGS+=(--scumm-disable-embedded-test-programs)", source)


if __name__ == "__main__":
    unittest.main()
