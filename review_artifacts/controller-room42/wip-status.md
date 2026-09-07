# WIP review status

Architecture cleanup is present in the focused source extract: SCUMM is kept
blind to PPU, BG2/Mode3, BW-RAM, and backend implementation names. The current
WIP includes the controller/presentation sources and focused tests copied from
the dirty development tree.

Status:

* controller/semantic execution: previously reported passing;
* native visual evidence: mixed, independently inspectable below;
* visual defects: observed in the preserved failing captures;
* HUD/dialogue handoff: WIP; latest `native-final5` stops before inspect mode;
* controller-playable milestone: NOT PASS.

This branch is a review checkpoint only. It is not a fix and does not claim
that the current dirty-main implementation is accepted.
