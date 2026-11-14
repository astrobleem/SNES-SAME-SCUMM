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

def source_files(*, masks: bool = False, transitions: bool = False,
                 sound_status_probe: bool = False) -> dict[str, bytes]:
    base = camera_files()
    decoded = bytes(b ^ 0x69 for b in base['ATLANTIS/ATLANTIS.001'])
    size = int.from_bytes(decoded[34:38], 'big')
    room = decoded[38:30+size]
    if masks:
        # Original-format source z-planes, decoded by the existing ROOM parser.
        chunks=[];pos=0
        while pos<len(room):
            length=int.from_bytes(room[pos+4:pos+8],'big');tag=room[pos:pos+4];payload=room[pos+8:pos+length]
            if tag==b'RMIM':
                smap=payload[18:]  # RMIH(10), IM00 header(8), then original SMAP
                planes=[]
                for plane in (1,2):
                    offsets=[];data=bytearray()
                    for strip in range(80):
                        offsets.append(8+160+len(data))
                        column=bytes((0xAA if plane==1 else 0x55) if 16<=strip<31 and 84<=y<122 else 0 for y in range(144))
                        # Two literal source packets; SC5MASK cooker independently
                        # chooses its checked raw/RLE block representation.
                        data+=bytes((127,))+column[:127]+bytes((17,))+column[127:]
                    planes.append(ch(f'ZP{plane:02d}'.encode(),b''.join(struct.pack('<H',v) for v in offsets)+data))
                payload=ch(b'RMIH',struct.pack('<H',2))+ch(b'IM00',smap+b''.join(planes))
            chunks.append(ch(tag,payload));pos+=length
        room=b''.join(chunks)
    p = Program()
    if sound_status_probe:
        def query(sound, result):
            p.emit('queued status', bytes((0x4c, 0, 13, 0, 0, sound, 0, 255)))
            p.emit('flush', bytes((0x4c, 0, 255, 255, 255)))
            p.emit('copy VAR_SOUNDRESULT', bytes((0x9a, result, 0, 56, 0)))
        query(64, 150)
        p.emit('start logical SFX', bytes((0x1c, 64)))
        query(64, 151)
        query(0, 152)
        p.emit('stop logical SFX', bytes((0x3c, 64)))
        query(64, 153)
        p.emit('queue start', bytes((0x4c, 0, 8, 0, 0, 64, 0, 255)))
        p.emit('flush start', bytes((0x4c, 0, 255, 255, 255)))
        query(64, 155)
        p.emit('queue stop all', bytes((0x4c, 0, 10, 0, 255)))
        p.emit('flush stop all', bytes((0x4c, 0, 255, 255, 255)))
        p.emit('mutating result', bytes((0x9a, 156, 0, 56, 0)))
        query(64, 157)
        p.move(154, 0x1357)
        p.emit('probe complete', b'\0')
    p.move(0x4000,0);p.move(0x4001,0)
    p.emit('load room',b'\x72\x01')
    for actor in (1,2):
        p.emit('defaults costume ignoreBoxes animation speed',bytes((0x13,actor,8,1,actor,20,22,8,255)))
        if masks:p.emit('foreground plane',bytes((0x13,actor,19,actor,255)))
        p.emit('actor room',bytes((0x2d,actor,1)))
    for n, actors in enumerate(STAGES,1):
        for actor, (x,y,sx,sy,facing,frame) in enumerate(actors,1):
            p.emit('scale',bytes((0x13,actor,17,sx,sy,255)))
            p.emit('position',bytes((1,actor))+struct.pack('<hh',x,y))
            p.emit('facing',bytes((0x11,actor,{180:250,90:249,270:248}[facing])))
            p.emit('chore',bytes((0x11,actor,frame)))
        p.wait_ack(n,f'scene {n}')
    if transitions:
        for n, target in ((4, 2), (5, 1)):
            # Start another animated pose before the original room request.
            # This exercises whole-scene ownership, including scratch-free
            # intervals; no engine diagnostic code or resource writes.
            for actor in (1,2):p.emit('chore',bytes((0x11,actor,2)))
            p.emit('yield',b'\x80')
            p.emit('load room',bytes((0x72,target)))
            for actor in (1,2):p.emit('actor room',bytes((0x2d,actor,target)))
            p.wait_ack(n,f'room transition {n}')
    p.move(0x4001,6 if transitions else len(STAGES)+1);p.emit('stop',b'\0')
    container=bytearray(ch(b'ROOM',room));script=len(container);container+=ch(b'SCRP',bytes(p.data))
    costs=[]
    for actor in (1,2):
        raw=bytearray(costume())
        if actor==2:raw[3:6]=bytes((0,120,200))
        costs.append(len(container));container+=ch(b'COST',raw)
    if transitions:
        first=ch(b'LFLF',container);second=ch(b'LFLF',ch(b'ROOM',room))
        loff=bytes((2,1))+struct.pack('<I',35)+bytes((2,))+struct.pack('<I',35+len(first))
        data=ch(b'LECF',ch(b'LOFF',loff)+first+second)
    else:
        data=ch(b'LECF',ch(b'LOFF',bytes((1,1))+struct.pack('<I',30))+ch(b'LFLF',container))
    index=(ch(b'DOBJ',struct.pack('<H',256)+bytes(1280))
           +ch(b'DSCR',directory(bytes((0,1)),(0,script)))
           +ch(b'DCOS',directory(bytes((0,1,1)),(0,*costs)))+ch(b'DSOU',directory(b'',[])))
    return {f'ATLANTIS/ATLANTIS.{n:03}':bytes(b^0x69 for b in raw) for n,raw in enumerate((index,data))}

def write_archive(path: Path, *, masks: bool = False, transitions: bool = False,
                  sound_status_probe: bool = False) -> None:
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as archive:
        for name,data in source_files(masks=masks,transitions=transitions,
                                      sound_status_probe=sound_status_probe).items():
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.external_attr=0o100644<<16
            archive.writestr(info,data)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--masks',action='store_true');parser.add_argument('--transitions',action='store_true')
    parser.add_argument('--sound-status-probe', action='store_true')
    args=parser.parse_args();write_archive(args.output,masks=args.masks,transitions=args.transitions,
                                         sound_status_probe=args.sound_status_probe)
