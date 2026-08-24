from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import wave

from same.audio import (
    ChipWrite,
    SN76489,
    demo_trace,
    read_trace,
    render_sn76489,
    write_trace,
    write_wav,
)


class AudioTests(unittest.TestCase):
    def test_psg_latch_and_data_write(self) -> None:
        psg = SN76489()
        # Tone 0 period = 0x123; volume = 2.
        psg.write(0x80 | 0x03)
        psg.write(0x12)
        psg.write(0x90 | 0x02)
        self.assertEqual(psg.tone_period[0], 0x123)
        self.assertEqual(psg.volume[0], 2)
        self.assertGreater(psg.tone_frequency(0), 0)

    def test_noise_write(self) -> None:
        psg = SN76489()
        psg.write(0xE7)
        psg.write(0xF0)
        self.assertEqual(psg.noise_control, 7)
        self.assertEqual(psg.volume[3], 0)

    def test_trace_roundtrip_and_wav(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trace = root / "trace.jsonl"
            wav_path = root / "demo.wav"
            writes = demo_trace()
            write_trace(trace, writes)
            self.assertEqual(read_trace(trace), writes)
            pcm = render_sn76489(writes, duration=1.25, sample_rate=22050)
            self.assertEqual(len(pcm), round(1.25 * 22050) * 2)
            self.assertNotEqual(set(pcm), {0})
            write_wav(wav_path, pcm, 22050)
            with wave.open(str(wav_path), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertEqual(wav.getframerate(), 22050)

    def test_renderer_rejects_wrong_chip(self) -> None:
        with self.assertRaises(Exception):
            render_sn76489(
                [ChipWrite(at=0, chip="ym2612", address=0x28, value=0xF0)],
                duration=0.1,
            )


if __name__ == "__main__":
    unittest.main()
