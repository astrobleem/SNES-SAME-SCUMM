"""Execute actual held-input/clamp instructions without emulator or game data."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


def machine(entry, camera=False):
    m=StripMachine()
    source=(ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
    source=source.split(entry+':',1)[1]
    if entry.endswith('CursorMotion_Far'):source=source.split('; Keep the logical cursor',1)[0]
    m.code=[];m.labels={};active=[True]
    for raw in source.splitlines():
        line=raw.split(';')[0].strip()
        if line.startswith('.if '):
            assert line[4:] in ('SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES','SCUMM_MSU1_CAMERA_VIEWPORT')
            active.append(active[-1] and camera);continue
        if line=='.endif':active.pop();continue
        if not active[-1] or not line or line.startswith('.'):continue
        if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
        else:m.code.append(line)
    return m


class ControllerCursorRepeatTests(unittest.TestCase):
    def test_immediate_edge_then_bounded_hold_and_no_action_repeat(self):
        m=machine('ScummV5_Controller_CursorMotion_Far');result=[]
        for frame in range(10):
            m.put('SAME_FRAME_COUNTER',frame)
            m.put('SAME_INPUT_PRESSED',0x180 if frame==0 else 0)
            m.put('SAME_INPUT_HELD',0x180)
            m.consume();result.append(m.get('SAME_SCUMM_PLAY_UI_MOTION'))
        self.assertEqual(result,[0x100,0,0x100,0,0x100,0,0x100,0,0x100,0])
        self.assertEqual(m.get('SAME_INPUT_HELD'),0x180)
        m.put('SAME_INPUT_HELD',0);m.consume()
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_HELD'),0)
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MOTION'),0)

    def test_frame_wrap_and_direction_change(self):
        m=machine('ScummV5_Controller_CursorMotion_Far')
        m.put('SAME_INPUT_HELD',0x200);m.put('SAME_FRAME_COUNTER',65535);m.consume()
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MOTION'),0x200)
        m.put('SAME_FRAME_COUNTER',0);m.consume();self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MOTION'),0)
        m.put('SAME_FRAME_COUNTER',1);m.consume();self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MOTION'),0x200)
        m.put('SAME_INPUT_HELD',0x400);m.consume();self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MOTION'),0x400)

    def test_cursor_clamp_uses_installed_viewport_and_preserves_world_transform(self):
        for camera in (False,True):
            m=machine('ScummV5_Controller_ClampCursor_Far',camera)
            m.put('SAME_VIDEO_SURFACE_SOURCE_X',352);m.put('SAME_SCUMM_CAMERA_VSCREEN_XSTART',320)
            m.put('SAME_VIDEO_SURFACE_SOURCE_Y',0);m.put('SAME_SCUMM_CAMERA_CURRENT_Y',100)
            m.put('SAME_VIDEO_SURFACE_COPY_WIDTH',256);m.put('SAME_VIDEO_SURFACE_COPY_HEIGHT',144)
            for x,y in ((-2,-2),(84,60),(400,300),(32,143)):
                m.put('SAME_SCUMM_CONTROLLER_CURSOR_X',x);m.put('SAME_SCUMM_CONTROLLER_CURSOR_Y',y)
                m.consume()
                self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_CURSOR_X'),max(32 if camera else 0,min(287 if camera else 319,x)))
                self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_CURSOR_Y'),max(0,min(143 if camera else 199,y)))

    def test_delayed_controller_turn_is_frame_paced_and_bounded(self):
        m=machine('ScummV5_Controller_CursorMotion_Far')
        m.put('SAME_INPUT_HELD',0x100);m.put('SAME_FRAME_COUNTER',100);m.consume()
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_STEP'),2)
        for frame,step in ((106,6),(113,6),(130,8),(500,8)):
            m.put('SAME_FRAME_COUNTER',frame);m.consume()
            self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_STEP'),step)
            self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_MOTION'),0x100)
        m.put('SAME_INPUT_PRESSED',0x200);m.put('SAME_INPUT_HELD',0x200);m.consume()
        self.assertEqual(m.get('SAME_SCUMM_PLAY_UI_STEP'),2)
