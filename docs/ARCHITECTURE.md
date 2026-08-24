# SAME architecture

## 1. The central split

SAME supports two equal kinds of clients:

```text
Engine personality                         Machine personality
------------------                         -------------------
SCUMM v5                                   MC68000 + Taito X
Sierra AGI                                 Z80 + Black Tiger hardware
native 65816 game engine                   68000 + Z80 + Genesis devices
other bytecode/content engines             other foreign machines
```

Both use the same services, event packets, resource packages, save identity,
timing, debug evidence, and processor-placement rules. Neither personality is
the definition of SAME.

## 2. Ownership layers

### Kernel

Owns:

- lifecycle enforcement;
- frame/NMI ownership;
- service routing;
- event queue integrity;
- processor and memory ownership;
- panic/budget/overflow evidence.

The kernel does not know what a room, actor, walkbox, sprite character, player,
level, or Genesis VDP is.

### Services/backends

Own platform mechanisms:

- video surface and optional SNES tile/OAM/z-mask acceleration;
- music/SFX/speech delivery;
- physical input and logical events;
- resource reads and package/MSU access;
- save slots;
- timers;
- synchronous host jobs and eventual SA-1 jobs;
- debug/oracle output.

A backend can be replaced without changing engine semantics.

### Engine module

Owns one game-engine family’s semantics:

- bytecode/logic execution;
- engine state;
- engine objects and scheduling;
- resource interpretation;
- game-family save payload.

An engine receives an `EngineContext`; it does not receive raw SNES register
addresses.

### Game profile

Owns policy and data selection:

- engine identifier;
- game/version identity;
- timing and operation budget;
- logical and physical video dimensions;
- input profile;
- resource key bindings;
- required and optional capabilities;
- options and explicitly named quirks.

A second game should normally be a new profile plus converted resources.

### Machine adapter

Owns guest buses, CPU stepping, interrupts, and hardware portals for a foreign
machine. It consumes the same services as an engine module.

## 3. Engine lifecycle

```text
CREATED
   │ probe + capability negotiation
   v
PROBED
   │ boot
   v
RUNNING <---------- resume ---------- SUSPENDED
   │                                   ^
   ├----------- suspend ---------------┘
   │
   ├── halt/shutdown ──> STOPPED
   └── exception/budget fault ──> FAILED ──> STOPPED
```

The Python host enforces this state machine. The Poppy source mirrors it in
`runtime/snes/engine/host.pasm`.

A frame is host-owned:

```text
clock advance
physical input sample
logical event generation
Engine_HandleEvent(event...)
Engine_Tick(operation budget)
optional present
service packet drain/commit
```

The engine may yield, but cannot call an unbounded private frame loop.

## 4. Capability negotiation

Baseline capabilities describe portable services, such as an indexed surface,
pointer input, save slots, random-access resources, timers, and normalized audio.
Normalized audio includes an explicit flush operation: engines may preserve
their native command-list batching, while the backend receives semantic packets
and a deterministic boundary without inheriting an engine-specific queue.

SNES-specific acceleration is optional:

```text
tiled_video
sprite_oam
z_mask
hdma
sa1_jobs
msu1_stream
chip_audio
foreign_cpu
```

An engine declares required and optional capabilities. The profile may add
requirements. Boot fails before engine state changes when a required capability
is absent.

This prevents SCUMM’s SA-1 costume scaler or a future AGI picture accelerator
from becoming hidden universal requirements.

## 5. Resources

Engines use stable keys:

```text
script.boot
room.33
logic.0
picture.17
view.4
speech.102
```

The key may resolve to:

- a plain converted file;
- an in-memory test fixture;
- a section in `SAMEPKG`;
- a composite provider;
- eventually, a raw original-game resource provider.

The engine never branches on whether the bytes came from ROM, MSU-1, a host test,
or a package.

## 6. Video model

The portable baseline is an indexed 8-bit surface plus palette, dirty rectangles,
and cursor. This resembles the useful low-level portion of a ScummVM platform
backend without importing desktop GUI assumptions.

SNES backends may accelerate the same semantics through:

- BG tilemaps and tile caches;
- OAM sprites;
- priority/z masks;
- HDMA palette or tile-base changes;
- SA-1 bitmap scaling and character conversion.

The engine’s result remains an indexed scene. The backend chooses the physical
representation.

## 7. Save model

The host wraps an engine payload in:

```text
magic/version
engine id
game id
engine save-schema
payload size
payload CRC32
payload
```

The host rejects another engine, another game, another schema, truncation, or
corruption before invoking `Engine_Load`.

## 8. Python/SNES relationship

The Python implementation is not a substitute SNES emulator. It is:

- the executable engine ABI reference;
- a semantic oracle for bytecode/logic tests;
- a deterministic packet/resource/save validator;
- a place to prove profiles before 65816 integration.

The Poppy implementation owns the actual SNES runtime. Host and SNES must converge
on the same service packets, lifecycle, resource identity, and save semantics.

## 9. Repository layout

```text
src/same/
    engine.py              lifecycle, registry, host
    profile.py             game profiles
    services.py            host service implementations
    resources.py           resource-provider layer
    savegame.py            save envelope/stores
    video.py               indexed surface
    engines/scumm_v5/      SCUMM v5 host oracle
    engines/agi/           Sierra AGI host oracle
    target.py/runtime.py   legacy machine-personality host model

runtime/snes/
    engine/host.pasm       SNES lifecycle
    engines/               active demo + SCUMM/AGI adapter seams
    kernel/                event/frame/memory ownership
    services/              platform backends
    targets/               0.1 compatibility shims

examples/profiles/         game-engine profiles
examples/resources/        copyright-free conformance resources
labs/vdp/                  machine-video translation lab
```
