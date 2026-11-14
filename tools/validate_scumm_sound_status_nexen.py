#!/usr/bin/env python3
"""Copyright-free SCUMM sound-status control; run only under run_visual_once.py.

Requires actor_scene_fixture.source_files(sound_status_probe=True), the normal
streamed runtime and synthetic MAXS variables. Does not write guest state or
claim audio rendering. All observations use Nexen MCP in the owned session.
"""
import argparse,sys,json,hashlib,time,re,os
from pathlib import Path
R=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--nexen',type=Path,required=True)
parser.add_argument('--mcp-python-root',type=Path,required=True)
parser.add_argument('--core',type=Path,required=True)
parser.add_argument('--port',type=int,required=True)
parser.add_argument('--case', choices=('sound-status', 'cutscene-callback'), default='sound-status')
a=parser.parse_args()
if not re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', os.environ.get('DISPLAY', '')) or not Path(os.environ.get('XAUTHORITY', '/nonexistent')).is_file():
 raise RuntimeError('requires the canonical private-Xvfb supervisor; no display fallback')
sys.path[:0]=[str(R/'tools'),str(R/'src'),str(a.mcp_python_root)]
from mesen_mcp import session as ms
from validate_scumm_startup42_nexen import verified_symbol_map_for_rom
from fate_replay import advance_bounded
rom=a.rom.resolve();out=a.output_dir.resolve();out.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
_, symbols = verified_symbol_map_for_rom(rom)
listing=rom.with_suffix('.lst').read_text()
constant=lambda n:int(re.search(r'^; '+re.escape(n)+r'\s+= \$(\w+)\s+\(Constant\)',listing,re.M)[1],16)
variables=constant('SAME_SCUMM_VARIABLES')
def validate(path):
 for sibling,marker in [(Path(path).parent/'Nexen.dll',b'McpRunner'),(a.core,b'McpDrainEvents')]:assert marker in sibling.read_bytes()
ms.validate_mesen_build=validate
report={'hypothesis':'Original bytecode status queries read logical sound ownership and publish VAR_SOUNDRESULT through the existing interpreter','expected':[0,1,0,0,0x1357,1,0,0],'exit_condition':'sentinel, first SCUMM error, 512 frames or 90 seconds','kind':'COPYRIGHT_FREE_NATIVE_CONFORMANCE','guest_writes':0,'result':'NOT_VERIFIED','identities':{s:sha(rom.with_suffix(s)) for s in ('.sfc','.map','.msu','.build_identity.json')},'samples':[]}
if a.case == 'cutscene-callback':
 report.update(hypothesis='C19 callback enters ordinary C4 retirement with X8; both callback activations must complete with original locals and no BRK or cache writes', expected=[2,0x1234,0,0,0x1357,0,0,0], case=a.case)
def save():(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
save();begin=time.monotonic()
try:
 with ms.McpSession(rom=rom,mesen=a.nexen,cwd=rom.parent,port=a.port,boot_wait=2,socket_timeout=12,stderr_log=out/'nexen.stderr.log') as s:
  s.pause();s.tool('reset_emulator',{'power':True});s.pause()
  brk_hook=s.add_exec_hook(symbols['brk_handler'])
  alias_hook=s.add_write_hook(0x001000,0x001fff)
  report['invalid_execution_events']=[]
  for _ in range(64):
   advance_bounded(s,8)
   raw=s.read_memory('snesMemory',variables+300,16);values=[int.from_bytes(raw[i:i+2],'little') for i in range(0,16,2)]
   frame=s.get_state()['frameCount'];error=s.read_u8(0x7E2303)
   report['invalid_execution_events'].extend(x['params'] for x in s.drain_notifications(.01) if x.get('method')=='notifications/mesen/hookFired' and x.get('params',{}).get('handle') in (brk_hook,alias_hook))
   report['samples'].append({'frame':frame,'values':values,'error':error,'vm':s.read_memory('snesMemory',0x7E2300,8).hex()});save()
   if report['invalid_execution_events']:
    report['cpu']=s.get_cpu_state();save();raise RuntimeError('native BRK or executable WRAM alias write')
   if error:report['cpu']=s.get_cpu_state();save();raise RuntimeError('native SCUMM error')
   if values[4]==0x1357:
    assert values==report['expected'],values
    assert not report['invalid_execution_events'], 'native BRK or executable WRAM alias write'
    report['result']='NATIVE_CUTSCENE_CALLBACK_MATCH' if a.case == 'cutscene-callback' else 'NATIVE_SOUND_STATUS_QUERY_MATCH';save();break
   if time.monotonic()-begin>90:raise TimeoutError('native observation wall budget')
  else:raise TimeoutError('native observation frame budget')
except BaseException as exc:report['failure']=f'{type(exc).__name__}: {exc}';save();raise
finally:report['elapsed_seconds']=time.monotonic()-begin;save()
