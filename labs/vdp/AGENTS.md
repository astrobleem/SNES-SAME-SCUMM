# SAME-VDP agent rules

## Truth hierarchy

1. Raw `.vdptrace.jsonl` control/data writes are the source workload.
2. The Python `VDPState` and Genesis-color renderer are the host oracle for the
   implemented scope.
3. `render_bundle()` is the independent SNES-asset oracle.
4. A Poppy-built ROM plus an emulator capture is the hardware-backend result.
5. A clean screenshot never expands the validated feature scope.

## Current gate

V0 only: Mode 5, H32, 256x224, Plane A, 32x32 map, zero scroll, static frame,
normal VRAM/CRAM writes. Do not claim Plane B, sprites, raster effects, DMA timing,
H40, window, shadow/highlight or commercial-game compatibility.

## Required checks before changing the gate

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m same_vdp.cli verify --root .
```

For a SNES backend change, build all four ROMs with `astrobleem/poppy`, capture the
256x224 output, and run `same-vdp compare` against each `.snes.png` golden.

## Poppy boundary

Use only `astrobleem/poppy`. `tools/check_poppy.py` requires a checkout containing
commit `ec005c196eedabf7d0c25ff6336398c427dd43ac`. Do not silently switch assemblers
or bypass the check with a custom ROM packer.

## Next implementation gate

V1 is whole-tile horizontal and vertical scroll. Validate V1 before beginning
sub-tile scroll, Plane B, or sprites.
