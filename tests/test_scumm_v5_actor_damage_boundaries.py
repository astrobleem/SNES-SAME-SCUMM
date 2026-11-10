"""Evaluate the actual bounded damage helper, with RestoreRect as an ABI stub.

This is a source-level arithmetic/control-flow test, not a ROM/hardware test.
The oracle uses mathematical rectangles independently of the helper sequence.
"""
from pathlib import Path
import random
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'runtime/snes/engines/scumm_v5_controller_far.pasm'
PREFIX = 'ScummV5_Controller_Damage'
DAMAGE = 'SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_'
SURFACE = 'SAME_VIDEO_SURFACE_'


def evaluate(new, old=None, projection=(0, 0, 0, 0, 256, 224), fail_call=0):
    source = SOURCE.read_text()
    text = source.split('ScummV5_Controller_RestoreActorDamage:', 1)[1]
    text = text.split('\n.endif', 1)[0]
    code, labels = [], {}
    for raw in text.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line or line.startswith('.'):
            continue
        if line.endswith(':'):
            labels[line[:-1]] = len(code)
        else:
            code.append(line)
    memory = {}
    for role, point in [('DESIRED', new), ('RENDER', old or (0, 0))]:
        for axis, value in zip('XY', point):
            memory['SAME_SCUMM_CONTROLLER_' + role + '_' + axis] = value & 65535
    memory['SAME_SCUMM_CONTROLLER_RENDER_VALID'] = int(old is not None)
    for field, value in zip(('DEST_X', 'DEST_Y', 'SOURCE_X', 'SOURCE_Y', 'COPY_WIDTH', 'COPY_HEIGHT'), projection):
        memory[SURFACE + field] = value
    a = x = 0
    width = 16
    carry = zero = negative = False
    pc = 0
    stack, calls = [], []
    for _ in range(2000):
        line = code[pc]
        pc += 1
        op, _, arg = line.partition(' ')
        mask = (1 << width) - 1
        value = (int(arg[2:], 16) if arg.startswith('#$') else memory.get(arg, 0)) & mask
        result = None
        if op == 'rep':
            if value & 0x20:
                width = 16
        elif op == 'sep':
            if value & 0x20:
                width = 8
        elif op == 'lda.l' or op == 'lda':
            result = value
        elif op == 'sta.l':
            memory[arg] = a & mask
        elif op == 'clc':
            carry = False
        elif op == 'sec':
            carry = True
        elif op in ('adc', 'adc.l'):
            result = (a & mask) + value + int(carry)
            carry = result > mask
        elif op in ('sbc', 'sbc.l'):
            result = (a & mask) - value - int(not carry)
            carry = result >= 0
        elif op in ('cmp', 'cmp.l'):
            carry = (a & mask) >= value
            zero = (a & mask) == value
            negative = bool(((a & mask) - value) & (1 << (width - 1)))
        elif op in ('ora', 'ora.l'):
            result = (a & mask) | value
        elif op == 'dec':
            result = (a & mask) - 1
        elif op == 'xba':
            a = ((a & 255) << 8) | (a >> 8)
            zero, negative = (a & 255) == 0, bool(a & 128)
        elif op == 'tax':
            x = a
        elif op == 'jsr':
            stack.append(pc)
            pc = labels[arg]
        elif op == 'rts':
            if not stack:
                return memory, calls, carry
            pc = stack.pop()
        elif op in ('jmp', 'brl', 'bra', 'bcc', 'bcs', 'bne', 'beq', 'bmi'):
            take = {'bcc': not carry, 'bcs': carry, 'bne': not zero,
                    'beq': zero, 'bmi': negative}.get(op, True)
            if take:
                pc = labels[arg]
        elif op == 'jsl':
            assert arg == 'Same_VideoSurface_RestoreRect_Far'
            calls.append((a & 255, a >> 8, x & 255, x >> 8))
            # Documented clobbers; the helper must reconstruct the full union.
            for field in ('X', 'Y', 'WIDTH', 'HEIGHT'):
                memory[SURFACE + 'DAMAGE_' + field] = 0xDEAD
            a, x = 0xBEEF, 0xFACE
            carry = len(calls) == fail_call
        else:
            raise AssertionError('unhandled helper instruction: ' + line)
        if result is not None:
            result &= mask
            a = (a & ~mask) | result
            zero, negative = result == 0, bool(result & (1 << (width - 1)))
    raise AssertionError('helper did not return')


def expected(new, old, projection):
    dx, dy, sx, sy, width, height = projection
    boxes = [(x + dx - sx - 32, y + dy - sy - 64,
              x + dx - sx + 32, y + dy - sy + 8)
             for x, y in ([new, old] if old is not None else [new])]
    left = max(0, dx, min(b[0] for b in boxes))
    top = max(0, dy, min(b[1] for b in boxes))
    right = min(256, dx + width, max(b[2] for b in boxes))
    bottom = min(224, dy + height, max(b[3] for b in boxes))
    return None if right <= left or bottom <= top else (left, top, right-left, bottom-top)


class ActorDamageBoundaryTests(unittest.TestCase):
    def check_case(self, new, old=None, projection=(0, 0, 0, 0, 256, 224)):
        memory, calls, failed = evaluate(new, old, projection)
        self.assertFalse(failed)
        want = expected(new, old, projection)
        active = memory['SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_ACTIVE']
        if want is None:
            self.assertEqual((active, calls), (0, []))
            return
        self.assertEqual(active, 1)
        got = tuple(memory[SURFACE + 'DAMAGE_' + f] for f in ('X', 'Y', 'WIDTH', 'HEIGHT'))
        self.assertEqual(got, want)
        left, top, width, height = want
        self.assertEqual(calls, [(left, top, width, height)] if width < 256 else
                         [(0, top, 255, height), (255, top, 1, height)])
        self.assertTrue(all(0 < w <= 255 and 0 < h <= 224 for _, _, w, h in calls))

    def test_requested_top_left_move_both_directions(self):
        self.check_case((20, 40))
        self.check_case((80, 40), (20, 40))
        self.check_case((20, 40), (80, 40))

    def test_full_width_union_keeps_last_column(self):
        self.check_case((250, 120), (5, 120))
        self.check_case((5, 120), (250, 120))

    def test_offscreen_new_restores_old_visible_actor(self):
        for new in [(-100, 120), (400, 120), (120, -100), (120, 400)]:
            self.check_case(new, (120, 120))
            self.check_case(new)
            self.check_case(new, new)

    def test_one_pixel_and_viewport_intersections(self):
        for point in [(-31, 120), (287, 120), (120, -7), (120, 287)]:
            self.check_case(point)
        for viewport in [(0, 0, 0, 0, 1, 224), (255, 0, 255, 0, 1, 224),
                         (32, 24, 90, 10, 192, 176)]:
            self.check_case((250, 120), (5, 120), viewport)

    def test_restore_failure_returns_carry_without_publishing(self):
        for failed_call in (1, 2):
            memory, calls, failed = evaluate((250, 120), (5, 120), fail_call=failed_call)
            self.assertTrue(failed)
            self.assertEqual(len(calls), failed_call)
            self.assertNotIn('SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_ACTIVE', memory)

    def test_boundary_grid_against_geometric_oracle(self):
        rng = random.Random(571)
        xs = [-100, -32, -31, 0, 20, 31, 32, 224, 255, 256, 287, 288, 400]
        ys = [-100, -8, -7, 0, 40, 63, 64, 216, 223, 224, 287, 288, 400]
        for _ in range(300):
            new = rng.choice(xs), rng.choice(ys)
            old = (rng.choice(xs), rng.choice(ys)) if rng.randrange(2) else None
            self.check_case(new, old)

    def test_new_helper_is_actor_guarded_and_body_is_separate(self):
        source = SOURCE.read_text()
        start = source.index('; Signed screen endpoints')
        self.assertTrue(source[:start].rstrip().endswith('.if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER'))
        helper = source[start:source.index('\n.endif', start)]
        self.assertNotIn('SAME_SCUMM_ACTOR_', helper)
        self.assertNotIn('Compose_Far', helper)


if __name__ == '__main__':
    unittest.main()
