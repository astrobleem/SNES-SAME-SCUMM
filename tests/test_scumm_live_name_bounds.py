"""Live ROOM identity does not authorize writing past the bounded name cache."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class LiveNameBoundsTests(unittest.TestCase):
    def machine(self, ids, old=False):
        m=StripMachine();m.code=[];m.labels={}
        text=(ROOT/'runtime/snes/engines/scumm_v5_msu_live_room.pasm').read_text()
        text=text.split('ScummV5_LiveRoom_LoadNames_Far:',1)[1].split('ScummV5_LiveRoom_LoadGeometry_Far:',1)[0]
        if old:
            begin=text.index('    lda.l SCUMM_LIVE_ROOM_TEMP2\n    cmp #SAME_SCUMM_OBJECT_NAME_COUNT')
            end=text.index('ScummV5_LiveRoom_LoadNames_Far__cached_identity:',begin)
            text=text[:begin]+text[end:]
        for raw in text.splitlines():
            line=raw.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
            else:m.code.append(line)
        base=m.symbols['SCUMM_LIVE_ROOM_BASE'];m.put(base+m.symbols['SCUMM_LIVE_ROOM_OBJECT_COUNT'],len(ids))
        m.put(base+m.symbols['SCUMM_LIVE_ROOM_OBJECTS_OFFSET'],0x100)
        m.put(base+m.symbols['SCUMM_LIVE_ROOM_NAMES_OFFSET'],0x200)
        offset=base+0x200
        for i,identity in enumerate(ids):
            m.put(base+0x100+i*11,identity)
            name=bytes((65+i,))* (i+1)
            m.put(offset,len(name),1);m.ram[offset+1:offset+1+len(name)]=name;offset+=len(name)+1
        return m

    def test_last_valid_and_unrepresentable_identity_keep_guards_and_following_rows(self):
        ids=(1023,1024,1394,2047,3)
        m=self.machine(ids);guard=m.symbols['SAME_SCUMM_OBJECT_NAMES']+1024*32
        m.ram[guard:guard+32768]=bytes((0xC7,))*32768
        _,writes=m.consume()
        self.assertEqual(m.ram[guard:guard+32768],bytes((0xC7,))*32768)
        self.assertFalse(any(guard<=a<guard+32768 for a in writes))
        for identity,name in ((1023,b'A'),(3,b'EEEEE')):
            at=m.symbols['SAME_SCUMM_OBJECT_NAMES']+identity*32
            self.assertEqual(m.ram[at:at+32],name+bytes(32-len(name)))
            self.assertEqual(m.get(m.symbols['SAME_SCUMM_OBJECT_NAME_LENGTH']+identity,1),len(name)+1)

    def test_original_path_reproduces_invalid_name_write(self):
        m=self.machine((1024,),old=True);guard=m.symbols['SAME_SCUMM_OBJECT_NAMES']+1024*32
        _,writes=m.consume();self.assertIn(guard,writes);self.assertEqual(m.get(guard,1),65)
