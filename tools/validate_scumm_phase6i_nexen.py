#!/usr/bin/env python3
"""Fresh-emulator authentic global-script-83 execution gate."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NEXEN=Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
def u16(b,o=0): return int.from_bytes(b[o:o+2],"little")
def req(v,m):
    if not v: raise RuntimeError(m)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--rom",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    p.add_argument("--manifest",type=Path,default=ROOT/"build/m23a-rooms/authentic/manifest.json")
    p.add_argument("--nexen",type=Path,default=NEXEN); p.add_argument("--port",type=int,default=44351)
    p.add_argument("--frames",type=int,default=1300); p.add_argument("--sa1",action="store_true"); a=p.parse_args()
    manifest=json.loads(a.manifest.read_text()); script=next(x for x in manifest["global_scripts"] if x["number"]==83)
    req(script["length"]==45 and script["sha256"]=="598a8bed2a2870fba2dfe1622572608f2877fb1a9e1c172f2dd0ecd3f6f2e538","script 83 identity")
    sys.path.insert(0,"/home/chad/Mesen2/python"); import mesen_mcp.session as ms; ms.validate_mesen_build=lambda _:None
    a.output.mkdir(parents=True,exist_ok=True)
    with ms.McpSession(rom=a.rom.resolve(),mesen=a.nexen.resolve(),cwd=ROOT,port=a.port,boot_wait=2,socket_timeout=120,stderr_log=a.output/"nexen-stderr.log") as s:
        s.pause(); s.tool("reset_emulator",{"power":True}); s.pause(); sa0=s.get_cpu_state("Sa1") if a.sa1 else None
        run=s.run_frames(a.frames); req(run["framesAdvanced"]==a.frames and not run["timedOut"],"timeout")
        core=s.read_memory("snesMemory",0x7E2300,8); status=s.read_memory("snesMemory",0x7E2380,25)
        number=s.read_memory("snesMemory",0x7E2399,25); program=s.read_memory("snesMemory",0x7E23B2,25)
        did=s.read_memory("snesMemory",0x7E23CB,25); pcs=s.read_memory("snesMemory",0x7E23E4,50)
        where=s.read_memory("snesMemory",0x7E7F46,25); locals_=s.read_memory("snesMemory",0x7E2448,25*64)
        variables=s.read_memory("snesMemory",0x7E0800,1600); depth=s.read_memory("snesMemory",0x7FF465,1)[0]
        trace_count=s.read_memory("snesMemory",0x7E7ED7,1)[0]; trace=s.read_memory("snesMemory",0x7E7ED8,64)
        sa1=s.get_cpu_state("Sa1") if a.sa1 else None
    child=next((i for i,x in enumerate(program) if x==0xEE),None); req(child is not None,"script 83 slot evidence missing")
    starts=[tuple(trace[i*4:i*4+4]) for i in range(min(trace_count,16))]
    start83=next((x for x in starts if x[0]==83),None)
    req(where[child]==2 and status[child]==4,"script 83 did not terminate as a global")
    req(locals_[child*64:child*64+64]==bytes(64),"script 83 locals not zero"); req(u16(variables,240)==0xFFFF,"Var[120] regressed")
    req(core[3]==3 and core[6]==0x9E and u16(core)==0x02A1,"next blocker differs")
    stable=("pc","k","a","x","y","sp","d","dbr","ps","emulationMode")
    unchanged=True if not a.sa1 else all(sa0[k]==sa1[k] for k in stable); req(unchanged,"SA-1 changed")
    ev={"format":"same-phase6i-script83-evidence","rom_sha256":hashlib.sha256(a.rom.read_bytes()).hexdigest(),"script83":{**script,"program":238,"slot":child,"allocation_trace":start83,"start_trace_records":starts,"retired_pc":u16(pcs,child*2),"status":status[child],"locals_zero":True,"didexec":did[child]},"nested_depth":depth,"var119":u16(variables,238),"var120":u16(variables,240),"var121":u16(variables,242),"next_blocker":{"script":"room.49/LSCR.211","opcode_pc":0x02A0,"continuation_pc":0x02A1,"opcode":core[6],"error":core[3]},"sa1_unchanged":unchanged}
    (a.output/"evidence.json").write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n"); print(json.dumps(ev,sort_keys=True))
if __name__=="__main__": main()
