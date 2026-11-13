"""Execute the native CRC leaf against Python's independent IEEE CRC oracle.

This is instruction-level host coverage, not native emulator acceptance.
"""
import random
import re
import unittest
import zlib
from test_scumm_camera_native_copy import StripMachine, ROOT


class CheckedReadCrcTests(unittest.TestCase):
    def machine(self):
        m = StripMachine()
        source = (ROOT/'runtime/snes/services/storage_msu1.pasm').read_text()
        body = source.split('Same_Msu1_CrcByte:', 1)[1].split('Same_Msu1_CheckCrc:', 1)[0]
        m.code = [line.split(';')[0].strip() for line in body.splitlines()
                  if line.strip() and not line.strip().startswith((';', '.'))]
        m.labels = {}
        source = (ROOT/'runtime/snes/services/storage_msu1_crc_table.inc.pasm').read_text()
        for n, name in enumerate(('Low', 'High')):
            label = 'Same_Msu1_CrcTable'+name
            part = source.split(label+':', 1)[1].split('\n\n', 1)[0]
            words = [int(w, 16) for w in re.findall(r'\$([0-9A-F]{4})', part)]
            self.assertEqual(len(words), 256)
            base = 0x008000+n*512
            m.symbols[label] = base
            for i, word in enumerate(words):
                m.put(base+i*2, word)
                oracle = zlib.crc32(bytes([i]), 0xFFFFFFFF) ^ 0xFFFFFFFF
                self.assertEqual(word, (oracle >> (n*16)) & 65535)
        return m

    def test_all_input_bytes_random_seeds_and_adjacent_scratch_are_irrelevant(self):
        m = self.machine(); rng = random.Random(20261111)
        for byte in range(256):
            for _ in range(4):
                seed = rng.getrandbits(32)
                crc = m.symbols['SAME_MSU1_CRC_STATE']
                m.put(crc, seed, 4)
                m.put(crc+4, rng.getrandbits(8), 1)
                m.put('SAME_MSU1_BYTE_SCRATCH', byte | rng.getrandbits(8)<<8)
                _, writes = m.consume()
                self.assertEqual(m.get(crc, 4), zlib.crc32(bytes([byte]), seed^0xFFFFFFFF)^0xFFFFFFFF)
                self.assertEqual(set(writes), set(range(crc, crc+4)))

    def test_incremental_requests_cross_service_quanta_without_reset(self):
        m = self.machine(); crc = m.symbols['SAME_MSU1_CRC_STATE']
        for data in (b'', b'123456789', bytes(range(256))*9):
            m.put(crc, 0xFFFFFFFF, 4)
            for offset, byte in enumerate(data):
                m.put('SAME_MSU1_BYTE_SCRATCH', byte, 1); m.consume()
                if offset % 256 == 255:
                    self.assertEqual(m.get(crc, 4)^0xFFFFFFFF, zlib.crc32(data[:offset+1]))
            self.assertEqual(m.get(crc, 4)^0xFFFFFFFF, zlib.crc32(data))
