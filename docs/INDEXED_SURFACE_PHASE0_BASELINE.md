# IndexedSurface Phase 0 characterization baseline

Date: 2026-08-28

Scope: Phase 0 of `SAME_Indexed_Surface_and_SNES_Presentation_Implementation_Spec.docx` only. Production behavior is unchanged. No `SameSurface` class, surface API, renderer, pixel format, dirty-tracking ownership, or SNES backend was added or modified.

Environment:

- Python 3.12.3
- Pillow 10.2.0

## IndexedSurface unit baselines

`tests/test_video.py` pins the existing behavior below:

- Legacy framebuffer serialization is `u16le width + u16le height + 256 RGB triples + tightly packed index bytes`.
- The 3x2 characterization stream is 778 bytes and hashes to `04500d0905c9df798d76366bc7af0ed507b4f8693ad9f7d35188957cffbea63b`.
- Cursor composition is output-only and does not change that framebuffer hash.
- PNG without cursor is indexed mode `P`, 4x3, SHA-256 `fbb97dd8d61c7a192ae147b67abbb61fccafca206309e77834012aa2fce8dcf2`.
- PNG with cursor is mode `RGBA`, 4x3, SHA-256 `86214297f8274d9ef7da46cb0bf67234595c0c1a29e2d9c6fe6d970c48fe6347`.
- Negative-coordinate fill clipping, negative-coordinate pitched blit clipping, `source_pitch`, and keyed transparency are asserted byte-for-byte.
- The initial/full and subsequent dirty sequence is exactly:

  ```text
  Rect(0,0,4,3)
  Rect(0,1,2,2)
  Rect(3,0,1,1)
  Rect(0,0,4,3)
  Rect(2,2,1,1)
  ```

- Cursor definition, movement, and visibility do not append surface dirty rectangles.

## Existing SCUMM v5 video baseline

`tests/test_scumm_v5_video.py` remains unchanged and passes. The S3 validator reports:

- logical framebuffer SHA-256, baseline and accelerated: `6d4451b55770536cde22b8b01338d5dbda06cdf0d6198d1d1066d86faf53b086`
- physical framebuffer SHA-256, baseline and accelerated: `54ddea1f2a877e6a88fad3ea2a94987688e29705e78e8fb21fd1fb9f29e2afaf`
- logical PNG SHA-256: `9c2aeb3e62a81de19ebda55c7918c78f7c845a7b69bc7937d4471336cee82ca0`
- physical PNG SHA-256: `a0d7a2d079bba5fc35a10512fbfdc2b27dea83ebca8ad66ed35d3a8af79d6832`
- report SHA-256: `23dc2bd7b8faef09770df554cd339dc300e3f01dd582c7202267837473a9aef4`

Fixture SHA-256 identities remain:

- `s3_scene.scn3`: `9a5cd8815da5b4f5cf963e48da1303663a5272214fdf230a1cc83852404de54c`
- `s3_font.char`: `fd6352d825b511ba6424849b0832226b03ffa12a1def2d4e00528a85d3142189`
- `s3_cursor.scc3`: `5b624fb6e8fd531b6e9d2d19e631f7e110ca8c4527b8a97127590d537a811ab7`

## SAME-VDP golden baseline

`labs/vdp/golden.json` SHA-256 is `ab13ca51d24fd1f068565c7ce10e3bba125812b7064c7c55a3504bbc4dd55988`. Verification passed all four cases. Expected PNG SHA-256 values are:

| Case | Genesis | SNES |
|---|---|---|
| 01_solid_palette | `1191b1007565e675ab40aac4582adde2536cf90514024e120a2b33a0ca9c4ec2` | `1191b1007565e675ab40aac4582adde2536cf90514024e120a2b33a0ca9c4ec2` |
| 02_single_tile | `b8d06e5e9528bde5d038cb5db32fae5df7c9d1b5fcb5f3187e6155783458a74e` | `85e6c868a850da3176aa04849c1c61d2c30d984600010ca087b2f8ca4d477725` |
| 03_tile_flip | `5b14d23bf8fece4f1ee01bb60f55152afffb44715f493d29a40861c55672789f` | `eec57129fddcab09805b27a2166d1d8217721e089c74dc08e691d6a94d6647df` |
| 04_plane_a | `2e60c6f3e3e6f1eb88036b56bf24d7eff8214704cf33ccd952691f3f7af92ccf` | `26181af31a99affb623a54b5cc03c9694cbfe3bb0b95e182949acf9d6ca88446` |

## SNES and emulator baseline

- Integrated M25 ROM SHA-256: `a48c0db782b6d1df304d164527f2123a0fd99e0f56617e4404a64aeb35765a8c`; LoROM audit passed at 524,288 bytes with reset `$8000`, NMI `$8062`, IRQ `$8084`.
- M25 object-script conformance ROM SHA-256: `a14b56f0cf8307a5ff2ccb604769ccf82daf499751eaff303c51546014f12778`; LoROM audit passed at 262,144 bytes with the same vector values.
- Fresh-emulator M25 integrated and object-script conformance validators both passed.

## Commands and results

```text
PYTHONPATH=src python3 -m unittest -v tests.test_video tests.test_scumm_v5_video
    PASS: 12 tests

make test
    PASS: 361 tests

make validate
    PASS, including Poppy lint: 29 files, 2803 global labels

make demo
    PASS, including SAME-VDP verification: 4 golden cases

PYTHONPATH=src python3 tools/validate_scumm_s3_video.py
    PASS

python3 tools/audit_snes_rom.py build/m25-start-object.sfc
python3 tools/audit_snes_rom.py build/m25-start-object-conformance.sfc
    PASS / PASS

PYTHONPATH=/home/chad/Mesen2/python python3 tools/validate_scumm_start_object_nexen.py \
  --rom build/m25-start-object-conformance.sfc \
  --output build/surface-phase0-m25-start-object-conformance.json
    PASS

PYTHONPATH=/home/chad/Mesen2/python python3 tools/validate_scumm_m25_sentence_movement_nexen.py \
  --rom build/m25-start-object.sfc \
  --output build/surface-phase0-m25-start-object.json
    PASS
```

`make snes` was also run. Poppy lint passed, but the generic build stopped before assembly at the separately known Fate catalog/base-TAD mismatch: catalog entry 19 references missing compiled song `fate_sound_80_default`. Phase 0 does not modify that unrelated pre-existing issue. The unchanged accepted M25 ROMs above were audited and emulator-regressed successfully.

## Discrepancies

No framebuffer hash, PNG, dirty sequence, VDP golden, accepted ROM identity, ROM audit, or emulator result changed. The only observed incomplete prescribed command is the unrelated, pre-existing generic `make snes` catalog/base-TAD mismatch recorded above.
