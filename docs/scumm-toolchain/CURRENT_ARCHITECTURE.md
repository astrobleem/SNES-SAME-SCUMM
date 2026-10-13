# Current SCUMM/SAME Architecture

This map records the source-bound room compiler, whole-game analyzer, native
resident resolver, and current semantic-capability checkpoint. It does not
claim whole-game runtime support: each operation still has independent
front-end, IR, host, backend, native-runtime, and save evidence. “Current
layer” is the dominant responsibility of a component; some modules cross
boundaries.

| Component | Responsibility; inputs → outputs | Consumer | Current layer | Desired layer |
|---|---|---|---|---|
| `src/same/profile.py`, `src/same/capabilities.py` | Validate engine identity, resource bindings, timing, video/input and capabilities → `EngineProfile`. | SAME host/bootstrap | `SAME_GENERIC` | Keep the generic profile envelope; move SCUMM source/build policy into typed front-end/profile records. |
| `src/same/engine.py`, `resources.py`, `video.py`, `input.py`, `save.py` | Lifecycle, host services, resource access, normalized I/O and save envelope → engine-facing contract. | All host engines | `SAME_GENERIC` | Remain platform abstractions; do not learn SCUMM archive formats or SNES memory. |
| `src/same/engines/scumm_v5/policy.py` | Parse SCUMM-specific resource, audio, geometry/presentation and copy-protection options. | SCUMM host and adapters | `GENERIC_SCUMM` | Typed source-edition policy; split backend realization preferences from source identity. |
| `src/same/engines/scumm_v5/resources.py` | Decrypt/validate v5 indices/containers and expose stable `room.N`, `script.N`, `sound.N`, `costume.N`, `charset.N` keys. | Host runtime and cookers | `GENERIC_SCUMM` | Front-end resource catalog with archive/member/offset provenance. |
| `room.py`, `costume.py`, `font.py`, `text.py`, `embedded_audio.py` under the SCUMM v5 package | Decode source room/object/verb/walkbox, costume, charset, text-control and embedded-audio structures. | Host, cookers, asset generators | `GENERIC_SCUMM` | Front-end parsers producing validated target-neutral resource data. |
| `src/same/engines/scumm_v5/room_compiler.py`, `game_analysis.py`, `capability_frontier.py`, `program_units.py`, `selector_demand.py`, `residency.py`, `residency_contract.py` | Reuse room IR; inventory source executables/resources; separate structural decode, semantic IR and support evidence; emit source-bound graph, readiness and selector-free residency data. | Room/game compiler CLIs, tests, backend planning | `GENERIC_SCUMM` | Keep analysis target-neutral; enrich support evidence from generic conformance controls. |
| `src/same/engines/scumm_v5/engine.py` | Interpret v5 bytecode; own scheduler, variables/bits, slots, actors, object state, verbs, room lifecycle, messages, cutscenes and logical sound requests. | SAME `EngineHost`, semantic tests | `GENERIC_SCUMM` | Preserve as host runtime/behavioral oracle; compare compiled operation execution against it. |
| `cooked_room.py`, `room_visual.py` | Encode/decode versioned SC5C/SC5VIS records, source/profile/archive hashes and executable directories. | Host provider, build generators, native runtime | `GENERIC_SCUMM` | Stable compiler interchange/backend artifact schemas with explicit provenance. |
| `tools/cook_scumm_v5_rooms.py`, `tools/compile_scumm_room.py`, `tools/compile_scumm_game.py` | Room compiler emits SC5C/IR; game analyzer emits source census, GameIR projection, graph, reachability, capabilities and frontiers deterministically. | SNES generators, source-build tooling, developer/tests | `BUILD_TOOLING` + `GENERIC_SCUMM` front end | Keep legacy room cooker; Milestone 3 may consume trusted analysis to derive backend manifests. **Room compilation and game analysis implemented, partial.** |
| `tools/generate_snes_cooked_rooms.py`, `backend_layout.py`, `compile_scumm_v5_source_image.py` | Emit legacy static or canonical dynamic ProgramUnit directories, share verified immutable room/body bytes, place source resources/tables, preflight LoROM pages and produce a source-bound byte ledger. | SNES build, M23A resource service, full-source diagnostics | `SNES_BACKEND` + `BUILD_TOOLING` | Keep source IDs selector-free; use manifest-owned inputs and a checked target-specific storage plan. |
| `tools/generate_snes_scumm_variables.py` | Derive source variable capacity or synthetic equivalent; emit WRAM symbols and identity manifest. | Assembly and memory audits | `SNES_BACKEND` | GameIR source limits plus target-specific WRAM layout report. |
| `tools/generate_snes_room_visuals.py`, `generate_snes_scumm_charset.py`, actor/object sprite generators | Convert decoded visual/font/costume/object source to bank-safe SNES data and descriptors. | Native rendering services and ROM build | `SNES_BACKEND` | Keep source parsing upstream; retain target palette/tile/bank packing here. |
| `src/same/engines/scumm_v5/audio.py`, `same.music`, SCUMM/FATE music import tools | Preserve logical audio intent and build score realizations; title adapters read external formats. | Host audio services and SNES audio build | `GENERIC_SCUMM` + `BUILD_TOOLING` | Generic sound IR, title importer/profile, backend realization. |
| `runtime/snes/engines/scumm_v5*.pasm` | Native bytecode fetch/dispatch, scheduler, SCUMM state, interaction, movement, room transactions, resident ProgramUnit resolver and visual handoff. | Active engine in SNES kernel | `SNES_BACKEND` implementing generic semantics | Preserve byte selector as ephemeral handle; continue generic semantic conformance and eventually consume more compiler-generated operations/tables. |
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
allocates no native selectors. Dynamic/unresolved dependencies preserve
closure uncertainty. The current canonical DOS-CD FATE corpus has 96 indexed
and parsed rooms and 116,730 structurally decoded instructions; current
normalized semantic IR covers all observed instructions. Whole-game execution
support remains explicitly NOT READY because known host gaps and backend/native
support evidence remain. See `CAPABILITY_ANALYSIS.md` and
`CAPABILITY_FRONTIER_BURN_DOWN.md` for the measured frontier.

`selector_demand.py` distinguishes source semantic executables, OBCD resource
records, executable carriers, selector units, and resident bindings. Passive
object records have no selector. The current canonical full-source census is
96 parsed rooms, 4,108 semantic executable identities, 2,203 true selector
units, and 1,372 object resource records. The dynamic resolver maps canonical
ProgramUnit IDs to temporary byte selectors; legacy static mode remains
available. See `MILESTONE_6_TRUE_SELECTOR_DEMAND.md` and
`WHOLE_SOURCE_BACKEND.md` for the dispatch trace and current storage boundary.

`residency_contract.py` consumes that selector-free directory in the simulator;
the accepted native resolver uses canonical ProgramUnit IDs, generated
global/room directories, temporary selector bindings, generations and live
activation pins. The bounded deterministic FATE route has passed with dynamic
residency and matches the static control at semantic checkpoints. Separately,
the compiler can emit all parsed source ProgramUnits, but full FATE does not
fit the current directly addressed 4 MiB LoROM target. This proves the route
and source representation, not whole-game FATE support; see
`WHOLE_SOURCE_BACKEND.md`.

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
callable selectors. The corrected full-source directory has 2,203 Selector
Units, while the accepted runtime binds only a bounded resident subset.
Whole-source body emission is complete for the current parsed corpus, but the
ROM payload/layout exceeds the current carrier; addressability, image storage,
and simultaneous residency remain separate constraints.

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

## Integration checkpoint (2026-10-13)

The merged implementation is an experimental SCUMM v5 toolchain/runtime, not a
whole-game release. The accepted bounded DOS-CD FATE replay is
`0 → 68 → 0 → 4 → 5 → 6 → 7 → 3`; its static and dynamic runs were compared at
normalized semantic checkpoints. The complete source package represents the
currently parsed corpus through compiler-generated ProgramUnit and room
directories, with executable and supported room payloads stored in SAMEPKG.
The package directory is not a claim that every operation, resource, or room
can execute.

The native contract remains a 178-selector resident window over stable 16-bit
ProgramUnit identities. Checked MSU reads feed instruction-aligned bytecode
pages and versioned live-room metadata; ROM-backed operation remains available.
SC5LIVE v4 separates compact active metadata from checked route data, and route
values are validated as walkbox indices or the `0xFF` no-route sentinel. The
focused boundary controls accept 6,143- and 6,144-byte active records and reject
6,145 before publication. This does not imply portable streamed-script save
restoration.

Current evidence and limits:

- The source analyzer reports 96 indexed/parsed rooms, 4,108 semantic
  executable identities, 2,203 selector-bearing ProgramUnits, and 2,376
  checked code pages. The full-source package and directory are deterministic;
  native execution remains bounded to the documented controls.
- Native live-room metadata probes are established for rooms 4, 40, 43, 51,
  55, and 66. Diagnostic native startup probes for rooms 78 and 98 remain
  unverified; host structural/capacity validation is not counted as native
  consumption.
- SCUMM semantic families remain unsupported or unverified; original graphics,
  costume/charset/font and general text conversion, broad audio/iMUSE service,
  dynamic resource closure, and portable save reconstruction remain incomplete.
  Full-game execution readiness is **NOT_READY**.
- GitHub-hosted CI runs the host suite, static/package checks, WRAM audit, and
  pinned Poppy SNES assembly/ROM audit. It does not run Nexen; assembly is not
  native emulator acceptance. No physical FXPAK result is claimed.
- The pinned Poppy dependency restore reports ImageSharp NU1902/NU1903
  advisories. Follow-up is tracked in repository issue
  [#11](https://github.com/astrobleem/SNES-SAME-SCUMM/issues/11); auditing is
  not disabled or suppressed.

No FATE-specific production hooks were added. FATE room/script/object IDs and
the bounded replay remain integration evidence only; SCUMM v5 semantics and
storage interfaces are generic.
