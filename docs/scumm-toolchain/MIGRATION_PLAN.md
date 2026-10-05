# Incremental Migration Plan

FATE progress and the current interpreters stay usable. Each phase adds a seam,
compares it against host/native behavior, and leaves existing paths available
until a new artifact participates in acceptance.

| Phase | Goal/components | New seam; retain/retire | Validation | Principal risk | Size |
|---|---|---|---|---|---|
| 0. Inventory | Current audit docs and coupling record. | No production change; preserve engines/replay. | JSON/doc consistency. | Inventory can become stale; keep it small and tested. | SMALL |
| 1. Front-end resource model | **Partial/implemented for rooms:** public checked chunk adapter, provider source locations, and source-bound room compiler input. | Keep resource/provider APIs as adapters; no runtime-format change. | Synthetic plus optional authentic source bytes, offsets and hashes. | Other resource kinds still lack a common source catalog. | MEDIUM |
| 2. Script IR slice | **Partial/implemented:** bounded v5 instruction records preserve raw bytes and stop at an opaque unknown-width tail. | Host/native interpreters remain unchanged; no basic-block IR yet. | Synthetic decoded/dynamic/opaque tests and FATE room-7 differential. | Do not present partial scripts as fully decoded. | MEDIUM |
| 3. Capability/dependency analysis | **Partial/implemented:** direct/dynamic calls, room/sound/resource references and room capacities. | Explicit roots remain; transitive closure and backend-version support matrix remain planned. | Synthetic dependency graph and room-7 source assertions. | Static soundness is bounded by opaque tails and incomplete global inputs. | MEDIUM |
| 4. Room executable compiler output | **Implemented adapter:** cooker routes rooms through IR/analysis and existing SC5C plus SNES selector generator; standalone CLI emits IR/report and tables. | Preserve SC5C, stable IDs and runtime ABI. Legacy selection/visual cooker behavior remains available. | Byte-identical synthetic/FATE records, host fixture runtime, deterministic selector output. Compiler-backed full-profile ROM is byte-identical to a ROM with an existing bounded Nexen report; the report is reused by exact hash, not rerun. | Current backend still packages original script bytes, not semantic operations. | MEDIUM |
| 5. Static room/object tables | Generate object/verb/walkbox metadata from IR for current runtime. | Keep mutable state/routing runtime; retire duplicate parsing incrementally. | Compare hit tests, routes and object state against oracle. | Confusing authored initial state with mutable state; test save/load and dynamic matrices. | MEDIUM |
| 6. Media front/back ends | Type costume/font/background/audio metadata and existing conversions. | Keep generators as backends; original archives stay external. | Per-resource provenance and visual/audio intent parity; optional title integrations. | Codec breadth and redistribution inputs; preserve explicit optional-source boundaries. | LARGE |
| 7. Selected compiled operations | Lower measured/high-value operations to compact SNES form. | Keep VM fallback for unsupported/rare operations. | Differential traces plus native fixtures and cycle/capacity comparison. | Dual execution paths increase maintenance; lower one operation family at a time. | LARGE |
| 8. Capability-gated title build | Preflight/report reproducible full selected-title artifacts. | FATE stays integration corpus; profile retains edition/source policy. | Clean build and visible unresolved dynamic edges. | Static analysis cannot prove arbitrary dynamic execution; retain conservative warnings/runtime detection. | LARGE |

## Migration invariants

1. No wholesale runtime replacement.
2. Provenance survives every transform.
3. Host semantics and accepted native controls remain behavioral references.
4. Every lowered slice gets a generic synthetic fixture and, where relevant,
   a FATE differential case.
5. Original archives remain external; generated outputs are reproducible.
6. Parsing an opcode does not imply backend support.
7. Gameplay can continue between phases; architecture work is incremental.

The first implementation establishes a reusable room compiler API and backend
seam across phases 1–4, without completing those phases. Transitive analysis
and full operation coverage remain explicit next gates. Native evidence is
linked only where the compiler-backed build reproduces an already-tested ROM
byte-for-byte; no new Nexen execution is claimed.

## Fixture ladder

1. **Semantic micro-fixtures:** tiny copyright-free scripts/rooms for
   StartScript, transition, inventory, movement, object state, dialogue,
   cutscene, timer, save/load and logical sound. Existing `cN`/`sN` fixtures
   migrate here; they remain focused semantic controls.
2. **Tiny compiled SCUMM game:** a coherent copyright-free source game that
   traverses front end → IR → analysis → SNES backend → runtime. It is not a
   disguised opcode unit test and does not require implementing Winston.
3. **FATE integration corpus:** external authentic source inputs, selected
   replays and native reports validate scale, provenance and real interactions.
   Keep that corpus distinct from reusable unit semantics.
