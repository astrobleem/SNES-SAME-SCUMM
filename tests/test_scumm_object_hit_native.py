"""Execute generated room hit-test instructions; Nexen remains separate proof."""
import ast
import unittest
import test_scumm_cutscene_callback_native as callback_native
from test_scumm_camera_native_copy import ROOT
from test_scumm_class_defaults_native import room_service_path


class ObjectHitNativeTests(unittest.TestCase):
    machine = callback_native.CutsceneCallbackNative.machine

    def query(self, hidden, x=130, y=110, missing=False, defaults=()):
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
        find = 'ScummV5_C16_QueryMask_Far:'+native.split('ScummV5_C16_QueryMask_Far:', 1)[1].split(
            '; Convert class 1..32', 1)[0]
        # This fixture has the ordinary generated room service enabled.
        find = room_service_path(find)
        find += '\n'+(ROOT/'runtime/snes/engines/scumm_v5_classes_far.inc.pasm').read_text()
        initial = source.split('"ScummV5_ObjectClass_QueryInitial_Far:"',1)[1].split(
            '"ScummV5_ObjectClass_ApplyScenarioOverlay_Far:"',1)[0]
        generated = []
        for line in initial.splitlines():
            try: expr = ast.parse('['+line+']',mode='eval')
            except SyntaxError: continue
            generated.extend(n.value for n in ast.walk(expr) if isinstance(n,ast.Constant) and isinstance(n.value,str))
        code = '\n'.join(lines)+'\n'+find+'\nScummV5_ObjectClass_QueryInitial_Far:\n'+'\n'.join(generated)
        m = self.machine(code.replace('brl ', 'jmp '))
        m.symbols.update(ScummV5_ObjectClass_Initial=0x508000, ScummV5_ObjectClass_InitialCount=16)
        for identity in defaults:m.put(0x508000+identity*4,0x80000000,4)
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

    def test_source_defaults_apply_without_consuming_mutable_records(self):
        self.assertEqual(self.query(set(),missing=True,defaults=(8,)),(True,9))
        self.assertEqual(self.query(set(),missing=True,defaults=(8,9)),(False,0))
        # A present zero mutation overrides the immutable untouchable bit.
        self.assertEqual(self.query(set(),defaults=(8,9)),(True,8))

    def test_no_class_record_is_touchable_and_bounds_remain_half_open(self):
        self.assertEqual(self.query(set(),missing=True),(True,8))
        for x,y in ((127,110),(152,110),(130,103),(130,136)):
            self.assertEqual(self.query(set(),x,y),(False,0))
