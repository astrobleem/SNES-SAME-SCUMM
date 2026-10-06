# Capability and Dependency Analysis

Status is **IMPLEMENTED, PARTIAL v1** for whole-source census, the SCUMM v5
structural opcode schema, the semantic-operation subset, known dependency
edges, conservative roots/reachability, and explicit structural frontiers.
Complete v5 structural coverage, perfect control-flow certainty,
resource-specific codec analysis, and per-version backend/runtime
certification remain **PLANNED**.

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
Classifications distinguish definite and conditional blockers, possible
dynamic requirements, partial/unverified semantics, and unknown behavior
beyond an opaque boundary. Corpus-only use is not confused with a definite
boot blocker.

## Current limits

Residency demand is reported independently from semantic support. A source
corpus count, a room-bundle directory size, and simultaneous live C4 slots are
different measurements; see `MILESTONE_4_RESIDENCY.md`. Selector capacity is
a backend addressability limit, not evidence that every source executable
must be resident at once.

The opcode schema covers the registered SCUMM v5 byte forms, while this FATE
source still contains nine structurally unknown occurrences and two
truncated operands among parsed-room executables. The configured
`GlobalScript(1)` now decodes completely; root closure remains incomplete due
to dynamic references, unresolved room/resource identities, and reachable
opaque frontiers elsewhere. Three FATE rooms still exceed the room decoder's
BOXD z-plane representation and remain explicitly unsupported. Actor metadata
is inferred from decoded references rather than claimed as a complete actor
table. Text literals are retained as encoded IR operands, not normalized into
a complete string table.

In the opcode census, zero `SUPPORTED` backend/runtime occurrences means
“none certified as fully supported by this whole-source registry,” not that
the existing runtime implements no operations. Existing bytecode preservation,
handler presence and prior conformance evidence are deliberately not promoted
to whole-corpus per-operation certification.

Capacity values distinguish exact indexed/cooked counts, static lower bounds,
and unknown runtime scheduling pressure. Static graph depth is not a runtime
script-slot or stack maximum. This analyzer does not automatically generate a
full FATE ROM or replace profile-selected backend inputs.
