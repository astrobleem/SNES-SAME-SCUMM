"""Production cancellation source with video stubs; not emulator evidence."""
from pathlib import Path
import unittest

from test_scumm_v5_actor_damage_boundaries import ControllerMachine


class SceneAbortMachine(ControllerMachine):
    def __init__(self, phase, ready, locked=False):
        super().__init__([])
        text = (Path(__file__).resolve().parents[1] /
                'runtime/snes/engines/scumm_v5_actor_scene.inc.pasm').read_text()
        text = text[text.index('ScummV5_Scene_Abort_Far:'):]
        text = text[:text.index('; Palette presence')]
        self.code, self.labels, self.restores = [], {}, 0
        self.locked = locked
        for raw in text.splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
            else:
                self.code.append(line)
        self.mem.update(SAME_SCUMM_SCENE_PHASE=phase,
                        SAME_SCUMM_SCENE_JOURNAL_READY=ready,
                        SAME_SCUMM_SCENE_INITIALIZED=1,
                        SAME_SCUMM_SCENE_DIRTY=0,
                        SAME_SCUMM_ERROR=0,
                        SAME_SCUMM_CURSOR_COMPOSING=1,
                        SAME_SCUMM_CEL_VALID=1)

    def service(self, name):
        if name != 'Same_VideoSurface_RestoreActorUnderlay_Far':
            raise AssertionError(name)
        self.restores += 1
        self.c = self.locked


class SceneAbortTests(unittest.TestCase):
    def test_completed_dma_owned_scene_is_not_rolled_back(self):
        for locked in (False, True):
            m = SceneAbortMachine(4, 1, locked)
            m.run('ScummV5_Scene_Abort_Far')
            self.assertEqual(m.restores, 0)
            self.assertEqual(m.mem['SAME_SCUMM_ERROR'], 0)
            self.assertEqual(m.mem['SAME_SCUMM_SCENE_JOURNAL_READY'], 1)
            self.assertEqual(m.mem['SAME_SCUMM_SCENE_PHASE'], 0)
            self.assertEqual(m.mem['SAME_SCUMM_SCENE_DIRTY'], 1)

    def test_unpublished_composition_restores_only_committed_journal(self):
        for phase, ready in ((1, 0), (2, 1), (3, 1)):
            m = SceneAbortMachine(phase, ready)
            m.run('ScummV5_Scene_Abort_Far')
            self.assertEqual(m.restores, ready)
            self.assertEqual(m.mem['SAME_SCUMM_CEL_VALID'], 0)
            self.assertEqual(m.mem['SAME_SCUMM_CURSOR_COMPOSING'], 0)
            self.assertEqual(m.mem['SAME_SCUMM_ERROR'], 0)

    def test_last_mask_block_advances_strip_without_16bit_row_wrap(self):
        text = (Path(__file__).resolve().parents[1] /
                'runtime/snes/engines/scumm_v5_actor_masks.inc.pasm').read_text()
        text = text[text.index('MaskEnsure_block_released:'):text.index('MaskEnsure_more_blocks:')]
        for block, bottom, next_column in ((0, 255, True), (0, 257, False),
                                           (254, 65535, False), (255, 65535, True)):
            m = SceneAbortMachine(0, 0)
            m.code, m.labels = ['php', 'rep #$30'], {'entry': 0}
            for raw in text.splitlines():
                line = raw.split(';', 1)[0].strip()
                if not line or line.startswith('.'):
                    continue
                if line.endswith(':'):
                    m.labels[line[:-1]] = len(m.code)
                else:
                    m.code.append(line)
            m.labels['MaskEnsure_more_blocks'] = len(m.code)
            m.labels['MaskEnsure_ready'] = len(m.code)
            m.code.extend(('plp', 'rtl'))
            m.mem.update(SAME_SCUMM_MASK_BLOCK=block, SAME_SCUMM_MASK_BOTTOM=bottom,
                         SAME_SCUMM_MASK_COLUMN=2, SAME_SCUMM_MASK_RIGHT=3)
            m.run('entry', preserve_a=False)
            self.assertEqual(m.mem['SAME_SCUMM_MASK_COLUMN'], 3 if next_column else 2)

    def test_idle_scene_is_untouched(self):
        m = SceneAbortMachine(0, 1)
        m.run('ScummV5_Scene_Abort_Far')
        self.assertEqual(m.restores, 0)
        self.assertEqual(m.mem['SAME_SCUMM_SCENE_DIRTY'], 0)


if __name__ == '__main__':
    unittest.main()
