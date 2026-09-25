# Authentic Fate room-49 one-blocker report

Status: **complete**. This slice clears exactly one authentic semantic blocker: loss of the
outer interpreter context after the long nested global-script call. It does not implement
`$30 matrixOps` or any later SCUMM, actor, walkbox, movement, or audio behavior.

## Phase A — first actual blocker

The current script at the divergence was authentic room-49 `ENCD`, suspended immediately
after `+$0019 $0A startScript 144` at resume PC `+$0022`. Global script 144 executes from PC
zero and at `+$0030` starts global script 145; its `startScript` completes at `+$0039` after
145's authentic loop. Script 145 executes 1,243 traced operations before stopping at
`+$0081 $A0`. Script 144 then stops at `+$003C $A0`.

The accepted host oracle restores room-49 ENCD program `$D1`, slot 0, PC `+$0022`, and outer
return mode zero. Before this repair, fresh SNES execution retained those values in slot 0
but restored live `SAME_SCUMM_PROGRAM_SELECT` as `$00`. It consequently decoded unrelated
fixture bytecode instead of authentic ENCD. This was a missing interpreter-context field,
not an opcode, actor, inventory, class, matrix, walkbox, or earlier-game-state dependency.

The surrounding authentic branch results are unchanged from M23B:

| Script/offset | Result |
|---|---|
| ENCD `+$0022 $48` | indexed bit 418 is clear; branch bypasses local script 213 and reaches `+$002E` |
| ENCD `+$002E $28` | bit 425 is set; the irrelevant clear-bit path is skipped |
| ENCD `+$003D $7C` / `+$0041 $28` | sound 81 is stopped; execution continues |
| ENCD `+$0046 $7C` / `+$004A $28` | sound 80 is stopped; execution reaches the music block |
| ENCD `+$004F`, `+$0057`, `+$0065` | queue start 80, queue hook 14, then perform one authentic flush |

The source-bound host trace is `build/m23b-host-report.json`; the fresh SNES evidence is
`build/m25-authentic/evidence-final/report.json`.

## Phase B — narrow correction

`ScummV5_M23B_RunNestedChild` and its accepted far-bank equivalent now preserve all live
selection state needed by this path:

* the existing three-byte frame packs parent slot and exact outer/slot return mode;
* a parallel 24-byte array stores the exact parent program identity;
* PC, delay, status, locals, flags, room generation, and ownership continue to come from the
  authoritative scheduler slot;
* restoration occurs before child carry/error propagation.

The bound remains 24 suspended parents. No new recursion system or interpreter exists, and
overflow still fails through the existing capacity error. The implementation contains no
Fate, room 49, script 144/145, sound 80, hook 14, or source-offset constants.

The production changes are in:

* `runtime/snes/engines/scumm_v5.pasm` — near context save/restore;
* `runtime/snes/engines/scumm_v5_m24rb_far.pasm` — identical far context save/restore;
* `runtime/snes/kernel/memory.pasm` — bounded 24-byte program stack;
* `tools/validate_scumm_m25_authentic_next_nexen.py` — read-only fresh-emulator oracle.

Copyright-free host and SNES nested-script fixtures prove exact outer return mode, exact
parent resume PC, independent locals, immediate child execution, yielded-child rescheduling,
24-level bounds, and fail-closed lookup. The authentic run is the regression that exercises
the long 144 -> 145 call which originally exposed the missing program identity.

## Fresh-emulator result and next blocker

After the correction, the fresh emulator observes global 145 as program `$E5` at nesting
depth 2, then restores authentic ENCD program `$D1`, slot 0, return mode 0. ENCD executes
through `+$0065`; logical sound 80 is owned on hook route 14 without a debugger write or PC
override. It subsequently reaches `+$007A $0A startScript 200` through the normal generated
room-local resolver.

Authentic LSCR 200 is program `$D2`. Its first instruction is now the next fail-closed
semantic blocker:

```text
room.49/LSCR.200 +$0000: 30 01 0C 80
opcode $30 matrixOps, canonical setBoxFlags(12, 128)
```

**Erratum (2026-08-27):** the earlier `30 04 0C 80` presentation was a
diagnostic transcription error. The hash-bound authentic bytes are
`30 01 0C 80`; canonical subopcode `$01` is `setBoxFlags`. The prior emulator
run fetched only opcode `$30`, advanced to PC `+$0001`, and failed closed. It
did not fetch or decode the subopcode or either operand. The corrected validator
now derives and verifies the eight-byte `$30/$01` prefix from the authentic
cooked LSCR instead of trusting hand-entered operand metadata.

The child slot stops at PC `+$0001` with `SCUMM_ERR_OPCODE`; the error is propagated only
after ENCD context is restored. Matrix state was not fabricated and `$30` was not implemented
in this slice.

## Validation

* 328 unit tests pass.
* Repository validation and Poppy lint/source traps pass.
* All four M25A dedicated validator ROMs pass in fresh emulator processes.
* The authentic room-49 proof passes from cold power with zero debugger writes.
* SNES assembly and ROM audit pass.

Final integrated authentic ROM SHA-256:

```text
46b3f3f33c38b8dd3ba6f46e1f82d96609eb74a1c16c55b199b453349bc4ac63
```

The context correction necessarily changes the accepted M23B positive/negative builds; their
normal emulator gate passes with hashes
`314e63391a3cc024112432296e73f5e4f0bc9b475551f20d1e69a81bc915b516` and
`b2372da3513a19cf821e9b77949798c102549e528a904ae43dff8f110ff399b6`.

M24R-B remains incomplete. No new timbre approval is required.
