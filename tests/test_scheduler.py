from __future__ import annotations

import unittest

from same.scheduler import Affinity, FrameContext, FrameScheduler, Phase, Task


class SchedulerTests(unittest.TestCase):
    def test_phase_priority_and_name_order_are_deterministic(self) -> None:
        order: list[str] = []
        scheduler = FrameScheduler()

        def callback(name: str, consumed: int):
            def run(context: FrameContext, budget: int) -> int:
                order.append(name)
                return consumed
            return run

        scheduler.register(Task("z", Phase.GUEST, Affinity.SA1, 10, callback("z", 2), priority=2))
        scheduler.register(Task("input", Phase.INPUT, Affinity.SCPU, 10, callback("input", 1)))
        scheduler.register(Task("a", Phase.GUEST, Affinity.SA1, 10, callback("a", 3), priority=2))
        scheduler.register(Task("first", Phase.GUEST, Affinity.SA1, 10, callback("first", 4), priority=1))
        report = scheduler.run_frame(FrameContext(0, {}, None))
        self.assertEqual(order, ["input", "first", "a", "z"])
        self.assertEqual(report.consumed, 10)

    def test_overrun_is_reported_not_hidden(self) -> None:
        scheduler = FrameScheduler()
        scheduler.register(
            Task("bad", Phase.GUEST, Affinity.SA1, 10, lambda context, budget: 17)
        )
        report = scheduler.run_frame(FrameContext(0, {}, None))
        self.assertEqual(report.overruns[0].overrun, 7)

    def test_period(self) -> None:
        count = 0
        scheduler = FrameScheduler()
        def run(context: FrameContext, budget: int) -> int:
            nonlocal count
            count += 1
            return 1
        scheduler.register(Task("periodic", Phase.GUEST, Affinity.SCPU, 1, run, period=3))
        for frame in range(7):
            scheduler.run_frame(FrameContext(frame, {}, None))
        self.assertEqual(count, 3)  # frames 0, 3, 6


if __name__ == "__main__":
    unittest.main()
