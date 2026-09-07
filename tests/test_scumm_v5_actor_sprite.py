import unittest
from types import SimpleNamespace

from tools.generate_snes_scumm_actor_sprite import assemble_pose


class ScummV5ActorSpriteTests(unittest.TestCase):
    def test_assembly_uses_scumm_column_major_cels(self):
        # Source cel columns are [1, 2, 3] and [4, 5, 6].  The target canvas
        # is row-major, so the rasterized result must be 1,4 / 2,5 / 3,6.
        cel = SimpleNamespace(width=2, height=3, relative_x=0, relative_y=0,
                              pixels=bytes((1, 2, 3, 4, 5, 6)))
        pose = SimpleNamespace(draw_to_right=True, cels=(cel,))
        result = assemble_pose(SimpleNamespace(palette=tuple(range(16))), pose,
                               width=4, height=12)
        self.assertEqual(result, bytes((0,) * 12 + (0, 0, 1, 4,
                                                     0, 0, 2, 5,
                                                     0, 0, 3, 6) + (0,) * 24))

    def test_assembly_mirrors_destination_without_reversing_source_columns(self):
        cel = SimpleNamespace(width=2, height=1, relative_x=0, relative_y=0,
                              pixels=bytes((1, 2)))
        pose = SimpleNamespace(draw_to_right=False, cels=(cel,))
        result = assemble_pose(SimpleNamespace(palette=tuple(range(16))), pose,
                               width=4, height=10)
        self.assertEqual(result, bytes((0,) * 4 + (0, 2, 1, 0) + (0,) * 32))


if __name__ == "__main__":
    unittest.main()
