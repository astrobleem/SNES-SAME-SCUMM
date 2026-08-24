#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASE="${CASE:-01_solid_palette}"
POPPY_ROOT="${POPPY_ROOT:-/home/chad/poppy}"
DOTNET_ROOT="${DOTNET_ROOT:-/home/chad/.dotnet10}"
POPPY_DLL="${POPPY_DLL:-$POPPY_ROOT/src/Poppy.CLI/bin/Release/net10.0/poppy.dll}"
PYTHON="${PYTHON:-python3}"

cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" tools/check_poppy.py "$POPPY_ROOT" --dll "$POPPY_DLL"
"$PYTHON" -m same_vdp.cli select-snes "generated/$CASE" --output snes/generated
mkdir -p build
DOTNET_ROOT="$DOTNET_ROOT" PATH="$DOTNET_ROOT:$PATH" \
    dotnet "$POPPY_DLL" snes/main.pasm -o "build/same-vdp-$CASE.sfc" --no-verify
sha256sum "build/same-vdp-$CASE.sfc"
