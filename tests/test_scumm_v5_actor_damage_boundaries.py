"""Execute controller source with sparse video ABI stubs; no ROM/emulator needed."""
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'runtime/snes/engines/scumm_v5_controller_far.pasm'
P = 'ScummV5_ActorPose_Compose'
M = 'SAME_SCUMM_ACTOR_'
D = 'SAME_VIDEO_SURFACE_DAMAGE_'


class ControllerMachine:
    def __init__(self, spans, foot=(50, 130), bounds=(-300, -200, 300, 200),
                 fail_capture=0, writable=True, visible=True, fail_draw=0, fail_commit=False):
        source = SOURCE.read_text()
        source = source[source.index(P + '_Far:'):]
        source = source[:source.index('\n    rtl', source.index(P + '__invalid:')) + 8]
        self.code, self.labels = [], {}
        for raw in source.splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
            else:
                self.code.append(line)
        self.mem = {
            M + 'POSE_STATE': 2, M + 'TICKET_ROOM_EPOCH': 7,
            'SAME_VIDEO_SURFACE_ROOM_GENERATION': 7,
            M + 'TICKET_COSTUME_EPOCH': 3, M + 'POSE_GENERATION': 3,
            M + 'CHUNK_COUNT': int(bool(spans)), M + 'SCRATCH_OWNER': 1,
            M + 'SPAN_LOCAL_OFFSET': 0, M + 'SPAN_COUNT': len(spans),
            M + 'TICKET_LENGTH': sum(s[2] for s in spans),
            'SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE': int(visible),
            'SAME_SCUMM_CONTROLLER_DESIRED_X': foot[0] & 65535,
            'SAME_SCUMM_CONTROLLER_DESIRED_Y': foot[1] & 65535,
        }
        for name, value in zip(('LEFT', 'TOP', 'RIGHT', 'BOTTOM'), bounds):
            self.mem[M + 'POSE_BOUNDS_' + name] = value & 65535
        offset = 0
        self.spans = []
        for x, y, length in spans:
            self.spans.append((x, y, offset, length))
            offset += length
        self.a, self.x, self.y = 0xBEEF, 0x1234, 0x5678
        self.initial = (self.a, self.x, self.y)
        self.width, self.iwidth = 8, 8
        self.c = self.z = self.n = self.v = False
        self.stack = [0x54, 0x90, 0xCA]  # caller's JSL frame
        self.events, self.captures, self.draws = [], [], []
        self.surface = bytearray((i * 17 + 3) & 255 for i in range(256 * 224))
        self.original = bytes(self.surface)
        self.fail_capture, self.fail_draw = fail_capture, fail_draw
        self.writable = writable
        self.fail_commit = fail_commit
        self.committed = False

    def push(self, value, width):
        if width == 16:
            self.stack.append(value >> 8)
        self.stack.append(value & 255)

    def pop(self, width):
        value = self.stack.pop()
        return value | (self.stack.pop() << 8) if width == 16 else value

    def operand(self, arg):
        if arg.startswith('#$'):
            return int(arg[2:], 16)
        if arg.startswith('#'):
            return {'SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR': 1,
                    'SCUMM_ERR_RESOURCE': 9,
                    '<SAME_SCUMM_ACTOR_POSE_BUFFER': 0,
                    '>SAME_SCUMM_ACTOR_POSE_BUFFER': 0,
                    'SAME_SCUMM_LIVE_ROOM_PENDING_BANK': 0x41}[arg[1:]]
        if arg == '1,s':
            return self.stack[-1] | self.stack[-2] << 8
        return self.mem.get(arg, 0)

    def service(self, name):
        if name == 'ScummV5_ActorPose_LoadSpan_Far':
            span = self.spans[self.mem[M + 'SPAN_CURSOR'] // 8]
            for field, value in zip(('X', 'Y', 'SOURCE', 'LENGTH'), span):
                self.mem[M + 'SPAN_' + field] = value & 65535
        elif name == 'ScummV5_ActorPose_ReleaseBuffer_Far':
            self.events.append('release')
        elif name == 'Same_VideoSurface_CanWrite_Far':
            self.c = not self.writable
        elif name == 'Same_VideoSurface_BeginActorUnderlay_Far':
            self.events.append('begin')
            self.c = False
        elif name == 'Same_VideoSurface_CaptureActorRun_Far':
            self.events.append('capture')
            self.mem['SAME_VIDEO_SURFACE_DP_SOURCE'] = 0xDD
            self.mem['SAME_VIDEO_SURFACE_DP_SOURCE+$01'] = 0xEE
            self.mem['SAME_VIDEO_SURFACE_DP_SOURCE+$02'] = 0xFF
            self.c = len(self.captures) + 1 == self.fail_capture
            if not self.c:
                assert 1 <= self.x <= 256
                assert self.a % 256 + self.x <= 256
                assert self.a // 256 < 224
                self.captures.append((self.a, self.x, bytes(self.surface[self.a:self.a + self.x])))
        elif name == 'Same_VideoSurface_CommitActorUnderlay_Far':
            self.events.append('commit')
            self.mem['SAME_VIDEO_SURFACE_DP_SOURCE+$02'] = 0xDE
            self.committed = not self.fail_commit
            self.c = self.fail_commit
        elif name == 'Same_VideoSurface_BlitCheckedOpaqueRun_Far':
            assert [self.mem['SAME_VIDEO_SURFACE_DP_SOURCE' + suffix] for suffix in ('', '+$01', '+$02')] == [0, 0, 0x41], 'checked actor pointer not reset after commit'
            assert self.committed, 'draw before journal commit'
            assert len(self.captures) > len(self.draws), 'draw before all captures'
            self.events.append('draw')
            self.draws.append((self.a, self.x, self.y))
            self.c = len(self.draws) == self.fail_draw
            if not self.c:
                self.surface[self.a:self.a + self.x] = b'\xff' * self.x
        else:
            raise AssertionError(name)

    def run(self):
        pc = 0
        for _ in range(50000):
            line = self.code[pc]
            pc += 1
            op, _, arg = line.partition(' ')
            mask = (1 << self.width) - 1
            value = self.operand(arg) & mask
            result = None
            if op in ('rep', 'sep'):
                if value & 0x20:
                    self.width = 16 if op == 'rep' else 8
                if value & 0x10:
                    self.iwidth = 16 if op == 'rep' else 8
            elif op in ('lda', 'lda.l'):
                result = value
            elif op in ('sta', 'sta.l'):
                if arg == '1,s':
                    self.stack[-1], self.stack[-2] = self.a & 255, self.a >> 8
                else:
                    old = self.mem.get(arg, 0)
                    self.mem[arg] = (old & ~mask) | (self.a & mask)
            elif op == 'php':
                self.stack.append((0x20 if self.width == 8 else 0) |
                                  (0x10 if self.iwidth == 8 else 0) |
                                  int(self.c) | int(self.z) * 2 | int(self.n) * 128 | int(self.v) * 64)
            elif op == 'plp':
                flags = self.stack.pop()
                self.width = 8 if flags & 32 else 16
                self.iwidth = 8 if flags & 16 else 16
                self.c, self.z, self.n, self.v = (bool(flags & b) for b in (1, 2, 128, 64))
            elif op in ('pha', 'phx', 'phy'):
                self.push(getattr(self, op[-1]), self.width if op == 'pha' else self.iwidth)
            elif op in ('pla', 'plx', 'ply'):
                w = self.width if op == 'pla' else self.iwidth
                setattr(self, op[-1], self.pop(w))
            elif op == 'clc':
                self.c = False
            elif op == 'sec':
                self.c = True
            elif op in ('adc', 'adc.l', 'sbc', 'sbc.l'):
                a = self.a & mask
                subtract = op.startswith('sbc')
                result = a - value - int(not self.c) if subtract else a + value + int(self.c)
                self.c = result >= 0 if subtract else result > mask
                sign = 1 << (self.width - 1)
                self.v = bool(((a ^ value) if subtract else ~(a ^ value)) & (a ^ result) & sign)
            elif op in ('cmp', 'cmp.l'):
                self.c = (self.a & mask) >= value
                self.z = (self.a & mask) == value
                self.n = bool(((self.a & mask) - value) & (1 << (self.width - 1)))
            elif op in ('eor', 'and', 'ora', 'ora.l'):
                result = {'eor': lambda: self.a ^ value, 'and': lambda: self.a & value,
                          'ora': lambda: self.a | value, 'ora.l': lambda: self.a | value}[op]()
            elif op == 'dec':
                result = self.a - 1
            elif op == 'xba':
                self.a = (self.a & 255) << 8 | self.a >> 8
                self.z, self.n = (self.a & 255) == 0, bool(self.a & 128)
            elif op in ('tax', 'tay'):
                setattr(self, op[-1], self.a & ((1 << self.iwidth) - 1))
            elif op == 'jsl':
                self.service(arg)
            elif op in ('jmp', 'jml', 'brl', 'bra', 'bcc', 'bcs', 'bne', 'beq', 'bmi', 'bpl', 'bvc'):
                take = {'bcc': not self.c, 'bcs': self.c, 'bne': not self.z,
                        'beq': self.z, 'bmi': self.n, 'bpl': not self.n, 'bvc': not self.v}.get(op, True)
                if take:
                    pc = self.labels[arg]
            elif op == 'rtl':
                assert self.stack == [0x54, 0x90, 0xCA], self.stack
                assert (self.a, self.x, self.y) == self.initial
                assert self.width == self.iwidth == 8
                return self
            else:
                raise AssertionError(line)
            if result is not None:
                result &= mask
                self.a = (self.a & ~mask) | result
                self.z, self.n = result == 0, bool(result & (1 << (self.width - 1)))
        raise AssertionError('controller did not return')


class SparseControllerTests(unittest.TestCase):
    def test_displaced_sparse_runs_capture_before_any_draw_and_restore_exactly(self):
        vm = ControllerMachine([(-195, -114, 8), (-3, -114, 199), (10, 6, 2)], foot=(30, 130)).run()
        self.assertFalse(vm.c)
        self.assertEqual([(a, n) for a, n, _ in vm.captures], [(16 * 256 + 27, 199), (136 * 256 + 40, 2)])
        self.assertEqual([(a, n) for a, n, _ in vm.draws], [(a, n) for a, n, _ in vm.captures])
        self.assertLess(max(i for i, e in enumerate(vm.events) if e == 'capture'), vm.events.index('commit'))
        self.assertLess(vm.events.index('commit'), vm.events.index('draw'))
        for a, n, old in vm.captures:
            vm.surface[a:a+n] = old
        self.assertEqual(vm.surface, vm.original)
        self.assertEqual(vm.mem[M + 'POSE_COMPOSED'], 1)

    def test_full_width_and_left_clipping_reuse_exact_run_source(self):
        vm = ControllerMachine([(-10, 0, 276)], foot=(0, 20)).run()
        self.assertEqual(vm.draws, [(20 * 256, 256, 10)])
        self.assertEqual(vm.captures[0][:2], (20 * 256, 256))

    def test_capture_failure_never_commits_or_draws(self):
        vm = ControllerMachine([(0, 0, 2), (5, 1, 3)], fail_capture=2).run()
        self.assertTrue(vm.c)
        self.assertNotIn('commit', vm.events)
        self.assertNotIn('draw', vm.events)
        self.assertEqual(vm.surface, vm.original)
        self.assertEqual(vm.mem[M + 'POSE_COMPOSED'], 0)

    def test_commit_failure_never_draws_or_marks_complete(self):
        vm = ControllerMachine([(0, 0, 2)], fail_commit=True).run()
        self.assertTrue(vm.c)
        self.assertEqual(vm.draws, [])
        self.assertEqual(vm.mem[M + 'POSE_COMPOSED'], 0)
        self.assertEqual(vm.surface, vm.original)

    def test_projected_foot_overflow_rejected_before_begin(self):
        for field, value in [('SAME_VIDEO_SURFACE_DEST_X', 100),
                             ('SAME_VIDEO_SURFACE_SOURCE_X', -100)]:
            vm = ControllerMachine([(0, 0, 2)], foot=(32760, 0))
            vm.mem[field] = value & 65535
            vm.run()
            self.assertTrue(vm.c)
            self.assertNotIn('begin', vm.events)

    def test_late_invalid_span_rejected_before_begin(self):
        vm = ControllerMachine([(0, 0, 2), (0, 201, 3)]).run()
        self.assertTrue(vm.c)
        self.assertNotIn('begin', vm.events)
        self.assertEqual(vm.mem[M + 'POSE_COMPOSED'], 0)

    def test_signed_span_and_projection_overflows_fail_before_capture(self):
        cases = [([(32760, 0, 10)], (0, 0)),
                 ([(100, 0, 2)], (32700, 0)),
                 ([(0, -100, 2)], (0, -32700)),
                 ([(0, 0, 20)], (32760, 0))]
        for spans, foot in cases:
            with self.subTest(spans=spans, foot=foot):
                vm = ControllerMachine(spans, foot, (-32768, -32768, 32767, 32767)).run()
                self.assertTrue(vm.c)
                self.assertNotIn('begin', vm.events)

    def test_empty_hidden_offscreen_and_busy_balance_stack(self):
        for spans, options in [([], {}), ([(0, 0, 2)], {'visible': False}),
                               ([(0, 0, 2)], {'foot': (-100, -100)}),
                               ([(0, 0, 2)], {'writable': False})]:
            with self.subTest(options=options):
                vm = ControllerMachine(spans, **options).run()
                self.assertEqual(vm.draws, [])
                self.assertEqual(vm.c, options.get('writable') is False)

    def test_draw_retry_keeps_committed_journal_and_not_composed(self):
        vm = ControllerMachine([(0, 0, 2), (4, 1, 2)], fail_draw=2).run()
        self.assertTrue(vm.c)
        self.assertTrue(vm.committed)
        self.assertEqual(vm.mem[M + 'POSE_COMPOSED'], 0)
        for a, n, old in vm.captures:
            vm.surface[a:a+n] = old
        self.assertEqual(vm.surface, vm.original)

    def test_controller_uses_sparse_restore_and_sets_damage_after_compose(self):
        source = SOURCE.read_text()
        changed = source.split('ScummV5_Controller_RenderActor__compose_ready:', 1)[1].split('.else', 1)[0]
        self.assertIn('jsl Same_VideoSurface_RestoreActorUnderlay_Far', changed)
        self.assertNotIn('ScummV5_Controller_RestoreActorDamage:', source)
        finish = source.split('ScummV5_Controller_RenderActor__sparse_damage:', 1)[1].split('    .else', 1)[0]
        self.assertIn('lda.l ' + D + 'WIDTH', finish)
        self.assertIn('lda.l ' + D + 'HEIGHT', finish)
        self.assertIn('lda #$0000', finish)
        bounds = source.split('ScummV5_ActorPose_ValidateBounds_Far:', 1)[1].split('; Map checked', 1)[0]
        self.assertNotIn('#$7FE0', bounds)
        self.assertNotIn('#$7FC0', bounds)
        self.assertEqual(bounds.count('eor #$8000'), 4)


if __name__ == '__main__':
    unittest.main()
