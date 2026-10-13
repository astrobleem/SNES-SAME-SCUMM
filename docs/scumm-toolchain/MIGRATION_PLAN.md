# Incremental Migration Plan

FATE progress and the current interpreters stay usable. Each phase adds a seam,
compares it against host/native behavior, and leaves existing paths available
until a new artifact participates in acceptance.

| Phase | Goal/components | New seam; retain/retire | Validation | Principal risk | Size |
|---|---|---|---|---|---|
| 0. Inventory | Current audit docs and coupling record. | No production change; preserve engines/replay. | JSON/doc consistency. | Inventory can become stale; keep it small and tested. | SMALL |
| 1. Front-end resource model | **Partial/implemented:** checked raw v5 directories, source catalog for rooms/scripts/sounds/costumes/charsets, member/container/payload offsets and hashes. | Keep provider API as adapter; no runtime-format change. | Synthetic raw pair and external DOS-CD archive census. | Several types remain inventoried rather than semantically normalized. | MEDIUM |
| 2. Script IR slice | **Implemented for the current FATE corpus; generic dialect coverage remains partial:** shared v5 opcode-family/operand schema plus source-bound `InstructionIR`; structural status is independent from semantic IR status. Opaque tails mean unknown boundaries/truncation, not unmodeled semantics. | Host/native interpreters remain independent; no full CFG/SSA IR. | Synthetic structural uncertainty, opcode census and room-7 projection cross-check. | Other source editions may exercise forms absent from this corpus. | MEDIUM |
| 3. Whole-game census/analysis | **Implemented, conservative:** canonical identities, resource/execution graph, conditional/dynamic certainty, root reachability, capability dimensions and frontier. | Runs before allocation; selected build/profile path unchanged. | Synthetic uncertainty, canonical FATE census and two-directory determinism. | FATE graph closure remains incomplete from dynamic/unresolved references; current parsed corpus has no opaque tails. | MEDIUM |
| 4. Room executable compiler output | **Implemented adapter:** cooker and game analysis reuse room compiler and existing SC5C; selector generation remains a backend step. | Preserve SC5C, stable IDs and runtime ABI. Legacy selection/visual cooker remains available. | Byte parity, synthetic host fixture, source-bound room-7 IR equality. | Backend still preserves source script bytes rather than lowering operations. | MEDIUM |
| 5. Static room/object tables | Generate object/verb/walkbox metadata from IR for current runtime. | Keep mutable state/routing runtime; retire duplicate parsing incrementally. | Compare hit tests, routes and object state against oracle. | Confusing authored initial state with mutable state; test save/load and dynamic matrices. | MEDIUM |
| 6. Media front/back ends | Type costume/font/background/audio metadata and existing conversions. | Keep generators as backends; original archives stay external. | Per-resource provenance and visual/audio intent parity; optional title integrations. | Codec breadth and redistribution inputs; preserve explicit optional-source boundaries. | LARGE |
| 7. Selected compiled operations | Lower measured/high-value operations to compact SNES form. | Keep VM fallback for unsupported/rare operations. | Differential traces plus native fixtures and cycle/capacity comparison. | Dual execution paths increase maintenance; lower one operation family at a time. | LARGE |
| 8. Capability-gated title build | Preflight/report reproducible full selected-title artifacts. | FATE stays integration corpus; profile retains edition/source policy. | Clean build and visible unresolved dynamic edges. | Static analysis cannot prove arbitrary dynamic execution; retain conservative warnings/runtime detection. | LARGE |
| 9. ProgramUnit/residency analysis | **Implemented; refined by phase 10:** source executable projection groups object verbs by OBCD, but the original record-count view included passive object records. | Historical `program_units.json` remains for comparison; see true selector-demand projection below. | Room-7 79→44 legacy record reconciliation; no longer use that count as selector demand. | Record terminology obscured non-callable data-only OBCD objects. | MEDIUM |
| 10. True selector demand | **Implemented analysis:** distinguish SemanticExecutable, ResourceRecord, ExecutableCarrier and SelectorUnit; emit selector-free directories and recompute capacities from dispatch-reachable carriers. | Keep the legacy generator/IDs unchanged; no runtime paging or ABI change. | Synthetic data-only/multi-verb fixture; FATE 4,100→2,195; rooms 7/98; canonical deterministic analysis. | Unparsed rooms leave source-wide room maxima as lower bounds; exact concurrent liveness remains unknown. | MEDIUM |
| 11. Resolver/binding contract | **Pure simulator implemented:** stable SelectorUnit identity/bundle index → temporary ResidentBinding → byte selector. Consumes the selector-free directory, resolves globals lazily, and models activation/continuation pins, bundle lifecycle, generations, exhaustion and portable restore. | Keep current generated selector tables and ABI. Native directory/resolver, pin operations and save migration remain planned. | Synthetic pin/exhaustion/restore tests; canonical FATE manifest scenarios; deterministic traces. | Real runtime liveness and selector snapshots outside modeled state remain unknown. | MEDIUM |
| 12. Native resident resolver | **Implemented for the bounded synthetic control and accepted FATE route:** canonical IDs and generated directories resolve to ephemeral byte selectors; active slot ownership pins bindings and generations reject stale identities. | Legacy static path remains available; FATE dynamic profile remains experimental. | >178-unit native control, exhaustion/pinning tests, static-vs-dynamic bounded FATE replay. | Portable save migration and whole-game liveness remain outside this proof. | LARGE |
| 13. Capability-frontier burn-down | **Implemented, partial:** current FATE corpus has normalized semantic IR for every parsed instruction; host/SNES/backend support stays independently gated. A generic actor-to-actor walking primitive gained host/native conformance; other reported operation support remains partial, unsupported or unknown. | Keep the bytecode VM and accepted resolver; use the report to select generic semantic/runtime work. | Capability census, copyright-free operation fixtures, native actor-relative movement control, bounded FATE route regression when affected. | Whole-game SNES semantics and portable save coverage are not certified; dynamic/unresolved graph edges still limit reachability proof. | LARGE |

## Migration invariants

1. No wholesale runtime replacement.
2. Provenance survives every transform.
3. Host semantics and accepted native controls remain behavioral references.
4. Every lowered slice gets a generic synthetic fixture and, where relevant,
   a FATE differential case.
5. Original archives remain external; generated outputs are reproducible.
6. Parsing an opcode does not imply backend support.
7. Gameplay can continue between phases; architecture work is incremental.

The first compiler milestone establishes a reusable room compiler API; the
whole-game front end and structural/semantic separation now cover the current
DOS-CD FATE corpus. Native resolver acceptance is bounded to synthetic
controls and the deterministic route through room 3. Capability burn-down
adds generic semantic representations and selected runtime conformance, but
the release gate remains closed until per-operation backend/native support is
certified. None of these milestones proves full-game playability.

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
