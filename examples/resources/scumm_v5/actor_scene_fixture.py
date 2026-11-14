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

OBJECT_STAGES = (*STAGES, STAGES[-1])

def source_files(*, masks: bool = False, transitions: bool = False,
                 sound_status_probe: bool = False, cutscene_callback_probe: bool = False, room_hook_probe: bool = False,
                 object_images_probe: bool = False, absent_animation_probe: bool = False, walkbox_mask_probe: bool = False, one_shot_limb_probe: bool = False, hit_test_probe: bool = False) -> dict[str, bytes]:
    if hit_test_probe:
        object_images_probe = True
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
    if walkbox_mask_probe:
        if not masks:
            raise ValueError('walkbox mask probe requires original source masks')
        # PutActor follows source box scale231. The final pose crosses from
        # masked box1 into unmasked box2; actor2 retains explicit plane2.
        dummy=struct.pack('<hhhhhhhhBBH',*([-32000]*8),0,0,255)
        old=ch(b'BOXD',struct.pack('<H',2)+dummy+
               struct.pack('<hhhhhhhhBBH',0,0,639,0,639,143,0,143,0,0,255))
        new=ch(b'BOXD',struct.pack('<H',3)+dummy+
               struct.pack('<hhhhhhhhBBH',0,0,199,0,199,143,0,143,1,0,231)+
               struct.pack('<hhhhhhhhBBH',200,0,639,0,639,143,200,143,0,0,231))
        assert room.count(old)==1
        room=room.replace(old,new,1)
        room=room.replace(ch(b'BOXM',b'\0\0\0\xff\1\1\1\xff'),
                          ch(b'BOXM',b'\0\0\0\xff\1\1\1\2\2\2\xff\1\1\1\2\2\2\xff'),1)
    if object_images_probe:
        room = room.replace(ch(b'RMHD', struct.pack('<HHH', 640, 144, 0)),
                            ch(b'RMHD', struct.pack('<HHH', 640, 144, 2)), 1)
        for identity, parent in ((8, 0), (9, 1)):
            header = struct.pack('<HBBBBBBhhB', identity, 16, 13, 3, 4,
                                 0x80 if parent else 0, parent, 140, 130, 0)
            room += ch(b'OBCD', ch(b'CDHD', header) + ch(b'OBNA', f'original fixture {identity}'.encode()+b'\0'))
            states = bytearray()
            for state in (1, 2):
                strips = []
                for col in range(3):
                    pixels = bytes(255 if identity == 9 and (x+y)%3 == 0 else
                                   0 if identity == 8 and (x+y)%4 == 0 else
                                   (identity*17+state*9+col)%255 for y in range(32) for x in range(8))
                    if identity == 9:
                        bits=[]
                        for color in pixels[1:]:bits.extend((1,0,*((color>>b)&1 for b in range(8))))
                        packed=bytearray((len(bits)+7)//8)
                        for index,bit in enumerate(bits):packed[index//8] |= bit << (index%8)
                        strips.append(bytes((48,pixels[0]))+packed)
                    else:strips.append(b'\x01'+pixels)
                offset=20;directory_bytes=bytearray()
                for strip in strips:directory_bytes.extend(struct.pack('<I',offset));offset+=len(strip)
                content=ch(b'SMAP',directory_bytes+b''.join(strips))
                if masks:
                    for plane in (1,2):
                        content+=ch(f'ZP{plane:02d}'.encode(),struct.pack('<HHH',14,16,18)+bytes((0xA0,0xF0 if state==1 else 0))*3)
                states+=ch(f'IM{state:02X}'.encode(),content)
            room+=ch(b'OBIM',ch(b'IMHD',struct.pack('<8H',identity,2,2 if masks else 0,0,0,0,24,32))+states)
    if room_hook_probe:
        transitions = True
        def write(n, v): return b'\x1a'+struct.pack('<HH', n, v)
        def copy(n, v): return b'\x9a'+struct.pack('<HH', n, v)
        room = room.replace(ch(b'ENCD', b'\0'),
            ch(b'ENCD', copy(155, 150)+write(150, 5)+b'\0'))
        room = room.replace(ch(b'EXCD', b'\0'),
            ch(b'EXCD', copy(151, 150)+write(150, 2)+b'\0'))
    p = Program()
    if hit_test_probe:
        p.emit('install original room objects', b'\x72\x01')
        p.emit('visible parent state', bytes((0x07, 8, 0, 1)))
        def touchable(identity, enabled):
            p.emit('mutable class32', bytes((0x5d, identity, 0, 1,
                                            32 if enabled else 160, 0, 255)))
        def find(variable):
            p.emit('find overlapping room objects', bytes((0x35, variable, 0, 130, 110)))
        find(150)  # source defaults hide both objects before any mutation
        def class_op(identity, value):
            p.emit('class source override', b'\x5d'+struct.pack('<H',identity)+b'\x01'+struct.pack('<H',value)+b'\xff')
        def expect_class(value):
            p.emit('query source/override above old sparse seed limit',
                   b'\x1d'+struct.pack('<H',900)+b'\x01'+struct.pack('<H',value)+b'\xff\x03\x00')
            p.emit('count verified predicate', b'\x46\x9d\x00')
        expect_class(160)
        class_op(900,32); expect_class(32); expect_class(129)
        class_op(900,160); expect_class(160)
        class_op(900,0); expect_class(1); expect_class(32)
        class_op(900,129); class_op(900,160); expect_class(160)

        touchable(8, True); find(151)
        touchable(8, False); touchable(9, True); find(152)
        touchable(8, True); find(153)
        # Ownership alone is not a hit-test predicate. Only class32 changes
        # touchability; absent C16 rows mean no classes, not unselectable.
        p.emit('change owner without class mutation', bytes((0x29, 8, 0, 1)))
        find(155)
        touchable(8, False); touchable(9, False); find(156)
        p.move(154, 0x1357); p.emit('probe complete', b'\0')
    if room_hook_probe:
        p.emit('initial room without hooks', b'\x72\x01')
        for variable, number in ((30,2),(31,3),(28,4),(29,5)):p.move(variable,number)
        p.emit('ordered room lifecycle', b'\x72\x02')
        p.move(154,0x1357)
        p.emit('probe complete',b'\0')
    if cutscene_callback_probe:
        p.move(35, 2)
        p.move(36, 2)
        p.emit('cutscene argument', bytes.fromhex('40003412ff'))
        p.emit('end cutscene', b'\xc0')
        p.move(154, 0x1357)
        p.emit('probe complete', b'\0')
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
    if object_images_probe:
        for identity in (8,9):
            for _ in range(2):p.emit('idempotent source object state',bytes((0x07,identity,0,1)))
    for actor in (1,2):
        p.emit('defaults costume ignoreBoxes animation speed',bytes((0x13,actor,8,1,actor,20,22,8,255)))
        if walkbox_mask_probe and actor == 1:
            p.emit('source walkbox masking',bytes((0x13,actor,21,19,0,255)))
        elif masks:p.emit('foreground plane',bytes((0x13,actor,19,actor,255)))
        p.emit('actor room',bytes((0x2d,actor,1)))
    stages = OBJECT_STAGES if object_images_probe else STAGES
    for n, actors in enumerate(stages,1):
        if object_images_probe and n in (2,4):
            for _ in range(2):
                p.emit('idempotent replace or hide source object', bytes((0x07,8,0,2 if n==2 else 0)))
        if object_images_probe and n == 3:
            p.emit('owned object retains state-selected room patch', bytes((0x29,8,0,1)))
        for actor, (x,y,sx,sy,facing,frame) in enumerate(actors,1):
            p.emit('scale',bytes((0x13,actor,17,sx,sy,255)))
            p.emit('position',bytes((1,actor))+struct.pack('<hh',x,y))
            p.emit('facing',bytes((0x11,actor,{180:250,90:249,270:248}[facing])))
            p.emit('chore',bytes((0x11,actor,frame)))
            if absent_animation_probe:
                # Undefined source records must preserve each actor's live
                # chore, including one not yet sampled by presentation.
                p.emit('absent animation preserves live cels',bytes((0x11,actor,63)))
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
    p.move(0x4001,6 if transitions else len(stages)+1);p.emit('stop',b'\0')
    container=bytearray(ch(b'ROOM',room));script=len(container);container+=ch(b'SCRP',bytes(p.data))
    scripts = [0, script]
    if cutscene_callback_probe:
        scripts.append(len(container))
        # Each callback executes through the ordinary nested global resolver.
        # Increment a count and copy the inherited local0 argument.
        container += ch(b'SCRP', bytes.fromhex('4696009a97000040a0'))
    if room_hook_probe:
        for body in (
            copy(156,4)+write(150,1)+b'\0',
            copy(152,150)+write(150,3)+b'\0',
            copy(153,150)+write(150,4)+b'\0',
            copy(157,150)+write(150,6)+b'\0',
        ):
            scripts.append(len(container));container+=ch(b'SCRP',body)
    costs=[]
    for actor in (1,2):
        raw=bytearray(costume(one_shot_limb=one_shot_limb_probe))
        if actor==2:raw[3:6]=bytes((0,120,200))
        costs.append(len(container));container+=ch(b'COST',raw)
    if transitions:
        first=ch(b'LFLF',container);second=ch(b'LFLF',ch(b'ROOM',room))
        loff=bytes((2,1))+struct.pack('<I',35)+bytes((2,))+struct.pack('<I',35+len(first))
        data=ch(b'LECF',ch(b'LOFF',loff)+first+second)
    else:
        data=ch(b'LECF',ch(b'LOFF',bytes((1,1))+struct.pack('<I',30))+ch(b'LFLF',container))
    object_count=1024 if hit_test_probe else 256
    initial_classes=[0]*object_count
    if hit_test_probe:
        initial_classes[:1000]=[0x80000000]*1000
        initial_classes[900]=0x80000001
    dobj=struct.pack('<H',object_count)+bytes(object_count)+b''.join(struct.pack('<I',mask) for mask in initial_classes)
    index=(ch(b'DOBJ',dobj)
           +ch(b'DSCR',directory(bytes((0,)+(1,)*(len(scripts)-1)),scripts))
           +ch(b'DCOS',directory(bytes((0,1,1)),(0,*costs)))+ch(b'DSOU',directory(b'',[])))
    return {f'ATLANTIS/ATLANTIS.{n:03}':bytes(b^0x69 for b in raw) for n,raw in enumerate((index,data))}

def write_archive(path: Path, *, masks: bool = False, transitions: bool = False,
                  sound_status_probe: bool = False, cutscene_callback_probe: bool = False, room_hook_probe: bool = False,
                  object_images_probe: bool = False, absent_animation_probe: bool = False, walkbox_mask_probe: bool = False, one_shot_limb_probe: bool = False, hit_test_probe: bool = False) -> None:
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as archive:
        for name,data in source_files(masks=masks,transitions=transitions,
                                      sound_status_probe=sound_status_probe, cutscene_callback_probe=cutscene_callback_probe, room_hook_probe=room_hook_probe,
                                      object_images_probe=object_images_probe, absent_animation_probe=absent_animation_probe, walkbox_mask_probe=walkbox_mask_probe, one_shot_limb_probe=one_shot_limb_probe, hit_test_probe=hit_test_probe).items():
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.external_attr=0o100644<<16
            archive.writestr(info,data)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--masks',action='store_true');parser.add_argument('--transitions',action='store_true')
    parser.add_argument('--sound-status-probe', action='store_true')
    parser.add_argument('--cutscene-callback-probe', action='store_true')
    parser.add_argument('--room-hook-probe', action='store_true')
    parser.add_argument('--object-images-probe', action='store_true')
    parser.add_argument('--absent-animation-probe', action='store_true')
    parser.add_argument('--walkbox-mask-probe', action='store_true')
    parser.add_argument('--one-shot-limb-probe', action='store_true')
    parser.add_argument('--hit-test-probe', action='store_true')
    args=parser.parse_args();write_archive(args.output,masks=args.masks,transitions=args.transitions,
                                         sound_status_probe=args.sound_status_probe, cutscene_callback_probe=args.cutscene_callback_probe, room_hook_probe=args.room_hook_probe,
                                         object_images_probe=args.object_images_probe, absent_animation_probe=args.absent_animation_probe, walkbox_mask_probe=args.walkbox_mask_probe, one_shot_limb_probe=args.one_shot_limb_probe, hit_test_probe=args.hit_test_probe)
