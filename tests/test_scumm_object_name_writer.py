"""Execute the real bounded byte-writer instructions; native proof is separate."""
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


class ObjectNameWriterTests(unittest.TestCase):
    def test_encoded_bytes_and_bounded_lengths_preserve_neighbor_records(self):
        source=(ROOT/'runtime/snes/engines/scumm_v5_object_name_cache_far.pasm').read_text()
        helper=source[source.index('ScummV5_ObjectNameCache_StoreByte_Far:'):]
        for identity in (0,8,1023,1024,1500):
            for raw in (b'\0',b'Lamp\0',b'A\xff\x04\0\x01B\0',
                        b'x'*30+b'\0',b'y'*31+b'\0',b'z'*40+b'\0'):
                with self.subTest(identity=identity,raw=raw):
                    m=StripMachine()
                    m.symbols.update(SAME_SCUMM_OBJECT_NAME_OBJECT=0x200,
                        SAME_SCUMM_OBJECT_NAME_INDEX=0x202,SAME_SCUMM_FETCH_BYTE=0x203,
                        SAME_SCUMM_C17_PARAM0=0x204,SAME_SCUMM_OBJECT_NAME_COUNT=1024,
                        SAME_SCUMM_OBJECT_NAMES=0x7E9000)
                    m.put('SAME_SCUMM_OBJECT_NAME_OBJECT',identity)
                    base=m.symbols['SAME_SCUMM_OBJECT_NAMES']
                    m.ram[base-1:base+32769]=b'\xa5'*32770
                    driver='\n'.join(f'sep #$20\nlda #${b:02x}\njsr ScummV5_ObjectNameCache_StoreByte_Far' for b in raw)
                    m.code=[];m.labels={}
                    for line in (driver+'\nrtl\n'+helper).splitlines():
                        line=line.split(';')[0].strip()
                        if not line or line.startswith('.'):continue
                        if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                        else:m.code.append(line)
                    m.consume()
                    self.assertEqual(m.get('SAME_SCUMM_OBJECT_NAME_INDEX',1),min(len(raw),32))
                    expected=bytearray(b'\xa5'*32770)
                    if identity<1024:
                        for i,b in enumerate(raw):expected[1+identity*32+min(i,31)]=b
                    self.assertEqual(m.ram[base-1:base+32769],expected)
