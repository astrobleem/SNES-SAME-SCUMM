# Current SCUMM/SAME Architecture

This map records the audited baseline, the source-bound room compiler, and the
partial whole-game analysis milestone. The compiler does not replace the VM or
decode all SCUMM v5 operations. “Current layer” is the dominant responsibility
of a component; some modules cross boundaries.

| Component | Responsibility; inputs → outputs | Consumer | Current layer | Desired layer |
|---|---|---|---|---|
| `src/same/profile.py`, `src/same/capabilities.py` | Validate engine identity, resource bindings, timing, video/input and capabilities → `EngineProfile`. | SAME host/bootstrap | `SAME_GENERIC` | Keep the generic profile envelope; move SCUMM source/build policy into typed front-end/profile records. |
| `src/same/engine.py`, `resources.py`, `video.py`, `input.py`, `save.py` | Lifecycle, host services, resource access, normalized I/O and save envelope → engine-facing contract. | All host engines | `SAME_GENERIC` | Remain platform abstractions; do not learn SCUMM archive formats or SNES memory. |
| `src/same/engines/scumm_v5/policy.py` | Parse SCUMM-specific resource, audio, geometry/presentation and copy-protection options. | SCUMM host and adapters | `GENERIC_SCUMM` | Typed source-edition policy; split backend realization preferences from source identity. |
| `src/same/engines/scumm_v5/resources.py` | Decrypt/validate v5 indices/containers and expose stable `room.N`, `script.N`, `sound.N`, `costume.N`, `charset.N` keys. | Host runtime and cookers | `GENERIC_SCUMM` | Front-end resource catalog with archive/member/offset provenance. |
| `room.py`, `costume.py`, `font.py`, `text.py`, `embedded_audio.py` under the SCUMM v5 package | Decode source room/object/verb/walkbox, costume, charset, text-control and embedded-audio structures. | Host, cookers, asset generators | `GENERIC_SCUMM` | Front-end parsers producing validated target-neutral resource data. |
| `src/same/engines/scumm_v5/room_compiler.py`, `game_analysis.py`, `program_units.py`, `selector_demand.py`, `residency.py`, `residency_contract.py` | Reuse room IR; inventory legacy generated record candidates separately from callable carriers/SelectorUnits; emit selector-free directories and residency analysis. | Room/game compiler CLIs, tests, backend planning | `GENERIC_SCUMM` | Feed true SelectorUnit directories to a backend resolver/binder. **Analysis implemented; production binding remains planned.** |
| `src/same/engines/scumm_v5/engine.py` | Interpret v5 bytecode; own scheduler, variables/bits, slots, actors, object state, verbs, room lifecycle, messages, cutscenes and logical sound requests. | SAME `EngineHost`, semantic tests | `GENERIC_SCUMM` | Preserve as host runtime/behavioral oracle; compare compiled operation execution against it. |
| `cooked_room.py`, `room_visual.py` | Encode/decode versioned SC5C/SC5VIS records, source/profile/archive hashes and executable directories. | Host provider, build generators, native runtime | `GENERIC_SCUMM` | Stable compiler interchange/backend artifact schemas with explicit provenance. |
| `tools/cook_scumm_v5_rooms.py`, `tools/compile_scumm_room.py`, `tools/compile_scumm_game.py` | Room compiler emits SC5C/IR; game analyzer emits source census, GameIR projection, graph, reachability, capabilities and frontiers deterministically. | SNES generators, source-build tooling, developer/tests | `BUILD_TOOLING` + `GENERIC_SCUMM` front end | Keep legacy room cooker; Milestone 3 may consume trusted analysis to derive backend manifests. **Room compilation and game analysis implemented, partial.** |
| `tools/generate_snes_cooked_rooms.py` | Allocate stable executable selectors, serialize directories, place data in LoROM banks, emit Poppy includes/binaries/reports. | SNES build and M23A resource service | `SNES_BACKEND` | Backend layout/encoding over analyzed identities, preserving selector stability. |
| `tools/generate_snes_scumm_variables.py` | Derive source variable capacity or synthetic equivalent; emit WRAM symbols and identity manifest. | Assembly and memory audits | `SNES_BACKEND` | GameIR source limits plus target-specific WRAM layout report. |
| `tools/generate_snes_room_visuals.py`, `generate_snes_scumm_charset.py`, actor/object sprite generators | Convert decoded visual/font/costume/object source to bank-safe SNES data and descriptors. | Native rendering services and ROM build | `SNES_BACKEND` | Keep source parsing upstream; retain target palette/tile/bank packing here. |
| `src/same/engines/scumm_v5/audio.py`, `same.music`, SCUMM/FATE music import tools | Preserve logical audio intent and build score realizations; title adapters read external formats. | Host audio services and SNES audio build | `GENERIC_SCUMM` + `BUILD_TOOLING` | Generic sound IR, title importer/profile, backend realization. |
| `runtime/snes/engines/scumm_v5*.pasm` | Native bytecode fetch/dispatch, scheduler, SCUMM state, interaction, movement, room transactions and visual handoff. | Active engine in SNES kernel | `SNES_BACKEND` implementing generic semantics | Preserve semantics; gradually consume compiler-generated operations/tables rather than source encodings. |
| `runtime/snes/kernel/*`, `runtime/snes/services/*` | Frame/lifecycle, input polling, storage, video/audio and cartridge services with 65816/SA-1/WRAM contracts. | All native engine personalities | `SAME_GENERIC` | Stable target service API, isolated from SCUMM source syntax. |
| `tools/build_snes.sh`, `generate_snes_engine_selection.py`, Make targets | Select build personality/features/profile, generate includes, invoke Poppy and audit ROM/map identities. | Developers/CI | `BUILD_TOOLING` | Keep orchestration; feed it a compiler-produced build plan. |
| `examples/profiles/templates/fate_of_atlantis_*.json` | Identify Fate edition/archive keys, title policy, resource templates, optional audio/presentation settings, and selected script groups. | Profile loader, Fate cook/build | `FATE_SPECIFIC` | Thin edition profile; derived selection/capacity tables should be compiler output. |
| `tools/fate_replay.py`, `tools/replay_fate_room4_cold_nexen.py`, `examples/replays/*`, Fate validators | Check controller actions, source hashes/offsets, selector mappings, and authored state transitions against a specific ROM. | Tests/native acceptance | `TEST_FIXTURE_INFRASTRUCTURE` | Retain as source/ROM-bound integration corpus over compiler outputs. |
| `examples/resources/scumm_v5/*`, `tests/test_scumm_v5_*`, controller fixture builders | Copyright-free scripts/rooms/profiles and expected host/native behavior. | Host tests, conformance ROMs | `TEST_FIXTURE_INFRASTRUCTURE` | Grow into semantic micro-fixtures and a tiny compiled fixture game. |

## Existing seam and leakage

The host and native engines share behavior through conformance, not yet through
a common compiled operation representation. Both still execute source-like
SCUMM bytecode at runtime. For cooked rooms and whole-game analysis, raw source
flows through the shared v5 family/operand schema and bounded `RoomIR`/
`InstructionIR` API before unchanged SC5C encoding. Known instruction width is
kept distinct from semantic-IR and target support; only unknown boundaries,
truncated operands or uncertain control flow create opaque frontiers.

The most useful existing seam is the source-bound cooked room: SC5C preserves
the source ROOM payload while adding validated executable directory metadata;
SC5VIS carries decoded pixels/palette and hashes. The new room compiler wraps
existing parsers and adds a narrow semantic IR before SC5C; it does not replace
the runtime payload contract.

`game_analysis.py` builds whole-edition inventory and graph projections from
the same `RoomBundleCompilation` and `decode_script()` implementations. It
allocates no native selectors. Dynamic/opaque dependencies preserve closure
uncertainty. The configured boot global now decodes structurally to completion
and the source-wide known-boundary count has expanded substantially; three
FATE rooms remain inventoried but unsupported by the room BOXD representation,
with diagnostics retained instead of omission. See
`MILESTONE_3_STRUCTURAL_DECODER.md` for exact external-corpus counts and
remaining boundaries.

`selector_demand.py` refines the earlier ProgramUnit projection into distinct
source semantic executables, OBCD object resource records, VM-enterable
executable carriers, selector units, and future resident bindings. The old
projection counted every parsed object record as a selector-bearing unit;
593 FATE OBCD records have no verb entries and cannot pass the native
`Verb_Query` gate. The generator currently allocates an ID for those records
if included, but runtime dispatch never references those IDs. The new
`selector_demand.json` and `selector_residency.json` are authoritative for
selector demand; the older `program_units.json`/`residency.json` projection is
retained as historical compatibility data. See
`MILESTONE_6_TRUE_SELECTOR_DEMAND.md` for the backend/runtime trace and exact
room-7/room-98 reconciliation.

`residency_contract.py` now consumes that selector-free directory in a pure
compiler-side simulator. It models temporary selector bindings, generations,
multiple pin reasons, bundle load/release, global lookup, activation nesting,
room transitions, and portable canonical-identity restore. The CLI
`tools/simulate_scumm_residency.py` emits deterministic traces and capacity
reports. This proves the proposed contract over synthetic and compiler-known
FATE scenarios only; native runtime binding/pinning is not implemented and
actual scheduler liveness remains unknown.

The architectural invariant is:

```text
semantic executable count
    != object/resource record count
    != executable-carrier/SelectorUnit count
    != addressable SelectorUnit set
    != simultaneously pinned/live ResidentBinding count
```

Milestone 4's room-43 overflow claim (185 semantic records) was not a selector
overflow. Milestone 5 corrected semantic-to-object carrier grouping, but its
1,362 OBCD “ProgramUnits” still included 593 passive records. Milestone 6
traces actual native dispatch and separates those resource records from
callable selectors. The corrected full-source selector map is 2,195 units;
largest known room+static/conditional global set is 71, and the exact live
simultaneous set remains unknown.

Leakage to address incrementally:

1. Raw container/room knowledge is shared by host runtime adapters and cookers;
   consolidate around the existing parsers rather than fork them.
2. `generate_snes_cooked_rooms.py` mixes executable selection/allocation with
   SNES banking and assembly output; separate analysis from backend placement.
3. Fate profile options include selected global script sets/execution gates;
   some dependency closure is still accumulated by repeated build selection.
4. `SAME_BUILD_SCUMM_SCENARIO_FIXTURE` encloses title-root actor setup and a
   room-68-to-room-42 controller bootstrap in native source. This is a
   bring-up harness, not SCUMM semantics; keep it isolated and eventually
   replace it with an explicit fixture/bootstrap resource or retire it.

FATE remains a valuable build-scoped behavioral reference. This audit does not
extend its gameplay path or promote its room order to a language rule.
