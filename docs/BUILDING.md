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

## SNES bootstrap

Requirements:

- Chad's `astrobleem/poppy` checkout;
- .NET 10 capable of running its `net10.0` CLI;
- Poppy HEAD containing the required bank-cursor fix;
- Python 3.11+ for generated ABI and audits.

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
