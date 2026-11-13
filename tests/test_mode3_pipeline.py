"""Execute production step dispatch; service outcomes model dependency fences.

This is a host control-flow regression, not a substitute for native raster tests.
"""
from pathlib import Path
import unittest
from test_scumm_camera_native_copy import StripMachine


class PipelineMachine(StripMachine):
    def __init__(self, state, *, remaining=0, palette=256, dma_ready=True,
                 queue_state=5, nmi_pending=True):
        super().__init__()
        self.symbols.update(SAME_MODE3_STATE_IDLE=1, SAME_MODE3_STATE_CONVERTING=2,
                            SAME_MODE3_STATE_QUEUEING=3, SAME_MODE3_STATE_WAITING_DMA=4,
                            SAME_MODE3_STATE_COMPLETE=5)
        # Independent synthetic addresses: only dispatch control is executed.
        names = ('SAME_MODE3_CONTROL_STATE', 'SAME_MODE3_CONTROL_CANDIDATE_COUNT',
                 'SAME_MODE3_CONTROL_SCAN_PALETTE', 'SAME_BWRAM_CONTROL_SURFACE_VALID',
                 'SAME_BWRAM_CONTROL_TILE_VALID', 'SAME_BWRAM_CONTROL_CGRAM_VALID',
                 'SAME_BWRAM_CONTROL_PENDING_GENERATION', 'SAME_BWRAM_CONTROL_COMMITTED_GENERATION',
                 'SAME_MODE3_CONTROL_PENDING_GENERATION_HI', 'SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI',
                 'SAME_MODE3_CONTROL_SURFACE_LOCKED')
        self.symbols.update({n:0x300000+i*4 for i,n in enumerate(names)})
        self.put(names[0], state, 1); self.put(names[1], remaining); self.put(names[2], palette)
        self.put(names[-1],1,1)
        self.put(names[6],0xFFFF); self.put(names[8],0x1234)
        self.dma_ready=dma_ready;self.queue_state=queue_state;self.nmi_pending=nmi_pending;self.calls=[];self.service_writes=[]
        source=(Path(__file__).resolve().parents[1]/'runtime/snes/services/video_mode3.pasm').read_text()
        source=source.split('Same_Mode3_Step:',1)[1].split('; Packet decoding',1)[0]
        source=source.split('.if SAME_VIDEO_OVERLAY_BG2',1)[0]+source.split('.endif',1)[1]
        self.code=[];self.labels={}
        for line in source.splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.code)
            else:self.code.append(line)

    def service(self,name,p,a):
        self.calls.append(name)
        if name=='Same_Mode3_ObserveBatch' and self.dma_ready:self.put('SAME_MODE3_CONTROL_STATE',3,1)
        if name=='Same_Mode3_QueueBatch':self.put('SAME_MODE3_CONTROL_STATE',self.queue_state,1)
        if name=='Same_Mode3_Retained_Complete':p=(p&~1)|self.nmi_pending
        return p,a


class PipelineTests(unittest.TestCase):
    def test_conversion_queues_ready_data_without_another_scheduler_turn(self):
        m=PipelineMachine(2,queue_state=4);m.consume()
        self.assertEqual(m.calls,['Same_Mode3_ProcessPaletteCandidates','Same_Mode3_ProcessTileCandidates','Same_Mode3_QueueBatch'])
        self.assertEqual(m.get('SAME_MODE3_CONTROL_STATE',1),4)

    def test_unfinished_conversion_or_palette_cannot_queue(self):
        for kw in ({'remaining':1},{'palette':255}):
            m=PipelineMachine(2,**kw);m.consume()
            self.assertNotIn('Same_Mode3_QueueBatch',m.calls)

    def test_completed_dma_arms_nmi_ticket_in_same_slice(self):
        m=PipelineMachine(4);m.consume()
        self.assertEqual(m.calls,['Same_Mode3_ObserveBatch','Same_Mode3_QueueBatch','Same_Mode3_Retained_Complete'])
        self.assertEqual(m.get('SAME_MODE3_CONTROL_SURFACE_LOCKED',1),1)
        self.assertEqual(m.get('SAME_BWRAM_CONTROL_COMMITTED_GENERATION'),0)

    def test_refused_or_inflight_dma_never_spins_or_publishes(self):
        for kw in ({'dma_ready':False},{'queue_state':3},{'queue_state':4}):
            m=PipelineMachine(4,**kw);m.consume()
            self.assertLessEqual(m.calls.count('Same_Mode3_QueueBatch'),1)
            self.assertNotIn('Same_Mode3_Retained_Complete',m.calls)
            self.assertEqual(m.get('SAME_MODE3_CONTROL_SURFACE_LOCKED',1),1)

    def test_nmi_ack_commits_both_generation_words_and_unlocks(self):
        m=PipelineMachine(4,nmi_pending=False);m.consume()
        self.assertEqual(m.get('SAME_BWRAM_CONTROL_COMMITTED_GENERATION'),0xFFFF)
        self.assertEqual(m.get('SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI'),0x1234)
        self.assertEqual(m.get('SAME_MODE3_CONTROL_SURFACE_LOCKED',1),0)
        self.assertEqual(m.get('SAME_MODE3_CONTROL_STATE',1),1)

if __name__=='__main__':unittest.main()
