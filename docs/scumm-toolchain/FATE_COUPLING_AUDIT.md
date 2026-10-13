# FATE Coupling Audit

Baseline: `85d0d245e57fc24558972b54d833d2b98d5fff66`.
The grouped, machine-readable inventory is [`fate_coupling.json`](fate_coupling.json).
Every entry has exactly one agreed classification. Counts are mechanism
groups, not counts of every numeric literal in tests.

| Classification | Count | Meaning |
|---|---:|---|
| `GENERIC_SCUMM_SEMANTIC` | 2 | Reusable VM and interaction contracts exercised by FATE. |
| `COMPILER_DERIVABLE_DATA` | 12 | Source facts and deterministic target records derivable offline. |
| `FATE_PROFILE_DATA` | 3 | Edition/content selection and title-specific source import policy. |
| `TEMPORARY_BRINGUP_HOOK` | 2 | Compile-gated scenario-root/controller bootstrap code. |
| `TEST_FIXTURE_ONLY` | 5 | Replay expectations, provenance checks and fixture-profile data. |
| `TRUE_FATE_SPECIFIC_QUIRK` | 0 | No irreducible title-specific production semantic exception confirmed. |

## Findings

The opcode VM, scheduler, object/verb dispatch, talk/input edge ownership,
actor movement, save semantics and asynchronous room lifecycle are generic
SCUMM behavior. FATE supplies exercised scripts and outcomes; it does not
justify room-, object-, script-, variable- or PC-number branches in ordinary
runtime paths.

Two native source areas are materially different: `ScummV5_Scenario_Fixture_*`
actor initialization/reconciliation and `SAME_BUILD_SCUMM_CONTROLLER_FIXTURE`
room-68 handoff/string seeding are compile-gated bring-up behavior. They are
classified `TEMPORARY_BRINGUP_HOOK`; keep them isolated and eventually
represent them in an explicit fixture/bootstrap resource or retire them when
a source-driven fixture exists.

Raw v5 offsets, LFLF/ROOM boundaries, OBCD verb entries, script bodies, hashes,
MAXS limits and selector mappings are `COMPILER_DERIVABLE_DATA`. Fate edition,
archive member names, selected source rooms and script groups are
`FATE_PROFILE_DATA`. Program-ID allocation is generic backend policy; the
choice of which Fate executables to ship is not.

The source-bound room compiler (`room_compiler.py`, surfaced by
`compile_scumm_room.py`) is now itself recorded as `COMPILER_DERIVABLE_DATA`.
It contains generic SCUMM v5 resource/operand knowledge and no room-, object-,
script- or bit-specific FATE rules. FATE room 7 values appear in the optional
integration expectations only.

The whole-game analyzer (`game_analysis.py`, `compile_scumm_game.py`) is also
generic compiler-derived analysis. It distinguishes resource identity from
executable identity and includes no FATE root/script/object constants; title
roots are supplied by profile data.

The whole-source package path (`package_scumm_v5_source_msu.py`) is likewise
generic compiler-derived packaging. The DOS-CD profile and external archive
select the integration corpus; package generation itself consumes the complete
analyzed ProgramUnit/resource directory without title-specific selection rules.
The replay evidence journal/recovery helpers are integration-test tooling: they
bind snapshots to build identities and preserve missing observations as missing.

The residency planner (`residency.py`) is another compiler-derived analysis:
it classifies global/room executable scopes and annotates lifecycle edges
without allocating selectors or treating title room numbers as policy. The
ProgramUnit projection preserves per-verb semantic identities while grouping
the full OBCD object body that the SNES backend actually assigns one selector
to. Its pure binding simulator is test-only; it does not change runtime
dispatch.

Title audio converters and Fate sound IDs are source import/profile data. In
particular, `embedded_audio.py` currently contains a special logical
sound-80/sound-82 composite route for a bounded Fate music build. That is not a
SCUMM sound-opcode semantic; move the pairing/realization to profile or audio
backend data. The generic meaning “request logical sound N” remains separate
from selecting TAD/MSU or another realization. Do not add more runtime
branches for title sound numbers.

The embedded iMUSE event/SysEx parser is a separate source-format concern. Its
currently supported command vocabulary and payload checks are derivable from
resource bytes and belong in the front end/compiler analysis; this partial
parser support does not itself make a Fate-specific runtime quirk.

The replay and validators intentionally know concrete room/object/verb IDs,
variables/bits, script numbers, source offsets, body hashes and expected
selectors. These are `TEST_FIXTURE_ONLY`: acceptance inputs should fail closed
if source or mapping changes, but must not leak into engine policy. The room-7
object 118/119 progression and resulting local-script transition are retained
as content-specific integration observations, not generic SCUMM rules.

One useful contrast in `engine.py`: initializing v5 `VAR_CURRENT_LIGHTS` to
`$000B` is documented as a generic `resetScummVars` default (`GENERIC_SCUMM_SEMANTIC`),
even though a Fate global exposed the omission. By contrast, the observed
`VAR_CHARINC == 4` in a hash-bound Fate checkpoint is explicitly not a universal
default; it is integration-state evidence and must not become a VM initializer.

## Runtime identity scan

The production-source search found title identities in two distinct places:
compile-gated scenario/controller-fixture branches (rooms `$2A`/42 and
`$44`/68, actor and string setup), and a host embedded-audio special case for
the Fate composite logical sounds 80/82. The first is a temporary/test
bootstrap; the second is `FATE_PROFILE_DATA` leaking into an audio adapter.
Other compile-time profile controls seed object 595/class masks or logical
sound 82 for bounded M23C/M24R-B tests and restrict a controller visual witness
to room 42. Those are `TEST_FIXTURE_ONLY`, not retail runtime policy.
The ordinary controller path below the fixture branch resolves active room
object/verb metadata, and the core host VM does not branch on the room-7
object/script IDs in the replay.

Concrete source offsets and body hashes recorded by replay validators are
`TEST_FIXTURE_ONLY` evidence; parsing those offsets/hashes from a selected
archive is `COMPILER_DERIVABLE_DATA`. ROM/WRAM addresses are SNES backend
layout, not FATE identity. The executable allocator is generic; generated
selector numbers and hardcoded PCs in reports/validators are acceptance data,
not production selectors or dispatch policy.

No `TRUE_FATE_SPECIFIC_QUIRK` is recorded. A future such classification needs
evidence that authored title behavior cannot be represented by generic SCUMM
semantics or profile/source data.

The JSON records path, region, current consumer, desired destination,
migration action and priority. Classify the *fact*, not the file extension:
language rule, derivable source fact, edition choice, temporary bridge,
test-only expectation, or demonstrated irreducible quirk.
