# Controller interface integration (Milestone C, in progress)

SELECT opens a compact page of enabled, named C17 verbs. START opens the
current Ego-owned inventory. D-pad/Y changes the selection, A chooses it,
and B closes the page. The existing sentence mailbox executes actions;
opening a page never enables a verb, mutates ownership, or submits a command.
Choosing a verb first retains it while pointing at a room object. Object
selection and subsequent submission remain separate normal A edges.

Pages use the existing encoded text service and original runtime names,
charset, and palette. The bounded two-line view uses 13 encoded name bytes
per line. Full long-name paging and mixed-charset pages remain limitations;
a truncated malformed control is not reinterpreted as valid text. Inventory
names depend on the existing bounded source-name cache. Cross-room inventory
resource execution is not certified by displaying an inventory page.

Script-side verb disable and owner changes are rechecked before selection.
Controller UI/repeat state owns 24 bytes at `$7E8FE8..$7E8FFF`, immediately
before the existing name cache. The ownership audit includes this allocation.
The selector pool, bytecode pages, and active room buffers are unchanged.

Held D-pad input initially moves two pixels. Subsequent displacement follows
the NMI frame clock, rounded to even pixels and capped at eight per controller
turn. Action/acknowledgement buttons remain edge-triggered. Cursor coordinates
are clamped to the published viewport and converted to source-world coordinates
by the existing hit-test path.

## Native evidence and limits

The original C17 “Open” / “Close” page was presented with Indy, the original
room background, and cursor. Generation 19 had zero INDEX8-to-PPU differences
and zero CGRAM differences. Independent source charset/costume/background
interpretation also found zero indexed and PPU differences. SCUMM error was 0.
No gameplay-state writes were made. The private supervisor exited normally in
244.822 seconds and cleaned up its emulator/display.

- ROM: `3c4f5bdad9a01fe88ce6ed240b275b70cff0ce59c8256075e33b8134e2848ffb`
- Map: `cbd1c366d56367abaa541ad90ff55dbcc1030892e26b8b8195a690136dd0f688`
- Package: `70564585c15538ed04b7f614b5b4d929a07eedf7a8545b510ff0ed66e9ad29d0`
- Private evidence: `/tmp/astra-original-verb-menu-native-20261111/observations`

This image predates frame-paced held movement and corrected camera/message
waits. Its evidence is not transferred to subsequent ROM identities. A later
pickup attempt stopped before submission because the fixed two-pixel repeat
was too slow: a targeted trace measured 16 pixels in 60 emulated frames while
controller turns were separated by composition work. That run is not action
acceptance. The bounded frame-paced correction addresses this measured delay.

## Wait and lifecycle correction

The original action exposed missing host inventory-count dispatch and camera
wait semantics. Host count now reads the same global-owner table as native;
its direct, variable, and expression forms have source-neutral tests. Camera
wait compares eight-pixel logical strips, as the local ScummVM v5 reference
specifies. Pending native camera/message waits rewind their complete two-byte
instruction; presentation completion is a separate service contract.

Changed scheduling exposed a pre-existing lifecycle-child lookup defect:
A8 `TAX` copied a stale hidden accumulator high byte into X16. The captured
pending child and live slot both held selector `$F7`, yet the stale branch
rejected the lookup. Both child-index transfers now explicitly zero-extend.
The actual-instruction regression fails for all 255 nonzero high bytes before
the correction and passes all 256 values afterward. Invalid slots and stale
selectors still reject. These instruction-runner checks are host tests, not
emulator execution.

Persistent-action, inventory execution, scrolling camera, and current-image
native acceptance remain separate gates. This document does not certify the
complete Milestone C or whole-game readiness. Commercial assets and captures
remain outside Git.

### Current integration findings (2026-11-11)

The lifecycle-fixed image (`771bc0992ca30b215f8828233df25ad36f1af6afdc9058c0b378d8727313e264`)
reached the original New York introduction. Generation 44 rendered the
source dialogue with Indy and the viewport; its indexed/PPU comparison had
zero differences. A separate matching-checkpoint trace showed the earlier
partial room image still making conversion/DMA progress, followed by a valid
actor key 96 video frames later. A timeout during that transfer was not an
engine deadlock or a graphics pass.

The normal A edge was correctly reserved for dialogue but was never forwarded
to the generic talk service. The controller now expires only the current
segment's delay and invokes the existing talk frame-end continuation. The
ownership token remains consumed until the scene gate retires it; the same
edge cannot skip another segment or submit an object action. Focused actual-
instruction tests cover matching/stale tokens, unrelated buttons, and repeated
controller passes. Native acceptance of this correction is pending.

The full suite before this acknowledgement correction ran 1,470 tests with
12 skips. The 85 affected tests pass after the correction; full-suite and
current-image native results are recorded separately. Successful assembly is
not native interaction acceptance.

Inventory UI ordering is a presentation adaptation over the current owner
map, not certification of source inventory acquisition order. Inspection of
the local ScummVM reference found that its `findInventory` uses one-based
ordinals over an acquisition list. The existing SAME host/native opcode
instead uses a zero-based scan of source object IDs. This pre-existing semantic
frontier remains explicit; the new owner-count handler mirrors the existing
native representation and does not certify inventory resource retention or
ordered queries. Correct acquisition ordering and cross-room inventory names
remain necessary for broader gameplay.

### Measured scheduler/storage bottlenecks

A read-only 128-video-frame profile restored the identity-matched incomplete
newspaper action (`aac4aa15153c494985839739596a70f23d802a1252fd0f93a55ac9d3307ec589`).
Native execution hooks recorded frame/cycle timestamps at kernel phase entry.
Fourteen storage turns occupied 58 video frames; one turn spanned seven frames.
Mode-3 work occupied 23 frames and visual composition 17. Only five movement
phases occurred: the engine-wide provider gate also blocked movement while
any unrelated checked read was in flight. This is CPU work and scheduling
coupling, not raw MSU device throughput. The 10.309-second supervised profile
made no controller or guest-state writes.

The correction keeps package initialization and room transactions gated,
while an authenticated read blocks its existing per-resource waiter instead
of every activation. Checked READY-page and generation dispatch remain
mandatory. Sleeping C4 slots decrement their timers after freeze/didexec
checks, before executable-page admission. They do not fetch bytes just to
consume a delay tick.

The SAME provider now evaluates the identical reflected IEEE CRC using a
1,024-byte immutable table in its existing package-directory bank. The
request CRC range, initial/final XOR, capacity checks, transfer quantum and
error policy are unchanged. Independent zlib comparisons cover all input
bytes with randomized CRC seeds, adjacent scratch contamination, and requests
crossing service quanta. These are host instruction-runner checks. Revised
full-image native timing and persistent-action acceptance remain separate
measurements, not inferred from the optimization or successful assembly.

### Live camera and distance contracts

The source v5 camera's 10/30 strip triggers now update follow destinations,
respect fast-camera intent, and finish at the actor's logical strip. Normal
panning uses the source's two sequential comparisons, avoiding oscillation at
an unaligned destination. The SNES crop does not change world coordinates.
An adjacent concrete ownership defect was found: C29 actor-hit-test X/Y
scratch overlapped persistent C15 follow/mode/moving flags. Five scratch bytes
now occupy the declared alignment gap after actor-name lengths ($7F3EE0-E4).
The 33-region audit covers both owners and rejects the original alias.
Host/native-source instruction comparisons cover follow thresholds, moving
actors, fast-camera mode, room clamps, and unaligned arrival. Native scrolling
presentation remains an independent acceptance gate.

A continuous native original newspaper attempt reached its walking endpoint
but printed the authored refusal. Its captured SC5LIVE raw point and immutable
projection differed from the live walking endpoint. Walking already honors
matrixOps changes; native getDist incorrectly trusted the cooker's old
projection, even before testing ignoreBoxes or operand ordering. The query now
projects raw coordinates using current flags only for actor-to-object queries,
matching the host and existing walker. Synthetic tests hide a raised box via
matrixOps and require arrival and reachability to agree, while reverse and
ignoreBoxes queries remain raw. No original script or resource is changed.
This fixes the demonstrated contract; persistent-gameplay acceptance still
requires a current-ROM run.

A settled text observation may now nominate an idle, generation-acknowledged
frame for capture. This is only a candidate: independent source rasterization
and full INDEX8/VRAM/CGRAM comparisons must pass before acceptance. It does
not reinterpret overwritten pending text or an incremented counter as visible
text. The older queued-generation observer remains unchanged.
