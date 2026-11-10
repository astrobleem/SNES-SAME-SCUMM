"""Exercise generator emission and mandatory capacity auditing without assembly."""
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from audit_snes_rom import map_capacity_errors
from finalize_snes_rom import finalize


class GeometryBankCapacityTests(unittest.TestCase):
    def geometry_lines(self):
        tree = ast.parse((ROOT/'tools/generate_snes_cooked_rooms.py').read_text())
        def contains(node, label):
            return any(isinstance(n, ast.Constant) and n.value == label for n in ast.walk(node))
        for node in ast.walk(tree):
            body = getattr(node, 'body', None)
            if not isinstance(body, list): continue
            # Locate direct emission statements, not their enclosing function.
            starts = [i for i,n in enumerate(body) if isinstance(n, ast.Expr)
                      and contains(n, 'ScummV5_PutActor_LoadGeometry_Far:')]
            if not starts: continue
            start = starts[0]
            end = next(i for i in range(start+1, len(body))
                       if isinstance(body[i], ast.Expr) and contains(body[i], 'ScummV5_ObjectOwner_Query_Far:'))
            namespace = {'data_lines': [], 'records': [{'walkbox_flags': [0]} for _ in range(96)]}
            exec(compile(ast.Module(body=body[start:end], type_ignores=[]), '<geometry-emission>', 'exec'), namespace)
            return namespace['data_lines']
        self.fail('geometry emission not found')

    def test_live_excludes_entire_static_dispatch_rom_retains_all_records(self):
        lines = self.geometry_lines()
        self.assertEqual(lines[-1], '.endif', 'conditional must close before ObjectOwner')
        for live in (False, True):
            output, active, in_if = [], True, False
            for line in lines:
                if line == '.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES':
                    self.assertFalse(in_if)
                    active, in_if = live, True
                elif line == '.else':
                    self.assertTrue(in_if)
                    active = not live
                elif line == '.endif':
                    self.assertTrue(in_if)
                    active, in_if = True, False
                elif active: output.append(line)
            self.assertFalse(in_if)
            if live:
                self.assertEqual(output, ['ScummV5_PutActor_LoadGeometry_Far:',
                                          '    jml ScummV5_LiveRoom_LoadGeometry_Far'])
            else:
                self.assertNotIn('    jml ScummV5_LiveRoom_LoadGeometry_Far', output)
                self.assertEqual(sum(line.startswith('ScummV5_PutActor_LoadGeometry__copy_') for line in output), 96)
                self.assertIn('lda.l ScummV5_PutActor_Record_95_Geometry_Address+16,x', output)
                self.assertEqual(output[-2:], ['    sec', '    rtl'])

    def test_build_map_argument_is_unconditional_for_both_carriers(self):
        shell = (ROOT/'tools/build_snes.sh').read_text()
        block = shell[shell.index('ROM_AUDIT_ARGS='):shell.index('sha256sum "$SAME_SNES_OUTPUT"')]
        self.assertNotIn('if ', block)
        self.assertIn('--map "$SAME_SNES_MAP"', block)
        self.assertIn('"${ROM_AUDIT_ARGS[@]}"', block)
        ps = (ROOT/'tools/build_snes.ps1').read_text()
        self.assertIn('-o $Output -m $Map --no-verify', ps)
        self.assertIn('"tools\\audit_snes_rom.py" $Output --carrier $Carrier --manifest $CarrierManifest --map $Map', ps)

    def test_saved_overflow_segment_is_rejected_by_sa1_cli(self):
        # Exact segment row from the failing a24j map; no archive/ROM fixture.
        row = '; 15   $8000     $11a87      39560     39560\n'
        errors = map_capacity_errors(row)
        self.assertEqual(len(errors), 1)
        self.assertIn('segment 15 uses 39560 bytes', errors[0])
        self.assertEqual(map_capacity_errors('; 15 $8000 $ffff 32768 32768\n'), [])
        raw = bytearray(0x8000)
        raw[0x7FC0:0x7FD0] = b'SAME ENGINE HOST'
        raw[0x7FD5:0x7FD9] = bytes((0x23, 0x35, 5, 7))
        for offset in (0x7FFA, 0x7FFC, 0x7FFE):
            raw[offset:offset+2] = b'\x00\x80'
        with tempfile.TemporaryDirectory() as directory:
            rom, mapfile = Path(directory)/'fixture.sfc', Path(directory)/'fixture.map'
            rom.write_bytes(finalize(bytes(raw), carrier="sa1_bwram"))
            mapfile.write_text(row)
            result = subprocess.run([sys.executable, str(ROOT/'tools/audit_snes_rom.py'),
                                     str(rom), '--carrier', 'sa1_bwram', '--map', str(mapfile)],
                                    capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('segment 15 uses 39560 bytes', result.stderr)


if __name__ == '__main__':
    unittest.main()
