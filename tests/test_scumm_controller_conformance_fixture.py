import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from same.engines.scumm_v5.cooked_room import decode_cooked_room
from same.engines.scumm_v5.room import decode_room


ROOT = Path(__file__).resolve().parents[1]


class ControllerConformanceFixtureTests(unittest.TestCase):
    def test_round_trip_preserves_source_object_and_script_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                [sys.executable, str(ROOT / "tools/build_scumm_controller_conformance.py"), "--output-dir", directory],
                check=True, capture_output=True, text=True,
            )
            manifest = json.loads((Path(directory) / "manifest.json").read_text())
            record = decode_cooked_room((Path(directory) / "room-1.sc5c").read_bytes(), expected_room=1)
            room = decode_room(record.room_payload, key="room.1")
            self.assertEqual(room.objects[0].object_id, 7)
            self.assertEqual(room.objects[0].object_name, b"test console")
            self.assertEqual(room.objects[0].authored_verbs, (3,))
            self.assertNotEqual(room.objects[0].verb_entrypoint(3), 0)
            self.assertEqual([item.number for item in record.locals], [200])
            self.assertEqual(manifest["copyright"], "original copyright-free controller conformance fixture")


if __name__ == "__main__":
    unittest.main()
