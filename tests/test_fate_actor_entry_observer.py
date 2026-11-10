"""The graphics observer stops at room publication without inventing gameplay."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import replay_fate_room4_cold_nexen as replay


class PublishedRoom:
    def read_memory(self, kind, address, size):
        assert (address, size) == (0x7FF2BF, 4)
        return bytes((4, 1, 0, 0))

    def read_u8(self, address):
        return {0x7E2303: 0, 0x7E2221: 2, 0x7FF2C0: 1,
                0x7E5E8A: 1, 0x7E7A20: 1, 0x7E5FE0: 1}[address]

    def get_state(self):
        return {'frameCount': 123}


class ActorEntryObserverTests(unittest.TestCase):
    def test_graphics_entry_does_not_wait_for_dialogue_or_skip_cutscene(self):
        with patch.object(replay, '_snapshot', return_value={'room': 4}) as snapshot:
            state, transitions = replay._cold_wait_room4(
                PublishedRoom(), 10, require_interactive=False)
        self.assertEqual(state, {'room': 4})
        self.assertEqual(transitions[0]['room'], 4)
        snapshot.assert_called_once()

    def test_normal_replay_still_requires_interactive_checkpoint(self):
        with patch.object(replay, '_snapshot', side_effect=RuntimeError('still waiting')):
            with self.assertRaisesRegex(RuntimeError, 'still waiting'):
                replay._cold_wait_room4(PublishedRoom(), 10)

    def test_full_source_identity_is_not_the_selected_startup_personality(self):
        env = {"SAME_SCUMM_WHOLE_SOURCE_MANIFEST": "/source/manifest.json",
               "SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY": "1",
               "SAME_BUILD_SCUMM_MSU1_PROGRAMS": "1",
               "SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES": "1",
               "SAME_SCUMM_DYNAMIC_BOOT_SCRIPT": "1",
               "SAME_SCUMM_DYNAMIC_BOOT_ARGUMENT": "0"}
        self.assertTrue(replay.authentic_full_source_configuration(env))
        for change in ({"SAME_SCUMM_DIAGNOSTIC_ACTOR_PROBE": "1"},
                       {"SAME_SCUMM_DYNAMIC_BOOT_ARGUMENT": "-7873"},
                       {"SAME_SCUMM_WHOLE_SOURCE_MANIFEST": ""}):
            with self.subTest(change=change):
                self.assertFalse(replay.authentic_full_source_configuration(env | change))
