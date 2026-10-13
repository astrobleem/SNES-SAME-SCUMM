# SAME — Classic adventure engines on the Super Nintendo

**SAME (SA-1 Machine Environment)** is an experimental project to run classic game engines on real Super Nintendo hardware. We're building a reusable engine runtime, not a one-off remake of a game.

Our first target is **SCUMM v5**, the engine behind several LucasArts point-and-click adventures. **Indiana Jones and the Fate of Atlantis** is the proving ground. The longer-term goal is to support other engines through the same video, audio, input, storage, and save services.

> **This is a development project, not a playable FATE release.** The source is public; the commercial game data is not included. Hardware compatibility and complete gameplay are not yet established.

## How it works

The original game's scripts still run as SCUMM bytecode. SAME compiles the game's resource layout, then runs its own SCUMM interpreter on the SNES.

1. **On a PC:** Tools read game files you provide and build a checked **SAMEPKG** data package.
2. **On the SNES:** The cartridge runs the interpreter and shared game-engine services, using the **SA-1** and its memory where needed.
3. **From external storage:** **MSU-1** supplies script code, room information, images, and palettes that would not fit in a normal SNES ROM.
4. **On screen:** The existing SNES renderer, controls, and script scheduler use those streamed resources.

This is not ScummVM running on the SNES, and it is not a pre-rendered video of a PC game. It is an independently developed runtime executing real SCUMM instructions.

## What's working

- The DOS-CD edition of FATE has been parsed into **96 indexed rooms** and **2,203 executable ProgramUnits**, packaged in a reproducible external data file.
- A **4 MiB SNES ROM** can boot using the full ProgramUnit directory and fetch real script code and room resources over MSU-1.
- The existing interpreter executes fetched scripts, including nested scripts, yields, object verbs, and room transitions. Resident script slots are reused safely.
- Room objects, names, walkboxes, movement routes, indexed pixels, and palettes can come from MSU-1 instead of duplicate ROM tables.
- In the Nexen emulator, a bounded authentic FATE test completed the established **0 → 68 → 0 → 4 → 5 → 6 → 7 → 3** room sequence and seven scripted player actions.
- Independent GitHub Actions checks run the host tests, validate code and memory layouts, verify a synthetic data package, and build/audit a copyright-free SNES ROM.

These are engineering acceptance tests, **not proof that FATE can be played from beginning to end**. Some room/resource diagnostics still need native verification, and GitHub-hosted CI does not run the Nexen emulator.

## What still needs work

- More SCUMM instructions and game-specific resource behaviors need testing and implementation.
- Original graphics and costume formats, text and fonts, and sound/music (including iMUSE) are incomplete.
- Streamed-game save/restore and the broader runtime resource dependencies need work.
- Actual SNES/flash-cartridge hardware testing is still required.

**The goal is to make the engine general enough for other SCUMM v5 games—not just to patch FATE until one route works.**

## Try the open-source tests

You do **not** need FATE or other commercial game files to run the public test suite.

On Linux or WSL, with Python 3.11+ installed:

```bash
git clone https://github.com/astrobleem/SNES-SAME-SCUMM.git
cd SNES-SAME-SCUMM
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
make test
make validate
```

Building an SNES ROM additionally requires the project's pinned Poppy/Pansy assembler toolchain and .NET SDK. See [the reproducible CI setup](docs/INDEPENDENT_CI.md) and [the SNES build script](tools/build_snes.sh). The experimental full-game packaging process uses a separate, legally obtained source-game archive; none is distributed here.

## Where to look

- [SCUMM v5 source compiler and package tools](src/same/engines/scumm_v5/) — host-side engine logic and conversion.
- [SNES runtime](runtime/snes/) — 65816 code, game services, renderer, and storage.
- [Whole-source MSU-1 packaging](docs/scumm-toolchain/WHOLE_SOURCE_MSU_PACKAGE.md) — what is packaged and what is not yet executable.
- [Live-room resource integration](docs/scumm-toolchain/LARGE_ROOM_METADATA.md) — the room-data loader and limits.
- [Independent CI](docs/INDEPENDENT_CI.md) — automated checks and what they actually verify.
- [Issues](https://github.com/astrobleem/SNES-SAME-SCUMM/issues) — known limitations and upcoming work.

## Project status and licensing

The first merged MSU-1 integration baseline is [commit `781061a`](https://github.com/astrobleem/SNES-SAME-SCUMM/commit/781061a24f6994196603771ecd8e26341c98fcd1) (October 13, 2026). It is an **experimental engineering checkpoint**, not a finished game or production release.

SAME's code is released under the [Unlicense](LICENSE). LucasArts games and their assets belong to their respective rights holders. **No copyrighted game data is included or licensed by this repository.**
