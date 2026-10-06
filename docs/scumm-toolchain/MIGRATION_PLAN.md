# Incremental Migration Plan

FATE progress and the current interpreters stay usable. Each phase adds a seam,
compares it against host/native behavior, and leaves existing paths available
until a new artifact participates in acceptance.

| Phase | Goal/components | New seam; retain/retire | Validation | Principal risk | Size |
|---|---|---|---|---|---|
| 0. Inventory | Current audit docs and coupling record. | No production change; preserve engines/replay. | JSON/doc consistency. | Inventory can become stale; keep it small and tested. | SMALL |
| 1. Front-end resource model | **Partial/implemented:** checked raw v5 directories, source catalog for rooms/scripts/sounds/costumes/charsets, member/container/payload offsets and hashes. | Keep provider API as adapter; no runtime-format change. | Synthetic raw pair and external DOS-CD archive census. | Several types remain inventoried rather than semantically normalized. | MEDIUM |
| 2. Script IR slice | **Partial/implemented:** room and global scripts use shared bounded v5 decoder and source-bound InstructionIR; opaque tails are explicit. | Host/native interpreters unchanged; no full CFG/SSA IR. | Synthetic graph fixture and exact room-7 projection cross-check. | Decoder coverage is incomplete; opaque bytes remain unknown. | MEDIUM |
| 3. Whole-game census/analysis | **Partial/implemented:** canonical identities, resource/execution graph, conditional/dynamic certainty, root reachability, capability dimensions and frontier. | Runs before allocation; selected build/profile path unchanged. | Synthetic uncertainty fixture, FATE census and determinism. | FATE boot global reaches an opaque tail early; three rooms exceed current BOXD decoder. Closure remains incomplete. | MEDIUM |
| 4. Room executable compiler output | **Implemented adapter:** cooker and game analysis reuse room compiler and existing SC5C; selector generation remains a backend step. | Preserve SC5C, stable IDs and runtime ABI. Legacy selection/visual cooker remains available. | Byte parity, synthetic host fixture, source-bound room-7 IR equality. | Backend still preserves source script bytes rather than lowering operations. | MEDIUM |
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

The first two compiler milestones establish a reusable room compiler API and
a partial whole-source analysis seam across phases 1–4, without completing all
source formats, closure or capability certification. Native evidence is
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
