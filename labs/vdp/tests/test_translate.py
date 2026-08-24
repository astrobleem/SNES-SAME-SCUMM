from __future__ import annotations

import unittest

from same_vdp.translate import decode_snes_tile, encode_snes_tile


class TranslationTests(unittest.TestCase):
    def test_tile_planar_roundtrip(self) -> None:
        pixels = [[(x + y * 3) & 15 for x in range(8)] for y in range(8)]
        self.assertEqual(decode_snes_tile(encode_snes_tile(pixels)), pixels)


if __name__ == "__main__":
    unittest.main()
