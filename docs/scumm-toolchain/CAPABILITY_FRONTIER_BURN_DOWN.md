# SCUMM v5 Capability Frontier Burn-Down

Status: **IMPLEMENTED, PARTIAL**. This checkpoint closes the current canonical
DOS-CD FATE corpus's semantic-IR gaps and fixes an instruction-census bug. It
does not certify whole-game host or SNES execution.

## Measured change

The baseline is the canonical DOS-CD analysis available at the start of this
phase; the archive remains external and no source payload or generated corpus
report is committed.

| Measure | Before | Current |
|---|---:|---:|
| Parsed rooms | 93 of 96 | 96 of 96 |
| Executable identities | 4,100 lower bound | 4,108 exact |
| Instruction occurrences in the census | 114,399 | 116,730 |
| Structurally decoded occurrences | 114,388 | 116,730 |
| Structural unknown / truncated occurrences | 9 / 2 | 0 / 0 |
| Semantic IR available occurrences | 87,156 | 116,730 |
| Structurally known but semantic-IR unsupported | 27,232 across 55 families | 0 across 0 families |
| Semantic status unknown | 11 | 0 |
| Dependency graph nodes / edges | 6,538 / 34,539 | 6,602 / 37,063 |
| Root / definite / conditional / possible / unresolved executables | 1 / 2 / 3,822 / 268 / 7 | 1 / 2 / 3,859 / 237 / 9 |

The instruction total is not directly comparable as a count of executed
instructions. The compiler now continues structural scanning after a
`stopScript(0)` path terminator so code reached by a branch beyond that
instruction is not omitted. The synthetic regression includes exactly this
shape. All instruction bytes remain source-bound; runtime path certainty is a
separate analysis.

Before, the largest semantic-IR gaps were `expression` (4,224), `stringOps`
(3,471), `verbOps` (2,954), arithmetic `add` (1,727), `roomOps` (1,472),
`stopScript` (958), `isScriptRunning` (906), and `getRandomNr` (639). The
front-end now normalizes these and the related v5 families, including flagged
operand modes, state/query effects, and source provenance. It also normalizes
debug, draw-box and system-operation commands without implying those effects
are implemented by a target.

The current analysis reports 89 observed semantic operation families. The
zero semantic gap is a front-end/IR result only; these are independent gates:

```text
structural decode  ->  semantic IR  ->  host/reference behavior
                                      ->  SNES backend representation
                                      ->  SNES runtime behavior
                                      ->  save/restore coverage
```

## Runtime and backend frontier

The whole-game readiness report remains **NOT_READY**. The current registry
marks 67 of 116,730 instruction occurrences as supported by both the backend
and SNES runtime (the bounded `getActorWidth` and `walkActorToActor` families);
this small certified slice is not whole-corpus coverage. The operation
registry separates known `UNSUPPORTED` layers from `PARTIAL`/`UNKNOWN`
evidence, and the ranking no longer calls unverified behavior a definite
blocker.

The current family-level execution frontier separates known blockers from
families whose whole-game conformance is merely unverified:

| Family | Occurrences | Affected executables | Current evidence |
|---|---:|---:|---|
| `drawBox` | 28 | 8 | Host semantic rendering is covered for operand modes, inclusive/reversed bounds, clipping and color writes; SNES runtime remains unsupported because the native graphics path has no script-visible filled-rectangle surface. |
| `systemOps` | 4 | 4 | Host effects remain unsupported; classify the exact source subcommands before choosing an engine-owned system-control policy. |
| `findInventory` | 1 | 1 | Host behavior remains unsupported until ordered inventory semantics are represented; ownership counts alone cannot determine inventory ordinal. |
| `loadRoomWithEgo` | 227 | 128 | Host behavior is supported, including entry placement before yielded ENCD; SNES transition semantics remain partial and native conformance unknown. |
| `getActorWidth` | 3 | 2 | Supported end to end by host tests and a bounded native C14 Nexen control; direct and variable-selected actors return configured/default width. |
| `walkActorToActor` | 64 | 55 | Host and SNES runtime behavior are supported by generic operand/state tests and bounded Nexen C32 movement control; portable native save coverage remains partial. |

The report ranks known unsupported behavior independently from
`DEFINITE_UNVERIFIED` behavior. `loadRoomWithEgo` is now a definite but
unverified native/runtime frontier, not a known host blocker. `drawBox`,
`systemOps`, and `findInventory` remain conditional known blockers. The
generated report preserves source operation, reachability, support dimensions
and root-nearest paths; a missing conformance record is never converted to
`SUPPORTED`.

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
whole-game-ready. The next highest-value generic tranche is to resolve the
known conditional `drawBox` native graphics gap and the smaller explicit
`systemOps`/`findInventory` host gaps, while advancing `loadRoomWithEgo` from
partial native behavior to operation-level differential conformance. The
combined full-FATE plus M20 bank-0 layout limit remains a separate backend
layout issue; it was not worked around by disabling M20 or another feature.
