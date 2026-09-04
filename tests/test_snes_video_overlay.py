from __future__ import annotations

import unittest

from same.snes_video_overlay import (
    BLANK_TILE,
    FIRST_DYNAMIC_TILE,
    SET_LAYER_HIDE,
    SET_LAYER_SHOW_OR_REPLACE,
    SetLayerPacket,
    decode_4bpp_tile,
    decode_bg2_mask,
    encode_4bpp_tile,
    realize_overlay,
)


class SnesVideoOverlayTests(unittest.TestCase):
    def test_set_layer_packet_is_strict(self) -> None:
        for operation in (SET_LAYER_HIDE, SET_LAYER_SHOW_OR_REPLACE):
            packet = SetLayerPacket(7, operation)
            self.assertEqual(SetLayerPacket.unpack(packet.arg0, packet.arg1), packet)
        for args in ((0, 1), (1, 2), (1, 0x201), (1, 0x10001)):
            with self.assertRaises(ValueError):
                SetLayerPacket.unpack(*args)

    def test_4bpp_plane_and_x_order(self) -> None:
        rows = [[0] * 8 for _ in range(8)]
        rows[0] = [1, 2, 4, 8, 15, 0, 0, 0]
        encoded = encode_4bpp_tile(rows)
        self.assertEqual(encoded[0], 0x88)
        self.assertEqual(encoded[1], 0x48)
        self.assertEqual(encoded[16], 0x28)
        self.assertEqual(encoded[17], 0x18)
        self.assertEqual(len(encoded), 32)
        self.assertEqual(decode_4bpp_tile(encoded), tuple(tuple(row) for row in rows))

    def test_bg2_mask_decoder_uses_blank_and_dynamic_tiles(self) -> None:
        rows = [[0] * 8 for _ in range(8)]
        rows[1][2] = 15
        characters = bytearray(0x1800)
        characters[32:64] = encode_4bpp_tile(rows)  # tile 65, base is tile 64
        tilemap = bytearray(b"\x40\x00" * 1024)
        tilemap[4:6] = (0x2041).to_bytes(2, "little")
        mask = decode_bg2_mask(bytes(characters), bytes(tilemap))
        self.assertEqual(sum(mask), 1)
        self.assertEqual(mask[1 * 256 + 2 * 8 + 2], 1)

    def test_sparse_cells_clip_and_allocate_deterministically(self) -> None:
        pixels = bytearray(80 * 8)
        pixels[1] = 15
        pixels[79] = 15
        cells = realize_overlay(bytes(pixels), width=80, height=8, pitch=80,
                                x=-1, y=7)
        self.assertEqual([cell.screen_tile for cell in cells], [0, 9])
        self.assertEqual([cell.character for cell in cells],
                         [FIRST_DYNAMIC_TILE, FIRST_DYNAMIC_TILE + 1])
        self.assertTrue(all(cell.palette_group == 0 for cell in cells))
        self.assertEqual(BLANK_TILE, 64)

    def test_complete_declared_80_by_8_bound_realizes_22_cells(self) -> None:
        pixels = bytes([15]) * (80 * 8)
        cells = realize_overlay(pixels, width=80, height=8, pitch=80,
                                x=1, y=1)
        self.assertEqual(len(cells), 22)
        self.assertEqual(cells[0].screen_tile, 0)
        self.assertEqual(cells[-1].screen_tile, 42)
        self.assertEqual(
            [cell.character for cell in cells],
            list(range(FIRST_DYNAMIC_TILE, FIRST_DYNAMIC_TILE + 22)),
        )

    def test_palette_group_and_local_zero_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "local color zero"):
            realize_overlay(bytes([16]), width=1, height=1, pitch=1, x=0, y=0)
        with self.assertRaisesRegex(ValueError, "mixes palette groups"):
            realize_overlay(bytes([1, 17]), width=2, height=1, pitch=2, x=0, y=0)


if __name__ == "__main__":
    unittest.main()
