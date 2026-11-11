#!/usr/bin/env python3
"""Bounded source-font diagnostic; synthetic text is not gameplay acceptance.

Run ONLY under the installed canonical private-Xvfb run_visual_once.py supervisor.
The caller supplies an existing identity-bound diagnostic build and external
archive. No package/ROM modification, guest writes, or controller submission.
"""
from pathlib import Path
import sys,os,json,time,argparse,base64,socket,re,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
if os.environ.get('SAME_MCP_PYTHON'): sys.path.insert(0,os.environ['SAME_MCP_PYTHON'])
from validate_scumm_actor_visual_probe_nexen import validate_build, DEFAULT_NEXEN, capture_surface, ProbeObserver
from same.engines.scumm_v5.video import ScummV5Charset
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.policy import parse_game_policy
from same.profile import load_profile
from same.resources import MemoryResourceProvider

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def u16(b,n=0):return int.from_bytes(b[n:n+2],'little')
def text_is_presented(raw, state):
 # Only this producer's completed visible text is relevant. Requiring the
 # whole scene to remain idle misses short-lived messages during animation;
 # accepting any completed generation can accidentally accept a later hide.
 return (state['room']==4 and u16(raw,4)>0 and u16(raw,4)==u16(raw,2)
         and u16(raw)==0 and u16(raw,0x68)==1 and state['actor_render_valid'])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--profile',type=Path,required=True);ap.add_argument('--port',type=int,default=7398);ap.add_argument('--nexen',type=Path,default=DEFAULT_NEXEN);a=ap.parse_args()
 b=a.build;stem=b/'fate-authentic-room';storage=b/'whole-source/msu-program-storage'
 args=argparse.Namespace(rom=stem.with_suffix('.sfc'),package=stem.with_suffix('.msu'),map=stem.with_suffix('.map'),listing=stem.with_suffix('.lst'),identity=stem.with_suffix('.build_identity.json'),directory=b/'whole-source/scumm_v5_native_program_directory.json',storage=storage/'program-storage.json',audit=storage/'actor-probe-audit.json',poppy_inputs=stem.with_suffix('.poppy-inputs.json'),build_source=a.source)
 identity,audit,records,backdrop=validate_build(args)
 assert audit['program']['config']['font_sample'] is True
 assert records['visual']['projection']['reserved_bottom']==32
 assert re.fullmatch(r':[0-9]+(?:\.[0-9]+)?',os.environ.get('DISPLAY',''))
 assert Path(os.environ['XAUTHORITY']).is_file()
 a.output.mkdir(parents=True,exist_ok=False)
 report=dict(kind='SYNTHETIC_SOURCE_FONT_DIAGNOSTIC',gameplay_authentic=False,result='NOT_VERIFIED',hypothesis='SC5FNT v2 packed glyphs render with source bearings and opaque black through INDEX8 and the normal Mode-3 commit',expected='SAME text 24, source charset2, matching source/INDEX8/VRAM/CGRAM and screenshot',exit_condition='first settled text image or 240 seconds / 6000 logical frames',rom_sha256=sha(args.rom),map_sha256=sha(args.map),package_sha256=sha(args.package),build_identity_sha256=sha(args.identity),audit_sha256=sha(args.audit),samples=[])
 def save():(a.output/'font-native.json').write_text(json.dumps(report,indent=2)+'\n')
 with zipfile.ZipFile(a.archive) as z:
  raw={k:z.read(next(n for n in z.namelist() if n.upper().endswith(ext))) for k,ext in [('game.index','.000'),('game.data','.001')]}
 provider=LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw),parse_game_policy(load_profile(a.profile,verify_resources=False)))
 source=provider.read('charset.2');font=ScummV5Charset(source,key='charset.2',allow_multibit=True);report['source_font_sha256']=hashlib.sha256(source).hexdigest()
 expected=bytearray(256*32);mask=bytearray(len(expected));pen=2
 for char in b'SAME text 24':
  glyph=font.glyph(char);assert glyph is not None
  for y in range(glyph.height):
   for x in range(glyph.width):
    slot=glyph.pixels[y*glyph.width+x];dx=pen+glyph.x_offset+x;dy=glyph.y_offset+y
    if slot and 0<=dx<256 and 0<=dy<32:
     at=dy*256+dx;expected[at]=15 if slot==1 else source[5+slot];mask[at]=1
  pen+=glyph.width+glyph.x_offset
 (a.output/'expected-text.indexed.bin').write_bytes(expected);(a.output/'expected-text.opacity.bin').write_bytes(mask)
 with socket.socket() as sock:sock.bind(('127.0.0.1',a.port))
 from mesen_mcp import session as ms
 ms.validate_mesen_build=lambda path:None
 started=time.monotonic();save()
 try:
  with ms.McpSession(rom=args.rom,mesen=a.nexen,cwd=b,port=a.port,boot_wait=2,socket_timeout=15,stderr_log=a.output/'nexen.stderr.log') as session:
   session.pause()
   report['cold_process_state']=session.get_state();report['cold_process_ppu']=session.get_ppu_state();save()
   observer=ProbeObserver(session,a.output,backdrop,deadline=started+240,projection=records['visual']['projection'],evidence_kind=report['kind'])
   try:
    while observer.logical_frames<6000:
     state=observer.advance(10);raw=session.read_memory('snesMemory',0x400780,128)
     sample=dict(emulator_frame=session.get_state()['frameCount'],ppu_frame=session.get_ppu_state()['frameCount'],frame=observer.logical_frames,room=state['room'],error=state['error'],stage=state['stage'],text=raw.hex(),text_status=session.read_u8(0x7E7AC7),c23=session.read_memory('snesMemory',0x7FD408,81).hex(),talk=session.read_memory('snesMemory',0x7E7A20,0xB0).hex(),mode3=state['mode3_state'],committed=state['backend_committed_generation'],actor_valid=state['actor_render_valid'])
     report['samples'].append(sample);save()
     if state['error']:raise RuntimeError('SCUMM error: '+str(sample))
     if state['stage']==1 and sample['text_status']==2:raise RuntimeError('explicit text rejection: '+str(sample))
     if text_is_presented(raw,state):
      # No guest writes/ACKs. Observe one complete scanout after the
      # published fence, then recheck the same immutable text generation.
      prior_generation=u16(raw,4);observer.advance(2)
      after=session.read_memory('snesMemory',0x400780,128)
      assert u16(after,4)==prior_generation and after[0:2]==b'\x00\x00'
      report['scanout_state']=session.get_ppu_state();save()
      cap=capture_surface(session,a.output,'font',backdrop,projection=records['visual']['projection'])
      actual=(a.output/'font.indexed.bin').read_bytes()[192*256:]
      report['capture']=cap;report['indexed_differences']=sum(x!=y for x,y in zip(actual,expected));report['state']=state;report['text_state_hex']=raw.hex();save()
      assert report['indexed_differences']==0,'source/indexed text mismatch'
      from same.snes_surface import SnesIndexedSurfaceBundle,decode_bundle_indexed
      v=(a.output/'font.vram.bin').read_bytes();c=(a.output/'font.cgram.bin').read_bytes();ppu=decode_bundle_indexed(SnesIndexedSurfaceBundle(v[:0xE000],v[0xE000:0xE800],c))
      report['ppu_differences']=sum(x!=y for x,y in zip(ppu[192*256:],expected));assert report['ppu_differences']==0
      from PIL import Image
      image=Image.open(a.output/'font.ppu.png').convert('RGB');assert image.size in ((256,224),(256,239)),image.size
      report['screenshot_size']=list(image.size)
      colors=[]
      for i in range(256):
       col=u16(c,2*i);colors.append(tuple(((col>>shift)&31)*255//31 for shift in (0,5,10)))
      # Record RGB comparison separately; emulator color expansion can differ
      # by one rounding level. Indexed VRAM remains the exact palette-slot proof.
      diffs=[max(abs(a-b) for a,b in zip(image.getpixel((n%256,192+n//256)),colors[index])) for n,index in enumerate(expected)]
      report['screenshot_max_channel_delta']=max(diffs);assert max(diffs)<=1,'actual screenshot differs from committed text'
      report['result']='PASS_SOURCE_FONT_NATIVE';save();break
    else:raise TimeoutError('6000 logical frame bound reached')
   except BaseException as exc:
    report['failure']=f'{type(exc).__name__}: {exc}'
    try:report['failure_capture']=capture_surface(session,a.output,'first-failure',backdrop,projection=records['visual']['projection'])
    except BaseException as e:report['failure_capture_error']=str(e)
    save();raise
 finally:
  report['elapsed_seconds']=time.monotonic()-started;save()
if __name__=='__main__':main()
