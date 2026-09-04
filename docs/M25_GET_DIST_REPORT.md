# M25 canonical SCUMM v5 `$F4 getDist`

## Result

Canonical SCUMM v5 `getDist` now runs in the host model and production SNES
interpreter for all four v5 parameter-mode variants (`$34/$74/$B4/$F4`).  A
fresh-power authentic room-49 run executes global script 2 `+$038E`, writes
the canonical distance zero to `Var[0]`, and advances exactly to `+$0395`.

The milestone stops at the next unsupported script-visible operation:
global script 2 `+$0458`, `$F7 startObject`.  Object-program execution,
LSCR 211, `loadRoomWithEgo`, room 63, and later gameplay were not added.

## Authoritative contract

The local ScummVM reference is:

- `engines/scumm/script_v5.cpp`, `ScummEngine_v5::o5_getDist`;
- `engines/scumm/object.cpp`, `ScummEngine::getObjActToObjActDist`.

The opcode obtains its result destination, decodes two v5 word operands,
resolves each as an actor or object, and stores the helper result.  Actor IDs
are values below the v5 actor count (13 for this profile).  Current-room actor
positions are usable; room objects use canonical object walk positions;
inventory-owned objects may resolve through their owning current-room actor.
An unresolvable operand yields `$00FF`.

When the first operand is an actor and the second is a non-actor object, the
second position is projected through the actor's `adjustXYToBeInBox` query.
The reverse ordering does not project.  The metric is Chebyshev distance:

```text
max(abs(x1 - x2), abs(y1 - y2))
```

The query does not mutate actor, object, movement, room, scheduler, or route
state.

## Authentic operands and execution

The hash-bound instruction is:

```text
global script 2 +$038E
F4 00 00 03 40 04 40
```

It consumes seven bytes and advances `+$038E -> +$0395`.  The two encoded
references are `$4003` and `$4004`: the operative values are `Local[3]` and
`Local[4]`, not the original sentence inputs in `Local[0]` and `Local[1]`.
Immediately before the instruction the slot locals are:

```text
[10, 596, 0, 1, 596, 0]
```

The sentence inputs remain intact in locals 0 through 2; the authentic script
prelude has established actor 1 and object 596 in locals 3 and 4.

| Item | Authentic value |
|---|---|
| Result target | `Var[0]` |
| `Var[0]` before | 15 (the preceding owner query result) |
| Operand 1 | actor 1, room 49, `(57,46)` |
| Operand 2 | object 596, owner 15/room, raw walk point `(58,43)` |
| Actor-to-object projection | applies |
| Projected operand 2 | `(57,46)` |
| `dx`, `dy` | 0, 0 |
| Result / `Var[0]` after | 0 |

The complete actor record is byte-identical before and after the query.  The
authentic 91-tick walk and scheduler-pass-92 wait release remain unchanged.
The gate uses fresh power and performs zero debugger writes.

## Implementation and conformance

The host implementation shares existing actor, object-owner, object walk-point,
room, and walkbox projection state.  The SNES cold handler lives in the
existing far SCUMM helper bank, validates operand bounds before reading,
resolves actor/room-object/inventory-owner positions, applies only the
canonical asymmetric projection, and writes through the existing result
variable machinery.

Directly changed implementation/evidence files are:

- `src/same/engines/scumm_v5/engine.py`: host opcode family and canonical
  actor/object distance helper;
- `runtime/snes/engines/scumm_v5_matrix_far.pasm`: bounded far-bank production
  decoder/resolver/metric handler;
- `runtime/snes/kernel/memory.pasm`: bounded query evidence/scratch record;
- `tests/test_scumm_v5_engine.py`: host semantic conformance;
- `tools/build_m25a_validator_room.py`: copyright-free SNES programs;
- `tools/validate_scumm_get_dist_nexen.py`: valid/malformed SNES gate;
- `tools/validate_scumm_m25_sentence_movement_nexen.py`: authentic trace and
  next-blocker assertions.

Copyright-free host and SNES fixtures cover:

- actor/actor, actor/object, object/actor, and object/object queries;
- zero, horizontal, vertical, and diagonal Chebyshev distances;
- asymmetric actor-to-object projection where raw and adjusted points differ;
- direct/direct, variable/direct, direct/variable, and variable/variable forms;
- inventory-owner position resolution and both unresolved-operand cases;
- result replacement, exact instruction lengths, malformed/truncated input,
  and complete actor-state purity.

The dedicated SNES valid fixture executes eight queries and records:

```text
[5, 0, 7, 8, 0, 7, 255, 255]
```

The malformed fixture fails closed before executing a query.  Evidence is in:

- `build/m25-getdist-conformance.json`;
- `build/m25-getdist-authentic.json`;
- `build/m25-getdist-validator-valid.sfc`;
- `build/m25-getdist-validator-malformed.sfc`;
- `build/m25-getdist.sfc`.

ROM identities:

```text
valid conformance:     ba8f58d74578261a411d37bfe21fbfa657741fc4a16ab50f08c005fa76fea2c5
malformed conformance: 094a2ab9866ef92630487d2ddc926a00fc80fb6d46a01f2401ab688eadaf21e5
authentic production:  32ed15b18a096b4c966d72c4f7c8c5b0ae518f171f770775f26a948a09a7f41b
```

## Next authentic blocker

```text
global script 2 +$0448
06 40 2E 14 00 00 91 01 00 03 C0 9A 07 00 01 40
F7 01 40 00 40 81 02 40 81 00 40 FF
```

At `+$0458`, canonical `$F7 startObject` resolves object 596 from `Local[1]`,
verb 10 from `Local[0]`, and a word-vararg list.  The production interpreter
fails closed with `SCUMM_ERR_UNSUPPORTED` before object-program allocation or
execution.  This is an opcode/resource-execution gap, not a distance,
movement, or scheduler defect.

## Validation

- 352 repository tests: pass.  The initial combined run exposed only six
  missing explicit accumulator-width declarations at far-bank branch targets;
  the corrected static Poppy test passes independently without semantic code
  changes.
- Target/profile repository validation: pass.  Printed rejected-profile and
  unregistered-demo-engine messages are the existing expected negative cases.
- Poppy source/control-flow lint and source traps: pass.
- Production and both conformance ROMs assemble and pass the LoROM audit;
  reset `$8000`, NMI `$8062`, IRQ `$8084`.
- Fresh-power authentic and copyright-free emulator gates: pass with zero
  debugger writes.
- A second clean production assembly is byte-identical to the reported ROM.

M24R-B remains paused.  Costume 45 and text-glyph presentation remain separate
documented limitations.  No new timbre approval is required.
