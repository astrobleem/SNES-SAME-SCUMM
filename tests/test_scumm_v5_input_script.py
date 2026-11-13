"""Original copyright-free scripts for the variable-32 input ABI."""
from __future__ import annotations

import unittest

import test_scumm_v5_engine as fixtures
from same.engines.scumm_v5.input import ClickArea
from same.errors import EngineExecutionError, ResourceError, SaveFormatError
from same.services import InputEvent, InputEventType


def copy_local(result: int, local: int) -> bytes:
    return bytes((0x9A, result, 0, local, 0x40))


class InputScriptTests(unittest.TestCase):
    def host(self, callback: bytes | None = None):
        return fixtures.ScummV5EngineTests()._host(
            b'\x80\x18\xfc\xff', scripts={2: callback or (
                copy_local(100, 0) + copy_local(101, 1) + copy_local(102, 2)
                + b'\x46\x67\x00\x00')},
        )

    def test_all_click_areas_and_modes_execute_original_arguments_once(self):
        for area in ClickArea:
            for mode in (0, 1, 2):
                with self.subTest(area=area, mode=mode):
                    h = self.host(); e = h.engine
                    e.state.variables[32] = 2
                    self.assertTrue(e.queue_input_event(area, 47, mode))
                    h.tick()
                    self.assertEqual(e.state.variables[100:104], [area, 47, mode, 1])
                    h.tick()
                    self.assertEqual(e.state.variables[103], 1)
                    self.assertEqual(e.state.sentences, [])
                    slot = next(s for s in e.state.scripts if s.resource_key == 'script.2')
                    self.assertEqual(slot.locals[3:], [0] * 29)
                    self.assertFalse(slot.recursive or slot.freeze_resistant)

    def test_current_room_local_callback_and_yield(self):
        h = self.host(); e = h.engine
        e._room_scripts[204] = copy_local(100, 0) + b'\x80' + copy_local(101, 2) + b'\x00'
        e.state.variables[32] = 204
        e.queue_input_event(ClickArea.SCENE, 0, 2)
        h.tick()
        slot = next(s for s in e.state.scripts if s.number == 204)
        self.assertEqual((slot.script_kind, slot.room, slot.yielded), ('LSCR', 0, True))
        h.tick()
        self.assertEqual(e.state.variables[100:102], [2, 2])

    def test_absent_disabled_and_invalid_input(self):
        h = self.host(); e = h.engine
        self.assertFalse(e.queue_input_event(2, 0, 1))
        e.state.variables[32] = 2
        e.state.user_input_state = 0
        self.assertFalse(e.queue_input_event(2, 0, 1))
        for args in ((0, 0, 1), (6, 0, 1), (2, -1, 1), (2, 0, 3)):
            with self.assertRaises(EngineExecutionError):
                e.queue_input_event(*args)

    def test_mailbox_does_not_overwrite_an_accepted_event(self):
        h = self.host(); e = h.engine; e.state.variables[32] = 2
        e.queue_input_event(2, 0, 1)
        ticket = e._input_request
        with self.assertRaises(EngineExecutionError):
            e.queue_input_event(4, 65, 1)
        self.assertIs(e._input_request, ticket)
        h.tick()
        self.assertEqual(e.state.variables[100:103], [2, 0, 1])

    def test_resource_failure_preserves_request_and_never_queues_sentence(self):
        h = self.host(); e = h.engine; e.state.variables[32] = 204
        e.queue_input_event(2, 0, 1)
        ticket = e._input_request
        with self.assertRaises(ResourceError):
            e._check_and_run_input_script(e._context)
        self.assertIs(e._input_request, ticket)
        self.assertEqual(e.state.sentences, [])
        e._room_scripts[204] = copy_local(100, 0) + b'\x00'
        h.tick()
        self.assertEqual(e.state.variables[100], 2)
        self.assertIsNone(e._input_request)

    def test_room_revisit_invalidates_unconsumed_request(self):
        h = self.host(); e = h.engine; e.state.variables[32] = 2
        e.queue_input_event(2, 0, 1)
        e._load_room(e._context, 0, required=True)
        h.tick()
        self.assertEqual(e.state.variables[103], 0)
        self.assertIsNone(e._input_request)

    def test_callback_can_enqueue_sentence_without_duplicate_submission(self):
        # doSentence(8, 42, 0); stop. Only original callback creates C20.
        h = self.host(b'\x19\x08\x2a\x00\x00\x00\x00'); e = h.engine
        e._room_scripts[204] = copy_local(100, 0) + copy_local(101, 1) + b'\x00'
        e.state.variables[32:34] = [2, 204]
        e.queue_input_event(2, 0, 1)
        h.tick(); h.tick()
        self.assertEqual(e.state.variables[100:102], [8, 42])
        self.assertEqual(e.state.sentences, [])

    def test_ordinary_c20_without_callback_is_unchanged(self):
        h = self.host(); e = h.engine; e.state.variables[33] = 2
        e.queue_sentence(8, 42)
        h.tick(); h.tick()
        self.assertEqual(e.state.variables[100:104], [8, 42, 0, 1])

    def test_nested_start_uses_normal_vm(self):
        h = self.host(b'\x0a\xcc\x00\x09\x00\xff\x00'); e = h.engine
        e._room_scripts[204] = copy_local(104, 0) + b'\x00'
        e.state.variables[32] = 2
        e.queue_input_event(2, 0, 1)
        h.tick()
        self.assertEqual(e.state.variables[104], 9)

    def test_held_pointer_and_unrelated_motion_do_not_repeat(self):
        h = self.host(); e = h.engine; e.state.variables[32] = 2
        for frame in range(3):
            e.handle_event(e._context, InputEvent(
                type=InputEventType.POINTER_BUTTON, frame=frame,
                action='pointer_primary', pressed=True,
            ))
            e.handle_event(e._context, InputEvent(
                type=InputEventType.POINTER_MOVE, frame=frame, x=10, y=10,
            ))
            h.tick()
        self.assertEqual(e.state.variables[103], 1)

    def test_keyboard_uses_key_area_and_logical_pointer_is_published(self):
        h = self.host(); e = h.engine; e.state.variables[32] = 2
        e.state.virtual_screen_xstart = 80
        e.state.room_ops.screen_top = 10
        e.handle_event(e._context, InputEvent(
            type=InputEventType.POINTER_MOVE, frame=0, x=20, y=30,
        ))
        self.assertEqual([e.state.variables[i] for i in (20, 21, 44, 45)], [100, 20, 20, 30])
        e.handle_event(e._context, InputEvent(type=InputEventType.TEXT, frame=0, text='a'))
        h.tick()
        self.assertEqual(e.state.variables[100:103], [4, 97, 1])

    def test_pending_input_cannot_silently_disappear_in_a_portable_save(self):
        h = self.host(); e = h.engine; e.state.variables[32] = 2
        e.queue_input_event(2, 0, 1)
        with self.assertRaisesRegex(SaveFormatError, 'pending raw input'):
            e.save_state(e._context)
        h.tick()
        self.assertTrue(e.save_state(e._context))


if __name__ == '__main__':
    unittest.main()
