"""Host oracle plus source-driven tests of the narrow SNES handoff decision."""
from pathlib import Path
import unittest

import test_scumm_v5_engine as oracle

ROOT = Path(__file__).resolve().parents[1]


def selected_handoff(chain, status):
    text = (ROOT / 'runtime/snes/engines/scumm_v5.pasm').read_text()
    text = text.split('ScummV5_Op_StartScript__locals_ready:', 1)[1]
    text = text[text.index('    lda.l SAME_SCUMM_C4_CHAIN_MODE'):]
    text = text.split('ScummV5_Op_StartScript__nested_ok:', 1)[0]
    lines = [s.split(';')[0].strip() for s in text.splitlines()]
    lines = [s for s in lines if s]
    labels = {s[:-1]: i for i, s in enumerate(lines) if s.endswith(':')}
    memory = {'SAME_SCUMM_C4_CHAIN_MODE': chain, 'SAME_SCUMM_STATUS': status}
    pc, a, zero = 0, 0, False
    while pc < len(lines):
        s = lines[pc]; pc += 1
        if s.endswith(':') or s.startswith('.'):
            continue
        op, operand = s.split(maxsplit=1)
        if op == 'lda.l':
            a = memory[operand]; zero = a == 0
        elif op == 'cmp':
            assert operand == '#SCUMM_VM_STOPPED'
            zero = a == 4
        elif op in ('bne', 'beq'):
            if (not zero if op == 'bne' else zero):
                pc = labels[operand]
        elif op == 'jsr':
            return operand
        else:
            raise AssertionError(s)
    raise AssertionError('no handoff')


class StartScriptReplacementTests(unittest.TestCase):
    def check_replacement_handoff(self, program):
        self.assertEqual(selected_handoff(0, 4), 'ScummV5_C4_RunAllocatedNoParent')
        # The existing no-parent path loads the initialized descriptor before
        # its first SaveCurrentSlot; no stale caller PC can be saved first.
        text = (ROOT / 'runtime/snes/engines/scumm_v5.pasm').read_text()
        body = text.split('ScummV5_C4_RunAllocatedNoParent:', 1)[1].split('ScummV5_C4_StopNumber:', 1)[0]
        self.assertLess(body.index('lda.l SAME_SCUMM_C4_SLOT_PC,x'), body.index('jsr ScummV5_Engine_RunSelected'))
        self.assertLess(body.index('jsr ScummV5_Engine_RunSelected'), body.index('jsr ScummV5_C4_SaveCurrentSlot'))
        self.assertNotIn('SAME_SCUMM_C4_PARENT_SLOT', body)
        # Execute the actual load/transfer prefix up to RunSelected. The old
        # shared interpreter is stopped at $002D; slot1 is its replacement.
        memory = {
            # Reproduce the reviewed case: the 16-bit operation counter's
            # high byte is nonzero before the byte-sized slot is loaded.
            'SAME_SCUMM_FRAME_OPS': 0x0100,
            'SAME_SCUMM_C4_LAST_ALLOCATED': 1,
            'SAME_SCUMM_C4_SLOT_STATUS': {1: 1},
            'SAME_SCUMM_C4_SLOT_PROGRAM': {1: program},
            'SAME_SCUMM_C4_SLOT_PC': {2: 0},
            'SAME_SCUMM_C4_SLOT_DELAY': {2: 0},
            'SAME_SCUMM_STATUS': 4,
            'SAME_SCUMM_PC': 0x2D,
        }
        a = x = 0
        a_width = 16
        x_width = 16
        first_tax_x = None
        for line in body.split('    jsr ScummV5_Engine_RunSelected', 1)[0].splitlines():
            line = line.split(';', 1)[0].strip()
            parts = line.split(maxsplit=1)
            if not parts or parts[0].startswith('.'):
                continue
            op = parts[0]
            if op == 'rep':
                mask = int(parts[1].removeprefix('#$'), 16)
                if mask & 0x20:
                    a_width = 16
                if mask & 0x10:
                    x_width = 16
            elif op == 'sep':
                mask = int(parts[1].removeprefix('#$'), 16)
                if mask & 0x20:
                    a_width = 8
                if mask & 0x10:
                    x_width = 8
            elif op == 'lda.l':
                operand = parts[1]
                value = memory[operand[:-2]][x] if operand.endswith(',x') else memory[operand]
                a = ((a & 0xFF00) | (value & 0xFF)) if a_width == 8 else value & 0xFFFF
            elif op == 'sta.l':
                if a_width == 8:
                    memory[parts[1]] = (memory.get(parts[1], 0) & 0xFF00) | (a & 0xFF)
                else:
                    memory[parts[1]] = a & 0xFFFF
            elif op == 'tax':
                x = a & (0xFF if x_width == 8 else 0xFFFF)
                if first_tax_x is None:
                    first_tax_x = x
            elif op == 'txa':
                a = x & (0xFF if a_width == 8 else 0xFFFF)
            elif op == 'and':
                mask = int(parts[1].removeprefix('#$'), 16)
                a &= mask if a_width == 16 else (0xFF00 | (mask & 0xFF))
            elif op == 'asl':
                a = (a << 1) & (0xFFFF if a_width == 16 else 0xFF)
            else:
                self.fail(f'unmodelled no-parent instruction: {line}')
        self.assertEqual(memory['SAME_SCUMM_PROGRAM_SELECT'], program)
        self.assertEqual(memory['SAME_SCUMM_PC'], 0)
        self.assertEqual(memory['SAME_SCUMM_STATUS'], 1)
        self.assertEqual(memory['SAME_SCUMM_C4_SLOT_PC'][2], 0)
        self.assertEqual(first_tax_x, 1)

    def test_primary_handoff(self):
        self.check_replacement_handoff(0xD0)

    def test_overflow_handoff(self):
        self.check_replacement_handoff(0xCF)

    def test_live_different_script_stays_nested(self):
        self.assertEqual(selected_handoff(0, 1), 'ScummV5_C4_RunNestedChild')
        oracle.ScummV5EngineTests().test_c4_script_lifecycle_locals_and_slot_reuse()

    def test_chain_keeps_no_parent_path(self):
        self.assertEqual(selected_handoff(1, 1), 'ScummV5_C4_RunAllocatedNoParent')
        oracle.ScummV5EngineTests().test_c6_chain_script_handoff_reuses_slot_and_never_resumes_caller()

    def test_host_self_replacement_starts_at_zero_and_never_resumes_old_activation(self):
        script = bytes.fromhex('48 0040 0100 0600 9a 0500 0040 a0 0a 0a 01 0100 ff 1a 0600 6300 a0')
        host = oracle.ScummV5EngineTests()._host(bytes.fromhex('0a 0a ff a0'), scripts={10: script})
        starts = []
        step = host.engine._step
        def observe(slot, context):
            if slot.number == 10 and slot.pc == 0:
                starts.append((slot, slot.locals[0], host.engine.state.scripts.index(slot)))
            return step(slot, context)
        host.engine._step = observe
        host.tick()
        self.assertEqual([(arg, index) for _, arg, index in starts], [(0, 1), (1, 1)])
        self.assertIsNot(starts[0][0], starts[1][0])
        self.assertFalse(starts[0][0].active)
        variables = host.engine.inspect_state()['variables']
        self.assertEqual(variables['5'], 1)
        self.assertEqual(variables.get('6', 0), 0)
