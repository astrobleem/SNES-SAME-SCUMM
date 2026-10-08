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
| IR representation | `SUPPORTED` only for a normalized semantic operation and decoded operand/control-flow records; an opaque tail is only `PARTIAL`. |
| SNES backend | Independently scoped. Preserving source bytecode in SC5C is not by itself lowering certification. |
| Host runtime | `SUPPORTED`/`PARTIAL` only to the scope of host semantic tests; dispatch presence alone is not proof. |
| SNES runtime | `SUPPORTED`/`PARTIAL` only to the operation-specific native behavior exercised; an assembly label alone is not proof. |
| Save/restore | Independently scoped to serialized state and continuation coverage; it is not folded into execution support. |
| Native conformance | `SUPPORTED` only for source/build-bound Nexen evidence, never inferred from static analysis. |

The aggregate report is deliberately conservative: an operation being decoded
does not imply backend, host semantic, SNES, save-state, or native acceptance.
Execution gaps and persistence-only gaps are reported separately. A family
whose execution dimensions are supported but whose `save_restore` is unknown
does not appear as an execution blocker; it remains a persistence release-gate
item and can still keep whole-game readiness at `NOT_READY`.
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

The canonical DOS-CD FATE run (analysis identity
`2e7d2ed5b165d382a33f9031a89b63dd4c299e724162b27132fd047b45626673`)
reports 96 rooms inventoried and parsed, 4,108 complete executable
identities, 116,730 structurally decoded instruction records, and zero
structural unknown/truncated/malformed occurrences. Compared with the earlier
93-room run, the 2,331-record increase is from parsing the three previously
unsupported room resources, not from claiming that more instructions execute.
The BOXD parser
now interprets the format's implicit base z-buffer separately from additional
RMIH-declared planes; the previously rejected rooms parse through the same
generic room path. Root closure remains incomplete because dynamic and
unresolved dependencies still exist, not because the current run encountered
an opaque executable tail. Actor metadata is inferred from decoded references
rather than claimed as a complete actor table. Text literals remain encoded
IR operands rather than a complete normalized string table.

For this corpus, all 116,730 records have a normalized semantic-IR operation:
zero semantic-unsupported and zero semantic-unknown occurrences across 89
observed operation families. Structural scanning after terminators is not
execution evidence. The CFG report separately records 17,416 reachable,
92,197 conditionally reachable, 7,102 decoded-unreachable, and 15
control-flow-uncertain records; nine executable CFGs are incomplete. This does
**not** mean the runtime supports all 89 families.

The current operation-level frontier has 14 definitely reachable execution
families still unverified, 57 conditionally reachable execution families
still unverified, and one known conditional blocker (`systemOps`). Fifteen
additional families have persistence-only gaps (five definite, ten
conditional); these are not mislabeled as execution failures, but save-state
uncertainty still blocks whole-game readiness. The 386 dynamic and 408
unresolved dependency edges also keep closure incomplete.

Bounded host/native conformance now covers `loadRoomWithEgo` (the tested
multiroom transition scope), ordered `findInventory` (within the configured
2,048-entry object-owner table), and `drawBox` (the indexed room-surface
backend only). Existing `getActorWidth` and `walkActorToActor` controls remain
narrowly scoped. These evidence records do not certify unrelated families or
every dialect/platform profile. `systemOps` remains explicitly unsupported
until a generic platform lifecycle service exists. See
`CAPABILITY_FRONTIER_BURN_DOWN.md` for the full measured snapshot.

The current opcode census marks 20,485 of 116,730 occurrences as backend
supported and 20,513 as SNES-runtime supported, based on operation-scoped
registry evidence. The counters are independent: backend representation and
runtime execution are separate dimensions, so their totals need not be
monotonic. These totals do not certify the whole corpus or operations without
matching evidence. Existing bytecode preservation, handler presence, and
unrelated conformance are not promoted to whole-corpus per-operation
certification.

Capacity values distinguish exact indexed/cooked counts, static lower bounds,
and unknown runtime scheduling pressure. Static graph depth is not a runtime
script-slot or stack maximum. This analyzer does not automatically generate a
full FATE ROM or replace profile-selected backend inputs.
