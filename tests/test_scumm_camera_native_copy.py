"""Execute the native verified-strip copy leaf against independent crop pixels.

This narrow instruction runner is host evidence, not emulator acceptance.
"""
import re
import unittest
from pathlib import Path
from test_video_surface_sparse_underlay import ServiceMachine, ROOT
from test_scumm_v5_room_visual import fixture
from same.engines.scumm_v5.room_visual import camera_viewport, decode_room_visual, encode_camera_room_visual


def select_actor_path(text, enabled=False):
    """Honor the actual build conditional instead of executing both arms."""
    active=[True];arms=[];result=[]
    for line in text.splitlines():
        directive=line.strip()
        if directive == '.if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER':
            arms.append(enabled);active.append(active[-1] and enabled)
        elif directive == '.else':
            active[-1]=active[-2] and not arms[-1]
        elif directive == '.endif':
            active.pop();arms.pop()
        elif active[-1]:result.append(line)
    assert len(active)==1, 'unbalanced build conditional'
    return '\n'.join(result)


class StripMachine(ServiceMachine):
    def __init__(self):
        super().__init__()
        self.symbols.update(SAME_SCUMM_LIVE_ROOM_PENDING_BASE=0x4013C4,
                            SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE=0x410000)
        text=(ROOT/'runtime/snes/engines/scumm_v5_msu_live_room.pasm').read_text()
        for name,expr in re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+)',text,re.M):
            try:self.symbols[name]=self.value(expr)
            except (NameError,SyntaxError):pass
        text=select_actor_path((ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text(),getattr(self,'retained',False))
        text=text.split('ScummV5_Camera_ConsumeStrip_Far:',1)[1].split('ScummV5_Camera_InstallGeometry_Far:',1)[0]
        self.code=[];self.labels={}
        for line in text.splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.code)
            else:self.code.append(line)
        self.ram[0x410000:0x41E000]=bytes(57344)

    def consume(self):
        a=x=y=0;pc=getattr(self,"entry",0);p=0;stack=[];written=[];returns=[]
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
            elif op=='sep':
                p|=v
                if p&16:x&=255;y&=255
            elif op in ('lda','lda.l'):result=v
            elif op=='sta.l':self.put(addr,a&mask,bits//8);written.extend(range(addr,addr+bits//8))
            elif op=='sta' and arg.startswith('['):
                pointer=self.get(value(arg[1:arg.index(']')]),3)
                addr=pointer+y;self.put(addr,a&mask,bits//8);written.extend(range(addr,addr+bits//8))
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
            elif op=='ora.l':result=(a&mask)|v
            elif op=='inc':result=(a&mask)+1
            elif op=='dec':result=(a&mask)-1
            elif op=='xba':result=((a&255)<<8)|(a>>8)
            elif op=='ldx':x=v
            elif op=='ldy':y=v
            elif op in ('cpx','cpy'):
                delta=(x if op=='cpx' else y)-v;p=(p&~0x83)|int(delta>=0)|(2 if delta==0 else 0)|(128 if delta&32768 else 0)
            elif op=='txa':result=x
            elif op=='tya':result=y
            elif op=='tax':x=a&(255 if p&16 else 65535)
            elif op=='tay':y=a&(255 if p&16 else 65535)
            elif op=='tyx':x=y
            elif op=='inx':x=(x+1)&65535
            elif op=='iny':y=(y+1)&65535
            elif op=='dey':
                y=(y-1)&(255 if p&16 else 65535);p=(p&~0x82)|(2 if y==0 else 0)|(128 if y&(128 if p&16 else 32768) else 0)
            elif op=='dex':x=(x-1)&65535;p=(p&~0x82)|(2 if x==0 else 0)|(128 if x&32768 else 0)
            elif op=='php':stack.append((p,8))
            elif op=='plp':p,width=stack.pop();assert width==8
            elif op=='pha':stack.append((a,bits))
            elif op=='pla':result,width=stack.pop();assert width==bits
            elif op=='phy':stack.append((y,8 if p&16 else 16))
            elif op=='ply':y,width=stack.pop();assert width==(8 if p&16 else 16)
            elif op=='phx':stack.append((x,8 if p&16 else 16))
            elif op=='plx':x,width=stack.pop();assert width==(8 if p&16 else 16)
            elif op in ('jsl','jsr'):
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
        self.symbols.update(SCUMM_LIVE_ROOM_STAGE_PIXELS=4,SCUMM_MSU_ROOM_REQUESTED=1)
        self.put('SAME_SCUMM_VIEWPORT_ROOM_WIDTH',640)
        self.put('SAME_SCUMM_VIEWPORT_WIDTH',256)
        self.put('SAME_SCUMM_VIEWPORT_SOURCE_X',32)
        text=select_actor_path((ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text(),getattr(self,'retained',False))
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

    def test_superseded_checked_crop_never_enters_live_surface_or_video_queue(self):
        for pending,staged,latest in ((176,56,208),(-100,56,0),(999,56,384)):
            m=CameraTransactionMachine();m.put('SAME_SCUMM_VIEWPORT_STATE',2,1)
            m.put('SAME_SCUMM_VIEWPORT_MODE',1,1)
            m.put('SAME_SCUMM_VIEWPORT_SOURCE_X',staged)
            m.put('SAME_VIDEO_SURFACE_PENDING_XSTART',pending & 65535)
            m.put('SAME_VIDEO_SURFACE_SOURCE_X',32)
            m.ram[0x402000:0x40E000]=bytes([37])*49152
            m.ram[0x410000:0x41C000]=bytes([99])*49152
            def prepare(name,p,a):
                self.assertEqual(name,'ScummV5_Camera_Prepare_Far')
                self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),0)
                self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_TEMP'),max(0,pending+32))
                m.calls.append(name)
                m.put('SAME_SCUMM_VIEWPORT_SOURCE_X',latest)
                m.put('SAME_SCUMM_VIEWPORT_STATE',1,1)
                return p & ~1,a
            m.service=prepare;failed,writes=m.consume()
            self.assertFalse(failed)
            self.assertEqual(m.calls,['ScummV5_Camera_Prepare_Far'])
            self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),1)
            self.assertEqual(m.get('SCUMM_LIVE_ROOM_STAGE',1),4)
            self.assertEqual(m.get('SAME_VIDEO_SURFACE_SOURCE_X'),32)
            self.assertEqual(m.ram[0x402000:0x40E000],bytes([37])*49152)
            self.assertFalse(any(0x402000<=a<0x41E000 for a in writes))
            # Only the later fully validated crop may reach the live surface.
            m.put('SAME_SCUMM_VIEWPORT_STATE',2,1)
            m.service=lambda name,p,a: CameraTransactionMachine.service(m,name,p,a)
            m.consume()
            self.assertEqual(m.ram[0x402000:0x40E000],bytes([99])*49152)
            self.assertIn('Same_VideoSurface_PushDirtyPresent_Far',m.calls)

    def test_coalescing_backpressure_preserves_exclusive_staging_ownership(self):
        m=CameraTransactionMachine();m.put('SAME_SCUMM_VIEWPORT_STATE',2,1)
        m.put('SAME_SCUMM_VIEWPORT_MODE',1,1)
        m.put('SAME_VIDEO_SURFACE_PENDING_XSTART',176)
        m.service=lambda name,p,a:(p & ~1,a)  # Prepare could not acquire video.
        failed,writes=m.consume();self.assertFalse(failed)
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),2)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),0)
        self.assertFalse(any(0x402000<=a<0x41E000 for a in writes))

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
        source=select_actor_path((ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text())
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
            source=select_actor_path((ROOT/'runtime/snes/engines/scumm_v5_camera_stream.inc.pasm').read_text())
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

class RetainedCameraTransactionMachine(CameraTransactionMachine):
    retained = True

    def __init__(self):
        super().__init__()
        self.symbols.update(SAME_MODE3_CONTROL_SURFACE_LOCKED=0x401014,
                            SAME_BWRAM_CONTROL_COMMITTED_GENERATION=0x401010,
                            SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI=0x401018)
        self.put('SAME_SCUMM_VIEWPORT_STATE',2,1)
        self.put('SAME_SCUMM_VIEWPORT_MODE',1,1)
        self.put('SAME_SCUMM_ACTOR_SCRATCH_OWNER',1,1)
        self.put('SAME_VIDEO_SURFACE_SOURCE_X',32)
        self.put('SAME_SCUMM_VIEWPORT_SOURCE_X',40)
        self.put('SAME_VIDEO_SURFACE_WIDTH',640)
        self.put('SAME_VIDEO_SURFACE_COPY_WIDTH',256)
        self.put('SAME_VIDEO_SURFACE_PENDING_XSTART',8)
        self.labels['ScummV5_Camera_ServicePending_Far']=0
        self.put('SAME_VIDEO_SURFACE_NEXT_GENERATION',11)
        self.put('SAME_BWRAM_CONTROL_COMMITTED_GENERATION',10)

    def service(self,name,p,a):
        self.calls.append(name)
        if name=='Same_VideoSurface_CanWrite_Far':return p&~1,a
        if name=='Same_VideoSurface_CanPublishRetained_Far':
            return (p&~1)|int(self.queue_busy),a
        if name=='Same_VideoSurface_ComposeRetainedScroll_Far':
            self.assert_released = self.get('SAME_SCUMM_VIEWPORT_STATE',1)==0
            return p&~1,a
        if name=='Same_VideoSurface_ScrollPresented_Far':
            pending = (self.get('SAME_MODE3_CONTROL_SURFACE_LOCKED',1) or
                       self.get('SAME_VIDEO_SURFACE_NEXT_GENERATION') != self.get('SAME_BWRAM_CONTROL_COMMITTED_GENERATION') or
                       self.get(self.symbols['SAME_VIDEO_SURFACE_NEXT_GENERATION']+2) != self.get('SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI'))
            return (p&~1)|int(bool(pending)),a
        if name=='ScummV5_Camera_InstallGeometry_Far':
            self.put('SAME_VIDEO_SURFACE_SOURCE_X',self.get('SAME_SCUMM_VIEWPORT_SOURCE_X'))
            return p&~1,a
        raise AssertionError('unexpected retained service '+name)


class RetainedCameraTransactionTests(unittest.TestCase):
    def test_queue_refusal_retains_checked_strip_without_surface_mutation(self):
        m=RetainedCameraTransactionMachine();m.queue_busy=True
        surface=bytes(m.ram[0x402000:0x410000]);stage=bytes(m.ram[0x4013c4:0x402000])
        failed,writes=m.consume()
        self.assertFalse(failed)
        self.assertEqual(m.calls,['Same_VideoSurface_CanPublishRetained_Far'])
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),2)
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_SOURCE_X'),32)
        self.assertEqual(bytes(m.ram[0x402000:0x410000]),surface)
        self.assertEqual(bytes(m.ram[0x4013c4:0x402000]),stage)

    def test_transform_and_scratch_release_wait_for_exact_ppu_generation(self):
        m=RetainedCameraTransactionMachine();failed,_=m.consume()
        self.assertFalse(failed);self.assertTrue(m.assert_released)
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),4)
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_SOURCE_X'),32)
        self.assertEqual(m.get('SAME_SCUMM_ACTOR_SCRATCH_OWNER',1),1)
        for locked,generation,high in ((1,11,0),(0,10,0),(0,11,1)):
            m.put('SAME_MODE3_CONTROL_SURFACE_LOCKED',locked,1)
            m.put('SAME_BWRAM_CONTROL_COMMITTED_GENERATION',generation)
            m.put('SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI',high)
            m.calls=[];failed,_=m.consume();self.assertFalse(failed)
            self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),4)
            self.assertEqual(m.calls,['Same_VideoSurface_ScrollPresented_Far'])
            self.assertEqual(m.get('SAME_VIDEO_SURFACE_SOURCE_X'),32)
        m.put('SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI',0)
        m.calls=[];failed,_=m.consume();self.assertFalse(failed)
        self.assertEqual(m.calls,['Same_VideoSurface_ScrollPresented_Far','ScummV5_Camera_InstallGeometry_Far','Same_VideoSurface_CanWrite_Far'])
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_STATE',1),0)
        self.assertEqual(m.get('SAME_SCUMM_ACTOR_SCRATCH_OWNER',1),0)
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_SOURCE_X'),40)
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_PENDING_VISUAL',1),0)

    def test_committed_column_requests_next_foreground_without_idle_turn(self):
        m=RetainedCameraTransactionMachine()
        m.put('SAME_SCUMM_VIEWPORT_STATE',4,1)
        m.put('SAME_BWRAM_CONTROL_COMMITTED_GENERATION',11)
        m.put('SAME_VIDEO_SURFACE_PENDING_XSTART',176)
        failed,_=m.consume()
        self.assertFalse(failed)
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_SOURCE_X'),40)
        self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_ACTOR_SERVED',1),2)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),0)
        self.assertEqual(m.get('SAME_SCUMM_ACTOR_SCRATCH_OWNER',1),0)

class CameraForegroundFairnessTests(unittest.TestCase):
    def test_same_room_pan_does_not_cancel_actor_and_yields_only_one_turn(self):
        m=RetainedCameraTransactionMachine()
        m.symbols.update(SAME_MSU1_STATE_READING=4,SCUMM_MSU_ROOM_REQUESTED=1,
                         SAME_SCUMM_CURSOR_PENDING=0x40074E,
                         SAME_SCUMM_CURSOR_COMPOSING=0x400778)
        m.put('SAME_SCUMM_VIEWPORT_STATE',0,1);m.put('SAME_SCUMM_VIEWPORT_MODE',0,1)
        m.put('SAME_VIDEO_SURFACE_PENDING_XSTART',176)
        m.put('SAME_VIDEO_SURFACE_WIDTH',640);m.put('SAME_VIDEO_SURFACE_COPY_WIDTH',256)
        m.put('SAME_MSU1_STATUS',5,1);m.put('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT',255,1)
        m.put('SAME_SCUMM_ACTOR_POSE_STATE',1,1)
        def service(name,p,a):
            m.calls.append(name)
            if name in ('Same_VideoSurface_CanWrite_Far','ScummV5_MsuProgram_ReconcileRead_Far'):
                return p&~1,a
            if name in ('ScummV5_Controller_RenderActor_Far','ScummV5_Cursor_Frame_Far'):
                return p,a
            raise AssertionError('must not cancel checked actor read: '+name)
        m.service=service
        m.consume()
        self.assertNotIn('ScummV5_Controller_RenderActor_Far',m.calls)
        m.entry=m.labels['ScummV5_Camera_ServiceForeground_Far']
        for _ in range(3):
            m.consume()
            self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_ACTOR_SERVED',1),2)
            self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),0)
        # Existing compositor has now consumed its checked bytes and queued
        # its publication. The next idle turn may admit camera I/O even if a
        # new animation tick changes the desired actor again.
        m.put('SAME_SCUMM_ACTOR_POSE_STATE',0,1)
        m.put('SAME_SCUMM_ACTOR_SCRATCH_OWNER',0,1)
        m.consume();self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_ACTOR_SERVED',1),1)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),1)
        self.assertNotIn('ScummV5_Cursor_Frame_Far',m.calls)
        # A previously deferred cursor publication/restoration must drain
        # before actor composition. It never becomes a new blink-only pass.
        for field in ('SAME_SCUMM_CURSOR_PENDING','SAME_SCUMM_CURSOR_COMPOSING'):
            m.put('SAME_SCUMM_VIEWPORT_ACTOR_SERVED',2,1)
            m.put(field,1);m.calls=[];m.consume()
            self.assertIn('ScummV5_Cursor_Frame_Far',m.calls)
            self.assertNotIn('ScummV5_Controller_RenderActor_Far',m.calls)
            self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_ACTOR_SERVED',1),2)
            m.put(field,0)
        m.consume();self.assertEqual(m.get('SAME_SCUMM_VIEWPORT_ACTOR_SERVED',1),1)
        m.calls=[];m.entry=0;m.consume()
        self.assertNotIn('ScummV5_Controller_RenderActor_Far',m.calls)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ROOM_STATE',1),1)
