# M25 production SCUMM frame-loop/lifecycle ownership

## Result

The production SNES lifecycle now returns cleanly from a blocked `$AE
waitForActor`, completes the current scheduler pass, advances actor movement
once, returns to the SNES frame owner, and begins the next SCUMM scheduler
pass when due.  The authentic room-49 walk reaches `(57,46)`, box 1, facing
270 degrees on movement tick 91.

The milestone stops at the next real semantic blocker rather than widening
scope: global script 2 `+$038E` is `$F4 getDist`, which is not implemented by
the production SNES interpreter.  Consequently this report does **not** claim
that script 2 reached `+$0458 startObject`.

## One-shot divergence

The outer SNES loop was already persistent.  The broken ownership edge was
inside the SCUMM interpreter:

```text
Same_Main_Loop
  -> WAI
  -> Same_Frame_Run
       -> Same_Input_Poll
       -> Same_Engine_Frame
            -> Same_ActiveEngine_Frame
                 -> ScummV5_Engine_Frame
                      -> ScummV5_C4_Scheduler_Frame
                           -> script 2 $AE waitForActor
                           -> historical cold far tail dispatch (wrong owner)
       -> event drain
       -> audio process
```

The `$AE` cold handler transferred control as though it owned the whole
interpreter tail.  A yielded production slot therefore did not return through
the normal scheduler/save-slot/frame-completion path.  `$AE` itself evaluated
the correct condition; its cross-bank return ABI was the defect.

The corrected edge is a proper far-call ABI:

```text
$AE decode/check
  -> blocked: restore instruction PC, mark yielded, RTL
  -> scheduler saves the existing slot/program/locals
  -> scheduler completes its once-per-pass scan
  -> sentence processing
  -> one actor update
  -> talk frame-end update
  -> return to Same_Frame_Run
  -> event/audio service phases
  -> next SNES frame / next eligible SCUMM pass
```

No scheduler-until-idle loop was added.

## Phase contract

The local authoritative host model runs these relevant phases:

```text
talk frame-begin publication
script scheduler pass (clear did-exec, canonical slot scan)
sentence dequeue/launch
queued iMUSE frame-end processing
host audio lifecycle
actor movement
optional presentation/costume update
talk countdown/frame-end completion
```

The supported SNES production path is:

```text
input poll
talk frame-begin publication
room/resource lifecycle normalization
canonical scheduler pass
sentence dequeue/launch
one actor movement update
talk countdown/frame-end completion
return to kernel
event drain
SAME audio processing
```

Room changes remain script/lifecycle operations inside the engine phase.
Movement and talk both derive from this one production lifecycle; neither is
advanced by a query, wait opcode, validator loop, renderer, or audio callback.

## Directly involved repairs

Running the formerly stranded frame exposed three 65816 implementation defects
in the already-authorized bounded walker.  These were corrected without
changing its route policy:

1. Actor IDs loaded into a 16-bit X register now clear the hidden high byte.
2. Position records use their four-byte actor stride; movement-vector arrays
   retain their independent two-byte stride.
3. The movement-only multiply/divide far-call wrappers normalize M/X width on
   return, and diagonal factor calculation reconstructs source deltas after
   math scratch is consumed.

These defects explained the earlier false idle, stationary active leg, and
incorrect diagonal duration.  No Fate coordinates, box sequence, or tick table
was added to generic code.

## Authentic fresh-power evidence

The only semantic input was `doSentence(10,596,0)` at the production sentence
boundary.  The run proved the accepted prelude (`VAR_SENTENCE_SCRIPT=2`, VERB
entry `$0029`, owner 15, class 8/10 absent), then `$F6`, `$AE`, and the
production frame lifecycle.

Normalized stored-walkbox observations were:

| Tick | Box |
|---:|---:|
| 1 | 10 |
| 13 | 15 |
| 26 | 8 |
| 31 | 6 |
| 38 | 5 |
| 42 | 22 |
| 52 | 4 |
| 63 | 14 |
| 69 | 3 |
| 85 | 2 |
| 90 | 1 |

BOXM box 7 is consumed transiently during tick 31 and is never published as a
separate logical-tick result.  Movement completes on tick 91 at `(57,46)`, box
1, moving zero, facing 270 degrees.  There were 91 blocked wait evaluations;
the following scheduler pass advances beyond `+$0372` before encountering the
next unsupported instruction.

Evidence:

- `build/m25-production-frame-loop.json`
- `build/m25-production-frame-loop.sfc`
- ROM SHA-256: `468fca312e9e9afe6f667652fa944bcb5fe3aec495424d62120113036ca99761`
- debugger writes: zero

The historical blocker evidence remains unchanged:

- `build/m25-sentence-movement-blocker.json`
- validator ROM SHA-256:
  `8eaa2eb0307ddc87b5a5c9aac0513930bb962c8a90fc5fc02035d81b8b1a1cd1`

## Validation

- 350 repository tests: pass.
- Repository validation: pass (the emitted rejected-profile lines are the
  expected fail-closed CLI controls).
- Poppy source/control-flow lint: pass for both the production movement build
  and the regenerated default build.
- SNES assembly and LoROM audit: pass; reset `$8000`, NMI `$8062`, IRQ `$8084`.
- Fresh-power emulator production gate: pass with zero debugger writes.
- The regenerated production ROM is byte-identical to the reported candidate.

## Next blocker

```text
global script 2, SHA-256
09aa2fb2e9930723a9d0c9da0c94dcd64f6c62191633f4192318c594fea3d6dd

+$0380: 00 00 9D 04 40 01 8D 00 FF 03 00 18 37 00 F4 00
+$0390: 00 03 40 04 40 44 00 00 10 00 29 00 C9 03 40 04

+$038E: F4 00 00 03 40 04 40
$F4 getDist (result Var[0], operands Local[0], Local[1])
reached with Local[0]=10 and Local[1]=596
```

The opcode is unsupported by the production SNES dispatcher.  It was not
implemented in this lifecycle milestone.  `startObject`/OBCD execution,
LSCR 211, room 63, and later gameplay remain untouched.

Costume 45 and text glyph presentation remain separate documented
limitations.  M24R-B remains paused.  No new timbre approval is required.
