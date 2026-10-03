from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from trace_fate_first_scumm_error_nexen import room4_message_ready  # noqa: E402


class FateRoom4MessageInputTests(unittest.TestCase):
    @staticmethod
    def state(*, active: int = 1, have_message: int = 1,
              delay: int = 0, generation: int = 1) -> bytes:
        raw = bytearray(9)
        raw[0] = active
        raw[1] = have_message
        raw[4:6] = delay.to_bytes(2, "little")
        raw[6:8] = generation.to_bytes(2, "little")
        return bytes(raw)

    def test_waits_for_authored_display_delay_before_acknowledging(self) -> None:
        self.assertFalse(room4_message_ready(self.state(delay=1), None))
        self.assertTrue(room4_message_ready(self.state(delay=0), None))

    def test_acknowledges_each_ready_generation_once(self) -> None:
        self.assertFalse(room4_message_ready(self.state(generation=7), 7))
        self.assertTrue(room4_message_ready(self.state(generation=8), 7))

    def test_requires_active_message_and_complete_state(self) -> None:
        self.assertFalse(room4_message_ready(self.state(active=0), None))
        self.assertFalse(room4_message_ready(self.state(have_message=0), None))
        self.assertFalse(room4_message_ready(b"\x01\x01", None))


if __name__ == "__main__":
    unittest.main()
