# Incremental Migration Plan

FATE progress and the current interpreters stay usable. Each phase adds a seam,
compares it against host/native behavior, and leaves existing paths available
until a new artifact participates in acceptance.

| Phase | Goal/components | New seam; retain/retire | Validation | Principal risk | Size |
|---|---|---|---|---|---|
| 0. Inventory | Current audit docs and coupling record. | No production change; preserve engines/replay. | JSON/doc consistency. | Inventory can become stale; keep it small and tested. | SMALL |
| 1. Front-end resource model | Wrap `resources.py`, `room.py`, policy and cook discovery in typed records/source spans. | Keep APIs as adapters; no runtime-format change. | Match keys, bytes, offsets and hashes on synthetic/optional authentic data. | Two parser entry points could diverge; make old APIs adapters to shared parse results. | MEDIUM |
| 2. Script IR slice | Decode a bounded opcode subset into `ScriptIR`/basic blocks with original byte ranges. | Interpreters remain oracle/fallback; do not rewrite handlers. | Differential lengths, targets and selected semantics; unknown mandatory ops fail analysis. | Partial decode may imply false completeness; carry unknown/raw nodes and explicit capability status. | MEDIUM |
| 3. Capability/dependency analysis | Derive opcode needs, direct script/room/object edges and capacities. | Explicit profile roots remain; retire only redundant hand selections as closure is proven. | Synthetic graph and ROM-observed FATE edges; dynamic targets conservative. | Unsound reachability could omit code; classify dynamic edges as possible and fail unresolved required starts. | MEDIUM |
| 4. Room executable compiler output | Route one room/local/object-verb closure through front end → IR → analysis → existing cooked format/backend. | Preserve SC5C, stable IDs and runtime ABI. | Source/selector parity and bounded native execution on FATE + tiny fixture. | Artifact drift; compare provenance and keep current runtime contract. | MEDIUM |
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
