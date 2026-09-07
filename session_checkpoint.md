# SAME / SCUMM v5 session checkpoint

> UPDATE THIS FILE AT EVERY MEANINGFUL MILESTONE OR BEFORE A LONG/RISKY DEBUGGING PASS.

> **STOP-GATE:** Do not end work for an intermediate diagnostic, build,
> validator result, tooling change, or player choice.  A final response is
> permitted only after the active objective is complete, a source-backed major
> blocker is proven, or the user explicitly requests a status-only stop.  See
> `AGENTS.md`.

## Current WIP review status (2026-09-07)

- Actor cooker evidence is accepted: independent host composition and the
  actual emitted generator frames match 2048/2048 for idle and walking. The
  old striped output remains a negative regression witness.
- Fresh corrected ROM: `bbfabe380ed5b1c305af8174ab191bc79eb77e117e09a87be64df58b266f82d7`.
- The normal controller replay reaches the walking boundary and completes the
  locker/inspection semantic path. Native captures were opened; background,
  actor presence/movement, HUD, locker, active dialogue, cleared dialogue,
  and post-dialogue are visibly present in the final run.
- Walking capture synchronization is now backend-owned: the validator waits
  for a new accepted PRESENT after the walking request, requires backend
  pending == committed, valid surface/tile/palette, idle/unlocked backend, and
  empty event FIFO, then captures the paused framebuffer without advancing.
- Remaining actor-fidelity gate: a same-pose indexed-surface/native proof is
  not yet accepted. Earlier captures taken before the actor PRESENT retry show
  a partial live surface (`accepted_present` unchanged, `rejected_dirty=1`);
  they are preserved as negative timing witnesses. A later 4096-frame fence
  commits only after the actor has reached its destination, so it no longer
  binds a walking pose. This is a bounded backend conversion/actor-present
  timing blocker, not a cooker result.
- Native room/background and HUD evidence is useful, but actor costume
  fidelity is not accepted. `visualfix26-run1/native/03-walking.png` is a
  preserved FAIL witness; other captures containing Indy are UNKNOWN for actor
  fidelity until matched against a correct source pose.
- Review WIP branch: `review/controller-room42-visual-wip`, based on published
  `9639f1c`; local review commit is being updated with unmodified native PNGs,
  defective captures, reports, and focused source/tests. Public screenshot
  publication was explicitly authorized by the user.
- Do not resume HUD/dialogue or rendering fixes until the reviewer has inspected
  this packet. Main worktree remains intentionally dirty and untouched.
- The controller validator now includes a no-advance target surface dump at
  the walking capture boundary. A replay using it did not reach that boundary
  before the existing native-reference polling terminated, so exact walking
  surface/native equivalence remains unclaimed.
- Actor-pipeline audit: independent host composition versus the actual emitted
  generator `.bin` now matches byte-for-byte for source frames 1 and 2. The old
  malformed stage was the cooker’s row-major interpretation of column-major
  SCUMM cel data. Fresh corrected ROM `bbfabe380ed5b1c305af8174ab191bc79eb77e117e09a87be64df58b266f82d7`
  shows coherent standing/walking actor in opened native captures. Exact
  walking surface/native crop binding is still pending; actor gate is not final
  PASS. HUD/dialogue work remains paused.
- Actor-pipeline audit: source/host composites are coherent; the old cooker was
  proven wrong by row-major cel indexing and produced striped output. The
  isolated review branch now has the generic column-major cooker fix and focused
  regression. Corrected cooked idle/walk canvases match host bytes exactly.
  Native actor fidelity is still unproven because the corrected ROM has not yet
  been rebuilt/captured; preserve the malformed native walking witness.

## Mission and repository

- Expand SAME's generic SCUMM v5 runtime against Fate of Atlantis with source-backed resources and controlled scenario fixtures.
- Current cone: full-game startup42, room 42 gameplay and effect-bearing object branches.
- Repository: `/home/chad/SAME-0.2.0`; branch `main`; HEAD `3c88f54`.
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

- Controller/semantic room-42 path was reported passing, but the visible
  presentation milestone is NOT accepted.  The cited native captures in
  `build/controller-room42-finaltest-clean-run2/` and
  `build/controller-room42-visual-repro4/` were inspected and show
  multicolored static, not room/Indy/cursor/dialogue.  Preserve them as failing
  evidence.  Semantic controller execution remains separately useful; visible
  controller-playable acceptance is incomplete.
- Latest native presentation run: `build/controller-room42-nativefix-root42-v5.sfc`,
  SHA-256 `ffc37a47bed9547e0fceba8a4159d3411acb95e11dd7a71e8bce3ce13a79eb6f`.
  Its inspected native captures contain the room-42 harbor backdrop rather
  than static noise. This is only a partial correction: the target still has
  no native SCUMM costume/actor renderer, and the bounded HUD/cursor-control
  and dialogue overlay is partial/clipped. The visible controller milestone
  remains incomplete.
- Failing visual ROM: `build/controller-room42-finaltest.sfc`, SHA-256
  `4a98d260b33b60d9db45d090647fc9e4a76f2d8481f1a5265b315820f7d44676`.
  The intermediate indexed surface is authentic room-42 scenery, proving the
  first known gap is after surface generation, not source room decoding.
- Presentation investigation: the stale generated overlay service consumed
  non-overlay surface/palette/present packets before the Mode-3 backend.  The
  generated service now falls through without writing overlay state/error;
  the event drain also gates its one-frame stop only on SET_LAYER, so pending
  room/storage/video packets are not stranded by a stale PREPARING state.
  This is not yet a visual acceptance claim; native room capture must still be
  inspected after a same-scenario rebuild.
- The validator now requires accepted native present state, an empty event FIFO,
  and VRAM/CGRAM equality with production shadows before capture. This closes
  the former weak readiness claim but does not certify actor/cursor/costume
  presentation.
- The original visual report was false evidence: `01-ready.png` was opened and
  is multicolored static. The corrected v5 native captures were also opened;
  they show the authentic room-42 harbor/boat backdrop, but no target-rendered
  Indy/costume or visible cursor, and HUD/dialogue text is clipped. Semantic
  controller execution passes; visible controller-playable acceptance remains
  incomplete. The concrete target blocker is that actor state exists but no
  target SCUMM costume-to-tile/OAM renderer is implemented.
- Controller visual validator currently has weak historical readiness evidence;
  it now captures dialogue while logically active and distinguishes semantic
  readiness from native framebuffer evidence.  `04-dialogue-active.png` is
  required for a future passing report.
  Deterministic replay command:
  `PYTHONPATH=src python3 tools/validate_scumm_room42_controller_nexen.py
  --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom
  build/controller-room42-finaltest.sfc --output
  build/controller-room42-finaltest-clean-run2 --startup-frames 500 --port 44247`.
  Visual surface capture is `01-ready-surface.ppm`; final event evidence is
  local under `build/controller-room42-finaltest-clean-run2`.
- Controller-only fixture remains explicitly labeled scenario/presentation
  coverage: it uses normal input, cursor/verb/object selection, mailbox, C20,
  script 2, movement, OBCD, and C23/Talk. It never constructs C20 or writes
  script state from the validator. The fixture actor setup now calls the generic
  `DefaultActor` initializer before applying source-backed costume/placement,
  preventing zero scale/speed inherited state. Controller object2 is encoded as
  zero, matching `(verb, object1, object2)` semantics.
- Focused controller regression source:
  `tests/test_scumm_v5_controller_fixture.py`; target validator:
  `tools/validate_scumm_room42_controller_nexen.py`.
- Screened review update published on
  `astrobleem/SNES-SAME-SCUMM:review/hoist-message-lifetime` at commit
  `55627725d37fe3f161908bf212203dc641cd15d7`, verified equal to remote HEAD.
  Review files: `review_room42_controller_scene.md`,
  `review_room42_controller_checkpoint.md`,
  `review_room42_controller_source_extract.pasm`, and the focused controller
  test source. ROMs/captures/resources remain local.

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

### Compressor inverse and same-ROM hoist continuation (2026-09-05)

- Built separately as `build/same-startup42-compressor-off.sfc` from
  `ATLANTIS.zip` with the startup42/scenario-fixture/M25 flags above. SHA-256:
  `dc0f923bb8569667ac58a37b69ea5f4995463111a07ad6111053af3c91633eee`.
- Focused inverse run:
  `build/startup42-compressor-off-run2/report.json`, command:
  `PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-startup42-compressor-off.sfc --output build/startup42-compressor-off-run2 --frames 1400 --light --minimal-observation --sentence 9 492 0 --port 45501`.
  The mailbox sentence was consumed at frame 960; script 210 executed; room 42,
  error 0, C20 empty, and object 492 remained state 1 under the controlled
  source-backed state overlay. This establishes clean inverse dispatch but does
  not claim that verb 9 reverses the compressor state.
- Same-ROM continuation:
  `build/startup42-compressor-inverse-hoist/report.json`, command:
  `PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-startup42-compressor-off.sfc --output build/startup42-compressor-inverse-hoist --frames 2600 --light --minimal-observation --sentence 9 492 0 --sentence2 8 500 497 --sentence2-after-script-retired 2 --port 45503`.
  The inverse sentence was consumed, then hoist was submitted and observed:
  room 82 entry around frame 1152, return/continued room-42 lifecycle by the
  later run, object 492 state 1, object 500 state 0, error 0, cutscene depth 0,
  C20 empty, and `setstate_count=2`. The final snapshot is during continuing
  authored delayed scripts (not a claim that all room-42 scripts are retired).
- Current stable evidence remains the prior accepted debug91 compressor/hoist
  pair; this inverse experiment is supplementary and must not replace its
  matching ROM/savestate evidence.

## Next frontier

### Current continuation: compressor/hoist after yielded-slot fix (2026-09-05)

- The target message regression is now execution-proven on
  `build/same-message-debug80.sfc`, SHA-256
  `0508472287ba26094af1a35b4b8c0e967419a8a3acb934e1ac4fe6e75cfe5799`.
- Root cause: `$AE` cold/far wait entry returned through a profile seam with
  the post-decode PC (`$000B`), and the C4 epilogue saved that cursor over the
  suspension state. Generic fix: yielded waits return through the shared
  boundary and the C4 scheduler rewinds the fully decoded `$AE` before the
  authoritative slot save; the completion path preserves the committed slot.
- Target evidence: slot 200 remains yielded at PC `$0009`; C23 keeps logical
  ownership through the delay; completion occurs at recorded logical tick 15
  (16 inclusive frame-boundary states); `VAR_HAVE_MSG` clears on the next loop,
  then the script resumes and executes its continuation with error 0.
- Validator command/result:
  `PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_message_wait_nexen.py --rom build/same-message-debug80.sfc --manifest build/m25a-validator/message/manifest.json --output build/m25a-validator/message/message-wait-debug80.json --nexen /home/chad/NexenTrace/run/nexen-wrapper --port 45383 --max-frames 600` -> PASS.
- Current next action: rebuild startup42/hoist with the same flags and ROM
  identity discipline; observe compressor activation before `(8,500,497)` and
  continue LSCR 207. Do not claim hoist completion from static evidence.

### Hoist execution evidence after message-lifetime correction (2026-09-05)

- Focused host suite now passes 122 tests, including source checks for the
  fixture long-text logical cursor/lifetime path.  The validator now records
  M24RB state and narrow authored state-write witnesses without adding ROM
  state or changing production behavior.
- Fresh validator run uses `build/same-startup42-hoist-debug38.sfc`, whose
  SHA-256 is `75ce5647cad61948b028ae980a9bc08953883273994a43922cf64d388613a03f`;
  it is byte-identical to debug37 because this pass changed only the host
  validator.  Build audit passes; bank 0 ends `$F9E1`, with 1502 bytes free.
- Run `build/startup42-hoist-debug38-effects/report.json` proves the
  compressor-to-hoist chain on one same-ROM run: `(8,492,0)` consumes and
  makes object 492 state 1; `(8,500,497)` launches LSCR 207; object 500 is
  written state `1 -> 0` at frame 958; bit-444's packed byte is written at
  frame 1016; and the authored branch installs room 82 at frame 1087.
- Room 82 continues error-free.  The long system message reaches logical
  raw lengths 52/99/135 (including encoded controls, with 135 observed),
  while only the compact presentation window is capped.  Talk lifetime shows
  delayed ownership (`wait_blocks`), subsequent `wait_resumes`, and normal
  completion; no fixture auto-clear is used.  Final run at frame 1252 is
  room 82, error 0, cutscene depth 0, C20 empty.
- M24RB diagnostic state after this validator profile is
  `state=0, trigger_marker=1, deferred_count=1`; the startup42 validator
  deliberately owns the scenario scheduling profile, so this is not used to
  claim an independent M24RB driver transition.  The authored room-82
  transition and LSCR-207 effects above are separately observed.
- Target message evidence is in the same report's `trace`: room-42 messages
  with raw lengths above 32 complete their waits, and the room-82 message
  starts/ends with active/have_msg ownership rather than immediate clear.
- Next: keep the reviewed headless/message and scheduler diffs screened,
  update the review-only handoff branch from published history, and retain
  the exact ROM/report pair.  Do not load unrelated savestates against this
  ROM.

### Current reviewed hoist handoff (2026-09-05)

- The accepted headless message contract is logical, not auto-clear:
  presentation may be absent, but ownership, delay, continuation, and normal
  published-clear/waitForMessage release remain active.  The old paragraph
  below describing C23 acknowledgment as logical completion is superseded.
- Focused host validation: 122 tests pass with
  `PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q`;
  `git diff --check` and validator Python compilation pass.
- Same-ROM startup42 run:
  `build/same-startup42-hoist-debug38.sfc`, SHA-256
  `75ce5647cad61948b028ae980a9bc08953883273994a43922cf64d388613a03f`.
  Build uses `ATLANTIS.zip`; bank 0 ends `$F9E1`, 1502 bytes free.
- Execution evidence:
  `build/startup42-hoist-debug38-effects/report.json` records `(8,492,0)`
  consumption and compressor activation; `(8,500,497)` entering LSCR 207;
  object 500 state `1 -> 0` at frame 958; bit 444 packed-byte change at
  frame 1016; and authored `loadRoom(82)` at frame 1087.  The run remains
  `error=0`.  Room-42 logical messages of raw lengths 52, 99, and 135 with
  encoded controls completed through the retained Talk lifecycle.
- Room-82 entry is proven; later room-82 gameplay is not claimed.  Validator

### Geometry gates and hoist closure update (2026-09-05)

- Geometry acceptance is closed and must not be reopened without contradictory
  evidence: target accessor 64/64, copyright-free high-index multi-leg route,
  normal wait release, and room-55 lookup all pass.  Retain those regressions.
- Corrected generated executable-program banking is in
  `tools/generate_snes_cooked_rooms.py`: executable programs are packed into
  explicit LoROM banks so long `Program_*` fetches retain the emitted bank.
- Hoist continuation fix is generic room-slot selector recovery in
  `runtime/snes/engines/scumm_v5.pasm`: at an outer, non-nested room lifecycle
  boundary, a neutral selector is reconciled with the live slot-0 program
  before rehydration/saving; nonzero identity mismatches remain fail-closed.
- Final matching ROM: `build/same-hoist-final.sfc`, SHA-256
  `8484361a7d2f93d5046ed6401c91ab32c336680eb4e6187365d7bb9376f957d1`.
- Final chain artifacts (all same ROM):
  `build/hoist-final-start/report.json`,
  `build/hoist-final-compressor/report.json`,
  `build/hoist-final-hoist500/report.json`.
- Fresh startup reaches room 42, actor 1 `(157,101)` box 7, error 0.  The
  compressor sentence `(8,492,0)` is consumed and leaves object 492 state 1
  in `hoist-final-compressor`; that exact state saves and loads for hoist.
- Hoist `(8,500,497)` consumes on the matching ROM.  Observed writes:
  object 500 state `1 -> 0` at frame 1567 and bit-444 byte change at frame
  1598.  Room 82 is entered and executes error-free; room 82 reaches phase 5,
  then the authored lifecycle returns to room 42 at frame 1929/1930 with
  error 0, cutscene depth 0, C20 empty.  This is execution evidence, not a
  static expectation.
- The prior room-82 PC-0 observation was stale slot-0 rehydration after the
  selector became neutral, not an F5 resource error.  The original generator
  bank defect was fixed before this lifecycle result.  The attempted broad
  common-boundary save experiment was reverted; do not revive it.
- Focused host validation: `PYTHONPATH=src python3 -m unittest
  tests.test_scumm_v5_engine tests.test_scumm_v5_room tests.test_m25a_validator`
  -> 151 tests, OK.  Final ROM build audit and `git diff --check` pass.
- Current review publication remains `review/hoist-message-lifetime` at
  `b0c531eece1b4f165e8bc324731a799296bdfa5e`; focused final hoist evidence
  and the two generic fixes still need screened publication/update there.
  M24RB fields (`state=0`, `trigger_marker=1`, `deferred_count=1`) are
  profile diagnostics because startup42 owns scenario scheduling.
- Screened review publication: repository
  `astrobleem/SNES-SAME-SCUMM`, branch `review/hoist-message-lifetime`, remote
  HEAD `7aab755599ba6c6dc9e84ee6f675db6a064907f2`.  Published files are
  `review_correction_20260905.md`, `review_tests_20260905.md`, and
  `checkpoint_summary_20260905.md`; no ROM, savestate, archive, or generated
  resource was included.  Broad commit `3c88f54516bb04700ce353fb51e1d4f8c0627e6e`
  remains outside the review branch.

- Paused 2026-09-04 during the source-backed compressor -> hoist continuation.
  The full room-42 local closure (LSCR 200--213) is now cooked.  Real
  `(8,492,0)` starts LSCR 201 (the compressor animation loop) and leaves it
  live; the correct hoist sentence is `(8,500,497)`, not `(8,500,491)`.
  Object 500 verb 8 starts object 497 verb 8, which starts LSCR 207; LSCR 207
  then consumes the running-compressor condition and performs the authored
  hoist cutscene.  It includes persistent `setState(500,0)`, bit 444, and
  subsequent room-82/room-75 branches guarded by source bits.
- Historical note superseded: fixture builds no longer auto-clear or
  acknowledge message completion at C23 delivery.  Headless mode separates
  presentation absence from logical message lifetime; authored
  `waitForMessage` owns the normal delay/continuation/clear sequence.  The
  production Talk_Begin path is unchanged.  The earlier ROM with the now
  superseded shortcut was:
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

- Review branch published from the verified base: repository
  `astrobleem/SNES-SAME-SCUMM`, branch `review/hoist-message-lifetime`, commit
  `e2b1a44f988123368bc29fc97b48b991f68397b5`; remote HEAD was verified equal.
- Message-lifetime correction: fixture C23 no longer clears talk state or
  skips `Talk_Begin`; it uses the logical talk frame lifecycle. A generic
  headless long-text path now handles encoded messages filling the 32-byte
  presentation buffer by retaining logical length/delay without claiming
  presentation bytes. Focused host suite: 117 tests pass.
- Latest corrected ROM:
  `build/same-startup42-hoist-room82-talklifecycle4.sfc`, SHA-256
  `c8917d0dcfe6ddbf2be17ab2c2aa19c24928e62fe2370a2c9e1019686d14dcac`;
  audit PASS, bank-0 end `$F551`, 2670 bytes free. The matching startup
  checkpoint reaches room 42/error 0 at frame 1106.
- Compressor sentence `(8,492,0)` was published and consumed from the
  matching checkpoint; object 492 state became 1 and error remained 0. The
  prior sentence script report recorded 68 fetches but remained live at PC 0;
  that count was not reset per launch and was therefore not instance evidence.
  Current diagnostic build adds a generic C4 byte-index-width reassertion at
  every scheduler slot scan: after a prior slot's word-indexed PC load, X's
  high byte can no longer skew the next byte-indexed status/didexec/freeze
  lookup. This is the current compressor-launch fix under validation.

### Current compressor scheduler pass (2026-09-04)

- Rebuilt `build/same-startup42-hoist-debug2.sfc` from ATLANTIS.zip with the
  startup42 full-cone flags. SHA-256:
  `5610fd06cb739f401cb86083fa687da3696eca88a8a16367f6417ca1cd97317d`.
  Bank-0 end `$F706`, 2233 bytes free; ROM audit PASS.
- Generic fix: `ScummV5_C4_Scheduler_Frame__slot_in_range` now executes
  `SEP #$10` / `.i8` before `TAX`; this protects all subsequent byte-table
  slot lookups, not just sentence script 2.
- Focused host suite: 118 tests PASS; `git diff --check` PASS.
- The Nexen bridge is available at `/home/chad/Nexen/bin/linux-x64/Release/linux-x64/publish/Nexen`,
  but the attempted focused run did not produce a report because the bridge
  process terminated with loopback/transport error (`Operation not permitted`;
  Nexen exited code -6). Runtime execution therefore remains to be rerun with
  a functioning bridge; no hoist completion is claimed from this build.
- Diagnostic reservation `$7E57A4` is now named
  `SAME_SCUMM_SCENARIO_SCHED_SCAN_GATE` in `memory.pasm`; no prior symbol or
  reservation uses that byte. Do not treat its last value as execution proof.

### Hoist continuation (2026-09-05)

- Same-ROM startup42 build `build/same-startup42-hoist-debug18.sfc` uses
  `ATLANTIS.zip`, M24RB, M23A/B/C, M23C sound-control, M25 movement,
  scenario fixture, and startup42 validator flags. SHA-256:
  `7f7f849fa7afa800f0e97559a97b1c65af17f18a5e60784e0345d6fe53d31692`.
- Generic C25 fix: queue record offset is captured from the queue count before
  payload/fixture diagnostics; dispatch consumes normalized `LAST_WORDS`.
  This prevents multi-command room-82 batches from aliasing records.
- Authored room-82 C25 batch now runs error-free through `$0107`, `$010E`,
  `$010F`, `$010F`, `$0110`; focused run reaches room 82 with error 0 and
  LSCR 207 still active at PC `$01EB` (expected continuation requires further
  bounded observation/semantic tracing).
- New fixture-only C25 diagnostics: dispatch `$7E5F80`, queue dump via
  validator `$7FD45A`; validator reports `c25_dispatch`, `c25_queue_raw`.
- Latest frontier: room 82, program 230/LSCR 207, slot 6, PC `$01EB`,
  error 0. Do not claim hoist completion until setState/bit-444/cutscene and
  selected downstream room behavior are observed.
- The room-82 batch was confirmed from the live queue as five records:
  `$0107(009D,1,4,0190)`, `$010E(009D,1)`, `$010F(0106,009D,0)`,
  `$010F(FFFF)`, `$0110`. A 10,000-frame run remains in room 82 with error 0;
  LSCR 207 is a persistent running slot at saved PC `$01EB` after the room
  transition. This is execution evidence for clean C25 consumption, not yet
  proof of every downstream hoist effect.
- Focused host SCUMM suite after C25 queue/dispatch changes: 120 tests PASS;
  `git diff --check` PASS. Latest ROM remains
  `build/same-startup42-hoist-debug18.sfc` (`7f7f849fa7afa800f0e97559a97b1c65af17f18a5e60784e0345d6fe53d31692`).

### Hoist continuation after room-owner persistence (2026-09-05)

- Fixture-only message auto-clear was removed from `$AE` wait-for-message:
  headless mode now removes presentation ownership only; logical talk/message
  lifetime remains active and releases through normal Talk state.
- The attempted direct post-RunSelected slot save was rejected by runtime
  evidence: it regressed startup into room 49/room 0. It was removed. Current
  generic persistence is at the common successful opcode boundary, with an
  identity-checked room-owner pre-rehydrate save under investigation.
- `build/same-startup42-hoist-debug25.sfc` rebuilt from ATLANTIS.zip with the
  same startup42 flags; SHA-256:
  `9f7e0699eb2c10ee3dd0edda735c19e2e4b6512e323805bcd3747a30bb42667b`.
  Audit PASS; bank-0 end `$F9B4`, 1547 bytes free.
- Bounded run reaches room 82 and advances beyond the prior C25 stall. The
  next ordinary runtime failure is `SCUMM_ERR_UNKNOWN` while program 250
  (room-82 ENCD) executes opcode `$DD` (`ifClassOfIs`) around source PC
  `$005B`/observed post-fetch PC `$0061`; C25 trigger dispatch now reaches its
  diagnostic path. This is not yet hoist completion.
- Focused host suite: 120 tests PASS; `git diff --check` PASS. Matching run:
  `build/startup42-hoist-debug25-run1200/report.json`.
- Next: decode the room-82 `$DD` operands and fix its generic dispatch/error
  path; then continue LSCR 207 and observe setState(500,0), bit 444, cutscene
  completion, and the selected room branch. Preserve exact ROM/report pairs.

### Hoist continuation after C25/message fixes (2026-09-05)

- Debug28 exposed a fixture diagnostic accumulator clobber: after the bytewise
  `$0107` probe, `LAST_WORDS` was reloaded without executing `REP #$20`.
  Debug29 added the real width transition. Debug31 added a packed-byte fallback
  for `$0110` queue-clear recognition; both are generic fixture-safe C25
  handling, not Fate-specific command forcing.
- Debug32/33/34/35/36 isolated the next ordinary issue to headless encoded talk:
  the compact 32-byte presentation path must retain logical length/control
  consumption. Debug33 fixed `RAW_INDEX` advancement beyond the presentation
  window; debug37 additionally accepts canonical system-speaker actor `$FF`
  without creating an actor presentation owner. Fixture message ownership and
  wait lifetime remain logical; no auto-clear was restored.
- Exact latest ROM: `build/same-startup42-hoist-debug37.sfc`, SHA-256
  `75ce5647cad61948b028ae980a9bc08953883273994a43922cf64d388613a03f`.
  Build uses `ATLANTIS.zip`, M24RB/M23A/B/C, M23C sound control, M25 movement,
  startup42 validator, scenario fixture, class overlay `491:0x2f`, and the
  prebuilt Fate M21 TAD/music profile. Poppy `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`.
- Historical debug37 run: `build/startup42-hoist-debug37-run2500/report.json`.
  Its earlier PC-822 observation was superseded by the debug38 effect run and
  the 10,000-frame room-82 observation below.
- The room-82 long system message now decodes without `SCUMM_ERR_STRING`; its
  actor `$FF` is the canonical system/status-line speaker. The validator's
  `exit=1` is its non-success semantic predicate, not a CPU reset; final room
  is room 82, error 0.
- Historical next-step note superseded by the debug38 entries below; the
  message lifetime, LSCR-207 effects, and authored room-82 entry are now
  observed.

### Room-82 extended observation (2026-09-05)

- Matching ROM `75ce5647cad61948b028ae980a9bc08953883273994a43922cf64d388613a03f`
  ran for 10,000 safe frames with startup42 compressor/hoist inputs. Report:
  `build/startup42-hoist-debug38-run10000/report.json`.
- No reset, timeout, or SCUMM error occurred. Room 82 remained installed
  through frame 10002; room-82 ENCD completed, LSCR 207 retired, and authored
  delayed/persistent scripts settled to LSCR 75 (delayed) and LSCR 208
  (running). C20 was empty and talk state inactive.
- Final observed state: actor 1 room 82 at `(345,0)`, idle, costume 2,
  walkbox `255`; actor 2 at `(263,109)`, idle, costume 28. Cutscene depth and
  error were zero. This is downstream execution evidence, not a claim that a
  room-82 playable object action has been proven.
- Room 82 cooked source contains objects 1096--1102, each named `cave`, with
  authored verbs 9, 10, and 90. Their OBCD programs are the shared generic
  descriptive/walk/use family; static inspection found no durable transition.
  Do not inject an arbitrary sentence until a source-valid room-82 input
  boundary is identified.

### Current hoist continuation (2026-09-05)

- Debug45 was superseded by debug46 after two generic integration fixes: room-82 local
  scripts 200--205 are executable identities, and the cooker reserves 32
  dynamic class records instead of consuming the entire initial class table.
  ROM SHA-256: `56b8fd32a6230bf465aa42b6728b5a0f820fd31c578e99e2836f0349fc225aad`.
- The same startup42 compressor/hoist run now installs room 82 and executes
  local LSCR 201/204/208. Its first remaining failure is opcode `$3B`
  `getActorScale` at LSCR 201 PC `$0038` (runtime PC `$0039`), after authored
  `putActor`, `animateActor`, `breakHere`, `getActorX/Y`. This is an ordinary
  missing generic v5 opcode, not a resource or reset conclusion.
- Implemented locally: host and SNES generic
  `$3B/$BB getActorScale`, flagged actor-byte decoding, result-variable write,
  and horizontal actor scale return. Focused regression and matching
  compressor→hoist rerun are recorded below.

### Room-82 getActorScale continuation (2026-09-05)

- The implementation is now built and validated in
  `build/same-startup42-hoist-debug46.sfc`, SHA-256
  `1a618f6fd12f58f1840a91270bc3d56efe892d1e834dc4a53060f04d1c539f12`.
- Root cause was a host handler-registration collision: `$3B/$BB` had been
  registered as `waitForActor`, although canonical v5 reserves that family for
  `getActorScale`; `$AE` remains the wait-for-actor opcode. The generic host
  registration and SNES dispatch now agree, including direct/variable actor
  byte operands and result-variable writes. Focused host suite: 123 tests PASS.
- Matching validator run: `build/startup42-hoist-debug46-run/report.json`,
  1800 safe frames. It reaches room 82, executes local LSCR 201/204/208 with
  error 0, observes the authored room-82 excursion/return, and ends in room 42
  with error 0. The former room-82 `$3B` opcode failure is gone. Current final
  state has room 42, actor 1 `(377,87)` idle, cutscene depth 0, C20 empty;
  room-82 local LSCR 207 retired during the observed excursion. A longer
  10,000-frame observation was started but intentionally interrupted after
  repeated stable room-42 looping; it produced no new error evidence.
- Screened review evidence is published on `review/hoist-message-lifetime` at
  `astrobleem/SNES-SAME-SCUMM`, commit
  `7d92ac4073b2454fa205bbaa4aec34f4c6d6db62`; remote HEAD was fetched and
  matched. It contains only review markdown and no ROM, save state, archive,
  cooked resource, or broad implementation payload.

### Dispatch-family regression audit (2026-09-05)

- Debug47 corrected the SNES matcher to compare `$3B/$BB` exactly before
  applying the low-six-bit mask used by the `$11/$51/$91/$D1` animate family;
  this prevents `$7B/$FB getActorWalkBox` from being misrouted to
  `getActorScale`.
- Debug47 ROM SHA-256:
  `f241e0239f4bec1ac3826c5dbd7416c02db842ddfbcf102cc0e67462d1e14d67`.
  Build/audit passed, bank-0 end `$FA1C` with 1443 bytes free.
- Focused startup42 run (`build/startup42-hoist-debug47-run/report.json`,
  1800 safe frames) again reaches room 82, executes LSCR 207 and the local
  scripts, returns through the authored room-42 path, and finishes with
  `error=0`, C20 empty, and cutscene depth zero. The room-82 transition and
  return remain reproducible after the family-dispatch correction.

### Hoist/message continuation pass (2026-09-05)

- Current startup42 build `build/same-startup42-hoist-debug53.sfc` is an
  observationally equivalent continuation build. SHA-256:
  `9eab9a4847f78db12db0882ce5963dea54e7859f5573804ca6c65dc35eacb681`.
  Focused 1800-frame run `build/startup42-hoist-debug53-run/report.json`
  passes build/audit and reaches room 82, observes object 500 state `1->0`,
  bit-444 writes, the authored room-82 excursion/return, and ends room 42
  with error 0. This is the current hoist execution evidence.
- The message validator now defaults to the generated MAXS variable table at
  `$7E0800` (the map, not the old `$7FF500` assumption), and large diagnostic
  snapshots are taken only on lifecycle changes. A target run against the
  message fixture proves `var10=1` is written, but does not yet reach the
  canonical delayed completion boundary: C23 remains active with delay 52--56
  while the standalone scheduler stops/holds. This remains an unresolved
  focused target scheduler/message-service defect; no fixture-only auto-clear
  was restored.
- Message fixture revisions are intentionally limited to fixture source: the
  temporary nested sentinel was removed; the current case is a single-owner
  talk -> `waitForMessage` -> `move(var10,1)` program. Latest fixture ROM is
  `build/same-message-debug56.sfc`, SHA-256
  `3733503ac96ca31fdeeffc00bb80de5ea206b1fe7e72a281150c79c57e9d4046`.
- Focused host suite remains 123 tests PASS; ROM build/audit and startup42
  hoist run pass. Do not claim target message-lifetime regression complete
  until delayed C23 completion and wait release are observed.

### Current continuation checkpoint (2026-09-05)

- Latest startup42 ROM after the generic wait-state publication change:
  `build/same-startup42-hoist-debug57.sfc`, SHA-256
  `9b860ba27f540b51a506796183be15c5e46f530832e8c81c9d2534fd65507b67`.
  Effective profile remains M24RB/M23A/M23B/M23C/M25 movement + scenario
  fixture, ATLANTIS full corpus, prebuilt Fate TAD music. Build/audit pass;
  bank-0 end `$FA1C`, 1443 bytes free.
- `build/startup42-hoist-debug57-run/report.json` reproduces the authored
  startup42 -> room1 -> room42 -> room82 excursion/return. At frame 1802:
  room42, actor1 `(157,101)` walkbox7 idle, actor2 `(184,101)` idle,
  C20 empty, cutscene depth0, error0. Object500 state `1->0`, object488
  state1 and bit-444 writes are observed. LSCR207 and related room scripts
  execute; no reset/error.
- Target message fixture uses the generated MAXS variable base `$7E0800`.
  The current single-owner target run against `build/same-message-debug56.sfc`
  observes `VAR_HAVE_MSG=1` and `var10=1`, but the ROM does not yet reach the
  delayed C23 completion boundary before the fixture script retires/stalls.
  `waitForMessage` now consults authoritative `TALK_ACTIVE` before the
  compatibility mirror, and no fixture-only auto-clear exists. This remains
  an open focused scheduler/message-service issue, not accepted evidence.
- Focused host validation: 123 tests PASS; `git diff --check` PASS. The
  screened review branch is remotely verified at
  `astrobleem/SNES-SAME-SCUMM:review/hoist-message-lifetime`, commit
  `b2dbaf171d341873deaf5150b0d6540b27082f`, with the updated execution claim.

### Continuation audit: matching hoist control ROM (2026-09-05)

- The exact ROM used for the last accepted compressor/hoist behavior is
  `build/same-startup42-hoist-debug38.sfc`, SHA-256
  `75ce5647cad61948b028ae980a9bc08953883273994a43922cf64d388613a03f`.
- A fresh current-validator control run against that ROM,
  `build/startup42-hoist-debug38-continuation/report.json`, reached room 82
  through frame 3002 with error 0. It observed both sentence submissions,
  compressor/hoist lifecycle, bit-444 writes, and stable room-82 execution.
  Final actor state was `(345,0)`, walkbox `255`, idle; cutscene depth was 0;
  C20 was empty; active scripts were delayed LSCR 75 and LSCR 208.
- Current-source debug84 was startup-safe but left the first sentence slot at
  PC 0 without a subsequent C4 pass. The attempted common `$AE` scheduler
  rewind reproduced room-0/bootstrap behavior and has been removed. The
  direct cold-wait slot write/marker has also been removed. Do not treat
  debug84/debug86 as accepted hoist ROMs.
- Current focused message evidence remains
  `build/m25a-validator/message/message-wait-debug80.json` against
  `build/same-message-debug80.sfc`, SHA-256
  `0508472287ba26094af1a35b4b8c0e967419a8a3acb934e1ac4fe6e75cfe5799`:
  yielded slot PC 9 retains logical C23 ownership, completion occurs at
  logical frame 15, the publish clear occurs on the following boundary, and
  the continuation writes `var10=1`. No fixture-only message auto-clear is
  present.
- Immediate next work: compare the current-source first sentence handoff
  against debug38 at the completed-frame boundary, using host-side trace only;
  identify the common scheduler/return-state discrepancy without retaining a
  global `$AE` postamble or changing production room/SCUMM semantics.

### Current compressor/hoist continuation (2026-09-05)

- Generic fixture ABI fix: `ScummV5_Scenario_Fixture_EnsureActor2Room42_Far`
  now clears carry before `RTL`; its room-42 equality test no longer leaks
  carry into the caller's SCUMM success branch. The same-ROM startup42 run
  crossed sentence launch and completed without error.
- Generic wait fix: active `$AE 02` rewinds the complete two-byte polling
  instruction before yielding. A yielded message waiter cannot run its
  continuation before C23 publishes logical completion.
- Target execution proof: `build/same-message-long-v3.sfc`, SHA-256
  `bb6eabbd834d129345f475e2bc02fa05435461a5c5775a50503eed18aae408ac`.
  `build/m25a-validator/message-long/message-wait-v3.json` passes: 51
  logical bytes, `FF 03` at position 36 beyond the 32-byte presentation
  window, delayed wait held at PC 58, completion at logical tick 64, then
  normal continuation with error 0. Control metadata is a bounded logical
  witness, not a second presentation buffer.
- Same-ROM hoist evidence: `build/same-startup42-hoist-debug89.sfc`, SHA-256
  `54142e89acbdbaae89feac1b002257207e6aec03cad4e9d2c0c5692225a00a20`;
  report `build/startup42-debug89-compressor-hoist/report.json`. Compressor
  sentence consumed; object 500 changed to state 0; bit-444 packed-byte write
  observed; LSCR 207 cutscene balanced; authored room 82 installed and its
  local scripts executed before the authored return to room 42, all error 0.
- Current focused target message fixture status: short and long logical
  lifetime tests are covered; host suite is 124 tests. The long target proof
  is current; no fixture-only talk auto-clear is present.

### Current debug91 continuation (2026-09-05)

- Corrected the focused source regression test to assert the established far
  message-wait polling boundary in `scumm_v5_matrix_far.pasm`; the main opcode
  source remains free of the removed duplicate rewind. Host suite:
  `PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q` — 124/124.
- Same-ROM run:
  `build/same-startup42-hoist-debug91.sfc`, SHA-256
  `b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`.
  Command uses ATLANTIS.zip, M24RB/M23A/M23B/M23C/M25 movement, M25A
  startup42 fixture, scenario actor state, and prebuilt Fate TAD. Run output
  is `build/startup42-debug91-hoist4/report.json`.
- The run consumed both sentences (`sentence_sent=true`, `sentence2_sent=true`)
  with `error=0`; object 492 is state 1 and object 500 is state 0. Its trace
  reaches the authored room-82 excursion and returns to room 42. The final
  slot snapshot is a later scheduler observation, not evidence that the
  transient sentence program failed to execute.
- The long target message proof remains paired with
  `build/same-message-long-v3.sfc` SHA
  `bb6eabbd834d129345f475e2bc02fa05435461a5c5775a50503eed18aae408ac` and
  `build/m25a-validator/message-long/message-wait-v3.json`: logical length
  51, control at position 36, wait held at PC 58, continuation at PC 66,
  completion tick 64, error 0.

### Screened review update (2026-09-05)

- Isolated review worktree `/home/chad/SAME-review-hoist` published the
  source-only focused handoff on
  `astrobleem/SNES-SAME-SCUMM:review/hoist-message-lifetime` at commit
  `4622121c536bb722793007ba6cf7dff0ea42558c`; `git ls-remote` verified the
  remote HEAD matches. The branch contains only review text and no ROM,
  savestate, archive, or generated game resource.
- Review file: `review_message_scheduler_20260905.md`. It records the
  corrected logical-message contract, the 124-test result, long-message
  target evidence, and same-ROM compressor/hoist continuation evidence.
- Main worktree remains intentionally dirty with campaign changes and
  unrelated local artifacts; no reset, clean, stash, or broad commit was
  performed.

### Hoist continuation completed (2026-09-05)

- Extended exact-ROM debug91 run to 3000 frames with bounded observation:
  `build/startup42-debug91-hoist5/report.json`.
- ROM SHA-256:
  `b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`.
- Both semantic sentences consumed; object 492 is state 1 and object 500 is
  state 0; error remains 0. The trace enters room 82, executes its authored
  local scripts, and returns to room 42. At frame 3002, cutscene depth is 0,
  C20 is empty, and the remaining active scripts are authored delayed/live
  room-42 scripts 208, 75, 201, 204, and 203.
- Final observed actor1 snapshot is `(380,87)`, idle, authored room identity
  82 (the runtime's room-42 return snapshot retains the downstream actor
  identity); actor2 is `(160,112)` in room 42. Audio/M24RB diagnostics remain
  profile-owned (`state=0`, `trigger_marker=1`, `deferred_count=1`) and are
  not claimed as an independent driver transition.
- Review branch now includes screened focused-diff index commit
  `534f3e08759c3ee32d3ff09ab36b641f3b956404`, remotely verified on
  `review/hoist-message-lifetime`. Main worktree remains dirty by design.

### Repository validation cleanup (2026-09-05)

- Updated stale conformance fixtures to the accepted canonical `$3B` query
  operand layout and modern structural startScript-source assertion. These
  are test-only corrections; production movement and scheduler behavior were
  unchanged.
- Full repository suite now passes:
  `PYTHONPATH=src python3 -m unittest discover -s tests -q` — 477 tests.
- Focused suite remains 124/124. `git diff --check` remains clean.

### Post-hoist cone audit (2026-09-05)

- The exact room-82 resource contains objects 1096--1102, each with only
  source verbs 9 (look), 10 (walk), and 90 (name/auxiliary). No room-82 OBCD
  handler is an effect-bearing progression edge; the meaningful downstream
  work in this cone is the authored room-82 local-script lifecycle and its
  return to room 42, already observed by `startup42-debug91-hoist5`.
- No additional room-82 sentence is being injected. The next expansion must
  use a source-backed room-42/global input or a separately justified full-game
  scenario root rather than arbitrary descriptive probing.

### Current same-ROM continuation (2026-09-05)

- Replayed the compressor prerequisite and hoist on the unchanged ROM
  `build/same-startup42-hoist-debug91.sfc` (SHA-256
  `b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`).
- Command used:
  `PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-startup42-hoist-debug91.sfc --output build/startup42-debug91-hoist-retire --frames 2400 --light --minimal-observation --sentence 8 492 0 --sentence2 8 500 497 --sentence2-after-script-retired 2 --port 45496 --pre-event-trace-start 99999`.
- Both production mailbox sentences were consumed with `error=0`. The
  compressor sentence reached its authored state-1 condition; the second
  sentence was submitted only after global script 2 retired. The run entered
  room 82, executed local scripts 201/203/204/207, and returned to room 42.
- Observed hoist result: object 492 remained state 1, object 500 changed to
  state 0, bit 444 was written, cutscene depth returned to zero, C20 emptied,
  and no SCUMM error occurred. Room-82 execution was observed, not merely
  inferred from static resources.
- At frame 2402 the runtime was continuing authored room-42/room-82 delayed
  script activity; actor 1 was idle at `(382,87)` with downstream room
  identity 82. This is continuation evidence, not a new room-82 gameplay
  claim.
- Exploratory suit branch on separate ROM
  `build/same-startup42-suit-next.sfc` (SHA-256
  `5a314709b57078bde92926336b944bd877d10cc5a5f5040e5fd693f674a49d91`)
  consumed `(8,491,0)`, walked actor 1 to `(218,104)`/walkbox 10, ran the
  generated object program and nested script 14, and completed error-free;
  no additional object-state mutation was observed.
- Validation: focused SCUMM suite 124/124; full repository unittest suite
  previously 477/477. No production source was changed for this continuation.

### Hoist evidence instrumentation (2026-09-05)

- `validate_scumm_startup42_nexen.py` now records `sentence2_frame` and the
  complete observational `sentence2_pre_state`; this is validator-only and
  does not alter mailbox publication or production execution.
- On the unchanged debug91 ROM, the compressor sentence published at frame
  960 and the hoist sentence published at frame 1002 after the first sentence
  script had retired. The pre-publication snapshot was room 42, phase 0,
  error 0, idle actor in walkbox 7, empty C20, with authored delayed scripts
  75 and 208 still live. The subsequent trace entered room 82 and remained
  error-free; the 1400-frame capture ended during room-82 phase-4 teardown,
  while the earlier 2400/3000-frame same-ROM captures prove the return to
  room 42.
- Validation after this validator-only change: `python3 -m py_compile
  tools/validate_scumm_startup42_nexen.py`, focused SCUMM 124/124, and
  `git diff --check` all pass.

### Post-hoist door probe (2026-09-05)

- From the same source-backed compressor-on scenario ROM
  `build/same-startup42-compressor-off.sfc` (SHA-256
  `dc0f923bb8569667ac58a37b69ea5f4995463111a07ad6111053af3c91633eee`),
  submitted `(3,489,0)` through the production mailbox after startup42.
- Run: `build/startup42-door-after-hoist/report.json`; the sentence was
  consumed and script 2/its generated object path executed with `error=0`.
  Actor 1 moved authentically from the startup position to `(157,101)` in
  room 42, walkbox 8, then became idle. Object 489 remained state 0 and no
  room transition or additional persistent mutation occurred, so this is an
  exploratory movement/no-op result, not a progression claim.
- The accepted compressor/hoist result remains separately evidenced by the
  same-ROM inverse-hoist run and the debug91 2400/3000-frame runs.

### Post-hoist follow-up probes (2026-09-05)

- `(4,489,0)` was also submitted through the production mailbox on the same
  `dc0f923b...33eee` ROM. It consumed and completed error-free, moving actor 1
  to `(157,101)`/walkbox 8; object 489 stayed state 0 and no room transition
  occurred. Together with `(3,489,0)`, the room-42 door is a source-authored
  no-op under this state, not a missing runtime effect.
- `(11,500,0)` was submitted after the post-hoist state on the same ROM. It
  consumed and completed error-free with object 500 still state 0, no new
  script/resource transition, and no room change. These follow-ups are
  exploratory evidence only; the accepted authored progression remains the
  compressor/hoist excursion through room 82.
- Validation after these probes: focused SCUMM engine suite 124/124, ROM
  audit PASS, and `git diff --check` PASS.

### Repaired-suit pickup/state continuation (2026-09-05)

- On `build/same-startup42-excd-suit-rigged.sfc` (SHA-256
  `96b3a3af540e8170c41f004f2930fb74f700cd43b45f35dd045438238e7ee867`), the
  production sentence `(11,491,0)` was consumed after the source-backed EXCD
  bundle/class mask. Actor 1 moved to `(218,104)`/walkbox 10 and object 491
  changed state `0 -> 1`; nested child execution completed with `error=0`.
- Continuous follow-up run:
  `build/startup42-suit-pickup-use-chain/report.json`. Both `(11,491,0)` and
  `(8,491,0)` were consumed. The first mutation persisted; the downstream
  suit-use branch completed at the authored suit point with object 491 state 1,
  no owner/room transition, empty C20, cutscene depth 0, and error 0. This
  proves the previously blocked movement-dependent suit state effect without
  changing production movement.

### Suit-hose continuation (2026-09-05)

- On `build/same-startup42-excd-suit-rigged.sfc` (SHA-256
  `96b3a3af540e8170c41f004f2930fb74f700cd43b45f35dd045438238e7ee867`), the
  continuous run `build/startup42-suit-hose-chain/report.json` submitted
  `(11,491,0)` followed by `(8,491,1014)` after state 491 became 1.
- Both sentences were consumed and completed with `error=0`; actor 1 reached
  `(218,104)`/walkbox 10, object 491 remained state 1, no owner mutation or
  room transition occurred, C20 was empty, and cutscene depth was 0. This is
  the source-backed downstream suit/hose probe; no additional effect is
  claimed where the authored predicates produce none.

### Repaired-suit locker consumer (2026-09-05)

- On `build/same-startup42-excd-suit-rigged.sfc` (SHA-256
  `96b3a3af540e8170c41f004f2930fb74f700cd43b45f35dd045438238e7ee867`), the
  source-backed repaired-suit state enabled `(3,490,0)`. Continuous run:
  `build/startup42-rigged-locker-consumer/report.json`.
- The production path moved actor 1 to `(218,104)`/walkbox 10 and changed
  object 490 state `0 -> 1`; `(9,490,0)` then consumed that state through its
  authored consumer. Final room 42 state retained objects 490 and 491 at
  state 1, with no owner/room mutation, empty C20, cutscene depth 0, and
  `error=0`. This is the current strongest coupled room-42 state chain.

### Locker/suit combination check (2026-09-05)

- Exploratory `(3,490,491)` on the repaired-suit fixture was consumed through
  the production sentence path and completed with `error=0`, but object 490
  and 491 remained state 1, ownership was unchanged, and no room transition or
  follow-on script effect occurred. The tuple is not treated as a progression
  edge for this scenario state.

### Hoist/suit combination check (2026-09-05)

- Exploratory `(8,500,491)` on the repaired-suit fixture completed through the
  production sentence path with `error=0`, but produced no new mutation,
  ownership change, or room transition. The source-backed durable state stayed
  `490=1`, `491=1`, `492=1`; this combination is not an additional progression
  edge under the current authored predicates.

### Next full-game expansion candidate (2026-09-05)

- Full ATLANTIS resource inspection found direct authored room-55 edges in
  `script.1`: `$72 37` occurs at offsets `$2E4D`, `$2E7E`, `$2EAF`, `$2EE5`,
  `$2F1B`, `$2F51`, and `$2F87`. The surrounding code initializes the authored
  selection variables and branches before each load; these are source-backed
  global-script paths, not validator room requests.
- Room 55 is therefore the next expansion candidate after the completed
  room-42/82 cone. Its full source resource is available in `ATLANTIS.zip`
  (117711 bytes, 64 walkboxes, 66 objects, ENCD/EXCD, and local scripts
  200--218). No room-55 execution or scenario-root state has been claimed yet.

### Room-55 cone inspection (2026-09-05)

- Generalized `tools/trace_fate_room42_graph.py` to accept repeated `--room`
  and `--object` selectors; it now reports source logical room dimensions,
  walkbox count, ENCD/EXCD sizes, local-script IDs, OBCD geometry/verb tables,
  and candidate global-script references without changing production code.
- `ATLANTIS.zip` resolves logical room 55 to a 960x200 scene with 64 walkboxes,
  66 OBCD records, ENCD 1184 bytes, EXCD 131 bytes, and LSCR 200--218. The
  OBCD records are primarily authored walk/name handlers (`10`, `41`) plus
  presentation-only scenery; no room-55 state-changing OBCD was inferred.
- Its meaningful coverage is the authored script-1 incoming/room-entry and
  local dialogue/control cone. Direct `$72 37` branches remain at script.1
  offsets `$2E4D`, `$2E7E`, `$2EAF`, `$2EE5`, `$2F1B`, `$2F51`, `$2F87`.
- Static graph artifact: `build/fate-room55-summary.txt`; object summary:
  `build/room55-objects.txt`. These are local generated evidence, not source
  resources. Next action is to decode the script-1 selector predicates and
  build a controlled source-backed room-55 entry fixture before execution.

### Room-55 cooker boundary (2026-09-05)

- A separate `room55` scenario profile was added to the existing fixture/build
  plumbing. It selects scenario start room 55, uses the full `ATLANTIS.zip`
  source archive, and cooks room 55 through the normal room-install path; it
  does not alter the accepted startup42 profile.
- Initial room-55 executable closure was intentionally reduced to ENCD/EXCD
  (the room's OBCD records are primarily walk/name handlers); local scripts
  will be added only from an observed entry dependency. The generated source
  room record is `build/m25a-validator/room55/room42/manifest.json`, including
  room-55 payload SHA `321610e001c4b05f6a74641862a9886b10f22e1983e95c54957554926418d6ea`.
- Build command used:
  `SAME_FATE_DEMO_ARCHIVE=$PWD/ATLANTIS.zip SAME_BUILD_M24RB=1
  SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1
  SAME_BUILD_SCUMM_M25A_VALIDATOR=1 SAME_BUILD_SCUMM_SCENARIO_FIXTURE=1
  SAME_BUILD_SCUMM_M25_MOVEMENT=1 SAME_M25A_VALIDATOR_CASE=room55
  SAME_TAD_PREBUILT_DIR=$PWD/build/profile-music/fate-m21-final bash tools/build_snes.sh`
- The target cooker rejects the authentic source geometry before ROM assembly:
  `RuntimeError: room 55 has 64 walkboxes; SNES putActor placement capacity is
  32`. This is the first real room-55 blocker. Supporting this source room
  requires an explicit walkbox-capacity/actor-placement architecture decision;
  no coordinate reduction or fabricated geometry is permitted.
- `room55` fixture plumbing is therefore source-backed and build-proven up to
  the existing capacity gate, but no room-55 runtime execution is claimed.

### Room-55 capacity audit (2026-09-05)

- The limit is architectural, not a removable validation guard. ATLANTIS room
  55 contains 64 source BOXD walkboxes (960x200); the target runtime stores
  only 32 records at `SAME_SCUMM_PUT_ACTOR_BOXES=$7FFB65`, each 18 bytes, and
  indexes them throughout `ScummV5_PutActor_Adjust_Far` and related movement
  code. The following actor walkbox/destination/state tables occupy the fixed
  ranges through `$7FFFB1`.
- Room-55 cooker failure is the explicit source-preservation gate:
  `RuntimeError: room 55 has 64 walkboxes; SNES putActor placement capacity is
  32`. Removing the guard or truncating to 32 would discard authored geometry;
  supporting this room requires relocating/expanding the actor-placement
  tables and auditing every indexed consumer, a hardware/layout architecture
  change. No room-55 execution is claimed until that decision is made.
- Full-source static scan confirms script 1 has authored `loadRoom(55)` calls
  at offsets `$2E4D`, `$2E7E`, `$2EAF`, `$2EE5`, `$2F1B`, `$2F51`, and `$2F87`;
  the direct caller is source-backed, but its target cannot yet be installed
  without the geometry-capacity change above.

### Room-55 ROM-backed geometry refactor (2026-09-05)

- Authorized split: complete immutable BOXD geometry stays in generated LoROM;
  mutable matrix flags stay in RAM; placement uses one bounded working record.
- `$7FFB65` is now `SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK`, one 18-byte record.
  Existing walkbox/destination/redraw/last-valid/scale arrays retain their
  offsets through `$7FFFB1`; no unrelated state is borrowed.
- `SAME_SCUMM_MATRIX_BOX_FLAGS=$7FFA41` remains the mutable u8 flag table
  (255 bytes), with count at `$7FFA40`. Geometry is immutable ROM; accessor
  working data is temporary and must not be retained across nested calls.
- `ScummV5_PutActor_LoadGeometry_Far` is the single generated accessor. It
  validates active record/index and fetches all nine words; placement scale and
  interpolation now use it for every box index. No low/high split exists.
- Generator accepts 33--255 boxes and retains all records; only counts above
  the u8 index/count contract fail. Room 55 generation currently contains all
  64 geometry records, flags, routes, and portals.
- Room-55 build reached Poppy lint with full generated data and accessor, then
  hit the existing broad M25/M24RB bank-0 configuration overflow/flag mismatch;
  runtime execution is pending restoration of the accepted production profile.
- Focused host suite: 141 tests OK; `git diff --check` and generator
  `py_compile` pass. Room-55 payload SHA:
  `321610e001c4b05f6a74641862a9886b10f22e1983e95c54957554926418d6ea`.

### Room-55 assembled/accessor baseline (2026-09-05)

- Supersedes the earlier cooker-capacity blocker. The authorized split is now
  implemented: immutable BOXD geometry stays source-backed in ROM, mutable
  flags stay in RAM, and `ScummV5_PutActor_LoadGeometry_Far` fetches one full
  18-byte record for every box index through one generic path.
- `$7FFB65` is a bounded working record, not a 32-box image. Box count is u8
  (up to 255); actor/destination runtime arrays are unchanged. Geometry,
  route, portal, object-walk and state tables are emitted in explicit LoROM
  banks so indexed reads do not cross a bank boundary.
- C25's cold/frame-boundary closure is relocated to a far bank for this
  profile. Map: bank-0 `end=$D8DE`, `9953` bytes free before header.
- Fresh ROM: `build/same-room55-c25far.sfc`, SHA-256
  `82892bd71fe9345c27130ad23908b246f259f591395096fb5d614926aa20d667`.
  Poppy SHA-256: `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`.
- Fresh emulator run reaches room 55, phase 0, actor 1 `(399,116)` in
  walkbox 11, idle, cutscene 0, C20 empty, error 0. No room-55 sentence has
  yet been submitted on this ROM. The validator now has generic
  `--expected-room`; room-42 readiness remains unchanged.
- Focused host validation: `PYTHONPATH=src python3 -m unittest
  tests.test_scumm_v5_engine tests.test_scumm_v5_room -q` (143), generator
  and fixture `py_compile`, and `git diff --check` pass.
- Next run must use the exact ROM above with `--expected-room 55` and a
  source-authored room-55 sentence (starting with object 780 / verb 10) to
  measure placement/movement and expose any real high-index geometry defect.
  Do not reuse older savestates.

### Room-55 first runtime execution (2026-09-05)

- The initial room-55 sentence run exposed and fixed a fixture omission: the
  room55 case had not registered source global script 2. It now includes the
  real `_authored_global_script(2)`; no production dispatch was changed.
- Fresh build `build/same-room55-c25far-final.sfc`, effective profile:
  `ATLANTIS.zip`, scumm_v5, M24RB, M23A/B/C, M25A validator, scenario
  fixture, M25 movement, prebuilt `build/m24rb-content`, and the nested
  conformance profile. SHA-256:
  `a788eb6b78c8ed6d11154a7480c5a0526e02e407eddba0fa1e2654c5cba4d518`.
  Map bank-0: `end=$D8E8`, `9943` bytes free before header.
- Fresh room55 run:
  `PYTHONPATH=src python3 tools/validate_scumm_startup42_nexen.py --rom
  build/same-room55-c25far-final.sfc --output build/validate-room55-object780-v3
  --expected-room 55 --frames 420 --light --minimal-observation --sentence
  10 780 0`
  consumed the mailbox, ran global script 2 and its nested source path,
  retired cleanly with room 55, phase 0, C20 empty, cutscene 0 and error 0.
  Actor 1 remained `(399,116)`, walkbox 11, idle: object 780's authored
  handler is a scenery walk/name path and produced no persistent mutation.
  The live room reported `box_count=64` and resolved its authored walk point
  `(640,198)` to box 43; no high-index truncation/error occurred.
- The old startup42 regression invocation was not a valid comparison for this
  room55 profile: its default scenario start room is 49 and it entered the
  unrelated room49 path. It must not be used as room42 evidence for this
  build. Host focused tests remain the authoritative movement regression until
  a correctly configured startup42 ROM is run.
- `tools/build_snes.sh` now accepts `SAME_SCUMM_SCENARIO_START_ROOM`; absent
  that override it selects authored room 68 for startup42 and retains room55
  as 55. This is build/fixture configuration only, not a production room
  special case.

### Room-55 geometry acceptance evidence (2026-09-05)

- The earlier room-55 capacity-blocker paragraphs above are superseded by the
  ROM-backed accessor implementation and evidence in this section.
- Independent ATLANTIS room-55 decode versus cooked `room-55.sc5c` contains 64
  records in both streams. All 64 point/scale records compare equal in source
  ordering; geometry SHA-256 for both is
  `729295d85e84cc33d2414f41d255eb74472bc2b10f61ccebf6d9f443e3b0a8a6`.
  Box 43 resolves distinctly (scale 178), and box 63 remains present.
- Final ROM `build/same-room55-c25far-final.sfc` is
  `a788eb6b78c8ed6d11154a7480c5a0526e02e407eddba0fa1e2654c5cba4d518`;
  bank-0 ends `$D8E8`, leaving 9,943 bytes before the header. The former
  576-byte 32-record RAM image is now one 18-byte temporary record at
  `$7FFB65`, reclaiming 558 RAM bytes; mutable flags/count and
  actor/destination/scale arrays retain their audited RAM locations. The
  geometry refactor itself saves no bank-0 ROM bytes; immutable geometry remains
  in generated ROM/far banks.
- Target command used the final ROM with `--expected-room 55`, 420 frames, and
  sentence `(10,780,0)`. It reached room 55 phase 0/error 0, reported
  `box_count=64`, and resolved object 780's authored `(640,198)` walk point to
  box 43. Object 780 is a scenery/name path, so this proves high-index lookup,
  not a game-authored movement. A copyright-free target multi-leg route through
  a box above 31 remains unproven.
- Validation: focused room/engine suite 144 tests OK; combined validator,
  engine, and room suite 150 tests OK; Python compilation PASS; `git diff
  --check` PASS; ROM audit PASS. The no-sentence target baseline was also run;
  raw cycle counts vary with fixture scheduler activity, so no cache is added.
- Review handoff is being added to the existing isolated
  `review/hoist-message-lifetime` worktree. It intentionally excludes ROMs,
  savestates, ATLANTIS.zip, generated payloads, and unrelated campaign files.

### Room-55 stride correction (2026-09-05)

- Review found and source validation confirmed that the accessor generator had
  four post-save ASLs, computing 34*index instead of the 18-byte record stride.
  The generator now uses three post-save ASLs: 2*index + 16*index. Generated
  assembly was regenerated normally; no hand patch was used.
- Correct witnesses are indices 1/$0012, 31/$022E, 32/$0240, 43/$0306, and
  63/$046E; index 64 fails the room-55 count guard. The rebuilt accepted-room
  ROM is now `build/same-room55-c25far-final.sfc`, SHA-256
  `5a3efe446e36d5f4b77af2209ed4d483dae328ae357686ce92bde51a2ca37ec8`.
- Focused suite is 151 tests OK and ROM audit PASS. The final-ROM target lookup
  still reaches room55 with error 0, box_count 64, and object780 box43.
- Cooker equality and target accessor correctness are separate claims: all 64
  source/cooked records match, but target execution has directly demonstrated
  the valid high-index lookup only. A target all-index accessor harness and a
  copyright-free high-index multi-leg movement fixture remain pending.
- Room-55 acceptance continuation (2026-09-05): current generator and
  emitted accessor use saved `2*index` plus exactly three ASLs = `18*index`;
  no hand-patched assembly/ROM. Witness offsets: 1=`$0012`, 31=`$022E`,
  32=`$0240`, 43=`$0306`, 63=`$046E`; index 64 rejected by `cpx #$0040`.
  Source/cooked decode is 64/64 equal, geometry SHA
  `729295d85e84cc33d2414f41d255eb74472bc2b10f61ccebf6d9f443e3b0a8a6`.
- Target `build/same-room55-accessor-fixed2.sfc` SHA
  `44a9dc0cf25e6bf10ce31ed781a137a55e4b0ae086f79e7b25934119108acedd`
  executed 64 real production `putActor` calls, box_count 64, error 0. An
  observational `--capture-put-actor-sequence` validator mode was added; the
  first frame-granular attempt still collapsed the fixture calls, so returned
  work-record comparison remains open. No production movement change made.
- Added copyright-free `room55-movement` fixture and high-index route-table
  generation. First run was contaminated by fixture startup/resource lifecycle
  noise and is not accepted as movement proof.
- Fresh current startup/hoist ROM `build/same-room55-hoist-current.sfc`, SHA
  `acf3045278fc31d5e11b3ef17993bfb1ef226e8ef7f6dd8094a5e921a991981b`; the
  2200-frame run remained in room 68 and did not consume the hoist sentence,
  so same-source hoist preservation remains open.
- Focused validation: `PYTHONPATH=src python3 -m unittest
  tests.test_scumm_v5_engine tests.test_scumm_v5_room tests.test_m25a_validator
  -q` = 151 pass; Python compilation and `git diff --check` pass. Geometry
  acceptance remains pending target returned-byte comparison, multileg route,
  and hoist rerun.
- Screened review branch `astrobleem/SNES-SAME-SCUMM:review/hoist-message-lifetime`
  is remotely verified at `a36dcf8c7331c40d52dc46e588d2ee01f984d4a5`.
  It contains the corrected review evidence and exact copyright-free fixture
  source only; ROMs, savestates, ATLANTIS.zip, and broad campaign files remain
  local.
- Latest bounded fixture wiring: `room55-movement` is now routed by
  `build_snes.sh` to a room-49 scenario start instead of startup42/title.
  ROM `build/same-room55-movement-fixture2.sfc` SHA
  `f7fc7681d93768a4b9d525968a3d96e0684992816b14cabd1af8acea8bf844a4`.
  Target run is error-free but still does not expose an accepted multileg
  actor trace; the fixture/script handoff remains the next diagnostic target.
## Current bounded room-55 acceptance frontier (2026-09-05)

- Production room-55 accessor is the corrected 18-byte stride implementation;
  source/cooked records compare 64/64.  Current target accessor ROM:
  `67142583180bee350b07b6632b86a66a6800c15aed3ffe9d6d195be7976ed6de`.
- Target fixture witness is `0xA0`: record 0 sentinel matched and index 64 was
  rejected.  The 64 production calls are observed in order; independent
  comparison matches records 1-63 exactly using the latest occurrence per box
  (the first count-0 observation is a pre-yield stale observation, not used as
  evidence for record 0).
- Copyright-free target movement ROM:
  `845abdab907261e26448064861e64d35778a18b4d1a74e8abfa27a8f9feb21aa`.
  Production route: `4,5,9,16,21,25,31,36,41,47,52,57,62,63`; final actor
  `(24,114)`, box 63, moving 0, wait released.  This is the standalone
  movement fixture, not Fate startup.
- Correct RAM accounting: old geometry `$7FFB65-$7FFDA4` (576); new work
  `$7FFB65-$7FFB76` (18); released `$7FFB77-$7FFDA4` (558).  Neighboring
  arrays are not free.  No bank-0 ROM saving.
- Hoist comparison remains open.  Preserved prior passing ROM/report:
  `b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`.
- Fresh current root-49 acceptance ROM
  `b6a9f823d91b67b09e7f0eec3fe343e7fa85e87142646882ff912c609626ef73`
  consumes both sentences, reaches room 82, observes bit 444 and
  `setState(500,0)`, then raises its first ordinary error 12 at room82
  program 245/LSCR 201, PC `$0003`, opcode `$00`; it does not return/settle.
  A fresh build with the current startup configuration diverges earlier in
  the synthetic room-49 root at frame 34, room49 program208 PC `$0006`,
  opcode `$26`, error 2, before either sentence.  Removing the extra cooked
  rooms did not remove that divergence (experiment ROM
  `51fda4577129381fc16abc822dacaa76af100ba7f95053a80ecc05ed78cb7804`).
  The current default startup run likewise remains in room68; this is an
  open configuration/runtime regression, not accepted hoist evidence.
- Current dirty source diff identity for the fresh-build comparisons is
  `e5804665986f094e231d5940fcabf735d1849ff642785da3b7dd7b18a745f863`.
  Current default ROM is
  `0efd55311bfb99659f53a84620df3ad1eb1d138cf9194122d0e7648b495cf763`;
  the room55-case comparison ROM is
  `90046cdd1a3af02afe94c100b7874c26f0769b8fcc31e29d2c2f714af5274a61`.
  Both use ATLANTIS.zip, Poppy
  `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`,
  prebuilt TAD `build/profile-music/fate-m21-final`, and the focused M24RB /
  M23A / M23B / M23C / M25 movement-validator flags. ROM output names were
  isolated; generated intermediate directories remain a build-harness
  isolation limitation and were not acceptance evidence.
- Focused validation already run: `PYTHONPATH=src python3 -m unittest
  tests.test_scumm_v5_engine tests.test_scumm_v5_room tests.test_m25a_validator
  -q` (151 tests), `py_compile` for changed Python tools, and `git diff --check`.
- Screened review branch `astrobleem/SNES-SAME-SCUMM:review/hoist-message-lifetime`
  is remotely verified at `b0c531eece1b4f165e8bc324731a799296bdfa5e`. It
  contains the focused source/test extracts and target evidence, including
  the current hoist-open note, and excludes ROMs, savestates, ATLANTIS.zip,
  and broad campaign files.

## Controller-visible room-42 frontier (2026-09-06)

- The earlier controller visual claim is rejected: `build/controller-room42-`
  `finaltest-clean-run2/` and `visual-repro4/` were inspected and contained
  multicolored static.  The validator had checked file existence/dimensions,
  state readiness, and nonzero presentation counters without inspecting the
  emulator pixels.
- Native backdrop repair is proven separately.  The current presentation
  ROM is `build/controller-room42-visualfix26.sfc`, SHA-256
  `ddd8c1835f83169cbe49483a402e1f189d14b30cd3a1a22e190b09f7a9b00b6e`.
  Build used `tools/build_snes.sh` with the startup42/controller flags recorded
  in the controller validator command; Poppy SHA is
  `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`.
- Native run: `build/controller-room42-visualfix26-run1/`, result pass,
  report ROM SHA matches.  The following emulator screenshots were opened and
  inspected individually: `01-ready.png`, `02-hover.png`,
  `03-walking.png`, `03-opened.png`, `04-dialogue-active.png`,
  `04-dialogue-complete.png`, and `05-post-dialogue.png`.  They show the
  harbor room, source-backed Indy costume, visible cursor/HUD selection,
  walking, locker open state, readable active dialogue, cleared completed
  dialogue, and post-dialogue room/control.  Intermediate surface files are
  not acceptance evidence.
- Native semantic result: room 42; actor reaches `(218,104)`, walkbox 10,
  moving 0; object 490 state `0 -> 1`; inspection dialogue is active with
  `talk_segment_length=16`, `overlay_pixels_nonzero=142`, then talk inactive,
  error 0, and an ordinary post-dialogue RIGHT input advances the cursor.
- Presentation fixes: controller dialogue now retains logical message lifetime
  but hides the committed talk layer on completion; controller text scans the
  bounded encoded prefix for printable glyphs; native capture uses a harbor
  landmark below the letterbox rather than a black corner.  The existing
  indexed-surface compositor now draws the source-cooked actor/object and
  cursor in one backend-owned present transaction.  The cursor helper is
  entered by JSL and returns by RTL; cursor movement invalidates its cached
  render state.  No PPU writes or mailbox/script injection were added.
- Exact replay command:
  `PYTHONPATH=src python3 -u tools/validate_scumm_room42_controller_nexen.py`
  ` --rom build/controller-room42-visualfix26.sfc`
  ` --output build/controller-room42-visualfix26-run1 --port 44441`
  ` --startup-frames 5000` (Mesen/Nexen native execution).
- Focused validation: `PYTHONPATH=src python3 -m unittest
  tests.test_scumm_v5_controller_fixture tests.test_scumm_v5_engine
  tests.test_scumm_v5_room tests.test_m25a_validator -q` = 164 pass;
  Python compilation and `git diff --check` pass.  The carrier-aware command
  `python3 tools/audit_snes_rom.py --carrier sa1_bwram
  build/controller-room42-visualfix26.sfc` passes.
- Visible milestone status: native controller interaction is demonstrated by
  inspected captures for this ROM.  Keep ATLANTIS.zip, ROMs, captures, and
  savestates local; do not stage them into the review branch.
- Screened publication completed from isolated worktree
  `/tmp/same-review-controller`, rooted at fetched published review base
  `55627725d37fe3f161908bf212203dc641cd15d7`.  Remote branch
  `origin/review/controller-room42-native` is verified at commit
  `08cf552546c2547f568710805f949e227c270da8`.  It contains source/test/docs
  only; ROMs, captures, ATLANTIS.zip, savestates, generated payloads, and the
  broad dirty campaign are excluded.  Main `session_checkpoint.md` was then
  updated locally; main remains intentionally dirty.
- Target accessor capture command used one production frame per putActor:
  `PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-room55-accessor-proof-final5.sfc --output build/validate-room55-accessor-proof-final5 --expected-room 49 --frames 700 --light --minimal-observation --capture-put-actor-sequence --port 45784`.
  It produced 64 calls in order: the record-0 target verifier matched the
  sentinel and index64 rejected; independent target observations for records
  1-63 matched all 63 source records.  Witness offsets are 1 `$0012`, 31
  `$022E`, 32 `$0240`, 43 `$0306`, 63 `$046E`.
- Copyright-free movement command used the production route/accessor:
  `PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-room55-movement-acceptance.sfc --output build/validate-room55-movement-acceptance --expected-room 49 --frames 5000 --light --minimal-observation --port 45785`.
  Observed route `4,5,9,16,21,25,31,36,41,47,52,57,62,63`, final
  `(24,114)`, box63, moving0, and wait release.
## Controller presentation boundary cleanup (2026-09-06)

- Goal: keep the accepted native room-42 controller scene while moving all
  PPU/carrier/backend knowledge below the SCUMM engine boundary.
- Accepted behavioral oracle remains
  `build/controller-room42-visualfix26.sfc`, SHA-256
  `ddd8c1835f83169cbe49483a402e1f189d14b30cd3a1a22e190b09f7a9b00b6e`.
  Its inspected native run remains the visual/semantic oracle: harbor, Indy,
  cursor/HUD, walk, locker open, active readable dialogue, clear, control.
- SCUMM engine sources now use neutral `Same_VideoSurface_*` and
  `Same_VideoText_*` seams. Architecture trap coverage rejects engine
  references to PPU registers, BG2/Mode3 names, BW-RAM, and VRAM/CGRAM/OAM/DMA
  implementation symbols. Focused suite: 167 tests pass.
- Backend ownership is retained in video services/backend files. The indexed
  pixel write service is the only SCUMM compositor destination seam; the
  carrier owns its backing. The selected BG2 overlay remains a backend choice.
- Current correctly configured source build:
  `build/controller-room42-arch-clean.sfc`, SHA-256
  `c527550a639bd36b937185e4e21e026b4181b9753f6607700101ff2f8b5bfbf0`.
  It reaches room 42/error 0 but native publication does not accept a present
  (`accepted_present=0`, no rejected presents); it is not visual acceptance.
  A direct-call diagnostic build has the same failure, so this is not yet
  attributed to the neutral SCUMM seam. Diagnostic ROM:
  `build/controller-room42-diag-direct2.sfc`, SHA-256
  `3a165df1449afa0dbc2d27ffd7c0171560aaffc2c6a3a9a0f272b6de2120d8bb`.
- Build command must include `SAME_SCUMM_SCENARIO_START_ROOM=42`; without it
  the validator correctly remains in room 68 and is not startup42 evidence.
- Current gate: preserve source cleanup, identify the pre-existing dirty-source
  delta that prevents a fresh build from matching the accepted oracle, then
  rerun and inspect native captures before claiming completion. Do not use a
  host-rendered image as evidence.
- Review branch remains `origin/review/controller-room42-native`; prior
  verified source-only commit is now
  `9639f1c95cfa6319d4bb7408ba04f7bd746a0389` (remote HEAD matches). It
  contains the neutral engine/service source, backend implementation files,
  architecture traps, controller tests, and screened evidence only.
