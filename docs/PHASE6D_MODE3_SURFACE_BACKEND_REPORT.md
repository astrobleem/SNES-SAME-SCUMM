# Phase 6D Selectable Production Mode-3 Surface Backend

Phase 6D adds a separately selectable S-CPU production video backend that
realizes the fixed 256x224 `INDEX8` display surface from SA-1 BW-RAM. The
legacy backdrop backend remains the default and contributes no new assembly
bytes. SCUMM and AGI remain unwired; the proof uses a copyright-free engine
fixture and the production event, frame, video-service, NMI, and DMA seams.

## Selection and production lifecycle

The build selection is:

```text
SAME_SNES_VIDEO_BACKEND=legacy_backdrop   # default
SAME_SNES_VIDEO_BACKEND=mode3_surface
```

`mode3_surface` is rejected unless `SAME_SNES_CARRIER=sa1_bwram`. Backend
selection is independent of engine and output filename. The source of truth is
`runtime/snes/video_backends.json`; the Mode-3 storage policy is
`runtime/snes/video_backends/mode3_surface_layout.json`. The generator emits
backend constants, bounded reset/service/frame/commit/boot hooks, a code
include, the fixed tilemap, and a machine-readable build manifest. Legacy
hooks intentionally contain no instructions.

The production proof lifecycle is:

```text
S-CPU reset / forced blank
  -> carrier boot (SA-1 reset remains asserted)
  -> Same_Kernel_Init / Same_Video_Reset / backend reset hook
  -> Same_Engine_Boot / copyright-free fixture fills live surface + palette
  -> normal SAME video events are drained
  -> backend forced-blank realization through the production DMA queue
  -> display enable

normal frame
  -> Same_ActiveEngine_Frame
  -> Same_Kernel_DrainEvents -> Same_Video_Handle -> backend service hook
  -> backend bounded conversion/queue step

NMI
  -> Same_Video_Commit
  -> Same_Dma_ProcessQueue (kernel-owned channel 7)
```

No active-display PPU write occurs in the engine-frame path. No second event
queue or DMA queue exists.

## Fixed surface and backend storage

The displayed surface is identity zero, `INDEX8`, 256x224, pitch 256, at the
generated carrier surface base (`$40:2000`, `$E000` bytes). Phase 6D does not
create arbitrary surfaces.

The accepted `$41:E200-$41:FFFF` staging range is partitioned as follows:

```text
$41:E200-E4FF  live RGB8 palette                 $0300
$41:E500-E56F  candidate tile bitset             $0070
$41:E570-E5DF  pending tile bitset               $0070
$41:E5E0-E64F  in-flight tile bitset             $0070
$41:E650-E66F  candidate palette bitset           $0020
$41:E670-E68F  pending palette bitset             $0020
$41:E690-E6AF  in-flight palette bitset           $0020
$41:E6B0-E6EF  64-byte tile conversion scratch   $0040
$41:E6F0-E74F  eight bounded in-flight records   $0060
$41:E750-E7FF  bounded work state                 $00B0
$41:E800-EFFF  copyright-free fixture evidence   $0800
$41:F000-FFFF  reserved                           $1000
```

The existing `$40:1000` carrier control block is extended with backend ID and
state, surface lock, valid flags, pending/committed generation, accepted and
rejected request counters, candidate/pending/in-flight counts, converted and
unchanged counts, queued tile/CGRAM bytes, batch count, retry/error status, and
expected DMA completion. Generated offsets and overlap assertions own this
layout; engine code contains no BW-RAM literals.

## Packet contract

The existing 16-byte SAME packet and ABI revision are unchanged. Phase 6D
implements only these reserved video operations:

```text
SURFACE_DIRTY
  arg0 low/high  = unsigned x/y
  arg1 low/high  = unsigned width/height
  nonzero dimensions required; clip to 256x224; fully clipped is a no-op

PALETTE_WRITE
  arg0 low/high  = first index/count
  arg1           = 0
  count > 0 and first+count <= 256

PRESENT
  arg0           = nonzero unsigned generation
  arg1           = 0
  generation must exceed committed generation and backend must be idle
```

Packets carry no bulk pixels or palette bytes. Writers populate the fixed live
BW-RAM surface/palette and announce the changed ranges. While a generation is
locked, dirty, palette, and present requests are rejected explicitly.
`SURFACE_CREATE`, `SURFACE_UPLOAD`, and all cursor operations remain reserved.

## State machine and realization

The bounded states are `UNINITIALIZED`, `IDLE`, `CONVERTING`, `QUEUEING`,
`WAITING_DMA`, `COMPLETE`, and `ERROR`. An accepted present locks the surface.
Candidate tiles are processed in ascending fixed tile number. Each is encoded
from the linear surface into the exact Phase 6A 64-byte 8bpp planar form and
compared byte-for-byte with its permanent shadow record. Identical records do
not produce DMA. Changed records update the shadow and remain pending until the
kernel DMA committed counter reaches the recorded target.

RGB8 entries use the accepted `R5 | G5<<5 | B5<<10` conversion and exact
two-byte comparison against the CGRAM shadow. Palette runs have deterministic
priority and are committed separately before tile runs. Consecutive tiles are
one VRAM run. Every batch obeys `$0800` bytes and eight descriptors; overflow
remains pending. Generation completion requires empty candidate, pending, and
in-flight work plus observed DMA completion; only then is the surface unlocked.

The active conversion limit is four tiles per engine frame. Fresh-emulator
sampling observed at most three completed conversions between emulator-frame
checkpoints. NMI remained stable, all 43 production DMA descriptors committed,
and pending/rejected kernel DMA counts ended at zero.

## PPU realization

The fixed production state is:

```text
BGMODE  = $03
BG1SC   = $70        # tilemap word address $7000 / byte address $E000
BG12NBA = $00
TM      = $01
TS      = $00
BG1HOFS = $0000
BG1VOFS = $03FF
MOSAIC  = $00
CGWSEL  = $00
CGADSUB = $00
SETINI  = $00
```

The requested Phase 6D text listed `BG1VOFS=0`, but the already accepted Phase
6A hardware oracle proves the normal BG fetch origin is one scanline ahead.
`$03FF` is therefore required for source row zero to equal screenshot row zero.
Using zero produced an independently observed one-row displacement. Keeping
the accepted Phase 6A encoder, tile bytes, and pixel oracle takes precedence
over that transcription.

VRAM remains `$0000-$DFFF` for 896 fixed 8bpp characters and `$E000-$E7FF`
for the static 32x32 tilemap; hidden rows point at tile zero. The initial
surface and all 512 CGRAM bytes are generated from live BW-RAM source data at
runtime under forced blank; no planar framebuffer is preloaded from ROM.

## Six-generation evidence

The target-side 8bpp output equals the Phase 6A reference encoder for the full
896-tile fixture, which exercises all 256 indices, all planes, tile boundaries,
and left/right bit ordering.

| Gen | Result | Tile bytes | CGRAM bytes | Batches |
|---:|---|---:|---:|---:|
| 1 | full initial realization: 896 changed tiles | 57344 | 512 | 29 |
| 2 | full dirty, byte-identical content: 896 unchanged | 0 | 0 | 0 |
| 3 | one changed pixel / tile 33 | 64 | 0 | 1 |
| 4 | palette entry 1 only | 0 | 2 | 1 |
| 5 | tiles 0..32 | 2112 | 0 | 2 (32 tiles, then 1) |
| 6 | tiles 0,2,4,6,8,10,12,14,32 | 576 | 0 | 2 (8 descriptors, then 1) |

Generation five's locked follow-up dirty, palette, and present requests each
incremented its rejection counter once without changing active work. Final
accepted/committed generation is six, the surface is unlocked, and all valid
flags are true.

Fresh-emulator reference and captured PNG hashes match for every generation:

```text
gen 1  b531911c0adb618b2ff30675ea564984ec66fa895ea510c71314560b3ceef5f0
gen 2  b531911c0adb618b2ff30675ea564984ec66fa895ea510c71314560b3ceef5f0
gen 3  b531911c0adb618b2ff30675ea564984ec66fa895ea510c71314560b3ceef5f0
gen 4  359ceeb18f2cec58cea73737e53c0e40e26ea63ea1d186c08a3d0c5c5f465f28
gen 5  67ebb7363b55facd89fb4723215428fd3f3b44f4ceff9ddb328dadd0bbc844b2
gen 6  359ceeb18f2cec58cea73737e53c0e40e26ea63ea1d186c08a3d0c5c5f465f28
```

Final memory identities are:

```text
live indexed surface  f139c6f2ac0da00f16ea00c85d1c43f494509bcfb1ecb8ca2c076b441356cdeb
tile shadow           574d90ded0c50be6c888ccfdedfb5a0221c1159bf93b92410e8fb140a6400f33
VRAM realized range   590cbf5dc5317446b7e8555697fb4ef4fbeb430cea91ebec83538ea31726a727
CGRAM shadow/PPU      9a665f796f8c731d39bfec6b554d422239ddfd4e9246ea818515a725ebb5ec59
```

The fresh emulator used zero debugger writes. SA-1 architectural state was
captured at power-on, every completed generation, and termination and remained
`K:PC=00:0000` with unchanged registers; no SA-1 DMA or mailbox path exists.

## Artifacts and regressions

The deterministic Mode-3 proof artifact (two byte-identical builds) is:

```text
build/phase6d-mode3-surface.sfc
3ba6d8e0e9f84b12a1d066354ba7fc8684aa9aaa0cf6fca68a1e087294937707
```

The four default/legacy M25 identities remain exact and their audits and
sequential Nexen validators pass:

```text
ordinary integrated   a48c0db782b6d1df304d164527f2123a0fd99e0f56617e4404a64aeb35765a8c
ordinary conformance  a14b56f0cf8307a5ff2ccb604769ccf82daf499751eaff303c51546014f12778
SA-1 integrated       451a1d769b2bb6df5cfd9f17997aff353758918fcd1ef16b5b189d9623115ca4
SA-1 conformance      90619a24992b5a7e8b0a5ab2737068dfa0c6ec456720e799a860a9b2e588ff0c
```

Cross-carrier M25 comparison reports no semantic differences. Phase 6A and 6B
proof identities remain `e980b827...deb06` and `c126c0ba...a4df`; both fresh
emulator screenshots remain
`a4d2f0001edead73e6dd4091fb9ea9e12dba4616ec84aae10d6da15a92c4f95c`.
The full unit suite passes 426 tests. `make validate`, `make demo`, S3, all four
SAME-VDP goldens, carrier persistence, Poppy lint, Python compile checks, ROM
audits, and `git diff --check` pass. Established host framebuffer/PNG, S3, and
VDP identities remain exact. The unrelated generic `make snes`
`fate_sound_80_default` catalog/base-TAD discrepancy was not changed.

## Scoped files

Phase 6D adds the backend descriptions, `src/same/snes_video_backend.py`, the
backend generator, Mode-3 production service, fixture engine, ABI note,
fresh-emulator validator, focused tests, and this report. It updates the
shell/PowerShell build selection, Make generation, bounded generated hook seams
in main/video/frame, PPU register definitions, fixture engine selection, and
the Poppy source trap needed to audit the additional far-code personality.
Small SCUMM conditional guards only permit a non-SCUMM fixture build; no SCUMM
video path references or uses Mode 3.

## Recommended Phase 6E seam

The next smallest seam is a target adapter that copies the already composed
final SCUMM display surface and RGB8 palette into the fixed BW-RAM source state,
then translates the existing ordered host-style display invalidations into the
three accepted packets. It should wait for committed generation before allowing
the next mutable frame. It must not expose tile, VRAM, CGRAM, DMA, or carrier
addresses to SCUMM, and cursor/OAM should remain a separate later gate.

