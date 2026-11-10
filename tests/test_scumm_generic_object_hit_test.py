"""Execute the generator's literal instruction sequence, not a Python hit oracle."""
import ast
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT/'tools/generate_snes_cooked_rooms.py'
PREFIX = 'ScummV5_Generic_Object_'


def generated_instructions():
    tree = ast.parse(GENERATOR.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'extend' and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Tuple) and any(isinstance(v, ast.Constant) and v.value == PREFIX+'HitTest_Far:' for v in arg.elts):
                lines = ast.literal_eval(arg)
                return lines[:lines.index('ScummV5_Generic_Verb_First_Far:')]
    raise AssertionError('generator instruction tuple missing')


class HitMachine:
    def __init__(self):
        self.symbols = {}
        text = (ROOT/'runtime/snes/kernel/memory.pasm').read_text()
        for name, value in re.findall(r'^(SAME_\w+)\s*=\s*\$([0-9A-Fa-f]+)\b', text, re.M):
            self.symbols[name] = int(value, 16)
        self.code, self.labels = [], {}
        for line in generated_instructions():
            line = line.strip()
            if line.startswith('.'): continue
            if line.endswith(':'): self.labels[line[:-1]] = len(self.code)
            else: self.code.append(line)
        self.ops = []
        for line in self.code:
            op, _, arg = line.partition(' ')
            value = None
            if arg.startswith('#'):
                value = int(arg[2:], 16)
            elif '.l' in op:
                expression = re.sub(r'SAME_\w+', lambda m: str(self.symbols[m[0]]),
                                    arg.removesuffix(',x'))
                value = eval(expression, {'__builtins__': {}}, {})
            self.ops.append((op, arg, value, arg.endswith(',x'),
                             'SAME_SCUMM_SETSTATE_LOCAL_RECORDS' in arg))
        self.mem = {}
        self.base = self.symbols['SAME_SCUMM_SETSTATE_LOCAL_RECORDS']

    def put(self, name, value, size=2):
        address = self.symbols[name] if isinstance(name, str) else name
        for i in range(size): self.mem[address+i] = (value >> (i*8)) & 255

    def get(self, name, size=2):
        address = self.symbols[name] if isinstance(name, str) else name
        return sum(self.mem.get(address+i, 0) << (8*i) for i in range(size))

    def run(self, count, dirty, point, selected=None):
        self.put('SAME_SCUMM_SETSTATE_LOCAL_COUNT', count, 1)
        self.put('SAME_SCUMM_SETSTATE_DIRTY_COUNT', dirty, 1)
        self.put('SAME_SCUMM_INTERACTION_X', point[0])
        self.put('SAME_SCUMM_INTERACTION_Y', point[1])
        self.put('SAME_SCUMM_CONTROLLER_OBJECT', selected or 0)
        self.reads = []
        # Disjoint records with half-open 2x3 rectangles and varied flags.
        for i in range(count):
            record = struct.pack('<HHHHHB', i+1, i*3, 20, 2, 3, (i+129)&255)
            for offset, value in enumerate(record): self.mem[self.base+i*11+offset] = value
        a, x, y, width, iw, carry, zero = 0xABCD, 0, 0, 8, 8, False, False
        pc = self.labels[PREFIX+('ValidateSelected' if selected is not None else 'HitTest')+'_Far']
        for _ in range(20000):
            op, arg, operand, indexed, table_read = self.ops[pc]; pc += 1
            mask = (1 << width)-1
            value, address, result = operand, None, None
            if '.l' in op:
                address = operand + (x if indexed else 0)
                if op != 'sta.l':
                    if table_read:
                        assert self.base <= address and address+width//8 <= self.base+count*11, (op, arg, count, dirty, address-self.base, width)
                        self.reads.append((address-self.base, width//8))
                    value = self.get(address, width//8)
            if op in ('rep', 'sep'):
                if value & 32: width = 16 if op == 'rep' else 8
                if value & 16: iw = 16 if op == 'rep' else 8
            elif op in ('lda', 'lda.l'): result = value
            elif op == 'ldx': x = value
            elif op == 'ldy': y = value
            elif op == 'sta.l': self.put(address, a & mask, width//8)
            elif op == 'tya': result = y
            elif op == 'txa': result = x
            elif op == 'tax': x = a & ((1 << iw)-1)
            elif op == 'iny': y = (y+1) & ((1 << iw)-1)
            elif op == 'and': result = a & value
            elif op in ('adc', 'adc.l'):
                result = (a & mask)+value+carry
                carry = result > mask
            elif op in ('cmp', 'cmp.l'):
                carry, zero = (a & mask) >= value, (a & mask) == value
            elif op == 'clc': carry = False
            elif op == 'sec': carry = True
            elif op in ('bne', 'beq', 'bcc', 'bcs', 'brl'):
                if {'bne': not zero, 'beq': zero, 'bcc': not carry, 'bcs': carry}.get(op, True): pc = self.labels[arg]
            elif op == 'rtl':
                assert width == 8 and iw == 16
                return carry, self.get('SAME_SCUMM_INTERACTION_OBJECT')
            else: raise AssertionError((op, arg))
            if result is not None:
                a = (a & ~mask) | (result & mask)
                zero = (a & mask) == 0
        raise AssertionError('hit loop failed to terminate')


class GenericObjectHitTests(unittest.TestCase):
    def test_all_dirty_bytes_zero_one_and_full_table_misses_are_bounded(self):
        m = HitMachine()
        for count in (0, 1, 200):
            for dirty in range(256):
                self.assertEqual(m.run(count, dirty, (1000, 21)), (False, 0))
                if count == 0: self.assertEqual(m.reads, [])

    def test_all_dirty_bytes_first_and_last_hits_in_full_table(self):
        m = HitMachine()
        for dirty in range(256):
            for index in (0, 199):
                self.assertEqual(m.run(200, dirty, (index*3+1, 22)), (True, index+1))
                self.assertEqual(m.get('SAME_SCUMM_INTERACTION_INDEX', 1), index)
                self.assertEqual(m.get('SAME_SCUMM_INTERACTION_FLAGS', 1), (index+129)&255)

    def test_half_open_rectangle_edges_and_y_miss(self):
        m = HitMachine()
        for point, hit in (((0,20),True), ((1,22),True), ((2,21),False),
                           ((0,23),False), ((0,19),False)):
            self.assertEqual(m.run(1, 255, point), (hit, int(hit)))

    def test_adjacent_validate_selected_widening_and_last_flags_read(self):
        m = HitMachine()
        for dirty in range(256):
            for count, selected, hit in ((0,1,False),(200,1,True),(200,200,True),(200,201,False)):
                self.assertEqual(m.run(count, dirty, (0,0), selected), (hit, selected if hit else 0))


if __name__ == '__main__':
    unittest.main()
