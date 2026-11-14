#!/usr/bin/env python3
"""Bounded source-driven two-actor native scene acceptance.

Public synthetic SCUMM bytecode controls actors and waits for local diagnostic
acknowledgements. Native snapshots supply each actor's actual pose step; the
independent source compositor supplies expected complete INDEX8/PPU pixels.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,os,re,socket,sys,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]

class Reads:
    def __init__(self,session):
        self.session=session;self.pages={};self.state=session.get_state()
        assert self.state['isPaused']
    def __getattr__(self,name):return getattr(self.session,name)
    def get_state(self):return self.state
    def read_memory(self,kind,address,size):
        if kind!='snesMemory' or not (0x7e0000<=address and address+size<=0x800000 or 0x400000<=address and address+size<=0x420000):
            return self.session.read_memory(kind,address,size)
        result=bytearray()
        while size:
            page=address&~4095
            if page not in self.pages:self.pages[page]=self.session.read_memory(kind,page,4096)
            off=address-page;n=min(size,4096-off);result.extend(self.pages[page][off:off+n]);address+=n;size-=n
        return bytes(result)
    def read_u8(self,address):return self.read_memory('snesMemory',address,1)[0]
    def read_u16(self,address):return int.from_bytes(self.read_memory('snesMemory',address,2),'little')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('rom','directory','archive','profile','nexen','native-core','mcp-python','output'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--port',type=int,required=True)
    ap.add_argument('--masks',action='store_true')
    ap.add_argument('--expect-mask-crc-error',type=Path,metavar='FAULT_MANIFEST',
                    help='negative control: isolated package with one intentionally corrupt checked mask block')

    args=ap.parse_args()
    if args.expect_mask_crc_error and not args.masks:
        ap.error('mask CRC control requires the original masked fixture')
    if not re.fullmatch(r':\d+',os.environ.get('DISPLAY','')) or not Path(os.environ.get('XAUTHORITY','/missing')).is_file():
        ap.error('canonical private Xvfb supervisor required')
    sys.path.insert(0,str(args.mcp_python))
    from mesen_mcp import session as ms
    from fate_replay import advance_bounded
    from validate_scumm_startup42_nexen import verified_symbol_map_for_rom
    from validate_scumm_actor_visual_probe_nexen import read_committed_pose,committed_pose_is_presented,capture_committed_surface,selector_index
    from examples.resources.scumm_v5.actor_scene_fixture import source_files, STAGES
    stages = STAGES
    from tools.generate_snes_scumm_actor_sprite import source_bytes
    from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
    from same.engines.scumm_v5.policy import parse_game_policy
    from same.engines.scumm_v5.room import ScummV5RoomAdapter
    from same.engines.scumm_v5.engine import ActorState
    from same.resources import MemoryResourceProvider
    from same.profile import load_profile
    from same.video import IndexedSurface
    from same.engines.scumm_v5.cursor import MASKS
    from same.snes_surface import encode_cgram
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    def validate_nexen(path):
        for file,marker in ((Path(path).parent/'Nexen.dll',b'McpRunner'),(args.native_core,b'McpDrainEvents')):
            if not file.is_file() or marker not in file.read_bytes():raise RuntimeError(f'unverified Nexen MCP build {file}')
    validate_nexen(args.nexen);ms.validate_mesen_build=validate_nexen
    verified_symbol_map_for_rom(args.rom)
    listing=args.rom.with_suffix('.lst').read_text()
    symbols={n:int(v,16) for n,v in re.findall(r'^; ([A-Z][A-Z0-9_]*)\s+= \$([0-9A-Fa-f]+)\s+\(Constant\)',listing,re.M)}
    assert symbols['SCUMM_V5_ACTOR_CEL_FORMAT']==1
    # C4 public ABI: 25 slots, 32 u16 locals each. Check contiguous allocation.
    assert symbols['SAME_SCUMM_C4_STATE_END'] >= symbols['SAME_SCUMM_C4_SLOT_LOCALS']+25*64
    native=json.loads(args.directory.read_text());boot=next(e for e in native['entries'] if e['identity']=='GlobalProgram(1)')
    source=source_bytes(args.archive)
    fixture=source_files(masks=args.masks)
    assert source=={'game.index':fixture['ATLANTIS/ATLANTIS.000'],'game.data':fixture['ATLANTIS/ATLANTIS.001']},'diagnostic acknowledges only its exact public synthetic source'
    provider=LucasartsScummV5ResourceProvider(MemoryResourceProvider(source),parse_game_policy(load_profile(args.profile,verify_resources=False)))
    assert hashlib.sha256(provider.read('script.1')).hexdigest()==boot['sha256']
    services=SimpleNamespace(resources=provider,resource_read=provider.read,debug=SimpleNamespace(marker=lambda *a:None))
    adapter=ScummV5RoomAdapter(SimpleNamespace(services=services))
    from same.engines.scumm_v5.room import decode_room
    room=decode_room(provider.read('room.1'),key='room.1')
    adapter.room=room;adapter.backdrop_surface=IndexedSurface.wrap(room.width,room.height,room.width,room.pixels)
    adapter.logical_surface=IndexedSurface(room.width,room.height)
    args.output.mkdir(parents=True,exist_ok=False)
    report=dict(result='NOT_VERIFIED',hypothesis='Ordered checked cels reproduce source phase scaling at255,231,asymmetric,mirrored and clipped poses; multichunk publication is complete and old pixels restore.',expected='8 acknowledged stages; 9 source/INDEX8/VRAM/CGRAM matches including two animation steps; error0',exit_condition='first failed boundary or all captures;540sec internal/600sec supervisor',kind='COPYRIGHT_FREE_NATIVE_SCALING',identities={ext:sha(args.rom.with_suffix(ext)) for ext in ('.sfc','.map','.msu','.build_identity.json')},archive_sha256=sha(args.archive),boot_identity=boot,samples=[],captures=[],acknowledgements=[])
    report.update(hypothesis='Two independently scaled/animated source actors compose in source Y/ID order and restore their overlapping old coverage.',expected='3 staged scene captures plus a second animated scene; complete source/INDEX8/PPU/CGRAM equality',kind='COPYRIGHT_FREE_NATIVE_ACTOR_SCENE')
    if args.expect_mask_crc_error:
        import zlib
        fault=json.loads(args.expect_mask_crc_error.read_text())
        package=args.rom.with_suffix('.msu').read_bytes()
        block=fault['block'];offset=int(block['package_offset']);length=int(block['length'])
        assert sha(args.rom.with_suffix('.msu'))==fault['fault_package_sha256']
        assert fault['source_package_sha256']!=fault['fault_package_sha256']
        assert 0<=offset<=len(package)-length and 0<length<=256
        assert zlib.crc32(package[offset:offset+length])&0xffffffff != int(block['crc32'],16)
        report.update(kind='COPYRIGHT_FREE_NATIVE_MASK_CRC_REJECTION',fault_manifest=fault,
                      hypothesis='A corrupt checked mask block cannot publish any part of the first actor scene',
                      expected='SCUMM resource error16 and provider CRC error6; zero completed actor scenes')
    def save():
        p=args.output/'report.pending.json';p.write_text(json.dumps(report,indent=2)+'\n');p.replace(args.output/'report.json')
    started=time.monotonic()
    def sym(name):return symbols[name]
    def sample(session):
        r=Reads(session);pose=read_committed_pose(r,cursor_base=sym('SAME_SCUMM_CURSOR_VALID'))
        slots=r.read_memory('snesMemory',sym('SAME_SCUMM_C4_SLOT_STATUS'),200)
        slot=None
        for i in range(25):
            if slots[i] not in (0,4) and slots[25+i]==1:
                selector=slots[50+i]
                if r.read_u16(sym('SAME_SCUMM_RESIDENT_UNIT_IDS')+2*selector_index(selector))==boot['program_unit_id']:
                    assert slot is None;slot=i
        stage=0 if slot is None else r.read_u16(sym('SAME_SCUMM_C4_SLOT_LOCALS')+slot*64+2)
        row=dict(scene_dirty=r.read_u16(sym('SAME_SCUMM_SCENE_DIRTY')),scene_phase=r.read_u16(sym('SAME_SCUMM_SCENE_PHASE')),scene_generation=int.from_bytes(r.read_memory('snesMemory',sym('SAME_SCUMM_SCENE_GENERATION'),4),'little'),snapshots=r.read_memory('snesMemory',sym('SAME_SCUMM_SCENE_SNAPSHOTS'),1024).hex(),scene_control=r.read_memory('snesMemory',sym('SAME_SCUMM_SCENE_CONTROL'),256).hex(),frame=r.state['frameCount'],slot=slot,stage=stage,pose=pose,cel=r.read_memory('snesMemory',sym('SAME_SCUMM_CEL_STATE_BASE'),72).hex(),actor=r.read_memory('snesMemory',sym('SAME_SCUMM_ACTOR_POSE_STATE_BASE'),128).hex(),provider=r.read_memory('snesMemory',0x7e2f00,72).hex())
        row['cpu_state']=session.get_cpu_state()
        row['live_control']=r.read_memory('snesMemory',sym('SAME_SCUMM_LIVE_ROOM_CONTROL'),64).hex()
        row['live_pending']=r.read_memory('snesMemory',sym('SAME_SCUMM_LIVE_ROOM_PENDING_BASE'),64).hex()
        row['room_request']=r.read_memory('snesMemory',sym('SAME_SCUMM_MSU_ROOM_STATE'),48).hex()
        report['samples'].append(row);save()
        if len(report['samples']) > 1:
            previous=report['samples'][-2]
            if row['scene_phase'] in (1,2) and previous['scene_phase'] in (1,2):
                assert pose['surface_next_generation']==previous['pose']['surface_next_generation'], 'partial scene publication'
                assert pose['composition_active'], 'incomplete scene lost owner'
        if row['frame']>100 and pose['error'] and not args.expect_mask_crc_error:raise RuntimeError(f"SCUMM error{pose['error']} stage{stage}")
        if time.monotonic()-started>540 or row['frame']>12000:raise TimeoutError('bounded native control deadline')
        return r,row
    def compare(session,r,row,expected,label):
        pose=row['pose'];rec=capture_committed_surface(r,args.output,label,cursor_base=sym('SAME_SCUMM_CURSOR_VALID'),expected_room=1)
        rec['scene_generation']=row['scene_generation']
        actors={}
        raw=bytes.fromhex(row['snapshots'])
        for actor_id,e in enumerate(expected,1):
            d=raw[actor_id*32:(actor_id+1)*32]
            u16=lambda off:int.from_bytes(d[off:off+2],'little')
            assert (u16(0),u16(2),d[6],d[7],u16(4),d[10])==e, (actor_id,d.hex(),e)
            actors[actor_id]=ActorState(costume=d[8],room=1,visible=bool(d[9]),position=(u16(0),u16(2)),scale=(d[6],d[7]),facing=u16(4),costume_frame=d[10],costume_step=d[12],ignore_boxes=True,force_clip=d[18])
        adapter.render_actors(actors,current_room=1,costume_key=lambda n:f'costume.{n}',project=False)
        rec['actor_snapshots']={str(k):dict(position=v.position,scale=v.scale,facing=v.facing,frame=v.costume_frame,step=v.costume_step,costume=v.costume) for k,v in actors.items()}
        ox=r.read_u16(sym('SAME_VIDEO_SURFACE_SOURCE_X'));oy=r.read_u16(sym('SAME_VIDEO_SURFACE_SOURCE_Y'))
        dx=r.read_u16(sym('SAME_VIDEO_SURFACE_DEST_X'));dy=r.read_u16(sym('SAME_VIDEO_SURFACE_DEST_Y'))
        expected_pixels=bytearray(256*224)
        for y in range(room.height):
            target=y-oy+dy
            if 0<=target<192:
                for x in range(256):
                    sx=x-dx+ox
                    if 0<=sx<room.width:expected_pixels[target*256+x]=adapter.logical_surface.pixels[y*room.width+sx]
        cursor=rec['pose']['builtin_cursor']
        if cursor['visible']:
            for i,covered in enumerate(MASKS[cursor['id']]):
                x=cursor['left']+i%16;y=cursor['top']+i//16
                if covered and 0<=x<256 and 0<=y<192:expected_pixels[y*256+x]=cursor['color']
        actual=(args.output/(label+'.indexed.bin')).read_bytes()
        rec['source_indexed_differences']=sum(a!=b for a,b in zip(expected_pixels,actual))
        rec['source_reference_sha256']=hashlib.sha256(expected_pixels).hexdigest();rec['source_origin']=[ox,oy,dx,dy]
        source_palette=tuple(room.palette)+((0,0,0),)*(256-len(room.palette))
        rec['source_cgram_differences']=sum(a!=b for a,b in zip(encode_cgram(source_palette),(args.output/(label+'.cgram.bin')).read_bytes()))
        (args.output/(label+'.reference.bin')).write_bytes(expected_pixels)
        report['captures'].append(rec);save()
        assert not any(rec[k] for k in ('source_indexed_differences','ppu_indexed_differences','cgram_difference_bytes','source_cgram_differences')),rec
    with socket.socket() as probe:probe.bind(('127.0.0.1',args.port))
    save()
    try:
        with ms.McpSession(rom=args.rom,mesen=args.nexen,cwd=args.rom.parent,port=args.port,boot_wait=2,socket_timeout=12,stderr_log=args.output/'nexen.stderr.log') as session:
            session.pause();session.set_input(0,1)
            if args.expect_mask_crc_error:
                first_error_frame = None
                for _ in range(500):
                    r,row=sample(session)
                    if row['pose']['error']:
                        report['msu_error']=r.read_u8(sym('SAME_MSU1_ERROR'))
                        assert row['pose']['error']==16 and report['msu_error']==6
                        assert row['scene_generation']==0, 'failed actor scene was published'
                        # An emulated frame stop can interrupt the synchronous
                        # underlay rollback after the error byte is written.
                        # Observe cleanup completion, never infer it from error.
                        if first_error_frame is None:
                            first_error_frame = row['frame']
                            report['first_error_frame'] = first_error_frame
                        if row['scene_phase']==0 and not row['pose']['composition_active']:
                            report['result']='NATIVE_MASK_CRC_REJECTED_BEFORE_SCENE_PUBLICATION';save()
                            return 0
                        assert row['frame'] - first_error_frame < 32, 'mask failure cleanup did not finish'
                    advance_bounded(session,8)
                raise TimeoutError('expected checked mask rejection not observed')
            for stage,expected in enumerate(stages,1):
                seen=set();first=None; previous_generation=report['captures'][-1]['scene_generation'] if report['captures'] else 0
                while True:
                    r,row=sample(session);pose=row['pose']
                    if first is None:first=row['frame']
                    raw=bytes.fromhex(row['snapshots']);key=tuple(raw[i*32+12] for i in (1,2))
                    ready=(row['stage']==stage and row['scene_phase']==0 and row['scene_generation']>previous_generation and not row['scene_dirty']
                           and committed_pose_is_presented(pose,expected_room=1))
                    if ready and key not in seen:
                        compare(session,r,row,expected,f'stage-{stage}-steps-{key[0]}-{key[1]}')
                        seen.add(key)
                        if stage!=2 or len(seen)==2:
                            address=sym('SAME_SCUMM_C4_SLOT_LOCALS')+row['slot']*64
                            session.write_u16(address,stage)
                            report['acknowledgements'].append(dict(stage=stage,frame=row['frame'],slot=row['slot'],local_address=address));save();break
                    if row['frame']-first>1800:raise TimeoutError(f'stage{stage} did not reach a completed matching image')
                    # Cold room conversion is not an actor completion fence.
                    # Poll it in bounded batches; inspect each frame near actor publication.
                    advance_bounded(session,16 if pose['surface_pending_visual'] or row['stage']!=stage else 4)
            report['result']='NATIVE_ACTOR_SCENE_SOURCE_INDEX8_PPU_MATCH';save()
    except Exception as exc:
        report['failure']=repr(exc);save();raise
    print(json.dumps(dict(result=report['result'],captures=len(report['captures']),report=str(args.output/'report.json'))))
    return 0

if __name__=='__main__':raise SystemExit(main())
