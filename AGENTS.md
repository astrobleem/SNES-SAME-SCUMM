# SAME contributor instructions

Read `STATUS.md`, `docs/ARCHITECTURE.md`, `docs/ENGINE_ABI.md`, and the active gate
in `docs/NEXT_GATES.md` before editing.

## Non-negotiable boundaries

- Keep game-specific policy in profiles or engine adapters, not the kernel.
- Keep engine semantics out of video/audio/input/storage/save backends.
- Do not write PPU registers outside the video backend/NMI commit path.
- Do not let engines or machine personalities claim DMA channels directly.
- Do not accept guest addresses as SNES pointers.
- Do not silently drop a service packet lacking `DROP_OK`.
- Do not report missing oracle evidence as a pass.
- Do not move work to SA-1 without a measured gate.
- Do not copy an entire donor subsystem into the build at once.
- Do not make a Monkey Island quirk a SCUMM v5 rule.
- Do not make a SCUMM facility mandatory for AGI or another engine.

## Required validation after every change

```bash
make test
make validate
```

When a SNES ROM can be built, also run:

```bash
make snes
```

and the prior emulator gates. Preserve exact ROM identity.

## Engine completion rule

An engine extraction is not complete because one existing game still runs. It
must also pass a synthetic semantic suite, save/load, and a second profile or
resource set without editing the engine core.

## Poppy source rules

Follow `docs/POPPY_NOTES.md`. In particular, no `@` locals in included files and
no `stz.l`, long-indexed Y, standalone `^(Label)`, or short access to far WRAM.

## Donor workflow

Import a hash-recorded local snapshot. Dirty/unpushed work is valid and must be
recorded. Extract one neutral mechanism behind a SAME interface. Keep the donor's
existing tests and observed behavior as independent regression evidence, not
semantic truth. Do not rewrite the donor and the SAME adapter simultaneously
without a fixture that distinguishes them.
