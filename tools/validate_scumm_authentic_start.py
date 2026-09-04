#!/usr/bin/env python3
"""Probe the profile-owned Fate title start without synthetic room setup."""

from __future__ import annotations

import argparse
from pathlib import Path

from same.input import SnesButton
from validate_scumm_m23c_host import make_host


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    host, _ = make_host(args.archive, [args.manifest])
    engine = host.engine
    trace: list[dict[str, object]] = []
    for frame in range(601):
        host.tick(input_word=int(SnesButton.START) if frame == 600 else 0)
        if frame in (0, 523, 524, 600):
            trace.append({
                "frame": frame,
                "room": engine.state.current_room,
                "slots": [
                    {"number": slot.number, "pc": slot.pc, "active": slot.active,
                     "room": slot.room, "kind": slot.script_kind}
                    for slot in engine.state.scripts if slot.active
                ],
            })
    # Submit the already-decoded semantic action at SCUMM's public sentence
    # boundary.  This is the same queue consumed by the normal sentence
    # scheduler; it does not select or allocate any script.
    engine.queue_sentence(10, 596, 0)
    failure = None
    for _ in range(1200):
        try:
            host.tick()
        except Exception as exc:
            failure = str(exc)
            break
        if any(slot.active and slot.number == 208 for slot in engine.state.scripts):
            break
    if engine.state.current_room != 49:
        raise RuntimeError(f"title start did not reach room 49: {engine.state.current_room}")
    print({"result": "pass", "trace": trace,
           "sentence": {"verb": 10, "object1": 596, "object2": 0},
           "post_sentence_slots": [
               {"number": slot.number, "pc": slot.pc, "active": slot.active,
                "room": slot.room, "kind": slot.script_kind}
               for slot in engine.state.scripts if slot.active
           ],
           "failure": failure,
           "lifecycle": list(engine.inspect_room_lifecycle())[-8:]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
