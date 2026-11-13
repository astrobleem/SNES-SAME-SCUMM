"""Shared checked allocations preserve distinct source bodies and logical PCs."""
import hashlib
import tempfile
import unittest
import zlib
from pathlib import Path
from same.engines.scumm_v5.program_storage import build_program_storage


class PackedStorageTests(unittest.TestCase):
    def build(self, root, *, packed=True):
        sizes = (787, 120, 107, 163, 181, 21002)
        entries = [dict(program_unit_id=i, identity=f'unit-{i}',
                        kind='GLOBAL' if i == 0 else 'LSCR',
                        room=None if i == 0 else 42,
                        bundle='global' if i == 0 else 'room42')
                   for i in range(len(sizes))]
        bodies = {f'unit-{i}': bytes((j*17+i)&255 for j in range(size))
                  for i,size in enumerate(sizes)}
        metadata = {k: {'instruction_spans': [[pc, 1] for pc in range(len(b))]}
                    for k,b in bodies.items()}
        result = build_program_storage({'entries': entries}, bodies, root,
                                       page_metadata=metadata, pack_small=packed,
                                       rom_bank=10, page_directory_bank=12)
        return result, bodies

    def test_measured_working_set_uses_two_checked_allocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);r,b=self.build(root)
            self.assertEqual(len(r['checked_storage_groups']),1)
            self.assertEqual(set(r['checked_storage_groups'][0]),{1,2,3,4})
            self.assertEqual(sum(len(x) for x in b.values()),r['program_body_bytes'])
            payload=(root/'scumm-program-bodies.bin').read_bytes()
            for record in r['records']:
                data=b[record['identity']];offset=record['section_relative_offset']
                self.assertEqual(payload[offset:offset+record['length']],data)
                self.assertEqual(record['sha256'],hashlib.sha256(data).hexdigest())
            group=r['page_records'][r['page_indices'][1]['first_page']]
            self.assertEqual(group['length'],571)
            anchor=r['records'][group['storage_anchor_id']]
            data=payload[anchor['section_relative_offset']:anchor['section_relative_offset']+571]
            self.assertEqual(group['crc32'],f'{zlib.crc32(data)&0xffffffff:08x}')
            identities={('group',r['records'][i]['storage_anchor_id']) if 'storage_anchor_id' in r['records'][i] else ('unit',i) for i in range(5)}
            self.assertEqual(len(identities),2)

    def test_every_member_offset_and_crc_reject_neighbor_or_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            r,b=self.build(Path(tmp));raw=(Path(tmp)/'scumm-program-bodies.bin').read_bytes()
            for unit in range(1,5):
                index=r['page_indices'][unit];self.assertTrue(index['encoded_count']&0x8000)
                page=r['page_records'][index['first_page']];anchor=r['records'][page['storage_anchor_id']]
                group=raw[anchor['section_relative_offset']:anchor['section_relative_offset']+page['length']]
                off=index['encoded_count']&0x7fff;body=b[f'unit-{unit}']
                self.assertEqual(group[off:off+len(body)],body)
                self.assertLessEqual(off+len(body),len(group))
                for position in (0,off,len(group)-1):
                    bad=bytearray(group);bad[position]^=1
                    self.assertNotEqual(zlib.crc32(bad)&0xffffffff,int(page['crc32'],16))
            large=r['page_indices'][5];self.assertNotIn('encoded_count',large)
            pages=r['page_records'][large['first_page']:large['first_page']+large['page_count']]
            self.assertEqual(sum(p['length'] for p in pages),21002)
            self.assertTrue(all(p['length']<=2048 for p in pages))

    def test_deterministic_complete_artifacts_and_legacy_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b';c=Path(tmp)/'c'
            self.build(a);self.build(b);old,_=self.build(c,packed=False)
            # Package manifest paths are intentionally rooted in each build.
            for name in ('scumm-program-bodies.bin','scumm_msu1_programs.inc.pasm','program-storage.json'):
                self.assertEqual((a/name).read_bytes(),(b/name).read_bytes(),name)
            self.assertFalse(old['packed_small_programs']);self.assertFalse(old['checked_storage_groups'])
            self.assertTrue(all('encoded_count' not in i for i in old['page_indices']))

if __name__=='__main__':unittest.main()
