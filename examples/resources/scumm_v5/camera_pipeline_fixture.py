"""Original source-driven camera fixture; no commercial resource dependency.

Global 1 loads room 1, initializes variable 70 to 160, then repeatedly pans
with that variable and yields. Native tests may change this diagnostic command;
no renderer state, pixels, or canonical executable bindings are injected.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import struct
import zipfile
from examples.resources.scumm_v5.game_analysis_fixture import _chunk as ch, _directory as directory

COMMAND_VARIABLE = 70
WIDTH, HEIGHT = 640, 144

def _costume(*, color_count: int = 16) -> bytes:
    costume_format = 0x58 if color_count == 16 else 0x59
    animation_count = 6
    table = 2 + color_count
    data_offsets = table + 34
    record = data_offsets + (animation_count + 1) * 2
    commands = record + 5
    frame_table = commands + 1
    cel = frame_table + 2
    data = bytearray(cel + 12)
    data[0:2] = bytes((animation_count, costume_format))
    data[2 : 2 + color_count] = bytes(range(color_count))
    struct.pack_into("<H", data, table, commands + 6)
    struct.pack_into("<H", data, table + 2, frame_table + 6)
    struct.pack_into("<H", data, data_offsets + 6 * 2, record + 6)
    struct.pack_into("<HHB", data, record, 0x8000, 0, 0)
    data[commands] = 0
    struct.pack_into("<H", data, frame_table, cel + 6)
    struct.pack_into("<HHhhhh", data, cel, 2, 2, -1, -1, 0, 0)
    shift = 4 if color_count == 16 else 3
    data.extend(bytes(((color << shift) | 1) for color in (1, 2, 2, 1)))
    return bytes(data)


def source_files() -> dict[str, bytes]:
    w,h=640,144
    # Raw original synthetic strips, source decoder codec1. No external assets.
    strips=[bytes([1])+bytes(((x*13+y*37)^(x>>8))&255 for y in range(h) for x in range(col*8,col*8+8)) for col in range(w//8)]
    off=8+4*len(strips);offsets=[]
    for s in strips:offsets.append(off);off+=len(s)
    smap=ch(b'SMAP',b''.join(struct.pack('<I',v) for v in offsets)+b''.join(strips))
    rmim=ch(b'RMIM',ch(b'RMIH',b'\0\0')+ch(b'IM00',smap))
    room=ch(b'RMHD',struct.pack('<HHH',w,h,0))+ch(b'CLUT',bytes(v for c in range(256) for v in (c,c,c)))+rmim+ch(b'ENCD',b'\0')+ch(b'EXCD',b'\0')
    room+=ch(b'BOXD',struct.pack('<H',2)+struct.pack('<hhhhhhhhBBH',*([-32000]*8),0,0,255)+struct.pack('<hhhhhhhhBBH',0,0,w-1,0,w-1,h-1,0,h-1,0,0,255))+ch(b'BOXM',b'\0\0\0\xff\1\1\1\xff')
    # Load original fixture room; pan to a variable destination on each turn.
    # Variable70 is a synthetic diagnostic command, never commercial game state.
    boot=bytes([0x72,1,0x1a,70,0,160,0,0x92,70,0,0x80,0x18,0xf9,0xff])
    container=bytearray(ch(b'ROOM',room));script_off=len(container);container+=ch(b'SCRP',boot)
    costume_off=len(container);container+=ch(b'COST',_costume())
    loff=bytes([1,1])+struct.pack('<I',30)
    data=ch(b'LECF',ch(b'LOFF',loff)+ch(b'LFLF',container))
    index=ch(b'DOBJ',struct.pack('<H',256)+bytes(1280))+ch(b'DSCR',directory(bytes([0,1]),[0,script_off]))+ch(b'DCOS',directory(bytes([0,1]),[0,costume_off]))+ch(b'DSOU',directory(b'',[]))
    return {"ATLANTIS/ATLANTIS.000": bytes(v ^ 0x69 for v in index),
            "ATLANTIS/ATLANTIS.001": bytes(v ^ 0x69 for v in data)}


def write_archive(path: Path) -> None:
    # Names reuse the existing source-pair discovery contract, not game data.
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, data in source_files().items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    write_archive(parser.parse_args().output)
