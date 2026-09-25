# Phase 6C SA-1/BW-RAM Production Carrier

Phase 6C adds a separately selectable SA-1/BW-RAM carrier for the existing
S-CPU SAME runtime. The ordinary LoROM carrier remains the default. This phase
does not activate the production surface ABI, Mode-3 presentation, SA-1 CPU
execution, SA-1 DMA, character conversion, or the M25 `$B2 setCameraAt`
blocker.

## Production preflight

The production assembly root is `runtime/snes/main.pasm`. The accepted M25
integrated image is 524288 bytes and the conformance image is 262144 bytes.
Both ordinary images retain internal-header bytes `$20,$02,$09,$01` and the
accepted S-CPU vectors RESET `$8000`, NMI `$8062`, and IRQ `$8084`. The bounded
SA-1 carrier boot call moves its NMI/IRQ labels to `$8066`/`$8088`.

The integrated M25 image emits immutable content in physical ROM banks 0
through 13: bank 0 contains the kernel, engine, interpreter, and service code;
banks 1 and 2 contain TAD data; banks 3 through 13 contain generated cooked
room/script/object resources. The SA-1 carrier adds its bounded carrier boot
routine in physical ROM bank 14. The generated production map audit resolves
all assembly banks, long labels, and `incbin` operands and proves that no
active code or resource depends on ROM remaining visible through S-CPU banks
`$40` or `$41`. Under the SA-1 mapping those banks are the two distinct 64 KiB
halves of BW-RAM; WRAM remains at `$7E/$7F`.

The accepted ordinary save base was `$70:0000`. Every production save access
now uses the generated `SAME_SAVE_STORAGE_BASE`; it resolves to the same
ordinary address or to `$40:0800` for the SA-1 carrier. Capacity remains exactly
2048 bytes and the SAMESAV schema, identity checks, CRC32, atomic commit, and
music restore policy are unchanged.

The production path is finalized by `tools/finalize_snes_rom.py` and audited by
`tools/audit_snes_rom.py`; the build entry points are `tools/build_snes.sh` and
`tools/build_snes.ps1`. Engine selection, cooked rooms, music catalogs, save
identity, ABI definitions, and carrier policy are emitted as generated includes
before Poppy assembly.

## Carrier selection and source of truth

`SAME_SNES_CARRIER` accepts `lorom` and `sa1_bwram`; absence of the variable
selects `lorom`. `SAME_SNES_OUTPUT` controls the distinct output path and never
selects the carrier implicitly. Typical production outputs are:

```text
build/m25-start-object.sfc
build/m25-start-object-sa1.sfc
```

`runtime/snes/carriers.json` is the carrier source of truth.
`runtime/snes/carriers/sa1_bwram_layout.json` is the canonical Phase 6B layout
and is now consumed by both the proof lab and production carrier generator.
`tools/generate_snes_carrier.py` validates them and produces:

```text
runtime/snes/generated/carrier_constants.inc.pasm
runtime/snes/generated/carrier_boot.inc.pasm
runtime/snes/generated/carrier_header.inc.pasm
runtime/snes/generated/carrier_code.inc.pasm
<output>.carrier.json
```

The generated assembly defines the save, backend reserve, live surface, exact
tile shadow, CGRAM shadow, and staging ranges. Validation requires exactly
128 KiB, the accepted region sizes, complete coverage, and no overlap. No SCUMM
or AGI source refers to carrier constants or literal BW-RAM addresses.

## Headers and finalization

| Carrier | Map | Cartridge | ROM size | RAM size |
|---|---:|---:|---:|---:|
| ordinary LoROM M25 | `$20` | `$02` | `$09` | `$01` |
| SA-1/BW-RAM M25 | `$23` | `$35` | `$09` | `$07` |

The carrier-aware finalizer requires an explicit selected carrier, verifies the
assembled header against the generated carrier manifest, preserves the existing
LoROM padding/checksum algorithm, and rejects an SA-1 ROM whose size code does
not exactly describe its finalized size. The auditor retains separate strict
LoROM checks and adds exact SA-1 header, size, checksum/complement, vector,
profile, and layout-identity checks; it does not use a weakened shared allowlist.

## SA-1 boot and control contract

While forced blank is active and interrupts remain disabled, the SA-1 carrier
calls a bounded S-CPU routine which performs:

```text
CCNT  $2200 = $20
BWPA  $2228 = $03
SBWE  $2226 = $00
BMAPS $2224 = $00
```

It then writes only the 18-byte carrier control record at `$40:1000`: magic
`SA1C`, layout version 1, carrier ID 1, BW-RAM size `$00020000`, three false
validity flags, and zero pending/committed generations. It does not clear or
populate the live surface, tile shadow, CGRAM shadow, staging, or save range.
The ordinary generated boot/code includes intentionally emit no instructions
or data.

Nexen captured the SA-1 architectural state at power-on, engine boot, during
the 91-tick walk, LSCR 211 entry, and the terminal blocker. At every checkpoint:

```text
K:PC = 00:0000
A=X=Y=D=DBR=0
SP=$01FF
P=$34
emulation mode=true
```

There were no SA-1 IRQs, mailbox commands, SA-1 DMA operations, or SA-1
instructions. Reset, kernel initialization, frame/NMI ownership, the scheduler,
SCUMM VM, audio, input, and the existing DMA queue all remain S-CPU-owned.

## Accepted BW-RAM layout

```text
$40:0000-$07FF  protected/reserved
$40:0800-$0FFF  2 KiB production save
$40:1000-$1FFF  backend/control reserve
$40:2000-$FFFF  $E000 live INDEX8 surface (invalid/unpopulated in Phase 6C)

$41:0000-$DFFF  $E000 planar tile shadow (invalid/unpopulated)
$41:E000-$E1FF  $0200 CGRAM shadow (invalid/unpopulated)
$41:E200-$FFFF  $1E00 future staging/metadata
```

The finalized production map report is
`build/phase6c-production-map.json`. It reports ROM banks 0 through 14 at
S-CPU `$00-$0E:8000-FFFF`, BW-RAM at `$40/$41`, WRAM at `$7E/$7F`, no ROM/BW-RAM
collision, and no forbidden BW-RAM literals in engine code.

## Save persistence

`tools/validate_sa1_carrier_persistence_nexen.py` uses two fresh Nexen
processes and normal production M20 save/load opcodes. Process 1 creates a
valid SAMESAV envelope; process 2 starts from the emulator's battery-backed
128 KiB cartridge RAM and restores it. There are no debugger writes, copied
save bytes, emulator savestates, or SA-1 execution.

The persisted record is 340 bytes with schema 1, game `indy4-fate-demo`, engine
`scumm_v5`, payload length 252, payload CRC32 `84e35394`, and SHA-256
`919eef182b08a6d14a3072189b5ca07881426d40d2c6dd68e91531a93b0b9f15`.
The save image is 131072 bytes and the tested save range is `$40:0800`, length
2048. The detailed evidence is `build/phase6c-sa1-persistence.json`.

## Cross-carrier M25 evidence

The ordinary and SA-1 production carriers both reach the accepted authentic
path through sentence script 2, the exact 91 blocked waits and movement route,
`getDist`, object 596 entry `$0029`, `$F7 startObject`, object `chainScript(211)`,
LSCR 211, and the unsupported `$B2 setCameraAt` blocker. The machine-readable
comparison at `build/phase6c-cross-carrier.json` has no differences after
excluding header/checksum, carrier ID/control block, and CPU cycle count.

Equal checkpoints include frame 412, logical tick 93, current room 49, actor
position `(57,46)`, walkbox 1, movement stopped, the script slots/PCs/locals,
message state, one audio packet, and normal DMA counters (4 committed, 402
forced-blank deferrals, one pending, zero budget deferrals/rejections).

## Deterministic ROM identities

```text
ordinary integrated
a48c0db782b6d1df304d164527f2123a0fd99e0f56617e4404a64aeb35765a8c

ordinary conformance
a14b56f0cf8307a5ff2ccb604769ccf82daf499751eaff303c51546014f12778

SA-1 integrated
451a1d769b2bb6df5cfd9f17997aff353758918fcd1ef16b5b189d9623115ca4

SA-1 conformance
90619a24992b5a7e8b0a5ab2737068dfa0c6ec456720e799a860a9b2e588ff0c

SA-1 persistence validator
549ce199fc254d81dc4d21cc8afcd3dda1934d013ee94a2d672676569ba99694
```

Two clean generated-state builds of each production carrier are byte-identical.
The ordinary integrated and conformance identities remain the accepted hashes;
the SA-1 hashes are additional carrier identities.

Phase 6A and 6B remain distinct proof targets. Their preserved identities are:

```text
Phase 6A ROM  e980b827c4dc452a49d6a04265f2f35edfb29d7e6518acc34e1c7fb9a3cdeb06
Phase 6B ROM  c126c0badb6251900d4ea9ab321f1b43bb646f982b24d8a66f786821efa8a4df
reference/emulator visible PNG
a4d2f0001edead73e6dd4091fb9ea9e12dba4616ec84aae10d6da15a92c4f95c
```

## Validation summary

The final repository run completed 418 unit tests. Focused carrier, finalizer,
auditor, BW-RAM-layout, and surface-realization coverage completed 25/25.
`make validate`, `make demo`, Poppy lint (33 files, 2804 global labels), S3,
all four SAME-VDP goldens, both proof-ROM rebuilds/emulator checks, both
ordinary M25 validators, both SA-1 M25 validators, fresh-process battery
persistence, cross-carrier comparison, production map audit, Python compile
checks, and `git diff --check` all pass.

The preserved host identities include legacy framebuffer
`04500d0905c9df798d76366bc7af0ed507b4f8693ad9f7d35188957cffbea63b`,
cursor-excluded PNG
`fbb97dd8d61c7a192ae147b67abbb61fccafca206309e77834012aa2fce8dcf2`,
cursor-included PNG
`86214297f8274d9ef7da46cb0bf67234595c0c1a29e2d9c6fe6d970c48fe6347`,
S3 report
`23dc2bd7b8faef09770df554cd339dc300e3f01dd582c7202267837473a9aef4`,
S3 logical/physical PNGs
`9c2aeb3e62a81de19ebda55c7918c78f7c845a7b69bc7937d4471336cee82ca0`
and `a0d7a2d079bba5fc35a10512fbfdc2b27dea83ebca8ad66ed35d3a8af79d6832`,
and VDP manifest
`ab13ca51d24fd1f068565c7ce10e3bba125812b7064c7c55a3504bbc4dd55988`.

The known generic `make snes` `fate_sound_80_default` catalog/base-TAD issue
was not modified or bypassed. The explicit carrier builds use the accepted
prebuilt M22 TAD inputs and do not change that unrelated catalog policy.

## Scoped files

Phase 6C adds `runtime/snes/carriers.json`, the canonical
`runtime/snes/carriers/sa1_bwram_layout.json`, `src/same/snes_carrier.py`,
`tools/generate_snes_carrier.py`, `tools/audit_snes_carrier_map.py`,
`tools/compare_snes_carrier_traces.py`,
`tools/validate_sa1_carrier_persistence_nexen.py`,
`tests/test_snes_carrier.py`, and this report. It updates the shell/PowerShell
SNES builders, finalizer, auditor, production main/carrier include seam, save
base use, persistence-only validation personality, M25 trace capture, Phase 6B
proof builder/layout consumer, Make generation, and the related focused tests.
Generated carrier includes/manifests are build products rather than a second
source of truth.

## Next seam

The smallest Phase 6D seam is an S-CPU-owned `SnesVideoBackend` that consumes
the existing target-neutral `PresentRequest`, addresses storage exclusively
through the generated carrier constants, converts/compares tiles against the
Phase 6A/6B shadows, and submits bounded work through the existing NMI DMA
queue. Surface packet semantics, generation completion, palette/cursor upload,
and Mode-3 activation must remain separately proven rather than inferred from
the storage carrier.
