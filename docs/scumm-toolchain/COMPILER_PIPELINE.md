# Compiler Pipeline and Resource Dependencies

## Intended flow

```text
external game files + thin edition profile
  -> SCUMM front end: identify/decrypt/parse resources
  -> GameIR + source map
  -> capability and dependency analysis
  -> SNES backend: layout/encode/package
  -> generated resource tables and ROM data
  -> existing generic SCUMM/SAME runtime
```

**Status:** source-room compilation, whole-source analysis, normalized
semantic IR, complete ProgramUnit directory emission, source-body
reconciliation, and pre-assembly target-layout rejection are implemented for
the current canonical DOS-CD FATE corpus. It contains 96 parsed rooms, 4,108
semantic executable identities, and 2,203 selector-bearing ProgramUnits.
Structural decode, semantic IR, host behavior, backend lowering, native
execution and resource support remain independent. The full source payload
does not fit the current 4 MiB LoROM mapping, and whole-game readiness remains
NOT READY. See `WHOLE_SOURCE_BACKEND.md` for the byte ledger and measured
boundary.
`tools/compile_scumm_room.py` and the room cooker use the same
`room_compiler.compile_room_payload` API. The cooker remains available as the
legacy selection/visual CLI, and its output continues to use the existing
SC5C record format.

`tools/compile_scumm_game.py --analyze` enumerates a raw source edition through
the same resource provider, invokes `compile_room_payload()` for each room,
and invokes the same `decode_script()` for global scripts. `v5_opcode_schema.py`
defines opcode families, parameter flags, operand forms and default control
flow; operation decoders add subcommand-specific boundaries. A known-width
semantic-unsupported instruction remains in the IR and dependency walk. Only
unknown structure/truncation becomes an opaque frontier. For the current
canonical DOS-CD FATE corpus, every parsed instruction has normalized semantic
IR. The CLI emits
canonical semantic identities and resource identities, graph certainty,
root-based reachability, capability dimensions and opaque frontiers without
SNES selector allocation. A source room rejected by the current room decoder
remains inventoried with an explicit unsupported status and diagnostic. The
current FATE archive's 96 indexed rooms all parse through the generic decoder.
The remaining release frontier is implementation/support evidence, not a
current FATE structural-decoder gap; see
`CAPABILITY_FRONTIER_BURN_DOWN.md`.

This is incremental. Existing profile loading,
`LucasartsScummV5ResourceProvider`, room decoders, cooked-room codecs and
cookers are retained and adapted; a second resource parser is not proposed.

## Front-end boundary

The front end owns dialect/version, archive/index structures, resource
discovery, rooms/chunks, objects/verbs, scripts and operands, actor/variable/
string/costume/sound references, source offsets, control-flow checks and
source-level dependencies. Its public output is target-neutral. It must not
import Poppy, name WRAM, encode LoROM addresses or know 65816 register width.

Current seeds include `policy.py`, `resources.py`, `room.py`, `costume.py`,
`font.py`, `text.py`, `embedded_audio.py` and `cook_scumm_v5_rooms.py`. Separate
discovery/parse APIs from CLI orchestration gradually.

## Thin profile boundary

Keep in a game/edition profile: stable game and edition identity, dialect,
original archive/member layout, resource key templates, authentic source
quirks that are actually demonstrated, and title audio import policy. The
Fate templates' `snes_global_script_sets`, execution gates, and long lists of
selected rooms/executables are useful transitional build roots, but are not
language semantics. Move their derived portions to an analyzed build manifest
containing selected roots, transitive closure, target capacities and backend
choices. Retain explicit root overrides for diagnostics and intentionally
partial builds.

Do not hand-maintain hundreds of room/script/object records in profile JSON.
The front end should derive resource inventories and metadata from source;
the profile should identify which source edition and any genuine policy
exceptions.

## Implemented room-bundle slice

The adapter emits source-bound room, entry/exit/local, object and verb records;
instructions with separate structural and semantic status in the currently
covered generic v5 forms; direct/dynamic call, room, sound, music, costume and
resource-routine dependencies; variable/bit read/write observations; and
simple room capacity counts. A boundary that cannot be established becomes an
opaque tail retaining the remaining bytes and source location. The report
says `partial` when such tails exist. It does not prove all control-flow paths
or establish that every operation is supported by a selected runtime.
Whole-game graph walking exists, but closure remains explicitly incomplete at
dynamic references, unsupported room parses and reachable opaque bodies. Exact
structural coverage and residuals are in
`MILESTONE_3_STRUCTURAL_DECODER.md`.

The encoded SC5C record is byte-identical to the prior cooker for the checked
synthetic fixture and FATE room 7. `generate_snes_cooked_rooms.py` remains the
single selector allocator and emits the existing runtime tables. The standalone
CLI can invoke that generator with portable relative `.incbin` paths.

Whole-game analysis now also emits `residency.json`. This is a compiler
planning report, not a selector allocation pass: canonical source identities
remain independent of the current byte selector, and lifecycle edges describe
whether code may overlap, is staged across room commit, or remains uncertain.

## Dependency graph

Execution nodes use typed source identities such as `GlobalScript(n)`,
`RoomEntry(r)`, `RoomExit(r)`, `RoomLocal(room=r,local=n)` and
`ObjectVerb(room=r,object=o,verb=v)`. Resource nodes use distinct identities
such as `ScriptResource(n)`, `RoomResource(r)`, `Costume(n)`, `Charset(n)` and
`Sound(n)`. Each edge records
kind, source span, confidence and resolution:

| Edge | Static source | Confidence policy |
|---|---|---|
| Script → global/local script | Literal `startScript` / `chainScript`; source context resolves namespace | `definite` for literal target; `possible` for variable target/range |
| Object verb → script body | OBCD verb entry offset and decoded object code | `definite` when the verb directory is complete |
| Script → object verb | Literal `startObject` target/verb | `definite` for literals; `possible` for dynamic operands |
| Room → entry/exit/local scripts | ENCD, EXCD, LSCR chunks | `definite` for selected room resources present |
| Script → room | `loadRoom`, `loadRoomWithEgo`, pseudo-room mapping | `definite` for literal physical target; conservative for variables/maps |
| Room → objects | OBCD/CDHD tables | `definite` for decoded local objects |
| Actor → costume | Actor setup and costume operations | Definite or possible based on operand constancy |
| Script → string/sound | Text/audio operands and source directories | `definite` for literal IDs; `possible` for indirect IDs |

Edges distinguish `STATIC`, `CONDITIONAL_STATIC`, `DYNAMIC` and `UNRESOLVED`.
Reachability is a lattice (`ROOT`, `DEFINITE`, `CONDITIONAL`, `POSSIBLE`,
`UNRESOLVED`, or `UNREACHED`) and retains known paths. Dynamic selectors are
not guessed. A reached opaque body makes closure incomplete; bytes beyond its
boundary provide no negative evidence about calls, capabilities or effects.
Native observed events remain separate from this source graph.

## SNES backend boundary

The backend owns selector allocation, ROM-bank layout, generated Poppy/data,
WRAM/capacity checks, compact operation encoding, room/verb directories,
resource packaging, image/palette/tile conversion, charset packing, audio
binding and target-to-source maps.

Legacy static builds use stable byte selectors. Dynamic-residency builds use
the accepted native resolver: a canonical `u16` ProgramUnit ID resolves to a
temporary member of the existing 178-byte selector pool. Room/global
directories are compiler-generated metadata; live C4 activations retain a
pinned selector and generation checks prevent stale dispatch. The 25-slot
active-script bound, total source units, ROM storage, and simultaneous
resident bindings are separate capacities. This architecture is accepted;
the current issue is whole-source storage, not selector residency.

The compiler projects semantic executables into selector-bearing `ProgramUnit`s
before backend layout. Global scripts, room entry/exit, and local scripts each
map to one unit. All semantic `ObjectVerb(room,object,verb)` records for a
single OBCD map to that object's `ObjectProgram`; verb source spans and hashes
remain independently preserved. Passive object records acquire no selector.
The full-source generator emits all 2,203 canonical ProgramUnits for current
FATE, retaining complete source room records and sharing verified body/prefix
bytes where address-safe. Backend descriptors preserve source identity, body
hash, room/bundle, dispatch and storage location; no source identity is
replaced by a selector.

The capacity analysis keeps separate answers for source semantic identities,
addressable ProgramUnits, and simultaneous live/pinned bindings. Dynamic
candidate unions are not interpreted as live sets. Current FATE room parsing
is complete for the indexed 96 rooms; storage placement remains invalid for
the target because it crosses LoROM mirror pages and exceeds physical
capacity. See `MILESTONE_5_PROGRAM_UNITS.md` for residency evidence and
`WHOLE_SOURCE_BACKEND.md` for the current layout ledger and missing storage
service.

Representation may vary by item:

- scripts: retain SCUMM bytecode initially; later use compact semantic ops or
  threaded/native sequences where measurements justify it; very hot, stable
  operations may become direct native primitives behind the same semantic
  contract;
- dispatch and directory metadata: ROM tables/generated assembly;
- static room geometry/object/verb defaults: precomputed tables, separate from
  mutable runtime state;
- backgrounds/costumes/fonts: backend-oriented payloads plus descriptors;
- large immutable assets: binary ROM data/incbin segments with generated
  descriptors and source maps;
- scheduler, actor motion, interaction, room-transaction state: runtime.

## Existing compiler-like chain

`cook_scumm_v5_rooms.py` reads source resources, selects rooms/globals,
retains offsets/hashes, emits SC5C rooms and manifests, and can emit SC5VIS
visuals. `compile_scumm_v5_source_image.py` drives all-source cooking and
directory generation; `generate_snes_cooked_rooms.py` retains the legacy
static allocator and emits dynamic canonical ProgramUnit directories plus
banked data. `backend_layout.py` verifies current-target placement and
accounts payloads before Poppy assembly. Specialized generators handle
variables, visuals, charset, actor/object sprites, engine selection and save
identity. These are pipeline assets to modularize, not replace.

The compiler-owned result now extends from source parsing through all parsed
FATE ProgramUnit descriptors and body storage metadata. A complete linked
FATE image is not emitted: preflight rejects before assembly because the
directly addressed room records alone exceed the 4 MiB LoROM target and the
planned pages exceed LoROM addressability. The copyright-free 191-unit
synthetic image does assemble and has native cross-bank fetch acceptance.
Selected static/dynamic FATE route builds remain separate, build-root-owned
regressions; neither one proves full-source execution or asset completeness.
