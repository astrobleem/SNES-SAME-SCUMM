from dataclasses import replace
from pathlib import Path
import unittest
from examples.resources.scumm_v5.actor_scene_fixture import source_files, STAGES
from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.policy import parse_game_policy
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices

class ActorSceneFixture(unittest.TestCase):
    def test_two_original_costumes_and_source_script_stages(self):
        root=Path(__file__).resolve().parents[1]
        p=load_profile(root/'examples/profiles/scumm_v5_game_analysis_fixture.json',verify_resources=False)
        p=replace(p,options={**p.options,'headless_presentation':True})
        files=source_files()
        provider=LucasartsScummV5ResourceProvider(MemoryResourceProvider({
            'game.index':files['ATLANTIS/ATLANTIS.000'],'game.data':files['ATLANTIS/ATLANTIS.001']}),parse_game_policy(p))
        self.assertNotEqual(provider.read('costume.1'),provider.read('costume.2'))
        h=EngineHost(p,default_registry(),services=HostServices.create(p,resources=provider));h.boot()
        for n,actors in enumerate(STAGES,1):
            for _ in range(20):
                h.tick();slots=[s for s in h.engine.state.scripts if s.number==1]
                if slots and slots[0].locals[1]==n:break
            self.assertEqual(slots[0].locals[1],n)
            for actor,expected in enumerate(actors,1):
                a=h.engine.state.actors[actor]
                self.assertEqual((a.position,*a.scale,a.facing,a.costume_frame),
                                 ((expected[0],expected[1]),*expected[2:]))
                self.assertEqual(a.costume,actor)
            slots[0].locals[0]=n
