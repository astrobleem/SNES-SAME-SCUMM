from __future__ import annotations

import random
import unittest

from same.snes_surface import (
    BG1SC,
    BG12NBA,
    BGMODE,
    CGRAM_BYTES,
    DMA_DESCRIPTOR_LIMIT,
    DMA_FRAME_BUDGET,
    TILE_DATA_BYTES,
    TILEMAP_BYTES,
    TILEMAP_VRAM_BYTE_ADDRESS,
    TILEMAP_VRAM_WORD_ADDRESS,
    TM,
    TS,
    VRAM_BYTES_REMAINING,
    VRAM_BYTES_USED,
    PaletteRange,
    TileRun,
    TileTransferPlan,
    bgr555_to_rgb8,
    build_static_tilemap,
    build_tile_runs,
    candidate_tiles,
    changed_palette_ranges,
    changed_tiles,
    decode_bundle_indexed,
    decode_cgram,
    decode_snes_8bpp_tile,
    encode_cgram,
    encode_snes_8bpp_tile,
    plan_tile_transfers,
    realize_indexed_surface,
    rgb8_to_bgr555,
)
from same.video import IndexedSurface, Rect


def patterned_surface(*, pitch: int = 256) -> tuple[IndexedSurface, bytearray]:
    backing = bytearray([0xCC] * (pitch * 224))
    surface = IndexedSurface.wrap(256, 224, pitch, backing)
    for y in range(224):
        row = surface._visible_row(y)
        for x in range(256):
            row[x] = (x * 17 + y * 29 + (x // 8) * 7 + (y // 8) * 11) & 0xFF
    surface.palette[:] = [
        ((index * 13) & 0xFF, (index * 37) & 0xFF, (index * 73) & 0xFF)
        for index in range(256)
    ]
    return surface, backing


class SnesSurfaceTests(unittest.TestCase):
    def test_mode3_layout_constants_are_exact(self) -> None:
        self.assertEqual((BGMODE, BG1SC, BG12NBA, TM, TS), (0x03, 0x70, 0x00, 0x01, 0x00))
        self.assertEqual(TILEMAP_VRAM_BYTE_ADDRESS, 0xE000)
        self.assertEqual(TILEMAP_VRAM_WORD_ADDRESS, 0x7000)
        self.assertEqual((TILE_DATA_BYTES, TILEMAP_BYTES, CGRAM_BYTES), (57344, 2048, 512))
        self.assertEqual((VRAM_BYTES_USED, VRAM_BYTES_REMAINING), (59392, 6144))

    def test_bitplanes_and_x_bit_order_are_exact(self) -> None:
        tile = [[0] * 8 for _ in range(8)]
        tile[0] = [1, 2, 4, 8, 16, 32, 64, 128]
        tile[1] = [0xFF, 0, 0, 0, 0, 0, 0, 0xFF]
        encoded = encode_snes_8bpp_tile(tile)
        self.assertEqual(
            tuple(encoded[offset] for offset in (0, 1, 16, 17, 32, 33, 48, 49)),
            (0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01),
        )
        self.assertEqual(
            tuple(encoded[offset] for offset in (2, 3, 18, 19, 34, 35, 50, 51)),
            (0x81,) * 8,
        )
        self.assertEqual(decode_snes_8bpp_tile(encoded), tile)

    def test_random_tiles_round_trip_and_validate(self) -> None:
        random_source = random.Random(0x536E6573)
        for _ in range(128):
            tile = [[random_source.randrange(256) for _ in range(8)] for _ in range(8)]
            self.assertEqual(decode_snes_8bpp_tile(encode_snes_8bpp_tile(tile)), tile)
        with self.assertRaisesRegex(ValueError, "8x8"):
            encode_snes_8bpp_tile([[0] * 8] * 7)
        with self.assertRaisesRegex(ValueError, "0..255"):
            encode_snes_8bpp_tile([[256] + [0] * 7] + [[0] * 8 for _ in range(7)])
        with self.assertRaisesRegex(ValueError, "64 bytes"):
            decode_snes_8bpp_tile(bytes(63))

    def test_static_tilemap_has_fixed_visible_slots_and_safe_hidden_rows(self) -> None:
        tilemap = build_static_tilemap()
        self.assertEqual(len(tilemap), 2048)
        words = [tilemap[i] | (tilemap[i + 1] << 8) for i in range(0, len(tilemap), 2)]
        self.assertEqual(words[:896], list(range(896)))
        self.assertEqual(words[896:], [0] * 128)

    def test_bundle_round_trip_honors_pitch_and_excludes_padding(self) -> None:
        padded, backing = patterned_surface(pitch=272)
        tight = IndexedSurface(256, 224)
        tight.pixels[:] = padded.visible_bytes()
        tight.palette[:] = padded.palette
        padded_bundle = realize_indexed_surface(padded)
        tight_bundle = realize_indexed_surface(tight)
        self.assertEqual(padded_bundle, tight_bundle)
        self.assertEqual(decode_bundle_indexed(padded_bundle), padded.visible_bytes())
        self.assertEqual(len(padded_bundle.tiles_8bpp), 57344)
        self.assertEqual(len(padded_bundle.tilemap), 2048)
        self.assertEqual(len(padded_bundle.cgram), 512)
        for y in range(224):
            self.assertEqual(backing[y * 272 + 256 : (y + 1) * 272], bytes([0xCC] * 16))
        with self.assertRaisesRegex(ValueError, "256x224"):
            realize_indexed_surface(IndexedSurface(255, 224))

    def test_palette_bgr555_words_and_quantized_decode(self) -> None:
        palette = [(0, 0, 0)] * 256
        palette[:7] = [
            (0, 0, 0),
            (255, 255, 255),
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (0x84, 0x42, 0x21),
            (7, 7, 7),
        ]
        cgram = encode_cgram(palette)
        words = [cgram[i] | (cgram[i + 1] << 8) for i in range(0, 14, 2)]
        self.assertEqual(words, [0x0000, 0x7FFF, 0x001F, 0x03E0, 0x7C00, 0x1110, 0x0000])
        decoded = decode_cgram(cgram)
        self.assertEqual(decoded[1:5], ((255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255)))
        for color in palette:
            word = rgb8_to_bgr555(*color)
            self.assertEqual(bgr555_to_rgb8(word), tuple(((component >> 3) << 3) | ((component >> 3) >> 2) for component in color))

    def test_dirty_candidates_clip_deduplicate_and_preserve_first_seen_order(self) -> None:
        self.assertEqual(
            candidate_tiles((Rect(-3, -2, 12, 12), Rect(15, 7, 2, 2), Rect(250, 220, 20, 20))),
            (0, 1, 32, 33, 2, 34, 895),
        )
        self.assertEqual(candidate_tiles((Rect(-20, -20, 1, 1),)), ())

    def test_tile_shadow_filters_full_dirty_and_detects_real_changes(self) -> None:
        surface, _ = patterned_surface()
        committed = realize_indexed_surface(surface).tiles_8bpp
        full_candidates = candidate_tiles((Rect(0, 0, 256, 224),))
        self.assertEqual(len(full_candidates), 896)
        self.assertEqual(changed_tiles(committed, committed, full_candidates), ())

        surface.set_pixel(17, 9, surface._visible_row(9)[17] ^ 0xFF)
        one_change = realize_indexed_surface(surface).tiles_8bpp
        self.assertEqual(changed_tiles(one_change, committed, full_candidates), (34,))

        surface.set_pixel(250, 220, surface._visible_row(220)[250] ^ 0x55)
        two_changes = realize_indexed_surface(surface).tiles_8bpp
        self.assertEqual(changed_tiles(two_changes, committed, full_candidates), (34, 895))
        self.assertEqual(build_tile_runs((64, 65, 66, 67, 70, 71)), (TileRun(64, 4), TileRun(70, 2)))
        self.assertEqual((TileRun(64, 4).vram_byte_address, TileRun(64, 4).byte_length), (4096, 256))

    def test_dma_reference_plan_retains_over_budget_and_over_descriptor_work(self) -> None:
        self.assertEqual((DMA_FRAME_BUDGET, DMA_DESCRIPTOR_LIMIT), (2048, 8))
        plan = plan_tile_transfers(range(100))
        self.assertEqual(
            plan,
            TileTransferPlan(
                runs=(TileRun(0, 32),),
                scheduled_tiles=tuple(range(32)),
                pending_tiles=tuple(range(32, 100)),
            ),
        )
        self.assertEqual(plan.byte_length, 2048)

        isolated = tuple(range(0, 18, 2))
        descriptor_limited = plan_tile_transfers(isolated)
        self.assertEqual(descriptor_limited.runs, tuple(TileRun(tile, 1) for tile in isolated[:8]))
        self.assertEqual(descriptor_limited.pending_tiles, isolated[8:])
        self.assertEqual(
            plan_tile_transfers((1, 2), byte_budget=63).pending_tiles,
            (1, 2),
        )

    def test_palette_shadow_reports_only_changed_contiguous_ranges(self) -> None:
        surface, _ = patterned_surface()
        committed = realize_indexed_surface(surface).cgram
        self.assertEqual(changed_palette_ranges(committed, committed), ())
        surface.palette[4] = (255, 0, 0)
        surface.palette[5] = (0, 255, 0)
        surface.palette[9] = (0, 0, 255)
        current = realize_indexed_surface(surface).cgram
        self.assertEqual(
            changed_palette_ranges(current, committed),
            (PaletteRange(4, 2), PaletteRange(9, 1)),
        )


if __name__ == "__main__":
    unittest.main()
