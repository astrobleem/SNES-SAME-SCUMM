from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "runtime/snes/engines"


class ScummV5ArchitectureTests(unittest.TestCase):
    """SCUMM may request presentation, but must not select its realization."""

    FORBIDDEN = (
        re.compile(r"\b(?:BG[0-9]+SC|BG12NBA|INIDISP|CGADSUB|VMAIN|VMADDL|VMADDH|VMDATAL|VMDATAH|OAMADDL|OAMDATA|NMITIMEN|MDMAEN|HDMAEN)\b"),
        re.compile(r"SAME_VIDEO_OVERLAY_BG2"),
        re.compile(r"SAME_MODE3_|Same_Mode3_"),
        re.compile(r"SAME_BWRAM_"),
        re.compile(r"\b(?:VRAM|CGRAM|OAM|DMA)\b"),
    )

    def test_production_scumm_sources_have_no_backend_or_carrier_dependencies(self) -> None:
        violations: list[str] = []
        for path in sorted(ENGINE_DIR.glob("scumm_v5*.pasm")):
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                for pattern in self.FORBIDDEN:
                    if pattern.search(line):
                        violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")
        self.assertEqual([], violations, "SCUMM presentation boundary violations:\n" + "\n".join(violations))

    def test_compositor_uses_target_neutral_surface_contract(self) -> None:
        source = (ENGINE_DIR / "scumm_v5_controller_far.pasm").read_text()
        self.assertIn("Same_VideoSurface_WriteIndexedPixel_Far", source)
        self.assertIn("Same_VideoSurface_CanWrite_Far", source)
        self.assertNotIn("SAME_BWRAM_SURFACE_BASE", source)

    def test_talk_uses_target_neutral_text_service(self) -> None:
        source = (ENGINE_DIR / "scumm_v5_matrix_far.pasm").read_text()
        self.assertIn("Same_VideoText_ShowSegment_Far", source)
        self.assertIn("Same_VideoText_Hide_Far", source)
        self.assertNotIn("Same_VideoOverlay_", source)


if __name__ == "__main__":
    unittest.main()
