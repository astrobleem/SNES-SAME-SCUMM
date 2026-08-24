# SAME 0.2.0 validation record

Validated in the packaging environment on **2026-08-21 UTC**.

## Release command

```bash
make all
```

## Results

- **87/87 unique unit and integration tests passed.**
- SCUMM v5 and AGI profiles both passed structural/resource validation and
  capability negotiation.
- SCUMM v5 completed 120 ticks with `var[20] = 120`, room 0 loaded, music 1
  active, deterministic framebuffer SHA-256
  `f4a68583e391af75177bd170aaf676f7ac8b2ea58ab9940acd564148c7cfc2bc`,
  252 packets pushed/popped, and zero rejected or dropped packets.
- AGI v2 completed 120 cycles with `var[20] = 120`, flag 40 set, deterministic
  framebuffer SHA-256
  `e5ff8ba07c7d28947e3a48e5cc943190ac7cf956dfdc6fdf9f5ce2fb41c898d6`,
  248 packets pushed/popped, and zero rejected or dropped packets.
- Both engine save envelopes passed CRC, engine identity, game identity, schema,
  and restore tests.
- File, memory, composite, and SAME-package resource providers passed.
- Indexed fill/blit/transparency, palette, dirty rectangles, cursor composition,
  frame hashing, and PNG output passed.
- The 16-byte packet remained wire-compatible with 0.1 while adding engine,
  save, and job services.
- Poppy static audit passed across **15 included files / 80 global labels**.
- A regression test proves the lint rejects DBR-relative access to far WRAM;
  this caught and fixed a real `$7E:2222` lifecycle-reset bug before release.
- `adventure-demo.samepkg` passed whole-package and four per-section CRC checks.
- The legacy Genesis scheduler simulation completed 120 frames with no queue
  loss or budget overrun.
- The SN76489 trace rendered 55,125 samples at 44.1 kHz for 1.25 seconds.
- SAME-VDP verified all **4/4 exact golden cases**.
- The Python wheel was built without network/build isolation, installed into an
  empty target directory, reported version `0.2.0`, and registered both
  `agi_v2` and `scumm_v5`.
- The final ZIP was extracted into a clean directory. All **207 internal
  SHA-256 records** passed before and after `make all`, proving the generated
  fixtures, reports, saves, packages, audio, and VDP outputs are path-independent
  and reproducible.
- ZIP and tar.gz integrity/listing checks passed with 208 archived files.

## Generated evidence

```text
out/scumm-v5-report.json
out/scumm-v5-frame.png
out/scumm-v5-slot0.same-save
out/agi-v2-report.json
out/agi-v2-frame.png
out/agi-v2-slot0.same-save
out/adventure-demo.samepkg
out/adventure-demo.inc.pasm
out/genesis-simulation.json
out/sn76489-demo.wav
```

## Workstation SNES build follow-up — 2026-08-22

The configured Linux host adds two checksum/finalizer regression tests and
successfully runs `make snes` with the pinned corrected Poppy fork used by
`supermn-snes`:

```text
Poppy commit ec005c196eedabf7d0c25ff6336398c427dd43ac
Poppy DLL 715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e
ROM size 32768 bytes
reset=$8000 nmi=$8047 irq=$8069
ROM SHA-256 d452760a3089a271eb4cdb7be181e39d4ecdf760e089ae0f306cdec95afc0a0b
```

Two consecutive builds produced the same ROM hash. The audit checks the actual
ROM byte-sum checksum, not only the checksum/complement relationship.

The H0 emulator gate passed in MCP-enabled Nexen from fresh power-on. The retained
report records exact lifecycle/status bytes, frame/operation counters, queue
health through frame 180 and a 240-frame held-input test, press/release timelines,
four framebuffer captures, and Start-to-audio routing:

```text
build/h0-nexen-d452760a3089a271/report.json
SHA-256 bacaa052cc99c6d11ec28f68e2c38405aa8ac03e421decc00d0ad52d0a88bda7
result pass
```

## Boundary

The SNES engine-host ROM is assembled, structurally audited, and passes H0 in
Nexen. No physical-hardware result is claimed. K1 in `docs/NEXT_GATES.md` is the
next kernel gate.

The public `SNES-SuperMonkeyIsland` branch was not imported into the release and
is not treated as current local state. The actual SCUMM extraction must begin
from Chad's local checkout and its current tests.
