"""Original ordered-cel, checked multichunk scaling fixture (not gameplay).

The ordinary source VM drives actorOps and holds each stage until its local
acknowledgement. No native diagnostic personality or guest renderer writes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import struct
import zipfile
from .camera_pipeline_fixture import source_files as camera_source_files
from .game_analysis_fixture import _chunk as ch, _directory as directory
from tools.actor_probe_program import Program

STAGES = (
    dict(scale=(255,255), facing=180, frame=1, x=130,y=125),
    dict(scale=(231,231), facing=180, frame=1, x=130,y=125),
    dict(scale=(128,200), facing=90, frame=1, x=130,y=125),
    dict(scale=(231,231), facing=270, frame=1, x=130,y=125),
    dict(scale=(255,255), facing=180, frame=1, x=2,y=20),
    dict(scale=(231,231), facing=180, frame=0, x=130,y=125),
    dict(scale=(231,231), facing=180, frame=2, x=130,y=125),
    dict(scale=(231,231), facing=180, frame=1, x=190,y=120),
)
CAMERA_STAGES = tuple(dict(scale=(231,231), facing=180, frame=1, x=330, y=125,
                          camera=camera) for camera in (160,224,160,216,224,200,224))

def costume() -> bytes:
    # Two independently anchored limbs, transparent holes and color slot 1
    # mapping to opaque screen zero. >2 KiB opaque pixels at full size.
    animations=11; table=18; data_offsets=52
    data=bytearray(data_offsets+(animations+1)*2)
    data[:2]=bytes((animations,0x58));data[2:18]=bytes((0,0,80,240,*range(4,16)))
    static=len(data);data+=struct.pack('<HHBHB',0xc000,0,0,0,0)
    animated=len(data);data+=struct.pack('<HHBHB',0xc000,0,1,0,1)
    for animation in range(4,12):struct.pack_into('<H',data,data_offsets+animation*2,(static if animation<8 else animated)+6)
    commands=len(data);data+=bytes((0,1));struct.pack_into('<H',data,table,commands+6)
    frames=[]
    for limb in range(2):
        frames.append(len(data));data+=bytes(4)
        struct.pack_into('<H',data,table+2+limb*2,frames[-1]+6)
    for limb in range(2):
        w,h=(36,64) if limb==0 else (24,32)
        for step in range(2):
            off=len(data);struct.pack_into('<H',data,frames[limb]+2*step,off+6)
            data+=struct.pack('<HHhhhh',w,h,-18+step if limb==0 else -8,-64 if limb==0 else -40,3 if limb==0 else 0,2 if limb==0 else 0)
            for x in range(w):
                for y in range(h):
                    slot=0 if (x*7+y*3)%19==0 else 1+(x+y//4+step+limb)%3
                    data.append(slot<<4|1)
    return bytes(data)


def source_files(scenario: str = 'scaling') -> dict[str,bytes]:
    if scenario not in ('scaling', 'camera-exposure'):
        raise ValueError('unknown original fixture scenario')
    stages = STAGES if scenario == 'scaling' else CAMERA_STAGES
    original=camera_source_files();decoded=bytes(v^0x69 for v in original['ATLANTIS/ATLANTIS.001'])
    size=int.from_bytes(decoded[34:38],'big');room=decoded[38:30+size]
    p=Program();p.move(0x4000,0);p.move(0x4001,0)
    p.emit('loadRoom',b'\x72\x01')
    p.emit('actor defaults/costume/ignoreBoxes/speed',b'\x13\x01\x08\x01\x01\x14\x16\x08\xff')
    p.emit('putActorInRoom',b'\x2d\x01\x01')
    for n,stage in enumerate(stages,1):
        # Camera-only stages must not reset an animation or actor key: that
        # could conceal the missing exposure invalidation being exercised.
        if scenario == 'scaling' or n == 1:
            p.emit('actor scale',bytes((0x13,1,0x11,*stage['scale'],0xff)))
            p.emit('putActor',b'\x01\x01'+struct.pack('<hh',stage['x'],stage['y']))
            p.emit('face',bytes((0x11,1,{180:250,90:249,270:248}[stage['facing']])))
            p.emit('animate',bytes((0x11,1,stage['frame'])))
        if 'camera' in stage:
            p.emit('setCameraAt', b'\x32'+struct.pack('<H',stage['camera']))
        p.wait_ack(n,f'scaled pose {n}')
    p.move(0x4001,len(stages)+1);p.emit('stop',b'\0')
    body=bytes(p.data)
    container=bytearray(ch(b'ROOM',room));script=len(container);container+=ch(b'SCRP',body)
    cost=len(container);container+=ch(b'COST',costume())
    loff=bytes((1,1))+struct.pack('<I',30)
    data=ch(b'LECF',ch(b'LOFF',loff)+ch(b'LFLF',container))
    index=(ch(b'DOBJ',struct.pack('<H',256)+bytes(1280))
           +ch(b'DSCR',directory(bytes((0,1)),(0,script)))
           +ch(b'DCOS',directory(bytes((0,1)),(0,cost)))+ch(b'DSOU',directory(b'',[])))
    return {f'ATLANTIS/ATLANTIS.{n:03}':bytes(v^0x69 for v in payload) for n,payload in enumerate((index,data))}


def write_archive(path:Path, scenario: str = 'scaling')->None:
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as out:
        for name,data in source_files(scenario).items():
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.external_attr=0o100644<<16
            out.writestr(info,data)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    parser.add_argument('--scenario',choices=('scaling','camera-exposure'),default='scaling')
    args=parser.parse_args();write_archive(args.output,args.scenario)
