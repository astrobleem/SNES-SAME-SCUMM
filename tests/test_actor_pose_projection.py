"""Differential oracle: composite in logical space, then project real SC5VIS."""
from dataclasses import dataclass
import random
import unittest

from same.engines.scumm_v5.room_visual import (
    decode_room_visual, encode_room_visual, project_room_visual,
)
from tools.actor_pose_plan import (
    PoseError, PosePlan, Span, compile_pose, project_pose_aspect_fit,
    render_reference, validate_chunk, visible_runs,
)


def project(pixels, width, height, tw, th):
    record = encode_room_visual(
        room=0, width=width, height=height, pitch=width,
        palette=bytes(768), pixels=bytes(pixels),
        archive_sha256='00' * 32, index_sha256='00' * 32,
        data_sha256='00' * 32, room_sha256='00' * 32,
    )
    projected, metadata = project_room_visual(
        record, target_width=tw, target_height=th)
    return decode_room_visual(projected).pixels, metadata


@dataclass
class Cel:
    width: int
    height: int
    relative_x: int
    relative_y: int
    move_x: int
    move_y: int
    pixels: bytes


@dataclass
class Pose:
    draw_to_right: bool
    cels: tuple


class ActorProjectionTests(unittest.TestCase):
    def check_projection(self, plan, foot, size, target=(256, 224)):
        w, h = size
        tw, th = target
        # Full logical surfaces are deliberately independent of production's
        # sparse lookup. Separate source-slot coverage catches mapped-zero loss.
        background = bytes((i * 37 + 19) % 256 for i in range(w * h))
        composite = bytearray(background)
        source_slots = bytearray(w * h)
        for span in plan.spans:
            for i, slot in enumerate(span.slots):
                x, y = foot[0] + span.x + i, foot[1] + span.y
                if 0 <= x < w and 0 <= y < h:
                    source_slots[y * w + x] = slot
                    composite[y * w + x] = plan.palette[slot]
        expected_slots, _ = project(source_slots, w, h, tw, th)
        expected, _ = project(composite, w, h, tw, th)
        projected_background, _ = project(background, w, h, tw, th)
        result = project_pose_aspect_fit(
            plan, foot_x=foot[0], foot_y=foot[1], source_width=w,
            source_height=h, target_width=tw, target_height=th)
        self.assertEqual(result.palette, plan.palette)
        actual_slots = bytearray(tw * th)
        covered = set()
        for span in result.spans:
            self.assertTrue(1 <= len(span.slots) <= 256)
            self.assertTrue(0 <= span.x < span.x + len(span.slots) <= tw)
            self.assertTrue(0 <= span.y < th)
            for i, slot in enumerate(span.slots):
                pos = span.y * tw + span.x + i
                self.assertNotIn(pos, covered)
                covered.add(pos)
                actual_slots[pos] = slot
        self.assertEqual(bytes(actual_slots), expected_slots)
        self.assertEqual(result.opaque_pixels, len(covered))
        expected_bounds = ((min(p % tw for p in covered), min(p // tw for p in covered),
                            max(p % tw for p in covered) + 1,
                            max(p // tw for p in covered) + 1)
                           if covered else (0, 0, 0, 0))
        self.assertEqual(result.bounds, expected_bounds)
        self.assertEqual(render_reference(
            projected_background, tw, th, result, anchor_x=0, anchor_y=0), expected)
        for chunk in result.chunks(17):
            validate_chunk(chunk, len(result.palette))
            for x, y, pixels in visible_runs(
                    chunk, result.palette, anchor_x=0, anchor_y=0, width=tw, height=th):
                self.assertTrue(1 <= len(pixels) <= 256)
                self.assertEqual(pixels, expected[y * tw + x:y * tw + x + len(pixels)])
        return result

    def test_global_phase_signed_offsets_and_letterbox(self):
        plan = PosePlan((-3, -2, 6, 2), (
            Span(-3, -2, b'\x01\x02\x03\x01\x02\x03\x01\x02\x03'),
            Span(-1, 0, b'\x03\x02'), Span(3, 1, b'\x01\x02'),
        ), (99, 0, 77, 77), 13)
        for x in range(15, 26):  # every 4/5 sampling phase
            self.check_projection(plan, (x, 40), (320, 200))
        for foot in [(-4, -2), (0, 0), (319, 199), (321, 201),
                     (-100, 40), (400, 40), (20, -100), (20, 300)]:
            self.check_projection(plan, foot, (320, 200))
        _, meta = project(bytes(320 * 200), 320, 200, 256, 224)
        self.assertEqual(tuple(meta[k] for k in (
            'content_width', 'content_height', 'offset_x', 'offset_y')),
            (256, 160, 0, 32))

    def test_full_width_run_and_mapped_zero_is_opaque(self):
        plan = PosePlan((0, 0, 320, 1), (Span(0, 0, bytes([1]) * 320),), (55, 0), 320)
        result = self.check_projection(plan, (0, 0), (320, 200))
        self.assertEqual(result.spans, (Span(0, 32, bytes([1]) * 256),))

    def test_unsampled_pixel_empty_and_extreme_aspect_ratios(self):
        plan = PosePlan((0, 0, 1, 1), (Span(0, 0, b'\x01'),), (0, 9), 1)
        self.assertFalse(self.check_projection(plan, (2, 0), (320, 200)).spans)
        self.check_projection(PosePlan((0, 0, 0, 0), (), (0, 9), 0), (0, 0), (320, 200))
        for size in [(1, 1000), (1000, 1), (1, 1)]:
            self.check_projection(plan, (0, 0), size)

    def test_random_composed_poses_borders_up_and_down_sampling(self):
        rng = random.Random(0xA8)
        sizes = [(320, 200), (320, 144), (200, 320), (17, 13), (511, 333)]
        for case in range(100):
            size = sizes[case % len(sizes)]
            cels = []
            for _ in range(3):
                w, h = rng.randint(1, 20), rng.randint(1, 15)
                cels.append(Cel(w, h, rng.randint(-20, 5), rng.randint(-20, 5),
                                rng.randint(-5, 5), rng.randint(-5, 5),
                                bytes(rng.randrange(5) for _ in range(w * h))))
            plan = compile_pose(Pose(bool(case % 2), tuple(cels)), (88, 0, 44, 44, 255))
            foot = (rng.choice([0, size[0] - 1, rng.randrange(size[0]), -15, size[0] + 15]),
                    rng.choice([0, size[1] - 1, rng.randrange(size[1]), -15, size[1] + 15]))
            with self.subTest(case=case, size=size, foot=foot):
                self.check_projection(plan, foot, size,
                                      (256, 224) if case % 3 else (63, 57))

    def test_rejects_nonidentity_actor_scale_and_invalid_geometry(self):
        plan = PosePlan((0, 0, 0, 0), (), (0,), 0)
        args = dict(foot_x=0, foot_y=0, source_width=320, source_height=200)
        for name, value in [('actor_scale', 204), ('actor_scale', True),
                            ('source_width', 0), ('source_height', 65536),
                            ('target_width', 257), ('target_height', 0),
                            ('foot_x', 1.5), ('foot_y', -32769)]:
            with self.subTest(name=name, value=value), self.assertRaises(PoseError):
                project_pose_aspect_fit(plan, **(args | {name: value}))


if __name__ == '__main__':
    unittest.main()
