# SAME-VDP Lab

**SAME** is the **SA-1 Machine Environment**: a reusable foreign-machine runtime
for SNES/SA-1. SAME-VDP is its CPU-independent video laboratory.

This repository proves Genesis VDP → SNES PPU translation without a 68000, Z80, game
ROM, Superman runtime, or Black Tiger runtime. Synthetic traces drive a deterministic
Mode-5 state model. The same final VDP state is rendered as:

- a Genesis-color reference PNG;
- the exact SNES-quantized PNG expected from the translated assets;
- SNES 4bpp tiles, Mode-1 tilemap, and BGR555 CGRAM;
- a static SNES test ROM source assembled by **astrobleem/poppy**.

## What works now

The first four gates are present:

1. solid palette/tile fill;
2. one asymmetric tile on a backdrop;
3. Genesis name-table H/V flip bits translated to SNES map bits;
4. a full 32x28 visible Plane A using four palettes, tile reuse, flips and priority bits.

The VDP input is real control/data-port traffic, not a made-up tile API. The compact
`data_words` record means “repeat normal data-port writes.”

## Run the host oracle

```bash
cd same-vdp-lab
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
make all
```

Useful commands:

```bash
same-vdp render cases/04_plane_a.vdptrace.jsonl \
  --palette genesis --output /tmp/genesis.png

same-vdp compile-snes cases/04_plane_a.vdptrace.jsonl \
  --output generated/04_plane_a

same-vdp render-snes-bundle generated/04_plane_a \
  --output /tmp/translated-snes.png

same-vdp compare expected/04_plane_a.snes.png capture.png \
  --crop 0,0,256,224 --diff build/diff.png --result build/result.json
```

`compare` exits 0 only for an exact frame.

## Build the SNES ROM with Chad's Poppy fork

The build refuses an unrelated Poppy checkout. It requires `astrobleem/poppy` and a
HEAD containing commit `ec005c196eedabf7d0c25ff6336398c427dd43ac`.

Expected local layout matches the existing SNES projects:

```text
/home/chad/poppy/
/home/chad/.dotnet10/
```

Build one case:

```bash
make rom CASE=01_solid_palette
make rom CASE=02_single_tile
make rom CASE=03_tile_flip
make rom CASE=04_plane_a
# or all four:
make rom-all
```

Output is `build/same-vdp-<case>.sfc`. The Poppy source uses the fork's native SNES
system/header directives and 24-bit `.org` layout. No ASAR, ca65, WLA-DX, MSYS, or
handwritten opcode packer is involved.

## Current honesty boundary

Milestone 0 is frame-static Plane A in Mode 5, H32, 256x224, 32x32 map, zero scroll.
The model already preserves raw registers, 64 KB VRAM, CRAM, VSRAM, command latching,
auto-increment and normal VRAM/CRAM/VSRAM data writes. Unsupported video behavior is
rejected rather than approximated.

See `SAME_VDP_TRACE.md` and `docs/ROADMAP.md`.
