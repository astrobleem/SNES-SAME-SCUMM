# M25 movement dependency preflight

## Outcome

Phase A concludes **B — missing movement-initiation opcode/state first**.
No production movement or pathfinding code was changed, and Phase B was not
started.

The accepted room-63 path does not execute a walk request.  It changes the
active room through the bounded `ScummV5_M23C_Driver` resource/lifecycle
harness, while actor 1 retains its room-49 state:

```text
room=49, position=(399,116), walkbox=11
destination=(-1,0), destination_box=11, moving=0
```

Consequently LSCR 202 is behaving correctly: it repeatedly reads the stored
walkbox and sees 11.  Adding per-tick walking now would have no canonical
destination to execute and would require inventing the very request this
preflight was intended to find.

The integrated ROM is unchanged:

```text
0a027331ec470324d8ea6071ff6ce8a274d0f1a571f3b752730542e3509312b3
```

## Resource and script identity

The source remains `/home/chad/fatedemo-box.zip`, SHA-256
`558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`.
`FATEDEMO/PLAYFATE.001` has SHA-256
`e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240`.
The complete room-63 ROOM payload has SHA-256
`94896a976d35531ab2ab5180a1a9f90387f34f4b12b0a8034bf1b3bbc901d390`.

LSCR 202 is 208 bytes and has SHA-256
`90e13f2440380e9f77fae78204e2cc0d8122124c73f1d06556cdfa1166049671`.
Its source mapping is:

| Coordinate | Value |
| --- | ---: |
| `PLAYFATE.001` program offset | `$07B0E7` (504039) |
| ROOM-relative program offset | `$00A940` (43328) |
| LSCR payload offset | `$0000` |
| cooked-record program offset | `$00AC08` (44040) |
| logical local script | 202 (local index 2 with 200 globals) |

The complete authentic byte stream is:

```text
0000: 1a 00 40 ff ff 80 7b 01 40 01 88 01 40 00 40 bb
0010: 00 48 01 40 02 00 09 00 13 01 02 08 03 ff 18 a6
0020: 00 48 01 40 06 00 09 00 13 01 02 10 04 ff 18 96
0030: 00 48 01 40 07 00 09 00 13 01 02 14 06 ff 18 86
0040: 00 48 01 40 08 00 09 00 13 01 02 14 06 ff 18 76
0050: 00 48 01 40 09 00 09 00 13 01 02 14 06 ff 18 66
0060: 00 48 01 40 0a 00 09 00 13 01 02 14 06 ff 18 56
0070: 00 48 01 40 0b 00 09 00 13 01 02 14 06 ff 18 46
0080: 00 48 01 40 0d 00 09 00 13 01 02 14 06 ff 18 36
0090: 00 48 01 40 0e 00 09 00 13 01 02 10 04 ff 18 26
00a0: 00 48 01 40 0f 00 09 00 13 01 02 10 04 ff 18 16
00b0: 00 48 01 40 10 00 09 00 13 01 02 10 04 ff 18 06
00c0: 00 13 01 02 08 02 ff 9a 00 40 01 40 18 36 ff a0
```

## Complete LSCR 202 decode

`Local[0]` is the last observed walkbox and `Local[1]` is the newly queried
stored walkbox.  The conditional opcodes jump when their predicate is false.

| Offset | Bytes | Canonical operation | Control flow/state |
| --- | --- | --- | --- |
| `$0000` | `1A 00 40 FF FF` | `move(Local[0], -1)` | Initializes prior box. |
| `$0005` | `80` | `breakHere` | Yields; resumes at `$0006`. |
| `$0006` | `7B 01 40 01` | `getActorWalkBox(Local[1], actor 1)` | Pure stored-field query. |
| `$000A` | `88 01 40 00 40 BB 00` | `if Local[1] != Local[0]` | If false, jump to `$00CC`; if true, choose a speed. |
| `$0011` | `48 01 40 02 00 09 00` | `if Local[1] == 2` | False skips to `$0021`. |
| `$0018` | `13 01 02 08 03 FF` | `actorOps(1): speed(8,3)` | Then `$001E` jumps to `$00C7`. |
| `$0021` | `48 01 40 06 00 09 00` | `if Local[1] == 6` | False skips to `$0031`. |
| `$0028` | `13 01 02 10 04 FF` | `actorOps(1): speed(16,4)` | Then `$002E` jumps to `$00C7`. |
| `$0031` | `48 01 40 07 00 09 00` | `if Local[1] == 7` | Speed `(20,6)`, jump from `$003E` to `$00C7`. |
| `$0041` | `48 01 40 08 00 09 00` | `if Local[1] == 8` | Speed `(20,6)`, jump from `$004E` to `$00C7`. |
| `$0051` | `48 01 40 09 00 09 00` | `if Local[1] == 9` | Speed `(20,6)`, jump from `$005E` to `$00C7`. |
| `$0061` | `48 01 40 0A 00 09 00` | `if Local[1] == 10` | Speed `(20,6)`, jump from `$006E` to `$00C7`. |
| `$0071` | `48 01 40 0B 00 09 00` | `if Local[1] == 11` | Speed `(20,6)`, jump from `$007E` to `$00C7`. |
| `$0081` | `48 01 40 0D 00 09 00` | `if Local[1] == 13` | Speed `(20,6)`, jump from `$008E` to `$00C7`. |
| `$0091` | `48 01 40 0E 00 09 00` | `if Local[1] == 14` | Speed `(16,4)`, jump from `$009E` to `$00C7`. |
| `$00A1` | `48 01 40 0F 00 09 00` | `if Local[1] == 15` | Speed `(16,4)`, jump from `$00AE` to `$00C7`. |
| `$00B1` | `48 01 40 10 00 09 00` | `if Local[1] == 16` | Speed `(16,4)`, jump from `$00BE` to `$00C7`. |
| `$00C1` | `13 01 02 08 02 FF` | default `actorOps(1): speed(8,2)` | Used for every other changed box. |
| `$00C7` | `9A 00 40 01 40` | `move(Local[0], Local[1])` | Commits the newly observed box. |
| `$00CC` | `18 36 FF` | relative jump to `$0005` | Re-enters the once-per-pass polling loop. |
| `$00CF` | `A0` | `stopObjectCode` | Structurally present but unreachable from the loop. |

Thus this script is not waiting for one geography-derived destination.  It is
a persistent walkbox-change monitor which adjusts actor 1's speed whenever the
stored walkbox changes:

```text
current actor walkbox = 11
expected condition    = actor.walkbox != Local[0] (currently != 11)
```

While actor 1 remains in box 11, `$000A` takes its false jump to `$00CC`, then
the script yields again at `$0005`.  On any change, it selects the speed for
the new box, copies `Local[1]` to `Local[0]`, and continues polling.

## Movement initiator search

There is no movement initiator in the accepted authentic room-63 instruction
path.  Room-63 ENCD runs from PC zero through `startScript(202)` at `$00DE` and
stops at `$00E1`; it does not execute the v5 `walkActorTo` family or another
operation which gives actor 1 a destination.

The transition which precedes it is explicitly a bounded profile driver.  In
`runtime/snes/engines/scumm_v5.pasm`, `ScummV5_M23C_Driver` waits for accepted
music ownership and calls `ScummV5_M23A_RequestRoom(63)`.  That correctly
exercises resource acquisition and room lifecycle, but it is not canonical
`loadRoomWithEgo`, a player Walk-To verb, or a script movement opcode.  It
neither transfers/places ego nor starts a walk.

The canonical reference demonstrates the missing distinction:

* a player Walk-To click reaches `verbExec`, records the virtual mouse X/Y,
  and calls `startWalkActor(x,y,-1)`;
* v5 `loadRoomWithEgo` places ego at the entry object during `startScene` and
  may call `startWalkActor(x,y,-1)` for its encoded post-entry destination;
* a script `walkActorTo` supplies an explicit destination.

None of those occurred here.  Therefore there is no authentic opcode offset,
destination X/Y, destination box, or requested final direction to report for
the current transition.  Supplying one would be a manufactured request.

## Host and SNES state at the would-be movement boundary

The host and fresh-power-on SNES evidence agree on the script-visible movement
state.  The SNES snapshot is from
`build/m25-movement-preflight-snes.json`; the host oracle recorded 600
successive `$7B` queries in
`build/m25-get-actor-walkbox/host-report.json`.

| Field | Host | SNES | Availability |
| --- | --- | --- | --- |
| room | 49 | 49 | both |
| X/Y | `(399,116)` | `(399,116)` | both |
| stored walkbox | 11 | 11 | both |
| destination X/Y | `(-1,0)` | `(-1,0)` | SNES compact state does not yet carry a complete canonical movement route |
| destination walkbox | 11 | 11 | both |
| current path box | 255/unset | not represented in the compact gate | host only |
| leg origin/target | `(0,0)/(0,0)` | not represented | host only |
| fraction/delta | zero | not represented | host only |
| movement flags | 0 | 0 | both |
| speed X/Y | `(8,2)` | not captured in compact actor record | host; SNES actorOps state exists separately |
| facing | 0 | 0 | both |
| target facing | no active target | not represented | host concept only |
| scale X/Y | `(255,255)` | `(255,255)` | both |
| ignoreBoxes | false | not represented in compact gate | host only |
| walkbox flags | room-49 box state | room-49 actor state | no room-63 movement owns them |

Across all 600 host queries, the first and last states are identical.  The
fresh SNES scheduler snapshots likewise remain `(399,116)`, box 11,
`moving=0`, with LSCR locals `[11,11]`.  Therefore:

* first movement tick: **not applicable**;
* tick box 11 is left: **not applicable**;
* tick LSCR 202's predicate becomes true: **not applicable**;
* final destination/stopping state: **not established**.

This stationary trace is the authoritative oracle for the state actually
constructed by the accepted path.  A moving oracle cannot be obtained without
first establishing the omitted authentic initiation event.

## Room-63 navigation resources

The supplied room has 17 walkboxes, numbered 0 through 16, and a static
authentic `BOXM`.  All room-63 box flags initially decode as zero.

| Box | Polygon/segment coordinates | Scale encoding |
| ---: | --- | ---: |
| 0 | sentinel/unusable coordinates | 255 |
| 1 | `(3,127) (255,127) (236,128) (3,128)` | 200 |
| 2 | `(125,100) (181,100) (137,127) (9,127)` | `$8001` |
| 3 | `(219,109) (267,109) (267,127) (171,127)` | `$8000` |
| 4 | `(267,110) (320,128) (320,131) (267,119)` | `$8000` |
| 5 | line `(320,131)` to `(432,140)` | 200 |
| 6 | line `(322,87)` to `(197,96)` | `$8003` |
| 7 | `(153,83) (175,83) (175,87) (153,87)` | `$8002` |
| 8 | line `(232,71)` to `(175,85)` | `$8002` |
| 9 | `(354,71) (399,71) (400,86) (323,86)` | 30 |
| 10 | `(290,55) (297,55) (399,71) (378,71)` | 25 |
| 11 | line `(182,64)` to `(158,83)` | `$8002` |
| 12 | `(241,104) (274,104) (267,109) (218,109)` | `$8000` |
| 13 | line `(139,76)` to `(153,83)` | `$8002` |
| 14 | `(152,87) (175,87) (175,100) (126,100)` | `$8002` |
| 15 | `(322,86) (399,86) (399,89) (322,89)` | `$8003` |
| 16 | `(175,89) (197,96) (197,100) (175,100)` | `$8002` |

The static BOXM row for source box 11 routes every other valid destination
through box 7 (and 11 to itself).  This does **not** establish an authentic
route for the current actor: its box 11 belongs to retained room-49 state, and
there is no requested point or destination box.

The complete original ROOM payload retained by the cooked `SC5ROOM` record
contains both BOXD and BOXM, so the supplied data is not missing.  The host
room decoder consumes both.  The generated SNES room record currently exposes
box count, mutable flags, and geometry, but not a runtime BOXM route table.
That is a real later resource-delivery dependency for multi-box walking, not
the first blocker.

The canonical responsibilities remain separate:

* `setBoxFlags` changes a box's raw mutable flag;
* `createBoxMatrix` rebuilds routing after a change which requires it;
* `getNextBox` consults the matrix;
* `adjustXYToBeInBox` normalizes a requested point and identifies its box;
* per-tick actor walking advances route legs and updates the stored walkbox.

The earlier accepted flag changes were in room 49, not room 63.  Room 63
already supplies a static BOXM, so the evidence does not presently require a
`createBoxMatrix` call.

## Implementation boundary and next gate

Classification **B** is mandatory at this point.  The immediate missing state
transition is an authentic ego/movement initiator, not a walking tick.  Phase B
therefore did not run.

The narrow next gate should establish one real source-bound entry/action into
room 63 before implementing navigation:

1. identify the preceding authentic script, object/verb, or input event which
   invokes `loadRoomWithEgo` or `startWalkActor` for this room;
2. execute it through the normal interpreter/input path;
3. prove actor 1 is transferred to room 63 and capture the requested point,
   entry object, adjusted destination, destination box, and final direction;
4. stop before advancing movement.

Only after that gate supplies a genuine destination can the next preflight
decide whether the required walk is a single bounded leg or needs the coherent
BOXM/edge-gate/per-tick navigation closure.  If the supplied demo does not
contain the preceding gameplay route, that absence must be documented and an
explicit, source-bound player-input fixture authorized; an arbitrary coordinate
chosen merely to make LSCR 202 change boxes would not be authentic evidence.

Costume 45, costume rendering, and text-glyph rendering remain independent
presentation limitations.  M24R-B remains paused.  No new timbre approval is
required.
