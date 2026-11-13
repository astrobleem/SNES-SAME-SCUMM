"""Execute the production 65816 phase/origin source; this is NOT Nexen evidence."""
from pathlib import Path
import random
import unittest
from same.engines.scumm_v5.room import _scaled_cel_origin, _COSTUME_SCALE_TABLE
from test_scumm_v5_actor_damage_boundaries import ControllerMachine

ROOT = Path(__file__).resolve().parents[1]
C = 'SAME_SCUMM_CEL_'

class CelMachine(ControllerMachine):
    def __init__(self):
        super().__init__([])
        self.code, self.labels = [], {}
        raw = (ROOT/'runtime/snes/engines/scumm_v5_actor_cels.inc.pasm').read_text()
        for line in raw.splitlines():
            line = line.split(';',1)[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]] = len(self.code)
            else:self.code.append(line)

    def operand(self, arg):
        if arg == 'ScummV5_Cel_ScaleTable,x':
            return _COSTUME_SCALE_TABLE[self.x]
        return super().operand(arg)


class CelMath(unittest.TestCase):
    def test_retained_camera_exposes_clipped_cels_without_invalidating_in_view_poses(self):
        cases = ((390,410,8,False), (258,280,8,True), (-12,20,-8,True),
                 (40,80,8,False), (40,80,-8,False), (-30,-12,-8,False),
                 (-30,-4,-8,True), (-12,20,8,False), (248,270,-8,False),
                 (0x7fff,0x8000,8,False))
        for left,right,delta,invalidate in cases:
            m=CelMachine();m.mem.update({C+'BOUND_LEFT':left&65535,
                C+'BOUND_RIGHT':right&65535,'MODE3_R_DELTA':delta&65535,
                'SAME_SCUMM_CONTROLLER_RENDER_VALID':1,
                'SAME_SCUMM_CONTROLLER_RENDER_VISIBLE':1})
            m.run('ScummV5_Cel_CameraCommitted_Far')
            self.assertEqual(m.mem['SAME_SCUMM_CONTROLLER_RENDER_VALID'],int(not invalidate),
                             (left,right,delta))
            if left!=0x7fff:
                self.assertEqual(m.mem[C+'BOUND_LEFT'],(left-delta)&65535)
                self.assertEqual(m.mem[C+'BOUND_RIGHT'],(right-delta)&65535)

    def test_camera_cannot_publish_between_checked_actor_chunks(self):
        from test_scumm_v5_actor_damage_boundaries import camera_source
        text=(ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text()
        text=text.split('ScummV5_Camera_ServiceForeground_Far:',1)[1].split('ScummV5_Camera_ServicePending__retained_commit:',1)[0]
        text=camera_source(text,True,True)
        class ForegroundMachine(CelMachine):
            def service(self,name):
                self.calls.append(name)
                self.c=False
        for incomplete in (0,1):
            m=ForegroundMachine();m.code=[];m.labels={'entry':0};m.calls=[]
            for raw in text.splitlines():
                line=raw.split(';',1)[0].strip()
                if not line or line.startswith('.'):continue
                if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                else:m.code.append(line)
            m.mem.update({'SAME_SCUMM_VIEWPORT_ACTOR_SERVED':2,C+'VALID':incomplete,
                          'SAME_SCUMM_ACTOR_POSE_STATE':0})
            m.run('entry',preserve_a=False)
            self.assertIn('ScummV5_Controller_RenderActor_Far',m.calls)
            self.assertEqual('ScummV5_Camera_ServicePending_Far' in m.calls,not incomplete)
            self.assertEqual(m.mem['SAME_SCUMM_VIEWPORT_ACTOR_SERVED'],2 if incomplete else 1)

    def test_phase_table_matches_source_reference(self):
        s=(ROOT/'runtime/snes/engines/scumm_v5_actor_cels.inc.pasm').read_text()
        rows=s.split('ScummV5_Cel_ScaleTable:\n')[1].split('; Read')[0]
        values=bytes(int(t.strip().lstrip('$'),16) for line in rows.splitlines()
                     if '.byte' in line for t in line.split('.byte')[1].split(','))
        self.assertEqual(values,_COSTUME_SCALE_TABLE)

    def test_native_origin_source_matches_host_random_scales_and_signed_offsets(self):
        rng=random.Random(231)
        for i in range(1000):
            foot=(rng.randrange(-20,300),rng.randrange(-20,240))
            offset=(rng.randrange(-150,150),rng.randrange(-150,150))
            sx,sy=((255,255),(231,231),(255,128),(128,255),(0,0))[i%5] if i<100 else (rng.randrange(256),rng.randrange(256))
            right=bool(rng.randrange(2))
            m=CelMachine()
            m.mem.update({C+'TICKET_SCALE':sx|sy<<8,C+'DIRECTION':int(right),
                          C+'RX':offset[0]&65535,C+'RY':offset[1]&65535,
                          'SAME_SCUMM_ACTOR_FOOT_SCREEN_X':foot[0]&65535,
                          'SAME_SCUMM_ACTOR_FOOT_SCREEN_Y':foot[1]&65535})
            m.run('ScummV5_Cel_Origin_Far')
            expected=(foot[0]+(offset[0] if right else -offset[0]),foot[1]+offset[1],128,128) if sx==sy==255 else _scaled_cel_origin(*foot,*offset,sx,sy,right)
            self.assertFalse(m.c)
            self.assertEqual(tuple(m.mem[C+k] for k in ('ORIGIN_X','ORIGIN_Y','PHASE_X','PHASE_Y')),
                             tuple(v&65535 for v in expected),(foot,offset,sx,sy,right))

    def test_signed_overflow_fails(self):
        m=CelMachine();m.mem.update({C+'TICKET_SCALE':65535,C+'DIRECTION':1,C+'RX':1,C+'RY':0,
                                    'SAME_SCUMM_ACTOR_FOOT_SCREEN_X':32767,
                                    'SAME_SCUMM_ACTOR_FOOT_SCREEN_Y':0})
        m.run('ScummV5_Cel_Origin_Far');self.assertTrue(m.c)

class CelComposeMachine(CelMachine):
    def operand(self, arg):
        if arg == 'SAME_SCUMM_ACTOR_POSE_BUFFER,x':
            assert 0 <= self.x < len(self.pixels), 'read outside verified chunk'
            return self.pixels[self.x]
        return super().operand(arg)

    def __init__(self, plan, scale=(231,231), foot=(100,120), chunk_size=2048):
        super().__init__()
        self.plan = plan
        self.chunks = plan.chunks(chunk_size)
        self.mem.update({C+'TICKET_SCALE':scale[0]|scale[1]<<8,C+'DIRECTION':int(plan.draw_to_right),
                         C+'FIRST':0,C+'COUNT':len(plan.cels),C+'CHUNK':0,C+'TOTAL_BYTES':len(plan.data),
                         'SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH':7,'SAME_VIDEO_SURFACE_ROOM_GENERATION':7,
                         'SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH':3,'SAME_SCUMM_ACTOR_POSE_GENERATION':3,
                         'SAME_SCUMM_CONTROLLER_DESIRED_X':foot[0]&65535,
                         'SAME_SCUMM_CONTROLLER_DESIRED_Y':foot[1]&65535,
                         'SAME_SCUMM_ACTOR_CHUNK_COUNT':len(self.chunks)})
        self.all_spans = [span for cel in plan.cels for span in cel.spans]
        for name in ('ScummV5_Cel_Load_Far','ScummV5_Cel_Span_Far'):
            del self.labels[name]  # ROM metadata reads are service inputs, scaling executes real source.

    def service(self, name):
        if name == 'Same_VideoSurface_WriteIndexedPixel_Far':
            assert self.writable and self.committed
            assert 0 <= self.x < 256 * 224
            assert any(a <= self.x < a+n for a,n,_ in self.captures)
            self.events.append('draw')
            self.draws.append((self.x, 1, self.a & 255))
            self.surface[self.x] = self.a & 255
        elif name == 'ScummV5_Cel_Load_Far':
            n=self.mem[C+'CURSOR'];cel=self.plan.cels[n]
            for k,a in (('WIDTH','width'),('HEIGHT','height'),('RX','relative_x'),('RY','relative_y'),('MX','move_x'),('MY','move_y')):
                self.mem[C+k]=getattr(cel,a)&65535
            for axis in ('X','Y'):
                self.mem[C+'R'+axis]=(self.mem[C+'R'+axis]+self.mem[C+'CUM_'+axis])&65535
            self.mem[C+'CUM_X']=(self.mem[C+'CUM_X']+cel.move_x)&65535
            self.mem[C+'CUM_Y']=(self.mem[C+'CUM_Y']-cel.move_y)&65535
            self.mem['SAME_SCUMM_ACTOR_SPAN_FIRST']=sum(len(c.spans) for c in self.plan.cels[:n])
            self.mem['SAME_SCUMM_ACTOR_SPAN_COUNT']=len(cel.spans)
            self.c=False
        elif name == 'ScummV5_Cel_Span_Far':
            span=self.all_spans[self.mem['SAME_SCUMM_ACTOR_SPAN_CURSOR']]
            for k,a in (('X','x'),('Y','y'),('SOURCE','offset'),('LENGTH','length')):
                self.mem['SAME_SCUMM_ACTOR_SPAN_'+k]=getattr(span,a)
            self.c=False
        else:super().service(name)

    def compose(self):
        offset=0
        for chunk in self.chunks or [None]:
            self.mem[C+'CHUNK_OFFSET']=offset
            self.pixels=bytes(self.plan.palette[b] for b in chunk.data) if chunk else b''
            self.mem['SAME_SCUMM_ACTOR_TICKET_LENGTH']=len(self.pixels)
            self.run('ScummV5_Cel_Compose_Far')
            offset+=len(self.pixels)
        return self


class CelPixels(unittest.TestCase):
    def test_chunked_scaling_skips_unowned_spans_and_preserves_write_gate(self):
        from types import SimpleNamespace
        from same.engines.scumm_v5.costume import CostumeCel
        from tools.actor_pose_plan import compile_cel_pose
        pose = SimpleNamespace(cels=(CostumeCel(32, 64, -16, -64, 0, 0,
                                              bytes([1] * 2048)),), draw_to_right=True)
        plan = compile_cel_pose(pose, (0, 0))
        single = CelComposeMachine(plan, chunk_size=2048).compose()
        split = CelComposeMachine(plan, chunk_size=128).compose()
        self.assertEqual(split.surface, single.surface)
        self.assertEqual(len(split.draws), len(single.draws))
        # Directory checks may repeat, but pixel projection must not grow
        # sixteenfold with the number of individually checked transfers.
        self.assertLess(split.instructions, single.instructions * 3)
        for reason in ('busy', 'room', 'costume', 'capture'):
            m = CelComposeMachine(plan)
            if reason == 'busy': m.writable = False
            elif reason == 'room': m.mem['SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH'] += 1
            elif reason == 'costume': m.mem['SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH'] += 1
            else: m.fail_capture = 1
            m.compose()
            self.assertTrue(m.c, reason)
            self.assertEqual(m.surface, m.original, reason)
            self.assertEqual(m.draws, [], reason)

    def test_hidden_actor_needs_no_stale_cel_resource_or_ticket(self):
        m = CelMachine()
        m.mem.update(SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE=0,
                     SAME_SCUMM_CEL_DESIRED_SCALE=0xE7E7,
                     SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH=999)
        m.run('ScummV5_Cel_Compose_Far')
        self.assertFalse(m.c)
        self.assertEqual(m.surface, m.original)
        self.assertEqual(m.mem['SAME_SCUMM_ACTOR_POSE_COMPOSED'], 1)
        self.assertEqual(m.mem['SAME_SCUMM_CEL_TICKET_SCALE'], 0xE7E7)
        self.assertEqual(m.events, ['release'])
        self.assertEqual(m.captures, [])
        self.assertEqual(m.draws, [])

    def host_pixels(self, pose, palette, scale, foot, background):
        from types import SimpleNamespace
        from unittest.mock import patch
        from same.engines.scumm_v5.room import ScummV5RoomAdapter
        from same.engines.scumm_v5.engine import ActorState
        from same.video import IndexedSurface
        services=SimpleNamespace(resources=SimpleNamespace(contains=lambda k: True),
                                 resource_read=lambda k:b'',debug=SimpleNamespace(marker=lambda *args:None))
        adapter=ScummV5RoomAdapter(SimpleNamespace(services=services))
        adapter.room=SimpleNamespace(width=256,height=224,zplanes=[],walkboxes=[])
        adapter.backdrop_surface=IndexedSurface.wrap(256,224,256,background)
        adapter.logical_surface=IndexedSurface(256,224)
        costume=SimpleNamespace(palette=palette,decode_pose=lambda *args,**kw:pose)
        actor=ActorState(costume=1,room=1,visible=True,position=foot,scale=scale)
        with patch('same.engines.scumm_v5.room.ScummV5Costume',return_value=costume):
            adapter.render_actors({1:actor},current_room=1,costume_key=lambda n:'costume.1',project=False)
        return bytes(adapter.logical_surface.pixels)

    def test_production_compositor_source_matches_host_complete_surface(self):
        from types import SimpleNamespace
        from same.engines.scumm_v5.costume import CostumeCel
        from tools.actor_pose_plan import compile_cel_pose
        rng=random.Random(0x231255)
        for i in range(80):
            cels=tuple(CostumeCel(w,h,rng.randrange(-10,10),rng.randrange(-15,5),
                                  rng.randrange(-4,4),rng.randrange(-4,4),
                                  bytes(rng.randrange(4) for _ in range(w*h)))
                       for w,h in ((rng.randrange(1,12),rng.randrange(1,12)) for _ in range(rng.randrange(1,5))))
            pose=SimpleNamespace(cels=cels,draw_to_right=bool(i%2))
            scale=((255,255),(231,231),(128,231),(255,64),(64,255),(0,0),(1,1),(200,90))[i%8]
            foot=((100,120),(0,2),(254,221),(256,230))[i%4]
            palette=(0,0,128,255)
            plan=compile_cel_pose(pose,palette)
            m=CelComposeMachine(plan,scale,foot,chunk_size=37).compose()
            self.assertFalse(m.c,(i,m.mem))
            self.assertEqual(bytes(m.surface),self.host_pixels(pose,palette,scale,foot,m.original),(i,scale,foot))
            for a,n,old in m.captures:m.surface[a:a+n]=old
            self.assertEqual(bytes(m.surface),m.original)

    def test_real_decoder_cels_at_231_and_255(self):
        from same.engines.scumm_v5.costume import ScummV5Costume
        from test_scumm_v5_costume import rectangular_costume
        from tools.actor_pose_plan import compile_cel_pose
        costume=ScummV5Costume(rectangular_costume(),key='synthetic')
        for facing in (0,90,180,270):
            pose=costume.decode_pose(1,facing=facing,step=0)
            for scale in ((231,231),(255,255),(99,203)):
                plan=compile_cel_pose(pose,costume.palette)
                m=CelComposeMachine(plan,scale,chunk_size=7).compose()
                self.assertFalse(m.c)
                self.assertEqual(bytes(m.surface),self.host_pixels(pose,costume.palette,scale,(100,120),m.original))
