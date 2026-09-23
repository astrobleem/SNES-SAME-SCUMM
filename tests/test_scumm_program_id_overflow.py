import unittest
import json
import hashlib
from pathlib import Path
import subprocess
import struct
import sys
import tempfile

from generate_snes_cooked_rooms import (
    OVERFLOW_PROGRAM_IDS, PRIMARY_PROGRAM_IDS, ProgramIdAllocator,
    reserved_program_ids,
)
from same.engines.scumm_v5.cooked_room import ScriptChunkInput, encode_cooked_room


def _chunk(tag, payload):
    return tag + struct.pack(">I", len(payload) + 8) + payload


def _raw_room(locals_):
    palette = bytes(value for index in range(256) for value in (index, index, index))
    strip = bytes((1,)) + bytes(range(16))
    smap = _chunk(b"SMAP", struct.pack("<I", 12) + strip)
    rmim = _chunk(b"RMIM", _chunk(b"RMIH", struct.pack("<H", 0)) + _chunk(b"IM00", smap))
    walkboxes = (
        struct.pack("<hhhhhhhhBBH", *([-32000] * 8), 0, 0, 255),
        struct.pack("<hhhhhhhhBBH", 0, 0, 7, 0, 7, 1, 0, 1, 0, 0, 255),
    )
    box_matrix = b"\x00\x00\x00\xff\x01\x01\x01\xff"
    return b"".join((
        _chunk(b"RMHD", struct.pack("<HHH", 8, 2, 0)),
        _chunk(b"CLUT", palette), rmim,
        _chunk(b"BOXD", struct.pack("<H", 2) + b"".join(walkboxes)),
        _chunk(b"BOXM", box_matrix),
        _chunk(b"ENCD", b"\x00"), _chunk(b"EXCD", b"\x00"),
        *(_chunk(b"LSCR", bytes((number,)) + b"\xa0") for number in locals_),
    ))


def _cooked_room(room, payload):
    scripts = []
    offset = 0
    while offset < len(payload):
        tag = payload[offset:offset + 4]
        size = int.from_bytes(payload[offset + 4:offset + 8], "big")
        if tag in (b"ENCD", b"EXCD", b"LSCR"):
            if tag == b"LSCR":
                number, body_offset = payload[offset + 8], 9
            else:
                number, body_offset = (10002 if tag == b"ENCD" else 10001), 8
            identity = (
                f"room.{room}/LSCR.{number}" if tag == b"LSCR"
                else f"room.{room}/{tag.decode('ascii')}"
            )
            scripts.append(ScriptChunkInput(
                tag.decode("ascii"), number, identity, offset, body_offset,
                size - body_offset,
            ))
        offset += size
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    return encode_cooked_room(
        payload, room=room, flags=0, original_room_file_offset=100_000 + room * 1000,
        profile_sha256=digest("profile"), game_identity_sha256=digest("game"),
        archive_sha256=digest("archive"), index_sha256=digest("index"),
        data_sha256=digest("data"), scripts=tuple(scripts),
    )


class ProgramIdOverflowTests(unittest.TestCase):
    def test_48_historical_ids(self):
        allocator = ProgramIdAllocator()
        self.assertEqual(tuple(allocator.allocate() for _ in range(48)), PRIMARY_PROGRAM_IDS)

    def test_49_first_overflow(self):
        allocator = ProgramIdAllocator()
        self.assertEqual([allocator.allocate() for _ in range(49)][-1], 0xCF)

    def test_multiple_overflow_deterministic(self):
        def allocate():
            a = ProgramIdAllocator()
            return [a.allocate() for _ in range(52)]
        self.assertEqual(allocate(), allocate())
        self.assertEqual(allocate()[48:], [0xCF, 0xCE, 0xCD, 0xCC])

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'duplicate'):
            ProgramIdAllocator(pool=(0xD0, 0xD0))

    def test_exhaustion_hard_failure(self):
        a = ProgramIdAllocator()
        values = [a.allocate() for _ in range(178)]
        self.assertEqual(len(set(values)), 178)
        self.assertEqual(values[-1], 0x4E)
        with self.assertRaisesRegex(RuntimeError, 'exhausted'):
            a.allocate()

    def test_reserved_collision_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'reserved'):
            ProgramIdAllocator(reserved=reserved_program_ids() | {0xCF})

    def test_all_personality_reservations(self):
        self.assertEqual(max(reserved_program_ids()), 0x4D)
        self.assertFalse(set(OVERFLOW_PROGRAM_IDS) & reserved_program_ids())

    def test_non_byte_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'unsigned byte'):
            ProgramIdAllocator(pool=(0x100,))

    def test_generated_overflow_and_explicit_append(self):
        # Original copyright-free globals, including two historically deferred
        # records. A newly inserted input must not displace those records.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            scripts = [dict(number=i, output='stop.bin', length=1,
                            append_after_rooms=i in (47, 48)) for i in range(1, 49)]
            manifest = dict(schema='same_scumm_v5_cooked_rooms_v1',
                            num_global_scripts=200, records=[], global_scripts=scripts)
            path = root / 'manifest.json'
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'),
                       '--manifest', str(path), '--output', str(root / 'rooms.pasm'),
                       '--data-output', str(root / 'data.pasm'), '--binary-dir', str(root / 'bin'),
                       '--far-programs']
            path.write_text(json.dumps(manifest))
            subprocess.run(command, check=True, capture_output=True)
            before = (root / 'data.pasm').read_text()
            scripts.insert(0, dict(number=49, output='stop.bin', length=1))
            path.write_text(json.dumps(manifest))
            subprocess.run(command + ['--append-global-script', '49'], check=True, capture_output=True)
            after = (root / 'data.pasm').read_text()
            near = (root / 'rooms.pasm').read_text()
            for number, program in zip(range(1, 49), PRIMARY_PROGRAM_IDS):
                block = (f'cmp #${number:02X}\n'
                         f'    bne ScummV5_M23A_ResolveGlobalScript_Far__next_{program:02X}\n'
                         f'    lda #${program:02X}')
                self.assertIn(block, before)
                self.assertIn(block, after)
            self.assertIn('cmp #$31\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_CF\n    lda #$CF', after)
            self.assertIn('cmp #$CF\n    bne ScummV5_M23A_GetProgramSize__next_CF\n    rep #$20\n    .a16\n    lda #$0001\n    sec', after)
            self.assertIn('cmp #$CF\n    bne ScummV5_M23A_FetchProgramByte__next_CF\n    lda.l ScummV5_M23A_Program_CF,x\n    clc', near)
            self.assertIn('PROGRAM_COUNT = $31', near)
            self.assertIn('PROGRAM_MIN = $CF', near)
            self.assertIn('PROGRAM_IDS_IN_ALLOCATION_ORDER', near)

    def test_append_local_order_and_preserved_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            room_records = []
            for room, locals_ in ((42, (200, 202)), (75, (202,))):
                payload = _raw_room(locals_)
                name = f'room-{room}.cooked'
                (root / name).write_bytes(_cooked_room(room, payload))
                room_records.append({'room': room, 'output': name})
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': room_records,
                'global_scripts': [
                    {'number': 1, 'output': 'stop.bin', 'length': 1},
                    {'number': 2, 'output': 'stop.bin', 'length': 1},
                ],
            }))
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py')]

            def generate(name, appended=()):
                output, data = root / f'{name}.pasm', root / f'{name}-data.pasm'
                binary = root / f'{name}-bin'
                args = command + [
                    '--manifest', str(manifest), '--output', str(output),
                    '--data-output', str(data), '--binary-dir', str(binary), '--far-programs',
                    '--entry-only-room', '42', '--entry-only-room', '75',
                    '--executable-local', '42:200', '--append-global-script', '2',
                ]
                for item in appended:
                    args.extend(('--append-executable-local', item))
                result = subprocess.run(args, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(result.stdout), output.read_text(), data.read_text()

            baseline_report, baseline, baseline_data = generate('baseline')
            appended_report, generated, data = generate(
                'appended', ('42:202', '75:202'),
            )
            self.assertEqual(baseline_report['programs'], 7)
            self.assertEqual(appended_report['programs'], 9)

            # Existing room programs and the appended global retain their IDs;
            # the ordinary local remains before the appended global/local tail.
            for program in range(0xD0, 0xD7):
                label = f'ScummV5_M23A_Program_{program:02X}:'
                self.assertIn(label, baseline_data)
                self.assertIn(label, data)
            self.assertIn(
                'cmp #$01\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_D5\n    lda #$D5',
                data,
            )
            self.assertIn(
                'cmp #$02\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_D6\n    lda #$D6',
                baseline_data,
            )
            self.assertIn(
                'cmp #$02\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_D6\n    lda #$D6',
                data,
            )
            self.assertIn(
                'cmp #$C8\n    bne ScummV5_M23A_ResolveLocalScript__next_D2\n'
                '    lda #$D2', data,
            )

            # Local script 202 exists in both rooms. The active-record dispatch
            # selects a room-specific resolver arm, each with its own ID.
            self.assertIn('ScummV5_M23A_RoomNumbers:\n    .byte $2A,$4B', generated)
            self.assertIn('ScummV5_M23A_RoomLocalNumbers_0:\n    .byte $C8,$CA', generated)
            self.assertIn('ScummV5_M23A_RoomLocalPrograms_0:\n    .byte $D2,$D7', generated)
            self.assertIn('ScummV5_M23A_RoomLocalNumbers_1:\n    .byte $CA', generated)
            self.assertIn('ScummV5_M23A_RoomLocalPrograms_1:\n    .byte $D8', generated)
            resolver_start = data.index('ScummV5_M23A_ResolveLocalScript_Far:')
            room42_arm_start = data.index('ScummV5_M23A_ResolveLocalScript__record_0:', resolver_start)
            room75_arm_start = data.index('ScummV5_M23A_ResolveLocalScript__record_1:', room42_arm_start)
            dispatch = data[resolver_start:room42_arm_start]
            room42_arm = data[room42_arm_start:room75_arm_start]
            room75_arm = data[room75_arm_start:]
            self.assertIn('cmp #$00\n    bne ScummV5_M23A_ResolveLocalScript__dispatch_0', dispatch)
            self.assertIn('cmp #$01\n    bne ScummV5_M23A_ResolveLocalScript__dispatch_1', dispatch)
            self.assertIn('lda #$D2', room42_arm)
            self.assertIn('cmp #$CA', room42_arm)
            self.assertIn('lda #$D7', room42_arm)
            self.assertIn('cmp #$CA', room75_arm)
            self.assertIn('lda #$D8', room75_arm)

            # Reversing CLI order reverses only the appended local IDs.
            _, reverse_output, reverse_data = generate(
                'reversed', ('75:202', '42:202'),
            )
            self.assertIn('ScummV5_M23A_RoomLocalPrograms_0:\n    .byte $D2,$D8', reverse_output)
            self.assertIn('ScummV5_M23A_RoomLocalPrograms_1:\n    .byte $D7', reverse_output)
            for program in range(0xD0, 0xD7):
                self.assertIn(f'ScummV5_M23A_Program_{program:02X}:', reverse_data)

            # Malformed and conflicting selections fail before producing a ROM map.
            base = command + [
                '--manifest', str(manifest), '--output', str(root / 'bad.pasm'),
                '--data-output', str(root / 'bad-data.pasm'),
                '--binary-dir', str(root / 'bad-bin'), '--far-programs',
                '--entry-only-room', '42', '--entry-only-room', '75',
                '--append-global-script', '2',
            ]
            # A malformed local selector and duplicate append selections fail
            # before any output is produced.
            for extra, message in [
                (['--append-executable-local', '1'], 'requires ROOM:SCRIPT'),
                (['--append-executable-local', '42:202', '--append-executable-local', '42:202'], 'duplicate'),
                (['--executable-local', '42:202', '--append-executable-local', '42:202'], 'both ordinary'),
            ]:
                result = subprocess.run(base + extra, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr + result.stdout)

    def test_append_local_cli_is_exposed(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'), '--help'],
            check=True, capture_output=True, text=True,
        )
        self.assertIn('--append-executable-local', result.stdout)
