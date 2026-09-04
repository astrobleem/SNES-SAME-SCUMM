from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M24RATadTransitionTests(unittest.TestCase):
    def test_patch_is_bounded_and_driver_tick_observed(self) -> None:
        patch = (ROOT / "audio/m24ra/terrific_audio_driver_m24ra.patch").read_text(encoding="utf-8")
        self.assertIn("call same_process_layer_transition", patch)
        self.assertLess(patch.index("call same_process_layer_transition"), patch.index("mov A, pendingNon_music"))
        self.assertIn("sameTransitionAdmissionTicks", patch)
        self.assertIn(".db 19, 38, 63, 94, 125", patch)
        self.assertIn(".db 7, 6, 5, 4, 3", patch)
        self.assertIn("[subroutineTable_l]", patch)
        self.assertIn("[subroutineTable_h]", patch)
        self.assertIn("tclr1 sameTransitionGroupAMask", patch)
        self.assertIn("and A, sameTransitionGroupAMask", patch)
        self.assertIn("sameTransitionCurrentGeneration", patch)
        self.assertNotIn("second interpreter", patch.lower())

    def test_fixture_holds_all_outgoing_streams_inside_notes(self) -> None:
        mml = (ROOT / "audio/m24ra/m24ra_async_layer_transition.mml").read_text(encoding="utf-8")
        for channel in "ABCDEFGH":
            self.assertIn(f"{channel} @0 V48", mml)
        self.assertEqual(mml.count("%4000"), 8)
        positions = [mml.index(f"!b_lane_{index}") for index in range(5)]
        self.assertEqual(positions, sorted(positions))

    def test_catalog_contains_only_the_synthetic_song(self) -> None:
        catalog = json.loads((ROOT / "audio/m24ra/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema"], "same_compiled_music_catalog_v1")
        self.assertEqual(len(catalog["entries"]), 1)
        entry = catalog["entries"][0]
        self.assertEqual(entry["logical_id"], 1)
        self.assertEqual(entry["compiled_song"], "m24ra_async_layer_transition")
        self.assertEqual(entry["compiled_song_id"], 1)
        self.assertTrue(entry["source_resource"].startswith("synthetic."))
