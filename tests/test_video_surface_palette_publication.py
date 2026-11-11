"""Actual surface palette/publication instructions; only kernel stage/push stubbed.

CanWrite executes the separate actual-source ring model. No ROM/native emulator.
"""
import re
import unittest

from test_video_surface_publication import PublicationMachine, ROOT, SERVICE


class PalettePublicationMachine:
    def __init__(self):
        self.guard = PublicationMachine()
        self.symbols = self.guard.symbols
        self.ram = self.guard.ram
        self.get, self.put, self.value = self.guard.get, self.guard.put, self.guard.value
        self.symbols['SAME_MODE3_LIVE_PALETTE'] = 0x407000
        self.code, self.labels = [], {}
        source = SERVICE.read_text()
        sections = []
        for first, last in (
            ('Same_VideoSurface_InstallPalette_Far:', '; A producer'),
            ('Same_VideoSurface_PushPresentation:', '; Restore one clipped'),
            ('Same_VideoSurface_PushDamagePresent:', '; Compose the installed'),
        ):
            block = source[source.index(first):]
            sections.append(block[:block.index(last)])
        for raw in '\n'.join(sections).splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
            else:
                self.code.append(line)
        self.events = []
        self.fail_opcode = None
        self.put('SAME_VIDEO_SURFACE_PALETTE_SOURCE', 0x406000, 3)
        self.ram[0x406000:0x406300] = bytes((i*37+5) & 255 for i in range(768))

    def run(self, name, p=0):
        a, x, y = 0xBEEF, 0x1234, 0x5678
        stack, returns = [], []
        pc = self.labels['Same_VideoSurface_'+name]
        initial_p = p
        for _ in range(20000):
            line = self.code[pc]; pc += 1
            op, _, arg = line.partition(' ')
            width, iw = (8 if p & 32 else 16), (8 if p & 16 else 16)
            mask = (1 << width)-1
            result = value = address = None
            if arg.startswith('#'):
                value = self.value(arg[1:])
            elif arg.startswith('['):
                address = self.get(self.value(arg[1:arg.index(']')]), 3)+y
                value = self.get(address, width//8)
            elif op in ('lda', 'lda.l', 'sta', 'sta.l'):
                address = self.value(arg.removesuffix(',x')) + (x if arg.endswith(',x') else 0)
                value = self.get(address, width//8)
            if op == 'php': stack.append(p)
            elif op == 'plp': p = stack.pop()
            elif op == 'rep': p &= ~value
            elif op == 'sep': p |= value
            elif op == 'clc': p &= ~1
            elif op == 'sec': p |= 1
            elif op in ('lda', 'lda.l'): result = value
            elif op in ('sta', 'sta.l'): self.put(address, a & mask, width//8)
            elif op == 'ldx': x = value
            elif op == 'ldy': y = value
            elif op in ('inx', 'iny'):
                if op == 'inx': x = (x+1) & ((1 << iw)-1)
                else: y = (y+1) & ((1 << iw)-1)
                v = x if op == 'inx' else y
                p = (p & ~2) | (2 if v == 0 else 0)
            elif op in ('cmp', 'cpy'):
                v = y if op == 'cpy' else a & mask
                p = (p & ~3) | int(v >= value) | (2 if v == value else 0)
            elif op == 'inc': result = (a & mask)+1
            elif op == 'jsr': returns.append(pc); pc = self.labels[arg]
            elif op == 'jsl':
                if arg == 'Same_VideoSurface_CanWrite_Far':
                    p = (p & ~1) | int(not self.guard.can_write(p))
                elif arg == 'Same_Mode3_Event_Stage_Far':
                    start = self.symbols['SAME_EVENT_STAGING']
                    self.ram[start:start+16] = bytes(16)
                elif arg == 'Same_Mode3_Event_Push_Far':
                    start = self.symbols['SAME_EVENT_STAGING']
                    packet = bytes(self.ram[start:start+16])
                    opcode = packet[self.symbols['SAME_PKT_OPCODE']]
                    refused = opcode == self.fail_opcode or self.get('SAME_EVENT_COUNT') >= 16
                    p = (p & ~1) | int(refused)
                    if not refused:
                        self.events.append(packet)
                        tail = self.get('SAME_EVENT_TAIL')
                        dest = self.symbols['SAME_EVENT_BUFFER']+tail*16
                        self.ram[dest:dest+16] = packet
                        self.put('SAME_EVENT_TAIL', (tail+1) & 15)
                        self.put('SAME_EVENT_COUNT', self.get('SAME_EVENT_COUNT')+1)
                else: raise AssertionError(line)
            elif op in ('bra', 'brl', 'jmp', 'beq', 'bne', 'bcc', 'bcs'):
                take = {'beq': bool(p & 2), 'bne': not p & 2,
                        'bcc': not p & 1, 'bcs': bool(p & 1)}.get(op, True)
                if take: pc = self.labels[arg]
            elif op in ('rts', 'rtl'):
                if returns: pc = returns.pop()
                else:
                    assert not stack
                    if op == 'rtl': assert p & ~1 == initial_p & ~1
                    return bool(p & 1)
            else: raise AssertionError(line)
            if result is not None:
                result &= mask
                a = (a & ~mask) | result
                p = (p & ~0x82) | (2 if result == 0 else 0) | (128 if result & (1 << (width-1)) else 0)
        raise AssertionError('publication instructions failed to terminate')

    def opcodes(self):
        return [packet[self.symbols['SAME_PKT_OPCODE']] for packet in self.events]


class PaletteServicePublicationTests(unittest.TestCase):
    def test_palette_only_preserves_pixels_and_emits_no_dirty_rectangle(self):
        for flags in (0, 0x30, 0x39):
            m=PalettePublicationMachine()
            m.put('SAME_VIDEO_SURFACE_PALETTE_DIRTY',1,1)
            before=bytes(m.ram[0x402000:0x406000])
            self.assertFalse(m.run('PushPalettePresent_Far',p=flags))
            self.assertEqual(m.opcodes(),[m.symbols['SAME_VIDEO_OP_PALETTE_WRITE'],
                                          m.symbols['SAME_VIDEO_OP_PRESENT']])
            self.assertEqual(bytes(m.ram[0x402000:0x406000]),before)
            self.assertEqual(m.get('SAME_VIDEO_SURFACE_PALETTE_DIRTY',1),0)
            packet=m.events[0]
            offset=m.symbols['SAME_PKT_ARG0']+2
            self.assertEqual(int.from_bytes(packet[offset:offset+2],'little'),256)

    def test_palette_only_busy_or_queue_failure_retains_color_ownership(self):
        for failure in ('capacity','palette','present'):
            m=PalettePublicationMachine();m.put('SAME_VIDEO_SURFACE_PALETTE_DIRTY',1,1)
            if failure=='capacity':m.put('SAME_EVENT_COUNT',15)
            else:m.fail_opcode=m.symbols['SAME_VIDEO_OP_'+('PALETTE_WRITE' if failure=='palette' else 'PRESENT')]
            self.assertTrue(m.run('PushPalettePresent_Far'))
            self.assertEqual(m.get('SAME_VIDEO_SURFACE_PALETTE_DIRTY',1),1)
            self.assertNotIn(m.symbols['SAME_VIDEO_OP_SURFACE_DIRTY'],m.opcodes())

    def test_install_marks_dirty_after_exact_copy_and_refuses_queued_owner(self):
        m = PalettePublicationMachine()
        self.assertFalse(m.run('InstallPalette_Far', p=0x39))
        self.assertEqual(m.ram[0x407000:0x407300], m.ram[0x406000:0x406300])
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_PALETTE_DIRTY', 1), 1)
        self.assertFalse(m.run('PushDirtyPresent'))
        old = bytes(m.ram[0x407000:0x407300])
        m.ram[0x406000] ^= 255
        self.assertTrue(m.run('InstallPalette_Far'))
        self.assertEqual(bytes(m.ram[0x407000:0x407300]), old)
        self.assertEqual(m.get('SAME_VIDEO_SURFACE_PALETTE_DIRTY', 1), 0)

    def test_dirty_damage_and_full_publications_emit_palette_before_present(self):
        for entry in ('PushDirtyPresent', 'PushDamagePresent', 'PushPresentation'):
            m = PalettePublicationMachine()
            m.run('InstallPalette_Far')
            m.put('SAME_VIDEO_SURFACE_NEXT_GENERATION', 65535)
            self.assertFalse(m.run(entry))
            self.assertEqual(m.opcodes(), [m.symbols['SAME_VIDEO_OP_'+op] for op in
                                          ('SURFACE_DIRTY', 'PALETTE_WRITE', 'PRESENT')])
            arg = m.symbols['SAME_PKT_ARG0']
            self.assertEqual(m.events[1][arg:arg+4], b'\x00\x00\x00\x01')
            self.assertEqual(m.events[2][arg:arg+2], b'\x01\x00')
            self.assertEqual(m.get('SAME_VIDEO_SURFACE_PALETTE_DIRTY', 1), 0)
            self.assertTrue(m.run(entry), 'queued PRESENT must prevent second publication')
            self.assertEqual(len(m.events), 3)
            self.assertEqual(m.get('SAME_VIDEO_SURFACE_NEXT_GENERATION'), 1)

    def test_full_group_capacity_preflight_and_clean_two_packet_legacy(self):
        for entry in ('PushDirtyPresent', 'PushDamagePresent'):
            for dirty, count, refused in ((1, 14, True), (1, 13, False),
                                          (0, 14, False), (0, 15, True)):
                m = PalettePublicationMachine()
                m.guard.queue(15, [(0, 0)]*count)
                m.put('SAME_VIDEO_SURFACE_PALETTE_DIRTY', dirty, 1)
                self.assertEqual(m.run(entry), refused)
                self.assertEqual(len(m.events), 0 if refused else 2+dirty)
                self.assertEqual(m.get('SAME_VIDEO_SURFACE_PALETTE_DIRTY', 1), dirty if refused else 0)

    def test_each_queue_failure_retains_dirty_until_retry_present_accepted(self):
        for entry in ('PushDirtyPresent', 'PushDamagePresent', 'PushPresentation'):
            for operation in ('SURFACE_DIRTY', 'PALETTE_WRITE', 'PRESENT'):
                m = PalettePublicationMachine()
                m.run('InstallPalette_Far')
                m.fail_opcode = m.symbols['SAME_VIDEO_OP_'+operation]
                self.assertTrue(m.run(entry))
                self.assertEqual(m.get('SAME_VIDEO_SURFACE_PALETTE_DIRTY', 1), 1)
                self.assertNotIn(m.symbols['SAME_VIDEO_OP_PRESENT'], m.opcodes())
                # Drain partial non-PRESENT events before retry, as frame service does.
                m.guard.queue(0, [])
                m.fail_opcode = None
                self.assertFalse(m.run(entry))
                self.assertEqual(m.get('SAME_VIDEO_SURFACE_PALETTE_DIRTY', 1), 0)

    def test_surface_slack_is_owned_and_reset_includes_dirty_byte(self):
        import json
        layout = json.loads((ROOT/'runtime/snes/carriers/sa1_bwram_layout.json').read_text())
        state = layout['backend_reserved']['allocations']['video_surface_state']
        self.assertEqual(state['bytes'], 0x44)
        m = PalettePublicationMachine()
        self.assertEqual(m.symbols['SAME_VIDEO_SURFACE_PALETTE_DIRTY'],
                         m.symbols['SAME_VIDEO_SURFACE_STATE']+0x43)
        reset = (ROOT/'runtime/snes/services/video_mode3.pasm').read_text()
        self.assertIn('SAME_BWRAM_VIDEO_SURFACE_STATE-SAME_BWRAM_BACKEND_BASE+SAME_VIDEO_SURFACE_STATE_SIZE', reset)


if __name__ == '__main__':
    unittest.main()
