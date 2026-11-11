"""Source-neutral v5 inventory query and horizontal camera wait contracts."""
import unittest
import test_scumm_v5_engine as conformance


class InventoryCameraWaitTests(unittest.TestCase):
    def test_camera_wait_uses_source_strip_convergence_and_rewinds(self):
        host = conformance.ScummV5EngineTests()._host(bytes((0xAE, 3, 0xA0)))
        engine = host.engine
        slot = engine.state.scripts[0]
        for current, destination, waiting in ((160, 167, False), (160, 168, True),
                                               (167, 160, False), (168, 160, True),
                                               (-7, 7, False), (-8, 0, True)):
            with self.subTest(current=current, destination=destination):
                slot.pc = 1
                slot.yielded = False
                engine.state.camera_x = current
                engine.state.camera_destination_x = destination
                self.assertEqual(engine._op_wait(slot, engine._context), waiting)
                self.assertEqual(slot.pc, 0 if waiting else 2)
                self.assertEqual(slot.yielded, waiting)
        engine.state.camera_x = engine.state.camera_destination_x = 168
        slot.pc = 1
        slot.yielded = False
        self.assertFalse(engine._op_wait(slot, engine._context))
        self.assertEqual(slot.pc, 2)

    def test_inventory_count_direct_variable_and_expression_observe_owners(self):
        # Direct count ->50; variable owner ->51; nested expression ->52.
        program = bytes((0x31, 50, 0, 1, 0xB1, 51, 0, 10, 0,
                         0xAC, 52, 0, 6, 0xB1, 0, 0, 10, 0, 0xFF, 0x80,
                         0x31, 53, 0, 1, 0xA0))
        host = conformance.ScummV5EngineTests()._host(program)
        engine = host.engine
        engine.state.variables[10] = 1
        owners = bytearray(engine._object_owners)
        owners[7] = owners[91] = 1
        owners[12] = 2
        engine._object_owners = bytes(owners)
        host.tick()
        self.assertEqual([engine.state.variables[i] for i in (50, 51, 52)], [2, 2, 2])
        owners[91] = 2
        engine._object_owners = bytes(owners)
        host.tick()
        self.assertEqual(engine.state.variables[53], 1)

    def test_unimplemented_wait_remains_an_explicit_error(self):
        host = conformance.ScummV5EngineTests()._host(bytes((0xAE, 0x1F)))
        with self.assertRaisesRegex(Exception, 'wait sub-op 31 is not implemented'):
            host.tick()


class NativeWaitInstructionTests(unittest.TestCase):
    def machine(self, entry):
        from test_scumm_camera_native_copy import StripMachine, ROOT
        m = StripMachine()
        source = (ROOT/'runtime/snes/engines/scumm_v5.pasm').read_text()
        code = source.split('ScummV5_Op_Wait__message:', 1)[1].split('ScummV5_Op_Wait__done:', 1)[0]
        m.code = ['jmp '+entry]; m.labels = {}
        for raw in ('ScummV5_Op_Wait__message:\n'+code).splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'): continue
            if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
            else: m.code.append(line)
        m.labels['ScummV5_Op_Wait__yield'] = len(m.code)
        m.code += ['sec', 'rtl']
        m.labels['ScummV5_Op_Wait__done'] = len(m.code)
        m.code += ['clc', 'rtl']
        return m

    def test_camera_rechecks_until_strip_arrival_without_stack_leak(self):
        for current, destination, waiting in ((160, 167, False), (160, 168, True),
                                               (168, 160, True), (640, 640, False)):
            with self.subTest(current=current, destination=destination):
                m = self.machine('ScummV5_Op_Wait__camera')
                m.put('SAME_SCUMM_PC', 102)
                m.put('SAME_SCUMM_CAMERA_CURRENT_X', current)
                m.put('SAME_SCUMM_CAMERA_DEST_X', destination)
                yielded, writes = m.consume()
                self.assertEqual(yielded, waiting)
                self.assertEqual(m.get('SAME_SCUMM_PC'), 100 if waiting else 102)
                self.assertEqual(writes, [m.symbols['SAME_SCUMM_PC']+i for i in range(2)] if waiting else [])

    def test_message_wait_rewinds_only_while_owned(self):
        for active in (0, 1):
            m = self.machine('ScummV5_Op_Wait__message')
            m.put('SAME_SCUMM_PC', 2);m.put('SAME_SCUMM_TALK_ACTIVE', active, 1)
            yielded, _ = m.consume()
            self.assertEqual(yielded, bool(active))
            self.assertEqual(m.get('SAME_SCUMM_PC'), 0 if active else 2)
