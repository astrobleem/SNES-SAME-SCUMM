# SAME — SA-1 Machine Environment

SAME is a reusable **game-engine, virtual-machine, and foreign-machine host** for
SNES/SA-1 hardware.

ScummVM compatibility is the first major engine ecosystem. The existing SNES
Super Monkey Island project demonstrates substantial prior implementation work,
but it is known-broken and is not a correctness oracle. SAME is not restricted
to SCUMM or even adventure games:
Sierra AGI, native 65816 engines, OpenBOR-like engines, MC68000/Z80 machines, and
Genesis-style hardware personalities all use the same host services.

```text
                         game profile / machine manifest
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
            engine personality                       machine personality
        SCUMM v5 / AGI / native VM                68000 / Z80 / device model
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                       SAME lifecycle + 16-byte service ABI
                                      │
          ┌──────────┬──────────┬─────┴─────┬──────────┬──────────┐
          │          │          │           │          │          │
        video      audio      input      resources    saves      jobs/time
          │          │          │           │          │          │
                         SNES / SA-1 / SPC700 / MSU-1
```

## What 0.2.0 contains

### Reusable engine host

- `Engine_Probe`, `Boot`, `Tick`, `HandleEvent`, `Save`, `Load`, `Suspend`,
  `Resume`, `Shutdown`, and capability negotiation.
- Engine profiles that carry game identity, timing, video geometry, resource
  bindings, options, quirks, and required/optional capabilities.
- An indexed 8-bit surface, 256-color palette, dirty rectangles, cursor, frame
  hashes, and PNG output.
- Logical digital input, pointer events, and text events.
- Normalized music, sound-effect, and speech requests.
- File, in-memory, composite, and SAME-package resource providers.
- CRC-protected, engine/game/schema-qualified save envelopes.
- A deterministic host jobs seam representing work that may later run on SA-1.
- The original 16-byte service packet and fail-closed event ring, extended with
  `ENGINE`, `SAVE`, and `JOBS` services without changing the wire layout.

### SCUMM v5 module

The host oracle executes a real subset of the SCUMM v5 opcode map, including
script yield/stop/jump, variables, arithmetic, comparisons, delays, room loads,
camera changes, and normalized music/SFX calls. It uses real SCUMM opcode numbers
and the opcode-bit operand-selection convention.

The bundled synthetic profile runs a persistent script for 120 frames, loads a
cooked room, starts music, increments a variable once per frame, presents exact
indexed frames, and round-trips a save.

The SNES ROM also contains an independent 61-byte semantic fixture. Its C1 gate
checks five exact VM ticks—normally six video frames—for operands, arithmetic,
branches, yield, delay, and stop. It uses no game ROM or Monkey-derived behavior.
The C2 matrix adds signed multiply/divide, bitwise operations, comparisons,
variable delay, and seven exact error cases; the complete emulator run uses 12
video frames.
The C3 matrix adds indexed results, all implemented variable operand forms,
16-bit wraparound, and deterministic two-slot scheduling; it uses 10 video
frames and proves a delayed slot cannot starve its runnable peer.
The C4 matrix adds nested start/stop-script lifecycle, 32 local variables per
slot, deterministic slot reuse, and fail-closed 25-slot capacity; it uses five
video frames and no game or donor data.
The C5 matrix adds recursive and freeze-resistant starts, nested freeze counts,
deterministic thaw, and script-running queries; it uses six video frames and no
game or donor data.
The C6 matrix adds direct and variable `chainScript` handoff, inherited slot
flags, fresh locals, caller non-resumption, and exact missing/capacity failures;
its three cases use six video frames and no game or donor data.
The C7 matrix adds packed bit-variable reads/writes and generic v5
`cursorCommand` state for visibility, user input, images, hotspots, cursor IDs,
charsets, and charset colors. Its exact host/SNES case uses one execution frame.
The C8 matrix adds all five canonical `$27 stringOps` forms. It preserves typed
glyph/control streams for the font layer, gives all 256 IDs independent
255-byte storage, persists host strings through saves, and matches exact raw
bytes across a bounded SNES scheduler yield.

S1 adds a validated Monkey 1 Ultimate Talkie profile template under
`examples/profiles/templates/`. It names raw game, audio-map, speech-index, and
optional script-patch resources plus narrowly scoped policy. The template
intentionally fails normal validation until the user supplies required game
resources; it is not bundled game data and does not make the current core a
complete Monkey engine.

S2 adds strict host-side raw v5 index/data lookup behind SAME resource keys and
logical SCUMM pointer/joypad/text input behind SAME events. Its encrypted raw
fixtures are generated and copyright-free; no Monkey ROM or commercial data is
part of the gate.

S3 adds exact logical room composition with actor priority, z-mask occlusion,
cursor projection, and resource-backed SCUMM v5 bitmap fonts. Baseline and
negotiated SNES acceleration plans must produce the same indexed result.

S4 adds backend-neutral score intent plus exact music, SFX, and speech mapping.
Curated TAD arrangements, live score interpretation, and MSU streams can be
profile-selected renditions of one logical timeline. Save schema 2 restores the
complete SCUMM state, including audio playheads, across a room transition.

S5 makes SCUMM the sole active engine in a generated SNES build selection. Its
host and SNES semantic/service traces agree exactly with zero packet loss; the
kernel no longer runs a private SCUMM conformance lane beside the demo engine.

This is the extraction seam for the much more complete public/local
SNES-SuperMonkeyIsland interpreter. It is **not** a claim that the small Python
oracle already replaces that 65816 engine.

### Sierra AGI v2 module

The AGI module accepts the decoded original logic-resource shape:

```text
u16 bytecode_size
bytecode[bytecode_size]
optional message count / offsets / strings
```

It currently executes the foundational variable, indirect-variable, flag,
room-change, sound, and control commands needed to establish an independent AGI
engine behind the same host ABI. A synthetic AGI logic and 16-color picture run
through the same video, input, save, resource, and timing services as SCUMM.

This is the start of the King’s Quest path, not a game-complete AGI interpreter.

### SNES/Poppy engine-host bootstrap

`runtime/snes/` now centers the same lifecycle:

- `Same_Engine_Boot`, `Same_Engine_Frame`, suspend/resume, and shutdown;
- engine-owned state separated from kernel/service-owned hardware state;
- generated packet ABI shared with the Python host;
- event routing for video, audio, storage, engine, save, and job services;
- auto-joypad held/pressed/released state;
- NMI-owned video commit;
- an active side-lane SCUMM v5 semantic nucleus and an inactive AGI adapter seam;
- one active conformance-demo engine;
- compatibility shims for SAME 0.1 machine targets.

The source passes static Poppy hazard checks. On the configured Linux host it
assembles with Chad's pinned Poppy fork into an audited 32 KiB LoROM.

## Validate it

Linux or WSL:

```bash
cd SAME-0.2.0
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
make all
```

Native PowerShell:

```powershell
cd SAME-0.2.0
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
.\tools\validate.ps1
```

The current gate is **123 unit/integration tests**, two 120-frame host-engine
runs, two save files, two framebuffer captures, two package builds, the legacy
Genesis scheduling simulation, SN76489 WAV generation, Poppy static checks, and
four exact SAME-VDP golden cases. The separate SNES C1 check is a five-tick
semantic trace observed in six video frames; C2 through C8 add bounded
copyright-free emulator matrices of 12, 10, five, six, six, and one execution
frame plus the C8 scheduler-yield case.

## Run the engines

```bash
same engine list
same engine validate examples/profiles/scumm_v5_conformance.json
same engine run examples/profiles/scumm_v5_conformance.json \
  --frames 120 \
  --output out/scumm-v5-report.json \
  --framebuffer out/scumm-v5-frame.png \
  --save-file out/scumm-v5-slot0.same-save

same engine run examples/profiles/agi_v2_conformance.json \
  --frames 120 \
  --output out/agi-v2-report.json \
  --framebuffer out/agi-v2-frame.png \
  --save-file out/agi-v2-slot0.same-save
```

The fixtures are synthetic and copyright-free. Real profiles point to resources
converted from data supplied by the user.

## Build the SNES host

The build requires Chad’s `astrobleem/poppy` fork and a .NET 10 SDK:

```powershell
.\tools\build_snes.ps1 `
  -PoppyRoot E:\gh\poppy-astrobleem `
  -DotnetExe $env:USERPROFILE\.dotnet\dotnet.exe
```

or:

```bash
POPPY_ROOT=/home/chad/poppy-astrobleem-latest \
DOTNET_ROOT=/home/chad/.dotnet10 make snes
```

Expected output:

```text
build/same-engine-host.sfc
```

The configured Linux host can run the completed emulator gates with:

```bash
make h0
make k1
```

`make k1` rebuilds the ROM, reruns H0, then verifies exact VRAM/CGRAM/OAM DMA,
channel ownership, held-input edges, frame pacing, and forced-blank deferral.

## Donor projects

Local unpushed work is allowed and expected. `same donors import` records exact
HEAD, dirty paths, sizes, and SHA-256 rather than substituting a stale public
branch.

```bash
same donors check monkey --path E:\gh\SNES-SuperMonkeyIsland
same donors import monkey --path E:\gh\SNES-SuperMonkeyIsland
same donors import scummvm --path E:\gh\scummvm
```

BOR remains a useful generic SNES-service donor, but SAME 0.2 makes no assumption
that the current BOR design is VM-centered.

## Boundaries

1. Engines own game semantics, never hardware windows.
2. Profiles own game-specific policy and quirks, never engine implementation.
3. Video, audio, input, resources, saves, timing, jobs, and debug are host
   services.
4. Optional SNES accelerators are negotiated capabilities, not required engine
   assumptions.
5. Missing resource, opcode, packet, save, or validation evidence fails loudly.
6. A second game must be supportable through a profile/resource change before an
   engine is considered extracted.
7. A non-SCUMM engine must keep working before SAME can be called a ScummVM-style
   host rather than a renamed Monkey Island port.

## Read next

- `STATUS.md` — exact verified boundary.
- `HANDOFF.md` — workstation steps and Monkey extraction gates.
- `docs/ENGINE_ABI.md` — reusable engine contract.
- `docs/SCUMMVM_COMPAT.md` — what “ScummVM on SNES” means here.
- `docs/SCUMM_V5.md` and `docs/AGI.md` — implemented semantics and next gaps.
- `docs/PORTING_ENGINE.md` — contract for adding another engine.
- `docs/NEXT_GATES.md` — ordered path forward.
