"""Execute production matrix instructions with an independent full Floyd oracle."""
import random
import unittest
from unittest.mock import patch

from test_scumm_camera_native_copy import StripMachine, ROOT
from tools import audit_scumm_residency_wram as ownership


def reference(edges):
    n = len(edges)
    distance = [[0 if i == j else 1 if edges[i][j] else 255
                 for j in range(n)] for i in range(n)]
    routes = [[j if i == j or edges[i][j] else 255
               for j in range(n)] for i in range(n)]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                candidate = distance[i][k] + distance[k][j]
                if candidate < distance[i][j]:
                    distance[i][j] = candidate
                    routes[i][j] = routes[i][k]
    return distance, routes


class MatrixMachine(StripMachine):
    def __init__(self, edges, wrapper=None):
        super().__init__()
        self.edges = edges
        self.service_writes = []
        self.symbols['ScummV5_Matrix_DistanceRowOffsets'] = 0x68000
        for i in range(64):
            self.put(0x68000 + i*2, i*63-i*(i-1)//2)
        source = (ROOT/'runtime/snes/engines/scumm_v5_matrix_far.pasm').read_text()
        body = source[source.index('ScummV5_Matrix_BuildRoutes_Far:'):
                      source.index('; Runtime next-hop lookup used after createBoxMatrix.')]
        helpers = source[source.index('ScummV5_Matrix_DistanceRead:'):]
        self.code, self.labels = [], {}
        for line in ((wrapper or '') + body + helpers).splitlines():
            line = line.split(';')[0].strip()
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                self.labels[line[:-1]] = len(self.code)
            else:
                self.code.append(line.replace('brl ', 'jmp '))
        self.put('SAME_SCUMM_MATRIX_BOX_COUNT', len(edges), 1)
        for i in range(64):
            self.put(self.symbols['SAME_SCUMM_MATRIX_BOX_FLAGS']+i, 0, 1)
        self.ram[0x7f1000:0x7f1800] = bytes([0xa5])*2048
        self.ram[0x7f1fe5:0x7f2000] = bytes([0x5a])*27

    def service(self, name, p, a):
        assert name == 'ScummV5_Movement_Portal_Far'
        i = self.get('SAME_SCUMM_MOVE_ROUTE_SOURCE', 1)
        j = self.get('SAME_SCUMM_MOVE_ROUTE_NEXT', 1)
        return (p & ~1) | int(self.edges[i][j]), a


class MatrixCacheOwnershipTests(unittest.TestCase):
    def test_distance_index_all_4096_coordinates_and_cache_guards(self):
        # Exercise every production adapter index, including diagonal and
        # reversed pairs. Distances can hold 0..63 and the exact FF sentinel.
        m = MatrixMachine([[False]])
        for i in range(64):
            for j in range(i+1, 64):
                offset = i*63-i*(i-1)//2+j-i-1
                m.put(0x7f1800+offset, (i*7+j*3) % 256, 1)
        helper_code, helper_labels = m.code, m.labels
        for i in range(64):
            for j in range(64):
                m.code = [f'ldx #{i*64+j}', 'sep #$20',
                          'jsr ScummV5_Matrix_DistanceRead', 'sta.l $070000', 'rtl'] + helper_code
                m.labels = {k:v+5 for k,v in helper_labels.items()}
                m.consume()
                lo, hi = sorted((i,j))
                expected = 0 if i==j else (lo*7+hi*3) % 256
                self.assertEqual(m.get(0x70000, 1), expected)
        self.assertEqual(m.ram[0x7f1000:0x7f1800], bytes([0xa5])*2048)
        self.assertEqual(m.ram[0x7f1fe5:0x7f2000], bytes([0x5a])*27)

    def test_native_instruction_routes_match_full_directed_floyd(self):
        rng = random.Random(392014)
        for n in (1, 2, 5, 8, 12):
            for _ in range(3):
                edges = [[False]*n for _ in range(n)]
                for i in range(n):
                    for j in range(i+1, n):
                        edges[i][j] = edges[j][i] = rng.random() < .35
                _, expected = reference(edges)
                m = MatrixMachine(edges)
                failed, _ = m.consume()
                self.assertFalse(failed)
                self.assertEqual(m.get('SAME_SCUMM_MATRIX_DYNAMIC_VALID',1),1)
                for i in range(n):
                    self.assertEqual(list(m.ram[0x7f2000+i*64:0x7f2000+i*64+n]),expected[i])
                self.assertEqual(m.ram[0x7f1000:0x7f1800],bytes([0xa5])*2048)
                self.assertEqual(m.ram[0x7f1fe5:0x7f2000],bytes([0x5a])*27)

    def test_ownership_audit_rejects_historical_distance_cache_alias(self):
        values = ownership.symbols()
        values['SAME_SCUMM_MATRIX_DISTANCE'] = 0x7f1000
        with patch.object(ownership, 'symbols', return_value=values):
            with self.assertRaisesRegex(ValueError, 'ownership overlaps'):
                ownership.audit()
