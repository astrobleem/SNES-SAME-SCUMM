# Room-42 presentation boundary review

## Source change

SCUMM engine sources call target-neutral `Same_VideoSurface_*` and
`Same_VideoText_*` services. PPU registers, BG2/Mode3 names, BW-RAM backing,
and VRAM/CGRAM/OAM/DMA implementation names remain confined to video/carrier
services. `Same_VideoSurface_WriteIndexedPixel_Far` is the compositor write
seam; the selected carrier owns the destination.

`tests/test_scumm_v5_architecture.py` scans every production `scumm_v5*.pasm`
engine source and rejects the forbidden hardware/backend/carrier names.

## Evidence

Focused Python tests: 167 pass, including architecture traps and controller
source contracts. `git diff --check`: pass.

The preserved native oracle is `build/controller-room42-visualfix26.sfc`,
SHA-256 `ddd8c1835f83169cbe49483a402e1f189d14b30cd3a1a22e190b09f7a9b00b6e`.
Its inspected capture set remains the accepted harbor/Indy/cursor/walk/open/
dialogue/control evidence.

The correctly configured fresh source build is
`build/controller-room42-arch-clean.sfc`, SHA-256
`c527550a639bd36b937185e4e21e026b4181b9753f6607700101ff2f8b5bfbf0`.
It reaches room 42 with error 0, but native presentation is not yet accepted:
the backend reports `accepted_present=0` and no rejected presents. A temporary
direct-call diagnostic build also fails identically, so this pass does not
attribute the failure to the neutral SCUMM service seam. The fresh build must
include `SAME_SCUMM_SCENARIO_START_ROOM=42`.

ROMs, captures, ATLANTIS.zip, savestates, and generated game payloads are
intentionally excluded from this review branch.
