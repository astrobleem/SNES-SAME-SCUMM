# Actor pose pipeline audit

This audit is bound to `ATLANTIS/ATLANTIS.000` and `.001` from `ATLANTIS.zip`;
the `.001` payload SHA-256 is
`8381ba5a2eee3ed887a42d63794f7c6f1b4bbf809c928a4223f95ee3646a7baf`. The
authoritative resource is `costume.2`; decoding uses
`src/same/engines/scumm_v5/costume.py`.

Pose identity for the malformed native walking witness: actor 1, costume 2,
facing 180 (direction 2, draw-to-right), source frame 2, step 0. Source frame
1 is the idle comparison. The runtime fixture selects cooked slot 0 while
standing and slot 1 while moving; its exact walking frame-counter value was
not preserved and is recorded as UNKNOWN rather than guessed. The audit uses a
32x64 canvas, origin `(16 + relative_x, 55 + relative_y)`, source transparency
0, palette indirection, source column-major cel data, and row-major canvas
output. The complete cel metadata is in `pose-manifest.json`. The actual
emitted four-frame binary SHA-256 is
`12a6590e7da085c98666a1a5eefdc5f9fde9cf5bf9072c3aacd7caec46177eee`.

## Independent stage results

| stage | idle | walk | result |
|---|---|---|---|
| independent host composition | `host-composite.png`, SHA `09e14514f0ad9dcf446765ee072866f606f223a7aaadd2a33a18f0d4fe7050f0` | `host-composite.png`, SHA `28688a892671ea00df57d7ee006ab0193e1e4637d5aa757d8f1d084f3eaa682c` | coherent |
| old cooker witness | `current-cooker-composite.png`, SHA `3d1ec39c2743beb793efdc5e2028ab4e849ad210a2863cbc175dadadf8332691` | `current-cooker-composite.png`, SHA `2c764d7ef1a6f03b5485bb69436d952cf3a1cfeb0d1cba9cc5dc8fc580d72433` | visibly striped/malformed |
| actual corrected generator `.bin` frame | `cooked-composite.png`, SHA `09e14514f0ad9dcf446765ee072866f606f223a7aaadd2a33a18f0d4fe7050f0` | `cooked-composite.png`, SHA `28688a892671ea00df57d7ee006ab0193e1e4637d5aa757d8f1d084f3eaa682c` | exact host match, 2048/2048 bytes, zero mismatches |
| SAME indexed surface | fresh `fresh-corrected-surface/01-ready-surface.png` | not captured at the exact walk pose | standing surface opened; walking surface UNKNOWN |
| native emulator | fresh `fresh-corrected-surface/01-ready.png` | fresh `fresh-corrected-rom/03-walking.png` | standing and walking captures opened; coherent actor visible |

The first proven divergence was the old cooker assembly. The generic fix in
`tools/generate_snes_scumm_actor_sprite.py` reads SCUMM cel pixels with
`x * cel.height + y` and mirrors the destination according to the decoded
pose. No PPU/BG/Mode3/BW-RAM/backend knowledge was added. The fresh ROM is
`bbfabe380ed5b1c305af8174ab191bc79eb77e117e09a87be64df58b266f82d7`.

The fresh standing surface PNG SHA-256 is
`28db9682e60ba90fdbde8a902c2494c90e649ec9d7be5fe0bcb0f412201a184d`; its
fresh native ready PNG SHA-256 is
`1e86912c66a45ee777ee247d3aae65838441077fad26e38a99d4dc82c4aa4581`; the
fresh native walking PNG SHA-256 is
`4fa91a46264c681530213bcf64a83e7972149bbc354920bd61e56ba2a1f6a156`.
The native actor gate is not promoted to final PASS yet: the exact walking
pose’s indexed-surface crop and native frame correspondence still need a
formalized capture. The prior malformed native frame remains preserved in the
parent evidence packet.
