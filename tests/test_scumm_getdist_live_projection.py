"""Distance must share live walkbox projection with walking, not cooked hints.

The instruction runner checks the actual native query branch. Geometry is the
existing host oracle here; native geometry retains its separate controls.
"""
from dataclasses import replace
import unittest
from same.engines.scumm_v5.engine import ActorState, RoomObjectState
from same.engines.scumm_v5.room import ScummV5Walkbox
import test_scumm_v5_engine as conformance
from test_scumm_camera_native_copy import StripMachine, ROOT


class LiveDistanceTests(unittest.TestCase):
    def fixture(self):
        h=conformance.ScummV5EngineTests()._host(bytes((0x30,1,2,0x80,0x80)))
        h.engine.state.actors[1]=ActorState(room=0,position=(20,40))
        h.engine.state.room_objects[20]=RoomObjectState(20,18,5,4,4,20,10)
        owners=bytearray(h.engine._object_owners);owners[20]=15;h.engine._object_owners=bytes(owners)
        sentinel=ScummV5Walkbox(0,(0,0),(0,0),(0,0),(0,0),0,0,255)
        ground=ScummV5Walkbox(1,(0,40),(40,40),(40,60),(0,60),0,0,255)
        raised=ScummV5Walkbox(2,(10,0),(30,0),(30,20),(10,20),0,0,255)
        h.engine._video.room=replace(h.engine._video.room,walkboxes=(sentinel,ground,raised))
        return h

    def native_query(self,h,first=1,second=20):
        m=StripMachine();m.code=[];m.labels={};m.service_writes=[]
        s=(ROOT/'runtime/snes/engines/scumm_v5_matrix_far.pasm').read_text()
        s=s.split('ScummV5_GetDist_FarEntry__second_resolved:',1)[1].split('ScummV5_GetDist_FarEntry__operand_error:',1)[0]
        s=s.replace('jml ScummV5_Engine_Frame__next','rtl').replace('brl ','bra ')
        for raw in s.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        calls=[]
        def service(name,p,a):
            calls.append(name)
            if name=='ScummV5_PutActor_Adjust_Far':
                xy,_=h.engine._video.room.adjust_actor_point_v5(m.get('SAME_SCUMM_PUT_ACTOR_REQUEST_X'),m.get('SAME_SCUMM_PUT_ACTOR_REQUEST_Y'))
                m.put('SAME_SCUMM_PUT_ACTOR_RESULT_X',xy[0]);m.put('SAME_SCUMM_PUT_ACTOR_RESULT_Y',xy[1])
            else:self.assertEqual(name,'ScummV5_GetActorFacing_FarCall_WriteResult')
            return p,a
        m.service=service
        (x1,y1),_=h.engine._object_or_actor_position(first)
        (x2,y2),_=h.engine._object_or_actor_position(second)
        for key,val in [('OPERAND1',first),('OPERAND2',second),('X1',x1),('Y1',y1),('X2_RAW',x2),('Y2_RAW',y2),('X2',20),('Y2',10)]:m.put('SAME_SCUMM_GET_DIST_'+key,val)
        m.put('SAME_SCUMM_GET_DIST_ADJUSTED',2,1) # obsolete cooker hint deliberately poisoned
        m.put(m.symbols['SAME_SCUMM_C14_ACTORS']+64+m.symbols['SAME_SCUMM_C14_A_IGNORE_BOXES'],int(h.engine.state.actors[1].ignore_boxes),1)
        m.consume()
        self.assertEqual(m.get('SAME_SCUMM_GET_DIST_RESULT'),h.engine._object_actor_distance(first,second))
        return m.get('SAME_SCUMM_GET_DIST_RESULT'),calls

    def test_matrix_change_moves_walk_target_and_reach_test_together(self):
        h=self.fixture();self.assertEqual(self.native_query(h)[0],30)
        h.tick() # original matrixOps contract hides the raised walkbox
        h.engine._start_actor_walk(h.engine.state.actors[1],(20,10))
        self.assertEqual(h.engine.state.actors[1].moving,0) # already at live normalized target
        self.assertEqual(self.native_query(h)[0],0)
        self.assertEqual(h.engine.state.room_objects[20].walk_y,10) # raw resource unchanged

    def test_ignore_boxes_and_reversed_operands_do_not_project(self):
        h=self.fixture();h.tick();h.engine.state.actors[1].ignore_boxes=True
        value,calls=self.native_query(h);self.assertEqual(value,30)
        self.assertNotIn('ScummV5_PutActor_Adjust_Far',calls)
        h.engine.state.actors[1].ignore_boxes=False
        value,calls=self.native_query(h,20,1);self.assertEqual(value,30)
        self.assertNotIn('ScummV5_PutActor_Adjust_Far',calls)
