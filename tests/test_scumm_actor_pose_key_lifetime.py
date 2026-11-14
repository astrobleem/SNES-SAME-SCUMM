"""Execute pose-key reset/advance source blocks across resource backpressure."""
import unittest
from test_scumm_controller_hud_text import HudMachine, ROOT


class PoseKeyLifetimeTests(unittest.TestCase):
    def machine(self, block):
        m = HudMachine(1, 1)
        # Existing checked costume control allocation, not a new native layout.
        source = (ROOT/'runtime/snes/kernel/memory.pasm').read_text()
        import re
        for name, offset in re.findall(r'^(SAME_SCUMM_ACTOR_POSE_\w+)\s*=\s*SAME_SCUMM_ACTOR_POSE_STATE_BASE\+\$([0-9A-Fa-f]+)', source, re.M):
            m.symbols[name] = 0x41E780 + int(offset,16)
        code = 'php\nsep #$20\n' + block + '\nTest_Done:\nplp\nrtl\n'
        m.code=[];m.labels={}
        for line in code.splitlines():
            line=line.split(';',1)[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:op,_,arg=line.partition(' ');m.code.append((op,arg))
        return m

    def test_new_chore_cannot_inherit_previous_checked_animation_loop(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        prefix='ScummV5_Controller_PublishActorVisual__'
        reset=source.split(prefix+'reset_pose_step:',1)[1].split(prefix+'save_pose_key:',1)[0]
        advance=source.split(prefix+'advance_pose_step:',1)[1].split(prefix+'reset_pose_step:',1)[0]
        advance=advance.replace(prefix+'save_pose_key','Test_Done')
        for old_start,old_length in ((0,8),(2,12),(128,128)):
            m=self.machine(reset)
            for name,value in (('LOOP_START',old_start),('LOOP_LENGTH',old_length),('DESIRED_STEP',7),('ANIM_COUNTER',99)):
                m.put('SAME_SCUMM_ACTOR_POSE_'+name,value,1)
            m.run()
            # Hundreds of camera/provider wait turns must leave new step zero
            # until its own directory row supplies valid loop metadata.
            n=self.machine(advance);n.mem.update(m.mem)
            n.put('SAME_SCUMM_ACTOR_POSE_STATE',0,1)
            for _ in range(300):n.run()
            self.assertEqual(n.get('SAME_SCUMM_ACTOR_POSE_DESIRED_STEP',1),0)
            self.assertEqual(n.get('SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH',1),0)
            n.put('SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH',1,1);n.run()
            self.assertEqual(n.get('SAME_SCUMM_ACTOR_POSE_DESIRED_STEP',1),0)
            # A subsequently checked multi-step key still animates normally.
            n.put('SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH',3,1)
            for expected in (1,2,0):
                n.run();self.assertEqual(n.get('SAME_SCUMM_ACTOR_POSE_DESIRED_STEP',1),expected)

    def test_idle_put_actor_position_is_a_complete_snapshot(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        prefix='ScummV5_Controller_PublishActorVisual__'
        block=source.split(prefix+'check_destination:',1)[1].split(prefix+'destination_valid:',1)[0]
        block=block.replace(prefix+'standing','Test_Done')
        block=block.replace(prefix+'destination_valid','Test_Done')
        m=self.machine(block)
        m.put('SAME_SCUMM_CONTROLLER_DESIRED_DEST',65535,2)
        m.put('SAME_SCUMM_CONTROLLER_DESIRED_X',220,2)
        m.put('SAME_SCUMM_CONTROLLER_RENDER_X',150,2)
        m.run()
        self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_DESIRED_X',2),220)
        self.assertNotIn(prefix+'done',block)
