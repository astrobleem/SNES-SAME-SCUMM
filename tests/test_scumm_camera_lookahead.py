"""Instruction-level ticket/ownership tests, separate from native evidence."""
import re
import unittest
from pathlib import Path
from test_scumm_camera_native_copy import StripMachine
ROOT=Path(__file__).resolve().parents[1]

class AheadMachine(StripMachine):
    def __init__(self):
        super().__init__()
        self.symbols.update(SAME_BWRAM_RETAINED_VIEWPORT=0x401084,
                            SAME_MODE3_CONTROL_STATE=0x40100e,
                            SAME_MODE3_CONTROL_CANDIDATE_COUNT=0x401022,
                            SAME_MODE3_STATE_QUEUEING=3, SAME_MODE3_STATE_COMPLETE=5)
        for file in ('runtime/snes/services/video_mode3_retained.inc.pasm','runtime/snes/services/storage_msu1.pasm'):
            p=ROOT/file
            if p.exists():
                for n,e in re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+)',p.read_text(),re.M):
                    try:self.symbols[n]=self.value(e)
                    except (NameError,SyntaxError):pass
        assert self.symbols["SAME_MSU1_STATE_READ_OK"] == 5
        self.code=[];self.labels={};self.calls=[];self.service_writes=[];self.accepted=False;self.failed=False
        source=(ROOT/'runtime/snes/engines/scumm_v5_camera_lookahead.inc.pasm').read_text()
        facade=(ROOT/'runtime/snes/services/video_surface.pasm').read_text()
        source+='\nSame_VideoSurface_PlanLookahead_Far:'+facade.split('Same_VideoSurface_PlanLookahead_Far:',1)[1].split('Same_VideoSurface_ComposeRetainedScroll_Far:',1)[0]
        for line in source.splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.code)
            elif line.startswith('jml '):self.code.extend(['jsl '+line[4:],'rtl'])
            else:self.code.append(line)
        self.put('SAME_SCUMM_VIEWPORT_STATE',4,1);self.put('SAME_SCUMM_VIEWPORT_MODE',1,1)
        self.put('MODE3_R_ACTIVE',1,1)
        self.put('SAME_MODE3_CONTROL_STATE',3,1)
        self.put('MODE3_R_NEXT',40);self.put('MODE3_R_CURRENT',32)
        self.put('MODE3_R_MAX',384);self.put('MODE3_R_FIRST',4);self.put('MODE3_R_LAST',35)
        self.put('SAME_VIDEO_SURFACE_PENDING_XSTART',24)
        self.put('SAME_SCUMM_ACTOR_SCRATCH_OWNER',2,1)
        self.put('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT',255,1)
        self.put('SAME_SCUMM_MSU_ROOM_STATE',3,1)
        self.put('SAME_MSU1_STATUS',3,1)
        self.put('SAME_SCUMM_VIEWPORT_STRIP',36);self.put('SAME_SCUMM_VIEWPORT_STRIP_BYTES',1152)
        self.put('SAME_VIDEO_SURFACE_ROOM',10,1);self.put('SAME_VIDEO_SURFACE_ROOM_GENERATION',21)
        self.put('SAME_VIDEO_SURFACE_NEXT_GENERATION',0x10005,4)
        self.put('MODE3_R_GENERATION',5);self.put('MODE3_R_GENERATION_HI',1)

    def run(self,entry):
        self.entry=self.labels['ScummV5_Camera_'+entry+'_Far'];return self.consume()

    def service(self,name,p,a):
        self.calls.append(name)
        if name=='ScummV5_Camera_BuildStripRequest_Far':
            for n,v,size in [('REQUEST_OFFSET',0x1000000+self.get('SAME_SCUMM_VIEWPORT_STRIP')*1152,4),('REQUEST_LENGTH',1152,4),('EXPECTED_CRC',0x12345678,4),('DESTINATION',0x4013C4,3)]:self.put('SAME_MSU1_'+n,v,size)
            p&=~1
        elif name=='Same_Msu1_ReadBegin_FarEntry':self.put('SAME_MSU1_STATUS',4,1);p&=~1
        elif name=='ScummV5_Camera_Invalid_Far':self.failed=True;p|=1
        elif name=='ScummV5_Camera_ConsumeStrip__length_ok':
            if getattr(self,'fail_install',False):p|=1
            else:self.accepted=True;p&=~1
        else:raise AssertionError(name)
        return p,a

    def ready(self):
        self.run('AheadService');assert self.get('SAME_SCUMM_CAMERA_AHEAD_STATE',1)==1
        self.put('SAME_MSU1_STATUS',5,1);self.run('AheadReconcile')
        self.put('MODE3_R_CURRENT',40);self.put('SAME_SCUMM_VIEWPORT_STRIP',37)

class AheadTests(unittest.TestCase):
    def test_request_is_checked_32bit_and_does_not_move_camera_or_change_strip(self):
        m=AheadMachine();m.run('AheadService')
        self.assertEqual(m.get('SAME_SCUMM_CAMERA_AHEAD_STATE',1),1)
        self.assertEqual(m.get('SAME_SCUMM_CAMERA_AHEAD_OFFSET',4),0x1000000+37*1152)
        self.assertEqual(m.get('SAME_SCUMM_CAMERA_AHEAD_GENERATION',4),0x10005)
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STRIP'),36)
        self.assertEqual(m.get('MODE3_R_CURRENT'),32)
        self.assertNotIn('ScummV5_Camera_ConsumeStrip__length_ok',m.calls)

    def test_no_speculation_while_conversion_or_foreground_owns_data(self):
        for key,v,size in [('SAME_MODE3_CONTROL_STATE',2,1),('SAME_MODE3_CONTROL_STATE',255,1),('SAME_MODE3_CONTROL_CANDIDATE_COUNT',1,2),('SAME_SCUMM_M23A_PHASE',4,1),('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT',0,1),('SAME_MSU1_STATUS',4,1),('SAME_SCUMM_ACTOR_SCRATCH_OWNER',1,1),('SAME_SCUMM_ACTOR_POSE_STATE',1,1),('MODE3_R_NEXT',41,2)]:
            with self.subTest(key=key):
                m=AheadMachine();m.put(key,v,size);m.run('AheadService')
                self.assertNotIn('Same_Msu1_ReadBegin_FarEntry',m.calls)

    def test_checked_completion_survives_other_provider_descriptor_after_acceptance(self):
        m=AheadMachine();m.ready();m.put('SAME_MSU1_REQUEST_LENGTH',7,4)
        m.run('AheadConsume');self.assertTrue(m.accepted);self.assertFalse(m.failed)
        self.assertEqual(m.get('SAME_SCUMM_CAMERA_AHEAD_HITS'),1)

    def test_checked_hit_installation_failure_is_an_error_not_a_read_retry(self):
        m=AheadMachine();m.ready();m.calls=[];m.fail_install=True
        m.run('AheadConsume')
        self.assertTrue(m.failed)
        self.assertFalse(m.accepted)
        self.assertNotIn('Same_Msu1_ReadBegin_FarEntry',m.calls)

    def test_crc_timeout_interruption_and_changed_request_never_publish(self):
        for key,v,size in [('SAME_MSU1_STATUS',255,1),('SAME_MSU1_REQUEST_OFFSET',0,4),('SAME_MSU1_REQUEST_LENGTH',1151,4),('SAME_MSU1_REQUEST_LENGTH+2',1,2),('SAME_MSU1_EXPECTED_CRC+2',0,2),('SAME_MSU1_DESTINATION',0x401bc4,3)]:
            m=AheadMachine();m.run('AheadService');m.put('SAME_MSU1_STATUS',5,1);m.put(m.value(key),v,size);m.run('AheadReconcile')
            self.assertTrue(m.failed,key);self.assertFalse(m.accepted)
            self.assertEqual(m.get('SAME_SCUMM_CAMERA_AHEAD_STATE',1),0)

    def test_room_epoch_full_generation_column_and_origin_are_independent_fences(self):
        for key,v,size in [('SAME_VIDEO_SURFACE_ROOM',11,1),('SAME_VIDEO_SURFACE_ROOM_GENERATION',22,2),('SAME_SCUMM_VIEWPORT_STRIP',3,2),('MODE3_R_CURRENT',32,2),('MODE3_R_GENERATION_HI',2,2),('MODE3_R_GENERATION',6,2),('SAME_SCUMM_VIEWPORT_STRIP_BYTES',1151,2)]:
            m=AheadMachine();m.ready();m.put(key,v,size);m.run('AheadConsume')
            self.assertFalse(m.accepted,key);self.assertFalse(m.failed)
            self.assertEqual(m.get('SAME_SCUMM_CAMERA_AHEAD_STATE',1),0)

    def test_actor_priority_cannot_release_writing_buffer(self):
        m=AheadMachine();m.run('AheadService');m.put('SAME_SCUMM_VIEWPORT_STATE',0,1);m.run('AheadRelease')
        self.assertEqual(m.get('SAME_SCUMM_ACTOR_SCRATCH_OWNER',1),2)
        m.put('SAME_MSU1_STATUS',5,1);m.run('AheadReconcile');m.run('AheadRelease')
        self.assertEqual(m.get('SAME_SCUMM_ACTOR_SCRATCH_OWNER',1),0)
        self.assertEqual(m.get('SAME_SCUMM_CAMERA_AHEAD_STATE',1),0)

    def test_cached_reverse_discards_ticket_before_reusing_pending_pixels(self):
        m=AheadMachine();m.ready()
        source=(ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text()
        source='    lda #$00\n'+source.split('    ; Admission has drained any provider write.',1)[1].split('    lda #$00\n',1)[1].split('ScummV5_Camera_Prepare__retained_read:',1)[0]
        m.code=[line.split(';')[0].strip() for line in source.splitlines() if line.strip() and not line.strip().startswith((';','.'))]
        m.entry=0;m.consume()
        self.assertEqual(m.get('SAME_SCUMM_CAMERA_AHEAD_STATE',1),0)
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),2)
        self.assertEqual(m.get('SAME_SCUMM_ACTOR_SCRATCH_OWNER',1),2)

    def test_room_request_preserves_camera_owner_until_existing_drain(self):
        m=AheadMachine();m.run('AheadService')
        before=bytes(m.ram)
        source=(ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text().split('ScummV5_MsuRoom_Request_Far:',1)[1].split('ScummV5_MsuRoom_Service_Far:',1)[0]
        m.code=[];m.labels={}
        for line in source.splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        m.entry=0;m.consume()
        self.assertEqual(bytes(m.ram),before)

    def test_no_reads_for_retained_columns_boundaries_or_stationary_target(self):
        for nxt,target,first,last in [(40,8,4,36),(40,-8,4,36),(0,-40,0,32),(384,400,48,79)]:
            m=AheadMachine();m.put('MODE3_R_NEXT',nxt);m.put('SAME_VIDEO_SURFACE_PENDING_XSTART',target&65535);m.put('MODE3_R_FIRST',first);m.put('MODE3_R_LAST',last);m.run('AheadService')
            self.assertNotIn('Same_Msu1_ReadBegin_FarEntry',m.calls)

if __name__=='__main__':unittest.main()
