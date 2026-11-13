"""Source-neutral checked cel representation: no flattened-image scaling."""
import dataclasses
import copy
import random
import unittest
import zlib
from types import SimpleNamespace

from same.engines.scumm_v5.costume import CostumeCel
from tools.actor_pose_plan import compile_cel_pose, PoseError
from tools.generate_snes_scumm_actor_sprite import compile_pose_set, pose_directory_include
from test_scumm_v5_costume import rectangular_costume


class CelResources(unittest.TestCase):
    def test_directory_rejects_invalid_cel_and_checked_chunk_boundaries(self):
        _, rows = compile_pose_set({1: ('synthetic', rectangular_costume())}, preserve_cels=True)
        index = next(i for i, r in enumerate(rows) if r['source_slot_bytes'])
        mutations = (
            lambda r: r['chunks'][0].update(pose_offset=1),
            lambda r: r['chunks'][0].update(length=2049),
            lambda r: r['chunks'][0].update(relative_offset=0xffffffff),
            lambda r: r.update(source_slot_bytes=65536),
            lambda r: r['cels'][0].update(width=0),
            lambda r: r['cels'][0].update(relative_x=32768),
            lambda r: r['cels'][0]['spans'][0].update(offset=1),
            lambda r: r['cels'][0]['spans'][0].update(length=65535),
        )
        for mutate in mutations:
            bad = copy.deepcopy(rows)
            mutate(bad[index])
            with self.assertRaises(ValueError):
                pose_directory_include(bad, bank=30)

    def test_random_roundtrip_preserves_order_transparency_and_geometry(self):
        rng = random.Random(0x5C51)
        for _ in range(1000):
            cels = tuple(CostumeCel(w, h, rng.randrange(-40, 40), rng.randrange(-40, 40),
                                   rng.randrange(-8, 8), rng.randrange(-8, 8),
                                   bytes(rng.randrange(4) for _ in range(w*h)))
                         for w, h in ((rng.randrange(1, 30), rng.randrange(1, 30))
                                      for _ in range(rng.randrange(5))))
            plan = compile_cel_pose(SimpleNamespace(cels=cels, draw_to_right=bool(rng.randrange(2))),
                                    (0, 0, 128, 255))
            self.assertEqual(plan.decoded_cels(), cels)
            self.assertTrue(all(plan.data))
            self.assertEqual(sum(c.width*c.height for c in cels),
                             sum(c.width*c.height for c in plan.cels))

    def test_overlapping_cels_are_not_flattened(self):
        cel = CostumeCel(2, 2, -1, -1, 0, 0, b'\1\2\0\1')
        plan = compile_cel_pose(SimpleNamespace(cels=(cel, cel), draw_to_right=False), (7, 0, 255))
        self.assertEqual(len(plan.data), 6)
        self.assertEqual(plan.decoded_cels(), (cel, cel))

    def test_multiple_checked_chunks_preserve_logical_offsets(self):
        cel = CostumeCel(100, 100, -50, -100, 0, 0, b'\1'*10000)
        plan = compile_cel_pose(SimpleNamespace(cels=(cel,), draw_to_right=True), (0, 0))
        chunks = plan.chunks()
        self.assertEqual([len(c.data) for c in chunks], [2048]*4+[1808])
        self.assertEqual(b''.join(c.data for c in chunks), plan.data)
        for chunk in chunks:
            self.assertEqual(zlib.crc32(chunk.data)&0xffffffff, chunk.crc32)
            bad = bytes((chunk.data[0]^1,))+chunk.data[1:]
            self.assertNotEqual(zlib.crc32(bad)&0xffffffff, chunk.crc32)

    def test_empty_pose_and_transparent_cel(self):
        for cels in ((), (CostumeCel(2, 2, -1, -1, 0, 0, bytes(4)),)):
            plan = compile_cel_pose(SimpleNamespace(cels=cels, draw_to_right=True), (0,))
            self.assertEqual(plan.chunks(), ())
            self.assertEqual(plan.decoded_cels(), cels)

    def test_malformed_cel_and_span_rejected(self):
        good = CostumeCel(2, 2, -1, -1, 0, 0, b'\1'*4)
        for bad in (dataclasses.replace(good, width=0), dataclasses.replace(good, pixels=b'\1'),
                    dataclasses.replace(good, relative_x=32768),
                    dataclasses.replace(good, pixels=b'\2'*4)):
            with self.assertRaises(PoseError):
                compile_cel_pose(SimpleNamespace(cels=(bad,), draw_to_right=True), (0, 0))
        plan = compile_cel_pose(SimpleNamespace(cels=(good,), draw_to_right=True), (0, 0))
        cel = plan.cels[0]
        bad = dataclasses.replace(cel, spans=(dataclasses.replace(cel.spans[0], offset=1),)+cel.spans[1:])
        with self.assertRaises(PoseError):
            dataclasses.replace(plan, cels=(bad,)).decoded_cels()

    def test_existing_costume_decoder_drives_checked_directory(self):
        costumes = {1: ('original synthetic', rectangular_costume())}
        payload, records = compile_pose_set(costumes, preserve_cels=True)
        self.assertTrue(payload)
        self.assertTrue(all(r['cel_format']==3 for r in records))
        text = pose_directory_include(records, bank=30)
        self.assertIn('SCUMM_V5_ACTOR_CEL_FORMAT = $01', text)
        self.assertIn('ScummV5_ActorCelDirectory0:', text)
        self.assertEqual((payload, records), compile_pose_set(costumes, preserve_cels=True))
        _, legacy = compile_pose_set(costumes)
        self.assertNotIn('cel_format', legacy[0])
        self.assertIn('SCUMM_V5_ACTOR_CEL_FORMAT = $00', pose_directory_include(legacy, bank=30))
