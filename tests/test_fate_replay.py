from __future__ import annotations

import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fate_replay import (  # noqa: E402
    ControllerInputLease,
    activation_observation,
    advance_bounded,
    finish_room4_authored_cutscene,
    next_input_safe_window,
    replay_room4_open_trapdoor_prefix,
    replay_room4_open_trapdoor_from_origin,
    replay_room4_trapdoor_use,
    replay_room6_books_interaction,
    replay_room7_lost_dialogue_interaction,
    replay_room7_cat_figure_use,
    replay_room5_rope_to_room6,
    room4_c19_record_snapshot,
    skip_room4_authored_override,
    room4_message_ready,
    room4_controller_snapshot,
    room4_synchronous_input_edge,
    reposition_room4_cursor_to_world,
    world_point_direction_mask,
)
from validate_fate_authentic_startup_nexen import _button_names  # noqa: E402
from replay_fate_room4_cold_nexen import (  # noqa: E402
    _snapshot as cold_startup_snapshot,
    _SnapshotReader,
    _bounded_observation_step,
    _has_watched_resource_wait,
    _has_live_watched_activation,
    _activation_identity_by_slot,
    _require_room4_object_dispatch,
    _native_directory_for_build,
    _observed_pinned_selectors,
    _known_resident_bindings,
    _record_residency_events,
    _generated_input_identity,
    _parse_global_script_selector,
    _parse_room_local_program_table,
    _parse_rom_variable_layout,
    _room_lifecycle_is_idle,
    _room7_runtime_context,
    _room_entry_failure_summary,
    _selected_executable_object_identities,
)
import replay_fate_room4_cold_nexen as cold_startup_module  # noqa: E402


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


class SparseSnapshotSession:
    def __init__(self, values: dict[int, int]) -> None:
        self.values = values
        self.reads: list[tuple[str, int, int]] = []

    def get_state(self) -> dict[str, int]:
        return {"frameCount": 0}

    def read_memory(self, space: str, address: int, length: int) -> bytes:
        if space != "snesMemory":
            raise AssertionError(space)
        self.reads.append((space, address, length))
        return bytes(self.values.get(address + offset, 0) for offset in range(length))


class FakeRoom4Session:
    def __init__(self, *, ready: int = 1,
                 cursor: tuple[int, int] = (117, 138),
                 camera: tuple[int, int] = (0, 100),
                 input_poll_delay_frames: int = 0) -> None:
        self.frame = 100
        self.values = {
            0x7FF2BF: 4, 0x7FF2C2: 0, 0x7E2303: 0, 0x7E2221: 2,
            0x7E5E8A: ready, 0x7E7A20: 0, 0x7E5FE0: 0,
            0x7E5FE1: cursor[0] & 0xFFFF, 0x7E5FE3: cursor[1] & 0xFFFF,
            0x7E5FE5: 0,
            0x7E7FB8: camera[0], 0x7E7FAA: camera[1],
            0x7E5FE6: 0, 0x7E5F94: 0, 0x7E5FE9: 22,
            0x7FD348: 0,
            0x7E2200: 0, 0x7E2202: 0, 0x7E2204: 0, 0x7E2206: 0,
            0x7E2208: 0, 0x7E220A: 0, 0x7E220C: 0,
        }
        self.inputs: list[tuple[int, int]] = []
        self.controller_events: list[tuple[int, int, bool, int]] = []
        self.advances: list[tuple[int, int, int, int]] = []
        self.dangerous_set_input_calls: list[tuple[int, int, int]] = []
        self.held_buttons = 0
        self.pending_edge = 0
        self.pending_edge_sampled = False
        self.fail_next_advance = False
        self.cutscene_finish_after = 0
        self.pending_edge_delay = 0
        self.input_poll_delay_frames = input_poll_delay_frames
        self.input_poll_delay_remaining = 0
        self.override_owner_slot = 3

    def get_state(self) -> dict[str, int]:
        return {"frameCount": self.frame}

    def read_u8(self, address: int) -> int:
        return self.values.get(address, 0) & 0xFF

    def read_memory(self, mem_type: str, address: int, length: int) -> bytes:
        if mem_type != "snesMemory":
            raise AssertionError(mem_type)
        value = self.values.get(address, 0)
        return value.to_bytes(length, "little")

    def tool(self, name: str, args: dict[str, object]) -> dict[str, object]:
        if name != "set_input":
            raise AssertionError(name)
        buttons = int(args["buttons"])
        hold = bool(args["hold"])
        frames = int(args["frames"])
        if frames != 0:
            raise AssertionError("durable replay must not advance in set_input")
        self.inputs.append((buttons, frames))
        self.controller_events.append((self.frame, buttons, hold, frames))
        if buttons and buttons != self.held_buttons:
            self.pending_edge = buttons
            self.pending_edge_sampled = False
            self.input_poll_delay_remaining = self.input_poll_delay_frames
        self.held_buttons = buttons
        return {}

    def set_input(self, *, buttons: int, frames: int, port: int) -> dict[str, object]:
        """Model the wall-clock overshoot hazard of set_input(frames=...)."""
        if port != 0:
            raise AssertionError(port)
        self.dangerous_set_input_calls.append((buttons, frames, self.frame))
        self.frame += frames * 2
        if buttons:
            self._apply_edge(buttons)
            self._apply_edge(buttons)
        return {}

    def run_frames(self, count: int) -> dict[str, object]:
        if self.fail_next_advance:
            self.fail_next_advance = False
            raise RuntimeError("simulated frame runner failure")
        start = self.frame
        held = self.held_buttons
        self.advances.append((start, start + count, count, held))
        previous = self.values[0x7E2200]
        for _ in range(count):
            current = self._internal_buttons(held)
            if held and self.input_poll_delay_remaining:
                current = previous
                self.input_poll_delay_remaining -= 1
            self.values[0x7E2202] = previous
            self.values[0x7E2200] = current
            self.values[0x7E2204] = current & ~previous
            self.values[0x7E2206] = previous & ~current
            if self.values[0x7E2204]:
                self.values[0x7E2208] = (self.values[0x7E2208] + 1) & 0xFFFF
                self.pending_edge_sampled = bool(self.pending_edge)
                if self.values[0x7E7A20]:
                    self.values[0x7E220A] = self.values[0x7E2208]
                    self.values[0x7E220C] = 1
            if self.pending_edge and self.pending_edge_sampled:
                talk_owns_edge = (
                    self.values[0x7E220C]
                    and self.values[0x7E220A] == self.values[0x7E2208]
                    and self.values[0x7E7A20]
                )
                if self.pending_edge_delay:
                    self.pending_edge_delay -= 1
                else:
                    if not talk_owns_edge:
                        self._apply_edge(self.pending_edge)
                    self.pending_edge = 0
                    self.pending_edge_sampled = False
            if self.cutscene_finish_after and held == 0:
                self.cutscene_finish_after -= 1
                if self.cutscene_finish_after <= 0:
                    self.values[0x7FD348] = 0
            previous = current
            self.frame += 1
        return {
            "startFrame": start,
            "endFrame": self.frame,
            "framesAdvanced": count,
            "timedOut": False,
        }

    @staticmethod
    def _internal_buttons(buttons: int) -> int:
        return {
            0x001: 0x0080,
            0x010: 0x0800,
            0x020: 0x0400,
            0x040: 0x0200,
            0x080: 0x0100,
            0x100: 0x0040,
            0x800: 0x4000,
        }.get(buttons, 0)

    def _apply_edge(self, buttons: int) -> None:
        if buttons == 0x040:
            self.values[0x7E5FE1] = (self.values[0x7E5FE1] - 2) & 0xFFFF
        elif buttons == 0x080:
            self.values[0x7E5FE1] = (self.values[0x7E5FE1] + 2) & 0xFFFF
        elif buttons == 0x010:
            self.values[0x7E5FE3] = (self.values[0x7E5FE3] - 2) & 0xFFFF
        elif buttons == 0x020:
            self.values[0x7E5FE3] = (self.values[0x7E5FE3] + 2) & 0xFFFF
        if buttons in (0x040, 0x080, 0x010, 0x020):
            x = (self.values[0x7E5FE1] + self.values.get(0x7E7FB8, 0)) & 0xFFFF
            y = (self.values[0x7E5FE3] + self.values.get(0x7E7FAA, 0) - 0x64) & 0xFFFF
            self.values[0x7E5F94] = int(64 <= x < 104 and 128 <= y < 136) * 61
        elif buttons == 0x001:
            if self.values[0x7E5FE0] == 0:
                self.values[0x7E5FE0] = 1
                self.values[0x7E5FE5] = 3
                self.values[0x7E5FE6] = 61
                self.values[0x7E5F94] = 61
            else:
                self.values[0x7E5FE0] = 2
                self.values[0x7E5FE9] += 1
        elif buttons == 0x100:
            if self.values[0x7FD348]:
                if self.values.get(0x7FD356) == 126:
                    self.values[0x7FD348] = 0
                self.values[0x7FD356] = 0
                self.values[0x7FD35F] = 0
                self.values[0x7FD363 + self.override_owner_slot] = 0
                self.cutscene_finish_after = 5
        elif buttons == 0x800:
            if self.values[0x7E5FE0] == 1 and self.values[0x7E5FE6] == 61:
                verbs = (3, 4, 9, 10)
                current = self.values[0x7E5FE5]
                self.values[0x7E5FE5] = verbs[(verbs.index(current) + 1) % len(verbs)]

    def activate_room4_override(self, *, slot: int = 3, pc: int = 0x0019,
                                owner_depth: int = 1) -> None:
        self.override_owner_slot = slot
        self.values.update({
            0x7FD348: 1,
            0x7FD356: pc,
            0x7FD35F: slot,
            0x7E2380 + slot: 2,
            0x7E2399 + slot: 206,
            0x7E23B2 + slot: 0xF9,
            0x7FF2E7 + slot: 4,
            0x7FD363 + slot: owner_depth,
        })


class FakeRoom5Session(FakeRoom4Session):
    """Copyright-free controller fixture for the authored room5 rope step."""

    def __init__(self) -> None:
        super().__init__(cursor=(145, 134))
        self.values.update({
            0x7FF2BF: 5,
            0x7E5FE5: 0,
            0x7E5FE6: 0,
            0x7E5FE9: 40,
            0x7F3716: 5,
            0x7E2BA8: 0,
        })

    def _apply_edge(self, buttons: int) -> None:
        if buttons in (0x040, 0x080, 0x010, 0x020):
            super()._apply_edge(buttons)
            # This room's controller hit test is performed on selection, not
            # continuously while the cursor moves.
            self.values[0x7E5F94] = 0
        elif buttons == 0x001:
            if self.values[0x7E5FE0] == 0:
                x, y = self.values[0x7E5FE1], self.values[0x7E5FE3]
                if not (224 <= x < 264 and 120 <= y < 128):
                    return
                self.values[0x7E5FE0] = 1
                self.values[0x7E5FE5] = 8
                self.values[0x7E5FE6] = 77
                self.values[0x7E5F94] = 77
            else:
                self.values[0x7E5FE0] = 2
                self.values[0x7E5FE9] += 1
        elif buttons == 0x800:
            if self.values[0x7E5FE0] == 1 and self.values[0x7E5FE6] == 77:
                self.values[0x7E5FE5] = 9


class FakeRoom6Session(FakeRoom4Session):
    """Copyright-free controller fixture for the room6 authored books verb."""

    def __init__(self, cursor: tuple[int, int] = (226, 139)) -> None:
        super().__init__(cursor=cursor)
        self.values.update({
            0x7FF2BF: 6,
            0x7E5FE5: 0,
            0x7E5FE6: 0,
            0x7E5FE9: 70,
            0x7F3716: 6,
            0x7E2BA8: 0,
        })

    def _apply_edge(self, buttons: int) -> None:
        if buttons in (0x040, 0x080, 0x010, 0x020):
            super()._apply_edge(buttons)
            # This room recomputes hit ownership on the A selection edge.
            self.values[0x7E5F94] = 0
        elif buttons == 0x001:
            if self.values[0x7E5FE0] == 0:
                x, y = self.values[0x7E5FE1], self.values[0x7E5FE3]
                if not (0 <= x < 40 and 40 <= y < 128):
                    return
                self.values[0x7E5FE0] = 1
                self.values[0x7E5FE5] = 9
                self.values[0x7E5FE6] = 91
                self.values[0x7E5F94] = 91
            else:
                self.values[0x7E5FE0] = 2
                self.values[0x7E5FE9] += 1
        elif buttons == 0x800:
            if (self.values[0x7E5FE0] == 1
                    and self.values[0x7E5FE6] == 91
                    and self.values[0x7E5FE5] == 9):
                self.values[0x7E5FE5] = 10


class FakeRoom7Session(FakeRoom4Session):
    """Copyright-free model for the source-derived room7 book sentence."""

    VARIABLE_BASE = 0x7E0800
    VARIABLE_COUNT = 0x0320

    def __init__(self, cursor: tuple[int, int] = (162, 129)) -> None:
        super().__init__(cursor=cursor)
        self.values.update({
            0x7FF2BF: 7,
            0x7E5FE5: 0,
            0x7E5FE6: 0,
            0x7E5FE9: 90,
            0x7F3716: 7,
            0x7E2BA8: 0,
        })
        self.variables = bytearray(self.VARIABLE_COUNT * 2)

    def read_memory(self, mem_type: str, address: int, length: int) -> bytes:
        if address == self.VARIABLE_BASE:
            return bytes(self.variables[:length])
        return super().read_memory(mem_type, address, length)

    def _apply_edge(self, buttons: int) -> None:
        if buttons in (0x040, 0x080, 0x010, 0x020):
            super()._apply_edge(buttons)
            self.values[0x7E5F94] = 0
        elif buttons == 0x001:
            if self.values[0x7E5FE0] == 0:
                x, y = self.values[0x7E5FE1], self.values[0x7E5FE3]
                if not (176 <= x < 200 and 120 <= y < 128):
                    return
                self.values[0x7E5FE0] = 1
                self.values[0x7E5FE5] = 9
                self.values[0x7E5FE6] = 133
                self.values[0x7E5F94] = 133
            else:
                self.values[0x7E5FE0] = 2
                self.values[0x7E5FE9] += 1
        elif buttons == 0x800:
            if (self.values[0x7E5FE0] == 1
                    and self.values[0x7E5FE6] == 133
                    and self.values[0x7E5FE5] == 9):
                self.values[0x7E5FE5] = 11


class FakeRoom7CatSession(FakeRoom4Session):
    """Controller model for the authored two-distinct-cat progression gate."""

    VARIABLE_BASE = 0x7E0800
    VARIABLE_COUNT = 0x0320

    def __init__(self, cursor: tuple[int, int] = (188, 125)) -> None:
        super().__init__(cursor=cursor)
        self.values.update({
            0x7FF2BF: 7, 0x7FF2C2: 0, 0x7E2303: 0, 0x7E2221: 2,
            0x7E5E8A: 1, 0x7E7A20: 0, 0x7E5FE0: 1,
            0x7E5FE5: 9, 0x7E5FE6: 133, 0x7E5FE9: 128,
            0x7F3716: 7, 0x7E2BA8: 0,
        })
        self.variables = bytearray(self.VARIABLE_COUNT * 2)
        self.owners = bytearray(2048)
        for object_id in (118, 119, 133):
            self.owners[object_id] = 15
        self.owners[937] = 1
        self.object_states = {118: 0, 119: 0, 133: 0}

    def read_u8(self, address: int) -> int:
        if 0x7E8000 <= address < 0x7E8000 + len(self.owners):
            return self.owners[address - 0x7E8000]
        if address in (0x7E6000 + 118, 0x7E6000 + 119, 0x7E6000 + 133):
            return self.object_states[address - 0x7E6000]
        return super().read_u8(address)

    def read_memory(self, mem_type: str, address: int, length: int) -> bytes:
        if address == self.VARIABLE_BASE:
            return bytes(self.variables[:length])
        if address == 0x7E8000:
            return bytes(self.owners[:length])
        if address == 0x7E6000 + 112:
            raw = bytearray(length)
            for object_id, state in self.object_states.items():
                offset = object_id - 112
                if 0 <= offset < length:
                    raw[offset] = state
            return bytes(raw)
        return super().read_memory(mem_type, address, length)

    def _apply_edge(self, buttons: int) -> None:
        if buttons in (0x040, 0x080, 0x010, 0x020):
            if buttons == 0x040:
                self.values[0x7E5FE1] -= 2
            elif buttons == 0x080:
                self.values[0x7E5FE1] += 2
            elif buttons == 0x010:
                self.values[0x7E5FE3] -= 2
            else:
                self.values[0x7E5FE3] += 2
            if self.values[0x7E5FE0] == 1:
                self.values.update({0x7E5FE0: 0, 0x7E5FE5: 0, 0x7E5FE6: 0})
            self.values[0x7E5F94] = 0
        elif buttons == 0x001:
            mode = self.values[0x7E5FE0]
            x, y = self.values[0x7E5FE1], self.values[0x7E5FE3]
            hit = (118 if 104 <= x < 120 and 112 <= y < 136 else
                   119 if 120 <= x < 136 and 112 <= y < 136 else 0)
            self.values[0x7E5F94] = hit
            if mode == 0 and hit:
                self.values.update({0x7E5FE0: 1, 0x7E5FE5: 9, 0x7E5FE6: hit})
            elif mode == 1:
                self.values[0x7E5FE0] = 2
                self.values[0x7E5FE9] = (self.values[0x7E5FE9] + 1) & 0xFF
        elif buttons == 0x800 and self.values[0x7E5FE0] == 1:
            self.values[0x7E5FE5] = 10

    def complete_cat_action(self, object_id: int) -> None:
        """Apply the source-described result after the fake sentence executes."""
        if object_id not in (118, 119) or self.values[0x7E5FE6] != object_id:
            raise AssertionError("unexpected cat-action completion")
        marker = 217 if object_id == 118 else 218
        self.variables[marker * 2:marker * 2 + 2] = (1).to_bytes(2, "little")
        value = int.from_bytes(self.variables[428:430], "little") + 1
        self.variables[428:430] = value.to_bytes(2, "little")
        self.values.update({0x7E5FE0: 1, 0x7E5FE5: 9})
        if object_id == 119:
            self.values[0x7F3716] = 3


class FateReplayTests(unittest.TestCase):
    def test_room_entry_failure_keeps_program_page_ownership_diagnostics(self) -> None:
        cache = {
            "slots": [{"slot": 2, "program_unit_id": 19,
                       "pins": 0x80, "generation": 7}],
            "completion_waiters": [{"page": 2, "selector": 0xD3,
                                    "c4_slot": 4, "held": True}],
            "page_lookup": {"pc": 0x2345, "remaining": 0},
            "provider": {"status": 4, "error": 0, "bytes_read": 8192},
        }
        result = _room_entry_failure_summary({
            "status": "bounded-observation-limit",
            "final": {"program_cache": cache},
        })
        self.assertEqual(result["program_cache"], cache)

    def test_snapshot_reader_batches_room_observer_wram_windows(self) -> None:
        session = SparseSnapshotSession({})
        reader = _SnapshotReader(session)
        reads_after_capture = len(session.reads)
        self.assertEqual(reads_after_capture, 5)
        for address in (
            0x7E2200, 0x7E5F19, 0x7E5F92, 0x7E5FE0, 0x7E6000,
            0x7E7A20, 0x7E8C00, 0x7FD300, 0x7FF100, 0x7F3700,
        ):
            self.assertEqual(reader.read_memory("snesMemory", address, 1), b"\x00")
        self.assertEqual(len(session.reads), reads_after_capture)

    def test_room_entry_observation_chunks_never_exceed_frame_budget(self) -> None:
        start = 100
        budget = 33
        steps = []
        current = start
        while True:
            step = _bounded_observation_step(start, current, budget)
            if step == 0:
                break
            steps.append(step)
            current += step
        self.assertEqual(steps, [16, 16, 1])
        self.assertEqual(current - start, budget)
        self.assertEqual(_bounded_observation_step(start, current, budget), 0)
        self.assertEqual(_bounded_observation_step(start, current + 1, budget), 0)

    def test_room7_cat_selection_unions_both_object_program_tiers(self) -> None:
        selected = _selected_executable_object_identities({
            "SAME_SCUMM_APPEND_EXECUTABLE_LOCAL_OBJECTS": "4:60,7:118,7:119",
            "SAME_SCUMM_APPEND_TERMINAL_EXECUTABLE_LOCAL_OBJECTS": "7:133",
        })
        self.assertEqual(selected, {"4:60", "7:118", "7:119", "7:133"})

    def test_room_action_quiescence_requires_idle_committed_lifecycle(self) -> None:
        settled = {
            "room": 6,
            "phase": 0,
            "active_record": 3,
            "pending_record": 3,
            "pending_room": 6,
        }
        self.assertTrue(_room_lifecycle_is_idle(settled))

        exiting = {
            **settled,
            "phase": 1,
            "pending_record": 4,
            "pending_room": 7,
        }
        self.assertFalse(_room_lifecycle_is_idle(exiting))

        pending_before_phase_advance = {
            **settled,
            "pending_room": 7,
        }
        self.assertFalse(_room_lifecycle_is_idle(pending_before_phase_advance))

        record_mismatch = {
            **settled,
            "pending_record": 4,
        }
        self.assertFalse(_room_lifecycle_is_idle(record_mismatch))

    def test_room4_replay_requires_normalized_object_carrier_dispatch(self) -> None:
        result = {
            "final": {"start_object": {
                "exec_count": 5, "object": 61, "entry": 10,
                "program": 214, "entry_offset": 203,
            }},
            "frame_boundary_execution_samples": [{
                "frame": 1234,
                "start_object": {
                    "exec_count": 5, "object": 61, "entry": 10,
                    "program": 214, "entry_offset": 203,
                },
                "slots": [{
                    "program": 214,
                    "program_unit_identity": "ObjectProgram(room=4,object=61)",
                }],
            }],
        }
        evidence = _require_room4_object_dispatch(
            result, before_count=4, verb=10, entry_offset=203,
        )
        self.assertEqual(evidence["semantic_identity"],
                         "ObjectVerb(room=4,object=61,verb=10)")
        self.assertEqual(evidence["dispatch_count"], 1)
        result["frame_boundary_execution_samples"][0]["slots"] = []
        with self.assertRaisesRegex(RuntimeError, "canonical carrier"):
            _require_room4_object_dispatch(
                result, before_count=4, verb=10, entry_offset=203,
            )

    def test_room4_replay_accepts_completed_verb_with_canonical_resident_binding(self) -> None:
        result = {
            "final": {"start_object": {
                "exec_count": 9, "object": 61, "entry": 10,
                "program": 214, "entry_offset": 203,
            }},
            "frame_boundary_execution_samples": [{
                "frame": 2870,
                "start_object": {
                    "exec_count": 9, "object": 61, "entry": 10,
                    "program": 214, "entry_offset": 203,
                },
                # The tiny OBCD activation completed between samples.
                "slots": [],
                "start_object_program_binding": {
                    "selector": 214,
                    "identity": "ObjectProgram(room=4,object=61)",
                    "generation": 2,
                },
            }],
        }
        evidence = _require_room4_object_dispatch(
            result, before_count=8, verb=10, entry_offset=203,
        )
        self.assertEqual(evidence["carrier_evidence"], ["resident-binding"])
        self.assertEqual(evidence["sample_frames"], [2870])

        result["frame_boundary_execution_samples"][0][
            "start_object_program_binding"
        ]["identity"] = "RoomEntryProgram(5)"
        with self.assertRaisesRegex(RuntimeError, "canonical carrier"):
            _require_room4_object_dispatch(
                result, before_count=8, verb=10, entry_offset=203,
            )

    def test_action_wait_resource_is_not_a_quiescent_boundary(self) -> None:
        slots = [
            {"slot": 2, "status": 5},
            {"slot": 4, "status": 2},
        ]
        self.assertTrue(_has_watched_resource_wait(slots, {2, 7}))
        self.assertFalse(_has_watched_resource_wait(slots, {4, 7}))
        self.assertFalse(_has_watched_resource_wait(
            [{"slot": 2, "status": 2}], {2},
        ))

    def test_action_owned_yielded_activation_is_not_quiescent(self) -> None:
        slots = [
            {"slot": 2, "status": 2},
            {"slot": 4, "status": 4},
        ]
        self.assertTrue(_has_live_watched_activation(slots, {2, 7}))
        self.assertFalse(_has_live_watched_activation(slots, {4, 7}))
        self.assertFalse(_has_live_watched_activation(
            [{"slot": 2, "status": 0}], {2},
        ))

    def test_activation_baseline_includes_canonical_binding_generation(self) -> None:
        slots = [{
            "slot": 3, "script": 2, "program": 252,
            "program_unit_id": 97, "binding_generation": 1,
        }]
        baseline = _activation_identity_by_slot(slots)
        self.assertEqual(baseline[3], (2, 252, 97, 1))
        slots[0]["binding_generation"] = 2
        self.assertNotEqual(
            baseline[3], _activation_identity_by_slot(slots)[3],
        )

    def test_room4_cursor_world_coordinates_follow_native_camera_transform(self) -> None:
        session = FakeRoom4Session(cursor=(-31, 140), camera=(148, 98))
        state = room4_controller_snapshot(session)
        self.assertEqual((state["cursor_world_x"], state["cursor_world_y"]), (117, 138))
        result = replay_room4_open_trapdoor_prefix(session)
        self.assertEqual(
            (result["precondition"]["cursor_world_x"],
             result["precondition"]["cursor_world_y"]),
            (117, 138),
        )
        self.assertEqual(
            ((result["final"]["x"] + 148) & 0xFFFF,
             (result["final"]["y"] + 98 - 100) & 0xFFFF),
            (89, 132),
        )
        self.assertEqual(result["final"]["hit_object"], 61)

    def test_room4_cursor_reposition_is_bounded_and_does_not_submit_sentence(self) -> None:
        session = FakeRoom4Session(cursor=(-31, 140), camera=(0, 100))
        moved = reposition_room4_cursor_to_world(session, (117, 138))
        self.assertEqual(len(moved["steps"]), 75)
        self.assertEqual(moved["sentence_submission_delta"], 0)
        self.assertEqual(
            (moved["final"]["cursor_world_x"], moved["final"]["cursor_world_y"]),
            (117, 138),
        )
        action = replay_room4_open_trapdoor_prefix(session)
        self.assertEqual(action["final"]["hit_object"], 61)
        self.assertEqual(action["final"]["submissions"], 23)

    def test_cold_startup_snapshot_reads_room_counters_not_adjacent_timing_fields(self) -> None:
        room_requests = 0x1234
        room_validations = 0x5678
        values = {
            0x7E2FB0: 3,
            0x7E2FED: room_requests & 0xFF,
            0x7E2FEE: room_requests >> 8,
            0x7E2FEF: room_validations & 0xFF,
            0x7E2FF0: room_validations >> 8,
            # Adjacent timing fields intentionally carry different sentinels.
            0x7E2FF3: 0xAA,
            0x7E2FF4: 0xBB,
            0x7E2FF5: 0xCC,
            0x7E2FF6: 0xDD,
            0x7E2347: 0xA5,
        }
        with (
            patch("replay_fate_room4_cold_nexen.ACTIVE_DYNAMIC_RESIDENCY", True),
            patch("replay_fate_room4_cold_nexen.ACTIVE_MSU_PROGRAMS", True),
        ):
            observed = cold_startup_snapshot(SparseSnapshotSession(values))
        self.assertEqual(observed["program_cache"]["room_requests"], room_requests)
        self.assertEqual(observed["program_cache"]["execution_depth"], 3)
        self.assertEqual(
            observed["program_cache"]["room_validations"], room_validations
        )
        self.assertEqual(observed["condition"], 0xA5)

    def test_rom_backed_dynamic_snapshot_does_not_read_msu_only_state(self) -> None:
        session = SparseSnapshotSession({})
        with (
            patch("replay_fate_room4_cold_nexen.ACTIVE_DYNAMIC_RESIDENCY", True),
            patch("replay_fate_room4_cold_nexen.ACTIVE_MSU_PROGRAMS", False),
            patch("replay_fate_room4_cold_nexen.ACTIVE_LIVE_ROOM_RESOURCES", False),
        ):
            observed = cold_startup_snapshot(session, include_live_room=True)
        self.assertNotIn("program_cache", observed)
        self.assertNotIn("live_room_header", observed)

    def test_dynamic_build_report_is_resolved_from_its_isolated_output_root(self) -> None:
        import hashlib
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            build_root = Path(temporary) / "build"
            dynamic_root = build_root / "fate-dynamic-residency"
            dynamic_root.mkdir(parents=True)
            directory = {"entries": [{
                "program_unit_id": 7,
                "identity": "GlobalProgram(1)",
            }]}
            directory_bytes = (json.dumps(directory, sort_keys=True) + "\n").encode()
            (dynamic_root / "native-program-directory.json").write_bytes(directory_bytes)
            report = {
                "native_program_directory": "native-program-directory.json",
                "native_program_directory_sha256": hashlib.sha256(
                    directory_bytes
                ).hexdigest(),
            }
            (dynamic_root / "cooked-rooms.json").write_text(
                json.dumps(report), encoding="utf-8",
            )
            identity_path = build_root / "dynamic.build_identity.json"
            identity_path.write_text(json.dumps({
                "explicit_environment": {
                    "SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY": "1",
                },
            }), encoding="utf-8")

            result = _native_directory_for_build(identity_path)

        self.assertEqual(result["path"], str(
            dynamic_root / "native-program-directory.json"
        ))
        self.assertEqual(result["by_identity"]["GlobalProgram(1)"]["program_unit_id"], 7)

    def test_dynamic_build_report_discovery_rejects_ambiguous_outputs(self) -> None:
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as temporary:
            build_root = Path(temporary) / "build"
            dynamic_root = build_root / "fate-dynamic-residency"
            dynamic_root.mkdir(parents=True)
            (build_root / "cooked-rooms.json").write_text("{}", encoding="utf-8")
            (dynamic_root / "cooked-rooms.json").write_text("{}", encoding="utf-8")
            identity_path = build_root / "dynamic.build_identity.json"
            identity_path.write_text(json.dumps({
                "explicit_environment": {
                    "SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY": "1",
                },
            }), encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "ambiguous"):
                _native_directory_for_build(identity_path)

    def test_dynamic_build_report_uses_identity_bound_custom_build_root(self) -> None:
        import hashlib
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dynamic_root = root / "isolated-dynamic-output"
            dynamic_root.mkdir()
            directory = {"entries": [{
                "program_unit_id": 9,
                "identity": "RoomEntryProgram(room=4)",
            }]}
            payload = (json.dumps(directory, sort_keys=True) + "\n").encode()
            (dynamic_root / "native-program-directory.json").write_bytes(payload)
            (dynamic_root / "cooked-rooms.json").write_text(json.dumps({
                "native_program_directory": "native-program-directory.json",
                "native_program_directory_sha256": hashlib.sha256(payload).hexdigest(),
            }), encoding="utf-8")
            identity_path = root / "route.build_identity.json"
            identity_path.write_text(json.dumps({
                "explicit_environment": {
                    "SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY": "1",
                    "SAME_SCUMM_DYNAMIC_FATE_BUILD_DIR": str(dynamic_root),
                },
            }), encoding="utf-8")

            result = _native_directory_for_build(identity_path)

        self.assertEqual(result["by_identity"]["RoomEntryProgram(room=4)"][
            "program_unit_id"
        ], 9)

    def test_dynamic_report_ignores_stale_shared_native_directory(self) -> None:
        import hashlib
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build_root = root / "isolated-dynamic-output"
            build_root.mkdir()
            report_directory = build_root / "native-directory.json"
            report_bytes = (json.dumps({"entries": [{
                "program_unit_id": 42,
                "identity": "GlobalProgram(42)",
            }]}, sort_keys=True) + "\n").encode()
            report_directory.write_bytes(report_bytes)
            (build_root / "cooked-rooms.json").write_text(json.dumps({
                "native_program_directory": "native-directory.json",
                "native_program_directory_sha256": hashlib.sha256(
                    report_bytes
                ).hexdigest(),
            }), encoding="utf-8")

            # Simulate a later build replacing the old shared generated file.
            shared = root / "runtime/snes/generated"
            shared.mkdir(parents=True)
            (shared / "scumm_v5_native_program_directory.json").write_text(
                json.dumps({"entries": [{
                    "program_unit_id": 7,
                    "identity": "GlobalProgram(7)",
                }]}), encoding="utf-8",
            )

            identity_path = root / "route.build_identity.json"
            identity_path.write_text(json.dumps({
                "explicit_environment": {
                    "SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY": "1",
                    "SAME_SCUMM_DYNAMIC_FATE_BUILD_DIR": str(build_root),
                },
            }), encoding="utf-8")
            result = _native_directory_for_build(identity_path)

        self.assertEqual(result["by_identity"]["GlobalProgram(42)"][
            "program_unit_id"
        ], 42)

    def test_dynamic_build_writes_native_directory_inside_owned_root(self) -> None:
        build_script = (ROOT / "tools/build_snes.sh").read_text(encoding="utf-8")
        dynamic_start = build_script.index(
            'if [[ "${SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY:-0}" == "1" ]]; then',
            build_script.index("ROOM_GENERATOR_REPORT=")
        )
        dynamic_block = build_script[dynamic_start:]
        self.assertIn(
            '--native-directory-output "$M23A_BUILD/scumm_v5_native_program_directory.json"',
            dynamic_block,
        )
        self.assertIn(
            '--native-directory-include "$M23A_BUILD/scumm_v5_native_program_directory.inc.pasm"',
            dynamic_block,
        )

    def test_generated_input_provenance_uses_sealed_manifest_not_mutable_workspace(self) -> None:
        import hashlib
        import json

        manifest = [{"path": "runtime/generated.inc", "sha256": "a" * 64}]
        identity = {
            "generated_inputs": manifest,
            "generated_inputs_sha256": hashlib.sha256(
                json.dumps(manifest, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }
        self.assertEqual(
            _generated_input_identity(identity, "runtime/generated.inc"),
            manifest[0],
        )
        identity["generated_inputs_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "manifest is inconsistent"):
            _generated_input_identity(identity, "runtime/generated.inc")

    def test_residency_observer_excludes_uninitialized_unmapped_rows(self) -> None:
        rows = [
            {"selector": 0xD0, "program_unit_id": 0xBEEF,
             "identity": None, "generation": 0x1234, "flags": 1},
            {"selector": 0xD1, "program_unit_id": 7,
             "identity": "GlobalProgram(7)", "generation": 1, "flags": 1},
        ]
        self.assertEqual(_known_resident_bindings(rows), [rows[1]])

    def test_observed_pins_include_bundle_flags_and_live_slots_once(self) -> None:
        bindings = [
            {"selector": 0xD0, "flags": 3},
            {"selector": 0xD1, "flags": 1},
            {"selector": 0xD2, "flags": 5},
        ]
        slots = [
            {"status": 2, "program": 0xD1},
            {"status": 3, "program": 0xD2},
            {"status": 4, "program": 0xD0},
            {"status": 2, "program": 0xA0},
        ]
        self.assertEqual(
            _observed_pinned_selectors(bindings, slots), {0xD0, 0xD1, 0xD2}
        )

    def test_residency_telemetry_recognizes_release_then_rebind_as_reuse(self) -> None:
        previous: dict[int, dict[str, object]] = {}
        history: dict[int, dict[str, object]] = {}
        events: list[dict[str, object]] = []
        first = {
            "selector": 0xD0, "program_unit_id": 17,
            "identity": "RoomLocal(room=4,local=206)",
            "generation": 1, "flags": 3,
        }

        _record_residency_events(10, {0xD0: first}, previous, history, events)
        previous.clear()
        previous[0xD0] = first
        _record_residency_events(20, {}, previous, history, events)
        previous.clear()
        second = {
            "selector": 0xD0, "program_unit_id": 29,
            "identity": "RoomEntry(room=5)",
            "generation": 2, "flags": 3,
        }
        _record_residency_events(30, {0xD0: second}, previous, history, events)

        reuse = [event for event in events if event["event"] == "reuse"]
        self.assertEqual(len(reuse), 1)
        self.assertEqual(reuse[0]["reuse_kind"], "released_rebind")
        self.assertEqual(reuse[0]["old_program_unit_id"], 17)
        self.assertEqual(reuse[0]["old_generation"], 1)
        self.assertEqual(reuse[0]["new_program_unit_id"], 29)
        self.assertEqual(reuse[0]["new_generation"], 2)

    def test_residency_telemetry_labels_unsampled_owner_change_cautiously(self) -> None:
        old = {
            "selector": 0xD0, "program_unit_id": 17,
            "identity": "ObjectProgram(room=4,object=61)",
            "generation": 1, "flags": 3,
        }
        new = {
            "selector": 0xD0, "program_unit_id": 29,
            "identity": "ObjectProgram(room=5,object=77)",
            "generation": 2, "flags": 3,
        }
        events: list[dict[str, object]] = []
        _record_residency_events(20, {0xD0: new}, {0xD0: old}, {}, events)
        self.assertEqual(events[0]["event"], "reuse")
        self.assertEqual(events[0]["reuse_kind"], "sampled_owner_change")
        self.assertIn("intermediate release/valid transitions were not sampled",
                      events[0]["observation"])

    def test_room7_runtime_snapshot_reads_authored_vars_bits_and_objects(self) -> None:
        class Ram:
            def read_u8(self, address: int) -> int:
                if address == 0x7E8000 + 937:
                    return 1
                self_outer.assertEqual(address, 0x7F6F1B)
                return 1

            def read_memory(self, memory_type: str, address: int, length: int) -> bytes:
                self_outer.assertEqual(memory_type, "snesMemory")
                raw = bytearray(length)
                if address == 0x7E0800:
                    raw[214 * 2:214 * 2 + 2] = b"\x01\x00"
                    raw[215 * 2:215 * 2 + 2] = b"\x02\x00"
                elif address == 0x7E2BA0:
                    raw[69 >> 3] = 1 << (69 & 7)
                elif address == 0x7E6000 + 112:
                    raw[4] = 3
                elif address == 0x7E8000 + 112:
                    raw[4] = 1
                elif address == 0x7E8000:
                    raw[937] = 1
                elif address == 0x7F5F10:
                    # Empty class table for this fixture; production reads
                    # the same 0x1000-byte table to report room-7 classes.
                    pass
                else:
                    raise AssertionError(hex(address))
                return bytes(raw)

        self_outer = self
        result = _room7_runtime_context(
            Ram(), variable_base=0x7E0800, variable_count=0x0320,
            object_count=1395,
        )
        self.assertEqual(result["selected_variables"]["214"], 1)
        self.assertEqual(result["selected_variables"]["215"], 2)
        self.assertEqual(
            result["global_variables"], {"base": "$7E0800", "count": 0x0320}
        )
        self.assertIn(69, result["set_bits"])
        self.assertEqual(result["objects"][4], {"object": 116, "state": 3, "owner": 1})
        self.assertEqual(result["object_classes"], {})
        self.assertEqual(result["object_classes_initialized"], 1)
        self.assertIn({"index": 214, "value": 1}, result["nonzero_global_variables"])
        self.assertEqual(result["book_inventory_object937_owner"], 1)
        self.assertEqual(result["inventory_owner1_objects"], [937])

    def test_room7_variable_layout_comes_from_rom_bound_listing_constants(self) -> None:
        listing = """; SAME_SCUMM_VARIABLE_COUNT = $0320      (Constant)
; SOME_OTHER_CONSTANT = $1234 (Constant)
; SAME_SCUMM_VARIABLES = $7e0800    (Constant)
; SCUMM_M23A_GLOBAL_OBJECT_COUNT = $0573 (Constant)
"""
        self.assertEqual(
            _parse_rom_variable_layout(listing),
            {"base": 0x7E0800, "count": 0x0320, "object_count": 0x0573},
        )
        with self.assertRaisesRegex(RuntimeError, "lacks SCUMM variable layout"):
            _parse_rom_variable_layout("; SAME_SCUMM_VARIABLES = $7e0800 (Constant)\n")

    def test_room_local_selector_parser_keeps_room_identity_distinct(self) -> None:
        generated = """; Complete executable-local directory for room 6.
ScummV5_M23A_RoomLocalNumbers_5:
    .byte $C8,$C9
ScummV5_M23A_RoomLocalIndices_5:
    .word $0000,$0001
ScummV5_M23A_RoomLocalPrograms_5:
    .byte $93,$9A
; Complete executable-local directory for room 7.
ScummV5_M23A_RoomLocalNumbers_6:
    .byte $C8,$D0
ScummV5_M23A_RoomLocalIndices_6:
    .word $0000,$0008
ScummV5_M23A_RoomLocalPrograms_6:
    .byte $91,$92
"""
        self.assertEqual(_parse_room_local_program_table(generated, 6)[0xC8], 0x93)
        self.assertEqual(_parse_room_local_program_table(generated, 7)[0xC8], 0x91)
        with self.assertRaisesRegex(RuntimeError, "missing for room 8"):
            _parse_room_local_program_table(generated, 8)

    def test_global_script_selector_is_read_from_the_generated_resolver(self) -> None:
        generated = """ScummV5_M23A_ResolveGlobalScript_Far:
    cmp #$90
    bne next
    lda #$84
    sec
    rtl
ScummV5_M23A_FetchProgramByte_Far:
"""
        self.assertEqual(_parse_global_script_selector(generated, 144), 0x84)
        with self.assertRaisesRegex(RuntimeError, "does not map global script 143"):
            _parse_global_script_selector(generated, 143)

    def test_native_button_mask_names_match_the_nexen_set_input_abi(self) -> None:
        self.assertEqual(_button_names(0x004), ["SELECT"])
        self.assertEqual(_button_names(0x100), ["X"])
        self.assertEqual(_button_names(0x800), ["Y"])

    @staticmethod
    def talk_state(*, active: int = 1, message: int = 1,
                   delay: int = 0, generation: int = 1) -> bytes:
        raw = bytearray(8)
        raw[0] = active
        raw[1] = message
        raw[4:6] = delay.to_bytes(2, "little")
        raw[6:8] = generation.to_bytes(2, "little")
        return bytes(raw)

    def test_room4_only_treats_explicit_wait_segment_as_acknowledgeable(self) -> None:
        self.assertFalse(room4_message_ready(self.talk_state(delay=1), None))
        self.assertFalse(room4_message_ready(self.talk_state(generation=2), 1))
        self.assertTrue(room4_message_ready(
            self.talk_state(message=0xFF, generation=2), 1
        ))
        self.assertFalse(room4_message_ready(
            self.talk_state(message=0xFF, generation=2), 2
        ))
        self.assertFalse(room4_message_ready(self.talk_state(active=0), None))
        self.assertFalse(room4_message_ready(self.talk_state(message=0), None))

    def test_cursor_tolerance_finishes_the_other_axis_without_oscillation(self) -> None:
        self.assertEqual(world_point_direction_mask(227, 134, 226, 124, tolerance=1), 0x010)
        self.assertEqual(world_point_direction_mask(223, 124, 226, 130, tolerance=1), 0x080)
        self.assertIsNone(world_point_direction_mask(227, 125, 226, 124, tolerance=1))

    def test_cursor_diagonal_is_explicit_and_uses_both_native_direction_bits(self) -> None:
        self.assertEqual(world_point_direction_mask(124, 30, 224, 124), 0x080)
        self.assertEqual(
            world_point_direction_mask(124, 30, 224, 124, allow_diagonal=True),
            0x0A0,
        )
        self.assertEqual(
            world_point_direction_mask(124, 130, 120, 124, allow_diagonal=True),
            0x050,
        )

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
        self.assertEqual(result["input_schedule"], {
            "press_frames": 4,
            "release_neutral_frames": 1,
            "controller_level_changes_advance_frames": False,
            "equivalent_attempts_per_step": 1,
        })
        masks = [0x040] * 14 + [0x010] * 3 + [0x001, 0x001]
        self.assertEqual(
            [buttons for _frame, buttons, hold, _frames in session.controller_events
             if hold and buttons], masks,
        )
        self.assertEqual(len(session.advances), len(masks) * 2)
        for index, (mask, step) in enumerate(zip(masks, result["steps"], strict=True)):
            hold_frame, held, hold, hold_frames = session.controller_events[index * 2]
            release_frame, neutral, release_hold, release_frames = (
                session.controller_events[index * 2 + 1]
            )
            press_start, press_end, press_count, press_mask = session.advances[index * 2]
            neutral_start, neutral_end, neutral_count, neutral_mask = (
                session.advances[index * 2 + 1]
            )
            self.assertEqual((hold_frame, held, hold, hold_frames),
                             (step["start_frame"], mask, True, 0))
            self.assertEqual((press_start, press_end, press_count, press_mask),
                             (step["start_frame"], step["start_frame"] + 4, 4, mask))
            self.assertEqual((release_frame, neutral, release_hold, release_frames),
                             (press_end, 0, True, 0))
            self.assertEqual((neutral_start, neutral_end, neutral_count, neutral_mask),
                             (press_end, press_end + 1, 1, 0))
            self.assertEqual(step["attempt"], 1)
            self.assertEqual(step["press_frames_advanced"], 4)
            self.assertEqual(step["release_frames_advanced"], 1)
            self.assertTrue(step["release_sampled"])
            self.assertEqual(
                step["input_state_after_release_sample"]["input_held"] &
                step["input_state_at_press_end"]["input_held"],
                0,
            )
        self.assertEqual(session.dangerous_set_input_calls, [])
        self.assertEqual((result["final"]["x"], result["final"]["y"]), (89, 132))
        self.assertEqual(result["final"]["verb"], 3)
        self.assertEqual(result["final"]["object"], 61)
        self.assertEqual(result["final"]["submissions"], 23)
        self.assertEqual(result["final"]["error"], 0)
        self.assertEqual(session.controller_events[-1][1:], (0, True, 0))

    def test_room4_wall_clock_input_model_overshoots_but_driver_avoids_it(self) -> None:
        unsafe = FakeRoom4Session()
        unsafe.set_input(buttons=0x040, frames=4, port=0)
        self.assertEqual(unsafe.frame, 108)
        self.assertEqual(unsafe.values[0x7E5FE1], 113)

        safe = FakeRoom4Session()
        result = replay_room4_open_trapdoor_prefix(safe)
        self.assertEqual(safe.dangerous_set_input_calls, [])
        self.assertEqual((result["final"]["x"], result["final"]["y"]), (89, 132))

    def test_room5_rope_step_is_exact_bounded_and_submits_once(self) -> None:
        session = FakeRoom5Session()
        result = replay_room5_rope_to_room6(session)
        self.assertEqual(result["precondition"]["room"], 5)
        self.assertEqual(result["precondition"]["actor1_room"], 5)
        self.assertFalse(result["precondition"]["bit69"])
        self.assertEqual(result["target"], {
            "world": [225, 124],
            "preselection_hit_object": 0,
            "selected_hit_object": 77,
        })
        self.assertEqual(len(result["movement_edges"]), 45)
        self.assertEqual(
            [step["mask"] for step in result["movement_edges"]],
            [0x080] * 40 + [0x010] * 5,
        )
        self.assertEqual(result["selection"]["after"]["verb"], 8)
        self.assertEqual(result["selected_verb_cycle"]["after"]["verb"], 9)
        self.assertEqual(result["submission_count_before"], 40)
        self.assertEqual(result["submission_count_after"], 41)
        self.assertEqual(result["submission"]["after"]["mode"], 2)
        self.assertEqual(result["submission"]["attempts"], 1)
        self.assertEqual(session.dangerous_set_input_calls, [])
        self.assertEqual(session.held_buttons, 0)
        self.assertEqual(session.values[0x7E2303], 0)
        self.assertTrue(all(
            count == 1 and end - start == 1
            for start, end, count, _mask in session.advances
        ))

    def test_room6_books_accepts_streamed_entry_cursor_parity(self) -> None:
        session = FakeRoom6Session(cursor=(228, 124))
        result = replay_room6_books_interaction(session)
        self.assertEqual(result["precondition"]["room"], 6)
        self.assertEqual(result["target"]["requested_world"], [4, 81])
        self.assertEqual(result["target"]["world"], [4, 80])
        self.assertEqual(result["target"]["selected_hit_object"], 91)
        self.assertEqual(result["submission_count_after"], 71)
        self.assertEqual(result["submission"]["attempts"], 1)

    def test_room5_rope_step_rejects_non_authentic_branch_before_input(self) -> None:
        session = FakeRoom5Session()
        session.values[0x7E2BA8] = 0x20
        with self.assertRaisesRegex(RuntimeError, "precondition mismatch"):
            replay_room5_rope_to_room6(session)
        self.assertEqual(session.controller_events, [])

    def test_room6_books_step_replays_the_source_selected_verb_once(self) -> None:
        session = FakeRoom6Session()
        result = replay_room6_books_interaction(session)
        self.assertEqual(result["precondition"]["room"], 6)
        self.assertEqual(result["precondition"]["actor1_room"], 6)
        self.assertFalse(result["precondition"]["bit69"])
        self.assertEqual(result["target"]["world"], [4, 81])
        self.assertEqual(result["target"]["selected_hit_object"], 91)
        self.assertEqual(len(result["movement_edges"]), 140)
        self.assertEqual(
            [step["mask"] for step in result["movement_edges"]],
            [0x040] * 111 + [0x010] * 29,
        )
        self.assertEqual(result["selection"]["after"]["verb"], 9)
        self.assertEqual(result["selected_verb_cycle"]["after"]["verb"], 10)
        self.assertEqual(result["submission_count_before"], 70)
        self.assertEqual(result["submission_count_after"], 71)
        self.assertEqual(result["submission"]["after"]["mode"], 2)
        self.assertEqual(result["submission"]["attempts"], 1)
        self.assertEqual(session.dangerous_set_input_calls, [])
        self.assertEqual(session.held_buttons, 0)
        self.assertEqual(session.values[0x7E2303], 0)
        self.assertTrue(all(
            count == 1 and end - start == 1
            for start, end, count, _mask in session.advances
        ))

    def test_room7_book_step_selects_authored_verb11_and_submits_once(self) -> None:
        session = FakeRoom7Session()
        result = replay_room7_lost_dialogue_interaction(
            session,
            variable_base=session.VARIABLE_BASE,
            variable_count=session.VARIABLE_COUNT,
        )
        self.assertEqual(result["precondition"]["room"], 7)
        self.assertEqual(result["precondition"]["actor1_room"], 7)
        self.assertEqual((result["target"]["world"]), [188, 125])
        self.assertEqual(result["target"]["source_order_winner"], 133)
        self.assertEqual(result["target"]["selected_hit_object"], 133)
        self.assertEqual(len(result["movement_edges"]), 15)
        self.assertEqual(
            [step["mask"] for step in result["movement_edges"]],
            [0x080] * 13 + [0x010] * 2,
        )
        self.assertEqual(result["selection"]["after"]["verb"], 9)
        self.assertEqual(result["selected_verb_cycle"]["after"]["verb"], 11)
        self.assertEqual(result["submission_count_before"], 90)
        self.assertEqual(result["submission_count_after"], 91)
        self.assertEqual(result["submission"]["after"]["mode"], 2)
        self.assertEqual(result["submission"]["attempts"], 1)

    def test_room7_book_accepts_streamed_entry_cursor_parity(self) -> None:
        session = FakeRoom7Session(cursor=(4, 80))
        result = replay_room7_lost_dialogue_interaction(
            session,
            variable_base=session.VARIABLE_BASE,
            variable_count=session.VARIABLE_COUNT,
        )
        self.assertEqual(result["target"]["requested_world"], [188, 125])
        self.assertEqual(result["target"]["world"], [188, 124])
        self.assertEqual(result["target"]["selected_hit_object"], 133)
        self.assertEqual(result["submission_count_after"], 91)
        self.assertEqual(result["submission"]["attempts"], 1)
        self.assertEqual(session.dangerous_set_input_calls, [])
        self.assertEqual(session.held_buttons, 0)
        self.assertEqual(session.values[0x7E2303], 0)
        self.assertTrue(all(
            count == 1 and end - start == 1
            for start, end, count, _mask in session.advances
        ))

    def test_room7_distinct_cat_verbs_follow_authored_progression_gate(self) -> None:
        session = FakeRoom7CatSession()
        first = replay_room7_cat_figure_use(
            session, object_id=118,
            variable_base=session.VARIABLE_BASE,
            variable_count=session.VARIABLE_COUNT,
        )
        self.assertEqual(first["target"]["world"], [112, 123])
        self.assertEqual(first["selection"]["after"]["object"], 118)
        self.assertEqual(first["selected_verb_cycle"]["after"]["verb"], 10)
        self.assertEqual(first["submission_count_before"], 128)
        self.assertEqual(first["submission_count_after"], 129)
        self.assertEqual(len(first["movement_edges"]), 39)
        self.assertEqual(
            [step["mask"] for step in first["movement_edges"]],
            [0x040] * 38 + [0x010],
        )
        self.assertEqual(first["submission"]["attempts"], 1)
        self.assertIn("set V217", first["expected_authored_effect"])
        session.complete_cat_action(118)

        second = replay_room7_cat_figure_use(
            session, object_id=119,
            variable_base=session.VARIABLE_BASE,
            variable_count=session.VARIABLE_COUNT,
        )
        self.assertEqual(second["precondition"]["V214"], 1)
        self.assertEqual(second["precondition"]["variables215_218"],
                         (0, 0, 1, 0))
        self.assertEqual(second["target"]["world"], [128, 123])
        self.assertEqual(second["selection"]["after"]["object"], 119)
        self.assertEqual(second["selected_verb_cycle"]["after"]["verb"], 10)
        self.assertEqual(second["submission_count_before"], 129)
        self.assertEqual(second["submission_count_after"], 130)
        self.assertEqual(len(second["movement_edges"]), 8)
        self.assertEqual([step["mask"] for step in second["movement_edges"]],
                         [0x080] * 8)
        self.assertIn("start LSCR207", second["expected_authored_effect"])
        self.assertEqual(second["submission"]["attempts"], 1)
        session.complete_cat_action(119)
        self.assertEqual(session.values[0x7F3716], 3)
        self.assertEqual(session.values[0x7E2303], 0)
        self.assertEqual(session.held_buttons, 0)
        self.assertEqual(session.dangerous_set_input_calls, [])

    def test_room7_cat_accepts_streamed_entry_cursor_parity(self) -> None:
        session = FakeRoom7CatSession(cursor=(188, 124))
        result = replay_room7_cat_figure_use(
            session, object_id=118,
            variable_base=session.VARIABLE_BASE,
            variable_count=session.VARIABLE_COUNT,
        )
        self.assertEqual(result["target"]["requested_world"], [112, 123])
        self.assertEqual(result["target"]["world"], [112, 122])
        self.assertEqual(result["selection"]["after"]["object"], 118)
        self.assertEqual(result["selected_verb_cycle"]["after"]["verb"], 10)
        self.assertEqual(result["submission"]["attempts"], 1)
        self.assertEqual(result["submission_count_after"], 129)
        self.assertEqual(session.dangerous_set_input_calls, [])
        self.assertEqual(session.held_buttons, 0)

    def test_room7_cat_replay_rejects_unjustified_order_without_input(self) -> None:
        session = FakeRoom7CatSession()
        with self.assertRaisesRegex(RuntimeError, "precondition mismatch"):
            replay_room7_cat_figure_use(
                session, object_id=119,
                variable_base=session.VARIABLE_BASE,
                variable_count=session.VARIABLE_COUNT,
            )
        self.assertEqual(session.controller_events, [])

    def test_cold_room4_replay_reaches_authentic_hitbox_from_cursor_origin(self) -> None:
        session = FakeRoom4Session(cursor=(0, 0))
        result = replay_room4_open_trapdoor_from_origin(session)
        self.assertEqual(result["target"]["world"], [90, 132])
        self.assertEqual(result["target"]["hit_object"], 61)
        self.assertEqual(result["movement_pulses"], 111)
        self.assertEqual((result["final"]["x"], result["final"]["y"]), (90, 132))
        self.assertEqual(result["final"]["hit_object"], 61)
        self.assertEqual(result["final"]["object"], 61)
        self.assertEqual(result["final"]["verb"], 3)
        self.assertEqual(result["final"]["submissions"], 23)
        self.assertEqual(session.dangerous_set_input_calls, [])
        self.assertEqual(session.held_buttons, 0)

    def test_room4_authored_override_uses_one_normal_x_edge_and_unwinds(self) -> None:
        session = FakeRoom4Session(cursor=(0, 0))
        session.activate_room4_override()
        result = skip_room4_authored_override(session)
        self.assertEqual(result["button"], "X")
        self.assertEqual(result["step"]["mask"], 0x100)
        self.assertEqual(result["step"]["press_frames_to_sample"], 1)
        self.assertTrue(result["step"]["release_sampled"])
        self.assertEqual(result["cleared_override_record"], {
            "stack_index": 1, "override_pc": 0,
            "override_slot": 0, "owner_slot": 3, "owner_slot_depth": 0,
        })
        self.assertEqual(session.controller_events, [
            (100, 0x100, True, 0),
            (101, 0, True, 0),
        ])
        self.assertEqual(session.advances, [
            (100, 101, 1, 0x100),
            (101, 102, 1, 0),
        ])
        self.assertEqual(result["after"]["c19_stack_pointer"], 1)
        completion = finish_room4_authored_cutscene(session)
        self.assertEqual(completion["idle_frames"], 4)
        self.assertEqual(completion["final"]["c19_stack_pointer"], 0)
        self.assertEqual(session.held_buttons, 0)

    def test_c19_record_snapshot_uses_explicit_stack_index(self) -> None:
        session = FakeRoom4Session()
        session.values.update({
            0x7FD356: 0x1234,
            0x7FD35F: 7,
            0x7FD363 + 7: 2,
            0x7FD35A: 0x5678,
            0x7FD361: 9,
            0x7FD363 + 9: 1,
        })
        self.assertEqual(room4_c19_record_snapshot(session, 1), {
            "stack_index": 1,
            "override_pc": 0x1234,
            "override_slot": 7,
            "owner_slot_depth": 2,
        })
        self.assertEqual(room4_c19_record_snapshot(session, 3), {
            "stack_index": 3,
            "override_pc": 0x5678,
            "override_slot": 9,
            "owner_slot_depth": 1,
        })
        with self.assertRaisesRegex(ValueError, "outside the native table"):
            room4_c19_record_snapshot(session, 5)

    def test_room4_override_waits_for_delayed_native_input_sample_once(self) -> None:
        session = FakeRoom4Session(
            cursor=(0, 0), input_poll_delay_frames=3,
        )
        session.activate_room4_override()
        result = skip_room4_authored_override(session)
        self.assertEqual(result["step"]["press_frames_to_sample"], 4)
        self.assertEqual(result["step"]["after"]["edge_sequence"], 1)
        self.assertEqual(result["step"]["action_state_at_sample_frame_end"][
            "c19_override_pc"
        ], 0)
        self.assertEqual(
            [buttons for _frame, buttons, hold, _frames in session.controller_events
             if hold and buttons],
            [0x100],
        )

    def test_room4_override_accepts_caller_verified_resident_selector(self) -> None:
        session = FakeRoom4Session(cursor=(0, 0))
        session.activate_room4_override()
        session.values[0x7E23B5] = 0xE0
        result = skip_room4_authored_override(
            session, expected_override_program=0xE0,
        )
        self.assertEqual(result["before"]["c19_override_program"], 0xE0)
        self.assertEqual(result["after"]["c19_override_pc"], 0)

    def test_room4_override_accepts_caller_verified_live_owner_slot(self) -> None:
        session = FakeRoom4Session(cursor=(0, 0))
        session.activate_room4_override(slot=4)
        result = skip_room4_authored_override(
            session,
            expected_override_program=0xF9,
            expected_override_slot=4,
        )
        self.assertEqual(result["before"]["c19_override_slot"], 4)
        self.assertEqual(result["after"]["c19_override_pc"], 0)

    def test_room4_second_authored_override_can_have_zero_cutscene_depth(self) -> None:
        session = FakeRoom4Session(cursor=(0, 0))
        session.activate_room4_override(slot=1, pc=126, owner_depth=0)
        result = skip_room4_authored_override(
            session,
            expected_override_program=0xF9,
            expected_override_slot=1,
            expected_override_pc=126,
        )
        self.assertEqual(result["before"]["c19_override_pc"], 126)
        self.assertEqual(result["after"]["c19_stack_pointer"], 0)
        self.assertEqual(result["cleared_override_record"]["owner_slot_depth"], 0)
        self.assertEqual(
            [buttons for _frame, buttons, hold, _frames in session.controller_events
             if hold and buttons],
            [0x100],
        )

    def test_room4_override_replay_rejects_unexpected_owner_without_input(self) -> None:
        session = FakeRoom4Session(cursor=(0, 0))
        session.activate_room4_override()
        session.values[0x7E239C] = 201
        with self.assertRaisesRegex(RuntimeError, "precondition mismatch"):
            skip_room4_authored_override(session)
        self.assertEqual(session.controller_events, [])

    def test_room4_replay_releases_input_when_frame_advance_raises(self) -> None:
        session = FakeRoom4Session()
        session.fail_next_advance = True
        with self.assertRaisesRegex(RuntimeError, "simulated frame runner failure"):
            replay_room4_open_trapdoor_prefix(session)
        self.assertEqual(
            [(buttons, hold) for _frame, buttons, hold, _frames
             in session.controller_events],
            [(0x040, True), (0, True)],
        )
        self.assertEqual(session.held_buttons, 0)

    def test_room4_authored_use_cycles_source_verbs_then_submits_once(self) -> None:
        session = FakeRoom4Session()
        session.values.update({
            0x7FF2BF: 4,
            0x7E2221: 2,
            0x7E2303: 0,
            0x7E7A20: 0,
            0x7E5FE0: 1,
            0x7E5FE5: 3,
            0x7E5FE6: 61,
            0x7E5FE9: 79,
        })
        result = replay_room4_trapdoor_use(
            session, pulse=lambda current, mask, predicate: room4_synchronous_input_edge(
                current, mask, predicate
            )
        )
        self.assertEqual([step["after"]["verb"] for step in result["verb_cycle_edges"]], [4, 9, 10])
        self.assertEqual([step["mask"] for step in result["verb_cycle_edges"]], [0x800] * 3)
        self.assertEqual(result["submission_count_before"], 79)
        self.assertEqual(result["submission_count_after"], 80)
        self.assertEqual(result["submission"]["after"]["mode"], 2)
        self.assertEqual(session.held_buttons, 0)
        self.assertEqual(session.dangerous_set_input_calls, [])

    def test_room4_replay_driver_rejects_wrong_start_state_without_input(self) -> None:
        session = FakeRoom4Session(ready=0)
        with self.assertRaisesRegex(RuntimeError, "precondition mismatch"):
            replay_room4_open_trapdoor_prefix(session)
        self.assertEqual(session.inputs, [])

    def test_room4_edge_waits_for_exact_frame_sample_and_neutral_release(self) -> None:
        session = FakeRoom4Session()
        result = room4_synchronous_input_edge(
            session,
            0x040,
            lambda before, after: after["x"] == before["x"] - 2,
        )
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["press_frames_to_sample"], 1)
        self.assertEqual(result["action_state_at_sample_frame_end"]["x"], 115)
        self.assertTrue(result["release_sampled"])
        self.assertEqual(result["after"]["input_held"], 0)
        self.assertEqual(result["after"]["input_released"] & 0x0200, 0x0200)
        self.assertEqual(result["after"]["edge_sequence"], 1)
        self.assertEqual(len(result["press_frames"]), 1)
        self.assertEqual(len(result["release_frames"]), 1)
        self.assertEqual(result["press_frames"][0]["advance"]["frames_advanced"], 1)
        self.assertEqual(result["release_frames"][0]["advance"]["frames_advanced"], 1)

    def test_room4_edge_waits_for_dispatch_without_sending_another_press(self) -> None:
        session = FakeRoom4Session()
        session.pending_edge_delay = 1
        result = room4_synchronous_input_edge(
            session,
            0x040,
            lambda before, after: after["x"] == before["x"] - 2,
        )
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["after"]["edge_sequence"], 1)
        self.assertEqual(len(result["press_frames"]), 2)
        self.assertTrue(result["press_frames"][1]["same_held_edge"])
        self.assertEqual(
            [buttons for _frame, buttons, hold, _frames in session.controller_events
             if hold and buttons],
            [0x040],
        )

    def test_room4_edge_does_not_repeat_after_semantic_mismatch(self) -> None:
        session = FakeRoom4Session()
        with self.assertRaisesRegex(RuntimeError, "no retry was sent"):
            room4_synchronous_input_edge(
                session,
                0x040,
                lambda _before, after: after["x"] == 100,
            )
        self.assertEqual(session.values[0x7E2208], 1)
        self.assertEqual(session.held_buttons, 0)
        self.assertEqual(
            [buttons for _frame, buttons, hold, _frames in session.controller_events
             if hold and buttons],
            [0x040],
        )

    def test_talk_owned_edge_is_not_reused_for_retained_selection_model(self) -> None:
        session = FakeRoom4Session()
        session.values.update({
            0x7E7A20: 1,
            0x7E7A21: 1,
            0x7E5FE0: 1,
            0x7E5FE5: 3,
            0x7E5FE6: 61,
            0x7E5FE9: 77,
            0x7E2208: 12,
        })
        result = room4_synchronous_input_edge(
            session,
            0x001,
            lambda _before, after: after["submissions"] == 77,
        )
        edge = result["press_frames"][-1]["state_at_frame_end"]
        self.assertEqual(edge["talk_owned_valid"], 1)
        self.assertEqual(edge["talk_owned_sequence"], edge["edge_sequence"])
        self.assertEqual(result["action_state_at_sample_frame_end"]["submissions"], 77)
        self.assertEqual(result["after"]["submissions"], 77)
        self.assertEqual(result["after"]["edge_sequence"], 13)


if __name__ == "__main__":
    unittest.main()
