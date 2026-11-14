"""The native control is genuine decoded source with ordinary actorOps."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from examples.resources.scumm_v5.actor_scaling_fixture import source_files, costume, STAGES, CAMERA_STAGES, write_archive
from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.costume import ScummV5Costume
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.policy import parse_game_policy
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices
from tools.actor_pose_plan import compile_cel_pose

ROOT=Path(__file__).resolve().parents[1]

class ScalingFixture(unittest.TestCase):
    def test_actual_source_costume_has_multiple_cels_and_chunks(self):
        c=ScummV5Costume(costume(),key='original-test')
        for facing in (0,90,180,270):
            pose=c.decode_pose(1,facing=facing)
            self.assertEqual(len(pose.cels),2)
            plan=compile_cel_pose(pose,c.palette)
            self.assertGreater(len(plan.data),2048)
            self.assertEqual(len(plan.chunks()),2)
            self.assertEqual(plan.decoded_cels(),pose.cels)
        self.assertNotEqual(c.decode_pose(2,step=0),c.decode_pose(2,step=1))
        self.assertEqual(c.palette[1],0)

    def test_fixture_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.zip',Path(d)/'b.zip';write_archive(a);write_archive(b)
            self.assertEqual(a.read_bytes(),b.read_bytes())

    def test_host_executes_source_stages_with_authored_scales(self):
        self.exercise_host_stages('scaling', STAGES)

    def test_host_camera_only_exposure_and_reversal_preserve_actor_state(self):
        self.exercise_host_stages('camera-exposure', CAMERA_STAGES)

    def exercise_host_stages(self, scenario, stages):
        p=load_profile(ROOT/'examples/profiles/scumm_v5_game_analysis_fixture.json',verify_resources=False)
        p=replace(p,options={**p.options,'headless_presentation':True})
        files=source_files(scenario)
        raw=MemoryResourceProvider({'game.index':files['ATLANTIS/ATLANTIS.000'],'game.data':files['ATLANTIS/ATLANTIS.001']})
        provider=LucasartsScummV5ResourceProvider(raw,parse_game_policy(p))
        h=EngineHost(p,default_registry(),services=HostServices.create(p,resources=provider));h.boot()
        for n,stage in enumerate(stages,1):
            for _ in range(20):
                h.tick()
                scripts=[slot for slot in h.engine.state.scripts if slot.number==1]
                if scripts and scripts[0].locals[1]==n:break
            self.assertEqual(scripts[0].locals[1],n)
            actor=h.engine.state.actors[1]
            self.assertEqual(actor.scale,stage['scale'])
            self.assertEqual(actor.position,(stage['x'],stage['y']))
            self.assertEqual(actor.facing,stage['facing'])
            self.assertEqual(actor.costume_frame,stage['frame'])
            scripts[0].locals[0]=n
