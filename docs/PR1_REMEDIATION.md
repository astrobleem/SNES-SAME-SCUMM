# PR #1 maintainer-review remediation record

This record supersedes the earlier claim that the exercised room42 action
proved a complete authentic room42-to-room0 original-game path. It tracks the
review findings against the local remediation branch; it does not claim that
the PR is ready to merge while the audio rights evidence below is unresolved.

## Finding ledger

| # | Disposition | Baseline evidence | Correction and regression | Evidence class / remaining limit |
| ---: | --- | --- | --- | --- |
| 1 | Fixed | Static WRAM width/lifetime conflict: the validity byte shared the upper byte of a 16-bit storage scratch word. | Moved M23A return metadata to separately allocated bytes at `$7FF467-$7FF469`; added width-aware layout/lifetime test. | Native Nexen storage-transaction controls pass for invalid room-local (`5cf65d9421031bed525cc93a74d815319740df9a242316d59685cebc03def4cb`) and surviving global (`800b59ff19d805a9458c4db6ce5364bd04d5faa37faf05930bcc10f46b0c7162`) continuations. |
| 2 | Fixed | Host decoder showed the launcher consumed `$0A $12` as Global1's word argument `$120A`. | Launcher now uses complete encoded calls; `tests/test_startup42_launcher.py` decodes all operations, arguments, and boundaries. | Host decoder regression; this launcher remains a controlled fixture, not original-game startup. |
| 3 | Partial; endpoint claim withdrawn | Build graph selected a synthetic logical room49 that restarted startup; a separate phase-6 fixture transformed Global144. | Bootstrap carrier moved to explicitly checked room254; authentic room49 included in the resource selection; transformed Global144 now has synthetic identity and separate original/transformed hashes and source body. | The corrected cold bootstrap replay is real Nexen execution but stops at room68 phase1 with error 0 before the room42 action. The full original-game route and room0 endpoint have not been reproven. See “Authenticity boundary.” |
| 4 | Fixed | Native slot/context inspection showed valid M23A returns restored code location without the owning C4 activation. | Restore surviving caller through the slot/context loader; outgoing room-local callers remain invalid. | Native Nexen global control `800b59ff19d805a9458c4db6ce5364bd04d5faa37faf05930bcc10f46b0c7162` preserves distinctive local state and resumes exactly once; local-requester control `5cf65d9421031bed525cc93a74d815319740df9a242316d59685cebc03def4cb` remains retired. |
| 5 | Fixed | Host reproduction showed an old local ran after resource-less room0 and EXCD did not run. | Null-room transition now shares outgoing exit/retirement lifecycle while skipping destination resource acquisition. | Host behavioral regression and native Nexen control pass: EXCD once, local retired, global preserved, no room0 storage read (`9bcae4e0c3ee75e4da2c77ef381ed293a4adc996f41e9763d76c648afee730ab`). |
| 6 | Fixed | Native allocation/handoff analysis exposed same-object replacement reusing a dead caller slot. | StartObject now dispatches replacement without saving a stopped caller as parent. | Native Nexen self-replacement `6d6538010d86f202b9933f0462f4de520101b1632f414d83230cc620481f66b4` and distinct-object nesting `89f23e9412d95c90dc45ff49e0dee847979768ac0b343b756d11f83fff3ee8ca` pass; ordinary StartObject control `e23e34e8e613e9fc47201b3cafc0a5ffbe6941771401e0689545a6150f737da2` passes. StartScript controls remain green. |
| 7 | Fixed | Native call-contract audit found operand-error exits could abandon a live JSL return frame. | Actor-query return/error convention is balanced without weakening the four-form word-selector grammar. | Native Nexen malformed/truncated operand cases report intended errors with balanced stack and correct return: `1fcaf47f58cb647a6e1cf6590687aad85f98fd1e5acea793e9bda0f66678d623`, `07a7796a192aa1dd917683ad32f5762dee72f72d594ecff6b0dd900e8baffdd8`, `349457a1ac4edaed1608738cab2a232bf4917645bae0704cf86f362c14db2535`. Four-form success matrix remains covered. |
| 8 | Fixed; near-route native coverage remains open | Near/far request paths could overwrite a phase4/5 accepted request before deciding how to handle a second request. | Decide before mutating; same-target requests coalesce, a conflicting VM request fails explicitly, and external conflicting targets remain serialized. | The historical bounded Nexen report for `7b86caca5ffd0cbceb22cb34cfd1a0523821481ae5d6305d5b88293121cc539f` proves the far implementation only. Its “near” label was incorrect: that ROM identity has M24RB enabled and invokes the far guard. See the independent re-review follow-up below; the near native matrix is not claimed. |
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

On this remediation tree, `make test` passed 729 tests with 7 optional-data
skips. An isolated export at `/tmp/same-pr1-clean-final.Q6zU63`, assembled from
the base archive, tracked diff, and explicit source-fixture list, passed `make
test` with 729 tests and 8 skips and `make validate` with Poppy lint passing
for 38 files and 2,218 global labels. The one additional skip is a
user-generated authentic-room record unavailable in the export. Python
compilation, `bash -n tools/build_snes.sh`, and the working-diff check also pass.

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

This follow-up is intentionally not a blanket native-acceptance claim.
The original remediation reports were generated against dirty `a389ae8`
builds. Their ROM identities do not match builds containing the R1 correction,
so those native results are not reused as evidence for the corrected source.

| Finding | Current disposition | Correction / regression | Evidence and remaining limit |
| ---: | --- | --- | --- |
| R1 — no-parent slot index width | Corrected in source; native acceptance pending | `ScummV5_C4_RunAllocatedNoParent` now masks the byte slot into a 16-bit accumulator before `TAX`. The long same-object fixture executes 260 counted operations before replacing the activation; its native validator checks the high-byte boundary, entry/arguments, old-tail non-resumption, no-parent state, and the JSL/RTL stack delta. | Long-case build, Poppy lint, assembly and ROM audit pass (`1bfc111108bcbf405e3ed66909fc363016c5e5dde72a256211179f984e9ef1d3`). Nexen execution could not connect to its local control socket (`Errno 1: Operation not permitted`); the built test is not reported as a native runtime pass. The source-driven StartScript handoff model also now models M/X widths for the `$0100` counter case. |
| R2 — genuine near RequestRoom coverage | Partial; no near native pass | Pending-request validator resolves the route-specific RequestRoom entry and rejects a route label inconsistent with the ROM build identity before hooks are installed. The pending Make target is explicitly far-only instead of producing two mislabeled copies. | The former `pending-near` image records `M24RB=1`; requesting `--route near` now fails closed before emulator startup. A true near-only M23A/M25A build attempt (`M24RB=0`, `M23A=1`, `M23B/C=0`) failed assembly: bank 0 exceeded its header boundary and near/far symbols were unresolved. The rebuilt far ROM audits successfully (`3d55021473edcfde5c9f03012db648fe809421a24bc71ede08e80aad155cd86f`), but its Nexen execution is also blocked by the socket restriction. The required real near-route native matrix remains open. |
| R3 — path-cached ROM/map identity | Fixed | ROM, map, listing, and identity are revalidated for each acceptance lookup; parsed symbols are cached only by verified map content. Same-process regressions replace the map and ROM at the same paths, delete the ROM, invalidate identity, and install a new matching tuple without `cache_clear`. | `tests.test_snes_rom_symbol_identity` passes; invalid tuples fail before symbol hooks are resolved. |
| R4 — unknown conditional symbol merge | Fixed | The include linter now evaluates conditional blocks against branch-local symbol environments and merges equal values while retaining conflicts or one-sided assignments as unknown. | `tests.test_poppy_source` covers differing and identical branch assignments, later conditions, one-sided assignments, nested conditions, fail-closed possible includes, and known true/false cases. |

The full documented `make test` run after these changes passed 739 tests with 7
optional-corpus skips. `make validate` passed, including Poppy lint (38 source
files, 2,217 global labels). These are host/source and static-build results;
they do not replace the blocked R1/R2 native execution.

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
