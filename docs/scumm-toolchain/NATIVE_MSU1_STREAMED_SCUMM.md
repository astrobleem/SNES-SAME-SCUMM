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

The transfer is resumable across frame processing. At most 64 bytes are
transferred per service turn. In the current 206-unit fixture, the largest
body is 86 bytes and the longest checked fetch (a room record) took 49 logical
frames. The bounded four-room run read 28,110 bytes over 1,410 logical frames
(19.94 bytes/logical frame; 24.07 bytes in frames where data progressed), with
zero provider timeouts or range rejects. The raw service ceiling is 64 bytes
per frame (3,840 bytes/s at 60 Hz), not a measured sustained hardware rate.

## Bounded cache and ownership

The feature reserves two 2 KiB bytecode windows:

| WRAM | Purpose |
| --- | --- |
| `$7E1000-$7E17FF` | Program cache slot 0 |
| `$7E1800-$7E1FFF` | Program cache slot 1 |
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
allocator consumes an empty second window before evicting a ready body. The
room-owned lifecycle code uses the same adapter. Generations and canonical
IDs are checked before a cache window is used.

The cache can hold at most two bodies of 2 KiB each. Larger bodies or nested
working sets that cannot be pinned fail explicitly; the compiler rejects an
individual body above this cache limit. This is bounded prototype behavior,
not evidence that every FATE activation pattern fits.

## Room boundary: partial

The native fixture fetches and CRC-validates each compiler-generated cooked
room record in `SC5ROOM` before it advances the room-transition lifecycle.
This gates the existing EXCD/commit/ENCD ordering and demonstrates that a
failed incoming record is not published as a successful transition.

The fetched record is currently a validation/staging input, not the full room
resource backing store. The generated ROM room/object tables and existing
render/resource data still provide the live room contents. Therefore this is
not complete room streaming. Fonts, room images, costume data, and general
resource lookups are not transparently serviced from the external package by
this change.

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
  package offsets, CRC-checked asynchronous native fetch, two bounded cache
  windows, interpreter execution, and the synthetic native route.
- **PARTIAL:** cooked room record fetch gates lifecycle; live room contents
  still use generated ROM tables.
- **PLANNED:** general MSU-backed resource services, portable save-state
  reconstruction for streamed activations, broader cache-capacity policy,
  physical FXPAK acceptance, and whole-game FATE streaming.

The storage provider contract and its previous checked-read acceptance remain
documented in [MSU1_CHECKED_READS.md](../MSU1_CHECKED_READS.md). The earlier
Super Monkey Island work was consulted for MSU packing, script/room data, and
PCM experience; its game-specific framework and media were not imported
([repository](https://github.com/astrobleem/SNES-SuperMonkeyIsland),
[historical plan](https://github.com/astrobleem/SNES-SuperMonkeyIsland/blob/master/snes-secret-plan.md)).
