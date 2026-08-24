# SAME engine ABI

## Purpose

The engine ABI lets a game-engine family run without owning a platform. It is
small enough to implement in 65816 assembly, but explicit enough to host SCUMM,
AGI, native engines, and other bytecode systems.

## Descriptor

Every engine publishes:

```text
identifier
human-readable name
module version
supported game families
required capabilities
optional capabilities
save schema
```

Engine identifiers are stable profile-facing names such as `scumm_v5` and
`agi_v2`. They are not game identifiers.

## Lifecycle functions

### `Probe(profile, services) -> ProbeResult`

Checks whether the profile is structurally suitable before engine state is
created. Probe cannot mutate game state.

### `Boot(context)`

Loads initial resources and initializes deterministic state. Required capability
checking has already succeeded.

### `HandleEvent(context, event)`

Receives digital, pointer, pointer-button, text, and quit events. Engines should
not poll hardware words directly.

### `Tick(context) -> FrameResult`

Runs at most `profile.max_ops_per_tick` semantic operations. Result fields:

```text
operations
whether execution yielded
whether the engine halted
whether a frame should be presented
diagnostic key/value evidence
```

Exceeding the profile budget is an engine failure, not a slow frame that is
silently accepted.

### `SaveState(context) -> bytes`

Returns only the engine-owned payload. The host adds engine/game/schema identity
and CRC.

### `LoadState(context, payload)`

Restores a previously emitted payload. It is never called with a mismatched or
corrupt outer envelope.

### `Suspend`, `Resume`, `Shutdown`

Allow host-owned menus, storage operations, or platform state changes without
inventing engine-specific lifecycle rules.

### `InspectState() -> map`

Debug/oracle view. It is not a save format and must not be used as gameplay
truth by the engine itself.

## Context

`EngineContext` contains:

```text
profile
HostServices
negotiated capability mask
```

Services currently exposed:

```text
video       indexed surface, palette, dirty rects, cursor, present
audio       music, SFX, speech, master volume, explicit flush
input       event queue and current logical state
resources   stable-key reads/stat/open
saves       slot store owned by host
clock       frame and monotonic microseconds
jobs        deterministic job submission / future SA-1 seam
debug       markers and counters
events      fixed 16-byte service packet bus
```

## Python implementation

```python
from same.engine import Engine, EngineDescriptor, FrameResult

class MyEngine(Engine):
    descriptor = EngineDescriptor(...)

    def boot(self, context):
        ...

    def tick(self, context):
        return FrameResult(operations=12, yielded=True, presented=True)

    def save_state(self, context):
        return b"..."

    def load_state(self, context, payload):
        ...
```

Register it in an `EngineRegistry`, then select it with a profile.

## Poppy implementation

The host calls stable active-engine labels:

```text
Same_ActiveEngine_Boot
Same_ActiveEngine_Frame
Same_ActiveEngine_Suspend
Same_ActiveEngine_Resume
Same_ActiveEngine_Shutdown
```

Only one engine adapter provides those active labels in a ROM build. Other
modules expose namespaced seams such as `ScummV5_Engine_*` and `AgiV2_Engine_*`.
`tools/generate_snes_engine_selection.py` generates the one include that binds a
namespaced module to the active labels. The demo and SCUMM v5 builds therefore
share the host/kernel/services while selecting exactly one lifecycle owner.

## Extension rules

A new engine is accepted only after it has:

1. a descriptor and profile;
2. a synthetic semantic fixture independent of game data;
3. bounded tick execution;
4. save/load round-trip tests;
5. unknown-opcode/resource failure tests;
6. a host framebuffer or other service proof;
7. an SNES adapter seam;
8. a second resource set or game profile without engine-core edits.
