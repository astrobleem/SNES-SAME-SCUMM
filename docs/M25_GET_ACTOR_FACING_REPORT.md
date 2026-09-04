# M25 canonical SCUMM v5 `$63 getActorFacing`

Status: complete. M24R-B remains paused. No subsequent semantic blocker was
implemented.

## Canonical contract

The local authoritative oracle is ScummVM
`script_v5.cpp::o5_getActorFacing` plus `util.cpp::newDirToOldDir`. The opcode
reads a result-variable reference, reads a var/direct actor byte, converts the
actor's internal facing, and writes only the result. The ordered conversion is:

| internal angle | old direction |
|---|---:|
| 71 through 109 | 1 |
| 109 through 251 | 2 |
| 251 through 289 | 0 |
| otherwise | 3 |

The ordered predicates make the inclusive overlaps authoritative: 109 maps to
1 and 251 maps to 2. The handler does not rotate, turn, animate, move, redraw,
or otherwise mutate the actor.

The host registers `$63/$e3` and uses the existing result-variable and
var/direct operand machinery. The SNES implementation uses the same parameter
bits, a 32-entry u16 internal-facing table, and the same ordered comparisons.
Existing immediate-direction `animateActor` requests maintain that table; no
turning or animation engine was added.

## Focused conformance

Copyright-free host and fresh-emulator fixtures prove direct and variable
actor operands, multiple result targets, replacement, isolation, invalid actor
and truncated forms, exact PCs, and these boundaries:

```text
0→3, 70→3, 71→1, 90→1, 109→1, 110→2,
180→2, 250→2, 251→2, 270→0, 289→0,
290→3, 359→3
```

The direct queries advance four bytes. The variable-actor `$e3` fixture
advances five bytes. All 32 actor records and all facing entries are
byte-identical before and after the query-only fixture. Invalid and malformed
forms execute zero successful queries and fail closed.

Evidence: `build/m25-get-actor-facing/conformance-report.json`.

## Authentic Fate proof

Fresh power-on, with zero debugger writes, traverses authentic room 49 ENCD,
globals 144/145, the authentic single start-80/hook-14 flush, LSCR 200, both
matrix writes, actor setup, putActor, setState, and the normal immediate nested
start of authentic LSCR 201 before decoding:

```text
room.49/LSCR.201 +$0000: 63 00 00 0A
result variable 0, direct actor 10
PC $0000 -> $0004
```

Actor 10's actual internal facing is 90 degrees at the query. The conversion
is 1. Var[0] is 0 before the first query, receives 1, and the authentic second
query at `+$000B` observes 1 before replacing it with the same result. Both
query traces read 90 and return 1. The complete host actor record is identical
before and after each query; the SNES copyright-free gate independently hashes
all actor records before and after and proves no mutation.

The authentic nested path also exposed a pre-existing M25A index-width defect:
the far context helper transferred an 8-bit slot into 16-bit X without clearing
the accumulator's hidden high byte. That could select LSCR 208 instead of the
newly allocated LSCR 201 slot. Slot conversion and program-store indexing now
zero-extend explicitly. This is a generic scheduler correction, not a Fate or
script-201 exception. The established 24-level bounded context model is
unchanged.

The integrated pre-Thera boot also now clears the complete sparse class table
before seeding its source-bound object-595 class record. Previously it marked
one record initialized over unspecified cold WRAM, allowing later canonical
`setClass` calls to see phantom occupied records. This is deterministic state
initialization for the already-implemented class subsystem, not new class or
Fate-specific opcode behavior.

Evidence: `build/m25-get-actor-facing/host-report.json` and
`build/m25-get-actor-facing/authentic-report.json`.

## Next authentic blocker (not implemented)

The authoritative host's first post-query blocker occurs after LSCR 201's
legitimate first `breakHere`, when the engine performs its normal visible-actor
presentation lifecycle:

```text
room.49/LSCR.201 +$0029
f9 18 03 00 11 0a f8 80 80 1a 00 40 00 00 1d 52
```

`+$0028` is the already-supported `$80 breakHere`; the child remains runnable
at `+$0029`. Presentation then fails because visible actor 10 uses authentic
costume 45 and no `costume.45` resource is available through the current room
profile. This is a costume-resource/presentation subsystem dependency, not an
opcode decode gap. Source mapping for `+$0029` is original file `$58985`, ROOM
relative `$EEA6`, chunk relative `$0032`, cooked record `$F70E`.

The SNES has no actor-render lifecycle, so it advances beyond that authoritative
host stop and later fails closed at the separate, already-known `$14 print`
gap:

```text
room.49/LSCR.200 +$01A8: 14 01 0f 57 65 6c 6c 2c ...
```

That later SNES-only stopping point was recorded but not implemented. The next
honest core milestone should decide the bounded costume-45 delivery/presentation
closure before using the later `$14` as the path frontier.

## Validation and identity

- Unit suite: 337 tests (335 prior plus two focused host cases).
- Copyright-free SNES direct/variable/boundary/error gate: pass.
- Fresh-power-on authentic Fate gate: pass.
- Repository validation and Poppy lint: pass (29 files, 2,261 integrated
  global labels).
- SNES assembly and LoROM header/vector audit: pass.
- Integrated ROM: `build/m25-get-actor-facing/fate.sfc`.
- SHA-256: `aae7a5e1ab8e249e356509c86523a7f2be287528ba7fe44529bb67e32e49b9ea`.

No audio, TAD, iMUSE, actor rendering, walking, pathfinding, or subsequent
opcode behavior was added. No new timbre review is required.
