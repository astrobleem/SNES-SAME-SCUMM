#!/usr/bin/env python3
"""Focused standalone room-49 scenario fixture for Open/Close crate."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEXEN = Path('/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen')
ROOM, RECORD, PHASE = 0x7FF2BF, 0x7FF2BE, 0x7FF2C2
POS, WALK, MOVING = 0x7FF1A0, 0x7FFDA5, 0x7FF220
C20, API_PENDING, API_VERB, API_OBJ1, API_OBJ2 = 0x7FD380, 0x7E7EC7, 0x7FD3A6, 0x7FD3A8, 0x7FD3AA
ERROR, STATES, SETCOUNT = 0x7E2303, 0x7E6000, 0x7E5FF7

def u16(b, o=0): return b[o] | b[o+1] << 8
def read(s, a, n=1): return s.read_memory('snesMemory', a, n)
def snap(s, frame):
    p = read(s, POS + 4, 4)
    record0 = list(read(s, C20 + 2, 6))
    statuses = list(read(s, 0x7E2380, 8))
    numbers = list(read(s, 0x7E2399, 8))
    trace_count = read(s, 0x7E5000)[0]
    trace = []
    for i in range(min(trace_count, 16)):
        b = read(s, 0x7E5010 + i * 8, 8)
        trace.append({'event': b[0], 'depth': b[1], 'slot': b[2],
                      'program': b[3], 'pc': u16(b, 4), 'status': b[6],
                      'active': b[7]})
    child_opcode_count = read(s, 0x7E53E0)[0]
    child_opcodes = []
    for i in range(min(child_opcode_count, 32)):
        b = read(s, 0x7E53E2 + i * 4, 4)
        child_opcodes.append({'opcode': b[0], 'pc': u16(b, 1)})
    return {'frame': frame, 'room': read(s, ROOM)[0], 'record': read(s, RECORD)[0],
            'vm_pc': u16(read(s, 0x7E2300, 2)),
            'last_opcode': read(s, 0x7E2306)[0],
            'phase': read(s, PHASE)[0], 'position': [u16(p), u16(p, 2)],
            'hold': read(s, 0x7FF2C4)[0],
            'c1_hold_after': u16(read(s, 0x7E2364, 2)),
            'fixture_ready': read(s, 0x7E5601)[0],
            'api_pending': read(s, API_PENDING)[0],
            'api_record': list(read(s, API_VERB, 6)),
            'error_site': read(s, 0x7FF466)[0],
            'walkbox': read(s, WALK + 1)[0], 'moving': read(s, MOVING + 1)[0],
            'sentence_count': read(s, C20)[0], 'error': read(s, ERROR)[0],
            'sentence_record0': record0,
            'sentence_records': list(read(s, C20 + 2, 36)),
            'selected_object': u16(read(s, 0x7E7F91, 2)),
            'selected_entry': read(s, 0x7E7F93)[0],
            'selected_program': read(s, 0x7E7F94)[0],
            'selected_entry_offset': u16(read(s, 0x7E7F95, 2)),
            'selected_slot': read(s, 0x7E7F9B)[0],
            'trace_count': read(s, 0x7E5000)[0],
            'trace': trace,
            'child_opcode_count': child_opcode_count,
            'child_opcodes': child_opcodes,
            'child_slot': read(s, 0x7E5607)[0],
            'child_program': read(s, 0x7E5608)[0],
            'child_pc': u16(read(s, 0x7E5609, 2)),
            'child_number': u16(read(s, 0x7E560B, 2)),
            'child_where': read(s, 0x7E560D)[0],
            'parent_slot': read(s, 0x7E560E)[0],
            'parent_program': read(s, 0x7E560F)[0],
            'parent_pc': u16(read(s, 0x7E5610, 2)),
            'nest_depth': read(s, 0x7E5612)[0],
            'first_fetch_program': read(s, 0x7E5613)[0],
            'first_fetch_pc': u16(read(s, 0x7E5614, 2)),
            'first_fetch_opcode': read(s, 0x7E5616)[0],
            'sentence_slot': read(s, 0x7E5617)[0],
            'sentence_program': read(s, 0x7E5618)[0],
            'sentence_pc': u16(read(s, 0x7E5619, 2)),
            'sentence_status': read(s, 0x7E561B)[0],
            'sentence_active': read(s, 0x7E561C)[0],
            'sentence_calls': read(s, 0x7E5602)[0],
            'sentence_returns': read(s, 0x7E5603)[0],
            'sentence_last_count': read(s, 0x7E5604)[0],
            'sentence_dequeues': read(s, 0x7E5605)[0],
            'sentence_allocs': read(s, 0x7E5606)[0],
            'sched_calls': read(s, 0x7E561D)[0],
            'sched_ready': read(s, 0x7E561E)[0],
            'sched_didexec': read(s, 0x7E561F)[0],
            'sched_freeze': read(s, 0x7E5620)[0],
            'sched_phase': read(s, 0x7E5621)[0],
            'sched_gate': read(s, 0x7E5622)[0],
            'c4_calls': read(s, 0x7E5623)[0],
            'stop_slot': read(s, 0x7E5624)[0],
            'stop_pc': u16(read(s, 0x7E5625, 2)),
            'stop_count': read(s, 0x7E5627)[0],
            'stop_status': read(s, 0x7E5628)[0],
            'save_status': read(s, 0x7E5629)[0],
            'sentence_fetch_count': read(s, 0x7E562A)[0],
            'sentence_fetch_pc': u16(read(s, 0x7E562B, 2)),
            'sentence_fetch_opcode': read(s, 0x7E562D)[0],
            'sentence_local0': u16(read(s, 0x7E562E, 2)),
            'sentence_local1': u16(read(s, 0x7E5630, 2)),
            'sentence_local2': u16(read(s, 0x7E5632, 2)),
            'slot1_local0': u16(read(s, 0x7E2448 + 64, 2)),
            'slot1_local1': u16(read(s, 0x7E2448 + 66, 2)),
            'slot1_local2': u16(read(s, 0x7E2448 + 68, 2)),
            'launch_tuple_saved': [u16(read(s, 0x7E5640, 2)), u16(read(s, 0x7E5642, 2)), u16(read(s, 0x7E5644, 2))],
            'launch_tuple_written': [u16(read(s, 0x7E5648, 2)), u16(read(s, 0x7E564A, 2)), u16(read(s, 0x7E564C, 2))],
            'sentence_record_offset': u16(read(s, 0x7E5636, 2)),
            'c20_scratch_verb': read(s, 0x7FD3A6)[0],
            'c20_scratch_object_a': u16(read(s, 0x7FD3A8, 2)),
            'c20_scratch_object_b': u16(read(s, 0x7FD3AA, 2)),
            'driver_reached': read(s, 0x7E5634)[0],
            'phase_branch': read(s, 0x7E5635)[0],
            'crate_state': read(s, STATES + 594)[0], 'setstate_exec': read(s, SETCOUNT)[0],
            'balloon_state': read(s, STATES + 593)[0],
            'balloon_owner': read(s, 0x7E8000 + 593)[0],
            'hose_owner': read(s, 0x7E8000 + 1014)[0],
            'last_owner_value': u16(read(s, 0x7E7EC5, 2)),
            'put_actor_exec': read(s, 0x7FFEE6)[0],
            'move_start_count': read(s, 0x7E7F18)[0],
            'move_start_pc': u16(read(s, 0x7E7F1A, 2)),
            'move_start_program': read(s, 0x7E7F1C)[0],
            'move_start_actor': read(s, 0x7E7F1D)[0],
            'start_object_exec': read(s, 0x7E7F9D)[0],
            'current_slot': read(s, 0x7E2A88)[0], 'active_count': read(s, 0x7E2A8A)[0],
            'slot1_pc': u16(read(s, 0x7E23E4 + 2, 2)),
            'slot2_pc': u16(read(s, 0x7E23E4 + 4, 2)),
            'slot3_pc': u16(read(s, 0x7E23E4 + 6, 2)),
            'slot1_program': read(s, 0x7E23B2 + 1)[0],
            'slot2_program': read(s, 0x7E23B2 + 2)[0],
            'slot3_program': read(s, 0x7E23B2 + 3)[0],
            'owner_591': read(s, 0x7E6000 + 591)[0],
            'owner_595': read(s, 0x7E6000 + 595)[0],
            'nested_postrun_pc': u16(read(s, 0x7E5638, 2)),
            'nested_postrun_slot': read(s, 0x7E563A)[0],
            'nested_postrun_status': read(s, 0x7E563B)[0],
            'nested_saved_pc': u16(read(s, 0x7E563C, 2)),
            'nested_saved_status': read(s, 0x7E563E)[0],
            'slot_statuses': statuses, 'slot_numbers': numbers,
            'sentence_script': u16(read(s, 0x7FF500 + 66, 2)),
            'program': read(s, 0x7E23B2 + 1)[0], 'pc': u16(read(s, 0x7E23E4 + 2, 2)),
            'c18_nested': read(s, 0x7FD335)[0],
            'c19_error_selector': read(s, 0x7E5684)[0],
            'c19_error_operand': u16(read(s, 0x7E5685, 2)),
            'c19_error_stack': read(s, 0x7E5687)[0],
            'c19_after_push': read(s, 0x7E5688)[0],
            'c16_record0': list(read(s, 0x7F5F10, 8)),
            'c16_record1': list(read(s, 0x7F5F18, 8)),
            'c16_eval_object': u16(read(s, 0x7E5470, 2)),
            'c16_eval_class': u16(read(s, 0x7E5472, 2)),
            'c16_eval_result': read(s, 0x7E5474)[0],
            'walk_obj_seen': read(s, 0x7E5689)[0],
            'walk_actor_seen': read(s, 0x7E568A)[0],
            'walk_object_seen': u16(read(s, 0x7E568B, 2)),
            'walk_lookup_ok': read(s, 0x7E568C)[0],
            'last_class_condition': read(s, 0x7E568E)[0],
            'last_class_object': u16(read(s, 0x7E568F, 2)),
            'last_class': u16(read(s, 0x7E5691, 2)),
            'walk_trace_seen': read(s, 0x7E5700)[0],
            'walk_trace_actor': read(s, 0x7E5701)[0],
            'walk_trace_object': u16(read(s, 0x7E5702, 2)),
            'walk_trace_ok': read(s, 0x7E5705)[0],
            'launch_tuple_verb': read(s, 0x7E5708)[0],
            'launch_tuple_object1': u16(read(s, 0x7E5709, 2)),
            'launch_tuple_object2': u16(read(s, 0x7E570B, 2)),
            'fetch_ring': [list(read(s, 0x7E5710 + i * 4, 4)) for i in range(32)],
            'fetch_locals': [u16(read(s, 0x7E5790 + i * 2, 2)) for i in range(3)],
            'queue_api': [read(s, 0x7E57A0)[0], u16(read(s, 0x7E57A1, 2)),
                          u16(read(s, 0x7E57A3, 2))],
            'fetch_locals_early': [list(read(s, 0x7E57C0 + i * 8, 6)) for i in range(6)],
            'class_ring_count': read(s, 0x7E57F0)[0],
            'class_ring': [list(read(s, 0x7E5800 + i * 8, 5)) for i in range(8)]}
def ready(x):
    return (x['room'] == 49 and x['record'] == 0 and x['phase'] == 0 and
            x['position'] == [399, 116] and x['walkbox'] == 11 and
            x['moving'] == 0 and x['sentence_count'] == 0 and x['error'] == 0)
def submit(s, verb, object_id=594, object2=0):
    s.write_memory('snesMemory', API_VERB, bytes((verb, 0)).hex())
    s.write_memory('snesMemory', API_OBJ1, object_id.to_bytes(2, 'little').hex())
    s.write_memory('snesMemory', API_OBJ2, object2.to_bytes(2, 'little').hex())
    s.write_memory('snesMemory', API_PENDING, '01')
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rom', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True); ap.add_argument('--port', type=int, default=45940)
    ap.add_argument('--object', type=int, default=594)
    ap.add_argument('--object2', type=int, default=0)
    ap.add_argument('--verbs', type=int, nargs='+', default=(3, 4))
    ap.add_argument('--nexen', type=Path, default=NEXEN); a = ap.parse_args()
    if not a.nexen.is_file() or not os.access(a.nexen, os.X_OK): raise RuntimeError('Nexen unavailable')
    sys.path.insert(0, '/home/chad/Mesen2/python'); import mesen_mcp.session as mcp
    mcp.validate_mesen_build = lambda _: None
    with mcp.McpSession(rom=a.rom.resolve(), mesen=a.nexen.resolve(), cwd=ROOT, port=a.port,
                        boot_wait=2.0, socket_timeout=120.0, stderr_log=a.output.with_suffix('.stderr.log')) as s:
        s.pause(); s.tool('reset_emulator', {'power': True}); s.pause(); timeline=[]; checkpoint=None
        stable_frames = 0
        for f in range(1, 240):
            r=s.run_frames(1)
            if r.get('timedOut') or not r.get('framesAdvanced'): raise RuntimeError(r)
            f = r.get('endFrame', f)
            x=snap(s,f); timeline.append(x)
            if ready(x):
                stable_frames += 1
                if stable_frames >= 3:
                    checkpoint=x; break
            else:
                stable_frames = 0
        if checkpoint is None:
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(json.dumps({'result':'not-ready','timeline':timeline}, indent=2)+'\n')
            raise RuntimeError(f'standalone fixture did not reach accepted checkpoint; last={timeline[-1]}')
        phases=[]
        for verb in a.verbs:
            submit(s,verb,a.object,a.object2); before=snap(s, checkpoint['frame'])
            phases.append({'verb': verb, 'submitted': before})
            result=None
            for f in range(checkpoint['frame']+1, checkpoint['frame']+241):
                r=s.run_frames(1)
                if r.get('timedOut') or not r.get('framesAdvanced'): raise RuntimeError(r)
                f = r.get('endFrame', f)
                x=snap(s,f); phases.append(x)
                # SCUMM_VM_STOPPED is the normal terminal state (4); only
                # the VM error marker is a failed slot.  A stopped parent and
                # child are expected after a completed object script.
                if 255 in x['slot_statuses']:
                    a.output.parent.mkdir(parents=True, exist_ok=True)
                    a.output.write_text(json.dumps({'result':'slot-error','checkpoint':checkpoint,
                                                    'phases':phases}, indent=2)+'\n')
                    raise RuntimeError(f'verb {verb} slot error: {x}')
                completed = (x['sentence_count'] == 0 and x['active_count'] == 0 and
                             x['error'] == 0 and
                             (x['setstate_exec'] > before['setstate_exec'] or
                              (a.object == 593 and x['balloon_owner'] == 15 and
                               x['hose_owner'] == 0) or
                              (a.object == 592 and x['sentence_count'] == 0)))
                if completed:
                    result=x; break
            if result is None:
                a.output.parent.mkdir(parents=True, exist_ok=True)
                a.output.write_text(json.dumps({'result':'incomplete','checkpoint':checkpoint,
                                                'phases':phases}, indent=2)+'\n')
                raise RuntimeError(f'verb {verb} did not complete; last={phases[-1]}')
            phases.append({'verb':verb,'before':before,'after':result})
            checkpoint=result
    out={'fixture':f'accepted room-49 checkpoint -> authentic object {a.object} sentence',
         'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(), 'checkpoint':checkpoint,
         'phases':phases, 'result':'pass'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps({'result':'pass','output':str(a.output)}))
if __name__ == '__main__': main()
