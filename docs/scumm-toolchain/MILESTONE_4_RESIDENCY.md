# Milestone 4: Initial Executable Residency Planning (Historical)

Status: **IMPLEMENTED, ANALYSIS ONLY; SELECTOR ESTIMATES SUPERSEDED**.

This milestone first compared source executable identities against the backend
selector pool. It correctly kept source identities selector-free and
identified the 25-slot scheduler bound, staged room transitions, global
continuations, and save-state concerns. Its first room-size arithmetic,
however, counted each object-verb semantic IR record as a separate
selector-bearing backend program.

That projection was incorrect. The existing SNES generator emits one
selector-bearing OBCD record per object, containing an object verb-entry table;
several semantic `ObjectVerb` identities therefore share one backend program
unit. The previously stated room-43 value of 185 compared semantic executable
records with selectors and is withdrawn. It was not evidence of overflow.

The corrected model is implemented in `program_units.py` and
`residency.py`. The exact source-to-unit mapping, selector-free manifest,
room-by-room capacity analysis, selector-reference audit, and pinning contract
are documented in
[`MILESTONE_5_PROGRAM_UNITS.md`](MILESTONE_5_PROGRAM_UNITS.md). All present-day
selector-capacity claims should use Milestone 5's ProgramUnit counts.

## Findings retained from this milestone

- The backend currently assigns build-global byte selectors; it does not
  reassign them on room changes.
- A running/yielded scheduler slot retains its selector with PC and locals.
- Outgoing room cleanup and incoming entry are staged; a surviving global
  continuation must remain resolvable.
- The host save representation preserves canonical source script identity,
  while emulator savestates preserve raw WRAM selectors and depend on matching
  program tables.
- Static dependency unions do not prove concurrent activation/liveness.

These lifecycle observations remain useful; the semantic-record-to-selector
arithmetic does not.
