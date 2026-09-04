from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from same.snes_carrier import default_carrier, layout_regions, load_carrier


ROOT = Path(__file__).resolve().parents[1]


def load_generator():
    path = ROOT / "tools/generate_snes_carrier.py"
    spec = importlib.util.spec_from_file_location("generate_snes_carrier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tool(name: str):
    path = ROOT / f"tools/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SnesCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()

    def test_ordinary_lorom_is_default_and_exact(self) -> None:
        self.assertEqual(default_carrier(ROOT), "lorom")
        carrier = load_carrier(ROOT, "lorom", save_enabled=True)
        self.assertEqual(
            (
                carrier.carrier_id,
                carrier.map_mode,
                carrier.cartridge_type,
                carrier.ram_size,
                carrier.save_base,
                carrier.save_bytes,
            ),
            (0, 0x20, 0x02, 0x01, 0x700000, 0x0800),
        )

    def test_sa1_layout_is_exact_nonoverlapping_and_complete(self) -> None:
        carrier = load_carrier(ROOT, "sa1_bwram", save_enabled=True)
        self.assertEqual(
            (
                carrier.carrier_id,
                carrier.map_mode,
                carrier.cartridge_type,
                carrier.ram_size,
                carrier.save_base,
                carrier.save_bytes,
            ),
            (1, 0x23, 0x35, 0x07, 0x400800, 0x0800),
        )
        assert carrier.layout is not None
        regions = layout_regions(carrier.layout)
        self.assertEqual(regions[0].address, 0x400000)
        self.assertEqual(regions[-1].end, 0x420000)
        self.assertEqual(sum(region.size for region in regions), 0x20000)
        for left, right in zip(regions, regions[1:]):
            self.assertLessEqual(left.end, right.address)

    def test_generated_ordinary_carrier_emits_no_boot_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.json"
            self.generator.generate(
                carrier_name="lorom",
                save_enabled=True,
                rom_size_code=0x09,
                output_dir=root,
                manifest_path=manifest_path,
            )
            self.assertEqual(
                (root / "carrier_header.inc.pasm").read_text(encoding="utf-8").splitlines()[1:],
                [".byte $20", ".byte $02", ".byte $09", ".byte $01"],
            )
            boot = (root / "carrier_boot.inc.pasm").read_text(encoding="utf-8")
            self.assertNotIn("lda", boot)
            self.assertNotIn(".bank", (root / "carrier_code.inc.pasm").read_text())
            self.assertIn("SAME_SAVE_STORAGE_BASE = $700000", (root / "carrier_constants.inc.pasm").read_text())

    def test_generated_sa1_carrier_binds_reset_layout_control_and_save(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.json"
            manifest = self.generator.generate(
                carrier_name="sa1_bwram",
                save_enabled=True,
                rom_size_code=0x09,
                output_dir=root,
                manifest_path=manifest_path,
            )
            self.assertEqual(
                (root / "carrier_header.inc.pasm").read_text(encoding="utf-8").splitlines()[1:],
                [".byte $23", ".byte $35", ".byte $09", ".byte $07"],
            )
            constants = (root / "carrier_constants.inc.pasm").read_text(encoding="utf-8")
            for line in (
                "SAME_SAVE_STORAGE_BASE = $400800",
                "SAME_BWRAM_SURFACE_BASE = $402000",
                "SAME_BWRAM_TILE_SHADOW_BASE = $410000",
                "SAME_BWRAM_CGRAM_SHADOW_BASE = $41E000",
            ):
                self.assertIn(line, constants)
            boot = (root / "carrier_boot.inc.pasm").read_text(encoding="utf-8")
            self.assertIn("jsl Same_Carrier_Boot", boot)
            code = (root / "carrier_code.inc.pasm").read_text(encoding="utf-8")
            self.assertIn(".bank 14", code)
            self.assertIn("lda #$20\n    sta $2200", code)
            self.assertNotIn("sta $2200\n    lda #$00", code)
            self.assertNotIn("$2230", code)
            self.assertEqual(manifest["save"], {"base": "400800", "bytes": 2048})

    def test_finalizer_rejects_carrier_header_conflict(self) -> None:
        raw = bytearray(0x8000)
        raw[0x7FC0:0x7FD0] = b"SAME ENGINE HOST"
        raw[0x7FD5:0x7FD9] = bytes((0x20, 0x02, 0x09, 0x01))
        finalizer = load_tool("finalize_snes_rom")

        with self.assertRaisesRegex(ValueError, "conflicts"):
            finalizer._validate_carrier_header(
                bytes(raw), carrier="sa1_bwram", manifest=None
            )

    def test_sa1_finalizer_requires_exact_final_size_code(self) -> None:
        finalizer = load_tool("finalize_snes_rom")
        raw = bytearray(0x40000)
        raw[0x7FD5:0x7FD9] = bytes((0x23, 0x35, 0x09, 0x07))
        with self.assertRaisesRegex(ValueError, "ROM size code"):
            finalizer.finalize(bytes(raw), carrier="sa1_bwram")
        raw[0x7FD7] = 0x08
        self.assertEqual(len(finalizer.finalize(bytes(raw), carrier="sa1_bwram")), 0x40000)

    def test_save_service_uses_generated_carrier_base_only(self) -> None:
        storage = (ROOT / "runtime/snes/services/storage.pasm").read_text(encoding="utf-8")
        self.assertIn("SAME_SAVE_STORAGE_BASE", storage)
        self.assertNotIn("$700000", storage)
        self.assertNotIn("$400800", storage)

    def test_engines_are_carrier_blind_and_video_abi_remains_unwired(self) -> None:
        engine_sources = list((ROOT / "runtime/snes/engines").glob("*.pasm"))
        for path in engine_sources:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("SAME_CARRIER", text, str(path))
            self.assertNotIn("SAME_BWRAM", text, str(path))
            self.assertNotRegex(text, r"\$(?:40|41)[0-9A-Fa-f]{4}", str(path))
        host_abi = (ROOT / "runtime/snes/engine/host.pasm").read_text(encoding="utf-8")
        self.assertNotIn("SAME_VIDEO_OP_SURFACE_UPLOAD", host_abi)
        boot_template = (ROOT / "tools/generate_snes_carrier.py").read_text(encoding="utf-8")
        self.assertNotIn("$2230", boot_template)
        self.assertNotIn("mailbox", boot_template.lower())


if __name__ == "__main__":
    unittest.main()
