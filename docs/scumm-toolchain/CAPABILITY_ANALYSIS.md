# Capability and Dependency Analysis

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
