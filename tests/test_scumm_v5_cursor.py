"""Host cursor contract checked against reference v5 row-mask vectors."""
from dataclasses import asdict
from pathlib import Path
import unittest

from same.engines.scumm_v5.cursor import (
    COLORS, HOTSPOTS, MASKS, apply_cursor_command, cursor_pixels, publish_cursor,
)
from same.engines.scumm_v5.engine import ScummState
from same.errors import EngineExecutionError
from same.video import VideoService


class BuiltinCursorTests(unittest.TestCase):
    def test_native_include_exactly_matches_host_geometry_and_little_endian_abi(self):
        path = Path(__file__).resolve().parents[1] / 'runtime/snes/engines/scumm_v5_cursor_shapes.inc.pasm'
        tables = {}
        current = None
        for line in path.read_text().splitlines():
            line = line.split(';', 1)[0].strip()
            if not line:
                continue
            if line.endswith(':'):
                current = line[:-1]
                self.assertNotIn(current, tables)
                tables[current] = bytearray()
            else:
                self.assertTrue(line.startswith('.byte '), line)
                self.assertIsNotNone(current)
                tables[current].extend(int(token.strip()[1:], 16)
                                       for token in line[6:].split(','))
        expected_rows = b''.join(
            sum(mask[y*16+x] << (15-x) for x in range(16)).to_bytes(2, 'little')
            for mask in MASKS for y in range(16))
        self.assertEqual(tables, {
            'ScummV5_Cursor_Masks': expected_rows,
            'ScummV5_Cursor_Hotspots': bytes(v for pair in HOTSPOTS for v in pair),
            'ScummV5_Cursor_Colors': bytes(COLORS),
        })
        self.assertEqual(sum(map(len, tables.values())), 140)

    def test_default_zero_override_witnesses_are_not_overrides(self):
        state = ScummState()
        self.assertEqual(state.cursor_image, (0, 0))
        self.assertEqual(state.cursor_hotspot, (0, 0, 0))
        video = VideoService(256, 224)
        publish_cursor(state, video, screen_x=128, screen_y=141)
        self.assertEqual(video.cursor.pixels, cursor_pixels(0))
        self.assertEqual((video.cursor.hotspot_x, video.cursor.hotspot_y), (8, 7))
        self.assertEqual((video.cursor.x, video.cursor.y), (128, 141))
        self.assertTrue(video.cursor.visible)

    def test_all_four_shapes_match_reference_rows_and_orientation(self):
        # Reference data from local ScummVM resetCursors; MSB is screen left.
        reference = (
            (0x0080,0x0080,0x0080,0x0080,0x0080,0x0080,0,0x7e3f,
             0,0x0080,0x0080,0x0080,0x0080,0x0080,0x0080,0),
            (0,0x7ffe,0x6006,0x300c,0x1818,0x0c30,0x0660,0x03c0,
             0x0660,0x0c30,0x1998,0x33cc,0x67e6,0x7ffe,0,0),
            (0,0x4000,0x6000,0x7000,0x7800,0x7c00,0x7e00,0x7f00,
             0x7f80,0x78c0,0x7c00,0x4600,0x0600,0x0300,0x0300,0x0180),
            (0x1e00,0x1200,0x1200,0x1200,0x1200,0x13ff,0x1249,0x1249,
             0xf249,0x9001,0x9001,0x9001,0x8001,0x8001,0x8001,0xffff),
        )
        for index, mask in enumerate(MASKS):
            with self.subTest(cursor=index):
                self.assertEqual(len(mask), 256)
                rows = tuple(sum(mask[y*16+x] << (15-x) for x in range(16)) for y in range(16))
                self.assertEqual(rows, reference[index])
        self.assertEqual(sum(MASKS[0]), 24)
        self.assertEqual(HOTSPOTS, ((8,7), (8,7), (1,1), (5,0)))

    def test_color_phase_and_transparency_are_independent_of_selection(self):
        for index in range(4):
            for tick, color in enumerate((15,15,15,15,7,7,8,8,15,15)):
                pixels = cursor_pixels(index, animation_index=tick)
                self.assertEqual({p for p, covered in zip(pixels, MASKS[index]) if covered}, {color})
                self.assertEqual({p for p, covered in zip(pixels, MASKS[index]) if not covered}, {255})

    def test_existing_c7_state_selection_visibility_and_service_hotspot(self):
        state = ScummState()
        video = VideoService(256, 224)
        apply_cursor_command(state, 12, (2,))
        publish_cursor(state, video, screen_x=128, screen_y=141, animation_index=4)
        self.assertEqual((video.cursor.x, video.cursor.y), (128,141))
        self.assertEqual((video.cursor.width, video.cursor.height), (16,16))
        self.assertEqual((video.cursor.hotspot_x, video.cursor.hotspot_y), (1,1))
        self.assertEqual(video.cursor.pixels, cursor_pixels(2, animation_index=4))
        self.assertEqual(video.cursor.transparent_index, 255)
        self.assertTrue(video.cursor.visible)
        apply_cursor_command(state, 2)
        publish_cursor(state, video, screen_x=0, screen_y=0)
        self.assertFalse(video.cursor.visible)
        self.assertEqual(video.presented, [])

    def test_soft_counters_are_signed_and_user_input_does_not_hide_cursor(self):
        state = ScummState()
        apply_cursor_command(state, 2)
        apply_cursor_command(state, 6)
        self.assertEqual(state.cursor_state, -1)
        apply_cursor_command(state, 5)
        self.assertFalse(state.cursor_visible)
        apply_cursor_command(state, 5)
        self.assertTrue(state.cursor_visible)
        apply_cursor_command(state, 4)
        apply_cursor_command(state, 8)
        self.assertEqual(state.user_input_state, -1)
        self.assertTrue(state.cursor_visible)
        apply_cursor_command(state, 7)
        apply_cursor_command(state, 3)
        self.assertEqual(state.user_input_state, 1)
        apply_cursor_command(state, 1)
        self.assertEqual(state.cursor_state, 1)

    def test_charset_commands_delegate_without_changing_cursor_or_charset(self):
        state = ScummState()
        state.charset_id = 2
        before = asdict(state)
        self.assertFalse(apply_cursor_command(state, 13, (1,)))
        self.assertFalse(apply_cursor_command(state, 14, (15,7)))
        self.assertEqual(asdict(state), before)

    def test_invalid_selection_and_overrides_fail_without_mutation(self):
        state = ScummState()
        before = asdict(state)
        for subop, operands in [(10,(0,0)), (11,(0,0,0)), (12,(9,)), (12,(-1,)),
                                (12,(True,)), (12,()), (1,(2,)), (9,())]:
            with self.subTest(subop=subop, operands=operands), self.assertRaises(EngineExecutionError):
                apply_cursor_command(state, subop, operands)
            self.assertEqual(asdict(state), before)
        for tick in (-1, True, 1.5):
            with self.assertRaises(EngineExecutionError):
                cursor_pixels(0, animation_index=tick)
        state.cursor_image = (3,4)
        video = VideoService(256,224)
        before_cursor = asdict(video.cursor)
        with self.assertRaises(EngineExecutionError):
            publish_cursor(state, video, screen_x=20, screen_y=40)
        self.assertEqual(asdict(video.cursor), before_cursor)


if __name__ == '__main__':
    unittest.main()
