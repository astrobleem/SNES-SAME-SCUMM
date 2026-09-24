# PR #1 maintainer-review remediation record

This record supersedes the earlier claim that the exercised room42 action
proved a complete authentic room42-to-room0 original-game path. It tracks the
review findings against the local remediation branch; it does not claim that
the PR is ready to merge while the audio rights evidence below is unresolved.

## Finding ledger

| # | Disposition | Baseline evidence | Correction and regression | Evidence class / remaining limit |
| ---: | --- | --- | --- | --- |
| 1 | Fixed | Static WRAM width/lifetime conflict: the validity byte shared the upper byte of a 16-bit storage scratch word. | Moved M23A return metadata to separately allocated bytes at `$7FF467-$7FF469`; added width-aware layout/lifetime test. | Clean-source Nexen storage-transaction controls pass for invalid room-local (`f00cf1e31d3931f075c59b4cc02747a55da687a41e53ff02d2bcb1ca587ae059`) and surviving global (`6c8a128061df080dfcc2723f91321c670b0d670a5ef8c07df7d474a8b6fa8a0d`) continuations. |
| 2 | Fixed | Host decoder showed the launcher consumed `$0A $12` as Global1's word argument `$120A`. | Launcher now uses complete encoded calls; `tests/test_startup42_launcher.py` decodes all operations, arguments, and boundaries. | Host decoder regression; this launcher remains a controlled fixture, not original-game startup. |
| 3 | Partial; endpoint claim withdrawn | Build graph selected a synthetic logical room49 that restarted startup; a separate phase-6 fixture transformed Global144. | Bootstrap carrier moved to explicitly checked room254; authentic room49 included in the resource selection; transformed Global144 now has synthetic identity and separate original/transformed hashes and source body. | The corrected cold bootstrap replay is real Nexen execution but stops at room68 phase1 with error 0 before the room42 action. The full original-game route and room0 endpoint have not been reproven. See “Authenticity boundary.” |
| 4 | Fixed | Native slot/context inspection showed valid M23A returns restored code location without the owning C4 activation. | Restore surviving caller through the slot/context loader; outgoing room-local callers remain invalid. | Clean-source Nexen global control `6c8a128061df080dfcc2723f91321c670b0d670a5ef8c07df7d474a8b6fa8a0d` preserves distinctive local state and resumes exactly once; local-requester control `f00cf1e31d3931f075c59b4cc02747a55da687a41e53ff02d2bcb1ca587ae059` remains retired. |
| 5 | Fixed | Host reproduction showed an old local ran after resource-less room0 and EXCD did not run. | Null-room transition now shares outgoing exit/retirement lifecycle while skipping destination resource acquisition. | Host behavioral regression and clean-source native Nexen control pass: EXCD once, local retired, global preserved, no room0 storage read (`3a31729dd54483eeee2285623c7e5818f93fd871efcc08f646388154d62f815f`). |
| 6 | Fixed | Native allocation/handoff analysis exposed same-object replacement reusing a dead caller slot. | StartObject now dispatches replacement without saving a stopped caller as parent; no-parent slot index is explicitly zero-extended. | Clean-source Nexen long case `4d4265b25135b6030dd62463ddfe0a26fe5fe21c441eee886b59a0bd4ab3cdce` observed 261 live counted operations at handoff, a nonzero high byte, slot index X=1, authored verb entry/argument, no old-tail resume, balanced JSL/RTL stack, and error 0. Short self-replacement `7bda2238b4550bfa9ebfc69ca78192f7592410125e844c3853309ee98f7cb9b7`, distinct-object nesting `fb60fdefce7a44a098cee40dd21bf3f39f08ad99269abb700d9abc689fc0da3b`, and ordinary StartObject `bdf43e1ae4bde0394b33ce10988f689543a5e9066d6fe3af6bb9c85874a961d2` also pass. StartScript replacement `d797f6f309b901ae16c94f2b6bc050871222369a9159357d995b1224d87d55e3` passes. `chainScript` remains covered by the host scheduler regression; this campaign did not claim a separate native chainScript fixture. |
| 7 | Fixed | Native call-contract audit found operand-error exits could abandon a live JSL return frame. | Actor-query return/error convention is balanced without weakening the four-form word-selector grammar. | Clean-source Nexen malformed result/truncated result/truncated selector cases pass with intended errors, balanced stack, and correct return: `actor-position-errors/evidence.json` under the final-source build record. The four-form success matrix ROM is `ec7743e9b96f9651e63bd0358db2cccde49eca17ff5cc588197f54a06f1572d1`. |
| 8 | Fixed; near and far native matrices pass | Near/far request paths could overwrite a phase4/5 accepted request before deciding how to handle a second request. | Decide before mutating; same-target requests coalesce, a conflicting public request is serialized until the accepted transaction completes, and a conflicting direct VM request is rejected with error 13 while preserving the accepted transaction. | Fresh-power-on Nexen controls execute all four required combinations (phase 4/5 × same/conflicting public target) on both actual implementations. Near ROM `ff83404a304f94d3229f2ac681e7cf25a8017bb35063fe32e826ccb293a1d530` hits bank-0 `ScummV5_M23A_RequestRoom` at `$BACF` (5 hits per non-direct case); far ROM `a5136a2261fbeb651e152d0798277d6d7f678bc53a381bca557bc2652119319c` hits `ScummV5_M23A_RequestRoom_FarEntry` in bank 9. Direct conflicting-call rejection is additionally tested at phase 4/5. All reports preserve pending target/continuation, verify event/read ordering and completion, and bind to ROM identity. |
| 9 | Fixed | Clean export reproduced missing generated include and mandatory machine-local archive failures. | `make generate` supplies lint/test generated inputs; original-data tests use configurable opt-in corpus selection and fail when an explicitly supplied archive is invalid. | Clean exported tree passed `make test`; optional corpus absence is reported as skips. The default suite does not depend on `/home/chad`. |
| 10 | Fixed | ROM-specific symbol lookup could silently fall back to an unrelated shared map. | Build identity binds ROM, map, and listing hashes; ROM-aware lookup rejects missing/mismatched identity rather than accepting the shared map. | Two-pair, absent, and mismatched-map tests pass. Native addresses must be regenerated from the exact tested build identity. |

The hashes above identify the ROMs used by bounded native controls. The source
and host regressions remain distinct evidence and are not substitutes for the
native execution results.

## Authenticity boundary

The old `room42 -> room75 -> room49 -> room68 -> room0` endpoint claim is
withdrawn. The reviewed build could resolve room49 to a synthetic carrier
that restarted startup. The corrected selection keeps the bootstrap at room254
and cooks authentic room49, but the cold Nexen run performed for remediation
reached room68 phase1 with error 0 before submitting the room42 controller
action. A separate direct room42-root diagnostic also stopped before the
controller sentence. Neither run proves the former complete action or room0
endpoint.

The strongest retained claims are limited to the individually observed
controller/runtime controls and the bounded authentic resource/runtime
segments documented by their validators. Synthetic roots and wrappers are
identified as such in build manifests. The Global144 phase-6 wrapper retains
the original Global144 bytes separately and hashes both source and executed
forms. A generated self-consistent hash is provenance metadata, not evidence
that transformed bytes equal the archive resource.

The cold bootstrap artifact used for the corrected bounded replay was
`eff31d3afa939c06cf474eb9bc6587c515d3df6948f34978df3063a25bee3eec`; its
build identity is `441be77419c32deef4ec7c2dc149fdd43c7a25f9f3fde3e0bf702ac958e60813`.
It selected synthetic room254 and authentic room49 source data, but the replay
ended at room68 phase1 and is not an endpoint acceptance artifact.

The remediation rebuild for the same separated-room selection produced ROM
`b06e517c8b63d51bdc7be6fe77327f65c1393270aad9c88cc6cb0a995b851c52` with build
identity `5e103ed241f28f09f6c69991b9d09dcb39106a47ae3075b2a722add397d7afe7`.
A fresh Nexen controller-validator attempt ran 8,000 frames, sent the title
input through the emulator API, and remained in room68 phase1 with error 0;
room42 readiness was not reached. This is a bounded stop observation, not a
successful controller-action replay.

## Executable lookup policy

The bounded native missing-local and missing-global start controls now fail
with SCUMM error `$0B`; they do not silently continue as successful starts.
The current authentic-path validator also treats a reached unresolved,
body-requiring start as a failure. Stops and status queries are not classified
as body starts. This record makes no claim that every possible dynamic start
in every Fate path has been exhaustively enumerated.

## Reproducibility

The ordinary documented `make test` suite runs without the private Fate
archive. Authentic-data integration tests are opt-in through
`SAME_FATE_DEMO_ARCHIVE`; an unset corpus skips those cases, while an invalid
explicit path fails. `make generate` is part of the test graph. Build commands,
Poppy/.NET prerequisites, and the distinction between host tests, source-path
evaluation, and Nexen execution are documented in `BUILDING.md` and the
individual validator targets.

On the clean-source final control build, `make test` passed 741 tests with 8
optional-corpus skips. `make validate` passed Poppy lint (38 source files,
2,219 global labels). Changed Python compilation, `bash -n tools/build_snes.sh`,
and `git diff --check` also passed. Exact final-commit reruns are recorded in
the Native acceptance follow-up below.

## Publication and asset provenance

`PR1_ASSET_PROVENANCE.md` inventories the 28 WAV, 2 BRR, and 38 MML additions.
Source matching and transformations are recorded there, but the repository
does not contain sufficient asset-specific permission or attribution terms to
establish redistribution rights. Because those blobs occur in the published
history, a later-tree deletion alone would not remove them from the PR. This is
an external maintainer/licensing decision and remains a merge blocker; no rights
determination is inferred here.

The historical patch attachment and contributor guidance have not been
rewritten as part of this remediation. `AGENTS.md` retains discoverable
architecture, validation, and worktree-safety constraints. Any PR description
must replace the former complete-authentic-endpoint claim with the bounded
scope stated above.

## Independent re-review follow-up

This section supersedes the earlier R1/R2 “native execution pending” status
below. The native controls were rebuilt from clean tracked source at commit
`ea7621680b7a44c41c81066536c0f19178f150ea` and executed on the verified Nexen
binary. A final documentation-only commit is being followed by a clean-source
rebuild and ROM-hash comparison so the reports remain explicitly bound to the
final source tree.

| Finding | Current disposition | Correction / regression | Evidence and remaining limit |
| ---: | --- | --- | --- |
| R1 — no-parent slot index width | Fixed; native execution pass | `ScummV5_C4_RunAllocatedNoParent` zero-extends the byte slot index before `TAX`. The long same-object fixture exceeds 255 operations without yielding and checks entry/arguments, no-parent state, old-tail non-resumption, and the JSL/RTL stack contract. | Fresh-power-on Nexen observed `FRAME_OPS=261` at replacement, X=`$0001` at descriptor access, authored replacement verb and `$BEEF` local0, old-tail sentinel 0, balanced native stack, and SCUMM error 0. ROM SHA `4d4265b25135b6030dd62463ddfe0a26fe5fe21c441eee886b59a0bd4ab3cdce`. |
| R2 — genuine near RequestRoom coverage | Fixed; near and far native matrices pass | Added a minimal near-only pending diagnostic personality that includes the production near M23A RequestRoom and real storage/event transaction path. Build identity disables M24RB and far room service; the validator resolves a route-specific symbol and requires a hit. | The actual near entry `ScummV5_M23A_RequestRoom` (bank 0, CPU `$BACF`) was hit five times per serialized same/conflict run. The far entry `ScummV5_M23A_RequestRoom_FarEntry` was separately exercised in bank 9. Both routes pass phase4/phase5 same-target and conflicting-target public request cases, plus direct conflicting-call rejection. Near ROM SHA `ff83404a304f94d3229f2ac681e7cf25a8017bb35063fe32e826ccb293a1d530`; far ROM SHA `a5136a2261fbeb651e152d0798277d6d7f678bc53a381bca557bc2652119319c`. |
| R3 — path-cached ROM/map identity | Fixed | ROM, map, listing, and identity are revalidated for each acceptance lookup; parsed symbols are cached only by verified map content. Same-process regressions replace the map and ROM at the same paths, delete the ROM, invalidate identity, and install a new matching tuple without `cache_clear`. | `tests.test_snes_rom_symbol_identity` passes; invalid tuples fail before symbol hooks are resolved. |
| R4 — unknown conditional symbol merge | Fixed | The include linter now evaluates conditional blocks against branch-local symbol environments and merges equal values while retaining conflicts or one-sided assignments as unknown. | `tests.test_poppy_source` covers differing and identical branch assignments, later conditions, one-sided assignments, nested conditions, fail-closed possible includes, and known true/false cases. |

The clean documented suite passes 741 tests with 8 optional-corpus skips;
`make validate` passes. These host/source checks supplement, and are separate
from, the Nexen execution results above.

The clean-export assembly attempt exposed one additional build-graph defect:
Poppy resolves paths for feature-gated includes before processing their `.if`
guards, while ignored leftovers had supplied empty or generated files in the
developer tree. `tools/build_snes.sh` now emits deterministic empty includes
for disabled M20/M22, room-visual, and fixture-sprite producers. Clean assembly
and ROM audit are required again after this correction; the source-linked
records in the follow-up evidence distinguish those build results from native
execution.

The original-game acceptance limitation is unchanged: corrected gameplay
observation did not reach room42 readiness, and the complete original-game
action remains unauthenticated. Asset redistribution permissions also remain
unresolved. These technical, gameplay, and publication conclusions are
separate; this follow-up does not make the PR merge-ready by asserting a
broader scope.

### Final-source native acceptance — 2026-09-24

The controls were built and executed from a clean tracked checkout of
`ea7621680b7a44c41c81066536c0f19178f150ea`. The detailed report JSONs include
the exact ROM SHA, build-identity SHA, native symbol map/listing SHA, generated
input hashes, and clean Git identity. The follow-up source commit updates this
document only; the final-source linkage record compares clean rebuild ROM
hashes after that commit before reusing these runtime observations.

The native runner is the verified Nexen executable at
`/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen`,
SHA-256 `17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`.
It launched each cartridge with its loopback MCP endpoint, the validator
connected to `127.0.0.1`, reset to fresh power, executed the bounded fixture,
read CPU/WRAM state, and closed the owned emulator session. No alternate
emulator or public bind was used. Copyright-free M24R-A test audio was built
from the pinned toolchain source commit `822164b09cb3d4750bd4c1960a430dc35b6ae04a`;
no private Fate archive was used by these controls.

The genuine near profile was independently assembled with `SAME_BUILD_M24RB=0`,
`SAME_BUILD_SCUMM_ROOM_SERVICE_FAR=0`, `SAME_BUILD_SCUMM_M23A=1`,
`SAME_BUILD_SCUMM_M23B=0`, `SAME_BUILD_SCUMM_M23C=0`, and
`SAME_BUILD_SCUMM_M25A_PENDING_ONLY=1`. Its build identity reports those values,
the actual native breakpoint resolves to bank-0
`ScummV5_M23A_RequestRoom`, and fresh-power Nexen execution hits that entry.
The far profile separately resolves and hits
`ScummV5_M23A_RequestRoom_FarEntry` in bank 9. For each route, phase4 and phase5
were tested with a repeated target and a conflicting target. Same-target
requests coalesce without a second storage read. Conflicting public requests
remain pending while the accepted target completes, then are retried and
complete in order. Direct conflicting calls reject with error 13 without
mutating the accepted pending target/continuation or queuing another read.
The production near implementation and transaction/event path are therefore
native-tested; this is not a far-wrapper alias or a source-only guard test.

The long StartObject case runs 261 counted operations before replacement, with
the operation counter's high byte live at the no-parent handoff. Native state
proves X was `$0001` at slot descriptor access, the allocated replacement
reused slot 1 and began at its authored verb entry with local0 `$BEEF`, the old
continuation sentinel remained zero, the nested/no-parent adapters had the
expected call counts, native stack deltas balanced, and SCUMM error remained
zero. Short self-replacement, ordinary and different-object nesting,
StartScript self-replacement, global/local room continuation, storage validity,
null-room lifecycle, and actor-position success/error controls also pass on
Nexen. `chainScript` remains covered by the host scheduler regression; no
separate native chainScript case is claimed here.

Clean-source validation: `make test` — 741 passed, 8 optional-corpus skips;
`make validate` — PASS; changed Python compilation — PASS; Bash syntax — PASS;
`git diff --check` — PASS; Poppy lint — PASS; assembly and ROM audits — PASS.
The complete commands, tool identities, per-control reports, map/build
identities, and ROM-to-source linkage comparison are in the companion evidence
archive. These bounded conformance controls do not establish the full original
Fate gameplay path. Corrected gameplay observation still did not reach room42
readiness, and asset redistribution permissions remain unresolved.
