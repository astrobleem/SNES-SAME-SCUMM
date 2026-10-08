# SCUMM v5 Capability Frontier Burn-Down

Status: **IMPLEMENTED, PARTIAL**. This checkpoint adds bounded generic
host/native conformance for `loadRoomWithEgo`, `findInventory`, and `drawBox`,
plus native evidence for a C2 arithmetic/control-flow tranche. It does not
certify whole-game host or SNES execution.

## Measured change

The baseline is the canonical DOS-CD analysis available at the start of this
phase; the archive remains external and no source payload or generated corpus
report is committed.

| Measure | Before | Current |
|---|---:|---:|
| Parsed rooms | 93 of 96 | 96 of 96 |
| Executable identities | 4,100 lower bound | 4,108 exact |
| Instruction records in the census | 114,399 | 116,730 |
| Structurally decoded records | 114,388 | 116,730 |
| Structural unknown / truncated / malformed occurrences | 9 / 2 | 0 / 0 / 0 |
| Semantic IR available occurrences | 87,156 | 116,730 |
| Structurally known but semantic-IR unsupported | 27,232 across 55 families | 0 across 0 families |
| Semantic status unknown | 11 | 0 |
| Dependency graph nodes / edges | 6,538 / 34,539 | 6,602 / 37,063 |
| Root / definite / conditional / possible / unresolved executables | 1 / 2 / 3,822 / 268 / 7 | 1 / 2 / 3,859 / 237 / 9 |

The instruction total is not a count of executed instructions. The increase
of 2,331 records from the earlier census is attributable to parsing the three
previously unsupported room resources (93 parsed rooms became 96), not to
executing more bytecode. The compiler
continues structural scanning after path terminators so later branch targets
are not omitted, and annotates the resulting control-flow graph. In the current
DOS-CD run, 17,416 instructions are CFG-reachable, 92,197 are conditionally
reachable, 7,102 are decoded but unreachable from their executable entry, and
15 lie beyond control-flow uncertainty. Nine executable CFGs remain
incomplete. Synthetic regressions cover a valid branch after a terminator and
distinguish unreachable linear code from inline data using instruction
boundaries and branch targets. CFG uncertainty is not hidden by the zero
structural-unknown count.

Before, the largest semantic-IR gaps were `expression` (4,224), `stringOps`
(3,471), `verbOps` (2,954), arithmetic `add` (1,727), `roomOps` (1,472),
`stopScript` (958), `isScriptRunning` (906), and `getRandomNr` (639). The
front-end now normalizes these and the related v5 families, including flagged
operand modes, state/query effects, and source provenance. It also normalizes
debug, draw-box and system-operation commands without implying those effects
are implemented by a target.

The current analysis reports 89 observed semantic operation families. The
zero semantic gap means each observed instruction has a normalized semantic
IR record, not that every family has backend lowering or executable runtime
behavior. The audit found no generic raw-opcode/no-op wrapper being counted as
semantic support. These remain independent gates:

```text
structural decode  ->  semantic IR  ->  host/reference behavior
                                      ->  SNES backend representation
                                      ->  SNES runtime behavior
                                      ->  save/restore coverage
```

## Runtime and backend frontier

The whole-game readiness report remains **NOT_READY**. At this snapshot, 20,485
instruction occurrences have backend status `SUPPORTED` and 20,513 have SNES
runtime status `SUPPORTED`, based on operation-scoped registry evidence.
Native controls are bounded to documented semantics for `drawBox`,
`findInventory`, `getActorWidth`, `walkActorToActor`, `loadRoomWithEgo`, and the
C2 extended fixture operations. The counters are independent and are not
corpus-wide correctness claims. The registry separates known `UNSUPPORTED`
layers from `PARTIAL`/`UNKNOWN` evidence.

The current execution frontier contains 14 definitely reachable but
unverified families, 57 conditionally reachable but unverified families, and
one known conditional blocker (`systemOps`). Separately, five definite and ten
conditional families have persistence-only gaps; they are not counted as
execution failures, but still keep the release gate closed. There are 386
dynamic and 408 unresolved execution edges, so source closure is incomplete.
Lack of native evidence is not itself classified as a definite blocker.

Recent bounded family controls and their residual support scope:

| Family | Occurrences | Affected executables | Current status/evidence |
|---|---:|---:|---|
| `startScript` | 3,903 | 1,321 | **DEFINITE_UNVERIFIED**, not known broken. Host lifecycle and Nexen C4/resolver controls cover arguments, nested starts, yields, variable-selected globals, live-global room transitions, and binding safety. Host/backend/native claims remain **PARTIAL** because not all scheduler interleavings or target domains are covered. |
| `print` | 4,576 | 700 | **DEFINITE_UNVERIFIED**. Text command IR and bounded presentation paths exist; complete control-code/layout/voice behavior is not native-certified. |
| `drawBox` | 28 | 8 | Conditional use; host and Nexen controls cover direct/variable operands, inclusive/reversed bounds, clipping, indexed color writes, and untouched neighbors. SNES backend is **PARTIAL**, scoped to builds with the writable indexed room surface. |
| `systemOps` | 4 | 4 | **CONDITIONAL_BLOCKER**. IR identifies restart/pause/quit requests, but host dispatch and a generic platform lifecycle service are absent. |
| `findInventory` | 1 | 1 | Host and Nexen agree on ascending object-ID order, direct/variable owner and ordinal operands, empty/out-of-range results, and owner mutation. Runtime enumeration is bounded by the configured 2,048-entry owner table. |
| `loadRoomWithEgo` | 227 | 128 | Host behavior and a four-room dynamic-residency Nexen control cover destination preflight, placement, optional walk, `VAR_WALKTO_OBJ`, EXCD/ENCD order, yielded entry, continuation, camera, and settled movement. Execution is **SUPPORTED within that generated service contract**; portable in-flight save coverage remains unknown. |
| `getActorWidth` | 3 | 2 | Host and bounded C14 Nexen controls verify direct/variable actor IDs, actorOps width mutation, and configured/default results. |
| `walkActorToActor` | 64 | 55 | Host and bounded C32 Nexen controls verify actor-relative destination and lifecycle state; portable movement-state persistence remains separate. |

The report ranks known unsupported behavior independently from
`DEFINITE_UNVERIFIED` behavior and save-only gaps. `loadRoomWithEgo`,
`drawBox`, and `findInventory` are not known unsupported operations; their
remaining backend/persistence scope is explicit above. `systemOps` remains
explicitly unsupported rather than being treated as a successful no-op. The
generated report preserves source operation, reachability, independent
execution/persistence dimensions, and root-nearest paths; missing conformance
is never converted to `SUPPORTED`.

### Conformance tranche

`loadRoomWithEgo` uses the existing shared transition and room-commit path. The
host and native fixture checks actor entry placement before yielded ENCD
resumes, old-room exit and bundle retirement, destination entry, camera follow,
optional walking, and continuation completion. It does not certify portable
save/restore during an in-flight transition.

`findInventory` returns the object at the requested ordinal in ascending source
object-ID order for the requested owner, or zero when the ordinal is absent.
Host/native fixtures compare direct and variable forms and mutate ownership
between queries. It adds no persistent state; persistence of object ownership
is a separate save capability.

`drawBox` fills the clipped, inclusive rectangle on the projected INDEX8 room
surface, normalizing reversed corners. Host and Nexen fixtures compare exact
pixels, including boundaries and untouched neighbors. This does not certify
other video surfaces, direct-color platforms, text/voice composition, or save
persistence of the mutated image.

The generic native `walkActorToActor` implementation handles independently
flagged actor operands, explicit or automatic stand-off distance, scaled actor
width, actor residency checks and ordinary movement dispatch. A copyright-free
Nexen C32 control checks the actor-relative destination and room/lifecycle
state. The bounded room-4-to-room-3 FATE replay does not exercise this family,
so it remains unchanged and is not extended. This evidence is not generalized
to other actor operations.

The read-only `getActorWidth` query now follows the same independent registry
dimensions. Its native handler reads the existing C14 width field and returns
the ordinary result variable value; it adds no operation-local save state.
The C14 fixture checks width 35 after actorOps and the default width 24 for a
second actor through both direct and variable-selected forms.

## Structural/resource frontier

The BOXD z-plane validation now treats the base plane as implicit and RMIH as
the number of additional planes. This generic format correction allows the
previously rejected room resources to pass through the same parser; all 96
indexed rooms parse in this source edition. The regression tests both a valid
implicit-base mask and an invalid mask exceeding the available slots. No room
number is present in production parser logic.

This does not certify every SCUMM v5 edition, resource codec, audio command,
or runtime semantic. The current DOS-CD corpus has zero opaque, structurally
unknown, truncated, or malformed instruction boundaries, but source-wide
execution closure remains incomplete because dynamic and unresolved
references exist. Audio command semantics, SAME audio playback, and converted
title assets remain separate support questions.

## Bounded FATE regression and scope

The corrected static/dynamic replay comparator reports all seven fresh
checkpoints semantically matching, including active canonical ProgramUnit
identities/status, room ownership, runnable-vs-waiting state, and progression
state. It reports transient continuation-PC and exact delay-tick differences
separately; selectors and frame timing are not used as semantic identity, but
the raw timing observations remain in the comparison output. The accepted route
remains `0 -> 68 -> 0 -> 4 -> 5 -> 6 -> 7 -> 3`; this phase does not extend
gameplay.

This result proves semantic-IR coverage for the parsed corpus and selected
runtime controls, not that all FATE scripts execute or that the game is
whole-game-ready. The next execution tranche is driven by the refreshed report:
root-near variable/control-flow and script-lifecycle behavior remains
PARTIAL/UNKNOWN at whole-corpus scope, while a generic platform lifecycle
service is needed to implement `systemOps`. The combined full-FATE plus M20
bank-0 layout limit remains a separate backend layout issue; it was not worked
around by disabling M20 or another feature.

## Readiness and remaining limits

The release gate is **NOT_READY** for independent, measured reasons: nine
CFGs are incomplete; 386 dynamic and 408 unresolved execution edges prevent a
closed source graph; backend/runtime behavior is not certified for every
reachable family; 85 indexed resource slots are unavailable to the current
front end; actor and normalized string metadata are partial; and stateful
portable save coverage is incomplete. Audio command semantics, SAME playback,
and title asset conversion are separate requirements. A supported script
command does not certify the resource or device service it references.

The canonical source census currently contains 96 rooms, 4,108 complete
executable identities, 116,730 decoded/represented instructions, and 89
semantic families. The static/dynamic bounded replay still ends in room 3;
this mission did not extend gameplay. No whole-game playability claim follows
from this evidence.
