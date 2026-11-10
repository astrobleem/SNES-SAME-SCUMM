from __future__ import annotations

from dataclasses import dataclass
import unittest

from tools.actor_pose_plan import (
    PoseError, compile_pose, render_reference, validate_chunk, visible_runs,
)


@dataclass(frozen=True)
class Cel:
    width: int
    height: int
    relative_x: int
    relative_y: int
    move_x: int
    move_y: int
    pixels: bytes


@dataclass(frozen=True)
class Pose:
    draw_to_right: bool
    cels: tuple[Cel, ...]


class ActorPosePlanTests(unittest.TestCase):
    def test_signed_foot_anchor_and_no_fixed_crop(self) -> None:
        pose = Pose(True, (Cel(40, 2, -20, -3, 0, 0, bytes(range(1, 81))),))
        plan = compile_pose(pose, tuple(range(256)))
        self.assertEqual(plan.bounds, (-20, -3, 20, -1))
        self.assertEqual(plan.opaque_pixels, 80)

    def test_column_major_cumulative_moves_and_last_opaque_wins(self) -> None:
        pose = Pose(True, (
            Cel(2, 2, -1, -1, 3, 2, bytes((1, 2, 3, 4))),
            Cel(2, 2, 0, 0, 0, 0, bytes((0, 5, 6, 0))),
        ))
        plan = compile_pose(pose, tuple(range(16)))
        rendered = render_reference(bytes(16 * 16), 16, 16, plan,
                                    anchor_x=4, anchor_y=4)
        # First cel coordinate (-1,-1) is retained and later opaque cel wins
        # only where its source sample is nonzero.
        self.assertEqual(rendered[3 * 16 + 3], 1)
        self.assertEqual(rendered[3 * 16 + 7], 5)
        self.assertEqual(rendered[2 * 16 + 8], 6)

    def test_palette_zero_is_opaque_and_transparency_is_source_zero(self) -> None:
        plan = compile_pose(Pose(True, (Cel(2, 1, 0, 0, 0, 0, b"\x01\x00"),)),
                            (0, 0))
        chunk = plan.chunks()[0]
        self.assertEqual(visible_runs(chunk, plan.palette, anchor_x=0, anchor_y=0,
                                      width=8, height=8), ((0, 0, b"\x00"),))
        self.assertEqual(render_reference(bytes(64), 8, 8, plan,
                                          anchor_x=0, anchor_y=0)[0], 0)

    def test_chunks_are_bounded_checked_and_keep_signed_clipping(self) -> None:
        slots = bytes([1]) * 5000
        plan = compile_pose(Pose(True, (Cel(100, 50, -10, 0, 0, 0, slots),)),
                            (0, 1))
        chunks = plan.chunks(2048)
        self.assertEqual([len(chunk.data) for chunk in chunks], [2048, 2048, 904])
        for chunk in chunks:
            validate_chunk(chunk, 2)
        left_runs = visible_runs(chunks[0], plan.palette, anchor_x=3, anchor_y=2,
                                 width=256, height=224)
        self.assertTrue(all(0 <= x < 256 and len(pixels) <= 256 - x
                            for x, _y, pixels in left_runs))
        damaged = type(chunks[0])(
            chunks[0].data[:-1], chunks[0].spans, chunks[0].crc32, chunks[0].sha256)
        with self.assertRaises(PoseError):
            validate_chunk(damaged, 2)


if __name__ == "__main__":
    unittest.main()
