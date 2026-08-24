# Guest adapters and foreign buses

## Why the bus is separate from a CPU core

Superman and Black Tiger need different CPU interpreters, but both interpreters
must remain reusable. A core that directly knows `$C00004` is a VDP control port
cannot be reused for a Taito X board. SAME therefore gives a core only a bus.

A target manifest declares each bus:

```json
"buses": {
  "m68k": {"address_bits": 24, "endianness": "big"},
  "z80":  {"address_bits": 16, "endianness": "little"}
}
```

It then declares non-overlapping memory and device regions. `same target validate`
rejects an out-of-range or overlapping map before a core runs.

## Device portals

A portal is a target adapter at a foreign address range. It can:

- preserve a register-level state model;
- emit SAME packets;
- return status or open-bus values;
- trace every access;
- stop with an explicit unsupported-operation fault.

A portal must not call an SNES backend recursively from inside a guest instruction.
It records work for the appropriate scheduler phase.

## Core acceptance gates

Before a core is called a SAME guest:

1. Its semantic opcode tests pass outside a game.
2. Reads/writes use `GuestBus` equivalents, with no hidden target globals.
3. State serialization round-trips exactly.
4. A fixed instruction budget yields cooperatively and repeatably.
5. Faults include guest PC/opcode and the last bus operation.
6. A host trace and SNES trace agree for the same test program.

Superman's existing MC68000 semantic sweeps are the starting oracle for the 68K
adapter. Black Tiger's Z80 work needs the equivalent gate before game boot work.

## OpenBOR / BOR-derived engines

SAME does not presume whether the current local BOR project is a native engine,
bytecode VM, interpreter, or hybrid. Inspect the local checkout first. Whatever
execution model it uses becomes an engine or guest adapter whose external calls
map to SAME services; unsupported operations must fault or return an explicitly
documented result rather than disappearing silently.
