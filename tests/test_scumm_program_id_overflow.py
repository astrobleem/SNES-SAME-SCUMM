import unittest
import json
import hashlib
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import re

from generate_snes_cooked_rooms import (
    OVERFLOW_PROGRAM_IDS, PRIMARY_PROGRAM_IDS, ProgramIdAllocator,
    cpu_visible_rom_bank, cpu_visible_rom_symbol, reserved_program_ids,
)
from same.engines.scumm_v5.cooked_room import HEADER, ScriptChunkInput, encode_cooked_room


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


def _raw_room_with_object(object_id, locals_=()):
    raw = bytearray(_raw_room(locals_))
    # RMHD starts at byte zero; its third little-endian word is object count.
    raw[12:14] = (1).to_bytes(2, 'little')
    cdhd = _chunk(
        b'CDHD', struct.pack('<HBBBBBBhhB', object_id, 1, 1, 1, 1, 0, 0, 1, 1, 0)
    )
    # VERB's table points at its final STOP byte. The object is a minimal
    # copyright-free OBCD fixture, sufficient to test generated dispatch.
    verb_payload = bytes((3,)) + (12).to_bytes(2, 'little') + bytes((0, 0xA0))
    raw.extend(_chunk(b'OBCD', cdhd + _chunk(b'VERB', verb_payload)))
    return bytes(raw)


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
            self.assertIn(
                'ScummV5_M23A_FetchProgramByte:\n'
                '    jsl ScummV5_M23A_FetchProgramByte_Far_Address\n'
                '    rts', near,
            )
            self.assertIn(
                'cmp #$CF\n'
                '    bne ScummV5_M23A_FetchProgramByte__next_CF\n'
                '    lda.l ScummV5_M23A_Program_CF,x\n'
                '    clc\n'
                '    rtl', after,
            )
            self.assertIn(
                'ScummV5_M23A_FetchProgramByte_Far_Address = ', after,
            )
            self.assertIn('PROGRAM_COUNT = $31', near)
            self.assertIn('PROGRAM_MIN = $CF', near)
            self.assertIn('PROGRAM_IDS_IN_ALLOCATION_ORDER', near)

    def test_appended_executable_object_preserves_existing_program_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            cooked = root / 'room-42.cooked'
            cooked.write_bytes(_cooked_room(42, _raw_room_with_object(61)))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': [{'room': 42, 'output': cooked.name}],
                'global_scripts': [{'number': 1, 'output': 'stop.bin', 'length': 1}],
            }))
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, append_object=False):
                output, data = root / f'{name}.pasm', root / f'{name}-data.pasm'
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(output), '--data-output', str(data),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42',
                ]
                if append_object:
                    command.extend(('--append-executable-local-object', '42:61'))
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(result.stdout), output.read_text(), data.read_text()

            before_report, before_output, before_data = generate('before')
            after_report, _, after_data = generate('after', append_object=True)
            routine_label = 'ScummV5_Matrix_LoadActiveRoomNames_Far:'
            address_label = 'ScummV5_Matrix_LoadActiveRoomNames_Far_Address'
            self.assertIn(f'jsl {address_label}', before_data)
            helper_bank = int(re.findall(
                r'^\.bank (\d+)$', before_data, re.MULTILINE
            )[-1])
            for label in (
                'ScummV5_Matrix_LoadActiveRoomNames_Far',
                'ScummV5_M23A_GetProgramSize_Far',
                'ScummV5_M23A_ResolveGlobalScript_Far',
            ):
                self.assertIn(
                    f'{label}_Address = ' + cpu_visible_rom_symbol(
                        helper_bank, label, sa1_aliases=False,
                    ),
                    before_data,
                )
            self.assertIn(
                'jsl ScummV5_M23A_GetProgramSize_Far_Address', before_output
            )
            self.assertIn(
                'jsl ScummV5_M23A_ResolveGlobalScript_Far_Address', before_output
            )
            self.assertNotIn(
                'jsl ScummV5_M23A_GetProgramSize_Far\n', before_output
            )
            before_ids = {item['identity']: item['id'] for item in before_report['program_map']}
            after_ids = {item['identity']: item['id'] for item in after_report['program_map']}
            self.assertEqual(after_report['programs'], before_report['programs'] + 1)
            for identity, program_id in before_ids.items():
                self.assertEqual(after_ids[identity], program_id)
            object_mapping = next(
                item for item in after_report['program_map']
                if item['identity'] == 'room.42/object.61/OBCD'
            )
            self.assertEqual(object_mapping['id'], max(before_ids.values()) + 1)
            self.assertIn(
                f'    cmp #$003D\n    beq ScummV5_ObjectProgram_Resolve_Far__object_{object_mapping["id"]:02X}',
                after_data,
            )
            self.assertIn(
                f'ScummV5_ObjectProgram_Resolve_Far__object_{object_mapping["id"]:02X}:',
                after_data,
            )

    def test_final_appended_local_preserves_existing_object_and_script_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            cooked = root / 'room-42.cooked'
            cooked.write_bytes(_cooked_room(
                42, _raw_room_with_object(61, locals_=(200, 202)),
            ))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': [{'room': 42, 'output': cooked.name}],
                'global_scripts': [
                    {'number': 1, 'output': 'stop.bin', 'length': 1},
                    {'number': 2, 'output': 'stop.bin', 'length': 1, 'append_after_rooms': True},
                ],
            }))
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, include_final=False):
                output, data = root / f'{name}.pasm', root / f'{name}-data.pasm'
                contents = json.loads(manifest.read_text())
                if include_final:
                    contents['global_scripts'].append(
                        {'number': 3, 'output': 'stop.bin', 'length': 1}
                    )
                manifest.write_text(json.dumps(contents))
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(output), '--data-output', str(data),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42',
                    '--append-executable-local-object', '42:61',
                    '--append-late-global-script', '2',
                ]
                if include_final:
                    command.extend((
                        '--append-final-executable-local', '42:202',
                        '--append-final-global-script', '3',
                    ))
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(result.stdout), output.read_text(), data.read_text()

            before, _, _ = generate('before')
            after, output, data = generate('after', include_final=True)
            before_ids = {item['identity']: item['id'] for item in before['program_map']}
            after_ids = {item['identity']: item['id'] for item in after['program_map']}
            self.assertEqual(after['programs'], before['programs'] + 2)
            for identity, program_id in before_ids.items():
                self.assertEqual(after_ids[identity], program_id, identity)
            new_local, new_global = after['program_map'][-2:]
            self.assertEqual(new_local['identity'], 'room.42/LSCR.202')
            self.assertEqual(new_global['identity'], 'script.3')
            self.assertIn(f'ScummV5_M23A_Program_{new_local["id"]:02X}:', data)
            self.assertIn(
                'ScummV5_M23A_RoomLocalPrograms_0:\n'
                f'    .byte ${new_local["id"]:02X}', output,
            )
            self.assertIn(f'ScummV5_M23A_Program_{new_global["id"]:02X}:', data)

    def test_post_terminal_global_preserves_terminal_object_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            cooked = root / 'room-42.cooked'
            cooked.write_bytes(_cooked_room(42, _raw_room_with_object(61)))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': [{'room': 42, 'output': cooked.name}],
                'global_scripts': [
                    {'number': 1, 'output': 'stop.bin', 'length': 1},
                    {'number': 2, 'output': 'stop.bin', 'length': 1},
                ],
            }))
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, add_later_global=False):
                output, data = root / f'{name}.pasm', root / f'{name}-data.pasm'
                contents = json.loads(manifest.read_text())
                if add_later_global:
                    contents['global_scripts'].append(
                        {'number': 3, 'output': 'stop.bin', 'length': 1}
                    )
                manifest.write_text(json.dumps(contents))
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(output), '--data-output', str(data),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42',
                    '--append-terminal-global-script', '2',
                    '--append-terminal-executable-local-object', '42:61',
                ]
                if add_later_global:
                    command.append('--append-post-terminal-global-script')
                    command.append('3')
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(result.stdout), output.read_text(), data.read_text()

            before, _, _ = generate('before')
            after, output, data = generate('after', add_later_global=True)
            before_ids = {item['identity']: item['id'] for item in before['program_map']}
            after_ids = {item['identity']: item['id'] for item in after['program_map']}
            self.assertEqual(after['programs'], before['programs'] + 1)
            for identity, program_id in before_ids.items():
                self.assertEqual(after_ids[identity], program_id, identity)
            self.assertEqual(after['program_map'][-1]['identity'], 'script.3')
            self.assertIn(
                f'ScummV5_M23A_Program_{after_ids["script.3"]:02X}:', data,
            )
            self.assertIn(
                f'cmp #$03\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_'
                f'{after_ids["script.3"]:02X}',
                data,
            )

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
            self.assertIn(
                'ScummV5_M23A_ResolveLocalScript_Far_Address = ', data
            )
            self.assertIn(
                'jsl ScummV5_M23A_ResolveLocalScript_Far_Address', generated
            )
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
        self.assertIn('--append-final-executable-local', result.stdout)
        self.assertIn('--append-final-global-script', result.stdout)
        self.assertIn('--append-terminal-global-script', result.stdout)

    def test_expected_room_directories_move_to_a_bounded_bank(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            short_room = _raw_room(()) + _chunk(b'LSCR', bytes((200, 0xA0)))
            short_cooked = _cooked_room(42, short_room)
            target_size = 0x7F80
            body = bytes((0xA0,)) * (1 + target_size - len(short_cooked))
            raw = _raw_room(()) + _chunk(b'LSCR', bytes((200,)) + body)
            cooked = _cooked_room(42, raw)
            self.assertEqual(len(cooked), target_size)
            directory_size = HEADER.size + 3 * 96
            self.assertGreater(target_size + directory_size, 0x8000)
            (root / 'room-42.cooked').write_bytes(cooked)
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': [{'room': 42, 'output': 'room-42.cooked'}],
                'global_scripts': [],
            }))
            output, data = root / 'rooms.pasm', root / 'data.pasm'
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'
            result = subprocess.run([
                sys.executable, str(generator), '--manifest', str(manifest),
                '--output', str(output), '--data-output', str(data),
                '--binary-dir', str(root / 'segments'), '--far-programs',
            ], capture_output=True, text=True)
            if result.returncode:
                self.fail(result.stderr + result.stdout)

            generated = data.read_text()
            self.assertIn(
                '.bank 3\n.org $8000\nScummV5_M23A_Record_0_Segment_0:',
                generated,
            )
            self.assertIn(
                '.bank 4\n.org $8000\nScummV5_M23A_Record_0_ExpectedDirectory:',
                generated,
            )
            self.assertNotIn(
                'ScummV5_M23A_Record_0_Segment_0:\n'
                f'    .incbin "{(root / "segments/record-0-segment-0.bin").resolve()}"\n'
                'ScummV5_M23A_Record_0_ExpectedDirectory:',
                generated,
            )

    def test_late_appended_local_follows_late_global_without_renumbering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            records = []
            for room in (42, 49):
                name = f'room-{room}.cooked'
                (root / name).write_bytes(_cooked_room(room, _raw_room((200,))))
                records.append({'room': room, 'output': name})
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': records,
                'global_scripts': [
                    {'number': 1, 'output': 'stop.bin', 'length': 1},
                    {'number': 2, 'output': 'stop.bin', 'length': 1},
                ],
            }))
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, *, late_local):
                output, data = root / f'{name}.pasm', root / f'{name}-data.pasm'
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(output), '--data-output', str(data),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42', '--entry-only-room', '49',
                    '--append-executable-local', '42:200',
                    '--append-late-global-script', '2',
                ]
                if late_local:
                    command.extend(('--append-late-executable-local', '49:200'))
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(result.stdout), output.read_text(), data.read_text()

            base_report, base_output, base_data = generate('base', late_local=False)
            full_report, output, data = generate('full', late_local=True)
            self.assertEqual(base_report['programs'], 7)
            self.assertEqual(full_report['programs'], 8)
            # The normal appended local remains before the explicitly late
            # global; the late local follows it and cannot shift that global.
            self.assertIn('cmp #$C8\n    bne ScummV5_M23A_ResolveLocalScript__next_D5\n    lda #$D5', base_data)
            self.assertIn('cmp #$C8\n    bne ScummV5_M23A_ResolveLocalScript__next_D5\n    lda #$D5', data)
            self.assertIn('cmp #$02\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_D6\n    lda #$D6', data)
            self.assertIn('ScummV5_M23A_RoomLocalPrograms_1:\n    .byte $D7', output)
            self.assertIn('cmp #$C8\n    bne ScummV5_M23A_ResolveLocalScript__next_D7\n    lda #$D7', data)

    def test_new_room_entry_exit_and_local_can_append_after_accepted_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            room42 = root / 'room-42.cooked'
            room49 = root / 'room-49.cooked'
            room42.write_bytes(_cooked_room(42, _raw_room((200, 202))))
            room49.write_bytes(_cooked_room(49, _raw_room((200,))))
            manifest = root / 'manifest.json'
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, *, include_room49):
                records = [{'room': 42, 'output': room42.name}]
                if include_room49:
                    records.append({'room': 49, 'output': room49.name})
                manifest.write_text(json.dumps({
                    'schema': 'same_scumm_v5_cooked_rooms_v1',
                    'num_global_scripts': 200,
                    'records': records,
                    'global_scripts': [
                        {'number': 1, 'output': 'stop.bin', 'length': 1},
                        {'number': 2, 'output': 'stop.bin', 'length': 1},
                    ],
                }))
                output, data = root / f'{name}.pasm', root / f'{name}-data.pasm'
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(output), '--data-output', str(data),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42', '--entry-only-room', '49',
                    '--append-executable-local', '42:200',
                    '--append-late-global-script', '2',
                ]
                if include_room49:
                    command.extend((
                        '--append-late-room-entry-exit', '49',
                        '--append-late-executable-local', '49:200',
                    ))
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(result.stdout), output.read_text(), data.read_text()

            base_report, base_output, base_data = generate('base', include_room49=False)
            full_report, full_output, full_data = generate('full', include_room49=True)
            self.assertEqual((base_report['programs'], full_report['programs']), (5, 8))
            # The prior room, local, and late-global IDs are byte-for-byte
            # preserved; only the newly introduced room resources consume tail IDs.
            self.assertIn('ScummV5_M23A_RoomEntryPrograms:\n    .byte $D0', base_output)
            self.assertIn('ScummV5_M23A_RoomEntryPrograms:\n    .byte $D0,$D5', full_output)
            self.assertIn('ScummV5_M23A_RoomExitPrograms:\n    .byte $D1', base_output)
            self.assertIn('ScummV5_M23A_RoomExitPrograms:\n    .byte $D1,$D6', full_output)
            self.assertIn('cmp #$01\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_D2\n    lda #$D2', base_data)
            self.assertIn('cmp #$01\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_D2\n    lda #$D2', full_data)
            self.assertIn('cmp #$02\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_D4\n    lda #$D4', base_data)
            self.assertIn('cmp #$02\n    bne ScummV5_M23A_ResolveGlobalScript_Far__next_D4\n    lda #$D4', full_data)
            self.assertIn('ScummV5_M23A_RoomLocalPrograms_0:\n    .byte $D3', base_output)
            self.assertIn('ScummV5_M23A_RoomLocalPrograms_1:\n    .byte $D7', full_output)

    def test_room_entry_exit_append_preserves_record_order_and_allocation_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            room24 = root / 'room-24.cooked'
            room42 = root / 'room-42.cooked'
            room24.write_bytes(_cooked_room(24, _raw_room(())))
            room42.write_bytes(_cooked_room(42, _raw_room(())))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': [
                    {'room': 24, 'output': room24.name},
                    {'room': 42, 'output': room42.name},
                ],
                'global_scripts': [
                    {'number': 1, 'output': 'stop.bin', 'length': 1},
                    {'number': 2, 'output': 'stop.bin', 'length': 1},
                ],
            }))
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'
            output, data, report_path = (
                root / 'ordered.pasm', root / 'ordered-data.pasm', root / 'report.json'
            )
            result = subprocess.run([
                sys.executable, str(generator), '--manifest', str(manifest),
                '--output', str(output), '--data-output', str(data),
                '--binary-dir', str(root / 'ordered-bin'), '--far-programs',
                '--append-room-entry-exit', '24', '--report', str(report_path),
            ], capture_output=True, text=True)
            if result.returncode:
                self.fail(result.stderr + result.stdout)

            generated = output.read_text()
            report = json.loads(report_path.read_text())
            self.assertEqual(report['rooms'], [24, 42])
            identities = {item['identity']: item['id'] for item in report['program_map']}
            self.assertEqual(identities['room.42/ENCD'], 0xD0)
            self.assertEqual(identities['room.42/EXCD'], 0xD1)
            self.assertEqual(identities['room.24/ENCD'], 0xD2)
            self.assertEqual(identities['room.24/EXCD'], 0xD3)
            self.assertEqual(identities['script.1'], 0xD4)
            self.assertEqual(identities['script.2'], 0xD5)
            self.assertIn('ScummV5_M23A_RoomEntryPrograms:\n    .byte $D2,$D0', generated)
            self.assertIn('ScummV5_M23A_RoomExitPrograms:\n    .byte $D3,$D1', generated)

    def test_entry_only_room_omits_unselected_object_verb_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            room42 = root / 'room-42.cooked'
            room74 = root / 'room-74.cooked'
            room42.write_bytes(_cooked_room(42, _raw_room(())))
            room74.write_bytes(_cooked_room(74, _raw_room_with_object(61)))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': [
                    {'room': 42, 'output': room42.name},
                    {'room': 74, 'output': room74.name},
                ],
                'global_scripts': [],
            }))
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, *, select_object):
                output = root / f'{name}.pasm'
                data = root / f'{name}-data.pasm'
                report = root / f'{name}.json'
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(output), '--data-output', str(data),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42', '--entry-only-room', '74',
                    '--append-terminal-room-entry-exit', '74', '--report', str(report),
                ]
                if select_object:
                    command.extend(('--append-terminal-executable-local-object', '74:61'))
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return data.read_text(), json.loads(report.read_text())

            unselected_data, unselected_report = generate('unselected', select_object=False)
            unselected_count = re.search(
                r'ScummV5_Verb_Record_1_Count = \$(\w+)', unselected_data,
            )
            self.assertIsNotNone(unselected_count)
            self.assertEqual(int(unselected_count.group(1), 16), 0)
            self.assertNotIn('room.74/object.61/OBCD', {
                item['identity'] for item in unselected_report['program_map']
            })

            selected_data, selected_report = generate('selected', select_object=True)
            selected_count = re.search(
                r'ScummV5_Verb_Record_1_Count = \$(\w+)', selected_data,
            )
            self.assertIsNotNone(selected_count)
            self.assertGreater(int(selected_count.group(1), 16), 0)
            self.assertIn('room.74/object.61/OBCD', {
                item['identity'] for item in selected_report['program_map']
            })

    def test_last_append_phase_preserves_terminal_profile_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            room42 = root / 'room-42.cooked'
            room75 = root / 'room-75.cooked'
            room74 = root / 'room-74.cooked'
            room42.write_bytes(_cooked_room(42, _raw_room((200,))))
            room75.write_bytes(_cooked_room(75, _raw_room_with_object(62, (200, 201))))
            room74.write_bytes(_cooked_room(74, _raw_room_with_object(61, (200, 201))))
            manifest = root / 'manifest.json'
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, *, include_room74):
                records = [
                    {'room': 42, 'output': room42.name},
                    {'room': 75, 'output': room75.name},
                ]
                if include_room74:
                    records.append({'room': 74, 'output': room74.name})
                manifest.write_text(json.dumps({
                    'schema': 'same_scumm_v5_cooked_rooms_v1',
                    'num_global_scripts': 200,
                    'records': records,
                    'global_scripts': [
                        {'number': 1, 'output': 'stop.bin', 'length': 1},
                        {'number': 3, 'output': 'stop.bin', 'length': 1},
                    ],
                }))
                report = root / f'{name}.json'
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(root / f'{name}.pasm'),
                    '--data-output', str(root / f'{name}-data.pasm'),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42', '--entry-only-room', '75',
                    '--executable-local', '42:200',
                    '--append-terminal-room-entry-exit', '75',
                    '--append-terminal-executable-local', '75:200',
                    '--append-post-terminal-executable-local', '75:201',
                    '--append-terminal-executable-local-object', '75:62',
                    '--append-post-terminal-global-script', '3',
                    '--report', str(report),
                ]
                if include_room74:
                    command.extend((
                        '--entry-only-room', '74',
                        '--append-last-room-entry-exit', '74',
                        '--append-last-executable-local', '74:200',
                        '--append-last-executable-local', '74:201',
                        '--append-last-executable-local-object', '74:61',
                    ))
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(report.read_text())

            base = generate('base', include_room74=False)
            extended = generate('extended', include_room74=True)
            base_ids = {item['identity']: item['id'] for item in base['program_map']}
            extended_ids = {item['identity']: item['id'] for item in extended['program_map']}
            for identity, program_id in base_ids.items():
                self.assertEqual(extended_ids.get(identity), program_id, identity)
            self.assertEqual(extended['programs'], base['programs'] + 5)
            self.assertEqual(
                [item['identity'] for item in extended['program_map'][-5:]],
                [
                    'room.74/ENCD', 'room.74/EXCD',
                    'room.74/LSCR.200', 'room.74/LSCR.201',
                    'room.74/object.61/OBCD',
                ],
            )

    def test_terminal_room_closure_preserves_every_established_program_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            room42 = root / 'room-42.cooked'
            room74 = root / 'room-74.cooked'
            room42.write_bytes(_cooked_room(42, _raw_room((200, 202))))
            room74.write_bytes(_cooked_room(
                74, _raw_room_with_object(61, (200, 201, 202)),
            ))
            manifest = root / 'manifest.json'
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, *, include_room74, include_terminal_global=False):
                records = [{'room': 42, 'output': room42.name}]
                if include_room74:
                    records.append({'room': 74, 'output': room74.name})
                global_scripts = [
                    {'number': 1, 'output': 'stop.bin', 'length': 1},
                ]
                if include_terminal_global:
                    global_scripts.append(
                        {'number': 3, 'output': 'stop.bin', 'length': 1}
                    )
                manifest.write_text(json.dumps({
                    'schema': 'same_scumm_v5_cooked_rooms_v1',
                    'num_global_scripts': 200,
                    'records': records,
                    'global_scripts': global_scripts,
                }))
                output, data, report = (
                    root / f'{name}.pasm', root / f'{name}-data.pasm',
                    root / f'{name}.json',
                )
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(output), '--data-output', str(data),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42', '--executable-local', '42:200',
                    '--append-final-executable-local', '42:202', '--report', str(report),
                ]
                if include_room74:
                    command.extend((
                        '--entry-only-room', '74',
                        '--append-terminal-room-entry-exit', '74',
                        '--append-terminal-executable-local', '74:200',
                        '--append-terminal-executable-local', '74:201',
                        '--append-post-terminal-executable-local', '74:202',
                        '--append-terminal-executable-local-object', '74:61',
                    ))
                if include_terminal_global:
                    command.extend(('--append-terminal-global-script', '3'))
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(report.read_text())

            base = generate('base', include_room74=False)
            extended = generate(
                'extended', include_room74=True, include_terminal_global=True
            )
            base_ids = {item['identity']: item['id'] for item in base['program_map']}
            extended_ids = {item['identity']: item['id'] for item in extended['program_map']}
            for identity, program_id in base_ids.items():
                self.assertEqual(extended_ids[identity], program_id, identity)
            self.assertEqual(extended['programs'], base['programs'] + 7)
            new_entries = [
                item['identity'] for item in extended['program_map'][-7:]
            ]
            self.assertEqual(new_entries, [
                'room.74/ENCD', 'room.74/EXCD',
                'room.74/LSCR.200', 'room.74/LSCR.201', 'script.3',
                'room.74/LSCR.202',
                'room.74/object.61/OBCD',
            ])
            allocator = ProgramIdAllocator()
            for _ in range(base['programs']):
                allocator.allocate()
            expected_new_ids = [allocator.allocate() for _ in range(7)]
            self.assertEqual(
                [item['id'] for item in extended['program_map'][-7:]],
                expected_new_ids,
            )

    def test_ultimate_local_append_preserves_last_global_and_object_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\xa0')
            cooked = root / 'room-42.cooked'
            cooked.write_bytes(_cooked_room(
                42, _raw_room_with_object(61, locals_=(200, 202, 203)),
            ))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': [{'room': 42, 'output': cooked.name}],
                'global_scripts': [
                    {'number': 1, 'output': 'stop.bin', 'length': 1},
                    {'number': 2, 'output': 'stop.bin', 'length': 1},
                ],
            }))
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'

            def generate(name, include_ultimate=False):
                output, data, report = (
                    root / f'{name}.pasm', root / f'{name}-data.pasm',
                    root / f'{name}.json',
                )
                command = [
                    sys.executable, str(generator), '--manifest', str(manifest),
                    '--output', str(output), '--data-output', str(data),
                    '--binary-dir', str(root / f'{name}-bin'), '--far-programs',
                    '--entry-only-room', '42', '--executable-local', '42:200',
                    '--append-last-executable-local', '42:202',
                    '--append-last-executable-local-object', '42:61',
                    '--append-last-global-script', '2', '--report', str(report),
                ]
                if include_ultimate:
                    command.extend((
                        '--append-ultimate-executable-local', '42:203',
                    ))
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    self.fail(result.stderr + result.stdout)
                return json.loads(report.read_text()), data.read_text()

            before, _ = generate('before')
            after, data = generate('after', include_ultimate=True)
            before_ids = {
                item['identity']: item['id'] for item in before['program_map']
            }
            after_ids = {
                item['identity']: item['id'] for item in after['program_map']
            }
            self.assertEqual(after['programs'], before['programs'] + 1)
            for identity, program_id in before_ids.items():
                self.assertEqual(after_ids[identity], program_id, identity)
            appended = after['program_map'][-1]
            self.assertEqual(appended['identity'], 'room.42/LSCR.203')
            self.assertEqual(appended['id'], max(before_ids.values()) + 1)
            self.assertIn(
                f'ScummV5_M23A_Program_{appended["id"]:02X}:', data,
            )

    def test_dynamic_residency_directory_exceeds_selector_pool_without_room_overflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'stop.bin').write_bytes(b'\x00')
            records = []
            for room in (1, 2, 3, 4):
                cooked = root / f'room-{room}.sc5c'
                cooked.write_bytes(_cooked_room(
                    room, _raw_room(tuple(range(200, 250))),
                ))
                records.append({'room': room, 'output': cooked.name})
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'schema': 'same_scumm_v5_cooked_rooms_v1',
                'num_global_scripts': 200,
                'records': records,
                'global_scripts': [{'number': 1, 'output': 'stop.bin', 'length': 1}],
            }))
            generator = Path(__file__).resolve().parents[1] / 'tools/generate_snes_cooked_rooms.py'
            output, data, report = root / 'rooms.pasm', root / 'data.pasm', root / 'report.json'
            result = subprocess.run([
                sys.executable, str(generator), '--manifest', str(manifest),
                '--output', str(output), '--data-output', str(data),
                '--binary-dir', str(root / 'segments'), '--far-programs',
                '--dynamic-program-residency', '--executable-local-room', '1',
                '--executable-local-room', '2', '--executable-local-room', '3',
                '--executable-local-room', '4', '--report', str(report),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            generated = json.loads(report.read_text())
            self.assertEqual(generated['program_id_namespace'], 'canonical_program_unit_id')
            self.assertEqual(generated['programs'], 209)
            self.assertEqual(len(generated['program_map']), 209)
            self.assertFalse(Path(generated['native_program_directory']).is_absolute())
            directory_path = Path(generated['native_program_directory'])
            if not directory_path.is_absolute():
                directory_path = report.parent / directory_path
            directory_bytes = directory_path.read_bytes()
            directory_doc = json.loads(directory_bytes)
            self.assertEqual(hashlib.sha256(directory_bytes).hexdigest(),
                             generated['native_program_directory_sha256'])
            self.assertEqual(len(directory_doc['entries']), 209)
            self.assertFalse(directory_doc['selector_values_emitted'])
            self.assertIn('ScummV5_M23A_ProgramPointers:', data.read_text())
            self.assertIn('ScummV5_M23A_ProgramLengths:', data.read_text())
            generated_output = output.read_text()
            self.assertIn('ScummV5_Resident_RoomBundleUnitIds:', generated_output)
            self.assertIn('ScummV5_M23A_RoomEntryProgramUnitIds:', generated_output)
            self.assertNotIn('ScummV5_M23A_RoomEntryPrograms:', generated_output)
            self.assertNotIn('ScummV5_M23A_RoomExitPrograms:', generated_output)
            self.assertNotIn('ScummV5_M23A_RoomLocalPrograms_0:', generated_output)
            generated_data = data.read_text()
            self.assertIn(
                'cmp #$00\n    bne ScummV5_M23A_GetProgramSize__resident\n'
                '    rep #$20\n    .a16\n    lda #$0000\n    sec\n    rtl',
                generated_data,
            )
