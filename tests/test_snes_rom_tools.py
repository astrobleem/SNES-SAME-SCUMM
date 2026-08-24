from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from finalize_snes_rom import finalize  # noqa: E402


class SnesRomToolTests(unittest.TestCase):
    def test_finalize_pads_and_writes_real_checksum(self) -> None:
        raw = bytearray(0x7FE0)
        raw[0x7FC0 : 0x7FC0 + 16] = b"SAME ENGINE HOST"
        raw[0x7FD5] = 0x20
        raw[0x7FFC:0x7FFE] = (0x8000).to_bytes(2, "little")
        image = finalize(bytes(raw))
        self.assertEqual(len(image), 0x8000)
        complement = int.from_bytes(image[0x7FDC:0x7FDE], "little")
        checksum = int.from_bytes(image[0x7FDE:0x7FE0], "little")
        self.assertEqual(checksum ^ complement, 0xFFFF)
        self.assertEqual(checksum, sum(image) & 0xFFFF)

    def test_audit_rejects_content_corruption(self) -> None:
        raw = bytearray(0x8000)
        raw[0x7FC0 : 0x7FC0 + 16] = b"SAME ENGINE HOST"
        raw[0x7FD5] = 0x20
        for offset in (0x7FFA, 0x7FFC, 0x7FFE):
            raw[offset : offset + 2] = (0x8000).to_bytes(2, "little")
        image = bytearray(finalize(bytes(raw)))
        image[0] ^= 0x01
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "corrupt.sfc"
            path.write_bytes(image)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "audit_snes_rom.py"), str(path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match ROM byte sum", result.stderr)


if __name__ == "__main__":
    unittest.main()
