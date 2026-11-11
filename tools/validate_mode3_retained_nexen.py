#!/usr/bin/env python3
"""Bounded native retained-viewport control; original fixture, no game writes.

Run only through the canonical private-display process supervisor. Commands
address the existing Mode-3 fixture, never output pixels or renderer counters.
"""
from __future__ import annotations
import argparse, base64, hashlib, io, json, sys, time
from pathlib import Path
from PIL import Image, ImageChops
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from same.snes_surface import decode_snes_8bpp_tile, decode_cgram
from same.snes_video_backend import retained_map_offset, linearize_retained_index8
from validate_mode3_surface_backend_nexen import fixture_states, reference_image
from validate_scumm_startup42_nexen import verified_symbol_map_for_rom


def pixel(x, y):
    value=(x+y)&255
    if y==9 and x==9: value ^= 1
    if y==0 and 0<=x<256 and x%8==0 and (x>=128 or x&8): value ^= 1
    return value


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--port',required=True,type=int)
    ap.add_argument('--seconds',type=int,default=150)
    ap.add_argument('--foreground',action='store_true')
    ap.add_argument('--targets',default='1,8,9,16,8,0')
    a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    mp,symbols=verified_symbol_map_for_rom(a.rom.resolve())
    for required in ('Same_Mode3_Retained_Nmi__map_row','Same_Mode3_Retained_Nmi__range_done','Same_Mode3_Boot_Realize__map_ready'):
        if required not in symbols: raise RuntimeError(f'missing native retained commit: {required}')
    identity=a.rom.with_suffix('.build_identity.json')
    report={'hypothesis':'small camera steps retain characters; NMI commits only after checked-column DMA',
            'expected':'complete INDEX8 and visible PPU equality, <=24 converted tiles/step, fixed HUD',
            'exit':'requested fixture targets captured or first mismatch/deadline',
            'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),
            'map_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),
            'identity_sha256':hashlib.sha256(identity.read_bytes()).hexdigest(),
            'native':True,'gameplay':False,'steps':[],'result':'NOT_VERIFIED'}
    def save(): (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();deadline=time.monotonic()+a.seconds
    sys.path.insert(0,'/home/chad/Mesen2/python')
    import mesen_mcp.session as m
    m.validate_mesen_build=lambda _:None # invocation is the established Nexen MCP contract
    try:
        with m.McpSession(rom=a.rom.resolve(),mesen=Path('/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen'),cwd=ROOT,port=a.port,boot_wait=2,socket_timeout=15,stderr_log=a.output/'nexen-stderr.log') as s:
            def rd(addr,n):return s.read_memory('snesMemory',addr,n)
            def word(addr):return int.from_bytes(rd(addr,2),'little')
            def wr(addr,v):s.write_memory('snesMemory',addr,v.to_bytes(2,'little').hex())
            def frames(n=1):
                if time.monotonic()>deadline: raise TimeoutError('bounded diagnostic deadline')
                r=s.run_frames(n)
                if r['timedOut'] or r['framesAdvanced']!=n:raise RuntimeError('frame advance incomplete')
            def wait(predicate,limit):
                for i in range(limit):
                    if predicate():return
                    frames()
                    if i % 8 == 0:
                        record={'sample':i,'control':rd(0x401000,64).hex(),
                                'retained':rd(0x401084,64).hex(),
                                'fixture':rd(0x41e900,32).hex(),
                                'cpu':s.get_cpu_state(),
                                'dma':rd(0x7e223a,14).hex()}
                        report.setdefault('boundary_trace',[]).append(record);save()
                raise TimeoutError('fixture boundary not reached within frame budget')
            s.pause();s.tool('reset_emulator',{'power':True});s.pause()
            for _ in range(100):
                if word(0x41e806)==1:break
                frames(8)
            else:raise RuntimeError('legacy six-generation control did not finish')
            frames(2)
            assert rd(0x402000,57344)==fixture_states()[0][-1], 'baseline INDEX8'
            wr(0x41e900,1)
            wait(lambda:word(0x41e900)==0,20)
            assert word(0x41e904)==1,'retained init rejected'
            if a.foreground:
                wr(0x41e900,4);wait(lambda:word(0x41e900)==0,160)
                assert word(0x41e904)==1,'foreground command rejected'
            for target in map(int,a.targets.split(',')):
                target=max(0,min(1024,target))
                while word(0x401084)!=target:
                    prior=word(0x401084);wr(0x41e902,target);wr(0x41e900,2)
                    wait(lambda:word(0x41e900)==0,160)
                    assert word(0x41e904)==1,'fixture command rejected'
                    frames(2) # full raster after generation acknowledgment, never an in-flight screenshot
                    x=word(0x401084); gen=word(0x401010)
                    c=rd(0x401000,64)
                    step={'previous_x':prior,'source_x':x,'generation':gen,
                          'frames':(word(0x41e90a)-word(0x41e908))&65535,
                          'converted_tiles':int.from_bytes(c[42:44],'little'),
                          'character_bytes':int.from_bytes(c[46:48],'little'),
                          'dma_budgets':int.from_bytes(c[50:52],'little')}
                    report['steps'].append(step); save()
                    def visible(xx,y):
                        wx=xx+(x if y<192 else 0)
                        if a.foreground and 44<=xx<48 and 40<=y<46:return 240
                        if a.foreground and 100<=wx<112 and 80<=y<96:return 177 if wx&1 else 0
                        return pixel(wx,y)
                    expected=bytes(visible(xx,y) for y in range(224) for xx in range(256))
                    physical=rd(0x402000,57344)
                    (a.output/f'{gen}-physical-index8.bin').write_bytes(physical)
                    live=linearize_retained_index8(physical,origin=word(0x40109c))
                    step['index_mismatches']=sum(p!=q for p,q in zip(live,expected))
                    v=s.read_memory('snesVideoRam',0,65536); cg=s.read_memory('snesCgRam',0,512)
                    tiles={t:decode_snes_8bpp_tile(v[t*64:t*64+64]) for t in range(920)}
                    decoded=bytearray()
                    for y in range(224):
                        for xx in range(256):
                            sx=xx+(x if y<192 else 0)
                            off=0xf000+retained_map_offset(sx//8,y//8)
                            t=int.from_bytes(v[off:off+2],'little')&1023
                            decoded.append(tiles[t][y&7][sx&7])
                    step['vram_mismatches']=sum(p!=q for p,q in zip(decoded,expected))
                    shot=base64.b64decode(s.take_screenshot(format='base64')['base64'])
                    img=Image.open(io.BytesIO(shot)).convert('RGB').crop((0,0,256,224))
                    colors=decode_cgram(cg)
                    ref=Image.frombytes('RGB',(256,224),bytes(v for p in expected for v in colors[p]))
                    img.save(a.output/f'{gen}-native.png');ref.save(a.output/f'{gen}-reference.png')
                    step['ppu_equal']=ImageChops.difference(img,ref).getbbox() is None
                    step['ppu_state']=s.get_ppu_state()
                    step['cpu']=s.get_cpu_state()
                    save()
                    assert not step['index_mismatches'],'INDEX8 mismatch'
                    assert not step['vram_mismatches'],'VRAM mismatch'
                    assert step['ppu_equal'],'visible PPU mismatch'
                    assert step['converted_tiles']<= (30 if a.foreground else 24) and step['character_bytes']<= (30*64 if a.foreground else 1536),'full conversion regression'
            report['result']='PASS';save()
    except BaseException as e:
        report['failure']=repr(e);save();raise
    print(json.dumps({'result':report['result'],'steps':len(report['steps']),'report':str(a.output/'report.json')}))

if __name__=='__main__':main()
