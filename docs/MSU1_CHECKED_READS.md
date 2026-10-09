# SAME MSU-1 checked reads and Winston I/O fixture

This is a bounded storage-provider and diagnostic-client milestone. It is not
a playable Winston game, a general bytecode paging system, or evidence that all
SAME resource classes are MSU-backed.

## Ownership and API

`same.msu1.CheckedPackageReader` is the synchronous host/reference contract.
It verifies the host package offline, checks the MSU-1 ID, compares the trusted
SAMEPKG header/directory bytes, validates 32-bit bounds and destination
capacity, seeks the shared cursor for each request, computes the requested
CRC32, and publishes bytes to the caller's destination only after validation.
Its `DataPort` protocol deliberately exposes the data device rather than
pretending it is an ordinary file. `FileDataPort` is a test oracle, not native
hardware evidence.

The native storage service is implemented in
`runtime/snes/services/storage_msu1.pasm` and is reached through
`Same_Storage_Process`. The service is the sole owner of MSU data-port
registers. A client fills the `SAME_MSU1_REQUEST_*` descriptor and invokes
`Same_Msu1_ReadBegin`; the frame storage phase transfers at most 64 bytes in
one logical frame, with a bounded data-busy poll. Completion is exposed as
`READ_OK` only after the request CRC matches. Clients must wait for completion
before submitting the next request: the physical data cursor and request
descriptor are singular and service-owned, not a multi-request queue.

The native provider occupies `$7E2F00-$7E2F47` (72 bytes). The diagnostic
client owns `$7E6000-$7EAFFF` (20,480-byte staging), `$7EB000-$7EB0FF`
(256-byte rolling ring), and `$7EB100-$7EB1FF` (guard/results). These ranges
are feature-gated and the Winston personality is rejected alongside the SCUMM
engine personality. General request destinations must be in WRAM bank `$7E`
or `$7F`, fit the caller capacity, and not exceed 32 KiB. The provider never
allocates the full package or full package resource in WRAM.

Native errors are explicit: `NO_DEVICE=1`, `BUSY=2`, `IDENTITY=3`, `RANGE=4`,
`CAPACITY=5`, and `CRC=6`. The MSU-1 data interface has no general EOF/short-read
register. Runtime integrity therefore uses the compiler-trusted exact package
length, exact trusted header/directory bytes, an expected final-byte check,
range checks, and per-request CRC32. CRC32 detects accidental corruption; it
is not cryptographic authentication, and the full body CRC is not rescanned on
each request. Nexen's one-byte-truncated sidecar was rejected by the trusted
tail/identity check; it is not evidence of a hardware EOF exception.

PCM register access is separate and owned by `audio_msu1.pasm`. The device
plays one MSU PCM track at a time. Reads do not stop the current PCM track; the
fixture starts loop track 1 during the read suite and requests short tracks
101-104 while visual reads continue, then tests track 2's nonzero loop point.
This does not provide independent music/speech mixing or a promise of
gapless audio.

## Diagnostic client

The generic build selector `SAME_SNES_ENGINE=winston_io` enables the fixture
client. `tools/generate_snes_msu1_directory.py` verifies the external package
and emits the trusted directory and read-oracle table. Native read expectations
come from `read_cases.json`; the generator also turns its ordered
`interleaved_clients` entries into native CRC/sample cases. Thus A/B/A client
requests are issued serially against the shared cursor, with a fresh seek for
each request, and checked against expected bytes and CRC. No request inherits
another client's cursor position.

After the read suite, the client reads and CRC-validates `GATE4B`, `BGTMAP`,
`PAL16`, `OPEN4B`, `VERGE4B`, and `SLATE4B` from MSU data storage. It displays a
small test card through SAME's video shadow, DMA queue, and NMI commit path.
It is not a SCUMM room, and the pictures are not ROM fallbacks. The PCM service
owns track register writes; the engine submits service requests only.

## Reproducible validation record

The external fixture used for this run is
`Winston_Inkpen_MSU1_Fixture_v1`; it remains outside Git. Its package SHA-256 is
`94c05cddcd1ad704b8cad9961e86bf12c275201a1aa880af0b0b39b75d4cfd6e` and its
length is 16,777,746 bytes. The fixture verifier reported 75 file hashes,
21 package sections, all six image round trips, the stereo clock check, and
seven malformed-package rejections as HOST PASS.

The fixture generator was also run twice into clean directories with the
available Pillow 10.2.0; both fresh 76-file output sets were byte-identical and
passed the verifier. Comparing that output with the supplied generated tree
found eight changed derived files, all downstream of `unfinished_verge`
(`graphics/unfinished_verge.{png,idx8,chr4}`, `data/VERGE4B.bin`,
`read_cases.json`, `package_index.json`, `generated_manifest.json`, and
`msu/winston_io.msu`). The supplied and locally regenerated PNG/CHR bytes differ
slightly under the installed Pillow rasterization, so the regenerated package
SHA differs (`2c4b2df90c2366162bdf135c8ff0b83b387e9e30a6ce26d69454429df07f598f`).
The actual native run used the supplied package and its supplied read oracles.
Independently rebuilding that same supplied package from its manifest with
SAME's `same.package.build_package` reproduced it byte-for-byte, including SHA
`94c05cddcd1ad704b8cad9961e86bf12c275201a1aa880af0b0b39b75d4cfd6e`.

The final ordinary Nexen build used `build/winston-io-final3/winston_io.sfc`:

- ROM SHA-256: `ece24bc4872d6dc4e3cc00af3d36bb89ec5d9f0a59293ee57859bcc0e000ad35`
- map SHA-256: `88c8ea82d8af00520ab784a37feede2d1be9267fbb48170ddcf480f84a676878`
- build identity SHA-256: `38f25997000d6cb75fc1efba4cdda669c91a94c7c0c8dab8d789ae6ccc5a2a0b`
- package sidecar SHA-256 matches the source package above
- finalizer/audit: 128 KiB LoROM, reset `$8000`, NMI `$80C8`, IRQ `$80EA`

On Nexen, all 18 generated read oracles passed: the original 15 boundary,
large-read, byte-sample/CRC and rejection cases plus the fixture's A/B/A
requests. The A/B/A records were:

| Client | Offset | Length | Expected CRC32 |
| --- | ---: | ---: | --- |
| A | `0x0000FFF0` | 17 | `0e5a0f2c` |
| B | `0x01000011` | 127 | `7acbe552` |
| A | `0x00010001` | 19 | `fe6f2c7c` |

Final fixture state was PASS (`2`), case index/count `18/18`, failed case
`$FFFF`, six validated visual sections, final section `SLATE4B` (20,480 bytes),
last visual CRC pass, 40 accepted tile-DMA chunks, and 500 track-2 loop-check
frames. Provider diagnostics showed 23 seeks, 257,508 data bytes read, 21
completed/failed service requests, no provider error, and the final request at
offset 86,065 for 20,480 bytes. The two initialization seeks account for the
difference between non-empty checked requests and total seeks; zero-length and
range-rejected tests do not transfer data.

The staging high-water requirement was 20,480 bytes; the larger-than-64-KiB
test used the 256-byte rolling ring. Each service turn is capped at 64 data
bytes. The Nexen end-to-end run covered 10,200 logical frames; this is an
emulator measurement, not a hardware throughput claim.

The final-build native audio capture was 48 kHz, stereo, 16-bit, 8,148,181
frames (about 170 seconds), SHA-256 of PCM payload
`694348d097ed63285afcd909da24aeec803ca42b0f8ab58f917c79ed8ae1b4bc`. Its
measured active intervals were approximately 0-94 s, 101-104 s, 112-116 s,
123-127 s, and 134-169 s. The gaps are real in this capture; it supports that
PCM playback was exercised while data transfers occurred, not that the audio
was uninterrupted or glitch-free. At the final checkpoint, the fixture passed
its 500-frame track-2 loop observation.

## Failure controls and evidence class

| Control | Result | Evidence class / limit |
| --- | --- | --- |
| Absent/wrong device, stuck-busy and physical truncation | Explicit statuses and destination preservation | HOST mock PASS |
| Seven malformed generated packages | Rejected by fixture verifier | HOST PASS |
| Missing `.msu` sidecar | Engine fail, provider `NO_DEVICE (1)` | Nexen native PASS |
| Wrong package magic/directory identity | Engine fail, provider `IDENTITY (3)` | Nexen native PASS |
| One-byte-short package sidecar | Engine fail, provider `IDENTITY (3)` at trusted-tail validation | Nexen native PASS; not a hardware short-read signal |
| Forced busy | Engine records bounded provider `BUSY (2)`, timeout count 1 | Nexen diagnostic build PASS; busy bit is test-forced, not a physical stuck device |
| Missing PCM track 101 | Engine fails during the first asset stage; audio error observed; storage remains ready | Nexen native PASS |
| Actual hardware absent/stuck/short device | Not run | Requires physical MSU-1 hardware |

The native diagnostic ROM is not a production content loader. The two raw SC5B
fixture sections are not executed by the SNES VM; no bytecode streaming, pinned
program-buffer lifetime, or general resource-cache behavior is claimed.
Audio gaps, hardware-only behavior, and wider resource integration remain
outside this milestone. No fixture package, generated PCM, image payload, ROM,
or savestate is part of the source change.
