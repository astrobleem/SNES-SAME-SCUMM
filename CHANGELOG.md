# Changelog

## 0.2.0 — reusable engine host

- Reframed SAME around reusable engine personalities while preserving machine
  personalities.
- Added engine lifecycle, descriptors, registry, probes, capability negotiation,
  profiles, and deterministic host execution.
- Added indexed-video, input event, normalized audio, resource-provider, save,
  job, clock, and debug services.
- Added engine/save/job packet services while retaining the 16-byte ABI revision.
- Added a functional SCUMM v5 host-oracle module using real opcode numbers.
- Added a functional Sierra AGI v2 module and decoded logic-resource parser.
- Added synthetic SCUMM and AGI profiles, pictures/rooms, scripts/logics,
  screenshots, save artifacts, and combined adventure package.
- Reworked the Poppy bootstrap around `Same_Engine_*`; retained 0.1 target shims.
- Added explicit SCUMM v5 and AGI assembly adapter seams.
- Added Super Monkey Island and upstream ScummVM donor definitions.
- Removed the stale requirement that the BOR donor contain a particular public
  VM-era commit; local unpushed state is now recorded as authoritative.
- Expanded validation from 52 to 85 tests.

## 0.1.0 — machine runtime bootstrap

- Introduced service packets, event queue, scheduler, buses, packages, input,
  oracle, PSG lab, SAME-VDP lab, donor tooling, and the first Poppy kernel demo.
