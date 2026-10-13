# Minimum Useful SCUMM IR

## Implemented bounded room IR v1

`src/same/engines/scumm_v5/room_compiler.py` currently implements a room-only
slice: `SourceIdentity`, `RoomIR`, `ObjectIR`, `ObjectVerbIR`, `ScriptIR`,
`InstructionIR`, `Dependency`, and `CapabilityReport`. Stable JSON
serialization is provided for room IR and analysis. It distinguishes the
source container offset from the ROOM payload's member-relative offset and
retains script/object source spans, raw source body bytes through the
compilation object, hashes, script kind/number, object/verb identity, source
PCs and raw instruction bytes.

`InstructionIR` is a bounded decoded record, not yet a complete semantic
operation algebra or basic-block graph. The SCUMM v5 structural schema records
raw opcode, canonical family base, family-variant flags, operand-parameter
flags, operand bytes, width, source PC, semantic status, capability identity
and control-flow/fallthrough data independently.
Known branch instructions retain targets, but global branch-boundary
validation is not complete. A structurally known but semantically unsupported
instruction stays in the stream and does not by itself stop decoding. Only an
unknown width/control-flow form or truncated encoding creates one
`opaque_bytecode_tail`; `decode_complete` is then false. This is an explicit
partial-analysis boundary, not a runtime no-op. Semantic IR, backend support,
host/SNES runtime support and native evidence remain distinct questions.
Global scripts, standalone string/costume/sound nodes and backend addresses
are not fields in the initial room-only IR, although the same ScriptIR decoder
is reused by whole-game analysis.

The broader model below is the target vocabulary, not a claim that all of it
has been implemented.

The first IR is a small typed interchange between existing parsers, analysis
passes and cookers—not a universal adventure-game model. The host interpreter
remains a behavioral oracle while the IR grows.

## Core records

### `GameIR`

One immutable parsed source edition plus compiler facts. Minimum fields:

- game/edition identity, SCUMM dialect/version and source-profile identity;
- keyed resource records with source provenance and digest;
- scripts, rooms and global tables under typed identities;
- resource graph and capability analysis products;
- source limits from MAXS, kept distinct from target capacity.

Validate unique identities and all source ranges. Preserve unsupported dialect
features in diagnostics; never silently discard them.

### `SourceSpan` and `ResourceRef`

Each resource and operation retains archive/member or input path, source digest,
resource kind/logical identity, chunk/resource byte range, and original script
offset/PC where applicable. Source coordinates are not SNES addresses; a
backend mapping points from target locations back to source spans.

### `ScriptIR`

Use a tagged identity to prevent namespace collisions:

```text
GlobalScript(number) | RoomEntry(room) | RoomExit(room)
RoomLocal(room, number) | ObjectVerb(room, object, verb)
```

Fields include source span, original byte range, known local/argument metadata,
ordered operations, original bytes for lossless fallback, and optional basic
blocks/control-flow edges. Each operation retains its original opcode/operand
bytes and source span.

The initial semantic vocabulary should cover only proven constructs, e.g.
`WriteVariable`, `SetBit`, `Branch`, `Jump`, `StartScript`, `ChainScript`,
`StopScript`, `StartObject`, `LoadRoom`, `LoadRoomWithEgo`, actor movement and
placement, object state/owner/class changes, `Print`, `Wait`, cutscene
boundaries and `SoundCommand`.

`UnknownOrUnloweredOp` retains raw opcode, operand span and location. If a
selected path may execute it, capability analysis must report/fail it; it may
not become a no-op. This enables partial lowering without claiming the full
dialect.

### `RoomIR`, `ObjectIR` and `VerbEntry`

`RoomIR` contains room identity/span, ENCD/EXCD references, local scripts,
static geometry/walkboxes and objects. Source geometry stays target-neutral.

`ObjectIR` contains source object identity, initial state/class/owner,
CDHD geometry, walk target/direction and verb entries. Authored initial values
are distinct from mutable runtime state. `VerbEntry` maps a SCUMM verb ID to
an object-code script source range; it does not encode cursor UX.

### Actor, text, costume and sound metadata

The first increment needs source actor defaults/costume references; encoded
strings plus decoded control tokens; costume format/palette/frame/codec needs;
and logical sound/music/speech resource references. Decoded pixels, SNES
palette layout, sample conversion and bank placement are backend products.

## Graph, capabilities and invariants

`ResourceGraph` has typed script/room/object-verb/costume/string/sound nodes
and typed edges with source span, resolution and confidence (`definite`,
`possible`, `observed`). `CapabilitySet` records language requirements
separately from backend support and target capacity.

Invariants:

1. Every lowered operation maps to valid source bytes and a source span.
2. Static branch targets land on decoded instruction boundaries or remain
   explicitly unresolved/unsupported.
3. Script identities include namespace and owning room/object.
4. Static references resolve or remain explicit graph edges; the front end
   never invents target selectors.
5. Source-derived initial state and runtime-mutated state remain separate.
6. Backend records carry source map and build identity.
7. Unknown operations remain visible to diagnostics.

No SSA, optimizer, universal object system or all-opcode lowering is needed
for this seam. Preserve raw bytes so the current interpreter can execute while
typed semantics are introduced incrementally.
