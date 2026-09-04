# M25A report — canonical nested execution and SNES parity gate complete

Status: **complete**. The authoritative host oracle, copyright-free host fixture, complete
authentic resolver, four dedicated fresh-power-on SNES gates, ROM layout, 328-test unit
suite, repository validation, Poppy lint, assembly, and ROM audit pass. M25 and M24R-B remain
paused; neither was resumed by this closure work.

Post-acceptance correction: the later authentic room-49 run exposed one context field that
the short validator could not disturb. A long-running nested global script leaves
`SAME_SCUMM_PROGRAM_SELECT` live across many NMIs, so program identity cannot be reconstructed
only from the scheduler slot at unwind. The generic 24-frame context now also stores the
exact parent program in a parallel 24-byte array at `$7E:5420`; the parent slot byte packs the
outer/slot return mode in bit 7. The four dedicated validator ROMs (including the outer-frame
case) and the authentic ENCD -> global 144 -> global 145 unwind pass with this stronger
contract. This is the shared production correction documented by the subsequent one-blocker
report; it adds no opcode, room, actor, walkbox, matrix, or audio semantics.

No matrixOps, actor/object/facing, movement, walkbox, dialog, inventory, audio, TAD,
QuickTime, or MOV semantic was added.

## Canonical nested `startScript` semantics

The authoritative local implementation establishes the following contract:

1. `startScript` decodes the script number and complete argument list before allocation.
2. Non-recursive start first retires existing instances of the same number. Resolution then
   prefers a global resource and otherwise uses the current room's typed LSCR registry.
3. A free slot is reused from slots 1–24, or a new slot is appended while fewer than 25 slots
   exist. Locals are zero-initialized and arguments are copied to the child's first locals.
   Freeze-resistant and recursive bits come from opcode bits `$20` and `$40`.
4. During a scheduler tick, the new child is marked executed and runs immediately using the
   same interpreter. The parent is suspended after the fully consumed `startScript` stream.
5. `breakHere` is decoded normally, so the child PC already points after `$80`; it sets the
   child yielded without retiring it. The caller then resumes in the same engine frame at its
   post-`startScript` PC. The child remains runnable for the next scheduler pass.
6. A child error propagates after restoring the parent's execution context. Missing lookup or
   exhausted slot capacity leaves no partially initialized child. The parent PC nevertheless
   reflects the operands already decoded, matching the authoritative implementation.
7. A room transition retires all old room-owned slots before committing the new room registry.
   Thus a yielded local cannot execute against a new room lifecycle generation, including a
   re-entry into the same numeric room.

The direct evidence is
`src/same/engines/scumm_v5/engine.py::tick`, `_execute_slot`, `_op_break_here`,
`_allocate_script_slot`, `_op_start_script`, and `_load_room`. The fixed scheduler has 25
slots. Therefore one executing slot permits at most 24 suspended parents; overflow fails with
the existing slot-capacity error rather than introducing an independent recursion model.

For the authentic path this contract gives the required continuation:

```text
LSCR 200 +$0196 startScript 201
→ LSCR 201 +$0000 immediate entry
→ LSCR 201 +$0028 breakHere
→ child remains runnable at +$0029
→ LSCR 200 restored at +$0199
```

## SNES execution context

The existing 25-entry SNES slot table remains authoritative for PC, delay, status, locals,
freeze-resistant/recursive flags, and room ownership. M25A replaces the old
four-frame, ten-byte caller save area with a slot-bounded 24-frame stack. Each suspended frame
contains:

| Offset | Field | Width |
|---:|---|---:|
| `+0` | parent scheduler slot (bits 0-6) and return mode (bit 7) | 1 byte |
| `+1` | accumulated frame opcode count | 2 bytes |

The parallel program array stores one exact u8 program identity per suspended frame. This is
live interpreter state: it must survive a long child even if the common decoder selection is
changed before the parent unwinds.

The main stack occupies `$7F:F900–$7F:F947`; exact programs occupy `$7E:5420–$7E:5437`.
PC, delay, status, flags, locals, and room owner are restored from the live parent slot. The child uses the
existing interpreter; no second interpreter exists. Carry/error state is propagated only
after the parent slot and operation count are restored.

In the integrated M24R-B configuration, the cold suspend/run/restore helper is located at
`$09:8503–$09:860F`. Bank 0 retains a proper JSL/RTS wrapper and two JSR/RTL adapters for the
existing slot-save and interpreter helpers. All shared state accesses in far code are long;
no code pointer, bank-relative table, DBR-following access, cross-bank JSR/RTS, or truncated
target was introduced. The non-M24R-B M23B build retains the equivalent near helper.

## Complete local-script resolver

`tools/generate_snes_cooked_rooms.py --executable-local-room 49` now emits executable program
and lookup entries for every LSCR descriptor in the active cooked room. The lookup key is the
validated active record plus local script number. Data from other room records cannot resolve;
record validation rejects malformed bounds and duplicate room identities before activation,
and the cooked ROOM decoder rejects duplicate local IDs. Room commit retires slots owned by
the old room lifecycle before replacing the active record.

The complete resolver is profile-generated and deterministic. Bank 0 contains only the
five-byte `JSL ScummV5_M23A_ResolveLocalScript_Far` / `RTS` adapter at `$00:967C`; the resolver
itself is `$08:DA5C–$08:DAFF` with the cooked profile data.

Authentic room 49 proves these entries came from one generated table rather than a validator
whitelist:

| LSCR | Program | Bytes | Original file | ROOM-relative | Cooked | SHA-256 |
|---:|---:|---:|---:|---:|---:|---|
| 200 | `$D2` | 460 | 362375 | 60584 | 62736 | `dc34f2d549455fbd6ee30eb057470b39e97e4544ff3cbe49d94424158e3cbc6c` |
| 201 | `$D3` | 252 | 362844 | 61053 | 63205 | `920a5a11a61c1eac8f06ad13ddf35698f7e8fa8863052d8f77a49b3ce429e85d` |
| 208 | `$DA` | 7441 | 372057 | 70266 | 72418 | `2c84fa24e6e6c37c353cc08cfb2d94b78cc2a27be39cdc161b1131f480cd7876` |

All have original chunk offset 9 and normalized script offset zero. A two-run clean-output
comparison produced byte-identical generated sources. Normalized generated hashes were
`306b9a1d3fc2070723a9c65eca9456ac6b6da3f17ccccb3ebdddfb7d02f0d3be`
for the lookup include and
`61be79a625714e8514a9688724c6468172fb1c2ccb0122c87e2d97330e7c8b37`
for profile data in the M23B build.

## Conformance and controls

The new copyright-free host fixture in `tests/test_scumm_v5_cooked_room.py` uses an ENCD that
starts room-local A, then A immediately starts room-local B. Its first-frame trace proves:

```text
A local[0] = 1
B entry; B local[0] = 10
B breakHere at PC 6
A resumes; A local[0] = 2; A breakHere at PC 12
```

On the next scheduler pass B resumes independently, increments its own local to 11, and stops;
A also stops. Both slots retain room ownership until normal retirement. Existing focused C4
fixtures continue to cover child slot reuse, independent locals, immediate child dispatch,
parent continuation, 25-slot exhaustion without reusing slot zero, recursive/freeze flags,
and malformed/missing script failures. The M23A copyright-free lifecycle fixture continues to
prove old-room local retirement and absence of stale execution.

The missing SNES proof now runs in a dedicated validation profile. It uses generated,
copyright-free cooked ROOM records and the production cooked-record validator, complete LSCR
resolver, C4 scheduler/slot allocator, interpreter, 24-frame context stack, `startScript`, and
`breakHere`. Validator-only code selects the synthetic room at cold boot and records evidence;
it does not supply a child pointer, PC, branch result, scheduler mutation, or alternate
implementation. The integrated Fate driver is unchanged.

The normal fresh-power-on trace is:

```text
event  depth slot program PC      meaning
01       0    0   $D0   $0003    ENCD suspended after startScript 200
02       1    1   $D2   $0000    parent 200 immediate entry
01       1    1   $D2   $0012    parent suspended after startScript 201
02       2    2   $D3   $0000    child 201 immediate entry
03       2    2   $D3   $0010    child yielded after breakHere
04       1    1   $D2   $0012    exact parent restoration
03       1    1   $D2   $001B    parent later yielded
04       0    0   $D0   $0003    exact ENCD restoration
05       0    1   $D2   $001B    scheduler independently resumes parent
05       0    2   $D3   $0010    scheduler independently resumes child
```

The global PC sentinels are `[15, 18, 27, 0, 16]`. Final retained locals are parent
`[$1112,$2222]` and child `[$3334,$4444]`, proving that the child ran before parent resume,
both post-yield paths ran once, and neither context overwrote the other.

The bound ROM enters depths 1 through 24, then emits one normal slot-capacity fault at depth
24 for the attempted 25th context. It unwinds to depth zero, retains slot-local sentinels
200–223, and records no trace overflow or context beyond 24. The missing-local ROM emits one
explicit script-resolution fault at depth one, unwinds to zero, retains the parent's `$5151`
local, does not execute the post-fault `$DEAD` write, and never installs script 250.

Machine-readable evidence and the concise transition trace are generated at
`build/m25a-validator/evidence/report.json` and
`build/m25a-validator/evidence/critical-trace.txt`. The production lookup keys are active room
49 plus LSCR IDs 200/201 in the normal gate; the report binds their complete cooked
descriptors and record SHA-256. The authentic LSCR 200/201/208 table uses the same generated
resolver implementation, but this closure gate does not claim authentic execution of those
scripts.

## Validation and layout

Passing results:

* 328/328 unit tests;
* repository validation (with its established unregistered-demo diagnostics);
* Poppy lint;
* SNES assembly and ROM audit for all three dedicated ROMs;
* four dedicated fresh-power-on emulator processes with zero debugger writes;
* the post-acceptance context correction necessarily changes the M23B positive and negative
  ROMs; both rerun their accepted emulator gate successfully as
  `314e63391a3cc024112432296e73f5e4f0bc9b475551f20d1e69a81bc915b516` and
  `b2372da3513a19cf821e9b77949798c102549e528a904ae43dff8f110ff399b6`.

Integrated M25A ROM:

```text
SHA-256: 46b3f3f33c38b8dd3ba6f46e1f82d96609eb74a1c16c55b199b453349bc4ac63
bank 0 emitted end: $00:FFA3
free before header: 28 bytes
header: $00:FFC0–$00:FFDF
vectors: $00:FFE0–$00:FFFF
far closure: $09:8000–$09:862D
reset/NMI/IRQ: $8000/$8062/$8084
```

No regions overlap and all relocated routines remain wholly inside bank 9.

Dedicated validator ROM SHA-256 identities:

```text
normal:  67d127367b2f35a682b879a3d158df22a098dedec64de5679cd2af876c382e5d
depth:   990f7cf8ff29cccdaa94b79b4f28c14484c8ffe4abd11331ac1122cb93bdefa9
missing: bfb3f87799d611c4365834c2338ab22e0fbbb0f88ec45bc63b6baddb3c04d289
outer:   1b9f4c3ff9844d76fbb4c3303d77b1932d13c12f367c28a3cbc52a0472419438
```

## Stop condition

M25A is complete. No speculative harness or scheduler bypass was added. M25 opcode work and
M24R-B remain paused, and no later milestone was begun.

No new timbre approval required.
