#!/usr/bin/env python3
"""Source-driven checked camera lookahead native control (original fixture only).

Launch through the canonical private-Xvfb supervisor; never directly on a user
DISPLAY. Variable 70 belongs to the verified synthetic program, not gameplay.
"""
import argparse,sys,json,time,hashlib,base64,io
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'tools'),str(R/'src'),'/home/chad/Mesen2/python']
from mesen_mcp import session as m
from validate_scumm_startup42_nexen import verified_symbol_map_for_rom
from same.snes_video_backend import linearize_retained_index8,retained_map_offset
from same.snes_surface import decode_snes_8bpp_tile,decode_cgram
from same.engines.scumm_v5.room_visual import decode_room_visual,camera_viewport
from PIL import Image,ImageChops
from validate_scumm_actor_visual_probe_nexen import read_committed_pose,snapshot_locked_generation,queued_generation_is_presented,capture_presented_generation
from same.engines.scumm_v5.cursor import MASKS
class Reads:
 def __init__(self,s):self.s=s;self.pages={};self.state=s.get_state();assert self.state['isPaused']
 def __getattr__(self,k):return getattr(self.s,k)
 def get_state(self):return self.state
 def read_memory(self,m,a,n):
  if m!='snesMemory' or not (0x7E0000<=a and a+n<=0x800000 or 0x400000<=a and a+n<=0x420000):return self.s.read_memory(m,a,n)
  data=bytearray()
  while n:
   page=a&~4095
   if page not in self.pages:self.pages[page]=self.s.read_memory(m,page,4096)
   o=a-page;k=min(n,4096-o);data.extend(self.pages[page][o:o+k]);a+=k;n-=k
  return bytes(data)
 def read_u8(self,a):return self.read_memory('snesMemory',a,1)[0]
 def read_u16(self,a):return int.from_bytes(self.read_memory('snesMemory',a,2),'little')
m.validate_mesen_build=lambda _:None
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--rom',type=Path,required=True)
ap.add_argument('--directory',type=Path,required=True)
ap.add_argument('--storage-manifest',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--port',type=int,required=True)
ap.add_argument('--seconds',type=int,default=240)
args=ap.parse_args()
if not 1<=args.seconds<=580:ap.error('seconds must fit supervised 600-second ceiling')
rom=args.rom.resolve();out=args.output;out.mkdir(parents=True,exist_ok=False)
verified_symbol_map_for_rom(rom)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
w=lambda b,o=0:int.from_bytes(b[o:o+2],'little')
directory=json.loads(args.directory.read_text())
boot=bytes([0x72,1,0x1a,70,0,160,0,0x92,70,0,0x80,0x18,0xf9,0xff])
assert len(directory['entries'])==3, 'not the original camera fixture'
assert [(e['identity'],e['sha256']) for e in directory['entries'] if e['kind']=='GLOBAL']==[('GlobalProgram(1)',hashlib.sha256(boot).hexdigest())], 'refuse diagnostic writes in another program'
storage=json.loads(args.storage_manifest.read_text());package=rom.with_suffix('.msu').read_bytes()
assert hashlib.sha256(package).hexdigest()==storage['package_sha256']
record=next(v for v in storage['visual_records'] if v['room']==1)
visual_bytes=package[record['package_offset']:record['package_offset']+record['length']]
assert hashlib.sha256(visual_bytes).hexdigest()==record['sha256']
visual=decode_room_visual(visual_bytes,expected_room=1)
assert (visual.width,visual.height)==(640,144)
assert visual.pixels==bytes(((x*13+y*37)^(x>>8))&255 for y in range(144) for x in range(640))
assert record['projection']['reserved_bottom']==0
r={'hypothesis':'checked strip lookahead overlaps publication without changing source pixels',
   'expected':'synthetic forward/reverse, accepted lookahead hits, full source/INDEX8/PPU match',
   'exit':'first failed boundary or both directions; bounded process supervisor required',
   'native':True,'gameplay':False,'identities':{ext:sha(rom.with_suffix(ext)) for ext in ('.sfc','.map','.msu','.build_identity.json')},
   'samples':[],'captures':[],'result':'NOT_VERIFIED'}
start=time.monotonic()
def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
with m.McpSession(rom=rom,mesen=Path('/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen'),cwd=rom.parent,port=args.port,boot_wait=2,socket_timeout=12,stderr_log=out/'nexen.stderr.log') as s:
 try:
  def rd(a,n):return s.read_memory('snesMemory',a,n)
  def sample():
   z={'frame':s.get_state()['frameCount'],'room':rd(0x7ff2bf,1)[0],'error':rd(0x7e2303,1)[0],'retained':rd(0x401084,64).hex(),'viewport':rd(0x7e8fc0,40).hex(),'ahead':rd(0x7e2ee8,24).hex(),'mode3':rd(0x401000,64).hex(),'provider':rd(0x7e2f00,72).hex(),'command':w(rd(0x7e088c,2))};r['samples'].append(z);save();return z
  def advance(n):
   if time.monotonic()-start>args.seconds:raise TimeoutError('diagnostic deadline')
   z=s.run_frames(n)
   if z['timedOut'] or z['framesAdvanced']!=n:raise RuntimeError('incomplete frame advance')
  def wait(target,limit):
   for _ in range(limit//4):
    z=sample();a=bytes.fromhex(z['retained']);b=bytes.fromhex(z['mode3']);v=bytes.fromhex(z['viewport'])
    if z['frame']>20 and z['error']:r['cpu']=s.get_cpu_state();save();raise RuntimeError('SCUMM error')
    if z['room']==1 and b[19]==1 and not v[0] and (w(a)==target if target is not None else w(rd(0x40104c,2))==32 and z['command']==160):
     advance(2);return z
    advance(4)
   r['cpu']=s.get_cpu_state();save();raise TimeoutError('bounded camera boundary')
  def capture(label):
   queued=None;presented=None
   for _ in range(100):
    rr=Reads(s);pose=read_committed_pose(rr,cursor_base=0x400740)
    if queued is not None and queued_generation_is_presented(queued,pose):
     if presented is None:presented=rr.get_state()['frameCount']
     elif rr.get_state()['frameCount']>presented:
      rec=capture_presented_generation(rr,queued,out,label,cursor_base=0x400740)
      origin=w(rd(0x401084,2));back,g=camera_viewport(visual,xstart=origin-32,reserved_bottom=0)
      expected=bytearray(back);cur=queued['cursor']
      if w(cur,10):
       x=int.from_bytes(cur[16:18],'little',signed=True);y=int.from_bytes(cur[18:20],'little',signed=True)
       for i,covered in enumerate(MASKS[w(cur,6)]):
        dx,dy=x+i%16,y+i//16
        if covered and 0<=dx<256 and 0<=dy<224:expected[dy*256+dx]=w(cur,8)
      rec.update(origin=origin,hits=w(rd(0x7e2efe,2)),source_differences=sum(a!=b for a,b in zip(expected,queued['indexed'])))
      image=Image.open(out/(label+'.ppu.png')).convert('RGB').crop((0,0,256,224));colors=decode_cgram((out/(label+'.cgram.bin')).read_bytes());ref=Image.frombytes('RGB',(256,224),bytes(c for q in expected for c in colors[q]));ref.save(out/(label+'-reference.png'))
      rec['screenshot_equal']=ImageChops.difference(image,ref).getbbox() is None;r['captures'].append(rec);save()
      assert not rec['source_differences'] and not rec['ppu_indexed_differences'] and not rec['cgram_difference_bytes'] and rec['screenshot_equal'],rec
      return
    else:presented=None
    if presented is None and pose['mode3_surface_locked'] and pose['mode3_state'] in (2,3,4) and not pose['composition_active'] and not pose['actor_render_retry'] and not pose['event_count'] and not pose['surface_packets_pending'] and pose['backend_pending_generation']==pose['surface_next_generation']:
     if queued is None or queued['state']['backend_pending_generation']!=pose['backend_pending_generation']:queued=snapshot_locked_generation(rr,cursor_base=0x400740)
    advance(1)
   raise RuntimeError('no exclusive queued generation committed within100frames')
  s.pause();s.tool('reset_emulator',{'power':True});s.pause();advance(32)
  wait(None,6000);r['cold_completed_frame']=s.get_state()['frameCount'];r['initial_hits']=w(rd(0x7e2efe,2));save()
  # Move the real cursor off the black letterbox onto textured source pixels.
  # Transparent holes must follow the new background during retained exchange.
  s.set_input(s.BTN_RIGHT|s.BTN_DOWN,60,port=0);advance(64);s.set_input(0,1,port=0);advance(8)
  r['textured_cursor']=rd(0x400740,64).hex();save()
  s.write_memory('snesMemory',0x7e088c,(400).to_bytes(2,'little').hex());r['forward_input']=s.get_state()['frameCount'];wait(272,1800);capture('forward')
  assert ((r['captures'][-1]['hits']-r['initial_hits'])&65535)>0,'speculative path never consumed'
  s.write_memory('snesMemory',0x7e088c,(160).to_bytes(2,'little').hex());r['reverse_input']=s.get_state()['frameCount'];wait(32,1800);capture('reverse')
  r['result']='PASS_CHECKED_SYNTHETIC_CAMERA';save()
 except BaseException as e:r['failure']=str(e);save();raise
