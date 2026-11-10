"""Execute production movement completion instructions; no native/emulator run."""
import unittest

from test_video_surface_sparse_underlay import ROOT, ServiceMachine
import test_scumm_v5_room as room_tests
from same.engines.scumm_v5.engine import ActorState
from same.engines.scumm_v5.room import ScummV5RoomAdapter

PREFIX = 'ScummV5_Movement_'


class MovementMachine(ServiceMachine):
    def __init__(self, renderer=True):
        super().__init__()
        source = (ROOT / 'runtime/snes/engines/scumm_v5_matrix_far.pasm').read_text()
        self.code, self.labels = [], {}
        # Extract real completion, stand helper and direction conversion. No
        # movement/animation result is mocked; unrelated planning is a boundary.
        sections = [source[source.index(PREFIX + 'UpdateActor_Far__after_step:'):
                           source.index(PREFIX + 'UpdateActor_Far__not_last:')],
                    source[source.index(PREFIX + 'StartStand:'):
                           source.index(PREFIX + 'CalcFactor_Far:')],
                    source[source.index(PREFIX + 'OldToNewDir_Far:'):
                           source.index(PREFIX + 'OldToNewDir_Far__south:')] +
                    PREFIX + 'OldToNewDir_Far__south:' +
                    source.split(PREFIX + 'OldToNewDir_Far__south:', 1)[1].split('rts', 1)[0] + 'rts']
        enabled = True
        for raw in '\n'.join(sections).splitlines():
            line = raw.split(';', 1)[0].strip()
            if line == '.if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER':
                enabled = renderer
            elif line == '.endif':
                enabled = True
            elif not enabled or not line or line.startswith('.'):
                continue
            elif line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
            else:
                self.code.append(line)

    def execute(self, label, p=0x08):
        a, x, y, db = 0xBEEF, 0x56, 0x78, 0x91
        initial = (a, x, y, p, db)
        stack, returns = [], []
        pc = self.labels[PREFIX + label]
        def push(v, bits):
            if bits == 16:
                stack.append(v >> 8)
            stack.append(v & 255)
        def pop(bits):
            v = stack.pop()
            return v | (stack.pop() << 8) if bits == 16 else v
        def flags(v, bits):
            nonlocal p
            p = (p & ~0x82) | (2 if v == 0 else 0) | (128 if v & (1 << (bits-1)) else 0)
        for _ in range(500):
            line = self.code[pc]
            pc += 1
            op, _, arg = line.partition(' ')
            bits, ibits = (8 if p & 32 else 16), (8 if p & 16 else 16)
            mask = (1 << bits)-1
            value = address = result = None
            if arg.startswith('#'):
                value = self.value(arg[1:])
            elif '.l' in op:
                address = self.value(arg.removesuffix(',x')) + (x if arg.endswith(',x') else 0)
                value = self.get(address, bits//8)
            if op == 'php': push(p, 8)
            elif op == 'pha': push(a, bits)
            elif op == 'phx': push(x, ibits)
            elif op == 'phy': push(y, ibits)
            elif op == 'plp': p = pop(8)
            elif op == 'pla': result = pop(bits)
            elif op == 'plx': x = pop(ibits); flags(x, ibits)
            elif op == 'ply': y = pop(ibits); flags(y, ibits)
            elif op == 'rep': p &= ~value
            elif op == 'sep': p |= value
            elif op == 'clc': p &= ~1
            elif op in ('lda', 'lda.l'): result = value
            elif op == 'sta.l':
                self.put(address, a & mask, bits//8)
                self.writes.append((address, bits//8))
            elif op == 'tax': x = a & ((1 << ibits)-1); flags(x, ibits)
            elif op in ('and', 'and.l'): result = a & value
            elif op == 'eor': result = a ^ value
            elif op in ('asl', 'lsr'):
                p = (p & ~1) | ((a >> (bits-1)) & 1 if op == 'asl' else a & 1)
                result = (a & mask) << 1 if op == 'asl' else (a & mask) >> 1
            elif op == 'dex': x = (x-1) & ((1 << ibits)-1); flags(x, ibits)
            elif op in ('cmp', 'cpx'):
                v, b = (x, ibits) if op == 'cpx' else (a & mask, bits)
                p = (p & ~1) | int(v >= value)
                flags((v-value) & ((1 << b)-1), b)
            elif op == 'jsr': returns.append(pc); pc = self.labels[arg]
            elif op == 'rts':
                if returns: pc = returns.pop()
                else:
                    assert not stack
                    return initial, (a, x, y, p, db)
            elif op in ('beq', 'bne'):
                if bool(p & 2) == (op == 'beq'):
                    if arg.endswith('__not_last'):
                        assert not stack and not returns
                        return 'intermediate'
                    pc = self.labels[arg]
            else: raise AssertionError(line)
            if result is not None:
                result &= mask
                a = (a & ~mask) | result
                flags(result, bits)
        raise AssertionError('instruction bound exceeded')

    def seed(self, actor, stand=9):
        self.put('SAME_SCUMM_MOVE_ACTOR', actor, 1)
        base = self.symbols['SAME_SCUMM_C14_ACTORS'] + actor*64
        self.put(base + self.symbols['SAME_SCUMM_C14_A_STAND_FRAME'], stand, 1)
        self.put(base + self.symbols['SAME_SCUMM_C14_A_ANIMATION'], 0xF6, 1)
        self.put('SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION', 0xFFFFFFFF, 4)
        return base + self.symbols['SAME_SCUMM_C14_A_ANIMATION']


class MovementStandTests(unittest.TestCase):
    def test_all_actors_widths_flags_and_context(self):
        for renderer in (False, True):
            m = MovementMachine(renderer)
            for actor in range(32):
                for p in (0, 0x08, 0x31, 0xEF):
                    address = m.seed(actor)
                    before = bytes(m.ram)
                    m.writes.clear()
                    initial, final = m.execute('StartStand', p)
                    self.assertEqual(final, initial)
                    self.assertEqual(m.get(address, 1), 9)
                    bits = m.get('SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION', 4)
                    self.assertEqual(bits, 0xFFFFFFFF ^ (1 << actor) if renderer else 0xFFFFFFFF)
                    allowed = {address}
                    if renderer:
                        allowed.add(m.symbols['SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION'] + actor//8)
                    self.assertTrue(all(addr in allowed and size == 1 for addr, size in m.writes))
                    # Verify all other memory, including MOVE/C14 scratch, unchanged.
                    restored = bytearray(m.ram)
                    for addr in allowed: restored[addr] = before[addr]
                    self.assertEqual(restored, before)

    def test_finish_preserves_final_facing_and_clears_only_own_bit(self):
        m = MovementMachine()
        for actor in (0, 1, 7, 8, 15, 16, 31):
            for olddir, expected in ((255, 123), (0, 270), (1, 90), (2, 180), (3, 0)):
                address = m.seed(actor, 7)
                for name, value in (('C31_MOVING', 8), ('PUT_ACTOR_DESTBOX', 5),
                                    ('PUT_ACTOR_WALKBOX', 2), ('MOVE_FINAL_OLD_DIR', olddir)):
                    m.put(m.symbols['SAME_SCUMM_' + name] + actor, value, 1)
                facing = m.symbols['SAME_SCUMM_ACTOR_FACINGS'] + actor*2
                m.put(facing, 123)
                m.execute('UpdateActor_Far__after_step')
                self.assertEqual(m.get(address, 1), 7)
                self.assertEqual(m.get(m.symbols['SAME_SCUMM_C31_MOVING']+actor, 1), 0)
                self.assertEqual(m.get(m.symbols['SAME_SCUMM_PUT_ACTOR_WALKBOX']+actor, 1), 5)
                self.assertEqual(m.get(facing), expected)

    def test_intermediate_leg_does_not_start_stand(self):
        m = MovementMachine()
        address = m.seed(1)
        m.put(m.symbols['SAME_SCUMM_C31_MOVING']+1, 0, 1)
        self.assertEqual(m.execute('UpdateActor_Far__after_step'), 'intermediate')
        self.assertEqual(m.get(address, 1), 0xF6)
        self.assertEqual(m.get('SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION', 4), 0xFFFFFFFF)

    def test_host_finish_resets_chore_even_when_stand_equals_walk(self):
        fixture = room_tests.ScummV5RawRoomTests()
        host = fixture._matrix_host(bytes((0x80,)), None)
        adapter = ScummV5RoomAdapter(host.context)
        adapter.render('room.1', room_data=room_tests.raw_room(bytes((1,)) + bytes(range(16))))
        engine = host.engine
        engine._video = adapter
        engine.state.current_room = 1
        for actor_id, stand in ((1, 3), (8, 2), (31, 9)):
            actor = ActorState(room=1, moving=8, walk_destination_box=0,
                               stand_frame=stand, walk_frame=2, costume_frame=2,
                               costume_step=5, animation_progress=7)
            engine.state.actors[actor_id] = actor
            engine._advance_actor_movement()
            self.assertEqual((actor.moving, actor.costume_frame, actor.costume_step,
                              actor.animation_progress), (0, stand, 0, 0))


if __name__ == '__main__':
    unittest.main()
