# SAME MSU-1 live SCUMM room resources

This is a feature-gated integration of the existing SCUMM v5 engine with
SAME's checked MSU-1 package provider. The original native acceptance used a
copyright-free synthetic game; a later bounded external-source experiment now
also consumes the selected DOS-CD FATE route through the same generic
representations. This is not full FATE streaming and does not add a second
room parser or room-transition scheduler.

## Implemented live consumers

The compiler projects already parsed/cooked `RoomIR` into deterministic
`SC5LIVE` records and `SC5VIS` visual records. The ROM contains the checked
record directory (offset, size, CRC and identity), not a second copy of these
payloads in streamed-room mode. SAMEPKG remains the data source; SC5ROOM,
SC5LIVE, SC5VIS and palette reads use the existing serialized 32-bit MSU
cursor and are checked before publication.

| SCUMM consumer | Feature-mode source | Scope/status |
| --- | --- | --- |
| Transition/header record | Checked SC5ROOM | Validates target room and lifecycle metadata before commit. |
| Objects and object state/placement | Active checked SC5LIVE | Existing engine-facing object state remains in WRAM; source records, names and placement are installed from this room record. |
| Object verbs | SC5LIVE carrier/verb directory plus MSU-backed ProgramUnit body | Individual verbs retain entry PCs and resolve through their existing shared object carrier. |
| Room-local script directory | SC5LIVE local and bundle tables | Canonical ProgramUnit IDs are resolved through the resident resolver. |
| Walkboxes, geometry, routes and portals | Active checked SC5LIVE | Installed into the existing movement service; no ROM table fallback in live mode. |
| Entry/exit lifecycle | SC5LIVE ProgramUnit IDs and the existing M24R-B lifecycle | EXCD/ENCD order is retained; the outgoing room remains installed until its exit/retirement boundary. |
| Background pixels and palette | Checked SC5VIS plus checked palette record | Pixels enter the indexed active surface; the existing Mode-3 converter/DMA path writes PPU VRAM and CGRAM. |
| Actor placement/camera | Existing SCUMM runtime state and services | Actor/camera state is not a room asset payload; room geometry and live visual surface are room-backed. |
| Object names | Validated length-prefixed rows in the compact SC5LIVE v4 active record, copied to the existing bounded object-name cache | General strings, dialogue text, and font/charset data are not part of this adapter. |

The feature build has no embedded copy of the SC5LIVE/SC5VIS payloads and no
fallback to generated ROM object, local-script, movement, or visual tables for
the live-room consumers above. Compiler/runtime directory metadata remains in
ROM. This is required to locate external package bytes and is not the room
payload itself. The bounded authentic FATE experiment uses this contract for
the selected route resources in rooms 3–7 and 68; it does not imply that every
source-game room or resource codec is supported.

## Transaction and memory ownership

Room transitions use the existing pending-room and M24R-B lifecycle state
machine. Incoming SC5ROOM and SC5LIVE descriptors are checked before the
outgoing room is retired. V4 SC5LIVE metadata is fetched in bounded chunks;
each checked chunk is structurally preflighted before EXCD. After EXCD, the
same chunks are fetched and CRC-checked again before copying to the active
record, which is then validated in full before the existing consumers can
observe it.

V4 route data is a separate SC5ROUT resource. It is checked during preflight,
but the pending buffer is reused for metadata installation. The route resource
is therefore fetched and checked a second time after installation, immediately
before validation and expansion into the existing movement table. This closes
the gap where preflighted bytes could be replaced in the shared staging window.
Palette and pixel records are also checked before room publication and ENCD. A
pre-commit failure leaves the old room installed. A failure after irreversible
EXCD retirement enters the explicit resource-error state; the runtime does not
claim rollback.

The M24R-B commit path can resume after asynchronous visual reads. A
transaction-scoped `old_bundle_released` bit makes retiring the outgoing
resolver bundle idempotent across those resumptions; it is reset by the next
accepted room request, not by each resume. The native route verifies four
bundle loads and three releases for its four room commits, matching the host
residency simulator rather than counting resume entries as additional releases.

The SA-1/BW-RAM layout is mechanically declared in
`runtime/snes/carriers/sa1_bwram_layout.json` and checked by the WRAM/BW-RAM
ownership audit. Relevant live-resource allocations are:

- `$40:13C4` onward: separate 3,132-byte pending metadata/resource window;
  metadata transfers are at most 2,048 bytes per checked chunk.
- `$41:E800` through the exclusive end at `$42:0000`: 6,144-byte active
  SC5LIVE v4 record. It owns the Mode-3 fixture/reserved tail while this live
  profile is active; Mode-3 writes exclude that range.
- `$41:E200-$41:E4FF`: 768-byte visual palette staging/active palette area.
- `$41:0000-$41:DFFF`: 57,344-byte tile shadow used as bounded pixel staging.
- `$40:2000-$40:FFFF`: 57,344-byte active indexed surface.
- `$7E:1000-$7E:17FF`, `$7E:1800-$7E:1FFF`, and `$7F:1000-$7F:17FF`:
  three separate 2-KiB ProgramUnit cache pages. The bank-$7F page occupies
  the audited gap after object-name storage; no page overlaps active room
  metadata or generated variables.

The active record is not a full contiguous copy of the normalized source
record: routes are external, sparse portals are compact, and runtime tables
retain only what consumers need. In the canonical DOS-CD corpus all 96 active
records fit 6,144 bytes; the largest is 6,081 bytes (room 66). All 96 SC5ROUT
records fit the pending bound; the largest is 3,118 bytes (room 51). Eleven
SC5LIVE records require more than one metadata chunk. These are measured
capacities, not a claim that every room is playable. The active and pending
metadata, visual buffers, indexed surfaces, cache pages, resolver, C4/C19,
controller, name cache, and save validator are mechanically checked for
overlap.

Visual records continue through bounded checked reads into their dedicated
staging. Room-resource buffers and bytecode cache have separate ownership and
generation rules. A failed validation never publishes a partially received
record or executable body.

## Performance and limits

The live-room feature uses a 256-byte maximum MSU transfer budget per service
turn (the general provider default remains 64 bytes). Reads are resumable and
share the serialized provider cursor, checked ranges, and CRC validation.
Measurements below are from Nexen, not physical FXPAK hardware.

### Bounded authentic DOS-CD FATE route

The current acceptance traverses the complete established route
`0 → 68 → 0 → 4 → 5 → 6 → 7 → 3`. It uses the canonical DOS-CD profile
(`indy4-fate-dos-cd-en`, DOS CD English, full voice (1993)) and a selected
287-ProgramUnit package for the six rooms required by this route. This is not
the entire 2,203-unit backend directory or whole-game streaming.

The fresh ROM-backed control and streamed experiment are separate builds.
Static control v25 has ROM SHA-256
`d87704d6d9d0e2e17b0ab72b1c56cfeee239b584458e26e228ac9f36916132dd`, map
SHA-256 `3ecb8f1bb51bc4fe67410c1a123b515e0939c628f4645016292b222af754078b`,
and build identity
`df3d85e2be222dae9e8d660d9c4a15cd6c4c1b873ca315e2e226b72ad774167f`.
The streamed v113 build has ROM SHA-256
`59027f2cc04c41c3abd3fa1cd7741b79086545bfbd5c9a1fd223f1c14f02ea5b`, map
SHA-256 `7850e76a4aa6482941604ab0c77bd464c1247281c6d446aa118d3e67d08f2db7`,
build identity
`2a64eac003338cea13ec0ff159b456713d9ee5a0d9fe77080db1ec1f9c92ed99`, and
SAMEPKG SHA-256
`32bea432e369a2853b917a06f283c8d9b67669354462541749ac7d94727a301b`.
The canonical ProgramUnit directory SHA-256 is
`07524e9b170c60c4a5f04100062d5baa1597ce2a5ba7434a40772a774084c920`.
The external source archive SHA-256 is
`0f3fc396642c800069d31ab9a087b314f1bb1612d37accbe13b6013219ac94f0`.

The earlier newly built static control did not reach room 4 because its replay
helper passed an unsupported keyword to `_room7_runtime_context`; this was a
harness error, not an engine or resource-selection failure. The helper was
corrected and the isolated static v25 replay then passed. A later streamed
continuation completed native execution but raised an `UnboundLocalError`
while assembling its JSON report. We did not count that raw exception as a
pass: a recovery tool checked the partial report's route, all seven one-shot
actions, runtime snapshots, and identities before emitting a recovered report
with explicit provenance. The native route was not re-executed after this
report-only exception.

The seven submissions were exactly once: room 4 Open trapdoor, room 4 Use
trapdoor, room 5 rope, room 6 books on statues, room 7 Lost Dialogue of Plato,
room 7 object 118 verb 10, and room 7 object 119 verb 10. Normalized static /
dynamic comparison passed all seven checkpoints, including live-script
identity/status, lifecycle, progression state, object state, actor state,
input ownership, and errors. Selector bytes and scheduler timing are
normalized because they are implementation-specific. Room-7 dispatch
observed the generic object-carrier relationships to
`RoomLocalProgram(room=7,local=207)` and
`RoomLocalProgram(room=7,local=201)`; the latter reaches room 3 without
title-specific resolver behavior. The final checkpoint is room 3, SCUMM
error 0, lifecycle RUNNING, Ego in room 3 at `(71,142)`, and expected
room-local 213 active.

The streamed route's cumulative provider byte counters at checkpoints were
1,327,568 (room 5), 2,573,984 (room 6), 3,985,548 (room 7), and 4,964,642
(room 3). These include executable-page and room/visual traffic. The runtime
exposes a shared 16-bit “last request started” timestamp that can be overwritten
by either a code-page or room-resource request, so the measured checkpoint
intervals of 292, 266, 453, and 165 frames (counter wrap accounted for) are
**not** isolated room-load durations. For room 4, transition-to-ready was 32
frames; subsequent settle/presentation work took 173 frames in the recorded
interval, followed by a 640-frame final presentation drain. These must not be
conflated with older 25-frame publication or 1,589-frame end-to-end values,
which came from different builds and timing definitions. Exact per-room
request/CRC/presentation timing remains a measurement limitation.

### Visual reconciliation

An earlier room-4 comparison reported 892/896 matching PPU tiles. The four
indices were 736, 740, 744, and 764 (tile row 23; x positions 0, 32, 64, and
224). They were zero-filled background tiles, not actor, cursor, text, or
foreground overlays. The Mode-3 invalid-shadow path skipped uploads for blank
tiles, leaving old VRAM contents. The generic renderer was fixed to upload
zero-valued tiles too; the comparison was not weakened. After presentation,
room 4 matched 896/896 tiles. Settled room-6, room-7, and room-3 snapshots
also report 896/896 PPU tile matches and no mismatched background tiles. The
continuation evidence does not capture an equivalent full-PPU comparison for
room 5. SC5VIS indexed surfaces and palettes are checked from package records
before installation. These results cover this compiled indexed-pixel route,
not every original FATE graphics codec.

The selected package includes six SC5LIVE records: room 3 (1,449 bytes), room
4 (1,646), room 5 (2,062), room 6 (2,266), room 7 (2,475), and room 68 (768).
Each of the six SC5VIS records has a 57,344-byte pixel surface and 768-byte
palette. Route-specific objects, locals, walkboxes, and verb carriers are
generated from the external source archive. Program bodies and live-room
payloads used by the dynamic build remain package-backed; ROM contains
resolver/resource identity metadata, not hidden copies of those payloads.

### PCM and fault controls

An original Winston PCM diagnostic track was active during the streamed
route's startup and room-4 external reads. In the 66.721-second capture while
the finite track was active, one silent 20-ms window was measured (maximum
20 ms); room-4 reads did not correlate with an additional gap. Longer silent
regions in a separate long capture occurred after the finite PCM track ended.
This is emulator concurrency evidence only, not physical hardware acceptance
or FATE voice/music support.

Fresh Nexen fault controls passed with synthetic package data. A corrupted
executable page produced explicit CRC error (SCUMM error 16), left the page
FAILED rather than READY, and did not execute post-corruption markers. A stale
page-generation reference produced error 16 before any marker executed. A
corrupted incoming SC5LIVE record failed CRC validation before publication;
room 1 remained installed with its original active-record hash and the room
resource failure count incremented. The first room-fault attempt used an old
incompatible fixture schema and is not counted; the freshly rebuilt
current-schema ROM passed. These controls do not certify every timeout or
capacity combination.

The streamed ProgramUnit cache has three 2-KiB instruction-aligned pages. A
canonical DOS-CD FATE backend-directory audit measured 2,203 selector-bearing
ProgramUnits and 1,000,867 body bytes. The largest body is 21,002 bytes
(`RoomLocalProgram(room=27,local=208)`); 78 bodies exceed 2 KiB, 33 exceed 4
KiB, 16 exceed 8 KiB, and three exceed 16 KiB. The largest complete object
carrier is 2,116 bytes (`ObjectProgram(room=92,object=1195)`) with verb entry
offsets retained in its directory. A copyright-free 21,271-byte body passed
native cross-page branch/yield/resume acceptance. This does not certify all
2,203 FATE ProgramUnits for semantics or every possible simultaneously pinned
working set.

Original SCUMM background codecs, all image variants, costume codecs, fonts and
charsets, general text resources, sound/iMUSE assets, and portable streamed
save-state reconstruction remain separate limitations. SC5VIS is a compiler
owned indexed-pixel representation, not proof that every original room image
format has a generic decoder. No full-game FATE streaming or playthrough is
claimed.

## Status

- **IMPLEMENTED, feature-gated:** checked live metadata, object/name/verb
  directories, room locals, walkboxes, indexed surfaces/palettes, and room
  lifecycle integration for synthetic rooms and the selected authentic FATE
  route rooms 3–7 and 68.
- **NATIVE-VERIFIED:** fresh static and streamed controls agree at the seven
  route checkpoints. The dynamic route reaches settled room 3 with error 0
  and the accepted actor/local state. Full PPU comparisons are exact for
  rooms 4, 6, 7, and 3; room 5's full-PPU comparison was not captured.
- **DIAGNOSTIC RECOVERY:** the final streamed native continuation completed,
  but its report writer threw after execution. A recovery utility revalidated
  saved runtime evidence and recorded provenance. This is not a clean run of
  that report-writing path, although the fresh static replay and native fault
  controls completed normally.
- **PARTIAL:** only route-selected ProgramUnits and six room bundles are
  included. Whole-game execution, all original graphics/costume/charset
  codecs, general text resources, complete sound/iMUSE assets, portable save
  reconstruction for streamed scripts, and physical hardware operation
  remain unproven. This bounded replay is not a claim that FATE is playable
  end-to-end.
- **PLANNED:** per-resource request/CRC/presentation timing records that do
  not share an overwritten timestamp; broader resource codecs and audio
  conversion; portable streamed-save migration; and physical hardware tests.

## SC5LIVE validation invariants

The native v4 active record is bounded by the 6,144-byte active metadata
allocation. Its 16-bit length is checked before any record bytes are published
to that allocation; 6,143 and 6,144 are in range, while 6,145 is rejected.
The host decoder applies this bound to the compact v4 bytes only. Its expanded
legacy-shaped validation view has a separate 65,535-byte format bound because
external route rows and compact portal data can expand during normalization.

Each SCUMM v5 `BOXM` route-matrix cell is either a walkbox index in
`[0, box_count)` or `$FF`, the no-route sentinel. This remains true after raw,
RLE, or sparse-row decoding. Sparse rows encode only actual next-hop entries,
so `$FF` is not a valid sparse entry value. Container CRC validity authenticates
the bytes; it does not waive these semantic bounds.
