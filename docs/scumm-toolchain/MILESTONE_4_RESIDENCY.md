# Milestone 4: Executable Residency and Backend Partition Planning

Status: **IMPLEMENTED, ANALYSIS ONLY**. The planner adds no runtime behavior,
does not assign selectors, and does not replace profile-selected build inputs.
It answers addressability/lifetime questions from the whole-game source graph;
it does not claim an exact schedule or actual simultaneous code-memory maximum.

## Identity and current selector contract

Source executable identities (`GlobalScript(n)`, `RoomEntry(r)`,
`RoomExit(r)`, `RoomLocal(room=r,local=n)`, and
`ObjectVerb(room=r,object=o,verb=v)`) remain canonical, game-wide compiler
identities. The planner does not include a byte selector, ROM bank, address,
or loaded-room state in those identities.

The current SNES backend pool in `tools/generate_snes_cooked_rooms.py` is
48 primary plus 130 overflow byte values: 178 unique build-global selector
addresses. Generated M23A room directories contain selector bytes; generated
global-script resolution maps a script number to a selector; generated
`GetProgramSize` and `FetchProgramByte` dispatch compare that same selector
against the build's program table. There is no room-change remapping today.
The allocator rejects duplicate selector use within the generated build.

The selector is stored in `SAME_SCUMM_PROGRAM_SELECT` (`$7E2362`). Each of the
25 C4 activation slots stores one byte in `SAME_SCUMM_C4_SLOT_PROGRAM`, beside
its status, script number, PC, delay, and locals (`runtime/snes/kernel/memory.pasm`).
The scheduler repeatedly restores that stored selector before execution and
fetch. Nested scripts and room-lifecycle continuations therefore retain the
same build-global selector identity while live. Selector reuse without a
canonical binding/pinning mechanism could make an old PC fetch a different
program after a bundle replacement.

The host save format instead serializes source resource identity, script kind,
room/number, PC, locals, and scheduler state, then reconstructs program bytes
from the resource provider (`ScriptSlot.to_dict()` and `load_state()` in
`engine.py`). The native custom save envelope in `storage.pasm` binds engine
and game identity and payload CRC and delegates the currently selected
compiled-music save service; it does not serialize the active C4 script-slot
table. Emulator savestates capture WRAM, including selector bytes, and are
therefore tied to the matching ROM/build tables. These are three distinct
save mechanisms; this milestone changes none of them.

## Lifetime model

| Source scope | Natural owner/lifetime | Residency planning treatment |
|---|---|---|
| `GLOBAL` | Callable across rooms; an active global may survive a room transition. | Keep its canonical identity resolvable while any activation/continuation is live. A `yield` marks a candidate, not proof of overlap. |
| `ROOM_ENTRY` | Incoming room lifecycle. | Needed at entry stage; may be discarded after its activation retires. |
| `ROOM_EXIT` | Outgoing room lifecycle. | Needed during outgoing cleanup, before room commit. |
| `ROOM_LOCAL` | Active owning room. | Stored/indexed in the room bundle; calls may overlap caller activations. |
| `OBJECT_VERB` | Active room/object resource, invocable by the sentence controller. | All verb records may need directory addressability without being active at once. |
| `OTHER_RESOURCE_LOCAL` / unknown | Source-specific or unresolved ownership. | Preserve uncertainty; do not assign an assumed room/global lifetime. |

`LoadRoom`/`LoadRoomWithEgo` edges are staged: outgoing execution and EXCD
cleanup precede room commit, then incoming ENCD runs. The two complete room
directories need not be simultaneously resident. A global activation that
survives the handoff still needs its old executable identity. `StartScript`,
`StartObject`, and local-script calls may overlap a caller; `chainScript` is a
replacement edge. Dynamic targets remain candidates, not definite calls.

## Canonical DOS-CD FATE census and partition estimates

Input was `/home/chad/ATLANTIS.zip` with
`fate_of_atlantis_dos_cd.json` (`indy4-fate-dos-cd-en`, DOS CD English full
voice, 1993). The machine-readable full result is emitted as `residency.json`
by `compile_scumm_game.py --analyze`.

The census found 4,100 normalized executable identities, a source-wide static
lower bound because rooms 89–91 are indexed but not parsed by the current BOXD
decoder. Of these, 163 are globals, 93 room entries, 93 room exits, 1,077 room
locals, and 2,674 object-verb programs. No SNES selector was allocated.

The 163 available globals classify by configured-root reachability as 1 ROOT,
2 DEFINITE, 131 CONDITIONAL, and 29 POSSIBLE. Thus the root-proven global set
is 3; the corpus has 46 distinct statically referenced global targets, 125
distinct conditional-static targets, and 8 dynamic global script edges whose
candidate union covers all 163 available global bodies. There are 82 global
scripts containing a yield operation; 15 of those also contain a room-load
operation. Operation presence only proves a potential cross-room identity
requirement, not that every such global is simultaneously active.

Parsed-room executable directory sizes (entry + exit + locals + object verbs):

| Rank | Room | Entry | Exit | Locals | Object verbs | Bundle |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 43 | 1 | 1 | 16 | 156 | 174 |
| 2 | 46 | 1 | 1 | 29 | 121 | 152 |
| 3 | 73 | 1 | 1 | 24 | 116 | 142 |
| 4 | 50 | 1 | 1 | 18 | 119 | 139 |
| 5 | 40 | 1 | 1 | 36 | 83 | 121 |
| 6 | 39 | 1 | 1 | 16 | 94 | 112 |
| 7 | 67 | 1 | 1 | 23 | 75 | 100 |
| 8 | 76 | 1 | 1 | 29 | 65 | 96 |
| 9 | 7 | 1 | 1 | 18 | 59 | 79 |
| 10 | 79 | 1 | 1 | 11 | 64 | 77 |

Room 43 has 4 direct-static and 8 conditional-static global references,
including one shared target: 11 unique decoded global targets. Its
room-directory plus all decoded global targets is therefore 174 + 11 = 185,
a **static lower bound** that exceeds the current 178-selector namespace by
7. This is a build-addressability failure if the whole room bundle and every
decoded branch target must receive permanent unique selectors; it is not a
claim that 185 activations execute simultaneously.

Room 46 has 152 room executables and 15 unique decoded static/conditional
global targets (167 known addresses). It also has a dynamic script selector
whose candidate global set spans all 163 bodies. Prebinding that entire
candidate union with the room directory would be 315 addresses: a
conservative candidate-addressability bound, not simultaneous liveness. The
planner reports rooms 46 and 97 with such a known dynamic candidate union
above capacity; room 43 already exceeds capacity on decoded static and
conditional references alone.

## Working-set conclusions and epistemic limits

| Lifecycle case | Planned set/limit | Epistemic status |
|---|---|---|
| Steady room directory | Up to 174 room executable records among parsed rooms. | `STATIC_LOWER_BOUND` source-wide; exact for each parsed room. |
| Room + decoded static/conditional global targets | Up to 185 known identities (room 43). | `STATIC_LOWER_BOUND`; already exceeds 178. |
| Room + all known global bodies | 174 + 163 = 337. | `CONSERVATIVE_UPPER_BOUND` for known parsed identities, not liveness. |
| Room + global targets from a dynamic selector | Up to 315 in room 46 if every known candidate is permanently prebound. | Candidate-addressability upper bound; a resolver can avoid this union. |
| Outgoing/incoming room transition | At most the larger staged room bundle, 174 among parsed rooms, plus identities of surviving globals. | Room stages do not need full overlap; live global set is `UNKNOWN`, bounded by 25 C4 slots. |
| Active script descriptors | 25 C4 slots. | `EXACT` runtime table capacity, not selector or source-corpus capacity. |
| All normalized source executables | 4,100. | `STATIC_LOWER_BOUND`; not a simultaneous working set. |

The graph does not prove a precise maximum overlap of yielded globals, nested
scripts, or sentence actions. Static `StartScript`/`StartObject` edges show
which identities may coexist, but dynamic scheduling and branch/state
conditions prevent turning the transitive union into an exact maximum. The
report preserves per-edge certainty, source PC, caller/callee scope, and
whether an edge is staged, potentially co-resident, or unresolved.

## Dynamic resolution and recommendation

- Dynamic global selectors should resolve through a generated global
  identity directory at invocation; do not reserve one permanent byte
  selector for every possible global merely to encode a dynamic call.
- Dynamic room-local targets should resolve against the active room's local
  directory. A global script with unknown current-room context stays
  unresolved rather than pulling all rooms into one partition.
- Dynamic object/verb references should resolve through active room/object
  metadata. Dynamic room IDs need a generic room catalog/loader or an explicit
  profile constraint.
- Opaque tails, the 7 unresolved reachability records, and unsupported room
  containers remain visible. They can increase a lower bound and prevent any
  global-completeness claim; they do not justify silently dropping targets.

Recommendation: **B — canonical executable identity → generated
resource/bundle identity + local index → currently resident selector
binding**. This is the smallest model that permits room-local bundle entries
to reuse bounded runtime selector addresses while pinning the binding for
every active continuation. A generated resolver can support dynamic globals
without making the entire global corpus simultaneously resident. The first
next implementation seam should be a selector-free executable residency
manifest (global identities, room bundle membership/local indices, resource
provenance, dynamic-resolution requirements), followed by a generic resolver
contract test. Do not change the runtime slot ABI or save format until that
contract specifies pinning/reconstruction for yielded and cutscene
continuations.

The synthetic compiler fixture has two rooms, a room entry/exit/local, object
verbs, a dynamic global selector, and a global whose decoded body contains
both `yield` and a room transition. A separate generated planner test models
300 source executable identities split across ten 30-entry room bundles. It
proves the distinction between corpus count and per-room directory demand;
the source fixture proves lifecycle and dynamic-reference classification.

No production FATE-specific hooks were added. Runtime, SNES backend behavior,
program allocator, gameplay and save formats are unchanged.
