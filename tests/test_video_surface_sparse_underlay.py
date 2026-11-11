"""Execute the service's actual instruction sequence with bounded RAM fixtures.

The source-level runner covers arithmetic, widths, branches and stack contracts;
it is not an assembler or a SNES emulator. CanWrite is the only service stub.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / 'runtime/snes/services/video_surface.pasm'
U = 'Same_VideoSurface_Underlay_'


def pixel_leaves():
    source=SERVICE.read_text()
    leaves=source[source.index('Same_VideoSurface_WriteIndexedPixel_Far:'):source.index('; Fill an inclusive viewport-relative')]
    backend=(ROOT/'runtime/snes/services/video_mode3_retained.inc.pasm').read_text()
    return '\n'+leaves+backend[backend.index('Same_Mode3_MapSurfaceX_Far:'):backend.index('; Extension of the existing copyright-free')]


class ServiceMachine:
    def __init__(self, tail=4790):
        self.ram = bytearray(0x800000)
        layout = json.loads((ROOT / 'runtime/snes/carriers/sa1_bwram_layout.json').read_text())
        addr = lambda name: int(layout[name]['address'].replace(':', ''), 16)
        reserved = addr('backend_reserved')
        alloc = layout['backend_reserved']['allocations']
        self.symbols = {
            'SAME_SCUMM_LIVE_ROOM_STAGING_BASE': addr('live_room_active'),
            'SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE': layout['live_room_active']['bytes'],
            'SAME_SCUMM_LIVE_ROOM_SURFACE_BASE': addr('live_surface'),
            'SAME_SCUMM_LIVE_ROOM_CONTROL': reserved + alloc['live_room_control']['offset'],
            'SAME_BWRAM_VIDEO_SURFACE_STATE': reserved + alloc['video_surface_state']['offset'],
            'MODE3_R_ACTIVE': reserved + 13,
            'MODE3_R_INDEX_ORIGIN': reserved + alloc['retained_viewport']['offset'] + 0x18,
            'SAME_BWRAM_SURFACE_BASE': addr('live_surface'),
            'MODE3_R_EXCHANGE': reserved + alloc['retained_viewport']['offset'] + 0x39,
            'MODE3_R_DELTA': reserved + alloc['retained_viewport']['offset'] + 0x0c,
        }
        definitions = []
        for file in (ROOT / 'runtime/snes/kernel/memory.pasm',
                     ROOT / 'runtime/snes/engines/scumm_v5_msu_programs.pasm',
                     ROOT / 'runtime/snes/engines/scumm_v5.pasm', SERVICE):
            definitions.extend(re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+)', file.read_text(), re.M))
        for _ in range(12):
            for name, expression in definitions:
                if name not in self.symbols:
                    try: self.symbols[name] = self.value(expression)
                    except (NameError, SyntaxError, TypeError): pass
        self.base = self.symbols['SAME_SCUMM_LIVE_ROOM_STAGING_BASE']
        self.surface = self.symbols['SAME_SCUMM_LIVE_ROOM_SURFACE_BASE']
        self.length = 6144 - tail
        self.header = self.base + self.length
        self.put(self.base+0x30, self.length)
        self.put(self.symbols['SAME_SCUMM_LIVE_ROOM_CONTROL']+1, 1, 1)
        self.put('SAME_VIDEO_SURFACE_ROOM', 4)
        self.put('SAME_VIDEO_SURFACE_ROOM_GENERATION', 7)
        self.ram[self.surface:self.surface+57344] = bytes(i % 251 for i in range(57344))
        self.original_surface = bytes(self.ram[self.surface:self.surface+57344])
        source = SERVICE.read_text()
        text = source[source.index('Same_VideoSurface_ExchangeActorUnderlay_Far:'):]
        text = text.split('\n.endif', 1)[0] + pixel_leaves()
        self.code, self.labels, self.offsets = [], {}, []
        position, width = 0, 16
        for raw in text.splitlines():
            line = raw.split(';', 1)[0].strip()
            if line in ('.a8', '.a16'):
                width = int(line[2:])
            if not line or line.startswith('.'): continue
            if line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
                continue
            self.offsets.append(position)
            self.code.append(line)
            op, _, arg = line.partition(' ')
            if op in ('rep','sep') or op in ('bra','bcc','bcs','beq','bne'): size=2
            elif op in ('jmp','jsr','brl'): size=3
            elif op == 'jsl' or '.l' in op: size=4
            elif arg.startswith('#'): size=1+width//8
            else: size=1
            position += size
        self.busy = False
        self.writes = []

    def value(self, expression):
        expression = re.sub(r'\$([0-9A-Fa-f]+)', r'0x\1', expression.strip())
        return eval(expression, {'__builtins__': {}}, self.symbols)

    def put(self, address, value, size=2):
        if isinstance(address, str): address = self.symbols[address]
        self.ram[address:address+size] = (value & ((1 << (size*8))-1)).to_bytes(size, 'little')

    def get(self, address, size=2):
        if isinstance(address, str): address = self.symbols[address]
        return int.from_bytes(self.ram[address:address+size], 'little')

    def damage(self):
        return tuple(self.get('SAME_VIDEO_SURFACE_DAMAGE_'+f) for f in ('X','Y','WIDTH','HEIGHT'))

    def call(self, name, a=0xBEEF, x=0xABCD, y=0x1234, p=0x08, db=0x7E):
        if p & 0x10: x, y = x & 255, y & 255
        original = a, x, y, p, db
        stack, returns = [0xCA,0xFE,0xAB], []
        pc = self.labels['Same_VideoSurface_'+name+'_Far']
        def push(v, width):
            if width == 16: stack.append(v >> 8)
            stack.append(v & 255)
        def pop(width):
            v = stack.pop()
            return v | (stack.pop() << 8) if width == 16 else v
        for _ in range(300000):
            line = self.code[pc]; pc += 1
            op, _, arg = line.partition(' ')
            width = 8 if p & 0x20 else 16
            mask = (1 << width)-1
            value = address = None
            if arg.startswith('#'):
                value = self.value(arg[1:])
            elif '.l' in op or '.w' in op:
                expression = arg.removesuffix(',x').removesuffix(',y')
                address = self.value(expression) + (x if arg.endswith(',x') else y if arg.endswith(',y') else 0)
                if '.w' in op: address = (db << 16) | (address & 65535)
                value = self.get(address, width//8)
            result = None
            if op == 'php': push(p, 8)
            elif op == 'phb': push(db, 8)
            elif op == 'pha': push(a, width)
            elif op == 'phx': push(x, 8 if p & 0x10 else 16)
            elif op == 'phy': push(y, 8 if p & 0x10 else 16)
            elif op == 'plp': p = pop(8)
            elif op == 'plb': db = pop(8)
            elif op == 'pla': result = pop(width)
            elif op == 'plx': x = pop(8 if p & 0x10 else 16)
            elif op == 'ply': y = pop(8 if p & 0x10 else 16)
            elif op == 'rep': p &= ~value
            elif op == 'sep': p |= value
            elif op == 'cld': p &= ~8
            elif op == 'eor': result = a ^ value
            elif op == 'brl': pc = self.labels[arg]
            elif op == 'clc': p &= ~1
            elif op == 'sec': p |= 1
            elif op in ('lda', 'lda.l', 'lda.w'): result = value
            elif op in ('sta.l','sta.w'):
                self.put(address, a & mask, width//8)
                self.writes.append((address, width//8))
            elif op == 'tax': x = a & (255 if p & 0x10 else 65535)
            elif op == 'txa': result = x
            elif op == 'tya': result = y
            elif op in ('and', 'and.l'): result = a & value
            elif op == 'ora.l': result = a | value
            elif op in ('adc', 'adc.l'):
                assert not p & 8, 'arithmetic must use binary mode'
                result = (a & mask) + value + (p & 1)
                p = (p & ~1) | int(result > mask)
            elif op in ('sbc', 'sbc.l'):
                assert not p & 8
                result = (a & mask) - value - (1-(p & 1))
                p = (p & ~1) | int(result >= 0)
            elif op in ('cmp', 'cmp.l'):
                v = ((a & mask)-value) & mask
                p = (p & ~0x83) | int((a & mask) >= value) | (2 if v == 0 else 0) | (0x80 if v & (1 << (width-1)) else 0)
            elif op == 'ldy': y = value & (255 if p & 0x10 else 65535)
            elif op == 'iny': y = (y+1)&65535
            elif op == 'inx': x = (x+1)&65535
            elif op == 'inc': result = (a & mask)+1
            elif op == 'dec': result = (a & mask)-1
            elif op == 'xba':
                a = ((a & 255) << 8) | (a >> 8)
                p = (p & ~0x82) | (2 if a & 255 == 0 else 0) | (a & 128)
            elif op == 'jsr':
                returns.append(pc); pc = self.labels[arg]
            elif op == 'rts': pc = returns.pop()
            elif op == 'jsl':
                if arg == 'Same_VideoSurface_CanWrite_Far':
                    a = (a & 0xFF00) | int(self.busy)
                    p = (p & ~1) | int(self.busy)
                else:
                    returns.append(pc); pc = self.labels[arg]
            elif op in ('jmp','bra','bcc','bcs','bne','beq','bpl'):
                take = {'bcc': not p & 1, 'bcs': bool(p & 1),
                        'bpl': not p & 0x80, 'bne': not p & 2, 'beq': bool(p & 2)}.get(op, True)
                if take: pc = self.labels[arg]
            elif op == 'rtl':
                if returns:
                    pc=returns.pop();continue
                assert (a,x,y,p & ~1,db) == (original[0],original[1],original[2],original[3] & ~1,original[4])
                assert stack == [0xCA,0xFE,0xAB] and not returns
                return bool(p & 1)
            else: raise AssertionError(line)
            if result is not None:
                result &= mask
                a = (a & ~mask) | result
                p = (p & ~0x82) | (2 if result == 0 else 0) | (0x80 if result & (1 << (width-1)) else 0)
        raise AssertionError('bounded service failed to return')

    def capture(self, runs):
        assert not self.call('BeginActorUnderlay')
        for dest, count in runs:
            assert not self.call('CaptureActorRun', a=dest, x=count)
        assert not self.call('CommitActorUnderlay')

    def paint(self, runs):
        for dest,count in runs:
            self.ram[self.surface+dest:self.surface+dest+count] = bytes([255])*count


class SparseUnderlayServiceTests(unittest.TestCase):
    def test_sparse_wide_pose_roundtrip_and_consumed_magic(self):
        m = ServiceMachine()
        # 739 pixels, broad 214x108 bbox (23112 bytes), 127 runs:
        # 16+127*4+739 = 1263 bytes, conservatively above measured max 1248.
        runs = [(20*256+1, 6)] + [((21+i%106)*256+20+i%180, 6) for i in range(116)]
        runs += [(127*256+214, 1)] + [(70*256+40+i*4, 4) for i in range(9)]
        self.assertEqual(sum(n for _,n in runs), 739)
        m.capture(runs)
        self.assertEqual(m.get(m.header+6), 1263)
        self.assertEqual(m.get(m.header,1), 0xA8)
        m.paint(runs)
        self.assertFalse(m.call('RestoreActorUnderlay',p=0x38))
        self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)
        self.assertEqual(m.get(m.header,1),0)
        old = m.damage()
        self.assertGreater(old[2]*old[3],4790)
        m.ram[m.surface+20*256+1] = 77
        self.assertFalse(m.call('RestoreActorUnderlay'))
        self.assertEqual(m.damage(),(0,0,0,0))
        self.assertEqual(m.ram[m.surface+20*256+1],77)

    def test_full_row_and_old_new_union_and_empty(self):
        m=ServiceMachine(); m.capture([(0,256)]); m.paint([(0,256)])
        self.assertFalse(m.call('RestoreActorUnderlay'))
        self.assertEqual(m.damage(),(0,0,256,1))
        self.assertFalse(m.call('BeginActorUnderlay'))
        self.assertEqual(m.damage(),(0,0,256,1))
        self.assertFalse(m.call('CaptureActorRun',a=223*256+255,x=1))
        self.assertEqual(m.damage(),(0,0,256,224))
        self.assertFalse(m.call('CommitActorUnderlay'))
        self.assertFalse(m.call('RestoreActorUnderlay'))
        self.assertEqual(m.damage(),(255,223,1,1))
        self.assertFalse(m.call('BeginActorUnderlay'))
        self.assertFalse(m.call('CommitActorUnderlay'))
        self.assertEqual(m.get(m.header+6),16)
        self.assertFalse(m.call('RestoreActorUnderlay'))
        self.assertEqual(m.damage(),(0,0,0,0))

    def test_capacity_exact_and_exhausted_no_publish(self):
        for tail,failed in [(21,False),(20,True)]:
            m=ServiceMachine(tail=tail)
            self.assertFalse(m.call('BeginActorUnderlay'))
            self.assertEqual(m.call('CaptureActorRun',a=0,x=1),failed)
            self.assertEqual(m.call('CommitActorUnderlay'),failed)
            self.assertEqual(m.get(m.header,1),0 if failed else 0xA8)
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)
        m=ServiceMachine(tail=15)
        self.assertTrue(m.call('BeginActorUnderlay'))
        self.assertEqual(m.get('SAME_SCUMM_ERROR',1),0x10)

    def test_capture_rejects_invalid_runs_and_commit_after_failure(self):
        for dest,count in [(0,0),(0,257),(255,2),(0xE000,1),(0xFFFF,256)]:
            m=ServiceMachine(); self.assertFalse(m.call('BeginActorUnderlay'))
            self.assertTrue(m.call('CaptureActorRun',a=dest,x=count))
            self.assertTrue(m.call('CommitActorUnderlay'))
            self.assertEqual(m.get(m.header,1),0)
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),m.original_surface)

    def test_malformed_last_record_cannot_restore_prefix(self):
        runs=[(0,2),(0xDF00,3)]
        for offset,value in [(4,1),(4,3),(4,65535),(6,16),(6,28),(6,30),(6,65535),(8,1),(12,257),(14,225),
                             (16+6,0xE000),(16+6+2,0),(16+6+2,257),(16+6+2,256)]:
            m=ServiceMachine(); m.capture(runs);m.paint(runs)
            m.put(m.header+offset,value)
            before=bytes(m.ram[m.surface:m.surface+57344])
            self.assertTrue(m.call('RestoreActorUnderlay'),(offset,value))
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),before,(offset,value))
            self.assertEqual(m.get(m.header,1),0)

    def test_stale_generation_room_and_absent_old_magic_are_inert(self):
        for offset,value,size in [(1,5,1),(2,8,2),(0,0xA7,1),(0,0,1)]:
            m=ServiceMachine();m.capture([(4,3)]);m.paint([(4,3)])
            m.put(m.header+offset,value,size)
            before=bytes(m.ram[m.surface:m.surface+57344])
            self.assertFalse(m.call('RestoreActorUnderlay'))
            self.assertEqual(m.damage(),(0,0,0,0))
            self.assertEqual(bytes(m.ram[m.surface:m.surface+57344]),before)

    def test_busy_and_register_contract_and_scratch_ownership(self):
        m=ServiceMachine();m.capture([(0,256)])
        m.busy=True
        self.assertTrue(m.call('RestoreActorUnderlay',p=0x39))
        self.assertEqual(m.get(m.header,1),0xA8)
        m.busy=False
        for status in (0,0x10,0x20,0x30,0xCF,0xFF):
            self.assertFalse(m.call('RestoreActorUnderlay',p=status))
            self.assertFalse(m.call('BeginActorUnderlay',p=status))
            self.assertFalse(m.call('CommitActorUnderlay',p=status))
            self.assertEqual(m.call('InvalidateActorUnderlay',p=status), bool(status & 1))
        scratch=m.symbols['SAME_VIDEO_ACTOR_UNDERLAY_SCRATCH_BASE']
        state=m.symbols['SAME_VIDEO_SURFACE_STATE']
        error=m.symbols['SAME_SCUMM_ERROR']
        for address,size in m.writes:
            self.assertTrue(any(start <= address and address+size <= end for start,end in
                [(m.header,m.base+6144),(m.surface,m.surface+57344),(scratch,scratch+14),
                 (state+0x34,state+0x40),(error,error+1),
                 (m.symbols['MODE3_R_EXCHANGE'],m.symbols['MODE3_R_EXCHANGE']+1)]),hex(address))

    def test_short_branch_distances_and_feature_guard(self):
        m=ServiceMachine()
        for i,line in enumerate(m.code):
            op,_,arg=line.partition(' ')
            if op in ('bra','bcc','bcs','beq','bne'):
                displacement=m.offsets[m.labels[arg]]-(m.offsets[i]+2)
                self.assertTrue(-128 <= displacement <= 127,(line,displacement))
        source=SERVICE.read_text()
        self.assertNotIn('Same_VideoSurface_CaptureActorUnderlay_Far:',source)
        block=source.split('Same_VideoSurface_RestoreActorUnderlay_Far:',1)[1].split('\n.endif',1)[0]
        self.assertNotIn('SAME_SCUMM_ACTOR_POSE_',block)
        self.assertIn('.if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER && SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES',source)


if __name__ == '__main__':
    unittest.main()
