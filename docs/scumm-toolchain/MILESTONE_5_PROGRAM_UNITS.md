# Milestone 5: ProgramUnit Reconciliation and Residency Contract

Status: **IMPLEMENTED, COMPILER ANALYSIS AND PURE CONTRACT MODEL ONLY**.
No native selector allocator, SNES runtime behavior, or save format changed.

## Identity layers and backend projection

The compiler now keeps these layers distinct:

| Layer | Meaning | Example |
|---|---|---|
| Semantic executable | Permanent source identity for a script body/verb. | `ObjectVerb(room=7,object=118,verb=10)` |
| ProgramUnit | The backend body/table record that consumes one selector in the current SNES generator. | `ObjectProgram(room=7,object=118)` |
| ResidentBinding | A future temporary mapping from canonical ProgramUnit identity to a currently usable selector. | `ObjectProgram(...) -> ResidentBinding` |
| Selector | Current VM byte handle for generated size/fetch dispatch. | Not part of either source identity |
| Bundle | Resource ownership/loading group. | `RoomBundle(7)` |
| Pin | A live reason an ephemeral binding cannot be reassigned. | Active C4 slot or saved continuation |

The invariant is:

```text
semantic executable corpus size
    != selector-bearing ProgramUnit count
    != addressable ProgramUnit set for a chosen bundle/resolver scope
    != simultaneous live/pinned ProgramUnit set
```

`program_units.py` derives the mapping from the shared compiler IR and room
compilations. Global, entry, exit, and local scripts each map to their own
ProgramUnit. Each `ObjectVerb(room,object,verb)` maps to the `ObjectProgram`
for its owning object. The complete OBCD record and verb-entry offsets remain
the backend representation; per-verb source identities, PCs, offsets, and
hashes remain independently recorded. The current generator also emits an
OBCD selector-bearing record for an object with no decoded verb body, so those
records are counted in the current backend projection rather than silently
omitted.

Machine-readable outputs are:

- `program_units.json`: selector-free unit records, exact semantic-to-unit
  mapping, per-unit provenance and projected dependencies.
- `residency_manifest.json`: room-bundle membership, global candidates,
  cross-unit dependencies, pin reasons, and unresolved residency edges. It
  contains no assigned selector values.
- `residency.json`: addressability and liveness questions, reported separately.

Every parsed semantic executable maps exactly once. Units may contain several
semantic object-verb identities; an OBCD unit can also have no semantic verb
members when the current generator emits an object record with an empty verb
table.

## Canonical DOS-CD FATE result

Input: `/home/chad/ATLANTIS.zip`, profile
`fate_of_atlantis_dos_cd.json`, game identity
`indy4-fate-dos-cd-en` (DOS CD English, full voice, 1993). Source data remains
external. No selector was allocated.

| Measure | Discovered value | Epistemic note |
|---|---:|---|
| Semantic executable identities | 4,100 | Lower bound; rooms 89–91 remain unparsed. |
| Mapped semantic identities | 4,100 | Exactly once among currently parsed executable records. |
| Backend ProgramUnits | 2,788 | Lower bound for the same unparsed-room reason. |
| GlobalProgram | 163 | Exact for indexed global script directory. |
| RoomEntryProgram / RoomExitProgram | 93 / 93 | One each for parsed rooms. |
| RoomLocalProgram | 1,077 | Parsed source locals. |
| ObjectProgram | 1,362 | One current-backend OBCD record per parsed object. |
| Object-verb semantic identities | 2,674 | Preserved separately and grouped into object units. |
| ObjectProgram units with no semantic verb body | 593 | Still emitted as selector-bearing OBCD records by the current generator. |

The 2,674 semantic object verbs map into 1,362 ObjectPrograms (maximum 11
semantic verb identities in one unit). Room 7 independently reproduces the
reviewed reconciliation:

```text
79 semantic executable records
 2 RoomEntry/RoomExit units
18 RoomLocal units
24 ObjectProgram units, containing all 59 verb identities
--------------------------------
44 ProgramUnits
```

The integration test checks both totals, the breakdown, all 59 independent
semantic mappings, and the authored object 118/119 dependency projections.

## Room bundles and selector addressability

Largest room bundles by ProgramUnit count:

| Rank | Room | Semantic records | ProgramUnits | Lifecycle | Locals | Objects |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 98 | 2 | 128 | 2 | 0 | 126 |
| 2 | 55 | 52 | 87 | 2 | 19 | 66 |
| 3 | 50 | 139 | 75 | 2 | 18 | 55 |
| 4 | 20 | 21 | 65 | 2 | 19 | 44 |
| 5 | 40 | 121 | 64 | 2 | 36 | 26 |
| 6 | 46 | 152 | 64 | 2 | 29 | 33 |
| 7 | 29 | 69 | 61 | 2 | 22 | 37 |
| 8 | 66 | 32 | 56 | 2 | 17 | 37 |
| 9 | 51 | 74 | 55 | 2 | 7 | 46 |
| 10 | 36 | 47 | 50 | 2 | 23 | 25 |

Room 98's large unit count with only two semantic script records reflects 126
source OBCD object records with no decoded verb bodies. They still count for
this backend projection because the current generator emits selector-bearing
OBCD records for those objects.

Corrected cases:

| Resolver scope | Semantic records | Room ProgramUnits | Global ProgramUnits | Addressability result |
|---|---:|---:|---:|---:|
| Room 43 + decoded static/conditional global targets | 174 | 40 | 11 unique | 51; below 178 |
| Room 46 + decoded static/conditional global targets | 152 | 64 | 15 unique | 79; below 178 |
| Room 46 + all decoded dynamic global candidates | 152 | 64 | 163 candidate globals | 227 candidate units; may exceed 178, not a live set |
| Largest parsed room bundle, room 98 | 2 | 128 | 0 decoded | 128; below 178 |

Thus the earlier room-43 `174 + 11 = 185` selector assertion is incorrect:
174 was semantic IR count. The correct backend set is `40 + 11 = 51`.
Room 46's 227 is likewise a candidate-universe bound: a dynamic global
selector does not mean all 163 candidate ProgramUnits must be bound at once.
Rooms 46 and 97 have decoded dynamic candidate bounds above 178; no known
room's decoded static/conditional addressability set exceeds 178. Three
unparsed rooms and opaque tails remain uncertainty, not evidence of a specific
overflow.

The whole 2,788-unit known source corpus cannot be assigned unique selectors
in one current static selector map (`2,788 > 178`, definite for the known
corpus). That does not mean 2,788 units must be resident simultaneously.

Per-room "room + globals" values above are the room bundle plus its directly
decoded static/conditional `StartScript`/`chainScript` target units. They are
not a transitive whole-game closure: global-to-global targets are reported in
the global resolver target sets. A future static binder must account for the
selected global resolver population as well as each room bundle; this report
does not imply all candidate globals are simultaneously resident.

## Globals and live working sets

There are 163 available global ProgramUnits: 3 are root/definitely reachable,
131 conditional, and 29 possible. The decoded graph contains 46 unique static
global targets, 125 conditional-static targets, and 8 dynamic global edges;
their dynamic candidate union spans all 163 globals. Eighty-two globals
contain a yield operation; 15 contain both a yield and a room-load operation.
These are potential cross-room identity-retention candidates, not proof that
all such activations overlap.

Static/conditional room addressability peaks at 128 known units (room 98); all
parsed room scopes fit the 178-selector pool. Room 46's decoded dynamic union
is 227, but a resolver can bind only the global target actually selected.
Room transitions remain staged: outgoing EXCD/cleanup precedes commit and
incoming ENCD. The whole incoming and outgoing room bundles need not be
resident together.

Static source analysis cannot prove an exact maximum set of concurrently live
ProgramUnits. The existing scheduler has exactly 25 C4 activation slots. Under
the proposed resolve-on-activation contract, this provides a conservative
upper bound of 25 distinct active selector pins; it does not prove that 25 are
simultaneously used. Inactive object/local entries must therefore be addressed
by bundle-local indices, not by prebinding every dynamic candidate.

The three capacity questions remain separate in `residency.json`:

1. **Source corpus:** 4,100 semantic identities, 2,788 current-backend units.
2. **Addressable set:** largest room bundle 128; largest known static room +
   globals 128; largest decoded dynamic candidate union 227.
3. **Simultaneously pinned:** unknown exact maximum; no more than 25 active
   slot bindings under the proposed lazy resolver contract.

## Selector references and pinning contract

The selector is currently a build-global static byte, not a dynamic cache
entry. Generated room/global tables and size/fetch dispatch use the same
selector mapping. Selector reuse is unsafe until every old reference is gone,
pinned, or represented by a canonical identity that can be resolved again.
The generator's candidate pool is `$D0..$FF` plus `$CF..$4E` (178 byte values);
the allocator also validates the complete pool against reserved built-in IDs.

| Cause/reference | Current selector-bearing state | Lifetime/release | Portable identity now? |
|---|---|---|---|
| Active script | `C4_SLOT_PROGRAM` (`SAME_SCUMM_C4_SLOT_PROGRAM = $7E23B2`, 25 bytes), beside status/number/PC/delay/locals | From allocation through stop, replacement, or retirement | Not in selector byte; script/slot context is separate |
| Yielded/delayed script | Same occupied C4 slot | Across frames until resume and retirement/replacement | No standalone canonical unit field |
| Nested parent/child | Parent and child C4 slots; `C4_PARENT_PROGRAM = $7E2A8E` is temporary parent scratch | Both until child return or parent abort | Parent slot carries its selector |
| Room transition return | `M23A_RETURN_PROGRAM = $7FF2C3`, `RETURN_VALID = $7FF467`, `RETURN_SLOT = $7FF468`, and return PC; surviving global slot retains its own selector | Transaction completes or continuation is invalidated | No; return byte is a selector snapshot |
| Cutscene override | `C19_OVERRIDE_PC = $7FD354` plus `C19_OVERRIDE_SLOT = $7FD35E`; owning C4 slot still carries selector | Override resumes/clears or slot retires | Through the owning slot only |
| Sentence script | Ordinary C4 slot program selector | Sentence activation retirement | No standalone canonical selector field |
| Room entry/exit | `M23A_ENTRY_PROGRAM = $7FF2CD` / `M23A_EXIT_PROGRAM = $7FF2CE`; generated active room directory also contains selector references for room programs | Active room record replacement; transitions use outgoing then incoming phases | Room record gives role/context, not relocatable selector identity |
| Current execution | `SAME_SCUMM_PROGRAM_SELECT = $7E2362` scratch | Current fetch/dispatch; restored from slot/room record | Transient alias, not an independent long-lived owner |
| Native emulator savestate | Raw WRAM selector bytes and selector-bearing room state | Until save discarded; restore against matching ROM tables | No cross-build identity without matching program map |
| Host save | Host `ScriptSlot` resource/script identity, PC, locals, scheduler state | Portable host save lifetime | Yes; host reconstructs from provider |
| Native custom save envelope | Does not serialize the live C4 activation table in the inspected storage path | Save payload lifetime | Not an active scheduler restore format |

The generated room directory is also an important selector reference even
though its records reside in ROM rather than C4 state. A future paged design
must replace those embedded selector bytes (including the entry/exit fields)
with bundle-local ProgramUnit indices or keep every referenced binding pinned
for the directory's lifetime. The recommended design is to use local indices
and resolve on invocation, avoiding an eager pin of every inactive OBCD.

The scenario selector snapshots at `$7E56xx` and `$7E5Fxx` are compile-gated
fixture/diagnostic state, not production activation owners or portable program
identities. The selector-bearing production locations above were checked
against `runtime/snes/kernel/memory.pasm` and their dispatch/transition
callers; a future binder must account for those production references before
reusing a byte selector.

Pin ownership in a future runtime:

- The scheduler owns activation pins. A normal start pins the callee before
  publishing its slot; nested caller and child pins coexist. Same-identity
  replacement/`chainScript` releases the retired activation only after the
  replacement identity is secured.
- Yield/delay preserves the slot pin. A global activation surviving room
  transition keeps its canonical ProgramUnit identity pinned; room/local
  callers retired at commit release theirs.
- Cutscene override records refer to the owning slot and need no additional
  ProgramUnit pin beyond that slot.
- Sentence and room entry/exit executions use ordinary activation pins.
- A room bundle loader owns the bundle's source/resource mapping; bundle
  directories contain local indices, not ephemeral selectors.
- A pending transaction stores canonical return identity or a reference to
  its still-pinned slot, never an unowned selector byte.
- Exhaustion must fail/defer explicitly. It must never overwrite a selector
  while any live owner still refers to the prior unit.

Portable saves should store canonical ProgramUnit identity, PC, locals,
ownership, and continuation relationships, then rebuild pins on restore.
Emulator savestates remain build-bound because they snapshot raw WRAM.
Existing formats are unchanged in this milestone.

## Synthetic contract acceptance

The generated copyright-free analysis case has 300 OBCD semantic verb
identities across 30 object units, plus 200 global candidates; semantic corpus
size is larger than the 178-selector pool while each room-local unit set is
small. A pure Python binding simulator pins a yielded global across a room
transition, resolves one member of a 200-global dynamic candidate universe,
and verifies that a fourth binding fails while all three test selectors are
pinned. After a room pin is released, an unpinned selector can be reused while
the yielded global's selector remains unchanged. The simulator is not used by
production execution.

## Recommendation and next seam

**Recommendation B — canonical ProgramUnit → bundle-local index → ResidentBinding
→ ephemeral selector.** The whole corpus exceeds 178 as a single static map,
but every known parsed room's static addressability set fits. The dynamic
candidate union must not be prebound. A compact resolver/binder allows the
backend to package many bundles while pinning only active slot identities.
This conclusion is conditional on migrating selector-bearing room/global
directory fields to canonical or bundle-local identities before reuse.

Next implementation milestone: generate a selector-free executable directory
with stable ProgramUnit IDs and per-bundle local indices, then exercise a
generic resolver/pin lifecycle against the simulator. Do not alter the native
selector ABI until directory references, pending transitions, slot
continuations, cutscene slots, and portable-save reconstruction are specified.
