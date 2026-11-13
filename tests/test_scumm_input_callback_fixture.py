"""Source-bound host oracle for the public native input callback fixture."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from examples.resources.scumm_v5.input_callback_fixture import source_files, write_archive
from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]


class InputCallbackFixtureTests(unittest.TestCase):
    def host(self, **fixture_options):
        p = load_profile(ROOT / 'examples/profiles/scumm_v5_game_analysis_fixture.json', verify_resources=False)
        p = replace(p, options={**p.options, 'headless_presentation': True})
        files = source_files(**fixture_options)
        resources = MemoryResourceProvider({
            'game.index': files['ATLANTIS/ATLANTIS.000'],
            'game.data': files['ATLANTIS/ATLANTIS.001'],
        })
        provider = LucasartsScummV5ResourceProvider(resources, parse_game_policy(p))
        services = HostServices.create(p, resources=provider)
        h = EngineHost(p, default_registry(), services=services)
        h.boot()
        return h

    def test_exact_native_sequence_against_source_host(self):
        h = self.host(); e = h.engine
        h.tick()
        self.assertEqual((e.state.current_room, e.state.variables[32]), (1, 204))
        e.queue_input_event(2, 0, 1); h.tick()
        self.assertEqual(e.state.variables[100:104], [2, 0, 1, 1])
        self.assertEqual(e.state.variables[32], 2)
        e.queue_input_event(2, 0, 2); h.tick(); h.tick()
        self.assertEqual(e.state.variables[100:111], [2, 0, 1, 1, 2, 0, 2, 1, 1, 42, 1])
        self.assertEqual(e.state.variables[111:114], [77, 1, 1])
        self.assertEqual(e.state.sentences, [])

    def test_nested_object_and_hover_share_carrier_without_losing_action(self):
        h=self.host(nested_object_wait=True);e=h.engine;h.tick()
        e.queue_input_event(2,0,1);h.tick()
        e.queue_input_event(2,0,2)
        for _ in range(8):h.tick()
        self.assertEqual(e.state.variables[114:117],[42,42,1])
        self.assertEqual(e.state.variables[118],1)
        self.assertEqual(e.state.variables[117],1)
        self.assertEqual(e.state.variables[119:123],[2,0x1234,2,0])
        self.assertEqual(e.state.cutscenes,[])
        self.assertEqual(e.state.variables[123],1) # absent optional verb returned

    def test_archive_is_reproducible_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.zip', Path(d) / 'b.zip'
            write_archive(a); write_archive(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with self.assertRaises(FileExistsError):
                write_archive(a)


if __name__ == '__main__':
    unittest.main()
