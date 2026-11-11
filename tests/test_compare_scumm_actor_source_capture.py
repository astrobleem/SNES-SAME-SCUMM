"""Offline comparison contracts, using no original archives or emulator."""
import hashlib
import unittest

from tools.actor_pose_plan import PosePlan, Span
from tools.compare_scumm_actor_source_capture import compare_capture, require_sha256


class SourceCaptureComparisonTests(unittest.TestCase):
    def setUp(self):
        self.plan = PosePlan((0, 0, 2, 1), (Span(0, 0, b'\x01\x02'),), (99, 0, 7), 2)
        self.backdrop = bytes([9]) * (256 * 224)
        self.projection = dict(source_width=320, source_height=200,
                               target_width=256, target_height=224,
                               content_width=256, content_height=160,
                               offset_x=0, offset_y=32,
                               sampling='nearest_neighbor_aspect_fit')
        self.visual = dict(width=256, height=224, pitch=256, projection=self.projection)

    def test_legacy_surface_comparison_and_mapped_zero(self):
        actual = bytearray(self.backdrop)
        actual[40 * 256 + 20:40 * 256 + 22] = b'\x00\x07'
        result = compare_capture(self.plan, dict(foot_screen=[20, 40]),
                                 self.visual, self.backdrop, bytes(actual))
        self.assertEqual(result['different_pixels'], 0)
        self.assertEqual(result['foot_coordinate_space'], 'surface')
        self.assertEqual(result['source_reference_sha256'], hashlib.sha256(actual).hexdigest())

    def test_source_room_projection_uses_global_phase_and_holes(self):
        plan = PosePlan((-1, 0, 5, 1), (
            Span(-1, 0, b'\x01\x02'), Span(4, 0, b'\x01'),
        ), (99, 0, 7), 3)
        pose = dict(foot_screen=[21, 40], foot_coordinate_space='source_room',
                    room_projection=self.projection)
        # X samples at target 16,17,18,19,20 are 20,21,23,24,25.
        actual = bytearray(self.backdrop)
        actual[64 * 256 + 16:64 * 256 + 18] = b'\x00\x07'
        actual[64 * 256 + 20] = 0
        result = compare_capture(plan, pose, self.visual, self.backdrop, bytes(actual))
        self.assertEqual(result['different_pixels'], 0)
        self.assertEqual(compare_capture(plan, pose, self.visual, self.backdrop,
                                         self.backdrop)['different_pixels'], 3)

    def test_signed_foot_raw_u16_and_signed_integer_agree(self):
        actual = bytearray(self.backdrop)
        actual[0] = 7
        for x in (-1, 65535):
            with self.subTest(x=x):
                self.assertEqual(compare_capture(
                    self.plan, dict(foot_screen=[x, 0], foot_coordinate_space='surface'),
                    self.visual, self.backdrop, bytes(actual))['different_pixels'], 0)

    def test_identity_projection_matches_direct_surface(self):
        projection = dict(self.projection, source_width=256, source_height=224,
                          content_height=224, offset_y=0)
        visual = dict(self.visual, projection=projection)
        pose = dict(foot_screen=[0, 0], foot_coordinate_space='source_room',
                    room_projection=projection)
        projected = compare_capture(self.plan, pose, visual, self.backdrop, self.backdrop)
        direct = compare_capture(self.plan, dict(foot_screen=[0, 0]), visual,
                                 self.backdrop, self.backdrop)
        self.assertEqual(projected['source_reference_sha256'], direct['source_reference_sha256'])

    def test_rejects_truncated_capture_overrides_scale_and_bad_projection(self):
        pose = dict(foot_screen=[20, 40], foot_coordinate_space='source_room',
                    room_projection=self.projection)
        for change in [dict(palette_overrides={1: 8}), dict(actor_scale=204),
                       dict(room_projection=None), dict(foot_coordinate_space='unknown'),
                       dict(room_projection=dict(self.projection, offset_y=0))]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                compare_capture(self.plan, pose | change, self.visual, self.backdrop, self.backdrop)
        with self.assertRaises(ValueError):
            compare_capture(self.plan, pose, self.visual, self.backdrop, self.backdrop[:-1])

    def test_builtin_cursor_is_composited_after_actor_and_clipped(self):
        pose = dict(foot_screen=[21, 40], foot_coordinate_space='source_room',
                    room_projection=self.projection,
                    builtin_cursor=dict(valid=1, pending=0, visible=1, id=0,
                                        logical_x=0, logical_y=0, left=-8, top=25, color=7))
        actual = bytearray(self.backdrop)
        actual[64*256+17] = 0
        # Source X22 is skipped by the shared sample grid.
        for y in (*range(6), *range(9, 15)):
            actual[(25+y)*256] = 7
        for x in range(2, 8):
            actual[32*256+x] = 7
        self.assertEqual(compare_capture(self.plan, pose, self.visual, self.backdrop,
                                         bytes(actual))['different_pixels'], 0)
        for mutation in ({'left': -7}, {'color': 44}, {'pending': 1}, {'valid': 0}):
            invalid = dict(pose, builtin_cursor=pose['builtin_cursor'] | mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                compare_capture(self.plan, invalid, self.visual, self.backdrop, bytes(actual))

    def test_required_identities_match_and_fail_closed(self):
        data = b'bound bytes'
        digest = hashlib.sha256(data).hexdigest()
        for field in ('rom_sha256', 'package_sha256', 'indexed_surface_sha256'):
            with self.subTest(field=field):
                self.assertEqual(require_sha256({field: digest}, field, data), digest)
                for record in ({}, {field: None}, {field: ''}, {field: 'g' * 64},
                               {field: hashlib.sha256(b'other').hexdigest()}):
                    with self.assertRaises(ValueError):
                        require_sha256(record, field, data)


if __name__ == '__main__':
    unittest.main()
