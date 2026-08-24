# Sierra AGI v2 engine module

## Purpose

`agi_v2` is the proof that SAME is not a Monkey Island framework. It is an
independent Sierra AGI engine personality intended to lead to King’s Quest,
Space Quest, and other AGI titles through the same video, input, resource, audio,
save, timing, and job services.

## Current host-oracle implementation

The module is under:

```text
src/same/engines/agi/
```

It accepts the decoded AGI logic-resource layout:

```text
u16 bytecode_size
u8  bytecode[bytecode_size]
u8  message_count                 optional
u16 message_section_size          optional
u16 message_offsets[count]        optional
u8  zero-terminated strings       optional
```

The current command subset implements:

- `return`;
- increment/decrement;
- assign/add/subtract, direct and variable forms;
- left- and right-indirect variable access;
- set/reset/toggle, direct and variable flag forms;
- `new.room` and `new.room.v`;
- `sound` and `stop.sound` service seams;
- program/player control;
- simple ego directional movement;
- save/load and state inspection.

Unknown commands report the opcode and bytecode offset.

## Cooked picture fixture

The conformance picture is deliberately simple and copyright-free:

```text
magic       "AGIP"
version     u8
width       u16 little-endian
height      u16 little-endian
colors      u8
palette     colors * RGB888
pixels      width * height indexed bytes
```

It proves that AGI can use the common indexed-surface service. It is not a
substitute for the original vector-picture decoder or AGI priority screen.

## Why King’s Quest I is the recommended first real profile

A first real AGI target should exercise the original engine rather than a custom
fixture while keeping the initial content scope understandable. The profile must
point to user-supplied game data and preserve game/version detection outside the
engine core.

The real milestone is not a title screen. It is a bounded play path with:

```text
logic 0 cycle
room transition
picture + priority decode
view animation
ego movement/collision
parser command
text window
sound completion flag
save/load
```

## Ordered implementation gates

### AGI-1 — condition expressions and GOTO

Implement the v2 condition stream, NOT, OR groups, relative branches, and the
logic-zero rerun model. Add independent bytecode fixtures for true/false paths,
nested expressions, and malformed streams.

### AGI-2 — raw resource discovery

Read the appropriate DIR/VOL layout for a selected DOS AGI version. Keep loader
and decompression behind `ResourceProvider`; logic execution must not know the
physical package.

### AGI-3 — vector picture and priority screen

Decode the original picture commands into visual and priority buffers. Compare
host output against an independent AGI implementation before writing the SNES
backend. On SNES, decide whether each buffer is represented as tiles, a staged
indexed surface, or an SA-1-assisted conversion.

### AGI-4 — views and motion

Implement view/loop/cel decode, object table, animation cycles, priorities,
horizon, block/object collision, and ego movement. Keep object semantics in AGI,
not in SAME's kernel.

### AGI-5 — text, vocabulary, and parser

Implement vocabulary loading, tokenization, `said`, prompt editing, text windows,
inventory, controller bindings, and menu seams. SAME supplies text/key events; AGI
owns parser semantics.

### AGI-6 — sound and saves

Translate AGI sound resources to an agreed SPC/TAD path, retaining completion
flags and timing. Serialize the complete variable/flag/object/logic/input state
through the host save envelope.

### AGI-7 — King’s Quest progression gate

Boot from user-supplied data and prove a reproducible sequence spanning multiple
rooms, interaction, death/restart or restore, and sound. Add a regression fixture
for every engine gap found.

## Non-negotiable boundary

AGI does not inherit SCUMM concepts such as actors, verbs, walkboxes, iMUSE, or
SCUMM resource chunks. Both engines share only host services. That is the design
proof SAME needs.
