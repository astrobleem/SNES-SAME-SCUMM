"""Original SCUMM-v5 actor diagnostic bytecode; no new 65816 code required.

This is a synthetic driver, never an authentic-game or gameplay acceptance.
L0 is the observer acknowledgement; L1 is the stage. Both are script locals.
Provided under the Unlicense/public-domain dedication.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct

ACK = 0x4000
STAGE = 0x4001


@dataclass(frozen=True)
class ProbeConfig:
    room: int
    costume: int
    actor: int = 1
    x: int = 160
    y: int = 136
    moved_x: int = 184
    stand_frame: int = 3
    animate_frame: int = 2
    boot_script: int = 1

    def validate(self) -> None:
        for name in ('room', 'costume', 'boot_script'):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 255:
                raise ValueError(f'{name} must be an integer in 1..255')
        if type(self.actor) is not int or not 1 <= self.actor <= 31:
            raise ValueError('actor must be an integer in 1..31')
        for name in ('x', 'y', 'moved_x'):
            value = getattr(self, name)
            if type(value) is not int or not -32768 <= value <= 32767:
                raise ValueError(f'{name} must fit a signed SCUMM word')
        for name in ('stand_frame', 'animate_frame'):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value < 244:
                raise ValueError(f'{name} must be a raw frame, not a special animateActor request')


class Program:
    def __init__(self) -> None:
        self.data = bytearray()
        self.instructions: list[dict] = []
        self.stage_records: list[dict] = []

    def emit(self, label: str, raw: bytes) -> int:
        pc = len(self.data)
        self.data.extend(raw)
        self.instructions.append({'pc': pc, 'length': len(raw), 'operation': label, 'hex': raw.hex()})
        return pc

    def move(self, variable: int, value: int) -> None:
        self.emit(f'move var:{variable:04x}={value}', b'\x1a' + struct.pack('<HH', variable, value))

    def wait_ack(self, stage: int, name: str) -> None:
        self.move(STAGE, stage)
        target = self.emit('breakHere', b'\x80')
        pc = len(self.data)
        # isEqual jumps on FALSE. The seven-byte comparison branches back
        # to breakHere, preventing an unbounded same-tick spin.
        self.emit(f'isEqual local0,{stage}; false -> {target}',
                  b'\x48' + struct.pack('<HHh', ACK, stage, target - (pc + 7)))
        self.stage_records.append({'stage': stage, 'name': name, 'wait_pc': target,
                                   'ack_local': 0, 'stage_local': 1})


def build_probe(config: ProbeConfig) -> tuple[bytes, dict]:
    config.validate()
    p = Program()
    a = config.actor
    p.move(ACK, 0)
    p.move(STAGE, 0)
    p.emit('loadRoom diagnostic backdrop', bytes((0x72, config.room)))
    p.emit('actorOps defaults/costume/scale/ignoreBoxes/speed',
           bytes((0x13, a, 0x08, 0x01, config.costume,
                  0x11, 0xff, 0xff, 0x14, 0x16, 8, 0xff)))
    p.emit('putActorInRoom', bytes((0x2d, a, config.room)))
    p.emit('putActor initial position', bytes((0x01, a)) + struct.pack('<hh', config.x, config.y))
    p.emit('animateActor facing 180', bytes((0x11, a, 250)))
    p.emit('animateActor standing frame', bytes((0x11, a, config.stand_frame)))
    p.wait_ack(1, 'standing')
    p.emit('animateActor facing 90', bytes((0x11, a, 249)))
    p.emit('animateActor standing frame', bytes((0x11, a, config.stand_frame)))
    p.wait_ack(2, 'turned')
    p.emit('animateActor animated frame', bytes((0x11, a, config.animate_frame)))
    p.wait_ack(3, 'animated-in-place')
    p.emit('putActor moved position', bytes((0x01, a)) + struct.pack('<hh', config.moved_x, config.y))
    p.emit('animateActor standing frame', bytes((0x11, a, config.stand_frame)))
    p.wait_ack(4, 'moved-background-restored')
    p.move(STAGE, 5)
    target = p.emit('breakHere final', b'\x80')
    pc = len(p.data)
    p.emit('jumpRelative final wait', b'\x18' + struct.pack('<h', target - (pc + 3)))
    body = bytes(p.data)
    report = {'schema': 'same-actor-proof-program-v1', 'kind': 'SYNTHETIC_GRAPHICS_DIAGNOSTIC',
              'production_release_eligible': False, 'config': config.__dict__,
              'length': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
              'stage_records': p.stage_records, 'instructions': p.instructions,
              'instruction_spans': [[r['pc'], r['length']] for r in p.instructions],
              'completed_stage': 5}
    return body, report


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--room', type=int, required=True)
    ap.add_argument('--costume', type=int, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--boot-script', type=int, default=1)
    ap.add_argument('--x', type=int, default=160)
    ap.add_argument('--y', type=int, default=136)
    args = ap.parse_args()
    if args.output.exists():
        ap.error('output must be a new directory')
    body, report = build_probe(ProbeConfig(args.room, args.costume, boot_script=args.boot_script,
                                           x=args.x, y=args.y, moved_x=args.x + 24))
    args.output.mkdir(parents=True)
    (args.output / 'actor-proof.scrp').write_bytes(body)
    (args.output / 'actor-proof.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'bytes': len(body), 'sha256': report['sha256'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
