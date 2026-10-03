from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fate_replay import world_point_direction_mask  # noqa: E402


class FateRoom5NavigationTests(unittest.TestCase):
    def test_two_pixel_cursor_lattice_finishes_other_axis_within_tolerance(self) -> None:
        # X=227 is the reachable neighbor of requested X=226. Do not oscillate
        # between 225 and 227 while Y still needs to move upward.
        self.assertEqual(
            world_point_direction_mask(227, 134, 226, 124, tolerance=1),
            0x010,
        )
        self.assertEqual(
            world_point_direction_mask(225, 134, 226, 124, tolerance=1),
            0x010,
        )

    def test_moves_outside_tolerance_on_one_axis_before_the_other(self) -> None:
        self.assertEqual(
            world_point_direction_mask(223, 124, 226, 130, tolerance=1),
            0x080,
        )
        self.assertEqual(
            world_point_direction_mask(226, 124, 226, 130, tolerance=1),
            0x020,
        )

    def test_returns_no_direction_when_both_axes_are_within_tolerance(self) -> None:
        self.assertIsNone(
            world_point_direction_mask(227, 125, 226, 124, tolerance=1)
        )


if __name__ == "__main__":
    unittest.main()
