import unittest

from same.errors import EngineExecutionError
from same.engines.scumm_v5.embedded_audio import (
    ScummV5EmbeddedAudioAdapter, _LogicalCompiledOwner,
)
from test_scumm_v5_audio_save import make_host


class SoundStatusQueryTests(unittest.TestCase):
    def test_deferred_query_tracks_live_queue_not_a_stale_owner(self):
        h = make_host()
        adapter = ScummV5EmbeddedAudioAdapter(h.context, lambda n: f'sound.{n}')
        adapter.logical_compiled[7] = _LogicalCompiledOwner('active', 0)
        self.assertEqual(adapter.sound_status(7), 1)
        self.assertTrue(adapter.install_trigger(7, 3))
        self.assertTrue(adapter.enqueue_deferred([8, 9]))
        self.assertEqual(adapter.sound_status(9), 2)
        adapter.clear_deferred()
        self.assertEqual(adapter.sound_status(9), 0)
        self.assertTrue(adapter.install_trigger(7, 3))
        self.assertTrue(adapter.enqueue_deferred([8, 9]))
        adapter._compiled_generation += 1
        self.assertEqual(adapter.sound_status(9), 0)

    def test_query_uses_logical_music_sfx_and_absent_ownership(self):
        h = make_host()
        h.tick()  # The original fixture starts music 7, SFX 9 and speech 5.
        e = h.engine
        for sound, expected in ((7, 1), (9, 1), (5, 0), (64, 0), (0, 0)):
            with self.subTest(sound=sound):
                before = len(h.services.audio.command_history)
                e.state.sound_queue = [[13, sound]]
                e._flush_sound_commands(h.context)
                self.assertEqual(e.state.sound_result, expected)
                self.assertEqual(e.state.variables[56], expected)
                self.assertEqual(e.state.sound_history[-1], [13, sound])
                commands = h.services.audio.command_history[before:]
                self.assertFalse(any(c['command'].endswith('_play') for c in commands))
        e._audio.stop_sfx(9)
        e.state.sound_queue = [[13, 9]]
        e._flush_sound_commands(h.context)
        self.assertEqual(e.state.variables[56], 0)

    def test_queue_order_and_result_publication(self):
        h = make_host()
        h.tick()
        e = h.engine
        e.state.sound_queue = [[13, 7], [9, 7], [13, 7]]
        e._flush_sound_commands(h.context)
        self.assertEqual(e.state.variables[56], 0)
        self.assertEqual(e.state.sound_history[-3:], [[13, 7], [9, 7], [13, 7]])

    def test_bad_shape_and_unrepresented_player_order_fail_explicitly(self):
        h = make_host()
        for command in ([13], [13, 7, 0], [13, -1], [13, 65535], [13, 65536]):
            with self.subTest(command=command), self.assertRaises(EngineExecutionError):
                h.engine._dispatch_sound_command(h.context, command)


if __name__ == '__main__':
    unittest.main()
