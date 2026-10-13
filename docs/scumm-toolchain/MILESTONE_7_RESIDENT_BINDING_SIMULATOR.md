# Milestone 7: Resident-Binding Resolver and Pinning Simulator

Status: **IMPLEMENTED as a pure compiler-side contract model. Native resolver,
runtime selector reuse, and save-format changes remain PLANNED.**

## Identity and ownership contract

The simulator consumes `selector_directory.json` emitted by the compiler. It
does not allocate selectors in that directory and does not replace the source
identity model.

| Concept | Contract |
|---|---|
| `ProgramUnitIdentity` | Stable callable backend identity from the compiler directory. It has no selector, bank, address, or current-room field. |
| `BundleIdentity` | Resource/lifecycle group, currently the global directory or one room's callable units. |
| `ResidentBinding` | Temporary `ProgramUnitIdentity → Selector` mapping with a per-selector generation and explicit pin reasons. |
| `Selector` | One byte handle in the existing VM dispatch pool. It is ephemeral and is not portable source identity. |
| `Pin` | An owned reason that prevents reassignment; several independent pins can protect one binding. |

The supported pin vocabulary is `ACTIVE_SCRIPT_SLOT`, `YIELDED_SCRIPT`,
`NESTED_PARENT`, `ROOM_CONTINUATION`, `CUTSCENE_OVERRIDE`,
`ROOM_LIFECYCLE`, `SENTENCE_EXECUTION`, and
`SAVE_RESTORE_RECONSTRUCTION`. The simulator checks canonical identity before
resolving globals and fails explicitly for a missing global; dynamic candidates
are not prebound.

Bindings are deterministic: use a free selector first, otherwise evict the
least-recently-used unpinned binding, with pool order and canonical identity as
tie-breakers. A binding generation increments whenever a selector is assigned
again. Diagnostic `SelectorReference`s can therefore detect stale use. If all
selectors are pinned, resolution reports `RESIDENCY_EXHAUSTED` without
changing existing bindings.

## Bundle and transition policy

The initial policy eagerly binds and lifecycle-pins every true SelectorUnit in
the active room bundle. Passive resource records are absent from the bundle's
selector list. Global units are lazy: a global number resolves through the
generated global directory and only that requested unit is bound.

The modeled transition order is:

1. Run outgoing EXCD while the old bundle remains loaded.
2. Retire outgoing room-owned activations and their room-local continuations.
3. Release old bundle pins and reclaim units with no other live pin.
4. Bind the incoming room bundle and run its ENCD.
5. Preserve live global activations/continuations and their binding identity.

The policy does not require both complete room bundles to coexist. If a
non-room pin retains an outgoing unit, that unit remains bound; it is never
silently reassigned. Transition tests include a yielded global, a room-local
activation and continuation, and a compiler-discovered incoming bundle.

## Activation, continuation, and portable state

Activations retain canonical unit, PC, locals, parent relation, room ownership,
and a generation-checked diagnostic reference. A child pins its parent while
the child runs. Same-program replacement reuses the same canonical binding.
Yielded activations have an additional yielded pin. Room/cutscene continuation
records pin the canonical unit until released. Room retirement ends outgoing
room-owned activations and drops their owned continuation pins; global
continuations survive.

`snapshot()` is intentionally portable: it stores canonical identities,
program counters, locals, parent/continuation relationships, room ownership,
bundle state, and semantic pins, but no selector or binding generation.
`restore()` reconstructs bindings and activations in a fresh resolver. A
separate diagnostic snapshot may show current selectors and generations; it is
not a save format. The test demonstrates an activation moving from `$CE` to
`$A1` after restore while retaining identical semantic state.

## Selector-bearing native state: future ABI checklist

The runtime inspection recorded in Milestone 6 remains the basis for native
work:

| Current state | Current role | Future treatment before reuse |
|---|---|---|
| `C4_SLOT_PROGRAM` | Durable selector in each active/yielded activation slot. | **KEEP SELECTOR BUT PIN** for the complete slot lifetime; preferably add canonical identity to reconstruct/debug the binding. |
| `PROGRAM_SELECT` | Current fetch/dispatch selector scratch, normally restored from the current activation. | **RECOMPUTE FROM OWNER** at dispatch boundaries; do not treat the scratch byte as an independent long-lived owner. |
| `C4_PARENT_PROGRAM` | Temporary nested-allocation copy of the parent's slot selector. | **RECOMPUTE FROM OWNER** while allocating; the parent activation's slot is the pin owner. |
| `M23A_RETURN_PROGRAM` | Pending room-transaction selector snapshot paired with return slot/PC/validity. | **KEEP SELECTOR BUT PIN** through the transaction, or migrate the transaction record to canonical identity; invalidate outgoing-local return state before releasing its pin. |
| `M23A_ENTRY_PROGRAM` / `M23A_EXIT_PROGRAM` | Active room lifecycle selector fields. | **KEEP SELECTOR BUT PIN** while the owning room directory is active; derive them again from the room bundle when entering it. |
| C19 override PC/slot records | PC and slot index; the owning activation slot supplies the program selector. | **RECOMPUTE FROM OWNER** via the pinned C4 slot; no independent selector pin is needed. |
| Sentence activation | Ordinary C4 activation for sentence execution. | **KEEP SELECTOR BUT PIN** as an active slot until completion. |
| Scenario return snapshots and observer fields | Compile-gated fixture or diagnostics. | **DIAGNOSTIC ONLY** unless separately shown to affect production dispatch. |

Native selector bytes carry no generation. The future runtime must make stale
reuse impossible by ownership/pinning or migrate long-lived references to a
canonical identity. A host save already reconstructs from source executable
identity. An emulator savestate contains raw WRAM selectors and remains tied to
the exact compatible ROM/program tables. The current native custom save
envelope does not serialize live C4 script activations, so it is not a
portable active-selector save. A future portable save should persist canonical
ProgramUnit identities, PCs, locals, room ownership and continuation
relations, then resolve and pin on restore. No format changes are part of
this milestone.

## Synthetic and FATE model results

Copyright-free tests cover pool fidelity/reserved values, reuse, generations,
multiple pins, LRU eviction, missing global lookup, bundle preflight,
room-local retirement, yielded globals across transitions, nested scripts,
same-program replacement, portable restore, explicit exhaustion, and a source
corpus/dynamic-global universe larger than the selector pool. These tests
exercise the model, not native runtime behavior.

The FATE integration consumes the canonical DOS-CD compiler directory and
models every parsed room at steady state, room bundles with the 25-slot
activation ceiling's worth of globals, compiler-discovered static or
conditional room-load transitions, the largest bundle with a yielded global
and on-demand dynamic global, and sequential requests into the largest
dynamic-candidate universe. It creates no gameplay trace and does not allocate
backend selectors into compiler output.

Canonical external run (DOS-CD English profile, source archive external):

| Observation | Result |
|---|---:|
| Parsed room bundles / available global SelectorUnits | 93 / 163 |
| Largest parsed room bundle | Room 40: 60 SelectorUnits |
| Room 40 yielded-global + dynamic-lookup scenario peak | 84 bindings |
| Room 40 → compiler-discovered room 41 transition | 84 binding peak; 25 activation slots peak; yielded global preserved |
| Compiler-discovered static/conditional room transitions modeled | 186; maximum transition residency 83 bindings |
| Largest simulated scenario across room/global cases | 85 bindings |
| Conservative modeled upper bound | 85 of 178 |
| Room 46 dynamic candidate universe | 216 total candidates (53 room units + 163 globals); one requested global bound at a time; 54 peak bindings |
| Selector exhaustion in modeled scenarios | No |
| Exact concurrent runtime liveness | Unknown |
| Parsed-room coverage caveat | 3 inventoried rooms remain unparsed |

The room-40 transition is compiler-derived from the graph, not a gameplay
claim. Room 46's 216-candidate set is not a simultaneous binding demand. The
overall 85 figure is the explicit conservative `max room bundle + 25 distinct
global activation bindings` calculation; it is not an observed native high
water mark.

Two separate canonical analysis directories (18 files each) and two separate
simulation directories (3 files each) were compared. Both file sets and all
contents matched; the simulator's internal two-run report also had equal
binding traces, capacity reports, and snapshot/restore semantics.

The conservative arithmetic bound is:

```text
largest parsed room SelectorUnit bundle
+ at most 25 distinct active global bindings
+ 0 extra room lifecycle units
```

Room entry/exit units are already part of each eager room bundle. The 25-slot
term deliberately does not assume that every slot is a global; it is a
conservative non-overlap bound. Exact concurrent liveness, selector snapshots
outside activation slots, and unparsed source rooms remain unknown. Passing
this modeled bound is not native safety certification.

Run the canonical model with:

```bash
python3 tools/compile_scumm_game.py \
  --source /path/to/external/ATLANTIS.zip \
  --profile examples/profiles/templates/fate_of_atlantis_dos_cd.json \
  --analyze --output /tmp/fate-analysis
python3 tools/simulate_scumm_residency.py \
  --analysis-dir /tmp/fate-analysis --output /tmp/fate-residency
```

## Next native implementation seam

The next milestone should add a generated canonical ProgramUnit directory and
a small native resolver/binder interface, only after this contract is
reviewed. The eventual WRAM state needs a selector-to-canonical-unit binding
table, canonical-unit-to-current-selector lookup, pin ownership/reference
counts, and invalidation/generation diagnostics. Room bundle load/release owns
room pins; activation/continuation owners acquire and release their pins.
Dynamic `StartScript` resolves one requested global via the directory. Missing
identities and exhaustion fail explicitly; neither case aliases another
program. Before reuse is enabled, migrate or pin every selector-bearing state
listed above and add bounded native tests for transitions, nesting, cutscene
resume, stale references, exhaustion, and portable save reconstruction.

No production runtime, SNES backend execution, allocator, or save format was
changed for Milestone 7.
