# Authentic Fate SCUMM v5 `$01 putActor` report

Status: **complete**. This slice implements only the canonical v5 `$01`
opcode family and advances authentic room-49 LSCR 200 to the next unsupported
semantic. M24R-B remains paused.

## Canonical contract

The local reference is ScummVM `engines/scumm/script_v5.cpp::o5_putActor` and
`engines/scumm/actor.cpp::Actor::putActor`. The opcode uses bits `$80/$40/$20`
for variable actor/X/Y operands. It calls `putActor(x, y, actor.room)`, so it
does not select or change the actor's room.

Placement always stores the requested position and marks the actor for redraw.
For an actor in the active room it applies the v5 BOXD adjustment, sets the
current and destination box, refreshes box/effective scale, invalidates the
walk destination X, stops movement, clears actor-costume sound progress, and
shows an invisible actor (including its bounded initial costume frame). A
visible actor assigned elsewhere is hidden and any active movement is stopped.
The v5 nearest-box scan also updates its last-valid coordinates. Fate does not
take the HE-only background-reset branch. No route search, actor walking,
rendering, camera behavior, or room mutation is part of this implementation.

The host keeps redraw as its existing aggregate actor-dirty state; the SNES
keeps an explicit actor redraw byte. The SNES also retains the normalized
position, current/destination box, invalid destination X, movement, visibility,
and last-valid coordinates. Immutable BOXD geometry is copied from generated
profile data; BOXM/pathfinding data is not consulted.

## Authentic actor 10

The hash-bound cooked ROOM record is
`2904015371af15b616711013298b8e95874e55c5e9c45216fe09bf9a544a025f`;
LSCR 200 is
`dc34f2d549455fbd6ee30eb057470b39e97e4544ff3cbe49d94424158e3cbc6c`.
The instruction maps as follows:

```text
original PLAYFATE.001 offset  $0588CD
original ROOM-relative       $00EDEE
original LSCR chunk-relative $014F (including the 9-byte chunk/id prefix)
cooked-record offset         $00F656
normalized/runtime offset    $0146

+$0146  01 0A 47 02 88 00
         putActor(actor 10, x=583, y=136)
         next PC +$014C
```

Immediately before it, actor 10 is in room 49, invisible at `(0,0)`, not
moving, with no valid destination, costume 45, facing 180, and scale 255.
Boxes 12 and 20 have already been changed to invisible by the accepted
matrixOps instructions. The canonical reverse nearest-box scan therefore
selects visible box 9 and normalizes the position:

```text
position              (0,0) -> (536,137)
room                  49 -> 49
visible               false -> true
moving                0 -> 0
walkbox               0 -> 9
destination box       $FF -> 9
destination X         0 -> -1
costume frame         uninitialized -> init frame 1
box scale             $00FF -> source scale $8001
effective scale       255 -> 255 (no initialized slot-2 override)
```

Host evidence is `build/m25-put-actor/host-report.json`. Fresh-power-on SNES
evidence is `build/m25-put-actor/evidence/report.json`; no debugger writes,
PC forcing, sliced script, or state mutation after execution begins is used.

## Copyright-free conformance

The dedicated SNES fixture executes all eight `$01/$21/$41/$61/$81/$A1/$C1/$E1`
forms through production lookup and dispatch. Its trace proves variable/direct
actor, X, and Y combinations, coordinates above 255, exact instruction
boundaries, replacement, and isolation across actors 1-8. Separate fresh ROMs
fail closed for actor 32 (`SCUMM_ERR_ARGUMENTS`) and a truncated Y operand
(`SCUMM_ERR_PC_RANGE`) without a placement mutation. The machine-readable
report is `build/m25-put-actor/conformance/report.json`.

## Next authentic blocker

After putActor, the already implemented `$11 animateActor(10,$F9)` executes.
The next unsupported instruction is:

```text
room.49 / LSCR.200 +$014F
07 4E 02 00
setState(object 590, state 0)
```

Surrounding bytes from `+$0141` are:

```text
D9 00 2D 0A 31 01 0A 47 02 88 00 11 0A F9 07 4E
02 00 5D 50 02 01 A0 00 FF 48 E0 00 3F 00 1A 00
```

This is an opcode implementation gap in object-state mutation; it is not
implemented or otherwise bypassed here.

## Validation and identities

- All 333 tests pass (330 accepted plus three new host conformance tests).
- Repository validation and full Poppy lint/source traps pass.
- The integrated SNES ROM assembles and passes the header/vector/overlap audit.
- Fresh-emulator authentic execution and three copyright-free SNES operand/
  failure fixtures pass.
- The four M25A nested-context emulator gates pass unchanged semantically.
- The accepted M23B positive/negative artifact pair still passes its fresh
  emulator control gate.

The production semantic and generated active-room geometry necessarily change
newly rebuilt integrated/validator identities. Historical accepted artifacts
are not rewritten. The final integrated Fate ROM SHA-256 is:

```text
e87d325dd9498d177e9e40fc5a1764d41380717c40ff5420ffb2e97207090578
```

Rebuilt M25A validator hashes are normal
`fc955f35390db49256273364241410b65907b896a999f8b20164efa9ebb43e46`,
depth `4c856e35caf4a372d01844ffb350d2d4e076d93602d688894ed91d4e2a83d7c4`,
missing `29523ead0c3f89f40d6f8b644273e563000c44fc6990681cb72cfc8ba46d67bc`,
and outer `3f1010df88a6ef18b1b82eeae614557c23086a4d12d8d8fe85b9cd327c42800f`.

No audio, iMUSE, TAD, instrument, rendering, movement, pathfinding, or matrix
construction behavior changed. No new timbre review is required.
