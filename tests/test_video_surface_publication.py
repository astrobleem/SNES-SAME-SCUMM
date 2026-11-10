"""Execute CanWrite's actual source against the kernel's counted packet ring.

This is a bounded instruction model, not an assembler/native execution test.
Reuse ServiceMachine's memory and symbol evaluation; A is allowed to clobber.
"""
import re
import unittest

from test_video_surface_sparse_underlay import ROOT, SERVICE, ServiceMachine


class PublicationMachine(ServiceMachine):
    def __init__(self):
        super().__init__()
        # Fixed Mode-3 control ABI; the checkout's generated selection can be
        # legacy_backdrop, which deliberately omits these three constants.
        self.symbols.update(SAME_MODE3_CONTROL_STATE=0x401013,
                            SAME_MODE3_CONTROL_SURFACE_LOCKED=0x401014,
                            SAME_MODE3_STATE_IDLE=1)
        for filename in ('abi.inc.pasm',):
            source = (ROOT / 'runtime/snes/generated' / filename).read_text()
            definitions = re.findall(r'^([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+)', source, re.M)
            for _ in range(4):
                for name, expression in definitions:
                    try:
                        self.symbols[name] = self.value(expression)
                    except (NameError, SyntaxError):
                        pass
        source = SERVICE.read_text().split('Same_VideoSurface_CanWrite_Far:', 1)[1]
        source = source.split('Same_VideoSurface_WriteIndexedPixel_Far:', 1)[0]
        self.code, self.labels, self.offsets = [], {}, []
        position, width, index_width = 0, 16, 16
        for raw in source.splitlines():
            line = raw.split(';', 1)[0].strip()
            if line in ('.a8', '.a16'):
                width = int(line[2:])
            if line in ('.i8', '.i16'):
                index_width = int(line[2:])
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
            else:
                self.offsets.append(position)
                self.code.append(line)
                op, _, arg = line.partition(' ')
                if op in ('rep', 'sep', 'bra', 'beq', 'bne', 'bcc', 'bcs'):
                    size = 2
                elif op in ('jmp', 'brl'):
                    size = 3
                elif '.l' in op:
                    size = 4
                elif arg.startswith('#'):
                    size = 1 + (index_width if op in ('ldx', 'ldy', 'cpx', 'cpy') else width)//8
                else:
                    size = 1
                position += size
        self.put('SAME_MODE3_CONTROL_STATE', self.symbols['SAME_MODE3_STATE_IDLE'], 1)

    def packet(self, slot, service, opcode):
        base = self.symbols['SAME_EVENT_BUFFER'] + slot * 16
        self.put(base + self.symbols['SAME_PKT_SERVICE'], service, 1)
        self.put(base + self.symbols['SAME_PKT_OPCODE'], opcode, 1)

    def queue(self, head, packets):
        capacity = self.symbols['SAME_EVENT_CAPACITY']
        self.put('SAME_EVENT_HEAD', head)
        self.put('SAME_EVENT_COUNT', len(packets))
        self.put('SAME_EVENT_TAIL', (head + len(packets)) % capacity)
        for index, (service, opcode) in enumerate(packets):
            self.packet((head + index) % capacity, service, opcode)

    def can_write(self, p=0x08):
        a, x, y, db = 0xBEEF, 0xA35C, 0xD792, 0x53
        if p & 0x10:
            x &= 255
            y &= 255
        initial = x, y, p & ~1, db
        sentinel = [0xCA, 0xFE, 0xAB]
        stack, pc = sentinel.copy(), 0
        def push(value, bits):
            if bits == 16:
                stack.append(value >> 8)
            stack.append(value & 255)
        def pop(bits):
            value = stack.pop()
            return value | (stack.pop() << 8) if bits == 16 else value
        def nz(value, bits):
            return (2 if value == 0 else 0) | (0x80 if value & (1 << (bits-1)) else 0)
        for steps in range(2000):
            line = self.code[pc]
            pc += 1
            op, _, arg = line.partition(' ')
            bits, ibits = (8 if p & 0x20 else 16), (8 if p & 0x10 else 16)
            mask = (1 << bits)-1
            value = None
            if arg.startswith('#'):
                value = self.value(arg[1:])
            elif '.l' in op:
                address = self.value(arg.removesuffix(',x')) + (x if arg.endswith(',x') else 0)
                value = self.get(address, (ibits if op.startswith(('ldx', 'ldy')) else bits)//8)
            result = None
            if op == 'php': push(p, 8)
            elif op == 'pha': push(a, bits)
            elif op == 'phx': push(x, ibits)
            elif op == 'phy': push(y, ibits)
            elif op == 'phb': push(db, 8)
            elif op == 'plp':
                p = pop(8)
                if p & 0x10:
                    x &= 255
                    y &= 255
            elif op == 'pla': result = pop(bits)
            elif op in ('plx', 'ply'):
                value = pop(ibits)
                if op == 'plx': x = value
                else: y = value
                p = (p & ~0x82) | nz(value, ibits)
            elif op == 'plb':
                db = pop(8)
                p = (p & ~0x82) | nz(db, 8)
            elif op == 'rep': p &= ~value
            elif op == 'sep':
                p |= value
                if p & 0x10:
                    x &= 255
                    y &= 255
            elif op == 'cld': p &= ~8
            elif op == 'clc': p &= ~1
            elif op == 'sec': p |= 1
            elif op in ('lda', 'lda.l'): result = value
            elif op in ('ldx', 'ldx.l', 'ldy', 'ldy.l', 'tax', 'tay', 'inx', 'iny', 'dex', 'dey'):
                is_x = op in ('ldx', 'ldx.l', 'tax', 'inx', 'dex')
                value = (a if op in ('tax', 'tay') else
                         (x if is_x else y) + (1 if op in ('inx', 'iny') else -1)
                         if op in ('inx', 'iny', 'dex', 'dey') else value)
                value &= (1 << ibits)-1
                if is_x: x = value
                else: y = value
                p = (p & ~0x82) | nz(value, ibits)
            elif op == 'txa': result = x
            elif op == 'tya': result = y
            elif op in ('and', 'and.l'): result = a & value
            elif op in ('cmp', 'cmp.l'):
                p = (p & ~0x83) | int((a & mask) >= value) | nz(((a & mask)-value) & mask, bits)
            elif op == 'asl':
                p = (p & ~1) | int(bool(a & (1 << (bits-1))))
                result = a << 1
            elif op == 'inc': result = (a & mask)+1
            elif op == 'dec': result = (a & mask)-1
            elif op in ('adc', 'adc.l'):
                assert not p & 8, 'queue arithmetic must use binary mode'
                result = (a & mask) + value + (p & 1)
                overflow = (~(a ^ value) & (a ^ result) & (1 << (bits-1))) != 0
                p = (p & ~0x41) | int(result > mask) | (0x40 if overflow else 0)
            elif op in ('bra', 'brl', 'jmp', 'beq', 'bne', 'bcc', 'bcs'):
                take = {'beq': bool(p & 2), 'bne': not p & 2,
                        'bcc': not p & 1, 'bcs': bool(p & 1)}.get(op, True)
                if take: pc = self.labels[arg]
            elif op == 'rtl':
                assert (x, y, p & ~1, db) == initial, 'CanWrite register/width contract'
                assert stack == sentinel, 'CanWrite stack imbalance'
                self.steps = steps + 1
                return not bool(p & 1)
            else:
                raise AssertionError(f'unsupported actual instruction: {line}')
            if result is not None:
                result &= mask
                a = (a & ~mask) | result
                p = (p & ~0x82) | nz(result, bits)
        raise AssertionError('CanWrite exceeded bounded queue scan')


class VideoSurfacePublicationTests(unittest.TestCase):
    def check(self, machine, writable):
        before = bytes(machine.ram)
        for widths in (0, 0x10, 0x20, 0x30):
            for flags in (0, 0xCF):
                with self.subTest(widths=widths, flags=flags):
                    self.assertEqual(machine.can_write(widths | flags), writable)
                    self.assertEqual(bytes(machine.ram), before)

    def test_present_at_every_position_in_wrapped_full_ring_blocks(self):
        m = PublicationMachine()
        for head in (0, 7, 15):
            for position in range(16):
                with self.subTest(head=head, position=position):
                    packets = [(1, 0x10)] * 16
                    packets[position] = (1, 0x11)
                    m.queue(head, packets)
                    self.check(m, False)

    def test_wrapped_partial_ring_and_stale_tail_present(self):
        m = PublicationMachine()
        m.queue(15, [(1, 0x10), (1, 0x11)])
        self.check(m, False)
        m.queue(15, [(1, 0x10)])  # Slot zero is now stale, not queued.
        self.check(m, True)

    def test_empty_ring_ignores_stale_present_in_every_slot(self):
        m = PublicationMachine()
        for slot in range(16):
            m.packet(slot, 1, 0x11)
        for head in (0, 7, 15):
            m.queue(head, [])
            self.check(m, True)

    def test_other_service_same_opcode_and_video_nonpresent_do_not_block(self):
        m = PublicationMachine()
        m.queue(13, [(2, 0x11), (3, 0x11), (1, 0x10), (1, 0x12)] * 4)
        self.check(m, True)

    def test_backend_state_and_lock_still_block_without_packets(self):
        m = PublicationMachine()
        for state, locked in ((0, 0), (2, 0), (3, 0), (4, 0), (5, 0), (255, 0), (1, 1)):
            with self.subTest(state=state, locked=locked):
                m.put('SAME_MODE3_CONTROL_STATE', state, 1)
                m.put('SAME_MODE3_CONTROL_SURFACE_LOCKED', locked, 1)
                self.check(m, False)

    def test_malformed_count_fails_closed_without_scanning(self):
        m = PublicationMachine()
        for count in (17, 255, 256, 65535):
            with self.subTest(count=count):
                m.put('SAME_EVENT_COUNT', count)
                self.check(m, False)
                self.assertLess(m.steps, 40)

    def test_short_branches_reach_with_declared_operand_widths(self):
        m = PublicationMachine()
        for index, line in enumerate(m.code):
            op, _, target = line.partition(' ')
            if op in ('bra', 'beq', 'bne', 'bcc', 'bcs'):
                displacement = m.offsets[m.labels[target]] - (m.offsets[index] + 2)
                with self.subTest(instruction=line):
                    self.assertGreaterEqual(displacement, -128)
                    self.assertLessEqual(displacement, 127)

    def test_consumed_present_releases_guard_only_after_backend_unlock(self):
        m = PublicationMachine()
        m.queue(15, [(1, 0x11)])
        self.check(m, False)
        m.queue(0, [])
        m.put('SAME_MODE3_CONTROL_STATE', 2, 1)
        m.put('SAME_MODE3_CONTROL_SURFACE_LOCKED', 1, 1)
        self.check(m, False)
        m.put('SAME_MODE3_CONTROL_STATE', 1, 1)
        m.put('SAME_MODE3_CONTROL_SURFACE_LOCKED', 0, 1)
        self.check(m, True)
