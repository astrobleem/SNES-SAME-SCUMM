# Generic SCUMM Controller Service

This milestone separates the generic controller service from the bounded Fate
scenario fixture.

## Capability boundary

`SAME_BUILD_SCUMM_CONTROLLER` enables the generic controller service. The
fixture capability implies it, so existing fixture builds retain their
behavior:

- room-install interaction reset and room-ready latch
- cursor/input processing
- active-room CDHD hit testing
- authored VERB discovery and runtime C17/OBNA HUD composition
- normal sentence submission and `ACTION_PENDING`
- selected-object revalidation and cursor invalidation

These paths do not inspect Fate room or object identities.

`SAME_BUILD_SCUMM_CONTROLLER_FIXTURE` remains limited to scenario startup
seeding/room handoff, actor and locker visual fixture code, behavior masks, and
capture diagnostics. It is not required to compile or run the generic service.

The controller remains SCUMM-carrier- and video-backend-blind.

## Verification

The fixture-enabled personality assembled, linted, finalized, and passed the
SA-1/BW-RAM audit. A controller-disabled SCUMM personality also assembled,
linted, finalized, and passed the same audit. Focused controller tests passed
56/56.
