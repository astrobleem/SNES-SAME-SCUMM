# Room-55 geometry acceptance review

Screened review handoff only: no ROMs, savestates, ATLANTIS.zip, generated game payloads, or broad campaign history.

## Identity

- ROM: `build/same-room55-c25far-final.sfc`
- Corrected-stride ROM: `build/same-room55-accessor-fixed2.sfc`; SHA-256:
  `44a9dc0cf25e6bf10ce31ed781a137a55e4b0ae086f79e7b25934119108acedd`
- room-55 source payload SHA-256: `321610e001c4b05f6a74641862a9886b10f22e1983e95c54957554926418d6ea`
- Poppy: `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`
- Shared armory: `astrobleem/Mesen2` mcp-server `4e1e86bb1`.

## Storage/access contract

Old geometry: `$7FFB65-$7FFDA4` (576 bytes). New work record:
`$7FFB65-$7FFB76` (18 bytes). Released span:
`$7FFB77-$7FFDA4` (558 bytes). Neighboring arrays are not released storage:
walkbox `$7FFDA5`, destination `$7FFDC5`, destination-X `$7FFDE5`, redraw
`$7FFE25`, last-valid `$7FFE45`, diagnostics `$7FFEC5-$7FFF70`, and per-actor
raw scale `$7FFF71-$7FFFB0`. Active flags remain RAM at `$7FFA41-$7FFB3F`,
count at `$7FFA40`.

Immutable geometry/routes/portals/object-walk tables and initial flags are generated ROM data. `ScummV5_PutActor_LoadGeometry_Far` validates active record and unsigned 8-bit index, computes `index * $12` with 16-bit X/index arithmetic, copies nine words, returns carry clear, and returns with A8. It does not preserve X; callers own X as scratch. The fetched record is temporary and must not survive a nested geometry call. Explicit `.bank` sections keep each immutable table inside one LoROM bank. Room load reloads mutable flags/count and active record; no RAM geometry pointer is retained.

Bank-0 map: end `$D8E8`, 9,943 bytes free before header. The old 576-byte image was replaced by 18 bytes, reclaiming 558 RAM bytes. The geometry refactor itself saves zero bank-0 ROM bytes; generated immutable payload was retained in ROM/far banks.

## 64-record and target evidence

Independent ATLANTIS room-55 decode versus cooked `room-55.sc5c`: 64 records in source and cooked streams; all 64 point/scale records equal in source order. Geometry SHA-256 for both: `729295d85e84cc33d2414f41d255eb74472bc2b10f61ccebf6d9f443e3b0a8a6`. Final record 63 and distinct high records including 43 retain identity; box 43 has scale 178 and is not aliased.

Target accessor ROM: `67142583180bee350b07b6632b86a66a6800c15aed3ffe9d6d195be7976ed6de`.
Command: `PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-room55-accessor-proof-final5.sfc --output build/validate-room55-accessor-proof-final5 --expected-room 49 --frames 700 --light --minimal-observation --capture-put-actor-sequence`.
Target witness `0xA0` means the fixture-only verifier fetched record 0's
sentinel exactly and rejected index 64. The 64 production calls were observed;
the first count-0 sample is a pre-yield stale observation, so independent
comparison uses the latest occurrence for each requested box. Boxes 1-63 are
all present and match the independent decode 63/63; record 0 is covered by the
target sentinel verifier. Witness offsets remain `1*$12=$0012`,
`31*$12=$022E`, `32*$12=$0240`, `43*$12=$0306`, and `63*$12=$046E`.

Generated index witnesses are `1*$12=$0012`, `31*$12=$022E`,
`32*$12=$0240`, `43*$12=$0306`, and `63*$12=$046E`; index 64 is rejected by
the room-55 `cpx #$0040` guard. The corrected exact accessor body is in
`review_room55_geometry_source_extract.pasm`.

Target movement ROM: `845abdab907261e26448064861e64d35778a18b4d1a74e8abfa27a8f9feb21aa`.
The standalone copyright-free production route records
`4,5,9,16,21,25,31,36,41,47,52,57,62,63`, crossing the old 31/32 boundary;
final actor is `(24,114)`, box 63, moving 0, and the `$AE` wait releases.
The room-55 scenery action itself remains unchanged and does not request
movement.

## Validation/cost

- `PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine tests.test_scumm_v5_room tests.test_m25a_validator -q`: 151 tests OK.
- `python3 -m py_compile tools/generate_snes_cooked_rooms.py tools/build_m25a_validator_room.py tools/validate_scumm_startup42_nexen.py`: PASS.
- `git diff --check`: PASS.
- `python3 tools/audit_snes_rom.py build/same-room55-c25far-final.sfc`: PASS.
- Target reports are local-only: `build/validate-room55-accessor-proof-final5/report.json`
  and `build/validate-room55-movement-acceptance/report.json`.
- Same-ROM no-sentence 420-frame baseline also ran; existing scheduler fixture activity makes raw cycle counts nondeterministic, so no cache/performance claim is made beyond one bounded record fetch plus existing placement arithmetic.

Actual screened source excerpts are in `review_room55_geometry_focused.diff`.
