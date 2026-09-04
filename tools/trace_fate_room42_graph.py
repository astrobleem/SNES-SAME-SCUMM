#!/usr/bin/env python3
"""Print source-backed room-42 effect metadata and candidate writers."""
from pathlib import Path
import sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room import decode_room

archive = ROOT / "ATLANTIS.zip"
profile = load_profile(ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json", verify_resources=False)
with zipfile.ZipFile(archive) as z:
    names = [n for n in z.namelist() if n.upper().endswith((".000", ".001"))]
    raw = {"game.index": z.read(next(n for n in names if n.upper().endswith(".000"))),
           "game.data": z.read(next(n for n in names if n.upper().endswith(".001")))}
p = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw), parse_game_policy(profile))
print("objects", len(p.global_objects.owners), "scripts", p.global_script_count)
for oid in (489,490,491,492,493,496,497,500,591,592,593,594,595,596,1014):
    print("DOBJ", oid, "owner", p.global_objects.owners[oid], "state", p.global_objects.states[oid],
          "class", f"0x{p.global_objects.classes[oid]:08x}")
r = decode_room(p.read("room.42"), key="room.42")
for o in r.objects:
    if o.object_id in (489,490,491,492,493,496,497,500):
        print("OBJ", o.object_id, "xywh", (o.x,o.y,o.width,o.height), "walk", (o.walk_x,o.walk_y),
              "flags", hex(o.flags), "parent", o.parent, "verbs", o.verb_entries,
              "obcd", len(o.obcd), "table", o.verb_table_offset, o.verb_table_length)
        print("  bytes", o.obcd.hex())

needles = {oid.to_bytes(2, "little") for oid in (489,490,491,492,493,496,497,500,591,592,593,594,595,596,1014)}
for n in sorted(k for k in p.keys() if k.startswith("script.")):
    data = p.read(n)
    hits = [i for i in range(len(data)-1) if data[i:i+2] in needles]
    if hits:
        print("SCRIPT", n, "len", len(data))
        for i in hits:
            print(" ", f"0x{i:04x}", data[max(0,i-12):i+20].hex())
