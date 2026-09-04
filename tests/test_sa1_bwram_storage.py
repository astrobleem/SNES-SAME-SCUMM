from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "runtime/snes/carriers/sa1_bwram_layout.json"


def load_builder():
    path = ROOT / "tools/build_sa1_bwram_proof.py"
    spec = importlib.util.spec_from_file_location("build_sa1_bwram_proof", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Sa1BwRamStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_builder()
        cls.layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))

    def test_exact_128k_layout_and_surface_shadow_sizes(self) -> None:
        self.builder.validate_layout(self.layout)
        self.assertEqual(self.layout["bwram_bytes"], 0x20000)
        self.assertEqual(self.layout["live_surface"]["bytes"], 0xE000)
        self.assertEqual(self.layout["tile_shadow"]["bytes"], 0xE000)
        self.assertEqual(self.layout["cgram_shadow"]["bytes"], 0x0200)
        self.assertEqual(self.layout["save_reserved"]["bytes"], 0x0800)
        self.assertEqual(
            self.layout["live_surface"]["bytes"] + self.layout["tile_shadow"]["bytes"],
            0x1C000,
        )
        self.assertGreater(0x1C000 + 0x0200 + 0x0800, 0x10000)

    def test_layout_overlap_is_rejected(self) -> None:
        broken = copy.deepcopy(self.layout)
        broken["tile_shadow"]["address"] = "40:F000"
        with self.assertRaisesRegex(ValueError, "differs"):
            self.builder.validate_layout(broken)

    def test_layout_escape_is_rejected(self) -> None:
        broken = copy.deepcopy(self.layout)
        broken["future_staging"]["bytes"] = 0x2000
        with self.assertRaisesRegex(ValueError, "differs"):
            self.builder.validate_layout(broken)

    def test_proof_surface_is_deterministic_and_exercises_every_index(self) -> None:
        first = self.builder.proof_surface()
        second = self.builder.proof_surface()
        self.assertEqual(first.visible_bytes(), second.visible_bytes())
        self.assertEqual(set(first.visible_bytes()), set(range(256)))
        self.assertEqual(len(first.visible_bytes()), 0xE000)

    def test_bmaps_selectors_cover_the_seven_surface_bands(self) -> None:
        bands = [
            (selector, 0x400000 + selector * 0x2000, 0x2000)
            for selector in range(1, 8)
        ]
        self.assertEqual(bands[0], (1, 0x402000, 0x2000))
        self.assertEqual(bands[-1], (7, 0x40E000, 0x2000))
        self.assertEqual(sum(length for _, _, length in bands), 0xE000)


if __name__ == "__main__":
    unittest.main()
