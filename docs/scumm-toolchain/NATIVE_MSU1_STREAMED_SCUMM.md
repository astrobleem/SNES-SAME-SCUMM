# Native MSU-1 streamed SCUMM execution

This is an experimental, feature-gated storage path for compiler-generated
SCUMM v5 ProgramUnits. It is not whole-game FATE streaming, not a new
interpreter, and not a claim that all source resources can be consumed outside
ROM.

## Implemented path

`src/same/engines/scumm_v5/program_storage.py` consumes the existing canonical
ProgramUnit directory and exact compiled bodies. It emits one `SC5CODE`
collection and a deterministic ROM directory whose rows contain a 32-bit
SAMEPKG byte offset, 16-bit body length, and CRC-32. IDs are directory indexes
from the compiler-owned canonical directory; runtime selector bytes are not
stored here. The compiler can retain source fixture package sections and emits
cooked room records in `SC5ROOM`. Object verbs remain entries in their owning
object carrier.

With `SAME_BUILD_SCUMM_MSU1_PROGRAMS=1`, the native adapter resolves the
existing resident selector to its canonical ProgramUnit ID, requests the
complete body through the existing SAME storage service, and enters the
existing interpreter only after the request and body CRC are valid. There is
no ROM-body fallback. The existing 178-selector ABI and resolver remain
unchanged. Logical body PCs stay with the activation; a resumed activation
reacquires its canonical body rather than treating a WRAM address as source
identity.

The transfer is resumable across frame processing. Ordinary checked-read
clients retain a 64-byte per-service-turn budget. The live-room diagnostic
personality uses a bounded 256-byte quantum, validated with its input/NMI/audio
controls, so the 57-KiB indexed room surface does not take thousands of frames
to stage. These are emulator-observed service budgets, not a claim about
physical-hardware throughput.

## Bounded cache and ownership

The feature reserves three 2 KiB bytecode pages (6 KiB total) in SNES WRAM.
The third page uses bank `$7F`, separate from the profile-generated global
variable table in bank `$7E`; live room metadata and the indexed surface keep
their independent SA-1 BW-RAM allocations:

| WRAM | Purpose |
| --- | --- |
| `$7E1000-$7E17FF` | Program cache slot 0 |
| `$7E1800-$7E1FFF` | Program cache slot 1 |
| `$7F1000-$7F17FF` | Program cache slot 2 (WRAM gap after object names, before C10 state) |
| `$7E2F00-$7E2F47` | Existing 72-byte MSU provider state |
| `$7E2F48-$7E2FEA` | Program cache metadata, generations, ownership and diagnostics |
| `$7E2FEB-$7E2FFF` | Room-resource fetch/validation state |

The program cache is separate from the resident selector table. A body is
unloaded/requested/loading/validating before it becomes READY; failed or
partial transfers remain non-executable. An interpreter invocation pins its
cache slot while executing, including nested execution. The parent invocation
context is saved across child calls. Yielded C4 activations retain canonical
identity, selector ownership and logical PC; their bytes may be reclaimed and
are checked/refetched when execution resumes. A nested caller saves its
logical PC and releases its transient cache pin; the child runs through the
same adapter and the parent is validated/refetched before resuming. The cache
allocator fills unused windows first, then evicts the oldest unpinned page
using deterministic three-way LRU ranks. The room-owned lifecycle code uses
the same adapter. Generations and canonical IDs are checked before a cache
window is used.

Each cache page holds at most 2 KiB of one instruction-aligned body segment.
The compiler emits checked segment boundaries and per-segment CRCs; logical
source PCs remain independent of the physical window. Large ProgramUnits are
fetched page by page. The 6-KiB cache is bounded; an all-pinned working set
fails explicitly rather than reusing a live page. The third page is the
bank-$7F WRAM interval in the table above; it does not consume BW-RAM or
overlap the live room tile shadow, palette shadow, or active metadata. Reset
and mechanical WRAM/BW-RAM audits cover these ownership boundaries.

## Room boundary: implemented for the synthetic live-room profile

The follow-on live-room profile fetches and validates `SC5ROOM`, `SC5LIVE`,
`SC5VIS`, and palette records through SAMEPKG/MSU-1. `SC5LIVE` supplies the
implemented active room metadata: object records and names, object placement,
object/verb-carrier dispatch, local-script and bundle directories, walkbox
flags/geometry, movement routes/portals, and lifecycle ProgramUnit IDs.
`SC5VIS` supplies indexed pixels and palette data; checked pixels are copied to
the active surface and the existing Mode-3 video backend realizes that surface
into PPU tile VRAM/CGRAM. Program bodies remain in the separate checked
bytecode cache.

The transition retains the outgoing room through incoming metadata validation
and the existing EXCD/commit/ENCD boundary. Incoming visual resources are
validated before the incoming room is published. Failures before the retirement
boundary preserve the outgoing room; failures after it set the explicit SCUMM
resource error rather than claiming rollback. Room-resource buffers are
separate from the two bytecode windows and from resolver/controller/C19/name
cache/save-validator state; see
[NATIVE_MSU1_LIVE_ROOM_RESOURCES.md](NATIVE_MSU1_LIVE_ROOM_RESOURCES.md).

This is a bounded generic storage seam, not transparent decoding of every
original SCUMM resource. The fixture's indexed `SC5VIS` is already a
compiler-owned display representation: original room-image codec coverage,
costume/charset/font services, general string loading, and audio asset
conversion remain separate. ROM-backed room mode remains available.

## Native synthetic acceptance

The copyright-free generated corpus contains 206 selector-bearing ProgramUnits
and 193 globals. Its generated pressure script uses a compact loop to resolve
the same targets 5–192 without making the caller body dominate transfer time.
The SAMEPKG retains the supplied Winston fixture sections and places
`GlobalProgram(1)` at byte offset 16,783,798, beyond the 16 MiB boundary. The
program section contains 510 body bytes; its largest body is 86 bytes. Program
bodies and cooked-room bytes are omitted from the ROM image in this build.
Native Nexen execution uses the generated package directory, enters rooms
`0 → 1 → 2 → 3 → 4`, dispatches both verbs through one object carrier, runs a
room-local script that starts another global, resolves 192 globals on demand,
preserves a yielded global through the first room transition, and reclaims
selectors after retirement.

The accepted native observation included 205 bindings, a full 178-selector
resident peak, 17 selector reuses, 192 dynamic-global lookups, four
room-resource validations, two cache windows used (93 observed cached bytes),
zero exhaustion/stale/cache-failure events, and a balanced stack. Selector
D0 changed from `GlobalProgram(1)` generation 1 to a different ProgramUnit at
generation 2 only after that activation had stopped. The yielded global was
observed live at the first transition, resumed to write its marker, and then
retired. Host/reference execution of the same generated bodies and room
scripts reached the same fixture markers; the simulator/native residency
diff matched selectors, generations, transition tables, counters, and reuse.
This establishes this synthetic route, not general semantic support for all
compiler IR.

## First authentic FATE room (bounded external integration)

The canonical external source is `/home/chad/ATLANTIS.zip`, profile
`fate_of_atlantis_dos_cd.json`, game identity
`indy4-fate-dos-cd-en`. No original resource payloads are checked in. The
whole parsed source currently projects to 2,203 selector-bearing ProgramUnits
with 1,000,867 executable-body bytes. The largest is
`RoomLocalProgram(room=27,local=208)` (21,002 bytes; logical body PCs 0 through
21,001); 78 bodies exceed 2 KiB, 33 exceed 4 KiB, 16 exceed 8 KiB, and three
exceed 16 KiB. The largest object carrier is
`ObjectProgram(room=92,object=1195)` at 2,116 bytes, with verb entry offsets
50, 219, 1,816, and 2,069. Program body lengths and OBCD-relative verb entry
offsets are represented as 16-bit values, which cover this observed corpus.
The directory retains distinct source identities and entry offsets; this
size census is not a claim that every unit has complete runtime semantics.

The room-4 experiment packages the deterministic route's selected 209
ProgramUnits (152,548 body bytes) and required room resources, not all 2,203
units. Its package SHA-256 is
`c41b176eb5a86014c048af4a123c0d153e08e8cee5ef8145571832b9881d5d44`. The
fresh isolated Nexen replay used ROM SHA-256
`898f5a6c37305eab2fd660e9ff62b89dc6323593a2925e0df28afad96e7bd2c6`, map
SHA-256 `6f4588c6275c5c2a5219022185b1d6afa437e96d52bb0e6266b772bdb9d94637`,
build-identity SHA-256
`fee6a568a6db336dafd7846ac8177cdfd62dcfab90d1666c114a4ca01d00bb50`, and
ProgramUnit-directory SHA-256
`bc6768224ba6850e2084a752fac5e8c5b439348598d37ffa3982dd3e52c6a0e3`.
Generated ROM, map, package, and emulator reports remain ignored build
artifacts. Room 4's 2,372-byte live record contains 15
objects, 38 verb entries, 23 room locals, and 10 walkboxes; its visual record
contains a 57,344-byte indexed surface and 768-byte palette. The native
replay follows only `0 → 68 → 0 → 4`, settles room 4, and performs the single
established Open submission on object 61/verb 3. At the checkpoint the VM is
in room 4 with error 0, lifecycle settled, Ego in room 4 at `(77,136)`, and
the controller submission count increased once. The runtime consumed the
checked `SC5LIVE`/`SC5VIS` data: live object/walkbox/palette/surface hashes
matched their package records, and 892 of 896 drained PPU tiles matched the
compiled visual realization. This is an acceptance of one bounded route and
room, not whole-game FATE execution.

The ROM-backed reference is the previously accepted, source-bound static
build (`f5492f1c…71fd`, map `151a977a…64eec`) recorded in
`examples/replays/fate-room4-open-trapdoor.json`. Its cold replay observed
the same room-4 Open action on object 61/verb 3 and continued from room 4.
This MSU run reproduces the room/error/lifecycle state, cursor, hit object,
selected verb, and one-submission delta. The old ROM and native result are not
present in this isolated workspace, so there is no new same-session binary
comparison. A newly assembled static-selector control from this worktree did
not reach room 4 and is excluded as invalid control evidence; the streamed
build is independently validated against the source-derived replay and the
historical accepted semantic observations.

Across that replay the residency observer recorded a peak of 46 selectors,
40 observed pinned bindings, 10 selector rebinds, two bundle loads and one
release, and 12 dynamic global resolutions; stale executions, aliases,
invalid generations, and exhaustion were all zero. Provider byte accounting
reached 169,304 bytes by the post-action checkpoint. The route took 6,858
emulator frames from reset through the post-action observation (about 24.7
provider bytes/frame over that whole interval, including script and authored
wait time). Room publications occurred at frames 1,867, 3,007, and 4,747;
the room-4 body/resource request began at frame 4,722, 25 frames before its
publication. The cache observer's maximum checked-fetch interval was 1,589
frames across the run; it is an end-to-end request interval, not the duration
of one 256-byte service quantum. The live-room profile's service is bounded
and nonblocking, but this replay did not include PCM
(`pcm_during_room_load` is null), so it is not evidence of PCM continuity
during authentic FATE loading. The separate synthetic Winston PCM/data test
remains the audio concurrency evidence: four room-transition capture windows
had no silent 20-ms windows while its track was active. That is emulator
evidence only; MSU PCM is still a single-track interface.

A copyright-free native failure control mutates one byte of the incoming
room-2 `SC5LIVE` payload while preserving the original package header and
directory. The provider detects CRC error 6, SCUMM reports resource error 16,
and the outgoing room-1 live record remains installed with its original
length and SHA-256. No ROM fallback is used. This specifically covers a
failure before transition commit; it does not imply arbitrary post-commit
rollback.

## Failure and audio evidence

The existing checked-read controls continue to cover missing devices, wrong
package identity, range/capacity rejection, truncation/tail mismatch, bounded
busy timeout, and CRC failure without publishing partial data. Native
ProgramUnit execution also validates body identity/CRC and does not fall back
to ROM. The ordinary native route has no observed stale execution, alias, or
exhaustion. A full matrix of physical-device failure modes is not possible in
Nexen and has not been run on FXPAK hardware.

The Winston PCM/data-overlap run passed all 18 read cases while exercising
tracks 1, 101–104 and 2. A 169.7-second emulator capture contained silence
between several short fixture PCM segments. Those intervals coincide with the
fixture's intentional track changes/finite sample durations; reads continued
to progress and the provider reported no timeout or error. The capture does
not demonstrate gapless playback, hardware timing, or independent music plus
voice mixing. The MSU PCM device remains single-track.

## Status

- **IMPLEMENTED, experimental:** compiler-packed ProgramUnit bodies, u32
  package offsets, CRC-checked asynchronous native fetch, three bounded
  instruction-aligned cache pages (6 KiB), interpreter execution, and the
  synthetic and bounded authentic room-4 native routes.
- **IMPLEMENTED, experimental:** synthetic live room tables and indexed visual
  records are consumed from checked external storage by the existing engine.
- **PARTIAL:** the selected FATE route uses compiler-generated external room
  representations, but general source-game room codecs and all other resource
  classes are not yet transparently externalized. Only the selected 209 of
  2,203 FATE ProgramUnits are in this experiment.
- **PLANNED:** general MSU-backed resource services, portable save-state
  reconstruction for streamed activations, physical FXPAK acceptance, and
  whole-game FATE streaming. The current three-page cache was measured against
  the corpus maximum, but this bounded route does not certify every body's
  semantic/runtime behavior or every concurrent live-body working set.

The storage provider contract and its previous checked-read acceptance remain
documented in [MSU1_CHECKED_READS.md](../MSU1_CHECKED_READS.md). The earlier
Super Monkey Island work was consulted for MSU packing, script/room data, and
PCM experience; its game-specific framework and media were not imported
([repository](https://github.com/astrobleem/SNES-SuperMonkeyIsland),
[historical plan](https://github.com/astrobleem/SNES-SuperMonkeyIsland/blob/master/snes-secret-plan.md)).
