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
