# Room-55 geometry acceptance review

Screened review handoff only: no ROMs, savestates, ATLANTIS.zip, generated game payloads, or broad campaign history.

## Identity

- ROM: `build/same-room55-c25far-final.sfc`
- SHA-256: `a788eb6b78c8ed6d11154a7480c5a0526e02e407eddba0fa1e2654c5cba4d518`
- room-55 source payload SHA-256: `321610e001c4b05f6a74641862a9886b10f22e1983e95c54957554926418d6ea`
- Poppy: `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`
- Shared armory: `astrobleem/Mesen2` mcp-server `4e1e86bb1`.

## Storage/access contract

Before, `$7FFB65-$7FFF70` was a 32-record x 18-byte mutable geometry image (576 bytes). After, `$7FFB65-$7FFB76` is one 18-byte temporary record. Existing mutable arrays remain at walkbox `$7FFDA5`, destination `$7FFDC5`, destination-X `$7FFDE5`, redraw `$7FFE25`, last-valid `$7FFE45`, diagnostics `$7FFEC5-$7FFF70`, and per-actor raw scale `$7FFF71-$7FFFB0`. Active flags remain RAM at `$7FFA41-$7FFB3F`, count at `$7FFA40`.

Immutable geometry/routes/portals/object-walk tables and initial flags are generated ROM data. `ScummV5_PutActor_LoadGeometry_Far` validates active record and unsigned 8-bit index, computes `index * $12` with 16-bit X/index arithmetic, copies nine words, returns carry clear, and returns with A8. It does not preserve X; callers own X as scratch. The fetched record is temporary and must not survive a nested geometry call. Explicit `.bank` sections keep each immutable table inside one LoROM bank. Room load reloads mutable flags/count and active record; no RAM geometry pointer is retained.

Bank-0 map: end `$D8E8`, 9,943 bytes free before header. The old 576-byte image was replaced by 18 bytes, reclaiming 558 RAM bytes. The geometry refactor itself saves zero bank-0 ROM bytes; generated immutable payload was retained in ROM/far banks.

## 64-record and target evidence

Independent ATLANTIS room-55 decode versus cooked `room-55.sc5c`: 64 records in source and cooked streams; all 64 point/scale records equal in source order. Geometry SHA-256 for both: `729295d85e84cc33d2414f41d255eb74472bc2b10f61ccebf6d9f443e3b0a8a6`. Final record 63 and distinct high records including 43 retain identity; box 43 has scale 178 and is not aliased.

Final-ROM target command was the existing `validate_scumm_startup42_nexen.py` with `--expected-room 55 --frames 420 --light --minimal-observation --sentence 10 780 0`. Result: room 55, phase 0, error 0, `box_count=64`; authored object 780 walk point `(640,198)` resolved to box 43. Its source handler is scenery/name and correctly does not request movement. Thus target evidence proves valid high-index lookup, not game-authored movement. Host tests cover invalid index, high-index identity/scale, mutable flags, room re-entry, and nested decode. A separate copyright-free target multi-leg route through a box above 31 remains unproven.

Generated index witnesses are `1*$12=$0012`, `31*$12=$022E`,
`32*$12=$0240`, `43*$12=$0306`, and `63*$12=$046E`; index 64 is rejected by
the room-55 `cpx #$0040` guard. The corrected exact accessor body is in
`review_room55_geometry_source_extract.pasm`.

## Validation/cost

- `PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine tests.test_scumm_v5_room -q`: 144 tests OK.
- `python3 -m py_compile tools/generate_snes_cooked_rooms.py tools/build_m25a_validator_room.py tools/validate_scumm_startup42_nexen.py`: PASS.
- `git diff --check`: PASS.
- `python3 tools/audit_snes_rom.py build/same-room55-c25far-final.sfc`: PASS.
- Target report: `build/validate-room55-geometry-acceptance/report.json`.
- Same-ROM no-sentence 420-frame baseline also ran; existing scheduler fixture activity makes raw cycle counts nondeterministic, so no cache/performance claim is made beyond one bounded record fetch plus existing placement arithmetic.

Actual screened source excerpts are in `review_room55_geometry_focused.diff`.
