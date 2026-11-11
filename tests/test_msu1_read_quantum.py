"""Execute the actual transfer loop against an independent bounded-read model.

Hardware ports and CRC service calls are modeled; this is host instruction
coverage, not Nexen evidence. The CRC leaf has its own IEEE oracle tests.
"""
import re
import unittest
import zlib
from test_scumm_camera_native_copy import StripMachine, ROOT


class ReadMachine(StripMachine):
    def __init__(self, data, budget=256, capacity=None, initial_index=0,
                 busy_after=None, bad_crc=False, count=0):
        super().__init__()
        source = (ROOT/'runtime/snes/services/storage_msu1.pasm').read_text()
        for name, expr in re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+)', source, re.M):
            try: self.symbols[name] = self.value(expr)
            except (NameError, SyntaxError): pass
        self.symbols['SAME_MSU1_STEP_BUDGET'] = budget
        body = source.split('Same_Msu1_ReadStep:', 1)[1].split('Same_Msu1_CrcByte:', 1)[0]
        self.code, self.labels = [], {}
        for raw in body.splitlines():
            line = raw.split(';')[0].strip()
            if not line or line.startswith('.'): continue
            if line.endswith(':'): self.labels[line[:-1]] = len(self.code)
            else: self.code.append('jsr Fixture_DataPort' if line == 'lda MSU1_DATA' else line)
        self.data, self.cursor, self.busy_after, self.bad_crc = data, 0, busy_after, bad_crc
        self.crc = 0
        self.service_writes = []
        self.destination = 0x420001
        self.capacity = capacity if capacity is not None else len(data)
        self.ram[self.destination-1:self.destination+self.capacity+1] = b'\xa5'*(self.capacity+2)
        self.put('SAME_MSU1_DP_DEST', self.destination, 3)
        self.put('SAME_MSU1_STATUS', 4, 1)
        self.put('SAME_MSU1_FLAGS', int(capacity is not None), 1)
        self.put('SAME_MSU1_DEST_CAPACITY', self.capacity)
        self.put('SAME_MSU1_DEST_INDEX', initial_index)
        self.put('SAME_MSU1_REMAINING', len(data), 4)
        self.put('SAME_MSU1_BYTES_READ', count, 4)

    def service(self, name, p, a):
        if name == 'Same_Msu1_WaitDataReady':
            if self.busy_after is not None and self.cursor >= self.busy_after:
                self.put('SAME_MSU1_STATUS', 0xff, 1)
                return p|1, a
            return p&~1, a
        if name == 'Fixture_DataPort':
            a = self.data[self.cursor]; self.cursor += 1
            return p, a
        if name == 'Same_Msu1_CrcByte':
            self.crc = zlib.crc32(bytes([self.get('SAME_MSU1_BYTE_SCRATCH', 1)]), self.crc)
            return p, a
        if name == 'Same_Msu1_CheckCrc':
            if self.bad_crc or self.crc != zlib.crc32(self.data):
                self.put('SAME_MSU1_STATUS', 0xff, 1)
                return p|1, a
            return p&~1, a
        raise AssertionError(name)


class CheckedReadQuantumTests(unittest.TestCase):
    def verify(self, m, budget, start_count=0, initial_index=0):
        expected = bytearray(b'\xa5'*m.capacity)
        while m.get('SAME_MSU1_STATUS', 1) == 4:
            before = m.cursor
            m.consume()
            n = m.cursor-before
            self.assertLessEqual(n, budget)
            for offset in range(before, m.cursor):
                expected[(initial_index+offset)%m.capacity] = m.data[offset]
            self.assertEqual(m.get('SAME_MSU1_REMAINING', 4), len(m.data)-m.cursor)
            self.assertEqual(m.get('SAME_MSU1_BYTES_READ', 4), (start_count+m.cursor)&0xffffffff)
            self.assertEqual(m.get('SAME_MSU1_DEST_INDEX'),
                             (initial_index+m.cursor)%m.capacity if m.get('SAME_MSU1_FLAGS',1) else m.cursor)
            self.assertEqual(m.ram[m.destination:m.destination+m.capacity], expected)
            self.assertEqual(m.ram[m.destination-1], 0xa5)
            self.assertEqual(m.ram[m.destination+m.capacity], 0xa5)
            self.assertEqual(m.crc, zlib.crc32(m.data[:m.cursor]))
            if not n: break
        self.assertNotEqual(m.get('SAME_MSU1_STATUS', 1), 4)

    def test_quantum_boundaries_and_final_completion(self):
        for budget in (64, 256):
            for length in (0,1,budget-1,budget,budget+1,4097):
                with self.subTest(budget=budget,length=length):
                    m=ReadMachine(bytes(i%251 for i in range(length)),budget)
                    self.verify(m,budget)
                    self.assertEqual(m.get('SAME_MSU1_STATUS',1),5)
                    self.assertEqual(m.get('SAME_MSU1_READ_COUNT'),1)

    def test_ring_wrap_and_32bit_counter_carry(self):
        for capacity in (1,17,1024):
            m=ReadMachine(bytes(i%251 for i in range(65538)),capacity=capacity,
                          initial_index=capacity-1,count=0xfffffff0)
            self.verify(m,256,0xfffffff0,capacity-1)
            self.assertEqual(m.get('SAME_MSU1_STATUS',1),5)

    def test_busy_failure_commits_only_consumed_bytes_and_never_publishes(self):
        for limit in (0,1,63,64,255,256,300):
            m=ReadMachine(bytes(range(256))*2,busy_after=limit)
            self.verify(m,256)
            self.assertEqual(m.cursor,limit)
            self.assertEqual(m.get('SAME_MSU1_STATUS',1),255)
            self.assertEqual(m.get('SAME_MSU1_READ_COUNT'),0)

    def test_crc_failure_never_publishes(self):
        m=ReadMachine(b'checked bytes',bad_crc=True)
        self.verify(m,256)
        self.assertEqual(m.get('SAME_MSU1_STATUS',1),255)
        self.assertEqual(m.get('SAME_MSU1_READ_COUNT'),0)
