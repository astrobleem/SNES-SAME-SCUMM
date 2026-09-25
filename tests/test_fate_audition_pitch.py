import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fate_audition_pitch import ExpectedNote, validate_capture_pitch


class FateAuditionPitchTests(unittest.TestCase):
    @staticmethod
    def _write_tone(path: Path, frequency: float) -> None:
        rate = 48000
        samples = [round(12000 * math.sin(2 * math.pi * frequency * i / rate))
                   for i in range(rate)]
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    def test_known_note_passes_tight_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            self._write_tone(path, 440.0)
            result = validate_capture_pitch(
                path, (ExpectedNote("A4", 0.0, 440.0),),
                spc_sample_rate=32000.0, tolerance_cents=3.0,
            )
        self.assertEqual(result[0]["result"], "pass")
        self.assertLess(abs(result[0]["error_cents"]), 0.1)

    def test_detuned_note_fails_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            self._write_tone(path, 450.0)
            result = validate_capture_pitch(
                path, (ExpectedNote("A4", 0.0, 440.0),),
                spc_sample_rate=32000.0, tolerance_cents=3.0,
            )
        self.assertEqual(result[0]["result"], "fail")
        self.assertGreater(result[0]["error_cents"], 30.0)


if __name__ == "__main__":
    unittest.main()
