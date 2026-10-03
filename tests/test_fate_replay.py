from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fate_replay import (  # noqa: E402
    ControllerInputLease,
    activation_observation,
    advance_bounded,
    next_input_safe_window,
    replay_room4_open_trapdoor_prefix,
    room4_message_ready,
    room4_controller_snapshot,
    world_point_direction_mask,
)


class FakeSession:
    def __init__(self) -> None:
        self.frame = 20
        self.inputs: list[tuple[int, bool]] = []
        self.next_run: dict[str, object] | None = None
        self.actual_advance: int | None = None

    def tool(self, name: str, args: dict[str, object]) -> dict[str, object]:
        if name != "set_input":
            raise AssertionError(name)
        self.inputs.append((int(args["buttons"]), bool(args["hold"])))
        return {}

    def get_state(self) -> dict[str, int]:
        return {"frameCount": self.frame}

    def run_frames(self, count: int) -> dict[str, object]:
        result = self.next_run or {
            "startFrame": self.frame,
            "endFrame": self.frame + count,
            "framesAdvanced": count,
            "timedOut": False,
        }
        self.next_run = None
        self.frame += (
            int(result["framesAdvanced"])
            if self.actual_advance is None else self.actual_advance
        )
        return result

    def run_until(self, *, max_frames: int, hook_handle: int) -> dict[str, object]:
        del hook_handle
        self.frame += max_frames
        return {"reason": "maxFrames", "framesAdvanced": max_frames}


class FakeRoom4Session:
    def __init__(self, *, ready: int = 1) -> None:
        self.frame = 100
        self.values = {
            0x7FF2BF: 4, 0x7FF2C2: 0, 0x7E2303: 0, 0x7E2221: 2,
            0x7E5E8A: ready, 0x7E7A20: 0, 0x7E5FE0: 0,
            0x7E5FE1: 117, 0x7E5FE3: 138, 0x7E5FE5: 0,
            0x7E5FE6: 0, 0x7E5F94: 0, 0x7E5FE9: 22,
        }
        self.inputs: list[tuple[int, int]] = []

    def get_state(self) -> dict[str, int]:
        return {"frameCount": self.frame}

    def read_u8(self, address: int) -> int:
        return self.values[address] & 0xFF

    def read_memory(self, mem_type: str, address: int, length: int) -> bytes:
        if mem_type != "snesMemory":
            raise AssertionError(mem_type)
        value = self.values[address]
        return value.to_bytes(length, "little")

    def set_input(self, *, buttons: int, frames: int, port: int) -> dict[str, object]:
        if port != 0:
            raise AssertionError(port)
        self.inputs.append((buttons, frames))
        self.frame += frames
        if buttons == 0x040:
            self.values[0x7E5FE1] -= 2
        elif buttons == 0x010:
            self.values[0x7E5FE3] -= 2
        elif buttons == 0x001:
            if self.values[0x7E5FE0] == 0:
                self.values[0x7E5FE0] = 1
                self.values[0x7E5FE5] = 3
                self.values[0x7E5FE6] = 61
                self.values[0x7E5F94] = 61
            else:
                self.values[0x7E5FE0] = 2
                self.values[0x7E5FE9] += 1
        return {}

    def run_frames(self, count: int) -> dict[str, object]:
        self.frame += count
        return {"framesAdvanced": count, "timedOut": False}


class FateReplayTests(unittest.TestCase):
    @staticmethod
    def talk_state(*, active: int = 1, message: int = 1,
                   delay: int = 0, generation: int = 1) -> bytes:
        raw = bytearray(8)
        raw[0] = active
        raw[1] = message
        raw[4:6] = delay.to_bytes(2, "little")
        raw[6:8] = generation.to_bytes(2, "little")
        return bytes(raw)

    def test_room4_ack_waits_for_unique_ready_message_generation(self) -> None:
        self.assertFalse(room4_message_ready(self.talk_state(delay=1), None))
        self.assertTrue(room4_message_ready(self.talk_state(generation=2), 1))
        self.assertFalse(room4_message_ready(self.talk_state(generation=2), 2))
        self.assertFalse(room4_message_ready(self.talk_state(active=0), None))
        self.assertFalse(room4_message_ready(self.talk_state(message=0), None))

    def test_cursor_tolerance_finishes_the_other_axis_without_oscillation(self) -> None:
        self.assertEqual(world_point_direction_mask(227, 134, 226, 124, tolerance=1), 0x010)
        self.assertEqual(world_point_direction_mask(223, 124, 226, 130, tolerance=1), 0x080)
        self.assertIsNone(world_point_direction_mask(227, 125, 226, 124, tolerance=1))

    def test_activation_batch_keeps_event_times_separate_from_drain_snapshot(self) -> None:
        batch = [
            activation_observation(
                {"frame": 31, "cycleCount": 810, "address": 0xC01234},
                snapshot={"slot": 1, "program": 0xCE, "pc": 0x100},
                synchronized=False,
            ),
            activation_observation(
                {"frame": 31, "cycleCount": 992, "address": 0xC01234},
                snapshot={"slot": 4, "program": 0xCD, "pc": 0x25},
                synchronized=False,
            ),
        ]
        self.assertEqual(
            [event["hook_event"]["cycleCount"] for event in batch], [810, 992]
        )
        self.assertEqual(
            [event["drain_time_snapshot"]["program"] for event in batch],
            [0xCE, 0xCD],
        )
        self.assertTrue(all("program" not in event for event in batch))
        self.assertTrue(all(
            event["snapshot_timing"] == "after_notification_drain" for event in batch
        ))

    def test_error_watch_advances_only_bounded_windows_then_releases_owned_input(self) -> None:
        session = FakeSession()
        with ControllerInputLease(session) as controller:
            controller.hold(0x008)
            pulse = advance_bounded(session, 10, error_hook=77)
            self.assertEqual(pulse["frames_advanced"], 10)
            pulse = advance_bounded(session, 2, error_hook=77)
            self.assertEqual(pulse["end_frame"], 32)
        self.assertEqual(session.inputs, [(0x008, True), (0, True)])

    def test_error_watch_and_ordinary_runner_release_at_the_same_frame(self) -> None:
        observed_inputs: list[list[tuple[int, bool]]] = []
        for error_watch in (False, True):
            session = FakeSession()
            host_frame = session.frame
            release_frame = 40
            with ControllerInputLease(session) as controller:
                controller.hold(0x008)
                while host_frame < 50:
                    if host_frame == release_frame:
                        controller.release()
                        release_frame = -1
                    window = next_input_safe_window(
                        host_frame, 50,
                        release_frame=None if release_frame < 0 else release_frame,
                        sample_interval=13,
                    )
                    self.assertGreater(window, 0)
                    pulse = advance_bounded(
                        session, window,
                        error_hook=77 if error_watch else None,
                    )
                    host_frame = pulse["end_frame"]
            observed_inputs.append(session.inputs)
        self.assertEqual(observed_inputs[0], [(0x008, True), (0, True)])
        self.assertEqual(observed_inputs[1], observed_inputs[0])
        self.assertEqual(next_input_safe_window(
            39, 100, release_frame=40, sample_interval=10
        ), 1)
        self.assertEqual(next_input_safe_window(
            40, 100, release_frame=40, sample_interval=10
        ), 0)

    def test_frame_timeout_or_counter_mismatch_is_not_counted_as_progress(self) -> None:
        session = FakeSession()
        session.next_run = {
            "startFrame": 20,
            "endFrame": 24,
            "framesAdvanced": 4,
            "timedOut": True,
        }
        with self.assertRaisesRegex(RuntimeError, "timed out"):
            advance_bounded(session, 5)

        session = FakeSession()
        session.next_run = {
            "startFrame": 20,
            "endFrame": 22,
            "framesAdvanced": 1,
            "timedOut": False,
        }
        # The tool's own end-frame report matches the live frame count, but
        # its framesAdvanced field does not.
        session.frame = 20
        session.actual_advance = 2
        with self.assertRaisesRegex(RuntimeError, "disagrees"):
            advance_bounded(session, 5)

    def test_owned_input_releases_even_when_the_bounded_operation_raises(self) -> None:
        session = FakeSession()
        with self.assertRaises(ValueError):
            with ControllerInputLease(session) as controller:
                controller.hold(0x001)
                advance_bounded(session, 0)
        self.assertEqual(session.inputs, [(0x001, True), (0, True)])

    def test_room4_replay_driver_sends_and_observes_the_recorded_prefix(self) -> None:
        session = FakeRoom4Session()
        result = replay_room4_open_trapdoor_prefix(session)
        self.assertEqual(len(result["steps"]), 19)
        self.assertEqual(
            [mask for mask, frames in session.inputs if mask],
            [0x040] * 14 + [0x010] * 3 + [0x001, 0x001],
        )
        self.assertTrue(all(
            frames == 4 for mask, frames in session.inputs if mask
        ))
        self.assertTrue(all(
            frames == 1 for mask, frames in session.inputs if not mask
        ))
        self.assertEqual((result["final"]["x"], result["final"]["y"]), (89, 132))
        self.assertEqual(result["final"]["verb"], 3)
        self.assertEqual(result["final"]["object"], 61)
        self.assertEqual(result["final"]["submissions"], 23)
        self.assertEqual(result["final"]["error"], 0)
        self.assertEqual(session.inputs[-1], (0, 1))

    def test_room4_replay_driver_rejects_wrong_start_state_without_input(self) -> None:
        session = FakeRoom4Session(ready=0)
        with self.assertRaisesRegex(RuntimeError, "precondition mismatch"):
            replay_room4_open_trapdoor_prefix(session)
        self.assertEqual(session.inputs, [])


if __name__ == "__main__":
    unittest.main()
