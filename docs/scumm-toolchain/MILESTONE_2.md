# Milestone 2: Whole-Game Census and Conservative Closure

Status: **IMPLEMENTED, PARTIAL v1**. This milestone adds whole-edition source
inventory, executable/resource graphs, conservative reachability, capability
evidence, and incomplete-analysis frontiers. It does not produce the complete
FATE ROM, alter gameplay/runtime semantics, or allocate SNES selectors.

## Entry point and shared front end

Run:

```sh
python tools/compile_scumm_game.py \
  --source /path/to/source.zip \
  --profile examples/profiles/templates/fate_of_atlantis_dos_cd.json \
  --analyze --output build/scumm-analysis
```

The source may be a ZIP containing one `.000`/`.001` pair or a directory with
one pair. The profile supplies edition identity and roots. Room resources are
compiled through `compile_room_payload()`; global scripts use its
`decode_script()` implementation. Thus room analysis is a projection of the
room compiler's canonical IR, not a parallel room/script parser.

## Analysis contract

Outputs include `game.json`, `census.json`, `executables.json`,
`dependency_graph.json`, `reachability.json`, `capabilities.json`,
`unsupported_frontier.json`, `opaque_analysis.json`, `capacity.json`,
`opcode_coverage.json`, `summary.md`, and a content-hash manifest. Canonical
output does not include machine-local paths or timestamps.

Execution identities are source-semantic and selector-free. Resource nodes
are distinct from execution nodes. Edge resolution and reachability are
separate: static/conditional/dynamic/unresolved edges feed
root/definite/conditional/possible/unresolved/unreached statuses. A variable
selector retains its expression and possible candidates; it is not guessed.

Executable structure status is independent from semantic-model and target
support status. Structurally known but semantically unsupported operations
retain their width/operands/control flow and do not create an opaque tail. A
genuinely unknown boundary or truncated form creates an explicit opaque tail.
The source PC is the same absolute coordinate used by Milestone 1, including
OBCD entry bases. No dependency or capability is inferred after an opaque
boundary. A reached opaque body makes global closure incomplete;
graph-unvisited executables are then unresolved rather than proved
unreachable.

Capability dimensions separately record decode, IR representation, SNES
backend representation, host dispatch, SNES runtime, save/restore and native
conformance. SC5C source-byte preservation and a registered host handler are
not full semantic certification. Unknown remains unknown.

## Synthetic uncertainty fixture

`examples/resources/scumm_v5/game_analysis_fixture.py` deterministically
generates a copyright-free raw two-room v5 source pair. It exercises a boot
root, unconditional and conditional script starts, direct room loading,
object-verb ownership, an indirect script selector, a known unsupported
`loadRoomWithEgo` host dispatch, and an unknown-width tail. The test asserts a
definite blocker and separately identifies uncertainty beyond the opaque
tail. `tests/test_scumm_v5_game_analysis.py` runs the same CLI twice and
compares complete output file maps.

## Canonical external FATE integration

The optional integration uses the external archive with
`fate_of_atlantis_dos_cd.json` only. The room-7 GameIR projection equals the
direct room compiler representation; expected room-7 facts are assertions,
not compiler rules. Proprietary resource payloads and analysis output are not
committed. The test is enabled with `SAME_SCUMM_SOURCE_ARCHIVE`.

The initial Milestone-2 snapshot had an opaque boundary in the boot global.
Milestone 3 now decodes `GlobalScript(1)` completely and expands root
reachability, but dynamic selectors, unresolved logical/resource room
references, remaining opaque bodies and three unsupported room containers
still prevent a complete closure. The analysis is not approval to replace
selected build manifests.

## Explicit partial boundaries

- Canonical DOS-CD FATE integration snapshot (profile SHA-256
  `496632174a38a733a739ca6feb61eaaca400cd18a89c861cfb33d5217b6064be`,
  source archive SHA-256
  `0f3fc396642c800069d31ab9a087b314f1bb1612d37accbe13b6013219ac94f0`):
  96 indexed rooms; 200 global-script slots with 163 available bodies; 250
  sound slots; 244 costume slots; 6 charset slots; 1,395 DOBJ entries; 1,362
  parsed room objects; and 2,686 indexed object-verb entries. The resource
  catalog includes unavailable/stale directory slots.
- Semantic parsing succeeds for 93 rooms. Rooms 89, 90, and 91 have BOXD
  layouts beyond the current z-plane representation. They remain inventoried
  with diagnostics, so parsed object and executable totals are explicitly
  static lower bounds, not complete source totals.
- The original Milestone-2 snapshot emitted 4,100 known executable identities (1,996
  complete, 2,102 unsupported-decode tails and 2 malformed/truncated bodies),
  14,029 graph edges (813 static, 3,298
  conditional-static, 50 dynamic, 76 unresolved execution edges; the balance
  are resource relations), and 6,391 graph nodes. These are observed analysis
  counts, not claims that all source executables were normalized.
- In that original snapshot, GlobalScript(1) became opaque at an early source
  PC; it was the only `ROOT`, and the other 4,099 known identities remained
  `UNRESOLVED`, not unreachable. Structural-closure results are recorded in
  `MILESTONE_3_STRUCTURAL_DECODER.md`.
- Actor and string metadata are partial projections; costume/audio resource
  inventory does not certify all codecs or playback semantics.
- Runtime scheduling pressure remains unknown. Static dependency depth is
  not a maximum simultaneous script-slot requirement. Capacity values for
  executables, objects, verb entries and maxima observed only in parsed rooms
  are marked `STATIC_LOWER_BOUND` while unsupported rooms remain.
- Analysis does not assign selector IDs, mutate profile selection, or emit a
  whole-game SNES ROM.
