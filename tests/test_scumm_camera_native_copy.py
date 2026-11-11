"""Execute the native verified-strip copy leaf against independent crop pixels.

This narrow instruction runner is host evidence, not emulator acceptance.
"""
import re
import unittest
from pathlib import Path
from test_video_surface_sparse_underlay import ServiceMachine, ROOT
from test_scumm_v5_room_visual import fixture
from same.engines.scumm_v5.room_visual import camera_viewport, decode_room_visual, encode_camera_room_visual


class StripMachine(ServiceMachine):
    def __init__(self):
        super().__init__()
        self.symbols.update(SAME_SCUMM_LIVE_ROOM_PENDING_BASE=0x4013C4,
                            SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE=0x410000)
        text=(ROOT/'runtime/snes/engines/scumm_v5_msu_live_room.pasm').read_text()
        for name,expr in re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+)',text,re.M):
            try:self.symbols[name]=self.value(expr)
            except (NameError,SyntaxError):pass
        text=(ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text()
        text=text.split('ScummV5_Camera_ConsumeStrip_Far:',1)[1].split('ScummV5_Camera_InstallGeometry_Far:',1)[0]
        self.code=[];self.labels={}
        for line in text.splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.code)
            else:self.code.append(line)
        self.ram[0x410000:0x41E000]=bytes(57344)

    def consume(self):
        a=x=y=pc=0;p=0;stack=[];written=[];returns=[]
        cache={}
        def value(expr):
            if expr not in cache:cache[expr]=self.value(expr)
            return cache[expr]
        for _ in range(400000):
            op,_,arg=self.code[pc].partition(' ');pc+=1
            bits=8 if p&32 else 16;mask=(1<<bits)-1;v=addr=None;result=None
            if arg.startswith('#'):v=value(arg[1:])
            elif arg.endswith(',s'):
                flat=[]
                for item,width in stack:
                    if width==16:flat.append((item>>8)&255)
                    flat.append(item&255)
                n=int(arg[:-2]);v=flat[-n]|((flat[-n-1]<<8) if bits==16 else 0)
            elif '.l' in op:
                addr=value(arg.removesuffix(',x'))+(x if arg.endswith(',x') else 0)
                v=self.get(addr,bits//8)
            if op=='rep':p&=~v
            elif op=='sep':p|=v
            elif op in ('lda','lda.l'):result=v
            elif op=='sta.l':self.put(addr,a&mask,bits//8);written.extend(range(addr,addr+bits//8))
            elif op=='clc':p&=~1
            elif op=='sec':p|=1
            elif op in ('adc','adc.l'):
                result=(a&mask)+v+(p&1);p=(p&~1)|int(result>mask)
            elif op in ('sbc','sbc.l'):
                result=(a&mask)-v-(not p&1);p=(p&~1)|int(result>=0)
            elif op in ('cmp','cmp.l'):
                delta=(a&mask)-v;p=(p&~0x83)|int(delta>=0)|(2 if delta==0 else 0)|(128 if delta&(1<<(bits-1)) else 0)
            elif op=='asl':result=(a&mask)<<1
            elif op=='lsr':
                p=(p&~1)|(a&1);result=(a&mask)>>1
            elif op in ('eor','eor.l'):result=(a&mask)^v
            elif op=='and':result=(a&mask)&v
            elif op=='inc':result=(a&mask)+1
            elif op=='dec':result=(a&mask)-1
            elif op=='xba':result=((a&255)<<8)|(a>>8)
            elif op=='ldx':x=v
            elif op=='cpx':
                delta=x-v;p=(p&~0x83)|int(delta>=0)|(2 if delta==0 else 0)|(128 if delta&32768 else 0)
            elif op=='txa':result=x
            elif op=='tax':x=a&65535
            elif op=='tay':y=a&65535
            elif op=='tyx':x=y
            elif op=='inx':x=(x+1)&65535
            elif op=='iny':y=(y+1)&65535
            elif op=='php':stack.append((p,8))
            elif op=='plp':p,width=stack.pop();assert width==8
            elif op=='pha':stack.append((a,bits))
            elif op=='pla':result,width=stack.pop();assert width==bits
            elif op=='phy':stack.append((y,16))
            elif op=='ply':y,width=stack.pop();assert width==16
            elif op=='phx':stack.append((x,16))
            elif op=='plx':x,width=stack.pop();assert width==16
            elif op=='jsl':
                if arg in self.labels:returns.append(pc);pc=self.labels[arg]
                else:p,a=self.service(arg,p,a);written.extend(self.service_writes);self.service_writes=[]
            elif op in ('beq','bne','bcc','bcs','bpl','bmi','bra','jmp'):
                take={'beq':bool(p&2),'bne':not p&2,'bcc':not p&1,'bcs':bool(p&1),'bpl':not p&128,'bmi':bool(p&128),'bra':True,'jmp':True}[op]
                if take:pc=self.labels[arg]
            elif op in ('rtl','rts'):
                if returns:pc=returns.pop();continue
                assert not stack
                return bool(p&1),written
            else:raise AssertionError((op,arg))
            if result is not None:
                a=(a&~mask)|(result&mask);p=(p&~0x82)|(2 if a&mask==0 else 0)|(128 if a&(1<<(bits-1)) else 0)
        raise AssertionError('unbounded strip copy')


class NativeStripCopyTests(unittest.TestCase):
    def test_all_eight_camera_alignments_and_room_edges(self):
        for w,h in ((13,5),(640,144),(1280,200)):
            raw=fixture(width=w,height=h,pitch=w);v=decode_room_visual(raw);packed,ds=encode_camera_room_visual(raw)
            for xs in (-100,0,1,2,3,4,5,6,7,w):
                m=StripMachine();want,g=camera_viewport(v,xstart=xs)
                for key,value in g.items():m.put('SAME_SCUMM_VIEWPORT_'+key.upper().replace('COPY_',''),value)
                first=g['source_x']//8;last=(g['source_x']+g['copy_width']+7)//8
                m.put('SAME_SCUMM_VIEWPORT_LAST',last)
                m.put('SAME_SCUMM_VIEWPORT_STRIP_BYTES',h*8)
                m.put('SAME_MSU1_REQUEST_LENGTH',h*8)
                for index in range(first,last):
                    d=ds[index];m.ram[0x4013C4:0x4013C4+d['length']]=packed[d['offset']:d['offset']+d['length']]
                    m.put('SAME_SCUMM_VIEWPORT_STRIP',index)
                    failed,writes=m.consume();self.assertFalse(failed)
                    for address in writes:
                        if 0x410000<=address<0x420000:self.assertLess(address,0x410000+192*256)
                self.assertEqual(m.ram[0x410000:0x41E000],want)
                self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),2)

    def test_wrong_checked_length_cannot_touch_stage(self):
        m=StripMachine();m.put('SAME_SCUMM_VIEWPORT_STRIP_BYTES',1600);m.put('SAME_MSU1_REQUEST_LENGTH',1599)
        failed,writes=m.consume();self.assertTrue(failed);self.assertEqual(writes,[])


class CameraTransactionMachine(StripMachine):
    def __init__(self):
        super().__init__()
        self.symbols['SAME_VIDEO_SCENE_BOTTOM']=192
        self.symbols['SAME_VIDEO_CURSOR_UNDERLAY']=0x400620
        text=(ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text()
        text=text.split('ScummV5_Camera_ServicePending_Far:',1)[1].split('ScummV5_Camera_Invalid_Far:',1)[0]
        self.code=[];self.labels={};self.calls=[];self.service_writes=[];self.queue_busy=False
        for line in text.splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.code)
            else:self.code.append(line)
    def service(self,name,p,a):
        self.calls.append(name)
        if name=='Same_VideoSurface_PushDirtyPresent_Far':
            from test_video_surface_publication import PublicationMachine
            guard=PublicationMachine()
            guard.put('SAME_SCUMM_VIEWPORT_STATE',self.get('SAME_SCUMM_VIEWPORT_STATE',1),1)
            allowed=guard.can_write()
            return (p&~1)|int(self.queue_busy or not allowed),a
        if name in ('Same_VideoSurface_InvalidateTileCache_Far',
                    'Same_VideoSurface_InvalidateActorUnderlay_Far',
                    'ScummV5_Camera_InstallGeometry_Far'):
            return p,a
        raise AssertionError('unexpected service '+name)


class CameraTransactionTests(unittest.TestCase):
    def test_incoming_lifecycle_never_publishes_camera_pixels(self):
        for phase in range(1,7):
            for state in range(4):
                m=CameraTransactionMachine()
                m.put('SAME_SCUMM_M23A_PHASE',phase,1)
                m.put('SAME_SCUMM_VIEWPORT_STATE',state,1)
                m.put('SAME_SCUMM_VIEWPORT_MODE',1,1)
                failed,writes=m.consume()
                self.assertFalse(failed);self.assertEqual(writes,[]);self.assertEqual(m.calls,[])

    def test_initial_room_checked_stage_is_not_a_camera_commit(self):
        m=CameraTransactionMachine();m.put('SAME_SCUMM_VIEWPORT_STATE',2,1)
        failed,writes=m.consume();self.assertFalse(failed);self.assertEqual(writes,[]);self.assertEqual(m.calls,[])

    def test_queue_backpressure_retains_published_surface_without_recopied_stage(self):
        m=CameraTransactionMachine();m.put('SAME_SCUMM_VIEWPORT_STATE',2,1)
        m.put('SAME_SCUMM_VIEWPORT_MODE',1,1);m.put('SAME_VIDEO_SURFACE_PENDING_VISUAL',1,1)
        m.queue_busy=True
        m.ram[0x410000:0x41C000]=bytes([19])*49152
        failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),3)
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_PENDING_VISUAL',1),1)
        self.assertEqual(m.ram[0x402000:0x40E000],bytes([19])*49152)
        m.ram[0x410000:0x41C000]=bytes([99])*49152
        m.calls=[];m.queue_busy=False
        failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(m.calls,['Same_VideoSurface_PushDirtyPresent_Far'])
        self.assertEqual(m.ram[0x402000:0x40E000],bytes([19])*49152)
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),0)
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_PENDING_VISUAL',1),1)

    def test_video_guard_requires_explicit_completed_owner_handoff(self):
        m=CameraTransactionMachine();m.put('SAME_SCUMM_VIEWPORT_STATE',3,1)
        m.put('SAME_SCUMM_VIEWPORT_MODE',1,1)
        # Exercise the actual video CanWrite reader at the service boundary.
        self.assertEqual(m.service('Same_VideoSurface_PushDirtyPresent_Far',0,0)[0]&1,1)
        m.calls=[];failed,writes=m.consume()
        self.assertFalse(failed);self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),0)
        self.assertEqual(m.calls,['Same_VideoSurface_PushDirtyPresent_Far'])
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_PENDING_VISUAL',1),1)
        self.assertFalse(any(0x402000<=a<0x41E000 for a in writes))

    def test_completed_crop_does_not_acknowledge_a_newer_camera_request(self):
        for installed,expected_request in ((208,0),(56,1)):
            m=CameraTransactionMachine();m.put('SAME_SCUMM_VIEWPORT_STATE',3,1)
            m.put('SAME_SCUMM_VIEWPORT_MODE',1,1)
            m.put('SAME_VIDEO_SURFACE_SOURCE_X',installed)
            m.put('SAME_VIDEO_SURFACE_PENDING_XSTART',176)
            m.put('SAME_VIDEO_SURFACE_WIDTH',640);m.put('SAME_VIDEO_SURFACE_COPY_WIDTH',256)
            m.put('SAME_MSU1_STATUS',3,1);m.put('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT',255,1)
            m.symbols.update(SAME_MSU1_STATE_READING=4,SCUMM_LIVE_ROOM_STAGE_PIXELS=4,SCUMM_MSU_ROOM_REQUESTED=1)
            m.consume();self.assertEqual(m.get('SAME_VIDEO_SURFACE_PENDING_VISUAL',1),1)
            prior=m.service
            def service(name,p,a):
                if name in ('Same_VideoSurface_CanWrite_Far','ScummV5_MsuProgram_ReconcileRead_Far'):return p&~1,a
                return prior(name,p,a)
            m.service=service;m.consume()
            self.assertEqual(m.get('SAME_VIDEO_SURFACE_PENDING_VISUAL',1),expected_request)
            self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),expected_request)

    def test_memory_audit_rejects_original_lifecycle_trace_alias(self):
        from unittest.mock import patch
        import audit_scumm_residency_wram as audit
        original=audit.symbols()
        self.assertEqual(audit.audit()['result'],'pass')
        bad=dict(original)
        for key in original:
            if key.startswith('SAME_SCUMM_VIEWPORT_'):
                bad[key]=original[key]-0x7E8FC0+0x7E5ED8
        with patch.object(audit,'symbols',return_value=bad):
            with self.assertRaisesRegex(ValueError,'overlap'):
                audit.audit()


class CameraRoomPreemptionTests(unittest.TestCase):
    def machine(self):
        m=CameraTransactionMachine()
        source=(ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text()
        source=source.split('ScummV5_Camera_YieldToRoom_Far:',1)[1]
        m.code=[];m.labels={}
        for raw in source.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        m.symbols.update(SAME_MSU1_STATE_READING=4,SAME_MSU1_STATE_ERROR=255)
        def service(name,p,a):
            m.calls.append(name)
            if name not in ('Same_VideoSurface_InvalidateTileCache_Far',
                            'ScummV5_MsuRoom_Request_Far','ScummV5_MsuRoom_Service_Far__fail'):
                raise AssertionError(name)
            return p,a
        m.service=service
        m.put('SAME_SCUMM_VIEWPORT_MODE',1,1);m.put('SAME_SCUMM_VIEWPORT_STATE',1,1)
        m.put('SAME_SCUMM_M23A_PHASE',4,1)
        return m

    def test_room_priority_drains_before_releasing_scratch(self):
        m=self.machine();m.put('SAME_MSU1_STATUS',4,1)
        waiting,writes=m.consume();self.assertTrue(waiting);self.assertEqual(writes,[])
        self.assertEqual(m.calls,[])
        m.put('SAME_MSU1_STATUS',5,1)
        waiting,writes=m.consume();self.assertFalse(waiting)
        self.assertEqual(m.calls,['Same_VideoSurface_InvalidateTileCache_Far','ScummV5_MsuRoom_Request_Far'])
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),0)
        self.assertFalse(any(0x402000<=a<0x410000 for a in writes))

    def test_failed_checked_camera_read_remains_explicit_failure(self):
        m=self.machine();m.put('SAME_MSU1_STATUS',255,1)
        waiting,writes=m.consume();self.assertTrue(waiting);self.assertEqual(writes,[])
        self.assertEqual(m.calls,['ScummV5_MsuRoom_Service_Far__fail'])


class CameraCheckedReadAdmissionTests(unittest.TestCase):
    def machine(self, status=5, failure=False, old=False):
        m=CameraTransactionMachine()
        m.symbols.update(SAME_MSU1_STATE_READING=4,SCUMM_LIVE_ROOM_STAGE_PIXELS=4,
                         SCUMM_MSU_ROOM_REQUESTED=1)
        if old:
            # Reproduce the original end-of-frame READ_OK ownership starvation.
            # Remove the entire new call/error branch, then rebuild labels.
            source=(ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text()
            source=source.split('ScummV5_Camera_ServicePending_Far:',1)[1].split('ScummV5_Camera_Invalid_Far:',1)[0]
            start=source.index('    jsl ScummV5_MsuProgram_ReconcileRead_Far')
            end=source.index('    lda.l SAME_MSU1_STATUS',start)
            source=source[:start]+source[end:]
            m.code=[];m.labels={}
            for raw in source.splitlines():
                line=raw.split(';')[0].strip()
                if not line or line.startswith('.') :continue
                if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                else:m.code.append(line)
        m.put('SAME_VIDEO_SURFACE_PENDING_XSTART',176)
        m.put('SAME_VIDEO_SURFACE_WIDTH',640)
        m.put('SAME_VIDEO_SURFACE_COPY_WIDTH',256)
        m.put('SAME_VIDEO_SURFACE_SOURCE_X',32)
        m.put('SAME_VIDEO_SURFACE_ROOM',17,1)
        m.put('SAME_MSU1_STATUS',status,1)
        m.put('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT',1,1)
        def service(name,p,a):
            m.calls.append(name)
            if name=='Same_VideoSurface_CanWrite_Far':return p&~1,a
            if name=='ScummV5_MsuProgram_ReconcileRead_Far':
                if failure:return p|1,a
                if status==5:m.put('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT',255,1)
                return p&~1,a
            raise AssertionError(name)
        m.service=service
        return m

    def test_completed_code_read_admits_camera_before_another_scheduler_turn(self):
        m=self.machine();failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(m.calls,['Same_VideoSurface_CanWrite_Far','ScummV5_MsuProgram_ReconcileRead_Far'])
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_MODE',1),1)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),1)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_ID',1),17)
        old=self.machine(old=True);old_failed,_=old.consume();self.assertFalse(old_failed)
        self.assertEqual(old.get('SAME_SCUMM_VIEWPORT_MODE',1),0)
        self.assertEqual(old.get('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT',1),1)

    def test_pending_or_failed_read_does_not_claim_camera(self):
        for status,failure in ((4,False),(3,False),(255,True)):
            m=self.machine(status,failure);failed,_=m.consume()
            self.assertEqual(failed,failure)
            self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_MODE',1),0)
            self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),0)
