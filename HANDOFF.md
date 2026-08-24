# Chad handoff — SAME 0.2.0

## What is here

SAME now has a reusable engine host rather than a Genesis-first target skeleton.
The same host runs two unrelated executable engine modules:

```text
SCUMM v5    real opcode-number subset, script slots, room/video/audio/save
Sierra AGI  decoded logic-resource subset, picture/video/input/save
```

The Python host is validated. The Poppy source implements the matching engine
lifecycle and a conformance demo, but it has not been assembled in this
environment.

The public Monkey Island repository was used only to understand donor shape. Your
local unpushed checkout is the authority for extraction.

## Step 1 — validate this release unchanged

Native PowerShell:

```powershell
cd SAME-0.2.0
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
.\tools\validate.ps1
```

Linux or WSL:

```bash
cd SAME-0.2.0
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
make all
```

Expected test result:

```text
Ran 87 tests
OK
Poppy lint: PASS (15 files, 80 global labels)
verified 4 golden cases
```

Do not edit the release or import donor code until Step 1 passes.

## Step 2 — assemble the isolated engine host

PowerShell:

```powershell
.\tools\build_snes.ps1 `
  -PoppyRoot E:\gh\poppy-astrobleem `
  -DotnetExe $env:USERPROFILE\.dotnet\dotnet.exe
```

Linux:

```bash
POPPY_ROOT=/home/chad/poppy-astrobleem-latest \
DOTNET_ROOT=/home/chad/.dotnet10 \
make snes
```

Expected output:

```text
build/same-engine-host.sfc
```

The build refuses the wrong Poppy repository, requires the known bank-cursor fix,
generates the shared ABI, runs Poppy source traps, assembles, audits the ROM, and
prints SHA-256.

Then run `docs/EMULATOR_GATE.md`. Stop at the first mismatch. Do not import the
SCUMM engine into an engine host whose own frame, input, event, or lifecycle state
has not passed.

## Step 3 — snapshot the current local Monkey Island project

Use the local checkout, including unpushed work:

```powershell
same donors check monkey --path E:\gh\SNES-SuperMonkeyIsland
same donors import monkey `
  --path E:\gh\SNES-SuperMonkeyIsland `
  --output vendor\reference
```

The manifest must record:

```text
exact HEAD
dirty=true/false
dirty paths
copied relative paths
size and SHA-256 per file
```

Do not clean, reset, or replace that checkout with the public branch merely to
make the import look tidy.

## Step 4 — establish the Monkey baseline before extraction

In the Monkey repository, run its current real build and its current tests—not
commands copied from the public README if the local workflow has changed.
Record:

- checkout HEAD and dirty paths;
- ROM path and SHA-256;
- opcode/VM test result;
- integration result through the current playable checkpoint;
- save/load result;
- one known screenshot and audio proof.

This is the independent oracle. SAME must not redefine success while moving code.

## Step 5 — extract SCUMM v5 by service, not by directory

Read `docs/SCUMM_V5.md`. The first extraction pass should do only this:

1. Put Monkey game identity, resource names, audio/speech maps, and quirks into a
   profile.
2. Keep the existing SCUMM semantic code and state layout intact.
3. Wrap its input path behind SAME input events.
4. Wrap resource lookup behind stable keys.
5. Wrap frame presentation behind SAME video.
6. Wrap music/SFX/speech behind SAME audio.
7. Wrap persistence behind the SAME save envelope.

After each wrapper lands, rerun the original Monkey tests and the SAME synthetic
SCUMM fixture. Do not move actors, rooms, scripts, audio, and rendering in one
change.

Bind `ScummV5_Engine_*` to `Same_ActiveEngine_*` only after the isolated engine
host ROM passes.

## Step 6 — prove that SCUMM is an engine

Monkey Island reaching the same checkpoint is necessary but not sufficient.
Create a second SCUMM v5 profile and resource conversion without changing the
SCUMM opcode core. New per-game behavior belongs in a named profile quirk or
adapter.

That is the gate that prevents SAME from becoming Super Monkey Island under a new
folder name.

## Step 7 — continue the King’s Quest/AGI path

The AGI host module is already independent and executable. Follow `docs/AGI.md`:

```text
conditions + GOTO
raw DIR/VOL resource discovery
vector picture + priority screen
views/cels/motion/collision
vocabulary/parser/text/inventory
sound completion semantics
complete saves
King's Quest I progression gate
```

AGI should continue sharing only platform services with SCUMM. Do not create a
common “adventure actor” or “verb” layer unless both engines independently prove
they need the same primitive.

## Known boundaries

- No `.sfc` was assembled here; Poppy/.NET were unavailable.
- The SCUMM Python module is a conformance subset, not the mature Monkey engine.
- The AGI module is foundational, not game-complete.
- SNES storage, saves, TAD/SPC, and SA-1 jobs are still service placeholders.
- The current local BOR architecture is unknown to this archive and is not
  assumed to use a VM.
- Directly derived ScummVM code carries ScummVM's GPL obligations; keep that
  module separable from independently written SAME host code.

The ordered continuation is in `docs/NEXT_GATES.md`.
