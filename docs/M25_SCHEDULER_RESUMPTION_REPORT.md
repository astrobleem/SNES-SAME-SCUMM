# M25 integrated yielded-script scheduler resumption

Status: **implemented and fresh-emulator proven**. The production SCUMM tick
now owns normal later scheduler passes for validated active rooms. Authentic
room-63 LSCR 202 resumes from its saved PC without validator assistance.
Exactly one lifecycle blocker was cleared; M24R-B remains paused.

## Canonical pass contract

The local host and the checked-out SCUMM reference agree on the essential v5
contract:

1. At the start of a logical script pass, clear every slot's `didexec` flag.
2. Scan eligible running slots in ascending slot order (and supported cycle
   order).
3. Execute each eligible slot at most once in that pass.
4. Immediate `startScript` still allocates and executes its child before the
   parent resumes. Execution marks that child `didexec`.
5. `breakHere` preserves the slot, resource/program identity, locals, and
   post-opcode PC, but the child's `didexec` prevents a second execution later
   in the same pass.
6. The next logical pass clears `didexec` and resumes the same allocated slot
   at its saved PC; it does not resolve the numeric script ID again.

The host ordering in `ScummV5Engine.tick` is input/frame begin, talk-message
begin, `didexec` reset and scheduler scan, sentence processing, frame-end iMUSE
queue handling, audio tick, actor movement/presentation, then talk-message end.
The reference `ScummEngine::runAllScripts` independently clears `didexec` and
scans running slots in ascending order. In the existing SNES lifecycle, the
accepted room/audio work remains ahead of the scheduler, then an idle,
validated active room invokes the single production C4 scheduler owner before
common frame/talk completion. This milestone did not reorder accepted audio or
room transitions.

## Production correction

The active-room scheduler path was incorrectly restricted to the dedicated
M25A validator build. The production frame driver now calls a small far-bank
eligibility helper and invokes the existing C4 scheduler when:

```text
room lifecycle phase == idle
active cooked room record is valid
at least one scheduler slot is active
```

The helper is generic: it contains no Fate, room-63, LSCR-202, or slot-number
constant. The same scheduler resumes global, lifecycle-created, and room-local
slots. Existing room retirement remains authoritative and invalidates old
room-local slots/program ownership.

The copyright-free fixture also exposed a tightly related canonical retirement
defect: scheduled `stopObjectCode` used a historical fixture-ID whitelist and,
on one direct branch, allowed the common running status to overwrite the
slot's stopped status. Scheduled stop is now governed by scheduler return mode,
retires the current slot, and stores stopped status in both the slot and current
interpreter state before save-back. Unknown/malformed bytecode remains
fail-closed.

Relevant entry points:

- `runtime/snes/engines/scumm_v5.pasm`
  - `ScummV5_Engine_Frame__m23a_driver`
  - `ScummV5_C4_Scheduler_Frame`
  - `ScummV5_Op_Stop__c4_slot`
- `runtime/snes/engines/scumm_v5_matrix_far.pasm`
  - `ScummV5_SchedulerReady_FarEntry`

## Copyright-free conformance

The generated cooked room contains an ENCD and LSCR 200, 201, 202, 203, and
204. It uses the production cooked-directory lookup, slot allocator, immediate
nested execution, context stack, locals, `breakHere`, stop, and later scheduler
scan.

The measured immediate path is:

```text
parent 200: A
parent 200: startScript(201)
child  201: B; breakHere at saved PC 11
parent 200: D; breakHere at saved PC 19
script 202: segment 1; breakHere at saved PC 11
script 203: terminates
script 204: segment 1; breakHere, then is explicitly stopped
```

No yielded slot executes twice during this creation pass. On the next normal
pass the captured scheduler selections are, in ascending order:

```text
slot 1 / program $D2 / PC 19  -> parent F, terminate
slot 2 / program $D3 / PC 11  -> child E, terminate
slot 3 / program $D4 / PC 11  -> repeated-yield segment 2
next pass:
slot 3 / program $D4 / PC 17  -> repeated-yield segment 3, terminate
```

The stopped slot 4 and terminating child never resume. Distinct local values
`$A0A0`, `$B0B0`, and `$C0C0` survive independently. Host and SNES agree on
the immediate values `A/B/D`, the later `F/E` order, all saved PCs, slot
retirement, and the three-segment one-per-pass behavior. Existing host coverage
also proves room replacement kills a yielded old-room local and a same-number
script in the new room resolves to the new program.

Machine evidence:
`build/m25-scheduler/conformance/report.json`.

The dedicated M25A validator suite was rebuilt and rerun to guard the critical
same-pass rule and context semantics. Immediate child execution, exact parent
restoration, later child resumption, independent locals, missing lookup,
24-level nesting, deterministic 25th-level overflow, and outer-context cleanup
all still pass.

## Authentic Fate proof

The complete source-bound room-63 LSCR 202 is unchanged:

```text
identity: room.63/LSCR.202
SHA-256: 90e13f2440380e9f77fae78204e2cc0d8122124c73f1d06556cdfa1166049671
original PLAYFATE.001 offset: $07B0E7
ROOM-relative offset: $00A940
cooked-record offset: $00AC08
payload length: 208 bytes
```

From fresh power with zero debugger writes, the authentic nested trace is:

```text
room.63/ENCD     program $E7 +$00DE  $2A startScript(202)
room.63/LSCR.202 program $EA +$0000  $1A move(Local[0], -1)
room.63/LSCR.202 program $EA +$0005  $80 breakHere
room.63/ENCD     program $E7 +$00E1  $00 stopObjectCode
```

At return, child slot 2 remains runnable with program `$EA`, PC `$0006`, delay
zero, `didexec=1`, Local[0]=`$FFFF`, and room-63 record ownership. The parent is
retired. On the next integrated logical pass, the scheduler clears pass state,
selects slot 2, preserves program `$EA` and locals, and fetches:

```text
room.63/LSCR.202 +$0006  $7B getActorWalkBox(Local[1], actor 1)
```

The evidence labels the immediate creation/yield interval scheduler-pass
ordinal 0 at video frame 2199 and the eligible resume pass ordinal 1 at video
frame 2200. The existing shared M24 logical-clock field reads 1843 in both
snapshots; it is not used to manufacture or delay the scheduler transition.
`same_pass_reentry=false` is recorded explicitly.

No PC reset, script-ID re-resolution, debugger write, manual slot selection, or
validator resume seam participates. The resumed authentic segment continues
through the supported comparisons and actor speed operation:

```text
+$0071  $48 compare the observed walkbox against 11
+$0078  $13 actorOps set speed(20, 6)
+$007E  $18 jump
+$00C7  $9A move(Local[0], Local[1])
+$00CC  $18 jump to the breakHere loop boundary
```

The stable state is again runnable at PC `$0006`, with actor 1's stored
walkbox, Local[0], and Local[1] all equal to 11. This proves repeated normal
passes rather than a one-shot forced resume.

Machine evidence: `build/m25-scheduler/authentic-report.json`.

## Next authentic dependency

There is no new unsupported opcode immediately after this repair. Authentic
LSCR 202 is a persistent walkbox poller. Its first 32 bytes are:

```text
1A 00 40 FF FF 80 7B 01 40 01 88 01 40 00 40 BB
00 48 01 40 02 00 09 00 13 01 02 08 03 FF 18 A6
```

The next real dependency is the **actor movement/walkbox state lifecycle**.
The query correctly returns actor 1's stored walkbox 11, the supported branch
selects its speed, and the script yields again. Further player-visible progress
requires canonical movement to update actor position/destination and eventually
the stored walkbox. This is a missing subsystem/earlier gameplay-state
dependency, not an opcode decode gap. It was not implemented here.

## Validation, layout, and identity

```text
unit tests:                    PASS, 347/347 (345 accepted + 2 new)
repository validation:        PASS with established profile diagnostics
Poppy/source traps:            PASS, 29 files / 2344 global labels
SNES assembly/LoROM audit:     PASS, 524288 bytes
vectors:                       reset=$8000, NMI=$8062, IRQ=$8084
copyright-free validator ROM:  24bd3b8970ff8c25855381f489317bffa632be232a27aaf9c69d805e73199145
integrated Fate ROM SHA-256:   0a027331ec470324d8ea6071ff6ce8a274d0f1a571f3b752730542e3509312b3
```

Bank 0 emits through `$FFA7`, leaving 25 bytes before the mandatory header at
`$FFC0`. The scheduler eligibility helper is wholly in far bank 9 at
`$09:8659-$09:8673`; the established far closure ends at `$09:9486`. Header,
vectors, regions, JSL/RTL, PBR/DBR, and generated pointer audits pass.

Costume presentation remains blocked because authentic costume 45 is absent
from the supplied demo and the SNES costume renderer does not exist. Text glyph
rendering also remains unavailable. No presentation claim is made.

No audio, iMUSE, TAD, instrument, actor movement, pathfinding, costume/text
rendering, or later authentic semantic was implemented. No new timbre approval
is required.
