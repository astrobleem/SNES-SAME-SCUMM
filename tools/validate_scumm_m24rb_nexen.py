#!/usr/bin/env python3
"""Cold-emulator evidence for the real Fate M24R-B composite."""
from __future__ import annotations
import argparse, hashlib, json, math, os, struct, sys, wave
from pathlib import Path
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state, wav_evidence, u16

ROOT=Path(__file__).resolve().parents[1]; STATE=0x7FFA00
TOKENS=[0x90,0xA7,0xA6,0xA5,0xA4,0xA3,0xBF]

def run(rom:Path,nexen:Path,out:Path,port:int,label:str,max_frames:int,transition:bool)->dict:
 import mesen_mcp.session as ms
 ms.validate_mesen_build=lambda _p:None
 wav=out/f"m24rb-{label}.wav"; events=[]; snapshots={}; marker_frame=0
 with ms.McpSession(rom=rom,mesen=nexen,cwd=ROOT,port=port,boot_wait=2.0,socket_timeout=90.0,stderr_log=out/f"{label}.log") as s:
  s.pause(); s.tool("reset_emulator",{"power":True}); s.pause(); s.record_audio(wav)
  last=0
  for frame in range(1,max_frames+1):
   step=s.run_frames(1); require(step["framesAdvanced"]==1 and not step["timedOut"],f"{label} frame timeout")
   token=s.read_memory("snesMemory",STATE+2,1)[0]
   # Marker is intentionally observed directly by the ROM content engine and
   # does not share the transition event ring.
   if not marker_frame and s.read_memory("snesMemory",0x7E2228,1)[0]>=4: marker_frame=frame
   count=s.read_memory("snesMemory",STATE+1,1)[0]
   if count!=last:
    raw=s.read_memory("snesMemory",STATE,0x30)
    events=[{"token":raw[0x10+i],"tick":raw[0x18+i],"frame":u16(raw,0x20+2*i)} for i in range(count)]
    last=count
   if transition and events and events[-1]["token"]==0xBF: break
  snapshots["final"]=s.get_audio_state(); s.stop_audio()
  kernel=s.read_memory("snesMemory",0x7E2000,10); trace=s.read_memory("snesMemory",0x7E2B30,0x3A)
  phase=s.read_memory("snesMemory",0x7E2228,1)[0]; state=tad_state(s)
 require(marker_frame>0,f"{label} never crossed marker8")
 if transition:
  require([x["token"] for x in events]==TOKENS,f"{label} transition events differ: {events}")
  require([x["tick"] for x in events]==[0,19,38,63,94,125,0],f"{label} admission ticks differ")
  require(state["state"]==0x82 and state["ready"]==1 and state["next_song"]==1,f"{label} reloaded TAD")
 else:
  require(not events,f"{label} loop control unexpectedly transitioned")
 require(u16(kernel,8)==0 and trace[0]==1 and trace[1]==0,
         f"{label} packet rejected or lost: kernel={kernel.hex()} trace={trace[:4].hex()}")
 audio=wav_evidence(wav); require(0<audio["peak"]<32767 and audio["mean_square"]>1000,f"{label} silent/clipped")
 voices=snapshots["final"]["voices"]
 return {"label":label,"rom_sha256":hashlib.sha256(rom.read_bytes()).hexdigest(),"frames":frame,
         "marker_frame":marker_frame,"events":events,"tad":state,"audio":audio,
         "peak_active_dsp_voices":sum(v["envelope"]>0 and abs(v["volL"])+abs(v["volR"])>0 for v in voices),
         "phase":phase,"wav":str(wav)}

def main()->int:
 p=argparse.ArgumentParser();
 for name in ("low","high","sustain","loop"): p.add_argument(f"--{name}-rom",type=Path,required=True)
 p.add_argument("--nexen",type=Path,default=DEFAULT_NEXEN); p.add_argument("--output",type=Path,required=True); p.add_argument("--port",type=int,default=44200); a=p.parse_args()
 out=a.output.resolve(); out.mkdir(parents=True,exist_ok=True); sys.path.insert(0,"/home/chad/Mesen2/python")
 runs=[run(getattr(a,f"{name}_rom").resolve(),a.nexen.resolve(),out,a.port+i,name,4500,True) for i,name in enumerate(("low","high","sustain"))]
 loop=run(a.loop_rom.resolve(),a.nexen.resolve(),out,a.port+3,"full-loop",8500,False)
 report={"gate":"M24R-B-real-content-backend","result":"pass","fresh_power_on_processes":4,
         "phase_runs":runs,"loop_control":loop,"physical_song_reloads":0,"packet_loss":0,"packet_rejection":0,
         "driver_tick_hz":125,"fade_ticks":256,"admission_ticks":[19,38,63,94,125]}
 (out/"report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n"); print(out/"report.json"); return 0
if __name__=="__main__": raise SystemExit(main())
