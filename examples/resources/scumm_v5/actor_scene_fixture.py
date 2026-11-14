"""Original two-actor scene driven by ordinary source scripts, not game data."""
from __future__ import annotations
import argparse
from pathlib import Path
import struct
import zipfile
from .actor_scaling_fixture import costume
from .camera_pipeline_fixture import source_files as camera_files
from .game_analysis_fixture import _chunk as ch, _directory as directory
from tools.actor_probe_program import Program

STAGES = (
    ((150,124,231,231,180,1),(160,126,128,200,90,1)),
    ((150,126,231,231,180,2),(160,124,128,200,270,2)),
    ((220,130,231,231,90,1),(160,124,128,200,270,1)),
)

def source_files() -> dict[str, bytes]:
    base = camera_files()
    decoded = bytes(b ^ 0x69 for b in base['ATLANTIS/ATLANTIS.001'])
    size = int.from_bytes(decoded[34:38], 'big')
    room = decoded[38:30+size]
    p = Program()
    p.move(0x4000,0);p.move(0x4001,0)
    p.emit('load room',b'\x72\x01')
    for actor in (1,2):
        p.emit('defaults costume ignoreBoxes animation speed',bytes((0x13,actor,8,1,actor,20,22,8,255)))
        p.emit('actor room',bytes((0x2d,actor,1)))
    for n, actors in enumerate(STAGES,1):
        for actor, (x,y,sx,sy,facing,frame) in enumerate(actors,1):
            p.emit('scale',bytes((0x13,actor,17,sx,sy,255)))
            p.emit('position',bytes((1,actor))+struct.pack('<hh',x,y))
            p.emit('facing',bytes((0x11,actor,{180:250,90:249,270:248}[facing])))
            p.emit('chore',bytes((0x11,actor,frame)))
        p.wait_ack(n,f'scene {n}')
    p.move(0x4001,len(STAGES)+1);p.emit('stop',b'\0')
    container=bytearray(ch(b'ROOM',room));script=len(container);container+=ch(b'SCRP',bytes(p.data))
    costs=[]
    for actor in (1,2):
        raw=bytearray(costume())
        if actor==2:raw[3:6]=bytes((0,120,200))
        costs.append(len(container));container+=ch(b'COST',raw)
    data=ch(b'LECF',ch(b'LOFF',bytes((1,1))+struct.pack('<I',30))+ch(b'LFLF',container))
    index=(ch(b'DOBJ',struct.pack('<H',256)+bytes(1280))
           +ch(b'DSCR',directory(bytes((0,1)),(0,script)))
           +ch(b'DCOS',directory(bytes((0,1,1)),(0,*costs)))+ch(b'DSOU',directory(b'',[])))
    return {f'ATLANTIS/ATLANTIS.{n:03}':bytes(b^0x69 for b in raw) for n,raw in enumerate((index,data))}

def write_archive(path: Path) -> None:
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as archive:
        for name,data in source_files().items():
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.external_attr=0o100644<<16
            archive.writestr(info,data)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    write_archive(parser.parse_args().output)
