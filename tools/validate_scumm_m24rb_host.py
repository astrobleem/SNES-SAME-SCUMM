#!/usr/bin/env python3
"""Validate authentic LSCR 208 ordering and M24R-B logical ownership."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

from validate_scumm_m23c_host import make_host, require, STATE

ROOT=Path(__file__).resolve().parents[1]

def run(archive:Path, manifests:list[Path])->dict[str,object]:
    host,_=make_host(archive,manifests); engine=host.engine
    host.context.profile.options["imuse_frame_end_processing"] = True
    fixture=json.loads(STATE.read_text())
    engine.state.scripts[0].active=False
    for bit in fixture["bits_set"]: engine.state.bit_variables[int(bit)]=True
    for key,spec in fixture["strings"].items(): engine.state.strings[int(key)]=bytearray([int(spec["fill"])]*int(spec["length"]))
    engine.state.object_classes[595]=set(fixture["object_classes"]["595"])
    engine._load_room(host.context,49,required=True)
    engine._in_tick=True; engine._tick_operations=0; engine._tick_max_ops=20000
    trace=[]; original=engine._step
    def step(slot,context):
        pc=slot.pc; before=[list(x) for x in engine.state.sound_queue]
        original(slot,context)
        trace.append({"script":slot.resource_key,"pc":pc,"opcode":slot.program[pc],
                      "next":slot.pc,"queue_before":before,
                      "queue_after":[list(x) for x in engine.state.sound_queue],
                      "source":None if slot.source is None else slot.source.runtime_map(pc)})
    try:
        room=next(x for x in engine.state.scripts if x.active and x.script_kind=="ENCD")
        while room.active and room.pc<0x006a: step(room,host.context)
        require(engine._audio.music_id==80 and engine._audio.music_route==("hook",14),"room49 hook14 ownership missing")
        local=engine._allocate_script_slot(host.context,208,[],freeze_resistant=False,recursive=False)
        require(local.pc==0 and local.script_kind=="LSCR","LSCR 208 did not enter scheduler at PC zero")
        while local.active and local.pc<0x0086: step(local,host.context)
        # Authentic frame-end queue service; no synthetic -1 byte is inserted.
        require(engine.state.sound_queue,"LSCR 208 produced no queued commands")
        engine._flush_sound_commands(host.context)
    finally:
        engine._in_tick=False; engine._step=original
    lscr=[x for x in trace if x["script"].endswith("LSCR.208")]
    expected=[
        [0x010c,80,0,7],[0x010e,80,7],[0x010f,0x010d,80,0,600],
        [0x010f,-1],[0x010e,80,8],[0x010f,0x0101,80,0],
        [0x010f,0x0106,80,0],[0x010f,0x010d,80,0,60],
        [0x010f,8,82],[0x010f,-1],
    ]
    history=engine.state.sound_history
    require(all(item in history for item in expected),"LSCR 208 canonical command sequence differs")
    audio=engine._audio
    require(audio.is_running(82) and audio.inspect()["logical_compiled"]["82"]["state"]=="deferred",
            "sound82 was not logically owned while deferred")
    require(audio.notify_compiled_marker(80,8,audio._compiled_generation)==4,
            "marker8 did not consume its four deferred commands exactly once")
    require(audio.is_running(82) and audio.inspect()["logical_compiled"]["82"]["state"]=="active",
            "sound82 did not become active at marker8")
    require(audio.notify_compiled_marker(80,8,audio._compiled_generation)==0,"marker8 was not one-shot")
    audio.fade_sound(82,0,120); audio.play_sfx(80)
    overlap=(audio.is_running(80),audio.is_running(82))
    for _ in range(120): audio.tick()
    require(overlap==(True,True) and audio.is_running(80) and not audio.is_running(82),
            "independent overlap/fade completion status differs")
    return {"result":"pass","lscr208_sha256":hashlib.sha256(local.program).hexdigest(),
            "trace":lscr,"sound_history":history,"audio":audio.inspect(),
            "marker_consumed_once":True,"overlap_status":list(overlap)}

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--archive",type=Path,default=Path("/home/chad/fatedemo-box.zip")); p.add_argument("--manifest",type=Path,action="append",required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    report={"gate":"M24R-B-host-authentic-LSCR208","result":"pass","run":run(a.archive,a.manifest)}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n"); print(a.output); return 0
if __name__=="__main__": raise SystemExit(main())
