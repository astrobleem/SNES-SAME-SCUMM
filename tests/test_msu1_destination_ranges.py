"""Execute provider range-check instructions on the host; not emulator evidence."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class DestinationRangeTests(unittest.TestCase):
    def test_active_metadata_limit_plus_one_is_not_an_inclusive_end(self):
        source=(ROOT/'runtime/snes/services/storage_msu1.pasm').read_text()
        text=source.split('Same_Msu1_ReadBegin__bwram_active_extent_no_overflow:',1)[1].split('Same_Msu1_ReadBegin__bwram_active_range_ok:',1)[0]
        text+='\nSame_Msu1_ReadBegin__bwram_active_range_ok:\n clc\n rtl\nSame_Msu1_ReadBegin__capacity_error16:\n sec\n rtl\n'
        for extent in (6143,6144,6145,65535):
            m=StripMachine();m.symbols['SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE']=6144
            m.code=[f'lda #${extent:04X}'];m.labels={}
            for raw in text.splitlines():
                line=raw.split(';')[0].strip()
                if not line or line.startswith('.'):continue
                if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                else:m.code.append(line.replace('jml ','jmp '))
            failed,_=m.consume()
            self.assertEqual(failed,extent>6144,extent)

    def check_pending(self, address, capacity):
        m=StripMachine()
        m.symbols.update(SAME_BWRAM_LIVE_ROOM_PENDING=0x4013c4,
                         SAME_BWRAM_LIVE_ROOM_PENDING_SIZE=3132)
        source=(ROOT/'runtime/snes/services/storage_msu1.pasm').read_text()
        text=source.split('Same_Msu1_ReadBegin__check_pending_address:',1)[1].split('Same_Msu1_ReadBegin__dest_pending_capacity_ok16:',1)[0]
        text+='\nSame_Msu1_ReadBegin__dest_pending_capacity_ok16:\n clc\n rtl\nSame_Msu1_ReadBegin__capacity_error16:\n sec\n rtl\n'
        m.code=[];m.labels={}
        for raw in text.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line.replace('jml ','jmp '))
        m.put('SAME_MSU1_DESTINATION',address,3)
        m.put('SAME_MSU1_DEST_CAPACITY',capacity)
        return m.consume()

    def test_pending_subranges_and_exact_end(self):
        base=0x4013c4
        for offset,length in ((0,3132),(2048,1024),(3131,1),(2048,1084)):
            with self.subTest(offset=offset,length=length):
                failed,writes=self.check_pending(base+offset,length)
                self.assertFalse(failed)
                self.assertEqual(writes,[])

    def test_outside_extent_and_overflow_rejected_without_write(self):
        base=0x4013c4
        for offset,length in ((-1,1),(0,3133),(2048,1085),(3132,1),(65000,1000)):
            with self.subTest(offset=offset,length=length):
                failed,writes=self.check_pending(base+offset,length)
                self.assertTrue(failed)
                self.assertEqual(writes,[])
