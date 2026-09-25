#!/usr/bin/env python3
"""Report the fixed-header slack in a Poppy SNES memory map."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: report_snes_layout.py MAP")
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(
        r"^;\s*1\s+\$8000\s+\$([0-9A-Fa-f]{4})\s+\d+\s+\d+\s*$",
        text,
        re.MULTILINE,
    )
    if match is None:
        raise SystemExit(f"bank 0 segment not found in {path}")
    end = int(match.group(1), 16)
    header = 0xFFC0
    free = header - (end + 1)
    if free < 0:
        raise SystemExit(f"bank 0 overlaps the header by {-free} bytes")
    print(
        f"SNES bank 0 layout: end=${end:04X} "
        f"free_before_header={free} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
