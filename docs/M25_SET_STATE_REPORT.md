# M25 canonical SCUMM v5 `$07 setState`

Status: complete. M24R-B remains paused. No subsequent semantic blocker was implemented.

## Authoritative contract and authentic object

ScummVM's local v5 oracle (`script_v5.cpp::o5_setState`,
`object.cpp::putState`, and `object.cpp::markObjectRectAsDirty`) decodes a
var/direct object word and var/direct state byte, replaces the bounded global
u8 state, invalidates the loaded local object's rectangle, and clears the draw
queue when background redraw is pending.

The supplied Fate index `DOBJ` has 1,395 global objects. Object 590's packed
entry is `$0f`: initial state 0, owner 15 (`OF_OWNER_ROOM`), class mask
`$80000000`. Authentic cooked room 49 contains object 590 as local index 7:

| field | value |
|---|---:|
| position | `(312, 64)` |
| size / dirty rectangle | `96 x 64` |
| walk point | `(409, 107)` |
| CDHD flags / parent | `0 / 0` |
| pending draw entry before `$07` | none |
| background redraw before `$07` | false |

No local object was fabricated. The complete ROOM record and `DOBJ` source
remain user-supplied generated inputs; their payloads were not committed.

## Implementation

- Host `$07/$47/$87/$c7` uses the existing v5 parameter-mode readers and the
  game-declared global-object bound. Sparse test state retains canonical zero;
  authentic `DOBJ` supplies the bound and provenance.
- SNES uses a dense 4,096-byte state capacity with the active profile's
  generated declared count (1,395 for Fate). Active-room local descriptors are
  generated from every authentic cooked `OBCD/CDHD`, not a Fate/object-590
  special case.
- A loaded local hit records the real rectangle as dirty and sets background
  redraw. The existing logical draw-queue count is cleared. No object pixels,
  object script, ownership, class, resource, or immediate rendering behavior
  was added.
- Invalid object IDs and truncated operands fail closed. No other object opcode
  or matrix operation was implemented.

## Conformance

Copyright-free host and fresh-emulator fixtures cover direct/direct,
variable-object, variable-state, both-variable, object IDs above 255, states
0/1/255/`$80`, replacement, independent objects, malformed input, and invalid
IDs. The SNES trace proves these exact instruction boundaries:

| opcode | object | state | PC |
|---:|---:|---:|---:|
| `$07` | 590 | 0 | `0 -> 4` |
| `$47` | 590 | 1 | `9 -> 14` |
| `$87` | 591 | 255 | `19 -> 23` |
| `$c7` | 590 | 128 | `33 -> 38` |

Final independent states are object 590=`$80`, object 591=`$ff`; the last
local invalidation is `(8,8,24,8)`. Invalid and truncated records execute zero
mutations. Evidence: `build/m25-set-state/conformance-report.json`.

## Authentic Fate proof

Fresh power-on traverses authentic room 49 ENCD, globals 144/145, the authentic
single start-80/hook-14 flush, LSCR 200, both accepted matrix writes, actor
setup, and putActor before decoding:

```text
room.49/LSCR.200 +$014F: 07 4E 02 00
object 590, state 0
PC $014F -> $0153
```

Before/after global and local state are exactly 0. The handler records local
index 7, background redraw `false -> true`, dirty rectangle
`(312,64,96,64)`, and an empty draw queue after canonical clearing. Actor 10
remains at the previously accepted `(536,137)`, room 49, walkbox 9 state.
Evidence: `build/m25-set-state/host-report.json` and
`build/m25-set-state/evidence/report.json`.

## Next authentic blocker (not implemented)

The next newly encountered unsupported semantic is the immediately executed
room-local child:

```text
room.49/LSCR.201 +$0000
63 00 00 0A 08 00 00 F8 00 1F 00 63 00 00 0A 08
```

Canonical decode is `$63 getActorFacing`: result variable 0, direct actor 10,
next PC `$0004`. The full first 32 bytes are
`6300000a080000f8001f006300000a080000f900140016000001a80000060011`.
The generic actor record already carries facing, but the host opcode family is
absent; this is an opcode implementation gap rather than missing Fate state.
It was not implemented here.

## Validation and identity

- Unit suite: 335 tests (333 prior plus two focused host cases).
- Poppy lint/source audit: pass.
- SNES assembly and LoROM audit: pass.
- Fresh-power-on copyright-free and authentic emulator gates: pass.
- Integrated ROM: `build/m25-set-state/fate.sfc`
- SHA-256: `103297c1121e7f675561c98ba85e69dacd28f11650912d82fa7d3b2d6d034363`

The ROM identity changed only because shared production `$07` decoding,
global/local object-state storage, generated local-object descriptors, and
their evidence trace were added. No audio, TAD, iMUSE, actor rendering,
movement, pathfinding, or later blocker behavior changed.
