"""Copyright-free build binding and actual native admission instructions."""
import os
from pathlib import Path
import subprocess
import unittest

from same.engines.scumm_v5.font import encode_charset, decode_charset
from test_scumm_v5_font import _copyright_free_charset

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'runtime/snes/services/video_overlay_surface.pasm'
P = 'Same_VideoOverlay_'
STATUS = 'SAME_SCUMM_TALK_VISUAL_STATUS'
CHARSET = 'SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_CHARSET'
COLOR = 'SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR'


def admission(logical, requested, *, busy=False, flags=0, status=0, color=15):
    """Run the real producer prefix and CanWrite body until raster admission.

    Refuse unmodeled instructions/writes: rejected requests must not reach the
    HUD copy, work clear, descriptor or pixel writes. Not an assembler test.
    """
    source = OVERLAY.read_text()
    source = source[source.index(P + 'CanWrite_Far:'):
                    source.index(P + 'ShowTalkSegment__font_available:')]
    code, labels = [], {}
    for raw in source.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line or line.startswith('.'): continue
        if line.endswith(':'): labels[line[:-1]] = len(code)
        else: code.append(line)
    labels[P + 'ShowTalkSegment__font_available'] = len(code)
    record = encode_charset(_copyright_free_charset(), logical_id=logical, source_id=1)
    mem = {'SAME_FRAME_COUNTER': 0x1234, 'SAME_OVERLAY_STATE': int(busy),
           CHARSET: requested, STATUS: status, COLOR: color}
    a, x, p = 0xABCD, 0x7654, flags
    stack, calls, writes = [], [], []
    pc = labels[P + 'ShowTalkSegment_Far']
    for _ in range(100):
        if pc == len(code):
            assert stack == [flags] and not calls
            return True, mem, writes
        op, _, arg = code[pc].partition(' ')
        pc += 1
        width = 8 if p & 32 else 16
        mask = (1 << width)-1
        value = result = None
        if arg.startswith('#$'): value = int(arg[2:], 16)
        elif arg == '#SAME_OVERLAY_STATE_IDLE': value = 0
        elif arg == 'ScummV5_Font0_Record,x':
            value = int.from_bytes(record[x:x+width//8], 'little')
        elif arg in mem: value = mem[arg] & mask
        if op == 'php': stack.append(p)
        elif op == 'plp': p = stack.pop()
        elif op == 'rep': p &= ~value
        elif op == 'sep': p |= value
        elif op == 'ldx':
            x = value & (255 if p & 16 else 65535)
        elif op in ('lda', 'lda.l'): result = value
        elif op == 'sta.l':
            assert arg in ('SAME_OVERLAY_TRACE_S1', STATUS), 'write before admission: ' + arg
            mem[arg] = a & mask
            writes.append(arg)
        elif op in ('cmp', 'cmp.l'):
            p = (p & ~3) | int((a & mask) >= value) | (2 if (a & mask) == value else 0)
        elif op == 'inc': result = (a & mask)+1
        elif op == 'clc': p &= ~1
        elif op == 'sec': p |= 1
        elif op == 'jsl': calls.append(pc); pc = labels[arg]
        elif op == 'rtl':
            if calls: pc = calls.pop()
            else:
                assert not stack and p == flags
                return False, mem, writes
        elif op in ('bcc', 'bne', 'beq'):
            take = not p & 1 if op == 'bcc' else (bool(p & 2) == (op == 'beq'))
            if take: pc = labels[arg]
        else: raise AssertionError(op + ' ' + arg)
        if result is not None:
            a = (a & ~mask) | (result & mask)
            p = (p & ~2) | (2 if a & mask == 0 else 0)
    raise AssertionError('instruction bound exceeded')


class FontBindingTests(unittest.TestCase):
    def test_build_invocation_defaults_and_explicit_binding(self):
        source = (ROOT / 'tools/build_snes.sh').read_text()
        command = source.split('    "$PYTHON" tools/generate_snes_scumm_charset.py', 1)[1].split('\nelse', 1)[0]
        command = '"$PYTHON" tools/generate_snes_scumm_charset.py' + command
        for binding in ({}, {'SAME_SCUMM_FONT_SOURCE_ID': '1', 'SAME_SCUMM_FONT_LOGICAL_ID': '1'},
                        {'SAME_SCUMM_FONT_SOURCE_ID': '7', 'SAME_SCUMM_FONT_LOGICAL_ID': '3'}):
            env = {k: v for k, v in os.environ.items() if not k.startswith('SAME_')}
            env.update(PYTHON='capture', SAME_FATE_ARCHIVE='unused archive.zip', SAME_SNES_OUTPUT='unused.sfc')
            env.update(binding)
            script = "capture() { printf '%s\\0' \"$@\"; }\n" + command
            args = subprocess.check_output(['bash', '-c', script], env=env).decode().split('\0')[:-1]
            source_id = int(args[args.index('--source-id')+1])
            logical_id = int(args[args.index('--logical-id')+1])
            self.assertEqual(source_id, int(binding.get('SAME_SCUMM_FONT_SOURCE_ID', 1)))
            self.assertEqual(logical_id, int(binding.get('SAME_SCUMM_FONT_LOGICAL_ID', 0)))
            raw = encode_charset(_copyright_free_charset(), source_id=source_id, logical_id=logical_id)
            self.assertEqual(raw[7], logical_id)
            self.assertEqual(decode_charset(raw).source_id, source_id)

    def test_actual_guard_admits_only_matching_logical_id(self):
        for p in (0, 0x20, 0x10, 0x30):
            for logical in (0, 1, 3, 255):
                for requested in (0, 1, 2, 3, 255):
                    admitted, mem, writes = admission(logical, requested, flags=p, status=255)
                    self.assertEqual(admitted, logical == requested)
                    self.assertEqual(mem[STATUS], 255 if admitted else 2)
                    self.assertEqual(set(writes), {'SAME_OVERLAY_TRACE_S1'} if admitted else
                                     {'SAME_OVERLAY_TRACE_S1', STATUS})

    def test_busy_never_reaches_font_read_or_producer_writes(self):
        for logical, requested in ((0, 0), (1, 1), (1, 2)):
            admitted, mem, writes = admission(logical, requested, busy=True, status=2)
            self.assertFalse(admitted)
            self.assertEqual(mem[STATUS], 1)
            self.assertEqual(set(writes), {'SAME_OVERLAY_TRACE_S1', STATUS})

    def test_actual_group_zero_color_admission(self):
        for p in (0, 0x20, 0x10, 0x30):
            for color in (0, 1, 14, 15, 16, 127, 128, 178, 255):
                admitted, mem, writes = admission(1, 1, color=color, flags=p)
                self.assertEqual(admitted, 1 <= color <= 15)
                self.assertEqual(mem[STATUS], 0 if admitted else 2)
                self.assertEqual(mem[COLOR], color)
                self.assertEqual(set(writes), {'SAME_OVERLAY_TRACE_S1'} if admitted else
                                 {'SAME_OVERLAY_TRACE_S1', STATUS})

    def test_accepted_talk_executes_hud_retirement_before_publication(self):
        source = (ROOT / 'runtime/snes/engines/scumm_v5_matrix_far.pasm').read_text()
        block = source.split('ScummV5_Talk_Begin_Far__message_ready:', 1)[1]
        prefix = block.split('lda.l SAME_SCUMM_TALK_ACTIVE', 1)[0]
        for old in (0, 1, 255):
            memory = {'SAME_VIDEO_TEXT_CONTROLLER_VALID': old}
            a, width = 0xABCD, 16
            for raw in prefix.splitlines():
                line = raw.split(';', 1)[0].strip()
                if not line or line.startswith('.'): continue
                if line == 'sep #$20': width = 8
                elif line == 'lda #$00': a = 0
                elif line == 'sta.l SAME_VIDEO_TEXT_CONTROLLER_VALID':
                    self.assertEqual(width, 8)
                    memory['SAME_VIDEO_TEXT_CONTROLLER_VALID'] = a
                else: self.fail('unmodeled accepted-talk instruction: ' + line)
            self.assertEqual(memory['SAME_VIDEO_TEXT_CONTROLLER_VALID'], 0)
        # Both truncated and normal accepted paths converge at this boundary.
        before = source.split('ScummV5_Talk_Begin_Far__message_ready:', 1)[0]
        self.assertIn('brl ScummV5_Talk_Begin_Far__message_ready', before)


if __name__ == '__main__':
    unittest.main()
