"""Execute the production checked-pose return; not emulator acceptance."""
from pathlib import Path
import unittest
import test_scumm_cutscene_callback_native as blocks

ROOT = Path(__file__).resolve().parents[1]


class CheckedActorAdmission(unittest.TestCase):
    def test_ready_byte_is_independent_of_caller_width_and_adjacent_loop(self):
        source = (ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        block = source.split('ScummV5_ActorPose_Ensure__return:', 1)[1].split(
            '; Signed half-open bounds', 1)[0]
        for status in (0, 0x10, 0x20, 0x30):
            for ready in (0, 1):
                for loop in (0, 1, 6, 255):
                    with self.subTest(status=status, ready=ready, loop=loop):
                        prefix = (f'sep #${status:02x}\nphp\nrep #$30\n'
                                  'pha\nphx\nphy\n')
                        # Observe the returned status without changing carry.
                        observed = block.replace('rtl', 'php\nsep #$20\npla\n'
                                                 'sta.l TEST_STATUS\nrtl')
                        m = blocks.CutsceneCallbackNative.machine(self, prefix+observed)
                        m.symbols['TEST_STATUS'] = 0x100
                        m.put('SAME_SCUMM_ACTOR_POSE_RESULT', ready, 1)
                        m.put('SAME_SCUMM_ACTOR_POSE_LOOP_START', loop, 1)
                        self.assertEqual(m.symbols['SAME_SCUMM_ACTOR_POSE_RESULT']+1,
                                         m.symbols['SAME_SCUMM_ACTOR_POSE_LOOP_START'])
                        carry, _ = m.consume()
                        self.assertEqual(carry, bool(ready))
                        self.assertEqual(m.get('TEST_STATUS', 1)&0x30, status)

    def test_source_one_shot_limb_produces_nonzero_repeat_origin(self):
        from examples.resources.scumm_v5.actor_scaling_fixture import costume
        from same.engines.scumm_v5.costume import ScummV5Costume
        c = ScummV5Costume(costume(one_shot_limb=True), key='original fixture')
        for frame in (1, 2):
            for facing in (0, 90, 180, 270):
                commands = [c.decode_pose(frame, facing=facing, step=i).commands
                            for i in range(4)]
                self.assertNotEqual(commands[0], commands[1])
                self.assertIn(commands[3], commands[1:3])
                self.assertNotIn(commands[0], commands[1:])

    def test_scene_distinguishes_pending_from_fatal_checked_read(self):
        source = (ROOT/'runtime/snes/engines/scumm_v5_actor_scene.inc.pasm').read_text()
        block = source.split('ScummV5_Scene_Render__mask_ready:', 1)[1].split(
            'ScummV5_Scene_Render__checked:', 1)[0]
        code = ('rep #$30\n'+block.replace('jml ', 'jmp ')+
                'ScummV5_Scene_Render__checked:\nlda #$0001\nsta.l TEST_DRAW\n'
                'ScummV5_Scene_Render__done:\nrtl\n')
        for ready, error in ((False,0),(False,16),(True,0)):
            with self.subTest(ready=ready,error=error):
                m = blocks.CutsceneCallbackNative.machine(self, code)
                m.symbols['TEST_DRAW'] = 0x100
                m.put('SAME_SCUMM_ERROR',error,1)
                calls=[]
                def service(name,p,a):
                    calls.append(name)
                    return ((p|1) if ready else (p&~1)),a
                m.service=service
                m.consume()
                self.assertEqual(m.get('TEST_DRAW'),int(ready))
                self.assertEqual('ScummV5_ActorPose_Cancel_Far' in calls,bool(error))
                self.assertEqual(m.get('SAME_SCUMM_ERROR',1),error)
