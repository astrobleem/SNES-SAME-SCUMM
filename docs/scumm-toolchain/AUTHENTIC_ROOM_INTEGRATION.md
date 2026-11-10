# Authentic room integration

The actor subsystem was merged through PR #13 as `99127067adf6c2264e0217aa52ee91f3f3088e56`.
Main's hosted run [42749057867](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/42749057867)
passed. This branch continues from that commit; the historical progression
recovery worktree and experimental baseline tag remain unchanged.

## Current authentic-room result

The complete 2,203-ProgramUnit package now runs original startup into room 4
and presents Indy against the original indexed room background, with the live
controller cursor. This is original SCUMM startup, not the synthetic costume
script. No object action or seven-action route was needed for this capture.
The source decoder comparison has **zero differing pixels**; the captured
surface versus VRAM and palette versus CGRAM also have zero differences.
This proves an integrated scene, not complete gameplay or all palette effects.

A matching-ROM/package emulator checkpoint restores the exact INDEX8 hash and
actor state. Normal controller edges move the cursor; one empty-floor A click
now walks Indy from (117,138) to the original walkbox oracle's adjusted target
(161,133), box 2, with SCUMM error zero. No guest gameplay-state writes or
object-action replay were used. The corrected committed-pose observer captures the displayed key independently
of the next checked costume read. The 81.837-second matching-checkpoint control
now passes: source costume/background/cursor versus INDEX8, INDEX8 versus VRAM,
and palette versus CGRAM all have zero differences. Whole-surface equality
also rejects old-position residue. Movement flags clear at the adjusted target.
The earlier timeout is retained; it was not evidence of a deadlock or bad pixels.

This capture exposed a separate semantic omission: final-leg completion did not
start the configured stand chore. The display still showed walk frame 2 after
MOVING cleared, while both the host engine and ScummVM start the stand chore.
Commit `d2f0a3c` starts the configured stand chore at final-leg completion for
the moving actor, preserving final-facing behavior and interpreter scratch.
Four source-instruction/host tests cover all 32 actors, widths/flags, unrelated
bits, and intermediate legs. A fresh matching-ROM native control now verifies
stand frame 3/step 0, MOVING=0 and the actor's explicit-animation bit cleared.
The new surface matches the source decoder, VRAM and CGRAM exactly. Equal
stand/walk-frame animation restart timing remains unverified; this is not
certification of every animation command.

Text, verbs and inventory are not yet visibly usable in this build.

## Mapped-ROM interaction repair

Two concrete generated-code defects affected ordinary input. The hit tester
compared a byte object count as a word, accidentally including the adjacent
dirty counter. Commit `6c7e074` zero-extends that count and uses byte flag reads;
instruction-model regressions cover all 256 adjacent dirty values.

The full-directory MSU build also emitted an unreachable ROM-only geometry
dispatcher in bank 7. Its 39,560-byte segment exceeded the mapped 32 KiB window;
a hit-test call assembled as `22 50 19 01` (CPU `$01:1950`, not the intended ROM
helper). Commit `86ae336` excludes only that unreachable static dispatcher in
MSU mode. The segment is now 29,374 bytes (10,186 bytes less), and the call is
`22 86 F1 07` to `$07:F186`. ProgramUnits and package bytes are unchanged.
Both shell and PowerShell builds now require map-span auditing for SA-1 as well
as LoROM. The old map is explicitly rejected before acceptance; the new map
passes. Earlier ROM-audit success did not cover SA-1 segment spans.

The corrected image's fresh authentic scene control completed in 336.999 seconds.
Its normal-input control completed in 60.720 seconds, preserving both successful
walking state and the unsuccessful final-frame observer result. Both owned
process trees exited. No historical state was restored into a different ROM.

- ROM: `50b4812fe6cf357702b40bcffa63ec8de961f9f8a009c6b95a17dc388ba35b32`
- Map: `70b3a4f2f41a190df86b1d4e2521ad8bb53eb1f60c56f68ff2e5b64e8cca8e63`
- Package: `9f66adacf15836f2fdf1ea10485199e43f5b606deb49e26ba4b493aa12e622d0`
- Build identity: `b92e2e1ba72073588673f22c7ecaad13411cc5403183a1e32250765fdcaac07d`

Local evidence: `/tmp/astra-authentic-bank-fixed-scene-20261110` and
`/tmp/astra-authentic-room4-walk-bank-fixed-20261110`. The scene checkpoint is
hashed after asynchronous save completion and emulator exit (`96668b6`); a
nonempty file alone is not restoration acceptance. This checkpoint was then
restored and checked against its exact scene hash in the input control.

Local suite at `96668b6`: 1,362 tests, 12 skipped; `make validate` passes.
[Hosted run 42766444588](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/42766444588)
passed both required jobs on that exact commit. Hosted assembly is not Nexen
execution. Observer `bac2654` has 7 new committed-capture regressions plus the existing
held-pose regressions. Native evidence is local under
`/tmp/astra-authentic-room4-walk-committed-20261110`; its source comparison report
is identity-bound to the captured files. No native ROM bytes changed for this
observer correction. A source audit confirms all 47 tracked assembly/layout
inputs match the immutable build snapshot; observer commits are separate.

The following sections retain earlier evidence chronologically; older
NOT_VERIFIED statements are scoped to their named ROMs, not this capture.

## Final walk-to-stand native checkpoint

The corrected original-source image boots to room 4 in 319.766 seconds of
supervised host execution. Its own saved checkpoint is then restored and
verified. The normal-input walk/stand control completes in 70.801 seconds,
within its 180-second process-tree watchdog. No owned Nexen/Xvfb process remains;
the unrelated user session is untouched.

- ROM: `41a9f510a4a9475f43110be46cb26a171877e8857aba55d7745a8e95c02ed807`
- Map: `affb8c586ddfd16765327e1da9d09ac3a1e902f6f1df93f7fbcc4e2738024f37`
- Package: `9f66adacf15836f2fdf1ea10485199e43f5b606deb49e26ba4b493aa12e622d0`
- Build identity: `7c563758ece264dc4fe87b89c0d12171fdd3a58788872a69f8fef4008fb6be92`
- Final indexed surface: `87b911e009f2c73b162d13af7890fc0da8cce387644fd980f9071109f0886a26`

Evidence remains outside Git at `/tmp/astra-authentic-stand-fixed-scene-20261110`
and `/tmp/astra-authentic-room4-walk-stand-fixed-20261110`. A durable, hashed
private copy (including exact ROM/map/package) is retained outside Git at
`/home/chad/same-private-evidence/astra-authentic-walk-20261110`. The latter control includes
before/cursor-moved/stand-after-walk PPU images, indexed/VRAM/CGRAM bytes, source
comparison, ordinary input observations and the supervisor result. All three
captures have zero source/INDEX8/VRAM/CGRAM differences. Committed elevation is
not separately stored: the comparison predicts the source foot from committed
position and observed zero elevation; exact pixel equality verifies that
prediction for these captures, not arbitrary elevated actors.

Performance: the A edge is sampled in 6 emulated frames; destination and cleared
movement flags are observed 82 frames after its initial input level. The completed
stand image is captured 274 frames after input (192 after arrival). This visible
presentation lag still needs improvement. These are emulated frame intervals,
not raw MSU throughput or physical-hardware measurements. No audio acceptance
is inferred from this graphics control.

## Sparse source poses

The opening source costume has 100 cooked poses, 78 nonempty. Its largest
bounding rectangle covers 23,084 pixels, but its maximum opaque payload is
739 bytes. Its largest run journal (16-byte header plus four bytes per run
and original overwritten pixels) needs only 1,248 bytes. This is a resource
measurement, not a production costume-number exception.

The existing indexed surface service now saves the pixels beneath clipped
opaque runs in the unused tail of the installed SC5LIVE allocation. The engine
validates all spans, captures every run, commits the journal, then draws.
Restoration validates the entire journal before writing and consumes its magic.
Room/generation ownership, exact lengths, row boundaries, capacity, signed
coordinate overflow, and register/stack contracts are checked. No new pixel
buffer, executable-cache lease, package format, or selector scheme is added.
Capacity exhaustion remains explicit; this does not certify every costume or
room tail, multi-chunk poses, multiple actors, scaling, or occlusion.

### Native evidence

A single supervised private-Xvfb Nexen control completed in 69.187 seconds.
It uses original externally supplied costume bytes with a **synthetic SCUMM
control script**, not authentic gameplay. Five completed frames cover facing,
animation steps, and movement. All five indexed images match the host source
costume decoder exactly; VRAM/CGRAM comparison is exact, old-position residue
is zero, and SCUMM error is zero. Test-owned processes were cleaned up.

- ROM: `f539f54c9e0b9cfbff55c59bebf10478810bf23a924ead14605f264f2cf72fd9`
- Map: `1b5fd3d7f2c4c583a272fcb99172e2746b46d620607e57968a82432fd5487d41`
- Package: `281589a71af44c7476d79d7109977439bc94c31832653deb9cb0eb775183297a`
- Build identity: `f9506f780543e7810dc8ba7893efaeea44e1ab89ba3c552e903c375159695ed9`
- Probe audit: `dd1fee2033e5f9a5aaa3306ccf06f12f196dc4690bbaddf41c53cf8e67e3d146`

Local evidence: `/tmp/astra-sparse-costume26-proof-20261110/observations`.
Build: `/tmp/astra-sparse-actor-build.s2rroyv3`.
Immutable source: `/tmp/astra-sparse-ready-source.j1uycv58`.
That snapshot deliberately excludes the subsequent native palette hooks. Its
native acceptance must not be transferred to a later combined ROM identity.
Commercial captures and payloads remain outside Git.

## Palette integration

Classic-v5 intensity derives colors from the original installed room palette,
not cumulatively from the already darkened colors. Direct palette changes
modify the effective palette. The v5 intensity result is capped at 252.
The host oracle uses the existing serialized effective palette overrides.
Host schema 6 also stores an optional original base palette for resource-less
room restores; older resource-backed saves reconstruct it from the resource.

Native allocation is explicit within the formerly unused low BW-RAM reservation:

| Range | Owner |
|---|---|
| `$40:0000–02FF` | Immutable installed source palette |
| `$40:0300–05FF` | Ordered desired palette |
| `$40:0600–061F` | Palette publication/control scratch |
| `$40:0620–073F` | Independent cursor underlay (32-byte header + 256 pixels) |
| `$40:0740–077F` | SCUMM cursor presentation/cache state |
| `$40:0780–07FF` | Still reserved |
| `$40:0800–0FFF` | Existing save storage, unchanged |

Incoming room preflight cannot replace the installed palette. Desired colors
may change while presentation owns the live video palette; publication waits
for the existing surface service and NMI-owned presentation path. Native
portable save migration is not implemented by this allocation. Emulator
savestates remain ROM-specific. Physical hardware has not been tested.

The cold replay helper has an explicit actor-entry capture-only mode. It stops
before object/controller actions and does not label a screenshot as gameplay
acceptance. The existing seven-action route is not rerun for this work.

Whole-game readiness remains **NOT_READY**. Authentic interactive scene,
projection, multiple actors, masks, text, audio and persistence coverage remain
separate requirements.

The combined original-script build assembled and passed the ROM audit:
`0e56a33e862c60fb46f54653d4037b53c64d6bf5ec5b5f408f6e6060d1862886`.
Native palette source SHA is
`60201d5137b47a1710211905917ba373fe488461c520b432a8c9ce64cd960b05`.
Seven source-instruction palette controls pass; this is not native palette
acceptance. The first authentic entry attempt was rejected before emulator
launch because the observer still assumed a selected-build report directory.
The observer now follows the identity-owned whole-source root, with regression
coverage; it does not bypass ROM/map/directory identity checks.

## Original startup observation (not accepted)

The corrected full-directory observer ran once for 241.784 seconds and exited
with a bounded actor-presentation timeout, below its 600-second process-tree
limit. Original startup reached room 4 with SCUMM error zero, but no composed
actor reached the PPU during the observation window. No controller actions
were submitted. The final snapshot has pending presentation generation 6 and
committed generation 4; that snapshot alone does not establish a deadlock or
a renderer failure. The test-owned emulator exited; the unrelated user session
was left untouched.

Evidence remains under
`/tmp/astra-authentic-room-entry-directoryfix-20261110/`. The full final state is
in `process.log`; `observations/authentic-entry.json` retains the source/build
identities and room publication observation. No native acceptance is claimed
for the combined palette build.

The independent host projection oracle now compares sparse actors against
compositing in logical room space followed by the existing SC5VIS aspect-fit
projection. It covers signed offsets, sampling phase, letterboxing, transparent
holes, and opaque mapped-zero colors. Five tests include 100 randomized
differential cases. Native projection is still pending; actor scaling is a
separate unimplemented capability in this oracle.

## Shared actor/background projection

The native compositor now samples signed source-space actor runs on exactly
the existing SC5VIS aspect-fit grid. Room geometry is selected by installed
surface identity/generation. Four binary lower-bound searches replace per-run
full-screen scans. Capture and draw use the same projected coverage; skipped
or repeated source samples are emitted through the existing opaque blitter.
Actor scaling remains independently limited to 255/255 and fails explicitly
otherwise. Multiple actors, occlusion and multi-chunk poses remain pending.

All 96 source room records produce 31 geometry tables. The projection map and
tables occupy 20,960 bytes in explicitly reserved ROM bank 19. Existing bank-10
directories use 29,151 bytes, and bank-12 page directories use 27,820. There is
no additional WRAM allocation; the compositor uses 26 bytes of stack-local
iterator state. Package bytes are unchanged by this ROM lookup extension.

The first projected build rejected its pose before drawing. Assembled bytes
showed Poppy dropping the ROM bank from label-plus-constant long operands.
Header reads now advance X and use plain banked labels. An actual ROM-byte
preflight rejects the original failing image and admits the corrected image.
No compiler version or integrity policy was changed.

The corrected single native diagnostic completed in 77.594 seconds. Five
source-costume images match the independent host projection exactly, with
zero indexed/PPU/CGRAM differences and zero old-position residue. This remains
a synthetic graphics driver, not original gameplay acceptance.

- rom_sha256: `c44ba1ca39d5b29fb743b712d120cd853e80ba0c4facb7157592e77d1b9841bb`
- map_sha256: `6e30609e4fa3905b52ff770427ac5cb8afb9c73952187a5c208e830d037674b6`
- package_sha256: `281589a71af44c7476d79d7109977439bc94c31832653deb9cb0eb775183297a`
- build_identity_sha256: `4e7f23b20168acba6e7e92f4894a59b255785f5d5b9b5ea41de5d0fca9c074e4`
- actor_probe_audit_sha256: `dd1fee2033e5f9a5aaa3306ccf06f12f196dc4690bbaddf41c53cf8e67e3d146`

Evidence: `/tmp/astra-projection-bankfix-proof-20261110/observations`.
Immutable build source: `/tmp/astra-projection-bankfix-source.emed2144`.
The original failing build and its 59.124-second first-error capture remain
preserved separately. The observer's new playable-scene mode uses the existing
authored intro acknowledgements and stops before all object-action replay steps;
it has not yet established an authentic scene acceptance.

## Authentic scene observation remains blocked

The original-script projected build (`ae82819486a047aba09868bc331cf708f37d665445fa438b7f863ac033e6e717`)
passed assembly and ROM audit. Its scene observation stopped after 91.022 seconds
when Nexen advanced 15 of 16 requested frames before its per-call wall-clock
cap. The observer had enabled continuous instruction tracing unnecessarily.
Graphics-only mode now omits that tracing without changing frame, socket or
600-second process-tree deadlines, and persists startup progress/failure state.

A single corrected observation stopped after 119.438 seconds at the same class
of per-call cap. It preserved room68, SCUMM error0, lifecycle RUNNING, CPU
`$15:81E9`, status `$04`, stack `$0FE7`, DB/D=0, and CPU stop state Running.
The requested 16 frames advanced by15. This does not establish engine deadlock
or a successful authentic actor scene. No additional startup retry is planned
without new evidence. Normal intro/object interactions were not reached.

Evidence is preserved in `/tmp/astra-authentic-playable-scene-20261110` and
`/tmp/astra-authentic-scene-no-trace-20261110`. All test-owned emulator processes
exited; unrelated user processes remain untouched. Native captures and package
payloads are local only. The existing full seven-action route was not run.

At projected-actor commit `82bdbc9`, 1,274 tests pass with12 skips, make validate
and memory audit pass, and both hosted checks pass in run `42755315305`.
Subsequent observer-only corrections have focused regression coverage; their
CI status must be read independently.

## Live built-in cursor integration (native verification in progress)

The live MSU renderer previously recorded C7 cursor state but never drew the
cursor. The new path uses the four generic DOS-v5 built-in masks and hotspots,
with the two-tick 15/15/7/8 color cycle. Charset commands 13/14 remain text
semantics. Glyph/hotspot redefinition is explicitly unsupported in this
feature configuration; no source charset is substituted. The host cursor
module is a tested semantic/video adapter; the host interpreter has not yet
been switched to that adapter.

Logical input coordinates remain unchanged for object hit-testing. Only the
screen hotspot uses the installed SC5VIS sampling grid; the UI mask/hotspot
remain 16x16 screen pixels. The service saves a clipped rectangle independently
from actor storage. It restores the cursor before actor restoration, then draws
it last. Cursor-only movement does not reread costume data. Checked bounds,
room generations, background replacement invalidation, rejected publication,
error latches and retained old damage are covered by source-instruction tests.
The new 352-byte ownership lies within the former 480-byte reservation; save
storage, code-cache pages, room staging and resolver ownership are unchanged.

First native cursor run: `/tmp/astra-cursor-native-proof-20261110`, 66.317 seconds,
one capture, **FAIL_OR_NOT_VERIFIED**. Its INDEX8/VRAM comparison differed at
exactly the 24 crosshair pixels. The captured indexed image contains a partially
painted next color while the cached cursor key and VRAM contain the preceding
completed color. The previous-generation PPU commit alone is therefore not a
producer-completion fence. The observer must reject an in-progress composition;
this is not evidence that a draw counter certifies a complete image.

The correction adds a bounded composition-in-progress field to the existing
cursor owner, set before restore/draw and cleared only after accepted
publication. The actor and cursor paths both participate. The observer and
source-image comparison reject this incomplete state. No timeout is increased,
no story replay is added, and the failed capture is retained unchanged.

### Completed cursor/actor native control

The corrected control completed in **115.858 seconds**, with five captures,
zero INDEX8/VRAM differences, zero palette differences, zero old-actor residue,
and SCUMM error zero. All five full indexed images also match independent
source-costume decoding, SC5VIS projection and built-in cursor composition.
The cursor overlaps the actor during this control; moving the actor restores
its old footprint without removing the cursor. Cursor movement through player
input is not newly certified by this neutral-input graphics control.

- `actor-proof.sfc`: `bdf6a1a2eedb8635438d9a5cf8c9b68d8f93dea0c58cc1cd1008109982055647`
- `actor-proof.map`: `b77213363e1bf521e2d19b8245a4476c4ce2c6c67fbee767435c17b44b8c5674`
- `actor-proof.msu`: `281589a71af44c7476d79d7109977439bc94c31832653deb9cb0eb775183297a`
- `actor-proof.build_identity.json`: `2173418cabd0ef5a7808ad5878db2dd4302ac8e17926123974be052a39a498dd`

Evidence: `/tmp/astra-cursor-fence-proof-20261110/observations`.
Immutable source: `/tmp/astra-cursor-source._2oki1fg`.
This remains an original synthetic SCUMM driver with externally supplied
commercial images/costumes, not authentic story or interactive acceptance.
The earlier failed run is retained. No payloads or captures are in Git.

Validation at the cursor checkpoint: 1,312 host tests, 12 skips; `make validate`,
pinned assembly/ROM audit, WRAM/BW-RAM audit, Python compilation, tracked JSON
and Bash syntax pass. Hosted CI is reported separately for the pushed commit.

### Authentic room-4 observation after cursor integration

The original full-directory startup run
`/tmp/astra-authentic-cursor-scene-20261110` ended after 320.803 seconds,
without a watchdog overrun or remaining owned emulator. It reached room 4,
lifecycle RUNNING, error zero, and performed only the established intro
acknowledgements—not the seven object actions. Actor visibility was **not
accepted** within the bounded capture.

ROM: `60161ea762ea0f55cd1305360620bacd437407fc39d30ddb7e4544172d9129ff`.
Build identity: `e54df53fa2da4c54b944a68009db9a5e4364d662500f9927b1b84fd1c9f468bb`.
Immutable source: `/tmp/astra-authentic-cursor-source.80ov83at`.
The source-bound final slots were Local221 at PC19, Global75 at PC7,
Global79 at PC165, and a frozen room-owned activation at PC423.
The actor's 534-byte costume request completed with provider error zero,
but actor composition remained pending while Mode-3 was CONVERTING/locked,
pending generation9 and committed generation8. Producer next-generation10
is not proof that the backend accepted that generation. The captured engine
entries/returns both advanced to1417. This does **not** establish a deadlock.

Offline inspection found two concrete publication risks: palette installation
copied RGB without issuing PALETTE_WRITE, and CanWrite did not recognize an
already queued PRESENT before backend event consumption. Local221 and Global79
contain no palette writes; repeated palette starvation is therefore not proven
by this evidence. Conversion scan/candidate counters were NOT_CAPTURED. The
next bounded observation records them rather than inferring a cause from time.

Hosted CI on `1893b39` passed both jobs in run `42759128321`: 1,318 host tests,
12 skips, pinned assembly and ROM audit. Hosted CI does not execute Nexen.

### Publication ownership and cold-readiness corrections

Palette RGB installation now transfers a dirty intent to the video service.
Dirty/damage publication reserves the complete packet group and emits
PALETTE_WRITE before PRESENT; failed queue insertion retains the intent.
The existing surface-state byte +0x43 holds the flag, within its 0x44-byte
allocation. CanWrite treats a queued PRESENT as ownership even before backend
consumption, scanning only the bounded live FIFO. It preserves X/Y and P except
its carry result. Actor/cursor composition precedes palette-only publication;
an unfinished composition is never exposed by the palette flush.

A corrected-build native startup stopped at frame92 with resource error16,
run `/tmp/astra-authentic-publication-scene-20261110` (20.243 seconds).
A separate first-error breakpoint observation ended at its200-frame limit
(19.809 seconds), without reaching ScummV5_SetError: this does not identify
the direct writer. Both are retained as failures, not acceptance.
The captures showed ROOM_READY249 and23 before any room had been installed.
Source inspection confirmed the latch had no boot initialization; it was
cleared and armed only during room installation. Engine boot now explicitly
clears it for the generic controller configuration. This prevents power-on
WRAM from authorizing premature actor/cursor presentation. Native confirmation
of the corrected startup remains separate from the source invariant.

The observer also mislabeled address7E2364 (C1_HOLD_AFTER) as VM PC. It now
reads the true PC at7E2300 and reports the hold field under its own name.
Thus the failed capture's42496 value was not a corrupted VM PC; actual PC13625
matched the saved Global1 continuation. No historical report is rewritten.

## Authentic original-script scene and restored input

Corrected native capture: `/tmp/astra-authentic-coldinit-scene-20261110`.
The private supervised run took324.963 seconds and exited normally. Room4,
RUNNING, error0; actor1 is at(117,138), costume2, frame6, facing180, scale255.
Presentation producer/pending/committed generation47 agrees; backend is idle,
unlocked, queue empty, with zero rejected PRESENT/dirty/palette packets.

- ROM `dca4509f1f21e64bef7104469b982c1c16e3a5a207708ef23dc9b372a89ec8aa`
- Map `7c9bb2db3bf8c767a9f0b11c893abe2cdd04f51131425a86f7e3e103ba57c461`
- SAMEPKG `9f66adacf15836f2fdf1ea10485199e43f5b606deb49e26ba4b493aa12e622d0`
- Build identity `60ccabf6095dc5308c6e48df461b681988c251c9f7f1b2ebb8e441e4d9d7ce`
- INDEX8 `6e66d01fe602c0b4e791528656a521802076fa2bc3e5cd788d31a113c940d7ed`
- Original costume source `07e0c506e7d365e7210a6e8b380fa5e6b571d141aee4a476e61490d6b8ca0f2e`

The immutable build snapshot is1048878bacfbcc00d3a646e2881577c22d869ad7,
not the later publication commit. All35 tracked assembly inputs match
1ffb289adfb4e5e8ab90aeaa329a5e9f82a3471e byte-for-byte; the identity retains
its actual snapshot provenance. Local linkage evidence:
`/tmp/astra-authentic-native-source-linkage.json`.

Offline source comparison `/tmp/astra-authentic-room4-source-comparison.json`
uses the original costume decoder, stored SC5VIS backdrop, source-grid projection
and builtin cursor. It checks the restored override mask: none of the16 used
source palette slots is overridden. It does not mistake phase-local palette
scratch for persistent metadata. Commercial captures remain outside Git.

The first checkpoint-input attempt failed on a Python predicate-arity error.
The second verified the Right edge but the observer skipped its final allowed
boundary and demanded a future frame after the current committed frame; a new
composition could invalidate that artificial stability requirement. Actual-method
host tests now cover terminal readiness, terminal failure and no future advance.
The strict generation/lock/queue/composition fence is unchanged. Historical
failed reports remain unchanged. The corrected observer captured Right input
and exact indexed/PPU output in `/tmp/astra-authentic-room4-walk-20261110` before
that run stopped on the separate floor-click failure (50.163 seconds total).

Hosted run [42762004285](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/42762004285)
passed both jobs on1ffb289:1,344 tests,12skips, static validation, pinned Poppy
assembly and ROM audit. GitHub-hosted checks do not execute Nexen.

## Next text capability boundary

Original startup selects a2bpp charset. The current native SC5FNT consumer is
binary-mask-only, hardcodes Font0 and has an80x8 overlay. Authentic charset1
includes glyphs taller/wider than that contract; charset2 needs source-slot
color mapping and authored charset selection. The current build has text
presentation disabled. A visible cursor and actor are not a usable verb panel.
The bounded next integration must extend the existing font cooker/glyph service
and projection, not substitute fake dialogue or a second renderer.

The opt-in source decoder now preserves continuous MSB-first1/2/4bpp slots,
including nonzero slots mapped to screen color zero. Its authority is ScummVM
`CharsetRendererClassic::drawBitsN`, source revision
`10a54c2696126a81ee2b2f7f10b1a8be90ed7711`. Existing binary-mask consumers
still reject multibit input before drawing/cooking; this is source-decoding
coverage, not native text support. The actual external-source census gives
charset1:110 glyphs, max13x16; charset2:108 glyphs, max39x10. Original byte
identity and measurements are retained locally in
`/tmp/astra-authentic-charset-source-audit.json`.
