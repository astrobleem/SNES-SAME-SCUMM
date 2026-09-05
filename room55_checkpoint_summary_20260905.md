# Room-55 focused checkpoint

- Objective: accept the bounded ROM-backed accessor for all authored room-55
  BOXD records without publishing game-derived payloads.
- Accepted ROM SHA-256: `a788eb6b78c8ed6d11154a7480c5a0526e02e407eddba0fa1e2654c5cba4d518`.
- Source corpus: local `ATLANTIS.zip`; demo archive remains incomplete.
- Storage: one 18-byte temporary record at `$7FFB65`; mutable flags remain at
  `$7FFA41`, count `$7FFA40`; actor/destination/scale arrays remain unchanged.
- Evidence: independent source/cooked comparison is 64/64 equal; target room55
  run reports `box_count=64` and object-780 target box 43, error 0.
- Tests: combined focused host suite 150 tests OK; Python compile, diff check,
  and ROM audit pass.
- Remaining explicitly unproven item: target-executed copyright-free multi-leg
  movement fixture through a box index above 31. The authored object-780 action
  legitimately resolves a high-index target but does not request movement.
- No ROM, savestate, archive, generated game payload, or unrelated campaign
  file is included in this review branch.
