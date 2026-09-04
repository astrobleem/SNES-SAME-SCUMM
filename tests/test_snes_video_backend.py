from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from same.snes_surface import PaletteRange
from same.snes_video_backend import (
    PaletteWritePacket,
    SurfaceDirtyPacket,
    combined_dma_plan,
    default_video_backend,
    load_video_backend,
    mode3_dma_batches,
    validate_present,
)
from same.video import Rect


ROOT = Path(__file__).resolve().parents[1]


def load_generator():
    path = ROOT / "tools/generate_snes_video_backend.py"
    spec = importlib.util.spec_from_file_location("generate_snes_video_backend", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SnesVideoBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()

    def test_default_and_carrier_compatibility(self) -> None:
        self.assertEqual(default_video_backend(ROOT), "legacy_backdrop")
        self.assertEqual(load_video_backend(ROOT, "legacy_backdrop", carrier="lorom").backend_id, 0)
        with self.assertRaisesRegex(ValueError, "requires carrier sa1_bwram"):
            load_video_backend(ROOT, "mode3_surface", carrier="lorom")
        mode3 = load_video_backend(ROOT, "mode3_surface", carrier="sa1_bwram")
        self.assertEqual(mode3.backend_id, 1)
        self.assertIsNotNone(mode3.layout)

    def test_generated_legacy_hooks_emit_no_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            self.generator.generate(
                backend_name="legacy_backdrop",
                carrier_name="lorom",
                output_dir=output,
                manifest_path=output / "manifest.json",
            )
            for name in ("boot", "frame", "reset", "service", "commit", "code"):
                text = (output / f"video_backend_{name}.inc.pasm").read_text()
                self.assertNotIn("jsr ", text)
                self.assertNotIn("jsl ", text)
            self.assertEqual((output / "video_backend_mode3_tilemap.bin").read_bytes(), b"")

    def test_generated_mode3_contract_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            result = self.generator.generate(
                backend_name="mode3_surface",
                carrier_name="sa1_bwram",
                output_dir=output,
                manifest_path=output / "manifest.json",
            )
            constants = (output / "video_backend_constants.inc.pasm").read_text()
            self.assertIn("SAME_MODE3_LIVE_PALETTE = $41E200", constants)
            self.assertIn("SAME_MODE3_TILE_SCRATCH = $41E6B0", constants)
            self.assertIn("SAME_VIDEO_ACTIVE_CONVERT_TILE_BUDGET = $0004", constants)
            self.assertEqual(len((output / "video_backend_mode3_tilemap.bin").read_bytes()), 2048)
            self.assertEqual(result["carrier"], "sa1_bwram")

    def test_surface_dirty_wire_and_clipping(self) -> None:
        packet = SurfaceDirtyPacket(250, 220, 20, 20)
        self.assertEqual(SurfaceDirtyPacket.unpack(packet.arg0, packet.arg1), packet)
        self.assertEqual(packet.clipped(), Rect(250, 220, 6, 4))
        self.assertIsNone(SurfaceDirtyPacket(300, 300, 1, 1).clipped())
        with self.assertRaisesRegex(ValueError, "nonzero"):
            SurfaceDirtyPacket(0, 0, 0, 1).clipped()

    def test_palette_and_present_validation(self) -> None:
        packet = PaletteWritePacket(250, 6)
        packet.validate()
        self.assertEqual(packet.arg0, 250 | 6 << 16)
        for bad in (PaletteWritePacket(0, 0), PaletteWritePacket(255, 2), PaletteWritePacket(256, 1)):
            with self.assertRaises(ValueError):
                bad.validate()
        with self.assertRaises(ValueError):
            packet.validate(1)
        validate_present(2, 0, 1, True)
        for args in ((0, 0, 0, True), (1, 0, 1, True), (2, 1, 1, True), (2, 0, 1, False)):
            with self.assertRaises(ValueError):
                validate_present(*args)

    def test_palette_first_combined_dma_plan(self) -> None:
        palettes, runs, pending = combined_dma_plan(
            (PaletteRange(0, 256),), range(33)
        )
        self.assertEqual(palettes, (PaletteRange(0, 256),))
        self.assertEqual([(item.first_tile, item.tile_count) for item in runs], [(0, 24)])
        self.assertEqual(pending, tuple(range(24, 33)))
        palettes, runs, pending = combined_dma_plan((), (0, 2, 4, 6, 8, 10, 12, 14, 16))
        self.assertEqual(len(runs), 8)
        self.assertEqual(pending, (16,))

    def test_production_batch_plan_retains_budget_and_descriptor_overflow(self) -> None:
        batches = mode3_dma_batches((PaletteRange(0, 256),), range(33))
        self.assertEqual(
            [(batch.byte_length,
              [(item.first_color, item.color_count) for item in batch.palette_ranges],
              [(item.first_tile, item.tile_count) for item in batch.tile_runs])
             for batch in batches],
            [(512, [(0, 256)], []), (2048, [], [(0, 32)]), (64, [], [(32, 1)])],
        )
        batches = mode3_dma_batches((), (0, 2, 4, 6, 8, 10, 12, 14, 32))
        self.assertEqual(
            [[(item.first_tile, item.tile_count) for item in batch.tile_runs]
             for batch in batches],
            [[(0, 1), (2, 1), (4, 1), (6, 1), (8, 1), (10, 1), (12, 1), (14, 1)],
             [(32, 1)]],
        )

    def test_production_backend_is_target_and_engine_isolated(self) -> None:
        for relative in (
            "src/same/engines/scumm_v5/engine.py",
            "src/same/engines/scumm_v5/video.py",
            "src/same/engines/agi/engine.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("mode3_surface", text)
            self.assertNotIn("SAME_MODE3", text)
        host_video = (ROOT / "src/same/video.py").read_text(encoding="utf-8")
        for address in ("40:2000", "41:0000", "41:E000", "$402000", "$410000"):
            self.assertNotIn(address, host_video)
        target = (ROOT / "runtime/snes/services/video_mode3.pasm").read_text(encoding="utf-8")
        self.assertNotIn("$2230", target)  # SA-1 DMA remains unused.
        self.assertNotIn("SAME_VIDEO_OP_SURFACE_CREATE", target)
        self.assertNotIn("SAME_VIDEO_OP_SURFACE_UPLOAD", target)
        dma = (ROOT / "runtime/snes/kernel/dma.pasm").read_text(encoding="utf-8")
        self.assertIn("DMAP7", dma)
        self.assertIn("MDMAEN", dma)


if __name__ == "__main__":
    unittest.main()
