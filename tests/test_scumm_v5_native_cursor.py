"""Execute native cursor Draw/Frame and actor lower-bound instructions.

Only external video services are stubbed. No ROM build/emulator/archive.
The interpreter adapts ControllerMachine's width/stack model; cursor branches,
projection, clipping, mask shifts, and publication retries execute real source.
"""
from bisect import bisect_left
from pathlib import Path
import struct
import re
import unittest

from test_scumm_v5_actor_damage_boundaries import ControllerMachine, camera_source
from same.engines.scumm_v5.cursor import MASKS, HOTSPOTS, COLORS
from tools.validate_scumm_actor_visual_probe_nexen import pose_is_presented

ROOT = Path(__file__).resolve().parents[1]
C = 'SAME_SCUMM_CURSOR_'
D = 'SAME_VIDEO_SURFACE_DAMAGE_'


class CursorMachine(ControllerMachine):
    def __init__(self, source_size=(320, 200), camera=False):
        super().__init__([], source_size=source_size, camera=camera)
        cursor = (ROOT / 'runtime/snes/engines/scumm_v5_cursor_far.pasm').read_text()
        controller = (ROOT / 'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        helper = controller.split('ScummV5_ActorPose_ProjectSpan_Far:', 1)[1]
        helper = helper.split('; The provider has one global cursor.', 1)[0]
        self.code, self.labels = [], {}
        for raw in camera_source(cursor + '\nScummV5_ActorPose_ProjectSpan_Far:\n' + helper,camera).splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.') or ' = ' in line:
                continue
            if line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
            else:
                self.code.append(line)
        self.rom = {}
        label = None
        for raw in (ROOT / 'runtime/snes/engines/scumm_v5_cursor_shapes.inc.pasm').read_text().splitlines():
            line = raw.split(';', 1)[0].strip()
            if line.endswith(':'):
                label = line[:-1]
                self.rom[label] = bytearray()
            elif line.startswith('.byte '):
                self.rom[label].extend(int(v.strip()[1:], 16) for v in line[6:].split(','))
        self.mem.update({'SAME_SCUMM_CONTROLLER_ROOM_READY': 1,
                         'SAME_SCUMM_C7_CURSOR_STATE': 1,
                         'SAME_SCUMM_C7_CURSOR_ID': 0,
                         'SAME_SCUMM_CONTROLLER_CURSOR_X': 160,
                         'SAME_SCUMM_CONTROLLER_CURSOR_Y': 100,
                         'SAME_SCUMM_FRAME_COUNT': 0})
        self.mem.update(SAME_VIDEO_SURFACE_WIDTH=source_size[0],
                        SAME_VIDEO_SURFACE_COPY_WIDTH=min(256,source_size[0]))
        self.journal = None
        self.coverage = {}
        self.retained = None
        service_source = (ROOT / 'runtime/snes/services/cursor_underlay.inc.pasm').read_text()
        self.magic = int(re.search(r'SAME_VIDEO_CURSOR_MAGIC\s*=\s*\$([0-9A-Fa-f]+)', service_source)[1], 16)
        self.queue_fail = self.capture_fail = self.restore_fail = False
        self.queue_calls = self.capture_calls = self.pixel_calls = 0
        self.published_damage = []
        self.pixel_hook = None
        self.executed = set()

    def operand(self, arg):
        if arg == '#SAME_VIDEO_CURSOR_MAGIC':
            return self.magic
        if arg.endswith(',x') and arg[:-2] in self.rom:
            data = self.rom[arg[:-2]]
            # The last color is read A16 then masked; adjacent ROM high byte
            # is deliberately nonzero to expose missing masks.
            return int.from_bytes((data + b'\xA5')[self.x:self.x+2], 'little')
        return super().operand(arg)

    def union(self, box):
        if self.mem.get(D+'WIDTH', 0) and self.mem.get(D+'HEIGHT', 0):
            x, y = self.mem[D+'X'], self.mem[D+'Y']
            old = (x, y, x+self.mem[D+'WIDTH'], y+self.mem[D+'HEIGHT'])
            box = (min(old[0],box[0]),min(old[1],box[1]),max(old[2],box[2]),max(old[3],box[3]))
        self.damage = box
        self.mem.update({D+'X':box[0],D+'Y':box[1],D+'WIDTH':box[2]-box[0],D+'HEIGHT':box[3]-box[1]})

    def service(self, name):
        self.events.append(name)
        if name == 'Same_VideoSurface_CanWrite_Far':
            self.c = not self.writable
        elif name == 'Same_VideoSurface_CaptureCursorUnderlay_Far':
            self.capture_calls += 1
            self.c = self.capture_fail
            if self.c:
                return
            x, y, w, h = self.a & 255, self.a >> 8, self.x, self.y
            assert 1 <= w <= 16 and 1 <= h <= 16
            assert 0 <= x < x+w <= 256 and 0 <= y < y+h <= 224
            assert self.journal is None, 'recapture over live cursor underlay'
            box = (x,y,x+w,y+h)
            saved = [(r*256+x,bytes(self.surface[r*256+x:r*256+x+w])) for r in range(y,y+h)]
            self.journal = box, saved
            self.coverage = {}
            self.retained = box
            self.mem['SAME_VIDEO_CURSOR_UNDERLAY'] = self.magic
            self.union(box)
        elif name == 'Same_VideoSurface_SetCursorCoverageRow_Far':
            assert self.journal
            left,top,right,bottom=self.journal[0]
            assert 0<=self.x<bottom-top
            self.coverage[self.x]=self.a
            self.c=False
        elif name == 'Same_VideoSurface_RestoreCursorUnderlay_Far':
            self.c = self.restore_fail
            if self.c:
                return
            if self.journal:
                box, saved = self.journal
                for address, data in saved:
                    self.surface[address:address+len(data)] = data
                self.union(box)
                self.journal = None
                self.mem['SAME_VIDEO_CURSOR_UNDERLAY'] = 0
        elif name == 'Same_VideoSurface_MergeCursorDamage_Far':
            self.c = False
            if self.retained:
                self.union(self.retained)
        elif name == 'Same_VideoSurface_WriteIndexedPixel_Far':
            assert self.mem.get(C+'COMPOSING') == 1, 'mid-write surface advertised complete'
            assert self.journal, 'pixel write before capture'
            x,y = self.x % 256,self.x // 256
            left,top,right,bottom = self.journal[0]
            assert left <= x < right and top <= y < bottom, 'pixel outside captured bounds'
            assert self.coverage[y-top] & (0x8000>>(x-left)), 'opaque write outside source coverage'
            self.surface[self.x] = self.a & 255
            self.pixel_calls += 1
            if self.pixel_hook:
                self.pixel_hook(self)
        elif name == 'Same_VideoSurface_PushDamagePresent_Far':
            self.queue_calls += 1
            assert self.mem[D+'WIDTH'] and self.mem[D+'HEIGHT']
            self.c = self.queue_fail
            if not self.c:
                self.published_damage.append(tuple(self.mem[D+k] for k in ('X','Y','WIDTH','HEIGHT')))
        else:
            raise AssertionError(name)

    def entry(self, name='Frame', flags=0x39):
        self.a, self.x, self.y = 0xBEEF, 0x34, 0x56
        self.initial = self.a, self.x, self.y
        self.width, self.iwidth = (8 if flags & 32 else 16), (8 if flags & 16 else 16)
        self.c, self.z, self.n, self.v = (bool(flags & bit) for bit in (1,2,128,64))
        self.decimal = bool(flags & 8)
        self.stack = [0x54,0x90,0xCA]
        self.call_returns = []
        pc = self.labels['ScummV5_Cursor_' + name + '_Far']
        for _ in range(2000000):
            self.instructions += 1
            if self.call_returns:
                self.search_instructions += 1
            self.executed.add(pc)
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
            elif op == 'ldx':
                self.x = value & ((1 << self.iwidth)-1)
                self.z, self.n = self.x == 0, bool(self.x & (1 << (self.iwidth-1)))
            elif op in ('lda', 'lda.l'):
                result = value
            elif op in ('sta', 'sta.l'):
                if arg.endswith(',s'):
                    n = int(arg[:-2])
                    self.stack[-n], self.stack[-n-1] = self.a & 255, self.a >> 8
                else:
                    old = self.mem.get(arg, 0)
                    self.mem[arg] = (old & ~mask) | (self.a & mask)
            elif op == 'php':
                self.stack.append((0x20 if self.width == 8 else 0) |
                                  (0x10 if self.iwidth == 8 else 0) |
                                  int(self.c) | int(self.z) * 2 | int(self.n) * 128 | int(self.v) * 64 | int(self.decimal) * 8)
            elif op == 'plp':
                flags = self.stack.pop()
                self.decimal = bool(flags & 8)
                self.width = 8 if flags & 32 else 16
                self.iwidth = 8 if flags & 16 else 16
                self.c, self.z, self.n, self.v = (bool(flags & b) for b in (1, 2, 128, 64))
            elif op in ('pha', 'phx', 'phy'):
                self.push(getattr(self, op[-1]), self.width if op == 'pha' else self.iwidth)
            elif op in ('pla', 'plx', 'ply'):
                w = self.width if op == 'pla' else self.iwidth
                v = self.pop(w)
                if op == 'pla':
                    self.a = (self.a & ~((1 << w)-1)) | v
                else:
                    setattr(self, op[-1], v)
                self.z, self.n = v == 0, bool(v & (1 << (w-1)))
            elif op == 'clc':
                self.c = False
            elif op == 'sec':
                self.c = True
            elif op in ('adc', 'adc.l', 'sbc', 'sbc.l'):
                assert not self.decimal, 'decimal arithmetic in cursor'
                a = self.a & mask
                subtract = op.startswith('sbc')
                result = a - value - int(not self.c) if subtract else a + value + int(self.c)
                self.c = result >= 0 if subtract else result > mask
                sign = 1 << (self.width - 1)
                self.v = bool(((a ^ value) if subtract else ~(a ^ value)) & (a ^ result) & sign)
            elif op == 'cpx':
                self.c, self.z = self.x >= value, self.x == value
                self.n = bool((self.x-value) & (1 << (self.iwidth-1)))
            elif op in ('cmp', 'cmp.l'):
                self.c = (self.a & mask) >= value
                self.z = (self.a & mask) == value
                self.n = bool(((self.a & mask) - value) & (1 << (self.width - 1)))
            elif op in ('eor', 'and', 'ora', 'ora.l'):
                result = {'eor': lambda: self.a ^ value, 'and': lambda: self.a & value,
                          'ora': lambda: self.a | value, 'ora.l': lambda: self.a | value}[op]()
            elif op in ('dec', 'inc'):
                result = self.a + (1 if op == 'inc' else -1)
            elif op in ('asl', 'lsr'):
                self.c = bool(self.a & (1 << (self.width - 1) if op == 'asl' else 1))
                result = self.a << 1 if op == 'asl' else (self.a & mask) >> 1
            elif op in ('inx','dex'):
                self.x = (self.x + (1 if op == 'inx' else -1)) & ((1 << self.iwidth) - 1)
                self.z, self.n = self.x == 0, bool(self.x & (1 << (self.iwidth - 1)))
            elif op == 'tya':
                result = self.y
            elif op == 'cld':
                self.decimal = False
            elif op == 'xba':
                self.a = (self.a & 255) << 8 | self.a >> 8
                self.z, self.n = (self.a & 255) == 0, bool(self.a & 128)
            elif op in ('tax', 'tay'):
                setattr(self, op[-1], self.a & ((1 << self.iwidth) - 1))
                v = getattr(self, op[-1])
                self.z, self.n = v == 0, bool(v & (1 << (self.iwidth-1)))
            elif op == 'jsl':
                if arg in self.labels:
                    self.call_returns.append(pc)
                    self.stack.extend([0x21, 0x88, 0x00])
                    pc = self.labels[arg]
                else:
                    self.service(arg)
            elif op in ('jmp', 'jml', 'brl', 'bra', 'bcc', 'bcs', 'bne', 'beq', 'bmi', 'bpl', 'bvc', 'bvs'):
                take = {'bcc': not self.c, 'bcs': self.c, 'bne': not self.z,
                        'beq': self.z, 'bmi': self.n, 'bpl': not self.n, 'bvc': not self.v, 'bvs': self.v}.get(op, True)
                if take:
                    pc = self.labels[arg]
            elif op == 'rtl':
                if self.call_returns:
                    assert self.stack[-3:] == [0x21, 0x88, 0x00]
                    del self.stack[-3:]
                    pc = self.call_returns.pop()
                    continue
                assert self.stack == [0x54, 0x90, 0xCA], self.stack
                assert (self.a, self.x, self.y) == self.initial
                assert self.width == (8 if flags & 32 else 16)
                assert self.iwidth == (8 if flags & 16 else 16)
                assert self.decimal == bool(flags & 8) and self.db == 0x87
                return self
            else:
                raise AssertionError(line)
            if result is not None:
                result &= mask
                self.a = (self.a & ~mask) | result
                self.z, self.n = result == 0, bool(result & (1 << (self.width - 1)))
        raise AssertionError('controller did not return')


def expected_surface(vm):
    output = bytearray(vm.original)
    if vm.mem['SAME_SCUMM_C7_CURSOR_STATE'] == 0 or vm.mem['SAME_SCUMM_C7_CURSOR_STATE'] & 0x8000:
        return output
    sw, sh = vm.source_size
    if 256*sh <= 224*sw:
        cw,ch = 256,max(1,sh*256//sw)
    else:
        cw,ch = max(1,sw*224//sh),224
    xs = [(2*x+1)*sw//(2*cw) for x in range(cw)]
    ys = [(2*y+1)*sh//(2*ch) for y in range(ch)]
    def signed(v):
        return v-65536 if v & 32768 else v
    px = max(0,signed(vm.mem['SAME_SCUMM_CONTROLLER_CURSOR_X']))
    py = max(0,signed(vm.mem['SAME_SCUMM_CONTROLLER_CURSOR_Y']))
    index = vm.mem['SAME_SCUMM_C7_CURSOR_ID']
    left = bisect_left(xs,px)+(256-cw)//2-HOTSPOTS[index][0]
    top = bisect_left(ys,py)+(224-ch)//2-HOTSPOTS[index][1]
    left += signed(vm.mem.get('SAME_VIDEO_SURFACE_DEST_X',0))-signed(vm.mem.get('SAME_VIDEO_SURFACE_SOURCE_X',0))
    top += signed(vm.mem.get('SAME_VIDEO_SURFACE_DEST_Y',0))-signed(vm.mem.get('SAME_VIDEO_SURFACE_SOURCE_Y',0))
    color = COLORS[(vm.mem['SAME_SCUMM_FRAME_COUNT']//2)&3]
    for y in range(16):
        for x in range(16):
            if MASKS[index][y*16+x] and 0 <= x+left < 256 and 0 <= y+top < 224:
                output[(top+y)*256+left+x] = color
    return output


class NativeCursorTests(unittest.TestCase):
    def test_draw_all_shapes_phases_source_anchors_and_edges(self):
        for size in ((320,200),(256,224),(200,320),(17,13)):
            for index in range(4):
                for foot in ((0,0),(1,1),(20,40),(80,40),(size[0]-1,size[1]-1),(-1,-1),(size[0]+20,size[1]+20)):
                    with self.subTest(size=size,index=index,foot=foot):
                        vm=CursorMachine(size)
                        vm.mem.update({'SAME_SCUMM_C7_CURSOR_ID':index,
                                       'SAME_SCUMM_CONTROLLER_CURSOR_X':foot[0]&65535,
                                       'SAME_SCUMM_CONTROLLER_CURSOR_Y':foot[1]&65535,
                                       'SAME_SCUMM_FRAME_COUNT':index*2})
                        expected=expected_surface(vm)
                        vm.entry('Draw')
                        self.assertFalse(vm.c)
                        self.assertEqual(vm.surface,expected)
                        self.assertEqual(vm.mem[C+'VALID'],1)
                        vm.service('Same_VideoSurface_RestoreCursorUnderlay_Far')
                        self.assertEqual(vm.surface,vm.original)
                        self.assertIsNone(vm.journal)

    def test_width_flags_stack_and_viewport_clipping(self):
        for flags in (0x08,0x19,0x28,0x39):
            for delta in (-300,-129,0,125,300):
                vm=CursorMachine()
                vm.mem['SAME_VIDEO_SURFACE_DEST_X']=delta&65535
                vm.mem['SAME_VIDEO_SURFACE_DEST_Y']=delta&65535
                expected=expected_surface(vm)
                vm.entry('Draw',flags)
                self.assertEqual(vm.surface,expected)

    def test_frame_moves_restores_actor_backing_and_hides(self):
        vm=CursorMachine()
        # Backing pattern includes actor-like opaque pixels, including zero.
        vm.surface[100*256:101*256]=bytes(range(256))
        vm.original=bytes(vm.surface)
        vm.entry()
        self.assertEqual(vm.surface,expected_surface(vm))
        vm.mem['SAME_SCUMM_CONTROLLER_CURSOR_X']=80
        vm.mem['SAME_SCUMM_CONTROLLER_CURSOR_Y']=40
        vm.entry()
        self.assertEqual(vm.surface,expected_surface(vm))
        self.assertEqual(vm.capture_calls,2)
        vm.mem['SAME_SCUMM_C7_CURSOR_STATE']=0
        vm.entry()
        self.assertEqual(vm.surface,vm.original)
        self.assertIsNone(vm.journal)
        self.assertEqual(vm.queue_calls,3)

    def test_unchanged_frame_noops_color_change_and_negative_visibility(self):
        vm=CursorMachine().entry()
        counts=vm.capture_calls,vm.queue_calls,vm.pixel_calls
        vm.entry()
        self.assertEqual((vm.capture_calls,vm.queue_calls,vm.pixel_calls),counts)
        vm.mem['SAME_SCUMM_FRAME_COUNT']=4
        vm.entry()
        self.assertEqual(vm.surface,expected_surface(vm))
        self.assertEqual(vm.capture_calls,2)
        vm.mem['SAME_SCUMM_C7_CURSOR_STATE']=65535
        vm.entry()
        self.assertEqual(vm.surface,vm.original)
        vm.entry()
        self.assertEqual(vm.capture_calls,2)

    def test_queue_retry_never_recaptures_drawn_pixels(self):
        vm=CursorMachine()
        vm.queue_fail=True
        vm.entry()
        self.assertEqual(vm.mem[C+'PENDING'],1)
        self.assertEqual(vm.mem[C+'COMPOSING'],1)
        drawn=bytes(vm.surface)
        vm.entry()
        self.assertEqual(vm.capture_calls,1)
        self.assertEqual(vm.surface,drawn)
        self.assertEqual(vm.mem[C+'COMPOSING'],1)
        vm.queue_fail=False
        vm.entry()
        self.assertEqual(vm.mem[C+'PENDING'],0)
        self.assertEqual(vm.mem[C+'COMPOSING'],0)
        self.assertEqual(vm.capture_calls,1)
        vm.mem['SAME_SCUMM_C7_CURSOR_STATE']=0
        vm.entry()
        self.assertEqual(vm.surface,vm.original)

    def test_restore_failure_stops_draw_and_consumed_journal_triggers_redraw(self):
        vm=CursorMachine().entry()
        previous=bytes(vm.surface)
        vm.restore_fail=True
        vm.mem['SAME_SCUMM_CONTROLLER_CURSOR_X']=20
        vm.entry()
        self.assertEqual(vm.surface,previous)
        self.assertEqual(vm.capture_calls,1)
        vm.restore_fail=False
        vm.service('Same_VideoSurface_RestoreCursorUnderlay_Far')
        # Other composition restored the cursor, but its state cache is valid.
        vm.mem['SAME_SCUMM_CONTROLLER_CURSOR_X']=160
        vm.entry()
        self.assertEqual(vm.capture_calls,2)
        self.assertEqual(vm.surface,expected_surface(vm))
        self.assertIn(vm.labels['ScummV5_Cursor_Draw_Far'],vm.executed)
        self.assertIn(vm.labels['ScummV5_ActorPose_ProjectSpan_Far'],vm.executed)

    def test_busy_not_ready_capture_failure_and_missing_geometry(self):
        for ready,writable in ((0,True),(1,False)):
            vm=CursorMachine()
            vm.mem['SAME_SCUMM_CONTROLLER_ROOM_READY']=ready
            vm.writable=writable
            vm.entry()
            self.assertEqual(vm.capture_calls,0)
            self.assertEqual(vm.surface,vm.original)
        for reason in ('capture','geometry','id'):
            vm=CursorMachine()
            if reason=='capture':vm.capture_fail=True
            if reason=='geometry':vm.offsets=bytes([255])*512
            if reason=='id':vm.mem['SAME_SCUMM_C7_CURSOR_ID']=4
            vm.entry('Draw')
            self.assertTrue(vm.c)
            self.assertEqual(vm.pixel_calls,0)
            self.assertEqual(vm.surface,vm.original)
            self.assertFalse(vm.mem.get(C+'VALID',0))

    def test_frame_error_latch_blocks_pending_and_fresh_publication(self):
        for pending in (0,1):
            with self.subTest(pending=pending):
                vm=CursorMachine()
                vm.mem['SAME_SCUMM_ERROR']=9
                vm.mem[C+'PENDING']=pending
                vm.mem.update({D+'X':0,D+'Y':0,D+'WIDTH':16,D+'HEIGHT':16})
                vm.entry()
                self.assertEqual(vm.queue_calls,0,'Frame published despite SCUMM error latch')
                self.assertEqual(vm.capture_calls,0)
                self.assertEqual(vm.surface,vm.original)

    def test_frame_draw_refusal_does_not_publish_existing_actor_damage(self):
        for reason in ('capture','geometry','id'):
            vm=CursorMachine()
            vm.mem.update({D+'X':30,D+'Y':40,D+'WIDTH':10,D+'HEIGHT':20})
            if reason=='capture':vm.capture_fail=True
            if reason=='geometry':vm.offsets=bytes([255])*512
            if reason=='id':vm.mem['SAME_SCUMM_C7_CURSOR_ID']=4
            vm.entry()
            self.assertEqual(vm.queue_calls,0)
            self.assertEqual(vm.surface,vm.original)

    def test_failed_capture_move_retry_retains_consumed_old_damage(self):
        vm=CursorMachine().entry()
        old=vm.journal[0]
        vm.mem['SAME_SCUMM_CONTROLLER_CURSOR_X']=20
        vm.mem['SAME_SCUMM_CONTROLLER_CURSOR_Y']=40
        vm.capture_fail=True
        for _ in range(2):
            vm.entry()
            self.assertIsNone(vm.journal)
            self.assertEqual(vm.surface,vm.original)
            self.assertEqual(vm.queue_calls,1)
            self.assertEqual(vm.damage,old)
        vm.capture_fail=False
        vm.entry()
        new=vm.journal[0]
        left,top=min(old[0],new[0]),min(old[1],new[1])
        right,bottom=max(old[2],new[2]),max(old[3],new[3])
        self.assertEqual(vm.published_damage[-1],(left,top,right-left,bottom-top))
        self.assertEqual(vm.surface,expected_surface(vm))
        self.assertEqual(vm.queue_calls,2)

    def test_actor_retry_blocks_both_pending_and_fresh_cursor_publication(self):
        for pending in (0,1):
            vm=CursorMachine()
            vm.mem['SAME_SCUMM_CONTROLLER_RENDER_RETRY']=1
            vm.mem[C+'PENDING']=pending
            vm.mem.update({D+'X':30,D+'Y':40,D+'WIDTH':10,D+'HEIGHT':20})
            before=tuple(vm.mem[D+k] for k in ('X','Y','WIDTH','HEIGHT'))
            vm.entry()
            self.assertEqual(vm.queue_calls,0)
            self.assertEqual(vm.capture_calls,0)
            self.assertEqual(tuple(vm.mem[D+k] for k in ('X','Y','WIDTH','HEIGHT')),before)
            self.assertEqual(vm.mem[C+'PENDING'],pending)

    def test_pending_cursor_source_guard_precedes_actor_damage_mutation(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        actor=source.split('ScummV5_Controller_RenderActor_Far:',1)[1]
        actor=actor.split('ScummV5_Controller_RenderActor__cursor_published:',1)
        prefix=[line.split(';',1)[0].strip() for line in actor[0].splitlines()]
        prefix=[line for line in prefix if line and not line.startswith('.')]
        index=prefix.index('lda.l SAME_SCUMM_CURSOR_PENDING')
        self.assertEqual(prefix[index+1:index+3],[
            'beq ScummV5_Controller_RenderActor__cursor_published',
            'jml ScummV5_Controller_RenderActor__done'])
        self.assertFalse(any(line.startswith('sta') and 'DAMAGE_' in line for line in prefix))
        self.assertFalse(any('RestoreCursorUnderlay' in line or 'RestoreActorUnderlay' in line
                             for line in prefix))

    def test_mid_draw_21_of_24_pixels_is_composing_despite_old_cache(self):
        vm=CursorMachine()
        vm.mem['SAME_SCUMM_FRAME_COUNT']=4  # first committed cursor is color 7
        vm.entry()
        self.assertEqual(vm.mem[C+'COMPOSING'],0)
        self.assertEqual(vm.mem[C+'COLOR'],7)
        vm.mem['SAME_SCUMM_FRAME_COUNT']=0  # next Draw writes color 15
        count_before=vm.pixel_calls
        snapshot=[]
        written=[]
        def observe(machine):
            written.append(machine.x)
            if machine.pixel_calls-count_before == 21:
                snapshot.append((machine.mem[C+'COMPOSING'],machine.mem[C+'COLOR'],
                                 bytes(machine.surface)))
        vm.pixel_hook=observe
        vm.entry()
        self.assertEqual(len(snapshot),1)
        active,cached,pixels=snapshot[0]
        self.assertEqual((active,cached),(1,7))
        self.assertNotEqual(pixels,bytes(expected_surface(vm)))
        self.assertEqual(vm.pixel_calls-count_before,24)
        self.assertTrue(all(pixels[address] == 15 for address in written[:21]))
        self.assertTrue(all(pixels[address] == vm.original[address] for address in written[21:]))
        self.assertEqual(vm.surface,expected_surface(vm))
        self.assertEqual((vm.mem[C+'COMPOSING'],vm.mem[C+'COLOR']),(0,15))

    def test_draw_commit_is_not_publication_and_empty_frame_finishes(self):
        vm=CursorMachine().entry('Draw')
        self.assertEqual(vm.mem[C+'COMPOSING'],1)
        self.assertEqual(vm.queue_calls,0)
        hidden=CursorMachine()
        hidden.mem['SAME_SCUMM_C7_CURSOR_STATE']=0
        hidden.entry()
        self.assertEqual(hidden.queue_calls,0)
        self.assertEqual(hidden.mem[C+'COMPOSING'],0)
        failed=CursorMachine()
        failed.capture_fail=True
        failed.entry()
        self.assertEqual(failed.mem[C+'COMPOSING'],1)
        failed.capture_fail=False
        failed.entry()
        self.assertEqual(failed.mem[C+'COMPOSING'],0)

    def test_actor_composing_hooks_precede_restore_and_follow_present_success(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        actor=source.split('ScummV5_Controller_RenderActor_Far:',1)[1]
        lines=[line.split(';',1)[0].strip() for line in actor.splitlines()]
        lines=[line for line in lines if line and not line.startswith('.')]
        restore=lines.index('jsl Same_VideoSurface_RestoreCursorUnderlay_Far')
        self.assertEqual(lines[restore-2:restore],['lda #$0001','sta.l SAME_SCUMM_CURSOR_COMPOSING'])
        success=lines.index('ScummV5_Controller_RenderActor__present_success:')
        self.assertEqual(lines[success+1:success+4],['rep #$20','lda #$0000','sta.l SAME_SCUMM_CURSOR_COMPOSING'])
        result=lines.index('ScummV5_Controller_RenderActor__present_result:')
        self.assertIn('bcc ScummV5_Controller_RenderActor__present_success',lines[result:success])
        self.assertIn('brl ScummV5_Controller_RenderActor__present_retry',lines[result:success])
        # Retry clears composition only on the queue-success fallthrough.
        first_clear=lines.index('sta.l SAME_SCUMM_CURSOR_COMPOSING')
        self.assertEqual(lines[first_clear-1],'lda #$0000')
        self.assertIn('bcs ScummV5_Controller_RenderActor__retry_done',lines[first_clear-6:first_clear])

    def test_observer_rejects_active_composition_with_otherwise_committed_record(self):
        raw=bytearray(128)
        raw[3]=6
        raw[7:9]=(12).to_bytes(2,'little')
        raw[0x6B]=1
        # Captured cache/backend fields can still describe the prior present
        # while the surface has already begun its next cursor Draw.
        record=dict(render_valid=1,render_frame=6,render_step=0,
                    render_generation=12,render_facing=180,next_generation=9,
                    backend_pending_generation=9,backend_committed_generation=9,
                    backend_pending_generation_hi=0,backend_committed_generation_hi=0,
                    backend_state=1,surface_locked=0,pending_visual=0,
                    presented_room=4,room=4,surface_packets_pending=False)
        self.assertTrue(pose_is_presented(raw,**record))
        self.assertTrue(pose_is_presented(raw,**record,composition_active=0))
        self.assertFalse(pose_is_presented(raw,**record,composition_active=1))
        self.assertFalse(pose_is_presented(raw,**record,composition_active=256))


if __name__ == '__main__':
    unittest.main()


class CameraCursorTests(unittest.TestCase):
    def test_world_hit_point_and_visible_cursor_share_camera_origin(self):
        for origin in (0,40,320):
            for x,y in ((0,0),(40,60),(287,143),(319,199)):
                vm=CursorMachine((640,144),camera=True)
                vm.mem.update(SAME_SCUMM_CONTROLLER_CURSOR_X=x,
                              SAME_SCUMM_CONTROLLER_CURSOR_Y=y,
                              SAME_SCUMM_CAMERA_VSCREEN_XSTART=origin,
                              SAME_SCUMM_CAMERA_CURRENT_Y=100,
                              SAME_VIDEO_SURFACE_SOURCE_X=origin+32,
                              SAME_VIDEO_SURFACE_SOURCE_Y=0,
                              SAME_VIDEO_SURFACE_DEST_X=0,
                              SAME_VIDEO_SURFACE_DEST_Y=24)
                want=bytearray(vm.original);left=x-32-HOTSPOTS[0][0];top=y+24-HOTSPOTS[0][1]
                for i,covered in enumerate(MASKS[0]):
                    dx,dy=left+i%16,top+i//16
                    if covered and 0<=dx<256 and 0<=dy<224:want[dy*256+dx]=COLORS[0]
                vm.entry('Draw');self.assertFalse(vm.c);self.assertEqual(vm.surface,want)

    def test_future_camera_target_cannot_move_fixed_cursor_before_strip_commit(self):
        for width in (160,256,280,320,640):
            inset=min(32,max(0,width-min(width,256)))
            for target in (0,8,176,320):
                for committed in (0,32,72,208):
                    vm=CursorMachine((width,144),camera=True)
                    vm.mem.update(SAME_SCUMM_CONTROLLER_CURSOR_X=120,
                                  SAME_SCUMM_CONTROLLER_CURSOR_Y=100,
                                  SAME_SCUMM_CAMERA_VSCREEN_XSTART=target,
                                  SAME_SCUMM_CAMERA_CURRENT_Y=100,
                                  SAME_VIDEO_SURFACE_SOURCE_X=committed,
                                  SAME_VIDEO_SURFACE_SOURCE_Y=0,
                                  SAME_VIDEO_SURFACE_DEST_X=max(0,(256-width)//2),
                                  SAME_VIDEO_SURFACE_DEST_Y=24)
                    want=bytearray(vm.original)
                    left=120-inset+max(0,(256-width)//2)-HOTSPOTS[0][0]
                    top=124-HOTSPOTS[0][1]
                    for i,covered in enumerate(MASKS[0]):
                        dx,dy=left+i%16,top+i//16
                        if covered and 0<=dx<256 and 0<=dy<224:want[dy*256+dx]=COLORS[0]
                    vm.entry('Draw');self.assertFalse(vm.c)
                    self.assertEqual(vm.surface,want)
