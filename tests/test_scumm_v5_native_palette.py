"""Execute palette_far's actual instruction stream with video-service ABI stubs.

No assembled ROM, native emulator, commercial data, or hardware-math oracle.
"""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'runtime/snes/engines/scumm_v5_palette_far.pasm'
SYMBOLS = {
    'SAME_SCUMM_ROOM_PALETTE_BASE': 0x400000,
    'SAME_SCUMM_ROOM_PALETTE_DESIRED': 0x400300,
    'SAME_SCUMM_ROOM_PALETTE_STATE': 0x400600,
    'SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE': 0x401084,
    'SAME_SCUMM_C10_INTENSITY': 0x7F3020,
    'SAME_SCUMM_C10_RGB_INTENSITY': 0x7F302A,
    'SAME_SCUMM_C10_PARAM0': 0x7F34F0,
    'SAME_SCUMM_C10_PARAM1': 0x7F34F2,
    'SAME_SCUMM_C10_PARAM2': 0x7F34F4,
    'SAME_SCUMM_CONDITION': 0x7E2347,
    'SAME_SCUMM_M23A_ACTIVE_ROOM': 0x7E3000,
    'SAME_VIDEO_SURFACE_PALETTE_SOURCE': 0x401060,
    'SAME_VIDEO_SURFACE_PALETTE_DIRTY': 0x401063,
    'SAME_VIDEO_SURFACE_NEXT_GENERATION': 0x401070,
}
BASE = SYMBOLS['SAME_SCUMM_ROOM_PALETTE_BASE']
DESIRED = SYMBOLS['SAME_SCUMM_ROOM_PALETTE_DESIRED']
STATE = SYMBOLS['SAME_SCUMM_ROOM_PALETTE_STATE']
STAGE = SYMBOLS['SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE']


class PaletteMachine:
    def __init__(self):
        self.symbols = dict(SYMBOLS)
        self.code, self.labels = [], {}
        for raw in SOURCE.read_text().splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'):
                continue
            if ' = ' in line:
                name, expression = line.split(' = ')
                self.symbols[name] = self.expression(expression)
            elif line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
            else:
                self.code.append(line)
        self.ops = []
        for line in self.code:
            op, _, arg = line.partition(' ')
            indexed = arg.endswith(',x')
            arg = arg.removesuffix(',x')
            immediate = arg.startswith('#')
            if op in ('jmp', 'bra', 'brl', 'bcc', 'bcs', 'bne', 'beq'):
                operand = self.labels[arg]
            elif op == 'jsl':
                operand = arg
            elif arg:
                operand = self.expression(arg.removeprefix('#'))
            else:
                operand = 0
            self.ops.append((op, operand, immediate, indexed))
        self.mem = {}
        self.live = bytes([0xE7] * 768)
        self.calls = []
        self.busy = self.install_failed = self.queue_failed = False
        self.queue_failure_advances_generation = False
        self.presentations = []
        self.write(STAGE, bytes((i * 17 + 3) & 255 for i in range(768)))
        self.write(SYMBOLS['SAME_SCUMM_M23A_ACTIVE_ROOM'], bytes((4,)))

    def expression(self, text):
        if text.startswith('<'):
            return self.expression(text[1:]) & 255
        if text.startswith('>'):
            return (self.expression(text[1:]) >> 8) & 255
        text = re.sub(r'\$([0-9A-Fa-f]+)', r'0x\1', text)
        text = re.sub(r'\bSAME_[A-Z0-9_]+\b', lambda m: str(self.symbols[m[0]]), text)
        return int(eval(text.replace('/', '//'), {'__builtins__': {}}, {}))

    def read(self, address, count):
        return bytes(self.mem.get(address + i, 0) for i in range(count))

    def write(self, address, data):
        for i, value in enumerate(data):
            self.mem[address + i] = value

    def word(self, symbol, value):
        self.write(self.symbols[symbol], value.to_bytes(2, 'little'))

    def entry(self, name, flags=0x39):
        # D is initially set by default. All arithmetic must execute in binary.
        self.a, self.x, self.y, self.db, self.p = 0xBEEF, 0x34, 0x56, 0x73, flags
        initial = (self.a, self.x, self.y, self.db, self.p)
        self.stack = [0x56, 0x90, 0xCA]
        self.c = bool(flags & 1)
        self.z = bool(flags & 2)
        self.n = bool(flags & 128)
        self.w = 8 if flags & 32 else 16
        self.iw = 8 if flags & 16 else 16
        pc = self.labels['ScummV5_Palette_' + name + '_Far']
        returns = []

        def push(value, width):
            if width == 16:
                self.stack.append(value >> 8)
            self.stack.append(value & 255)

        def pop(width):
            value = self.stack.pop()
            return value | self.stack.pop() << 8 if width == 16 else value

        for _ in range(2000000):
            op, operand, imm, indexed = self.ops[pc]
            pc += 1
            mask = (1 << self.w) - 1
            result = None
            address = operand + self.x if indexed else operand
            if op == 'php':
                push(self.p, 8)
            elif op == 'plp':
                self.p = pop(8)
                self.w = 8 if self.p & 32 else 16
                self.iw = 8 if self.p & 16 else 16
                self.c = bool(self.p & 1)
            elif op == 'cld':
                self.p &= ~8
            elif op in ('rep', 'sep'):
                if op == 'rep':
                    self.p &= ~operand
                else:
                    self.p |= operand
                self.w = 8 if self.p & 32 else 16
                self.iw = 8 if self.p & 16 else 16
            elif op in ('pha', 'phx', 'phy', 'phb'):
                reg = 'db' if op == 'phb' else op[-1]
                push(getattr(self, reg), 8 if op == 'phb' else self.w if op == 'pha' else self.iw)
            elif op in ('pla', 'plx', 'ply', 'plb'):
                reg = 'db' if op == 'plb' else op[-1]
                setattr(self, reg, pop(8 if op == 'plb' else self.w if op == 'pla' else self.iw))
            elif op in ('lda', 'lda.l', 'ldx'):
                width = self.iw if op == 'ldx' else self.w
                value = operand if imm else int.from_bytes(self.read(address, width // 8), 'little')
                if op == 'ldx':
                    self.x = value
                    self.z = value == 0
                else:
                    result = value
            elif op == 'sta.l':
                self.write(address, (self.a & mask).to_bytes(self.w // 8, 'little'))
            elif op == 'clc':
                self.c = False
            elif op in ('adc', 'adc.l'):
                assert not self.p & 8, 'decimal arithmetic leaked into palette'
                value = operand if imm else int.from_bytes(self.read(address, self.w // 8), 'little')
                result = (self.a & mask) + value + int(self.c)
                self.c = result > mask
            elif op in ('cmp', 'cmp.l', 'cpx'):
                value = operand if imm else int.from_bytes(self.read(address, self.w // 8), 'little')
                actual = self.x if op == 'cpx' else self.a & mask
                self.c, self.z = actual >= value, actual == value
            elif op == 'and':
                result = self.a & operand
            elif op in ('asl', 'lsr'):
                self.c = bool(self.a & (1 << (self.w - 1))) if op == 'asl' else bool(self.a & 1)
                result = (self.a & mask) << 1 if op == 'asl' else (self.a & mask) >> 1
            elif op in ('inc', 'dec'):
                result = self.a + (1 if op == 'inc' else -1)
            elif op == 'inx':
                self.x = (self.x + 1) & ((1 << self.iw) - 1)
                self.z = self.x == 0
            elif op == 'tax':
                self.x = self.a & ((1 << self.iw) - 1)
                self.z = self.x == 0
            elif op == 'txa':
                result = self.x
            elif op == 'xba':
                self.a = (self.a & 255) << 8 | self.a >> 8
            elif op in ('jmp', 'bra', 'brl', 'bcc', 'bcs', 'bne', 'beq'):
                if {'bcc': not self.c, 'bcs': self.c, 'bne': not self.z, 'beq': self.z}.get(op, True):
                    pc = operand
            elif op == 'jsl':
                if operand in self.labels:
                    returns.append(pc)
                    self.stack.extend([0x21, 0x88, 0x00])
                    pc = self.labels[operand]
                    continue
                self.calls.append(operand)
                if operand == 'Same_VideoSurface_CanWrite_Far':
                    self.c = self.busy
                elif operand == 'Same_VideoSurface_InstallPalette_Far':
                    pointer = int.from_bytes(self.read(SYMBOLS['SAME_VIDEO_SURFACE_PALETTE_SOURCE'], 3), 'little')
                    assert pointer == DESIRED
                    self.c = self.install_failed
                    if not self.c:
                        self.live = self.read(pointer, 768)
                        self.write(SYMBOLS['SAME_VIDEO_SURFACE_PALETTE_DIRTY'], b'\x01')
                elif operand == 'Same_VideoSurface_PushPalettePresent_Far':
                    assert self.a & 255 == 4
                    self.c = self.queue_failed
                    if self.c and self.queue_failure_advances_generation:
                        self.advance_generation()
                    if not self.c:
                        self.scene_present()
                else:
                    raise AssertionError(operand)
                # Service ABI may clobber these; the public producer restores all.
                self.a, self.x, self.y, self.db = 0xABCD, 0x1234, 0x5678, 0x40
            elif op == 'rtl':
                if returns:
                    assert self.stack[-3:] == [0x21, 0x88, 0x00]
                    del self.stack[-3:]
                    pc = returns.pop()
                    continue
                assert self.stack == [0x56, 0x90, 0xCA]
                assert (self.a, self.x, self.y, self.db, self.p) == initial
                return
            else:
                raise AssertionError(op)
            if result is not None:
                result &= mask
                self.a = (self.a & ~mask) | result
                self.z, self.n = result == 0, bool(result & (1 << (self.w - 1)))
        raise AssertionError('palette source did not terminate')

    def scene_present(self):
        """Service queues PALETTE_WRITE when dirty, then accepts PRESENT."""
        assert not self.busy
        self.advance_generation()
        self.presentations.append(self.live)
        self.write(SYMBOLS['SAME_VIDEO_SURFACE_PALETTE_DIRTY'], b'\x00')
        self.busy = True

    def advance_generation(self):
        generation = int.from_bytes(self.read(SYMBOLS['SAME_VIDEO_SURFACE_NEXT_GENERATION'], 2), 'little')
        self.word('SAME_VIDEO_SURFACE_NEXT_GENERATION', ((generation + 1) & 65535) or 1)


class NativePaletteTests(unittest.TestCase):
    def test_install_exactly_768_bytes_and_all_entries_preserve_decimal_registers(self):
        for flags in (0x08, 0x19, 0x28, 0x39):
            vm = PaletteMachine()
            vm.write(STATE + 28, bytes([0xBD] * 4))
            vm.entry('InstallRoom', flags)
            self.assertEqual(vm.read(BASE, 768), vm.read(STAGE, 768))
            self.assertEqual(vm.read(DESIRED, 768), vm.read(STAGE, 768))
            self.assertEqual(vm.read(STATE, 2), b'\x01\x00')
            for entry in ('SetColor', 'Intensity', 'RgbIntensity', 'Prepare', 'Flush'):
                vm.entry(entry, flags)
            self.assertEqual(vm.read(STATE + 28, 4), bytes([0xBD] * 4))

    def test_invalid_zero_is_noop_for_all_mutations_and_flush(self):
        vm = PaletteMachine()
        before = dict(vm.mem)
        for name in ('SetColor', 'Intensity', 'RgbIntensity', 'Prepare', 'Flush'):
            vm.entry(name)
        self.assertEqual(vm.mem, before)
        self.assertEqual(vm.calls, [])

    def test_every_base_byte_at_boundary_scales_matches_v5_formula(self):
        vm = PaletteMachine()
        original = bytes(v for v in range(256) for _ in range(3))
        vm.write(STAGE, original)
        vm.entry('InstallRoom')
        for scale in (0, 1, 55, 127, 128, 254, 255):
            vm.write(SYMBOLS['SAME_SCUMM_C10_INTENSITY'], bytes((scale, scale, scale, 0, 255)))
            vm.entry('Intensity')
            self.assertEqual(vm.read(DESIRED, 768), bytes(min(252, v * scale // 255) for v in original))
            self.assertEqual(vm.read(BASE, 768), original)
            self.assertEqual(vm.mem[STATE + 1], 1)

    def test_direct_colors_do_not_change_base_and_intensity_is_not_cumulative(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        original = vm.read(BASE, 768)
        vm.write(SYMBOLS['SAME_SCUMM_CONDITION'], b'\xff\xa5')
        for i, value in enumerate((255, 1, 253)):
            vm.word(f'SAME_SCUMM_C10_PARAM{i}', value)
        vm.entry('SetColor')
        self.assertEqual(vm.read(DESIRED + 765, 3), bytes((255, 1, 253)))
        vm.write(SYMBOLS['SAME_SCUMM_C10_RGB_INTENSITY'], bytes((255, 128, 0, 255, 255)))
        for _ in range(2):
            vm.entry('RgbIntensity')
            self.assertEqual(vm.read(DESIRED + 765, 3), bytes((min(252, original[765]), original[766] * 128 // 255, 0)))
        self.assertEqual(vm.read(BASE, 768), original)
        self.assertEqual(vm.read(DESIRED, 765), original[:765])

    def test_invalid_range_or_color_does_not_mutate_desired(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        original = vm.read(DESIRED, 768)
        for symbol, entry in [('SAME_SCUMM_C10_INTENSITY', 'Intensity'),
                              ('SAME_SCUMM_C10_RGB_INTENSITY', 'RgbIntensity')]:
            vm.write(SYMBOLS[symbol], bytes((0, 0, 0, 9, 2)))
            vm.entry(entry)
            self.assertEqual(vm.read(DESIRED, 768), original)
            self.assertEqual(vm.mem[STATE + 1], 0)
        for i in range(3):
            for j in range(3):
                vm.word(f'SAME_SCUMM_C10_PARAM{j}', 256 if i == j else 1)
            vm.entry('SetColor')
            self.assertEqual(vm.read(DESIRED, 768), original)
            self.assertEqual(vm.mem[STATE + 1], 0)

    def test_busy_install_failure_and_queue_failure_retain_pending_and_desired(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        vm.word('SAME_SCUMM_C10_PARAM0', 252)
        vm.entry('SetColor')
        base, desired, old_live = vm.read(BASE, 768), vm.read(DESIRED, 768), vm.live
        vm.busy = True
        vm.entry('Flush')
        self.assertEqual(vm.calls, ['Same_VideoSurface_CanWrite_Far'])
        self.assertEqual(vm.live, old_live)
        self.assertEqual(vm.mem[STATE + 1], 1)
        vm.busy = False
        vm.install_failed = True
        vm.entry('Flush')
        self.assertEqual(vm.calls[-1], 'Same_VideoSurface_InstallPalette_Far')
        self.assertEqual(vm.mem[STATE + 1], 1)
        vm.install_failed = False
        vm.queue_failed = True
        vm.entry('Flush')
        self.assertEqual(vm.live, desired)
        self.assertEqual(vm.mem[STATE + 1], 2)
        self.assertEqual(vm.read(BASE, 768), base)
        self.assertEqual(vm.read(DESIRED, 768), desired)
        vm.queue_failed = False
        vm.entry('Flush')
        self.assertEqual(vm.mem[STATE + 1], 0)
        self.assertEqual(vm.calls[-2:], ['Same_VideoSurface_CanWrite_Far',
                                      'Same_VideoSurface_PushPalettePresent_Far'])
        count = len(vm.calls)
        vm.entry('Flush')
        self.assertEqual(len(vm.calls), count)

    def test_incoming_stage_does_not_replace_base_before_install(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        base = vm.read(BASE, 768)
        vm.write(STAGE, bytes([201] * 768))
        vm.write(SYMBOLS['SAME_SCUMM_C10_INTENSITY'], bytes((128, 128, 128, 0, 255)))
        vm.entry('Intensity')
        self.assertEqual(vm.read(DESIRED, 768), bytes(v * 128 // 255 for v in base))
        vm.entry('InstallRoom')
        self.assertEqual(vm.read(BASE, 768), bytes([201] * 768))
        self.assertEqual(vm.read(DESIRED, 768), bytes([201] * 768))
        self.assertEqual(vm.mem[STATE + 1], 0)

    def test_recurring_palette_intent_leaves_writable_pass_for_actor(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        for value in (9, 21, 87, 132):
            vm.busy = False  # previous scene conversion completed
            vm.word('SAME_SCUMM_C10_PARAM0', value)
            vm.entry('SetColor')
            before = int.from_bytes(vm.read(SYMBOLS['SAME_VIDEO_SURFACE_NEXT_GENERATION'], 2), 'little')
            vm.entry('Prepare')
            self.assertEqual(vm.mem[STATE+1], 2)
            self.assertEqual(int.from_bytes(vm.read(SYMBOLS['SAME_VIDEO_SURFACE_NEXT_GENERATION'], 2), 'little'), before)
            self.assertEqual(vm.read(SYMBOLS['SAME_VIDEO_SURFACE_PALETTE_DIRTY'], 1), b'\x01')
            self.assertFalse(vm.busy, 'palette prepare stole actor writable pass')
            self.assertNotIn('Same_VideoSurface_PushPalettePresent_Far', vm.calls)
            vm.scene_present()  # actor/cursor accepts the installed colors
            calls = len(vm.calls)
            vm.entry('Flush')
            self.assertEqual(len(vm.calls), calls)
            self.assertEqual(vm.mem[STATE+1], 0)
            self.assertEqual(vm.presentations[-1], vm.read(DESIRED, 768))
        self.assertEqual(len(vm.presentations), 4)

    def test_prepare_busy_and_failed_install_preserve_unprepared_intent(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        vm.word('SAME_SCUMM_C10_PARAM0', 42)
        vm.entry('SetColor')
        desired, live = vm.read(DESIRED, 768), vm.live
        vm.write(STATE+26, b'\xAD\xDE')
        for busy, failed in ((True, False), (False, True)):
            vm.busy, vm.install_failed = busy, failed
            vm.entry('Prepare')
            self.assertEqual(vm.mem[STATE+1], 1)
            self.assertEqual(vm.read(STATE+26, 2), b'\xAD\xDE')
            self.assertEqual(vm.live, live)
            self.assertEqual(vm.read(DESIRED, 768), desired)
            self.assertEqual(vm.presentations, [])
        vm.busy = vm.install_failed = False
        vm.entry('Prepare')
        count = len(vm.calls)
        vm.entry('Prepare')
        self.assertEqual(len(vm.calls), count, 'prepared colors were needlessly reinstalled')
        self.assertEqual(vm.live, desired)

    def test_new_intent_supersedes_prepared_even_after_prior_scene_present(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        vm.word('SAME_SCUMM_C10_PARAM0', 17)
        vm.entry('SetColor')
        vm.entry('Prepare')
        vm.scene_present()
        old_live = vm.live
        vm.word('SAME_SCUMM_C10_PARAM0', 99)
        vm.entry('SetColor')
        self.assertEqual(vm.mem[STATE+1], 1)
        vm.entry('Flush')  # busy; old generation cannot acknowledge new intent
        self.assertEqual(vm.mem[STATE+1], 1)
        self.assertEqual(vm.live, old_live)
        vm.busy = False
        vm.entry('Flush')
        self.assertEqual(vm.mem[STATE+1], 0)
        self.assertEqual(vm.presentations[-1], vm.read(DESIRED, 768))
        self.assertEqual(vm.presentations[-1][0], 99)
        self.assertEqual(len(vm.presentations), 2)

    def test_new_intensity_intent_also_replaces_prepared_state(self):
        for entry, symbol in (('Intensity','SAME_SCUMM_C10_INTENSITY'),
                              ('RgbIntensity','SAME_SCUMM_C10_RGB_INTENSITY')):
            vm = PaletteMachine()
            vm.entry('InstallRoom')
            vm.entry('SetColor')
            vm.entry('Prepare')
            vm.write(SYMBOLS[symbol], bytes((128, 64, 0, 0, 0)))
            vm.entry(entry)
            self.assertEqual(vm.mem[STATE+1], 1)
            vm.entry('Prepare')
            self.assertEqual(vm.mem[STATE+1], 2)
            self.assertEqual(vm.live, vm.read(DESIRED, 768))

    def test_generation_changes_never_acknowledge_dirty_palette(self):
        for before, after in ((10, 11), (65535, 1), (65535, 0), (0, 65535)):
            vm = PaletteMachine()
            vm.entry('InstallRoom')
            vm.entry('SetColor')
            vm.word('SAME_VIDEO_SURFACE_NEXT_GENERATION', before)
            vm.entry('Prepare')
            vm.word('SAME_VIDEO_SURFACE_NEXT_GENERATION', after)
            vm.busy = True
            vm.entry('Flush')
            self.assertEqual(vm.mem[STATE+1], 2)
            self.assertEqual(vm.read(SYMBOLS['SAME_VIDEO_SURFACE_PALETTE_DIRTY'], 1), b'\x01')
            vm.busy = False
            vm.entry('Flush')
            self.assertEqual(vm.mem[STATE+1], 0)
            self.assertEqual(len(vm.presentations), 1)

    def test_service_acknowledgement_does_not_need_generation_change(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        vm.entry('SetColor')
        vm.entry('Prepare')
        vm.write(SYMBOLS['SAME_VIDEO_SURFACE_PALETTE_DIRTY'], b'\x00')
        vm.busy = True
        count = len(vm.calls)
        vm.entry('Flush')
        self.assertEqual(len(vm.calls), count)
        self.assertEqual(vm.mem[STATE+1], 0)
        self.assertNotIn('NEXT_GENERATION', SOURCE.read_text())

    def test_failed_final_queue_push_generation_change_is_not_acknowledgement(self):
        vm = PaletteMachine()
        vm.entry('InstallRoom')
        vm.entry('SetColor')
        vm.word('SAME_VIDEO_SURFACE_NEXT_GENERATION', 65535)
        vm.queue_failed = vm.queue_failure_advances_generation = True
        vm.entry('Flush')
        self.assertEqual(vm.mem[STATE+1], 2)
        self.assertEqual(vm.read(SYMBOLS['SAME_VIDEO_SURFACE_PALETTE_DIRTY'], 1), b'\x01')
        vm.entry('Flush')
        self.assertEqual(vm.mem[STATE+1], 2)
        self.assertEqual(vm.read(SYMBOLS['SAME_VIDEO_SURFACE_PALETTE_DIRTY'], 1), b'\x01')
        self.assertEqual(vm.presentations, [])
        vm.queue_failed = False
        vm.entry('Flush')
        self.assertEqual(vm.mem[STATE+1], 0)
        self.assertEqual(len(vm.presentations), 1)


if __name__ == '__main__':
    unittest.main()
