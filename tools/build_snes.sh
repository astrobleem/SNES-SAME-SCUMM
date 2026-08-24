#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POPPY_ROOT="${POPPY_ROOT:-/home/chad/poppy-astrobleem-latest}"
DOTNET_ROOT="${DOTNET_ROOT:-/home/chad/.dotnet10}"
POPPY_DLL="${POPPY_DLL:-$POPPY_ROOT/src/Poppy.CLI/bin/Release/net10.0/poppy.dll}"
PYTHON="${PYTHON:-python3}"
EXPECTED_POPPY_SHA256=715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e

cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" tools/check_poppy.py "$POPPY_ROOT" --dll "$POPPY_DLL"
POPPY_SHA256="$(sha256sum "$POPPY_DLL" | awk '{print $1}')"
if [[ "$POPPY_SHA256" != "$EXPECTED_POPPY_SHA256" ]]; then
    echo "Refusing unpinned Poppy DLL: $POPPY_DLL" >&2
    echo "observed: $POPPY_SHA256" >&2
    echo "expected: $EXPECTED_POPPY_SHA256" >&2
    exit 1
fi
echo "Poppy SHA-256: $POPPY_SHA256"
"$PYTHON" -m same.cli abi generate runtime/snes/generated/abi.inc.pasm
"$PYTHON" tools/generate_snes_engine_selection.py \
    --engine "${SAME_SNES_ENGINE:-demo}"
"$PYTHON" tools/lint_poppy.py runtime/snes/main.pasm
mkdir -p build
SAME_SNES_OUTPUT="${SAME_SNES_OUTPUT:-build/same-engine-host.sfc}"
DOTNET_ROOT="$DOTNET_ROOT" PATH="$DOTNET_ROOT:$PATH" \
    dotnet "$POPPY_DLL" -t snes -I runtime/snes \
    runtime/snes/main.pasm -o "$SAME_SNES_OUTPUT" --no-verify
"$PYTHON" tools/finalize_snes_rom.py "$SAME_SNES_OUTPUT"
"$PYTHON" tools/audit_snes_rom.py "$SAME_SNES_OUTPUT"
sha256sum "$SAME_SNES_OUTPUT"
