# Continuation gate

This repository is in a persistent engineering campaign.  Intermediate
diagnosis, a passing build, a validator result, tool synchronization, a new
frontier, or a player-choice boundary is **not** permission to end work.

Before sending a final response, perform and state internally a `STOP-GATE`:

1. Is the active user objective actually complete?
2. If not, is there a genuine allowed stop condition backed by evidence?
   - required ATLANTIS source data is absent;
   - a genuinely major subsystem or hardware/capacity redesign is required;
   - an unresolved semantic contradiction remains after substantial tracing;
   - or the user explicitly asks for a status-only response or to stop.
3. If neither is true, do **not** send a final response. Continue from the
   current checkpoint, improve tooling if needed, and update
   `session_checkpoint.md` at milestones instead.

For the current Fate/SCUMM work, player choices invoke branch exploration;
they are not stop conditions.  Do not substitute a report for the next
authorized engineering step.
