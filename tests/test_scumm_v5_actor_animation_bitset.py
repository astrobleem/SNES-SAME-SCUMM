"""Source-instruction checks for packed flags and backend ownership."""
from pathlib import Path
import re
import tempfile
import contextlib
import io
import unittest
from unittest.mock import patch

from tools import audit_scumm_residency_wram as ownership

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'runtime/snes/engines/scumm_v5.pasm'
CONTROLLER = ROOT / 'runtime/snes/engines/scumm_v5_controller_far.pasm'


def run_helper(actor, enabled, initial_bits, status, high):
    source = ENGINE.read_text().split('ScummV5_C14_SetExplicitAnimation:', 1)[1].split('.endif', 1)[0]
    code, labels = [], {}
    for raw in source.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line or line.startswith('.'):
            continue
        if line.endswith(':'):
            labels[line[:-1]] = len(code)
        else:
            code.append(line)
    values = ownership.symbols()
    base = values['SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION']
    work = values['SAME_MODE3_WORK_OWNER_START']
    addresses = {'SAME_SCUMM_C14_ACTOR': 0x100,
                 'ScummV5_C7_BitMasks': 0x200,
                 'SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION': base}
    memory = {work + i: 0xA5 for i in range(176)}
    memory.update({base + i: value for i, value in enumerate(initial_bits.to_bytes(4, 'little'))})
    memory.update({0x100: actor, 0x101: 255})
    memory.update({0x200 + i: 1 << i for i in range(8)})
    a, p = (high << 8) | enabled, status
    x, y = (0x73, 0x95) if status & 0x10 else (0xB173, 0xA295)
    original = a, x, y, p
    pc, stack = 0, [0xCA, 0xFE]

    def push(value, width):
        if width == 16:
            stack.append(value >> 8)
        stack.append(value & 255)

    def pop(width):
        value = stack.pop()
        return value | (stack.pop() << 8) if width == 16 else value

    for _ in range(100):
        line = code[pc]
        pc += 1
        op, _, arg = line.partition(' ')
        width = 8 if p & 0x20 else 16
        mask = (1 << width) - 1
        value = address = None
        if arg.startswith('#$'):
            value = int(arg[2:], 16)
        elif arg in addresses or arg.endswith(',x'):
            name = arg.removesuffix(',x')
            address = addresses[name] + (x if arg.endswith(',x') else 0)
            value = memory.get(address, 0)
            if width == 16:
                value |= memory.get(address + 1, 0) << 8
        result = None
        if op == 'php': push(p, 8)
        elif op == 'plp': p = pop(8)
        elif op == 'rep': p &= ~value
        elif op == 'sep': p |= value
        elif op == 'pha': push(a, width)
        elif op == 'phx': push(x, 8 if p & 0x10 else 16)
        elif op == 'phy': push(y, 8 if p & 0x10 else 16)
        elif op == 'pla': result = pop(width)
        elif op == 'plx': x = pop(8 if p & 0x10 else 16)
        elif op == 'ply': y = pop(8 if p & 0x10 else 16)
        elif op == 'tay': y = a & (255 if p & 0x10 else 65535)
        elif op == 'tax': x = a & (255 if p & 0x10 else 65535)
        elif op == 'tya': result = y
        elif op == 'lda.l': result = value
        elif op in ('and', 'and.l'): result = a & value
        elif op == 'ora.l': result = a | value
        elif op == 'eor': result = a ^ value
        elif op == 'lsr': result = (a & mask) >> 1
        elif op == 'sta.l':
            memory[address] = a & 255
            if width == 16: memory[address + 1] = a >> 8
        elif op == 'beq':
            if p & 2: pc = labels[arg]
        elif op == 'bra': pc = labels[arg]
        elif op == 'rts':
            assert (a, x, y, p) == original
            assert stack == [0xCA, 0xFE]
            return memory, work, base
        else: raise AssertionError(line)
        if result is not None:
            result &= mask
            a = (a & ~mask) | result
            p = (p & ~0x82) | (2 if result == 0 else 0) | (0x80 if result & (1 << (width-1)) else 0)
    raise AssertionError('helper failed to return')


class ActorAnimationBitsetTests(unittest.TestCase):
    def test_all_actor_bits_preserve_registers_neighbors_and_backend_writes(self):
        for actor in range(32):
            for enabled in (0, 1, 255):
                for status in (0x09, 0x29, 0x19, 0x39):
                    for high in (0, 1, 255):
                        initial = 0xA55AA55A
                        memory, work, base = run_helper(actor, enabled, initial, status, high)
                        want = initial | (1 << actor) if enabled else initial & ~(1 << actor)
                        self.assertEqual(int.from_bytes(bytes(memory[base+i] for i in range(4)), 'little'), want)
                        self.assertTrue(all(memory[work+i] == 0xA5 for i in range(176)
                                            if not base <= work+i < base+4))
                        # All backend words, including tile high byte zero at
                        # the left edge and nonzero at the diagnostic center.
                        for tile in (0, 20, 80, 255, 256, 895):
                            for offset in range(0, 0x24, 2):
                                memory[work+offset] = tile & 255
                                memory[work+offset+1] = tile >> 8
                            self.assertEqual(int.from_bytes(bytes(memory[base+i] for i in range(4)), 'little'), want)

    def test_renderer_constant_selection_covers_all_32_actors(self):
        source = CONTROLLER.read_text()
        from tools.generate_snes_engine_selection import main
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'active_engine.inc.pasm'
            for actor in range(32):
                with patch('sys.argv', ['generate', '--output', str(output),
                                       '--scumm-actor-render-id', str(actor)]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0)
                config = output.with_name('build_config.inc.pasm').read_text()
                constants = dict((name, int(value, 16)) for name, value in re.findall(
                    r'(SCUMM_V5_ACTOR_ANIMATION_\w+) = \$([0-9A-F]+)', config))
                self.assertEqual(constants['SCUMM_V5_ACTOR_ANIMATION_BYTE'], actor // 8)
                self.assertEqual(constants['SCUMM_V5_ACTOR_ANIMATION_MASK'], 1 << (actor % 8))
        self.assertNotIn('.if (SCUMM_V5_ACTOR_RENDER_ID', source)
        self.assertEqual(source.count('lda.l SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION+SCUMM_V5_ACTOR_ANIMATION_BYTE\n    and #SCUMM_V5_ACTOR_ANIMATION_MASK'), 2)

    def test_call_sites_and_reset_use_packed_contract(self):
        source = ENGINE.read_text()
        self.assertNotIn('AnimationIndexX', source)
        costume = source.split('ScummV5_Op_ActorOps__costume:',1)[1].split('jsr ScummV5_C14_SetExplicitAnimation',1)[0]
        self.assertIn('lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_INIT_FRAME,x\n    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIMATION,x\n    lda #$01\n    .else\n    lda #$00\n    .endif', costume)
        for marker, value in [('ScummV5_Op_AnimateActor__store:', '01'),
                              ('ScummV5_C14_DefaultActor:', '00')]:
            block = source.split(marker, 1)[1].split('jsr ScummV5_C14_SetExplicitAnimation', 1)[0]
            self.assertTrue(block.rstrip().endswith('lda #$'+value))
        reset = source.split('ScummV5_C14_ResetState__clear:', 1)[1].split('    .endif', 1)[0]
        self.assertIn('lda #$0000\n    sta.l SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION\n    sta.l SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION+2', reset)

    def test_audit_owns_backend_and_rejects_original_overlap(self):
        report = ownership.audit()
        backend = next(r for r in report['regions'] if r['owner'] == 'mode3_backend_scratch')
        self.assertEqual((backend['start'], backend['end_exclusive']), ('$41E750', '$41E774'))
        values = ownership.symbols()
        values.update(SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION=0x41E750,
                      SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION_END=0x41E770)
        with patch.object(ownership, 'symbols', return_value=values):
            with self.assertRaisesRegex(ValueError, 'ownership overlaps'):
                ownership.audit()


if __name__ == '__main__':
    unittest.main()
