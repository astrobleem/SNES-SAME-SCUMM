# Validation record

Validated in the artifact-build environment on 2026-08-21:

- `python3 -m unittest discover -s tests -v`: 5/5 passed.
- Four traces generated and replayed through the Mode-5 state model.
- Four Genesis-color PNG goldens generated.
- Four SNES-quantized PNG goldens generated.
- Four SNES asset bundles generated.
- Every bundle was independently decoded from its emitted 4bpp tiles, little-endian
  tilemap and BGR555 CGRAM; all 57,344 pixels matched its SNES golden exactly.
- Golden trace, PNG and asset SHA-256 checks passed.

The SNES `.sfc` was not assembled in the artifact-build container because that
container has neither .NET nor the user's local Poppy checkout. `snes/main.pasm` is
written against the native SNES syntax demonstrated by `astrobleem/poppy`, and the
local build script refuses the wrong fork before assembly.
