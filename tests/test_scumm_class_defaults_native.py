"""Execute production C16 instructions with immutable generated source masks.

This instruction runner complements, and does not replace, Nexen acceptance.
"""
import ast
import unittest
import test_scumm_cutscene_callback_native as callback_native
from test_scumm_camera_native_copy import ROOT


def literal_block(source, start, end):
    body = source.split('"'+start+':"',1)[1].split('"'+end+':"',1)[0]
    lines = [start+':']
    for line in body.splitlines():
        if line.lstrip().startswith('#'): continue
        try: tree = ast.parse('['+line+']',mode='eval')
        except SyntaxError: continue
        lines.extend(n.value for n in ast.walk(tree)
                     if isinstance(n,ast.Constant) and isinstance(n.value,str))
    return '\n'.join(lines)


def room_service_path(code):
    active=[True];arms=[];lines=[]
    for line in code.splitlines():
        item=line.strip()
        if item=='.if SAME_BUILD_SCUMM_ROOM_SERVICE':
            arms.append(True);active.append(active[-1])
        elif item=='.else':active[-1]=active[-2] and not arms[-1]
        elif item=='.endif':active.pop();arms.pop()
        elif active[-1]:lines.append(line)
    assert len(active)==1
    return '\n'.join(lines)


class SourceClassNativeTests(unittest.TestCase):
    machine = callback_native.CutsceneCallbackNative.machine

    def setup_machine(self, mask=0x80000001):
        native=(ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        code='ScummV5_Op_SetClass__class_valid:'+native.split(
            'ScummV5_Op_SetClass__class_valid:',1)[1].split('; Locate the object record',1)[0]
        code+='\nScummV5_C16_QueryMask_Far:'+native.split(
            'ScummV5_C16_QueryMask_Far:',1)[1].split('; Canonical v5 $7A',1)[0]
        code=room_service_path(code)
        code+='\n'+(ROOT/'runtime/snes/engines/scumm_v5_classes_far.inc.pasm').read_text()
        code+='\n'+literal_block((ROOT/'tools/generate_snes_cooked_rooms.py').read_text(),
                    'ScummV5_ObjectClass_QueryInitial_Far','ScummV5_ObjectClass_ApplyScenarioOverlay_Far')
        code+='\nScummV5_Op_SetClass__selector_loop:\nScummV5_Engine_Frame__next:\nScummV5_Op__error:\nrtl\nScummV5_SetError:\nsta.l SAME_SCUMM_ERROR\nrts\n'
        m=self.machine(code)
        m.symbols.update(ScummV5_ObjectClass_Initial=0x508000,
                         ScummV5_ObjectClass_InitialCount=1024,
                         ScummV5_C7_BitMasks=0x50F000,SCUMM_ERR_SET_CLASS=23)
        for i in range(8):m.put(0x50F000+i,1<<i,1)
        m.put(0x508000+900*4,mask,4)
        m.put('SAME_SCUMM_C16_OBJECT',900)
        return m

    def mutate(self,m,raw):
        m.put('SAME_SCUMM_C16_CLASS',raw)
        m.entry=m.labels['ScummV5_Op_SetClass__'+('clear_all' if raw==0 else 'class_valid')]
        m.consume()

    def membership(self,m,bit):
        m.put('SAME_SCUMM_C16_CLASS',bit)
        m.entry=m.labels['ScummV5_C16_TestClass']
        return m.consume()[0]

    def count(self,m):
        base=m.symbols['SAME_SCUMM_C16_RECORDS']
        return sum(bool(m.get(base+i,1)) for i in range(0,4096,8))

    def test_query_return_width_is_explicit_to_the_assembler(self):
        native=(ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        query=native.split('ScummV5_C16_QueryMask:',1)[1].split('ScummV5_C16_QueryMask__source:',1)[0]
        before_compare=query.split('cmp #$FFFF',1)[0]
        self.assertIn('.a16',before_compare)
        self.assertIn('.i16',before_compare)
        far=(ROOT/'runtime/snes/engines/scumm_v5_classes_far.inc.pasm').read_text()
        for label in ('SourceTestClass','SourceEnsureRecord'):
            entry=far.split('ScummV5_C16_'+label+'_Far:',1)[1]
            self.assertIn('.a16',entry.split('lda.l',1)[0])
            self.assertIn('.i16',entry.split('lda.l',1)[0])
        generated=(ROOT/'tools/generate_snes_cooked_rooms.py').read_text()
        query=literal_block(generated,'ScummV5_ObjectClass_QueryInitial_Far',
                            'ScummV5_ObjectClass_ApplyScenarioOverlay_Far')
        self.assertNotIn('ScummV5_ObjectClass_Initial+2',query)
        self.assertEqual(query.count('lda.l ScummV5_ObjectClass_Initial,x'),2)

    def test_all_class_bits_query_source_without_allocating(self):
        for mask in (0,1,0x80000000,0x5AA5AA55,0xFFFFFFFF):
            m=self.setup_machine(mask)
            for bit in range(1,33):
                self.assertEqual(self.membership(m,bit),bool(mask&(1<<(bit-1))))
            self.assertEqual(self.count(m),0)

    def test_clear_zero_override_and_reclaim_only_at_original_mask(self):
        m=self.setup_machine()
        self.mutate(m,32)
        self.assertTrue(self.membership(m,1));self.assertFalse(self.membership(m,32))
        self.assertEqual(self.count(m),1)
        self.mutate(m,160)
        self.assertEqual(self.count(m),0)
        self.mutate(m,0)
        self.assertEqual(self.count(m),1)
        self.assertFalse(self.membership(m,1));self.assertFalse(self.membership(m,32))
        self.mutate(m,129);self.mutate(m,160)
        self.assertEqual(self.count(m),0)
        self.assertTrue(self.membership(m,1));self.assertTrue(self.membership(m,32))

    def test_full_mutation_table_allows_noop_but_rejects_new_override(self):
        m=self.setup_machine();base=m.symbols['SAME_SCUMM_C16_RECORDS']
        for i in range(512):
            m.put(base+i*8,1);m.put(base+i*8+2,i);m.put(base+i*8+4,1,4)
        before=bytes(m.ram[base:base+4096])
        self.mutate(m,160)
        self.assertEqual(m.get('SAME_SCUMM_ERROR',1),0)
        self.mutate(m,32)
        self.assertEqual(m.get('SAME_SCUMM_ERROR',1),23)
        self.assertEqual(bytes(m.ram[base:base+4096]),before)
        self.assertTrue(self.membership(m,32))
