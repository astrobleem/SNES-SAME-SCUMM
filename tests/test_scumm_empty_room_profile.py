from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EmptyRoomProfileTests(unittest.TestCase):
    def test_empty_synthetic_manifest_generates_complete_safe_tables(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            manifest = ROOT / "examples/resources/scumm_v5/empty_cooked_rooms.json"
            command = [
                sys.executable,
                str(ROOT / "tools/generate_snes_cooked_rooms.py"),
                "--manifest", str(manifest),
                "--output", str(output / "rooms.inc.pasm"),
                "--data-output", str(output / "room-data.inc.pasm"),
                "--binary-dir", str(output / "segments"),
                "--report", str(output / "report.json"),
            ]
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)

            rooms = (output / "rooms.inc.pasm").read_text()
            data = (output / "room-data.inc.pasm").read_text()
            report = json.loads((output / "report.json").read_text())
            self.assertIn("SCUMM_V5_NUM_GLOBAL_SCRIPTS = $00C8", rooms)
            self.assertIn("SCUMM_M23A_ROOM_COUNT = $00", rooms)
            self.assertIn("SCUMM_M23A_PROGRAM_FIRST = $00", rooms)
            self.assertIn("SCUMM_M23A_PROGRAM_COUNT = $00", rooms)
            self.assertIn("ScummV5_M23A_FindRoom:", rooms)
            self.assertIn("ScummV5_M23A_ResolveLocalScript:", rooms)
            self.assertIn("ScummV5_M23A_ValidateRecord:", rooms)
            self.assertIn("ScummV5_M23A_ResolveGlobalScript_Far:", data)
            self.assertEqual(report["rooms"], [])
            self.assertEqual(report["programs"], 0)
            self.assertEqual(list((output / "segments").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
