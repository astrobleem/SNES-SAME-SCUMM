# Focused implementation diff index

The full campaign diff is intentionally excluded. These are the reviewable
changes and their exact source locations in the private implementation tree.

## Logical message lifetime

`runtime/snes/engines/scumm_v5_matrix_far.pasm`:

```diff
 ScummV5_Talk_Wait_FarEntry:
+    lda.l SAME_SCUMM_PC
+    dec
+    sta.l SAME_SCUMM_TALK_WAIT_PC
     ...
+    lda.l SAME_SCUMM_TALK_WAIT_PC
+    sta.l SAME_SCUMM_PC
```

The headless fixture path records logical `FF 03` controls and retains the
message lifetime; it does not clear C23/talk state at delivery. Presentation
storage remains bounded.

## Scheduler sentence-instance witness

`runtime/snes/engines/scumm_v5_matrix_far.pasm` resets the per-launch fetch
counter, allocation frame, and allocation C4 marker when a sentence slot is
found. This prevents a cumulative fetch count or later PC-zero observation
from being mistaken for failure of a new instance.

## Test/validator changes

- `tests/test_scumm_v5_engine.py` checks the far wait save/restore boundary.
- `tools/validate_scumm_message_wait_nexen.py` validates logical completion,
  delayed release, and controls beyond the compact presentation window.
- `tools/validate_scumm_message_talk_nexen.py` exposes control witnesses.

Full source remains in the working repository for line-by-line review; this
screened branch deliberately contains only this source-level index and does
not embed game-derived bytes.
