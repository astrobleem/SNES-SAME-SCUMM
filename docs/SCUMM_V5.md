# SCUMM v5 engine module

## Role in SAME

`scumm_v5` is the first substantial engine personality. It owns SCUMM script
semantics and SCUMM game state; it does not own the SNES PPU, DMA, controller,
SPC700, MSU-1, save medium, or SA-1 mailbox.

The bundled Python module and the bounded 65816 nucleus are executable
conformance cores. Both are deliberately small enough to audit independently.
The local `SNES-SuperMonkeyIsland` checkout is known-broken donor material; its
behavior is not used to decide whether either core is correct.

## Current host-oracle implementation

The implementation is under:

```text
src/same/engines/scumm_v5/
```

It currently supports the following real SCUMM v5 opcode families:

- stop object code and `breakHere` yield;
- relative jump;
- result-variable addressing;
- increment and decrement;
- move, add, subtract, multiply, divide, bitwise AND, and bitwise OR;
- zero/nonzero tests and signed relational branches;
- fixed and variable delays;
- start/stop-script dispatch with `$FF`-terminated local arguments;
- 25 persistent script slots with 32 local variables apiece;
- deterministic first-dead-slot allocation and nonrecursive replacement;
- recursive/freeze-resistant starts, nested freeze counts, and running queries;
- direct/variable chain-script handoff with inherited flags and fresh locals;
- packed bit variables, cursor commands, strings, variable ranges, room/resource
  operations, deterministic random, pseudo-room mapping, actors, classes, verbs,
  expressions, cutscenes, sentence dispatch, and canonical `drawObject`;
- room loading and camera position;
- music and sound request translation;
- persistent script slots;
- engine-state inspection and save/load.

Unknown opcodes stop with the opcode and script offset. They never become silent
no-ops.

## Synthetic fixture

`examples/resources/scumm_v5/core_conformance.scrp` is a copyright-free 61-byte
semantic fixture shared by host tests and the SNES build. The SNES nucleus in
`runtime/snes/engines/scumm_v5.pasm` executes it through five completed ticks,
recording exact WRAM state for direct/variable operands, arithmetic, conditional
flow, relative jump, yield, delay, and stop. `make c1` verifies the complete
trace in Nexen; the observed run uses six video frames and no donor assets.

C2 adds eight generated fixture programs. One four-tick success trace covers
signed multiply/divide, AND/OR, decrement, signed comparisons, zero tests, and
variable delay. Seven isolated programs prove exact unknown-opcode, variable
range, truncated operand, operation budget, division-by-zero, jump escape, and
16-bit SNES delay-range errors. The complete SNES matrix normally uses 12 video
frames and can be run with `make c2`.

C3 adds indexed result references with literal and variable indices, variable
forms across every implemented arithmetic and comparison family, exact 16-bit
wraparound, and deterministic two-slot scheduling. Its five-frame scheduler
trace proves that a delayed slot does not starve its runnable peer. A separate
fixture rejects unsupported bit-variable results explicitly. The complete C3
matrix uses 10 video frames and can be run with `make c3`; it contains no game
data or donor-derived behavior.

C4 adds the v5 `startScript` opcode family, `stopScript`, `$FF`-terminated
word arguments copied into a new slot's 32-word local namespace, nested child
execution, self/peer stop, deterministic first-dead-slot reuse, and an exact
25-slot limit. Its lifecycle trace and isolated capacity terminal use five video
frames total and can be run with `make c4`. The latest 2026-08-22 regression is
`build/scumm-c4-nexen-de56a0b3c163e470/report.json`; no game ROM, donor state,
screenshots, or audio participate.

C5 gives recursive and freeze-resistant start flags observable scheduler
semantics and implements `$60/$E0` freeze/unfreeze plus `$68/$E8`
`isScriptRunning`. Its five-tick trace proves recursive coexistence,
nonrecursive replacement, nested freeze counts, resistant execution, live
queries for frozen slots, deterministic thaw, and stable slot order. `make c5`
checks the exact trace in six video frames; evidence is
`build/scumm-c5-nexen-de56a0b3c163e470/report.json`.

C6 implements `$42/$C2` `chainScript` with direct and variable targets. Its
three-case trace proves retirement before replacement execution, deterministic
same-slot reuse, inherited recursive/freeze-resistant flags, fresh local
arguments, and non-resumption of the caller. Missing-resource and full-table
paths fail after retirement without reusing reserved slot zero. `make c6` checks
the complete matrix in six video frames; evidence is
`build/scumm-c6-nexen-b637228d640c0f8c/report.json`.

C7 implements packed v5 bit variables and `$2C cursorCommand` without adding
game identity to the opcode core. Direct and variable parameters cover cursor
and user-input counters, image/character selection, hotspots, cursor and charset
IDs, and a terminated charset-color list. The same state is included in host
save/load. `make c7` checks an exact host/SNES fixture in one execution frame;
evidence is `build/scumm-c7-nexen-b637228d640c0f8c/report.json` (SHA-256
`ed793f1e588c67e7ff02ccb946e575be01b65f458a1b99424b9d2366100c643a`).

S1 now provides `examples/profiles/templates/monkey1_ultimate_talkie.json` and
the game-neutral parser in `src/same/engines/scumm_v5/policy.py`. The template
names `monkey.000`, `monkey.001`, `monster.sou`, the derived sound/voice maps,
and an optional script-patch manifest through stable resource keys. It also
records logical geometry, host-owned presentation, default engine cursor,
speech track base 1000, silent-stub behavior, and the copy-protection choice as
profile policy. Missing user resources fail before execution. `make s1` checks
this boundary without reading game data or running a Monkey ROM.

S2 adds `LucasartsScummV5ResourceProvider`, which decrypts the v5 index/data
containers, validates chunk and directory bounds, and exposes ROOM/SCRP/SOUN,
COST, and CHAR payloads through profile-defined stable keys. Sparse demo indexes
can retain full-game directory entries; those absent resources are not advertised
by `keys()` or `contains()`. It also adds a SCUMM logical input
adapter for pointer motion/buttons, joypad cursor/commands, text, and quit events.
The generated `scumm_v5_s2_conformance.json` profile and tiny encrypted raw pair
are copyright-free. `make s2` verifies exact resource bytes, fail-closed
truncation, and a three-frame input trace without reading game data or running a
Monkey ROM. S2 does not interpret or render raw ROOM payloads; that is S3.

S3 adds canonical 320x200 indexed scene composition and host-owned viewport
projection. Copyright-free fixtures cover background, priority-sorted actors,
z-mask occlusion, cursor placement, and text rendered from a strict SCUMM v5
CHAR-style offset table with per-glyph metrics. The baseline path and negotiated
tile/OAM/z-mask/SA-1 plan produce the same logical and physical hashes. `make s3`
emits exact reports plus logical and projected PNGs without game data.

S4 adds a strict backend-neutral score-intent resource, exact music/SFX/speech
mapping, and logical audio playheads. Capability negotiation can select a live
score interpreter, a curated TAD rendition, or MSU streaming without making
the rendition part of SCUMM semantics. Save schema 2 restores complete current
engine state and reconstructs audio through public services after a room
transition. Wrong game, schema, and CRC fail before engine load. Evidence is in
`build/scumm-s4-audio-save/report.json`.

S5 adds generated active-engine selection and binds `ScummV5_Engine_*` to the
stable SNES host lifecycle. The kernel no longer boots or ticks a private SCUMM
lane beside the demo engine. A two-tick copyright-free semantic/service fixture
matches the Python host exactly, including four normalized audio packets and
zero queue loss. Evidence is in
`build/scumm-s5-binding-44bb9e4eca6d7287/report.json`.

C8 adds the five canonical v5 `$27 stringOps` forms to both semantic engines.
Encoded strings retain `$FF` controls and zero-valued arguments as raw bytes,
while `decode_scumm_v5_text` exposes separate glyph and control tokens for the
resource-backed font/rendering layer. String IDs are never clamped: all 256
have independent 255-byte capacity in the SNES runtime's 64 KiB WRAM table.
Copying an absent source removes the destination; missing get/set operations
fail closed; out-of-range get returns zero and set is ignored. Host saves carry
the complete string table. `make c8` verifies exact bytes and variables across
a bounded scheduler yield without game or donor data.

C9 adds canonical v5 `$26/$A6 setVarRange` to both semantic engines. A result
reference is resolved once and advanced for each byte or signed-word value, so
indexed globals, locals, and packed bits share the existing variable machinery.
The independent fixture also fixes zero-count behavior at 256 assignments,
packed-bit wrap, truncation, and global/local boundary failures. `make c9`
proves exact host/SNES state without game or donor data.

C10 adds the complete full-header v5 `$33/$73/$B3/$F3 roomOps` family to both
semantic engines. The engine owns deterministic intent for scroll and screen
bounds, shake, scale slots, palette overrides, intensity/shadow/transform,
fade, temporary slot-99 save requests, cycle timing, and named auxiliary
strings. Host palette intent crosses the public video boundary and all roomOps
state round-trips through save schema 2. The v3-only room-color form and invalid
inputs fail closed. `make c10` proves all valid sub-ops, variable operands,
palette bytes, auxiliary-string restore, and cycle timing without game or donor
data.

C11 adds canonical v5 `$16/$96 getRandomNr` to both semantic engines. A
deterministic nonzero 16-bit generator advances once per opcode and maps its
high-byte sample into the inclusive range `0..maximum`; direct and variable
maximum forms are identical after operand decoding. The generator state is
validated and carried through save/load for exact replay. `make c11` proves the
0 and 255 boundaries, intermediate maxima, exact state, and save continuation
without game or donor data.

C12 adds generic v5 `$CC pseudoRoom` to both semantic engines. Its first byte is
the physical room and each following high-bit entry, up to the zero terminator,
selects one of 128 mapper slots; low entries are consumed but ignored. High-bit
room loads resolve through the engine-owned table, which is validated and saved
for exact replay. `make c12` proves mapping, overwrite, ignored entries, room
resolution, malformed-list failure, and persistence without game or donor data.

C13 adds generic v5 `$0C/$8C resourceRoutines` to both semantic engines. Five
packed resource-class tables retain cache intent and four retain lock intent;
room operations use the C12 mapper, clear-heap is a no-op, and object loads
retain mapped room plus 16-bit object identity. Nuke changes cache intent but
never deletes provider-owned source bytes. `make c13` proves all 20 operations,
direct and variable operands, malformed/resource failures, and save/load replay.

C21 adds canonical `$05/$85 drawObject` to both semantic engines and teaches the
raw-room adapter to decode `OBCD/CDHD` local-object identity, geometry, flags,
parent, walk target, and actor direction. Full-header selectors cover position,
state, and neither; relocation updates the walk target, identical rectangles
clear before the target state is installed, and missing local objects are
canonical no-ops. The bounded draw queue and mutable object state survive host
save/load. `make c21` proves the exact host/SNES fixture without game or donor
data.

C22 completes `$72/$F2 loadRoom` transition intent and canonical room zero.
Room operands retain direct, variable, and pseudo-room resolution. A successful
transition clears local objects and pending draws; room zero is committed
without a ROOM lookup, preserves global object state, detaches the room adapter,
and blanks portable presentation. Explicit synthetic initial-scene/`room.0`
fixtures remain supported at the adapter boundary. `make c22` proves the exact
four-tick host/SNES trace, while host tests cover missing nonzero resources and
save/load replay.

C23 adds canonical `$14/$94 print` and `$D8 printEgo`. Four persistent default
slots are selected by actor 252/253/254 or the ordinary slot 0; each operation
works on a transient copy, `$FF` saves that copy, and a low-nibble-15 selector
emits bounded encoded text without changing defaults. AT, COLOR, CLIPPED,
CENTER, LEFT, and OVERHEAD use variable/direct selector flags; v5 erase and the
v4-only voice form fail closed. Print state and messages are inspectable and
saveable. The presentation path uses resource-backed glyphs, and
`ScummV5Charset` now strictly decodes both the cooked conformance format and raw
LucasArts v5 CHAR wrappers with font-relative offsets. `make c23` proves the
SNES state machine; host tests prove glyph projection and save/load replay.

C24 corrects `$58 beginOverride/endOverride` when no cutscene is active. The
canonical five-record structure reserves record zero as a sentinel, so depth
zero is valid: beginOverride stores the current PC/slot there and skips the
following jump; endOverride clears it; skip-abort resumes it. Save schema 2 now
persists this record and accepts older payloads that omit it. `make c24` proves
the exact record-zero lifecycle in the SNES state machine, while host tests add
save/load, malformed-state, and skip-abort coverage.

S6 now has a bounded preflight against the redistributable Fate of Atlantis
interactive demo. `examples/profiles/templates/fate_of_atlantis_demo.json`
models embedded audio, costumes, all three readable charsets, the original
320x200 coordinate space, and the demo-disabled save menu without adding a game
branch to the opcode core. `make s6-preflight` verifies the exact archive,
included redistribution notice, 10 rooms, 74 scripts, 27 readable sounds, 20
costumes, three charsets, logical pointer input, and a SAME save-state round trip.

This remains an in-progress S6 gate. The real boot script now crosses the C8 string workload,
both C9 variable ranges, and its first C10 `loadString(31, "iq-points")` while
preserving the preallocated destination when the auxiliary file is absent. C11
then produces 226 for the real maximum-255 random call, leaves generator state
`$E270`, and uses that result as the child-script delay. C12 then consumes all
31 pseudo-room records and constructs an exact table with 100 populated entries.
C13-C20 then cross resource, actor, class, verb, expression, cutscene, and
sentence initialization before the raw room-68 transition. C21 consumes the
real `$05` in script 74 at offset `$0033`, drawing local object 939 at its
decoded 24,32 position and 272x144 size with default state 1. After pointer
release, C22 enters canonical resource-less room zero, clears local object/draw
state, preserves object 939's global state, and blanks presentation. C23 then
saves `(160,8)`, centered and overhead, as slot-0 defaults through setup-only
`$14`; the preflight also validates the real raw CHAR digit-three glyph. Boot
crosses `$58 00` in callback script 21 at offset `$0004`, retires script 74 and
the main boot script, and enters decoded raw room 75 on frame 524. Actor
placement now crosses C31/C32, C33 decodes costume 58's initial classic
BYLE-RLE pose into a 7x7 logical actor image with an exact published hitbox,
and C34 persistently advances its limb cursors with canonical speed timing.
C35 applies the classic phase-table actor scales around the foot anchor.
C36 decodes classic raw-room `ZPxx` strip masks and applies explicit actor
`forceClip` occlusion; Fate room 42 plane 1 hides all 37 pixels of costume 58
in the pinned proof. C37 decodes `BOXD` geometry and automatically selects that
plane from walkbox 10 at the actor's foot position. C38 decodes `BOXM` and
implements `$7B/$FB getActorWalkBox`. C39 implements all eight `$1E
walkActorTo` forms, reverse-order destination snapping, shared-edge gates,
scaled fixed-point stepping, movement facing and chores, `$56/$D6
getActorMoving`, and `$3B/$BB waitForActor`. Save schema 5 restores complete
in-flight routes. Fate room 42 traverses boxes `5→6→8→7→10` from `(44,80)` to
`(200,110)` in the pinned proof. C40 strictly decodes the embedded `SOU` hardware
renditions and their initial MIDI tracks, streams deterministic signed-16 PCM,
implements `$7C/$FC isSoundRunning`, and restores embedded playheads under save
schema 6. All 27 readable sounds decode; sound 172 supplies an audible exact
WAV proof. C41 then decodes all of Fate's observed iMUSE branch commands across
every MIDI track, proves a real hook jump and exact restore, and delivers a
reviewed sound-172 arrangement through TAD on the S-SMP. C43 then adds a bounded
ROL-to-zoned-MML converter and the complete 23-note sound-17 pad/flute cue. C44
adds explicit cue-specific register policies and the complete 28-note,
eight-voice sound-154 arrangement. C45 adds audited, deterministic reduction for
over-capacity cues and the 29-retained-note sound-83 arrangement. C46 adds
interval-based merging/ducking and retains all 25 notes of eleven-voice sound
18. C47 adds the complete seven-note sound-185 marimba chord. C48 adds the
complete split-register impact cues 190 and 192. The generic engine and
production backend are therefore proven. C49 corrects the reviewed marimba
ceiling and adds complete sounds 141/201/202/207. C50 adds chord-aware
virtualization and all 110 attacks of sound 183. C51 adds complete rapid
wide-register effects 91/117 without dropping an attack. C52 adds all 91 notes
of the 84-second sound 78 and full-length DSP validation. C53 adds complete
sound 81 with capacity-only identical-pitch sharing. C54 adds complete sound
153 with attack-preserving orchestral virtualization. C55 remains under focused
listener review after sound 150's rejection exposed discarded in-note CC7
automation. The converter now preserves TAD fine-volume envelopes without
retrigger, and a raw-event audit regenerated all five affected production cues:
18, 83, 150, 154, and 192. The other fourteen contain no active-note CC7
movement. S6 remains open until listener acceptance and the other 9 readable
sounds have production SNES arrangements. Frontier evidence is in
`build/scumm-s6-fate-preflight/report.json` and the hash-keyed
`build/scumm-s6-tad-*/report.json`.

M19 closes the first real-music runtime integration seam. A 32-byte
copyright-free script executed by the SNES SCUMM dispatcher starts Monkey
church sound 154 with `$02`, observes `$7C` running status, stops it with `$20`,
observes stopped status, and restarts it. All three requests cross the ordinary
SAME event/audio-service path; the logical-request debugger byte remains zero.
SCUMM owns only the logical active sound used by its synchronous status opcode,
while the catalog maps 154 to existing TAD song 26 below the engine boundary.
One fresh emulator lifecycle proves stop-to-blank, restart, and the accepted
57.303875-second DSP loop.

`examples/resources/scumm_v5/boot.scrp` uses real opcode numbers. It starts music,
loads room zero, increments variable 20, yields, and loops. The conformance profile
therefore proves all of these independently:

```text
script dispatch
resource lookup
indexed room presentation
normalized audio command
bounded yielding
frame timing
service packets
save/load
```

The cooked room fixture uses this intentionally simple host-only format:

```text
magic       "SC5R"
version     u8
width       u16 little-endian
height      u16 little-endian
colors      u16 little-endian
palette     colors * RGB888
pixels      width * height indexed bytes
```

That format is not proposed as the final SCUMM asset format. It exists so engine
semantics and host services can be tested without LucasArts data or a room
converter.

## Profile boundary

A game profile selects:

```json
{
  "engine": "scumm_v5",
  "resources": [
    {"key": "script.boot", "path": "...", "kind": "SCRP"},
    {"key": "room.0", "path": "...", "kind": "ROOM"}
  ],
  "options": {
    "boot_script": "script.boot",
    "initial_room": 0,
    "room_key_template": "room.{room}"
  },
  "quirks": {}
}
```

Monkey Island-specific sound maps, copy-protection policy, speech tables, intro
pacing, coordinate transforms, and script workarounds belong in its profile or a
narrow game adapter. They do not belong in the SCUMM v5 opcode core.

The S1 template is intentionally stored below `examples/profiles/templates/`,
outside the bundled-profile validation glob. Copy it to a user profile and
supply the required files before validation. Its expected layout is:

```text
user-data/monkey1/monkey.000
user-data/monkey1/monkey.001
user-data/monkey1/monster.sou
user-data/monkey1/scumm_sound_map.bin
user-data/monkey1/voice_table.bin
user-data/monkey1/scumm_patches.json   optional
```

The Fate demo template is stored beside it. Extract the freely redistributable
demo without altering its notices into:

```text
user-data/fate-demo/PLAYFATE.000
user-data/fate-demo/PLAYFATE.001
user-data/fate-demo/READ.ME
```

The demo's `READ.ME` says its disk may be freely copied and distributed if
copyright and trademark notices are not altered or removed. The original game
menu intentionally cannot save or restore; SAME save states remain a separate
engine-host facility and pass a boot-state round trip in the preflight.

## Consulting the local Monkey Island donor

A selected hash-recorded checkout can reveal implementation ideas and known
SNES mechanisms. It is not authoritative for semantics or behavior, including
its cursor, UI, room, timing, and post-dock behavior. Use upstream ScummVM and
copyright-free differential fixtures for semantic comparison.

Proceed in this order:

1. Identify a narrow subsystem whose mechanism is needed; do not begin with a
   gameplay run.
2. Import a reference snapshot with `same donors import monkey`. This copies
   selected files only and records SHA-256 for every file.
3. Define a `MonkeyProfile` equivalent containing game identity, resource keys,
   sound/speech mappings, and known quirks.
4. Add service adapter routines around the existing engine without changing its
   semantics: input first, then resource lookup, video presentation, audio, and
   save storage.
5. Move one direct hardware dependency at a time behind SAME while keeping the
   independent fixtures exact.
6. Bind the namespaced `ScummV5_Engine_*` Poppy routines to
   `Same_ActiveEngine_*` only after the generic engine-host ROM gate passes.
7. Add a second SCUMM v5 game profile without modifying the opcode core. Any new
   game-specific exception goes into that profile or an explicitly named quirk.

## ScummC compiler reference

`AlbanBedel/scummc` is useful as a reference for a source-language compiler,
linker, resource builders, and authoring workflow. Upstream ScummC targets SCUMM
v6 and partially v7, however, so its emitted opcode encoding is not used as a v5
oracle. A future SAME fixture compiler can borrow the architectural idea while
using independently defined v5 tables and checking output against upstream
ScummVM semantics. ScummC is GPL-2.0; copied or derived code must remain clearly
licensed and separable.

## What remains for a full SCUMM v5 SAME engine

- the complete opcode surface, enumerated from upstream semantics and exercised
  by independent fixtures (the local 65816 donor may suggest implementation);
- route-gate traversal, actor movement, objects, verbs,
  dialog, walkboxes, pathfinding,
  camera, room scripts, cutscenes, palettes, and resource routines;
- a stable cooked-resource directory usable from ROM and MSU-1;
- TAD/SPC music and SFX plus optional MSU-1 speech;
- listener approval of the isolated Fate instrument/octave zones and complete
  reviewed arrangements beyond sound 172;
- complete save serialization;
- a second game profile;
- host/SNES differential fixtures for opcode and gameplay state.

The acceptance criterion is not merely “Monkey Island still runs.” It is “the
same SCUMM v5 module runs Monkey Island and another compatible profile through the
same host services without engine-core edits.”

## Bounded Fate compiled hooks

M21 proves immediate hook-14 route selection before audible ownership with a
bounded synthetic command fixture. M22 proves a delayed hook 8 while that route
is already playing, also using a bounded synthetic command fixture. Neither is
an authentic room-entry trace. The
SCUMM layer retains logical cue generation, route history, one pending hook,
section identity, and one-shot consumption only. A profile-generated section
table maps those semantics to a compiled TAD boundary token and continuation;
the generic `$4C` dispatcher does not name Fate, rooms, cue 80, hook 8, or TAD
song numbers.

M23A supplies the missing authentic-resource substrate without claiming that
unsupported gameplay semantics executed. Complete Fate rooms 49 and 63 are
cooked locally into profile-owned records; host and SNES resource providers
validate and expose typed ENCD, EXCD, and LSCR descriptors with distinct source,
cooked, normalized, and runtime offsets. Authentic validation stops with ENCD
scheduled at PC zero and emits no music. A copyright-free fixture separately
proves the generic old-EXCD, retirement, acquisition, activation, registration,
new-ENCD, and room-local script lifecycle.

M23B uses that substrate to execute the complete authentic room-49 ENCD from
PC zero. A named, source-bound ordinary SCUMM state initializes bit 425 and the
two IQ strings; no PC or branch result is supplied. Authentic global scripts
144 and 145 run nested, including canonical `$A0` termination, before indexed
bit 418 and sound 81/80 conditions reach the source `$4C` operations at
`+0x004F`, `+0x0057`, and `+0x0065`. Start 80 and hook 14 are queued together
and consumed by one flush. The accepted hook-14 compiled route then plays
through SAME/TAD/SPC. A sound-81-running negative control takes the real skip
branch and emits no sound-80 packet.

M23C continues from that authentic room-49 ownership through the normal EXCD,
retirement, resource-acquisition, registration, and ENCD lifecycle into room
63. The complete authentic room-63 ENCD starts at PC zero. Canonical `$1D`
class-list tests, global script 151's real delay/yield, sound-80/82 status, and
the intervening conditional execute before the source queues `0x0110` and
performs its later flush. The exact flushed list is hook 8 followed by iMUSE
command 16 (`clear_queue`). Hook 8 then uses the already accepted M22 compiled
boundary selector; no new live sequencer or transition graph was added.

Canonical `$1D/$9D ifClassOfIs` uses the normal sparse 32-class object mask.
Each direct/variable class selector is terminated by `0xFF`; bit 7 requires
presence and an unflagged selector requires absence. All selectors must match,
otherwise the normal signed relative branch is taken. Malformed class IDs or
lists fail closed on host and SNES.

M22 is not a general transition graph or live note sequencer. Its source audit
binds one decision at track 3 tick 68160 to default continuation or the hook-8
destination at track 3 tick 1920. Cold SCUMM load restarts the complete cue from
its beginning with that saved eventual choice. It does not restore the musical
tick or any live SPC/DSP state.

## Authentic headless interpreter frontier

Complete room-owned OBCD programs now share the canonical VERB lookup used by
`getVerbEntrypoint`.  `$37/$77/$B7/$F7 startObject` decodes signed word
varargs, allocates a generation-bound object slot, and executes it immediately
through the existing nested interpreter.  Authentic object 596 verb 10 runs
from OBCD `+$0029`; `chainScript(211)` retires and retypes that slot before
LSCR 211 begins at PC zero. The historical frontier was LSCR 211 `+$026E`,
`$B2 setCameraAt(Var[2])`; Phase 6L subsequently cleared it. See
`M25_START_OBJECT_REPORT.md`.

The room-49 path now includes canonical matrix box-flag mutation, actor
placement, global object state, actor-facing conversion, timed headless actor
talk, and the pure stored-walkbox query `$7B/$FB`. At LSCR 216 `+$0000`, actor
1's authentic `putActor(399,116)` state supplies walkbox 11; the query writes
11 to Var[442] without consulting geometry or mutating actor state. The local
script then reaches its legitimate `breakHere` loop.

That earlier room-63 LSCR-directory and scheduler boundary is retained in its
milestone reports as historical evidence; it is no longer the active frontier.
