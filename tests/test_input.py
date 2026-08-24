from __future__ import annotations

import unittest

from same.input import PhysicalController, SnesButton, profile


class InputTests(unittest.TestCase):
    def test_edges(self) -> None:
        controller = PhysicalController()
        first = controller.update(int(SnesButton.RIGHT | SnesButton.B))
        self.assertEqual(first.pressed, int(SnesButton.RIGHT | SnesButton.B))
        second = controller.update(int(SnesButton.RIGHT))
        self.assertEqual(second.released, int(SnesButton.B))
        self.assertEqual(second.pressed, 0)
        third = controller.update(0)
        self.assertEqual(third.released, int(SnesButton.RIGHT))

    def test_genesis_mapping(self) -> None:
        controller = PhysicalController()
        physical = controller.update(int(SnesButton.RIGHT | SnesButton.Y | SnesButton.A))
        logical = profile("genesis_3button").map_snapshot(physical)
        self.assertEqual(logical.held, frozenset({"right", "a", "c"}))

    def test_arcade_alias_buttons(self) -> None:
        controller = PhysicalController()
        logical = profile("arcade_2button").map_snapshot(controller.update(int(SnesButton.Y)))
        self.assertIn("button1", logical.held)


if __name__ == "__main__":
    unittest.main()
