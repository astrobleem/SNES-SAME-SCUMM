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

## Repository engineering constraints

The architecture and validation requirements remain documented here even
when a long-running campaign is active:

- Keep game-specific policy in profiles or engine adapters, not the kernel.
- Keep engine semantics out of video/audio/input/storage/save backends.
- Do not write PPU registers outside the video backend/NMI commit path.
- Do not let engines or machine personalities claim DMA channels directly.
- Do not accept guest addresses as SNES pointers.
- Do not silently drop a service packet lacking `DROP_OK`.
- Do not report missing oracle evidence as a pass.
- Do not move work to SA-1 without a measured gate or copy a donor subsystem
  wholesale into the build.
- Keep Monkey Island quirks specific; do not make them SCUMM v5 rules or make
  SCUMM facilities mandatory for AGI or another engine.

Before editing, read `STATUS.md`, `docs/ARCHITECTURE.md`,
`docs/ENGINE_ABI.md`, and the active gate in `docs/NEXT_GATES.md`. Follow
`docs/POPPY_NOTES.md`; in particular, do not use `@` locals in included files,
`stz.l`, long-indexed Y, standalone `^(Label)`, or short access to far WRAM.

## Validation

After a source change, run the focused tests and `make test` plus `make
validate`. When a SNES ROM can be built, run `make snes` and the relevant
prior emulator gates. Keep generated artifacts and original game data out of
commits unless a task explicitly requires a source-neutral manifest or
selection input. An engine extraction is not complete based only on one game:
retain synthetic semantic tests, save/load coverage, and a second profile or
resource set where applicable.

For the current Fate/SCUMM work, player choices invoke branch exploration;
they are not stop conditions.  Do not substitute a report for the next
authorized engineering step.
