# Actor pose pipeline audit

This audit is bound to `ATLANTIS/ATLANTIS.000` and `.001` from `ATLANTIS.zip`
(the `.001` payload SHA-256 is
`8381ba5a2eee3ed887a42d63794f7c6f1b4bbf809c928a4223f95ee3646a7baf`). The
authoritative resource is `costume.2`; the decoder is
`src/same/engines/scumm_v5/costume.py`.

Pose identity used by the malformed walking witness:

* actor 1, costume 2, facing 180 -> direction 2, draw-to-right true;
* source frame 1 is the idle pose and source frame 2 is the walking pose;
* runtime fixture selects cooked slot 0 for standing and slot 1 for its
  alternating movement frame (the report does not preserve the exact walking
  frame-counter value, so that value is UNKNOWN rather than guessed);
* step 0, 32x64 indexed canvas, anchor/origin `(16 + relative_x, 55 +
  relative_y)` for this right-facing pose;
* cel transparency is source pixel 0; nonzero pixels are mapped through the
  costume palette. Source cel pixels are column-major; composition writes the
  target canvas row-major.

The generated `pose-manifest.json` records direction, commands, every cel's
dimensions, signed offsets, decoded-pixel count, palette, transparency,
source order, and draw order. Individual cel images are exported after the
canonical column-major-to-row-major conversion.

## Stage results

| stage | idle artifact | walk artifact | result |
|---|---|---|---|
| decoded/assembled host pose | `idle/host-composite.png` (`ae40473839038f62eed49af2eef2047474a362be191ceca745a15379089a93a9`) | `walk/host-composite.png` (`d62ffd3614adb656a3201400a53a19876b2764b4e208d0e1d73a7a56a9f3cc08`) | coherent standing/walking pose |
| old cooker transformation | `idle/current-cooker-composite.png` (`3d1ec39c2743beb793efdc5e2028ab4e849ad210a2863cbc175dadadf8332691`) | `walk/current-cooker-composite.png` (`2c764d7ef1a6f03b5485bb69436d952cf3a1cfeb0d1cba9cc5dc8fc580d72433`) | visibly striped/malformed; regression witness |
| corrected cooked indexed pose | `idle/cooked-composite.png` (`ae40473839038f62eed49af2eef2047474a362be191ceca745a15379089a93a9`) | `walk/cooked-composite.png` (`d62ffd3614adb656a3201400a53a19876b2764b4e208d0e1d73a7a56a9f3cc08`) | exact host indexed bytes: 2048/2048, zero differences |
| SAME indexed surface | not captured for this exact pose | not captured for this exact pose | UNKNOWN; no surface claim |
| native emulator | `../visualfix26-run1/native/01-ready.png` | `../visualfix26-run1/native/03-walking.png` | standing UNKNOWN; walking FAIL actor fidelity |

The first demonstrated divergence is the old cooker assembly. The fix is in
`tools/generate_snes_scumm_actor_sprite.py`: use source column-major indexing
and the pose's draw-to-right destination direction. No PPU, BG, Mode3, BW-RAM,
or native-backend change was made in this pass. The native ROM has not yet
been rebuilt from this corrected cooker, so native actor fidelity remains
unaccepted pending a new matching-ROM capture.
