# ScummVM compatibility strategy

## What the goal means

The goal is a SNES host capable of running multiple game-engine families that
ScummVM supports, beginning with SCUMM v5 and Sierra AGI.

It does **not** initially mean compiling the entire current ScummVM desktop C++
program unchanged for 65816. That program includes a launcher, GUI, filesystem
abstractions, software audio and video facilities, many engines, and platform
features that are neither free nor useful on this hardware.

SAME adopts the valuable architectural split:

```text
platform/backend services  <---->  independent game engines
```

but implements a smaller SNES-native host.

## Three compatibility levels

### Level 1 — behavioral compatibility

A native engine implements the same game semantics and uses upstream ScummVM as
an independent oracle. SNES-SuperMonkeyIsland already follows this model for
SCUMM v5 behavior.

### Level 2 — source-derived engine module

Selected upstream engine code or algorithms are ported behind SAME. That module
must follow upstream GPLv3 obligations. SAME’s independently written kernel and
service ABI remain separable.

### Level 3 — upstream-buildable SAME backend

A future constrained ScummVM build could provide an `OSystem`-like SAME backend
and statically select a small engine set. This is only worthwhile after memory,
compiler, ABI, and performance experiments demonstrate that the C++ core can be
made practical.

0.2 implements Level 1 infrastructure and the module boundary needed for Level
2. It makes no Level 3 claim.

## Why SCUMM and AGI first

SCUMM v5 has a mature SNES donor with substantial gameplay and test coverage.
AGI is comparatively small, uses low-resolution graphics and compact logic
resources, and proves the architecture is not secretly Monkey-Island-specific.

Together they force the host to support:

- two unrelated bytecode models;
- different screen geometry and palette expectations;
- pointer-centric and parser/digital input;
- different resource organization;
- independent save payloads;
- shared video/audio/storage/timing services.

## Build selection

The SNES should initially build one engine family into one ROM. Dynamic desktop-
style plugins are not required. Reusability comes from stable source modules,
profiles, packages, and services—not from loading arbitrary code at runtime.

A later multi-engine launcher is possible if ROM and WRAM budgets support it.

## Licensing boundary

- SAME’s independently written host code is distributed under its own license.
- Directly copied or derived ScummVM engine code is GPLv3-compatible and must be
  kept in an appropriately licensed module/distribution.
- Original game data is not distributed. Profiles and tools consume data from a
  user-supplied copy.
- Donor import manifests preserve exact provenance.
