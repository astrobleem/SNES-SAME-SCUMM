#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for case_name in 01_solid_palette 02_single_tile 03_tile_flip 04_plane_a; do
    echo "== $case_name =="
    CASE="$case_name" "$ROOT/tools/build_rom.sh"
done
