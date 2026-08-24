# Porting another engine to SAME

This guide applies to an adventure interpreter, a native game engine, a bytecode
VM, or a machine personality that can cooperate with the SAME lifecycle.

## 1. Name the semantic owner

Choose a stable engine identifier such as `agi_v2`, `scumm_v5`, or
`my_engine`. The engine owns game semantics and serializable state. SAME owns
platform services.

Do not begin by copying rendering, audio, filesystem, and input code together.
List each external dependency and map it to a host service first.

## 2. Publish a descriptor

The descriptor declares:

```text
identifier
human name
module version
supported families
required capabilities
optional capabilities
save schema
```

Required capabilities reject an unsuitable host at probe time. Optional
capabilities select an acceleration path without changing semantics.

## 3. Create a profile

A profile carries the game-specific choices:

```text
game id/title/variant
tick rate and operation budget
physical and logical video geometry
input mapping
resource bindings
required/optional capabilities
options
quirks
```

A quirk must be named narrowly enough to identify the game/version behavior it
changes. Avoid booleans such as `compat_mode` whose meaning will drift.

## 4. Implement the lifecycle

Minimum Python implementation:

```python
class MyEngine(Engine):
    descriptor = EngineDescriptor(...)

    def boot(self, context): ...
    def tick(self, context): ...
    def save_state(self, context): ...
    def load_state(self, context, payload): ...
```

`tick()` must stop at the profile operation budget and return a `FrameResult`.
A blocking guest loop that owns host timing is not acceptable.

## 5. Build an independent synthetic fixture

Before loading commercial game data, build a tiny copyright-free fixture that
proves:

- dispatch;
- state mutation;
- bounded yield;
- one video operation;
- one input path;
- one audio or storage request if relevant;
- save/load;
- an explicit unknown-operation failure.

The fixture's expected result must be computed independently of the engine under
test.

## 6. Use stable resource keys

The engine requests names such as `logic.0`, `room.33`, or `script.boot`.
Profiles decide whether those keys map to files, ROM sections, MSU-1 package
sections, memory fixtures, or another provider.

Never bake a host path, MSU offset, ROM bank, or package section offset into the
semantic core.

## 7. Add the SNES adapter seam

Create namespaced Poppy labels:

```text
MyEngine_Engine_Boot
MyEngine_Engine_Frame
MyEngine_Engine_Suspend
MyEngine_Engine_Resume
MyEngine_Engine_Shutdown
```

A build-selection layer binds exactly one module to `Same_ActiveEngine_*`.
Hardware writes remain inside services. Run `tools/lint_poppy.py` before Poppy and
preserve exact ROM identity for emulator tests.

## 8. Prove reuse

An engine is not extracted when the original game still works. It is extracted
when all of these are true:

1. the donor's original tests remain green;
2. the synthetic SAME fixture passes on host and SNES;
3. save/load round-trips;
4. missing resources/opcodes fail loudly;
5. no engine code touches platform hardware directly;
6. a second profile/resource set runs without engine-core edits.

Only then should performance-specific SA-1, tile, OAM, HDMA, or streaming paths
be enabled as negotiated accelerators.
