# First Compiler Milestone: Source-Bound Room Executable Bundle

Status at implementation branch: **IMPLEMENTED, PARTIAL ANALYSIS**.

The parser adapter, small IR, dependency/capability report, SC5C backend
adapter, stable selector handoff and developer CLI now exist. The synthetic
room runs through the existing host runtime. External FATE room 7 compiles
through the same path and retains byte-identical SC5C output. This is not yet
a complete SCUMM v5 decoder or a claim that every room-7 dependency has been
proven. The current room-7 analysis contains 79 executable records; 21 scripts
end at an explicitly unclassified bytecode tail. Raw code remains intact for
the existing VM, and the report stays partial rather than inferring beyond
those boundaries.

## Decision

Build one generic SCUMM v5 room-executable compile pass. Given a source room,
its ENCD/EXCD/LSCR scripts and object verb directory, it constructs a small
`RoomIR`/`ScriptIR` bundle, analyzes the decoded subset and direct executable
dependencies, then emits the existing cooked-room/backend artifact and source
map consumed by the current runtime. Complete control-flow validation remains
future work.

This seam has more leverage than an isolated opcode translator: the observed
integration work repeatedly depends on complete authentic room/object/local
executable closure and correct generated selector maps. It makes source
identity and dependency analysis compiler-owned without replacing the
interpreter or runtime ABI.

## End-to-end slice

| Stage | Implemented contract / remaining boundary |
|---|---|
| Source | **Implemented:** external archive + thin v5 profile; CLI accepts one raw room. FATE input is room 7. No game bytes are committed. Whole-game root selection is still profile/build tooling. |
| Synthetic source | **Implemented:** copyright-free room with ENCD/EXCD/LSCR, two authored object verbs, a local/global call, branch, state mutation and room transition. It uses the same compiler API. |
| Front end | **Implemented for this slice:** reuse checked provider/chunk/object decoders; emit member, container/resource offsets, body hashes, source PCs and typed room/script/object/verb identities. |
| IR | **Implemented v1:** `RoomIR`, `ObjectIR`, `ObjectVerbIR`, `ScriptIR`, instruction records, dependencies and capability report. Original bytes are preserved. Unknown widths become an opaque tail, never a no-op. |
| Analysis | **Partial:** decodes a bounded generic opcode/operand subset; records known direct and variable-indirect dependencies, operation inventory, bit/variable reads and writes, and room capacities. It does not yet validate every jump target or compute transitive/global closure. Unknown tails are surfaced and make the report partial. |
| Backend | **Implemented adapter:** reuses `encode_cooked_room` and the existing selector/table generator. The room cooker now calls the compiler API; selector IDs remain assigned only by the stable backend allocator. No runtime ABI change. |
| Runtime | **Synthetic host runtime:** compiler-produced SC5C executes through the existing host resource service. FATE room 7 SC5C is byte-identical to the legacy output and its executable identities pass the existing SNES selector generator. The compiler-backed full-profile rebuild reproduced ROM SHA-256 `f5492f1c…76471fd`, byte-identical to a previously executed bounded Nexen control; that historical runtime report is reused by exact ROM identity. Nexen was not rerun for this milestone. |

The FATE identities are test inputs, never compiler special cases. A profile
names the external source edition, not “when object 119 runs, use PC X.”

## Replaces or narrows

- For a selected room, source parsing, ENCD/EXCD/LSCR discovery, OBCD verb
  discovery and direct room-local dependency checks now come from the generic
  compiler adapter. This does **not** replace whole-title room/global roots or
  the manually accumulated cross-room executable closure; those remain build
  profile inputs until a sound transitive analysis exists.
- Stable executable selectors remain, generated from typed source identities
  and backend layout.
- Existing SC5C/current runtime interface remains initially; its producer
  boundary changes, not its semantics.

## Acceptance

1. **Passed:** synthetic tests assert source identities, boundaries, dependency
   classification, unknown-tail handling and byte-preserving output.
2. **Passed with external archive:** room 7 source hashes/offsets and the
   object118/119 verb-to-LSCR207/201 references match the accepted source
   evidence; bit69 is reported as a bit read without title-specific meaning.
3. **Passed:** SC5C output matches the legacy cooker byte-for-byte; compiler
   output and generated SNES tables are deterministic across output dirs; the
   existing stable allocator assigns executable IDs.
4. **Passed:** synthetic compiler output executes through the existing host
   runtime. The compiler-backed profile rebuild is byte-identical to the ROM
   in a previously executed bounded native report, which is linked by exact
   ROM hash. **Not claimed:** Nexen was not rerun, this milestone does not
   progress FATE, and it does not certify a new gameplay replay.
5. Validation is recorded in the implementation handoff; proprietary archive
   integration is optional for ordinary tests.

This does not require whole-game symbolic execution, all-opcode IR, direct
native code generation, a new SNES interpreter or a complete gameplay route.
