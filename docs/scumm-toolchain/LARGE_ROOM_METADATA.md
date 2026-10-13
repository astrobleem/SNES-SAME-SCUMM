# Large SC5LIVE room metadata

## Representation and compatibility

SC5LIVE v4 is the sectioned live-room representation used by the feature-gated
MSU-1 room path. The host decoder continues to accept v2/v3 records. V4 keeps
the tables needed by native room consumers in a compact, validated active
record and stores the route matrix in a separate checked SC5ROUT resource.
Sparse portal rows and deduplicated descriptors avoid retaining the old dense
box-count-squared portal payload in active metadata. The route matrix is
encoded by rows and expanded into the existing movement table only after the
checked route bytes are available.

This is not a second room parser: the compiler projection and native adapter
preserve the same room/object/local/verb identities and entry PCs. Object,
name, walkbox, local-script, bundle, and movement consumers continue using the
existing SCUMM engine APIs.

## Canonical corpus measurements

The current clean DOS-CD profile run represents 4,108 semantic executable
identities in 2,203 selector-bearing ProgramUnits. It emits live metadata for
all 96 indexed rooms; room 0 remains the resource-less lifecycle case.

Across the 96 records:

- Total v4 active metadata: 157,980 bytes.
- Largest active record: 6,081 bytes, room 66.
- Largest normalized v3 semantic record: 11,237 bytes, room 66.
- Eleven v4 active records exceed the 3,132-byte pending window and are
  transferred as CRC-checked chunks of at most 2,048 bytes. The older
  preflight's "oversized room" count used a different, pre-v4 serialization;
  it is not directly comparable to these compact active-record lengths.
- Every active record fits the 6,144-byte active allocation.
- Largest separately encoded SC5ROUT resource: 3,118 bytes, room 51; it fits
  the pending capacity.
- Expanded route matrices account for 41,239 bytes across the corpus.

The preflight covers 96 source rooms plus resource-less room 0. All 96
SC5LIVE v4 records and all 96 indexed SC5VIS records have valid package
descriptors, lengths, section bounds, and checksums; each SC5LIVE/SC5VIS pair
is marked `native_room_loadable` by the current capacity/representation
preflight. This is a bounded loader claim, not a claim that every executable
semantic, visual codec, or room behavior is certified. SC5ROOM retains the
complete cooked source records for provenance; live mode consumes SC5LIVE,
SC5ROUT, and SC5VIS rather than silently falling back to those ROM records.

Room 66 has 61 walkboxes, 37 objects, 13 object-verb entries, and 17 room
locals. Its v4 active record is 6,081 bytes, leaving 63 bytes in the current
active allocation. Its route resource is 871 bytes; the decoded movement
matrix is 3,721 bytes. Room 51 has the largest external route resource.
Per-room table sizes, hashes, package offsets, and capacity decisions are
available in the deterministic generated `room-resource-preflight.json`.

The 6,144-byte active allocation is at BWRAM `41:E800` and intentionally owns
the Mode-3 fixture/reserved tail while the live-resource profile is active.
Mode-3 write paths exclude that range. The separately audited pending
metadata/resource window remains 3,132 bytes. Room pixels, palette, indexed
surface, tile shadow, and the three bytecode-cache pages have distinct
allocations. The third bytecode page was moved out of the active-room range.
The mechanical BWRAM/WRAM ownership audit is required on every relevant build.

## Transaction and validation

Incoming v4 metadata is first read in bounded chunks and structurally
validated before the outgoing room is retired. The route resource is checked
and validated in that preflight as well. After EXCD, the metadata chunks are
fetched again into the active allocation; each provider CRC is checked before
copying. The complete installed record is then validated before consumers can
use it.

The pending window is reused for those metadata chunks, so it no longer holds
the previously preflighted route bytes. The runtime therefore fetches and
checks the route resource again after metadata installation, immediately
before expanding it into the existing movement table. This avoids consuming
unvalidated or overwritten bytes. A failure before the lifecycle commit keeps
the outgoing room intact; an error after retirement is reported through the
existing explicit room-resource failure state rather than being described as
a rollback.

The v4 active metadata is not a single contiguous copy of the original larger
record. Immutable source identity/provenance and per-resource checksums remain
in package metadata; runtime consumers receive the compact projection and
checked route data. No room payload fallback to generated ROM tables is
introduced in the live-resource mode.

## Evidence boundary

The whole-source host preflight currently establishes that all 96 records are
structurally valid, their section bounds and hashes are valid, all active
records fit 6,144 bytes, and all route records fit 3,132 bytes. Native
acceptance must be reported separately: a passing native room load proves the
tested record and consumers, not a full-game visit or semantic certification
of that room. The package readiness remains `NOT_READY` for whole-game
execution while semantic, graphics/resource, audio, persistence, and
unresolved-dependency frontiers remain.

## Native large-room evidence

The original copyright-free native fixture was expanded to a 19,680-byte
normalized semantic record (larger than the measured authentic room-66
record), then compiled to a 6,117-byte active v4 record plus its checked
route resource. Nexen loaded the code and room data only from SAMEPKG, exercised
objects/names, shared multi-verb dispatch, movement data, transition and
revisit, and matched the host markers. Room/resource hashes and indexed
surface/palette checks matched; no ROM payload fallback was present. The
control ended with error 0, stack `$0FFF`, seven peak resident selectors, no
stale reference or exhaustion, and no PPU mismatch after presentation.

The authentic DOS-CD package was also used by generic native room-metadata
diagnostics (these are not authored gameplay progression). The following
records were observed as the active room and hash-checked against SAMEPKG:

| Room | Active v4 bytes | Objects | Verb entries | Locals | Walkboxes | Matrix bytes | Native ROM SHA-256 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4 | 1,354 | 15 | 38 | 23 | 10 | 100 | `bcff378445211d7775d9a6ea907b0c36d23fdaed06278d8c01a36bb7e9e7e9fb` |
| 40 | 3,442 | 26 | 83 | 36 | 40 | 1,600 | `80e1c124e4d6ec084fc226b578e6bd75cbb544b419ac7dd21c97a34ada1de38` |
| 43 | 4,583 | 22 | 156 | 16 | 64 | 4,096 | `009d1138ad9366813ae21effd6d25f5fa6a352f7914f5aed4fd615fde7b77279` |
| 51 | 4,345 | 46 | 65 | 7 | 64 | 4,096 | `9218e5ad65d49d60d2edf8d20cc671262bf65f987ff8b001d530932ceb110c3f` |
| 55 | 4,800 | 66 | 31 | 19 | 64 | 4,096 | `ec7a9ffd5bc88edcdc10d64edd830397d591c18dc90c82420de7f9896974b73d` |
| 66 | 6,081 | 37 | 13 | 17 | 61 | 3,721 | `510322c308ed63b1eddf0aa124b8cd6b9bce33b8b487e7a29f29036c6ce2125e` |

The probes' request-to-room-observation measurements were:

| Room | Checked bytes read | Storage service turns | Max checked-fetch latency | Emulator frames from request to room observation |
| ---: | ---: | ---: | ---: | ---: |
| 4 | 61,170 | 269 | 53 frames | 1,701 |
| 40 | 66,870 | 296 | 53 frames | 1,861 |
| 43 | 69,440 | 309 | 53 frames | 1,941 |
| 51 | 73,181 | 325 | 53 frames | 2,053 |
| 55 | 69,875 | 311 | 53 frames | 1,957 |
| 66 | 72,125 | 319 | 53 frames | 2,005 |

Frame counts include boot continuation, script scheduling, and the asynchronous
request/validation path; they are not raw MSU bus throughput or a calibrated
frame-budget measurement. The probe samples room publication at bounded
intervals and does not measure when the final video presentation settles.

These probes all used the 2,203-entry canonical ProgramUnit directory and the
same 13,364,554-byte package (SHA-256
`b79cc2e24ee428acd8d0ff8bb4714ca2d4264d6e041bbf6e91baa0cac7720ca6`). They
verified active-record identity, applicable route/matrix contents, visual
surface and palette payload identity, and no runtime error, stale binding, or
selector exhaustion. The probe intentionally does not claim settled PPU
equivalence for authentic FATE backgrounds: SC5VIS is an indexed aspect-fit
projection, not a reconstruction of original PPU composition.

Attempts to use the diagnostic startup selector for rooms 78 and 98 did not
yield a matching final active-room observation: the target request was
preempted/redirected by the authentic startup/lifecycle continuation. These
are recorded as *not natively verified*, not as evidence that either room's
record is malformed. Both remain covered by the all-room host descriptor and
capacity preflight. Room 98 is the maximum-object case (126 records) and still
needs a diagnostic load that reaches its stable publication point. Room 78's
64-box/4,096-byte matrix bounds are independently exercised by the successful
room-43/51/55 probes, but this does not substitute for room-78 identity
verification.

A separate copyright-free native corruption control failed the incoming
room-2 resource before commit. It reported SCUMM error `$10`, retained room 1
and its prior active-record hash, and did not publish partial data or use a ROM
fallback. The large-room fault and revisit controls are distinct from a claim
that every post-retirement failure is rollback-safe.

The native probe telemetry records bytes read, request/read counts, storage
service turns, and maximum individual checked-fetch latency. It is not a
device-throughput benchmark: emulator-frame deltas include script execution,
resource scheduling and presentation, and native PPU settlement is not
measured by the metadata probe. The existing independent Winston PCM/data-read
control remains the audio/data concurrency evidence; it demonstrates
continued reads during PCM, not gapless playback or physical-device timing.

For a direct large-room overlap check, room 66 was also rebuilt with the
existing Winston PCM track 1 sidecar and probed while its 72,122-byte room
load was serviced. The observation reported selected track 1, play flag set,
and no PCM error bit in either service or device status. ROM SHA-256 is
`1b873d02afb2d17cfbe3a4b9b3f78db92cac719a76e772d50bfe6be90a722f60`, map
SHA-256 `4171f2fe83e757ab8b018a5cb3ad22b0106aff8fc4c669f01acf50d48381b057`,
and build-identity SHA-256
`2e180527dc85d72189bf5377dc7330e3bfeac013b143b033d8930e4214ec4994`.
This checks concurrent service state at room publication; it is not a PCM
waveform continuity or FXPAK hardware test.

## Build artifacts

The package, per-room preflight, ROM, and native traces are generated under
ignored build directories from the user's external archive. They are not
source assets and are not committed.
