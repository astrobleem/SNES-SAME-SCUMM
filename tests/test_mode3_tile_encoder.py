"""Execute the production gather leaf against the independent planar oracle.

This narrow source-instruction model checks the 65816 width/DBR/stack and
address contract. It is not a substitute for assembled native acceptance.
"""
from pathlib import Path
import random
import re
import unittest

from same.snes_surface import encode_snes_8bpp_tile

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = {
    'Same_Mode3_RowPlanes': 0xE768,
    'SAME_MODE3_WORK_TILE': 0x41E750,
    'SAME_MODE3_WORK_SOURCE': 0x41E752,
    'SAME_MODE3_WORK_COLUMN': 0x41E756,
    'SAME_MODE3_WORK_X0': 0x41E768,
    'SAME_MODE3_TILE_SCRATCH': 0x41E6B0,
    'SAME_BWRAM_SURFACE_BASE': 0x402000,
}


def execute(pixels, tile, initial_dbr):
    text = (ROOT / 'runtime/snes/services/video_mode3.pasm').read_text()
    text = text.split('Same_Mode3_EncodeTile:', 1)[1].split('Same_Mode3_CommitEncodedTile:', 1)[0]
    code, labels = [], {}
    for line in text.splitlines():
        line = line.split(';')[0].strip()
        if not line or line.startswith('.'): continue
        if line.endswith(':'): labels[line[:-1]] = len(code)
        else: code.append(line.split(None, 1))
    ram = {0x41E750: tile & 255, 0x41E751: tile >> 8}
    source = 0x402000 + (tile // 32) * 2048 + (tile % 32) * 8
    source_addresses = set()
    for y, row in enumerate(pixels):
        for x, value in enumerate(row):
            ram[source + y * 256 + x] = value
            source_addresses.add(source + y * 256 + x)
    a = x = y = carry = 0
    dbr = initial_dbr
    aw = 16
    stack, writes, reads = [], set(), set()
    zero = False
    pc = count = 0

    def expr(value):
        for key, address in SYMBOLS.items(): value = value.replace(key, str(address))
        value = re.sub(r'\$([0-9A-Fa-f]+)', r'0x\1', value)
        if re.search(r'[^0-9xA-Fa-f()+&\s]', value): raise AssertionError(value)
        return eval(value, {'__builtins__': {}}, {})

    def address(arg, op):
        offset = x if arg.endswith(',x') else 0
        if offset or arg.endswith(',x'): arg = arg[:-2]
        n = expr(arg) + offset
        return (dbr << 16) | (n & 65535) if op.endswith('.w') else n

    def read(n, width):
        reads.add(n)
        if width == 16: reads.add(n + 1)
        return ram.get(n, 0xA5) | (ram.get(n + 1, 0xA5) << 8 if width == 16 else 0)

    def write(n, value, width):
        ram[n] = value & 255; writes.add(n)
        if width == 16: ram[n + 1] = value >> 8; writes.add(n + 1)

    while True:
        count += 1
        if count > 10000: raise AssertionError('unbounded encoder')
        ins = code[pc]; pc += 1; op = ins[0]; arg = ins[1] if len(ins) > 1 else ''
        mask = (1 << aw) - 1
        if op == 'phb': stack.append(dbr)
        elif op == 'plb': dbr = stack.pop()
        elif op == 'pha':
            if aw == 16: stack.append(a >> 8)
            stack.append(a & 255)
        elif op == 'pla':
            a = stack.pop()
            if aw == 16: a |= stack.pop() << 8
        elif op == 'phx': stack.extend([x >> 8, x & 255])
        elif op == 'plx': x = stack.pop() | stack.pop() << 8
        elif op == 'rep':
            if expr(arg[1:]) & 0x20: aw = 16
        elif op == 'sep':
            if expr(arg[1:]) & 0x20: aw = 8
        elif op.startswith('lda'):
            value = expr(arg[1:]) if arg.startswith('#') else read(address(arg, op), aw)
            a = (a & 0xFF00 | value) if aw == 8 else value
        elif op.startswith('sta'): write(address(arg, op), a & mask, aw)
        elif op == 'and': a &= expr(arg[1:])
        elif op == 'asl': carry = bool(a & (1 << (aw - 1))); a = (a << 1) & mask
        elif op == 'lsr':
            carry = a & 1
            a = (a & ~mask) | ((a & mask) >> 1)
        elif op.startswith('rol'):
            n = address(arg, op); v = read(n, aw); old = carry
            carry = bool(v & (1 << (aw - 1))); write(n, ((v << 1) | old) & mask, aw)
        elif op == 'clc': carry = 0
        elif op.startswith('adc'):
            value = expr(arg[1:]) if arg.startswith('#') else read(address(arg, op), aw)
            value += (a & mask) + carry; carry = value > mask; a = value & mask
        elif op == 'tax': x = a & mask
        elif op == 'txa': a = x & mask
        elif op == 'tyx': x = y
        elif op == 'ldy': y = expr(arg[1:])
        elif op == 'inx': x = (x + 1) & 65535
        elif op == 'iny': y = (y + 1) & 65535
        elif op == 'dec': a = (a & ~mask) | ((a - 1) & mask); zero = (a & mask) == 0
        elif op == 'cpy': zero = y == expr(arg[1:])
        elif op == 'bne':
            if not zero: pc = labels[arg]
        elif op == 'beq':
            if zero: pc = labels[arg]
        elif op in ('bra', 'brl'): pc = labels[arg]
        elif op == 'rts': break
        else: raise AssertionError(ins)
    output = bytes(ram.get(0x41E6B0 + i, 0xA5) for i in range(64))
    allowed = set(range(0x41E6B0, 0x41E6F0)) | set(range(0x41E768, 0x41E770)) | {0x41E752, 0x41E753, 0x41E756}
    assert writes <= allowed, sorted(writes - allowed)
    assert reads & set(range(0x402000, 0x410000)) == source_addresses
    assert not stack and dbr == initial_dbr and aw == 16
    return output, count


class Mode3GatherTests(unittest.TestCase):
    def test_all_palette_values_and_dirty_prior_scratch(self):
        for value in range(256):
            pixels = [[value] * 8 for _ in range(8)]
            actual, count = execute(pixels, 895, 0x7E)
            self.assertEqual(actual, encode_snes_8bpp_tile(pixels))
            self.assertLess(count, 2500)

    def test_random_tiles_all_rows_and_bank_edges(self):
        rng = random.Random(0x65816)
        for tile in [0, 1, 31, 32, 863, 864, 895] + [rng.randrange(896) for _ in range(64)]:
            pixels = [[rng.randrange(256) for _ in range(8)] for _ in range(8)]
            self.assertEqual(execute(pixels, tile, rng.randrange(256))[0], encode_snes_8bpp_tile(pixels))

    def test_individual_bits_preserve_column_and_plane_order(self):
        for y in range(8):
            for x in range(8):
                pixels = [[0] * 8 for _ in range(8)]
                pixels[y][x] = 1 << ((x + y) % 8)
                self.assertEqual(execute(pixels, 33, 0)[0], encode_snes_8bpp_tile(pixels))
