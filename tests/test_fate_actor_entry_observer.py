"""The graphics observer stops at room publication without inventing gameplay."""
import sys
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

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
    def test_cold_four_frame_slices_exact_progress_and_tail(self):
        session = ColdSlices(ready_at=8)
        active = [dict(slot=i, script=n, status=2, saved_pc=100+i,
                       program_unit_identity=f'LocalProgram(room=4,script={n})')
                  for i,n in enumerate((206,201,129))]
        observations=[]
        with patch.object(replay, '_snapshot', return_value={'slots':active}), \
             patch.object(replay, '_slots', return_value=[]):
            replay._cold_wait_room4(session, 10, frame_step=4, trace_enabled=False,
                                    progress_callback=observations.append)
        self.assertEqual(session.calls,[4,4])
        self.assertEqual(session.frame,8)
        self.assertEqual(observations[0]['sample']['active_c4'],active)
        self.assertEqual(session.actions,[])
        session=ColdSlices(ready_at=100)
        with patch.object(replay, '_snapshot', return_value={}), \
             patch.object(replay, '_slots', return_value=[]):
            with self.assertRaises(TimeoutError):
                replay._cold_wait_room4(session,10,frame_step=4,trace_enabled=False)
        self.assertEqual(session.calls,[4,4,2])
        self.assertEqual(session.frame,10)

    def test_timeout_with_partial_progress_remains_fatal_without_retry(self):
        for step in (4,16):
            session=ColdSlices(ready_at=100,timed_out=True)
            observations=[]
            with patch.object(replay, '_snapshot', return_value={'slots':[]}), \
                 patch.object(replay, '_slots', return_value=[]):
                with self.assertRaisesRegex(RuntimeError,'timed out'):
                    replay._cold_wait_room4(session,100,frame_step=step,
                                            progress_callback=observations.append)
            self.assertEqual(session.calls,[step])
            self.assertEqual(session.frame,step-1)
            self.assertIn('timed out',observations[-1]['error'])
            self.assertEqual(session.actions,[])

    def test_frame_step_validation_and_legacy_default(self):
        for step in (0,17,True,1.5):
            with self.assertRaises(ValueError):
                replay._cold_wait_room4(Mock(),10,frame_step=step)
        session=ColdSlices(ready_at=16)
        with patch.object(replay, '_snapshot', return_value={}), \
             patch.object(replay, '_slots', return_value=[]):
            replay._cold_wait_room4(session,20)
        self.assertEqual(session.calls,[16])

    def test_graphics_cold_source_selects_small_slices_and_returns_before_actions(self):
        source=Path(replay.__file__).read_text()
        call=source.split('ready, transitions = _cold_wait_room4(',1)[1].split('report["room_transitions"]',1)[0]
        self.assertIn('frame_step=4 if graphics_only else 16',call)
        self.assertIn('trace_enabled=not graphics_only',call)
        capture=source.split('def capture_authentic_actor(',1)[1].split('if args.capture_room4_actor_entry:',1)[0]
        self.assertIn('cursor_base=_authentic_cursor_base(rom, build_identity)',capture)
        self.assertIn('cursor_base=observer.cursor_base',capture)
        for action in ('set_input(', 'reposition_room4_cursor_to_world(', 'room4_synchronous_input_edge('):
            self.assertNotIn(action,capture)
        self.assertIn('report.setdefault("startup_progress", []).append(observation["sample"])',source)

    def test_cursor_owner_requires_matching_rom_listing_and_assembly_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            rom=root/'capture.sfc'
            rom.write_bytes(b'ROM')
            listing=rom.with_suffix('.lst')
            listing.write_text('ScummV5_Cursor_Draw_Far\n')
            paths=('runtime/snes/kernel/memory.pasm',
                   'runtime/snes/generated/carrier_constants.inc.pasm')
            payloads=('memory contract\n','SAME_SCUMM_CURSOR_PRESENTATION_BASE = $400740\n')
            entries=[]
            for relative,payload in zip(paths,payloads):
                path=root/relative
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(payload)
                entries.append(dict(kind='ASSEMBLY_INCLUDE',path=relative,
                                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            inputs=rom.with_suffix('.poppy-inputs.json')
            inputs.write_text(json.dumps({'inputs':entries}))
            generated=[dict(path=str(inputs),sha256=hashlib.sha256(inputs.read_bytes()).hexdigest())]
            identity=dict(rom={'sha256':hashlib.sha256(rom.read_bytes()).hexdigest()},
                          git={'worktree':str(root)},generated_inputs=generated,
                          generated_inputs_sha256=hashlib.sha256(json.dumps(generated,sort_keys=True).encode()).hexdigest(),
                          native_symbols={'listing':{'sha256':hashlib.sha256(listing.read_bytes()).hexdigest()}})
            self.assertEqual(replay._authentic_cursor_base(rom,identity),0x400740)
            for path in (rom,listing,inputs,root/paths[0],root/paths[1]):
                saved=path.read_bytes()
                path.write_bytes(saved+b'changed')
                with self.subTest(path=path),self.assertRaises(RuntimeError):
                    replay._authentic_cursor_base(rom,identity)
                path.write_bytes(saved)

    def test_graphics_capture_does_not_enable_continuous_native_trace(self):
        session = Mock()
        self.assertFalse(replay.arm_startup_trace(session, enabled=False)["enabled"])
        session.trace_log.assert_not_called()
        session.trace_log.return_value = {"rows": []}
        self.assertTrue(replay.arm_startup_trace(session, enabled=True)["enabled"])
        session.trace_log.assert_called_once_with(count=1, cpu_type="Snes")

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


class ColdSlices:
    def __init__(self,ready_at,timed_out=False):
        self.frame=0
        self.ready_at=ready_at
        self.timed_out=timed_out
        self.calls=[]
        self.actions=[]

    def read_memory(self,kind,address,size):
        if address==0x7FF2BF and size==4:
            return bytes((4 if self.frame>=self.ready_at else 0,1,0,0))
        return bytes(size)

    def read_u8(self,address):
        return {0x7E2221:2,0x7E5E8A:int(self.frame>=self.ready_at)}.get(address,0)

    def get_state(self):
        return {'frameCount':self.frame}

    def get_cpu_state(self,cpu):
        return {}

    def run_frames(self,count):
        self.calls.append(count)
        start=self.frame
        self.frame+=count-int(self.timed_out)
        return dict(startFrame=start,endFrame=self.frame,framesAdvanced=self.frame-start,
                    timedOut=self.timed_out)

    def tool(self,*args,**kwargs):
        self.actions.append((args,kwargs))
        raise AssertionError('cold observer must not submit actions')
