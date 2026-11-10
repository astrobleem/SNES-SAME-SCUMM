"""Execute native controller source against independent full-image projection."""
import unittest

from test_scumm_v5_actor_damage_boundaries import ControllerMachine, M, SOURCE
from test_actor_pose_projection import project


class NativeActorProjectionTests(unittest.TestCase):
    def check_case(self, spans, foot, size):
        vm = ControllerMachine(spans, foot=foot, source_size=size,
                               bounds=(-32768, -32768, 32767, 32767))
        w, h = size
        background = bytes((i * 17 + 3) & 255 for i in range(w * h))
        composite = bytearray(background)
        coverage = bytearray(w * h)
        cursor = 0
        for x, y, length in spans:
            for i in range(length):
                sx, sy = foot[0] + x + i, foot[1] + y
                if 0 <= sx < w and 0 <= sy < h:
                    composite[sy * w + sx] = vm.pixels[cursor + i]
                    coverage[sy * w + sx] = 1
            cursor += length
        vm.original, _ = project(background, w, h, 256, 224)
        vm.surface[:] = vm.original
        expected, _ = project(composite, w, h, 256, 224)
        expected_mask, _ = project(coverage, w, h, 256, 224)
        vm.run()
        self.assertFalse(vm.c)
        self.assertEqual(bytes(vm.surface), expected)
        captured = set()
        for a, count, _ in vm.captures:
            cells = set(range(a, a + count))
            self.assertFalse(captured & cells)
            captured.update(cells)
        self.assertEqual(captured, {i for i, value in enumerate(expected_mask) if value})
        drawn = [a + i for a, count, _ in vm.draws for i in range(count)]
        self.assertEqual(set(drawn), captured)
        self.assertEqual(len(drawn), len(captured))
        if captured:
            self.assertEqual(vm.damage, (min(i % 256 for i in captured),
                                        min(i // 256 for i in captured),
                                        max(i % 256 for i in captured) + 1,
                                        max(i // 256 for i in captured) + 1))
        for a, count, old in vm.captures:
            vm.surface[a:a + count] = old
        self.assertEqual(bytes(vm.surface), vm.original)
        return vm

    def test_long_projection_rom_access_keeps_plain_banked_label(self):
        # Pinned Poppy encoded label+4 as BF 04 82 00 instead of bank $13.
        # The byte-level build guard belongs to the observer/build validator;
        # this source guard prevents reintroducing the known assembler shape.
        source = SOURCE.read_text()
        loads = [line.strip() for line in source.splitlines()
                 if 'lda.l ScummV5_MsuVisualProjection' in line]
        self.assertEqual(len(loads), 8)
        self.assertTrue(all(line in (
            'lda.l ScummV5_MsuVisualProjectionOffsets,x',
            'lda.l ScummV5_MsuVisualProjectionData,x') for line in loads))

    def test_identity_coalesces_and_preserves_mapped_zero(self):
        vm = self.check_case([(0, 0, 9), (3, 2, 4)], (80, 100), (256, 224))
        self.assertEqual(vm.draws[0], (100 * 256 + 80, 9, 0))
        self.assertEqual(vm.pixels[0], 0)

    def test_320x200_source_foot_before_sampling_and_skipped_rows(self):
        vm = self.check_case([(0, 0, 12), (-31, 1, 40), (2, 2, 4), (0, 4, 1)],
                             (33, 100), (320, 200))
        self.assertEqual(vm.mem[M + 'FOOT_SCREEN_X'], 33)
        self.assertEqual(vm.mem[M + 'FOOT_SCREEN_Y'], 100)
        self.assertGreater(len(vm.draws), len(vm.captures))
        self.assertTrue(any(count == 1 for _, count, _ in vm.draws))

    def test_all_edges_clipped_in_source_space(self):
        for foot in [(-5, 0), (316, 199), (-30, -3), (320, 200)]:
            with self.subTest(foot=foot):
                self.check_case([(0, 0, 14), (0, 1, 8), (2, 3, 4)], foot, (320, 200))

    def test_upscale_repeats_capture_once_per_projected_row(self):
        vm = self.check_case([(0, 0, 3), (1, 1, 2)], (4, 5), (17, 13))
        self.assertGreater(len(vm.captures), 2)
        self.assertGreater(len(vm.draws), len(vm.captures))
        self.assertTrue(any(count == 1 for _, count, _ in vm.draws))

    def test_portrait_and_extreme_aspect_ratios(self):
        for size, foot in [((200, 320), (80, 150)), ((1, 600), (0, 20)),
                           ((600, 1), (100, 0))]:
            with self.subTest(size=size):
                self.check_case([(0, 0, 6), (-4, 1, 3)], foot, size)

    def test_scale_and_stale_generation_fail_before_capture(self):
        for field, value in [
            ('SAME_SCUMM_C14_ACTORS+(SCUMM_V5_ACTOR_RENDER_ID*$40)+SAME_SCUMM_C14_A_SCALE_X', 0xFEFF),
            (M + 'TICKET_ROOM_EPOCH', 8),
        ]:
            vm = ControllerMachine([(0, 0, 2)], source_size=(320, 200))
            vm.mem[field] = value
            vm.run()
            self.assertTrue(vm.c)
            self.assertNotIn('begin', vm.events)
            self.assertEqual(vm.surface, vm.original)

    def test_installed_room_selects_table_and_missing_fails_closed(self):
        vm = ControllerMachine([(0, 0, 2)])
        vm.mem['SAME_SCUMM_M23A_ACTIVE_ROOM'] = 99
        vm.run()
        self.assertFalse(vm.c)
        vm = ControllerMachine([(0, 0, 2)])
        vm.mem['SAME_VIDEO_SURFACE_ROOM'] = 99
        vm.run()
        self.assertTrue(vm.c)
        self.assertNotIn('begin', vm.events)

    def test_elevation_and_target_viewport_are_applied_in_correct_spaces(self):
        vm = ControllerMachine([(0, 0, 10)], foot=(100, 100), source_size=(320, 200))
        vm.mem['SAME_SCUMM_C14_ACTORS+(SCUMM_V5_ACTOR_RENDER_ID*$40)+SAME_SCUMM_C14_A_ELEVATION'] = 10
        vm.mem['SAME_VIDEO_SURFACE_DEST_X'] = 4
        vm.mem['SAME_VIDEO_SURFACE_SOURCE_X'] = 2
        vm.run()
        self.assertEqual(vm.mem[M + 'FOOT_SCREEN_Y'], 90)
        self.assertEqual(vm.captures[0][:2], (104 * 256 + 82, 8))

    def test_bounded_search_cost_for_123_short_source_spans(self):
        spans = [(i % 3 * 10, i, 6) for i in range(123)]
        vm = self.check_case(spans, (100, 10), (320, 200))
        # 123 runs, two passes, four searches, at most 9 comparisons each.
        # Executed-source instruction bound catches accidental W/H full scans.
        self.assertLess(vm.search_instructions, 123 * 2 * 4 * 180)
        self.assertLess(vm.instructions, 200000)


if __name__ == '__main__':
    unittest.main()
