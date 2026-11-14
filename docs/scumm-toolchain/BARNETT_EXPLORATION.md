# Barnett exploration — Milestone E in progress

Milestone D remains accepted at `0740cbca`. This successor work does not
requalify the taxi/map trip or claim the office is playable yet.

## Source-selected route

The original room-2 office door is object34. Open (verb3, OBCD PC65) sets
state1 and clears walkbox16's flags before rebuilding the movement matrix.
Walk-to (verb10, PC50) loads room1 at PC62 only when the door is open.
An isolated original-body host control verifies the open operation.

The candidate persistent action in room1 is Pick up coat (object25, verb11,
PC53): ordinary pickup, global10, state0, classes26/32. The isolated host
control yields owner15→1 and preserves newspaper141 ownership. This is a
semantic oracle, **not evidence of native reachability or a host playthrough**.
The exact eventual input/state must come from the installed original room.

## Observed exit failure and correction

Normal input on the matching D ROM opened the door, retired its object script,
and entered `RoomExitProgram(2)`. Its `soundKludge(13,64)` and flush raised
SCUMM error25. Class-zero iMUSE command13 is a sound-status query; it does not
request a new music conversion. Reference: pinned ScummVM
`10a54c2696126a81ee2b2f7f10b1a8be90ed7711`,
`engines/scumm/imuse/imuse.cpp` and `engines/scumm/sound.cpp`.

The host and native command dispatch now publish the logical result through
v5 VAR_SOUNDRESULT (56). The native query shares the existing logical music
and 256-bit SFX ownership used by isSoundRunning. SFX ownership was previously
compiled only in the M23C fixture; normal M19 runtime now initializes and
maintains it after accepted service requests. The same 32-byte allocation is
included explicitly in the ownership audit. No additional audio buffer,
executable-cache lease or title-specific sound branch is introduced.

Native support is bounded to IDs0..255 and explicit logical start/stop
ownership. First-player (`-1`) and wider native IDs fail explicitly. This does
not certify natural completion of every converted sound, a general iMUSE
player allocator, deferred-trigger playback, or acoustic output. The host's
existing deferred adapter distinguishes queued starts (2) from active (1) and
absent (0), and does not report a cleared deferred entry as queued.

`actor_scene_fixture --sound-status-probe` produces original copyright-free
SCUMM bytecode for start/query/stop, queued start/stop-all and result lifetime.
`validate_scumm_sound_status_nexen.py` observes it under `run_visual_once.py`;
there are no guest memory writes. Process success is separate from semantic
acceptance. The initial native control failed because the ownership table was
not enabled; the corrected initial control observed `[0,1,0,0,0x1357]` at
frame24 with error0. The extended control observes `[0,1,0,0,0x1357,1,0,0]` at frame24,
error0. Supervisor completion: 5.582 seconds, normal exit,
cleanup complete and no owned survivors. This control precedes the additional guard preventing a wider SFX service ID
from aliasing the 256-bit ownership table. The final guarded build also passes at frame24, error0, in 5.576 seconds,
with complete cleanup. Its ROM is `b88edd64c35760c836fe11914477fa66af6f7246afc3c83f809e3f5a0686d286`,
map `4dbaa3b85d55a3ffdacd2b151876e4b1cde5c57fd5b7155a9951b79be90ce140`,
and build identity `eb2e4581da89d4a33b72cac09329f28d560f3465cec179256427e476a61d0405`.
Package identity is unchanged. This is synthetic logical-query acceptance.

- Native fixture ROM: `7a0d2150a5d8cb60c5ba775ad482afdf1d3fc8944c55201365fb961794833fe5`
- Map: `0a93ec461e262183a88407a8de04b247e8fd09a0739bf95eacd53926a3aacbc3`
- Package: `fb29d19dde30fedc721c68d78c4bdac8bd3bb96b8e9773bf51fce4ac63142311`
- Build identity: `c2243b033f2bfcc93fc24a93b89a3fafb9ed652778aa4749f349b4b53c62eca3`

The exact command is retained in `native-sound-status-extended/process-result.json`.
Generate the original source input with
`python3 -m examples.resources.scumm_v5.actor_scene_fixture OUTPUT.zip --sound-status-probe`.
Cook all executable bodies/visuals using the existing fixture profile, then use
the normal streamed actor build with synthetic MAXS and no story overlay.
Run `tools/validate_scumm_sound_status_nexen.py` only through
`tools/run_visual_once.py`; its explicit ROM, output, Nexen/core, MCP-library
and port arguments keep this local native test separate from hosted CI.

## Cutscene callback retirement corruption

Fresh normal-game setup on the experimental E ROM reached the original map,
then failed with variable error2 in LSCR201. The package was intact. Native
write/execute journals isolated a CPU-width defect: the start-cutscene callback
enters the ordinary nonrecursive StartScript retirement scanner with X8.
`ScummV5_C4_StopNumber` declared `.i16` but did not clear the runtime X flag
before its immediate LDX. The CPU decoded the high immediate byte as BRK and
later executed a branch displacement as `STA long,X`. That wrote through bus
address `$001861` into executable WRAM, changing logical PC56 from `$40` to
`$20`. The subsequent variable error was a consequence, not a drawBox defect.
The write preceded the SFX ownership operation; it was not caused by that table.

The scanner now establishes X16 with `REP #$10` before its first indexed
instruction. This changes no C4 scheduling or script-number semantics and
requires no additional memory. A copyright-free fixture installs both original
cutscene callback variables, passes local0=`$1234`, and runs both callbacks
through the normal nested global resolver.

Native positive control `native-cutscene-width` finishes at frame24 with
variables `[2,4660,0,0,4951,0,0,0]`, error0, no BRK execution and no writes through
the executable WRAM mirror. A private negative build removing only this width
correction reaches the **same semantic sentinel and error0**, but produces
three BRKs and a cache-alias write. The validator correctly rejects it. Thus
checking only the sentinel or error counter would have missed the corruption.
Both runs clean up their owned processes; neither is authentic gameplay proof.

Positive identities:

- ROM: `6a88bfaed541ccf64586bf6a15cb2a112c265e4307924d7d206ee638efd5051e`
- Map: `0be2739b8e9661477f793b23269a2a0535bc30702c6bbb30651fb0e2c1f42e03`
- Package: `8da0272e59e7a630ec9f7761bbce207835683c1cca32d6f64bac0218fb6ebf0b`
- Build identity: `9fc054871556d61f0a7b1d103403e4ed00bf108ccad9d40aeb32465dd5722717`

Generate with `actor_scene_fixture --cutscene-callback-probe`; run the existing
supervised validator with `--case cutscene-callback`. Private journals include
`trace-operand-journal`, `trace-cache-mutation`, and `trace-cache-writer`.
Earlier observer limitations remain recorded; an asynchronous hook name is
not a claim of stopped CPU state at that instruction.

## State-selected object presentation

The new host OBIM decoder uses IMHD object IDs; OBIM and OBCD resource order
are not interchangeable. It shares the existing SMAP/ZP decoders, preserves
codec-specific transparent pixels separately from opaque color zero, and
composes in reverse local-object order with parent-state filtering.
Classic v5 object mask strips replace the corresponding background masks.
State-only invalidations are consumed by the normal host composition tick.

The original room2 door's IM01 changes77 background pixels. The feature-gated native state-selected object consumer now passes its
synthetic complete object/actor/mask comparison. Authentic office gameplay
remains **NOT_VERIFIED**; a base-background comparison is insufficient. Object relocation and broader image families also require
coverage before general support can be claimed. All proprietary image bytes
and rendered comparisons remain private.

## Evidence and integration boundaries

Private evidence is under
`/home/chad/SAME-private-evidence/milestone-e-exploration-20261114`.
`office-boundary` preserves the early-input observer failure;
`office-retirement` preserves the actual original exit failure. Neither is
labeled an engine deadlock. All native sessions use private Xvfb/Nexen MCP,
bounded process trees and exact ROM/map/package/build identities.

A changed ROM requires fresh ordinary-game setup. Old D savestates are never
restored into E builds. The progression recovery worktree is untouched.
PR14→PR15→PR16 ancestry remains intact. E is a successor, not an amendment to
accepted D. No automatic merge. Whole-game readiness remains **NOT_READY**.

## Checked object-image integration (in progress)

`SAME_SCUMM_OBJECT_IMAGES=1` extends the existing room-strip preparation path.
The compiler uses the shared source OBIM/SMAP/ZP decoder and stores coverage,
eight palette indexes and foreground-plane bytes per source strip row in
SAMEPKG `SC5OBJ`. Blocks are at most1024 bytes, each with an independent CRC.
ROM contains identity, geometry, parent-state and checked-address descriptors,
not image pixels. All source image states remain represented. Native selection
uses mutable object state, source parent chains and reverse
local-object painter order. V5 clips object height to complete eight-row units;
the source-faithful host compositor and cooker now agree on that boundary.

The camera retains its checked source strip in the first2048 bytes of the
existing3132-byte pending window. The object read leases a disjoint1024-byte
tail. Actor-mask composition instead leases the same scratch base sequentially
through the existing actor ticket. No executable page or additional framebuffer
holds object imagery. Eighty control bytes fit after the mask controls inside
the audited256-byte scene-control allocation. The checked provider now accepts
bounded subranges of the pending allocation, rejecting overflow and any extent
outside it. Its active-metadata extent comparison also rejects limit+1.

Original-source preflight decoded all96 rooms:1372 local object records,
1329 images,10673 checked blocks and5463776 payload bytes. This is compiler
coverage, **not native gameplay certification**. State changes
invalidate a32-bit object generation; staged background installation checks its
ticket before publication, and actor composition waits for the matching image.
The current conservative object-state refresh rebuilds the viewport; ordinary
unchanged-object camera movement retains the existing incremental path.

Public focused tests cover deterministic package construction, per-block CRC,
malformed coverage and lengths, multiblock images, opaque zero, parent states,
mask replacement and show/replace/hide behavior. The source-script scene fixture
uses `--object-images-probe --masks`, cooked with `--executable`. Its existing
native validator adds `--object-images` and refuses registration-only room
inputs before launching Nexen. Synthetic acknowledgements are diagnostic input,
never authentic gameplay acceptance.

Private failed controls remain preserved: the first found short-address ROM
descriptor loads; the second used registration-only input; the executable
control exposed the provider's previous exact-base destination restriction.
The first subrange control found stale letterbox pixels during state refresh.
Mode2 now clears its private stage and hands the complete background to the
existing actor/cursor scene transaction before requesting presentation. It does
not expose a background-only intermediate frame. Repeated writes of an unchanged
state or owner do not advance the image generation.

`native-object-idempotent` passes four complete native captures: show, replace,
a second animation step with overlapping scaled actors, and hide/move/restore.
Each has zero source/INDEX8, INDEX8/PPU and original-palette/CGRAM differences.
Repeated identical source state writes produce exactly generations2,3,4.
The final capture reaches frame4068; the438.982-second supervised run exits
normally with complete cleanup and no owned survivors. This is copyright-free
native graphics acceptance, **not authentic office gameplay**.

- ROM: `30ea41b624a2a28d1b0e164b706c6ba5048862d8c6bb17e42946c353cb7dfe07`
- Map: `944e4572b12d576928f3e9c4a294f44d7380d6326701e42e0b56b8f7443ba377`
- Package: `e759118e00c403fda3cd36dd8b9f545971ce6e0135765edd03693608a91b0610`
- Build identity: `000240c9ecde1d2f054d278d47bf0c541cd0a29b7d392807591cc28bc55e26f8`

The private assembly snapshot contains the same runtime source as this change.
Subsequent compiler descriptor-linkage validation and host boundary regressions
add rejection checks; they do not change the accepted emitted bytes. All96
original room descriptors pass that linkage check. The source snapshot's
private Git SHA is not represented as the later public commit SHA.

Local host suite:1707 run, including12 skipped, no failures. Additional focused
range/index rejection tests pass. `make validate`, pinned Poppy assembly,
4MiB ROM audit and45-region memory audit pass. Hosted native emulation is not
claimed. No timeout is classified as an engine deadlock, and no draw counter
substitutes for complete image equality.

Native corruption control `native-object-crc` flips one selected checked object
block in the copyright-free package. At frame752 it rejects the transfer with
SCUMM error16/provider error6, before any actor scene or replacement publication.
The installed surface captured at frame616 remains byte-identical and its
presentation generation is unchanged. The60.441-second supervised run exits
normally with no surviving owned processes. The faulty package SHA-256 is
`ed59955ca1886b6eaa4952852589610457327311ef9ca646263d36dd24908491`;
the ROM/map are the positive control's identities above. This is deliberately
corrupt test input, not an identity-valid release package.

## Owned room-image correction

A pinned-reference review found that inventory ownership must not suppress a
local room image. `ScummEngine::drawRoomObject` selects state and parent chains;
v5 pickup assigns owner=ego and state=1, which may paint the removal patch over
an object baked into the room background. The initial host and native paths
shared an incorrect owner filter. Both now retain state-selected owned imagery;
SetOwner alone no longer advances the room-image generation.

The unowned synthetic captures above remain valid for their scope. Earlier
private original newspaper captures compared two implementations sharing this
wrong assumption and do **not** certify the original pickup's complete visual
result. Their input and ownership observations remain evidence. The
owned-image fixture adds an explicit ownership transfer while state2 and its
mask remain installed, followed by a separate state0 hide operation.

`native-object-owned` collected four exact source/INDEX8/PPU/CGRAM captures:
show, replacement, a second animation step, and the still-visible owned state2
image. Ownership transfer retained image generation3, as required. The final
state0 hide capture was **NOT_CAPTURED**: at437.330 seconds the supervisor
received SIGTERM from its Codex parent; cleanup completed at439.458 seconds
with no owned survivors. The watchdog did not expire and no engine error was
observed. The overall four-stage run remains incomplete; this is not a full
native-suite PASS. The previous unowned hide/restore evidence remains separate.

Local full suite:1709 tests run,12 skipped, no failures (352.233 seconds).
`make validate`,45-region memory audit, pinned assembly and4MiB ROM audit pass.

- Owned fixture .sfc: `f56f53a12eeee9a42b6786bdd745fe23dc86e0f0fd1a76fc83eb3bbab9ccc793`
- Owned fixture .map: `65e3a5a54b9d969add2df7b45e0d196b817cd6208036a78c44121b5a3fac9127`
- Owned fixture .msu: `3d72ec97452f1481b6314ac5e38d5adb3d0310c50916635631e02154dc332f76`
- Owned fixture .build_identity.json: `5fc2d523831e23c88110037c92687f3733505996ed3f27076e2b8d29f4a74d13`

## Complete-scene observer fence

The corrected authentic ROM160bcc6a now matches the original owned newspaper
state1 patch, inventory and closure exactly (`owned-object-room10-ready`).
A subsequent map observer compared live INDEX8 while SCENE_DIRTY=1 despite an
idle video backend: two cursor pixels differed from the already committed PPU.
The captured record is rejected by the new optional, map-bound scene-control
fence in `capture_committed_surface`. Busy/dirty scenes and changes during
capture cannot qualify as completed live scenes; immutable queued-generation
captures retain their separate fence. Legacy non-scene controls remain valid.

`owned-map-scene-fence` resumes that exact-ROM map checkpoint, with no repeated
taxi input, and obtains complete source/INDEX8/PPU/CGRAM equality for the map
and Barnett. It exits normally after281.580 seconds with complete cleanup.
This is setup continuation, not one uninterrupted taxi trip or office acceptance.

The original entry branch oracle uses the captured bits69=1 and211=0. SCUMM
conditions fall through when true and take the encoded displacement when false:
room1 ENCD PC29 jumps365, the incoming-from-room2 case falls through385→392,
and PC392 jumps523, leading to local210. An earlier private entry note had
interpreted predicate names as taken-branch names; it is explicitly superseded.
The original isolated door/coat behavior remains verified independently. After
pickup sets classes26/32, original coat verb9 prints “It's an expensive topcoat.”
Native office/coat acceptance is still pending.

Observer-change validation:1710 host tests run,12 skipped, no failures;
`make validate` and45-region memory audit pass. Runtime binaries are unchanged
by the observer correction; their exact-ROM checkpoints remain valid.

## State-image refresh after camera scrolling

The next normal Open-door input set object34 state1 and retired its script,
with error0. Its completed generation375 failed visual acceptance:1092
INDEX8/PPU differences in screen column24..31. Offline inspection also found
that the full checked viewport had been copied linearly into circular INDEX8
storage (origin232). The independent source oracle's inset was already correct.

Full object-image refresh now preserves the installed transform and copies via
surface pair writes, including wrap within a row. Camera target movement still
uses the retained/NMI path; after the complete object/actor scene is submitted,
the latest target is rechecked even if motion stopped during I/O. Invalid tile
shadows include all920 retained
characters when scrolling is active, rather than omitting the now-visible24
guard characters. Cached source coverage is reduced to fully replaced columns;
partial edges and old off-screen columns require checked source data before
being exposed again. No allocation, DMA budget, or ordinary scroll policy changes.

The existing copyright-free Mode-3 control now includes full source replacement
at scrolled origins. Nexen ROM
`95d182ebc82b30152de078671f9c20b34504a0c27d94399f89b7e79cbf7e8643`
passes six full-raster comparisons: scroll8, replace8, reverse0, scroll1,
replace1, reverse0. INDEX8 and decoded VRAM differences are zero; actual PPU
screenshots match. Replacements encode920 characters and take548/555 frames;
ordinary source-column updates still encode24 characters in15/16 frames.
These conservative full state-image refreshes are correct but remain costly;
they are not claimed as responsive incremental object redraws.

Evidence: private `milestone-e-exploration-20261114/native-retained-object-refresh`.
The supervisor exits normally after54.322 seconds with no owned survivors.
This backend control does not qualify office gameplay. A rebuilt authentic ROM
requires fresh matching state; the failed prior-ROM office capture is preserved.
