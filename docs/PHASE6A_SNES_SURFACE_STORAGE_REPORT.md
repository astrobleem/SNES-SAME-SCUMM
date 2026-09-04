# Phase 6A SNES Indexed-Surface Realization and Storage Gate

Phase 6A proves a static, copyright-free SNES realization of the accepted host
`IndexedSurface` boundary. It does not activate a production SNES video backend
or assign packet semantics to any reserved video opcode.

## Representation

The supported input is exactly `PixelFormat.INDEX8`, 256x224. BG1 uses SNES
Mode 3, 8bpp 8x8 characters, a 32x32 tilemap, main screen only. Screen tile
position `(tx, ty)` permanently owns character `ty * 32 + tx`; visible character
numbers are 0 through 895. Hidden tilemap rows 28 through 31 reference tile 0.

| Item | Byte range | Word address / register |
|---|---:|---:|
| 896 8bpp characters | `$0000..$DFFF` | BG1 character base `$0000`, `BG12NBA=$00` |
| 32x32 tilemap | `$E000..$E7FF` | `$7000`, `BG1SC=$70` |
| reserved VRAM | `$E800..$FFFF` | 6144 bytes |

The fixed register state is `BGMODE=$03`, `BG1SC=$70`, `BG12NBA=$00`,
`TM=$01`, and `TS=$00`. The proof ROM uses a 10-bit vertical scroll of -1
(`$03FF`) to align source row zero with screenshot row zero; this is presentation
alignment, not part of the encoded surface representation.

The exact sizes are:

| Representation | Bytes |
|---|---:|
| Linear indexed surface | 57344 (`$E000`) |
| 8bpp character data | 57344 (`$E000`) |
| tilemap | 2048 (`$0800`) |
| steady VRAM use | 59392 (`$E800`) |
| remaining VRAM | 6144 (`$1800`) |
| CGRAM image | 512 (`$0200`) |

The runtime DMA helper accepts semantic byte addresses and shifts a VRAM target
right exactly once before writing VMADD. Thus tilemap byte `$E000` becomes VMADD
word `$7000`; callers must not divide it a second time.

## Reference realization

`same.snes_surface` supplies an independently tested 8bpp tile encoder and
decoder, full surface bundle encoder and decoder, RGB8/BGR555 conversion, fixed
tilemap construction, dirty-rectangle candidate selection, tile and palette
shadow comparison, contiguous tile-run construction, and a reference bounded
transfer partition. Source pitch is honored through visible rows; padding does
not enter tiles.

The current production limits remain `$0800` bytes and eight descriptors per
NMI. One 8bpp tile is 64 bytes, so an otherwise empty NMI can transfer at most
32 tiles. The reference partition returns all unscheduled tiles as pending.
It neither queues DMA nor discards excess work.

The smallest safe later generation policy is:

1. Load the initial tilemap, full character plane, and palette under forced
   blank in bounded chunks, then enable the display.
2. During active display, compare dirty candidate tiles and CGRAM bytes with
   committed shadows.
3. Schedule fixed-slot, contiguous row-major runs within both existing limits.
4. Keep the accepted generation stable while unscheduled work remains; do not
   claim `PRESENT` completion until its pending tile/palette work commits.
5. Defer replacement/coalescing of pending generations until a later policy is
   separately specified. Arbitrary 56 KiB replacements cannot be atomic at
   60 Hz with the single-copy VRAM layout.

## Live-memory audit

| Memory | Range / capacity | Current owner and access | Reset/lifetime | Surface decision |
|---|---|---|---|---|
| S-CPU WRAM | `$7E0000..$7FFFFF`, 128 KiB | Mutable and S-CPU/DMA-source accessible, but fixed kernel and SCUMM allocations fragment both banks. The C8 string array alone spans `$7E3000..$7F2FFF`; accepted state reaches `$7FFFB1`. | Volatile; owned regions are initialized by their subsystems. | Rejected. No safe contiguous `$E000` allocation exists. The earlier C26 tail `$7FF18E..$7FFFFF` was only `$0E72`, and later accepted state reduces the top tail to `$004F`. |
| Cartridge SRAM | Active M25 header type `$02`, size code `$01`; 2 KiB mapped at `$700000` | S-CPU-visible and owned by the save service. The current kernel's use of it as a PPU-DMA source is unproven. It is far smaller than `$E000`. | Persistent/battery-backed; save identity must survive reset. | Rejected today. Enabling a new 64 KiB SRAM profile would be a cartridge/storage-policy change and was not done. |
| SA-1 I-RAM | Not present on the active target; an enabled SA-1 exposes 2 KiB at S-CPU `$00-$3F/$80-$BF:3000-$37FF` and SA-1 `$0000-$07FF`/`$3000-$37FF` | The ROM is ordinary slow LoROM (`map=$20`); there is no SA-1 register initialization. The `$003000` symbols are explicitly a planned mailbox only. S-CPU/SA-1 sharing and PPU-DMA sourcing therefore have no current implementation. | No present hardware/lifetime contract; optional battery wiring would need a target decision. | Unavailable today and too small for the surface even after SA-1 enablement. |
| SA-1 BW-RAM | Not present or mapped on the active target; an enabled ordinary mapping exposes up to 256 KiB at S-CPU banks `$40-$43` plus a selected 8 KiB `$6000-$7FFF` window | No SA-1 header, initialization, BW-RAM mapping/write enable, or character-conversion DMA exists. S-CPU and SA-1 visibility and the eventual PPU-DMA source path require proof. | No present hardware/lifetime contract; battery/persistence and reset ownership must be specified. | Best intended candidate, but blocked on a separate SA-1 enablement/mapping gate and S-CPU/SA-1/DMA-source proof. |
| ROM | ordinary LoROM, build-dependent capacity | Immutable at runtime; directly readable and DMA-source capable. | Persistent cartridge content. | Suitable for the static proof assets only, not a live surface. |
| PPU VRAM | 64 KiB | PPU display storage, written through ports/DMA in VBlank or forced blank; not linear S-CPU pixel memory. | Volatile presentation state; the initial realization must always load it. | Holds the realized characters/map, not the host-contract live `IndexedSurface`. |

The active integrated and conformance M25 headers are slow LoROM (`$20`),
ROM+SRAM+battery (`$02`), ROM size code `$09`, RAM size code `$01`. No enabled
enhancement hardware was found. A direct-to-tile-cache design is therefore not
selected: it would replace the accepted “surface is linear indexed pixel memory”
contract with a different semantic abstraction.

## Storage conclusion

**Classified storage blocker:** the current production target has no safe home
for a mutable, linear 57344-byte surface. Production packet semantics and
`SnesVideoBackend` activation must remain unwired.

The recommended next gate is a deliberate SA-1/BW-RAM target enablement and
memory-visibility audit. It must prove capacity, mapper/header configuration,
S-CPU and SA-1 access, normal DMA source feasibility, reset ownership, and only
then decide whether SA-1 character-conversion hardware is useful. Cartridge
SRAM expansion remains a possible but less attractive separate hardware/profile
decision because it changes save/persistence and cartridge requirements.

## Static proof

`labs/snes_surface/main.pasm` is an isolated ROM. It boots forced blank, loads
the generated characters, static tilemap, and CGRAM image, enables Mode 3 BG1,
then remains alive. It does not modify production SNES services or use any
reserved semantic video opcode. The fresh-emulator validator checks ROM header
and vectors, PPU state, all 64 KiB of VRAM, all 512 bytes of CGRAM, and the
256x224 screenshot against the independent bundle rendering with zero debugger
writes.
