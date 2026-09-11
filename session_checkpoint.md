# SAME / SCUMM v5 session checkpoint

## Refresh-clear diagnosis and fix (2026-09-09)

- The BAD clear is a semantic revalidation hit-test failure, not C17 display
  readiness. BAD's active records still contain object 490's CDHD record
  (`EA 01 B8 00 40 00 50 00 20 00 00`), and C17 verb 3 is present, text
  type, and has name length 5. The clear path also leaves
  `SAME_SCUMM_INTERACTION_OBJECT=0`, which is written by the generic hit-test
  miss path; the authored-verb failure path would not clear that field.
- The failing refresh code was recomputing a hit from the current cursor after
  a sentence. In BAD the cursor/projection state was no longer the original
  object point by the time the clear was observed, so a valid selected object
  was treated as absent. GOOD retained mode 1 because its refresh inputs did
  not diverge.
- Production fix: generated room metadata now provides the generic
  `ScummV5_Generic_Object_ValidateSelected_Far` service, which validates the
  selected object against active source records and preserves its interaction
  flags/index. `ScummV5_Controller_RefreshSelection_Far` uses that service,
  then re-queries authored verbs; it no longer re-hit-tests the presentation
  cursor. No Fate ID or verb special case was added.
- Focused controller suite: 50/50 PASS. Poppy lint passed during the rebuilt
  target assembly. Candidate ROM:
  `build/generic-action-refresh-fix.sfc`, SHA-256
  `85a1da9d53c899d6692b9929de24201a42f67d5f849ccbcbf1dd962ea6f6b511`;
  SA-1 finalization/audit passed. The normal visual validator has not yet
  completed this candidate: it stalled in its generation-aware surface fence
  after reaching room 42, so target interaction acceptance remains pending.

## Generation-aware presentation fence A/B (2026-09-09)

- Control: `f7826ed39e3c2297724a7ffe223dd05a73e6328316c46ce0a1ec41644f01a1d5`.
  Candidate: `85a1da9d53c899d6692b9929de24201a42f67d5f849ccbcbf1dd962ea6f6b511`.
- The control proves that the initial full-surface conversion is not a one-frame
  operation. At completed logical-frame samples, generation 1 progressed from
  892 candidate tiles / 4 converted tiles at +0 frames to 0 candidate / 896
  converted at +256 frames, then reached a stable committed generation. After
  the cursor redraw, generation 2 also reached idle/unlocked with FIFO empty.
  This is measured progress, not a backend deadlock; the fence must allow
  progress-aware waiting rather than a short fixed horizon.
- The candidate diverges before interaction while the initial room presentation
  is still pending: it accepts generation 1, but after the first completed-frame
  advances the engine remains busy in the room-entry phase and the backend step
  counter stops at 2 (later samples retain pending visual 2 and no committed
  room-42 generation). NMI activity alone continues. This is not explained by
  conversion duration. The candidate's generated selected-object validation
  helper is not on the pre-interaction controller path; a validator-only
  execution hook is now armed at the pre-A boundary when its symbol is present,
  and the helper must report zero calls before selection.
- The first validator-side observation defect is now identified: the startup
  gate had accepted six consecutive room-42 phase-2 snapshots even while
  `SAME_ENGINE_FRAME_BUSY=1`. Phase 2 is ENCD/room-entry execution, not a
  coherent interactive boundary. The candidate then reached error 20 while
  the validator was advancing from that premature boundary; the control
  naturally reached phase 0. The validator now requires room 42, phase 0,
  `engine_busy=0`, and the existing semantic idle predicates before installing
  the generation fence. This is validator timing/fencing work; no production
  change has been made.
- With that corrected gate, the control reaches room 42 phase 0 at startup
  frame 303 and then enters the measured generation-1 conversion. The
  candidate remains coherently at room 42 phase 2 (ENCD/room-entry), with
  walkbox 7, error 0, active count 2, and no transition to phase 0 through
  startup frames 1200. Thus the candidate's pre-interaction difference is not
  a short conversion timeout. The selected-object validator hook has not fired
  before interaction because the candidate never reaches the corrected
  interactive boundary; no production helper call is being used as an
  explanation for this divergence.
- The provenance audit then found that these ROMs are not an exact
  configuration A/B. Both use FULL ATLANTIS, the same member hashes, the
  historical Poppy DLL `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`,
  startup42, and the same carrier/backend. The control explicitly set
  `SAME_SCUMM_SCENARIO_START_ROOM=42` and
  `SAME_BUILD_SCUMM_ROOM_VISUAL_ROOMS=42`; the candidate set neither and
  generated `SCUMM_V5_SCENARIO_START_ROOM=$44` (room 68). The candidate also
  used a relative visual-manifest path while the control used an absolute
  path. Generated build-config hashes differ (`c86b2e...` versus `183d2a...`)
  and generated room-data hashes differ (`d5da28...` versus `06c2f6...`).
  The shared room-42 manifest identifies ENCD length 161, but ROM-level
  program-223 byte identity has not been established across these mismatched
  builds. Rebuild the candidate with the control's explicit FULL startup42
  environment before tracing lifecycle 8/9/10.
- Rebuilt the refresh-fix source with the control's exact FULL startup42
  environment as `build/generic-action-refresh-fix-full42.sfc`, ROM SHA
  `b80d63a62be9f8afdfd1951f61ea216c2341a94be65c2d909adf4ab57eda5795`.
  Its identity has the same explicit start room/room-visual settings and the
  same build-config hash as the control. The embedded room-42 ENCD chunk is
  byte-identical between control and rebuilt candidate at both embedded copies;
  the 169-byte chunk SHA is
  `d78775b6596efb8a602c6f9e575b63fab1cedf7f4fc2503c27a608cfa43d6242`.
  Under this valid A/B, both runs reach phase 0, and the rebuilt candidate
  shows the same progressing generation-1 conversion and committed generation
  2 after cursor presentation. The prior phase-2-through-1200 result was
  configuration-induced, not a selected-object-helper or refresh regression.
- Validator-only change: `wait_for_surface_quiescent` now records completed-frame
  progress and extends the budget while backend work advances; it reports a
  bounded no-progress diagnostic instead of treating a progressing conversion
  as a hang. No production video, interaction, or refresh code changed in this
  pass. Candidate target acceptance remains pending until its first divergence
  is localized.

## First-A transient forensic trace (2026-09-09)

- Validator-only event-loop implementation is complete in
  `tools/validate_scumm_room42_controller_nexen.py`. It arms all four
  diagnostic writers and both mode-value writers together, advances one
  pressed frame and one released frame, records ordered hook notifications,
  then uses a completed logical-frame fence only for the final semantic
  snapshot. No production code or input helper was changed.
- GOOD `ca4b89f8...` (`build/generic-action-lifecycle3-names9.sfc`) trace:
  `diag_31 -> diag_33 -> mode_01 (0 -> 1)`. There were no `$32` or `$34`
  events. Final completed-frame state is mode `1`, object `490`, verb `3`,
  error `0`. Artifact:
  `build/forensic-good-final3/first-a-forensic.json`.
- BAD `f7826ed3...` (`build/generic-action-lifecycle4-names26.sfc`) trace:
  `diag_31 -> diag_33 -> mode_01 (0 -> 1) -> mode_10_or_reset (1 -> 0)`.
  Final completed-frame state is mode `0`, object `0`, verb `0`, error `0`.
  The first differing event is therefore the later mode `1 -> 0` clear, not
  hit testing or authored-verb discovery. Artifact:
  `build/forensic-bad-final3/first-a-forensic.json`.
- Hook notifications preserve event ordering by emulator cycle/frame and the
  mode writer's before/after value. The register/memory fields attached to
  each notification are paused frame-boundary observations; final semantic
  conclusions use the separate completed-frame snapshot. The BAD trace is
  now the concrete frontier for the refresh-clear path. Do not change
  production interaction code in this diagnostic checkpoint.

## Current Fate/Open-verb checkpoint (2026-09-09)

- `docs/winston_inkpen_unconfirmed.md` explicitly begins with “Documented by
  Luna” and date `2026-09-09`; it remains documentation-only.
- First-A regression comparison has begun using the exact local GOOD binary
  `build/generic-action-lifecycle3-names9.sfc` (SHA
  `ca4b89f8c5581465a71829f7e99e4cf5dea8c540056c8774d975a94de9c6a889`) and
  current BAD ROM `f7826ed39e3c2297724a7ffe223dd05a73e6328316c46ce0a1ec41644f01a1d5`.
  Under the same current harness and committed-surface setup, GOOD advances
  beyond the first A into object-selection mode; its run then stops only at
  the expected later C17-name field incompatibility. BAD receives the A
  edge, but remains mode 0 after the first-A attempt and never reaches the
  stable mode-1 checkpoint. BAD's post-attempt state retains source hit
  scratch for object 490 and authored verb result 3, so this is not yet
  evidence of a coordinate miss or C17 readiness failure. Exact `$31/$32/$33/$34`
  capture at the completed controller boundary remains the next diagnostic
  step; do not change production interaction semantics until that breadcrumb
  is captured.
- Current mode-writer audit is narrow: boot initialization writes mode 0;
  the hover hit-success path at `ScummV5_Controller_Frame__verb_ok` writes
  mode 1; the sentence path writes mode 2; refresh-selection success writes
  mode 1; refresh-selection clear writes mode 0. No C17-name writer changes
  mode. The next pass must hook these writes during the one BAD first-A frame
  and bind the `$31/$32/$33/$34` execution labels to that same event, because
  later completed frames overwrite the diagnostic breadcrumb with the normal
  room-ready value `$06`.

- The requested C17/HUD separation work is built with the recovered historical
  SAME-compatible Poppy DLL (`34514923...`) and passes Poppy lint, assembly,
  SA-1/BW-RAM ROM audit, and FULL startup42 through room 42 / actor room 42 /
  phase 0 / readiness 1 / error 0. Current ROM:
  `build/generic-action-lifecycle4-names26.sfc`, SHA-256
  `f7826ed39e3c2297724a7ffe223dd05a73e6328316c46ce0a1ec41644f01a1d5`.
- C17 remains source/runtime authoritative: after startup and at the failed
  controller attempt, verb 3 has length 5 and bytes `Open\0`. No controller
  verb-name table or fabricated name was added. The controller-owned text
  buffer is staged through the target-neutral text service so authored C23 text
  cannot overwrite it.
- The first replay from a committed room-42 surface is not yet a pass: the
  deterministic released/A/released edge is observed, but the controller does
  not leave hover mode or submit the source-authored Open sentence. The final
  state is room 42, error 0, C17 `Open`, controller mode 0/object 0, with the
  source hit-test scratch still identifying object 490. This is now a concrete
  controller input/selection-path checkpoint; it is not evidence that C17 is
  unready. Temporary branch witnesses were added to the validator for the
  cursor-A, hit-success, and authored-verb-success labels.
- The current target replay log is `build/names26-c17trace/run.log`; preserve it
  as diagnostic evidence while localizing the first missing controller edge.
  Do not change video, surface, cooker, or closed graphics milestones for this
  checkpoint.
- Future copyright-free fixture direction is documented in
  [`docs/winston_inkpen_unconfirmed.md`](docs/winston_inkpen_unconfirmed.md).
  This is documentation only; no Winston scene conversion or implementation
  has started.

## Current development toolchain pin (2026-09-09)

- Historical Poppy DLL `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e` was found locally in `poppy-jsl-address-fix`; retain it as provenance for earlier ROMs only.
- Focused upstream #376 fix: PR #393, source `5ab64a4745532d8ef732a2ee694ac9b6dd0e054d`, proposed DLL `57a8768599972c15a09ad92b80b9c4af041345bc1aad61d004159f8a7c54b1cf`; correct/focused but rejected for SAME compatibility because it leaves generated `ScummV5_*_Far` symbols unresolved.
- Current SAME-compatible pin: recovered DLL `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`, source identity independently `8ee859b33bad94e3a01e9c78026803e482292801`; `tools/poppy_pin.json` and both build scripts enforce this pair. Historical ROM build identities remain unchanged.
- With the recovered DLL, current SAME builds and audits successfully: ROM `build/generic-action-lifecycle3-room42-historical.sfc`, SHA-256 `14003404823ad62f2836949214ce559bc31cde53d6170ffb003715f0441da52c`, FULL startup42 coherent result room 42 / actor room 42 / M23A phase 0 / readiness 1 / error 0.
- Controller edge delivery is now proven as validator behavior, with no production interaction change. Nexen's `set_input(..., frames=...)` auto-advance form was the wrong primitive for an edge: it releases after the run, and it can leave the previous directional level latched at the next fence. The validator now uses `hold=true` level control, a bounded released baseline, and a write-hook fence on `SAME_INPUT_PRESSED`.
- Accepted baseline A-control `b97fe25e...`: completed released frame `[0,0,0,0,0,0]`; one A press observed as `[0x80,0,0,0,0x80,0]` (JOY1 A is `$0080`, distinct from MCP enum `$0001`); next release returned all six bytes to zero. The same edge entered normal controller selection and then Open: object 490, verb 3, one sentence submission, actor `(157,101)` moving toward `(218,104)`, mode 2, error 0.
- Current ROM `14003404823ad62f...`: the identical helper produced the same release/A/release sequence and entered the same authored Open/movement state (`object=490`, `verb=3`, `moving=2`, actor `(157,101)`, destination 218, error 0). Its later moving-publication witness remains a separate validator/presentation-observation failure; input delivery is no longer the blocker.
- Edge evidence logs: `build/accepted-b97-edge-test9/` and `build/current-edge-test.log` (current log SHA-256 `816ef3b5d576308b515d5f062250f329d71164b45ee66cd9de9fb2b9fd62d253`). The full replay still stops in `wait_for_moving_publication` after the semantic moving snapshot; that witness issue is downstream and remains open. Do not change production interaction code to address it.

## Moving-publication classification (2026-09-09)

- The accepted `b97fe25e...` and current `140034048...` runs both reach the
  same moving semantic state and enter the actor compositor. The current
  failure is classified **A: moving witness never publishes**, not “witness
  invalidated”: no run has yet observed `WITNESS_VALID=1` followed by zero.
- At the failure frontier the current run reports actor render entries 16,
  moving render entries 8, bounded damage `32x64`, render retry 1, initial
  accepted PRESENT count still 1, and no additional moving PRESENT/commit.
  Thus the first missing edge is after moving composition/restore and before
  successful moving PRESENT; the final `VALID=0` is still the reset/default
  state, not evidence of a 1→0 production clear.
- Static writer audit: `SAME_SCUMM_CONTROLLER_WITNESS_VALID` is written only
  by `ScummV5_Controller_ResetVisualCache_Far` (clear) and the successful
  post-PRESENT block in `ScummV5_Controller_RenderActor_Far` (set); SERIAL is
  incremented only after that set. No other direct source writer was found.
- The visual phase still has an old numeric gate (`mode >= 2` before actor
  rendering), but the captured moving run has `mode=2`, `DESIRED_SELECT=1`,
  and eight moving compositor entries. That gate is therefore not the first
  divergence in this run; do not change it speculatively. The next boundary
  is `PushDamagePresent` result/lock state.

## Generation-aware quiescence fence (2026-09-09)

- Added validator-only `wait_for_surface_quiescent`: it fences completed
  logical frames and requires room 42 semantic readiness, no pending room
  visual, presented room 42, backend idle/unlocked, committed generation equal
  to `NEXT_GENERATION`, no live surface DIRTY/PRESENT packet for an
  uncommitted generation, and the same relationship after one additional
  completed frame.
- Static audit found no production writer for
  `SAME_VIDEO_SURFACE_PRESENTED_GENERATION` (`$4010A2`). It is retained in
  diagnostics as `presented_generation_stale` only and is not a readiness
  predicate. No production writer was added.
- The validator now records bounded completed-frame conversion samples at
  offsets 0/1/8/32/64/128/256: backend steps/state/lock, next/pending/
  committed generations, candidate/pending/inflight/converted tiles, scan
  cursors, DMA words, and accepted/rejected PRESENT counts.
- A-control `b97fe25e...` and current `140034048...` both pass initial and
  post-cursor stable quiescence. In both, generation 1 progresses from
  `CONVERTING`/locked with 892 candidates and 4 converted tiles to 0
  candidates and 896 converted tiles by the 256-frame sample, then reaches
  generation 1 committed and idle/unlocked. This is bounded conversion work,
  not a stalled initial backend or a validator rejection.
- The same fenced runs naturally submit Open and reach the moving semantic
  state (`actor=(157,101)`, destination `(218,104)`, moving=2, pose=1) on both
  ROMs. The subsequent moving generation remains the separate unresolved
  frontier: no accepted moving PRESENT/commit was observed before the current
  validator's commit wait expired. No production interaction, actor, damage,
  or backend code was changed in this pass.
- Evidence directories: `build/quiescent-a-b97-r2/` and
  `build/quiescent-b-140034-r1/` (native captures disabled; raw Nexen logs
  retained locally). The full logs are diagnostic artifacts, not acceptance
  evidence.

## Latest completed-frame A/B classification (2026-09-09)

- Accepted A-control binary: `build/generic-room42-interaction-fixedpoppy23.sfc`,
  SHA-256 `b97fe25e4d7795004610ff1d6e171fe9e1758b94f319c3739c317e808d26547d`.
  The current strict readiness path, with no interior video/FIFO hooks, reaches
  room 42, phase 0, actor room 42/walkbox 7, readiness 1, error 0 at frame 502
  (`build/strict-a-b97/report.json`). This rules out a validator-wide rejection
  of the accepted binary.
- Candidate B: `build/action-matrix-mask7.sfc`, SHA-256
  `762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`.
  Under the same strict run it reaches room 42 but remains phase 2/readiness 0,
  error 0 at frame 502 (`build/strict-b-762/report.json`). A no-screenshot,
  non-readiness-gated natural control reproduces B's failure, so this is not
  manufactured solely by the strict visual-readiness loop.
- The first coherent B divergence is the authored room-68 path, not a backend
  lock invariant: completed frame 223 is room 68 phase 5 with one accepted
  PRESENT, pending generation 1, committed generation 0, state CONVERTING (2),
  lock 1, and live FIFO count 0 (`build/frameboundary3-b-762/report.json`).
  Later SCUMM execution enters source script 145/program 252 in slot 2 and
  repeatedly executes its authored `iq-points` loop without returning through
  `C4_RunNestedChild`; no SCUMM budget/error path was observed.
- A and B are not equivalent build configurations: A is an explicit direct
  room-42 root with controller witness and room-42 visual manifest; B is the
  room-68 startup root with class `491:0x2f` and source-actor overlays, and no
  explicit start-room/witness. Both identify FULL ATLANTIS and the same fixed
  Poppy DLL. This configuration difference is recorded, not treated as proof
  that ACTION_PENDING/C17 caused the B scheduler divergence.
- Lock/state writer evidence is ordered correctly. At completed-frame boundaries
  no stable `IDLE + surface_locked=1` was observed. The actual accepted-PRESENT
  sequence is lock=1 followed by state=CONVERTING; completion is lock=0 followed
  by state=IDLE. The apparent mixed state is therefore an interior-observation
  possibility, not yet a production invariant failure. Writer evidence is in
  `build/writers-b-762/report.json`; completed-frame evidence is in
  `build/frameboundary3-{a-b97,b-762}/report.json`.
- No production fix was made for this classification. The next safe step is to
  reconstruct or locate the exact accepted authored startup42 configuration,
  then compare its completed-frame scheduler path with B before changing
  SCUMM, video service, FIFO, or backend state.
- The validator's engine-phase read was corrected from the unrelated
  `$7E1024` byte to `SAME_RESET_DIAG_ENGINE_PHASE=$7E103C`; this is
  validator-side observation only. With that correction, a bounded B run
  captures `engine_phase=2` while program 252/PC `$001E` is active, whereas A
  captures `engine_phase=3` after `Same_Engine_Frame` returns. The longer B
  run is not used as a new acceptance claim because its phase byte is later
  overwritten by unrelated runtime state; the bounded first-stall snapshot is
  the useful evidence.
- Existing B action-matrix binaries with masks 0, 1, 2, and 4 reproduce the
  same room-42 phase-2/readiness-0 outcome as mask 7. The pre-input failure is
  therefore common to this room-68-root configuration, not isolated to one
  controller behavior mask. Their results are under
  `build/natural-m{0,1,2,4}-matrix/`.
- A local isolation build with the B room-68 root, mask 7, and the class/source
  actor overlays removed was assembled and ROM-audited as
  `build/room68-no-overlays-v2.sfc`, SHA-256
  `e7eb9483774770b62f0c0fdac2b2bddcb3204eeebbe00e2966fc6de3d046153e`.
  Its target run now reproduces the same result: room 42, phase 2, error 0,
  readiness 0, `engine_phase=2`, with NMIs continuing
  (`build/room68-no-overlays-v2-run/report.json`). Removing both overlays does
  not remove the stall, so they are not the cause. The failure remains in the
  room-68 authored startup/SCUMM scheduler path; no backend or strict-readiness
  fix is justified.

### Room-42 ENCD / engine-return localization after reboot (2026-09-09)

- Added only a validator-side read of the existing fixture opcode ring to
  `snap_light`; no ROM was rebuilt or changed. Fresh diagnostic outputs are
  `build/optrace-good-b97-r2/` and `build/optrace-bad-nooverlay-r2/`.
- GOOD `b97fe25e...` is the accepted direct-room-42 oracle, not an equivalent
  room-68-root build. BAD `e7eb9483...` uses the room-68 startup root and
  remains phase 2. This configuration mismatch remains explicit.
- At the shared room-42 ENCD prefix both traces agree: global 144/program
  219, slot 1, PC `$0031`, opcode `$7A`, then global 145/program 252 is
  allocated as slot 2. The child executes the same authored `iq-points`
  bytecode (`script-145.scrp`, 130 bytes); no ENCD byte/resource mismatch has
  been shown at entry or child launch.
- BAD reaches room 42 after room-68 phase-4 retirement, then remains in phase
  2 through the program-252 child path. Its no-hook final state is error 0,
  `engine_phase=2`, with NMIs advancing and no completed engine return.
- GOOD's direct-room diagnostic path reaches program 223/PC `$008A` and phase
  0 after the child path; BAD retains room-lifecycle/live-slot ownership after
  the analogous terminal transition. The exact return/rehydration instruction
  is still the next capture target; no production fix has been made.
- Engine hooks are timing-perturbed and are used only for call counts. BAD has
  engine-frame returns before entering the stalled room-42 pass but none after
  that point, agreeing with the coherent no-hook `engine_phase=2` snapshot.
- The problem is now narrowed to generic outer room-slot save/retire or
  `ScummV5_Engine_Frame__complete_success` return handling after child
  completion, not video, FIFO, room bytes, or the initial ENCD opcode. Do not
  patch until the exact writer/PC and slot identity are captured.

### ENCD terminal boundary evidence (2026-09-09, post-reboot)

- Compared accepted GOOD `b97fe25e...` with BAD no-overlay
  `e7eb9483...`; no ROM changes were made. The validator-only reports are
  `build/lifecycle-fence-good-r4/` and `build/lifecycle-fence-bad-r5/`.
- Both room-42 ENCD executions fetch the same terminal sequence from program
  223 / `room.42/ENCD` (161 bytes, SHA
  `9fcdea10c8763db018d188db1e67e140c8f4ea86cdced2514af4e25bc12bbcfc`):
  the final useful opcode is PC `$008A`, `$0A` (`stopObjectCode`). The
  preceding program-223 opcode PCs match through `$0087`; no first ENCD-byte
  divergence has been observed.
- GOOD then reaches a coherent next-frame boundary with `m23a_phase=0`,
  `engine_phase=3`, `active_count=1`, and only delayed script 208/program 226
  live. BAD reaches the same program-223 terminal boundary with
  `m23a_phase=2`, `engine_phase=2`, `active_count=2`, and only delayed script
  208/program 226 visible in the slot table; it does not produce a normal
  `Same_Engine_Frame` return.
- BAD's M23A ring is full but records the room-68 lifecycle through code 10,
  then room-42 request/validation/old-room retirement/commit codes 1..5. The
  room-42 ENCD is therefore installed and executed; the remaining gap is the
  terminal stop/outer lifecycle return, not room acquisition. Stale packet
  slots and backend state are not implicated.
- The current diagnostic tool attempted `run_to_exact_exec_stop`, but the
  post-reboot Nexen instance does not expose that tool (`Unknown tool`). This
  is a tooling capability loss, not runtime evidence. Do not claim the exact
  stop-handler PC until an available synchronous hook/trace captures it.
- Current classification: BAD is CPU/mainline-stalled after the identical
  ENCD stop fetch, before the phase-2-to-phase-0 lifecycle return. The exact
  stop-handler/return instruction and whether the room-owner slot identity is
  wrong remain open. No production fix or speculative slot mutation has been
  made.

## Current objective: generic room-object interaction (2026-09-08)

- The room-42 graphics/surface/controller milestone is CLOSED at review
  `review/controller-room42-final`, commit
  `f95f7e26e6c81fbf2dfaf5517939283128b61c7a`, ROM
  `9370b4acb6ff649b008c5e4135771b24dc89fb74be798e5bfbc2cbda7aa8702f`.
  Do not reopen graphics without contradictory regression evidence.
- Poppy provenance is split deliberately: the accepted historical ROM keeps
  its recorded toolchain identity. New development uses focused upstream
  Poppy #376 PR #393, commit
  `5ab64a4745532d8ef732a2ee694ac9b6dd0e054d`.
- Generic interaction implementation is target-proven on fresh ROM
  `build/generic-room42-interaction-fixedpoppy23.sfc`, SHA-256
  `b97fe25e4d7795004610ff1d6e171fe9e1758b94f319c3739c317e808d26547d`.
  FULL startup42 reaches room 42/error 0; the controller resolves a source
  CDHD hit to object 490, discovers authored verb 3, submits the normal
  `(3,490,0)` sentence, moves to `(218,104)`/walkbox 10, opens the locker,
  completes inspection dialogue, and selects a second source object 492 from
  its own CDHD bounds. Target report:
  `build/generic-room42-interaction-fixedpoppy23-run-normal/report.json`.
  No production controller path contains a locker rectangle or object-490
  selection policy. Host synthetic coverage proves miss, half-open edges,
  camera projection, overlap precedence, parent-state visibility, and
  authored-verb fallback exclusion. The generic interaction implementation is
  still dirty and not yet published.
- Host CDHD hit testing now uses room/world coordinates, half-open
  rectangles, reverse OBCD order for overlap precedence, and flags bit 7 as
  non-selectable. Explicit OBCD VERB entries are exposed separately from the
  `0xFF` fallback. Target generation now emits generic hit-test and first/next
  authored-verb services over the existing active-room object records.
- Controller integration is now target-proven through the first authored action:
  the FULL startup42 target resolves cursor → CDHD object 490 → authored verb 3
  → normal sentence API `(3,490,0)`, moves to `(218,104)`/walkbox 10, opens
  object 490, and completes the existing inspection dialogue with error 0.
  The production selection path contains no locker rectangle or object-490
  selection policy; the remaining presentation helper reads the selected
  controller object dynamically.
- Remaining before publication: consolidate the screened review branch and
  run/record the publication-facing evidence. The target second-object
  witness is complete; miss/edge/overlap/camera/verb semantics are covered by
  copyright-free host fixtures. No graphics/surface/hoist work is reopened.
- Screened review commit `f0f945509c81a00e32c8eb745af1e6b136d6be34` was
  published from isolated worktree `/home/chad/SAME-0.2.0-review-generic` to
  `astrobleem/SNES-SAME-SCUMM`, branch
  `review/controller-room42-generic`. Remote HEAD is verified at the same
  SHA. The commit adds source/tests/checkpoint/review documentation only;
  ROMs, savestates, ATLANTIS data, and unrelated dirty work were not added.

## Poppy semantic-address fix (2026-09-08)

- Independent Poppy reproducer and matrix are in `/home/chad/poppy-jsl-address-fix`.
  The JSL encoder emits the correct four bytes (`$22 ll hh bb`); the SAME
  apparent `+3` drift was caused by conditional `EQU` symbols not being
  pre-registered during semantic sizing. The fix recursively pre-registers
  constants in conditional branches, so direct-page sizing agrees with codegen.
- Existing upstream issue: [TheAnsarya/poppy#376](https://github.com/TheAnsarya/poppy/issues/376);
  supplemental evidence comment:
  https://github.com/TheAnsarya/poppy/issues/376#issuecomment-5587606104.
  Review PR: https://github.com/TheAnsarya/poppy/pull/392.
- SAME remains pinned to the tested fork DLL/commit:
  `8ee859b33bad94e3a01e9c78026803e482292801`, DLL SHA-256:
  `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`.
- The clean upstream-base review is now `astrobleem/poppy` branch
  `fix/poppy-376-focused-clean`, commit
  `5ab64a4745532d8ef732a2ee694ac9b6dd0e054d`, PR #393:
  https://github.com/TheAnsarya/poppy/pull/393. Stale broad PR #392 was
  closed/superseded. The clean branch excludes unrelated fork work; full
  Poppy suite: 3375/3375. Issue #376 has final root-cause and evidence
  comments recorded.
- Fixed-Poppy SAME ROM: `build/poppy-fixed-startup42.sfc`, SHA-256
  `2059497c0d5bddb0df5c622662060f7082f504b4c2f3128f531c9aeff12cda26`.
  Build identity: `build/poppy-fixed-startup42.build_identity.json`; explicit
  FULL corpus is `/home/chad/ATLANTIS.zip` with member hashes recorded there.
  The corrected map now places `RenderActor__blit_ok=$9DDE`,
  `full_compose_retry=$9DF4`, and `ScummV5_Camera_ResetState_Far=$D0FE`,
  matching emitted bytes. Explicit startup42 reaches room 42, actor room 42,
  readiness 1, error 0 at frame 702. Do not resume walking proof from the
  old Poppy build; use this ROM/configuration.
- Witness perturbation matrix on the same explicit FULL configuration:
  witness-out ROM `build/poppy-fixed-startup42-witness-off.sfc`, SHA-256
  `47edf9f9f3e3526e127d7840e982637c7210ac21c0ac67d1896fc9ae53486ae9`,
  also reaches room 42/readiness 1/error 0 at frame 702. Witness-in and
  witness-out therefore do not show an early startup divergence. The fixed
  witness-in controller run reaches hover, Open, and a moving semantic
  snapshot, but no successful moving actor PRESENT is currently observed;
  that is a separate post-startup visual-publication frontier, not evidence
  against the Poppy fix.

## Event-driven walking-proof frontier (2026-09-08)

- Startup regression remains accepted CLOSED at ROM
  `d4eaba6099f9ae428a3ad7dd582d2b432c216b1d9d9b72ac3d38999cd113d746`:
  explicit FULL startup42 reaches room 42, actor room 42, readiness 1, and
  error 0; the accepted focused regression total is 516/516.
- The walking observation path is now fenced by production-success events in
  the validator, not guessed frame polling: a write hook on the semantic
  final desired-visible field (`$7E5E4D`) records the complete desired snapshot,
  a write hook
  on the fixture-only successful-publication validity byte (`$7E5E6A`) records
  only a completed actor PRESENT, and a backend committed-generation hook
  (`$401010-$401011`) fences the same PRESENT through conversion completion.
- `wait_for_semantic_moving_snapshot()` and the ordered validator stages
  `semantic_moving_snapshot -> walking publication witness -> committed
  generation` are observational only. They do not add production waits,
  alter movement timing, submit sentences, or update the witness on failed
  PRESENTs.
- Exact moving surface/native fidelity is still pending. Do not claim it from
  a standing frame or from a post-movement screenshot. Run A must capture the
  moving witness and its committed generation before advancing another logical
  frame; Run B remains the ordinary full controller/dialogue replay.

## Current semantic-snapshot frontier (2026-09-07)

- Accepted baseline for this pass: explicit FULL startup42 must reproduce
  `script 1 -> room 1 -> room 42 -> ENCD/scripts 200/201/208 -> error 0`
  before the walking gate is considered. Current regression ROM under audit:
  `e1739ea71cef9d60909072ec9d40e33dab8292ea3187565b5a471f70a90338da`.
- Bisect scope is limited to three behavior families: pose-aware cache
  invalidation, no-cache-commit on failed PRESENT, and post-controller visual
  snapshot/order. Fresh explicit-FULL target results: A mask `$00` ROM
  `21ef65148004af9f8e4917a87ce4ec961789b2698f1d4035ae3def8c8f555d08`, B
  pose-only mask `$01` ROM `c1f70977b71264c7f43705f482e0a5a9f5a72cc630e77957d59c6c70b9acc99c`,
  and D ordering-only mask `$04` ROM
  `01ac818ebb000796fc558ea104ad07e83526558e62f660ddb34165dceca08938`
  reached room 42/error 0; C mask `$02` ROM
  `123c5c6ae9978197ab16be0d5d8bb5a8e1b320bacc344af9c36828b600769a7c`
  was first bad, and E mask `$07` ROM
  `7119cb18d7c1eee42b2bf46fafbc8353e62361d65d118950d30447de2d8b4145`
  reproduced it. At frame 282 C/E had room 42/error 0 but actor-1 room 0,
  active slots 0/144/145, readiness 0; A/D had actor-1 room 42 and delayed
  script 208. The failure is visual-service starvation, not a SCUMM error.
- Generic repair: if a rejected PRESENT leaves the accepted render cache
  invalid, the late visual phase waits for the room's pending visual request
  to clear and surface status to become OK before one-time actor composition.
  This avoids repeated pre-ready full-room composition without committing a
  failed render. Guard-fixed all-three ROM `build/semantic-snapshot-guardfix.sfc`
  SHA-256 `074c98ab84bc5c4dc1718cb1271d0f928eaa7dd7741087ec6379225a960dd30a`;
  target startup reaches room 42/actor room 42/readiness 1/error 0 at frame
  352.
- Finalized guard-fixed ROM (carrier manifest applied):
  `build/semantic-snapshot-guardfix.sfc`, SHA-256
  `9ac22e244e44495d5803b12e48ace3e159fdf2b4bfb1136a49b88c947cf62823`.
  Explicit FULL startup42 replay reaches room 42, actor room 42, readiness 1,
  error 0 at frame 352; the pre-finalization `074c98...` hash is retained only
  as intermediate target evidence.
- Current controller replay reaches room 42 and consumes Open with the
  expected semantic movement (`157,101` toward `218,104`), but the validator
  currently fails to bind an accepted moving generation before movement ends.
  This is the next visual-snapshot/runtime observation frontier; no actor
  fidelity PASS is claimed from that run.
- Contract repair after the bisect: `ScummV5_Controller_RenderActor_Far` no
  longer writes `DESIRED_SELECT` while choosing a cooked frame. The semantic
  snapshot is now immutable during attempted composition; only a successful
  PRESENT updates the accepted render key. Focused suite is 165 tests passing.
  Rebuilt/finalized ROM `build/semantic-snapshot-contractfix.sfc`, SHA-256
  `d4eaba6099f9ae428a3ad7dd582d2b432c216b1d9d9b72ac3d38999cd113d746`;
  explicit FULL startup42 reaches room 42, actor room 42, readiness 1,
  error 0 at frame 352. The native controller replay still needs a bounded
  moving-generation run; no visual acceptance is claimed.
- Validator-only observation improvements: `--no-native-captures` permits a
  semantic run without screenshot calls, `advance_until` uses a compact poll
  instead of the full scene snapshot, and surface damage reads use the
  generated carrier service window. These do not alter production execution.
- Startup guard requirement: fixture actor snapshot/cache logic is inert before
  a valid room/actor state exists in rooms 68, 75, and 1. Room mismatch must
  not clear or publish unrelated presentation state.

## Retained bounded-damage frontier (historical)

- Latest source fix: `Same_VideoSurface_ComposeRoomOnly_Far` now prepares an
  installed room in the indexed surface without publishing. The actor path
  adds actor/locker/cursor pixels and submits one atomic PRESENT, preventing a
  background PRESENT from starving the actor transaction. Actor damage bounds
  use the semantic desired snapshot consistently. Fresh ROM
  `build/room55-semanticcontract.sfc` SHA-256
  `f9fe12d9bc612e37d90e81d95ce462bfd907675aeb413764eb072dc974b52a15`.
- Explicit FULL startup42 reaches room 42/error 0 on the fresh ROM. The
  target replay has proven desired moving state `(200,101), moving=10,
  destination=218` before the late visual phase, but the current controller
  replay is not yet a complete acceptance run: input/observation is flaky at
  hover in recent runs. No visual or semantic PASS is claimed for this ROM.
- Target service synchronization in the validator uses Mode3 IDLE=`$01` and
  live FIFO count, not the uninitialized state code `$00`. This is validator
  observation only. `action_tap` is separated from the long cursor hold so
  Open does not consume the short authored walk before sampling.

- Acceptance status: bounded-damage semantics and natural intermediate
  `(200,101)` remain proven; exact actor walking fidelity is pending. The
  current task is a generic semantic-state-to-visual-snapshot repair, not a
  cooker/backend change.
- Current source baseline after the first ordering repair builds and enters
  room 42/error 0. The latest semantic-snapshot diagnostic ROM is
  `build/room55-snapshotfix3.sfc`, SHA-256
  `1329d6811cf35d504271d6fddf9838ad916534029b7cb0a20a4fbfd5c0efee4e`.
- First demonstrated new cache failure: making non-room RenderActor calls
  inert exposed stale/uninitialized `RENDER_VALID` at room entry. The generic
  fix moves cache invalidation to `ScummV5_RoomVisual_Installed_Far` via
  `ScummV5_Controller_ResetVisualCache_Far`; nonmatching rooms no longer clear
  presentation state. Semantic actor snapshot fields are `$7E5E42-$7E5E49`.
- The snapshot producer runs after `ScummV5_Movement_UpdateAll_Far`; the late
  compositor consumes desired X/Y/pose and commits accepted cache identity only
  after successful PRESENT. Target scene has reached a natural
  `(200,101), moving=10, destination=218` state on the snapshot build, but the
  latest controller replay still has an intermittent input/readiness failure;
  full visual acceptance is not claimed.
- Latest source build: `build/room55-snapshotfinal.sfc`, SHA-256
  `78cc06b578ca7f0015ceaaafdf71a4b2be57169a38fd98b47e56590cfae0ebef`.
  Explicit FULL startup42 reaches room 42/error 0 and a natural moving state;
  target replay has not yet completed the controller handoff in the latest
  runs. The current validator waits at complete frame boundaries for semantic
  mode transitions and records the failure state rather than advancing a
  guessed batch.
- Current proof status: host focused suite 29/29 and full test discovery
  504/504 pass; Poppy build/lint and `sa1_bwram` ROM audit pass. Target visual
  fidelity remains pending. Do not publish this diagnostic ROM as accepted.
- Current diagnostic builds: `build/room55-phasefix.sfc` SHA-256
  `0c08cd7ae5e307a412ceae2deb21488abdf837e740dbdc216b0abd586254a18f`,
  `build/room55-phasefix2.sfc` SHA-256
  `3e847142a3a7ddce4b97865147ed62cb14d5573759713a08230a7c16f4f8e14c`,
  and `build/room55-phasefix3.sfc` SHA-256
  `3be51823032a712ac4bff2f750626efe9e168c4b1ca818c8be593ddea1c01e32`.
- Current source changes move actor composition to the post-controller
  semantic boundary and add pose-aware invalidation; target replay must still
  bind a committed moving generation. Do not claim actor fidelity yet.
- The prior concrete evidence remains: renderer samples were
  `moving=0/mode=0/destination=$FFFF` while post-frame state was
  `(200,101)/moving=10/mode=2/destination=218`. This is the ordering symptom,
  not evidence against the accepted cooker or backend.
- Last complete target scene before the unresolved fidelity gate:
  `build/room55-damage19-run1/`, ROM SHA-256
  `f55281926afa113bb041983c72fa4beaf6085a0421e51c450cb352a9095d82bb`;
  semantic controller result PASS, native scene generated, exact actor crop
  NOT PASS. Diagnostic run 17 records the same pre-publication samples.

- Explicit FULL corpus is authoritative: `/home/chad/ATLANTIS.zip`; DEMO is
  only a negative control. Do not let `fatedemo-box.zip` substitute silently.
- Current bounded-damage ROM: `build/room55-damage6.sfc`, SHA-256
  `1c06c3d2f4fb5beeade6da139fc7c379f1363300b202eb280d966326a56e62b3`.
- Build used `SAME_FATE_DEMO_ARCHIVE=/home/chad/ATLANTIS.zip`, the Fate profile,
  `SAME_M25A_VALIDATOR_CASE=startup42`, scenario fixture/start room 42,
  `sa1_bwram` + `mode3_surface` + `bg2_index4`, ROM size `0x0C`, and the
  generated room manifest under `build/m25a-validator/startup42/room42/`.
- Service-progress diagnosis is closed: the S-CPU reaches `WAI` in the main
  loop while NMI/frame activity continues; `Same_Frame_Run`, event drain/pop,
  and backend steps all advance. The earlier five “queued events” were stale
  packet slots; the live FIFO drains to count zero. The first producer fault
  was `Same_VideoSurface_FindVisual` failing to reload the requested room key
  after failed-record arithmetic; the generic room-key reload fix is retained.
- Kernel drain/pop counters and live FIFO decoding are now diagnostic-only;
  `SAME_ENGINE_FRAME_BUSY` plus logical/NMI counters distinguish main service
  from NMI-only activity. Do not overlap SCUMM state.
- Corrected target capture `build/service-progress-findfix-capture3/` proves
  service progress: NMI `19188`, logical frames `1765`, kernel drain entries
  `3271`, successful FIFO pops `13`, backend steps `545`; backend state idle,
  lock clear, accepted PRESENT `2`, rejected PRESENT `1`, live FIFO
  head=tail=`13`, count `0`. The earlier apparent five events were stale
  packet-buffer bytes, not queued records. Room 42 PRESENT is now genuinely
  accepted and drained.
- Corrected ROM `build/service-progress-findfix.sfc` SHA-256
  `c8018b33e4dc0eca2cf8846bc9f5fa9a438f73c4a566b900d6571fc92226c49e`.
- Focused host validation: `PYTHONPATH=src python3 -m unittest
  tests.test_scumm_v5_room_visual tests.test_m25a_validator -q` => 15/15.
- Full-compose before measurement: 256x224 dirty coverage (896 candidate
  tiles) per actor redraw; the prior trace recorded roughly 515 full compose
  calls. Bounded actor redraw now restores/presents one clipped pixel union.
- Current target run `build/room55-damage6-run6/` is PASS semantically and
  reaches a natural intermediate walk state `(x=200,y=101,moving=10,
  walkbox=10)` before the locker destination `(218,104)`. Its bound snapshot
  records one committed generation, empty FIFO, backend idle/unlocked, and a
  clipped damage rectangle `x=0,y=0,w=82,h=64`; native walking differs from
  the opened frame. The matching no-advance indexed-surface capture is
  `03-walking-surface.ppm` (SHA-256
  `2aaabd8be1d17a0ad255895e64ef6f9723cad9ecf683ed01a5359da20b99a89b`); the
  native walking PNG is SHA-256
  `a1c5fcacfe256549051cc4391d8ff4e5df76c2564ac0ea50a9620bfb686c3374`.
  The complete scene remains error-free.
- Run-6 target command: `PYTHONPATH=src python3 -u
  tools/validate_scumm_room42_controller_nexen.py --rom
  build/room55-damage6.sfc --nexen
  /mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/mcp-exact-publish/Nexen
  --port 44521 --startup-frames 4096 --output
  build/room55-damage6-run6`.
- Target-side service binding is now captured by the validator at the walking
  boundary (`walking_presentation`); the diagnostic reader uses the generated
  backend offsets for pending/committed generation and tile counts. Remaining
  acceptance work is exact indexed-surface/native crop conformance and the
  focused restore-retry target regression, not startup corpus selection.

> UPDATE THIS FILE AT EVERY MEANINGFUL MILESTONE OR BEFORE A LONG/RISKY DEBUGGING PASS.

> **STOP-GATE:** Do not end work for an intermediate diagnostic, build,
> validator result, tooling change, or player choice.  A final response is
> permitted only after the active objective is complete, a source-backed major
> blocker is proven, or the user explicitly requests a status-only stop.  See
> `AGENTS.md`.

## Corpus/configuration audit (2026-09-07)

- FULL corpus is `/home/chad/ATLANTIS.zip`: archive SHA-256
  `0f3fc396642c800069d31ab9a087b314f1bb1612d37accbe13b6013219ac94f0`;
  `.000` `72913003d61fffaa614795f12b33d9f2ef3bdcebb155cc5a53fc93b88e57c3bb`;
  `.001` `8381ba5a2eee3ed887a42d63794f7c6f1b4bbf809c928a4223f95ee3646a7baf`.
- DEMO is `/home/chad/fatedemo-box.zip`: archive SHA-256
  `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`;
  `.000` `4e277158329edab802619ea3ef91c3f6ecec04f3fab6b67f44d275fc5f9b65a9`;
  `.001` `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240`.
- Recovered accepted-style env: `SAME_FATE_DEMO_ARCHIVE=/home/chad/ATLANTIS.zip`,
  `SAME_SNES_PROFILE=examples/profiles/templates/fate_of_atlantis_demo.json`,
  `SAME_M25A_VALIDATOR_CASE=startup42`,
  `SAME_BUILD_SCUMM_SCENARIO_FIXTURE=1`,
  `SAME_SCUMM_SCENARIO_START_ROOM=42`, `SAME_SNES_ENGINE=scumm_v5`,
  `SAME_SNES_CARRIER=sa1_bwram`, `SAME_SNES_VIDEO_BACKEND=mode3_surface`,
  `SAME_SNES_VIDEO_OVERLAY=bg2_index4`, M24RB/M23A/M23B/M23C/PHASE6L_A1D/
  M25A/M25_MOVEMENT/ROOM_VISUAL/CONTROLLER_FIXTURE all `=1`, and
  `SAME_SNES_ROM_SIZE_CODE=0x0C`; room visual manifest is
  `build/m25a-validator/startup42/room42/manifest.json`.
- Full-corpus room manifest source fields match both FULL member hashes;
  main-tree SHA is `9b07e3d06ac98f2a03e66c129feadbb90c25129992872f043935f4220dc95468`.
  M25A now records `selected_corpus` and writes `corpus_identity.json` before
  resource resolution, including on a negative build.
- Full-corpus isolated rebuild: ROM
  `18cc43b26f79aefa143ea4a3e13f84fb0f7ca0d259142c813209ca037d6b0d14`,
  reaches room 42/error 0 but current video service does not accept initial
  PRESENT. This is not damage-path acceptance evidence. The DEMO control
  identifies PLAYFATE then fails on missing full-cone `script.57`, proving no
  silent substitution. The old `0fa66db...` artifact lacks a complete env dump
  and remains historical evidence only; details: `docs/corpus_config_audit_20260907.md`.
- Target-testing the generic deferred initial-publication path retains the
  room-42 request (`pending_visual=2`, generation 1), but backend state remains
  locked with five queued events and no accepted PRESENT through 4096 frames;
  bounded damage remains unjudged.

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

## Poppy #376 closure and current moving-presentation frontier (2026-09-08)

- Poppy issue `TheAnsarya/poppy#376` is closed for SAME. Fixed commit:
  `8ee859b33bad94e3a01e9c78026803e482292801`. Pinned DLL SHA-256:
  `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`.
  Clean focused upstream review is Poppy PR #393; polluted PR #392 was
  superseded. Do not blame Poppy again without new evidence.
- Explicit FULL startup42 uses `SAME_FATE_DEMO_ARCHIVE=/home/chad/ATLANTIS.zip`,
  `SAME_M25A_VALIDATOR_CASE=startup42`, `SAME_SCUMM_SCENARIO_START_ROOM=42`,
  `SAME_SNES_CARRIER=sa1_bwram`, `SAME_SNES_VIDEO_BACKEND=mode3_surface`,
  and controller witness flags.
- `build/poppy-fixed-startup42-actorabi6-facing90.sfc` SHA-256:
  `21a61986407b4cf42d44887533f77f316ef68d0a4c85d9f1bc4e6bcfe954c5d6`.
  Run `build/poppy-fixed-actorabi6-facing90-run1/` proved moving actor
  `(157,101)`, moving `1`, destination `218`, pose `1`, damage
  `(65,86,32,64)`, PRESENT 3 committed as generation 3, idle/unlocked with
  empty FIFO; the full locker/dialogue replay passed with error `0`.
- Dirty cooker fix: `tools/generate_snes_scumm_actor_sprite.py` now traverses
  BYLE cels column-major, applies directional placement, and accepts explicit
  `--facing`; the FULL room-42 fixture uses facing `90`. Asymmetric executable
  tests cover column order and facing selection.
- Dirty surface fix: `RestoreRect` used `row*3` for five-byte room-visual row
  descriptors, while full projection uses `row*5`. It now uses `row*5`; the
  old behavior caused wrong-row bytes and horizontal background stripes.
- Rebuild after restore fix:
  `build/poppy-fixed-startup42-actorabi7-restorefix.sfc` SHA-256
  `9370b4acb6ff649b008c5e4135771b24dc89fb74be798e5bfbc2cbda7aa8702f`;
  build identity SHA-256
  `3b2678c61632ca3b90fe2e0f52088da25d10d28c9c73466f191c2125ee698b5e`.
  Poppy lint and ROM audit pass. The fresh target rerun completed in
  `build/poppy-fixed-actorabi7-restorefix-run3/`; report result is `pass` and
  its ROM SHA matches the build above.
- Event-driven moving witness is proven: actor `(157,101)`, moving `1`,
  destination `(218,104)`, pose `1`, damage `(65,86,32,64)`, PRESENT
  generation `3`; the matching backend commit witness reports committed
  generation `3`, idle/unlocked, FIFO empty. The later `walking_presentation`
  snapshot is deliberately not used as the semantic moving-state capture;
  it records the already-committed generation after movement advanced.
- The committed indexed crop is `03-walking-surface.indexed.bin`, region
  `(65,86,32,58)`. Against emitted pose 1 (503 non-transparent pixels),
  481 pixels match exactly and 22 are occupied by legitimate overlapping
  room/cursor/object pixels in the crop; the crop and native capture were
  bound to PRESENT/commit generation 3. `03-walking.png` was opened and
  shows recognizable Indy in the harbor with no former horizontal stripe
  corruption. `04-dialogue-active.png` was opened and shows readable active
  authored dialogue.
- The full normal controller replay passes: locker opens at `(218,104)` in
  walkbox 10, object 490 changes `0 -> 1`, inspection dialogue starts and
  completes, post-dialogue input remains usable, and error is `0`.
- Focused cooker tests, Poppy lint, ROM audit, and `git diff --check` pass.
  The prior actorabi6 run remains a semantic/presentation comparison; the
  actorabi7 run is the current restore-fix evidence. Do not reopen Poppy,
  cooker, Mode3, or RestoreRect without contradictory evidence.

## Room-42 surface/controller milestone — CLOSED (2026-09-08)

- Corpus ambiguity: CLOSED. FULL is `/home/chad/ATLANTIS.zip`; member hashes
  are recorded in the build identity.
- Poppy #376 sizing defect: CLOSED/PINNED. Issue `TheAnsarya/poppy#376`,
  focused PR #393, commit `8ee859b33bad94e3a01e9c78026803e482292801`, DLL
  SHA-256 `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`.
- Cooker column-major/directional defect: CLOSED. SAME actor pose 1 emitted
  bytes match the independent host pose; asymmetric cooker tests remain.
- SAME architecture leak, FindVisual defect, bounded restore retry defect,
  and visual snapshot/cache ordering defect: CLOSED with regressions.
- Accepted ROM: `build/poppy-fixed-startup42-actorabi7-restorefix.sfc`,
  SHA-256 `9370b4acb6ff649b008c5e4135771b24dc89fb74be798e5bfbc2cbda7aa8702f`.
  Build identity SHA-256:
  `3b2678c61632ca3b90fe2e0f52088da25d10d28c9c73466f191c2125ee698b5e`.
- Natural moving PRESENT: actor `(157,101)`, moving, destination `(218,104)`,
  pose 1, damage `(65,86,32,64)`, PRESENT generation 3 committed as
  generation 3, backend idle/unlocked, FIFO empty. Indexed accounting:
  503 emitted nontransparent pixels, 481 exact captured matches, 22
  documented overlap pixels, 0 unexplained pixels.
- Full controller/dialogue result: actor reaches `(218,104)`/walkbox 10;
  object 490 changes `0 -> 1`; inspection dialogue starts/completes; input
  remains usable; error `0`.
- Final validation: `PYTHONPATH=src python3 -m unittest discover -s tests -q`
  = 525/525; Python compilation, `git diff --check`, Poppy lint, and
  `audit_snes_rom.py --carrier sa1_bwram` pass. Explicit FULL startup42
  replay: `build/poppy-fixed-actorabi7-final-run/`, result `pass`.
- Final review publication is screened separately from dirty main. ROMs,
  savestates, ATLANTIS.zip, generated game payloads, and unrelated campaign
  files remain local. Next goal is generic source-driven cursor/object/verb
  selection; do not continue room-42-specific graphics work.

## Generic action lifecycle / runtime HUD (WIP, 2026-09-08)

- Accepted generic hit testing/verb discovery remains published at
  `review/controller-room42-generic`, commit
  `f0f945509c81a00e32c8eb745af1e6b136d6be34`; do not reopen it absent a
  regression.
- Current implementation removes the active Open→state→Inspect transition:
  ACTION_PENDING waits on sentence mailbox, C20, talk ownership, C19, and
  actor movement, then re-runs source hit testing and authored-verb discovery.
  It does not inspect object state to release input.
- HUD construction now reads runtime C17 verb names and `$54 setObjectName`
  encoded object-name bytes; old proof-scene prompt payloads are blank/dead and
  must not return to the production path.
- Host/focused tests: 218 relevant tests PASS. Latest target build after the
  safe object-name-table clear fix:
  `build/generic-action-lifecycle3.sfc`, SHA-256
  `762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`.
  FULL startup42 semantic smoke: room 42, actor room 42, error 0 at frame
  2402. Poppy DLL remains the pinned #376 fix above.
- A validator-only `--skip-visual-ready` mode exists for semantic diagnostics;
  it is not visual acceptance. The normal controller run currently stalls at
  the pre-existing room-surface/backend gate: room-visual state remains room
  68 with `pending_visual=2`, backend locked, and live surface events before
  room-42 input is consumed. Do not call this a controller lifecycle pass or
  change video code under this goal without a separately demonstrated cause.
- Reproduced on `762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`:
  the strict controller replay fails before input at the same visual gate;
  the semantic-only replay then shows the controller cannot consume cursor
  edges while the initial backend conversion remains locked. This is a
  concrete presentation-service/mainline blocker, not evidence against the
  generic sentence lifecycle. No video implementation was changed for it.
- A temporary attempted `StoreObjectNameByte` PHP/PHX preservation change was
  reverted after target smoke produced SCUMM error 2; retain the proven caller
  behavior until its ABI is independently established. The byte-width boot
  clear remains and target-smoke passes.
- Validator correction: Open submits the source-first authored verb; Y is used
  only after generic action release to select the state-neutral authored verb.
- Coherent-frame diagnostic added to
  `tools/validate_scumm_startup42_nexen.py` (`--coherent-frame-trace`); it
  samples only after `run_frames` completes, and records live FIFO head plus
  DMA counters. `--trace-video-writers` records symbol-derived backend
  routine boundaries without changing production state.
- Binary A-control: `build/generic-room42-interaction-fixedpoppy23.sfc`,
  SHA-256
  `b97fe25e4d7795004610ff1d6e171fe9e1758b94f319c3739c317e808d26547d`.
  The current strict controller validator passes its room-42 visual gate and
  reaches normal Open/movement; its later moving-PRESENT commit failure is a
  separate post-input observation/runtime frontier.
- Binary B: `build/generic-action-lifecycle3.sfc`, SHA-256
  `762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`.
  Its strict run fails before controller input at the room-visual gate.
- First coherent A/B divergence: B accepts a room-68 PRESENT while room 68
  is still in its authored lifecycle (coherent frame 111: backend state
  CONVERTING, lock=1, accepted_present=1), then installs room 42 while that
  presentation remains in flight (frame 224: room 42 phase 2,
  `pending_visual=2`, live FIFO head is video opcode 2). A reaches room 42
  first and does not accept its first PRESENT until after the room-42 install;
  A reaches room 42 phase 0 with error 0 and an empty live FIFO. Thus the
  current failure is not produced by the validator merely sampling
  `IDLE+locked=1`; it is a pre-input presentation/lifecycle ordering
  difference in B, with room-68 presentation ownership blocking the room-42
  request.
- At completed-frame boundaries, B's backend remains CONVERTING/locked (not
  IDLE/locked) after the accepted room-68 PRESENT; no stable `IDLE+locked=1`
  violation was observed. The accepted-PRESENT writer boundary is
  `Same_Mode3_HandlePresent__accept` at bank `$0F:$83BA`; the normal completion
  boundary is `Same_Mode3_Step__complete` at `$0F:$81E7`. B's writer trace
  observed the former at frame 110 with state=CONVERTING, lock=1,
  accepted=1, pending generation 1, committed generation 0; no completion
  writer was observed before the room-42 stall. Source writers are only the
  accepted-PRESENT lock store and the completion unlock store in
  `runtime/snes/services/video_mode3.pasm`.
- A/B trace artifacts: `build/coherent-b97/report.json`,
  `build/coherent-762/report.json`, and `build/writers-762b/report.json`.
  These are local diagnostic artifacts, not publication evidence.
- Provenance caveat: the accepted b97 binary's identity records explicit
  `SAME_SCUMM_SCENARIO_START_ROOM=42`, while current startup42 builds default
  to authored room 68. Therefore b97 is a valid binary A-control for the
  validator contract, but not a like-for-like source/configuration baseline;
  this configuration difference must be kept separate from the production
  B divergence. Do not rebuild or relabel b97 as startup42.
- Immediate next step: reproduce the B failure with a same-source explicit
  startup42 matrix (mask families A/B/C/D/E) or prove the first family that
  changes room-68 PRESENT ordering. Do not change video code, force-unlock,
  drop FIFO entries, or weaken ACTION_PENDING until that bisect is complete.
- Same-source behavior-mask matrix completed with the authored room-68 root;
  all five local ROMs reproduce the same pre-input shape:
  `mask0=cfa1b1312d2f1280a20c933dc608de89c1da041ad4484d3f7b86fb274b211dc3`,
  `mask1=5e167d6ef3329743afe4410e97d19243ce5ad32ba8fcc06e97517420218e8e45`,
  `mask2=26e60c2af7c4a3810b2c14b7d782a9d06920a44f47ded0b15ffe7be56e7d8fe9`,
  `mask4=4e3af2a5e6a10d517ae8ac761aa9330736e0784b2d8970b8e058bc76992a319`,
  `mask7=762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`.
  Every run reached room 42/error 0 but remained phase 2 at the 260-frame
  sample; the first relevant coherent sample was room 68 phase 2 with
  `pending_visual=2`, backend CONVERTING, lock=1. Therefore none of the
  pose-cache, failed-PRESENT commit, or post-controller ordering mask bits is
  the first cause of this startup failure.
- The candidate's coherent scheduler trace identifies the current boundary
  more precisely: after room 42 installation, `engine_frame_busy` remains 1,
  `frame_entry_count` remains 57, backend step count remains 2, and the live
  FIFO head remains video opcode 2 while NMI continues. The S-CPU samples at
  `$00:80E2/$00:80E3` are the NMI handler, so they are not evidence that the
  CPU is executing the backend; the main logical-frame path is stalled in the
  SCUMM startup work. Program 145 runs through changing PCs/locals before
  retiring to script 208, but the room phase remains 2. This is a mainline/
  authored-startup execution stall with the video lock as a downstream
  symptom, not a proven backend lock invariant.

### 2026-09-09 coherent-frame classification update

- The completed-frame A/B comparison confirms the accepted binary is not
  rejected by the current readiness contract. Its `IDLE+locked` observation
  occurs at a coherent frame while the accepted PRESENT conversion is still
  legitimately in flight; it is not evidence of a stable invariant failure.
- The current B failure is not a validator-created `IDLE+locked` diagnosis.
  In the original candidate, the first concrete production error was
  `SCUMM_ERR_VARIABLE=2`, recorded as program 223 / PC `$008E` / opcode
  `$0A`, followed by a stalled main-frame path. NMI continued while
  `SAME_SCUMM_FRAME_ENTRY_COUNT` stopped and backend steps stopped; the live
  FIFO remained authoritative and was not classified from stale slots.
- Static layout audit found the first demonstrated generic corruption:
  `SAME_SCUMM_OBJECT_NAMES=$7E9000` with `2048*$20` bytes overlapped the C17
  verb table beginning at `$7F6F20`. This explains the variable error as a
  runtime-state alias, not a backend defect. Fixed locally by bounding the
  target-neutral name cache to 1024 records, ending at `$7F1000`, and making
  authored names outside that presentation cache decode/consume without
  writing runtime state. Added the explicit end/count contract in
  `runtime/snes/kernel/memory.pasm` and guarded both storage and length commit.
- Rebuilt with FULL ATLANTIS and pinned Poppy DLL SHA
  `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`:
  `build/generic-action-lifecycle3-namecache.sfc`, SHA-256
  `ddd1d4e7ecb43172bedd381547a5cdbc6542e925c8facea3fbbdd61a87b0c8d9`.
  Poppy lint and ROM audit pass. The target reaches room 42 with error 0,
  but still stalls in the authored startup work before room-42 visual
  publication; that is a separate remaining mainline execution defect.
- New evidence for that remaining stall: at the completed-frame boundary,
  room 42/error 0, `engine_frame_busy=1`, `frame_entry_count=3`,
  `backend_step_count=2`, `pending_visual=2`, backend state is converting,
  and the live video FIFO is nonempty. The CPU remains live under NMI, but
  the SCUMM logical frame does not complete. The name-cache alias is fixed;
  do not reinterpret this later mainline stall as an `IDLE+locked` backend
  invariant or alter video code before mapping its control-flow boundary.
- Trace artifacts: `build/coherent-namecache/report.json`,
  `build/stall-namecache/report.json`, and
  `build/controller-namecache-skip/` (local diagnostics only).
- The first stalled PC after the name-cache fix was mapped to the generic
  surface service: bank `$14:$8125-$8129`,
  `Same_VideoSurface_Clear__loop`. It was a full `$E000`-byte indexed-surface
  clear performed byte-at-a-time, monopolizing the logical frame while NMI
  continued. This was a service-side execution-cost defect, not a stable
  backend lock/FIFO invariant. The local generic fix clears two pixels per
  iteration under `PHP/PLP`, preserving caller P/A width; focused tests cover
  the word-bounded loop.
- Rebuilt after both fixes with pinned Poppy:
  `build/generic-action-lifecycle3-namecache2.sfc`, SHA-256
  `e86677e0a65673fc5493d1658ae39246844b59c203788d9c552452bf04ac8f22`.
  Poppy lint and ROM audit pass. The clear no longer dominates the trace;
  the remaining completed-frame trace reaches room 42/error 0 but remains in
  authored startup/scheduler work with a live video FIFO and
  `engine_frame_busy=1`. The current CPU trace is now in the generated
  program-size resolver (`$5B:91xx`), so the next boundary is scheduler/script
  execution, not surface clearing or backend conversion.

### 2026-09-09 completed-frame A/B and projection-service localization

- Accepted binary A control `build/generic-room42-interaction-fixedpoppy23.sfc`
  (`b97fe25e4d7795004610ff1d6e171fe9e1758b94f319c3739c317e808d26547`)
  passes the current controller readiness path. Its binary is the direct
  room-42 control; it is not being treated as an equivalent authored
  68→75→1→42 source build.
- Candidate B remains `762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`.
  The strict validator rejects B before controller input, while the accepted
  A control passes. The coherent boundary is not a stable backend-lock fault:
  A reaches room-42 with pending visual 0/live FIFO 0; B reaches room-42 with
  pending visual 2, pending room 42/generation 2, one live video packet, and
  no accepted PRESENT yet.
- The logical-frame fence is installed at `Same_Main_Loop` re-entry, after
  `Same_Frame_Run` returns. It proves NMI/frame-counter advancement is not
  equivalent to completed S-CPU logical frames. B's first post-room-42 fence
  does not return while the CPU remains live in SCUMM startup/scheduler work;
  the validator is not classifying a PRESENT-handler interior snapshot.
- `IDLE + surface_locked=1` is retained as a legitimate accepted-PRESENT
  intermediate observation. The coherent traces used here do not promote it
  to a stable invariant violation.
- First service-side stall was `Same_VideoSurface_Clear__loop`, a full
  `$E000`-byte clear. The generic `ClearForProjection` path now skips that
  clear only for a full 256×224 projection and retains it for clipped rooms.
- The next trace reached `Same_VideoSurface_BlitProjection`. Its original
  byte/M-width-switch loop was still too expensive. The current generic
  service copy uses A16/X16/Y16 bank-safe pairs, an eight-pair unroll, an
  explicit bounded remainder, and a zero-count guard. The zero guard prevents
  a zero remainder from underflowing to `$FFFF`; no SCUMM/backend semantics
  were changed.
- Latest rebuilt candidate after the projection fixes:
  `build/generic-action-lifecycle3-namecache4.sfc`, SHA-256
  `3d43f44d113d627cf4996fbf826620a7abf630e835430c6e7442adf7b3dd1b8f`.
  Build used FULL ATLANTIS, pinned Poppy DLL SHA
  `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`;
  Poppy lint and SA-1/BW-RAM ROM audit pass. Target traces now get past the
  redundant clear and projection-copy bottlenecks, but B still has not yet
  reached room-42 visual publication; the remaining first-live boundary is
  SCUMM/M23A scheduler execution, with the live video packet downstream.
- Local trace artifacts: `build/logical-b97/`,
  `build/logical-namecache4c/`, `build/trace-stall-namecache4c/`.

### 2026-09-09 accepted-ROM A/B readiness classification (current)

- A control: `build/generic-room42-interaction-fixedpoppy23.sfc`, SHA-256
  `b97fe25e4d7795004610ff1d6e171fe9e1758b94f319c3739c317e808d26547`.
  A read-only natural-frame run reaches room 42, room phase 0, readiness 1,
  actor room 42, and error 0. This remains a direct-room control, not an
  equivalent full authored 68→75→1→42 build.
- B candidate: `build/action-matrix-mask7.sfc`, SHA-256
  `762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`.
  Its natural no-screenshot run reaches room 68, then room 42, but remains
  room phase 2/readiness 0 through frame 502 with error 0. This is not merely
  a strict-readiness polling artifact: the ordinary frame-advance control also
  fails to reach the accepted semantic boundary.
- The first valid completed-frame boundary in B is frame 223: room 68 phase 5,
  pending visual 2, pending room 42/generation 2, accepted PRESENT 1,
  pending generation 1, committed generation 0, backend state CONVERTING,
  surface lock 1, live FIFO count 0 at that instant. Later the authored room
  lifecycle publishes room 42 but remains phase 2. NMI/frame counter activity
  is not being mistaken for completed logical frames.
- A current natural run reaches room-phase 0/readiness 1 at about frame 322;
  B remains phase 2. The A/B startup configurations are not identical (A is
  direct room-42), so this is a control classification, not a causal bisect.
- Accepted-PRESENT writer evidence from `build/writers-b-762/report.json`:
  `surface_locked=1` is written first, then `state=CONVERTING`; after both
  stores the observed state is 2/locked 1, accepted 1, pending 1, committed
  0. No stable IDLE+locked state was established. IDLE+locked remains a
  legitimate transient if sampled between the two accepted-handler stores.
- Correct bank-qualified service tracing shows the first live B control-flow
  boundary after room 42 is SCUMM scheduler execution, not Mode3 dirty handling:
  `Same_Frame_Run` → `Same_Engine_Frame` → `Same_ActiveEngine_Frame` →
  `ScummV5_Engine_Frame__m23a_room_runnable` → `ScummV5_Engine_RunSelected`.
  A nested child is entered with slot 2/program 252 (room 42 lifecycle state);
  no nested-success/return or later frame boundary is observed in the failing
  run. The video lock is downstream and not yet a proven backend invariant.
- Validator tooling correction: map symbols are bank-local. Kernel/frame hooks
  are bank 0; generated Mode3/surface hooks are bank `$0F`. Earlier unqualified
  service hooks observed unrelated bank-0 bytes and are retired. The current
  WAI/loop fence records only hook-fired completed-frame boundaries and does
  not label per-NMI polling snapshots as coherent. Local outputs:
  `build/natural-a-b97/`, `build/natural-b-762/`, `build/frameboundary3-a-b97/`,
  `build/frameboundary3-b-762/`, `build/service5-b-762/`,
  `build/service9-b-762/`.
- Remaining exact boundary: identify why B's room-42 SCUMM nested-child path
  does not return to the completed frame/phase-0 lifecycle. Do not alter
  backend lock state, drop FIFO packets, weaken readiness, or reopen the
  accepted PRESENT transient theory.
### 2026-09-09 current validator A/B lock classification

- Current task: classify the pre-input room-68/presentation readiness failure;
  do not change production video, ACTION_PENDING, or C17 behavior until the
  observation/configuration cause is isolated.
- Accepted binary control:
  `build/generic-room42-interaction-fixedpoppy23.sfc`, SHA-256
  `b97fe25e4d7795004610ff1d6e171fe9e1758b94f319c3739c317e808d26547d`.
- Candidate:
  `build/action-matrix-mask7.sfc`, SHA-256
  `762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`.
- Both were run with the current validator's logical-frame/coherent-frame
  tracing and `--trace-video-writers`; no production source was changed in
  this pass.
- Proven observation contract: `Same_Main_Loop` re-entry is the completed
  logical-frame fence. PRESENT/FIFO/backend hooks are event diagnostics only.
- Lock writer evidence on B: accepted PRESENT is followed by
  `surface_locked=1`, then backend `state=CONVERTING (2)` in separate writes.
  The clean completed-frame sample is `room 68, phase 5, pending_visual=0,
  pending_room=68, accepted_present=1, pending_generation=1,
  committed_generation=0, state=2, locked=1, FIFO count=0`.
  No coherent-frame sample proves stable `IDLE + locked=1`; treat that state
  as a possible interior observation only.
- Configuration mismatch prevents causal A/B attribution: A identity has
  explicit `SAME_SCUMM_SCENARIO_START_ROOM=42` and
  `SAME_SCUMM_CONTROLLER_WITNESS=1`; B has no explicit start-room variable
  (so startup42 defaults to room 68) and adds
  `SAME_SCUMM_SCENARIO_CLASS_OVERLAY=491:0x2f` plus
  `SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE=1`. Both use FULL ATLANTIS and the
  same Poppy DLL hash, but their build-config and room-visual hashes differ.
- Current natural runs: the ordinary no-extra-hook A control reaches room 42,
  phase 0/readiness 1/error 0 (`build/natural-a-b97/`); a traced A run can
  perturb timing and later sample phase 2, so that instrumented result is not
  the A readiness result. B reaches room 68 phase 5 at the first clean
  boundary and later room 42 phase 2/error 0, with the selected child program
  252 cycling at PCs 95,28,35,40,53,60,65,92 and not returning from the
  nested runner during the observed run. The ordinary B no-screenshot control
  reproduces the failure, so this is not solely a strict-readiness polling
  artifact. It is not yet a backend invariant diagnosis.
- Next: reconstruct/run the exact accepted startup42 configuration as a
  binary control (or document that the accepted A is direct-room42 only),
  then compare completed-frame snapshots. Keep the current validator's
  frame-boundary fence and live FIFO decoding; do not gate title input on
  pending visual/FIFO/backend state.

### 2026-09-09 room42 ENCD/frame-boundary reconciliation (latest)

- Presentation branch remains CLOSED for this blocker. No video/backend/
  overlay change is justified.
- Binary pair used:
  - GOOD `build/generic-room42-interaction-fixedpoppy.sfc`, SHA-256
    `b97fe25e4d7795004610ff1d6e171fe9e1758b94f319c3739c317e808d26547d`.
  - BAD no-overlay `build/room68-no-overlays-v2.sfc`, SHA-256
    `e7eb9483774770b62f0c0fdac2b2bddcb3204eeebbe00e2966fc6de3d046153e`.
- The original batched/readiness observation can leave BAD at room 42,
  phase 2, error 0, readiness 0, with NMIs alive. A completed-frame trace
  (logical `Same_Main_Loop` fence, one frame at a time) makes the same BAD
  binary execute the room-42 lifecycle normally; therefore the earlier
  phase-2 frontier is not yet proof of a production ENCD deadlock.
- Completed-frame traces:
  - GOOD: room68 phase5 at frame124; room42 phase2 at frame310, then phase0
    at frame313; `engine_phase=3` at every logical-frame snapshot.
  - BAD: room68 phase5 at frame189; room42 phase2 at frame322, then phase0
    at frame325; `engine_phase=3` at every captured logical-frame snapshot.
  - Thus `Same_Engine_Frame` entry/return is proven for both under the
    coherent fence. The earlier BAD run's `engine_phase=2` was an interior /
    timing-sensitive observation, not a stable completed-frame state.
- Room-42 ENCD opcode trace (both binaries, same source/cooked room bytes):
  program 223 follows the same ordered PCs through terminal fetch convention
  `$0087 -> $008A` (reported snapshot PC `$008A`, opcode `$0A`), then both
  reach program 226. No first divergent ENCD opcode or input state is
  demonstrated. The BAD trace's later program-252 cycling is downstream of
  the same terminal and disappears when observations are fenced coherently.
- Lifecycle rings at the coherent runs:
  - GOOD reaches room42 codes `1,2,4,5,6,7,8,9`, then phase0; the room42
    entry completion is not missing.
  - BAD reaches `1,2,4,5,6,7,8,9,10`, then phase0 under the coherent run.
    The extra trace-10 record is diagnostic ring history, not a failed ENCD
    completion once phase0 is observed.
- Live scheduler at room42 phase2 boundary in both: current program 223,
  reported PC `$008A`, opcode `$0A`; non-stopped child slot 1 is number 208,
  program 226, PC 7, status 2. The room-script slot is represented by the
  shared interpreter/active-record fields, not by the filtered non-stopped
  slot list.
- CPU failure evidence from the earlier un-fenced BAD trace is retained only
  as a historical observation witness: after a valid bank-0/resource trace,
  repeated `RTI` at `$00:8148` resumed into bank `$67` and executed BRK. That
  run did not capture a coherent pre-event stack, and the later 30k trace
  was timing-perturbed; it is not sufficient to identify a production bad
  return. Do not patch reset/RTI/ENCD on this evidence.
- Validator-only diagnostic change in this pass: `--exact-exec-stop` accepts
  a bank-base (e.g. `0x670000`) as a range probe; no ROM was rebuilt and no
  production runtime state/layout changed. The probe was not accepted as
  causal evidence because it altered timing and did not yield a stable
  first-transfer capture.
- Relevant commands:
  `PYTHONPATH=src python3 tools/validate_scumm_startup42_nexen.py --rom
  build/room68-no-overlays-v2.sfc --output build/frame-boundary-bad --frames
  330 --light --minimal-observation --logical-frame-trace
  --coherent-frame-trace`
  and the same command with `build/generic-room42-interaction-fixedpoppy.sfc`
  and output `build/frame-boundary-good`.
- Current conclusion: no source/runtime fix is justified yet. The next pass
  must reproduce the original stable BAD frontier with a coherent frame
  boundary or classify the validator's batching/readiness gate as the defect;
  only then trace a production first divergence. Do not change video,
  ACTION_PENDING, C17, scheduler retirement, or room logic speculatively.
## 2026-09-09 — generic-interaction baseline relabel and validator fence

- Accepted binary labels: `b97fe25e...` is the generic-interaction baseline;
  `e7eb948...` is the no-overlay control, not a production “BAD” result.
  Any older BAD wording for e7eb is historical validator terminology only.
- Closed evidence: both runs execute room-42 ENCD program 223 through terminal
  fetch `$0087 -> $008A`, opcode `$0A`; at a completed logical-frame boundary
  `Same_Engine_Frame` returns, M23A reaches phase 0, readiness is true, and
  error is 0. No ENCD, scheduler, video, overlay, backend, or reset change is
  justified by that comparison.
- Current candidate: `762a424541291380b16c525aea0b2689394e2401e44904758ab3f86b47b95117`.
  Generic interaction is the active goal: ACTION_PENDING must release by the
  canonical SCUMM lifecycle for both state-changing and state-neutral actions;
  C17 HUD text must come from runtime/source object and verb data.
- Validator correction implemented for post-startup semantic/presentation
  polling: completed `Same_Main_Loop` re-entry is authoritative, and the
  semantic poller rejects an uninstalled fence instead of falling back to
  arbitrary frame batches. Focused controller/validator tests pass (48/48;
  broader selected host set 210/210). Startup observations remain the normal
  completed emulator-frame control; the execution fence is installed before
  controller interaction so input transactions are not interrupted.
- Candidate-run provenance correction: `762a...` is an older authored
  room-68-root artifact and is not a valid proof of the generic controller
  path by itself. A target attempt reached room 42 and the source CDHD table,
  but did not complete the interaction proof. Rebuilding the equivalent
  explicit room-42 artifact is pending the exact recorded Poppy DLL; the
  clean local Poppy source is at `ec005c1` but its rebuilt DLL hash is
  `715b1443...`, not the pinned `34514923...`, so the build guard correctly
  refuses to treat it as the accepted toolchain.

## 2026-09-09 — generation-aware quiescence and generic verb-cycle proof

- `SAME_VIDEO_SURFACE_PRESENTED_GENERATION` has no production writer. It is
  diagnostic bookkeeping only and is not a readiness predicate. Quiescence
  uses room/readiness, pending visual state, NEXT/backend pending/committed
  generation equality, idle/unlocked backend, live FIFO surface-packet
  inspection, and stability across one completed logical frame.
- Initial and post-cursor quiescence passed on the accepted baseline and the
  current candidate. Conversion progress was observed through candidate and
  scan/conversion counters; the validator no longer mistakes in-flight work
  for a deadlock.
- Exact production bug found in generated `ScummV5_Generic_Verb_Next_Far`:
  after matching the current authored verb it set `VERB_AFTER=1` and fell
  through directly to that entry's return label, returning the current verb
  again. The generator now branches to the next-entry scan label after
  arming the cycle. This is generic; no room/object special case was added.
- Target ROM rebuilt with the recovered historical SAME-compatible Poppy DLL
  (`34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`):
  `build/generic-action-lifecycle3-verbcycle.sfc`, SHA-256
  `94a6a6e623afc4a8778da99c2cc0bdd90ad7532aea08c344e7890462f822b056`.
- Target run `build/verbcycle-r4/` passed: FULL ATLANTIS room42 readiness/
  error0; source CDHD hit selects object 490; authored verb 3/Open submits,
  moves to `(218,104)`, and changes object 490 state `0 -> 1`; ACTION_PENDING
  releases. Y then selects authored verb 4 (not inferred Inspect policy),
  submits a second normal sentence, and returns to generic selection with
  object state still 1 and error 0. A source-derived hit then selects object
  492 and its authored verb set, proving generic re-entry. No dialogue is
  assumed for the state-neutral verb.
- Validator-only improvements include generation-aware surface readiness,
  completed-frame fencing, byte-correct one-frame action edges, and verb API
  diagnostics. A clamped cursor position is not treated as controller
  failure; object-492 A selection is the post-action input witness.
- Host validation: controller fixture unit tests `49/49 PASS`; Python
  compilation and `git diff --check` pass. Target command:
  `PYTHONPATH=src python3 tools/validate_scumm_room42_controller_nexen.py
  --rom build/generic-action-lifecycle3-verbcycle.sfc --output
  build/verbcycle-r4 --no-native-captures --logical-frame-fence`.
- Next: run the broader generic-controller suite and screen/publish the
  focused generator, validator, tests, and checkpoint changes. Do not reopen
  closed presentation, input-edge, Poppy, cooker, or backend investigations
  without contradictory evidence.
## 2026-09-09 — generation-aware quiescence refinement and source-name boundary

- `SAME_VIDEO_SURFACE_PRESENTED_GENERATION` has no production writer; it is
  reserved/stale bookkeeping and is not used by validator readiness.
- The authoritative fence now requires, at a completed logical-frame
  boundary: room-42 readiness, `pending_visual == 0`, `NEXT_GENERATION ==
  backend PENDING_GENERATION == backend COMMITTED_GENERATION`, backend idle,
  surface unlocked, and no live current-generation surface DIRTY/PRESENT
  packet. It rechecks the same relationship after one additional completed
  frame.
- Object-name source path is proven for target room 42: OBNA is decoded from
  OBCD, copied by the normal generated room loader into the existing bounded
  SCUMM name cache, and object 490/492 report source names (`storage locker`,
  `air compressor switch`). The loader now preserves caller P/X/Y state and
  uses one bounded name-cache contract; object IDs >= 0x400 are retained in
  source metadata but are not written past the 1024-entry runtime cache.
- Target run `build/generic-action-lifecycle3-names9.sfc` (SHA
  `ca4b89f8c5581465a71829f7e99e4cf5dea8c540056c8774d975a94de9c6a889`)
  reached room 42 and completed the controller lifecycle with error 0;
  object-name lengths/bytes were nonzero for objects 490 and 492. C17 verb
  name lengths remained zero because the attempted early script-18 launch is
  cleared by the authored room transition; no English controller lookup table
  or production C17 injection was retained.
- A later experiment to initialize C17 directly from script-18 source bytes
  perturbed startup and was removed. The current open frontier is the
  source-authored/runtime lifecycle that populates C17 names after room 42,
  followed by the generation-fenced Open/state-neutral action proof. No video,
  backend, input, or damage semantics were changed.
- The stricter fence was rerun successfully on both controls: accepted
  `94a6a6e623afc4a8778da99c2cc0bdd90ad7532aea08c344e7890462f822b056`
  (the local accepted generic-interaction binary) and current source-derived
  `ca4b89f8c5581465a71829f7e99e4cf5dea8c540056c8774d975a94de9c6a889`.
  Both reached stable room-42 quiescence with NEXT/PENDING/COMMITTED aligned,
  then completed the natural Open movement, state-neutral action, object-492
  selection, and post-action input with error 0. The moving presentation path
  remained successful; no production video/backend/input change is indicated.
- Expansion from the proven active object-name subset to every low-ID OBNA
  record caused a pre-ready regression and is not accepted. The generated
  source metadata remains complete; runtime installation must be generalized
  with a separately proven bounded per-room path before publication.
- A source-backed fixture refinement now starts authored global script 18 via
  the normal script-2 dispatcher after room entry. ROM
  `b192bfde9c0d8b2217f58150cdeb57af67609c4e2c27f60d7b686e8f1854a72b`
  passed the stricter generation fence, natural moving presentation, Open,
  ACTION_PENDING release, state-neutral action, object-492 selection, and
  post-action input with error 0. Target HUD evidence now includes `Push` for
  object 492 and `air compressor switch`; object 490 has `storage locker` but
  its initial Open verb-name record is still empty at the first selection
  boundary because script 18 completes later. This is the remaining narrow
  source-lifecycle/HUD issue; no graphics/backend/input change is implicated.
- Script-144 wrapping is now source-lifecycle-correct: script 18 executes
  after room 42 entry, before controller eligibility. ROM
  `d2152236f295d52301df10a224b1f83221016d6079a4c95377d50bb85d5fb61d`
  reports runtime C17 `Open` (length 5) before first object-490 selection,
  and `Push` (length 5) for object 492. Semantic target replay passes with
  the generation fence, movement, ACTION_PENDING release, state-neutral
  action, and error 0. Native captures were inspected; the room/actor are
  present, but the selected-HUD text is not yet visibly demonstrated in the
  emulator framebuffer. Keep this as visual evidence pending, not PASS.

## 2026-09-09 — exact replay provenance restored

- The prior phase-2-through-1200 A/B result is superseded: its candidate did
  not include the control's `SAME_SCUMM_SCENARIO_START_ROOM=42` and
  `SAME_BUILD_SCUMM_ROOM_VISUAL_ROOMS=42` contract.
- Current exact-config candidate: ROM
  `b80d63a62be9f8afdfd1951f61ea216c2341a94be65c2d909adf4ab57eda5795`;
  FULL ATLANTIS; historical Poppy DLL
  `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`;
  Poppy source line `8ee859b33bad94e3a01e9c78026803e482292801`;
  room42 ENCD length 169, SHA
  `d78775b6596efb8a602c6f9e575b63fab1cedf7f4fc2503c27a608cfa43d6242`.
- Validator reports now carry a replay contract containing ROM/toolchain,
  corpus/member hashes, semantic scenario flags, manifest hash, and room42
  ENCD identity. Future A/B equivalence must compare this contract; ROM
  hashes may differ, but semantic scenario configuration may not.
- Candidate reaches room42 phase0 and generation-aware quiescence. Forensic
  first-A observation reaches `$31 -> $33 -> mode 0->1`; the current
  transient hook collector also reports a same-window mode-zero notification,
  but its exact generated `RefreshSelection__clear` hook does not fire. This
  is not yet accepted as a production refresh failure because the observer's
  notification snapshots are not instruction-atomic.
- A temporary validator-only action timing experiment was discarded; the
  previously proven action-edge helper is restored. Full controller replay on
  this candidate remains pending a clean forensic/semantic observation.

## 2026-09-09 — mode-byte alias fixed; HUD publication remains open

- The exact controller-mode write watch on the rebuilt target proved the old
  refresh-clear interpretation was wrong: `$31 -> $33 -> mode 0->1`, with no
  later `1->0` write from selected-object refresh. The actual `1->0` writer
  was `ScummV5_Controller_BuildHudText__verb_loop` at `$09:A2D9`, where an
  unchecked runtime verb copy overran the 32-byte target-neutral HUD buffer
  into `SAME_SCUMM_CONTROLLER_MODE` at `$7E5FE0`.
- The generic 32-byte bound is now in the controller HUD copier. Rebuilt ROM
  `build/generic-action-refresh-fix-full42-hudbound.sfc` is
  `46606fb5e96fef40a875d133e3bc779ae6d745e1f170e1a9285ad11d488dc1a8`.
  Its forensic completed-frame snapshot retains mode 1, object 490, verb 3,
  and error 0.
- A second demonstrated HUD issue was corrected in the rebuilt source:
  successful `BuildHudText` publication now leaves `TALK_VISUAL_STATUS=0`,
  while unavailable/rejected presentation remains nonzero. The resulting
  ROM is `build/generic-action-refresh-fix-full42-hudstatus.sfc`, SHA
  `5c6aebad2b3346ac6812dcc67cf14ab13d3c0512242d2acc549585ae6416d4c7`.
  The target reaches a valid runtime C17 payload (`Open`, `storage locker`),
  but the overlay service still reports a rejected/unavailable presentation;
  the second A therefore correctly remains pending and no sentence is
  submitted. The full interaction milestone is not yet accepted.
- Validator-only corrections: transient HUD text-valid state is no longer
  polled as a persistent flag, and the exception path no longer loses the
  global HUD hook table. Do not classify the remaining overlay rejection as
  an input, hit-test, selected-object, or refresh-clear regression.
- The current target trace further binds the failure: at the mode-1 HUD
  boundary, C17 and OBNA source records are valid (`Open`, `storage locker`),
  but the published controller text buffer contains `Open` followed by zero
  bytes and length 33. The raster/overlay path is therefore not yet the
  first proven bad stage; builder append checkpoints are still required.

## 2026-09-09 — validator runtime provenance corrected

- Accepted Nexen executable: `/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen`; SHA-256
  `17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`.
- Invalidated probe runtime: `/tmp/mcp-mesen.sh`; wrapper SHA-256
  `b56a658c3df9a8956fb884dc3dc2bf2bfd32dfe6509d2dcae5096731e59b9aeb`,
  wrapping `/home/chad/Mesen2/bin/linux-x64/Release/Mesen.dll` with SHA-256
  `5a9442d65046b0bc0b3c3b9b85ab65620f5d568096181544a0ae72db2935de4e`.
  The wrapper ran a rebuilt Mesen2 worktree at HEAD
  `5a99adef3a1a40355ad5175b3e2d6417d0fbfc78`, with local modifications;
  it was not the accepted Nexen runtime.
- **FAILED INPUT/CURSOR PROBES AGAINST `/tmp/mcp-mesen.sh`: INVALIDATED BY
  RUNTIME PROVENANCE MISMATCH.** They are not evidence against production
  input delivery or cursor behavior.
- The exact default Nexen reproduces the authentic handoff `$31 -> $33 ->
  mode 0->1`, object 490, verb 3. The validator now records requested and
  executed emulator executable provenance in forensic artifacts.
- Builder-only observation remains validator-only. The first reliable ledger
  evidence is that object-append bookkeeping advances while zero-valued
  destination stores are suppressed by the deployed write-watch report;
  no production conclusion is drawn until the source-load/store event is
  captured on the accepted runtime.

## 2026-09-10 — HUD builder A-width defect localized and fixed

- Frozen Nexen remained unchanged at
  `/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen`,
  SHA-256 `17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`.
- Temporary diagnostic-only ROM `ecf15b658fa23ac485b14d54492f45eda21ed59e9f55a08db6833d631e083166`
  was used only for the fixed in-engine ledger and is not an acceptance ROM.
- The first false builder transition was immediately after the A8 C17 verb
  length load: length 5 widened with a stale high byte to `0x0105`, then
  decremented to `0x0104` (260). The verb loop therefore consumed the 32-byte
  buffer with zero-padded source bytes and reached finish before object append.
- Generic fix: explicitly zero-extend the A8 length with `AND #$00FF` before
  widening/decrementing. Temporary HUDDBG WRAM/source/validator instrumentation
  was removed after localization.
- Clean rebuilt ROM `build/room42-hud-fixed.sfc`, SHA-256
  `f199d6b8f46dc621bab2e92415b69ec43f3fef8d8f539bfd06e345c0ef95116b`,
  assembles with the frozen historical Poppy DLL and passes Poppy lint and the
  SA-1/BW-RAM ROM audit. Runtime HUD evidence now shows exact printable bytes
  `Open storage locker`, `TALK_RAW_LENGTH=19`, and
  `TALK_SEGMENT_LENGTH=19`, with the terminator outside the declared segment.
- The full validator run still stops at its existing moving-snapshot observer
  boundary after the HUD proof; no new production graphics conclusion is made
  from that observer failure. Full interaction acceptance remains pending.
- The first clean replay used a stale semantic hook address for
  `DESIRED_VISIBLE` (`$7E5E4D`); validator-only fencing now watches
  `DESIRED_SELECT` (`$7E5E46`) for the walking publication. The corrected
  observer now passes: moving actor `(157,101)`, destination `218`, and the
  bounded moving publication is observed.
- The corrected clean native replay publishes `Open storage locker` with
  exact runtime bytes and declared length 19, then proceeds through Open,
  movement, and the state-neutral action with `error=0`. Native captures in
  `build/room42-hud-fixed-native/` were inspected.
- Full replay currently stops at the separate second-object assertion:
  `move_cursor_to_source_object` does not yet produce object 492 after the
  state-neutral action; the selected object remains 490. This is outside the
  HUD-builder fix and remains unaccepted evidence, not a graphics result.

## 2026-09-10 — Generic cursor re-entry fix

- The object-492 failure was localized to the interaction state contract:
  after state-neutral completion, the controller correctly retained object 490
  in verb-selection mode (`mode=1`), while cursor motion changed coordinates
  without ending that selection. The following A therefore submitted the old
  selection instead of entering CDHD hit-testing.
- Added the generic `ScummV5_Controller_InvalidateSelectionOnCursorMove_Far`
  path. Cursor movement while `mode=1` clears only the semantic selection and
  returns to ordinary object-selection mode; it does not know any object ID,
  room, or verb policy. The next A uses the existing source hit-test and
  authored-verb discovery path.
- Rebuilt with FULL ATLANTIS, startup42 room 42, and the frozen Poppy DLL:
  `build/room42-generic-reentry.sfc`, SHA-256
  `5297e4e63d8dfb9db37393445b77c30b81959e525cdb6540e2b82a318eb1c632`.
- Focused controller fixture tests: 50/50 PASS; Python compilation and
  `git diff --check` pass. Target replay is pending because the frozen Nexen
  service is currently unreachable at `127.0.0.1:44331`; no debugger/runtime
  change was made.

## 2026-09-10 — Generic re-entry target replay PASS

- The frozen Nexen runtime was restored and used unchanged:
  SHA-256 `17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`.
- ROM `build/room42-generic-reentry.sfc`, SHA-256
  `5297e4e63d8dfb9db37393445b77c30b81959e525cdb6540e2b82a318eb1c632`, passed
  the cold FULL ATLANTIS startup42 controller replay.
- Verified sequence: room 42 readiness; object 490/Open; moving actor and
  locker state `0 -> 1`; state-neutral authored action; generic cursor
  re-entry; object 492 selected from source CDHD bounds; runtime HUD
  `Push air compressor switch`; post-dialogue input; `error=0`.
- Native captures from `build/room42-generic-reentry-run2/` were inspected,
  including `02-open-selected.png`, `06-object492-selected.png`, and
  `05-post-dialogue.png`. Replay report result: `pass`.
- Focused controller fixture tests: 51/51 PASS. Python compilation and
  `git diff --check` pass. The prior object-492 failure was validator
  expectation drift after the generic cursor re-entry fix, not a runtime
  selection failure.

## 2026-09-10 — Generic controller across room boundaries (in progress)

- Worktree/branch: isolated `/home/chad/SAME-0.2.0/room-boundaries`,
  `review/controller-mult`; frozen acceptance branch was not modified.
- Added a generic room-installed interaction reset and removed the generic
  controller frame’s room-42/room-68 interaction gate. Room-68 startup
  acknowledgement remains fixture policy. Added static coverage for the
  room-neutral production path and lifecycle reset.
- Candidate second room: FULL ATLANTIS room 49. Source-backed candidates
  include object 591 “very large basket” with authored verbs 8/9/11/90/91,
  object 592 “salvage boat” with verbs 9/10/90, and object 595 “fish net”
  with verbs 8/9/11/90/91. The selection rationale and source metadata are in
  `docs/controller_room_boundaries.md`.
- Frozen toolchain checks: Poppy DLL
  `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`; frozen
  Nexen SHA `17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`.
- The accepted room-42 replay remains green with the legacy bounded OBNA
  install path. Expanding generated OBNA installation to every source object
  changes the generated runtime path and currently prevents startup42 from
  reaching room 42. This is the active generic loader blocker; no multi-room
  acceptance or publication claim is made.

## 2026-09-10 — OBNA A/B/C/D matrix

- The first diagnostic attempt was invalidated: it used
  `SAME_BUILD_M25A_VALIDATOR` instead of the build script’s
  `SAME_BUILD_SCUMM_M25A_VALIDATOR`, and reused a room-49 visual include for
  startup42. Those results are not evidence.
- The corrected matrix used FULL ATLANTIS, the explicit startup42 room-42
  visual manifest, pinned Poppy, and the frozen Nexen. A (legacy) produced
  ROM `25db81447a14c112d20ec7e10d5ba1ed45fe3ff8353e50d60b92a804579e5cf4`
  and reached room 42 phase 0/readiness/error 0. C (generalized installer
  over the exact legacy set) was byte-identical to A and has the same result.
- B2 retained the legacy installer on the live path and put the expanded
  installer after the live return. It still failed to reach the room-68
  handoff through 1000 completed frames, ending room 0/phase 0/error 0.
  D (expanded live installer) had the same pre-handoff failure. This proves
  the first failure family is generated loader layout/relocation sensitivity,
  not an expanded installer execution/WRAM-count failure.
- Matrix artifacts and hashes are consolidated in
  `docs/controller_room_boundaries.md`.

## 2026-09-10 — Layout-preserving active-room names

- The active-room name population routine is now separately banked and no
  longer shifts the established room-loader control layout. Its copy loop
  keeps immutable generated source offset separate from active-cache
  destination offset; the earlier diagnostic version copied only the first
  byte while retaining the full source length.
- Fresh FULL/startup42 ROM:
  `build/room-boundary-fixed5.sfc`, SHA256
  `8ede6b44908ef57a27a570fad3c50a59df8a7dbd356438d8ccae8d77e3bb9dab`.
  Build identity:
  `build/room-boundary-fixed5.build_identity.json`, SHA256
  `bcdda830dfdc83a5f91f5e49741e6d180cd91a40eb7b3634c4e0d20c9f591cac`.
- Target room-42 replay passed on this fresh ROM: room 42 phase 0, exact
  `Open storage locker` and `Push air compressor switch` buffers, both action
  shapes, object 492, and error 0.
- Authentic phase-6 room-49 control reaches room 49 but remains in ordinary
  room-entry phase 2 with SCUMM error 14 before controller readiness. This is
  a separate lifecycle prerequisite, not evidence against the active-room
  name cache or room-install reset. No direct room/WRAM write bypass was used;
  no publication is made from this worktree yet.
- Validation on the current source: focused controller fixture `54/54` pass;
  relevant SCUMM/surface/M25A set `248/248` pass; repository-wide Python
  suite `544` pass, `4` skipped after moving the generated phase-6 room-49
  artifact that otherwise makes the existing optional Phase6K byte oracle
  compare against a different generated script set. Python compilation,
  `git diff --check`, Poppy source/DLL guard, and SA-1/BW-RAM ROM audit all
  pass for fixed5. No review branch has been published.

## 2026-09-10 — Room-49 error-14 writer localized

- The accepted room-42 state and generic active-room OBNA solution remain
  preserved; no production interaction/OBNA change was made for this pass.
- Diagnostic ROM: `df4839a2d017d9889f14304ea8ee86e70bd5047b04ea70f41913f02446103bcb`.
- The first canonical SCUMM error transition is error `0 -> 14` at
  `ScummV5_SetError` map `$F5FA`; its caller return resolves to
  `ScummV5_Op_StringOps__missing` at `$ED41` (return `$ED45`). This is
  decimal 14 / `$0E`, `SCUMM_ERR_STRING`, not VerbOps.
- Atomic diagnostic context: room 49, M23A phase 2, global script 144, slot 1,
  program `$F3`, PC `$0015`, last opcode `$27`, error count 54 in the rerun.
- C8 resolver state at the same terminal observation: sub-op `$44`, string ID
  `30`, `C8_SIZES[30] = 0`; the string resource is absent. Program `$F3` and
  source `script-144.scrp` are byte-identical (61 bytes, generated identity
  unchanged), so this is a missing prerequisite runtime resource state rather
  than a cooker/program mapping divergence.
- Historical M23B room-49 setup seeded source-authored boot strings 30/31 as
  153-byte resources. The phase-6 scenario boot clears C8 and reaches script
  144 before that earlier lifecycle has installed string 30. Controller code,
  OBNA, hit testing, C17, and readiness do not execute before the writer.
- Classification: interpreter StringOps missing-resource path caused by
  incomplete phase-6 startup state. No forced phase transition, error clear,
  controller special case, or validator WRAM patch is permitted. The next
  implementation step is to restore the authentic source lifecycle/resource
  mapping generically, then rerun the room-49 boundary.
- Authored producer audit: FULL ATLANTIS global `script.1` performs `$27 $01`
  `loadString` at source offsets `$024D` (ID `$1F`/31) and `$02FA` (ID
  `$1E`/30). Each authored payload is 169 bytes of `$64` followed by a
  terminator, yielding `C8_SIZES[30] = C8_SIZES[31] = 169`. Global 144/145
  only read those strings; scripts 18/132 install verb metadata and do not
  create them. The phase-6 room49 scenario requests room49 directly and omits
  the boot script-1 lifecycle, so error `$0E` is an incomplete scenario root.
  The old 153-byte M23B seed remains fixture-only and is not reused.
## 2026-09-10 — Room49 source-backed string prerequisite target result

The earlier room49 error-14 observation remains a historical witness only. The
authentic producer audit is closed: FULL ATLANTIS global script 1 performs the
two `loadString` operations that establish strings 31 and 30 at source offsets
`$024D` and `$02FA`, respectively. Each authored payload is 169 bytes of
`$64` followed by its terminator. The direct phase-6 root intentionally omits
that earlier boot lifecycle, so global 144's `$27/$44` read of string 30 was
correctly exposing incomplete incoming scenario state.

The chosen correction is fixture-boundary, source-backed incoming state after
the normal C8 reset during room installation. It is enabled only for the
phase-6 scenario fixture; no StringOps, controller, OBNA, scheduler, or
room49 production policy was added. The obsolete cook-time script-prefix and
boot-global experiments were removed.

Target evidence, using the exact FULL configuration, historical Poppy DLL,
and frozen Nexen, is:

- ROM `build/room-boundary-room49-source-root-final.sfc`, SHA256
  `946aebf137d2a65aff2db889fc24db7765b66562643f4ee5b0bae3d1e39a1e31`;
- report `build/room-boundary-room49-source-root-final-run/report.json`;
- room 49 reaches M23A phase 0 with error 0;
- at room49 phase 2 and at completion, `C8_SIZES[30] = 169` and
  `C8_SIZES[31] = 169`, with both captured prefixes equal to `$64`;
- lifecycle trace reaches schedule/begin and completes without
  `SCUMM_ERR_STRING`.

This is the accepted source-backed mid-game-root evidence for resuming the
multi-room controller proof. The next target step is authentic room49 object
selection/action validation, followed by the unchanged room42 regression.

The first room49 controller probe then selected object 596 (`path away from
dock`) from the live CDHD records at source coordinates `(0,0)-(64,48)` and
resolved authored verb 10. Its active-room OBNA name was present. The direct
phase-6 root still has empty C17 display names for room49 verbs because the
earlier VerbOps-authoring lifecycle is not part of that root. This is now the
next distinct incoming-state prerequisite for native room49 HUD proof, not a
regression in CDHD hit testing, OBNA loading, or the fixed C8 string state.

## 2026-09-10 — Room49 authenticated C17 VerbOps prerequisite

The missing phase-6 interaction state is now authenticated. FULL global script
1 starts authored global script 18 at source offset `$060D`; script 18 installs
the textual VerbOps records and starts global script 132 at `$0167` for the
remaining VerbOps state. The direct phase-6 root intentionally skips that
earlier lifecycle.

The fixture now restores the incoming state through the established authored
script seam: `tools/cook_scumm_v5_rooms.py --prepend-global-script 144 18`
prepends the encoded `startScript(18)` packet to global 144. No C17 WRAM is
written directly, and the controller contains no Fate verb IDs or fallback
names. The fixture is source-backed because the producer and order are the
FULL authored scripts, not a guessed label table.

Target evidence:

- ROM `dda8be046d3d89f1d7aca0b08eb07324c7680f91aa4a41c744b35b944bb3eabc`;
- report `build/room-boundary-room49-c17source-final-run/report.json`;
- room49 reaches phase 0 with error 0 and C8 sizes 169/169;
- runtime C17 records include `3=Open`, `4=Close`, `8=Use`, `9=Look at`,
  `10=Walk to`, and `11=Pick up`, with their complete fields captured;
- object596 is selected from live CDHD, authors verb10, and resolves the
  active-room OBNA name `path away from dock`.

Native HUD capture and the ordinary room49 action replay remain the next
acceptance checks; no new controller or C17 policy is justified.

The first native room49 object596 probe reached the text-service boundary with
the complete source/runtime payload: `Walk to path away from dock`, printable
length 27, `TALK_VISUAL_STATUS = 0`, and an accepted overlay SET_LAYER
transaction. The frozen overlay service then failed during generic cell
encoding: overlay state became ERROR with `pending_cells = 22`,
`accepted = 2`, `rejected = 0`, and `error_count = 1`; the native capture
showed the harbor without the HUD. This was a distinct overlay geometry/encode
failure after C17 publication, not missing C17 state. The later generic fix
clamps descriptor bounds to the initialized raster; the room-neutral
native-settle validator was also widened to accept an explicit room instead of
hard-coding room 42.

The authenticated script-18 name operations are at `$00A7` (verb 3 Open),
`$00B8` (4 Close), `$00CA` (11 Pick up), `$00DE` (12 Talk to), `$00F2` (9
Look at), `$0106` (8 Use), `$0116` (6 Push), `$0127` (7 Pull), and `$0138`
(10 Walk to); each performs the authored NEW/NAME/AT sequence. Script 132 is
started at script-18 `$0167` and applies KEY sub-op `$12` to IDs `$65..$6E`.

## 2026-09-10 — Room49 overlay geometry correction

The room49 HUD failure was a descriptor-boundary defect, not a capacity
shortage. The failing text `Walk to path away from dock` produced a raster
bound `CONTENT_X1 = 156` while the initialized INDEX8 plane is only 80 pixels
wide. The backend's screen-relative scan therefore visited 11 columns by 2
rows: 22 unique in-range cells, then attempted another out-of-plane cell while
the capacity guard ran before source clipping. No duplicate cell accounting or
staging overflow was involved.

The generic text-service boundary now clamps descriptor content bounds to the
initialized 80x8 raster (`X0/Y0 >= 0`, `X1 <= 79`, `Y1 <= 7`). The 22-cell
allocation remains unchanged. Copyright-free overlay tests retain the exact
22-cell geometry regression and add a source assertion for the descriptor
clamp.

Target evidence:

- ROM `5d1b408c001f5afbe6ef07dfc6775bb78b7c81181ad85212e703008da0fdfa39`;
- build uses the historical Poppy DLL and frozen Nexen;
- room49 C17/OBNA semantic chain remains phase0/error0;
- overlay current generation equals committed generation 2, state is IDLE,
  error count is 0, and all 22 cells are accepted;
- native capture `build/room-boundary-room49-overlay-bounded-run/
  room49-object596-walkto.png` was inspected and visibly shows
  `Walk to path away from dock` over the harbor.

Focused controller/overlay unittest validation is `61/61 PASS`. The full
repository unittest run is `544 PASS, 1 FAIL, 1 SKIP`; the single failure is
the existing optional Phase6K byte oracle reading the generated room49
artifact after the phase-6 fixture build changed that artifact's script set,
not a runtime failure of the overlay correction. Poppy lint, ROM
assembly/finalization/audit, Python compilation, and `git diff --check` pass
for the bounded-overlay ROM.

The corrected ROM was rechecked with the frozen Nexen executable
(`17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`). The
phase-6L lifecycle report reaches room 49 phase 0 with error 0 and retains
the authenticated C8/C17 state. The native room49 object596 capture was
opened and visually inspected: the source/runtime HUD is rendered as
`Walk to path away from dock` over the harbor. Its overlay generation is
committed and idle with no encode error. The separate backdrop-only checker
is not used as the text acceptance oracle because its Mode-3 terminal-state
assertion is incompatible with this dynamic-overlay replay; the native text
capture is the authoritative overlay evidence here.

The same source was rebuilt with the explicit FULL/startup42 contract as
`build/room-boundary-room42-final.sfc` (SHA256
`9eed313b43ac0bbaf01a40163c962758ac4e3b1b6b39c7dd5e951df28d7ab546`). The
cold room42 controller replay passed: Open movement/state effect, canonical
action release, state-neutral action, object492/Push, post-action input, and
error 0. Its replay artifact is
`build/room-boundary-room42-final-run/report.json`.

The Phase6K byte oracle was adjudicated against the closest preserved
pre-multi-room cooked artifact (`build/m23a-preflight/cooked-a/room-49.sc5c`):
the baseline has the expected program-211 bytes
`4c01ffffff 2453033fffffffff`, while the current phase6 generated artifact
has `020114020f ff0ac09dff0afd07`. The current mismatch is generated-input
provenance drift from the phase6 fixture artifact, not a change to the
Phase6K host behavior; the oracle was not weakened.

Room49 cursor/viewport geometry was audited from a cold interactive boundary.
Initial cursor is `(399,116)`, camera current X/Y is `(160,100)`, and
`VSCREEN_XSTART=0`. The production left path is an unconditional
`cursor_x -= 2`; the assembled source/map contain no x=89 clamp. The earlier
x=89 endpoint came from a lossy long pulse sequence and is not a production
boundary. No cursor-clamp change was made.

The 640-pixel room visual is projected to the 256-pixel native surface from
source X 192..447. Object596 CDHD is `(x=0,y=0,width=64,height=48)`, so it is
off the displayed viewport despite its hit-test projection to cursor-space
`x=0..63,y=0..47`. The room49 live source enumeration is recorded in
`docs/controller_room_boundaries.md`; object592 (`salvage boat`, x312..415,
y56..103) is the selected next action target because it is fully visible and
offers authored `Look at`/`Walk to` with authenticated C17 names. Objects 591,
594, and 595 are additional visible source-backed candidates. Object596's
accepted CDHD/VERB/OBNA and long-HUD evidence is retained, but its action
replay remains pending an authentic camera/world transition.

The visible-object semantic replay was exercised without production changes.
From `(399,116)`, six right pulses and eighteen up pulses reached `(411,80)`
for object592, avoiding overlapping object597. The authentic first A selected
object592/authored verb9 and entered mode1. The second A entered mode2; the
ordinary SCUMM lifecycle returned to mode1 with room49 phase0/error0. Six
ordinary left pulses after completion moved the cursor to `(399,80)` and
returned the controller to mode0 with selection cleared. Artifact:
`build/room-boundary-room49-object592-run/report.json`.

Native room49 action proof remains open. The capture attempt was rejected as
evidence: the frozen runtime remained in backend state4 with 736 pending tiles
through the bounded convergence wait, and the screenshot was noise. No
production cursor, controller, or video change was made.

## Room49 backend convergence classification

Generated backend constants identify state `$04` as `WAITING_DMA`. A fresh
object592 replay sampled only at completed logical-frame fences. Progress was
normal: at offset 0 the backend was CONVERTING with candidate 256, pending
640, converted 640; at +16/+32/+48 candidates fell to 192/128/64 and
converted rose to 704/768/832; at +64 conversion reached candidate 0 and
converted 896; QUEUEING then drained pending work 896 -> 672 -> 416 -> 160;
at +128 the backend was IDLE/unlocked with pending 0 and FIFO 0. Backend
steps rose 161 -> 289 and DMA batches 0 -> 29. This exonerates a backend
stall and establishes that the earlier state-4 capture was premature.

The same run left the text service holding the exact 20-byte
`Look at salvage boat` payload and the overlay at generation 2/IDLE. The
post-convergence native capture still did not visibly show the HUD, so it is
not accepted as native text evidence yet; that is now a separate overlay
realization/capture boundary, not a conversion-progress failure. No
production change was made.

## Room49 overlay realization localization

The committed object592 failure is localized to coordinate realization. The
text payload was correct (`Look at salvage boat`, 20 bytes), generation 2 was
accepted and committed, conversion/DMA completed, and the backend was idle and
unlocked. The committed descriptor was `X=399,Y=84,W=80,H=8`, content bounds
`0..79` by `0..7`; BG2 therefore computed an off-tilemap column range `49..31`
and realized no visible cell range. The accepted object596 comparison had the
same bounded geometry but descriptor `X=51,Y=50` and 22 in-range cells.

The room49 surface crop is source X `192..447` to native X `0..255`. The
target-neutral overlay boundary was subtracting the virtual-screen center
offset but not this published source crop. It now also subtracts
`SAME_VIDEO_SURFACE_SOURCE_X`; cursor room X `411` consequently maps to the
established text anchor at descriptor X `207`, inside the native domain. This
is a generic surface-coordinate correction; no controller, Mode3, DMA, C17,
OBNA, or room/object-specific policy changed.

## 2026-09-10 — Canonical overlay-coordinate rebuild

The prior unresolved-symbol build was an invocation/configuration failure: the
generated configuration omitted `SAME_BUILD_M24RB=1`, leaving the bank-9 SCUMM
far closure out while the dispatcher referenced it. The unresolved symbols
included `ScummV5_C25_FarCall_EmitAudio`,
`ScummV5_M23A_EndRoomScript_FarEntry`, and generated `ScummV5_C2_Program_*`
labels. The verified Poppy DLL was source
`8ee859b33bad94e3a01e9c78026803e482292801`, SHA
`34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`.

With the canonical regenerated FULL room49 configuration and M24RB enabled,
the coordinate-fixed ROM assembled/audited as
`65f431e5659e0b7ee28e19cae892b0a174e1920ee4ea246dae71c8be1bdb10e5`. Frozen
Nexen SHA is `17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`.
The cold room49 replay selected object592/verb9, committed descriptor X=207,
and the inspected native capture
`build/room-boundary-room49-overlay-coordinate-replay/native.png` shows
`Look at salvage boat`. The second A entered ACTION_PENDING and returned to
generic selection without object-state mutation; a later D-pad edge cleared
the stale selection and left room49/error0.

The final rebuilt room42 target is `build/room-boundary-room42-final-rebuilt.sfc`,
SHA `c7c7edf52c5fa802428dc17c9387126e8708ae9d2f7ea75fd27541bfac9f5372`.
Its complete cold replay passed with the frozen Nexen and historical Poppy:
Open/state-changing action, state-neutral action, object492 Push, post-dialogue
input, and error0. Native captures were inspected. The repository unittest
suite reports 544 passing, 1 skipped, and the known pre-existing Phase6K
generated-artifact oracle failure; focused controller/architecture tests report
58 passing. Python compilation, diff check, Poppy guard/lint, and ROM audit
pass.

## 2026-09-10 — generic controller capability split

Work continues from frozen `review/controller-room-boundaries-final` commit
`b80f6e45c5cc4057ed51554dfdb8bb71c606d503` in isolated branch
`controller-service`; the frozen branch is untouched. Generic controller
service lifecycle and source-driven interaction are now enabled by
`SAME_BUILD_SCUMM_CONTROLLER`, with `SAME_BUILD_SCUMM_CONTROLLER_FIXTURE`
implying it. The room-install reset and room-ready latch are capability-owned;
room68 handoff, C8/C17 scenario seeding, actor/object visual fixture code, and
capture behavior remain fixture-only.

The fixture-enabled room49 personality assembled and passed Poppy lint and the
SA-1/BW-RAM audit, producing ROM SHA
`65f431e5659e0b7ee28e19cae892b0a174e1920ee4ea246dae71c8be1bdb10e5` with the
historical Poppy DLL SHA
`34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`. A
controller-disabled SCUMM personality also assembled, linted, finalized, and
passed the ROM audit, producing diagnostic ROM SHA
`fe4216e5e2cdd23981c0f04718f50d0923976efb7341270d35f686367082000b`.
Focused controller tests pass 56/56. The capability-split review is accepted
and published as `review/controller-service` at `39b1cc1`; this branch begins
the separate standalone generic-controller runtime conformance milestone.

The first standalone fixture milestone is complete locally. A new
copyright-free profile and cooked-room generator produce one self-contained
room with one reachable CDHD object (ID 7), OBNA `test console`, authored VERB
3, and an authored local VerbOps producer (script 200). The host round-trip
test verifies the object bounds/name, authored verb entrypoint, and script
identity. No Fate archive or Fate object/script content is used by this
fixture. Target builder wiring and the cold enabled/disabled runtime replay
remain in progress.
