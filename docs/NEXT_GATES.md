# Ordered SAME gates

Each gate must produce an independently checkable artifact. Do not advance
because code compiles or one game appears to run.

## H0 — assemble and observe the engine host

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for ROM
`d452760a3089a271eb4cdb7be181e39d4ecdf760e089ae0f306cdec95afc0a0b`.
Evidence: `build/h0-nexen-d452760a3089a271/report.json`.

**Work:** Build `build/same-engine-host.sfc` with Chad's Poppy fork and execute
`docs/EMULATOR_GATE.md`.

**Pass:** exact ROM identity; lifecycle reaches RUNNING; frame and operation
counters advance; input edges and four video requests work; Start reaches the
audio service; no packet loss.

---

## K1 — production NMI, input, and DMA ownership

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for ROM
`5f4182758e6e9649e2de6b067d4cf156ac69d58290f70cec2b7917039f72cade`.
Evidence: `build/k1-nexen-5f4182758e6e9649/report.json`. The same ROM passed
the complete H0 gate at `build/h0-nexen-5f4182758e6e9649/report.json`.

**Work:** Compare the current local Monkey and BOR implementations and extract
only the proven neutral mechanisms: frame pacing, automatic joypad completion,
shadow commits, DMA queue, and channel ownership.

**Pass:** H0 remains exact; VRAM/CGRAM/OAM fixtures transfer correctly; no client
claims a channel directly; held input produces one press edge; forced-blank work
does not spill into active display.

BOR's current local architecture must be inspected before use. No VM-centered BOR
assumption is permitted.

---

## C1 — independent SCUMM v5 semantic nucleus

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for ROM
`0c4067cdd9177ae4d97c5eed7f071e4b0bfbc04d0ccd3a52db61fa85ebef53b5`.
Evidence: `build/scumm-core-nexen-0c4067cdd9177ae4/report.json`.

**Work:** Execute a copyright-free, hand-authored 61-byte script in an
independent 65816 SCUMM v5 nucleus. Cover direct and variable operands,
arithmetic, true and false conditional flow, relative jump, yield, delay, and
stop.

**Pass:** Five exact WRAM semantic checkpoints agree with the host fixture; the
gate finishes below 120 frames (observed: 6); no game ROM, PCM, screenshot,
audio, or Monkey-derived behavior participates.

---

## C2 — expand the independent SCUMM opcode matrix

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for ROM
`8ade4f762b5e58e6a1bd9dd3c76c962455f548861175c4b9868e72377f51ecac`.
Eight cases completed in 12 video frames. Evidence:
`build/scumm-c2-nexen-8ade4f762b5e58e6/report.json`.

**Work:** Add table-driven copyright-free fixtures for decrement,
multiply/divide, bitwise operations, signed comparisons, variable delay, and
all fail-closed cases already supported by the host core.

**Pass:** host and SNES traces agree checkpoint-for-checkpoint; malformed
operands, division by zero, unknown opcodes, PC escape, and budget exhaustion
produce exact errors in short bounded runs.

---

## C3 — result addressing and script-slot scheduling

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for ROM
`1afca069a497b31c47c4472e59914772ff9976055cb14fbc004f23313a7fe738`.
Three cases completed in 10 video frames. Evidence:
`build/scumm-c3-nexen-1afca069a497b31c/report.json`. The same ROM retained the
complete C2 matrix in 12 video frames at
`build/scumm-c2-nexen-1afca069a497b31c/report.json`.

**Work:** Extend the independent matrix to indexed result references, variable
operand forms for every arithmetic/comparison family, multiple script slots,
and wraparound boundaries.

**Pass:** host and SNES traces agree without game data; indexed and unsupported
bit-variable outcomes are exact; both fixed slots stay within their state
bounds; one delayed script cannot starve another.

---

## C4 — script-slot lifecycle and local variables

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for ROM
`5055b69c377615409b3ad5dd3dc38f30d8e869d2f83743cfea1bc8b8e640a19d`.
Two cases completed in five video frames. Evidence:
`build/scumm-c4-nexen-5055b69c37761540/report.json`. The same ROM retained C3
in 10 frames and C2 in 12 frames at the corresponding
`build/scumm-c3-nexen-5055b69c37761540/` and
`build/scumm-c2-nexen-5055b69c37761540/` reports.

**Work:** Add synthetic start/stop-script semantics, per-slot local variables,
deterministic slot reuse, and an explicit 25-slot capacity limit to the host and
SNES conformance cores.

**Pass:** exact host/SNES traces cover slot creation, local-variable isolation,
self-stop, peer-stop, reuse order, and fail-closed capacity exhaustion. No game
data or donor behavior participates.

---

## C5 — recursive/freeze-resistant script scheduling

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for ROM
`de56a0b3c163e470e823f19133a925c5064b5f54dcc30efcedc723b12ee7c507`.
One exact case completed in six video frames. Evidence:
`build/scumm-c5-nexen-de56a0b3c163e470/report.json`. The same ROM retained C4
in five frames, C3 in 10, and C2 in 12 at the corresponding hash-qualified
reports.

**Work:** Give the existing `startScript` recursive and freeze-resistant flags
observable scheduler semantics. Add synthetic script-running queries and
freeze/unfreeze transitions without introducing room, actor, input, or game
policy.

**Pass:** exact host/SNES traces prove nonrecursive replacement, recursive
coexistence, frozen-slot starvation resistance, freeze-resistant execution,
stable slot order, and deterministic unfreeze. Malformed references and budget
exhaustion fail closed in bounded runs; no donor or game data participates.

---

## C6 — chainScript slot handoff

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for ROM
`9c59520d659c5e285a44f8b7a96aead95be5b40ab403d4ac77c4fde2cff81ff4`.
Three cases completed in six video frames. Evidence:
`build/scumm-c6-nexen-9c59520d659c5e28/report.json`. The same ROM retained C5
in six frames, C4 in five, C3 in 10, and C2 in 12 frames.

**Work:** Implement the v5 `$42/$C2` `chainScript` family: decode the target and
word arguments, retire the current slot, and start the replacement with the
caller's recursive and freeze-resistant flags.

**Pass:** exact host/SNES traces prove current-slot retirement before target
execution, flag inheritance, local reinitialization, deterministic first-dead
reuse, variable target selection, and fail-closed missing/capacity cases. The
retired script never resumes; no donor or game data participates.

---

## C7 — cursorCommand and bit variables

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for SCUMM ROM SHA-256
`b637228d640c0f8c940c5ff5ab2dfdbd49be3eec5dd5edb5cac0cf786538d665`.
The exact cursor/bit case completed in one execution frame. Evidence:
`build/scumm-c7-nexen-b637228d640c0f8c/report.json` (SHA-256
`ed793f1e588c67e7ff02ccb946e575be01b65f458a1b99424b9d2366100c643a`).
The same ROM retained C1-C6; demo ROM SHA-256
`3cf356111308478e1bcb1d629ee67185b9a12734fdb621b71269efaa55ed007d`
retained H0/K1.

**Work:** Implement packed bit-variable reads/writes and generic v5 `$2C`
`cursorCommand` state, including variable-selected parameters and charset color
lists, in both host and SNES engines. Persist the full host state through saves.

**Pass:** an exact copyright-free fixture agrees on bit 5, global variables,
cursor/user-input counters, image, hotspot, IDs, charset, and colors. Invalid
references and unsupported subcommands fail closed; no game or donor data
participates.

---

## C8 — string resources and encoded text

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for SCUMM ROM SHA-256
`2486bb6cc549e87cf7d2ffb05911d891f7ab0b820f6ac04eab957f8e9d861074`.
The exact case crossed a bounded scheduler yield. Evidence:
`build/scumm-c8-nexen-2486bb6cc549e87c/report.json` (SHA-256
`7518bbc69522d28c2da6b797ef0144490cb8908bcff87dc9b2882dd87663914e`).

**Work:** Implement all five generic v5 `$27 stringOps` forms with typed encoded
text, independent byte-sized IDs, bounded storage, and host save persistence.

**Pass:** exact host/SNES fixtures preserve raw `$FF` controls and arguments,
variable operands, mutation, copy, absent-source nuke, and scheduler survival.
Malformed, missing, identical-copy, and bounds cases follow canonical behavior
or fail closed; no game or donor data participates.

---

## C9 — variable-range initialization

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for SCUMM ROM SHA-256
`19bff51435685c9ce26ee413ba708760d67c6e83c95c9a67096c8b61822b241f`.
The exact byte/word range case completed in one execution frame. Evidence:
`build/scumm-c9-nexen-19bff51435685c9c/report.json` (SHA-256
`a2bf862be179fd38cd074f6eef1c0520a23930bbfae9f13b8ea25ded53061e57`).

**Work:** Implement canonical v5 `$26/$A6 setVarRange` with a resolved starting
result reference, byte count, and consecutive byte or signed-word values.

**Pass:** exact host/SNES fixtures cover indexed globals, locals, packed bits,
signed word values, zero-count 256-entry behavior, wrap, truncation, and storage
boundaries. Fate independently crosses both real `$26` ranges without a
game-specific branch; no game or donor data makes the gate pass.

---

## C10 — room operations and persistent room intent

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for SCUMM ROM SHA-256
`f4926d569b8bc2844b5b054c826b97310c755c251eec8a90f7067805dfa03a7e`.
The exact 19-operation case completed within eight video frames. Evidence:
`build/scumm-c10-nexen-f4926d569b8bc284/report.json` (SHA-256
`e46d2cbe3d7f14d2b76cc205020a2a8862d4e33cc48dd86fad98a1c5b8852911`).

**Work:** Implement the complete full-header v5 `$33/$73/$B3/$F3 roomOps`
family as engine-owned intent: camera and screen geometry, shake, scaling,
palette and intensity state, fade/transform/shadow, temporary save requests,
cycle timing, and named auxiliary strings. Preserve host intent through SAME
save states and route palette changes through the public video service.

**Pass:** a copyright-free host/SNES fixture proves every valid sub-op,
variable operands, exact palette bytes, slot-99 behavior, auxiliary-string
restore, and cycle timing. Malformed and v3-only forms fail closed. Fate crosses
its real `loadString(31, "iq-points")` without a game-specific branch; no game
or donor data makes the gate pass.

---

## C11 — deterministic random-number opcode

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for SCUMM ROM SHA-256
`847b318ea1716ce59af47b6036bf33e6d6b54d807e8c37ce19ab756179950652`.
The exact direct/variable and boundary case completed within five video frames.
Evidence: `build/scumm-c11-nexen-847b318ea1716ce5/report.json` (SHA-256
`98ae6678b066b74c07b3397c5eb85901a0f76bb993d90d5840dd8b6b01482aaa`).

**Work:** Implement canonical v5 `$16/$96 getRandomNr` with engine-owned,
deterministic PRNG state and inclusive `0..maximum` results. Preserve and
validate the generator state through SAME save/load.

**Pass:** a copyright-free host/SNES fixture proves direct and variable maxima,
the 0 and 255 boundaries, exact state advancement, and save/load continuation.
Fate independently consumes its real maximum-255 result without a game-specific
branch; no game or donor data makes the gate pass.

---

## C12 — pseudo-room resource mapping

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for SCUMM ROM SHA-256
`aadbf933825a881c0c8763b9df36b144ed8c01ce04575793bdcaa6f24bcbff3a`.
The exact two-tick case completed within five video frames. Evidence:
`build/scumm-c12-nexen-aadbf933825a881c/report.json` (SHA-256
`b3234bd590b54202da74a3db7c6652e583fe3c58f56e265cf5a9beb5e933fb95`).

**Work:** Implement generic v5 `$CC pseudoRoom` as a 128-entry engine-owned
room-resource mapper. Consume the complete zero-terminated list, ignore entries
without bit 7, resolve high-bit room loads, and preserve the map through saves.

**Pass:** a copyright-free host/SNES fixture proves mapping, ignored entries,
overwrite, tick survival, room resolution, malformed-list failure, and save/load
replay. Fate independently builds its exact mapper without a game-specific
branch; no game or donor data makes the gate pass.

---

## C13 — resource cache and lock intent

**Status:** Passed on 2026-08-22 in MCP-enabled Nexen for SCUMM ROM SHA-256
`44bb9e4eca6d7287a77262e56809015ff4cbda5a2934805da2e8512fd3456f3c`.
The exact two-tick case completed within five video frames. Evidence:
`build/scumm-c13-nexen-44bb9e4eca6d7287/report.json` (SHA-256
`586df1fe2caf5906953bd2be9cb93f1da022b761e32147fbffbfa851d1e2125e`).

**Work:** Implement generic v5 `$0C/$8C resourceRoutines` as engine-owned
load/nuke/lock/unlock intent for scripts, sounds, costumes, rooms, and charsets,
including clear-heap and room/object resource normalization.

**Pass:** a copyright-free host/SNES fixture proves all 20 operations, direct
and variable operands, mapped rooms, object identity, malformed failure, and
save/load replay. Fate independently crosses its real clear-heap operation.

---

## C14 — full-header actor configuration

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`172d9a439f5d5310da008f1516bb570ebe3d61c7235b5555036f170dd7b70125`.
The exact two-tick case completed within eight video frames. Evidence:
`build/scumm-c14-nexen-172d9a439f5d5310/report.json` (SHA-256
`ab21b1b886be8bccf7027ed521e05d73cd9a4ddf71de516ab5516c48d56ad867`).

**Work:** Implement canonical full-header v5 `$13/$53/$93/$D3 actorOps` as
engine-owned actor configuration state, including variable operands, reset
semantics, animation frames, palette, encoded names, scale, clipping, and
box-following policy.

**Pass:** a copyright-free host/SNES fixture proves every valid v5 sub-operation,
direct and variable operands, retained costume/palette/name across
`Actor::initActor(0)`, malformed-input failure, and host save/load replay. Fate
independently initializes Indy and Sophia and advances to its next generic opcode.

---

## C15 — actor-follow camera intent

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`f12914c423a97617b847e6ed8854eee25b606338a681efbbe31ab17bbc3a5865`.
The exact two-tick case completed within six video frames. Evidence:
`build/scumm-c15-nexen-f12914c423a97617/report.json` (SHA-256
`066648bd65cb0194bca2f790820bdc361586ba3337cd2d95b15f0ebb0d0218e3`).

**Work:** Implement canonical v5 `$52/$D2 actorFollowCamera` as a bounded,
engine-owned camera-follow intent with direct and variable actor selection.
Keep room transitions, actor movement, redraw, and inventory-script policy out
of this opcode slice until their semantic adapters exist.

**Pass:** a copyright-free host/SNES fixture proves direct and variable forms,
range and truncation failure, scheduler-yield persistence, and host save/load
replay. Fate independently selects actor 1 through its real variable form and
advances to `$5D setClass`.

---

## C16 — sparse object class state

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`fe1fb1421077648c9584eefcbb0a5eaf3e1f821e7727cba6a4816d52173ffbff`.
The exact two-tick case completed within six video frames. Evidence:
`build/scumm-c16-nexen-fe1fb1421077648c/report.json` (SHA-256
`282be45a82c5fc81f71df4c557523fc8f88d8a86bb2895f5ca2cea7c8d253529`).

**Work:** Implement canonical v5 `$5D/$DD setClass` with full 16-bit object
identity, direct and variable class selectors, 32-bit class masks, remove, and
clear-all semantics. Keep it bounded through a reusable 512-record sparse table.

**Pass:** a copyright-free host/SNES fixture proves direct and variable object
and class operands, set/remove/clear behavior across scheduler yields, capacity
recovery, malformed-input failure, and host save/load replay. Fate independently
sets class 13 on object 2 and advances into script 18 at `$7A verbOps`.

---

## C17 — bounded v5 verb state

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`c4ec37cdce22fa48f6123122c1e733393d9a94aea9048eacb2944347a4a26b26`.
The exact two-tick case completed within eight video frames. Evidence:
`build/scumm-c17-nexen-c4ec37cdce22fa48/report.json` (SHA-256
`5363624900dceebc7f9b4b580d4e893ceabcb05685d5ac8602a3c15f18006e29`).

**Work:** Implement canonical v5 `$7A/$FA verbOps` as engine-owned state:
all valid selectors, direct and variable operands, encoded inline/resource names,
image sources, `NEW` defaults, mode changes, and deletion. Keep drawing and
hit-testing in the presentation/input adapters.

**Pass:** a copyright-free host/SNES fixture proves the complete selector
surface, scheduler persistence, bounded names, malformed-input failure, and host
save/load replay. Fate independently constructs 18 exact verbs and advances to
`$AC expression` in script 132.

---

## C18 — canonical v5 expression evaluator

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`17c3d40202e4e80509a00ea7cf227c9b518af9e15498ceacc99ac106d1e254c6`.
The exact two-tick case completed within five video frames. Evidence:
`build/scumm-c18-nexen-17c3d40202e4e805/report.json` (SHA-256
`52953b0eba95034b8908565d8aabff21ec3451fc5a01fddadabff1bdf607db07`).

**Work:** Implement canonical v5 `$AC expression` with its shared 256-entry
signed 32-bit stack, direct/variable pushes, add/subtract/multiply/divide,
reserved-token behavior, nested ordinary opcodes, and final v5 variable
narrowing. Preserve bounded fail-closed behavior for malformed programs.

**Pass:** a copyright-free host/SNES fixture proves every arithmetic token,
32-bit intermediates, truncation-toward-zero division, nested dispatch,
indexed/local/bit results, reserved tokens, scheduler persistence, malformed
input, and host save/load replay. Fate independently completes both expressions
in script 132 and advances to `$40 cutscene` in script 74.

---

## C19 — canonical v5 cutscene stack and override

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`b4ad8bb60153535e9b4079009d72f068fb8aa2323b537d85f0fa047ef156178a`.
The exact two-tick case completed within four video frames. Evidence:
`build/scumm-c19-nexen-b4ad8bb60153535e/report.json` (SHA-256
`8267c9d9b00e05d1437c6ed8aab3c72fc750b56e92b29be1f972f6bd9fe6fd70`).

**Work:** Implement canonical v5 `$40 cutscene`, `$C0 endCutscene`, and `$58
beginOverride/endOverride`: signed word-varargs, the bounded nested cutscene
stack, per-script override depth, callback variables 35/36, recorded override
PC/slot state, logical skip abort, and save/load persistence.

**Pass:** copyright-free host/SNES fixtures prove direct and variable
arguments, nesting, override markers, exact unwind, malformed-state failure,
and host save/load replay. Host tests additionally prove callback and skip-abort
behavior. Fate enters the real start callback and advances to `$19 doSentence`
in script 20 offset `$0077`.

---

## C20 — canonical v5 sentence queue

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`da9e832a2a7b2d7c3b41050ed3a6926a89482ae7369987d9b97f20a5070c479a`.
The exact two-tick case completed within the twelve-frame bound. Evidence:
`build/scumm-c20-nexen-da9e832a2a7b2d7c/report.json` (SHA-256
`be2dc963a9e87df758a3496f26d652be00aefc696383709b3e1bf20e527a8055`).

**Work:** Implement canonical v5 `$19/$39/$59/$79/$99/$B9/$D9/$F9
doSentence`: every direct/variable operand combination, the bounded six-record
LIFO queue, derived preposition state, sentence freeze depth, deferred variable
33 callback launch, identical-object suppression, and the short `$FE`
cancellation form with transient click/key clearing.

**Pass:** copyright-free host/SNES fixtures prove every operand form, queue
order/capacity, nested freeze behavior, cancellation without object over-read,
malformed-state failure, and host save/load replay. Host tests additionally
prove deferred callback locals, same-object suppression, sentence-script stop,
and preservation of held input while click edges clear. Fate completes callback
script 20 and reaches raw room 68 through `$72 loadRoom` in script 74.

---

## C21 — canonical v5 drawObject

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`f0626c8194eb2ff30c51528480c009ea583b0cceb6ff0028024d3a047325c9d0`.
The exact two-tick case completed within four video frames. Evidence:
`build/scumm-c21-nexen-f0626c8194eb2ff3/report.json` (SHA-256
`e3237a6b0189f31628d0d700e17cbce1e6af73979cc8b6bf239c5b5bb534731a`).

**Work:** Implement canonical v5 `$05/$85 drawObject`: direct/variable object
identity, full-header at/state/neither selectors, coordinate relocation in
eight-pixel units, walk-target adjustment, bounded draw-queue intent, exact
rectangle overlap clearing, and missing-local-object no-op behavior. Decode
canonical `OBCD/CDHD` local-object metadata from raw v5 rooms and persist all
mutable object state.

**Pass:** a copyright-free host/SNES fixture proves variable/direct coordinates
and state, relocation, overlap clearing, exact queue order, missing lookup,
malformed/capacity failure, and host save/load replay. Fate independently draws
room-68 object 939 at script 74 offset `$0033` with its canonical geometry and
default state 1.

---

## C22 — canonical v5 null-room transition

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`f93789ee016d4c061d8833bf9e0d90ed3e35a8798f595872c94ef653c750ec8d`.
The exact four-tick case completed within the twelve-frame bound. Evidence:
`build/scumm-c22-nexen-f93789ee016d4c06/report.json` (SHA-256
`e4d460bf72cba2860144e0958351b395df8adcd8e0b15f2dee5eea06bdcf7e46`).

**Work:** Complete `$72/$F2 loadRoom` transition semantics for direct,
variable, and pseudo-room operands. Model canonical room zero as a
resource-less null scene that commits current room 0, clears room-local objects
and draw intent, preserves global object state, and detaches/clears room
presentation without looking up `room.0`.

**Pass:** the copyright-free host/SNES fixture proves variable and direct room
transitions, room-local clearing, the resource-less null marker, persistence
across yields, and exact termination. Host tests additionally prove deterministic
black presentation, missing-nonzero-room failure, and save/load replay. Fate
crosses `$72 00` at script 74 offset `$0078` and advances to `$14` at `$007A`.

---

## C23 — canonical v5 print slots and raw CHAR fonts

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`6c9a2b2421a728b434532eb3cc3c0419d94b71c060a600f61b5b5120c033bfd5`.
Evidence: `build/scumm-c23-nexen-6c9a2b2421a728b4/report.json` (SHA-256
`44df272262b4c29dac88c3f4379e9ad4325333c34833735c08e30380e469fea9`).

**Work:** Implement canonical `$14/$94 print` and `$D8 printEgo`, four persistent
default slots, direct/variable AT/COLOR/CLIPPED operands, center/left/overhead,
bounded encoded messages, and fail-closed v5 erase/voice selectors. Adapt raw
LucasArts v5 CHAR wrappers and relative glyph offsets for portable presentation.

**Pass:** copyright-free host/SNES fixtures prove actor-to-slot routing,
setup-only `$FF`, transient text styles, encoded controls, variable operands,
printEgo, save/load, and bounded failure. A synthetic raw CHAR matches the
cooked glyph exactly; Fate's real `charset.1` decodes its 6x8 digit-three glyph.
Fate saves slot-0 defaults `(160,8)`, centered and overhead, at script 74 offset
`$007A`, then advances through the callback that C24 covers.

---

## C24 — canonical zero-depth override sentinel

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`8f2f1a22e71a5c68238af5e58bc6623d30fa9d79665e95e96b17530d9d7387c3`.
Evidence: `build/scumm-c24-nexen-8f2f1a22e71a5c68/report.json` (SHA-256
`1dd70280d6f5c4d2e7f92b2caed32c5f9f5ab9da4e45b8e61bde51439f7a0e44`).

**Work:** Treat cutscene record zero as the canonical `$58` override sentinel.
At depth zero, beginOverride records PC/slot and skips its following jump;
endOverride clears that sentinel; skip-abort resumes it. Persist and validate
the sentinel in host save state without changing the active cutscene stack.

**Pass:** the copyright-free host/SNES fixture proves sentinel arming across a
yield, unchanged depth zero, standalone clear, continued execution, exact halt,
save/load, malformed-state rejection, and skip-abort. Fate crosses `$58 00` in
script 21 at offset `$0004`, retires script 74 and the main boot script, and
enters raw room 75 on frame 524.

---

## C25 — canonical v5 soundKludge queue and flush

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`b0e38b77bbd470289572ce0b7da7da3820fbac9271a8973244d8577a5fbe9c89`.
Evidence: `build/scumm-c25-nexen-b0e38b77bbd47028/report.json` (SHA-256
`d9b2755b4e9412f7a29ca1306b644cec19b59a1b1ec61bfc4bba3f4173050b22`).

**Work:** Implement canonical `$4C soundKludge` word-varargs, a bounded queue
that persists until command `-1`, and neutral normalized mappings for iMUSE
commands 6, 8, 9, 10, and 11. Persist and validate host queue/history state;
fail closed on malformed streams, unsupported commands, and capacity overflow.

**Pass:** The copyright-free host/SNES fixtures prove queue persistence across
a scheduler yield, ordered drain, command 11 stop-all mapping, explicit FLUSH,
exact halt, save/load, and bounded failures. Fate room 75 independently supplies
the exact real ENCD bytes at offsets `$00E7` and `$00EC` without a game-specific
opcode branch.

---

## C26 — canonical v5 saveRestoreVerbs banks

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`49cf161cc05cd27a668d9d6beff354cf52a64e06386f60efcd484c1ae653194c`.
Evidence: `build/scumm-c26-nexen-49cf161cc05cd27a/report.json` (SHA-256
`8d011ee0871dc7d4040bf9bc7a982f51a556c722b7e53ef123787de72dfdf4bf`).

**Work:** Implement canonical `$AB saveRestoreVerbs` save, restore, and delete
over inclusive u8 ranges. Preserve saved verbs in independent bounded physical
slots so active replacements may reuse the same verb identity; persist and
validate both namespaces in host save state.

**Pass:** The copyright-free host/SNES fixture proves two-verb save into bank
5, removal from the active namespace, same-ID replacement, destructive restore
of the original, saved-bank deletion, reversed-range no-op, exact halt,
save/load, malformed-state rejection, and capacity failure. Fate script 19
independently supplies four real `$AB` saves (`1..12`, `101..112`, `100`, and
`52..55`) without a game-specific opcode branch.

---

## C27 — generic v5 room-local script adapter

**Status:** Passed on 2026-08-23 in the host oracle and Fate preflight. Evidence:
`build/scumm-s6-fate-preflight/report.json` (SHA-256
`ee1c5d7cb50c9db308f6c21e16b5d33865846ea49ae2f76516b2732f1bddefe5`).
The SNES ROM is byte-identical to C26 because SNES-side raw resource delivery
remains explicitly owned by K2.

**Work:** Decode `ENCD`, `EXCD`, and canonical v5 `LSCR` room chunks. Resolve a
script missing from the global table only from the current room, retain its room
identity in the scheduler/save state, and retire local slots on room transition.

**Pass:** Synthetic resources prove local startScript resolution, nested
execution, yield/save/load, room-transition retirement, duplicate/truncated
chunk rejection, and malformed save rejection. Fate room 75 independently
provides local scripts `200..208`; exact entry code resolves `LSCR.200`.

---

## C28 — canonical v5 animateActor

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`8c692e621bbe787321074dd7cdaa3f04db7d5847b96a1e24b2b416dcf9642776`.
Evidence: `build/scumm-c28-nexen-8c692e621bbe7873/report.json` (SHA-256
`ff33aa0b99818f0c436df6e3c413454bd8f9f00ef3eac976c2d16242efc50ada`).

**Work:** Implement canonical `$11/$51/$91/$D1 animateActor` with independent
direct/variable actor and animation operands. Keep the live animation request
distinct from C14 actorOps frame/speed configuration and persist it in actor
save state.

**Pass:** The copyright-free host/SNES fixture proves direct animation 250,
fully-variable animation 6 across a yield, actor creation, exact halt,
save/load, malformed-state rejection, invalid actor rejection, and truncated
operand failure. Fate room 75 independently executes the exact `$11 0A FA` and
`$11 0A 06` records in `LSCR.200` at offsets `$0837/$083B`; the next pinned
frontier is `$D5 getActorFromPos` in `LSCR.205` at offset `$0004`.

---

## S1 — Monkey profile extraction

**Status:** Passed on 2026-08-22 without a game-ROM run. The structured profile
is `examples/profiles/templates/monkey1_ultimate_talkie.json`; evidence is
`build/scumm-s1-profile/report.json` (SHA-256
`821a2f65bfebaf1965ece0a36465cbac3e7f83d25410a85125f095a1f15d443f`).
The SNES build remained byte-identical to the already-gated C6 ROM
`9c59520d659c5e285a44f8b7a96aead95be5b40ab403d4ac77c4fde2cff81ff4`.

**Work:** Move only game identity and policy out of the SCUMM semantic core:
resource keys, sound/speech maps, game-specific quirks, coordinate policy, and
copy-protection choice.

**Pass:** the independent SCUMM fixtures remain exact; the core contains no
Monkey-only branch; profile validation fails on missing resources. Any Monkey
run is exploratory compatibility evidence only and cannot make this gate pass.

---

## S2 — SCUMM input and resource service adapters

**Status:** Passed on 2026-08-22 with copyright-free encrypted raw-resource and
logical-input fixtures. Evidence: `build/scumm-s2-adapters/report.json`
(SHA-256 `99ea6b5b744b85c95b703fc0114589eba211739614528063d30637222be15117`).
The unchanged C6 ROM retained H0, K1, and C2-C6.

**Work:** Wrap the existing engine's mouse/joypad/text input and resource lookup
behind SAME. The old implementation may be consulted for structure but provides
no behavioral pass condition.

**Pass:** synthetic SCUMM input/resource fixtures remain exact and no semantic
code reads controller or physical storage registers directly.

---

## S3 — SCUMM video adapter

**Status:** Passed on 2026-08-22 with copyright-free room, actor, z-mask,
cursor, and v5 CHAR-style font fixtures. Baseline and negotiated accelerator
plans produce the same exact logical and physical frames. Evidence:
`build/scumm-s3-video/report.json` (SHA-256
`23dc2bd7b8faef09770df554cd339dc300e3f01dd582c7202267837473a9aef4`).
The unchanged C6 ROM retained H0, K1, and C2-C6.

**Work:** Present the current room/actor/cursor result through SAME's baseline
indexed surface plus resource-backed fonts and negotiated SNES accelerators for
tiles, OAM, z-mask, HDMA, and SA-1 scaling.

**Pass:** copyright-free scene and font fixtures match the host logical frame; an
accelerator-disabled path produces the same logical result; NMI/DMA gates remain
clean.

---

## S4 — SCUMM audio and save adapters

**Status:** Passed on 2026-08-22 with a copyright-free score-intent, SFX,
speech, and two-room save fixture. Baseline score interpretation and a
negotiated curated-TAD plan preserve identical logical playheads. Evidence:
`build/scumm-s4-audio-save/report.json` (SHA-256
`715ffdbdd0b77480d3713f0d99668b6e8a0b31d065b54e472e5856f5b18c1765`).
The unchanged C6 ROM retained H0, K1, and C2-C6.

**Work:** Route music, SFX, and speech through normalized SAME audio. Put complete
SCUMM state inside the host save envelope and host storage backend.

**Pass:** synthetic music/SFX/speech requests are exact; synthetic save state
restores across a room transition; wrong game/schema/CRC fails visibly.

---

## S5 — bind the real SCUMM v5 engine to the SNES host

**Status:** Passed on 2026-08-23 in Nexen; the latest retained regression uses
SCUMM-selected ROM SHA-256
`49cf161cc05cd27a668d9d6beff354cf52a64e06386f60efcd484c1ae653194c`.
The two-tick host/SNES trace agrees on semantic state and four complete audio
packets with zero loss. Evidence:
`build/scumm-s5-binding-49cf161cc05cd27a/report.json` (SHA-256
`481c22b18b4b53f3d931dbda66df42cc752a372381d7e9a8dfffdbc541ac705e`).
The latest demo ROM SHA-256
`026ef519d6ae1af761f76f5b902a5b1ab8e102b2ecc74e41207120bc7bb42f5c`
retained H0/K1 and the SCUMM build retained C1-C26.

**Work:** Implement `ScummV5_Engine_*` using the extracted engine and select it as
`Same_ActiveEngine_*` for a SCUMM ROM build.

**Pass:** host and SNES semantic/service fixtures agree with zero host packet
loss. A game-specific demo may illustrate compatibility but is not gate evidence.

---

## S6 — second SCUMM v5 profile

**Status:** In progress. The latest bounded preflight passed on 2026-08-23 using the
redistributable Fate of Atlantis interactive demo archive SHA-256
`558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`.
The profile and generic raw adapter expose 10 rooms, 74 scripts, 28 sounds, 25
costumes, and four charsets; logical input and a SAME save-state round trip pass.
Evidence is `build/scumm-s6-fate-preflight/report.json` (SHA-256
`ee1c5d7cb50c9db308f6c21e16b5d33865846ea49ae2f76516b2732f1bddefe5`).
The S6 gate remains unpassed: real boot crosses both C9 variable ranges and its
first C10 auxiliary-string load, then consumes the real C11 maximum-255 random
result 226 as a child-script delay. C12 consumes all 31 pseudo-room records and
builds an exact mapper with 100 populated entries. C13 crosses the real
clear-heap resource routine. C14 initializes actor 1 as costume 2, color 15, name
`Indy`; actor 2 as costume 28, color 13, name `Sophia`; and actor 4 with talk
color 14. C15 then selects actor 1 as the camera-follow target through `$D2`.
C16 sets class 13 on object 2 through `$5D`. C17 then constructs 35 exact verb
records through generic `$7A/$FA verbOps`. C18 completes both canonical `$AC`
expressions in script 132. C19 enters the real `$40` cutscene and establishes
its exact stack record. C20 crosses `$19 FE`, clears the transient click while
preserving the held pointer, completes callback script 20 and its child
initializers, then returns to script 74. `$72 loadRoom(68)` now crosses through
a generic raw-v5 room decoder/presentation adapter. The adapter parses the
canonical room/image chunks, decodes raw, zig-zag, and major/minor strip
families, retains the 320x200 indexed logical image, and projects it into the
256x224 host viewport. The pinned room-68 logical SHA-256 is
`2f633aec02b1b7f5e22adc70e18aa15fff9a668b3b15d5c829ae1b1907e57490`;
all ten exposed Fate rooms decode. C21 then consumes the canonical `$05` at
script 74 offset `$0033`, draws room-local object 939 with default state 1, and
retains its decoded 24,32 / 272x144 geometry. After the pointer is released,
C22 crosses `$72 loadRoom(0)` as a resource-less null scene, clears room-local
objects/draw intent while preserving object 939's global state, and blanks the
presentation deterministically. C23 then consumes setup-only `$14`, saves the
canonical `(160,8)` centered/overhead defaults in print slot 0, and independently
decodes the real raw v5 CHAR resource. C24 then treats `$58 00` in callback
script 21 at offset `$0004` as the canonical zero-depth sentinel clear. Script
74 retires at PC 140; the main boot script retires at PC 13168 on frame 524 and
enters decoded raw room 75. C25 then consumes the exact room-75 ENCD `$4C`
command lists at offsets `$00E7` and `$00EC`, retaining command 11 until command
-1 emits normalized music-stop, all-SFX-stop, speech-stop, and flush packets.
The preflight also executes script 19's exact four `$AB` records at `$0117`,
saving verb ranges `1..12`, `101..112`, `100`, and `52..55` into their canonical
banks and removing all 29 from the active namespace through C26.
The C27 raw adapter decodes room 75's local scripts `200..208`; its exact ENCD
resolves local script 200. C28 executes that script's exact actor-10 animation
requests 250 and 6 at offsets `$0837/$083B`. The pinned next opcode frontier is
now `$D5 getActorFromPos` in local script 205 at offset `$0004`.
Actor behavior and actual embedded-audio playback proofs remain.

**Work:** Convert and profile a second user-supplied SCUMM v5 title without
editing the opcode core.

**Pass:** boot, room, actor/input, audio, and save fixture succeeds. Any required
game exception is a named profile quirk or narrow adapter, not a generic opcode
change.

This is the gate that earns the phrase “reusable SCUMM v5 engine.”

---

## A1 — AGI conditions, NOT/OR, and GOTO

**Work:** Complete AGI v2 logic control flow in the host oracle with malformed-
stream and operation-budget tests.

**Pass:** independent fixtures cover true/false conditions, NOT, OR groups,
relative branches, and logic-zero reruns.

---

## A2 — raw AGI resources and vector picture

**Work:** Implement selected DOS AGI DIR/VOL discovery, logic loading, vector
picture drawing, and priority screen behind resource/video services.

**Pass:** host images and priority samples match an independent AGI oracle; corrupt
or unsupported resource versions fail by resource and offset.

---

## A3 — views, motion, collision, and input

**Work:** Decode views/loops/cels and implement object animation, horizon,
priorities, blocks, collision, ego control, and controller events.

**Pass:** synthetic movement scenes and one real King’s Quest room are exact and
saveable.

---

## A4 — parser, text, inventory, menus, and sound

**Work:** Add vocabulary/tokenization, `said`, prompt/text windows, inventory,
menus, and AGI sound timing through SAME services.

**Pass:** a reproducible typed-command interaction changes the real room state,
plays sound with correct completion flag, and survives save/load.

---

## A5 — King’s Quest I progression gate

**Work:** Run user-supplied data through multiple rooms and one complete puzzle or
death/restore sequence.

**Pass:** every discovered semantic gap gains a host fixture; the SNES profile
uses no SCUMM-specific service.

---

## K2 — SNES SAME-package/resource backend

**Work:** Read package header/directory on SNES and expose bounded seek/read by
stable resource key.

**Pass:** all four adventure-demo sections are found and CRC-verified; a corrupt
package fails visibly; engines contain no hand-synchronized MSU offsets.

---

## K3 — production TAD/SPC backend

**Work:** Adapt the currently proven local TAD integration behind semantic music,
SFX, speech/control packets.

**Pass:** exact command mapping, nonzero captured audio, correct driver state, no
video timing regression.

---

## K4 — SNES save backend

**Work:** Implement SRAM/BW-RAM slot storage and atomic envelope writes.

**Pass:** power-cycle restore, corruption rejection, engine/game/schema mismatch,
and capacity failures are all observable.

---

## K5 — real S-CPU/SA-1 job backend

**Work:** Implement one-owner mailbox transitions and a deterministic buffer job.

```text
IDLE -> PENDING -> RUNNING -> COMPLETE -> IDLE
                         \-> FAULT
```

**Pass:** sequence/result exact; pending work cannot be overwritten; timeout and
fault are visible; repeated fresh resets work.

---

## Machine personalities remain supported

After the engine-host path is stable, continue independently:

- MC68000 core behind a big-endian guest bus;
- Z80 core behind a little-endian guest bus;
- dynamic SAME-VDP trace translation;
- Genesis trace target before commercial ROM boot;
- current BOR design as inspected locally, whether native engine, VM, or hybrid;
- Superman and Black Tiger as target adapters around reusable CPU cores.

These are parallel clients of SAME, not prerequisites for SCUMM or AGI.
