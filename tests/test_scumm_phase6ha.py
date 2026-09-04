from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest
import zipfile

from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.resources import MemoryResourceProvider


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
ARCHIVE = Path("/home/chad/fatedemo-box.zip")
SCRIPT14_SHA256 = "ee6b379d25e4ace9772673b05bb40d2f428dd2c0bd9142a8f53d85005fb4e371"


class Phase6HAScriptDeliveryTests(unittest.TestCase):
    def test_profile_owns_script_closure_and_bounded_execution_gate(self) -> None:
        raw = json.loads(PROFILE.read_text())
        options = raw["options"]
        self.assertEqual(options["snes_global_script_sets"]["phase6ha"],
                         [2, 14, 144, 145, 151])
        self.assertEqual(
            options["snes_execution_gates"]["phase6ha"],
            {"hold_after_started_global_script": 14},
        )

    @unittest.skipUnless(ARCHIVE.is_file(), "user-supplied Fate demo archive unavailable")
    def test_authentic_script14_is_a_complete_source_global(self) -> None:
        with zipfile.ZipFile(ARCHIVE) as archive:
            raw = {
                "game.index": archive.read("FATEDEMO/PLAYFATE.000"),
                "game.data": archive.read("FATEDEMO/PLAYFATE.001"),
            }
        profile = load_profile(PROFILE, verify_resources=False)
        provider = LucasartsScummV5ResourceProvider(
            MemoryResourceProvider(raw), parse_game_policy(profile),
        )
        self.assertEqual(provider.global_script_count, 200)
        payload = provider.read("script.14")
        self.assertEqual(len(payload), 258)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), SCRIPT14_SHA256)

    def test_start_script_has_no_outer_room_lifecycle_gate_or_script14_case(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        start = source.index("ScummV5_Op_StartScript:")
        end = source.index("ScummV5_Op_ChainScript:", start)
        body = source[start:end]
        prefix = body[:body.index("ScummV5_Op_StartScript__c4:")]
        self.assertNotIn("SAME_SCUMM_RETURN_MODE", prefix)
        self.assertNotIn("SAME_SCUMM_M23A_PHASE", prefix)
        self.assertNotIn("cmp #$0E", body)
        self.assertNotIn("RunScript14", body)
        self.assertIn("SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_PROGRAM", body)


if __name__ == "__main__":
    unittest.main()
