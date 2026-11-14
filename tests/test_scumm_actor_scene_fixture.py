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
    def test_cutscene_callbacks_use_normal_nested_global_arguments(self):
        root = Path(__file__).resolve().parents[1]
        profile = load_profile(root/'examples/profiles/scumm_v5_game_analysis_fixture.json', verify_resources=False)
        profile = replace(profile, options={**profile.options, 'headless_presentation': True})
        files = source_files(cutscene_callback_probe=True)
        provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider({
            'game.index': files['ATLANTIS/ATLANTIS.000'],
            'game.data': files['ATLANTIS/ATLANTIS.001']}), parse_game_policy(profile))
        host = EngineHost(profile, default_registry(), services=HostServices.create(profile, resources=provider))
        host.boot()
        for _ in range(8):
            host.tick()
            if host.engine.state.variables[154] == 0x1357:
                break
        self.assertEqual(host.engine.state.variables[150:155], [2, 0x1234, 0, 0, 0x1357])
        self.assertEqual(host.engine.state.cutscenes, [])

    def test_original_masked_room_transition_and_revisit(self):
        root=Path(__file__).resolve().parents[1]
        p=load_profile(root/'examples/profiles/scumm_v5_game_analysis_fixture.json',verify_resources=False)
        p=replace(p,options={**p.options,'headless_presentation':True})
        files=source_files(masks=True,transitions=True)
        provider=LucasartsScummV5ResourceProvider(MemoryResourceProvider({
            'game.index':files['ATLANTIS/ATLANTIS.000'],'game.data':files['ATLANTIS/ATLANTIS.001']}),parse_game_policy(p))
        self.assertEqual(provider.read('room.1'),provider.read('room.2'))
        h=EngineHost(p,default_registry(),services=HostServices.create(p,resources=provider));h.boot()
        for stage, room in enumerate((1,1,1,2,1),1):
            for _ in range(40):
                h.tick();slots=[s for s in h.engine.state.scripts if s.number==1]
                if slots and slots[0].locals[1]==stage:break
            self.assertEqual(slots[0].locals[1],stage)
            self.assertEqual(h.engine.state.current_room,room)
            self.assertEqual([h.engine.state.actors[a].room for a in (1,2)],[room,room])
            slots[0].locals[0]=stage

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

    def test_source_masks_remain_separate_and_select_original_planes(self):
        from same.engines.scumm_v5.room import decode_room, ScummV5RoomAdapter
        from same.engines.scumm_v5.engine import ActorState
        from same.video import IndexedSurface
        from types import SimpleNamespace
        root=Path(__file__).resolve().parents[1]
        p=load_profile(root/'examples/profiles/scumm_v5_game_analysis_fixture.json',verify_resources=False)
        files=source_files(masks=True)
        provider=LucasartsScummV5ResourceProvider(MemoryResourceProvider({
            'game.index':files['ATLANTIS/ATLANTIS.000'],'game.data':files['ATLANTIS/ATLANTIS.001']}),parse_game_policy(p))
        room=decode_room(provider.read('room.1'),key='room.1')
        self.assertEqual(len(room.zplanes),2)
        h=EngineHost(p,default_registry(),services=HostServices.create(p,resources=provider));h.boot()
        for _ in range(20):
            h.tick()
            slots=[slot for slot in h.engine.state.scripts if slot.number==1]
            if slots and slots[0].locals[1]==1:break
        self.assertEqual([h.engine.state.actors[i].force_clip for i in (1,2)],[1,2])
        adapter=ScummV5RoomAdapter(SimpleNamespace(services=HostServices.create(p,resources=provider)))
        adapter.room=room;adapter.backdrop_surface=IndexedSurface.wrap(room.width,room.height,room.width,room.pixels)
        adapter.logical_surface=IndexedSurface(room.width,room.height)
        actors={i:ActorState(costume=i,room=1,visible=True,position=(150+i*10,124),scale=(231,200),costume_frame=1,costume_step=0,facing=180,ignore_boxes=True,force_clip=i) for i in (1,2)}
        adapter.render_actors(actors,current_room=1,costume_key=lambda n:f'costume.{n}',project=False)
        masked=bytes(adapter.logical_surface.pixels)
        for a in actors.values():a.force_clip=0
        adapter.render_actors(actors,current_room=1,costume_key=lambda n:f'costume.{n}',project=False)
        self.assertGreater(sum(a!=b for a,b in zip(masked,adapter.logical_surface.pixels)),100)
