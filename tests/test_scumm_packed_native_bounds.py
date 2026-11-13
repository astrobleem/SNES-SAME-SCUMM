"""Execute actual cache leaf instructions; host evidence, not Nexen evidence."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class CacheMachine(StripMachine):
    def __init__(self, entry, *, selector=0xff, pc=0):
        super().__init__()
        self.symbols.update(ScummV5_MsuProgramRecords=0x68000,
                            SAME_SCUMM_MSU_CACHE_HAS_PAGE2=1,
                            ScummV5_MsuProgramPageIndex=0x69000,
                            ScummV5_MsuProgramPageRecords=0x6a000,
                            SCUMM_MSU1_PROGRAM_PAGE_INDEX_COUNT=3,
                            SCUMM_MSU1_PROGRAM_PAGE_RECORD_COUNT=1,
                            SCUMM_MSU1_PROGRAM_COUNT=3)
        text=(ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
        # All enabled arms in these leaves are positive feature conditionals.
        leaves=text[text.index('ScummV5_MsuProgram_FetchByte_Far:'):]
        leaves += '\n' + text[text.index('ScummV5_MsuProgram_FindPage_Far:'):
                              text.index('; A quick boundary check')]
        wrapper=f'''rep #$30
ldx #{pc}
sep #$20
lda #{selector}
jsl {entry}
sta.l $070000
rtl
'''
        self.code=[];self.labels={};self.service_writes=[]
        for line in (wrapper+leaves).splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.code)
            else:self.code.append(line.replace('jml ', 'jmp '))
        self.put('SAME_SCUMM_MSU_ACTIVE_SELECTOR',selector,1)
        self.put('SAME_SCUMM_PROGRAM_SELECT',selector,1)
        self.put('SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT',0,1)
        self.put('SAME_SCUMM_MSU_CACHE_ACTIVE_ID',0)
        self.put('SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION',7)
        self.put('SAME_SCUMM_MSU_CACHE_ID0',0)
        self.put('SAME_SCUMM_MSU_CACHE_GENERATION0',7)
        self.put('SAME_SCUMM_MSU_CACHE_STATE0',2,1)
        self.put('SAME_SCUMM_MSU_CACHE_SIZE0',32)
        self.put('SAME_SCUMM_MSU_ACTIVE_OFFSET',12)
        self.put('SAME_SCUMM_MSU_ACTIVE_START',0)
        self.put('SAME_SCUMM_MSU_ACTIVE_LENGTH',3)
        self.put('SAME_SCUMM_MSU_ACTIVE_PROGRAM',1)
        self.ram[0x7e1000:0x7e1020]=bytes(range(32))
        self.put(0x68000+10+4,3)  # unit 1 body length
        self.put(0x69000+4,0)     # shared group page index
        self.put(0x69000+6,0x800c)
        self.put(0x6a000,0)       # group anchor unit
        self.put(0x6a002,32)
        self.put(0x6a004,0x12345678,4)

    def service(self,name,p,a):
        if name=='ScummV5_Resident_ProgramUnitForSelector_Far':
            self.put('SAME_SCUMM_RESIDENT_EXPECTED_ID',1)
            return p|1,a
        if name=='ScummV5_Stream_RecordErrorSite_FarEntry':return p,a
        raise AssertionError(name)


class PackedNativeBounds(unittest.TestCase):
    def victim_machine(self):
        """Execute the real admission policy, stopping before descriptor I/O."""
        m = StripMachine()
        m.symbols.update(SAME_MSU1_STATE_READING=4, SCUMM_MSU_CACHE_LOADING=1)
        source = (ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
        start = 'ScummV5_MsuProgram_EnsureSelected_Far__find_slot:'
        chosen = 'ScummV5_MsuProgram_EnsureSelected_Far__chosen:'
        exhausted = 'ScummV5_MsuProgram_EnsureSelected_Far__exhausted:'
        tail = source[source.index(exhausted):source.index('; A nested SCUMM call')]
        body = 'php\n' + source[source.index(start):source.index(chosen)]
        body += chosen + '\nplp\nsec\nrtl\n' + tail
        m.code, m.labels, m.service_writes = [], {}, []
        for raw in body.splitlines():
            line = raw.split(';')[0].strip()
            if not line or line.startswith('.'): continue
            if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
            else: m.code.append(line.replace('jml ', 'jmp '))
        for slot in range(3):
            m.put(f'SAME_SCUMM_MSU_CACHE_STATE{slot}', 2, 1)
            m.put(f'SAME_SCUMM_MSU_CACHE_LRU{slot}', slot, 1)
            m.put(f'SAME_SCUMM_MSU_CACHE_PINS{slot}', 1, 1)
        m.put('SAME_MSU1_STATUS', 5, 1)
        return m

    def test_all_pinned_is_backpressure_and_release_permits_retry(self):
        m = self.victim_machine()
        before = bytes(m.ram)
        accepted, writes = m.consume()
        self.assertFalse(accepted)
        self.assertEqual(m.get('SAME_SCUMM_ERROR', 1), 0)
        permitted = {m.symbols[n] for n in ('SAME_SCUMM_MSU_CACHE_RETURN_P',
                                            'SAME_SCUMM_MSU_CACHE_TEMP')}
        self.assertTrue(set(writes) <= permitted)
        self.assertEqual(m.ram[0x7e1000:0x7e2000], before[0x7e1000:0x7e2000])
        m.put('SAME_SCUMM_MSU_CACHE_PINS1', 0, 1)
        self.assertTrue(m.consume()[0])
        self.assertEqual(m.get('SAME_SCUMM_MSU_CACHE_RETURN_P', 1), 1)

    def test_other_provider_clients_retain_read_and_completion_ownership(self):
        for provider, actor in ((4, 0), (5, 1)):
            m = self.victim_machine()
            m.put('SAME_SCUMM_MSU_CACHE_STATE0', 0, 1)
            m.put('SAME_MSU1_STATUS', provider, 1)
            m.put('SAME_SCUMM_ACTOR_SCRATCH_OWNER', actor, 1)
            accepted, writes = m.consume()
            self.assertFalse(accepted)
            self.assertEqual(writes, [])

    def test_loading_group_cannot_be_evicted_even_without_transient_pin(self):
        m = self.victim_machine()
        m.put('SAME_SCUMM_MSU_CACHE_PINS0', 0, 1)
        m.put('SAME_SCUMM_MSU_CACHE_STATE0', 1, 1)
        self.assertFalse(m.consume()[0])
        m.put('SAME_SCUMM_MSU_CACHE_STATE0', 2, 1)
        self.assertTrue(m.consume()[0])
        self.assertEqual(m.get('SAME_SCUMM_MSU_CACHE_RETURN_P', 1), 0)

    def test_native_binding_control_reaches_all_eight_assertions(self):
        m=CacheMachine('ScummV5_MsuProgram_RunBindingControl_Far')
        accepted,_=m.consume()
        self.assertTrue(accepted)
        self.assertEqual(m.get('SAME_SCUMM_RESIDENT_DIAG_SCRATCH'),8)
        self.assertEqual(m.ram[0x7e100b:0x7e1010],b'\xa5\x31\x32\x33\xa5')

    def test_bound_body_size_is_not_group_or_page_size(self):
        for body_size in (3,787,2048,21002,65535):
            m=CacheMachine('ScummV5_MsuProgram_BindLogical_Far')
            m.put(0x68000+10+4,body_size)
            m.consume()
            self.assertEqual(m.get('SAME_SCUMM_MSU_ACTIVE_BODY_LENGTH'),body_size)
            m=CacheMachine('ScummV5_MsuProgram_GetActiveSize_Far',pc=0x1234)
            m.put('SAME_SCUMM_MSU_ACTIVE_BODY_LENGTH',body_size)
            hit,_=m.consume()
            self.assertTrue(hit)
            self.assertEqual(m.get(0x70000),body_size)

    def test_size_fast_path_only_applies_to_current_execution(self):
        for selector,active,slot,hit in ((255,255,0,True),(254,255,0,False),
                (255,255,2,True),(255,255,3,False),(255,255,255,False),
                (0,0,0,False)):
            m=CacheMachine('ScummV5_MsuProgram_GetActiveSize_Far',selector=selector)
            m.put('SAME_SCUMM_MSU_ACTIVE_SELECTOR',active,1)
            m.put('SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT',slot,1)
            m.put('SAME_SCUMM_MSU_ACTIVE_BODY_LENGTH',21002)
            accepted,_=m.consume()
            self.assertEqual(accepted,hit)
            self.assertEqual(m.get(0x70000,2 if hit else 1),21002 if hit else selector)

    def test_large_page_size_and_complete_body_size_stay_independent(self):
        m=CacheMachine('ScummV5_MsuProgram_BindLogical_Far')
        m.put(0x69006,11)  # ordinary page count, not a packed member
        m.put(0x68000+10+4,21002)
        m.put('SAME_SCUMM_MSU_CACHE_PAGE_START0',2048)
        m.put('SAME_SCUMM_MSU_CACHE_SIZE0',2047)
        m.consume()
        self.assertEqual(m.get('SAME_SCUMM_MSU_ACTIVE_BODY_LENGTH'),21002)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ACTIVE_START'),2048)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ACTIVE_LENGTH'),2047)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ACTIVE_OFFSET'),0)

    def test_two_window_configuration_rejects_third_window_size_shortcut(self):
        m=CacheMachine('ScummV5_MsuProgram_GetActiveSize_Far')
        m.symbols['SAME_SCUMM_MSU_CACHE_HAS_PAGE2']=0
        m.put('SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT',2,1)
        accepted,_=m.consume()
        self.assertFalse(accepted)
        self.assertEqual(m.get(0x70000,1),255)

    def test_nested_child_directory_does_not_destroy_frame_stride(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_m24rb_far.pasm').read_text()
        start=source.index('    ; LAST_ALLOCATED is shared scratch')
        end=source.index('    sep #$20',source.index('    sta.l SAME_SCUMM_M23B_NEST_FRAMES+1,x',start))
        for depth in (0,1,2,23):
            m=CacheMachine('ScummV5_MsuProgram_Leave_Far')
            m.code=[];m.labels={}
            for line in (f'ldx #{depth*3}\n'+source[start:end]+'rtl\n').splitlines():
                line=line.split(';')[0].strip()
                if line and not line.startswith('.'):m.code.append(line)
            m.put('SAME_SCUMM_M23B_NEST_DEPTH',depth,1)
            m.put('SAME_SCUMM_C4_LAST_ALLOCATED',9,1)
            m.put('SAME_SCUMM_FRAME_OPS',0x1234)
            base=m.symbols['SAME_SCUMM_M23B_NEST_FRAMES']
            m.ram[base:base+72]=bytes([0xa5])*72
            m.consume()
            expected=bytearray([0xa5])*72
            expected[depth*3+1:depth*3+3]=b'\x34\x12'
            self.assertEqual(m.ram[base:base+72],expected)
            self.assertEqual(m.get(m.symbols['SAME_SCUMM_M23B_NEST_CHILD_SLOTS']+depth,1),9)

    def test_nested_wait_result_is_byte_sized_after_pc_restore(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_m24rb_far.pasm').read_text()
        begin=source.index('    ; CACHE_RETURN_P is a byte.')
        end=source.index('ScummV5_M25A_RunNestedChild__msu_parent_ready:',begin)
        code=source[begin:end]+'ScummV5_M25A_RunNestedChild__msu_parent_ready:\nrtl\n'
        for flag,expected in ((0,1),(1,5),(2,255)):
            m=CacheMachine('ScummV5_MsuProgram_Leave_Far')
            m.code=[];m.labels={};calls=[]
            for line in code.splitlines():
                line=line.split(';')[0].strip()
                if not line or line.startswith('.'):continue
                if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                else:m.code.append(line)
            def resume(name,p,a):
                self.assertEqual(name,'ScummV5_MsuProgram_ResumeActive_Far')
                calls.append(name)
                return p|0x21,1
            m.service=resume
            m.put('SAME_SCUMM_MSU_CACHE_RETURN_P',0xa500|flag)
            m.put('SAME_SCUMM_STATUS',0x5a01)
            m.put('SAME_SCUMM_C4_PARENT_SLOT',2,1)
            m.consume()
            self.assertEqual(m.get('SAME_SCUMM_STATUS'),0x5a00|expected)
            self.assertEqual(len(calls),int(flag==0))

    def test_member_bytes_and_neighbor_exclusion(self):
        for pc in range(5):
            m=CacheMachine('ScummV5_MsuProgram_FetchByte_Far',pc=pc)
            failed,_=m.consume()
            self.assertEqual(failed,pc>=3)
            self.assertEqual(m.get(0x70000,1),12+pc if pc<3 else 0)

    def test_unready_stale_or_reused_binding_cannot_fetch(self):
        for field,value,size in [('SAME_SCUMM_MSU_CACHE_STATE0',1,1),
                                 ('SAME_SCUMM_MSU_CACHE_GENERATION0',8,2),
                                 ('SAME_SCUMM_MSU_CACHE_ID0',2,2),
                                 ('SAME_SCUMM_MSU_ACTIVE_SELECTOR',0xfe,1)]:
            m=CacheMachine('ScummV5_MsuProgram_FetchByte_Far')
            m.put(field,value,size);failed,_=m.consume();self.assertTrue(failed)
            self.assertEqual(m.get(0x70000,1),0)

    def test_nested_return_restores_window_zero_and_ff_selector(self):
        m=CacheMachine('ScummV5_MsuProgram_Leave_Far')
        m.put('SAME_SCUMM_MSU_EXEC_DEPTH',1,1)
        m.put('SAME_SCUMM_MSU_EXEC_PREV_SLOT',0,1)
        m.put('SAME_SCUMM_MSU_EXEC_PREV_SELECTOR',0xff,1)
        m.put('SAME_SCUMM_MSU_CACHE_PINS0',1,1)
        m.consume()
        self.assertEqual(m.get('SAME_SCUMM_MSU_ACTIVE_SELECTOR',1),0xff)
        self.assertEqual(m.get('SAME_SCUMM_MSU_CACHE_ACTIVE_ID'),0)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ACTIVE_OFFSET'),12)
        self.assertEqual(m.get('SAME_SCUMM_MSU_ACTIVE_LENGTH'),3)
        self.assertEqual(m.get('SAME_SCUMM_MSU_CACHE_PINS0',1),0)

    def test_group_extent_pc_and_directory_bounds(self):
        for pc,offset,length,anchor,valid in [(0,12,32,0,True),(3,12,32,0,True),
                (4,12,32,0,False),(0,31,32,0,False),(0,12,2049,0,False),
                (0,12,32,3,False),(0,0x7fff,32,0,False)]:
            m=CacheMachine('ScummV5_MsuProgram_FindPage_Far')
            m.put('SAME_SCUMM_MSU_PAGE_REQUEST_ID',1)
            m.put('SAME_SCUMM_MSU_PAGE_REQUEST_PC',pc)
            m.put(0x69006,0x8000|offset);m.put(0x6a002,length);m.put(0x6a000,anchor)
            accepted,_=m.consume();self.assertEqual(accepted,valid)
            if valid:
                self.assertEqual(m.get('SAME_SCUMM_MSU_PAGE_REQUEST_LENGTH'),32)
                self.assertEqual(m.get('SAME_SCUMM_MSU_PAGE_REQUEST_CRC',4),0x12345678)
