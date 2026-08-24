# Donor references

This directory is intentionally empty in release archives.

`same donors import NAME --path PATH` copies only the configured reference
files and writes their exact Git HEAD, dirty-path list, byte sizes, and SHA-256
hashes. A dirty local checkout is allowed and is treated as authoritative; the
manifest records that fact rather than silently substituting the public branch.

The current donor roles are:

- `monkey` — mature native SCUMM v5/SNES implementation and test harness.
- `scummvm` — behavioral and interface reference for SCUMM and AGI.
- `bor` — generic SNES services (NMI, DMA, input, OAM, streaming, TAD), not a
  commitment to any particular BOR VM architecture.
- `superman` / `blacktiger` — foreign CPU and hardware-personality work.
- `poppy` — assembler identity check only.

Imported donor code is not redistributed in the normal SAME source archive.
