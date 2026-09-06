# Focused room-42 controller review checkpoint

- Parent review baseline: `a03d571882720a9e58da76fdccdfb4b9577175bc`.
- Main worktree remains dirty with broad campaign work; no broad files are
  copied into this review branch.
- Current accepted controller ROM:
  `4a98d260b33b60d9db45d090647fc9e4a76f2d8481f1a5265b315820f7d44676`.
- Fresh labeled `startup42` reaches room 42 and presents the existing room
  surface/actor. Normal controller input selects the locker and the production
  sentence path executes Open and Inspect.
- Open: `(3,490,0)`, actor `(150,101)` to `(218,104)`, walkbox `7 -> 10`,
  moving clears, object 490 state `0 -> 1`.
- Inspect: `(9,490,0)`, logical talk active then released, final error `0`,
  cutscene depth `0`, C20 empty, controller still usable.
- Root fixes in this focused pass: controller object2 high/low bytes are zero;
  scenario actor record is initialized through generic DefaultActor before
  source-backed costume/placement; replay waits for the semantic inspect-mode
  handoff before sending A.
- Full target command and evidence are in `review_room42_controller_scene.md`.
- Visual correction status: the original native PNGs were opened and are
  multicolored static; the old readiness check did not inspect native pixels.
  The corrected v5 ROM is
  `ffc37a47bed9547e0fceba8a4159d3411acb95e11dd7a71e8bce3ce13a79eb6f` and
  its opened native captures show the room-42 harbor backdrop, but not a
  target-rendered Indy/costume or visible cursor; HUD/dialogue text is clipped.
  Semantic/controller execution passes, while visible controller-playable
  acceptance remains incomplete pending a target costume/OAM renderer and
  complete visible controls.
