#!/usr/bin/env python3
"""Fresh-emulator Phase 6H-B dense-global/authentic Var[120] gate."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEXEN = Path("/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen")
VARS=0x7E0800; STATUS=0x7E2380; NUMBER=0x7E2399; PROGRAM=0x7E23B2; PC=0x7E23E4

def u16(b, o=0): return int.from_bytes(b[o:o+2], "little")
def req(v, m):
    if not v: raise RuntimeError(m)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--rom",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True); ap.add_argument("--frames",type=int,default=1400)
    ap.add_argument("--port",type=int,default=44331); ap.add_argument("--sa1",action="store_true")
    ap.add_argument("--nexen",type=Path,default=NEXEN); a=ap.parse_args()
    sys.path.insert(0,"/home/chad/Mesen2/python"); import mesen_mcp.session as ms
    ms.validate_mesen_build=lambda _:None; a.output.mkdir(parents=True,exist_ok=True)
    with ms.McpSession(rom=a.rom.resolve(),mesen=a.nexen.resolve(),cwd=ROOT,port=a.port,
                       boot_wait=2.0,socket_timeout=120.0,stderr_log=a.output/"nexen-stderr.log") as s:
        s.pause(); s.tool("reset_emulator",{"power":True}); s.pause()
        sa0=s.get_cpu_state("Sa1") if a.sa1 else None
        run=s.run_frames(a.frames); req(run["framesAdvanced"]==a.frames and not run["timedOut"],"timeout")
        values=s.read_memory("snesMemory",VARS,1600)
        statuses=s.read_memory("snesMemory",STATUS,25); nums=s.read_memory("snesMemory",NUMBER,25)
        progs=s.read_memory("snesMemory",PROGRAM,25); pcs=s.read_memory("snesMemory",PC,50)
        core=s.read_memory("snesMemory",0x7E2300,8); old=s.read_memory("snesMemory",0x7E2320,32)
        provisional=s.read_memory("snesMemory",0x7FF500+240,2)
        sp=s.get_cpu_state("Snes") ["sp"]; sa1=s.get_cpu_state("Sa1") if a.sa1 else None
    v119,v120,v121=(u16(values,n*2) for n in (119,120,121))
    parent=next((i for i in range(25) if nums[i]==2 and progs[i]==0xEC),None)
    child=next((i for i in range(25) if progs[i]==0xED),None)
    stable=("pc","k","a","x","y","sp","d","dbr","ps","emulationMode")
    unchanged=True if not a.sa1 else all(sa0[k]==sa1[k] for k in stable); req(unchanged,"SA-1 changed")
    ev={"format":"same-phase6hb-dense-global-evidence","rom_sha256":hashlib.sha256(a.rom.read_bytes()).hexdigest(),
        "globals":{"count":800,"base":"7E0800","end":"7E0E40","var1":u16(values,2),"var33":u16(values,66),"var119":v119,"var120":v120,"var121":v121},
        "parent":None if parent is None else {"slot":parent,"status":statuses[parent],"pc":u16(pcs,parent*2)},
        "child":None if child is None else {"slot":child,"status":statuses[child],"pc":u16(pcs,child*2)},
        "vm":{"pc":u16(core),"status":core[2],"error":core[3],"opcode":core[6]},"stack_pointer":sp,"sa1_unchanged":unchanged}
    ev["provisional_var120"] = u16(provisional)
    print(json.dumps(ev,sort_keys=True), flush=True)
    req(v120==0xFFFF,"Var[120] was not written"); req(v119==0 and v121==0,"adjacent global changed")
    req(old==bytes(32),"historical bootstrap window was used")
    (a.output/"evidence.json").write_text(json.dumps(ev,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
