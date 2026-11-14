"""Source-bound host oracle for the public native input callback fixture."""
from dataclasses import replace
from pathlib import Path
import tempfile
import hashlib
import json
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
        if fixture_options.get('lifecycle_chain'):
            from same.engines.scumm_v5.room_compiler import compile_room_payload
            sha=lambda b:hashlib.sha256(b).hexdigest()
            identities=dict(profile_sha256=sha(p.path.read_bytes()),
                            game_identity_sha256=sha(f'{p.engine_id}\0{p.game_id}\0{p.variant}'.encode()),
                            archive_sha256=sha(b'original-input-fixture'),
                            index_sha256=sha(files['ATLANTIS/ATLANTIS.000']),
                            data_sha256=sha(files['ATLANTIS/ATLANTIS.001']))
            compiled=compile_room_payload(provider.read('room.1'),room_number=1,
                game_name=p.game_id,resource_key='room.1',source_member='original fixture',
                source_container_offset=0,original_room_file_offset=0,
                global_script_count=provider.global_script_count,**identities)
            backing={k:resources.read(k) for k in resources.keys()}
            backing['cooked.room.1']=compiled.cooked_record
            backing['cooked.rooms.manifest']=json.dumps(dict(
                schema='same_scumm_v5_cooked_rooms_v1',num_global_scripts=provider.global_script_count,
                profile=dict(sha256=identities['profile_sha256'],identity_sha256=identities['game_identity_sha256']),
                source={k:identities[k] for k in ('archive_sha256','index_sha256','data_sha256')})).encode()
            provider=LucasartsScummV5ResourceProvider(MemoryResourceProvider(backing),parse_game_policy(p))
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

    def test_lifecycle_multilevel_child_chain_before_publication(self):
        h=self.host(lifecycle_chain=True);e=h.engine;h.tick()
        e.queue_input_event(2,0,1);h.tick()
        e.queue_input_event(2,0,2)
        for _ in range(8):h.tick()
        self.assertEqual(e.state.variables[32],8)
        e.queue_input_event(2,0,1)
        for _ in range(8):h.tick()
        self.assertEqual(e.state.current_room,0)
        self.assertEqual(e.state.variables[124:128],[42]*4)

    def test_archive_is_reproducible_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.zip', Path(d) / 'b.zip'
            write_archive(a); write_archive(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with self.assertRaises(FileExistsError):
                write_archive(a)


if __name__ == '__main__':
    unittest.main()
