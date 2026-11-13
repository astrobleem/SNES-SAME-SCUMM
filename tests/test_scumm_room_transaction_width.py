"""New-room chunk cursor reset must not depend on the caller's hidden B byte."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def reset_source():
    source = (ROOT / 'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
    request = source.split('ScummV5_MsuRoom_Request_Far:', 1)[1].split('ScummV5_MsuRoom_Request_Far__coalesced:', 1)[0]
    start = request.index('    lda #$00\n    sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED')
    end = request.index('    sta.l SCUMM_LIVE_ROOM_CHUNK_INDEX', start)
    return request[start:end] + '    sta.l SCUMM_LIVE_ROOM_CHUNK_INDEX\n'


def execute(source, hidden_b):
    a, width = hidden_b << 8 | 0xAC, 8
    addresses = {'SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED': 0,
                 'SCUMM_LIVE_ROOM_CHUNK_MODE': 1,
                 'SCUMM_LIVE_ROOM_CHUNK_INDEX': 2,
                 'SAME_SCUMM_VIEWPORT_STATE': 4,
                 'SAME_SCUMM_VIEWPORT_MODE': 5,
                 'SAME_SCUMM_VIEWPORT_ACTOR_SERVED': 6}
    memory = bytearray(b'\xA5' * 8)
    for raw in source.splitlines():
        line = raw.split(';')[0].strip()
        if not line or line.startswith('.'): continue
        op, arg = line.split(None, 1)
        if op == 'lda':
            n = int(arg[2:], 16)
            a = ((a & 0xFF00) | n) if width == 8 else n
        elif op == 'rep':
            assert arg == '#$20'; width = 16
        elif op == 'sta.l':
            at = addresses[arg]
            memory[at:at + width // 8] = (a & ((1 << width) - 1)).to_bytes(width // 8, 'little')
        else: raise AssertionError(line)
    return memory


class RoomTransactionWidthTests(unittest.TestCase):
    def test_all_hidden_accumulator_bytes_reset_both_cursor_bytes(self):
        for hidden_b in range(256):
            self.assertEqual(execute(reset_source(), hidden_b), b'\0\0\0\0\0\0\0\xA5')

    def test_unfixed_source_reproduces_native_0100_cursor(self):
        unfixed = reset_source().replace('    lda #$0000\n', '')
        self.assertEqual(execute(unfixed, 1)[2:4], b'\0\1')
