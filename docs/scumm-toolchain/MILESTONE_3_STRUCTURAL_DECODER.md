# Milestone 3: SCUMM v5 Structural Decoder Closure

Status: **IMPLEMENTED, PARTIAL**. The shared front end now separates
instruction-boundary knowledge from semantic IR availability and from backend
or runtime certification. This is source analysis only: no SCUMM host/native
runtime, SNES backend behavior, selector allocator, or gameplay path changed.

## Structural contract

`v5_opcode_schema.py` is the dialect-owned byte-structure table. Opcode
variants share a family and parameter-flag mask; the original byte remains in
`InstructionIR`. The decoder records source PC, canonical family base, raw
opcode-variant flags separately from operand-parameter flags, instruction
width, raw operand bytes, decoded operands, branch targets,
fallthrough/control-flow category, and semantic capability where known.
Variable command lists and nested expression forms use bounded parsers.
Helper-consumed inline strings are included in the instruction boundary.

The statuses answer separate questions:

| Layer | Question | Example status |
|---|---|---|
| Structural decode | Can the next boundary/control-flow continuation be established? | `STRUCTURALLY_DECODED`, `STRUCTURAL_UNKNOWN`, `TRUNCATED` |
| Semantic IR | Is the operation normalized into the available semantic model? | `SEMANTIC_IR_AVAILABLE`, `SEMANTIC_UNSUPPORTED`, `SEMANTIC_UNKNOWN` |
| Capability/runtime | Is the operation represented/executed correctly by a target? | Independent registry dimensions; not inferred from decoding |

A known-width but semantically unsupported instruction remains explicit and
does not hide later dependencies. An unknown subcommand layout or truncated
operand produces an opaque boundary; no claims extend beyond it:

> OPAQUE TAIL != COMPLETE ANALYSIS

Control-flow metadata is retained even where the operation's semantic IR is
not available. A known chain/stop operation is not represented as ordinary
fallthrough. The source corpus is still scanned conservatively; this is not a
claim that every decoded instruction is executable on every path.

## Canonical DOS-CD FATE result

Input is external `/home/chad/ATLANTIS.zip` with
`fate_of_atlantis_dos_cd.json`. Its archive SHA-256 is
`0f3fc396642c800069d31ab9a087b314f1bb1612d37accbe13b6013219ac94f0`; the
canonical profile SHA-256 is
`496632174a38a733a739ca6feb61eaaca400cd18a89c861cfb33d5217b6064be`.
No source payload or generated analysis bundle is committed.

| Measure | Before this milestone | After this milestone |
|---|---:|---:|
| Known executable identities | 4,100 | 4,100 |
| `COMPLETE` | 1,996 | 4,089 |
| `UNSUPPORTED_DECODE` / opaque | 2,102 | 9 |
| `MALFORMED` / truncated | 2 | 2 |
| Graph nodes | 6,391 | 6,538 |
| Graph edges | 14,029 | 34,539 |
| Static edges | 813 | 1,145 |
| Conditional-static edges | 3,298 | 8,240 |
| Dynamic edges | 50 | 372 |
| Unresolved execution edges | 76 | 372 |

The graph expansion reflects dependencies exposed after the decoder crossed
formerly opaque operations. It does not mean all those edges execute.
`GlobalScript(1)` is now structurally complete. Reachability changes from
`ROOT 1, DEFINITE 0, CONDITIONAL 0, POSSIBLE 0, UNRESOLVED 4,099` to
`ROOT 1, DEFINITE 2, CONDITIONAL 3,822, POSSIBLE 268, UNRESOLVED 7`.
The remaining root uncertainty begins with a dynamic actor-follow-camera room
reference at GlobalScript(1) PC 1549; later root-body edges also include
dynamic object/local selectors and unresolved room resources. The closure is
not complete. Some logical room IDs also depend on runtime pseudo-room
mapping, and that mapping is not currently propagated as a proven physical
room-entry identity by graph reachability.

The census covers 114,399 instruction occurrences: 190 raw opcode variants
and 91 observed semantic families. Of these, 114,388 have known structural
boundaries; 87,156 have semantic IR available, 27,232 are structurally known
but semantically unsupported, and 11 are structural unknown/truncated
occurrences (nine unknown, two truncated). No backend or SNES runtime
occurrence is certified `SUPPORTED` by this corpus-wide registry; this is an
absence of certification, not a claim that the runtime has no working
operations. The schema registers 244 active v5 opcode bytes across 101
families; 12 byte values are unregistered in the v5 opcode table.

### Remaining structural frontiers

The current nine structural-unknown occurrences affect nine executable
identities; the two truncated occurrences affect two more. The first remaining
root-closure structural frontiers are reached conditionally/possibly from the
root, not in `GlobalScript(1)` itself:

| Source | PC | Encoding | Why left opaque |
|---|---:|---|---|
| `RoomEntry(20)` | 11,711 | `print` selector low nibble `0xD` | SCUMM v5 `decodeParseString` has no operand grammar for selector 13 and errors; no subsequent boundary is asserted. |
| `RoomEntry(40)` | 574 | `print` selector low nibble `0xD` | Same unsupported subcommand layout. |
| `RoomLocal(room=68,local=200)` | 234 | `drawObject` subcommand `0` | The v5 handler recognizes subcommands 1, 2, and 31; default errors. No other structural form is specified. |
| `RoomEntry(96)` | 57 | opcode `0x4F` | Not registered by the v5 setup table; source implementation comments it out. Older-version meanings are not imported into v5. |
| `RoomLocal(room=46,local=204)` | 639 | `print` selector low nibble `0xA` | No v5 operand form; handler default errors. |
| `RoomLocal(room=46,local=206)` | 182 | `print` selector low nibble `0xA` | Same unknown form. |
| `RoomLocal(room=46,local=207)` | 182 | `print` selector low nibble `0xA` | Same unknown form. |
| `RoomLocal(room=50,local=203)` | 117 | `print` selector low nibble `0xC` | No v5 operand form; handler default errors. |
| `RoomLocal(room=96,local=205)` | 8 | `print` selector low nibble `0xC` | Same unknown form. |

Two source bodies end with insufficient bytes for their final operands and are
reported separately as truncated, not repaired by guesswork:

- `RoomLocal(room=33,local=206)`, PC 49, opcode `0x29` (`setOwnerOf`), body
  SHA-256 `b7cfdd59689c8df948e7557a30af7f64172560cb11326758a992415b81fd13f3`;
  only one operand byte remains where the direct word and owner byte are
  required.
- `RoomLocal(room=61,local=201)`, PC 122, opcode `0xFF` (`drawBox`), body
  SHA-256 `c17da85eb695096f7cb48c96990fd5fab32b63f00359cec37b381a37d47d9cbe`;
  the room-local body ends before the required coordinate operands complete.

The three unparsed rooms 89, 90, and 91 remain a separate BOXD z-plane
representation limitation; this opcode work did not change their status.

## Room-7 and synthetic checks

Room 7 still has 79 executable records, now all structurally complete. Its
object 118 verb 10 to LSCR 207, object 119 verb 10 to LSCR 201, LSCR 201's
room-3 placement relation, dynamic camera-follow relation, canonical source
identities, and absolute object-verb PCs remain checked by the external
integration. The earlier 21 incomplete records were caused by instruction
forms/boundaries not yet represented, not by a room-7-specific rule.

The copyright-free graph fixture proves that a known-width
semantic-unsupported operation does not hide a following static
`StartScript`/resource dependency, that branch certainty remains represented,
that dynamic selectors remain dynamic, and that malformed/truncated input
still creates an opaque frontier. The same shared decoder feeds room and
whole-game analysis.

Two canonical FATE analyses were emitted from the final source to separate
directories. All 12 emitted files (the 11 canonical analysis artifacts plus
the manifest) match byte-for-byte:

```json
{"runs":2,"file_sets_equal":true,"contents_equal":true,"differences":[],"analysis_file_set_sha256":"b979f355ade09174c4c7e0e6838b8b6e06c0531dc78da352fb5ad45e1642a4ae"}
```

This milestone changes only source-analysis/compiler front-end code and
tests/docs. Runtime, SNES backend behavior, program allocation, and ROM bytes
are unchanged; no native rerun is indicated.
