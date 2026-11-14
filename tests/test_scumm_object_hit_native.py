"""Execute generated room hit-test instructions; Nexen remains separate proof."""
import ast
import unittest
import test_scumm_cutscene_callback_native as callback_native
from test_scumm_camera_native_copy import ROOT


class ObjectHitNativeTests(unittest.TestCase):
    machine = callback_native.CutsceneCallbackNative.machine

    def query(self, hidden, x=130, y=110, missing=False):
        source = (ROOT/'tools/generate_snes_cooked_rooms.py').read_text()
        block = source.split('"ScummV5_Generic_Object_HitTest_Far:"', 1)[1].split(
            '"ScummV5_Generic_Object_ValidateSelected_Far:"', 1)[0]
        # Read actual literal generated instructions, not a duplicate algorithm.
        lines = []
        for line in block.splitlines():
            if line.lstrip().startswith('#'):
                continue
            try:
                expr = ast.parse('[' + line + ']', mode='eval')
            except SyntaxError:
                continue
            lines.extend(n.value for n in ast.walk(expr) if isinstance(n, ast.Constant)
                         and isinstance(n.value, str))
        native = (ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        find = native.split('ScummV5_C16_FindRecord_Far:', 1)[1].split(
            '; Convert class 1..32', 1)[0]
        code = '\n'.join(lines)+'\nScummV5_C16_FindRecord_Far:\n'+find
        m = self.machine(code.replace('brl ', 'jmp '))
        m.put('SAME_SCUMM_SETSTATE_LOCAL_COUNT', 2, 1)
        m.put(m.symbols['SAME_SCUMM_SETSTATE_LOCAL_COUNT']+1, 0xA5, 1)
        m.put('SAME_SCUMM_INTERACTION_X', x);m.put('SAME_SCUMM_INTERACTION_Y', y)
        for i, identity in enumerate((8,9)):
            row=m.symbols['SAME_SCUMM_SETSTATE_LOCAL_RECORDS']+i*11
            for offset,value in ((0,identity),(2,128),(4,104),(6,24),(8,32)):
                m.put(row+offset,value)
            if not missing:
                row=m.symbols['SAME_SCUMM_C16_RECORDS']+i*8
                m.put(row,1,1);m.put(row+2,identity)
                m.put(row+4,0x80000000 if identity in hidden else 0,4)
        carry,_=m.consume()
        return carry,m.get('SAME_SCUMM_INTERACTION_OBJECT')

    def test_mutable_classes_skip_front_object_and_preserve_next_record(self):
        for hidden,expected in ((set(),8),({8},9),({9},8),({8,9},0)):
            with self.subTest(hidden=hidden):
                self.assertEqual(self.query(hidden),(bool(expected),expected))

    def test_no_class_record_is_touchable_and_bounds_remain_half_open(self):
        self.assertEqual(self.query(set(),missing=True),(True,8))
        for x,y in ((127,110),(152,110),(130,103),(130,136)):
            self.assertEqual(self.query(set(),x,y),(False,0))
