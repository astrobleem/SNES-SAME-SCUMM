# SAME / SCUMM v5 session checkpoint

> UPDATE THIS FILE AT EVERY MEANINGFUL MILESTONE OR BEFORE A LONG/RISKY DEBUGGING PASS.

> **STOP-GATE:** Do not end work for an intermediate diagnostic, build,
> validator result, tooling change, or player choice.  A final response is
> permitted only after the active objective is complete, a source-backed major
> blocker is proven, or the user explicitly requests a status-only stop.  See
> `AGENTS.md`.

## Mission and repository

- Expand SAME's generic SCUMM v5 runtime against Fate of Atlantis with source-backed resources and controlled scenario fixtures.
- Current cone: full-game startup42, room 42 gameplay and effect-bearing object branches.
- Repository: `/home/chad/SAME-0.2.0`; branch `main`; HEAD `3476f81`.
- Worktree is intentionally very dirty with accepted ongoing SCUMM/runtime/tooling work and source artifacts. Preserve unrelated user changes.
- Crash-recovery integrity check (2026-09-04): `git fsck --full --no-dangling` passed for SAME and the shared Mesen2 checkout; `ATLANTIS.zip` passed ZIP CRC validation; `git diff --check`, validator `py_compile`, and the current ROM audit passed. No cleanup/reset/stash was performed.
- Authoritative full-game corpus: `/home/chad/SAME-0.2.0/ATLANTIS.zip`.
- `fatedemo-box.zip` / PLAYFATE is an incomplete demo subset; preserve support but never use it to declare full-game data absent.

## Hard invariants

- No forced script PCs, raw WRAM/script-slot construction, patched predicates, fabricated resources, or room-specific production hacks.
- Scenario fixtures may establish exact source-authored globals, object owner/state/class, inventory, actor, or startup state only through engine-owned setup APIs with recorded source justification.
- Sentences enter through the production mailbox/C20/global-script-2/OBCD path.
- Keep SA-1 inactive and preserve LoROM/header/vector architecture.
- Production movement is healthy; do not alter it without new contradictory evidence.

## Accepted milestones

- Phase 6L: authentic room 49 -> 63 -> 49, generic `$24/$64/$A4/$E4 loadRoomWithEgo`, room lifecycle/ENCD, movement/waits/camera, sound-82 fallback and C25 path.
- Closed room-49/63 cone: mountain Walk To 853/854/855; crate 594 Open/Close; balloon 593 + hose 1014; fishnet 595 fallback; salvage boat 592 verb 9.
- Full-game entry: global script 1 -> room 1 -> `$72 loadRoom(42)` -> room 42 ENCD and LSCR 200/201/208.
- Canonical actor setup: room-1 `putActorInRoom(1,1)` then `putActor(1,145,112)`; stable room 42 actor `(145,112)`, walkbox 1, costume 2, idle, error 0.
- Stable room-42 player boundary follows LSCR 200 retirement; LSCR 201/208 remain authored delayed loops.
- Closed room-42 no-op predicate paths: hatch, suit, compressor, lift, and object-500 probes.
- Object 496 verb 8 with object2 491 adds repaired classes `{1,2,3,4,6}`; object 491 verb 9 consumes that state and returns it to source-defined base configuration, error 0.

## Accepted generic fixes

- C4 slot stride, scheduler allocation/resume, nested parent restoration, slot-owned program/resource rehydration.
- Cutscene owner/depth/override lifecycle across yields and nested scripts.
- C19/C20 sentence lifecycle, variable-verb launch, generated OBCD program-relative entry semantics.
- Generic movement route/portal promotion and actor state ownership.
- `$0F/$8F getObjectState`, `$15/$55/$95/$D5 actorFromPos`, `$06/$86 getActorElevation`, flagged `$D1 animateActor`, `$FF drawBox`.
- Generic object owner/state/class/inventory operations and loadRoomWithEgo family.
- C25 commands 2/3 one-word compatibility and explicit accumulator-width transition before byte diagnostics.
- Closed reset corruption: missing runtime `SEP` shifted C25 error code into bogus `JSR $6AAF`, then fall-through to `$00:8000`; not external RESET.
- Banked scenario class overlay uses `JSL ScummV5_C16_FindRecord_Far`; no bank-local `JSR` into data.
- Generated `ScummV5_Movement_NextBox_Far` begins immediately before route dispatch, after unrelated overlay helpers.

## Mailbox map and controls

- C20 count `$7FD380`; six records `$7FD382-$7FD3A5`.
- Mailbox verb `$7FD3A6`, object1 `$7FD3A8`, object2 `$7FD3AA`, pending `$7E7EC7`.
- Bit variable 2049 is C7 byte `$7E2CA0`, mask `$02`; no overlap with mailbox/C20/slots.
- Fresh A/B/C/D controls all consumed and launched global script 2: no-overlay/bit-overlay crossed with `(8,496,491)` and `(3,490,0)`.
- Script-2 bytes `$9D 04 40 01 88 00 FF` mean `ifClassOfIs(local4, direct class 8)`, not bit `$8801`. Room-55's `$001E -> $8801` writer is real but irrelevant to object 490.

## Object-490 result

- `(3,490,0)` is consumed after stable room-42 readiness; global script 2 issues authentic `$F6 walkActorToObject(1,490)`.
- Route: `(145,112)` box 7 -> portal `(193,112)` -> `(199,110)` -> `(205,108)` -> `(211,106)` -> `(217,104)` -> `(218,104)` box 10, idle.
- First post-movement corruption:
  - bank 9 `$A387`: `JSR $ABCA` (`ScummV5_Movement_OldToNewDir_Far`);
  - helper entered with M=8 but emitted word `AND #$0003`;
  - CPU consumed `29 03`, then executed high immediate byte `$00` as BRK;
  - repeated BRKs consumed the stack and starved the next SCUMM frame, making `$AE` appear stuck.
- Generic fix: helper executes `REP #$20` before word immediates. Regression verifies the runtime transition, not only `.a16` metadata.
- After fix: `$AE` releases; object-490 OBCD completes; object 490 persists state `0 -> 1`; global script 2 and nested/global script 14 retire; error 0.
- Open entry `$0032`: if already state 1, print “already open”; `ifClassOfIs(500, NOT class 32)` conditionally adds class 32 to object 491; then `setState(490,1)`.
- Current root has object 500 class 32, so the conditional class mutation is correctly skipped. No pickup or `putActorInRoom` occurs in this actual Open path; earlier graph wording over-approximated raw opcode-looking bytes.
- Downstream consumer exercised: `(9,490,0)` from opened state takes the authored content branch, observes object 491 state 0, invokes normal dialogue/script 14, and leaves locker state 1, error 0.
- Current actor: room 42 `(218,104)`, walkbox 10, idle; camera follows actor 1.
- Latest ROM `build/same-startup42-direction-fix.sfc`: `ebd936ca9ef89a67853951f3d18f460d4280d061581363b8a5c3f9454ef5e126`.

## Source-coupled suit prerequisite

- Room-42 EXCD's 90-byte program contains `setClass(500, NOT class 32)` and simultaneously establishes other exit state, including object-491 state/class changes. Never inject only the class removal as independent state.
- LSCR 209 writes class 32 back to object 500 during its authored diving-suit sequence.
- To pursue locker-to-suit extraction, model the complete EXCD/re-entry bundle through engine-owned scenario setup or execute the transition normally.
- EXCD/re-entry fixture bundle now encoded at the semantic sentence boundary (never boot/room-install): EXCD `room.42/EXCD` / program `DD`, offsets `$0005/$0045/$0048-$0059`, establishes `491.state=1`; starts LSCR 202, whose source writes `493.state=0`, `495.state=0`, and `498.state=0`; reasserts object 500 class 32 (already present in source DOBJ defaults); and removes class 32 from 491 (a no-op for the same defaults). No owner/inventory/global mutation is coupled to this path. `SAME_SCUMM_SCENARIO_STATE_OVERLAY=491:1,493:0,495:0,498:0` is the corresponding source-backed scenario root.
- Generic fixture support added: `--scenario-state-overlay OBJECT:STATE`, emitted as `ScummV5_ObjectState_ApplyScenarioOverlay_Far` and called at all existing semantic sentence-boundary class/bit overlay sites. Current EXCD ROM: `build/same-startup42-excd-suit.sfc`, SHA-256 `b36d5b78c2202e50806443270b785768437d1af094a1f95a7efb086047195009`, audit PASS.

## Harness/tooling

- Shared Armory baseline (verified 2026-09-04): isolated clone `/home/chad/Nexen-armory`, branch `same-armory-sync`, is clean at published `astrobleem/Mesen2` `mcp-server` commit `4e1e86bb1` (`mcp: expose hook queue health`). It includes the reusable atomic hook snapshots, deterministic CPU stepping, reset/trace lifecycle hardening, and hook-queue health API. Reuse this published baseline; do not modify `/home/chad/Nexen` or `/home/chad/Mesen2`, both of which are dirty shared checkouts.
- No local debugger patch remains to publish for SAME: the useful capability is already published at the commit above. `/home/chad/NexenTrace` is a non-Git local runtime copy and is not an armory source of truth.
- Validator: `tools/validate_scumm_startup42_nexen.py`.
- Readiness uses completed-frame room42/phase0/error0/idle/in-walkbox/cutscene0/C20-empty state plus source slot identities; inactive status-0 slots do not block chaining.
- Generic sentence chaining supports `--sentence2-after-object-state OBJECT STATE`.
- Host-only trace options: `--pre-event-trace-start`, `--pre-event-trace-end`, `--pre-event-trace-count`.
- Local `/home/chad/NexenTrace` trace response cap was raised from 1,000 to its existing 30,000-row ring. That checkout has no `.git`; `/home/chad/Mesen2` is the shared fork but has overlapping uncommitted tooling changes, so no unsafe partial publication was made.
- C29 standalone profile incompatibility remains harness debt, not production debt.

## Commands

Build:

```bash
SAME_FATE_DEMO_ARCHIVE=/home/chad/SAME-0.2.0/ATLANTIS.zip SAME_SNES_ENGINE=scumm_v5 SAME_BUILD_M24RB=1 SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23C=1 SAME_BUILD_SCUMM_M25_MOVEMENT=1 SAME_BUILD_SCUMM_M25A_VALIDATOR=1 SAME_M25A_VALIDATOR_CASE=startup42 SAME_BUILD_SCUMM_SCENARIO_FIXTURE=1 SAME_SCUMM_SCENARIO_CLASS_OVERLAY=491:0x2f SAME_BUILD_SCUMM_PHASE6L_A1D=1 SAME_BUILD_SCUMM_PHASE6LA1D=1 SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE=1 SAME_TAD_PREBUILT_DIR=build/profile-music/fate-m21-final SAME_MUSIC_CATALOG=build/profile-music/fate-m21-final/catalog.json SAME_SNES_OUTPUT=build/same-startup42-direction-fix.sfc bash tools/build_snes.sh
```

Focused locker chain:

```bash
PYTHONPATH=/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-startup42-direction-fix.sfc --output build/startup42-locker-use-chain --frames 1350 --light --atomic-reset --sentence 3 490 0 --sentence2 9 490 0 --sentence2-after-object-state 490 1 --port 45234 --pre-event-trace-start 99999
```

Validation:

```bash
PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q
python3 tools/audit_snes_rom.py build/same-startup42-direction-fix.sfc
git diff --check
```

- 113 focused SCUMM tests PASS; ROM audit PASS; diff check PASS.

## Next frontier

- Paused 2026-09-04 during the source-backed compressor -> hoist continuation.
  The full room-42 local closure (LSCR 200--213) is now cooked.  Real
  `(8,492,0)` starts LSCR 201 (the compressor animation loop) and leaves it
  live; the correct hoist sentence is `(8,500,497)`, not `(8,500,491)`.
  Object 500 verb 8 starts object 497 verb 8, which starts LSCR 207; LSCR 207
  then consumes the running-compressor condition and performs the authored
  hoist cutscene.  It includes persistent `setState(500,0)`, bit 444, and
  subsequent room-82/room-75 branches guarded by source bits.
- Fixed generic headless-scenario print lifetime: fixture builds bypass
  Talk_Begin, so C23 message tokens must be acknowledged when inline text has
  been decoded; otherwise authored `waitForMessage` yields forever with no
  presentation owner capable of releasing it.  Production talk builds are
  unchanged.  Fresh ROM with this fix and the complete room-42 local cone:
  `build/same-startup42-excd-suit-fullcone.sfc`, SHA-256
  `1dae97ccbaf4aa9432312ab0357c6ce1fa72c04c22225127c9d351a17de0e98c`;
  ROM audit passed.
- Fresh current-ROM checkpoints: `build/startup42-fullcone2-stage1.mss`,
  `build/startup42-fullcone2-stage2.mss`, and compressor-on
  `build/startup42-fullcone2-switch.mss`.  The hoist run state is
  `build/startup42-fullcone2-hoist.mss`; inspect its report on resume and
  continue in bounded safe frame windows.

- 2026-09-04 suit continuation update: the semantic state overlay is live and
  applied only at sentence publication.  From the EXCD bundle
  `491:1,493:0,495:0,498:0`, `(8,500,491)` is consumed by production C20 and
  global script 2.  Object 500 verb 8 source-starts object 497 verb 8, which
  source-starts room-42 LSCR 207.  The first build omitted both object-497
  OBCD and LSCR 207 from the executable fixture cone; they are now explicitly
  cooked.  LSCR 207 reaches its authored fallback dialogue, “Better turn that
  compressor on first.”  This establishes the next source-backed prerequisite:
  compressor activation, not a mailbox, movement, or EXCD-overlay defect.
- Startup42 cone now includes objects 493, 490, 497, 500 and LSCR 207.
  Object 493 is the compressor's source OBCD dependency; derive its activation
  writer/complete coupled state before attempting the suit branch again.
- Follow-up source audit: object 492 is the actual air-compressor switch;
  object 493 is the compressor body and its direct use path is descriptive.
  Object-492 verb 8 performs the real walk/OBCD/script path.  Its durable
  continuation starts LSCR 202, which was missing from the executable local
  cone; startup42 now includes LSCR 202 and object 492 as well.  Re-stage the
  ROM and execute `(8,492,0)` before retrying `(8,500,491)`.
- Latest ROM after the complete switch/LSCR202 cone:
  `ff9ae64e171e69e5c53533410f62b6804ff07eaa4ea7b7569afe122fd41a5bdb`
  (`build/same-startup42-excd-suit.sfc`, ROM audit PASS).
- Latest rebuilt ROM after 497/207 (before object-493 rebuild):
  `build/same-startup42-excd-suit.sfc`
  `3a62034c501dc43c6a2a1e5db2c458799f68c4a488f3f1d3bee63051be0411ed`;
  audit PASS and `python3 -m unittest tests.test_scumm_v5_engine` = 113 PASS.

- Object-490 Open and its immediate authored content consumer are complete at the current root.
- Highest-value continuation is the source-coupled room-42 EXCD/re-entry -> suit/locker path. Preserve coupled object-491 state/class and object-500 class changes; do not return to arbitrary room-42 verbs.
- Current rebuilt suit-cone ROM: `build/same-startup42-suit.sfc`, SHA-256 `675d611806187bc7f3a7ea24f892944701b4422efa05440db41032a9d0f54848` (ROM audit passed). The earlier direction-fix ROM remains a known-good locker-chain identity above.
- 2026-09-04 active suit/switch investigation: executable startup42 closure now also
  includes room-42 LSCR 213 (local, not global; full-game global-script count is
  200).  Current ROM `build/same-startup42-excd-suit.sfc` is
  `830d9d8684d647bd387890668fa0aa727086cda427e2adcdb504c3caff416a25`;
  audit passes.  `(8,492,0)` is consumed and global script 2 reaches source
  PC `$038c`, then jumps to its authored wait path at `$052c` and retires
  before `startObject`; no object-492 child slot is allocated.  This is the
  current semantic-dispatch frontier, not a missing LSCR-213 resource claim.

## Active suit/re-entry investigation (2026-09-04)

### Hoist room-82 continuation checkpoint (2026-09-04)

- Added the source-backed room-82 transition target required by LSCR 207's
  authored `$72 82` path.  Startup42 now cooks room 82 entry-only: ENCD/EXCD
  are retained, dormant LSCR/OBCD programs do not consume IDs.
- Fixed the cooker to enforce program-ID capacity only after executable-script
  filtering.  Startup42 must use the scenario-fixture build flags; otherwise
  the ordinary room-49 object set exhausts the 8-bit program namespace.
- Fresh compatible build command:
  `SAME_SNES_ENGINE=scumm_v5 SAME_BUILD_SCUMM_M23A=1
  SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23C=1 SAME_BUILD_M24RB=1
  SAME_BUILD_SCUMM_M25A_VALIDATOR=1 SAME_BUILD_SCUMM_SCENARIO_FIXTURE=1
  SAME_BUILD_SCUMM_M25_MOVEMENT=1 SAME_M25A_VALIDATOR_CASE=startup42
  SAME_FATE_DEMO_ARCHIVE=$PWD/ATLANTIS.zip
  SAME_TAD_PREBUILT_DIR=build/music-m8-fate
  SAME_BUILD_SCUMM_PHASE6L_A1D=1
  SAME_SNES_OUTPUT=build/same-startup42-hoist-room82.sfc bash tools/build_snes.sh`
- ROM `build/same-startup42-hoist-room82.sfc` SHA-256:
  `d79dbe12a793389baa4502087e115da06322005c48d2d629d353e6e6e3aabde3`.
  Audit PASS; bank 0 ends `$F558`, 2663 bytes free before header.
- Fresh frame-safe checkpoint:
  `build/hoist-room82-before2.mss`, created from the exact fresh ROM above at
  room-42 readiness (frame 882).  Old `.mss` files are ROM-specific.
- Hoist sentence `(8,500,497)` consumes into C20 with error 0, but the current
  bounded run has not yet advanced past its allocated script-2 slot: slot 1
  remains script 2/program 210 at PC 0 while room 42 stays installed.  This is
  the next runtime frontier; inspect the scheduler/fixture profile before
  claiming room-82 transition completion.
- Focused validation: `PYTHONPATH=src python3 -m unittest
  tests.test_scumm_v5_engine -q` => 116 passed; `python3
  tools/audit_snes_rom.py build/same-startup42-hoist-room82.sfc` => PASS;
  `git diff --check` => PASS.

### Hoist continuation checkpoint (2026-09-04)

- The requested `startup42-fullcone2-hoist.mss` was authored from ROM
  `1dae97ccbaf4aa9432312ab0357c6ce1fa72c04c22225127c9d351a17de0e98c`, but
  that exact ROM file is no longer present.  Do not load this state with a
  different ROM.  The matching earlier diagnostic pair is
  `build/current-hoist.mss` + `build/same-startup42-excd-suit-fullcone.sfc`
  (`cf87e214...`), and is being used only for bounded diagnostics.
- Corrected the validator's actor-2 observational indexing: C31 position is
  `$7FF1A0 + actor*4`, moving is `$7FF220 + actor`, so actor 2 is `$7FF1A8`
  and `$7FF222`.  The previous zero/random actor-2 result was a validator
  read error, not production state.
- On the compatible hoist state, LSCR 207 is at its authored `waitForActor`
  continuation (PC `$53`, slot 8, program 230, cutscene depth 1, error 0).
  Actor 2 is genuinely moving from `(193,112)` toward the 16-bit target
  `(263,109)`; movement flags are `0x0A`.
- Bounded trace currently shows actor 2's X low byte advancing by 7 while its
  high byte remains zero across the `0xFF` crossing.  This is the active
  generic movement-width investigation; no production change has yet been
  made.  Do not confuse this with stale coordinate restoration.
- A prior experimental C31 reset helper regressed startup to room 0 and was
  removed; it must not be reintroduced.
- Hoist continuation on fresh ROM `build/same-startup42-hoist-widthfix.sfc`
  completed in bounded emulator stepping.  Actor 2 moved from `(193,112)` to
  `(263,109)` with the high byte preserved and then became idle; LSCR 207
  retired cleanly, object 500 state is `0`, and C7 bit 444 is set.  Room 42
  remains installed with error `0`; the persistent room/global loops remain
  scheduler-owned as authored.
- Root cause of the movement wrap was the actor-2 observational probe's
  `SEP #$20` leaving M=8 before the production X fixed-point commit.  A
  generic `REP #$20` now restores the word arithmetic ABI after the probe;
  focused `test_scumm_v5_engine` coverage guards this crossing-width seam.
- Current hoist-widthfix ROM SHA-256:
  `8941e97cc9a2d6ec93a46a0aada9037d25614df543ca60b71526c9fe68b91321`.
- Existing fixture-only waitForMessage coverage remains in
  `tests/test_scumm_v5_engine.py` and
  `tools/validate_scumm_message_wait_nexen.py`: headless inline text releases
  only without a presentation owner; normal Talk_Begin ownership is retained.

- Hoist continuation work is using fresh ROM builds; do not load the old
  `startup42-fullcone2-hoist.mss` after any rebuild. Latest ROM currently under
  investigation is `build/same-startup42-hoist-actor2.sfc`, SHA-256
  `78af8b11a90d85fdbedb23e0dc067692b6661ad22fb9101e6334bb9504bf222a`.
- Source-root actor-2 fixture correction: C14 actor records use 0x40-byte
  records (actor 1 at +64, actor 2 at +128); validator actor-2 reads were
  corrected accordingly. Actor 2 identity/room is now observed as costume 28,
  room 42, but C31 position remains zero after room entry. Source ENCD
  authoritative placement is `(2,184,101)`; this is the immediate hoist
  frontier. Additional fixture-only reconciliation was added after scheduler
  movement passes, but the current trace still requires isolating the later
  C31 position/movement-state writer before accepting it.
- New observational validator fields: actor-2 position/moving/walkbox,
  C14 costume/room, and last putActor request/result/count. No validator WRAM
  writes were added.

- The EXCD sentence-boundary scenario root is now exercised, not merely
  generated.  Its source-backed bundle is `491.state=1`, `493.state=0`,
  `495.state=0`, `498.state=0` from room-42 EXCD plus LSCR 202; no coupled
  owner/inventory/global write was found in that path.
- Room-42 LSCR 212 at offset `$0000` is the source writer for object 491
  class 12 (`setClass(491, 12)`): it is the additional repaired/rigged-suit
  predicate.  The current controlled root therefore uses class mask
  `491:0x102f` (classes 1,2,3,4,6,12), retaining the source default class31.
- Fixture cone correction: object 491's complete OBCD was omitted despite
  global script 2 reaching its real verb-8 entry `$007c`.  The startup42
  closure now includes `--executable-local-object 42:491`; this is a
  source-resource closure fix, not an OBCD semantic workaround.
- Fresh ROM with the corrected cone:
  `build/same-startup42-excd-suit-rigged.sfc`
  `96b3a3af540e8170c41f004f2930fb74f700cd43b45f35dd045438238e7ee867`
  (audit PASS).
- `(8,491,0)` is now proven through production C20/global script 2, real
  walk `(145,112)->(218,104)`/box10, `$AE` release, and object-491 OBCD
  child program entry `$007c`; it retires error-free.  That verb itself has
  no durable mutation under the rigged bundle.
- `(8,500,491)` remains an authored global-script-2 fallback before OBCD;
  static script-2 prelude tests primary object 500 for class7, which no
  source writer currently establishes.  Do not treat object 500 as the
  active suit action without a source writer.
- Compressor switch verb 6 `(6,492,0)` was executed through production
  movement to `(147,123)` and its normal global-script-14 dialogue path,
  but does not currently start LSCR 201.  The next task is to finish the
  source-level classification of the global-script-2 class/verb dispatch and
  identify the true authored action that establishes the running-compressor
  condition, rather than probe further tuples.

- Review correction, 2026-09-04: the previous fixture-only C23 shortcut was
  removed. Headless fixture builds now enter the existing `Talk_Begin` /
  `Talk_FrameBegin` / `Talk_FrameEnd` lifecycle with presentation optional;
  C23 delivery is no longer treated as logical message completion. Host
  focused suite: 116 tests pass. A reduced message-profile Nexen run is not a
  valid oracle because its fixed snapshot offsets do not match the full
  startup layout; this is validator-profile compatibility debt.
- New ROM after that correction:
  `build/same-startup42-hoist-room82-talklifecycle.sfc`, SHA-256
  `821e58555d1c2cc979bb781a93f269908f083bbd62dcffe68a20e98d1f956ec6`.
  Build used the startup42 full-cone flags and `ATLANTIS.zip`; audit passed.
- Message-profile ROM built for focused fixture probing:
  `build/same-scumm-message-talklifecycle.sfc`, SHA-256
  `9d3a5a8c05815f8adf57d6ffa8817a48c6a083a0de176c26d90d8016ad62d6a5`.
  Its existing validator failed on incompatible hard-coded layout addresses
  (garbage snapshots after a valid Talk start/stop), so it is not accepted
  as runtime evidence.
- Latest hoist rerun remains the pre-correction observation on
  `build/same-startup42-hoist-room82.sfc`, SHA-256
  `d79dbe12a793389baa4502087e115da06322005c48d2d629d353e6e6e3aabde3`:
  sentence `(8,500,497)` was published/consumed with error 0, but LSCR 207,
  `setState(500,0)`, bit 444, and room 82 were not dynamically observed.
- Current immediate work is paused for review publication/handoff; do not
  load any save state against a non-matching ROM.
