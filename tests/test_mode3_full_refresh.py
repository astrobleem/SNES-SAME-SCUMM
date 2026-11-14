"""Source-instruction regressions; native pixel acceptance is a separate gate."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class FullRefreshCoverageTests(unittest.TestCase):
    def test_only_fully_replaced_columns_remain_cached(self):
        text=(ROOT/'runtime/snes/services/video_mode3_retained.inc.pasm').read_text()
        text=text.split('Same_Mode3_Retained_InvalidateCoverage_Far:',1)[1]
        text=text.split('; Enable a cold,',1)[0]
        for active in (0,1,2,3):
            for current in (0,1,7,8,232,255,256,519,1024):
                with self.subTest(active=active,current=current):
                    m=StripMachine()
                    m.symbols.update(MODE3_R_CURRENT=0x401084,
                                     MODE3_R_FIRST=0x401088,MODE3_R_LAST=0x40108A)
                    m.code=[];m.labels={}
                    for raw in text.splitlines():
                        line=raw.split(';')[0].strip()
                        if not line or line.startswith('.'):continue
                        if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                        else:m.code.append(line)
                    m.put('MODE3_R_ACTIVE',active,1)
                    m.put('MODE3_R_CURRENT',current)
                    m.put('MODE3_R_FIRST',0x1234);m.put('MODE3_R_LAST',0x5678)
                    m.consume()
                    expected=((current+7)//8,(current+256)//8-1) if active==1 else (0x1234,0x5678)
                    self.assertEqual((m.get('MODE3_R_FIRST'),m.get('MODE3_R_LAST')),expected)
                    if active==1:
                        for c in range(expected[0],expected[1]+1):
                            self.assertTrue(current<=c*8 and c*8+8<=current+256)

    def test_full_refresh_keeps_camera_motion_in_the_retained_commit_path(self):
        text=(ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text()
        prepare=text.split('cmp #$0002',1)[1].split('CameraObjectsPrepare_camera_target:',1)[0]
        self.assertIn('lda.l SAME_VIDEO_SURFACE_SOURCE_X',prepare)
        self.assertNotIn('SAME_VIDEO_SURFACE_PENDING_XSTART',prepare)
        copy=text.split('ScummV5_Camera_ServicePending__copy:',1)[1].split('jsl Same_VideoSurface_InvalidateTileCache_Far',1)[0]
        self.assertIn('jsl Same_VideoSurface_WriteIndexedPair_Far',copy)
        self.assertNotIn('sta.l SAME_SCUMM_LIVE_ROOM_SURFACE_BASE',copy)

    def test_complete_object_scene_rechecks_a_target_that_stopped_during_io(self):
        text=(ROOT/'runtime/snes/engines/scumm_v5_actor_scene.inc.pasm').read_text()
        text=text.split('ScummV5_Scene_Render__submitted:',1)[1].split('lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION',1)[0]
        for refresh in (0,2):
            m=StripMachine()
            m.symbols['SAME_SCUMM_OBJECT_IMAGE_REFRESH']=0x37D0
            m.code=[];m.labels={}
            for raw in (text+'\nrtl').splitlines():
                line=raw.split(';')[0].strip()
                if not line or line.startswith('.'):continue
                if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                else:m.code.append(line)
            m.put('SAME_SCUMM_OBJECT_IMAGE_REFRESH',refresh)
            m.put('SAME_VIDEO_SURFACE_PENDING_VISUAL',0,1)
            m.consume()
            self.assertEqual(m.get('SAME_SCUMM_OBJECT_IMAGE_REFRESH'),0)
            self.assertEqual(m.get('SAME_VIDEO_SURFACE_PENDING_VISUAL',1),int(refresh==2))
