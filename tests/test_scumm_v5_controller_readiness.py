"""Cold WRAM must not arm the room-installed controller/actor lifecycle."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / 'runtime/snes/engines'
READY = 'SAME_SCUMM_CONTROLLER_ROOM_READY'


def execute_latch_block(source, memory, *, controller=True):
    """Execute the small actual straight-line byte-store initialization block.

    Includes the production feature guard, so the non-controller build does
    not accidentally gain a write to memory it does not own.
    """
    a, bits, enabled = 0xA5, 16, True
    writes = []
    for raw in source.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line or line in ('.a8', '.a16', '.i16', 'php'):
            continue
        if line == '.if SAME_BUILD_SCUMM_CONTROLLER':
            enabled = controller
        elif line == '.endif':
            enabled = True
        elif not enabled:
            continue
        elif line.startswith(('sep #', 'rep #')):
            if int(line.split('$')[1], 16) & 0x20:
                bits = 8 if line.startswith('sep') else 16
        elif line.startswith('lda #$'):
            a = int(line.split('$')[1], 16)
        elif line.startswith('lda.l '):
            a = memory.get(line[6:], 0)
        elif line == 'inc':
            a = (a + 1) & ((1 << bits)-1)
        elif line.startswith('sta.l '):
            assert bits == 8, 'readiness initialization must not overwrite its neighbor'
            memory[line[6:]] = a & 255
            writes.append((line[6:], a & 255))
        else:
            raise AssertionError(f'unexpected instruction in latch block: {line}')
    return writes


class ControllerReadinessTests(unittest.TestCase):
    def test_cold_boot_disarms_all_possible_stale_bytes(self):
        core = (ROOT / 'scumm_v5.pasm').read_text()
        boot = core.split('ScummV5_Engine_Boot:', 1)[1].split(
            '.if SAME_BUILD_SCUMM_M19', 1)[0]
        for garbage in range(256):
            with self.subTest(garbage=garbage):
                memory = {READY: garbage}
                writes = execute_latch_block(boot, memory)
                self.assertEqual(memory[READY], 0)
                self.assertEqual([value for name, value in writes if name == READY], [0])
        memory = {READY: 249}
        writes = execute_latch_block(boot, memory, controller=False)
        self.assertEqual(memory[READY], 249)
        self.assertNotIn(READY, [name for name, _ in writes])

    def test_both_room_install_paths_reset_then_rearm(self):
        controller = (ROOT / 'scumm_v5_controller_far.pasm').read_text()
        reset = controller.split('ScummV5_Controller_ResetInteractionOnRoomInstall_Far:', 1)[1]
        reset = reset.split('sta.l ' + READY, 1)[0] + 'sta.l ' + READY
        call = 'jsl ScummV5_Controller_ResetInteractionOnRoomInstall_Far'
        for filename in ('scumm_v5.pasm', 'scumm_v5_m24rb_far.pasm'):
            source = (ROOT / filename).read_text()
            callbacks = source.split(call)[1:]
            self.assertTrue(callbacks)
            for callback in callbacks:
                rearm = callback.split('sta.l ' + READY, 1)[0] + 'sta.l ' + READY
                for garbage in (0, 23, 249, 255):
                    with self.subTest(file=filename, garbage=garbage):
                        memory = {READY: garbage}
                        execute_latch_block(reset, memory)
                        self.assertEqual(memory[READY], 0)
                        execute_latch_block(rearm, memory)
                        self.assertEqual(memory[READY], 1)

    def test_actor_gate_precedes_pose_resolution_and_cursor_gate_precedes_draw(self):
        controller = (ROOT / 'scumm_v5_controller_far.pasm').read_text()
        actor = controller.split('ScummV5_Controller_RenderActor_Far:', 1)[1]
        gate, admitted = actor.split('ScummV5_Controller_RenderActor__room_ok:', 1)
        self.assertIn('lda.l ' + READY, gate)
        self.assertIn('bne ScummV5_Controller_RenderActor__room_ok', gate)
        self.assertIn('rtl', gate)
        self.assertNotIn('jsl ScummV5_ActorPose_Ensure_Far', gate)
        self.assertIn('jsl ScummV5_ActorPose_Ensure_Far', admitted)
        cursor = (ROOT / 'scumm_v5_cursor_far.pasm').read_text().split(
            'ScummV5_Cursor_Frame_Far:', 1)[1]
        prefix = cursor.split('ScummV5_Cursor_Frame__room:', 1)[0]
        self.assertRegex(prefix, r'lda\.l ' + READY + r'\s+and #\$00FF\s+'
                         r'bne ScummV5_Cursor_Frame__room\s+jml ScummV5_Cursor_Frame__done')
        self.assertNotIn('jsl ScummV5_Cursor_Draw', prefix)

    def test_visual_cache_is_initialized_before_install_arms_interaction(self):
        visual = (ROOT / 'scumm_v5_visual.pasm').read_text().split(
            'ScummV5_RoomVisual_Installed_Far:', 1)[1].split('ScummV5_Visual_CameraPublished_Far:', 1)[0]
        self.assertIn('jsl ScummV5_Controller_ResetVisualCache_Far', visual)
        for filename in ('scumm_v5.pasm', 'scumm_v5_m24rb_far.pasm'):
            source = (ROOT / filename).read_text()
            for before in source.split('jsl ScummV5_Controller_ResetInteractionOnRoomInstall_Far')[:-1]:
                self.assertIn('jsl ScummV5_RoomVisual_Installed_Far', before)
