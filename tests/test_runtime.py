from __future__ import annotations

from pathlib import Path
import unittest

from same.input import SnesButton
from same.runtime import SameRuntime

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def test_genesis_simulation_routes_services(self) -> None:
        runtime = SameRuntime.from_path(ROOT / "examples/targets/genesis.json")
        words = [0, int(SnesButton.RIGHT), int(SnesButton.RIGHT | SnesButton.B), 0]
        report = runtime.simulate(4, words)
        self.assertEqual(report["frames"], 4)
        self.assertEqual(report["event_queue"]["remaining"], 0)
        self.assertGreater(report["backend"]["service_counts"]["INPUT"], 0)
        self.assertEqual(report["backend"]["music_track"], 1)
        self.assertEqual(report["backend"]["backdrop"], 0x001F)
        task_names = [task["name"] for task in report["scheduler"]]
        self.assertIn("guest.m68k", task_names)
        self.assertIn("guest.z80", task_names)

    def test_openbor_lane_stays_on_scpu(self) -> None:
        runtime = SameRuntime.from_path(ROOT / "examples/targets/openbor.json")
        lane = next(task for task in runtime.scheduler.describe() if task["name"] == "guest.openbor_vm")
        self.assertEqual(lane["affinity"], "SCPU")


if __name__ == "__main__":
    unittest.main()
