"""Missing classic animation records preserve decoded cels, not blank poses."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import re
from same.engines.scumm_v5.costume import ScummV5Costume
from same.engines.scumm_v5.engine import ActorState, ScummV5Engine
from same.engines.scumm_v5.room import ScummV5RoomAdapter
from test_scumm_v5_costume import synthetic_costume, animated_costume
from tools.generate_snes_scumm_actor_sprite import compile_pose_set, pose_directory_include
import test_scumm_cutscene_callback_native as native_blocks

ROOT = Path(__file__).resolve().parents[1]


class AbsentAnimationTests(unittest.TestCase):
    machine = native_blocks.CutsceneCallbackNative.machine

    def test_presence_is_not_equivalent_to_decoded_opacity(self):
        costume = ScummV5Costume(synthetic_costume(), key="fixture")
        self.assertTrue(costume.has_animation(1, facing=180))
        self.assertFalse(costume.has_animation(1, facing=90))
        self.assertFalse(costume.has_animation(63, facing=180))
        raw = bytearray(synthetic_costume())
        # Existing animation record now explicitly clears its only limb.
        offset = int.from_bytes(raw[64:66], 'little') - 6
        raw[offset+2:offset+4] = b'\xff\xff'
        cleared = ScummV5Costume(bytes(raw), key="fixture")
        self.assertTrue(cleared.has_animation(1, facing=180))
        self.assertFalse(cleared.decode_pose(1).cels)

    def test_host_preserves_live_chore_and_command_position(self):
        engine = ScummV5Engine()
        engine.state.current_room = 1
        engine._video = object.__new__(ScummV5RoomAdapter)
        actor = ActorState(costume=1, room=1, visible=True, costume_frame=1,
                           costume_step=1, animation_progress=7)
        engine.state.actors[1] = actor
        context = SimpleNamespace(services=SimpleNamespace(resource_read=lambda key:animated_costume()))
        with patch.object(engine, '_var_or_direct_byte', side_effect=(1,63)):
            engine._op_animate_actor(None, context)
        self.assertEqual((actor.animation, actor.costume_frame, actor.costume_step,
                          actor.animation_progress), (63,1,1,0))

    def test_cooker_emits_source_presence_not_nonempty_pixel_heuristic(self):
        _, records = compile_pose_set({1: ('costume.1', synthetic_costume())}, preserve_cels=True)
        include = pose_directory_include(records, bank=24)
        table = include.split('ScummV5_ActorAnimationMasks:',1)[1].split('.bank',1)[0]
        raw = bytes(int(v,16) for v in re.findall(r'\$([0-9A-Fa-f]{2})(?![0-9A-Fa-f])',table))
        self.assertEqual(raw, bytes((1,64))+bytes(31))

    def test_native_admission_matches_frame_boundaries_and_all_directions(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_actor_animation.inc.pasm').read_text()
        costume=ScummV5Costume(synthetic_costume(), key="fixture")
        for frame in (0,1,2,6,63,64,243,244,250,252,255):
            for facing in (0,90,180,270):
                with self.subTest(frame=frame,facing=facing):
                    code=f'lda #${frame:04x}\nldx #$0040\n'+source.replace('brl ','jmp ')
                    m=self.machine(code)
                    m.symbols.update(SCUMM_V5_ACTOR_ANIMATION_MASK_COUNT=1,
                                     ScummV5_ActorAnimationMasks=0x100000,
                                     ScummV5_C7_BitMasks=0x100100)
                    m.ram[0x100000:0x100021]=bytes((1,64))+bytes(31)
                    m.ram[0x100100:0x100108]=bytes(1<<n for n in range(8))
                    base=m.symbols['SAME_SCUMM_C14_ACTORS']+64
                    m.put(base,1,1);m.put(base+0x16,1,1);m.put(base+6,1,1)
                    m.put('SAME_SCUMM_M23A_ACTIVE_ROOM',1,1)
                    m.put(m.symbols['SAME_SCUMM_ACTOR_FACINGS']+2,facing)
                    carry,writes=m.consume()
                    expected = True if 244<=frame<252 else not costume.has_animation(1 if frame>=252 else frame,facing=facing)
                    self.assertEqual(carry,expected)
                    self.assertFalse(writes)
