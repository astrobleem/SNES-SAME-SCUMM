"""Copyright-free, source-compiled raw-input callback native conformance.

First scene click runs room local 204, records its arguments and installs
Global 2. That global records the next click, starts Global 3 normally, yields,
and resumes. All bytecode passes through the normal compiler and checked cache.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import struct
import zipfile

from .camera_pipeline_fixture import source_files as camera_source_files, _costume
from .game_analysis_fixture import _chunk as ch, _directory as directory, _data_only_object


def move(result: int, value: int, *, local: bool = False) -> bytes:
    return bytes((0x9A if local else 0x1A,)) + struct.pack('<HH', result, value)


def source_files(*, nested_object_wait: bool = False) -> dict[str, bytes]:
    source = camera_source_files()
    data = bytes(v ^ 0x69 for v in source['ATLANTIS/ATLANTIS.001'])
    # Existing public camera fixture's first LFLF starts at offset 30.
    size = int.from_bytes(data[34:38], 'big')
    room = data[38:30 + size]
    room = room.replace(ch(b'RMHD', struct.pack('<HHH', 640, 144, 0)),
                        ch(b'RMHD', struct.pack('<HHH', 640, 144, 1)), 1)
    if nested_object_wait:
        header = struct.pack('<HBBBBBBhhB',77,1,1,1,1,0,0,40,20,0)
        action = (b'\x60\x01\x80\x60\x00' + move(114,42) + move(118,1)
                  + b'\x0a\x05\xff\x00')
        # Separate instruction-safe pages. The action later starts a child
        # that replaces its ancestor with a new entry in the SAME carrier.
        padding = b'\xa0' * 2100
        hover = move(116,1) + b'\x00'
        replace_ancestor = b'\x46\x75\x00\x00'
        at=18; entries=[]
        for verb,body in ((11,action+padding),(90,hover),(91,replace_ancestor)):
            entries.append(bytes((verb,))+struct.pack('<H',at));at+=len(body)
        table=b''.join(entries)+b'\x00'
        room += ch(b'OBCD',ch(b'CDHD',header)+ch(b'VERB',table+action+padding+hover+replace_ancestor))
    else:
        room += _data_only_object(77, 0)
    callback = (move(100, 0x4000, local=True) + move(101, 0x4001, local=True)
                + move(102, 0x4002, local=True) + b'\x46\x67\x00'
                + b'\x35\x6f\x00\x0c\x0c'
                + move(112, 52, local=True) + move(113, 53, local=True)
                + move(32, 2) + b'\x00')
    room += ch(b'LSCR', bytes((204,)) + callback)
    # No synthetic input injection: normal controller A/B edges are the driver.
    boot = (b'\x72\x01' + move(32, 204) + b'\x2c\x01\x2c\x03'
            + b'\x80\x18\xfc\xff')
    global2 = (move(104, 0x4000, local=True) + move(105, 0x4001, local=True)
               + move(106, 0x4002, local=True) + b'\x46\x6b\x00'
               + b'\x0a\x03\x00\x2a\x00\xff\x80\x46\x6c\x00\x00')
    global3 = move(109, 0x4000, local=True) + b'\x46\x6e\x00\x00'
    globals_ = [boot, global2, global3]
    if nested_object_wait:
        # Start a competing source hover loop, then synchronously start the
        # action on its same carrier. Parent must observe the action's write.
        nested = (b'\x0a\x04\xff\x37\x4d\x00\x0b\xff'
                  + move(115,114,local=True))
        globals_[1] = global2[:-1] + nested + b'\x00'
        globals_.append(b'\x37\x4d\x00\x5a\xff\x80\x18\xf7\xff')
        globals_.append(b'\x37\x4d\x00\x5b\xff\x00')
    container = bytearray(ch(b'ROOM', room)); offsets = [0]
    for body in globals_:
        offsets.append(len(container)); container += ch(b'SCRP', body)
    costume_offset = len(container); container += ch(b'COST', _costume())
    loff = bytes((1, 1)) + struct.pack('<I', 30)
    data = ch(b'LECF', ch(b'LOFF', loff) + ch(b'LFLF', container))
    index = (ch(b'DOBJ', struct.pack('<H', 256) + bytes(1280))
             + ch(b'DSCR', directory(bytes((0,))+bytes((1,))*len(globals_), offsets))
             + ch(b'DCOS', directory(bytes((0, 1)), (0, costume_offset)))
             + ch(b'DSOU', directory(b'', [])))
    return {f'ATLANTIS/ATLANTIS.{n:03}': bytes(v ^ 0x69 for v in payload)
            for n, payload in enumerate((index, data))}


def write_archive(path: Path, *, nested_object_wait: bool = False) -> None:
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_STORED) as archive:
        for name, data in source_files(nested_object_wait=nested_object_wait).items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--nested-object-wait', action='store_true')
    args=parser.parse_args()
    write_archive(args.output, nested_object_wait=args.nested_object_wait)
