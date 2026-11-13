#!/usr/bin/env python3
"""Bounded copyright-free controller -> VAR_VERB_SCRIPT -> C4 native proof.

Run ONLY under run_visual_once.py (private Xvfb/process-tree supervisor).
This cold-boots input_callback_fixture, never restores or writes guest state.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--nexen', type=Path, required=True)
    parser.add_argument('--native-core', type=Path, required=True, help='actual NexenCore.so selected by the documented app-base/HomeFolder resolver')
    parser.add_argument('--mcp-python', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--nested-object-wait', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r':\d+', os.environ.get('DISPLAY', '')):
        parser.error('a supervised private Xvfb DISPLAY is required')
    sys.path.insert(0, str(args.mcp_python))
    from mesen_mcp import session as ms
    import fate_replay as replay
    from validate_scumm_startup42_nexen import verified_symbol_map_for_rom
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    # The shared Python client predates the Nexen rename. Check the actual
    # matched Nexen files instead of accepting a Mesen filename check/no-op.
    def validate_nexen(path):
        path = Path(path)
        if not path.is_file():
            raise ms.MesenBuildError('missing Nexen apphost')
        for sibling, marker in ((path.parent / 'Nexen.dll', b'McpRunner'), (args.native_core, b'McpDrainEvents')):
            if not sibling.is_file() or marker not in sibling.read_bytes():
                raise ms.MesenBuildError(f'incomplete Nexen MCP build: {sibling}')
    validate_nexen(args.nexen)
    ms.validate_mesen_build = validate_nexen
    verified_symbol_map_for_rom(args.rom)
    text = args.rom.with_suffix('.lst').read_text()
    if 'ScummV5_Input_Process__program' not in text:
        parser.error('input callback allocation was not compiled into this ROM')
    symbols = {n: int(v, 16) for n, v in re.findall(
        r'^; ([A-Z][A-Z0-9_]*)\s+= \$([0-9A-Fa-f]+)\s+\(Constant\)', text, re.M)}
    for name in ('SAME_SCUMM_VARIABLES', 'SAME_SCUMM_M23A_ACTIVE_ROOM',
                 'SAME_SCUMM_M23A_PHASE', 'SAME_SCUMM_ERROR',
                 'SAME_SCUMM_CONTROLLER_ROOM_READY', 'SAME_SCUMM_INPUT_ACCEPTED',
                 'SAME_SCUMM_INPUT_ALLOCATED', 'SAME_SCUMM_INPUT_PENDING',
                 'SAME_SCUMM_INPUT_SLOT', 'SAME_SCUMM_INPUT_SELECTOR',
                 'SAME_SCUMM_C4_SLOT_LOCALS', 'SAME_VIDEO_SURFACE_PENDING_VISUAL',
                 'SAME_SCUMM_CONTROLLER_DIAG', 'SAME_SCUMM_C7_USERPUT_STATE',
                 'SAME_SCUMM_TALK_ACTIVE', 'SAME_SCUMM_C19_STACK_POINTER'):
        if name not in symbols:
            parser.error(f'ROM-bound listing lacks {name}')
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(result='NOT_VERIFIED', hypothesis='One scene edge allocates an ordinary local callback; held input never repeats; next secondary edge resolves a global callback with a yielding nested child.',
                  expected='local args 2/0/1; global args 2/0/2; child argument42; exactly two allocations; error0',
                  exit_condition='completed two callbacks or first failure; 180 seconds; 6000 frames',
                  start_mode='cold copyright-free source fixture', guest_writes=0, samples=[], inputs=[],
                  identities={suffix: sha(args.rom.with_suffix(suffix)) for suffix in ('.sfc', '.map', '.msu', '.build_identity.json')},
                  nexen={str(p): sha(p) for p in (args.nexen, args.nexen.parent / 'Nexen.dll', args.native_core)})
    def save():
        temporary = args.output / 'report.pending.json'
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(args.output / 'report.json')
    started = time.monotonic()
    def sample(s):
        def byte(n): return s.read_u8(symbols[n])
        def word(n): return s.read_u16(symbols[n])
        base = symbols['SAME_SCUMM_VARIABLES']
        values = s.read_memory('snesMemory', base + 200, 28)
        sample = dict(frame=s.get_state()['frameCount'], room=byte('SAME_SCUMM_M23A_ACTIVE_ROOM'),
                      phase=byte('SAME_SCUMM_M23A_PHASE'), error=byte('SAME_SCUMM_ERROR'),
                      ready=byte('SAME_SCUMM_CONTROLLER_ROOM_READY'),
                      visual_pending=byte('SAME_VIDEO_SURFACE_PENDING_VISUAL'),
                      controller_diag=byte('SAME_SCUMM_CONTROLLER_DIAG'),
                      userput=word('SAME_SCUMM_C7_USERPUT_STATE'),
                      talk=byte('SAME_SCUMM_TALK_ACTIVE'), cutscene=byte('SAME_SCUMM_C19_STACK_POINTER'),
                      script=s.read_u16(base + 64),
                      accepted=word('SAME_SCUMM_INPUT_ACCEPTED'), allocated=word('SAME_SCUMM_INPUT_ALLOCATED'),
                      pending=byte('SAME_SCUMM_INPUT_PENDING'), slot=byte('SAME_SCUMM_INPUT_SLOT'),
                      selector=byte('SAME_SCUMM_INPUT_SELECTOR'),
                      values=[int.from_bytes(values[i:i+2], 'little') for i in range(0, 28, 2)])
        report['samples'].append(sample); save()
        if sample['room'] == 1 and sample['ready'] and sample['accepted'] > 2:
            raise RuntimeError(f'input counter initialization/single-edge violation: {sample}')
        if sample['error']: raise RuntimeError(f'SCUMM error: {sample}')
        if time.monotonic() - started > 180 or sample['frame'] > 6000:
            raise TimeoutError('specific diagnostic deadline reached')
        return sample
    def wait(s, predicate, frames=3200):
        start_frame=s.get_state()["frameCount"]
        for _ in range(frames//4):
            q = sample(s)
            if predicate(q): return q
            replay.advance_bounded(s, 4)
        raise TimeoutError('bounded condition not observed')
    with socket.socket() as probe: probe.bind(('127.0.0.1', args.port))
    save()
    try:
        with ms.McpSession(rom=args.rom, mesen=args.nexen, cwd=args.rom.parent,
                           port=args.port, boot_wait=2, socket_timeout=12,
                           stderr_log=args.output / 'nexen.stderr.log') as s:
            s.pause()
            wait(s, lambda q: q['room'] == 1 and q['ready'] and q['script'] == 204
                 and not q['visual_pending'] and not q['talk'] and not q['cutscene']
                 and q['userput'] == 1 and q['controller_diag'] >= 6)
            for button, index in ((s.BTN_A, 1), (s.BTN_B, 2)):
                report['inputs'].append({'button': button, 'before': sample(s)})
                s.set_input(button, 120)
                q = wait(s, lambda q: q['allocated'] == index and q['values'][3 if index == 1 else 8] == 1, frames=256)
                report[f'activation{index}'] = q
                # A held button must not create a second activation while the
                # original script or its checked resource is waiting.
                replay.advance_bounded(s, 32)
                q = sample(s)
                assert q['allocated'] == index and q['accepted'] == index, q
                slot = q['slot']
                report[f'activation{index}_locals'] = s.read_memory(
                    'snesMemory', symbols['SAME_SCUMM_C4_SLOT_LOCALS'] + slot * 64, 64).hex()
                s.set_input(0, 1); replay.advance_bounded(s, 8)
            q = sample(s)
            assert q['values'] == [2, 0, 1, 1, 2, 0, 2, 1, 1, 42, 1, 77, 1, 1], q
            if args.nested_object_wait:
                base=symbols['SAME_SCUMM_VARIABLES']
                wait(s, lambda q: s.read_u16(base+230)==42 and s.read_u16(base+236)==1 and s.read_u16(base+234)==1, frames=512)
                report['nested_object_values']=[s.read_u16(base+2*i) for i in (114,115,116)]
                assert report['nested_object_values']==[42,42,1], report
                report['nested_freeze_resume']=s.read_u16(base+236)
                report['ancestor_replacement_count']=s.read_u16(base+234)
                replay.advance_bounded(s,64)
                assert s.read_u16(base+234)==1 and sample(s)['error']==0
            report['result'] = 'PASS'
            save()
    except BaseException as exc:
        report['failure'] = f'{type(exc).__name__}: {exc}'; save(); raise
    finally:
        report['elapsed_seconds'] = time.monotonic() - started; save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
