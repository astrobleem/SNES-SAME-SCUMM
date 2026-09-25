# Phase 6B SA-1 BW-RAM Carrier and Surface-Storage Proof

Phase 6B proves an isolated SA-1 cartridge carrier as storage infrastructure.
It does not change the accepted ordinary-LoROM SAME/M25 target, activate the
SA-1 processor, define surface packets, or implement a production video
backend.

## Carrier and processor ownership

The proof header is:

| Header byte | Value | Meaning |
|---|---:|---|
| `$FFD5` | `$23` | slow LoROM, SA-1 mapping |
| `$FFD6` | `$35` | ROM + SA-1 + RAM + battery |
| `$FFD7` | `$08` | 256 KiB proof ROM |
| `$FFD8` | `$07` | 128 KiB BW-RAM |

At reset the S-CPU writes `CCNT=$20`, leaving CCNT bit 5 asserted. The proof
contains no SA-1 vector, reset program, mailbox protocol, IRQ handler, or SA-1
DMA. Across the complete fresh-emulator run the SA-1 architectural state stays
at `K:PC=00:0000`, `A=X=Y=D=DBR=0`, `SP=$01FF`, `P=$34`; only emulator cycle
accounting advances. The S-CPU remains the sole code executor, NMI owner, and
PPU/DMA owner.

## Write protection and mapping

The initialized control state is:

```text
CCNT = $20    SA-1 reset asserted
BWPA = $03    protect 256 << 3 = $0800 low bytes
SBWE = $00    protection enforced
BMAPS = $00   restored baseline window selection
```

With `SBWE.7=0`, a write to `$40:07FF` is rejected while a write to
`$40:0800` sticks. Setting `SBWE=$80` temporarily permits the protected write;
the proof restores the byte and returns `SBWE` to zero. Writes also stick at
the backend reserve, `$40:FFFF`, `$41:0000`, and `$41:FFFF`.

For BMAPS selectors 1 through 7, the complete selected 8 KiB block compares
byte-for-byte through both `$00:6000-$7FFF` and `$80:6000-$7FFF`. Each band is
also mutated and restored once in each direction. The mapping is:

| BMAPS | Direct BW-RAM block |
|---:|---|
| 1 | `$40:2000-$3FFF` |
| 2 | `$40:4000-$5FFF` |
| 3 | `$40:6000-$7FFF` |
| 4 | `$40:8000-$9FFF` |
| 5 | `$40:A000-$BFFF` |
| 6 | `$40:C000-$DFFF` |
| 7 | `$40:E000-$FFFF` |

Any future production renderer using this window must preserve BMAPS around
interrupts, or make interrupt code independent of its current selection.

## Accepted storage layout

The machine-readable source of truth is `labs/sa1_bwram/layout.json`.

| Region | Address | Bytes |
|---|---:|---:|
| protected/reserved low area | `$40:0000` | `$0800` |
| future save replacement | `$40:0800` | `$0800` |
| backend/control reserve | `$40:1000` | `$1000` |
| live 256x224 INDEX8 surface | `$40:2000` | `$E000` |
| exact 896-tile planar shadow | `$41:0000` | `$E000` |
| exact BGR555 CGRAM shadow | `$41:E000` | `$0200` |
| future staging/metadata | `$41:E200` | `$1E00` |

The linear and planar images alone consume `$1C000` (114688) bytes. With the
save reservation, CGRAM shadow, and metadata space, 64 KiB cannot represent
the exact-shadow design. No checksum or collision-prone tile fingerprint was
substituted for byte-exact comparison.

Fresh Nexen exposes two independent 64 KiB cartridge-RAM halves. Its
`SnesSaveRam[0..$FFFF]` view equals direct bank `$40`, and
`SnesSaveRam[$10000..$1FFFF]` equals direct bank `$41`; the corresponding bank
sentinels do not mirror.

## Complete memory and DMA evidence

The S-CPU copies and reads back every byte of all accepted regions. Final
hashes are:

```text
LIVE_LINEAR_SURFACE
478ebd2fb0d2267b211e07e9acac5fa9965d844a8eb5a0a5075f3aa320a69771

PLANAR_TILE_SHADOW
f887613881ab773f1c40f50ddb849a06c47f035132c49b307f79770970734bdb

CGRAM_SHADOW
9e0eaef828e822ff06c2317a0c749350b3c5100f46c4c3efd97a4cce5e7be906
```

Tile 11 is overwritten and restored while both neighboring 64-byte tile
records are checked against their ROM sources. This independently proves tile
record isolation before the complete shadow hash.

The lab includes the exact production `Same_Dma_Enqueue`,
`Same_Video_Commit`, and `Same_Dma_ProcessQueue` implementation. It loads the
`$E000` planar shadow from bank `$41` to VRAM in 28 `$0800` forced-blank
chunks, loads CGRAM from `$41:E000`, then performs a 64-byte active-display NMI
transfer. All 31 descriptors commit through S-CPU MDMA channel 7 with zero
pending or rejected descriptors. SA-1 DMA registers and character conversion
are unused.

VRAM `$0000-$DFFF` equals the complete BW-RAM planar shadow, VRAM
`$E000-$E7FF` equals the fixed tilemap, and CGRAM equals the BW-RAM shadow. The
Mode-3 screenshot is pixel-identical to the independently decoded reference:

```text
reference and emulator-visible PNG
a4d2f0001edead73e6dd4091fb9ea9e12dba4616ec84aae10d6da15a92c4f95c
```

The proof ROM SHA-256 is:

```text
c126c0badb6251900d4ea9ab321f1b43bb646f982b24d8a66f786821efa8a4df
```

Battery persistence was not tested. The carrier declares battery-backed RAM,
but production save relocation remains deliberately out of scope.

## Production conclusion

The Phase 6A storage blocker is resolved for an SA-1 carrier: an unchanged
S-CPU execution model can directly maintain the accepted linear surface in
BW-RAM, retain an exact planar/CGRAM shadow, and use the existing S-CPU DMA
queue to feed the PPU while the SA-1 CPU remains reset.

The smallest next production-carrier gate is to introduce a separately
selectable SA-1 header/memory profile, carry this exact layout as target-owned
constants, repeat the reset-held BW-RAM and DMA audit in that carrier, and keep
the existing ordinary-LoROM artifact as a byte-identical build. Surface ABI
semantics and `SnesVideoBackend` activation remain subsequent, separately
approved work.
