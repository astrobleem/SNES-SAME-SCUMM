# SCUMM Toolchain Migration Ledger (historical seed)

FATE is the first serious customer and integration corpus for a reusable
SCUMM-to-SNES toolchain. Its observed behavior is evidence for generic SCUMM
semantics, not a runtime specification by itself. The small table below is the
historical opportunistic ledger created during the room-4-to-room-7 replay; it
is retained as evidence, but is no longer the canonical architecture plan.
The repository-wide audit and current migration plan live in
[`docs/scumm-toolchain/`](scumm-toolchain/CURRENT_ARCHITECTURE.md):

- [FATE coupling audit](scumm-toolchain/FATE_COUPLING_AUDIT.md) and
  [machine-readable inventory](scumm-toolchain/fate_coupling.json)
- [Minimum SCUMM IR](scumm-toolchain/IR.md)
- [Compiler pipeline](scumm-toolchain/COMPILER_PIPELINE.md)
- [Capability analysis](scumm-toolchain/CAPABILITY_ANALYSIS.md)
- [Runtime/offline boundary](scumm-toolchain/RUNTIME_BOUNDARY.md)
- [Migration plan](scumm-toolchain/MIGRATION_PLAN.md)
- [First implementation milestone](scumm-toolchain/FIRST_MILESTONE.md)

| Current file/component | Current behavior | Classification | Why | Desired eventual layer | Migration note |
|---|---|---|---|---|---|
| `src/same/engines/scumm_v5/resources.py`, `room.py` | Discover and decode the authentic LFLF room, object/CDHD records, OBCD verb tables, and local-script directory from the supplied game archive. | `COMPILER_DERIVABLE_DATA` | Resource identity, geometry, verb offsets, and script bodies are source data that can be parsed before ROM execution. | SCUMM front end -> canonical room/object/script IR. | Keep archive/container knowledge out of the SNES backend; emit validated compact room and verb records. |
| `runtime/snes/engines/scumm_v5_controller_far.pasm` | Resolve controller input against active room object metadata, enumerate authored verbs, publish a sentence, and wait for the sentence/talk lifecycle to release input ownership. | `GENERIC_SCUMM_SEMANTIC` | Hit testing, sentence ownership, and talk/controller edge separation are reusable interaction semantics, not FATE behavior. | Generic SCUMM runtime, with controller backend adapters. | Preserve the native regression controls; eventually feed the runtime from compiler-emitted interaction metadata. |
| `runtime/snes/engines/scumm_v5*.pasm` script dispatch and VM operations | Execute `startScript`, `chainScript`, bit/variable operations, object-owner/state changes, actor placement, and camera-follow room lifecycle. | `GENERIC_SCUMM_SEMANTIC` | These are general SCUMM operations whose behavior is merely exercised by this FATE path. | SCUMM IR operations plus generic runtime services. | Differentially test the semantic operation sequence using tiny copyright-free games before changing the backend representation. |
| `tools/generate_snes_cooked_rooms.py` and generated room tables | Assign selected globals, locals, and object programs to runtime selectors and emit per-room directories. | `COMPILER_DERIVABLE_DATA` | Selector allocation and resource tables are deterministic products of source identities and profile selections. | Capability/dependency analysis -> SNES backend artifacts. | Keep stable allocation policy; make generated manifests describe semantic identities and required dependencies rather than relying on ad hoc runtime identity checks. |
| FATE build environment (`SAME_SCUMM_APPEND_TERMINAL_EXECUTABLE_LOCAL_OBJECTS`, startup/profile room lists) | Selects the currently reached FATE rooms, OBCDs, and local/global executable closure. | `FATE_PROFILE_DATA` | The selected resource identities are title/content choices; the allocation mechanism itself remains generic. | Game profile / source manifest consumed by dependency analysis. | Replace long manually accumulated lists over time with compiler-derived reachable closure, while preserving explicit overrides for bounded diagnostics. |
| `tools/fate_replay.py`, `tools/replay_fate_room4_cold_nexen.py`, `examples/replays/fate-room4-open-trapdoor.json` | Drives exact-frame, normal controller input and checks current-ROM-bound state, source bodies, selector mappings, and progression effects. | `TEST_FIXTURE_ONLY` | The action sequence and object/script identities are acceptance inputs, not engine policy. | Integration/regression corpus over compiled game artifacts. | Keep every successful step deterministic and provenance-bound; do not move room/object identities into production runtime branches. |
| Room7 cat progression assertions in the cold replay validator | Checks object118/119 verb bodies and the resulting V214/V215–V218 variable state and LSCR dispatch for this specific authored sequence. | `TEST_FIXTURE_ONLY` | These identities are useful integration expectations, but they are not generic runtime behavior. | FATE-specific acceptance manifest generated from or checked against front-end IR. | The newly added checks are diagnostic/replay code only; no room7-specific production runtime hook was introduced. |

## Room7 evidence shaping the next replay step

The first room7 visit begins with global bit69 clear and V214=0. Authentic
object118 verb10 writes variable V217 and increments V214. A second distinct
figure, object119 verb10, writes variable V218, starts room-local script207,
and chains script201. Native replay observed selectors `$88` and `$89` and the
authentic room-3 installation. The room-local continuation places Ego in
room3 and follows the camera. This is a content-derived progression sequence;
global bit69 is not set by these room7 object verbs and must not be forced by
the validator.

The cold replay settled in room3 with error 0 and lifecycle RUNNING. The
active room-3 LSCR213 was program `$80`; its source body is compiler-derivable
data and remains in the external game archive. The current inventory of
room/object/script identities and action expectations lives in the replay
recipe and authored-graph note as `TEST_FIXTURE_ONLY`/`FATE_PROFILE_DATA`, not
as production runtime branches. No room-, script-, object-, or PC-specific
production hook was added during this continuation.

Source data remains external. The replay records hashes and archive locations;
no extracted FATE resource payload is added to this repository.
