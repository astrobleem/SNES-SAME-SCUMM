# Capability and Dependency Analysis

## Implemented room report (partial v1)

`room_compiler.analyze_room` currently reports the SCUMM v5 operations decoded
in the bounded room-script subset, corresponding runtime primitive names,
opaque/unclassified tails, incomplete scripts, direct and dynamic dependency
records, variable/bit reads and writes, object-state/class writes, and counts
for room scripts, objects, verb entries, decoded operations and source bytes.
The CLI emits this as deterministic JSON alongside human-readable counts.

An indirect script/room/resource operand is a dynamic edge with an expression;
it is never turned into a guessed selector. A direct room-local `startScript`
or direct `startObject` must resolve against the current room's decoded local
namespace/object verb directory or is reported missing. A direct global script
is currently marked external because this room-only compilation unit does not
yet ingest a global bundle.

FATE room 7 compiles through this path with 79 executable body records, 110
static edges, one dynamic edge, no unclassified *known-width* operation, and
21 incomplete scripts with opaque tails. The bit69 read is reported generically
as `bit:69`; the compiler assigns it no title-specific meaning. Because these
scripts have opaque boundaries, the report is explicitly `partial`; no later
control-flow dependency is inferred across those boundaries. It resolves the
literal object-verb calls to room-local LSCR 201 and 207, and fully decodes
LSCR 201's actor placement into room 3 followed by a dynamic
`actorFollowCamera` scene edge. The latter remains dynamic because the followed
actor's room is runtime state; no room number is inferred from a title-specific
rule.

The source manifest records hashes for the compiler/front-end/record source
components, CLI, IR, analysis, cooked record, and—when selected—the SNES
generator and every generated backend file. Archive, index/data members,
profile identity, distinct LFLF-container and ROOM-payload offsets, and body
hashes are recorded without embedding machine-specific absolute paths.

Not implemented yet: per-opcode support status against a named backend/runtime
version, selected-root reachability, transitive global closure, conservative
branch reachability, script-slot pressure, room-wide resource inventories,
costume codec and save-capacity analysis. An operation appearing in the report
means it was decoded, not that the SNES backend has certified its semantics.

The analyzer should answer what a source game requires, what the selected
backend implements, and what remains uncertain before a long native replay.
Initially it is a conservative static report, not perfect whole-game
reachability.

## Evidence levels

- **Definitely required** — in mandatory/selected roots or statically reached
  by literal references.
- **Possibly reachable** — target/resource is dynamic, conditional, or hidden
  behind a conservative branch/call edge.
- **Observed during execution** — event seen in a named ROM/build, with
  program identity, source PC/span and frame.

An observed path does not prove all game branches are covered; a decoded
opcode need not execute on the current route.

## Initial report categories

| Category | Static evidence and report |
|---|---|
| SCUMM dialect/version | Profile and resource headers; parser support and unsupported dialect features. |
| Opcode usage | Decode selected script bodies; per-opcode counts, malformed/truncated instructions and unknown opcodes. |
| Script constructs | Branches, waits, starts/stops/chains, cutscenes, messages; construct support state. |
| Script count/dependencies | Global directories, ENCD/EXCD/LSCR, object verbs and literal edges; selected closure and unresolved/dynamic refs. |
| Slot pressure | Literal call graph and conservative recursion/dynamic edges; lower bound, observed peak, conservative/unknown bound—not total scripts as exact peak. |
| Rooms/objects/verbs | ROOM/OBCD/CDHD/verb data; counts, local scripts, malformed/duplicate records. |
| Actor operations | Opcode use, actor defaults and costume refs; required services and capacity. |
| Walkboxes | BOXD geometry, matrixOps and route mutations; box count, static portals, dynamic route requirements. |
| Costumes/codecs | Headers and frame/codec fields; formats, palette/capacity needs, unsupported codecs. |
| Text/control codes | Encoded text and print ops; character/control coverage and message limits. |
| Cutscenes/overrides | Begin/end/override uses and structure; continuation/stack requirements. |
| Audio/iMUSE | Sound resources and audio opcodes; commands, mapped logical resources and partial backends. |
| Resource/capacity | Source counts/sizes plus generated data; ROM/WRAM/bank/directory requirements. |
| Save state | Mutable fields and schema; persistent state/capacity requirements. |
| Unsupported semantics | Unknown opcodes, unsupported fields/codecs and unresolved mandatory edges with source spans and confidence. |

For each feature report `SUPPORTED`, `PARTIAL`, `UNSUPPORTED` or `UNKNOWN`,
plus evidence and backend version. Semantic support and capacity are separate:
a supported `startScript` may exceed selected slot capacity.

## Existing facts to reuse

The raw provider exposes global directories/resource keys. Room decode exposes
objects, verb offsets, walkboxes and visual geometry. Cooked manifests already
carry room/script/object identities, hashes, source offsets, archive/index/data
hashes and profile identity. The selector generator checks duplicate/missing
scripts and allocates stable IDs. Host and native engines enumerate opcode
support. Profiles/build flags currently provide much of the root set manually.

The first analyzer can reuse these facts without perfect symbolic execution.
Variable script IDs, pseudo-room maps, resource operations and conditional
state widen results to `possibly reachable` with an explicit reason.
