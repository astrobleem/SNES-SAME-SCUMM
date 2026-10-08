# Capability and Dependency Analysis

Status is **IMPLEMENTED, PARTIAL** for the whole-source census, source-bound
SCUMM v5 structural decoding, normalized semantic IR for every instruction in
the current canonical DOS-CD FATE corpus, known dependency edges, conservative
reachability, and layer-separated capability frontiers. This corpus run parsed
all 96 indexed rooms and decoded/represented 116,730 instruction occurrences;
it found zero structural unknowns, truncated bodies, or missing semantic-IR
occurrences. This is corpus coverage, not proof that every SCUMM v5 dialect
form is implemented. Perfect control-flow certainty, full resource-codec
analysis, and per-operation backend/runtime certification remain **PARTIAL or
PLANNED**.

## Current outputs

`tools/compile_scumm_game.py --analyze` writes deterministic JSON for the
source GameIR, resource census, executable records, dependency/resource graph,
reachability, capability registry, unsupported frontier, opaque analysis, and
capacity observations. Its Markdown summary is generated from those reports.
Output is source-bound by archive/member, profile, compiler component and body
hashes; no absolute input paths are placed in canonical artifacts.

The source catalog keeps indexed directory slots, including unavailable or
unresolved entries. Rooms are passed through the same `compile_room_payload()`
used by `compile_scumm_room.py`; global scripts are passed through the same
`decode_script()`. A room the current semantic parser rejects stays inventoried
with an `UNSUPPORTED` diagnostic and contributes no fabricated executable
records. Object/actor/string metadata indicates when it is only a lower bound
or partial projection.

Canonical execution identities are source-level (`GlobalScript(n)`,
`RoomEntry(n)`, `RoomExit(n)`, `RoomLocal(room=n,local=m)`, and
`ObjectVerb(room=n,object=m,verb=v)`). Resource identities are distinct
(`ScriptResource(n)`, `RoomResource(n)`, `Sound(n)`, `Costume(n)`, `Charset(n)`).
No SNES selector is allocated by game analysis.

## Certainty and completeness

Dependency edges use `STATIC`, `CONDITIONAL_STATIC`, `DYNAMIC`, or
`UNRESOLVED`. Reachability uses `ROOT`, `DEFINITE`, `CONDITIONAL`, `POSSIBLE`,
`UNRESOLVED`, or `UNREACHED`. Dynamic selectors retain the source expression
and are not guessed into a target. Room containment/object-verb ownership is
reported in the resource graph, separately from executable reachability.

Each executable reports `COMPLETE`, `PARTIAL_OPAQUE`, `UNSUPPORTED_DECODE`, or
`MALFORMED`. These are structural-analysis statuses, not semantic-support
statuses. `UNSUPPORTED_DECODE` means the decoder cannot establish the next
instruction boundary or control-flow continuation. `MALFORMED` includes a
truncated operand. A structurally decoded operation may instead have
`SEMANTIC_UNSUPPORTED`; it keeps its width, operands, flags, source PC and
control-flow information and does not create an opaque tail solely because
the runtime semantics are not modeled. Opaque reports retain the last decoded
PC, absolute `opaque_from_pc`, reason, known operations, and known dependencies
before the boundary. The invariant is:

> OPAQUE TAIL != COMPLETE ANALYSIS

If an opaque or dynamic edge is reachable from configured roots, global
closure is incomplete. Other unvisited executables then remain `UNRESOLVED`,
not proven unreachable. The report provides a known path where one exists and
an uncertainty witness otherwise. No absence-of-edge claim extends beyond an
opaque boundary.

## Capability registry

The registry is keyed by generic decoded operation/capability, never by FATE
room/script/object identities. Structural byte decoding, semantic IR, backend
representation, runtime behavior and native conformance are separate claims.
It tracks these dimensions independently:

| Dimension | Current evidence/status rule |
|---|---|
| Front-end decode | `SUPPORTED` only for operations decoded by the shared v5 decoder; unknown-width tail is `UNSUPPORTED`. |
| IR representation | `SUPPORTED` for explicit `InstructionIR`; an opaque tail is only `PARTIAL`. |
| SNES backend | `PARTIAL`: SC5C preserves source bytecode, but this is not semantic lowering certification. |
| Host runtime | `PARTIAL` when dispatch exists; `UNSUPPORTED` when a decoded opcode has no handler. Dispatch presence alone is not conformance proof. |
| SNES runtime | `UNKNOWN` in static whole-source analysis; an assembly label alone would not certify semantics. |
| Save/restore | `UNKNOWN` unless a separate stateful regression establishes it. |
| Native conformance | `UNKNOWN` unless a source/build-bound native control establishes it. |

The aggregate report is deliberately conservative: an operation being decoded
does not imply backend, host semantic, SNES, save-state, or native acceptance.
Likewise Milestone 1's `unsupported_operations == 0` means only that the
bounded decoder did not classify a decoded operation as unsupported; it is not
runtime capability certification.

Required groups are reported for the whole source corpus, definite,
conditional, possible/dynamic and unresolved scopes, plus individual parsed
rooms and executables. Useful groups include script lifecycle, variables and
control flow, object execution/state, room lifecycle, actors/movement,
text/dialog, waits/timers, cutscenes, audio, and resource services. Resource
census separately reports indexed sound/music, costumes and charsets; codec
semantics are not certified merely by inventory.

## Unsupported/partial frontier

The frontier is an engineering backlog, not a claim that every listed
operation blocks the current game path. Each item identifies source identity,
source PC, capability, support dimensions, reachability, a known dependency
path or uncertainty witness, and whether dynamic/opaque analysis affects it.
Classifications distinguish known `UNSUPPORTED` implementation blockers from
`PARTIAL`/`UNKNOWN` evidence that is merely unverified. Root/definite known
blockers rank first, then conditional blockers, then unresolved verification
work; a family is never called a blocker just because the SNES runtime status
is unknown. Corpus-only use is not confused with a definite boot blocker.

## Current limits

Residency demand is reported independently from semantic support. A source
corpus count, a room-bundle directory size, and simultaneous live C4 slots are
different measurements; see `MILESTONE_4_RESIDENCY.md`. Selector capacity is
a backend addressability limit, not evidence that every source executable
must be resident at once.

The canonical DOS-CD FATE run reports 96 rooms inventoried and parsed, 4,108
complete executable identities, 116,730 structurally decoded instructions,
and zero structural unknown/truncated/malformed occurrences. The BOXD parser
now interprets the format's implicit base z-buffer separately from additional
RMIH-declared planes; the previously rejected rooms parse through the same
generic room path. Root closure remains incomplete because dynamic and
unresolved dependencies still exist, not because the current run encountered
an opaque executable tail. Actor metadata is inferred from decoded references
rather than claimed as a complete actor table. Text literals remain encoded
IR operands rather than a complete normalized string table.

For this corpus, semantic-IR availability is complete: 0 unsupported and 0
unknown semantic occurrences across 89 observed operation families. This
does **not** mean the runtime supports all 89. The release gate remains
`NOT_READY`. The current registry identifies three known implementation gaps:
SNES `drawBox`, host `systemOps`, and host `findInventory`; native
`loadRoomWithEgo` is partial rather than certified. Many other families have
working code but only partial or unknown whole-corpus conformance/save
evidence. `getActorWidth` and `walkActorToActor` now have bounded native
controls; this does not certify unrelated actor operations. See
`CAPABILITY_FRONTIER_BURN_DOWN.md` for the measured snapshot and ranked work.

The current opcode census marks 67 of 116,730 occurrences as supported by
both the backend and SNES runtime, from bounded `getActorWidth` and
`walkActorToActor` conformance. That does not certify the whole corpus or
operations without matching native evidence. Existing bytecode preservation,
handler presence and unrelated conformance evidence are deliberately not
promoted to whole-corpus per-operation certification.

Capacity values distinguish exact indexed/cooked counts, static lower bounds,
and unknown runtime scheduling pressure. Static graph depth is not a runtime
script-slot or stack maximum. This analyzer does not automatically generate a
full FATE ROM or replace profile-selected backend inputs.
