"""Production empty-byte seekers: bounded scans, not a native acceptance claim."""
from functools import lru_cache
from pathlib import Path
import random
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'runtime/snes/services/video_mode3.pasm'

@lru_cache(None)
def program(kind):
    label = 'Same_Mode3_Seek' + kind + 'Byte'
    text = SOURCE.read_text().split(label + ':', 1)[1]
    text = text.split('\n\n', 1)[0]
    code, labels = [], {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('.'): continue
        if line.endswith(':'): labels[line[:-1]] = len(code)
        else: code.append(line.split(None, 1))
    return code, labels


def seek(kind, index, pending, inflight=bytes(112)):
    code, labels = program(kind)
    a, x, pc, carry, zero = index, 0, 0, 1, False
    stack, reads = [], []
    for _ in range(32):
        ins = code[pc]; pc += 1
        op, arg = ins[0], ins[1] if len(ins) > 1 else ''
        if op in ('lda.l', 'and.l'):
            data = inflight if 'INFLIGHT' in arg else pending
            reads.append(x)
            # Actual A16 loads read a neighbor byte, ignored by AND #$00FF.
            v = data[x] | ((data[x+1] if x+1 < len(data) else 0xA5) << 8)
        elif arg.startswith('#'): v = int(arg[2:], 16)
        if op == 'pha': stack.append(a)
        elif op == 'pla': a = stack.pop(); zero = a == 0
        elif op == 'lsr': carry = a & 1; a >>= 1; zero = a == 0
        elif op == 'tax': x = a
        elif op == 'lda.l': a = v; zero = a == 0
        elif op in ('and', 'and.l'): a &= v; zero = a == 0
        elif op == 'eor': a ^= v; zero = a == 0
        elif op == 'clc': carry = 0
        elif op == 'sec': carry = 1
        elif op == 'adc':
            total = a + v + carry; a = total & 65535; carry = total > 65535
        elif op == 'bne':
            if not zero: pc = labels[arg]
        elif op == 'rts':
            assert not stack
            assert all(r == index // 8 for r in reads)
            return a, bool(carry)
        else: raise AssertionError(ins)
    raise AssertionError('unbounded seeker')


class SparseScanTests(unittest.TestCase):
    def test_every_bit_pattern_and_alignment_at_table_edges(self):
        for family, size in (('Tile', 112), ('Palette', 32)):
            for byte in (0, size//2, size-1):
                for value in range(256):
                    data = bytearray(size); data[byte] = value
                    for bit in range(8):
                        i = byte*8+bit
                        expected = (i, True) if value else ((i & ~7)+8, False)
                        self.assertEqual(seek('Candidate'+family, i, data), expected)
                        self.assertEqual(seek('Available'+family, i, data, bytes(size)), expected)
                        self.assertEqual(seek('Available'+family, i, data, data), ((i & ~7)+8, False))

    def test_sparse_scan_matches_exact_eligible_bits_and_cannot_skip_live_dma(self):
        rng = random.Random(0x5A4E)
        for family, size in (('Tile',112), ('Palette',32)):
            for _ in range(100):
                pending = bytes(rng.randrange(256) if rng.randrange(8)==0 else 0 for _ in range(size))
                inflight = bytes(rng.randrange(256) for _ in range(size))
                for prefix in ('Candidate','Available'):
                    effective = pending if prefix=='Candidate' else bytes(a & ~b for a,b in zip(pending,inflight))
                    expected=[i for i in range(size*8) if effective[i//8] & (1 << (i%8))]
                    observed=[];i=0;calls=0
                    while i < size*8:
                        n, nonempty=seek(prefix+family,i,pending,inflight);calls+=1
                        if nonempty:
                            if effective[n//8] & (1 << (n%8)): observed.append(n)
                            n+=1
                        self.assertGreater(n,i);i=n
                    self.assertEqual(observed,expected)
                    self.assertLessEqual(calls,size+7*sum(bool(b) for b in effective))

    def test_all_four_production_scans_use_seeker_and_keep_per_bit_test(self):
        text=SOURCE.read_text()
        for kind in ('CandidateTile','CandidatePalette','AvailableTile','AvailablePalette'):
            self.assertEqual(text.count('jsr Same_Mode3_Seek'+kind+'Byte'),1)
            self.assertIn('jsr Same_Mode3_Test'+kind,text)

if __name__ == '__main__': unittest.main()
