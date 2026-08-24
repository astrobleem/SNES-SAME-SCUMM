# Donor project map

SAME is a separate host with explicit interfaces. Donors remain independent
implementation references and playable projects. A donor's observed behavior
may be incomplete or broken and is never promoted to semantic truth merely
because no better SNES implementation exists. ScummVM is the semantic reference.

## `astrobleem/SNES-SuperMonkeyIsland` — first engine donor

Candidate reusable pieces:

- SCUMM v5 opcode core and dispatch table;
- script slots, variables, room/object/actor systems;
- costumes, chores, walking, walkboxes, camera, dialog, verbs, and cutscenes;
- room/costume/resource conversion tools;
- indexed/tiled rendering, OAM, z-mask/HDMA, and SA-1 scaling paths;
- TAD music/SFX and MSU-1 speech integration;
- save/load implementation;
- opcode and gameplay integration harnesses.

Extract game policy rather than importing it as engine law: Monkey-specific sound
maps, intro timing, speech tables, copy-protection behavior, coordinate quirks,
and script workarounds belong in a Monkey profile/adapter.

The Monkey donor is known-incomplete and is not a correctness oracle or
regression baseline. It may suggest mechanisms worth independently verifying,
but its behavior supplies no SAME pass condition.

K1 inspected local HEAD `640e48359c5a17a9edd3a0c2208d62180757a2c1` on
2026-08-22. The checkout had pre-existing changes in
`tools/mesen_mcp/validate.py`, both vendored WLA binaries, and two untracked
`*-new` WLA binaries; SAME did not modify them. The neutral observations used
were NMI-owned PPU commits, `$4212` auto-joy completion, publish-after-populate
OAM/CGRAM shadows, and serialized DMA channel use.

An archived investigation characterized the user-supplied binary bundle at ROM SHA-256
`89090a712861492b2573812c220e2dd77d241c9e1b55c87e1e126207132fe803`.
It is not layout-identical to either checkout. A clean latest checkout exists at
`/home/chad/SNES-SuperMonkeyIsland-latest`, GitHub HEAD
`3247641c38d00aa2ce5388708ab7301d43d865aa`. No source build or long gameplay
run is pending. See `docs/S0A_MONKEY_BASELINE.md` only as historical inventory.

## `scummvm/scummvm` — behavioral and interface oracle

Use selected source as a semantic reference for:

- platform/backend versus engine separation;
- SCUMM v5 opcode behavior;
- AGI opcode tables, logic, picture, view, parser, sound, and save behavior;
- game/version detection and known original-script workarounds.

Directly copied or derived modules must honor ScummVM's GPL. Keep them separable
from independently written SAME host code.

## `AlbanBedel/scummc` — compiler and authoring reference

ScummC demonstrates a practical SCUMM source compiler, linker, resource tools,
and from-scratch game workflow. Its current documented targets are SCUMM v6 and
partial v7, not v5. SAME may consult its compiler architecture and resource
workflow, but C1/C2 v5 byte encodings and semantics do not depend on ScummC
output. ScummC is GPL-2.0, so any derived implementation must be tracked as such.

## `astrobleem/snes-bor` — optional SNES-service donor

Potential neutral mechanisms:

- input and NMI pacing;
- DMA queue/channel ownership;
- OAM and allocators;
- streaming caches and MSU-1 access;
- TAD/SPC integration;
- Poppy audit techniques.

Do not assume the current local BOR implementation is VM-centered. Do not import
player-slot, entity-count, camera, roster, spawn, or game-state policy into SAME.

K1 cloned and inspected clean local HEAD
`b80edcbb8020373b9652cece24fb01d6d64cfb7c` on 2026-08-22. In particular,
`core/input.pasm` waits for auto-joy completion and derives `new & ~old` edges;
`core/dma.pasm` publishes complete descriptors, uses a fixed-capacity and
byte-budgeted queue, and drains it from the NMI/forced-blank commit path. SAME
reimplemented those mechanisms behind its own WRAM/service contract; no BOR
entity, VM, cache, or game policy was copied.

## `astrobleem/supermn-snes` and `astrobleem/blktiger-snes`

These remain foreign-machine donors for MC68000, Z80, device portals, traces, and
differential validation. Taito X and Black Tiger hardware behavior belongs in
target adapters, not CPU cores.

## `astrobleem/poppy`

Required assembler identity. The build checks the repository and required
bank-cursor ancestor before invoking its `net10.0` CLI.

## Import workflow

```powershell
same donors check monkey --path E:\gh\SNES-SuperMonkeyIsland
same donors import monkey --path E:\gh\SNES-SuperMonkeyIsland
same donors import scummvm --path E:\gh\scummvm
```

The importer records exact HEAD, dirty paths, copied paths, byte counts, and
SHA-256. Imported files are references only and are never added to the build
automatically.
