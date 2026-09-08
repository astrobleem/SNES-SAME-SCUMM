# Generic SCUMM v5 room-object interaction review

Status: focused engineering review evidence; room-42 graphics/surface milestone
remains closed.

## Source and tool identity

- Corpus: FULL `/home/chad/ATLANTIS.zip`; startup42 uses the full corpus, not
  the demo archive.
- Poppy #376 focused fix: PR #393,
  `5ab64a4745532d8ef732a2ee694ac9b6dd0e054d`; pinned DLL SHA-256
  `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`.
- Candidate ROM: `build/generic-room42-interaction-fixedpoppy23.sfc`, SHA-256
  `b97fe25e4d7795004610ff1d6e171fe9e1758b94f319c3739c317e808d26547d`.
- Build identity: `build/generic-room42-interaction-fixedpoppy23.build_identity.json`
  (local; ROMs and game-derived resources are intentionally not published).

## Implementation

- Existing CDHD metadata is retained and extended with authored OBCD VERB
  entries. The `0xFF` fallback is not advertised as an explicit UI verb.
- Host and target hit testing use room/world coordinates, active camera
  projection, half-open rectangles, source/OBCD ordering, parent-state
  visibility, and the source selectable flag. No room-42 hotspot table is
  used.
- Target services perform generic active-room hit testing and first/next
  authored-verb discovery. Controller selection writes only the normal
  sentence tuple and pending flag; C20/scheduler execution remains canonical.
- A remains object select/submit, Y cycles authored verbs, and D-pad moves the
  cursor. The controller has no object-490 selection policy or locker rectangle.

## Target evidence

Run: `build/generic-room42-interaction-fixedpoppy23-run-normal/report.json`.

- Explicit FULL startup42 reaches room 42, actor room 42, readiness 1, error 0.
- Source-derived cursor hit selects object 490; authored verb 3 is selected;
  normal sentence `(3,490,0)` executes; actor reaches `(218,104)`, walkbox 10;
  object 490 changes 0 -> 1; authored inspection dialogue runs and completes;
  post-dialogue input remains usable; error remains 0.
- A second source-derived cursor hit selects object 492 from its own CDHD
  record (`x=152,y=88,width=16,height=16`), and its authored verb set differs
  from the locker path. This is a selection witness, not a fabricated sentence.

## Host/synthetic evidence

`tests/test_scumm_v5_room.py` covers hit, miss, exact right/bottom edges,
camera projection, overlapping source-order precedence, parent-state visibility,
and authored verb entries with fallback exclusion. Controller source tests
reject the former locker rectangle/object-490 policy and require the normal
sentence API. The architecture test continues to enforce SCUMM hardware
blindness.

## Validation

- Focused SCUMM room/controller/architecture/engine/costume suite: 202 tests,
  PASS; full repository suite: 531 tests, PASS.
- Python compilation, `git diff --check`, Poppy lint (61 files / 5252 labels),
  and SA-1/BW-RAM ROM audit: PASS.
- The review branch excludes ROMs, savestates, ATLANTIS resources, generated
  game payloads, and unrelated campaign work.
