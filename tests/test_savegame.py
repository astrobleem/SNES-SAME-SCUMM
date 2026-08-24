from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from same.errors import SaveFormatError
from same.savegame import DirectorySaveStore, SaveEnvelope


class SaveGameTests(unittest.TestCase):
    def test_envelope_roundtrip(self) -> None:
        envelope = SaveEnvelope("scumm_v5", "monkey1", 3, b"state")
        self.assertEqual(SaveEnvelope.unpack(envelope.pack()), envelope)

    def test_envelope_corruption_fails(self) -> None:
        raw = bytearray(SaveEnvelope("agi_v2", "kq1", 1, b"state").pack())
        raw[-1] ^= 0xFF
        with self.assertRaises(SaveFormatError):
            SaveEnvelope.unpack(raw)

    def test_directory_store_atomic_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = DirectorySaveStore(Path(temporary), "test-game")
            store.write(2, b"save")
            self.assertEqual(store.list_slots(), (2,))
            self.assertEqual(store.read(2), b"save")
            store.delete(2)
            self.assertEqual(store.list_slots(), ())


if __name__ == "__main__":
    unittest.main()
