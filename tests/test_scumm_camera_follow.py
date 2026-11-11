"""v5 follow-strip semantics, independent host/native-source differential.

Instruction runner evidence is distinct from an emulator viewport capture.
"""
import unittest
from unittest.mock import patch
import test_scumm_v5_engine as conformance
from test_scumm_camera_native_copy import StripMachine, ROOT
import sys
sys.path.insert(0,str(ROOT/"tools"))
import audit_scumm_residency_wram as audit


class CameraFollowTests(unittest.TestCase):
    def pair(self, x=320, actor=320, fast=0):
        host = conformance.ScummV5EngineTests()._host(bytes((0x80,)))
        state = host.engine.state
        state.current_room = 1
        state.room_ops.room_width = 640
        state.room_ops.scroll_min_x = 160
        state.room_ops.scroll_max_x = 480
        state.camera_x = state.camera_destination_x = x
        state.camera_mode = 1; state.camera_follow_actor = 1
        state.screen_start_strip = x//8-20
        state.variables[26] = fast
        host.engine._actor(1).position = (actor, 100)
        m = StripMachine(); m.code = []; m.labels = {}; m.service_writes = []
        source = (ROOT/'runtime/snes/engines/scumm_v5_camera_far.pasm').read_text()
        source = source.split('ScummV5_Camera_Update_Far:',1)[1]
        enabled = [True]
        for raw in source.splitlines():
            line = raw.split(';')[0].strip()
            if line.startswith('.if '): enabled.append(enabled[-1]); continue
            if line == '.else': enabled[-1] = not enabled[-1]; continue
            if line == '.endif': enabled.pop(); continue
            if not all(enabled) or not line or line.startswith('.'): continue
            if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
            else: m.code.append(line)
        def service(name, p, a):
            self.assertEqual(name, 'ScummV5_Visual_CameraPublished_Far')
            return p, a
        m.service = service
        for name, value, size in (
            ('SAME_SCUMM_CAMERA_CURRENT_X',x,2),('SAME_SCUMM_CAMERA_DEST_X',x,2),
            ('SAME_SCUMM_CAMERA_SCREEN_START_STRIP',x//8-20,2),
            ('SAME_SCUMM_C10_ROOM_WIDTH',640,2),('SAME_SCUMM_C10_SCROLL_MIN',160,2),
            ('SAME_SCUMM_C10_SCROLL_MAX',480,2),('SAME_SCUMM_C15_CAMERA_MODE',1,1),
            ('SAME_SCUMM_C15_CAMERA_FOLLOWS',1,1)):
            m.put(name,value,size)
        m.put(m.symbols['SAME_SCUMM_C31_POSITIONS']+4,actor&65535)
        m.put(m.symbols['SAME_SCUMM_M23B_VARIABLES']+52,fast)
        return host,m

    def step(self, host, m):
        host.engine._move_camera(host.context); m.consume(); s=host.engine.state
        for symbol, expected, size in (
            ('SAME_SCUMM_CAMERA_CURRENT_X',s.camera_x,2),
            ('SAME_SCUMM_CAMERA_DEST_X',s.camera_destination_x,2),
            ('SAME_SCUMM_CAMERA_VSCREEN_XSTART',s.virtual_screen_xstart,2),
            ('SAME_SCUMM_C15_MOVING_TO_ACTOR',int(s.camera_moving_to_actor),1)):
            self.assertEqual(m.get(symbol,size),expected,(symbol,s.camera_x,s.camera_destination_x))
        return s

    def test_trigger_boundaries_fast_scroll_and_room_clamps(self):
        for fast in (0,1):
            for actor in (-8,0,199,200,239,240,247,320,400,407,408,440,448,640):
                with self.subTest(fast=fast,actor=actor):
                    host,m=self.pair(actor=actor,fast=fast)
                    for _ in range(42): self.step(host,m)
                    self.assertTrue(160<=host.engine.state.camera_x<=480)

    def test_follows_moving_actor_without_unaligned_oscillation(self):
        host,m=self.pair(x=160,actor=248)
        for actor in range(248,281):
            host.engine._actor(1).position=(actor,100)
            m.put(m.symbols['SAME_SCUMM_C31_POSITIONS']+4,actor)
            self.step(host,m)
        for _ in range(35): self.step(host,m)
        self.assertEqual(host.engine.state.camera_x,256) # catch-up ended, actor stays inside dead zone
        self.assertFalse(host.engine.state.camera_moving_to_actor)
        host,m=self.pair(x=320,actor=407)
        for _ in range(35): self.step(host,m)
        self.assertEqual(host.engine.state.camera_x,320) # still inside strip30
        host.engine.state.camera_moving_to_actor=True
        m.put('SAME_SCUMM_C15_MOVING_TO_ACTOR',1,1)
        for _ in range(35): self.step(host,m)
        self.assertEqual(host.engine.state.camera_x,400)
        self.assertFalse(host.engine.state.camera_moving_to_actor)

    def test_hit_test_scratch_cannot_overwrite_persistent_follow_state(self):
        _,m=self.pair()
        old=m.ram[m.symbols['SAME_SCUMM_C15_CAMERA_FOLLOWS']:m.symbols['SAME_SCUMM_C15_STATE_END']]
        m.put('SAME_SCUMM_C29_X',0xABCD);m.put('SAME_SCUMM_C29_Y',0x1234)
        m.put('SAME_SCUMM_C29_ACTOR',31,1)
        self.assertEqual(m.ram[m.symbols['SAME_SCUMM_C15_CAMERA_FOLLOWS']:m.symbols['SAME_SCUMM_C15_STATE_END']],old)
        self.assertEqual(audit.audit()['result'],'pass')
        bad=audit.symbols();bad['SAME_SCUMM_C29_SCRATCH_BASE']=0x7F5F0A;bad['SAME_SCUMM_C29_SCRATCH_END']=0x7F5F0F
        with patch.object(audit,'symbols',return_value=bad):
            with self.assertRaisesRegex(ValueError,'overlap'):audit.audit()


class CameraRoomBoundsTests(unittest.TestCase):
    def test_native_room_commit_installs_bounds_but_refresh_does_not(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text()
        body=source.split('ScummV5_Camera_InstallRoomBounds_Far:',1)[1].split('ScummV5_Camera_InstallGeometry_Far:',1)[0]
        for width in (8,256,320,640,1280):
            m=StripMachine();m.code=[];m.labels={}
            for raw in body.splitlines():
                line=raw.split(';')[0].strip()
                if not line or line.startswith('.'):continue
                if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                else:m.code.append(line)
            m.put('SAME_SCUMM_VIEWPORT_ROOM_WIDTH',width)
            m.put('SAME_SCUMM_C10_SCROLL_MIN',300)
            m.put('SAME_SCUMM_C10_SCROLL_MAX',300)
            m.put('SAME_SCUMM_C15_CAMERA_MODE',1,1)
            m.put('SAME_SCUMM_C15_MOVING_TO_ACTOR',1,1)
            m.consume()
            for name,value,size in (
                ('SAME_SCUMM_C10_ROOM_WIDTH',width,2),
                ('SAME_SCUMM_C10_SCROLL_MIN',160,2),
                ('SAME_SCUMM_C10_SCROLL_MAX',max(160,width-160),2),
                ('SAME_SCUMM_CAMERA_CURRENT_X',160,2),
                ('SAME_SCUMM_CAMERA_DEST_X',160,2),
                ('SAME_SCUMM_CAMERA_VSCREEN_XSTART',0,2),
                ('SAME_SCUMM_C15_CAMERA_MODE',0,1),
                ('SAME_SCUMM_C15_MOVING_TO_ACTOR',0,1)):
                self.assertEqual(m.get(name,size),value,(width,name))
        refresh=source.split('ScummV5_Camera_ServicePending_Far:',1)[1]
        self.assertNotIn('jsl ScummV5_Camera_InstallRoomBounds_Far',refresh)
        publisher=(ROOT/'runtime/snes/engines/scumm_v5_msu_live_room.pasm').read_text().split('ScummV5_LiveRoom_PublishVisual_Far:',1)[1].split('ScummV5_LiveRoom_LoadActiveRoom_Far:',1)[0]
        self.assertIn('jsl ScummV5_Camera_InstallRoomBounds_Far',publisher)
        self.assertLess(publisher.index('cmp #$0001'),publisher.index('jsl ScummV5_Camera_InstallRoomBounds_Far'))

    def test_host_room_entry_resets_previous_scroll_before_entry_callback(self):
        from examples.resources.scumm_v5.room_bundle_fixture import room2
        host=conformance.ScummV5EngineTests()._host(b'\x80',resources={'room.2':room2()})
        state=host.engine.state
        state.room_ops.scroll_min_x=state.room_ops.scroll_max_x=400
        state.camera_x=state.camera_destination_x=400
        state.camera_mode=1;state.camera_moving_to_actor=True
        observations=[]
        host.engine._load_room(host.context,2,required=True,before_entry=lambda:observations.append((
            state.room_ops.room_width,state.room_ops.scroll_min_x,state.room_ops.scroll_max_x,
            state.camera_x,state.camera_mode,state.camera_moving_to_actor,state.virtual_screen_xstart)))
        self.assertEqual(observations,[(8,160,160,160,0,False,0)])
        # Later authored bounds are not reset by the ordinary camera tick.
        state.room_ops.room_width=640
        state.room_ops.scroll_min_x=240;state.room_ops.scroll_max_x=400
        host.engine._move_camera(host.context)
        self.assertEqual((state.room_ops.scroll_min_x,state.room_ops.scroll_max_x),(240,400))


class CameraScriptPositionTests(unittest.TestCase):
    def test_source_program_observes_current_position_before_each_tick(self):
        # Original synthetic v5: copy VAR_CAMERA_POS_X into50, yield, repeat.
        program=bytes((0x9A,50,0,2,0,0x80,0x18,0xF7,0xFF))
        host=conformance.ScummV5EngineTests()._host(program)
        host.context.profile.options.pop("publish_camera_position", None)
        state=host.engine.state
        state.current_room=1
        state.room_ops.room_width=640
        state.room_ops.scroll_min_x=160;state.room_ops.scroll_max_x=480
        self.assertEqual(state.variables[27],0) # no optional scroll callback
        for x,destination in ((336,160),(328,160),(160,480),(480,160)):
            state.camera_x=x;state.camera_destination_x=destination
            state.variables[2]=-123
            host.tick()
            self.assertEqual(state.variables[50],x)
            self.assertEqual(state.variables[2],x)
            self.assertNotEqual(state.camera_x,x) # subsequent camera phase moved

    def test_native_publication_updates_both_banks_and_preserves_adjacent_state(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        body=source.split('ScummV5_PublishCameraPosition:',1)[1].split('ScummV5_Engine_Frame:',1)[0]
        for x in (160,168,336,480,32000):
            m=StripMachine();m.code=[];m.labels={}
            for raw in body.splitlines():
                line=raw.split(';')[0].strip()
                if not line or line.startswith('.'):continue
                if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                else:m.code.append(line)
            m.put('SAME_SCUMM_CAMERA_CURRENT_X',x)
            for bank in ('SAME_SCUMM_VARIABLES','SAME_SCUMM_M23B_VARIABLES'):
                address=m.symbols[bank];m.ram[address:address+12]=bytes([0xA5])*12
            failed,writes=m.consume();self.assertFalse(failed)
            expected=[]
            for bank in ('SAME_SCUMM_VARIABLES','SAME_SCUMM_M23B_VARIABLES'):
                address=m.symbols[bank];expected.extend((address+4,address+5))
                self.assertEqual(m.ram[address:address+12],bytes([0xA5])*4+x.to_bytes(2,'little')+bytes([0xA5])*6)
            self.assertEqual(sorted(writes),sorted(expected))
        frame=source.split('ScummV5_Engine_Frame:',1)[1]
        self.assertLess(frame.index('jsr ScummV5_PublishCameraPosition'),frame.index('jsl ScummV5_QueueSentence'))
