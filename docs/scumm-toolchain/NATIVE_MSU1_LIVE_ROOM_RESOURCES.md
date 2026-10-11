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
| Object names | SC5LIVE fixed-width object-name table | General strings, dialogue text, and font/charset data are not part of this adapter. |

The feature build has no embedded copy of the SC5LIVE/SC5VIS payloads and no
fallback to generated ROM object, local-script, movement, or visual tables for
the live-room consumers above. Compiler/runtime directory metadata remains in
ROM. This is required to locate external package bytes and is not the room
payload itself. The authentic room-4 experiment uses this contract for its
selected route resources; it does not imply that every source-game room or
resource codec is supported.

## Transaction and memory ownership

Room transitions use the existing pending-room and M24R-B lifecycle state
machine. Incoming SC5ROOM and SC5LIVE are fetched and checked before the
outgoing room is retired. The validated incoming metadata is staged separately
and copied to the active room window only after the old EXCD boundary. Palette
and pixel records are fetched/checked before room publication and ENCD. A
pre-commit failure leaves the old room installed. A failure after irreversible
EXCD retirement enters the explicit resource-error state; the runtime does not
claim rollback.

The M24R-B commit path can resume after asynchronous visual reads. A
transaction-scoped `old_bundle_released` bit makes retiring the outgoing
resolver bundle idempotent across those resumptions; it is reset by the next
accepted room request, not by each resume. The native route verifies four
bundle loads and three releases for its four room commits, matching the host
residency simulator rather than counting resume entries as additional releases.

The SA-1/BW-RAM feature layout is mechanically declared in
`runtime/snes/carriers/sa1_bwram_layout.json` and the WRAM overlap audit. The
live-room feature uses:

- `$40:1000-$40:1FFF`: 4 KiB backend reservation, including 768-byte palette
  stage, 64-byte transition/control record, and 2 KiB incoming metadata stage.
- `$41:E800-$41:EFFF`: third 2-KiB checked ProgramUnit cache page in the
  combined live-room/streamed-program personality.
- `$41:E200-$41:E4FF`: 768-byte active Mode-3 RGB palette; the subsequent
  Mode-3 bitsets/work area occupy the rest of the renderer's reserved tail.
- `$41:0000-$41:DFFF`: 57,344-byte Mode-3 tile shadow, used as bounded pixel
  staging before pixels are copied to the active indexed surface.
- `$40:2000-$40:FFFF`: 57,344-byte active indexed surface.
- `$41:F000-$41:FFFF`: 4-KiB active SC5LIVE metadata record.

These regions are disjoint from the two WRAM ProgramUnit windows and the
third BW-RAM page, resident resolver, C4/C19, controller, name cache and
save-validator state. The active live record is bounded at 4 KiB; incoming
metadata is staged in the separate 2.5-KiB transaction area. In authentic
room 4, SC5LIVE is 2,372 bytes and SC5VIS contains a 57,344-byte indexed
surface plus a 768-byte palette. Visual records are consumed in bounded
checked reads into their dedicated staging regions. Room-resource buffers and
bytecode cache have separate ownership and generation rules. A failed
validation never publishes a partially received record or executable body.

## Performance and limits

The live-room feature uses a 256-byte per-service-turn MSU budget, versus the
legacy 64-byte budget. It remains resumable and uses the same serialized
provider cursor, range checks and CRC validation. Native acceptance records
actual bytes, logical frame counts, checked-fetch latency, and provider errors;
these are emulator measurements, not a physical FXPAK throughput claim.

On the synthetic bounded four-room Nexen run, the provider read 261,162 data bytes over
10,390 logical frames (25.14 bytes/logical frame; 34.23 bytes per frame with
read progress), with a 256-byte service budget, 233 bytes as the largest
single-frame transfer, and a 10-frame maximum checked-fetch latency. The
bytecode windows peaked at 93 occupied bytes. The PCM capture covered 173.4
seconds; while the track was active it contained no silent 20 ms windows, and
the four 1.5-second room-transition windows likewise had no silent windows.
These measurements establish emulator coexistence for this fixture only.

The authentic DOS-CD FATE experiment traversed only `0 → 68 → 0 → 4`, settled
room 4, and then issued the established single Open action on object 61/verb
3. The selected package contains 209 ProgramUnits (152,548 body bytes), not
the entire 2,203-unit source projection. By the room-4 checkpoint the provider
had counted 129,836 bytes; by the later settled/action checkpoint it had
counted 169,304 bytes. The provider budget is 256 bytes per service turn in
this feature personality. Nexen reported no provider error or timeout. This
replay has no PCM track configured, so it is not PCM-continuity evidence.
Room-4 SC5LIVE (2,372 bytes), its 57,344-byte indexed surface and 768-byte
palette matched the external package/compiler records. After presentation,
892/896 PPU tiles matched the compiled visual realization; this is a
bounded-room visual check, not general image-codec coverage.

Mode-3 conversion and DMA are asynchronous. The route validator checks the
live indexed surface and palette at room publication, then drains the final
settled presentation without controller input and compares actual PPU tile
VRAM/CGRAM against the host realization of the same checked SC5VIS resource.
That presentation drain is not counted as room-load latency.

The streamed ProgramUnit cache has three 2-KiB instruction-aligned pages. A
canonical DOS-CD FATE backend-directory audit measured 2,203 selector-bearing
ProgramUnits and 1,000,867 body bytes. The largest body is 21,002 bytes
(`RoomLocalProgram(room=27,local=208)`); 78 bodies exceed 2 KiB, 33 exceed 4
KiB, 16 exceed 8 KiB, and three exceed 16 KiB. The largest complete object
carrier is 2,116 bytes (`ObjectProgram(room=92,object=1195)`) with verb entry
offsets retained in its directory. The cache can page this body size
structurally, and a copyright-free 21,271-byte body passed native cross-page
branch/yield/resume acceptance. That does not certify all 2,203 FATE
ProgramUnits for semantics or every possible simultaneously pinned working
set.

Original SCUMM background codecs, all image variants, costume codecs, fonts and
charsets, general text resources, sound/iMUSE assets, and portable streamed
save-state reconstruction remain separate limitations. SC5VIS is a compiler
owned indexed-pixel representation, not proof that every original room image
format has a generic decoder. No full-game FATE streaming or playthrough is
claimed.

## Status

- **IMPLEMENTED, feature-gated:** checked live room metadata, objects/names,
  object-verb dispatch metadata, locals/bundles, walkboxes/movement tables,
  indexed pixels/palette, and lifecycle integration for copyright-free
  synthetic rooms and the bounded authentic FATE room-4 route.
- **NATIVE-VERIFIED:** the generated multiroom fixture route consumed its
  package-owned SC5LIVE/SC5VIS records and checked the resulting settled PPU
  tile/CGRAM image; the build and package identities are in local evidence.
  The current acceptance traverses rooms 1–4, matches the ROM-backed control's
  observable marker state, records 17 safe selector reuses, and observes no
  stale rejection, exhaustion, alias, or PCM silence window during room loads.
  Native build SHA-256 is `cf577d9be0897c44f2478e32f5ba333a36ac0a1ed81e30e18719981801305ba2`;
  package SHA-256 is `66912bd000b908fe9ea91043cc0169b8baf01aee710815b9466b1a924af24517`.
- **NATIVE-VERIFIED, bounded external corpus:** canonical DOS-CD FATE room 4
  used package-owned room metadata, visual pixels/palette and selected
  executable bodies through `0 → 68 → 0 → 4`; Open on object 61/verb 3 was
  submitted once. This does not test all rooms.
- **PARTIAL:** original source-format background decoding and other resource
  families are not comprehensively streamed; program semantics, concurrent
  cache pressure, assets, audio conversion and portable save reconstruction
  remain incomplete.
- **PLANNED:** general resource cache/codec services, broader bytecode-cache
  policy, portable save migration, and physical hardware testing.
