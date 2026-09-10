# Room 42 generic interaction acceptance

Status: accepted cold replay; final screened review evidence.

## Build and replay identity

- ROM SHA-256: `5297e4e63d8dfb9db37393445b77c30b81959e525cdb6540e2b82a318eb1c632`
- Replay report: `build/room42-generic-reentry-run3/report.json`
- Corpus: FULL `ATLANTIS.zip`; member hashes are recorded in the replay report and build identity.
- Poppy source line: `8ee859b33bad94e3a01e9c78026803e482292801`
- Poppy DLL SHA-256: `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`
- Nexen: `/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen`
- Nexen SHA-256: `17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`

The replay used completed logical-frame fencing and deterministic one-frame input edges. It did not use `/tmp/mcp-mesen.sh`, raw controller-state writes, forced PCs, or fabricated object selection.

## Accepted interaction evidence

- First source CDHD hit selected object `490`.
- Authored verb ID `3`, runtime name `Open`; native capture shows `Open storage locker`.
- Second A submitted through the normal sentence API and entered `ACTION_PENDING`.
- Open completed; object state changed `0 -> 1` as an action effect, not as the lifecycle completion predicate.
- Canonical `ACTION_PENDING` release returned control to generic interaction.
- Cursor movement invalidated stale selected object/verb state and returned to generic object selection.
- A state-neutral authored action entered and released `ACTION_PENDING` without requiring object-state mutation.
- Object `492` was selected from source bounds; authored verb `Push`; source/runtime name `air compressor switch`; native capture shows `Push air compressor switch`.
- Post-dialogue controller input remained usable; error `0`.

Native captures inspected locally include `02-open-selected.png`, `06-object492-selected.png`, and `05-post-dialogue.png` under `build/room42-generic-reentry-run3/` (captures are not included in the screened source commit).

## Validation

- Focused controller fixture: `51` tests passed.
- Broad Python/SAME suite: `546` tests passed, `241` subtests passed.
- Python compilation: passed.
- `git diff --check`: passed.
- Poppy guard/lint: passed, historical SAME-compatible DLL above.
- SA-1/BW-RAM ROM audit: passed.
- FULL startup42 and cold controller replay: passed.

## Scope

The screened implementation contains generic ACTION_PENDING lifecycle handling, direct selected-object validation/requery, source/runtime HUD text assembly, bounded HUD text handling, cursor invalidation, tests, provenance tooling, and the Winston Inkpen fixture-direction document. Fate archives, ROMs, savestates, captures, and extracted copyrighted payloads are excluded.
