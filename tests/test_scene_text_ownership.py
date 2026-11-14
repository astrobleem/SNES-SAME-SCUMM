"""Execute the shared-damage ownership fence; this is not emulator evidence."""
from pathlib import Path
import unittest
from test_scumm_v5_actor_damage_boundaries import ControllerMachine

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT/'runtime/snes/services/video_overlay_indexed.inc.pasm').read_text()

class SceneTextOwnershipTests(unittest.TestCase):
    def fence(self, owner, writable):
        m = ControllerMachine([])
        body = TEXT.split('Same_VideoOverlay_CanCompose_Far:', 1)[1].split('Same_VideoOverlay_CanWrite_Far:', 1)[0]
        m.code, m.labels = [], {'entry': 0}
        for raw in body.splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'): continue
            if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
            else: m.code.append(line)
        m.labels['Same_VideoSurface_CanWrite_Far'] = len(m.code)
        m.code += ['lda #$0001', 'sta.l reached_surface', 'clc' if writable else 'sec', 'rtl']
        m.mem['SAME_VIDEO_SURFACE_COMPOSITION_OWNER'] = owner
        m.run('entry', preserve_a=False)
        return m.c, m.mem.get('reached_surface', 0)

    def test_owned_surface_cannot_publish_text_even_when_backend_idle(self):
        for owner in (1, 2, 65535):
            self.assertEqual(self.fence(owner, True), (True, 0))
        self.assertEqual(self.fence(0, True), (False, 1))
        self.assertEqual(self.fence(0, False), (True, 1))

    def test_show_hide_and_admission_use_same_fence_before_damage(self):
        for start, end in (('Same_VideoOverlay_CanWrite_Far:', 'Same_VideoOverlay_ShowTalkSegment_Far:'),
                           ('Same_Text_ProcessPending_Far:', 'Same_VideoOverlay_Hide_Far:'),
                           ('Same_Text_ProcessHide_Far:', 'Same_Text_Clear:')):
            body=TEXT.split(start,1)[1].split(end,1)[0]
            self.assertIn('jsl Same_VideoOverlay_CanCompose_Far',body)
            self.assertNotIn('jsl Same_VideoSurface_CanWrite_Far',body)
            if 'jsr Same_Text_SeedDamage' in body:
                self.assertLess(body.index('jsl Same_VideoOverlay_CanCompose_Far'),body.index('jsr Same_Text_SeedDamage'))

    def test_scene_lease_follows_existing_begin_submit_and_rollback(self):
        scene=(ROOT/'runtime/snes/engines/scumm_v5_actor_scene.inc.pasm').read_text()
        self.assertEqual(scene.count('sta.l SAME_VIDEO_SURFACE_COMPOSITION_OWNER'),3)
        for label in ('ScummV5_Scene_Render__begun:', 'ScummV5_Scene_Render__submitted:', 'ScummV5_Scene_Abort__clear:'):
            # Submission can perform a byte-wide camera notification before
            # releasing its scene lease. Bound by the actual pose retirement,
            # not by the first accumulator-width change in the transaction.
            end=('    sta.l SAME_SCUMM_CEL_VALID' if label.endswith('__submitted:')
                 else '    sep #$20')
            block=scene.split(label,1)[1].split(end,1)[0]
            self.assertIn('sta.l SAME_VIDEO_SURFACE_COMPOSITION_OWNER',block)
        self.assertIn('SAME_VIDEO_SURFACE_COMPOSITION_OWNER = SAME_VIDEO_TEXT_STATE+$6C', TEXT)
        self.assertIn('cpx #$0080',TEXT.split('Same_VideoOverlay_Reset_Far:',1)[1].split('Same_VideoOverlay_Frame_Far:',1)[0])
