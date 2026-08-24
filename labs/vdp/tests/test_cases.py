from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import ImageChops

from same_vdp.render import render_plane_a
from same_vdp.testsynth import CASES, write_case
from same_vdp.trace import read_trace
from same_vdp.translate import render_bundle, translate_plane_a
from same_vdp.vdp import VDPState


class SyntheticCasesTests(unittest.TestCase):
    def test_all_cases_render_and_translate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in CASES:
                trace_path = write_case(name, root / f"{name}.jsonl")
                trace = read_trace(trace_path)
                state = VDPState.from_trace(trace)
                self.assertEqual(render_plane_a(state).size, (256, 224))
                bundle = translate_plane_a(state, case_name=name)
                self.assertEqual(len(bundle.tilemap), 2048)
                self.assertEqual(len(bundle.cgram), 128)
                self.assertGreater(len(bundle.tiles), 0)
                expected_snes = render_plane_a(state, "snes")
                translated_snes = render_bundle(bundle)
                self.assertIsNone(ImageChops.difference(expected_snes, translated_snes).getbbox(), name)


if __name__ == "__main__":
    unittest.main()
