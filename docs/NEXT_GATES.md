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
`6c6a69620e5fab6020491ca2733b2a4223da970d3c5a70bc62033c7e0a7eacb6`).
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
`037756487486b48f54eef64cae52aa7270ad42e081cd168e7a322282bdf2c62a`.
Retained evidence: `build/scumm-c28-nexen-037756487486b48f/report.json`
(SHA-256
`0a43c63e13637aa396ea1bbc895b598f696ab57e6597d63befa6ee440c9d896f`).

**Work:** Implement canonical `$11/$51/$91/$D1 animateActor` with independent
direct/variable actor and animation operands. Keep the live animation request
distinct from C14 actorOps frame/speed configuration and persist it in actor
save state.

**Pass:** The copyright-free host/SNES fixture proves direct animation 250,
fully-variable animation 6 across a yield, actor creation, exact halt,
save/load, malformed-state rejection, invalid actor rejection, and truncated
operand failure. Fate room 75 independently executes the exact `$11 0A FA` and
`$11 0A 06` records in `LSCR.200` at offsets `$0837/$083B`.

---

## C29 — canonical v5 getActorFromPos

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`037756487486b48f54eef64cae52aa7270ad42e081cd168e7a322282bdf2c62a`.
Retained evidence: `build/scumm-c29-nexen-037756487486b48f/report.json`
(SHA-256
`f6411aea3423e1bd0b444aba6a9f47f504aca6f520102eb555d3e939ddbee274`).

**Work:** Implement canonical `$15/$55/$95/$D5 getActorFromPos` with a result
operand and independent direct/variable word coordinates. Search actors in
ascending identity order, requiring visibility, current-room membership,
inclusive renderer-published bounds, and absence of object class 32
(`untouchable`). Persist the neutral spatial seam in host save state.

**Pass:** The 34-byte copyright-free host/SNES fixture proves first-match
ordering, untouchable rejection, direct and fully-variable forms, no-match
zero, exact halt, save/load, malformed-state rejection, and truncated operand
failure. Fate room 75 independently executes the exact `$D5` in `LSCR.205` at
offset `$0004`, stores zero for the empty picking scene, and takes its branch.

---

## C30 — canonical v5 findObject

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`037756487486b48f54eef64cae52aa7270ad42e081cd168e7a322282bdf2c62a`.
Retained evidence: `build/scumm-c30-nexen-037756487486b48f/report.json`
(SHA-256
`7d4b53d68d041c4de4a1a140b838c05b92b030f29716c6745bfcca77156cd113`).

**Work:** Implement canonical `$35/$75/$B5/$F5 findObject` with a result
operand and independently direct-byte or full-variable coordinates. Search raw
room objects in local resource order, reject class 32, enforce each object's
parent-state chain, use half-open right/bottom bounds, and return zero on no
match. Persist and strictly validate local indexes and hierarchy metadata.

**Pass:** The 30-byte copyright-free host/SNES fixture proves resource-order
first match, untouchable rejection, visible and hidden parent chains, a
variable coordinate above 255, half-open boundary rejection, no-match zero,
exact halt, save/load, malformed-state rejection, and truncated operands. Fate
room 75 independently executes the exact `$F5` in `LSCR.205` at offset `$0018`,
stores zero in local 0 and variable 108, and reaches its canonical yield at PC
`$0025`. This removes the last unsupported opcode in the pinned polling branch;
actor room/placement behavior continues in C31.

---

## C31 — canonical v5 putActorInRoom

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`037756487486b48f54eef64cae52aa7270ad42e081cd168e7a322282bdf2c62a`.
Evidence: `build/scumm-c31-nexen-037756487486b48f/report.json` (SHA-256
`2a8c22ba55c3f7b2bd5d6031be1ff180c657cc258155e381127de64f2e5452dc`).

**Work:** Implement canonical `$2D/$6D/$AD/$ED putActorInRoom` with independent
direct/variable byte operands. A nonzero assignment changes only actor room;
room zero also performs the canonical removal placement at `(0,0)`, stops
movement, and hides the actor. Persist logical position and movement flags and
reserve their bounded SNES actor-state seam.

**Pass:** The 25-byte copyright-free host/SNES fixture proves both operand
forms, variable byte truncation, preservation on nonzero assignment,
room-zero position/movement/visibility removal, exact yields and halt,
save/load, malformed-state rejection, invalid actor rejection, and truncated
operands. Fate room 75 independently executes exact `$2D 0A 4B` in
`LSCR.200` at offset `$082D`: actor 10 joins room 75 but remains hidden at
`(0,0)` until `$0E putActorAtObject` at `$0830`, the next ordered frontier.

---

## C32 — canonical v5 putActorAtObject

**Status:** Passed on 2026-08-23 in MCP-enabled Nexen for SCUMM ROM SHA-256
`9600d1e035cd86e0aeecac5a75dd2a1595a9a1ac22cedc27ef90338d8f3687da`.
Evidence: `build/scumm-c32-nexen-9600d1e035cd86e0/report.json` (SHA-256
`47ec45e5fdd2aed1425614a1adee6f96f101ca7bb8511788f678191086e7963a`).

**Work:** Implement canonical `$0E/$4E/$8E/$CE putActorAtObject` with an
independently direct/variable actor byte and object word. Resolve decoded room
object walk points, use `(240,120)` when the object is unavailable, and apply
the canonical current-room show/stop and noncurrent visible hide/stop
lifecycle. Retain exact walk points until a later raw-room walkbox decoder can
perform canonical snapping.

**Pass:** The 27-byte copyright-free host/SNES fixture proves both operand
forms, object walk points, the missing-object fallback, current/noncurrent and
visible/hidden lifecycle branches, exact yields and halt, save/load, invalid
actor rejection, and truncated operands. Fate room 75 independently executes
exact `$0E 0A 07 04` in `LSCR.200` at offset `$0830`, placing actor 10 at
object 1031's walk point `(1164,46)`, showing it, and stopping movement. The
next ordered frontier is costume-backed actor rendering at that placement.

---

## C33 — generic v5 costume decode and initial actor pose

**Status:** Passed on 2026-08-23 in the host oracle and Fate preflight.
Evidence: `build/scumm-s6-fate-preflight/report.json` (SHA-256
`6c6a69620e5fab6020491ca2733b2a4223da970d3c5a70bc62033c7e0a7eacb6`).
The SNES ROM is byte-identical to C32 because SNES-side raw resource delivery
remains explicitly owned by K2.

**Work:** Strictly decode classic v5 costume formats `$58/$59`: palette,
animation/data/frame tables, initial limb sequences, signed cel geometry, and
BYLE RLE. Composite visible current-room initial poses into the raw room's
logical indexed surface in vertical actor order, honor actor palette overrides,
and publish exact rendered hitboxes for actor queries.

**Pass:** Copyright-free 16- and 32-color resources prove table/RLE decoding,
composition, palette mapping, hitbox publication, absent poses, and fail-closed
format/offset/truncation handling. Fate costume 58 independently decodes actor
10's initial 180-degree frame into one 7x7 cel with 37 opaque pixels and bounds
`(1161,43)..(1167,49)`, producing logical room SHA-256
`7b1c33673fd48f822bbaca4d25a2877e63596bce3dfaa42d4275cae66bf91ee5`.
The next ordered costume frontier is chore advancement, scaling, and raw-room
z-mask occlusion; embedded audio playback remains an independent S6 frontier.

---

## C34 — persistent classic costume chore advancement

**Status:** Passed on 2026-08-23 in the host oracle and Fate preflight.
Evidence: `build/scumm-s6-fate-preflight/report.json` (SHA-256
`6c6a69620e5fab6020491ca2733b2a4223da970d3c5a70bc62033c7e0a7eacb6`).
The host-only slice leaves both C32 SNES ROMs byte-identical.

**Work:** Persist cardinal facing, active frame, sequence step, and animation
speed progress per actor. Draw the current pose before advancing all 16 classic
limb cursors; honor looping and one-shot ranges and skip `$7C` counter and v5
`$78` sound commands. Save and strictly restore the portable cursor rather than
resource pointers; bump the SCUMM save envelope to schema 3 for the extended
actor state.

**Pass:** Copyright-free two-cel chores prove looping, one-shot holding,
draw-before-advance timing, speed gating, save/load, and malformed cursor
rejection. Fate costume 58 advances frame 1 from command 0 at step 0 to command
1 at step 1. Both poses contain 37 opaque pixels at
`(1161,43)..(1167,49)`, while the advanced logical room has exact SHA-256
`0e1972cf93f4fdce4d62abe54f4f2164417b50dfd971eee4be24c6aca041f104`.
Scaling and raw-room z-mask occlusion remain the ordered costume frontiers;
embedded audio remains independent.

---

## C35 — classic phase-table actor scaling

**Status:** Passed on 2026-08-23 in the host oracle and Fate preflight.
Evidence: `build/scumm-s6-fate-preflight/report.json` (SHA-256
`6c6a69620e5fab6020491ca2733b2a4223da970d3c5a70bc62033c7e0a7eacb6`).
The host-only slice leaves both C32 SNES ROMs byte-identical.

**Work:** Apply independent actor x/y scales through the classic 256-entry
phase table. Scale signed cel offsets around the actor's foot anchor, traverse
BYLE source data in canonical column-major order, preserve directional phase,
and derive actor hitboxes from the final unique destination pixels.

**Pass:** A copyright-free asymmetric 4x4 cel proves nonuniform `(128,192)`
scaling, horizontal destination overwrite, vertical row suppression, mirrored
phase asymmetry, exact anchors, bounds, and final pixel counts. Fate costume 58
at the same scale produces exactly 26 pixels at
`(1162,43)..(1166,48)` and logical-room SHA-256
`62db861295d986afacf38eb97e24ce29b99bdc2cb2e4eea3c0a79e29d94d33f2`.
Raw-room z-mask occlusion is the next ordered costume frontier; embedded audio
remains independent.

---

## C36 — raw v5 z-plane decode and explicit actor occlusion

**Status:** Passed on 2026-08-23 in the host oracle and Fate preflight.
Evidence: `build/scumm-s6-fate-preflight/report.json` (SHA-256
`6c6a69620e5fab6020491ca2733b2a4223da970d3c5a70bc62033c7e0a7eacb6`).
The host-only slice leaves both C32 SNES ROMs byte-identical.

**Work:** Decode the `RMIH` plane count and `ZP01..ZP04` chunks in raw v5
rooms. Validate little-endian per-strip offsets, preserve zero-offset blank
strips, expand classic literal/repeat mask RLE, and store MSB-first mask bits.
Apply an actor's explicit `forceClip` plane during costume composition and
derive pixels and hitboxes only from the visible result.

**Pass:** Copyright-free raw rooms prove both RLE packet forms, blank strips,
MSB-first pixel selection, complete actor occlusion, metadata, and fail-closed
truncation/offset/count handling. All ten Fate rooms decode with exact declared
plane counts. Fate room 42 exposes three planes; plane 1 hides all 37 opaque
pixels of costume 58 at `(10,55)`, leaves an empty hitbox, and retains logical
SHA-256 `9d451e87313acc1a834ed29dbfbc23c1bd3596de0c9de348e3ecf95117a7cc55`.
Automatic walkbox-driven plane selection belongs with the raw walkbox adapter;
embedded-audio playback remains the independent S6 frontier.

---

## C37 — raw v5 walkbox decode and automatic z-plane selection

**Status:** Passed on 2026-08-23 in the host oracle and Fate preflight.
Evidence: `build/scumm-s6-fate-preflight/report.json` (SHA-256
`6c6a69620e5fab6020491ca2733b2a4223da970d3c5a70bc62033c7e0a7eacb6`).
The host-only slice leaves both C32 SNES ROMs byte-identical.

**Work:** Strictly decode `BOXD`'s little-endian count and classic 20-byte
walkbox records: four signed corners, mask plane, flags, and scale. Determine
the actor's current usable box from its foot position using canonical reverse
priority and convex-edge containment, including v5 line boxes. When
`forceClip` is zero, select the box mask; class 20 and ignore-box actors bypass
it, while explicit clipping retains precedence.

**Pass:** Synthetic trapezoids prove geometry, reverse selection, mask limits,
automatic occlusion, class-20 bypass, explicit override, and malformed-record
rejection. All ten Fate rooms expose exact walkbox counts. In room 42, position
`(193,100)` resolves to walkbox 10 and its mask 1 automatically hides all 37
opaque pixels of costume 58, leaving an empty hitbox and logical SHA-256
`9d451e87313acc1a834ed29dbfbc23c1bd3596de0c9de348e3ecf95117a7cc55`.
`BOXM` route decoding and actor movement form the next ordered frontier;
embedded-audio playback remains independent.

---

## C38 — compressed `BOXM` routing and persistent actor walkbox

**Status:** Passed on 2026-08-23 in the host oracle and Fate preflight.
Evidence: `build/scumm-s6-fate-preflight/report.json` (SHA-256
`6c6a69620e5fab6020491ca2733b2a4223da970d3c5a70bc62033c7e0a7eacb6`).
The host-only slice leaves both C32 SNES ROMs byte-identical.

**Work:** Decode one `$FF`-terminated `BOXM` row per `BOXD` record. Expand each
ordered `(destination start, destination end, next box)` triple into a bounded
route table and reject malformed ranges, indices, row counts, and trailing
data. Implement canonical `$7B/$FB getActorWalkBox` with direct/variable actor
operands, update current-room actor box state from foot geometry, and persist it
under save schema 4.

**Pass:** Synthetic matrices prove compressed ranges, unreachable routes,
identity routing, corruption rejection, both opcode forms, and save/load.
Every Fate matrix decodes. Room 42's real 11-row matrix pins `1->10` via box 2,
`10->1` via box 7, `1->2` via box 2, and `2->1` via box 1. Canonical
`$1E/$3E/$5E/$7E/$9E/$BE/$DE/$FE walkActorTo` gate traversal is the next
ordered movement frontier; embedded-audio playback remains independent.

---

## C39 — canonical v5 actor route traversal

**Status:** Passed on 2026-08-24 in the host oracle and Fate preflight.
Evidence: `build/scumm-s6-fate-preflight/report.json` (SHA-256
`96e161d6caa2cfb5031369910dc385b3b8084b2cd888f162f0b7d6933aee2cf5`).
The host-only slice leaves both C32 SNES ROMs byte-identical.

**Work:** Implement all eight `$1E walkActorTo` operand forms, reverse-order
destination snapping, `BOXM` next-box selection, canonical shared-edge gates,
scaled 16.16 stepping, cardinal facing, walk/stand chores, `$56/$D6
getActorMoving`, and `$3B/$BB waitForActor`. Persist destinations, current and
destination boxes, leg endpoints, fractional residue, and deltas in save schema
5 so restore resumes the same step.

**Pass:** A copyright-free three-box route pins gate and direct-final-leg
selection, exact per-tick states, every operand form, wait/query behavior,
corruption rejection, and mid-leg save/load. Fate room 42 independently walks
from `(44,80)` to `(200,110)` through boxes `5→6→8→7→10`, reaching box 10 on
frame 27. Embedded-audio playback is now the sole remaining S6 behavior proof.

---

## C40 — embedded `SOU` MIDI playback

**Status:** Passed on 2026-08-24 in the host oracle and Fate demo. Evidence:
`build/scumm-s6-fate-preflight/report.json` (SHA-256
`8334ae6cc371d9f9e23b51b8bdb3bf2a247744d22668f2cac3a0c3c92335f95b`)
and `build/scumm-s6-fate-preflight/fate-sound-172.wav`. The host-only slice
leaves both C32 SNES ROMs byte-identical.

**Work:** Strictly decode `SOU ` containers, select `ROL `/`ADL `/`SPK ` by
profile order rather than child position, consume `MDhd`, parse the initial
Standard MIDI track with running status, tempo, channel, meta, and SysEx
framing, and synthesize deterministic signed-16 PCM into SAME's streaming audio
service. Implement `$7C/$FC isSoundRunning` and persist active embedded
playheads under save schema 6. Filter stale demo directory records before
advertising resource keys.

**Pass:** All 27 readable Fate sounds decode through their Roland rendition.
Sound 172 produces 12,210 mono frames at 22.05 kHz with PCM SHA-256
`e328daeefaedacf1316e284286e56fbe177d94a19d2959898dc5f61b06573749`.
It becomes active through real `$1C`, reports running through both `$7C` forms,
stops at its decoded end, and an active frame-1 save restores to a resumed PCM
stream byte-identical to uninterrupted synthesis. This closes static embedded
playback; interactive iMUSE behavior and production SNES arrangements remain
S6 blockers.

---

## C41 — Fate iMUSE branches and production TAD delivery

**Status:** Passed as a bounded implementation slice on 2026-08-24. Host report
SHA-256 is
`8334ae6cc371d9f9e23b51b8bdb3bf2a247744d22668f2cac3a0c3c92335f95b`.
Production ROM SHA-256 is
`e46fe585b7cf882fd589856883316e84711ce16e9516598731b6e0648a740517`;
its `build/scumm-s6-tad-e46fe585b7cf882f/report.json` SHA-256 is
`d88953e1f8ce9bc282912e490c02ef6eabc82c3331c369b9d94be6b38e97cdc0`.
S6 remains in progress because 26 readable sounds still lack reviewed SNES
arrangements.

**Work:** Decode every format-2 MIDI track and the exact Fate iMUSE SysEx command
surface: setup (`0`), start (`2`), hook jump (`$30`), part gate (`$32`), and
marker (`$40`). Preserve hook restoration, active notes, controller state,
branch position, and markers across save/load. On SNES, boot Terrific Audio
Driver protocol v20, transfer its loader, driver, common data, and a reviewed
sound-172 arrangement, then map SAME play/stop commands without silent loss.

**Pass:** The complete demo inventory contains 104 setup, 27 start, 189 hook,
28 part-gate, and 12 marker commands. Real sound 80 consumes hook 15 by jumping
from track 0 tick 90 to track 2 tick 1920 and resumes byte-identically after a
save. A fresh Nexen run of the 64 KiB production-audio ROM reaches TAD's playing
state, produces nonzero Fate sound-172 DSP output above a silent baseline, and
advances both video and SAME counters by exactly 120 frames. The same ROM retains
the C1 five-checkpoint semantic trace; debugger sampling uses the host frame
transaction guard so delayed SPC boot cannot expose a half-written checkpoint.

---

## C42 — isolated Fate instrument and octave-zone auditions

**Status:** Passed on 2026-08-24. Round one accepted and locked bass and percussion, rejected the organ
main loop/seam, low marimba, high flute, and low pad, and is preserved in
`audio/fate_s6/auditions/REVIEW_ROUND1.md`. Round two accepted and locked
marimba, rejected the remaining organ seam and both flute upper sources, and
accepted only the pad's low range; its verdict is preserved in
`audio/fate_s6/auditions/REVIEW_ROUND2.md`. Round three hard-rejected all three
repairs after exposing source-loop artifacts and is preserved in
`audio/fate_s6/auditions/REVIEW_ROUND3.md`. Round four's pitch concern and the
corrected TAD octave analysis are preserved in `REVIEW_ROUND4.md`. Round-five
128 KiB production ROM SHA-256 is
`01a9d2c5da64286298e9ddde8aa1b48c19f7ea34f2b9a21e538e4bd8df3d03a0`.
Its three-capture report SHA-256 is
`4c3510572edc65e918d091002fc99ab0f9600457b7585a6eac331452d228dd68`.
The same ROM passes the production TAD gate; its report SHA-256 is
`16b8524b5f1cad453f663c35f2b89c61da532b6591dafcb5cfd4ceeb00fbb5e2`.

**Work:** Reuse the user-authorized, manually reviewed Monkey Island sample
library as raw material for an initial Fate bank. Add explicit low/main/high
sample zones instead of forcing the S-SMP pitch multiplier across strained
octaves. Compile six dry listener-facing songs for organ, marimba, flute,
atmospheric pad, soft bass, and percussion. Generalize the ROM's TAD layout so
the larger common-data pool and songs span two LoROM banks without hard-coded
song offsets. Capture every audition through Nexen's real S-SMP/DSP path.

**Pass:** All six songs compile within audio RAM and produce nonzero stereo
48 kHz DSP captures. Every capture advances exactly 2,400 video frames and ends
with at least 0.5 seconds of verified silence. The review sheet identifies
scale, sustain, seam, deliberately strained-range, velocity, and beat sections
and uses a fixed verdict vocabulary. Instrument approval remains human: the
capture gate proves delivery and test isolation, not timbre or transition
quality. Listener verdicts drive the final program-to-zone map before complete
Fate arrangements are authored.

**Round-two response:** Preserve bass/percussion byte-for-byte. Move organ and
flute to the exact reviewed MI boundaries, replace the organ main source with
the reviewed generic MT-32 organ, remove the floaty marimba-low source, replace
the failed patch-77 flute high zone with a compact Phantasia candidate, and test
the acceptable pad-main source alone across the lower range. The resulting TAD
payload shrinks from 46,102 to 37,128 bytes. All four repair captures pass the
same mechanical checks and await listener verdicts.

**Round-three response:** Lock marimba with bass and percussion. Eliminate the
organ seam by using one reviewed source. Derive flute mid/high sources at 2x/4x
base pitch from the accepted p74-low PCM, and derive a 2x pad-high source from
the accepted p88 PCM. Offline SoX-resampler conversion moves the hard octave
work out of the S-SMP; every loop is closed with its own leading waveform and
aligned to a 16-sample BRR boundary. The smaller 30,750-byte payload also proves
the generated single-bank TAD layout path. Three repair captures pass and await
listener verdicts.

**Round-four response:** Treat round three as a source-loop construction
failure. Discard all accelerated long-loop derivatives. Phase-average 72 organ,
eight flute, and 39 pad source cycles into exact single-period wavetables; emit
separate flute 192/96/48-sample and pad 64/32-sample periods. Every source is
BRR-aligned and uses TAD's loop-safe duplicated-block mode. This intentionally
removes baked-in chorus/modulation so a clean periodic foundation can be judged
before character is reintroduced. Three sparse sustain captures pass mechanical
checks. The listener's interval concern exposed an analysis error rather than an
octave error: TAD uses C4 as middle C. Round five adds a canonical-note,
clock-corrected ±3-cent gate, on which all 16 sustained notes pass within 0.65
cents. It replaces the duplicated-block hack with filter-reset loops, eliminating
BRR predictor-state drift. The listener accepts organ, flute, and pad as usable
sounds while noting their limited texture; `REVIEW_ROUND5.md` preserves the
verdict and closes isolated-bank review.

---

## C43 — zoned ROL conversion and complete Fate sound 17

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`e18efcb6b9cf019fbc8d47c0074d858f6a9bc0a99215bfe47b74b83984b3f107`.
Sound-17 Nexen report SHA-256 is
`9f60623d3bf6c077de0cc7b5ddcefbca86d48c0f071ff9842d6ee3c352097139`;
the retained sound-172 report SHA-256 is
`e5866b8134cabd069aa8fdb9ead20287d07733883c5fb017989ac34e0873cccf`.

**Work:** Close C42 with the listener's usable-but-low-texture verdict. Add a
reusable bounded converter from canonical Fate ROL events to TAD MML: pair notes,
retain dynamics, quantize absolute event time, allocate S-DSP voices, and select
reviewed octave zones by MIDI note. Fail closed when a program has no reviewed
role or a resource requires explicit multi-track iMUSE branch handling. Replace
the sound-172-only runtime special case with a logical-sound-to-TAD-song mapper.

**Pass:** Fate sound 17 converts all 23 notes in its 13.380-second track into a
seven-voice pad/flute arrangement. Its four-note pad bed and flute low/mid seam
use only C42-accepted zones. Real S-SMP/DSP capture maps logical 17 to compiled
song 8, advances exactly 900 video and SAME frames, enters at 4.742 seconds,
ends at 13.658 seconds, and reports no rejected requests. Sound 172 and C1 remain
green. Twenty-five readable Fate sounds still require production arrangements.

---

## C44 — cue-specific register policies and complete Fate sound 154

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`6b5ee39f2e38d0bb19f99fcf47634e0961a094d63e2a5537e9d676443d322ec5`.
Sound-154 Nexen report SHA-256 is
`7b4c78744812b107b1ca6b5975fc3348ad1db02d8a8dcbf5d74feede522c7488`.

**Work:** Extend the bounded converter with explicit per-cue program and note
bands. Use the accepted bass only within its reviewed C1..B3 register, retain
pad/flute octave zoning, and fail closed on every unlisted program or note.
Compile sound 154, map logical `$9A` independently to its generated TAD song ID,
and pin real-DSP entrance/tail timing.

**Pass:** Fate sound 154 converts all 28 notes over 12.317 seconds without voice
loss at its exact eight-voice source peak. Programs 32/36 use bass through B3
and pad above it; programs 50/92 use pad; program 97 uses flute. Logical sound
154 maps to song 9. Fresh S-SMP/DSP capture advances exactly 840 video and SAME
frames, enters at 3.163 seconds, ends at 12.614 seconds, and records no rejected
requests. The strict sound-17, sound-172, and C1 gates remain green. Twenty-four
readable Fate sounds still require production arrangements.

---

## C45 — audited eight-voice reduction and complete Fate sound 83

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`264f68839b56a9486a9e2557842c994f619fbfadd7b6ec849baebcb391fcfcaf`.
Sound-83 Nexen report SHA-256 is
`6436c96170ac8effe8486d0a21d841783eb843a29905fc4661f33f822d43ccc7`.

**Work:** Add opt-in deterministic polyphony reduction for canonical cues above
the eight physical S-DSP voices. Preserve stronger notes, break exact-strength
ties toward the lower register, audit every omission in generated MML, and keep
unlisted cues fail-closed. Convert sound 83 and map logical `$53` independently
to its generated TAD song ID.

**Pass:** Sound 83 accounts for all 30 source notes over 12.317 seconds. Its
only nine-voice interval is 10.908–11.696 seconds; the arrangement retains 29
notes and omits only a velocity-1/CC7-47 G6 doubling an equally quiet retained
G5. The generated audit identifies that exact decision. Logical sound 83 maps
to song 10. Fresh S-SMP/DSP capture advances exactly 840 video and SAME frames,
enters at 3.140 seconds, ends at 12.534 seconds, and records no rejected
requests. Sounds 17/154/172 and C1 remain green. Twenty-three readable Fate
sounds still require production arrangements.

---

## C46 — interval voice virtualization and complete Fate sound 18

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`e6718d46726bdb2d2193767d1138b553f0b01cb90a78bdd12acc7658d2c764e4`.
Sound-18 Nexen report SHA-256 is
`6bd551ab280850d8387582c406b35a04070f7b08b09520d8febffa6a3a51537f`.

**Work:** Upgrade static reduction to interval-based eight-voice virtualization.
Merge simultaneous identical mapped pitches into the stronger foreground note,
duck only explicitly designated background-bed voices during over-capacity
intervals, restore them when capacity returns, and audit every decision. Convert
sound 18 and map logical `$12` independently to its generated TAD song ID.

**Pass:** Sound 18 retains all 25 source notes over 11.128 seconds despite an
eleven-voice source peak. Three identical pad overlaps merge into stronger
program-92 notes; six bounded intervals duck one or two quiet program-50 bed
notes, which resume afterward. The generated MML audits all nine decisions.
Logical sound 18 maps to song 11. Fresh S-SMP/DSP capture advances exactly 780
video and SAME frames, enters at 2.493 seconds, ends at 11.425 seconds, and
records no rejected requests. The listener accepts the capture as sounding
alright. Sounds 17/83/154/172 and C1 remain green.
Twenty-two readable Fate sounds still require production arrangements.

---

## C47 — reviewed program-0 attack role and complete Fate sound 185

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`50bb3b2d7be8407103f6685512b01c9c04234b8763c6ec4a484e145b50b27730`.
Sound-185 Nexen report SHA-256 is
`2b99221a25dc72ac12238d557edbe70b686e14b4f8f14d5004ae6f9a371ee4a5`.

**Work:** Add the listener-accepted marimba as an explicit program-0 attack
role within its reviewed C2..B5 register. Convert sound 185 without reduction,
map logical `$B9` independently to its generated TAD song ID, and fail closed
outside the cue-specific range.

**Pass:** Sound 185 retains all seven notes and dynamics of its D2–A4 chord over
1.315 seconds, using seven physical voices. Logical sound 185 maps to song 12.
Fresh S-SMP/DSP capture advances exactly 120 video and SAME frames, enters at
0.512 seconds, ends at 1.599 seconds, and records no rejected requests. Sounds
17/18/83/154/172 and C1 remain green. Twenty-one readable Fate sounds still
require production arrangements.

---

## C48 — split-register program-0 impacts, Fate sounds 190 and 192

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`f1fab4cb1b5f6dd080a2a918edcac12f9f66b1368df792127fc658c868fb3038`.
Sound-190 and sound-192 Nexen report SHA-256 values are
`839704a7ee7aa7c5fa8a45e24960a3c02ea72d0b13015f60d7058930b296bd61`
and `d269901f68701ccea9568a894350f5be18cab648cdf2df51761d3ed03e4e311c`.

**Work:** Add a shared cue-family policy mapping program-0 C1..B1 impacts to
the accepted bass and C2..B5 attacks to the accepted marimba. Convert sounds
190 and 192 without reduction, map logical `$BE/$C0` independently to generated
TAD song IDs, and fail closed outside the explicit bands.

**Pass:** Sound 190 retains all three notes over 0.906 seconds and maps to song
13; sound 192 retains all four notes over 0.764 seconds and maps to song 14.
Fresh S-SMP/DSP captures advance exactly 90 video and SAME frames apiece. Sound
190 is audible from 0.328–1.192 seconds and sound 192 from 0.393–1.050 seconds,
with no rejected requests. All six earlier production cues and C1 remain green.
Nineteen readable Fate sounds still require production arrangements.

---

## C49 — complete marimba range and compact program-0 cue family

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`88c0264e7ea2a05b38a03c1dc4b5754376efda4134063ad4ea770a16c304af3d`.
Sound 141/201/202/207 report SHA-256 values are
`d2d681cfc9527f1563a170e3db58902b45807c924e55e5f19405111bacf4cea2`,
`5ef5816cab45976a6efc9677c0fb94736f7c9947a5c5aeb09617b28a65f058f0`,
`0fc600f4b3d7c44faa068de0f959631bbc711625144a02a6c8e78ca9ae0bfff7`,
and `d5acf98e07d2d932e313406f64454a32493a759ba71a5896173246f51c95ac3f`.

**Work:** Correct the marimba numeric ceiling to its reviewed and TAD-declared
C2..B5 range. Apply that explicit role to compact program-0 sounds 141, 201,
202, and 207; preserve repeated-note overlaps, map every logical ID separately,
and pin each real-DSP audible window.

**Pass:** Each cue retains both source notes without reduction. Sounds 201/202
preserve their overlapping second attacks as separate voices. Logical sounds
141/201/202/207 map to songs 15/16/17/18. Fresh captures pin audible windows of
2.963–7.134, 0.319–5.576, 0.318–5.576, and 0.319–1.788 seconds respectively,
with exact frame pacing and zero rejected requests. All eight earlier production
cues and C1 remain green. Fifteen readable Fate sounds still require production
arrangements.

---

## C50 — chord-aware virtualization and complete Fate sound 183

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`39e7bcc4957ea241057dda10433c01686fe7bbdc838f34b9e374347af8dedf2e`.
Sound-183 Nexen report SHA-256 is
`41e40471c943070ad4cbce716266c08cf1ef5474881397ea7023402cf299780f`.

**Work:** Extend interval virtualization to dense same-instrument chords. Merge
identical pitches, protect the lowest/highest pitches and every new attack, fill
remaining voices by source strength, and distinguish true restores from
sustains ducked through note end. Encode TAD's minimum key-off duration as an
explicit two-tick cue grid and fail closed if protected attacks alone exceed
eight voices.

**Pass:** Sound 183 represents all 110 source attacks over 17.527 seconds despite
a twelve-voice peak. Fourteen audited decisions comprise ten duck/restore
cycles and four already-attacked sustains yielding through note end. Logical
sound `$B7` maps to song 19. Fresh S-SMP/DSP capture advances exactly 1,140
video and SAME frames, enters at 0.365 seconds, ends at 17.822 seconds, and
records no rejected requests. All twelve earlier production cues and C1 remain
green. Fourteen readable Fate sounds still require production arrangements.

---

## C51 — rapid wide-register Fate effects 91 and 117

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`787c8bf5da4674e98304c6376c98ec1923da1b7273927edbdf415bce077fa544`.
Sound-91 and sound-117 Nexen report SHA-256 values are
`8a49bb0b1bbd13fc57f78cf04dc2a025272609b7696874c834f1463a217a5df1`
and `125108f998790bba08804027633b8c3aef4821f2fd6a5273cec4b1dedfe3426c`.

**Work:** Arrange the shared 34-attack E2..G7 ascending gesture with accepted
bass below C3 and the production-proven Fate tone from C3 through B7. Reuse the
explicit two-tick driver grid for the rapid attacks, retain sound 117's three
additional sustained harmony notes, and fail closed outside those reviewed
registers.

**Pass:** Sounds 91 and 117 represent all 34 and 37 source attacks respectively,
with no omissions, merges, or voice reduction. Logical sounds `$5B/$75` map to
songs 20/21. Fresh real-DSP captures advance exactly 240/360 video and SAME
frames; their audible windows are 2.294–3.011 and 2.295–3.974 seconds, with no
rejected requests. All thirteen earlier production cues and C1 remain green.
Twelve readable Fate sounds still require production arrangements.

---

## C52 — complete long-form Fate sound 78

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`0c2f732bca9345130503788cb3ba4d43c30e189232fdd57bb494ce81fefcebaa`.
Sound-78 Nexen report SHA-256 is
`c0cea87666cf1ea3429b174e41046a6e04af28b46e754c26380326f2455d5a9f`.

**Work:** Map program 73's high lead to the reviewed zoned flute and programs
82/91's low/mid layers to the accepted pad. Preserve every note and dynamic over
the complete 84-second resource, and extend the bounded real-DSP harness beyond
its former 1,200-frame ceiling so the gate observes the actual tail.

**Pass:** Sound 78 represents all 91 source notes with no omission, reduction,
or virtualization; its source peak is six voices. Logical sound `$4E` maps to
song 22. A fresh full-length capture advances exactly 5,280 video and SAME
frames, remains audible from 6.333 through 82.957 seconds, and records no
rejected request. All fifteen earlier production cues and C1 remain green.
Eleven readable Fate sounds still require production arrangements.

---

## C53 — capacity-only identical-pitch sharing and Fate sound 81

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`6dd844df83205f2e2501c93c109bbbef4cdeed90249b6c9fddf29e7753855e5a`.
Sound-81 Nexen report SHA-256 is
`4d551f72664a029d57d896ae26fee3ea9b12c1f6ba34d41e58dce861c051da0b`.

**Work:** Add cue-specific marimba, split bass/pad, and pad mappings for programs
0/32/82/90/92. Resolve over-capacity intervals only by sharing identical mapped
pitches, choose the weakest duplicate needed to reach eight voices, preserve
duplicates everywhere else, and fail closed if distinct pitches still exceed
capacity.

**Pass:** Sound 81 represents all 113 source attacks. Its two source nine-voice
intervals quantize into one 56-millisecond capacity region where the quiet
program-92 G4 shares the stronger program-90 G4; no other note is merged,
reduced, or ducked. Logical sound `$51` maps to song 23. Fresh real-DSP capture
advances exactly 1,500 video and SAME frames, remains audible from 2.777 through
22.320 seconds, and records no rejection. All sixteen earlier production cues
and C1 remain green. Ten readable Fate sounds still require production
arrangements.

---

## C54 — attack-preserving orchestral virtualization and Fate sound 153

**Status:** Passed on 2026-08-24. Production ROM SHA-256 is
`fa4a10c07121757e8dc717814ccee46434f17edc7345128de7471b5d236a73a6`.
Sound-153 Nexen report SHA-256 is
`5f5f7909bfbbb0a8f61a931ae822ce16fa8157e8a0b7ecf800d26e02baf43429`.

**Work:** Map programs 0/32/36/50/92/97 across the existing marimba, bass, pad,
flute, and Fate-tone zones. At capacity, merge only already-sounding identical
pitches; protect every new attack and both register edges, then retain the
strongest interiors. Use an explicit two-tick grid and fail closed if protected
attacks alone exceed eight voices.

**Pass:** Sound 153 represents all 55 source attacks despite a twelve-voice
peak. Its 42 audited decisions comprise 31 sustained-pitch merges, eight
duck/restores, and three sustains yielding through note end. Logical sound
`$99` maps to song 24. Fresh real-DSP capture advances exactly 1,920 video and
SAME frames, remains audible from 3.156 through 28.388 seconds, and records no
rejection. All seventeen earlier production cues and C1 remain green. Nine
readable Fate sounds still require production arrangements.

---

## C55 — long-form dense sustain virtualization and Fate sound 150

**Status:** Reopened on 2026-08-24 after listener rejection. The first result's
84-second static hanging chord is not production audio despite its mechanical
gate pass. The all-cue envelope-audit candidate ROM SHA-256 is
`0d7c7641dc54478e6e7dad01e82bec1df202c38f76255e70d4fa697202b58805`.

**Work:** Map programs 0/33/36/56/92 across reviewed marimba, bass, and pad
roles. Reuse attack-preserving virtualization and the explicit two-tick grid,
retain every source attack over the complete 94.963-second sustain field, and
exercise the real-DSP harness at its 6,000-frame ceiling.

**Reopened finding:** The source contains six notes held to its 94.963-second
cleanup boundary, but no new musical event after 21.903 seconds and a live CC7
fade ending at 18.679 seconds. The old converter snapshotted CC7 only at note-on,
leaving static SNES loops at their initial volume. It now preserves active-note
CC7 as TAD 0..255 fine-volume changes without sample retrigger, while sound 150's
terminal voices use a 256-tick fade ending at 18.680 seconds. A fresh 1,800-frame
capture is audible from 3.668 through 22.197 seconds with exact pacing and no
rejection; report SHA-256 is
`6dcd613ace471406525e21fef965027df7755fea0c0dc996cfb97ac47adf42aa`.

The same raw-event audit covered every production cue and found active-note CC7
only in sounds 18, 83, 150, 154, and 192. All five corrected arrangements pass
fresh exact-ROM S6-TAD captures, and C1 passes 14 frames. Focused listener
acceptance remains required; nine readable Fate sounds remain open.

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
`9600d1e035cd86e0aeecac5a75dd2a1595a9a1ac22cedc27ef90338d8f3687da`.
The two-tick host/SNES trace agrees on semantic state and four complete audio
packets with zero loss. Evidence:
`build/scumm-s5-binding-9600d1e035cd86e0/report.json` (SHA-256
`415b88d8e5dcc683cbc08971db85f8e3acfd77f6ca6e6b9ca91d79da0a7a6ffd`).
The latest demo ROM SHA-256
`966caf1de4e38fddda4c156fb5b30491f4e322d147821fd4663b933a71189fb7`
retained H0/K1 and the SCUMM build retained C1-C32.

**Work:** Implement `ScummV5_Engine_*` using the extracted engine and select it as
`Same_ActiveEngine_*` for a SCUMM ROM build.

**Pass:** host and SNES semantic/service fixtures agree with zero host packet
loss. A game-specific demo may illustrate compatibility but is not gate evidence.

---

## S6 — second SCUMM v5 profile

**Status:** In progress on 2026-08-24 using the
redistributable Fate of Atlantis interactive demo archive SHA-256
`558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`.
The profile and generic raw adapter expose 10 rooms, 74 scripts, 27 readable
sounds, 20 costumes, and three charsets; logical input and a SAME save-state
round trip pass.
Evidence is `build/scumm-s6-fate-preflight/report.json` (SHA-256
`8334ae6cc371d9f9e23b51b8bdb3bf2a247744d22668f2cac3a0c3c92335f95b`).
The host compatibility path passes. Real boot crosses both C9 variable ranges and its
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
requests 250 and 6 at offsets `$0837/$083B`. C29 executes the exact `$D5` in
local script 205 at `$0004`, stores no-hit zero in local 0, takes the canonical
branch, and C30 executes `$F5 findObject` at `$0018`, storing zero in local 0
and variable 108 before yielding at PC `$0025`. C31 executes exact `$2D 0A 4B`
in local script 200 at `$082D`, assigning actor 10 to room 75 without showing
or repositioning it. C32 executes exact `$0E 0A 07 04` at `$0830`, places
actor 10 at object 1031's decoded walk point `(1164,46)`, and shows it. C33
decodes costume 58's initial 7x7 cel, draws 37 opaque pixels, and publishes
hitbox `(1161,43)..(1167,49)`. C34 advances its persistent classic limb cursor
to a distinct second pose with exact logical SHA-256
`0e1972cf93f4fdce4d62abe54f4f2164417b50dfd971eee4be24c6aca041f104`.
C35 scales costume 58 to `(128,192)`, producing 26 pixels with bounds
`(1162,43)..(1166,48)` and exact logical SHA-256
`62db861295d986afacf38eb97e24ce29b99bdc2cb2e4eea3c0a79e29d94d33f2`.
C36 decodes all declared raw-room z-planes. C37 decodes `BOXD` and proves that
room 42 walkbox 10 automatically selects plane 1 at `(193,100)`, occluding all
37 costume-58 pixels and leaving an empty hitbox. C38 decodes every `BOXM` and
implements `$7B/$FB`. C39 adds all `$1E` forms, destination snapping,
shared-edge gates, fixed-point movement, `$56/$D6`, and `$3B/$BB`; complete
in-flight walks resume under save schema 5. The Fate proof traverses room-42
boxes `5→6→8→7→10` and reaches `(200,110)` on frame 27. C40 then decodes every
readable embedded `SOU` resource, streams deterministic PCM, implements
`$7C/$FC`, and resumes sound 172 exactly under save schema 6. C41 adds the full
observed Fate iMUSE branch surface and a real TAD/S-SMP sound-172 rendition.
C42 adds a bank-spanning TAD layout and six isolated real-DSP instrument and
octave-zone auditions based on the authorized MI sample library; the listener
accepts the bank as usable with limited texture. C43 adds reusable zoned ROL
conversion and the complete sound-17 pad/flute cue. C44 adds cue-specific
register policies and the complete sound-154 arrangement. C45 adds audited
eight-voice reduction and the complete sound-83 arrangement. C46 adds interval
voice virtualization and the complete sound-18 arrangement. C47 adds the
complete sound-185 marimba chord. C48 adds the split-register sound-190 and
sound-192 impacts. C49 corrects the full marimba range and adds complete sounds
141/201/202/207. C50 adds chord-aware virtualization and complete sound 183.
C51 adds the rapid wide-register effects 91/117 without dropping an attack.
C52 adds complete 84-second sound 78 and full-length DSP validation. C53 adds
complete sound 81 with capacity-only identical-pitch sharing. C54 adds complete
sound 153 with attack-preserving orchestral virtualization. C55 remains under
focused listener review after sound 150's rejection exposed missing CC7
envelopes. The converter and all five affected production cues are corrected
mechanically; production arrangements for the remaining 9 readable sounds are
the other S6 blocker.

The parallel DOS oracle lane now decodes complete iMUSE `$10` AdLib
instruments and preserves all 30 bytes rather than only the eleven base OPL
fields. Fate sound 154's six patches render through ScummVM's SCUMM iMUSE
driver with Nuked OPL. Its unconditional `$30` jump skips the linear score's
setup silence at runtime; the exact capture and harness are recorded in
`audio/fate_s6/ADLIB_ORACLE.md`. The six definitions also now have isolated
C2..C6 Nuked auditions, locally extracted from the supplied demo without
committing commercial data. Listener acceptance of those files is the immediate
gate. The accepted regions now produce seven multi-cycle BRR zones from five
active patches and replace sound 154's generic TAD roles. The canonical TAD cue
also follows the `$30` jump, preserves 26 attacks and five timbres, fits exactly
at an eight-voice peak, restores the velocity-1 G5/G6 ending through the real
SCUMM AdLib attenuation model, and passes an 840-frame real-DSP capture. Focused A/B
listener acceptance against the Nuked whole-cue oracle remains. This is offline
reference/asset generation: the SNES does not execute Nuked OPL at runtime.

**Work:** Convert and profile a second user-supplied SCUMM v5 title without
editing the opcode core.

**Pass:** boot, room, actor/input, audio, and save fixture succeeds. Any required
game exception is a named profile quirk or narrow adapter, not a generic opcode
change.

This is the gate that earns the phrase “reusable SCUMM v5 engine.”

---

## M1 — backend-neutral music device and fingerprinted instrument bank

**Status:** Passed on 2026-08-24 for the canonical Fate sound-154 lane.

**Work:** Introduce a reusable symbolic sequence model that distinguishes parts,
stable note lifetimes, source channels, and physical voices. Move SCUMM v5
AdLib nonlinear volume/operator behavior into a source-device model. Resolve
complete patch fingerprints and pitch through a schema-validated bank whose
sample hashes, loop geometry, capture calibration, octave bounds, and listener
status are explicit. Route sound 154 through those layers without retuning it.

**Pass:** malformed lifetimes and ambiguous/unreviewed zones fail closed; unit
tests pin source-device response and sample identity; the canonical path retains
26 attacks at an eight-voice peak; regenerated `sound_154.mml` is byte-identical
at SHA-256
`45110f50f2b4d4ff31a922f8eb2c43d886dbba5940dea8dae5ea0b3f035a5a18`;
the unchanged ROM
`67daeb570fefb30b6db540ef0618fdf7daf35ebe74939e94ce93c57ed8a63514`
passes the 840-frame real-DSP sound-154 gate.

## M2 — second-cue generalization and importer seam

**Status:** Passed on 2026-08-24 with copyright-free SCUMM AdLib and raw QTMA
fixtures. The production Fate sound-154 output remains byte-identical.

**Work:** Route a second SCUMM AdLib cue through `SequenceIR`, the same source
device, and a fingerprinted reviewed bank without cue-specific volume math.
Then decode one copyright-free QTMA fixture to the same IR, leaving the TAD
realizer unaware of its source format.

**Pass:** both importers produce independently asserted IR timelines; one shared
device/bank path realizes both; malformed or unsupported semantics fail with
source provenance; no sound number appears in generic music-device code.

The second SCUMM cue carries two attacks and active-note CC7 through the generic
iMUSE importer and fingerprinted-bank AdLib realizer. The 232-byte QTMA fixture
declares melodic/percussion Note Requests, Volume/Pan/Sustain controllers, a
chord and crossing-rest percussion, and ends at tick 600 with peak polyphony 3.
Its SHA-256 is
`1a595217e6ef5e05e3f15c193a92d364243db7c308c179ff48109e1456e2b0c0`;
the committed 13-record trace is exact. Structured errors pin source word/byte
offsets for malformed and unsupported input. Sound 154 remains 26 attacks/eight
voices with MML SHA-256
`45110f50f2b4d4ff31a922f8eb2c43d886dbba5940dea8dae5ea0b3f035a5a18`.

## M3 — deterministic QTMA playback and reference synth

**Status:** Passed on 2026-08-25 with a copyright-free exact-output oracle.

**Work:** Add a source-neutral playback session, sustain-aware note lifetime,
deterministic voice handles, rational tick-to-sample timing, and a deliberately
plain internal reference synthesizer for the M2 QTMA fixture.

**Pass:** the golden trace renders to an exact sample count and WAV hash; sustain
delays only eligible note-offs; completion and explicit stop leave zero active
voices; repeated renders are byte-identical; voice-budget failure identifies
the exact tick and active notes. No MOV parsing or TAD policy enters the
scheduler/backend contract.

The M2 fixture renders 24,000 mono signed-16 frames at 24 kHz with no clipped
samples. PCM SHA-256 is
`0b5d2002c7a3f72069ddc373f6000ef90c29ff8b71de37909bb57eafd7a933a7`;
canonical WAV SHA-256 is
`5555b38dc9c89f9cd6572003ad1cfef3b39d81b0037cb5c5cbb91d77a9fad811`.
The scheduler releases the part-1 percussion normally while part 0 is sustained,
defers only part 0's eligible release, then deterministically reuses voice zero.

## M4 — real Monkey v5 cross-title conversion

**Status:** Passed on 2026-08-25 with user-supplied Ultimate Talkie data and no
committed commercial bytes.

**Work:** Mount the user-supplied Ultimate Talkie `monkey.000`/`.001` without
committing commercial bytes, derive a hash-recorded sound inventory, and select
one complete AdLib/iMUSE cue. Route it through the generic SCUMM importer,
source-device model, instrument-bank resolver, playback scheduler, and one
backend target. Reuse the reviewed Monkey sample library only where exact patch
and pitch coverage is established.

**Pass:** the raw source identities and cue selection are reproducible; the cue
has an exact IR/action trace and repeatable output hash; no Monkey condition is
added to shared music code; missing timbres or ranges fail closed into isolated
audition work; Fate sound 154 and its production ROM remain byte-identical.

The validator mounts `_monkeypacks_backup.zip` in memory. Its archive SHA-256 is
`2012bf139265afc3270bce418ea2d49b92df290ea814cbfbec455e308102edfc`;
the exact `monkey.000` and `.001` member hashes are
`34827cd5664361650c3081dc143e75167d31d80c462d22f2b8c35d45f5c8f74f`
and
`2954d067d56c1190456a911cd7bcc507ad6560365c1a24936115e3d9faa9c62f`.
The 138 sounds classify completely as 97 AdLib cues, 35 24-byte silent stubs,
and six SBL-only effects. The canonical inventory digest is
`d228484c8ab86a8b69fc2187b0ef1506f5ed588174e54f08be8d7ea8892fa0bd`.

Room-78 church `sound.154` has raw SHA-256
`dd5af48a6626fe50a31fe10ef1850a9c178d84ecdd505f937f49ba8afbb0325b`
and one complete AdLib patch with fingerprint
`625b3bfe1a9b2253828cd5c4179a02e2cf18e3aa15d98178d5a3fe597420992b`.
The generic path preserves its pan control and whole-cue iMUSE loop, imports all
197 attacks over MIDI 36..91, and records an eight-voice peak. Its IR, playback
action, and resolved-note digests are respectively
`ae9efce8ebe913269a0f8d9878a7db20aac855c43ce9456a6fc0e65edc1030eb`,
`65d97b64607cddb0e9e72bf33e20d75d3738587b6473e5f5295599265256ef63`,
and
`401ca8eafd2c85d18d91f51fefdb2c4d558afba3ae124cc816bdaea7b18e0b51`.
The 8 kHz integer-reference backend renders 459,072 unclipped frames with WAV
SHA-256
`0f41ec1d04eb7dd0cbd7b867b81c2ec1aa8438db91504b91384ad96bbfce3361`.
The bank reuses the exact manually reviewed MI `mt32_p13_low`/`mt32_p13`
samples at the established MIDI-58 boundary; any different patch or pitch has
no accepted zone.

## M5 — generic sampled-backend song compiler

**Status:** Passed on 2026-08-25 with the real Monkey v5 church cue and a
copyright-free independent compiler fixture.

**Work:** Consume resolved notes, loop metadata, bank zones, and playback
controls to emit one bounded TAD/SNES song without a handwritten cue-number
arrangement. Define explicit policy for pan on a mono/stereo target and retain
the source's eight voices without hidden reduction.

**Pass:** the Monkey church cue compiles from its M4 report inputs, a synthetic
cue proves the emitter contains no SCUMM dependency, real-DSP capture is
nonzero/unclipped and loop-stable, and unsupported controllers or capacity
fail with exact source provenance. Existing Fate MML and ROM hashes remain
unchanged.

`same.music.backends.tad_mml` consumes only `SequenceIR`, resolved sampled
notes, and named TAD instruments. It has no SCUMM, Monkey, Fate, or cue-number
dependency. The backend preserves CC10 through an explicit stereo policy
(`0..127` MIDI to `0..128` TAD pan); an explicit mono policy centers it. CC7 is
already present in resolved-note volume/automation. Any other controller,
missing zone, partial loop, note crossing the loop seam, duplicate identity, or
ninth voice fails with source and tick evidence.

TAD cannot encode a raw one-tick duration. The compiler therefore records its
bounded target adaptation: this cue receives one tick of leading bias, and note
IDs 87 and 150 release one tick early to expand their isolated one-tick rests.
All 197 attacks, pitches, loop duration, and eight physical voices remain. The
target loop is `(2, 7174)`, pan is 63, and generated MML SHA-256 is
`3781ebf57a3cacb4a8f9ffaa835642213b364f240d1595453f03fb75eda410de`.
The appended song-26 TAD binary is 46,267 bytes with SHA-256
`ee4a65af794b92850a4ac79ef6a101674c217faacbd451751eb174938c0e7a8d`.
Commercial-derived MML and the temporary project remain under `build/`.

The special validation ROM SHA-256 is
`aa5524ce8b3d04eeaa9e4931ebfdd7af221f8112c25ee830bb3c223300c8e673`.
A fresh Nexen power-on captures 3,900 video frames and 3,114,871 stereo audio
frames at 48 kHz. Peak is 12,710 with no clipping or rejected TAD request. The
57.376-second nominal loop measures 57.303875 seconds at the configured 32,040
Hz SPC clock, within 0.5 ms of the 57.304375-second clock-corrected prediction.
An early half-second window and its in-capture repeat correlate at 0.998933;
the repeated window remains strongly nonzero. Report SHA-256 is
`73cf93c715691beae8cff7d3467403d0da720ddae9e6633d775542bb51833255`.

## M6 — profile-driven compiled music catalog

**Status:** Passed on 2026-08-25 with exact Fate-demo and Monkey-v5 source
archives, generated SNES tables, semantic save/load, and fresh real-DSP runs.

**Work:** Replace the SNES audio backend's hard-coded logical-sound switch with
a generated, schema-validated catalog that binds stable music resource
identity, source hash, compiled song ID, duration, and loop metadata. Feed both
one Fate cue and the M5 Monkey cue through it without changing the audio
service or engine core.

**Pass:** catalog corruption, duplicate identities, stale source hashes, and
missing compiled songs fail closed; the generic backend contains no game or cue
names; semantic play/stop and saved logical playhead use catalog identity; both
titles reach their existing real-DSP hashes or explicitly versioned new hashes.

`same_compiled_music_catalog_v1` binds logical ID, stable source resource and
SHA-256, compiled song name and ID, time scale, duration, and optional loop.
The decoder rejects malformed data, repeated logical/source/compiled identities,
changed source bytes, missing compiled songs, and renumbered compiler output.
The SNES generator emits a bounded two-byte lookup table; the platform backend
contains no title or cue names. The normalized audio ABI and SCUMM engine core
are unchanged.

The 19-entry Fate and one-entry Monkey catalog SHA-256 values are
`809a3346c1db8113033119315f5bc1beebb7cad9fafebd3be3760f6d70ab23fc`
and `0859072807c14312901d6b4e60733ffb8e6f15fec57a6b046b9f05be3b0e8792`.
Both supplied archives validate every cataloged source hash against their real
raw-v5 providers and both compiled enum files. The cross-title report SHA-256
is `1756320cb2ac4f428a451d07eb1f38d4fe3e0e18ad647cc4db5db17544c0495a`.

Fate ROM `147c150c08468807e7acefb4c72f0164f2fd907e8adefdae5c6647b82a0ad04a`
retains C32 and sounds 172/154. Monkey ROM
`b6d39664487f700a93a6e13ceace0a37be7c8895cf52e15760f51c8d61cc1c43`
receives logical sound 154—not direct song 26—and resolves it through its
generated catalog. Its fresh 3,900-frame capture is unclipped and loop-stable at
0.998932 correlation; report SHA-256 is
`b039a969288a7281409a5bdc201f426bd86f88c3aa18b811700c42787997d55e`.

## M7 — declarative multi-song compilation graph

**Status:** Passed on 2026-08-25 with two regenerated Fate cues, Monkey church,
transaction/invalidation tests, byte-identical M6 ROMs, and fresh DSP captures.

**Work:** Replace per-cue build-script assembly with one profile-owned music
build graph. The graph selects importer, source-device model, reviewed bank,
target policy, and catalog identity for each rendition, then emits the TAD
project, catalog, dependency manifest, and provenance report in one bounded
transaction. Prove it with at least two Fate cues and Monkey church.

**Pass:** one command regenerates byte-identical MML/project/catalog outputs;
changed sources, banks, policies, compiler identities, or incomplete outputs
invalidate the graph; commercial-derived intermediates remain under `build/`;
the generic graph runner contains no game or cue names; generated Fate and
Monkey ROMs retain their M6 real-DSP evidence.

`same_music_build_graph_v1` is profile-owned and names importer, source device,
reviewed bank, target policy, expected MML, catalog identity, and target project.
The source-neutral runner stages every output and replaces the destination only
after MML hashes, TAD enums, project, binary, catalog, dependency manifest, and
report all exist. Unit coverage proves deterministic repeat builds, stale
source/bank/compiler rejection, artifact tamper rejection, and preservation of
the previous output after a failed finalizer.

Fate sounds 83 and 154 regenerate to SHA-256
`553a79f64cd171c74f8931c5adade7b7f3070334669a7981f66ef27f13d2a942`
and `45110f50f2b4d4ff31a922f8eb2c43d886dbba5940dea8dae5ea0b3f035a5a18`.
Monkey church regenerates to
`3781ebf57a3cacb4a8f9ffaa835642213b364f240d1595453f03fb75eda410de`.
The resulting ROM hashes exactly match M6. Fresh real-DSP report hashes for
Fate 83, Fate 154, and Monkey are
`84aabd1980d77ec0b8a7ee4f064cfdc9fc3ec086f0a0ab67c7e5bb783a66c025`,
`508517c781a5668b5f2d12cb042913af736d55db46d47c22a7564aed83869c34`,
and `592034cbc941167d7470154b1dc2a29c3d7df13e0d0f53ec49aa8ebe46effd01`.

## M8 — complete Fate graph migration

**Status:** Passed on 2026-08-25 with all 19 production entries accounted for,
repeatable complete-project output, exact accepted ROM identity, and four fresh
representative DSP captures.

**Work:** Move the remaining 17 Fate production catalog entries into the
declarative graph. Add explicit import modes for the short hand-authored cue and
the legacy sound-17 arrangement, and remove production dependence on committed
per-cue project assembly without changing listener-approved bytes.

**Pass:** all 19 catalog entries are graph-produced or explicitly declared as
reviewed immutable inputs; a clean graph build emits the complete accepted Fate
TAD image; every source, arrangement, and bank identity fails closed; selected
short, dense, CC7-automated, and virtualized cues retain their real-DSP gates.

The exact audit classifies ROL sounds 18, 83, 150, and 192 plus canonical AdLib
sound 154 as byte-reproducible. Fourteen listener-approved legacy arrangements
are explicit `reviewed_immutable_mml_v1` nodes, including the short hand-authored
sound 172 and legacy-dynamics sound 17. They are not silently rewritten by the
newer converter. Every node still validates the exact raw sound SHA-256 before
rendering or importing its reviewed arrangement.

Graph SHA-256 is
`9843346be7ede3bdd0328ac955f58dbbdd00def7a0d9fd1b7578b18e54637fbe`.
M9 subsequently versions only the graph's profile-owner field; the arrangements
and compiled bytes remain unchanged.
All 19 MML outputs feed one transaction-local project; its repeated TAD SHA-256
is `895dbaafb3479dac66d68a8125f7d57778333d7398439694993c36e9760bf44c`.
The ROM remains exactly
`147c150c08468807e7acefb4c72f0164f2fd907e8adefdae5c6647b82a0ad04a`.
Fresh DSP gates pass sounds 172, 18, 153, and 150, covering short immutable,
virtualized, dense, and CC7/terminal-fade behavior respectively.

## M9 — profile-to-ROM music build handoff

**Status:** Passed on 2026-08-25 for Fate and Monkey with exact ROM identities,
verified cache reuse, crossed-bundle rejection, and fresh real-DSP captures.

**Work:** Make the profile's `music.build_graph` the direct SNES build input.
Resolve the title adapter, archive location, generated TAD directory, and emitted
catalog through one build command instead of manually pairing
`SAME_TAD_PREBUILT_DIR` and `SAME_MUSIC_CATALOG`. Keep source archives external
and make cached output validity depend on the graph manifest.

**Pass:** one profile-oriented command builds Fate and Monkey ROMs from their
graphs; a stale or mismatched graph/catalog/TAD set cannot be paired; normal
non-graph builds remain available; no title names enter the generic SNES build
backend; both ROM and representative DSP identities remain exact.

`tools/build_profile_music_rom.py` takes one profile plus its external source
archive. It resolves the profile's `MBGR` resource, requires graph profile ID to
equal game ID, compiles with the engine-family adapter, embeds the profile hash
in the transaction, verifies catalog names/IDs against TAD enums, then invokes
the unchanged SNES build with that bundle's own catalog and binary. `--reuse`
repeats all checks and needs no source archive.

Fate profile/graph SHA-256 values are
`d824c9b7aa06db8acbd383c07227d52aad16af23eaba6b1687686066b2551561`
and `4eb320c36ef44e1eb1737405876845287422d4eb72a72d824a67e3c276a323a8`;
Monkey values are
`7cd28cc851b70cd25077561e21b7c6e19a674ab4a2632f2a6ae8957440fa563a`
and `9bf3a52d952c3e4e1631697d7d18ea95a1055a1dfd2e651de2659cc1371470b8`.
The resulting ROMs remain
`147c150c08468807e7acefb4c72f0164f2fd907e8adefdae5c6647b82a0ad04a`
and `b6d39664487f700a93a6e13ceace0a37be7c8895cf52e15760f51c8d61cc1c43`.
A deliberately crossed catalog is rejected as stale before assembly. Fresh
Fate-154 and Monkey-loop DSP reports pass.

## M10 — second engine-family music graph adapter

**Status:** Passed on 2026-08-25 with a repository-owned QTMA score, generated
instrument bank, exact bundle reuse, and unchanged Fate/Monkey ROM identities.

**Work:** Remove the profile orchestrator's last SCUMM-only adapter registration
by adding an engine-neutral adapter registry and a copyright-free second
consumer. Use the existing QTMA conformance score or another repository-owned
sequence to build a small TAD catalog and ROM through the same profile command.

**Pass:** the orchestrator imports no SCUMM adapter directly; adapter selection
is registered by engine/source family; a non-SCUMM profile builds and reuses a
verified bundle; malformed or mismatched adapter selection fails before output;
Fate and Monkey ROM identities remain exact.

`MusicBuildGraph.adapter` now selects a registration by the exact pair
`(profile.engine_id, graph.adapter)`. The profile orchestrator knows only the
registry contract. SCUMM archive and QTMA fixture construction live behind
separate registrations; an unregistered cross-family pair fails before graph
compilation or ROM output.

The `same-qtma-music-conformance` profile decodes the checked-in M2 fixture,
realizes its volume/pan/note lifetimes, generates two deterministic integer
waveform instruments, compiles one TAD catalog, and assembles the normal demo
ROM. Its profile, graph, TAD, and ROM SHA-256 values are
`3bf3cc7b28c8d653c60188ce449ff6adeabd3e04f36a9a8a7211ff01e6367fc7`,
`b622d815191cd2039d22b0f5fa3f9de1d43222c7f95ce30858f5b84be4ce9be9`,
`8abae1aef2f32568e17f5ddbdb420b4566b980b9d68b74dfe3e5e8d1ede49a77`,
and `c12f028ee17c81c4e81c46fc9209a78972bf6619341af727a8a579a9c7335f92`.
A verified `--reuse` build reproduces that ROM exactly.

Adding the explicit adapter field versions the Fate and Monkey graph identities
to `efbe8c2ff9c27899a459962a426a52841b7cd3d4ac6a933efcc12ec69c298487`
and `7b529f7d1f6c374b1c7ad0ac63c0a5787d09a99728790a0d9b8214f7f39e85a3`.
Their TAD and ROM bytes remain exact.
Fresh Fate-154 and Monkey-loop real-DSP report SHA-256 values are
`fe21816ec12440078d82db95ece4443bc9f65077710d0b47f89d613b8aa7fa4b`
and `0ecb6fd520db29d250c5b68322a9faf6b25251490b6a1c169fc7b9d69ab472ec`.

## M11 — non-SCUMM runtime music consumer

**Status:** Passed on 2026-08-25 with an opt-in QTMA SNES personality, exact
generic service trace, bounded completion state, and real-S-DSP audio evidence.

**Work:** Make the QTMA conformance ROM request its compiled song through the
engine-neutral runtime audio service, without importing SCUMM playback policy.
Add a real-S-DSP capture and exact start/stop/status evidence.

**Pass:** the repository-owned profile boots and audibly plays the QTMA score;
catalog lookup and TAD commands use the generic service contract; stop and
completion status are bounded and exact; SCUMM ROM/DSP identities remain exact.

The dedicated `qtma_conformance` personality is selected only by the M11
profile. It contains no TAD symbol, S-SMP port access, or SCUMM policy. At
semantic frame 120 it emits `MUSIC_PLAY(logical_id=1)` from the engine endpoint
to SPC; at frame 423 it retains COMPLETE and emits `MUSIC_STOP`. The backend
trace is exactly those two required packets, catalog lookup selects compiled
song 1, no request is rejected, and TAD returns to its loaded blank song.

Runtime-profile, graph, TAD, and ROM SHA-256 values are
`b38f5ff5f6565f13430bd529a90bbac43e30d367d709cf0f55268b2fdbb563ae`,
`b622d815191cd2039d22b0f5fa3f9de1d43222c7f95ce30858f5b84be4ce9be9`,
`8abae1aef2f32568e17f5ddbdb420b4566b980b9d68b74dfe3e5e8d1ede49a77`,
and `22cf9b2fd5cee700d98b1f50729a5728ac72a3f1661e5c24a607628b5f1d3c17`.
The final 48 kHz stereo DSP capture has peak 16283, first/last audible times
2.373 and 5.017 seconds, and no clipping. Its gate report SHA-256 is
`d77cab98c127ab31da56788b59cd0f6972f834ce7da2be56291230802af00404`.
Opt-in selection preserves the M10 demo, Fate, and Monkey ROMs exactly.
Fresh Fate-154 and Monkey-loop DSP reports pass with SHA-256 values
`96deae99d780514de41ee78ef6d1c0040dc00ad736618a0a993c6a36e0f04fec`
and `f779f8d1d3222fb980111dd6204067a6da78256d6609a40f768e33f00d36ca4e`.

## M12 — generic compiled-music lifecycle responses

**Status:** Passed on 2026-08-25 with generated lifecycle metadata, an opt-in
runtime coordinator, response-driven QTMA state, and real-S-DSP evidence.

**Work:** Move score-duration/completion knowledge out of the synthetic engine.
Generate bounded non-looping duration metadata with the catalog, track pending,
playing, completed, and stopped states in a generic coordinator, and return
lifecycle responses through the engine service seam.

**Pass:** the QTMA consumer reacts to backend responses rather than a hardcoded
completion frame; play, natural completion, explicit stop, invalid identity, and
looping/no-auto-complete cases are exact; no engine reads TAD state or ports;
Fate and Monkey DSP behavior remains accepted.

The normal catalog mapping remains byte-stable; a separate generated lifecycle
table supplies duration and loop policy only to personalities that opt into the
coordinator. The QTMA consumer requests logical entry 1 at frame 120, receives
READY at frame 135 and reacts at 136, then receives natural STOPPED at frame 423
and reacts at 424. The exact backend trace remains one play and one stop packet.
Host conformance also fixes explicit STOPPED, invalid-id FAILED, and looping
no-auto-complete behavior.

Profile, graph, TAD, and M12 ROM SHA-256 values are
`b38f5ff5f6565f13430bd529a90bbac43e30d367d709cf0f55268b2fdbb563ae`,
`b622d815191cd2039d22b0f5fa3f9de1d43222c7f95ce30858f5b84be4ce9be9`,
`8abae1aef2f32568e17f5ddbdb420b4566b980b9d68b74dfe3e5e8d1ede49a77`,
and `e19cd796323df3d85862fb4fa5f6610bb6754be1e9596c5a53608c79a2ec7b50`.
The real-emulator report SHA-256 is
`03ad5edceb90d18f0dcf776095e0c209832b283817213fa3a81cb381ec6e9b3b`.
Fate and Monkey ROM identities remain
`147c150c08468807e7acefb4c72f0164f2fd907e8adefdae5c6647b82a0ad04a`
and `b6d39664487f700a93a6e13ceace0a37be7c8895cf52e15760f51c8d61cc1c43`;
fresh representative DSP report SHA-256 values are
`7acaeef9a8e3e176a2049d4a01239d14319d7ab0d7a0568a1e04cbd84a314792`
and `f19e441379fb62a1a5c2210a239d444845be4893d5935c22bb3767b99e9f7da5`.

## M13 — QuickTime MOV `musi` extraction adapter

**Status:** Passed on 2026-08-25 with strict atom/sample-table validation,
split-sample reconstruction, graph-registry selection, deterministic builds,
and real-S-DSP lifecycle playback.

**Work:** Add a strict container adapter that inventories and extracts QuickTime
Music Architecture `musi` payloads into the existing QTMA event importer without
teaching the importer about MOV atoms or changing the canonical music IR.

**Pass:** copyright-free fixtures prove bounded atom traversal, exact payload
identity, malformed/truncated rejection, graph-registry selection, deterministic
bundle reuse, and audible runtime playback through the M12 lifecycle seam.

The self-contained reader handles normal and extended atom sizes, unknown atom
skipping, `musi` descriptions with zero flags, `stts/stsc/stsz`, and either
32-bit `stco` or 64-bit `co64`. Every sample must resolve wholly inside `mdat`.
The fixture places 184 bytes of NoteRequests in the sample description, then
splits 48 bytes of score events into 28- and 20-byte samples. Their concatenated
output is exactly the M2 event stream; the existing QTMA decoder remains unaware
of MOV atoms.

Raw movie, graph, profile, TAD, and ROM SHA-256 values are
`feb16d388acb55624f53b2dec2e8d76393ce1b5381b1f3d8880e23c74fe78ae1`,
`5e7d934680fc5abb34871371bfc4b5e9acac93c37ea1ae2393f8dd4bf3ce6571`,
`14fe551dfed95486f42d1c5c61c9c46ad615de2d927cbf9838794c1d36e834e9`,
`8abae1aef2f32568e17f5ddbdb420b4566b980b9d68b74dfe3e5e8d1ede49a77`,
and `e19cd796323df3d85862fb4fa5f6610bb6754be1e9596c5a53608c79a2ec7b50`.
Fresh/reuse M13 outputs are identical, and its TAD/ROM bytes equal M12. The
current real-DSP report SHA-256 is
`78722cc703d9b56d82cb86017a7274b167de0bbbcb76cc3e87508aa0c1286d26`.
Fresh Fate-154 and Monkey-loop M14 regression report SHA-256 values are
`99d9c2e7ddc4e311a9158183a566eca84ea6d85d6206434689b0f4fc4fc69818`
and `34de15b387c1baa963740c654b4e2601af86d2bdd021efff95a9ac123adb586d`.

## M14 — rational source-time normalization

**Status:** Passed on 2026-08-25 with explicit exact/nearest policy, preserved
source timing provenance, deterministic 600→125 conversion, and real-S-DSP
runtime evidence.

**Work:** Convert arbitrary positive source time scales, especially the common
QuickTime scale 600, into backend timing with absolute rational arithmetic and
an explicit bounded quantization policy. Preserve source timestamps in
provenance and keep the QTMA decoder and TAD backend format-neutral.

**Pass:** fixtures at 125, 600, and a non-divisible scale produce bounded exact
duration/error evidence with no cumulative drift; simultaneous ordering and
note lifetimes remain stable; graph policy selects the conversion explicitly;
fresh/reuse ROMs and M13 compatibility evidence remain exact.

Normalization maps absolute positions, never successively rounded deltas.
`exact` rejects the first fractional target position; `nearest_absolute` rounds
half up, retains same-time ordering, reports maximum error as an exact rational,
and rejects collapsed notes or loops. The 600 Hz fixture maps source positions
to backend ticks `0,31,52,63,94,125`, ends exactly at 125, and has maximum error
`300/600` target ticks. A scale-7 fixture independently proves the final absolute
duration does not drift.

Graph, profile, TAD, catalog, ROM, and real-DSP report SHA-256 values are
`8729f155b9313c3b0226a39ab867a9813156ee9f1588ddc346a77aae85907587`,
`f987c3745d5e6c3feafa135afd2449cd980a9e8aace48d0262156b7386a245aa`,
`b9552071d7124d738f11b2b3a7ef1823a7eb0442c2915fa43971cfcbf2ced939`,
`581127076eb0f8dac9be0a3dbd4415158e6fed33d083eda0c9903440df52afcb`,
`c1ed252514aeacd9863963477407f01f9676c662f6aa05bec00f6ba195474c59`,
and `73a8ef7a68dc942f2c3c1e38e8e9b8f605b5d51519e26a7e937d4d15601ba198`.
Fresh and reused M14 ROMs match. The lifecycle reaches PLAYING at 135,
COMPLETED at 195, and engine COMPLETE at 196; audio ends at 3.140 seconds.
M13 retains its accepted TAD and ROM identities exactly.

## M15 — segmented QTMA provenance

**Status:** Passed on 2026-08-25 with a generic fail-closed segment resolver,
exact `stsd`/`mdat` attribution, normalized timing retention, deterministic
builds, and real-S-DSP compatibility evidence.

**Work:** Preserve track, sample-description, media-sample, absolute file byte,
and original event-word identity across description/sample concatenation without
teaching the QTMA decoder about MOV atoms. Introduce a generic segmented byte
source/provenance resolver at the importer boundary.

**Pass:** description events and two media samples receive exact independent
provenance; an event at each boundary is attributed correctly; malformed segment
coverage and event framing fail closed; normalized M14 events retain both sample
identity and original 600 Hz ticks; M13/M14 artifacts remain byte-exact.

`SegmentedByteSource` accepts only ordered, contiguous, nonoverlapping physical
coverage and resolves a complete framed item to one segment. The QTMA decoder
uses that generic contract and rejects an event spanning a boundary; it contains
no MOV atom or sample-table policy. The MOV adapter supplies sample-description
1 at physical event byte 232, media sample 0 at file byte 44/logical byte 184,
and sample 1 at file byte 72/logical byte 212. NoteRequests retain physical
bytes 232 and 324. The first emitted sample-1 event retains word 54/file byte 76;
after M14 normalization it also retains source tick 300 at scale 600.

Fresh/reused M13 and M14 ROM identities remain
`e19cd796323df3d85862fb4fa5f6610bb6754be1e9596c5a53608c79a2ec7b50`
and `c1ed252514aeacd9863963477407f01f9676c662f6aa05bec00f6ba195474c59`.
M15 M13/M14 runtime report SHA-256 values are
`0f9a6501a012157f6e5a87fd683074580986695b02d82bd0c39c496a8682aba6`
and `e54f458a23e0e253d921d4dc2fd7e9c078596ccbd822be05dc5b849f0da2aa07`.
Fate and Monkey remain at accepted ROM identities
`147c150c08468807e7acefb4c72f0164f2fd907e8adefdae5c6647b82a0ad04a`
and `b6d39664487f700a93a6e13ceace0a37be7c8895cf52e15760f51c8d61cc1c43`
and pass fresh representative DSP gates.

## M16 — canonical conversion-audit manifest

**Status:** Passed on 2026-08-25 with canonical imported/normalized IR,
timing-error and realization evidence, graph-declared hashes, transactional
verification, and byte-exact runtime outputs.

**Work:** Serialize the canonical imported sequence, part/event provenance,
normalization evidence, and resolved realization identities as a deterministic
per-rendition graph artifact. Bind its SHA-256 into dependency and build reports
without making catalogs or runtime consumers source-aware.

**Pass:** M13 and M14 manifests attribute every part and scheduled event to an
exact source span and contain exact timing-error evidence; fresh/reuse builds
verify the manifest instead of trusting cached bytes; corrupt or omitted audit
artifacts fail closed; MML, TAD, catalog, ROM, and DSP identities remain exact.

The canonical document is sequencer-owned, not QTMA-owned. It records all parts,
instrument requests, events, note lifetimes, controls, markers, ordering,
provenance, timing scales, loops, and diagnostics for both imported and
normalized `SequenceIR` values. Exact rational normalization evidence and the
resolved sampled-note zone identities form separate sections.

M13/M14 audit SHA-256 values are
`d5515a65442e7c70d8137546b401a0ac187df59dc0b45ab920dbf765340bd37e`
and `146b6e9e8548e5d40a5a74df321ef339beeb045a1377e5f8b2da0d48ad97435b`.
Their TAD and ROM identities remain exact. M16 runtime report SHA-256 values are
`05bb8227c7e5b6a1cb3fde7b82e8c4a3c65593c4f5d2b122de686dff2d1f9faa`
and `ec384acc596dd92ec7a4368f72a21681ce167030fceeb2be23e54abdb006c5b6`.

## M17 — canonical IR interchange and replay

**Status:** Passed on 2026-08-25 with strict typed decoding, invariant and
normalization revalidation, importer-free realization, corruption rejection,
and byte-exact build/runtime evidence.

**Work:** Strictly decode the normalized canonical IR as a build input and feed
it directly into realization. This turns the intermediate representation into
a reusable boundary rather than a one-way diagnostic dump.

**Pass:** decoded M13/M14 IR is structurally equal to the in-memory normalized
sequence and compiles to identical MML; schema, ordering, provenance, note
lifetime, and identity corruption fail before realization; replay requires no
MOV or QTMA importer; TAD, catalog, ROM, and DSP identities remain exact.

The decoder accepts exact fields only and reconstructs model objects rather than
passing JSON dictionaries downstream. `SequenceIR` therefore rechecks sorted
unique parts, event ordering, source-order uniqueness, bounded values, note
lifetimes, loop bounds, and part references. Audit decoding recomputes rational
normalization from imported IR and compares the complete normalized sequence and
all error numerators/denominators.

M13 and M14 replay to their declared MML SHA-256 values while both source
importer entry points are forced to raise. Recorded sampled-note identities must
equal realization regenerated from normalized IR. Audit, TAD, catalog, and ROM
identities remain exact. M17 runtime report SHA-256 values are
`f9bf20d5077d826d3fe02a24962aefd962db004559beda0904a76d5bd8a371c4`
and `4e0c99a589669001461219ef3ee777db2d7d79b611f300ebc24159f55d04ef50`.

## M18 — deterministic sequencer checkpoints

**Status:** Passed on 2026-08-25 with separate warm and cold contracts,
transactional identity validation, and a destructive fresh-instance fork
oracle.

**Work:** `PlaybackCheckpoint` records a next-unconsumed event cursor, exact
integer rational-clock remainder, finite-loop iteration, controller/sustain
state, ordered deferred releases, stable note-instance/voice-generation and
allocator ownership, retired stolen notes, and pause/stop/completion state.

Warm restore is restricted to the originating live session/backend ownership
token. It changes only sequencer memory and emits no backend advance, note-on,
note-off, instrument, controller, or stop command. Cold state is canonical JSON
under a SHA-256 integrity envelope and is bound to schema version, canonical `SequenceIR` SHA-256,
realized sample-zone/catalog SHA-256, engine/profile identity, rational timing
algorithm, sample rate, source time scale, voice limit/policy, and loop count.
Decode and complete validation precede mutation; a cold target must be fresh.
MOV extraction and QTMA event decoding are patched to fail during the restore
proof and remain unreachable.

**Pass:** for each checkpoint the oracle runs A continuously, serializes B,
destroys B, restores into a fresh instance, then compares every subsequent tick
through completion: ordered actions and backend commands, cursor, tick/sample
and remainder, loop state, controllers, sustain/deferred order, allocator
decisions, active note and voice-generation identities, and final traces. Cases
cover before/during/after same-timestamp groups, a nonzero remainder, both sides
of a loop reset, sustained deferred releases, the event before deterministic
voice stealing, overlapping same-pitch notes, note-off groups, pause, explicit
stop, end-of-sequence, and repeated restoration of identical state.

Cold restore deliberately preserves **logical ownership only**. It does not
claim sample-continuous audio restoration: the schema has no backend sample
cursor, envelope phase, pitch/oscillator phase, backend voice-generation proof,
or pending-command queue. A backend snapshot carrying and validating all of
that state would be required for exact audible continuation. The deterministic
policy here is that restored stable voice handles receive the same subsequent
sequencer commands without synthesizing reconstruction commands at restore.
M18 runtime report SHA-256 values are
`7fc1113e13ed8e1b45de6524c60a8828f29f81aa51fca135d70a468a3ae9dc9f`
and `1aeaaa3e135569ce35a2021679a8920745ac42d13b252b6d14dc893ffac6f8ff`;
the accepted M13/M14 ROM identities remain exact.

## M19 — normal-path Monkey church playback

**Status:** Passed on 2026-08-25 in one fresh Nexen S-SMP/DSP lifecycle for
ROM `78a71ee35f2658da62a25958ad76ff6ed6036024793193ff04ab9ed27d91fc05`.
Evidence: `build/scumm-m19-monkey-78a71ee35f2658da/report.json` (SHA-256
`8c54e88c5cfd0058a0ad739754f268193de65bf4d361ba46022230ac61d7f8ee`).

**Work:** Execute a copyright-free SCUMM v5 script through the real SNES
dispatcher. It issues `$02 startMusic(154)`, queries `$7C isSoundRunning`,
issues `$20 stopMusic`, queries stopped status, then restarts and leaves the
cue alive. Logical sound 154 maps through the profile catalog to the existing
Monkey church TAD song 26. The validator may select the script fixture but may
not write the debugger-facing logical sound request.

The narrow integration repair adds `$7C/$FC` to the SNES dispatcher and keeps
logical music ownership in SCUMM engine state after required packet acceptance.
No compiled song id, catalog table, TAD lifecycle byte, or S-SMP port becomes
engine-visible. Engine boot also clears the pre-existing debugger hold byte so
fresh WRAM cannot freeze the semantic frame counter.

**Pass:** the exact normalized packet trace is play 154, stop, play 154, all
from endpoint ENGINE to SPC with no packet loss. Status results are `1,0,1` at
post-service program positions; TAD reaches blank song zero after stop and song
26 after restart. The probe request remains zero for the complete run. A
3,900-frame post-restart DSP capture is audible and unclipped, preserves exact
video/NMI pacing, and repeats after 57.303875 seconds with 0.998934 correlation.
No new cue, source-format behavior, hook, transition, or save-state policy is
part of this gate.

## M20 — compiled-music deterministic cue restart on cold SCUMM load

**Status:** Passed on 2026-08-25 across eleven fresh Nexen processes for ROM
`9349a24ca2df99bd374edf5cd7ef1d312b6d0b729ff3321a45f0ef6320015445`.
Evidence: `build/scumm-m20-save-9349a24ca2df99bd/report.json` (SHA-256
`afc7fbdc9efa6884d1db8e8c07fcac3523f4dedfe95cf4dfba2062edc90a8f0b`).

**Work:** Add one battery-backed 2 KiB SRAM slot behind the normal SAME save
service. The record reuses the `SAMESAV` envelope version, engine/game/schema,
fixed length, and payload CRC32 model. Its versioned compiled-music subrecord
stores policy id 1 (deterministic cue restart), logical sound/running state,
profile catalog SHA-256, source-resource SHA-256, and an advisory logical frame
position. Complete envelope and audio-identity validation precedes mutation.

Cold restore emits one engine-originated normal audio stop packet and, only for
a running record, one play-154 packet. The backend serializes the blank-song
transfer and compiled-song transfer without changing TAD or adding seek. Song
26 therefore restarts at its compiled beginning. The advisory position is not
honored; APURAM, DSP state, voices, BRR cursors, envelopes, echo, TAD pointers,
and pending SPC commands are not serialized.

**Pass:** independent midpoint and pre-loop saves persist through process
destruction and fresh emulator launch without savestates. Both restore traces
are exactly stop then play 154, reach TAD song 26 with zero rejection, report
running through `$7C`, and correlate above 0.99 with the accepted direct-start
audible prefix. A stopped record restores with one stop and no play. Corrupt,
wrong-engine, wrong-game, wrong-schema, and CRC-valid wrong-catalog records are
rejected transactionally while an already running cue retains its exact packet
trace, logical owner, and TAD lifecycle state. M19's accepted ROM remains exact.

---

## M21 — Fate room-49 sound-80 hook-14 compiled route

**Status:** Fully accepted on 2026-08-25, including Chad's instrument/timbre
review.

**Pass:** a bounded synthetic command fixture executes encoded start 80, flush,
hook 14, flush through the real SNES `$4C` dispatcher. It is not an authentic
room-entry trace. The profile catalog resolves default song 26 and hook song 27 by
logical/route key; the default never reaches ready/playing ownership before
the hook supersedes it. Stop/start/replay proves one-shot lifetime, and `$7C`
reports `[running, stopped, running, running]`. Fresh-process SRAM loads restart
the saved default or hook arrangement and reject a CRC-valid wrong route
identity transactionally. Route excerpts and six isolated program captures are
unclipped and distinct; only Chad can close the pending timbre gate.

Evidence: `build/scumm-m21-fate-route-b16fcb68583506d0/report.json` and
`build/fate-m21-auditions-b16fcb68583506d0/REVIEW.md`.

---

## M22 — Fate sound-80 delayed hook-8 section transition

**Status:** Fully accepted on 2026-08-26 for ROM
`de6e257897a8e150a85f78b0dcf1ea49ef80b0a49d9f359263e843f819f9b332`;
Chad accepted the newly reached programs 50-low, 97, and 107.

**Work:** A bounded synthetic dispatcher fixture starts sound 80, selects hook
14, and later issues the exact encoded class-0 hook-8 form. It is not an
authentic room-entry trace. The command arms one cue-generation-owned pending
decision and does not replace the song. At the audited track-3 tick-68160 decision, a bounded TAD bytecode opcode
selects either the no-hook continuation or eight precompiled hook-8 channel
subroutines and emits token 1 to the SNES. The generic SCUMM handler and audio
service contain no Fate, room, sound-80, hook-8, or song-27 policy constants.

**Pass:** hook/control DSP is equivalent before the boundary and decisively
different afterward; boundary notification count is exactly one and SCUMM
consumes it one engine frame later. TAD remains ready/playing song 27, `$7C`
never reports stopped, and no packet is lost or rejected. Stop/restart invalidates
old generation ownership. The v3 SRAM record transactionally binds route,
section-plan, catalog, source, and instrument-bank identities. Armed, consumed,
and default states cold-restart from the cue beginning and eventually reproduce
their saved route plan; playback position remains advisory and ignored.

The exact lifetime sequence additionally proves consume, stop, plain default
song 26, stop, and a second independent room-49/room-63 consumption with `$7C`
results `1,0,1,0,1`, arm/consume counts `2/2`, and no stale notification.

Evidence: `build/scumm-m22-fate-hook8-de6e257897a8e150/report.json`,
`build/scumm-m22-save-de6e257897a8e150/report.json`,
`build/scumm-m22-lifetime-de6e257897a8e150/report.json`, and
`build/fate-m22-auditions-de6e257897a8e150/REVIEW.md`.

---

## M23A — authentic Fate room delivery and generic lifecycle

**Status:** Passed on 2026-08-26 for ROM
`6a622d0ac0fef4faa52808311ff08b73a9125aa50ecc737740de3b1c5167e640`.

**Pass:** complete authentic rooms 49 and 63 are cooked locally from the
user-supplied archive and acquired through the normal profile resource path.
Host and SNES discover and register complete ENCD, EXCD, and LSCR descriptors
with source mapping. Both authentic runs stop before PC zero dispatch and emit
no music. A copyright-free room pair separately proves the documented exit,
retirement, acquisition, activation, registration, entry, and local-script
lifecycle. Malformed or mismatched records reject before room, scheduler, or
audio mutation.

The authentic inspection proves room 49 queues start 80 and hook 14 before one
flush. Room 63 queues hook 8, then executes `startScript 151`, sound-82 status
and conditional operations, and only the sound-82-running path queues `0x0110`
and reaches the later flush. M21/M22 remain accepted bounded synthetic command
fixtures, not authentic room-entry traces.

Evidence and the exact M23B dependency cone: `docs/M23A_REPORT.md`.
No new timbre approval required.

---

## M23B — authentic Fate room-49 ENCD execution

**Status:** Passed on 2026-08-26 for positive ROM
`d0d3452e62c51801efd3e475b3005432446d7b0516d93ee209c84d09ea932951`
and negative-control ROM
`3efc7e1e66a7b48fd5e4d94d7ab4573a6274b4505422ba90dbd0eb8657d79300`.

**Pass:** complete authentic room 49 is acquired normally; its ENCD begins at
PC zero and executes every reached instruction. Global scripts 144/145 run
nested, indexed bit and sound-status conditions are evaluated, and authentic
offsets `+0x004F/+0x0057/+0x0065` queue start 80 plus hook 14 and flush once.
The accepted hook-14 TAD route becomes ready/playing with audible unclipped DSP
and no packet loss/rejection. Changing only sound-81 ownership follows the
authentic alternate branch to `+0x006D` and emits no sound-80 packet.

Evidence and the former room-63 dependency cone:
`docs/M23B_REPORT.md`.

---

## M23C — authentic Fate room-63 ENCD and delayed hook 8

**Status:** Passed on 2026-08-26 for positive ROM
`ca5ae06865ebca737bc1fd5bb7f2cadbc2c6bdc829f7b449431d91939ca3bbef`.

**Pass:** authentic room 49 first establishes audible hook-14 ownership. The
normal room transition runs room-49 EXCD, retires old locals, validates and
activates authentic room 63, and starts its ENCD at PC zero. Canonical `$1D`
class tests, authentic global script 151, sound-status queries, hook-8 queueing,
`0x0110`, and the later flush execute through the real interpreter. Hook 8 is
then consumed exactly once at the accepted M22 compiled boundary with no song
reload, false stop, gap, clipping, packet loss, or rejection. Independent
class-state and sound-82 controls take their authentic alternate paths.

Evidence and the source-proven next blocker are in `docs/M23C_REPORT.md`.
M24 has not begun. No new timbre approval required.

---

## M24R-A — bounded asynchronous TAD layer transition

**Status:** Passed on 2026-08-26 for synthetic ROM
`e68f1b513076cb34039aee47c1ae1724d87ce87c438496fca061abd00478d8b6`.

**Pass:** an isolated SAME-owned patch to pinned TAD adds one generation-bound
asynchronous request, one outgoing group gain, five fixed precompiled-lane
admissions, and deterministic explicit steals. A copyright-free song holds all
eight outgoing streams inside 4,000-tick notes. The driver observes the request
at its next tick without waiting for channel bytecode, admits B at ticks
`19,38,63,94,125`, completes A once at tick 256, never reloads the song, and
leaves B running. Stale generation commands are inert. Two cold Nexen processes
retain exact logical traces, zero TAD lag, no silent 20 ms window, and unclipped
DSP output.

This is backend feasibility only. Fate sound 82, instrument work, SCUMM state,
M24R-B, and M25 were not started. Full costs, caveats, identities, and the
maintenance judgment are in `docs/M24RA_REPORT.md`.

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

**Status:** Passed for the bounded C41 Fate sound-172 lane on 2026-08-24. The
backend is production code; expanding its arrangement table and adding speech
remain content/coverage work.

**Work:** Drive TAD protocol v20 behind semantic music, SFX, and control packets,
with explicit not-ready/queue rejection state.

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

## Closed: Phase 6L authentic room-49 -> room-63 transition

Phase 6L is accepted and closed. The authored room-49 path reaches room 63
through generic `loadRoomWithEgo` (`$24/$64/$A4/$E4`), completes room-63 ENCD,
and runs global script 151's stable authored delay/movement/message loop. The
accepted stable target state is actor 1 at `(430,140)`, walkbox 5, stationary,
with sound 80 owned and sounds 81/82 inactive. The retained `$010C` command is
the canonical sound-82-false branch result; it is not an unexplained pending
lifecycle operation. ROM SHA-256 is
`fddea1f7b877bbdb5f0bc9d9ca9bf8a13df4d4cc319a708410df178014b3a555`.

The legacy `make m23c` failure is layout-compatibility debt caused by the
relocated M25 build and does not invalidate this gate. The next authentic
boundary is the normal player sentence/input dispatcher after the global-151
loop; no synthetic input is selected here.

## Historical boundary — room-63 LSCR 202 delivery

This historical boundary has been cleared by the later scheduler, sentence,
movement, object-program, and Phase 6L milestones. The former authentic frontier was
room-49 LSCR 211 `+$026E`: `B2 02 00`, canonical
`setCameraAt(Var[2])`, reached with Var[2] equal to zero after authentic object
596 verb 10 chains into LSCR 211. Phase 6L subsequently cleared this boundary.
See `M25_START_OBJECT_REPORT.md`.

`$7B getActorWalkBox` now passes in authentic room-49 LSCR 216. Normal
execution subsequently enters room 63 and reaches ENCD `+$00DE`:
`2A CA FF` (`startScript 202`). Canonical `$2A` decoding succeeds, but the
current generated room-63 executable-local table excludes LSCR 202 even though
the complete descriptor is present in the cooked record.

Phase 6L subsequently enabled this descriptor and cleared the integrated
scheduler boundary; the remaining text in this historical section is retained
for provenance only.

## Machine personalities remain supported

After the engine-host path is stable, continue independently:

- MC68000 core behind a big-endian guest bus;
- Z80 core behind a little-endian guest bus;
- dynamic SAME-VDP trace translation;
- Genesis trace target before commercial ROM boot;
- current BOR design as inspected locally, whether native engine, VM, or hybrid;
- Superman and Black Tiger as target adapters around reusable CPU cores.

These are parallel clients of SAME, not prerequisites for SCUMM or AGI.
## After complete room-local LSCR lookup

Authentic room-63 LSCR 202 now resolves and executes from PC zero. Its first
`breakHere` leaves it runnable at `+$0006`, but the integrated room/audio driver
does not subsequently invoke the accepted general scheduler. The next honest
SCUMM gate is integrated scheduler resumption; it is not another opcode or
audio milestone. See `M25_ROOM_LOCAL_LOOKUP_REPORT.md`.
