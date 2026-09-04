from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/generate_fate_tad_layout.py"
TABLE_OFFSET = 116 + 3218
BIAS = 51


def fixture(size: int) -> bytes:
    data = bytearray(size)
    data[TABLE_OFFSET:TABLE_OFFSET + 3] = (TABLE_OFFSET + 8).to_bytes(3, "little")
    data[TABLE_OFFSET + 3:TABLE_OFFSET + 6] = (TABLE_OFFSET + 16).to_bytes(3, "little")
    data[TABLE_OFFSET + 6:TABLE_OFFSET + 8] = (size + BIAS).to_bytes(2, "little")
    return bytes(data)


class FateTadLayoutTests(unittest.TestCase):
    def run_layout(self, size: int) -> tuple[str, bytes, bytes]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "fate-tad.bin"
            enums = root / "fate-tad.inc"
            output = root / "layout.inc.pasm"
            binary.write_bytes(fixture(size))
            enums.write_text(
                "!LAST_SONG_ID = 1\n!Song_BLANK = 0\n!Song_fate_sound_172 = 1\n",
                encoding="utf-8",
            )
            subprocess.run(
                [sys.executable, str(SCRIPT), str(binary), str(enums), str(output)],
                check=True, capture_output=True, text=True,
            )
            return (
                output.read_text(encoding="utf-8"),
                (root / "fate-tad-bank1.bin").read_bytes(),
                (root / "fate-tad-bank2.bin").read_bytes(),
            )

    def test_single_bank_emits_nonempty_incbin_sentinel(self) -> None:
        text, bank1, bank2 = self.run_layout(4000)
        self.assertEqual(len(bank1), 4000)
        self.assertEqual(bank2, b"\x00")
        self.assertIn("SAME_TAD_AUDIO_DATA_SIZE     = $0FA0", text)
        self.assertIn("SAME_TAD_BLANK_OFFSET        = $8001", text)
        self.assertIn("SAME_TAD_SONG_FATE_SOUND_172 = $01", text)

    def test_two_bank_layout_retains_exact_high_data(self) -> None:
        text, bank1, bank2 = self.run_layout(33000)
        self.assertEqual(len(bank1), 0x8000)
        self.assertEqual(len(bank2), 232)
        self.assertIn("SAME_TAD_AUDIO_DATA_SIZE     = $80E8", text)
        self.assertIn("SAME_TAD_BLANK_OFFSET        = $80E8", text)


if __name__ == "__main__":
    unittest.main()
