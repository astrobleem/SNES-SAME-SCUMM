# Continuation gate

This repository supports persistent engineering campaigns, but continuation
must remain bounded and evidence-driven.  Intermediate diagnosis, a passing
build, a validator result, or tool synchronization alone does not complete an
active objective; conversely, player-choice boundaries do not require endless
branch exploration.

Before sending a final response, perform and state internally a `STOP-GATE`:

1. Is the active user objective actually complete?
2. If not, is there a genuine allowed stop condition backed by evidence?
   - required ATLANTIS source data is absent;
   - a genuinely major subsystem or hardware/capacity redesign is required;
   - an unresolved semantic contradiction remains after substantial tracing;
   - or the user explicitly asks for a status-only response or to stop.
3. If neither is true, continue only with an experiment that changes a
   hypothesis, observation, implementation, or controlled input. Record
   successful interactions as reusable replay steps and record known setup
   and input procedures once, then reuse them instead of relearning them.
4. Two equivalent UI attempts that produce no new evidence end UI retries.
   Switch to instrumentation or report the concrete blocker. A failed
   regression blocks further gameplay until it is fixed or its failure is
   explained by a justified expectation change. Do not ignore red tests to
   pursue another room or branch.
5. A bounded, evidenced no-progress stop is valid. Do not explore every
   player-choice branch unless the active objective specifically requires it.
   Update `session_checkpoint.md` at meaningful milestones.

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

For Fate/SCUMM work, keep one repeatable input prefix and instrument the next
specified boundary. At a choice boundary, investigate only the action needed
for the current objective; do not launch an open-ended playthrough. Preserve
the distinction between synthetic fixtures and authentic game resources.

## Emulator operation — mandatory

- Never execute Nexen or Mesen to discover command-line arguments. Do not use
  `--help`, `-h`, `/?`, `--version`, or guessed switches; these graphical
  applications may open dialogs on the user's desktop.
- Do not launch an emulator from an exploratory shell command. Read the
  repository's documented invocation or an existing working validator.
- Never inherit or use the user's `DISPLAY` or `XAUTHORITY`, reconnect to
  MobaXterm, or treat the user's desktop as a test environment.
- Use only the project's canonical supervised emulator launcher with its own
  private Xvfb display and MCP port. Nexen is the default for automated native
  acceptance requiring MCP; Mesen is reserved for explicitly selected
  independent validation.
- Before each diagnostic, check for prior test-owned emulator/MCP processes.
  Give each run a dedicated MCP port, explicit deadline, supervised process
  tree, and guaranteed cleanup. Do not kill unrelated processes. A diagnostic
  must not exceed its configured timeout or leave emulator processes running.
- If the canonical launcher is absent or broken, stop and repair the launcher
  without executing an emulator on the user's desktop. Never fall back to a
  different emulator because the requested one failed to start.
- An X11/display failure never authorizes retrying on another display or the
  user's desktop. Do not enable, reconfigure, or ask the user to enable
  MobaXterm's X server for automated testing. If private headless execution is
  unavailable, report the dependency instead of launching elsewhere.
