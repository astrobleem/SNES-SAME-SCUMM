# Same-ROM hoist5 execution evidence

Screened evidence only; no ROM, savestate, archive, or generated resource is
included.

- ROM: `build/same-startup42-hoist-debug91.sfc`
- SHA-256: `b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`
- Output: `build/startup42-debug91-hoist5/report.json`
- Validator: `validate_scumm_startup42_nexen.py`, 3000 requested frames,
  `--light --minimal-observation`, sentences `(8,492,0)` and `(8,500,497)`.
- Both sentence transactions were consumed. Object 492 reached state 1;
  object 500 reached state 0; error stayed 0.
- The trace entered room 82, ran its authored local scripts, and returned to
  room 42. At frame 3002 C20 was empty and cutscene depth was zero. Remaining
  slots were authored delayed/live scripts 208, 75, 201, 204, and 203.

This supersedes no accepted claim; it extends the earlier debug89/debug91
evidence with a longer same-ROM observation window.
