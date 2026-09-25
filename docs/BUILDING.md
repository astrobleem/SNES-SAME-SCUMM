# Building SAME

## Host SDK

Requirements:

- Python 3.11+
- Pillow 10+

Linux/native shell:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
make all
```

Native PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
.\tools\validate.ps1
```

The host build never invokes an emulator.

## Tests and optional original-data integrations

The ordinary test suite uses the repository's original/copyright-free
fixtures and does not require a game archive or samples from another title.
Run it from a clean checkout with:

```bash
make test
```

`make generate`, a prerequisite of `make test`, emits the copyright-free
generated includes needed by source lint, including a lint-only TAD layout
fallback. `tools/build_snes.sh` replaces that fallback with layout data parsed
from the exact TAD image before assembly. The source linter follows known-active
build branches; unknown conditions remain fail-closed. `make validate` checks
the runnable AGI/SCUMM conformance profiles, not optional music catalog
templates.

Tests that inspect authentic Fate resources are optional. They skip when
`SAME_FATE_DEMO_ARCHIVE` is unset and fail explicitly if it names a missing or
invalid archive. Monkey integrations use an explicitly supplied archive in the
same manner. Never use a machine-local default path as acceptance evidence.
The optional `make s6-preflight` command likewise requires an explicit
`SAME_FATE_DEMO_ARCHIVE=/path/to/user-supplied/archive.zip` argument; its
distribution-notice check records source text and is not a legal determination.
The historical title-audio targets (`m4`–`m9`, the integrated `m10` target,
`m19`–`m23c`, and `m24rb`) are currently guarded: they depended on committed
game-derived sample/MML inputs removed during PR #1 asset clearance, or on
title-specific output built from those inputs. `m10-build` remains available
for its independent QTMA fixture; `m11`–`m18` are synthetic QTMA profiles and
remain supported. The source parsers can still process user-supplied data, but
the removed pre-rendered Fate/Monkey audio profiles are not reproduced by the
repository. The generic audio engine and M24R-A synthetic conformance fixture
remain supported.

## SNES bootstrap

Requirements:

- Chad's `astrobleem/poppy` checkout;
- .NET 10 capable of running its `net10.0` CLI;
- Poppy HEAD containing the required bank-cursor fix;
- Python 3.11+ for generated ABI and audits;
- Cargo and the pinned, locally available Terrific Audio Driver source checkout
  required by `tools/build_m24ra_tad_toolchain.py`. If it is not adjacent to
  this checkout, set `M24RA_TAD_DONOR_DIR` for Make or `SAME_TAD_DONOR_DIR` for
  direct shell/PowerShell builds.

The default SNES audio input is the original M24R-A conformance fixture. Its
waveform is generated deterministically into ignored `build/` output; no WAV,
BRR, or original-game audio is bundled as a build prerequisite. Original game
archives remain external user inputs for explicitly selected integrations.

### Native PowerShell

```powershell
.\tools\build_snes.ps1 `
  -PoppyRoot E:\gh\poppy-astrobleem `
  -DotnetExe $env:USERPROFILE\.dotnet\dotnet.exe
```

### Linux

Defaults match the existing arcade projects:

```bash
POPPY_ROOT=/home/chad/poppy-astrobleem-latest \
DOTNET_ROOT=/home/chad/.dotnet10 \
make snes
```

The build sequence is intentionally fail-closed and pins the same corrected
Poppy DLL used by `supermn-snes`:

1. identify the Poppy remote and required ancestor;
2. generate the 65816 ABI include from Python;
3. run the Poppy trap checker;
4. assemble with the explicit `-t snes` target used by the working Superman
   build;
5. finalize the explicit LoROM header and checksum;
6. audit LoROM header, vectors, and the actual ROM byte-sum checksum;
7. print SHA-256.

Output:

```text
build/same-engine-host.sfc
```

Run the accepted fresh-power Nexen gate separately:

```bash
make h0
```

This preserves its JSON report and boot/input screenshots under
`build/h0-nexen-<rom-hash-prefix>/`.

## Why there is no checked-in ROM

The ROM is a generated artifact and the source archive was produced without the
local Poppy/.NET environment. Keeping source and exact build gates is more honest
than packaging an unverified binary from another assembler.
