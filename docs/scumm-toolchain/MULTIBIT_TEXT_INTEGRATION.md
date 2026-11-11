# Native multibit text integration — Milestone B in progress

The source-font rasterization gate passes. Authentic verb/object interaction
remains unverified; this is not a completed gameplay milestone.

## Implemented

`surface_index8` extends the existing text-service facade, indexed surface,
dirty packet producer and NMI-owned Mode-3 presentation. It uses a declared
32-row UI viewport, rather than overlapping live-room metadata with the older
BG2 allocation. Room projection reserves that viewport explicitly. Actor
composition clips at its boundary; cursor restoration participates in damage
publication. Legacy configurations retain their existing overlay selection.

Five original source charsets fit as CRC-checked SC5FNT v2 records plus a source-ID
directory in one ROM bank: 29,146 bytes. Their original 1/2/4-bit source slots,
signed bearings, advances, and byte-sized glyph dimensions survive cooking.
Source slot zero is transparent. Other slots can map to opaque color zero;
text ink and palette colors are not masked to four bits. Missing charset IDs
fail explicitly. Original zero-offset glyphs draw nothing and advance zero,
as in classic prepareDraw/getCharWidth; no adjacent font or fabricated advance
is substituted. The synthetic scene golden hashes change for its absent space
because the former renderer invented a four-pixel gap.

128 bytes at $40:0780–07FF hold raster scratch, request ownership and generation
fence, with mechanical ownership validation. No new framebuffer is allocated.
The old BG2 configuration at $41:F000 is rejected when live SC5LIVE metadata
owns that range. Text bytes/style are captured before a busy surface can delay
consumption. The visible lifetime waits for the actual presentation generation;
hide requests persist until the surface becomes writable. Room/generation
checks prevent stale requests from writing the next room.

`initCharset` updates default string slots 0 and 1 as well as C7 state. C17 HUD
caption lookup rejects uninitialized, absent, hidden and dim verbs; it never
restores authored saved-away verbs. Native talk scanning consumes complete
encoded controls and separates glyph timing from raster byte lengths. Host
text supports multibit source slots, multiline controls, inline ink/charset
selection and exact charset identities. Unknown controls remain explicit.

## Native evidence

A data-only synthetic SCUMM driver displays `SAME text 24` using authentic source
charset 2 over the source room and real costume. It is a graphics diagnostic,
not authentic dialogue or gameplay. No guest acknowledgement or action was
injected. Private evidence: `/tmp/astra-font-native-text-fence-20261110`.

- rom_sha256: `ae55e5785ba90ce513c0a8c9fe57283bf483cd186a0337e16a6d16715f15202f`
- map_sha256: `1d0a3c073acb98eb122dd2be2a4971052fa162fbcd01e9f90fa041cf21a28d09`
- package_sha256: `9de63ae5247247a33c28a4fa1e85e85fce0adf4422f4586600dfd9dd0982ad15`
- build_identity_sha256: `18eb60eaa0e62178141b8e467037f0accb912ad80283082f5e28495f8c067a8d`
- audit_sha256: `bd73798c7c73cb75f9b980306f947a813472dad9c796bf9cac53fc2c4150eb13`
- source_font_sha256: `ce86c2b63044a2399762c0b849af0a30e9074be904218c4ec57239c471d06629`

Source/INDEX8 differences: 0. Source/decoded VRAM differences: 0. Actual captured
text RGB differences against CGRAM: 0. The observer requires a matching completed
**visible text** generation; a later hide or unrelated actor generation cannot
pass. It allows the existing scene to continue animating. The capture preserves
the emulator's full image rather than assuming its screenshot height is always
224. Earlier failed diagnostics remain private and are not upgraded to passes.

The accepted image was assembled from an isolated dirty-source snapshot before
the subsequent encoded-control scan and absent-glyph corrections. Those later
changes have source/host tests and a separately assembled authentic build; do
not transfer this narrow native result to every behavior on a later commit.

## Validation and limitations

1,401 tests ran: 1,389 passed, 12 skipped. `make validate` passes, including Poppy
lint and WRAM/BW-RAM ownership. The native diagnostic and authentic build use
the pinned Poppy DLL and pass ROM/map audits. Hosted CI is separate pending
publication evidence; no hosted Nexen claim.

The indexed native producer retains at most 255 encoded bytes per request.
Longer-message delivery, runtime charset-map
mutation, multiple distinct UI regions, inventory presentation and general
style layout remain incomplete. The current small UI raster supports newline,
inline color and charset, with clipping/wrapping; it does not certify every
SCUMM inline control or every glyph/font natively. Do not force verbs active to
conceal authored startup behavior. Whole-game readiness remains NOT_READY.

## Authored subtitle and replacement ownership correction

The indexed path now reserves $7F:FB80–FC7F for retained encoded message bytes
and $7F:FC80–FD7F for the immutable queued copy. These follow the one-record
18-byte geometry work area and precede actor walkbox state; the mechanical
ownership audit checks the boundaries. The legacy 32-byte path is unchanged.

Replacement retires the old talk owner before scanning the new message so
Stop cannot erase the new HAVE_MSG value. An outstanding text request retains
its message generation and is discarded before writes when superseded. Text
service observes backend completion before actor composition can claim the
newly writable surface. The lifetime starts after its own presentation fence.
Speech-cue words remain encoded, do not rasterize, and set a separate unavailable
voice-realization witness. This does not claim speech playback.

A read-only native checkpoint control captured the original authored room4
subtitle, without synthetic bytecode, gameplay writes, or controller input.
Original font2 interpretation, active INDEX8, decoded VRAM and actual screenshot
RGB against CGRAM all agree exactly. Local evidence is
`/tmp/astra-authentic-dialogue-direct-20261110/observations`; runtime 25.060s,
normal process-tree cleanup. It is dialogue evidence, not an object interaction.

ROM SHA256: `e47a904ed8c2c6e1540d359ee3f62ab1339f346a0da88a811889e89cc9285084`.
Build identity SHA256: `af46470237b28d9d1c6bada4eccda3ae792ec57db6909fb3ef830e05a7d67873`.
The private build is an isolated dirty-source snapshot. The subsequent widened
PC-before diagnostic arithmetic fix has source-instruction tests but is not
part of this ROM. Earlier broad-observer timeouts/stops are not engine deadlock
or graphics-failure evidence and remain preserved.

Current local suite: 1,406 tests, 12 skipped; make validate passes, 27 bounded
ownership regions. Public source-instruction tests exercise long strings,
control operands, replacement state, request generations and frame ordering.
Object-name substitution, distinct UI responsibilities, runtime font-map
mutation, complete long-message pagination and actual object-action acceptance
remain open. Whole-game readiness remains NOT_READY.

## Actor/provider ownership exposed by authored room transition

A normal controller skip through the original room-local override requested
another room. Its 1,880-byte checked metadata was intact in staging, but only
550 bytes reached active storage. Native captures show that actor pose lookup
had overwritten the shared completed request length before room installation
consumed it. READY/READ_OK branches bypassed the existing room/code/scratch
ownership guards; the later scratch check prevented transfer but was too late
to protect the descriptor.

All available-provider paths now pass those guards before lookup or request
writes. Nonavailable/unknown provider states wait. A source-instruction test
covers 315 provider/code/room/scratch combinations and verifies blocked cases
perform no writes, including a completed checked room request.

The corrected ROM
`dd57a0ee2df9b41fad0b7bdec88a996f29bfe870d078c2c77cf5d7ccb7c202a0`
passes that original transition and presents the original office background
and dialogue with resource error zero. The source sequence immediately requests
its next close-up; this is not a settled interactive-room acceptance. Evidence:
`/tmp/astra-authored-room1-owner-control2-20261110`, 50.246 seconds. A prior
observer incorrectly expected Local221 to have started in an earlier saved
frame; it sent no input and is not counted as a native engine failure. The
corrected observer verifies the actual saved room/frame/talk identity and waits
for the source override to be installed before sending one normal X edge.

The second original room4 subtitle, with Indy visible, also matches source
font/INDEX8/VRAM/screenshot pixels exactly on the earlier subtitle ROM. Its
identity-bound evidence is
`/tmp/astra-authentic-dialogue-continue-20261110/observations/comparison-46`.
Do not transfer that comparison to the ownership-fix ROM.

Broad intro observation now distinguishes HAVE_MSG=$FF (a continuation exists)
from an imminent expiry/acknowledgement boundary. It does not poll every frame
for the entire visible lifetime merely because a continuation exists. This
changes observation overhead, not input or SCUMM timing.

## Provider handoff under a paging script workload

Read-only room10 observations exposed a separate scheduling problem: recurring
script cache misses left each completed read owned by the code cache until the
next engine phase, which immediately started another request. Costume loading
never acquired the provider. The late visual phase now reconciles completed
code reads through the existing cache routine, preserving its completion pin
and waiting activation. It does not execute scripts or change residency.

Conversely, a code miss now waits while ACTOR owns the shared scratch ticket,
including READ_OK before consumption. Cached executable hits remain available.
Without this companion guard, the next code request could overwrite the actor's
completed request descriptor. Room cancellation retains its existing priority.
Source-instruction tests cover completion on all three pages, idempotence,
waiter/pin retention, and blocked descriptor writes. All 1,409 local tests ran
with 12 skips; validation, memory ownership, pinned assembly and ROM audit pass.

The updated native original-source startup restores verbs through three normal
cutscene-skip edges and enters the authored interactive scene. Costume1 is
included from the external archive through the existing cooker; no substitute
asset or story script is used. Native observations confirm actor composition,
but the object-action and completed-image comparison remain in progress.
The two short scene checks preserved advancing tile publication and an authored
continued subtitle at their frame limits; neither is evidence of deadlock.
Private evidence is `/tmp/astra-authored-interface-handoff-20261110` and
`/tmp/astra-room10-completed-scene-action-20261110`. The matching ROM SHA256 is
`b578503d90ac1e48c5e63166f4eafe8fb160c2d758520a0d1e3cb6cc038f5d31`;
its isolated source snapshot predates this documentation commit. These narrow
observations are not yet a completed Milestone B acceptance.

## Presentation observation and DMA publication interleaving

Continuous cursor animation need not leave a globally idle scene. The observer
now retains an immutable, locked queued INDEX8/palette generation and compares
it to actual VRAM/CGRAM after that exact generation commits, before a following
DMA. A later CPU-side conversion may be in progress, but a later queue/transfer
cannot satisfy the fence. Source tests reject missed commits, changed room
identity, unlocked/drifting snapshots and mismatched pixels. No counter alone
constitutes visual acceptance.

A room10 text-hide observation exposed a separate kernel defect: all eight DMA
descriptors were inactive while pending remained1, committed341, expected342.
The same values persisted over a read-only64-frame native capture. Enqueue
published the active descriptor and then loaded/incremented/stored pending;
NMI could decrement pending between that load and store. SEI does not mask NMI.

The kernel now owns one explicit byte at `$7E224E` during descriptor/accounting
publication. NMI defers queue processing while owned, without disabling NMI or
input. The same bounded ownership protects the completion-fence snapshot used
by Mode3 and legacy BG2. It prevents both phantom pending counts and torn
committed-plus-pending snapshots. The byte is inside the existing audited
kernel region, before TAD at `$7E2250`; no framebuffer/cache memory changes.

`test_dma_publication_interleaving.py` interrupts the actual source publication
instructions at every boundary, with zero through seven existing requests,
reject exits and counter-wrap fence snapshots. A negative control removes the
ownership writes and reproduces the lost update. These are source-instruction
interleaving tests, not an emulator claim. Pinned assembly/ROM audit and the
27-region memory audit pass; the corrected native startup is being checked
separately. Local suite:1,416 tests run,12 skipped. Object interaction remains
unverified until its original script and readable response are captured.


## First original object response — exact native evidence

Runtime revision `a6051dac241ce98c3cdfddca873f599982a9c7c5` reaches the original
room10 interface through three source-owned X cutscene skips. Ordinary
controller directional edges, A selection, Y cycling and one A submission
execute object140 verb9 (canonical ProgramUnit178, OBCD-relative entry53).
The original response is visible in source charset2. Its encoded bytes agree
with the isolated host execution of the original verb body; source glyphs,
whole scene INDEX8, decoded VRAM and screenshot/CGRAM comparisons all have
zero differences. The actor, original background and cursor remain present.
This is an authentic state-neutral Look action, not inventory progression.

The submission counter changes50->51 exactly once (absolute diagnostic initial
values are not assumed zero). Native room10 remains lifecycle RUNNING/error0;
Ego approaches from(84,60) to(82,59). No guest gameplay writes, synthetic story
or seven-action replay was used. The complete2203-unit directory remains active.

Private action evidence: `/tmp/astra-dma-fixed-original-action-20261111`.
The first observer paired REQUESTED response bytes with the prior HUD image;
that failed comparison remains preserved. A read-only continuation from its
matching-ROM state required a newly composed text generation before capture:
`/tmp/astra-original-response-fence-20261111/observations/response.ppu.png`.
That corrected observation completed in33.574 seconds, normal cleanup. No
input was repeated. The action run itself completed in450.003 seconds under
its600-second process-tree supervisor.

- ROM SHA256: `01bb3ec0766a9db00c3dabffcdb1df246220c5bd4931512c1992cdb5cb5b824f`
- map SHA256: `1058b815ca47f56a39be776da4ba2b7a38cfc4ce47e6d55ac9832f64547dbff6`
- SAMEPKG SHA256: `5f4dfa58b58bbad5c654924380b8277929a6b2b67012a2042c2f3b4645162a16`
- build identity SHA256: `fc019ea20c1e646f0ae96e4fe955f0644387769753918783d223f44c6b1032a8`
- original verb instruction SHA256: `b04a90d9e2ef30246283645ce33b94c6bf486a1ddc02800e4baad4be12618cbe`
- source font2 SHA256: `ce86c2b63044a2399762c0b849af0a30e9074be904218c4ec57239c471d06629`

The caption capture exposed two outstanding issues: its old Use caption was
not evidence that the new Look caption had been presented, and the streamed
name-length adapter dropped the last character. Text unnecessarily restored a
distant cursor and expanded strip damage across much of the screen. Corrections
are being validated separately; this proof does not certify those later bytes.
The final response image is observed1596 emulated frames after submission's
sampled boundary, including delayed observer continuation. This is not raw MSU
throughput or a new walking-latency measurement. The existing640-wide scene is
whole-room aspect-fit into256pixels; it is not a source-faithful camera crop.

Both hosted jobs pass for a6051da:
https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/42970095323 .
Hosted assembly is not Nexen execution. Commercial artifacts remain outside Git.
