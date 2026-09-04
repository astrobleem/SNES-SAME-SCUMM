# Phase 6J — canonical `walkActorTo`

## Result

Phase 6J implements the complete v5 `$1E/$3E/$5E/$7E/$9E/$BE/$DE/$FE`
`walkActorTo` family.  The opcode decoder resolves its actor byte parameter and
signed word X/Y parameters, then enters the same normalized movement state used
by `walkActorToObject`, with final direction `-1`.  Movement remains owned by
the normal actor-update phase and the existing `waitForActor` implementation.

The authentic `9E 01 00 1C 00 26 00` at room 49 LSCR 211 `$02A0` resolves
`Var[1] = 1`, requests `(28,38)`, normalizes to `(31,38)` in walkbox 1, and
advances the parent PC to `$02A7`.  The following `AE 81 01 00` blocks for four
direct-walk evaluations, releases at `$02AB`, and execution continues to the
next genuine blocker.  No actor pixels, costumes, video changes, or later
semantic opcode were added.

## Opcode family and shared movement

| Opcode | Actor | X | Y |
|---:|---|---|---|
| `$1E` | direct byte | direct word | direct word |
| `$3E` | direct byte | direct word | variable word |
| `$5E` | direct byte | variable word | direct word |
| `$7E` | direct byte | variable word | variable word |
| `$9E` | variable reference | direct word | direct word |
| `$BE` | variable reference | direct word | variable word |
| `$DE` | variable reference | variable word | direct word |
| `$FE` | variable reference | variable word | variable word |

The masks are `$80` actor-variable, `$40` X-variable, and `$20` Y-variable.
Both coordinates retain their complete 16-bit bit patterns and use the existing
signed-coordinate convention.  Invalid actors fail before movement mutation.

The target entry calls `ScummV5_PutActor_Adjust_Far` and then
`ScummV5_Movement_StartNormalized_Far`.  `walkActorToObject` now calls that same
state installer, so there remains one route state, one BOXM path, one actor
update routine, and one wait implementation.  The accepted object-596 91-tick
route is unchanged.

## Authentic oracle and movement trace

Immediately before `$02A0`, actor 1 is in room 49 at `(57,46)`, walkbox 1,
facing 270, idle.  Camera and subtitle work have already reached their accepted
states.  `Var[1]` is 1 and dense globals 119/120/121 are
`$0000/$FFFF/$0000`.

The actor-specific v5 adjustment is important: `(28,38)` becomes `(31,38)` in
box 1.  The generic room-point helper would produce a different answer and is
not canonical here.  Start and destination are both in box 1, so the authentic
request does not consult a BOXM route.  Destination direction remains `$FF`
(`-1`), and no forced final turn occurs.

Host and target logical actor updates agree:

| Movement tick | X | Y | Box | Moving | Facing |
|---:|---:|---:|---:|---:|---:|
| initial | 57 | 46 | 1 | 0 | 270 |
| 1 | 50 | 44 | 1 | 10 | 270 |
| 2 | 44 | 42 | 1 | 10 | 270 |
| 3 | 37 | 40 | 1 | 10 | 270 |
| 4 | 31 | 38 | 1 | 0 | 270 |

The tight hardware-frame trace observes the first update across an NMI: frame
1078 sees the X store `(50,46)`, and frame 1079 sees the completed logical state
`(50,44)`.  This is one interruptible actor update, not an extra semantic tick.
Completed later logical states appear at frames 1082, 1085, and 1088.

The total authentic counters include the earlier object walk: blocks/releases
move from 91/1 to 95/2.  Thus this direct-coordinate wait blocks four times,
then releases once; LSCR 211 reaches its `$02AB` continuation without observing
video or DMA state.

## Following stream and blocker

The supported continuation is:

```text
02AB C0                         endCutscene
02AC 7C 00 00 52               isSoundRunning -> Var[0], sound $52
02B0 A8 00 00 29 00            conditional branch
02B5 4C 01 06 01 01 52 00 01 00 00 FF
02C0 4C 01 01 01 01 52 00 01 00 00 FF
02CB 4C 01 0D 01 01 52 00 01 32 00 01 78 00 FF
02D9 4C 01 FF FF FF
02DE 24 53 03 3F FF FF FF FF 62 00 18 0D 00 48 00 40 ...
```

The next blocker begins at `$02D9`, not `$02DD`: `$4C` `soundKludge([-1])`,
selector 1, word `$FFFF`, terminator `$FF`, continuation `$02DE`.  The target
reports audio/subsystem error 25.  Phase 6J deliberately does not implement the
flush semantic.

## Artifacts and validation

Two clean builds of each Phase 6J artifact are byte-identical:

| Variant | SHA-256 |
|---|---|
| LoROM + legacy | `dd01937a6e589419a36fe936152d486c90d25eac5e33addbb981682570b0388f` |
| SA-1 + legacy | `37db7be8e1384eca2a77c769e8fc943f8c51a4c3536dbc6f9428f7837d5466b5` |
| SA-1 + Mode-3/BG2 | `c49b721d5cc4ac88f1863ff248e994f2cafb88a866c18f1e6410c6d0c558e160` |

Fresh-emulator carrier validation agrees on actor selection, destination,
four-tick movement trace, wait closure, dense globals, and the `$02D9` blocker.
Both SA-1 runs retain reset architectural state with K:PC `00:0000`, no IRQ,
mailbox, DMA, or character conversion.

The Phase 6G-B masks remain exact:

- segment 1: `2237a3ae1c7c292e61908c9b65b0867620bea331bc4b751a79810b1ed2a8db74`
- segment 2: `27bfa2acbc93bdd6e84aab3e6a9ddc395bd9e5c237a9a0d9fdfc1c7d701c1984`

The dense table remains 800 words at `$7E0800-$7E0E3F`, and
Var[119/120/121] remain `$0000/$FFFF/$0000`.  The known `m25a-validator`
umbrella failure remains the pre-existing missing
`ScummV5_M23A_ValidateRecord_FarEntry` symbol; its underlying nested validators
remain independently runnable.

The complete Python suite passes 457 tests.  `make validate`, `make demo`, the
four SAME-VDP goldens, Poppy production lint, and `git diff --check` pass.  The
Phase 6I historical ROM still validates at its original `$02A0` blocker.  The
older sentence-movement validator confirms its original sentence prelude,
canonical transitions, 91-tick movement, wait closure, and `getDist`, then
fails only because it encodes the historical downstream startObject/object/
LSCR blocker trace rather than the now-extended Phase 6J trace; no historical
artifact or expected identity was rewritten.
