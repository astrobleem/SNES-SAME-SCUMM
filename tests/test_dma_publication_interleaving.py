"""Interrupt actual DMA publication instructions at every source boundary.

The NMI queue guard executes from source. The subsequent hardware transfer is
modeled atomically (the interrupted producer cannot run inside its NMI).
These tests are CPU interleaving evidence, not native execution evidence.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'runtime/snes/kernel/dma.pasm').read_text()


def instructions(text):
    return [tuple(line.split(None, 1)) if ' ' in line else (line, '')
            for raw in text.splitlines()
            if (line := raw.split(';', 1)[0].strip())
            and not line.startswith('.') and not line.endswith(':')]


class Machine:
    def __init__(self, active=0):
        self.mem = dict(SAME_DMA_PENDING=active, SAME_DMA_COMMITTED=341,
                        SAME_DMA_PUBLISHING=0, SAME_DMA_REJECTED=0,
                        SAME_DMA_REQUEST_LENGTH=64, SAME_DMA_REQUEST_TARGET=0x100,
                        SAME_DMA_REQUEST_SOURCE_LO=0x100,
                        SAME_DMA_REQUEST_SOURCE_BANK=0x41,
                        SAME_DMA_REQUEST_TYPE_FLAGS=0)
        self.active = active
        self.transfers = 0
        self.a = 0
        self.p = 0
        self.stack = []
        self.max_pending = active

    def nmi(self):
        # Execute the actual guard (including width changes) on saved CPU state.
        guard = SOURCE.split('Same_Dma_ProcessQueue:\n', 1)[1].split(
            'Same_Dma_ProcessQueue__unowned:', 1)[0]
        saved = self.a, self.p, list(self.stack)
        taken = self.run(instructions(guard)) == 'unowned'
        self.a, self.p, self.stack = saved
        if not taken:
            return
        count = self.active + bool(self.mem.get('SAME_DMA_QUEUE+SAME_DMA_SLOT_TYPE,x', 0) & 0x80)
        self.transfers += count
        self.mem['SAME_DMA_PENDING'] = (self.mem['SAME_DMA_PENDING'] - count) & 65535
        self.mem['SAME_DMA_COMMITTED'] = (self.mem['SAME_DMA_COMMITTED'] + count) & 65535
        self.active = 0
        self.mem['SAME_DMA_QUEUE+SAME_DMA_SLOT_TYPE,x'] = 0

    def run(self, code, interrupt=None):
        for i, (op, arg) in enumerate(code):
            if i == interrupt:
                self.nmi()
            mask = 255 if self.p & 32 else 65535
            if arg.startswith('#'):
                v = int(arg[2:], 16) if arg.startswith('#$') else {'SAME_DMA_FLAG_ACTIVE':128}[arg[1:]]
            else:
                v = self.mem.get(arg, 0)
            if op == 'php': self.stack.append(self.p)
            elif op == 'plp': self.p = self.stack.pop()
            elif op == 'pha': self.stack.append(self.a & mask)
            elif op == 'pla': self.a = self.stack.pop()
            elif op == 'sei': self.p |= 4
            elif op == 'rep': self.p &= ~v
            elif op == 'sep': self.p |= v
            elif op in ('lda', 'lda.l'): self.a = (self.a & ~mask) | (v & mask)
            elif op == 'sta.l': self.mem[arg] = self.a & mask
            elif op == 'ora': self.a |= v
            elif op == 'inc': self.a = (self.a + 1) & mask
            elif op == 'clc': self.p &= ~1
            elif op == 'sec': self.p |= 1
            elif op == 'adc.l': self.a = (self.a + v + (self.p & 1)) & mask
            elif op == 'beq':
                if self.a & mask == 0:
                    assert arg == 'Same_Dma_ProcessQueue__unowned'
                    return 'unowned'
            elif op in ('rts', 'rtl'): return
            else: raise AssertionError((op, arg))
            self.max_pending = max(self.max_pending, self.mem['SAME_DMA_PENDING'])
        if interrupt == len(code): self.nmi()


def enqueue_code(source=SOURCE):
    claim = source.split('Same_Dma_Enqueue:\n', 1)[1].split('    rep #$30', 1)[0]
    found = source.split('Same_Dma_Enqueue__found:\n', 1)[1].split('Same_Dma_Enqueue__reject:', 1)[0]
    return instructions(claim + found)


class DmaPublicationTests(unittest.TestCase):
    def test_every_publication_boundary_with_existing_descriptors(self):
        code = enqueue_code()
        for active in range(8):
            for interrupt in range(len(code) + 1):
                with self.subTest(active=active, interrupt=interrupt):
                    m = Machine(active)
                    m.run(code, interrupt)
                    self.assertEqual(m.mem['SAME_DMA_PUBLISHING'], 0)
                    self.assertEqual(m.p & 1, 0)
                    self.assertEqual(m.stack, [])
                    m.nmi()
                    self.assertEqual(m.mem['SAME_DMA_PENDING'], 0)
                    self.assertEqual(m.transfers, active + 1)
                    self.assertLessEqual(m.max_pending, 8)

    def test_old_publication_reproduces_phantom_pending(self):
        # Negative control: remove only the new ownership writes, retaining
        # the original active-last + load/inc/store implementation.
        code = enqueue_code()
        code = [(op, arg) for op, arg in code if arg != 'SAME_DMA_PUBLISHING']
        failures = []
        for i in range(len(code)):
            m = Machine(3); m.run(code, i); m.nmi()
            failures.append(m.mem['SAME_DMA_PENDING'])
        self.assertTrue(any(failures), failures)

    def test_rejected_request_releases_owner_without_publishing(self):
        reject = instructions('php\n' + SOURCE.split('Same_Dma_Enqueue__reject:\n', 1)[1].split('; Called only', 1)[0])
        for i in range(len(reject)):
            m = Machine(2); m.mem['SAME_DMA_PUBLISHING'] = 1
            m.run(reject, i); m.nmi()
            self.assertEqual(m.mem['SAME_DMA_PENDING'], 0)
            self.assertEqual(m.mem['SAME_DMA_REJECTED'], 1)
            self.assertEqual(m.p & 1, 1)
            self.assertEqual(m.transfers, 2)

    def test_fence_snapshot_is_atomic_across_nmi_and_counter_wrap(self):
        code = instructions(SOURCE.split('Same_Dma_GetFence_Far:\n', 1)[1])
        for committed in (341, 65532, 65535):
            for active in range(9):
                for interrupt in range(len(code) + 1):
                    m = Machine(active); m.mem['SAME_DMA_COMMITTED'] = committed
                    m.run(code, interrupt)
                    self.assertEqual(m.a, (committed + active) & 65535)
                    self.assertEqual(m.mem['SAME_DMA_PUBLISHING'], 0)
                    self.assertEqual(m.stack, [])

    def test_consumers_use_kernel_fence_and_owner_has_distinct_byte(self):
        for file, label in [('video_mode3.pasm', 'Same_Mode3_QueueBatch__finish:'),
                            ('video_overlay_bg2.pasm', 'Same_Overlay_Bg2_Queue__armed:')]:
            code = (ROOT/'runtime/snes/services'/file).read_text().split(label, 1)[1].split('    sta.l ', 1)[0]
            self.assertIn('jsl Same_Dma_GetFence_Far', code)
        memory = (ROOT/'runtime/snes/kernel/memory.pasm').read_text()
        aliases = re.findall(r'^(\w+)\s*=\s*\$7E224E\b', memory, re.M)
        self.assertEqual(aliases, ['SAME_DMA_PUBLISHING'])


if __name__ == '__main__': unittest.main()
